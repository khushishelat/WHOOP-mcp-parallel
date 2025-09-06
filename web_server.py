#!/usr/bin/env python3

import os
import asyncio
import json
import logging
import secrets
import time
from typing import Any, Dict
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, HTTPException, Request, Header, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.types import JSONRPCMessage
import sys

# Import our WHOOP MCP server
from whoop_mcp import mcp as whoop_mcp

# Token file path (use user's home directory for better compatibility)
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".whoop_token.json")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security Configuration
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
if not API_SECRET_KEY:
    # Generate a secure random key if not provided (for development)
    API_SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning("API_SECRET_KEY not set! Using temporary key. Set API_SECRET_KEY environment variable for production.")
    logger.info(f"🔑 Temporary API Key: {API_SECRET_KEY}")

# Rate limiting storage
request_counts = defaultdict(list)
RATE_LIMIT_REQUESTS = 60  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Protected endpoints that require API key
PROTECTED_ENDPOINTS = {"/mcp", "/auth", "/tools"}

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY", 
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}

# Create FastAPI app
app = FastAPI(
    title="WHOOP MCP Server",
    description="WHOOP Model Context Protocol Server - Web Interface",
    version="2.0.0",
)

# Security Functions
def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def is_rate_limited(client_ip: str) -> bool:
    """Check if client IP is rate limited"""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old requests
    request_counts[client_ip] = [req_time for req_time in request_counts[client_ip] if req_time > window_start]
    
    # Check if over limit
    if len(request_counts[client_ip]) >= RATE_LIMIT_REQUESTS:
        return True
    
    # Add current request
    request_counts[client_ip].append(now)
    return False

def verify_api_key(api_key: str) -> bool:
    """Verify API key is valid"""
    return api_key and api_key == API_SECRET_KEY

def requires_api_key(path: str) -> bool:
    """Check if endpoint requires API key"""
    return any(path.startswith(endpoint) for endpoint in PROTECTED_ENDPOINTS)

# Security Middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Apply security checks and headers"""
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    # Log request with enhanced details
    user_agent = request.headers.get("user-agent", "unknown")
    logger.info(f"🌐 {request.method} {request.url.path} from {client_ip}")
    logger.info(f"🔍 USER-AGENT: {user_agent}")
    
    # Flag potential Parallel AI requests
    if "parallel" in user_agent.lower() or "python" in user_agent.lower():
        logger.info(f"🤖 POTENTIAL PARALLEL AI REQUEST detected!")
    
    if request.method == "POST":
        logger.info(f"🔍 REQUEST HEADERS: {dict(request.headers)}")
    
    # Rate limiting
    if is_rate_limited(client_ip):
        logger.warning(f"🚫 Rate limit exceeded for {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Please try again later."},
            headers=SECURITY_HEADERS
        )
    
    # API key authentication for protected endpoints
    if requires_api_key(request.url.path):
        api_key = request.headers.get("X-API-Key")
        if not verify_api_key(api_key):
            logger.warning(f"🔐 Unauthorized access attempt to {request.url.path} from {client_ip}")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized. Valid X-API-Key header required."},
                headers=SECURITY_HEADERS
            )
        logger.info(f"✅ Authorized access to {request.url.path} from {client_ip}")
    
    # Process request
    response = await call_next(request)
    
    # Add security headers
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"📊 {request.method} {request.url.path} → {response.status_code} ({process_time:.3f}s)")
    
    return response

# Add CORS middleware (with more restrictive settings for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:*", "https://127.0.0.1:*"] if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for fly.io"""
    return {"status": "healthy", "service": "whoop-mcp"}

# Root endpoint with API info
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "WHOOP MCP Server",
        "version": "2.0.0",
        "description": "WHOOP Model Context Protocol Server with enhanced API v2 features",
        "security": {
            "protected_endpoints": list(PROTECTED_ENDPOINTS),
            "authentication": "X-API-Key header required for protected endpoints",
            "rate_limit": f"{RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds"
        },
        "endpoints": {
            "health": "/health (public)",
            "mcp_http": "/mcp (POST) (protected - requires X-API-Key) - HTTP transport for Parallel API",
            "mcp_ws": "/mcp (WebSocket) (protected - requires X-API-Key) - WebSocket transport", 
            "tools": "/tools (protected - requires X-API-Key)",
            "auth": "/auth (protected - requires X-API-Key)"
        },
        "features": [
            "🔐 Secure API key authentication",
            "🛡️ Rate limiting protection", 
            "📊 Request logging & monitoring",
            "🚀 WHOOP API v2 integration",
            "📈 Enhanced workout analysis with elevation tracking",
            "😴 Advanced sleep quality assessment", 
            "💚 Recovery load analysis",
            "🎯 Training readiness scoring",
            "📊 Body composition tracking",
            "🇺🇸 US units & EST timezone formatting",
            "📅 Comprehensive daily summaries",
            "🌐 HTTP transport (Parallel API compatible)",
            "🔌 WebSocket transport (real-time)"
        ],
        "usage": {
            "authentication": "Include 'X-API-Key: your-api-key' header for protected endpoints",
            "http_mcp": "POST to /mcp with X-API-Key header for HTTP MCP communication (Parallel API compatible)",
            "websocket_mcp": "Connect to /mcp (WebSocket) with X-API-Key header for real-time MCP communication"
        }
    }

# Get available tools
@app.get("/tools")
async def get_tools():
    """Get list of available MCP tools"""
    try:
        # FastMCP stores tools in a different way - let's try to access them
        tools = []
        
        # Try to get tools from FastMCP
        if hasattr(whoop_mcp, 'mcp') and hasattr(whoop_mcp.mcp, '_tools'):
            for tool_name, tool_info in whoop_mcp.mcp._tools.items():
                tools.append({
                    "name": tool_name,
                    "description": tool_info.get("description", "No description available")
                })
        elif hasattr(whoop_mcp, 'mcp') and hasattr(whoop_mcp.mcp, 'tools'):
            for tool_name, tool_info in whoop_mcp.mcp.tools.items():
                tools.append({
                    "name": tool_name,
                    "description": tool_info.get("description", "No description available")
                })
        else:
            # Fallback: List the known tools manually
            known_tools = [
                "get_sleep_daily", "get_recovery_daily", "get_workout_daily", "get_cycle_daily",
                "get_profile_data", "get_body_measurement_data", "get_sports_mapping",
                "get_workout_analysis", "get_sleep_quality_analysis", "get_recovery_load_analysis",
                "get_training_readiness", "search_whoop_sports", "set_custom_prompt",
                "get_current_prompt", "get_daily_summary", "get_workout_trends",
                "get_recovery_trends", "get_strain_trends", "get_sleep_trends",
                "get_recovery_chart", "get_tools_guide", "authenticate_with_whoop", "check_authentication_status"
            ]
            for tool_name in known_tools:
                tools.append({
                    "name": tool_name,
                    "description": f"WHOOP MCP tool: {tool_name}"
                })
        
        return {"tools": tools}
        
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        return {"tools": [], "error": "Could not retrieve tools list"}

# Authentication status endpoint
@app.get("/auth")
async def auth_status():
    """Check WHOOP authentication status"""
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
        return {
            "authenticated": True,
            "token_type": token_data.get("token_type", "unknown"),
            "expires_in": token_data.get("expires_in", "unknown")
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {"authenticated": False}

# WHOOP OAuth initiation endpoint
@app.get("/whoop/auth")
async def whoop_auth_start():
    """Start WHOOP OAuth authentication flow"""
    import secrets
    from urllib.parse import urlencode
    
    # Generate secure state parameter
    state = secrets.token_urlsafe(32)
    
    # Store state for validation (in production, use Redis or database)
    # For now, we'll validate in the callback
    
    # WHOOP OAuth parameters
    client_id = os.getenv("WHOOP_CLIENT_ID")
    redirect_uri = os.getenv("WHOOP_REDIRECT_URI", "https://whoop-mcp.fly.dev/whoop/callback")
    
    if not client_id:
        return JSONResponse(
            status_code=500,
            content={
                "error": "WHOOP client ID not configured",
                "message": "Server configuration error. Please contact administrator."
            }
        )
    
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:profile read:body_measurement read:cycles read:recovery read:sleep read:workout",
        "state": state
    }
    
    auth_url = f"https://api.prod.whoop.com/oauth/oauth2/auth?{urlencode(auth_params)}"
    
    return {
        "auth_url": auth_url,
        "state": state,
        "instructions": "Visit the auth_url to authenticate with WHOOP",
        "callback_uri": redirect_uri
    }

# WHOOP OAuth callback endpoint
@app.get("/whoop/callback")
async def whoop_oauth_callback(request: Request):
    """Handle WHOOP OAuth callback"""
    import httpx
    from urllib.parse import parse_qs
    
    # Get query parameters
    query_params = dict(request.query_params)
    auth_code = query_params.get("code")
    error = query_params.get("error")
    state = query_params.get("state")
    
    if error:
        logger.error(f"WHOOP OAuth error: {error}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "WHOOP authentication failed",
                "details": error,
                "message": "Please try authenticating again"
            }
        )
    
    if not auth_code:
        logger.error("No authorization code received from WHOOP")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing authorization code",
                "message": "Please start the authentication process again"
            }
        )
    
    try:
        # Exchange authorization code for access token
        token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
        
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": os.getenv("WHOOP_CLIENT_ID"),
            "client_secret": os.getenv("WHOOP_CLIENT_SECRET"),
            "redirect_uri": os.getenv("WHOOP_REDIRECT_URI", "https://whoop-mcp.fly.dev/whoop/callback")
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            
            if response.status_code == 200:
                token_response = response.json()
                
                # Save token to file
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_response, f)
                
                logger.info("WHOOP authentication successful")
                
                # Return success page
                return JSONResponse(
                    content={
                        "success": True,
                        "message": "WHOOP authentication successful!",
                        "token_type": token_response.get("token_type"),
                        "expires_in": token_response.get("expires_in"),
                        "instructions": "You can now close this tab and use WHOOP tools in your MCP client."
                    }
                )
            else:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Token exchange failed",
                        "status_code": response.status_code,
                        "message": "Failed to exchange authorization code for access token"
                    }
                )
                
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Authentication processing failed",
                "message": "An error occurred while processing the authentication"
            }
        )

# HTTP endpoint for MCP communication (Parallel API compatible)
@app.post("/mcp")
async def mcp_http(request: Request):
    # CRITICAL: Log every single MCP request attempt
    logger.critical(f"🚨 MCP ENDPOINT HIT from {request.client.host}")
    """HTTP endpoint for MCP communication (compatible with Parallel Task API)"""
    
    client_ip = get_client_ip(request)
    
    try:
        # Get request body
        body = await request.body()
        data = body.decode('utf-8')
        
        # Parse JSON-RPC message with validation
        if len(data) > 10000:  # Limit message size
            raise ValueError("Message too large")
        
        message = json.loads(data)
        
        # Validate message structure
        if not isinstance(message, dict):
            raise ValueError("Invalid message format")
        
        # Sanitize input
        method = str(message.get("method", "")).strip()[:100]  # Limit method name length
        message_id = message.get("id")
        
        # Enhanced MCP request logging
        user_agent = request.headers.get("user-agent", "unknown")
        logger.critical(f"📥 MCP REQUEST: {method} from {client_ip}")
        logger.critical(f"📥 MCP USER-AGENT: {user_agent}")
        logger.critical(f"📥 MCP FULL MESSAGE: {message}")
        
        # Detect source of request
        if "parallel" in user_agent.lower() or "httpx" in user_agent.lower():
            logger.critical(f"🤖 CONFIRMED PARALLEL AI MCP REQUEST: {method}")
        else:
            logger.critical(f"👤 MANUAL/CURL MCP REQUEST: {method}")
        
        # Handle different message types
        if message.get("method") == "initialize":
            # MCP initialization
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "prompts": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "whoop-mcp",
                        "version": "2.0.0"
                    }
                }
            }
            return JSONResponse(content=response)
        
        elif message.get("method") == "tools/list":
            # List available tools
            logger.critical(f"🔧 TOOLS/LIST REQUEST from {client_ip} - user_agent: {user_agent}")
            try:
                tools = []
                if hasattr(whoop_mcp, 'mcp') and hasattr(whoop_mcp.mcp, '_tools'):
                    for tool_name, tool_info in whoop_mcp.mcp._tools.items():
                        tool_schema = {
                            "name": tool_name,
                            "description": tool_info.get("description", "No description available"),
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                        tools.append(tool_schema)
                elif hasattr(whoop_mcp, 'mcp') and hasattr(whoop_mcp.mcp, 'tools'):
                    for tool_name, tool_info in whoop_mcp.mcp.tools.items():
                        tool_schema = {
                            "name": tool_name,
                            "description": tool_info.get("description", "No description available"),
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                        tools.append(tool_schema)
                else:
                    # Fallback: List the known tools manually with proper descriptions
                    known_tools = {
                        "get_sleep_daily": "Get detailed sleep data for a single night including quality, duration, efficiency, and stages",
                        "get_recovery_daily": "Get detailed recovery metrics for a single day including recovery score, HRV, and RHR",
                        "get_workout_daily": "Get detailed data for a single workout including strain, heart rate, and performance metrics",
                        "get_cycle_daily": "Get daily strain and physiological cycle data for a single day",
                        "get_profile_data": "Get the user's personal profile information from WHOOP",
                        "get_body_measurement_data": "Get the user's personal body measurement data from WHOOP",
                        "get_sports_mapping": "Get WHOOP sports mapping data for workout types",
                        "get_workout_analysis": "Analyze the user's workout data and provide insights",
                        "get_sleep_quality_analysis": "Analyze the user's sleep quality and provide personalized insights",
                        "get_recovery_load_analysis": "Analyze the user's recovery and training load data",
                        "get_training_readiness": "Get comprehensive training readiness assessment combining recovery, sleep, and strain data",
                        "search_whoop_sports": "Search for WHOOP sport types and activities",
                        "set_custom_prompt": "Set a custom prompt for WHOOP data analysis",
                        "get_custom_prompt": "Get the current custom prompt for WHOOP data analysis",
                        "clear_custom_prompt": "Clear the custom prompt for WHOOP data analysis",
                        "get_daily_summary": "Get a comprehensive daily health summary combining all WHOOP metrics with smart recommendations",
                        "get_workout_trends": "Analyze workout trends, training patterns, and athletic profiling over multiple days (2-60 days)",
                        "get_recovery_trends": "Analyze recovery trends and patterns over multiple days (7-60 days)",
                        "get_strain_trends": "Analyze strain and training load progression over multiple days (2-60 days)",
                        "get_sleep_trends": "Analyze sleep patterns and quality trends over multiple days (2-60 days)",
                        "get_recovery_chart": "Generate ASCII chart visualization of recovery score trends over time",
                        "get_tools_guide": "Get a comprehensive guide to all available WHOOP analytics tools and their capabilities"
                    }
                    for tool_name, description in known_tools.items():
                        tool_schema = {
                            "name": tool_name,
                            "description": description,
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                        tools.append(tool_schema)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {"tools": tools}
                }
                logger.critical(f"🔧 TOOLS/LIST SUCCESS: Returning {len(tools)} tools")
                return JSONResponse(content=response)
            except Exception as e:
                logger.critical(f"🚨 TOOLS/LIST ERROR: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32603,
                        "message": f"Failed to list tools: {str(e)}"
                    }
                }
                return JSONResponse(content=error_response, status_code=500)
        
        elif message.get("method") == "tools/call":
            # Call a tool
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            # 🔍 DETAILED LOGGING for debugging
            logger.info(f"🔧 TOOL CALL DEBUG - Tool: {tool_name}")
            logger.info(f"🔧 TOOL CALL DEBUG - Arguments: {arguments}")
            logger.info(f"🔧 TOOL CALL DEBUG - Full params: {params}")
            
            # Valid WHOOP MCP tools that can provide real user data
            valid_tools = [
                "get_sleep_daily", "get_recovery_daily", "get_workout_daily", "get_cycle_daily",
                "get_profile_data", "get_body_measurement_data", "get_sports_mapping",
                "get_workout_analysis", "get_sleep_quality_analysis", "get_recovery_load_analysis",
                "get_training_readiness", "search_whoop_sports", "set_custom_prompt",
                "get_current_prompt", "get_daily_summary", "get_workout_trends",
                "get_recovery_trends", "get_strain_trends", "get_sleep_trends",
                "get_recovery_chart", "get_tools_guide", "authenticate_with_whoop", "check_authentication_status"
            ]
            
            if tool_name in valid_tools:
                try:
                    # Call the tool using proper FastMCP method
                    logger.info(f"🔧 TOOL CALL DEBUG - Calling FastMCP with tool: {tool_name}")
                    result = await whoop_mcp.call_tool(tool_name, arguments)
                    logger.info(f"🔧 TOOL CALL DEBUG - Raw result type: {type(result)}")
                    logger.info(f"🔧 TOOL CALL DEBUG - Raw result (first 200 chars): {str(result)[:200]}...")
                    
                    # Extract clean text from FastMCP response
                    clean_text = str(result)
                    if hasattr(result, '__iter__') and len(result) > 0:
                        # If it's a tuple/list with TextContent objects, extract the text
                        if hasattr(result[0], '__iter__'):
                            for item in result[0]:
                                if hasattr(item, 'text'):
                                    clean_text = item.text
                                    break
                        # If result has a 'result' key in a dict, use that
                        elif len(result) > 1 and isinstance(result[1], dict) and 'result' in result[1]:
                            clean_text = result[1]['result']
                    
                    logger.info(f"🔧 TOOL CALL DEBUG - Extracted clean text (first 200 chars): {clean_text[:200]}...")
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": clean_text
                                }
                            ]
                        }
                    }
                    logger.info(f"🔧 TOOL CALL DEBUG - Response format: {type(response)}")
                    logger.info(f"🔧 TOOL CALL DEBUG - Response content preview: {str(response)[:300]}...")
                except Exception as e:
                    # Log detailed error for debugging but don't expose to client
                    logger.error(f"🔧 TOOL CALL DEBUG - Tool execution error for {tool_name}: {e}")
                    logger.error(f"🔧 TOOL CALL DEBUG - Exception type: {type(e)}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32603,
                            "message": "Tool execution failed. Please check your authentication and try again."
                        }
                    }
            else:
                logger.warning(f"🔧 TOOL CALL DEBUG - Tool not found: {tool_name}")
                logger.warning(f"🔧 TOOL CALL DEBUG - Valid tools: {valid_tools}")
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }
            
            return JSONResponse(content=response)
        
        else:
            # Unknown method
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {message.get('method')}"
                }
            }
            return JSONResponse(content=response)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from {client_ip}: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": "Invalid JSON format"
            }
        }
        return JSONResponse(content=error_response, status_code=400)
    
    except ValueError as e:
        logger.error(f"Validation error from {client_ip}: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": message_id if 'message_id' in locals() else None,
            "error": {
                "code": -32602,
                "message": "Invalid request format"
            }
        }
        return JSONResponse(content=error_response, status_code=400)
    
    except Exception as e:
        logger.error(f"Unexpected error from {client_ip}: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": message_id if 'message_id' in locals() else None,
            "error": {
                "code": -32603,
                "message": "Internal server error"
            }
        }
        return JSONResponse(content=error_response, status_code=500)

# WebSocket endpoint for MCP communication
@app.websocket("/mcp")
async def mcp_websocket(websocket: WebSocket):
    """WebSocket endpoint for MCP communication"""
    
    # Check API key for WebSocket connection
    api_key = None
    for name, value in websocket.headers.items():
        if name.lower() == "x-api-key":
            api_key = value
            break
    
    if not verify_api_key(api_key):
        client_ip = websocket.client.host if websocket.client else "unknown"
        logger.warning(f"🔐 Unauthorized WebSocket connection attempt from {client_ip}")
        await websocket.close(code=1008, reason="Unauthorized: Valid X-API-Key header required")
        return
    
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info(f"✅ Authorized MCP WebSocket connection established from {client_ip}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received MCP message: {data[:100]}...")
            
            try:
                # Parse JSON-RPC message with validation
                if len(data) > 10000:  # Limit message size
                    raise ValueError("Message too large")
                
                message = json.loads(data)
                
                # Validate message structure
                if not isinstance(message, dict):
                    raise ValueError("Invalid message format")
                
                # Sanitize input
                method = str(message.get("method", "")).strip()[:100]  # Limit method name length
                message_id = message.get("id")
                
                # Handle different message types
                if message.get("method") == "initialize":
                    # MCP initialization
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {},
                                "prompts": {},
                                "resources": {}
                            },
                            "serverInfo": {
                                "name": "whoop-mcp",
                                "version": "2.0.0"
                            }
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                
                elif message.get("method") == "tools/list":
                    # List available tools
                    tools = []
                    for tool_name, tool_func in whoop_mcp._tools.items():
                        tool_schema = {
                            "name": tool_name,
                            "description": tool_func.__doc__ or "No description available",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                        tools.append(tool_schema)
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {"tools": tools}
                    }
                    await websocket.send_text(json.dumps(response))
                
                elif message.get("method") == "tools/call":
                    # Call a tool
                    params = message.get("params", {})
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if tool_name in whoop_mcp._tools:
                        try:
                            # Call the tool function
                            tool_func = whoop_mcp._tools[tool_name]
                            if asyncio.iscoroutinefunction(tool_func):
                                result = await tool_func(**arguments)
                            else:
                                result = tool_func(**arguments)
                            
                            response = {
                                "jsonrpc": "2.0",
                                "id": message.get("id"),
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": str(result)
                                        }
                                    ]
                                }
                            }
                        except Exception as e:
                            # Log detailed error for debugging but don't expose to client
                            logger.error(f"Tool execution error for {tool_name}: {e}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": message.get("id"),
                                "error": {
                                    "code": -32603,
                                    "message": "Tool execution failed. Please check your authentication and try again."
                                }
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": message.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Tool not found: {tool_name}"
                            }
                        }
                    
                    await websocket.send_text(json.dumps(response))
                
                else:
                    # Unknown method
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {message.get('method')}"
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error from {client_ip}: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Invalid JSON format"
                    }
                }
                await websocket.send_text(json.dumps(error_response))
            
            except ValueError as e:
                logger.error(f"Validation error from {client_ip}: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message_id if 'message_id' in locals() else None,
                    "error": {
                        "code": -32602,
                        "message": "Invalid request format"
                    }
                }
                await websocket.send_text(json.dumps(error_response))
            
            except Exception as e:
                logger.error(f"Unexpected error from {client_ip}: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message_id if 'message_id' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": "Internal server error"
                    }
                }
                await websocket.send_text(json.dumps(error_response))
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("MCP WebSocket connection closed")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting WHOOP MCP Web Server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
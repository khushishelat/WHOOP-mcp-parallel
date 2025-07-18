# WHOOP MCP Server - HTTP REST API Guide

This guide covers how to use your deployed WHOOP MCP server through HTTP REST API endpoints, enabling integration with any HTTP client or automation system.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Making HTTP Requests](#making-http-requests)
- [Response Formats](#response-formats)
- [Integration Examples](#integration-examples)
- [Automation Scripts](#automation-scripts)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Overview

Your WHOOP MCP server at **`https://whoop-mcp.fly.dev`** provides HTTP REST API endpoints for accessing server information, checking authentication status, and getting available tools.

**Benefits of HTTP API:**
- 🌐 **Universal compatibility** - Works with any HTTP client
- 🔧 **Simple integration** - Standard REST API patterns
- 🤖 **Automation friendly** - Perfect for scripts and workflows
- 📊 **Monitoring support** - Easy health checks and status monitoring
- 🔐 **Secure authentication** - API key-based access control

**Base URL:** `https://whoop-mcp.fly.dev`

## Prerequisites

### 1. API Key
Your secure API key for authentication:
```
YOUR_API_KEY_HERE
```

🚨 **SECURITY WARNING**: 
- **Never commit API keys to git** 
- **Replace `YOUR_API_KEY_HERE` with your actual key**
- **Keep this key secure** - it provides access to your WHOOP data
- **Use environment variables** for production deployments

### 2. HTTP Client
Any HTTP client can be used:
- **curl** (command line)
- **Python requests** library
- **Node.js fetch/axios**
- **Postman** (GUI)
- **Browser fetch API**

### 3. Network Access
Ensure you can reach:
- `https://whoop-mcp.fly.dev` (HTTPS required)

## API Endpoints

### 1. Public Endpoints (No Authentication Required)

#### Health Check
```http
GET https://whoop-mcp.fly.dev/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "whoop-mcp"
}
```

#### Server Information
```http
GET https://whoop-mcp.fly.dev/
```

**Response:**
```json
{
  "name": "WHOOP MCP Server",
  "version": "2.0.0",
  "description": "WHOOP Model Context Protocol Server with enhanced API v2 features",
  "security": {
    "protected_endpoints": ["/tools", "/auth", "/mcp"],
    "authentication": "X-API-Key header required for protected endpoints",
    "rate_limit": "60 requests per 60 seconds"
  },
  "endpoints": {
    "health": "/health (public)",
    "mcp_ws": "/mcp (protected - requires X-API-Key)",
    "tools": "/tools (protected - requires X-API-Key)",
    "auth": "/auth (protected - requires X-API-Key)"
  },
  "features": [
    "🔐 Secure API key authentication",
    "🛡️ Rate limiting protection",
    "📊 Request logging & monitoring",
    "🚀 WHOOP API v2 integration"
  ]
}
```

### 2. Protected Endpoints (Authentication Required)

#### Get Available Tools
```http
GET https://whoop-mcp.fly.dev/tools
Authorization: X-API-Key: YOUR_API_KEY_HERE
```

**Response:**
```json
{
  "tools": [
    {
      "name": "get_sleep_data",
      "description": "WHOOP MCP tool: get_sleep_data"
    },
    {
      "name": "get_recovery_data",
      "description": "WHOOP MCP tool: get_recovery_data"
    },
    {
      "name": "get_workout_data",
      "description": "WHOOP MCP tool: get_workout_data"
    }
  ]
}
```

#### Check Authentication Status
```http
GET https://whoop-mcp.fly.dev/auth
Authorization: X-API-Key: YOUR_API_KEY_HERE
```

**Response (authenticated):**
```json
{
  "authenticated": true,
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Response (not authenticated):**
```json
{
  "authenticated": false
}
```

#### WebSocket Endpoint
```http
WebSocket: wss://whoop-mcp.fly.dev/mcp
Authorization: X-API-Key: YOUR_API_KEY_HERE
```

*Note: See [WebSocket Guide](websocket-guide.md) for WebSocket usage.*

## Authentication

### 1. API Key Header
All protected endpoints require the `X-API-Key` header:

```bash
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
     https://whoop-mcp.fly.dev/tools
```

### 2. Authentication Responses

#### Successful Authentication
- **Status Code:** `200 OK`
- **Response:** Contains requested data

#### Missing API Key
- **Status Code:** `401 Unauthorized`
- **Response:**
```json
{
  "error": "Unauthorized. Valid X-API-Key header required."
}
```

#### Invalid API Key
- **Status Code:** `401 Unauthorized`
- **Response:**
```json
{
  "error": "Unauthorized. Valid X-API-Key header required."
}
```

### 3. Rate Limiting
- **Limit:** 60 requests per minute per IP address
- **Status Code:** `429 Too Many Requests`
- **Response:**
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

## Making HTTP Requests

### 1. Using curl

#### Basic Health Check
```bash
curl https://whoop-mcp.fly.dev/health
```

#### Get Server Information
```bash
curl https://whoop-mcp.fly.dev/ | jq .
```

#### Get Available Tools
```bash
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
     https://whoop-mcp.fly.dev/tools | jq .
```

#### Check Authentication Status
```bash
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
     https://whoop-mcp.fly.dev/auth | jq .
```

### 2. Using Python requests

```python
import requests

# Configuration
BASE_URL = "https://whoop-mcp.fly.dev"
API_KEY = "YOUR_API_KEY_HERE"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Health check (no auth required)
response = requests.get(f"{BASE_URL}/health")
print("Health:", response.json())

# Get server info (no auth required)
response = requests.get(f"{BASE_URL}/")
print("Server Info:", response.json())

# Get available tools (auth required)
response = requests.get(f"{BASE_URL}/tools", headers=headers)
if response.status_code == 200:
    tools = response.json()
    print(f"Available tools: {len(tools['tools'])}")
    for tool in tools['tools']:
        print(f"  - {tool['name']}: {tool['description']}")
else:
    print(f"Error: {response.status_code} - {response.text}")

# Check authentication status
response = requests.get(f"{BASE_URL}/auth", headers=headers)
auth_status = response.json()
print("Authentication Status:", auth_status)
```

### 3. Using Node.js fetch

```javascript
const BASE_URL = "https://whoop-mcp.fly.dev";
const API_KEY = "YOUR_API_KEY_HERE";

const headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
};

// Health check
fetch(`${BASE_URL}/health`)
    .then(response => response.json())
    .then(data => console.log('Health:', data));

// Get available tools
fetch(`${BASE_URL}/tools`, { headers })
    .then(response => response.json())
    .then(data => {
        console.log(`Available tools: ${data.tools.length}`);
        data.tools.forEach(tool => {
            console.log(`  - ${tool.name}: ${tool.description}`);
        });
    })
    .catch(error => console.error('Error:', error));

// Check authentication
fetch(`${BASE_URL}/auth`, { headers })
    .then(response => response.json())
    .then(data => console.log('Auth Status:', data));
```

### 4. Using Browser JavaScript

```html
<!DOCTYPE html>
<html>
<head>
    <title>WHOOP MCP HTTP Client</title>
</head>
<body>
    <div id="output"></div>
    
    <script>
        const BASE_URL = "https://whoop-mcp.fly.dev";
        const API_KEY = "YOUR_API_KEY_HERE";
        
        async function checkServer() {
            try {
                // Health check (public)
                const healthResponse = await fetch(`${BASE_URL}/health`);
                const healthData = await healthResponse.json();
                console.log('Health:', healthData);
                
                // Get tools (requires API key)
                const toolsResponse = await fetch(`${BASE_URL}/tools`, {
                    headers: {
                        'X-API-Key': API_KEY
                    }
                });
                
                if (toolsResponse.ok) {
                    const toolsData = await toolsResponse.json();
                    document.getElementById('output').innerHTML = 
                        `<h3>Available Tools (${toolsData.tools.length}):</h3>` +
                        toolsData.tools.map(tool => 
                            `<p><strong>${tool.name}</strong>: ${tool.description}</p>`
                        ).join('');
                } else {
                    console.error('Failed to fetch tools:', toolsResponse.status);
                }
                
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        // Run on page load
        checkServer();
    </script>
</body>
</html>
```

## Response Formats

### 1. Success Responses

#### JSON Structure
All successful responses return JSON with appropriate HTTP status codes:

```json
{
  "data": "response content",
  "status": "success"
}
```

#### Tools List Response
```json
{
  "tools": [
    {
      "name": "tool_name",
      "description": "Tool description"
    }
  ]
}
```

### 2. Error Responses

#### Authentication Error (401)
```json
{
  "error": "Unauthorized. Valid X-API-Key header required."
}
```

#### Rate Limit Error (429)
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

#### Server Error (500)
```json
{
  "error": "Internal server error"
}
```

### 3. Security Headers

All responses include security headers:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'
Referrer-Policy: strict-origin-when-cross-origin
```

## Integration Examples

### 1. Health Monitoring Script

```bash
#!/bin/bash
# health-monitor.sh - Monitor WHOOP MCP server health

URL="https://whoop-mcp.fly.dev/health"
API_KEY="YOUR_API_KEY_HERE"

while true; do
    RESPONSE=$(curl -s -w "%{http_code}" "$URL")
    HTTP_CODE="${RESPONSE: -3}"
    BODY="${RESPONSE%???}"
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo "$(date): ✅ Server healthy - $BODY"
    else
        echo "$(date): ❌ Server unhealthy - HTTP $HTTP_CODE"
    fi
    
    sleep 60  # Check every minute
done
```

### 2. Python Monitoring Class

```python
import requests
import time
from datetime import datetime
import logging

class WHOOPMCPMonitor:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
        self.logger = logging.getLogger(__name__)
    
    def check_health(self):
        """Check server health status"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, str(e)
    
    def check_auth(self):
        """Check authentication status"""
        try:
            response = requests.get(f"{self.base_url}/auth", headers=self.headers, timeout=10)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)
    
    def get_tools(self):
        """Get available tools"""
        try:
            response = requests.get(f"{self.base_url}/tools", headers=self.headers, timeout=10)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)
    
    def full_health_check(self):
        """Perform comprehensive health check"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'health': None,
            'auth': None,
            'tools': None
        }
        
        # Check basic health
        health_ok, health_data = self.check_health()
        results['health'] = {'status': 'ok' if health_ok else 'error', 'data': health_data}
        
        # Check authentication
        auth_ok, auth_data = self.check_auth()
        results['auth'] = {'status': 'ok' if auth_ok else 'error', 'data': auth_data}
        
        # Check tools availability
        tools_ok, tools_data = self.get_tools()
        results['tools'] = {'status': 'ok' if tools_ok else 'error', 'data': tools_data}
        
        return results

# Usage
monitor = WHOOPMCPMonitor(
    "https://whoop-mcp.fly.dev",
    "YOUR_API_KEY_HERE"
)

# Run health check
results = monitor.full_health_check()
print(f"Health Check Results: {results}")
```

### 3. Node.js Service Integration

```javascript
class WHOOPMCPClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }
    
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            ...options,
            headers: { ...this.headers, ...options.headers }
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${data.error || 'Unknown error'}`);
            }
            
            return data;
        } catch (error) {
            console.error(`Request to ${endpoint} failed:`, error.message);
            throw error;
        }
    }
    
    async getHealth() {
        // Public endpoint - no auth required
        const response = await fetch(`${this.baseUrl}/health`);
        return response.json();
    }
    
    async getServerInfo() {
        // Public endpoint - no auth required
        const response = await fetch(`${this.baseUrl}/`);
        return response.json();
    }
    
    async getTools() {
        return this.makeRequest('/tools');
    }
    
    async getAuthStatus() {
        return this.makeRequest('/auth');
    }
    
    async isServerHealthy() {
        try {
            const health = await this.getHealth();
            return health.status === 'healthy';
        } catch {
            return false;
        }
    }
}

// Usage
const client = new WHOOPMCPClient(
    'https://whoop-mcp.fly.dev',
    'YOUR_API_KEY_HERE'
);

// Example usage
(async () => {
    try {
        const isHealthy = await client.isServerHealthy();
        console.log('Server healthy:', isHealthy);
        
        if (isHealthy) {
            const tools = await client.getTools();
            console.log('Available tools:', tools.tools.length);
            
            const authStatus = await client.getAuthStatus();
            console.log('Auth status:', authStatus);
        }
    } catch (error) {
        console.error('Error:', error.message);
    }
})();
```

## Automation Scripts

### 1. Daily Health Report

```python
#!/usr/bin/env python3
"""
Daily WHOOP MCP Server Health Report
Checks server status and emails a report
"""

import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def generate_health_report():
    base_url = "https://whoop-mcp.fly.dev"
    api_key = "YOUR_API_KEY_HERE"
    headers = {"X-API-Key": api_key}
    
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'UNKNOWN',
        'details': {}
    }
    
    try:
        # Health check
        health_resp = requests.get(f"{base_url}/health", timeout=10)
        report['details']['health'] = {
            'status_code': health_resp.status_code,
            'response': health_resp.json() if health_resp.status_code == 200 else health_resp.text
        }
        
        # Auth check
        auth_resp = requests.get(f"{base_url}/auth", headers=headers, timeout=10)
        report['details']['auth'] = {
            'status_code': auth_resp.status_code,
            'response': auth_resp.json() if auth_resp.status_code == 200 else auth_resp.text
        }
        
        # Tools check
        tools_resp = requests.get(f"{base_url}/tools", headers=headers, timeout=10)
        report['details']['tools'] = {
            'status_code': tools_resp.status_code,
            'count': len(tools_resp.json().get('tools', [])) if tools_resp.status_code == 200 else 0
        }
        
        # Overall status
        if all(check['status_code'] == 200 for check in report['details'].values()):
            report['status'] = 'HEALTHY'
        else:
            report['status'] = 'DEGRADED'
            
    except Exception as e:
        report['status'] = 'ERROR'
        report['error'] = str(e)
    
    return report

def send_email_report(report):
    """Send email report (configure SMTP settings)"""
    subject = f"WHOOP MCP Server Status: {report['status']} - {report['timestamp']}"
    
    body = f"""
WHOOP MCP Server Daily Health Report
====================================

Timestamp: {report['timestamp']}
Overall Status: {report['status']}

Health Endpoint: {report['details'].get('health', {}).get('status_code', 'N/A')}
Auth Endpoint: {report['details'].get('auth', {}).get('status_code', 'N/A')}
Tools Available: {report['details'].get('tools', {}).get('count', 'N/A')}

Full Report:
{report}
"""
    
    # Configure your SMTP settings here
    # smtp_server = "your-smtp-server.com"
    # smtp_port = 587
    # email_user = "your-email@domain.com"
    # email_pass = "your-password"
    # to_email = "admin@domain.com"
    
    print("Email report generated:")
    print(body)

if __name__ == "__main__":
    report = generate_health_report()
    print(f"Server Status: {report['status']}")
    # send_email_report(report)
```

### 2. Uptime Monitor with Alerts

```bash
#!/bin/bash
# uptime-monitor.sh - Continuous uptime monitoring with Slack alerts

URL="https://whoop-mcp.fly.dev/health"
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
CHECK_INTERVAL=300  # 5 minutes
FAILURE_THRESHOLD=3

consecutive_failures=0

send_slack_alert() {
    local status="$1"
    local message="$2"
    
    if [ "$status" = "DOWN" ]; then
        color="danger"
        emoji="🚨"
    else
        color="good"
        emoji="✅"
    fi
    
    curl -X POST -H 'Content-type: application/json' \
        --data "{
            \"attachments\": [{
                \"color\": \"$color\",
                \"text\": \"$emoji WHOOP MCP Server Alert\",
                \"fields\": [{
                    \"title\": \"Status\",
                    \"value\": \"$status\",
                    \"short\": true
                }, {
                    \"title\": \"Message\",
                    \"value\": \"$message\",
                    \"short\": false
                }]
            }]
        }" \
        "$SLACK_WEBHOOK"
}

while true; do
    RESPONSE=$(curl -s -w "%{http_code}" "$URL" --max-time 30)
    HTTP_CODE="${RESPONSE: -3}"
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        if [ $consecutive_failures -ge $FAILURE_THRESHOLD ]; then
            send_slack_alert "UP" "Server is back online after $consecutive_failures failed checks"
        fi
        consecutive_failures=0
        echo "$(date): ✅ Server healthy"
    else
        consecutive_failures=$((consecutive_failures + 1))
        echo "$(date): ❌ Server check failed (attempt $consecutive_failures) - HTTP $HTTP_CODE"
        
        if [ $consecutive_failures -eq $FAILURE_THRESHOLD ]; then
            send_slack_alert "DOWN" "Server has failed $FAILURE_THRESHOLD consecutive health checks"
        fi
    fi
    
    sleep $CHECK_INTERVAL
done
```

## Error Handling

### 1. HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Continue processing |
| 401 | Unauthorized | Check API key |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Check server logs |
| 503 | Service Unavailable | Server may be restarting |

### 2. Retry Logic

```python
import requests
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    time.sleep(delay * (backoff ** (retries - 1)))
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2)
def make_api_request(url, headers):
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()
```

### 3. Error Response Parsing

```javascript
async function handleApiResponse(response) {
    if (response.ok) {
        return await response.json();
    }
    
    const errorData = await response.json().catch(() => ({}));
    
    switch (response.status) {
        case 401:
            throw new Error('Authentication failed. Check your API key.');
        case 429:
            throw new Error('Rate limit exceeded. Please wait before retrying.');
        case 500:
            throw new Error('Server error. Please try again later.');
        default:
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }
}
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Test basic connectivity
ping whoop-mcp.fly.dev

# Test HTTPS access
curl -I https://whoop-mcp.fly.dev/health
```

#### 2. SSL/TLS Issues
```bash
# Test with verbose SSL output
curl -vvv https://whoop-mcp.fly.dev/health
```

#### 3. API Key Issues
```bash
# Test with wrong key (should get 401)
curl -H "X-API-Key: wrong_key" https://whoop-mcp.fly.dev/tools

# Test with correct key (should get 200)
curl -H "X-API-Key: YOUR_API_KEY_HERE" \
     https://whoop-mcp.fly.dev/tools
```

#### 4. Rate Limiting
```bash
# Test rate limiting (make many requests quickly)
for i in {1..70}; do 
    curl -s https://whoop-mcp.fly.dev/health > /dev/null
    echo "Request $i completed"
done
```

### Debug Tools

#### 1. Comprehensive Health Check
```bash
#!/bin/bash
# comprehensive-check.sh

API_KEY="YOUR_API_KEY_HERE"

echo "=== WHOOP MCP Server Health Check ==="
echo "Timestamp: $(date)"
echo

echo "1. Testing public health endpoint..."
curl -s https://whoop-mcp.fly.dev/health | jq .
echo

echo "2. Testing server info endpoint..."
curl -s https://whoop-mcp.fly.dev/ | jq .
echo

echo "3. Testing protected tools endpoint..."
curl -s -H "X-API-Key: $API_KEY" https://whoop-mcp.fly.dev/tools | jq .
echo

echo "4. Testing auth status endpoint..."
curl -s -H "X-API-Key: $API_KEY" https://whoop-mcp.fly.dev/auth | jq .
echo

echo "5. Testing invalid API key (should return 401)..."
curl -s -H "X-API-Key: invalid_key" https://whoop-mcp.fly.dev/tools
echo
echo

echo "=== Health Check Complete ==="
```

#### 2. Response Time Monitor
```python
import requests
import time
import statistics

def measure_response_times(url, num_requests=10):
    times = []
    
    for i in range(num_requests):
        start = time.time()
        try:
            response = requests.get(url, timeout=30)
            end = time.time()
            times.append(end - start)
            print(f"Request {i+1}: {(end - start)*1000:.2f}ms - Status: {response.status_code}")
        except Exception as e:
            print(f"Request {i+1}: FAILED - {e}")
        
        time.sleep(1)  # Rate limiting friendly
    
    if times:
        print(f"\nResponse Time Statistics:")
        print(f"Average: {statistics.mean(times)*1000:.2f}ms")
        print(f"Median: {statistics.median(times)*1000:.2f}ms")
        print(f"Min: {min(times)*1000:.2f}ms")
        print(f"Max: {max(times)*1000:.2f}ms")

# Test response times
measure_response_times("https://whoop-mcp.fly.dev/health")
```

## Security Best Practices

### 1. API Key Security
- ✅ **Store in environment variables** - Never hardcode in scripts
- ✅ **Use secure transport** - Always HTTPS, never HTTP
- ✅ **Monitor usage** - Check server logs for unauthorized attempts
- ✅ **Rotate regularly** - Update API key periodically

### 2. Request Security
```python
# Good: Use environment variables
api_key = os.getenv('WHOOP_API_KEY')

# Good: Validate responses
if response.status_code == 200:
    data = response.json()
else:
    # Handle error appropriately

# Good: Use timeouts
response = requests.get(url, timeout=30)
```

### 3. Error Handling Security
```python
# Good: Don't log sensitive data
try:
    response = requests.get(url, headers={'X-API-Key': api_key})
except Exception as e:
    # Don't log the full exception (may contain API key)
    logger.error(f"Request failed: {type(e).__name__}")
```

## Next Steps

Once you have HTTP API integration working:
1. **Try the [WebSocket Guide](websocket-guide.md)** for real-time communication
2. **Explore the [SSE Guide](sse-guide.md)** for streaming data
3. **Check the [STDIO Guide](stdio-guide.md)** for local development

Your HTTP API provides powerful programmatic access to your WHOOP MCP server! 🌐🔧
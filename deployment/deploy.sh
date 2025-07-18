#!/bin/bash

# WHOOP MCP Deployment Script for fly.io
set -e

echo "🚀 Deploying WHOOP MCP to fly.io..."

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl CLI is not installed. Please install it first:"
    echo "curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if logged in to fly.io
if ! flyctl auth whoami &> /dev/null; then
    echo "❌ Not logged in to fly.io. Please run: flyctl auth login"
    exit 1
fi

# Check if app exists
if ! flyctl apps list | grep -q "whoop-mcp"; then
    echo "📱 Creating new fly.io app..."
    flyctl apps create whoop-mcp
else
    echo "📱 App 'whoop-mcp' already exists"
fi

# Set required environment variables (if not already set)
echo "🔧 Setting up environment variables..."

# Check if secrets are already set
if ! flyctl secrets list | grep -q "WHOOP_CLIENT_ID"; then
    echo "⚠️  WHOOP_CLIENT_ID not found in secrets."
    echo "Please set your WHOOP API credentials and security key:"
    echo ""
    echo "🔐 Generate a secure API key first:"
    API_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated API Key: $API_KEY"
    echo ""
    echo "📋 Run these commands to set your secrets:"
    echo "flyctl secrets set WHOOP_CLIENT_ID=your_client_id"
    echo "flyctl secrets set WHOOP_CLIENT_SECRET=your_client_secret"  
    echo "flyctl secrets set API_SECRET_KEY=$API_KEY"
    echo "flyctl secrets set WHOOP_REDIRECT_URI=https://your-app.fly.dev/whoop/callback"
    echo "flyctl secrets set ENVIRONMENT=production"
    echo ""
    read -p "Press Enter to continue with deployment (you can set secrets later)..."
fi

# Check if API_SECRET_KEY is set
if ! flyctl secrets list | grep -q "API_SECRET_KEY"; then
    echo "🚨 CRITICAL: API_SECRET_KEY not set! Your deployment will be insecure without it."
    echo "Generate and set one immediately after deployment:"
    API_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "flyctl secrets set API_SECRET_KEY=$API_KEY"
fi

# Deploy the application
echo "🚢 Deploying application..."
flyctl deploy

# Get the deployment info
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your WHOOP MCP server is available at:"
flyctl status --format json | jq -r '.Hostname' | sed 's/^/https:\/\//'
echo ""
echo "📋 Available endpoints:"
echo "  Health Check: https://$(flyctl status --format json | jq -r '.Hostname')/health"
echo "  API Info: https://$(flyctl status --format json | jq -r '.Hostname')/"
echo "  Tools List: https://$(flyctl status --format json | jq -r '.Hostname')/tools"
echo "  MCP WebSocket: wss://$(flyctl status --format json | jq -r '.Hostname')/mcp"
echo ""
echo "🔐 IMPORTANT: Set your credentials and API key if you haven't already:"
echo "  flyctl secrets set WHOOP_CLIENT_ID=your_client_id"
echo "  flyctl secrets set WHOOP_CLIENT_SECRET=your_client_secret"
echo "  flyctl secrets set API_SECRET_KEY=your_generated_api_key"
echo ""
echo "🛡️  Security Features Enabled:"
echo "  ✅ API key authentication for sensitive endpoints"
echo "  ✅ Rate limiting (60 requests/minute per IP)"
echo "  ✅ Request logging and monitoring"
echo "  ✅ Security headers (HSTS, CSP, etc.)"
echo "  ✅ Input validation and sanitization"
echo ""
echo "📖 Usage:"
echo "  Include 'X-API-Key: your_api_key' header when accessing:"
echo "  - /tools (get available tools)"
echo "  - /auth (check WHOOP auth status)"  
echo "  - /mcp (WebSocket MCP communication)"
echo ""
echo "🎉 Secure WHOOP MCP deployment complete!"
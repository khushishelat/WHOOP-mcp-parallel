#!/bin/bash

# WHOOP MCP Server - Parallel API Setup Script
# This script helps you get your API key and complete WHOOP OAuth

echo "🚀 WHOOP MCP Server - Parallel API Setup"
echo "========================================="

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if we're logged in to fly.io
if ! flyctl auth whoami &> /dev/null; then
    echo "❌ Not logged in to fly.io. Please run:"
    echo "   flyctl auth login"
    exit 1
fi

echo "✅ flyctl is installed and authenticated"

# Get the API key
echo ""
echo "🔑 Getting your MCP Server API Key..."

# Try to find existing API key in logs
API_KEY=$(flyctl logs --app whoop-mcp 2>/dev/null | grep "Temporary API Key:" | tail -1 | sed 's/.*Temporary API Key: //')

if [ -z "$API_KEY" ]; then
    echo "🔄 No API key found in logs. Generating a new one..."
    NEW_API_KEY=$(openssl rand -hex 32)
    flyctl secrets set API_SECRET_KEY="$NEW_API_KEY" --app whoop-mcp
    API_KEY="$NEW_API_KEY"
    echo "✅ New API key generated and set"
else
    echo "✅ Found existing API key in logs"
fi

echo ""
echo "🔑 Your MCP Server API Key:"
echo "   $API_KEY"
echo ""
echo "⚠️  Keep this key secure! You'll need it for Parallel API calls."

# Check WHOOP credentials
echo ""
echo "🔐 Checking WHOOP OAuth credentials..."

WHOOP_CLIENT_ID=$(flyctl secrets list --app whoop-mcp 2>/dev/null | grep WHOOP_CLIENT_ID | wc -l)
WHOOP_CLIENT_SECRET=$(flyctl secrets list --app whoop-mcp 2>/dev/null | grep WHOOP_CLIENT_SECRET | wc -l)

if [ "$WHOOP_CLIENT_ID" -eq 0 ] || [ "$WHOOP_CLIENT_SECRET" -eq 0 ]; then
    echo "❌ WHOOP credentials not set. Please set them:"
    echo "   flyctl secrets set WHOOP_CLIENT_ID=your_client_id --app whoop-mcp"
    echo "   flyctl secrets set WHOOP_CLIENT_SECRET=your_client_secret --app whoop-mcp"
    echo ""
    echo "📖 Get WHOOP credentials at: https://developer.whoop.com/"
    exit 1
else
    echo "✅ WHOOP credentials are set"
fi

# Test server health
echo ""
echo "🏥 Testing server health..."
if curl -s -f https://whoop-mcp.fly.dev/health > /dev/null; then
    echo "✅ Server is healthy and responding"
else
    echo "❌ Server health check failed. Your app might not be deployed."
    echo "   Try deploying with: flyctl deploy --app whoop-mcp"
    exit 1
fi

# Test API key authentication
echo ""
echo "🔐 Testing API key authentication..."
AUTH_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" https://whoop-mcp.fly.dev/auth)

if echo "$AUTH_RESPONSE" | grep -q '"authenticated":true'; then
    echo "✅ API key authentication working"
    echo "✅ WHOOP OAuth already completed!"
    echo ""
    echo "🎉 Your server is ready for Parallel API!"
elif echo "$AUTH_RESPONSE" | grep -q '"authenticated":false'; then
    echo "✅ API key authentication working"
    echo "⚠️  WHOOP OAuth not completed yet"
    echo ""
    echo "🔐 Complete WHOOP OAuth:"
    echo "   1. Visit: https://whoop-mcp.fly.dev/whoop/auth"
    echo "   2. Follow the authorization flow"
    echo "   3. Re-run this script to verify"
    echo ""
    echo "📖 Opening OAuth URL in your browser..."
    sleep 2
    if command -v open &> /dev/null; then
        open "https://whoop-mcp.fly.dev/whoop/auth"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "https://whoop-mcp.fly.dev/whoop/auth"
    else
        echo "   Please manually visit: https://whoop-mcp.fly.dev/whoop/auth"
    fi
else
    echo "❌ API key authentication failed"
    echo "   Response: $AUTH_RESPONSE"
    exit 1
fi

echo ""
echo "📋 Summary for Parallel API Usage:"
echo "=================================="
echo "🌐 MCP Server URL: https://whoop-mcp.fly.dev/mcp"
echo "🔑 X-API-Key: $API_KEY"
echo ""
echo "📖 Complete guide: docs/parallel-api-guide.md"
echo ""
echo "🧪 Test with curl:"
echo "curl -X POST https://whoop-mcp.fly.dev/mcp \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-API-Key: $API_KEY' \\"
echo "  -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}'"

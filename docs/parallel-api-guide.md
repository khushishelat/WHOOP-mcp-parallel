# 🔄 Parallel Task API Integration Guide

This guide shows how to use your WHOOP MCP Server with the [Parallel Task API](https://docs.parallel.ai/features/mcp-tool-call) for AI-powered WHOOP data analysis.

## 🚀 Quick Start

Your WHOOP MCP server is now compatible with Parallel's Task API via HTTP transport. Here's how to use it:

### 1. **Get Your Server Details**

**Your deployed server:** `https://whoop-mcp.fly.dev`
**HTTP MCP endpoint:** `https://whoop-mcp.fly.dev/mcp` (POST)
**API Key:** Set in your environment as `API_SECRET_KEY`

### 2. **Basic Parallel API Request**

```curl
curl -X POST "https://api.parallel.ai/v1/tasks/runs" \
  -H "x-api-key: YOUR_PARALLEL_API_KEY" \
  -H "Content-Type: application/json" \
  -H "parallel-beta: mcp-server-2025-07-17" \
  --data '{
  "input": "What was my sleep quality last night and how can I improve it?",
  "processor": "lite",
  "mcp_servers": [
    {
        "type": "url",
        "url": "https://whoop-mcp.fly.dev/mcp",
        "name": "whoop_mcp_server",
        "headers": {"X-API-Key": "YOUR_WHOOP_MCP_API_KEY"}
    }
  ]
}'
```

### 3. **Advanced Analysis Example**

```curl
curl -X POST "https://api.parallel.ai/v1/tasks/runs" \
  -H "x-api-key: YOUR_PARALLEL_API_KEY" \
  -H "Content-Type: application/json" \
  -H "parallel-beta: mcp-server-2025-07-17" \
  --data '{
  "input": "Analyze my recent workout performance and recovery patterns. Provide specific recommendations for my training plan.",
  "processor": "core",
  "mcp_servers": [
    {
        "type": "url",
        "url": "https://whoop-mcp.fly.dev/mcp",
        "name": "whoop_fitness_data",
        "headers": {"X-API-Key": "YOUR_WHOOP_MCP_API_KEY"},
        "allowed_tools": [
          "get_workout_analysis",
          "get_recovery_load_analysis", 
          "get_training_readiness",
          "get_daily_summary"
        ]
    }
  ]
}'
```

## 🔧 Configuration

### ⚠️ CRITICAL: Two-Layer Authentication

Your WHOOP MCP server uses **two separate authentication systems**:

1. **MCP Server API Key** (`X-API-Key`) - Protects YOUR server endpoints
2. **WHOOP OAuth** - Allows your server to access WHOOP's API

### 🔑 Getting Your MCP Server API Key

Your server's API key was auto-generated during deployment. To find it:

```bash
# If you deployed with the script, check logs:
flyctl logs | grep "Temporary API Key"

# Or generate a new one:
flyctl secrets set API_SECRET_KEY=$(openssl rand -hex 32)
```

### 🔐 Complete WHOOP OAuth Setup

**Before using with Parallel API**, you must complete WHOOP OAuth:

1. **Visit your server's auth endpoint:**
   ```
   https://whoop-mcp.fly.dev/whoop/auth
   ```

2. **Follow the OAuth flow** to authorize WHOOP access

3. **Verify authentication:**
   ```bash
   curl -H "X-API-Key: YOUR_MCP_API_KEY" https://whoop-mcp.fly.dev/auth
   ```

### Environment Variables

Make sure these are set in your server deployment:

```bash
# Required: Your WHOOP API credentials
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret

# Required: API key for MCP server authentication (auto-generated)
API_SECRET_KEY=your_secure_api_key

# Optional: Custom redirect URI
WHOOP_REDIRECT_URI=https://whoop-mcp.fly.dev/whoop/callback
```

### Available Tools

| Tool | Description | Best For |
|------|-------------|----------|
| `get_sleep_data` | Sleep metrics with quality scores | Sleep analysis, optimization |
| `get_recovery_data` | Recovery scores with load breakdown | Recovery planning |
| `get_workout_data` | Workout data with elevation tracking | Performance analysis |
| `get_workout_analysis` | Detailed performance analysis | Training insights |
| `get_sleep_quality_analysis` | Sleep optimization recommendations | Sleep improvement |
| `get_recovery_load_analysis` | System-specific recovery strategies | Recovery planning |
| `get_training_readiness` | Multi-factor readiness assessment | Training decisions |
| `get_daily_summary` | Comprehensive daily health overview | General health tracking |

## 📊 Use Cases

### 1. **Sleep Optimization**
```json
{
  "input": "Analyze my sleep patterns over the last week and provide actionable recommendations to improve my sleep quality.",
  "processor": "core",
  "mcp_servers": [{
    "type": "url",
    "url": "https://whoop-mcp.fly.dev/mcp",
    "name": "whoop_sleep",
    "headers": {"X-API-Key": "YOUR_API_KEY"},
    "allowed_tools": ["get_sleep_data", "get_sleep_quality_analysis"]
  }]
}
```

### 2. **Training Planning**
```json
{
  "input": "Based on my current recovery state and recent workouts, should I do a high-intensity training session today?",
  "processor": "core", 
  "mcp_servers": [{
    "type": "url",
    "url": "https://whoop-mcp.fly.dev/mcp", 
    "name": "whoop_training",
    "headers": {"X-API-Key": "YOUR_API_KEY"},
    "allowed_tools": ["get_training_readiness", "get_recovery_data", "get_workout_data"]
  }]
}
```

### 3. **Health Insights**
```json
{
  "input": "Give me a comprehensive health assessment for this week, including trends and recommendations.",
  "processor": "lite",
  "mcp_servers": [{
    "type": "url", 
    "url": "https://whoop-mcp.fly.dev/mcp",
    "name": "whoop_health",
    "headers": {"X-API-Key": "YOUR_API_KEY"},
    "allowed_tools": ["get_daily_summary", "get_recovery_load_analysis", "get_sleep_quality_analysis"]
  }]
}
```

## 🔒 Security

### API Key Management
- **WHOOP MCP API Key**: Set as `X-API-Key` header - this is YOUR server's API key
- **Parallel API Key**: Set as `x-api-key` header - this is Parallel's API key for your account

### Authentication Checklist ✅

Before using with Parallel API, ensure:

1. **✅ WHOOP OAuth Completed**: Visit `/whoop/auth` and authorize
2. **✅ MCP API Key**: Get from deployment logs or generate new one
3. **✅ WHOOP Credentials**: `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` set
4. **✅ Test Authentication**: Verify with `/auth` endpoint

### Rate Limits
- **Parallel**: Check their documentation for current limits
- **WHOOP MCP**: 60 requests/minute per IP address
- **WHOOP API**: Respects WHOOP's API rate limits

### Best Practices
1. **Complete OAuth first** - Always do WHOOP auth before Parallel API calls
2. **Rotate API keys** regularly
3. **Use allowed_tools** to limit which tools can be called
4. **Monitor usage** through logs
5. **Use appropriate processors** (lite/core/etc.) based on complexity

## 🧪 Testing

### 1. **Test Server Health**
```bash
curl https://whoop-mcp.fly.dev/health
```

### 2. **Test MCP Endpoint**
```bash
curl -X POST https://whoop-mcp.fly.dev/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### 3. **Test Tool Call**
```bash
curl -X POST https://whoop-mcp.fly.dev/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "jsonrpc": "2.0", 
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_profile_data",
      "arguments": {}
    }
  }'
```

## 🎯 Example Processors

### **Lite Processor** (Single tool call)
- Best for: Simple queries, single data points
- Example: "What was my sleep score last night?"

### **Core Processor** (Multiple tool calls) 
- Best for: Analysis requiring multiple data sources
- Example: "Analyze my training load and recovery for optimal performance"

### **Advanced Processors**
- Best for: Complex multi-step analysis and planning
- Example: "Create a 2-week training plan based on my historical data and current recovery state"

## 🔍 Troubleshooting

### Common Issues

**401 Unauthorized from MCP Server**
```bash
# Find your API key from deployment logs:
flyctl logs | grep "API Key"

# Or set a new one:
flyctl secrets set API_SECRET_KEY=$(openssl rand -hex 32)
```

**WHOOP Authentication Failed**
```bash
# 1. Complete OAuth first:
open https://whoop-mcp.fly.dev/whoop/auth

# 2. Verify WHOOP credentials are set:
flyctl secrets list | grep WHOOP

# 3. Check auth status:
curl -H "X-API-Key: YOUR_KEY" https://whoop-mcp.fly.dev/auth
```

**Tool Execution Failed**
- WHOOP OAuth must be completed first
- Check authentication with `/auth` endpoint
- Verify WHOOP account has data for the requested period

**Rate Limited** 
- Reduce request frequency
- Use `allowed_tools` to limit scope
- Consider caching results

**Tool not found**
- Check available tools at `/tools` endpoint
- Verify tool name spelling in `allowed_tools`

### Debug Commands

```bash
# Check server status
curl https://whoop-mcp.fly.dev/

# List available tools  
curl -H "X-API-Key: YOUR_KEY" https://whoop-mcp.fly.dev/tools

# Check WHOOP authentication
curl -H "X-API-Key: YOUR_KEY" https://whoop-mcp.fly.dev/auth
```

## 🚀 Deployment

Your server is already deployed at `https://whoop-mcp.fly.dev`. To update:

```bash
# Update code and redeploy
git push origin main
./deployment/deploy.sh
```

## 📞 Support

- **Documentation**: Check other guides in `/docs/`
- **Server logs**: `flyctl logs` for deployment issues
- **WHOOP API**: [WHOOP API Documentation](https://developer.whoop.com/)
- **Parallel API**: [Parallel Documentation](https://docs.parallel.ai/)

---

**Made with ❤️ for AI-powered fitness insights** 🏃‍♂️🤖

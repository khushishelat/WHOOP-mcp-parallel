# WHOOP MCP Deployment Guide

This guide explains how to deploy the WHOOP MCP server to fly.io for cloud access.

## Prerequisites

1. **fly.io Account**: Sign up at [fly.io](https://fly.io)
2. **flyctl CLI**: Install the fly.io CLI
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
3. **WHOOP Developer Account**: Get API credentials from [developer.whoop.com](https://developer.whoop.com/)

## Quick Deployment

1. **Clone and Setup**
   ```bash
   git clone <your-repo>
   cd WHOOP-mcp
   ```

2. **Login to fly.io**
   ```bash
   flyctl auth login
   ```

3. **Deploy**
   ```bash
   ./deploy.sh
   ```

4. **Set Environment Variables**
   ```bash
   flyctl secrets set WHOOP_CLIENT_ID=your_client_id WHOOP_CLIENT_SECRET=your_client_secret
   ```

## Manual Deployment Steps

### 1. Create fly.io App
```bash
flyctl apps create whoop-mcp
```

### 2. Configure Environment Variables
```bash
# REQUIRED: Generate a secure API key first
API_KEY=$(openssl rand -hex 32)
echo "Your API Key: $API_KEY"

# Required: WHOOP API credentials
flyctl secrets set WHOOP_CLIENT_ID=your_whoop_client_id
flyctl secrets set WHOOP_CLIENT_SECRET=your_whoop_client_secret

# CRITICAL: API key for endpoint security
flyctl secrets set API_SECRET_KEY=$API_KEY

# Optional: Custom redirect URI for production OAuth
flyctl secrets set WHOOP_REDIRECT_URI=https://whoop-mcp.fly.dev/whoop/callback

# Production environment flag
flyctl secrets set ENVIRONMENT=production
```

**🚨 IMPORTANT**: Save your API key securely! You'll need it to access protected endpoints.

### 3. Deploy Application
```bash
flyctl deploy
```

### 4. Monitor Deployment
```bash
flyctl status
flyctl logs
```

## API Endpoints

Once deployed, your WHOOP MCP server will be available at:

### Public Endpoints (No Authentication Required)
- **Health Check**: `https://your-app.fly.dev/health`
- **API Info**: `https://your-app.fly.dev/`

### Protected Endpoints (Require X-API-Key Header)
- **Available Tools**: `https://your-app.fly.dev/tools`
- **Auth Status**: `https://your-app.fly.dev/auth`
- **MCP WebSocket**: `wss://your-app.fly.dev/mcp`

### Usage Examples
```bash
# Public endpoint (no auth needed)
curl https://your-app.fly.dev/health

# Protected endpoint (requires API key)
curl -H "X-API-Key: your_api_key" https://your-app.fly.dev/tools

# WebSocket with authentication
wscat -c "wss://your-app.fly.dev/mcp" -H "X-API-Key: your_api_key"
```

## Features Available

### Enhanced WHOOP API v2 Features
- ✅ Elevation tracking (altitude gain/change)
- ✅ Advanced sleep quality analysis
- ✅ Recovery load breakdown (cardiovascular, musculoskeletal, metabolic)
- ✅ Training readiness assessment
- ✅ Body composition tracking
- ✅ Data quality indicators
- ✅ US units & EST timezone formatting

### Analysis Tools
- `get_workout_analysis()` - Detailed workout analysis with zone distribution
- `get_sleep_quality_analysis()` - Sleep optimization recommendations
- `get_recovery_load_analysis()` - System-specific recovery strategies
- `get_training_readiness()` - Comprehensive readiness scoring

## Using with MCP Clients

### Claude Desktop
Add to your MCP configuration:
```json
{
  "mcpServers": {
    "whoop": {
      "command": "node",
      "args": ["path/to/websocket-client.js"],
      "env": {
        "WHOOP_MCP_URL": "wss://your-app.fly.dev/mcp"
      }
    }
  }
}
```

### Direct WebSocket Connection
```javascript
const ws = new WebSocket('wss://your-app.fly.dev/mcp');
```

## Troubleshooting

### Check Application Status
```bash
flyctl status
flyctl logs
```

### Debug Issues
```bash
flyctl ssh console
```

### Update Application
```bash
flyctl deploy
```

### Scale Resources (if needed)
```bash
flyctl scale memory 512
flyctl scale count 2
```

## Security Features

### 🔐 Multi-Layer Security Architecture
- **API Key Authentication**: Required for all sensitive endpoints (`/mcp`, `/tools`, `/auth`)
- **Rate Limiting**: 60 requests per minute per IP address
- **Request Logging**: All requests logged with IP and timestamp for monitoring
- **Security Headers**: HSTS, CSP, X-Frame-Options, and more
- **Input Validation**: Message size limits and format validation
- **Error Sanitization**: No sensitive information leaked in error messages

### 🛡️ Security Best Practices
- Environment variables securely stored using fly.io secrets
- HTTPS/WSS encryption for all communications
- OAuth2 flow for WHOOP authentication
- No sensitive data stored in the application code
- Automatic API key generation if not provided

### 🚨 Critical Security Requirements
1. **Set a strong API key**: Use `openssl rand -hex 32` to generate
2. **Keep your API key private**: Only share with trusted MCP clients
3. **Monitor access logs**: Check `flyctl logs` for unauthorized attempts
4. **Rotate keys regularly**: Update API_SECRET_KEY periodically

### 🔍 Security Monitoring
```bash
# Monitor access attempts
flyctl logs | grep "🔐\|🚫"

# Check current security settings
curl https://your-app.fly.dev/

# Verify authentication is working
curl -H "X-API-Key: wrong_key" https://your-app.fly.dev/tools
# Should return 401 Unauthorized
```

## Cost Optimization

The application is configured for cost-effective operation:
- **Auto-stop**: Machines stop when idle
- **Auto-start**: Machines start on demand
- **Minimal resources**: 256MB RAM, shared CPU
- **No minimum instances**: Scales to zero when unused

## Support

For deployment issues:
- Check [fly.io documentation](https://fly.io/docs/)
- Review application logs: `flyctl logs`
- Monitor health endpoint: `https://your-app.fly.dev/health`
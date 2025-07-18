# 🌐 WebSocket Connection Guide

This guide shows you how to connect to the WHOOP MCP server via WebSocket for real-time communication.

## 🔧 Prerequisites

- **API Key**: Get your API key from the server administrator
- **WebSocket Client**: Any WebSocket client (browser, Node.js, Python, etc.)
- **WHOOP Authentication**: Complete OAuth flow at `https://whoop-mcp.fly.dev/whoop/auth`

## 🚀 Quick Start

### 1. **Get Your API Key**
```bash
# Contact administrator for your API key
API_KEY="your_api_key_here"
```

### 2. **Authenticate with WHOOP**
Visit the authentication URL to start the OAuth flow:
```
https://whoop-mcp.fly.dev/whoop/auth
```

This will redirect you to WHOOP's authorization page. After approval, you'll be redirected to:
```
https://whoop-mcp.fly.dev/whoop/callback
```

### 3. **Connect via WebSocket**
```javascript
const WebSocket = require('ws');

const ws = new WebSocket('wss://whoop-mcp.fly.dev/mcp', {
  headers: {
    'X-API-Key': 'YOUR_API_KEY_HERE'
  }
});

ws.on('open', () => {
  console.log('Connected to WHOOP MCP server');
  
  // Initialize MCP connection
  ws.send(JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {
        tools: {},
        prompts: {},
        resources: {}
      },
      clientInfo: {
        name: "websocket-client",
        version: "1.0.0"
      }
    }
  }));
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  console.log('Received:', message);
});
```

## 📋 Available Commands

### Initialize Connection
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "prompts": {},
      "resources": {}
    }
  }
}
```

### List Available Tools
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

### Call a Tool
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_sleep_data",
    "arguments": {
      "date": "2024-01-15"
    }
  }
}
```

## 🔒 Security

- **API Key Required**: All WebSocket connections must include a valid `X-API-Key` header
- **Rate Limiting**: 60 requests per minute per IP address
- **HTTPS Only**: All connections use WSS (secure WebSocket)
- **Input Validation**: All messages are validated and sanitized

## 🚨 Important Notes

⚠️ **Replace `YOUR_API_KEY_HERE`** with your actual API key before connecting.

⚠️ **WHOOP Authentication**: You must complete the OAuth flow at `https://whoop-mcp.fly.dev/whoop/auth` before using WHOOP tools.

## 📊 Example Usage

### Complete JavaScript Example
```javascript
const WebSocket = require('ws');

class WHOOPMCPClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.ws = null;
    this.messageId = 1;
  }

  connect() {
    this.ws = new WebSocket('wss://whoop-mcp.fly.dev/mcp', {
      headers: {
        'X-API-Key': this.apiKey
      }
    });

    this.ws.on('open', () => {
      console.log('✅ Connected to WHOOP MCP server');
      this.initialize();
    });

    this.ws.on('message', (data) => {
      const message = JSON.parse(data);
      console.log('📨 Received:', message);
    });

    this.ws.on('error', (error) => {
      console.error('❌ WebSocket error:', error);
    });
  }

  initialize() {
    this.sendMessage('initialize', {
      protocolVersion: "2024-11-05",
      capabilities: {
        tools: {},
        prompts: {},
        resources: {}
      }
    });
  }

  listTools() {
    this.sendMessage('tools/list');
  }

  getSleepData(date = null) {
    const args = date ? { date } : {};
    this.sendMessage('tools/call', {
      name: 'get_sleep_data',
      arguments: args
    });
  }

  sendMessage(method, params = {}) {
    const message = {
      jsonrpc: "2.0",
      id: this.messageId++,
      method,
      params
    };
    
    this.ws.send(JSON.stringify(message));
  }
}

// Usage
const client = new WHOOPMCPClient('YOUR_API_KEY_HERE');
client.connect();
```

## 🆘 Troubleshooting

### Connection Issues
- **401 Unauthorized**: Check your API key is correct
- **429 Too Many Requests**: You've exceeded rate limits
- **Connection Refused**: Server may be down, check status at `/health`

### Authentication Issues
- **OAuth Error**: Visit `https://whoop-mcp.fly.dev/whoop/auth` to re-authenticate
- **Token Expired**: Re-authenticate with WHOOP

### Message Errors
- **Invalid JSON**: Ensure your messages are valid JSON
- **Missing Method**: All messages must include a `method` field
- **Large Messages**: Messages over 10KB are rejected

## 📞 Support

For issues with WebSocket connections:
1. Check the server status: `https://whoop-mcp.fly.dev/health`
2. Verify your API key is valid
3. Ensure WHOOP authentication is complete
4. Review the error messages in your WebSocket client

---

**🌐 WebSocket URL**: `wss://whoop-mcp.fly.dev/mcp`  
**🔑 Authentication**: `X-API-Key` header required  
**🔒 Security**: HTTPS/WSS only with rate limiting
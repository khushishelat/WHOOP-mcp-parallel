# 🏃‍♂️ WHOOP MCP Server

A comprehensive **Model Context Protocol (MCP) server** for accessing WHOOP fitness and health data with enhanced API v2 features, real-time analytics, and secure cloud deployment.

## ✨ Features

### 🚀 **WHOOP API v2 Integration**
- **Enhanced sleep analysis** with sleep latency and efficiency scores
- **Elevation tracking** for workouts (altitude gain/change)
- **Recovery load breakdown** by cardiovascular, musculoskeletal, and metabolic systems
- **Training readiness assessment** combining multiple health metrics
- **Body composition tracking** with comprehensive measurements
- **Data quality indicators** showing percent recorded for each metric

### 🎯 **Advanced Analytics Tools**
- **Workout Analysis** - Detailed performance metrics with heart rate zones
- **Sleep Quality Analysis** - Comprehensive sleep optimization recommendations  
- **Recovery Load Analysis** - System-specific recovery strategies
- **Training Readiness** - Multi-factor readiness scoring

### 🌐 **Multiple Connection Methods**
- **STDIO** - Local development with Claude Desktop
- **WebSocket** - Real-time cloud communication
- **HTTP REST API** - Automation and integration
- **HTTP MCP** - Parallel Task API compatible transport
- **SSE** - Server-sent events for live monitoring

### 🔒 **Enterprise Security**
- **API key authentication** for all sensitive endpoints
- **Rate limiting** (60 requests/minute per IP)
- **Security headers** (HSTS, CSP, X-Frame-Options)
- **Input validation** and sanitization
- **Request logging** with IP tracking
- **Encrypted cloud deployment** on fly.io

### 🇺🇸 **Enhanced Data Formatting**
- **US units prioritization** (miles, Fahrenheit, etc.)
- **EST timezone conversion** for all timestamps
- **Pretty-printed outputs** with actionable insights
- **Custom prompts** for personalized responses

## 📁 Project Structure

```
WHOOP-mcp/
├── 📄 README.md              # This file
├── 🔧 requirements.txt       # Python dependencies
├── 🔧 pyproject.toml         # Project configuration
├── 🔧 uv.lock               # Locked dependencies
├── 🔒 .env.example          # Environment template
├── 🔒 .gitignore            # Git ignore rules
│
├── 🐍 whoop_mcp.py          # Main MCP server
├── 🌐 web_server.py         # Web/WebSocket server
│
├── 📚 docs/                 # Documentation
│   ├── 📖 stdio-guide.md    # Local STDIO setup
│   ├── 🌐 websocket-guide.md # WebSocket connections
│   ├── 🔧 http-guide.md     # REST API usage
│   ├── 📡 sse-guide.md      # Server-sent events
│   ├── 🚀 DEPLOYMENT.md     # Cloud deployment
│   └── 🔒 SECURITY.md       # Security guidelines
│
├── 🚀 deployment/           # Deployment files
│   ├── 🐳 Dockerfile        # Container configuration
│   ├── ✈️ fly.toml          # fly.io configuration
│   └── 📜 deploy.sh         # Deployment script
│
└── 🧪 tests/               # Test files
    ├── 🧪 test_deployment.py # Deployment tests
    ├── 🔒 test_security.py   # Security tests
    └── 🔄 test_parallel_integration.py # Parallel API tests
```

## 🚀 Quick Start

### 1. **Local Development (STDIO)**
```bash
# Clone and setup
git clone <your-repo>
cd WHOOP-mcp

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your WHOOP API credentials

# Run locally
python whoop_mcp.py
```

📖 **[Complete STDIO Guide](docs/stdio-guide.md)**

### 2. **Cloud Deployment (WebSocket/HTTP)**
```bash
# Deploy to fly.io
./deployment/deploy.sh

# Set your WHOOP credentials
flyctl secrets set WHOOP_CLIENT_ID=your_client_id
flyctl secrets set WHOOP_CLIENT_SECRET=your_client_secret
```

🚀 **[Complete Deployment Guide](docs/DEPLOYMENT.md)**

## 📚 Documentation

### Connection Methods
- **[📖 STDIO Guide](docs/stdio-guide.md)** - Local development with Claude Desktop
- **[🌐 WebSocket Guide](docs/websocket-guide.md)** - Real-time cloud connections
- **[🔧 HTTP Guide](docs/http-guide.md)** - REST API automation
- **[🔄 Parallel API Guide](docs/parallel-api-guide.md)** - AI-powered analysis with Parallel
- **[📡 SSE Guide](docs/sse-guide.md)** - Server-sent events streaming

### Deployment & Security
- **[🚀 Deployment Guide](docs/DEPLOYMENT.md)** - fly.io cloud deployment
- **[🔒 Security Guide](docs/SECURITY.md)** - Security best practices

## 🛠️ Available Tools

### Core Data Tools
| Tool | Description |
|------|-------------|
| `get_sleep_data` | Sleep data with quality metrics and EST timezone |
| `get_recovery_data` | Recovery scores with load breakdown |
| `get_workout_data` | Workout data with sport names and elevation |
| `get_cycle_data` | Daily cycle data (strain/load) |
| `get_profile_data` | User profile information |
| `get_body_measurement_data` | Body composition tracking |

### Advanced Analytics
| Tool | Description |
|------|-------------|
| `get_workout_analysis` | Detailed performance analysis with zones |
| `get_sleep_quality_analysis` | Sleep optimization recommendations |
| `get_recovery_load_analysis` | System-specific recovery strategies |
| `get_training_readiness` | Multi-factor readiness assessment |

### Discovery & Customization
| Tool | Description |
|------|-------------|
| `get_sports_mapping` | Sport ID to name mapping |
| `search_whoop_sports` | Search for specific sports |
| `set_custom_prompt` | Customize server responses |
| `get_custom_prompt` | View current custom prompt |
| `clear_custom_prompt` | Reset to default prompt |

## 🔧 Configuration

### Environment Variables
```bash
# WHOOP API (required)
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret

# Optional: Custom redirect URI
WHOOP_REDIRECT_URI=http://localhost:8000/whoop/callback

# Cloud deployment (auto-generated if not set)
API_SECRET_KEY=your_secure_api_key

# Web server configuration
PORT=8080
HOST=0.0.0.0
ENVIRONMENT=production
```

### Claude Desktop Integration
Add to your `~/.claude/mcp.json`:

**Local (STDIO):**
```json
{
  "mcpServers": {
    "whoop": {
      "command": "python",
      "args": ["/path/to/WHOOP-mcp/whoop_mcp.py"],
      "env": {
        "WHOOP_CLIENT_ID": "your_client_id",
        "WHOOP_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

**Cloud (WebSocket):**
```json
{
  "mcpServers": {
    "whoop-cloud": {
      "command": "node",
      "args": ["/path/to/websocket-client.js"],
      "env": {
        "WHOOP_MCP_URL": "wss://your-app.fly.dev/mcp",
        "WHOOP_API_KEY": "your_api_key"
      }
    }
  }
}
```

## 🧪 Testing

```bash
# Setup for Parallel API (gets API key & completes OAuth)
./setup_parallel_auth.sh

# Test Parallel API integration
python tests/test_parallel_integration.py

# Test security features
python tests/test_security.py

# Test deployment
python tests/test_deployment.py

# Test local server
python whoop_mcp.py --test
```

## 🔒 Security

This project implements enterprise-grade security:

- ✅ **No sensitive data in git** - All credentials use environment variables
- ✅ **API key authentication** - Required for all sensitive endpoints  
- ✅ **Rate limiting** - 60 requests/minute per IP
- ✅ **Security headers** - HSTS, CSP, X-Frame-Options
- ✅ **Input validation** - Message size limits and sanitization
- ✅ **Request logging** - All access monitored with IP tracking

**[🔒 Security Guide](docs/SECURITY.md)** | **[🛡️ Security Testing](tests/test_security.py)**

## 📊 Usage Examples

### Basic Health Check
```python
# Get recent sleep data
await get_sleep_data()

# Analyze workout performance  
await get_workout_analysis(workout_id="12345")

# Check training readiness
await get_training_readiness()
```

### Advanced Analytics
```python
# Comprehensive health assessment
recovery = await get_recovery_load_analysis()
sleep = await get_sleep_quality_analysis() 
readiness = await get_training_readiness()
```

### Custom Insights
```python
# Set custom prompt for personalized responses
await set_custom_prompt("Always provide actionable health insights and include relevant medical disclaimers.")
```

## 🚀 Live Deployment

Your WHOOP MCP server is deployed and accessible at:

**🌐 Base URL:** `https://whoop-mcp.fly.dev`

### Public Endpoints
- **Health Check:** `https://whoop-mcp.fly.dev/health`
- **Server Info:** `https://whoop-mcp.fly.dev/`

### Protected Endpoints (require API key)
- **Available Tools:** `https://whoop-mcp.fly.dev/tools`
- **Auth Status:** `https://whoop-mcp.fly.dev/auth`  
- **HTTP MCP:** `https://whoop-mcp.fly.dev/mcp` (POST - Parallel API compatible)
- **WebSocket MCP:** `wss://whoop-mcp.fly.dev/mcp`

## 🤝 Contributing

1. **Follow security guidelines** in [docs/SECURITY.md](docs/SECURITY.md)
2. **Never commit sensitive data** (API keys, credentials)
3. **Test your changes** with the provided test suites
4. **Update documentation** for new features

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

- **Documentation Issues:** Check the [docs/](docs/) folder
- **Security Concerns:** Review [docs/SECURITY.md](docs/SECURITY.md)
- **Deployment Problems:** See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Connection Issues:** Try different [connection guides](docs/)

---

**Made with ❤️ for the WHOOP community** | **Powered by Claude MCP** 🤖
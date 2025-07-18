# WHOOP MCP Server - STDIO Connection Guide

This guide covers how to run and use the WHOOP MCP server locally using the STDIO transport method, which is the traditional way to run MCP servers.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Claude Desktop Configuration](#claude-desktop-configuration)
- [Authentication Flow](#authentication-flow)
- [Available Tools](#available-tools)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

## Overview

STDIO (Standard Input/Output) is the default transport method for MCP servers. When running locally, the server communicates with Claude Desktop through stdin/stdout pipes, providing a secure and efficient connection method.

**Benefits of STDIO:**
- ✅ Secure local communication
- ✅ No network exposure
- ✅ Fast, low-latency connection
- ✅ Easy debugging and development
- ✅ No API key management needed

## Prerequisites

### 1. Python Environment
```bash
# Ensure Python 3.11+ is installed
python --version  # Should be 3.11 or higher

# Install dependencies
pip install -r requirements.txt
```

### 2. WHOOP API Credentials
Get your credentials from [developer.whoop.com](https://developer.whoop.com/):
- Client ID
- Client Secret

### 3. Environment Configuration
Create a `.env` file in the project directory:
```env
WHOOP_CLIENT_ID=your_whoop_client_id_here
WHOOP_CLIENT_SECRET=your_whoop_client_secret_here
WHOOP_REDIRECT_URI=http://localhost:8000/whoop/callback
```

## Local Setup

### 1. Clone and Install
```bash
git clone <your-repo>
cd WHOOP-mcp
pip install -r requirements.txt
```

### 2. Test Local Server
```bash
# Test the server runs without errors
python whoop_mcp.py
```

The server should start and show:
```
Starting WHOOP MCP server...
Server ready on stdio transport
```

### 3. Verify Dependencies
```bash
# Check all required packages are installed
python -c "
from mcp.server.fastmcp import FastMCP
import httpx, json, os, webbrowser, threading
print('✅ All dependencies installed successfully')
"
```

## Claude Desktop Configuration

### 1. Locate Configuration File

**macOS:**
```bash
~/.claude/mcp.json
```

**Windows:**
```bash
%APPDATA%\Claude\mcp.json
```

**Linux:**
```bash
~/.config/claude/mcp.json
```

### 2. Add WHOOP Server Configuration

Edit your `mcp.json` file to include the WHOOP server:

```json
{
  "mcpServers": {
    "whoop": {
      "command": "python",
      "args": ["/Users/dylanshade/Developer/WHOOP-mcp/whoop_mcp.py"],
      "env": {
        "WHOOP_CLIENT_ID": "your_whoop_client_id_here",
        "WHOOP_CLIENT_SECRET": "your_whoop_client_secret_here",
        "WHOOP_REDIRECT_URI": "http://localhost:8000/whoop/callback"
      }
    }
  }
}
```

**Important:** Replace the path with your actual project directory.

### 3. Alternative Configuration with UV

If you're using UV for dependency management:
```json
{
  "mcpServers": {
    "whoop": {
      "command": "uv",
      "args": ["--directory", "/Users/dylanshade/Developer/WHOOP-mcp", "run", "whoop_mcp.py"],
      "env": {
        "WHOOP_CLIENT_ID": "your_whoop_client_id_here",
        "WHOOP_CLIENT_SECRET": "your_whoop_client_secret_here"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

After updating the configuration:
1. **Quit Claude Desktop completely**
2. **Restart Claude Desktop**
3. **Verify connection** - You should see the WHOOP tools available

## Authentication Flow

### 1. Initial Authentication
The first time you use any WHOOP tool, you'll need to authenticate:

1. **Trigger authentication** by asking Claude to use any WHOOP tool:
   ```
   "Can you get my latest sleep data from WHOOP?"
   ```

2. **Browser opens automatically** to WHOOP's authorization page

3. **Login to WHOOP** and approve the authorization request

4. **Automatic callback handling** - The server will capture the authorization code

5. **Token storage** - Your access token is saved locally in `whoop_token.json`

### 2. Token Management
```bash
# Check if you're authenticated
ls -la whoop_token.json

# View token details (don't share this file!)
cat whoop_token.json
```

### 3. Re-authentication
If your token expires, simply use a WHOOP tool again and re-authenticate when prompted.

## Available Tools

Your local WHOOP MCP server provides 15 powerful tools:

### Core Data Tools
- **`get_sleep_data`** - Get sleep data with quality analysis
- **`get_recovery_data`** - Get recovery scores and metrics
- **`get_workout_data`** - Get workout data with sport details
- **`get_cycle_data`** - Get daily cycle data (strain/load)
- **`get_profile_data`** - Get user profile information
- **`get_body_measurement_data`** - Get body composition data

### Advanced Analysis Tools
- **`get_workout_analysis`** - Detailed workout analysis with elevation
- **`get_sleep_quality_analysis`** - Comprehensive sleep quality assessment
- **`get_recovery_load_analysis`** - Recovery load breakdown by system
- **`get_training_readiness`** - Training readiness scoring

### Discovery Tools
- **`get_sports_mapping`** - Get mapping of sport IDs to names
- **`search_whoop_sports`** - Search for specific sports

### Customization Tools
- **`set_custom_prompt`** - Set custom system prompt
- **`get_custom_prompt`** - Get current custom prompt
- **`clear_custom_prompt`** - Clear custom prompt

## Usage Examples

### 1. Basic Sleep Analysis
```
"Can you get my sleep data from last night and analyze the quality?"
```

Claude will:
1. Call `get_sleep_data` to fetch recent sleep
2. Use `get_sleep_quality_analysis` for detailed insights
3. Provide recommendations based on the data

### 2. Workout Performance Review
```
"Show me my latest workout and provide detailed analysis including elevation and heart rate zones."
```

Claude will:
1. Call `get_workout_data` to fetch recent workouts
2. Use `get_workout_analysis` for detailed breakdown
3. Analyze performance metrics and provide insights

### 3. Training Readiness Assessment
```
"Based on my recovery, sleep, and recent strain, am I ready for a hard workout today?"
```

Claude will:
1. Call `get_training_readiness` for comprehensive assessment
2. Analyze multiple factors (recovery, sleep, strain)
3. Provide specific training recommendations

### 4. Custom Analysis Setup
```
"Set a custom prompt to always include metric conversions to imperial units and focus on actionable insights."
```

Claude will:
1. Use `set_custom_prompt` to customize the server behavior
2. All future responses will follow the custom prompt guidelines

## Troubleshooting

### Common Issues

#### 1. Server Not Starting
```bash
# Check Python version
python --version

# Check dependencies
pip install -r requirements.txt

# Run with debug output
python whoop_mcp.py --debug
```

#### 2. Claude Desktop Can't Connect
```bash
# Verify configuration file syntax
cat ~/.claude/mcp.json | python -m json.tool

# Check file permissions
ls -la ~/.claude/mcp.json

# Verify Python path is correct
which python
```

#### 3. Authentication Issues
```bash
# Remove old token file
rm whoop_token.json

# Check environment variables
echo $WHOOP_CLIENT_ID
echo $WHOOP_CLIENT_SECRET

# Verify redirect URI matches WHOOP app settings
```

#### 4. Tools Not Available
1. **Restart Claude Desktop** completely
2. **Check server logs** for any error messages
3. **Verify all dependencies** are installed
4. **Check environment variables** are set correctly

### Debug Mode

Run the server with debug logging:
```bash
export PYTHON_LOG_LEVEL=DEBUG
python whoop_mcp.py
```

### Log Files

Check these locations for logs:
- **Server logs**: Console output when running `python whoop_mcp.py`
- **Claude Desktop logs**: Check Claude Desktop's developer console
- **Token file**: `whoop_token.json` for authentication status

### Getting Help

1. **Check the server is running**: `ps aux | grep whoop_mcp.py`
2. **Verify network connectivity**: Test WHOOP API directly
3. **Validate configuration**: Use `python -m json.tool` on your mcp.json
4. **Check WHOOP developer console**: Verify your app settings match

## Security Considerations

### Local Security Benefits
- ✅ **No network exposure** - Server runs locally only
- ✅ **Token stored locally** - No cloud token storage
- ✅ **Process isolation** - Each Claude conversation gets fresh server instance
- ✅ **No API key management** - Direct WHOOP OAuth only

### Best Practices
1. **Keep token file secure** - Don't share `whoop_token.json`
2. **Use environment variables** - Don't hardcode credentials
3. **Regular token rotation** - Re-authenticate periodically
4. **Monitor token usage** - Check WHOOP developer dashboard

## Next Steps

Once you have STDIO working locally:
1. **Try the [WebSocket Guide](websocket-guide.md)** for cloud deployment
2. **Explore the [HTTP Guide](http-guide.md)** for REST API access
3. **Check the [SSE Guide](sse-guide.md)** for real-time streaming

## Advanced Configuration

### Environment Variables
```bash
# Optional: Custom redirect URI
export WHOOP_REDIRECT_URI=http://localhost:9000/callback

# Optional: Custom token storage location
export WHOOP_TOKEN_FILE=/secure/path/whoop_token.json

# Optional: Debug mode
export WHOOP_DEBUG=true
```

### Custom Prompt Examples
```python
# Set a custom prompt for always including health insights
set_custom_prompt("Always provide actionable health insights and recommendations based on WHOOP data. Include relevant medical disclaimers.")
```

Your local WHOOP MCP server is now ready to provide powerful health and fitness insights directly in Claude Desktop! 🏃‍♂️💪
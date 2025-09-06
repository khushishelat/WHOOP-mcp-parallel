# WHOOP x Parallel AI MCP Integration

A demonstration of how to use [Parallel AI](https://parallel.ai) with WHOOP fitness data through the Model Context Protocol (MCP). This project shows how AI agents can access and analyze your personal WHOOP health and fitness data in real-time.

**Forked from:** [dpshade/WHOOP-mcp](https://github.com/dpshade/WHOOP-mcp) - A comprehensive MCP server for WHOOP data. The only adjustment made to this server was adding a workout analysis tool, to access strain and excercise type data for each workout.

## What This Demonstrates

- **AI Agent Integration**: Parallel AI agents can access your WHOOP data through MCP
- **Real-time Analysis**: Stream live analysis progress as the AI processes your fitness data
- **Personalized Insights**: Get AI-powered insights based on your actual WHOOP metrics
- **Multi-tool Coordination**: Watch as AI uses multiple WHOOP data tools to build comprehensive analysis

## Prerequisites

- Python 3.8+
- WHOOP account and API access
- Parallel AI account and API key
- ngrok for secure tunneling (free account works)

## Quick Start

### 1. Clone and Install Dependencies

```bash
git clone <your-repo-url>
cd WHOOP-mcp-parallel

# Install MCP server dependencies
pip install -r requirements.txt

# Install demo dependencies
pip install -r demo_requirements.txt
```

### 2. Set Up WHOOP API Credentials

Get your WHOOP API credentials from the [WHOOP Developer Portal](https://developer.whoop.com/):

```bash
export WHOOP_CLIENT_ID="your_whoop_client_id"
export WHOOP_CLIENT_SECRET="your_whoop_client_secret"
```

### 3. Set Up Parallel AI API Key

Get your API key from [Parallel AI](https://platform.parallel.ai):

```bash
export PARALLEL_API_KEY="your_parallel_api_key"
```

### 4. Start the Local MCP Server

```bash
python web_server.py
```

You should see:
```
INFO: Starting WHOOP MCP Web Server on 0.0.0.0:8080
INFO: Uvicorn running on http://0.0.0.0:8080
```

### 5. Expose Server with ngrok

In a new terminal, first kill any existing ngrok processes, then start ngrok:

```bash
# Kill any existing ngrok processes
pkill -f ngrok

# Start ngrok
ngrok http 8080
```

Copy the HTTPS URL from the output (e.g., `https://abc123.ngrok-free.app`)

### 6. Authenticate with WHOOP

```bash
curl "https://YOUR-NGROK-URL.ngrok-free.app/whoop/auth"
```

Follow the returned auth URL to complete WHOOP OAuth authentication.

### 7. Run the Demo

```bash
python demo_parallel_whoop.py https://YOUR-NGROK-URL.ngrok-free.app
```

## What You'll See

1. **Server startup** - Your local MCP server starts and exposes WHOOP data tools
2. **Parallel AI task creation** - A task is submitted to Parallel AI with access to your server
3. **Real-time streaming** - Watch as the AI:
   - Plans its analysis approach
   - Calls your WHOOP MCP tools to get real data
   - Searches for relevant research and benchmarks
   - Synthesizes personalized insights
4. **Final report** - Comprehensive analysis combining your data with research

## Available MCP Tools

The server exposes these tools that Parallel AI can use:

- `get_sleep_data` - Your sleep metrics and quality scores
- `get_recovery_data` - Recovery scores and HRV data
- `get_workout_data` - Workout details and performance metrics
- `get_cycle_data` - Daily strain and recovery cycles
- `get_profile_data` - Your WHOOP profile information
- `get_workout_analysis` - Detailed workout performance analysis
- `get_sleep_quality_analysis` - Sleep optimization recommendations
- `get_training_readiness` - Multi-factor readiness assessment

## Customization

### Modify the Analysis Prompt

Edit the prompt in `demo_parallel_whoop.py` to focus on different aspects:

```python
def create_prompt():
    return """Analyze my WHOOP data focusing on:
    1. Sleep optimization opportunities
    2. Training load management
    3. Recovery patterns
    [Add your specific questions here]
    """
```

### Add Custom MCP Tools

Add new tools to `whoop_mcp.py`:

```python
@mcp.tool()
def get_custom_analysis() -> str:
    """Your custom analysis tool"""
    # Implementation here
    return "Custom analysis result"
```

## Deployment Options

For production use, consider:

- **Cloud hosting**: Deploy the MCP server to platforms like Railway, Render, or AWS
- **SSL certificates**: Use proper SSL instead of ngrok for production
- **Authentication**: Add proper API key management for team use
- **Rate limiting**: Implement appropriate rate limiting for your use case

See the original [dpshade/WHOOP-mcp](https://github.com/dpshade/WHOOP-mcp) repository for full deployment guides and enterprise features.

## Related Documentation

- [Parallel AI Documentation](https://docs.parallel.ai/)
- [WHOOP Developer API](https://developer.whoop.com/docs)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Original WHOOP-MCP Project](https://github.com/dpshade/WHOOP-mcp)

## Troubleshooting

**"PARALLEL_API_KEY environment variable is required"**
- Make sure you've set the environment variable: `export PARALLEL_API_KEY="your_key"`

**"ngrok URL not working"**
- Check your ngrok tunnel is active: `curl http://localhost:4040/api/tunnels`
- Update the URL in your demo command

**"WHOOP authentication failed"**
- Re-run the auth step: `curl "https://YOUR-NGROK-URL.ngrok-free.app/whoop/auth"`
- Make sure you completed the OAuth flow in your browser

**"No MCP tool calls appearing"**
- Verify your ngrok URL is correct
- Check the MCP server logs for incoming requests
- Ensure WHOOP authentication is fresh (tokens expire)

## Contributing

This is a demonstration project. For production features and bug fixes, contribute to the original [dpshade/WHOOP-mcp](https://github.com/dpshade/WHOOP-mcp) repository.

## License

MIT License - See the original project for full license details.
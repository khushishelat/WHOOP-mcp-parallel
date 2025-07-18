# WHOOP MCP + n8n Integration Master Guide

Complete guide for connecting your Fly hosted WHOOP MCP server to n8n workflows.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Connection Methods](#connection-methods)
- [Setup Instructions](#setup-instructions)
- [n8n Workflow Examples](#n8n-workflow-examples)
- [Authentication & Security](#authentication--security)
- [Troubleshooting](#troubleshooting)
- [Advanced Use Cases](#advanced-use-cases)

## Overview

Your WHOOP MCP server at `https://whoop-mcp.fly.dev` can integrate with n8n in multiple ways:

1. **HTTP REST API** - Direct HTTP calls to your server endpoints
2. **MCP WebSocket** - Native MCP protocol over WebSocket
3. **n8n MCP Nodes** - Using n8n's built-in MCP client nodes

## Prerequisites

### 1. Your WHOOP MCP Server Details
- **Server URL:** `https://whoop-mcp.fly.dev`
- **API Key:** Your secure API key (from deployment)
- **WebSocket URL:** `wss://whoop-mcp.fly.dev/mcp`

### 2. n8n Requirements
- n8n instance (cloud or self-hosted)
- MCP client nodes (if using native MCP integration)
- HTTP Request node (for REST API integration)

### 3. WHOOP Authentication
Ensure your server has valid WHOOP OAuth tokens. Check status:
```bash
curl -H "X-API-Key: YOUR_API_KEY" https://whoop-mcp.fly.dev/auth
```

## Connection Methods

### Method 1: HTTP REST API (Recommended)

Use n8n's HTTP Request node to call your server's REST endpoints.

**Advantages:**
- ✅ Simple setup with standard HTTP Request node
- ✅ Works with any n8n installation
- ✅ Easy debugging and monitoring
- ✅ Familiar REST patterns

**Configuration:**
```json
{
  "method": "GET",
  "url": "https://whoop-mcp.fly.dev/tools",
  "headers": {
    "X-API-Key": "YOUR_API_KEY_HERE"
  }
}
```

### Method 2: Native MCP WebSocket

Use n8n's MCP Client Tool node to connect via WebSocket.

**Advantages:**
- ✅ Native MCP protocol support
- ✅ Real-time communication
- ✅ Built-in tool discovery
- ✅ Standardized interface

**Configuration:**
```json
{
  "serverUrl": "wss://whoop-mcp.fly.dev/mcp",
  "authentication": {
    "type": "header",
    "headerName": "X-API-Key",
    "headerValue": "YOUR_API_KEY_HERE"
  }
}
```

### Method 3: n8n MCP Server Trigger

Expose n8n workflows as MCP tools to your WHOOP server.

**Use Case:** Create custom data processing workflows that your WHOOP server can call.

## Setup Instructions

### Step 1: Test Server Connectivity

First, verify your server is accessible:

```bash
# Health check (public endpoint)
curl https://whoop-mcp.fly.dev/health

# Server info (public endpoint)
curl https://whoop-mcp.fly.dev/

# Available tools (requires API key)
curl -H "X-API-Key: YOUR_API_KEY" https://whoop-mcp.fly.dev/tools

# Auth status (requires API key)
curl -H "X-API-Key: YOUR_API_KEY" https://whoop-mcp.fly.dev/auth
```

### Step 2: n8n HTTP Integration Setup

1. **Create New Workflow** in n8n
2. **Add HTTP Request Node**
3. **Configure Node:**
   ```
   Method: GET
   URL: https://whoop-mcp.fly.dev/tools
   Headers:
     X-API-Key: YOUR_API_KEY_HERE
   ```
4. **Test Connection** - Should return list of available WHOOP tools

### Step 3: n8n MCP Client Setup

1. **Install MCP Client Node** (if not available)
2. **Add MCP Client Tool Node**
3. **Configure Connection:**
   ```
   Server URL: wss://whoop-mcp.fly.dev/mcp
   Authentication: Header
   Header Name: X-API-Key
   Header Value: YOUR_API_KEY_HERE
   ```
4. **Test Connection** - Should discover WHOOP tools automatically

## n8n Workflow Examples

### Example 1: Basic WHOOP Data Retrieval (HTTP Method)

```json
{
  "name": "WHOOP Health Data Fetch",
  "nodes": [
    {
      "name": "Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [240, 300]
    },
    {
      "name": "Get Sleep Data",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [460, 300],
      "parameters": {
        "method": "POST",
        "url": "wss://whoop-mcp.fly.dev/mcp",
        "headers": {
          "X-API-Key": "YOUR_API_KEY_HERE",
          "Content-Type": "application/json"
        },
        "body": {
          "jsonrpc": "2.0",
          "id": 1,
          "method": "tools/call",
          "params": {
            "name": "get_sleep_data",
            "arguments": {}
          }
        }
      }
    },
    {
      "name": "Process Data",
      "type": "n8n-nodes-base.function",
      "typeVersion": 1,
      "position": [680, 300],
      "parameters": {
        "functionCode": "// Extract sleep data from MCP response\nconst mcpResponse = items[0].json;\nconst sleepData = JSON.parse(mcpResponse.result.content[0].text);\n\n// Transform data for further processing\nreturn [{\n  json: {\n    sleep_efficiency: sleepData.sleep_efficiency,\n    sleep_score: sleepData.sleep_score,\n    total_sleep_time: sleepData.total_sleep_time,\n    date: sleepData.date\n  }\n}];"
      }
    }
  ],
  "connections": {
    "Trigger": {
      "main": [
        [
          {
            "node": "Get Sleep Data",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get Sleep Data": {
      "main": [
        [
          {
            "node": "Process Data",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

### Example 2: Daily Health Summary (MCP Client Method)

```json
{
  "name": "Daily WHOOP Summary",
  "nodes": [
    {
      "name": "Daily Trigger",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1,
      "position": [240, 300],
      "parameters": {
        "rule": {
          "hour": 8,
          "minute": 0
        }
      }
    },
    {
      "name": "Get Sleep Analysis",
      "type": "n8n-nodes-langchain.toolMcp",
      "typeVersion": 1,
      "position": [460, 200],
      "parameters": {
        "serverUrl": "wss://whoop-mcp.fly.dev/mcp",
        "authentication": {
          "type": "header",
          "headerName": "X-API-Key",
          "headerValue": "YOUR_API_KEY_HERE"
        },
        "toolName": "get_sleep_quality_analysis",
        "arguments": {}
      }
    },
    {
      "name": "Get Recovery Data",
      "type": "n8n-nodes-langchain.toolMcp",
      "typeVersion": 1,
      "position": [460, 350],
      "parameters": {
        "serverUrl": "wss://whoop-mcp.fly.dev/mcp",
        "authentication": {
          "type": "header",
          "headerName": "X-API-Key",
          "headerValue": "YOUR_API_KEY_HERE"
        },
        "toolName": "get_recovery_load_analysis",
        "arguments": {}
      }
    },
    {
      "name": "Get Training Readiness",
      "type": "n8n-nodes-langchain.toolMcp",
      "typeVersion": 1,
      "position": [460, 500],
      "parameters": {
        "serverUrl": "wss://whoop-mcp.fly.dev/mcp",
        "authentication": {
          "type": "header",
          "headerName": "X-API-Key",
          "headerValue": "YOUR_API_KEY_HERE"
        },
        "toolName": "get_training_readiness",
        "arguments": {}
      }
    },
    {
      "name": "Combine Data",
      "type": "n8n-nodes-base.merge",
      "typeVersion": 2,
      "position": [680, 350],
      "parameters": {
        "mode": "combine",
        "combineBy": "combineAll"
      }
    },
    {
      "name": "Generate Summary",
      "type": "n8n-nodes-base.function",
      "typeVersion": 1,
      "position": [900, 350],
      "parameters": {
        "functionCode": "// Combine all WHOOP data into daily summary\nconst sleepAnalysis = items[0].json;\nconst recoveryData = items[1].json;\nconst readinessData = items[2].json;\n\nconst summary = {\n  date: new Date().toISOString().split('T')[0],\n  sleep: {\n    score: sleepAnalysis.sleep_score || 'N/A',\n    efficiency: sleepAnalysis.sleep_efficiency || 'N/A',\n    recommendations: sleepAnalysis.recommendations || []\n  },\n  recovery: {\n    score: recoveryData.recovery_score || 'N/A',\n    load_breakdown: recoveryData.load_breakdown || {},\n    recommendations: recoveryData.recommendations || []\n  },\n  readiness: {\n    score: readinessData.readiness_score || 'N/A',\n    factors: readinessData.readiness_factors || {},\n    recommendations: readinessData.recommendations || []\n  },\n  overall_health_status: determineOverallStatus(sleepAnalysis, recoveryData, readinessData)\n};\n\nfunction determineOverallStatus(sleep, recovery, readiness) {\n  const scores = [sleep.sleep_score, recovery.recovery_score, readiness.readiness_score]\n    .filter(score => score && typeof score === 'number');\n  \n  if (scores.length === 0) return 'Insufficient Data';\n  \n  const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;\n  \n  if (avgScore >= 75) return 'Excellent';\n  if (avgScore >= 60) return 'Good';\n  if (avgScore >= 45) return 'Fair';\n  return 'Needs Attention';\n}\n\nreturn [{ json: summary }];"
      }
    },
    {
      "name": "Send Summary",
      "type": "n8n-nodes-base.emailSend",
      "typeVersion": 2,
      "position": [1120, 350],
      "parameters": {
        "to": "your-email@domain.com",
        "subject": "Daily WHOOP Health Summary - {{ $json.date }}",
        "text": "Your Daily Health Summary:\n\nOverall Status: {{ $json.overall_health_status }}\n\nSleep Score: {{ $json.sleep.score }}\nRecovery Score: {{ $json.recovery.score }}\nReadiness Score: {{ $json.readiness.score }}\n\nRecommendations:\n{{ $json.sleep.recommendations.join('\\n') }}\n{{ $json.recovery.recommendations.join('\\n') }}\n{{ $json.readiness.recommendations.join('\\n') }}"
      }
    }
  ],
  "connections": {
    "Daily Trigger": {
      "main": [
        [
          {
            "node": "Get Sleep Analysis",
            "type": "main",
            "index": 0
          },
          {
            "node": "Get Recovery Data",
            "type": "main",
            "index": 0
          },
          {
            "node": "Get Training Readiness",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get Sleep Analysis": {
      "main": [
        [
          {
            "node": "Combine Data",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get Recovery Data": {
      "main": [
        [
          {
            "node": "Combine Data",
            "type": "main",
            "index": 1
          }
        ]
      ]
    },
    "Get Training Readiness": {
      "main": [
        [
          {
            "node": "Combine Data",
            "type": "main",
            "index": 2
          }
        ]
      ]
    },
    "Combine Data": {
      "main": [
        [
          {
            "node": "Generate Summary",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Generate Summary": {
      "main": [
        [
          {
            "node": "Send Summary",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

### Example 3: Conditional Workout Alerts

```json
{
  "name": "WHOOP Workout Alerts",
  "nodes": [
    {
      "name": "Every Hour Check",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1,
      "position": [240, 300],
      "parameters": {
        "rule": {
          "minute": 0
        }
      }
    },
    {
      "name": "Get Recent Workouts",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [460, 300],
      "parameters": {
        "method": "POST",
        "url": "wss://whoop-mcp.fly.dev/mcp",
        "headers": {
          "X-API-Key": "YOUR_API_KEY_HERE",
          "Content-Type": "application/json"
        },
        "body": {
          "jsonrpc": "2.0",
          "id": 1,
          "method": "tools/call",
          "params": {
            "name": "get_workout_data",
            "arguments": {
              "limit": 5
            }
          }
        }
      }
    },
    {
      "name": "Check for High Strain",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [680, 300],
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.result.content[0].text }}",
              "operation": "contains",
              "value2": "strain"
            }
          ]
        }
      }
    },
    {
      "name": "Send High Strain Alert",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [900, 200],
      "parameters": {
        "channel": "#health-alerts",
        "text": "🔥 High strain workout detected! Consider extra recovery time."
      }
    },
    {
      "name": "Log Normal Activity",
      "type": "n8n-nodes-base.function",
      "typeVersion": 1,
      "position": [900, 400],
      "parameters": {
        "functionCode": "console.log('Normal workout activity detected');\nreturn items;"
      }
    }
  ],
  "connections": {
    "Every Hour Check": {
      "main": [
        [
          {
            "node": "Get Recent Workouts",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get Recent Workouts": {
      "main": [
        [
          {
            "node": "Check for High Strain",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Check for High Strain": {
      "main": [
        [
          {
            "node": "Send High Strain Alert",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "Log Normal Activity",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

## Authentication & Security

### API Key Management

1. **Store API Key Securely** in n8n:
   - Use n8n's credential system
   - Never hardcode in workflow JSON
   - Set as environment variable in n8n

2. **Test Authentication**:
   ```bash
   # Verify your API key works
   curl -H "X-API-Key: YOUR_API_KEY" https://whoop-mcp.fly.dev/auth
   ```

3. **Error Handling for Auth Failures**:
   ```javascript
   // Add to Function nodes for error handling
   if (items[0].json.error && items[0].json.error.includes('Unauthorized')) {
     throw new Error('WHOOP MCP authentication failed. Check API key.');
   }
   ```

### Rate Limiting

Your server has rate limiting (60 requests/minute). Handle this in n8n:

```javascript
// Add delays between requests
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
await delay(1000); // 1 second delay
```

### WHOOP OAuth Token Management

Monitor WHOOP token status:

```json
{
  "name": "Check WHOOP Auth",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "https://whoop-mcp.fly.dev/auth",
    "headers": {
      "X-API-Key": "YOUR_API_KEY"
    }
  }
}
```

If `authenticated: false`, you'll need to re-authenticate with WHOOP:
1. Visit: `https://whoop-mcp.fly.dev/whoop/auth`
2. Complete OAuth flow
3. Verify: `https://whoop-mcp.fly.dev/auth`

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Test basic connectivity
ping whoop-mcp.fly.dev
curl -I https://whoop-mcp.fly.dev/health
```

#### 2. 401 Unauthorized
- Verify API key is correct
- Check if API key is properly set in n8n headers
- Test with curl: `curl -H "X-API-Key: YOUR_KEY" https://whoop-mcp.fly.dev/tools`

#### 3. 429 Rate Limited
- Add delays between requests in workflows
- Reduce frequency of scheduled workflows
- Implement exponential backoff in Function nodes

#### 4. WHOOP Authentication Expired
- Check auth status: `GET /auth`
- Re-authenticate at: `GET /whoop/auth`
- Monitor token expiration in workflows

#### 5. WebSocket Connection Issues
- Verify WebSocket URL: `wss://whoop-mcp.fly.dev/mcp`
- Check firewall/proxy settings
- Try HTTP method as fallback

### Debug Workflow

Create this test workflow to verify all components:

```json
{
  "name": "WHOOP MCP Debug",
  "nodes": [
    {
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger"
    },
    {
      "name": "Test Health",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://whoop-mcp.fly.dev/health"
      }
    },
    {
      "name": "Test Auth",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://whoop-mcp.fly.dev/auth",
        "headers": {
          "X-API-Key": "YOUR_API_KEY"
        }
      }
    },
    {
      "name": "Test Tools",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://whoop-mcp.fly.dev/tools",
        "headers": {
          "X-API-Key": "YOUR_API_KEY"
        }
      }
    }
  ]
}
```

## Advanced Use Cases

### 1. Multi-User WHOOP Data Aggregation

If you have multiple WHOOP accounts, create workflows that:
- Aggregate data from multiple servers
- Compare metrics across users
- Generate team health reports

### 2. Integration with Other Health APIs

Combine WHOOP data with:
- Apple Health via n8n nodes
- Fitbit data
- Nutrition tracking apps
- Sleep tracking devices

### 3. AI-Powered Health Insights

Use n8n's AI nodes to:
- Analyze WHOOP trends with ChatGPT
- Generate personalized recommendations
- Predict optimal training times

### 4. Custom Alert Systems

Create sophisticated alerting:
- Anomaly detection in health metrics
- Predictive alerts for overtraining
- Recovery optimization suggestions

### 5. Data Visualization Pipelines

Send WHOOP data to:
- Grafana dashboards
- Google Sheets for analysis
- Custom web applications
- Business intelligence tools

## Available WHOOP MCP Tools

Your server provides these tools for n8n workflows:

### Core Data Tools
- `get_sleep_data` - Sleep metrics and analysis
- `get_recovery_data` - Recovery scores and load breakdown
- `get_workout_data` - Workout performance and metrics
- `get_cycle_data` - Daily strain and load cycles
- `get_profile_data` - User profile information
- `get_body_measurement_data` - Body composition tracking

### Advanced Analytics Tools
- `get_workout_analysis` - Detailed performance analysis
- `get_sleep_quality_analysis` - Sleep optimization recommendations
- `get_recovery_load_analysis` - System-specific recovery strategies
- `get_training_readiness` - Multi-factor readiness assessment

### Utility Tools
- `get_sports_mapping` - Sport ID to name mapping
- `search_whoop_sports` - Find specific sports
- `set_custom_prompt` - Customize server responses
- `get_custom_prompt` - View current custom prompt
- `clear_custom_prompt` - Reset to default prompt

## Quick Start Checklist

- [ ] Verify WHOOP MCP server is running: `https://whoop-mcp.fly.dev/health`
- [ ] Get your API key from server deployment
- [ ] Test authentication: `curl -H "X-API-Key: KEY" https://whoop-mcp.fly.dev/auth`
- [ ] Create basic n8n workflow with HTTP Request node
- [ ] Configure authentication headers in n8n
- [ ] Test WHOOP tool call (e.g., `get_sleep_data`)
- [ ] Set up error handling and rate limiting
- [ ] Create scheduled workflows for automated data collection
- [ ] Configure notifications and alerts
- [ ] Document your workflows for team use

## Support and Resources

- **Server Status:** https://whoop-mcp.fly.dev/health
- **Available Tools:** https://whoop-mcp.fly.dev/tools (with API key)
- **Authentication:** https://whoop-mcp.fly.dev/auth (with API key)
- **WHOOP OAuth:** https://whoop-mcp.fly.dev/whoop/auth

---

**🎯 You're now ready to integrate your WHOOP MCP server with n8n workflows!**

Start with the basic HTTP method, then explore advanced MCP features as you build more sophisticated health automation workflows.
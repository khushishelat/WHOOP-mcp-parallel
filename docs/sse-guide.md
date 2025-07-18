# WHOOP MCP Server - Server-Sent Events (SSE) Guide

This guide covers how to use Server-Sent Events (SSE) with your WHOOP MCP server for real-time data streaming and live updates.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [SSE vs Other Methods](#sse-vs-other-methods)
- [Claude Desktop Configuration](#claude-desktop-configuration)
- [SSE Client Examples](#sse-client-examples)
- [Custom SSE Implementation](#custom-sse-implementation)
- [Real-time WHOOP Data](#real-time-whoop-data)
- [Authentication & Security](#authentication--security)
- [Troubleshooting](#troubleshooting)

## Overview

Server-Sent Events (SSE) provide a way to receive real-time updates from your WHOOP MCP server. While your current deployment doesn't have native SSE endpoints, this guide shows how to implement SSE patterns and integrate with MCP using event-driven architectures.

**Benefits of SSE:**
- 📡 **Real-time updates** - Get data as it becomes available
- 🔄 **Automatic reconnection** - Built-in reconnection handling
- 🌐 **Browser compatible** - Native browser EventSource API
- 📊 **Live monitoring** - Real-time health and data monitoring
- ⚡ **Low latency** - Immediate data delivery

**Current Implementation:** While your server uses WebSocket for real-time communication, we'll show how to create SSE-compatible patterns and integrations.

## Prerequisites

### 1. API Access
- **Base URL:** `https://whoop-mcp.fly.dev`
- **API Key:** `YOUR_API_KEY_HERE`

🚨 **SECURITY WARNING**: 
- **Never commit API keys to git** 
- **Replace `YOUR_API_KEY_HERE` with your actual key**
- **Keep this key secure** - it provides access to your WHOOP data
- **Use environment variables** for production deployments

### 2. Understanding Event Sources
SSE uses a simple text-based protocol over HTTP:
```
data: {"event": "whoop_update", "data": {...}}

data: {"event": "heartbeat", "timestamp": "2024-01-15T10:30:00Z"}

```

### 3. Network Requirements
- **HTTPS connection** to your server
- **Persistent HTTP connection** support
- **CORS handling** for browser clients

## SSE vs Other Methods

| Method | Use Case | Benefits | Limitations |
|--------|----------|----------|-------------|
| **SSE** | Real-time updates, live monitoring | Simple, browser native, auto-reconnect | Server-to-client only |
| **WebSocket** | Bi-directional real-time communication | Full duplex, low overhead | More complex setup |
| **HTTP** | Request/response, automation | Simple, universal | Not real-time |
| **STDIO** | Local development, CLI tools | Secure, fast | Local only |

## Claude Desktop Configuration

### 1. SSE Server Configuration Template

While your current server uses WebSocket, here's how you would configure an SSE-based MCP server in Claude Desktop:

```json
{
  "mcpServers": {
    "whoop-sse": {
      "type": "sse",
      "url": "https://whoop-mcp.fly.dev/sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY_HERE",
        "X-API-Key": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### 2. Hybrid Configuration (Current + SSE)

You can combine your existing WebSocket server with SSE monitoring:

```json
{
  "mcpServers": {
    "whoop-primary": {
      "command": "node",
      "args": ["/path/to/websocket-client.js"],
      "env": {
        "WHOOP_MCP_URL": "wss://whoop-mcp.fly.dev/mcp",
        "WHOOP_API_KEY": "YOUR_API_KEY_HERE"
      }
    },
    "whoop-monitor": {
      "command": "node",
      "args": ["/path/to/sse-monitor.js"],
      "env": {
        "WHOOP_BASE_URL": "https://whoop-mcp.fly.dev",
        "WHOOP_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

## SSE Client Examples

### 1. Browser EventSource

```html
<!DOCTYPE html>
<html>
<head>
    <title>WHOOP MCP SSE Monitor</title>
    <style>
        .event { 
            border: 1px solid #ccc; 
            margin: 5px 0; 
            padding: 10px; 
            background: #f9f9f9; 
        }
        .error { background: #ffebee; }
        .success { background: #e8f5e8; }
    </style>
</head>
<body>
    <h1>WHOOP MCP Real-time Monitor</h1>
    <div id="status">Connecting...</div>
    <div id="events"></div>

    <script>
        const apiKey = 'YOUR_API_KEY_HERE';
        const baseUrl = 'https://whoop-mcp.fly.dev';
        
        // Simulated SSE using polling + WebSocket for real-time feel
        class WHOOPSSEMonitor {
            constructor() {
                this.eventContainer = document.getElementById('events');
                this.statusElement = document.getElementById('status');
                this.isConnected = false;
                this.pollInterval = null;
            }
            
            start() {
                this.statusElement.textContent = 'Connecting to WHOOP MCP...';
                this.setupPolling();
                this.connectWebSocket();
            }
            
            setupPolling() {
                // Poll health endpoint every 30 seconds
                this.pollInterval = setInterval(async () => {
                    try {
                        const response = await fetch(`${baseUrl}/health`);
                        const data = await response.json();
                        this.emitEvent('health_check', data);
                    } catch (error) {
                        this.emitEvent('error', { message: error.message });
                    }
                }, 30000);
            }
            
            connectWebSocket() {
                // Note: Browser WebSocket can't set custom headers
                // This is a simplified example - real implementation would need a proxy
                try {
                    const ws = new WebSocket('wss://whoop-mcp.fly.dev/mcp');
                    
                    ws.onopen = () => {
                        this.isConnected = true;
                        this.statusElement.textContent = 'Connected to WHOOP MCP';
                        this.statusElement.className = 'success';
                        this.emitEvent('connected', { timestamp: new Date().toISOString() });
                    };
                    
                    ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            this.emitEvent('whoop_data', data);
                        } catch (e) {
                            this.emitEvent('raw_message', { data: event.data });
                        }
                    };
                    
                    ws.onclose = () => {
                        this.isConnected = false;
                        this.statusElement.textContent = 'Disconnected from WHOOP MCP';
                        this.statusElement.className = 'error';
                        this.emitEvent('disconnected', { timestamp: new Date().toISOString() });
                    };
                    
                    ws.onerror = (error) => {
                        this.emitEvent('error', { message: 'WebSocket error occurred' });
                    };
                    
                } catch (error) {
                    this.emitEvent('error', { message: `Connection failed: ${error.message}` });
                }
            }
            
            emitEvent(type, data) {
                const eventDiv = document.createElement('div');
                eventDiv.className = `event ${type === 'error' ? 'error' : 'success'}`;
                eventDiv.innerHTML = `
                    <strong>${type.toUpperCase()}</strong> - ${new Date().toLocaleTimeString()}<br>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
                
                this.eventContainer.insertBefore(eventDiv, this.eventContainer.firstChild);
                
                // Keep only last 20 events
                while (this.eventContainer.children.length > 20) {
                    this.eventContainer.removeChild(this.eventContainer.lastChild);
                }
            }
            
            stop() {
                if (this.pollInterval) {
                    clearInterval(this.pollInterval);
                }
            }
        }
        
        // Start monitoring
        const monitor = new WHOOPSSEMonitor();
        monitor.start();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => monitor.stop());
    </script>
</body>
</html>
```

### 2. Node.js SSE Client

```javascript
#!/usr/bin/env node
// sse-client.js - Node.js SSE client for WHOOP MCP

const EventSource = require('eventsource');
const fetch = require('node-fetch');

class WHOOPSSEClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.eventSource = null;
        this.pollInterval = null;
    }
    
    // Simulate SSE using HTTP polling
    startPolling(interval = 10000) {
        console.log('Starting WHOOP MCP polling...');
        
        this.pollInterval = setInterval(async () => {
            try {
                await this.checkHealth();
                await this.checkAuthStatus();
            } catch (error) {
                this.emit('error', { message: error.message });
            }
        }, interval);
    }
    
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            const data = await response.json();
            this.emit('health_update', data);
        } catch (error) {
            this.emit('health_error', { error: error.message });
        }
    }
    
    async checkAuthStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/auth`, {
                headers: { 'X-API-Key': this.apiKey }
            });
            const data = await response.json();
            this.emit('auth_update', data);
        } catch (error) {
            this.emit('auth_error', { error: error.message });
        }
    }
    
    emit(eventType, data) {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] ${eventType.toUpperCase()}:`, JSON.stringify(data, null, 2));
        
        // Simulate SSE event format
        process.stdout.write(`event: ${eventType}\n`);
        process.stdout.write(`data: ${JSON.stringify({ timestamp, ...data })}\n\n`);
    }
    
    stop() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            console.log('Stopped WHOOP MCP polling');
        }
        
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}

// Usage
const client = new WHOOPSSEClient(
    'https://whoop-mcp.fly.dev',
    'YOUR_API_KEY_HERE'
);

client.startPolling(15000); // Poll every 15 seconds

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\nShutting down SSE client...');
    client.stop();
    process.exit(0);
});

process.on('SIGTERM', () => {
    client.stop();
    process.exit(0);
});
```

### 3. Python SSE Client

```python
#!/usr/bin/env python3
"""
Python SSE client for WHOOP MCP server
Provides real-time monitoring with SSE-like events
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import signal
import sys

class WHOOPSSEClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
        self.running = False
        self.headers = {'X-API-Key': api_key}
    
    async def start(self, poll_interval=10):
        """Start the SSE client with polling"""
        self.session = aiohttp.ClientSession()
        self.running = True
        
        print(f"Starting WHOOP MCP SSE client (polling every {poll_interval}s)")
        
        # Start polling task
        await asyncio.gather(
            self.health_monitor(poll_interval),
            self.auth_monitor(poll_interval * 2),  # Check auth less frequently
            return_exceptions=True
        )
    
    async def health_monitor(self, interval):
        """Monitor server health"""
        while self.running:
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    data = await response.json()
                    await self.emit_event('health_check', data)
            except Exception as e:
                await self.emit_event('health_error', {'error': str(e)})
            
            await asyncio.sleep(interval)
    
    async def auth_monitor(self, interval):
        """Monitor authentication status"""
        while self.running:
            try:
                async with self.session.get(f"{self.base_url}/auth", headers=self.headers) as response:
                    data = await response.json()
                    await self.emit_event('auth_status', data)
            except Exception as e:
                await self.emit_event('auth_error', {'error': str(e)})
            
            await asyncio.sleep(interval)
    
    async def emit_event(self, event_type, data):
        """Emit SSE-formatted event"""
        timestamp = datetime.now().isoformat()
        event_data = {
            'timestamp': timestamp,
            'event': event_type,
            'data': data
        }
        
        # SSE format output
        print(f"event: {event_type}")
        print(f"data: {json.dumps(event_data)}")
        print()  # Empty line to separate events
        
        # Also log to stderr for debugging
        print(f"[{timestamp}] {event_type.upper()}: {json.dumps(data)}", file=sys.stderr)
    
    async def stop(self):
        """Stop the SSE client"""
        self.running = False
        if self.session:
            await self.session.close()
        print("WHOOP SSE client stopped", file=sys.stderr)

# Global client instance for signal handling
client = None

async def shutdown():
    """Graceful shutdown"""
    if client:
        await client.stop()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down...", file=sys.stderr)
    if client:
        asyncio.create_task(shutdown())
    sys.exit(0)

async def main():
    global client
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start client
    client = WHOOPSSEClient(
        'https://whoop-mcp.fly.dev',
        'YOUR_API_KEY_HERE'
    )
    
    try:
        await client.start(poll_interval=15)
    except KeyboardInterrupt:
        await shutdown()
    except Exception as e:
        print(f"Client error: {e}", file=sys.stderr)
        await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Custom SSE Implementation

### 1. SSE Proxy Server

Create a proxy server that converts your WebSocket/HTTP API to SSE:

```javascript
// sse-proxy.js - Convert WHOOP MCP to SSE
const express = require('express');
const WebSocket = require('ws');
const fetch = require('node-fetch');

const app = express();
const PORT = process.env.PORT || 3001;

const WHOOP_BASE_URL = 'https://whoop-mcp.fly.dev';
const WHOOP_API_KEY = 'YOUR_API_KEY_HERE';

// CORS middleware
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
    next();
});

// SSE endpoint
app.get('/whoop/events', (req, res) => {
    // Set SSE headers
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
    });
    
    // Send initial connection event
    res.write(`event: connected\n`);
    res.write(`data: ${JSON.stringify({ timestamp: new Date().toISOString() })}\n\n`);
    
    // Setup polling for health checks
    const healthInterval = setInterval(async () => {
        try {
            const response = await fetch(`${WHOOP_BASE_URL}/health`);
            const data = await response.json();
            
            res.write(`event: health\n`);
            res.write(`data: ${JSON.stringify({ timestamp: new Date().toISOString(), ...data })}\n\n`);
        } catch (error) {
            res.write(`event: error\n`);
            res.write(`data: ${JSON.stringify({ error: error.message, timestamp: new Date().toISOString() })}\n\n`);
        }
    }, 30000);
    
    // Setup auth status checking
    const authInterval = setInterval(async () => {
        try {
            const response = await fetch(`${WHOOP_BASE_URL}/auth`, {
                headers: { 'X-API-Key': WHOOP_API_KEY }
            });
            const data = await response.json();
            
            res.write(`event: auth_status\n`);
            res.write(`data: ${JSON.stringify({ timestamp: new Date().toISOString(), ...data })}\n\n`);
        } catch (error) {
            res.write(`event: auth_error\n`);
            res.write(`data: ${JSON.stringify({ error: error.message, timestamp: new Date().toISOString() })}\n\n`);
        }
    }, 60000);
    
    // Heartbeat every 10 seconds
    const heartbeatInterval = setInterval(() => {
        res.write(`event: heartbeat\n`);
        res.write(`data: ${JSON.stringify({ timestamp: new Date().toISOString() })}\n\n`);
    }, 10000);
    
    // Cleanup on client disconnect
    req.on('close', () => {
        clearInterval(healthInterval);
        clearInterval(authInterval);
        clearInterval(heartbeatInterval);
    });
});

// Health endpoint for the proxy itself
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'whoop-sse-proxy' });
});

app.listen(PORT, () => {
    console.log(`WHOOP SSE Proxy running on port ${PORT}`);
    console.log(`SSE endpoint: http://localhost:${PORT}/whoop/events`);
});
```

### 2. MCP SSE Configuration

Use the proxy with Claude Desktop:

```json
{
  "mcpServers": {
    "whoop-sse": {
      "type": "sse",
      "url": "http://localhost:3001/whoop/events",
      "reconnectInterval": 5000
    }
  }
}
```

### 3. Browser Client for Proxy

```html
<!DOCTYPE html>
<html>
<head>
    <title>WHOOP MCP SSE Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .event { padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; background: #f8f9fa; }
        .error { border-color: #dc3545; background: #f8d7da; }
        .health { border-color: #28a745; background: #d4edda; }
        .connected { border-color: #17a2b8; background: #d1ecf1; }
        #status { font-weight: bold; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>WHOOP MCP Live Dashboard</h1>
    <div id="status">Connecting...</div>
    <div id="events"></div>

    <script>
        const eventSource = new EventSource('http://localhost:3001/whoop/events');
        const statusDiv = document.getElementById('status');
        const eventsDiv = document.getElementById('events');
        
        eventSource.onopen = function() {
            statusDiv.textContent = 'Connected to WHOOP MCP';
            statusDiv.style.color = 'green';
        };
        
        eventSource.onerror = function() {
            statusDiv.textContent = 'Connection error';
            statusDiv.style.color = 'red';
        };
        
        // Handle different event types
        eventSource.addEventListener('connected', function(e) {
            addEvent('connected', JSON.parse(e.data));
        });
        
        eventSource.addEventListener('health', function(e) {
            addEvent('health', JSON.parse(e.data));
        });
        
        eventSource.addEventListener('auth_status', function(e) {
            addEvent('auth_status', JSON.parse(e.data));
        });
        
        eventSource.addEventListener('error', function(e) {
            addEvent('error', JSON.parse(e.data));
        });
        
        eventSource.addEventListener('heartbeat', function(e) {
            // Update connection status
            statusDiv.textContent = `Connected - Last heartbeat: ${new Date().toLocaleTimeString()}`;
        });
        
        function addEvent(type, data) {
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${type}`;
            eventDiv.innerHTML = `
                <strong>${type.toUpperCase()}</strong> - ${new Date(data.timestamp).toLocaleString()}<br>
                <pre>${JSON.stringify(data, null, 2)}</pre>
            `;
            
            eventsDiv.insertBefore(eventDiv, eventsDiv.firstChild);
            
            // Keep only last 50 events
            while (eventsDiv.children.length > 50) {
                eventsDiv.removeChild(eventsDiv.lastChild);
            }
        }
    </script>
</body>
</html>
```

## Real-time WHOOP Data

### 1. Live Data Monitoring

Create a comprehensive monitoring solution:

```python
#!/usr/bin/env python3
"""
Real-time WHOOP data monitor using SSE patterns
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WHOOPRealTimeMonitor:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {'X-API-Key': api_key}
        self.session = None
        self.running = False
        self.last_data = {}
    
    async def start_monitoring(self):
        """Start real-time monitoring"""
        self.session = aiohttp.ClientSession()
        self.running = True
        
        logger.info("Starting WHOOP real-time monitoring")
        
        # Start different monitoring tasks
        tasks = [
            self.monitor_recovery(),
            self.monitor_sleep(),
            self.monitor_workouts(),
            self.monitor_server_health()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def monitor_recovery(self):
        """Monitor recovery data changes"""
        while self.running:
            try:
                # In a real implementation, you'd call WHOOP API through WebSocket
                # This simulates checking for recovery data updates
                await self.emit_sse_event('recovery_check', {
                    'message': 'Checking for new recovery data',
                    'interval': '5 minutes'
                })
                
                # Simulate recovery data
                recovery_data = {
                    'recovery_score': 85,
                    'hrv': 45.2,
                    'resting_hr': 52,
                    'skin_temp': 98.2
                }
                
                if self.data_changed('recovery', recovery_data):
                    await self.emit_sse_event('recovery_update', recovery_data)
                    self.last_data['recovery'] = recovery_data
                
            except Exception as e:
                await self.emit_sse_event('recovery_error', {'error': str(e)})
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def monitor_sleep(self):
        """Monitor sleep data changes"""
        while self.running:
            try:
                await self.emit_sse_event('sleep_check', {
                    'message': 'Checking for new sleep data'
                })
                
                # Simulate sleep data
                sleep_data = {
                    'sleep_score': 78,
                    'total_sleep': '7h 24m',
                    'deep_sleep': '1h 45m',
                    'rem_sleep': '2h 12m',
                    'efficiency': 89
                }
                
                if self.data_changed('sleep', sleep_data):
                    await self.emit_sse_event('sleep_update', sleep_data)
                    self.last_data['sleep'] = sleep_data
                
            except Exception as e:
                await self.emit_sse_event('sleep_error', {'error': str(e)})
            
            await asyncio.sleep(600)  # Check every 10 minutes
    
    async def monitor_workouts(self):
        """Monitor for new workouts"""
        while self.running:
            try:
                await self.emit_sse_event('workout_check', {
                    'message': 'Checking for new workouts'
                })
                
                # In real implementation, check for new workouts since last check
                # This simulates detecting a new workout
                
            except Exception as e:
                await self.emit_sse_event('workout_error', {'error': str(e)})
            
            await asyncio.sleep(180)  # Check every 3 minutes
    
    async def monitor_server_health(self):
        """Monitor server health"""
        while self.running:
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    data = await response.json()
                    await self.emit_sse_event('server_health', data)
                    
            except Exception as e:
                await self.emit_sse_event('server_error', {'error': str(e)})
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    def data_changed(self, data_type, new_data):
        """Check if data has changed since last check"""
        if data_type not in self.last_data:
            return True
        return self.last_data[data_type] != new_data
    
    async def emit_sse_event(self, event_type, data):
        """Emit SSE-formatted event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event': event_type,
            'data': data
        }
        
        # Output in SSE format
        print(f"event: {event_type}")
        print(f"data: {json.dumps(event)}")
        print()  # Empty line separator
        
        # Log to stderr for debugging
        logger.info(f"{event_type}: {json.dumps(data)}")
    
    async def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Monitoring stopped")

# Usage
async def main():
    monitor = WHOOPRealTimeMonitor(
        'https://whoop-mcp.fly.dev',
        'YOUR_API_KEY_HERE'
    )
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Alert System

Create an alert system using SSE patterns:

```javascript
// whoop-alerts.js - Real-time WHOOP alerts
const fetch = require('node-fetch');

class WHOOPAlertSystem {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.headers = { 'X-API-Key': apiKey };
        this.thresholds = {
            recovery: { low: 30, critical: 20 },
            sleep: { low: 60, critical: 40 },
            strain: { high: 18, critical: 20 }
        };
    }
    
    async startMonitoring() {
        console.log('Starting WHOOP alert monitoring...');
        
        // Check every 5 minutes
        setInterval(() => this.checkAlerts(), 5 * 60 * 1000);
        
        // Initial check
        await this.checkAlerts();
    }
    
    async checkAlerts() {
        try {
            // Simulate checking current metrics
            // In real implementation, you'd fetch actual WHOOP data
            const metrics = await this.getCurrentMetrics();
            
            await this.checkRecoveryAlerts(metrics.recovery);
            await this.checkSleepAlerts(metrics.sleep);
            await this.checkStrainAlerts(metrics.strain);
            
        } catch (error) {
            this.emitAlert('system_error', { error: error.message });
        }
    }
    
    async getCurrentMetrics() {
        // Simulate current metrics
        // In real implementation, call WebSocket or HTTP endpoints
        return {
            recovery: Math.floor(Math.random() * 100),
            sleep: Math.floor(Math.random() * 100),
            strain: Math.floor(Math.random() * 21)
        };
    }
    
    async checkRecoveryAlerts(recovery) {
        if (recovery <= this.thresholds.recovery.critical) {
            this.emitAlert('recovery_critical', {
                value: recovery,
                threshold: this.thresholds.recovery.critical,
                message: 'Critical recovery level - consider rest day'
            });
        } else if (recovery <= this.thresholds.recovery.low) {
            this.emitAlert('recovery_low', {
                value: recovery,
                threshold: this.thresholds.recovery.low,
                message: 'Low recovery - take it easy today'
            });
        }
    }
    
    async checkSleepAlerts(sleep) {
        if (sleep <= this.thresholds.sleep.critical) {
            this.emitAlert('sleep_critical', {
                value: sleep,
                threshold: this.thresholds.sleep.critical,
                message: 'Critical sleep deficit - prioritize rest'
            });
        } else if (sleep <= this.thresholds.sleep.low) {
            this.emitAlert('sleep_low', {
                value: sleep,
                threshold: this.thresholds.sleep.low,
                message: 'Poor sleep quality detected'
            });
        }
    }
    
    async checkStrainAlerts(strain) {
        if (strain >= this.thresholds.strain.critical) {
            this.emitAlert('strain_critical', {
                value: strain,
                threshold: this.thresholds.strain.critical,
                message: 'Extreme strain level - consider recovery'
            });
        } else if (strain >= this.thresholds.strain.high) {
            this.emitAlert('strain_high', {
                value: strain,
                threshold: this.thresholds.strain.high,
                message: 'High strain detected'
            });
        }
    }
    
    emitAlert(alertType, data) {
        const alert = {
            timestamp: new Date().toISOString(),
            type: alertType,
            severity: this.getAlertSeverity(alertType),
            ...data
        };
        
        // Emit as SSE event
        console.log(`event: ${alertType}`);
        console.log(`data: ${JSON.stringify(alert)}`);
        console.log(); // Empty line
        
        // Also send to other systems (email, Slack, etc.)
        this.sendNotification(alert);
    }
    
    getAlertSeverity(alertType) {
        if (alertType.includes('critical')) return 'critical';
        if (alertType.includes('high') || alertType.includes('low')) return 'warning';
        return 'info';
    }
    
    async sendNotification(alert) {
        // Send to Slack, email, push notifications, etc.
        console.error(`🚨 ALERT: ${alert.type} - ${alert.message}`);
    }
}

// Usage
const alertSystem = new WHOOPAlertSystem(
    'https://whoop-mcp.fly.dev',
    'YOUR_API_KEY_HERE'
);

alertSystem.startMonitoring();
```

## Authentication & Security

### 1. SSE with Authentication

```javascript
// Secure SSE client with token refresh
class SecureSSEClient {
    constructor(url, apiKey) {
        this.url = url;
        this.apiKey = apiKey;
        this.eventSource = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    connect() {
        // EventSource doesn't support custom headers in browser
        // Use a URL parameter or create a proxy
        const authenticatedUrl = `${this.url}?api_key=${encodeURIComponent(this.apiKey)}`;
        
        this.eventSource = new EventSource(authenticatedUrl);
        
        this.eventSource.onopen = () => {
            console.log('SSE connection established');
            this.reconnectAttempts = 0;
        };
        
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.handleReconnect();
        };
        
        this.eventSource.addEventListener('auth_error', (event) => {
            console.error('Authentication error:', event.data);
            this.eventSource.close();
        });
    }
    
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                this.eventSource.close();
                this.connect();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
    
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}
```

### 2. Rate Limiting for SSE

```python
import asyncio
from collections import defaultdict
import time

class SSERateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.client_requests = defaultdict(list)
    
    def is_rate_limited(self, client_id):
        """Check if client is rate limited"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.client_requests[client_id] = [
            req_time for req_time in self.client_requests[client_id] 
            if req_time > minute_ago
        ]
        
        # Check current rate
        if len(self.client_requests[client_id]) >= self.requests_per_minute:
            return True
        
        # Add current request
        self.client_requests[client_id].append(now)
        return False
    
    async def emit_if_allowed(self, client_id, event_func):
        """Emit event only if not rate limited"""
        if not self.is_rate_limited(client_id):
            await event_func()
        else:
            print(f"event: rate_limited")
            print(f"data: {json.dumps({'client_id': client_id, 'message': 'Rate limit exceeded'})}")
            print()
```

## Troubleshooting

### Common Issues

#### 1. EventSource Connection Issues
```javascript
// Debug EventSource connections
const eventSource = new EventSource('/events');

eventSource.addEventListener('error', function(e) {
    console.error('EventSource failed:', e);
    console.log('ReadyState:', eventSource.readyState);
    // 0 = CONNECTING, 1 = OPEN, 2 = CLOSED
});
```

#### 2. CORS Issues
```javascript
// Server-side CORS configuration
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Cache-Control');
    next();
});
```

#### 3. Authentication Problems
```bash
# Test SSE endpoint manually
curl -N -H "X-API-Key: your_key" "https://your-server.com/events"
```

### Debug Tools

#### 1. SSE Connection Tester
```html
<script>
function testSSEConnection(url) {
    const es = new EventSource(url);
    
    es.onopen = () => console.log('✅ Connected');
    es.onerror = (e) => console.error('❌ Error:', e);
    es.onmessage = (e) => console.log('📨 Message:', e.data);
    
    // Auto-close after 30 seconds for testing
    setTimeout(() => es.close(), 30000);
}

testSSEConnection('/events');
</script>
```

#### 2. Event Monitor
```python
async def debug_sse_events():
    """Debug SSE event stream"""
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:3001/whoop/events') as response:
            async for line in response.content:
                decoded = line.decode('utf-8').strip()
                if decoded:
                    print(f"RAW: {decoded}")
```

## Security Best Practices

### 1. Authentication
- ✅ **Use HTTPS only** for SSE connections
- ✅ **Validate API keys** on each connection
- ✅ **Implement token refresh** for long-lived connections
- ✅ **Rate limit connections** per client

### 2. Data Security
- ✅ **Sanitize event data** before sending
- ✅ **Don't include sensitive data** in events
- ✅ **Log security events** (failed auth, rate limits)
- ✅ **Monitor connection patterns** for abuse

### 3. Connection Management
- ✅ **Implement connection limits** per client
- ✅ **Clean up resources** on disconnect
- ✅ **Handle client timeouts** gracefully
- ✅ **Use exponential backoff** for reconnections

## Next Steps

SSE provides excellent real-time capabilities for your WHOOP data:

1. **Implement the SSE proxy** to convert your WebSocket server to SSE
2. **Create custom monitoring dashboards** using browser EventSource
3. **Build alert systems** for critical health metrics
4. **Integrate with other tools** using SSE-compatible clients

Your WHOOP MCP server can provide powerful real-time insights through SSE patterns! 📡💪

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create stdio-guide.md for local MCP server usage", "status": "completed", "priority": "high", "id": "17"}, {"content": "Create websocket-guide.md for remote WebSocket connections", "status": "completed", "priority": "high", "id": "18"}, {"content": "Create http-guide.md for REST API usage", "status": "completed", "priority": "high", "id": "19"}, {"content": "Create sse-guide.md for Server-Sent Events configuration", "status": "completed", "priority": "medium", "id": "20"}]
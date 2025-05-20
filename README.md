# WHOOP MCP

A Python API integration for accessing WHOOP fitness data. This tool provides a simple interface to interact with WHOOP's API for retrieving sleep, recovery, workouts, and more.

## Table of Contents
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Authentication](#authentication)
- [Available Tools](#available-tools)
- [Features](#features)
- [Example Usage](#example-usage)
- [Technical Notes](#technical-notes)
- [License](#license)

## Installation

1. Ensure you have Python 3.13+ installed
2. Clone this repository
3. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
   
   Alternatively, using uv:
   ```
   uv pip install -e .
   ```

## Configuration

1. Create a developer account at [WHOOP Developer Portal](https://developer.whoop.com/)
2. Register a new application to get client credentials
3. Create a `.env` file in the root directory with your WHOOP client credentials:
   ```
   WHOOP_CLIENT_ID=your_client_id
   WHOOP_CLIENT_SECRET=your_client_secret
   ```

## Usage

Run the MCP server:
```
uv --directory /path/to/whoop_mcp run whoop_mcp.py
```

Or if you're already in the whoop_mcp directory:
```
uv --directory . run whoop_mcp.py
```

Example configuration in `~/.cursor/mcp.json`:
```json
"whoop": {
  "command": "uv",
  "args": ["--directory /path/to/whoop_mcp run whoop_mcp.py"]
}
```

## Authentication

Authentication with WHOOP is fully automated:

1. Use the `authenticate_with_whoop` tool to start the authentication flow
2. Your browser will automatically open to the WHOOP authorization page
3. Approve the authorization request
4. The callback will be automatically handled, and your token will be saved for future use
5. All API tools will automatically use your saved token

You can check your authentication status with the `check_authentication_status` tool.

## Available Tools

### Authentication Tools

- `authenticate_with_whoop` - Start the WHOOP OAuth2 authentication flow
- `check_authentication_status` - Check if you are authenticated with WHOOP

### Data Tools

- `get_sleep_data` - Get sleep data from WHOOP
- `get_recovery_data` - Get recovery data from WHOOP
- `get_workout_data` - Get workout data from WHOOP
- `get_cycle_data` - Get daily cycle data from WHOOP (includes strain)
- `get_profile_data` - Get user profile data from WHOOP
- `get_body_measurement_data` - Get body measurement data from WHOOP
- `get_sports_mapping` - Get a mapping of sport IDs from your workout history
- `search_whoop_sports` - Search for information about specific sports

## Features

### Dynamic Sport Discovery

The application dynamically discovers sport information:

- Sport IDs are automatically captured from your workout history
- The app builds a mapping of known sport IDs as you use it
- Use `get_sports_mapping` to see all sport IDs found in your workout history
- Use `search_whoop_sports` to search for information about specific sports

### Enhanced Display

Includes human-readable information instead of just IDs:

- Sport names based on discovered sport IDs
- Friendly dates and times
- Categorized strain levels (Light, Moderate, Strenuous, All Out)
- Recovery zones (Red, Yellow, Green)
- Sleep types (Night Sleep vs Nap)

## Example Usage

1. Authenticate with WHOOP:
   ```
   authenticate_with_whoop
   ```

2. Get your recovery data:
   ```
   get_recovery_data
   ```

3. Get workout information:
   ```
   get_workout_data
   ```

4. Get data for a specific date:
   ```
   get_sleep_data --date 2023-05-15
   ```

5. View your sport history:
   ```
   get_sports_mapping
   ```

6. Search for a specific sport:
   ```
   search_whoop_sports --query running
   ```

## Technical Notes

- The app automatically starts a local server on port 8000 to handle OAuth callbacks
- Your access token is saved to `whoop_token.json` for future use
- You can specify dates for data retrieval (format: YYYY-MM-DD)
- The WHOOP API has rate limits (100 requests per minute, 10,000 per day)
- Client credentials are stored securely in a `.env` file (not in the code)
- Sport names are dynamically discovered from your workout history

## License

MIT

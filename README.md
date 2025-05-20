# WHOOP MCP (My Claude Plugin)

This plugin allows you to interact with your WHOOP data through Claude. It supports accessing all data available through WHOOP's API, including sleep, recovery, workouts, and more.

## Setup

1. Make sure you have the following Python packages installed:
   ```
   pip install httpx mcp-python python-dotenv
   ```

2. Create a `.env` file in the root directory with your WHOOP client credentials:
   ```
   WHOOP_CLIENT_ID=your_client_id
   WHOOP_CLIENT_SECRET=your_client_secret
   ```

3. Run the MCP:
   ```
   python whoop_mcp.py
   ```

## Authentication

Authentication with WHOOP is now fully automated:

1. Use the `authenticate_with_whoop` tool to start the authentication flow
2. Your browser will automatically open to the WHOOP authorization page
3. Approve the authorization request
4. The callback will be automatically handled, and your token will be saved for future use
5. All API tools will automatically use your saved token

You can check your authentication status with `check_authentication_status` tool.

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

## Dynamic Sport Discovery

The latest version dynamically discovers sport information:

- Sport IDs are automatically captured from your workout history
- The plugin builds a mapping of known sport IDs as you use it
- Use `get_sports_mapping` to see all sport IDs found in your workout history
- Use `search_whoop_sports` to search for information about specific sports

## Enhanced Display

The latest version includes human-readable information instead of just IDs:

- Sport names based on discovered sport IDs
- Friendly dates and times
- Categorized strain levels (Light, Moderate, Strenuous, All Out)
- Recovery zones (Red, Yellow, Green)
- Sleep types (Night Sleep vs Nap)

## Example Usage

1. Authenticate with WHOOP:
   ```
   I need to connect to my WHOOP account
   ```

2. Get your recovery data:
   ```
   What's my recovery score today?
   ```

3. Get workout information:
   ```
   Show me my latest workout
   ```

4. Get data for a specific date:
   ```
   How was my sleep on 2023-05-15?
   ```

5. View your sport history:
   ```
   What sport types have I done recently?
   ```

6. Search for a specific sport:
   ```
   What's the sport ID for running?
   ```

## Notes

- The MCP automatically starts a local server on port 8000 to handle OAuth callbacks
- Your access token is saved to `whoop_token.json` for future use
- You can specify dates for data retrieval (format: YYYY-MM-DD)
- The WHOOP API has rate limits (100 requests per minute, 10,000 per day)
- Client credentials are stored securely in a `.env` file (not in the code)
- Sport names are dynamically discovered from your workout history

## License

MIT

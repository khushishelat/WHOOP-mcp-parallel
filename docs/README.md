# WHOOP MCP Server

A Model Context Protocol (MCP) server that provides access to WHOOP fitness data through Claude.

## Features

- **OAuth2 Authentication**: Secure authentication with WHOOP API
- **Comprehensive Data Access**: Sleep, recovery, workouts, cycles, profile, and body measurements
- **Time-Aware Summaries**: Intelligent daily summaries with 4 AM rule and bedtime reminders
- **Advanced Analytics**: Workout analysis, sleep quality analysis, recovery load analysis, and training readiness
- **Custom Prompts**: Set custom prompts for personalized interactions
- **Sports Mapping**: Discover and search your workout sports

## Recent Fixes

### Robust Historical Date Handling (Latest)

**Problem**: The daily summary was trying to use the `date` parameter in display calculations before successfully fetching cycle data, causing crashes when no cycle was found for historical dates.

**Solution**: Implemented robust error handling and proper sequencing where cycle data is fetched first, then display information is determined only after successful data retrieval.

**Impact**: 
- Prevents crashes on historical date requests
- Provides clear error messages for invalid dates
- Ensures all display logic has access to valid cycle data
- More robust and reliable for all use cases

**Technical Details**: 
- Added try/catch for date parsing: `datetime.fromisoformat(date).date()`
- Moved display logic after cycle data validation: `if not all([cycle_id, cycle_start])`
- Clear error messages for invalid dates and missing data

### Current-First Strategy

**Problem**: The daily summary was using time-based heuristics (4 AM rule) to guess whether to show current or historical data, which was unreliable and error-prone.

**Solution**: Implemented a "current-first" strategy that always fetches the single most recent cycle from the API and uses its state (active vs completed) to determine what data to display.

**Impact**: 
- Eliminates guesswork and time-based rules
- Provides true live data for active cycles
- Automatically shows most recent completed cycle when no date specified
- 100% alignment with API's data model
- More reliable and accurate daily summaries

**Technical Details**: 
- For current data: `cycle_url = f"{WHOOP_API_BASE}/v2/cycle?limit=1"`
- For historical data: `cycle_url = f"{WHOOP_API_BASE}/v2/cycle?end={next_day}T12:00:00Z&limit=1"`
- Uses `cycle_record.get("end") is None` to detect active cycles

### Physiological Cycle Detection Fix

**Problem**: The daily summary was failing to find the correct physiological cycle by using restrictive calendar day boundaries, causing all subsequent data lookups (sleep, recovery, workouts) to fail.

**Solution**: Implemented intelligent cycle detection that finds the most recent physiological cycle completed by noon the day after the target date, ensuring reliable capture of the main sleep-to-sleep cycle.

**Impact**: 
- Reliably finds the correct physiological cycle for any given date
- Enables accurate sleep, recovery, and workout data retrieval
- Eliminates "no data found" errors in daily summaries
- Provides consistent and accurate daily summaries

**Technical Details**: 
- Old: `cycle_url = f"{WHOOP_API_BASE}/v2/cycle?start={target_date}T00:00:00Z&end={target_date}T23:59:59Z&limit=1"`
- New: `cycle_url = f"{WHOOP_API_BASE}/v2/cycle?end={next_day}T12:00:00Z&limit=1"`

### Cycle Boundary Fix

**Problem**: The daily summary was incorrectly using calendar day boundaries (midnight to midnight) for fetching workout data, which caused workouts to cross physiological day boundaries and result in double-counting.

**Solution**: Modified `get_daily_summary` to use the actual physiological cycle start and end timestamps for workout queries, ensuring perfect data alignment with WHOOP's sleep/wake cycles.

**Impact**: 
- Eliminates double-counting of workouts
- Ensures accurate strain calculations
- Aligns with WHOOP's physiological day structure
- Provides more accurate daily summaries

**Technical Details**: 
- Old: `workout_url = f"{WHOOP_API_BASE}/v2/activity/workout?start={target_date}T00:00:00Z&end={target_date}T23:59:59Z&limit=10"`
- New: `workout_url = f"{WHOOP_API_BASE}/v2/activity/workout?start={cycle_start}&end={cycle_end}&limit=10"`

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see Configuration section)
4. Run the server: `python whoop_mcp.py`

## Configuration

Create a `.env` file with your WHOOP API credentials:

```env
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_REDIRECT_URI=http://localhost:8000/whoop/callback
```

## Usage

The server provides the following tools:

### Authentication
- `authenticate_with_whoop()`: Complete OAuth2 flow
- `check_authentication_status()`: Verify authentication

### Data Retrieval
- `get_sleep_data(date)`: Get sleep data for a specific date
- `get_recovery_data(date)`: Get recovery data for a specific date
- `get_workout_data(workout_id)`: Get workout data
- `get_cycle_data(date)`: Get daily cycle data
- `get_profile_data()`: Get user profile
- `get_body_measurement_data()`: Get body measurements

### Advanced Analytics
- `get_workout_analysis(workout_id)`: Detailed workout analysis
- `get_sleep_quality_analysis(date)`: Sleep quality assessment
- `get_recovery_load_analysis(date)`: Recovery load breakdown
- `get_training_readiness(date)`: Training readiness assessment

### Utilities
- `get_daily_summary(date)`: Time-aware daily summary
- `get_sports_mapping()`: Discover your workout sports
- `search_whoop_sports(query)`: Search for specific sports
- `set_custom_prompt(prompt)`: Set custom conversation prompt
- `get_current_prompt()`: View current custom prompt

## Time-Aware Features

The `get_daily_summary` tool includes intelligent time handling:

- **Current-First Strategy**: Always fetches the most recent cycle and adapts display based on whether it's active or completed
- **Live Cycle Detection**: Automatically detects if you're in an active physiological cycle and shows live data
- **Bedtime Reminders**: Evening summaries include personalized bedtime recommendations
- **Time-Aware Content**: Adapts recommendations based on current time and cycle state

## API Endpoints

The server uses WHOOP's v2 API endpoints:

- Sleep: `/v2/activity/sleep`
- Recovery: `/v2/recovery`
- Workouts: `/v2/activity/workout`
- Cycles: `/v2/cycle`
- Profile: `/v2/user/profile/basic`
- Body Measurements: `/v2/user/measurement/body`

## Testing

Run tests with:

```bash
python -m pytest tests/
```

## Deployment

See `docs/DEPLOYMENT.md` for deployment instructions.

## Security

See `docs/SECURITY.md` for security considerations.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
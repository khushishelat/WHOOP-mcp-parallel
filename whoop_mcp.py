from typing import Any, Dict, List, Optional
import httpx
import json
import os
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from mcp.server.fastmcp import FastMCP
import secrets
import string
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("whoop")

# Constants
WHOOP_API_BASE = "https://api.prod.whoop.com/developer"
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/whoop/callback"

# Dynamic sport mapping - will be populated as we discover sport names
sport_name_cache = {}

# Global variables for auth flow
auth_code = None
auth_error = None
auth_state = None
expected_state = None
auth_completed = threading.Event()
server = None
server_thread = None

# Callback handler for OAuth2 redirect
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code, auth_error, auth_state, auth_completed, expected_state
        
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        query = urlparse(self.path).query
        query_components = parse_qs(query)
        
        if self.path.startswith("/whoop/callback"):
            auth_code = query_components.get("code", [""])[0]
            auth_error = query_components.get("error", [""])[0]
            auth_state = query_components.get("state", [""])[0]
            
            # Check if state matches
            state_valid = auth_state == expected_state
            
            if auth_code and state_valid:
                response = f"""
                <html>
                <head>
                    <title>WHOOP Authorization Successful</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .success {{ color: green; }}
                        .container {{ text-align: center; margin-top: 50px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Authorization Successful!</h1>
                        <p class="success">WHOOP has authorized your application.</p>
                        <p>You can close this window and return to Claude.</p>
                    </div>
                </body>
                </html>
                """
            elif not state_valid and auth_code:
                auth_error = "invalid_state"
                response = f"""
                <html>
                <head>
                    <title>WHOOP Authorization Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .error {{ color: red; }}
                        .container {{ text-align: center; margin-top: 50px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Authorization Failed</h1>
                        <p class="error">Error: State mismatch (possible CSRF attack)</p>
                        <p>Please try again or contact support.</p>
                    </div>
                </body>
                </html>
                """
            else:
                response = f"""
                <html>
                <head>
                    <title>WHOOP Authorization Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .error {{ color: red; }}
                        .container {{ text-align: center; margin-top: 50px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Authorization Failed</h1>
                        <p class="error">Error: {auth_error or "Unknown error"}</p>
                        <p>Please try again or contact support.</p>
                    </div>
                </body>
                </html>
                """
            
            self.wfile.write(response.encode())
            auth_completed.set()  # Signal that auth is completed
        else:
            self.wfile.write(b"404 Not Found")
    
    # Suppress logging
    def log_message(self, format, *args):
        return

def generate_state_parameter(length=32):
    """Generate a secure random state parameter for OAuth."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Helper functions
def start_callback_server():
    """Start the callback server in a separate thread."""
    global server, server_thread
    
    server = HTTPServer(('', 8000), CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print("Callback server started at http://localhost:8000")

def stop_callback_server():
    """Stop the callback server."""
    global server
    if server:
        server.shutdown()
        print("Callback server stopped")

async def make_whoop_request(url: str, headers: Dict[str, str], method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Make a request to the WHOOP API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

# Helper functions for getting human-readable information
async def discover_sport_name(sport_id: int, access_token: str) -> str:
    """Attempt to discover the sport name for a given sport ID by querying workout data."""
    # First check our cache
    if sport_id in sport_name_cache:
        return sport_name_cache[sport_id]
    
    # If not in cache, fetch a larger set of workouts to find matching sport_id
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Request a larger set of workouts to increase chance of finding this sport
    url = f"{WHOOP_API_BASE}/v1/activity/workout?limit=25"
    
    try:
        data = await make_whoop_request(url, headers)
        
        if "error" in data:
            return f"Sport {sport_id}"
        
        # Get all workouts
        records = data.get("records", [])
        
        # Look for workouts with matching sport_id
        for workout in records:
            workout_sport_id = workout.get("sport_id")
            if workout_sport_id is not None:
                # Add to our cache for future lookups
                sport_name_cache[workout_sport_id] = f"Sport {workout_sport_id}"
            
            # If this is the sport_id we're looking for
            if workout_sport_id == sport_id:
                # For now, we still return the generic name since WHOOP API doesn't provide sport names
                return f"Sport {sport_id}"
        
        # If we didn't find it in the recent workouts, return generic name
        return f"Sport {sport_id}"
        
    except Exception as e:
        return f"Sport {sport_id}"

async def get_sport_name_async(sport_id: int, access_token: str) -> str:
    """Asynchronous version of get_sport_name to use in formatters."""
    # First check our cache
    if sport_id in sport_name_cache:
        return sport_name_cache[sport_id]
    
    # If not in cache, try to discover it
    return await discover_sport_name(sport_id, access_token)

def get_sport_name(sport_id: int) -> str:
    """Get the human-readable sport name for a sport ID."""
    return sport_name_cache.get(sport_id, f"Sport {sport_id}")

def format_date(date_str: str, format_str: str = "%A, %b %d, %Y") -> str:
    """Format a date string in a more human-readable format."""
    if date_str == "Unknown":
        return date_str
    
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return date_str

async def get_workout_details(workout_id: int, access_token: str) -> Dict[str, Any]:
    """Get detailed information about a workout by its ID."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v1/activity/workout/{workout_id}"
    
    return await make_whoop_request(url, headers)

async def get_cycle_details(cycle_id: int, access_token: str) -> Dict[str, Any]:
    """Get detailed information about a cycle by its ID."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v1/cycle/{cycle_id}"
    
    return await make_whoop_request(url, headers)

async def get_sleep_details(sleep_id: int, access_token: str) -> Dict[str, Any]:
    """Get detailed information about a sleep session by its ID."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v1/activity/sleep/{sleep_id}"
    
    return await make_whoop_request(url, headers)

def format_sleep_data(data: Dict[str, Any]) -> str:
    """Format sleep data into a readable string."""
    if "error" in data:
        return f"Error fetching sleep data: {data['error']}"
    
    # Handle the paginated response format
    records = data.get("records", [])
    if not records:
        return "No sleep data found for the specified date range."
    
    # Get first record
    sleep = records[0]
    score = sleep.get("score", {}) or {}  # Ensure it's at least an empty dict
    
    # Format times if available
    start_time = sleep.get("start", "Unknown")
    end_time = sleep.get("end", "Unknown")
    
    # Format the date in human-readable format
    sleep_date = format_date(start_time) if start_time != "Unknown" else "Unknown Date"
    
    # Get sleep stages summary - ensure it's at least an empty dict
    stage_summary = score.get("stage_summary", {}) or {}
    
    # Calculate totals in hours/minutes with null safety
    light_sleep = stage_summary.get('total_light_sleep_time_milli', 0) or 0
    deep_sleep = stage_summary.get('total_slow_wave_sleep_time_milli', 0) or 0
    rem_sleep = stage_summary.get('total_rem_sleep_time_milli', 0) or 0
    in_bed_time = stage_summary.get('total_in_bed_time_milli', 0) or 0
    awake_time = stage_summary.get('total_awake_time_milli', 0) or 0
    
    total_sleep_milli = light_sleep + deep_sleep + rem_sleep
    total_sleep_hours = total_sleep_milli / 3600000
    total_in_bed_hours = in_bed_time / 3600000
    
    # Format times in hours and minutes
    sleep_hours = int(total_sleep_hours)
    sleep_minutes = int((total_sleep_hours % 1) * 60)
    
    bed_hours = int(total_in_bed_hours)
    bed_minutes = int((total_in_bed_hours % 1) * 60)
    
    # Create a more human-friendly description for the sleep session
    sleep_description = "Night Sleep" if not sleep.get("nap", False) else "Nap"
    
    return f"""
Sleep: {sleep_description} on {sleep_date}
Sleep Performance: {score.get('sleep_performance_percentage', 0) or 0}%
Sleep Efficiency: {score.get('sleep_efficiency_percentage', 0) or 0:.1f}%
Sleep Duration: {total_sleep_hours:.2f} hours ({sleep_hours}h {sleep_minutes}m)
Time in Bed: {total_in_bed_hours:.2f} hours ({bed_hours}h {bed_minutes}m)
Started: {start_time}
Ended: {end_time}
Light Sleep: {light_sleep/60000:.1f} minutes
Deep Sleep: {deep_sleep/60000:.1f} minutes
REM Sleep: {rem_sleep/60000:.1f} minutes
Awake: {awake_time/60000:.1f} minutes
Sleep Cycles: {stage_summary.get('sleep_cycle_count', 0) or 0}
Disturbances: {stage_summary.get('disturbance_count', 0) or 0}
"""

def format_recovery_data(data: Dict[str, Any]) -> str:
    """Format recovery data into a readable string."""
    if "error" in data:
        return f"Error fetching recovery data: {data['error']}"
    
    # Handle the paginated response format
    records = data.get("records", [])
    if not records:
        return "No recovery data found for the specified date range."
    
    # Get first record
    recovery = records[0]
    score = recovery.get("score", {}) or {}  # Ensure it's at least an empty dict
    
    # Convert temperature if available with null safety
    skin_temp_c = score.get('skin_temp_celsius')
    
    # Handle temperature display based on availability
    if skin_temp_c is not None:
        skin_temp_f = skin_temp_c * 9/5 + 32
        temp_display = f"{skin_temp_c:.1f}°C ({skin_temp_f:.1f}°F)"
    else:
        temp_display = "N/A"
    
    # Get sleep ID for reference
    sleep_id = recovery.get('sleep_id', 'Unknown')
    sleep_description = "Last Sleep Session"
    
    # Get a friendly date for this recovery
    created_at = recovery.get('created_at', 'Unknown')
    recovery_date = format_date(created_at) if created_at != "Unknown" else "Unknown Date"
    
    # Categorize recovery score
    recovery_score = score.get('recovery_score', 0) or 0
    if recovery_score >= 67:
        recovery_category = "Green (High)"
    elif recovery_score >= 34:
        recovery_category = "Yellow (Medium)" 
    else:
        recovery_category = "Red (Low)"
    
    return f"""
Recovery Status: {recovery_category}
Recovery Score: {recovery_score}%
Date: {recovery_date}
Resting Heart Rate: {score.get('resting_heart_rate', 0) or 0} bpm
Heart Rate Variability: {score.get('hrv_rmssd_milli', 0) or 0} ms
SPO2: {score.get('spo2_percentage', 'N/A')}%
Skin Temperature: {temp_display}
Based on: {sleep_description}
"""

async def format_workout_data(data: Dict[str, Any], access_token: str) -> str:
    """Format workout data into a readable string."""
    if "error" in data:
        return f"Error fetching workout data: {data['error']}"
    
    # Handle the paginated response format
    if "records" in data:
        records = data.get("records", [])
        if not records:
            return "No workout data found for the specified criteria."
        workout = records[0]
    else:
        # Single workout response
        workout = data
    
    score = workout.get("score", {}) or {}  # Ensure it's at least an empty dict
    
    # Format times
    start_time = workout.get("start", "Unknown")
    end_time = workout.get("end", "Unknown")
    
    # Format workout date
    workout_date = format_date(start_time) if start_time != "Unknown" else "Unknown Date"
    
    # Get sport name from ID
    sport_id = workout.get('sport_id', 0)
    sport_name = await get_sport_name_async(sport_id, access_token)
    
    # Calculate duration with null safety
    duration_minutes = 0
    if workout.get('end') and workout.get('start'):
        try:
            end_dt = datetime.fromisoformat(workout.get('end').replace('Z', '+00:00'))
            start_dt = datetime.fromisoformat(workout.get('start').replace('Z', '+00:00'))
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
        except (ValueError, TypeError):
            pass
    
    # Convert calories (kilojoules to kcal) with null safety
    kilojoules = score.get('kilojoule', 0) or 0
    calories = kilojoules / 4.184
    
    # Convert distance if available with null safety
    distance_meters = score.get('distance_meter')
    distance_info = ""
    if distance_meters is not None:
        distance_miles = distance_meters / 1609.34
        distance_info = f"Distance: {distance_meters:.2f}m ({distance_miles:.2f} miles)\n"
    
    # Get zone durations with null safety
    zone_data = score.get("zone_duration", {}) or {}
    z1 = zone_data.get('zone_one_milli', 0) or 0
    z2 = zone_data.get('zone_two_milli', 0) or 0
    z3 = zone_data.get('zone_three_milli', 0) or 0
    z4 = zone_data.get('zone_four_milli', 0) or 0
    z5 = zone_data.get('zone_five_milli', 0) or 0
    
    # Format duration in hours and minutes
    dur_hours = int(duration_minutes/60)
    dur_minutes = int(duration_minutes%60)
    
    # Categorize strain level
    strain = score.get('strain', 0) or 0
    if strain >= 18:
        strain_level = "All Out (18.0-21.0)"
    elif strain >= 14:
        strain_level = "Strenuous (14.0-17.9)"
    elif strain >= 10:
        strain_level = "Moderate (10.0-13.9)"
    elif strain >= 4:
        strain_level = "Light (4.0-9.9)"
    else:
        strain_level = "Minimal (0-3.9)"
    
    return f"""
Workout: {sport_name} on {workout_date}
Strain Level: {strain_level}
Strain Score: {strain:.1f}/21.0
Average Heart Rate: {score.get('average_heart_rate', 0) or 0} bpm
Max Heart Rate: {score.get('max_heart_rate', 0) or 0} bpm
Duration: {duration_minutes:.1f} minutes ({dur_hours}h {dur_minutes}m)
Calories Burned: {calories:.0f} kcal ({kilojoules:.0f} kJ)
{distance_info}Started: {start_time}
Ended: {end_time}
Zone 1 (50-60%): {z1/60000:.1f} minutes
Zone 2 (60-70%): {z2/60000:.1f} minutes
Zone 3 (70-80%): {z3/60000:.1f} minutes
Zone 4 (80-90%): {z4/60000:.1f} minutes
Zone 5 (90-100%): {z5/60000:.1f} minutes
"""

async def format_cycle_data(data: Dict[str, Any], access_token: str) -> str:
    """Format cycle data into a readable string."""
    if "error" in data:
        return f"Error fetching cycle data: {data['error']}"
    
    # Handle the paginated response format
    records = data.get("records", [])
    if not records:
        return "No cycle data found for the specified date range."
    
    # Get first record
    cycle = records[0]
    score = cycle.get("score", {}) or {}  # Ensure it's at least an empty dict
    
    # Format dates
    start_time = cycle.get("start", "Unknown")
    end_time = cycle.get("end", "Unknown") or "Current"
    
    # Format date for human readability
    cycle_date = format_date(start_time) if start_time != "Unknown" else "Unknown Date"
    
    # Convert kilojoules to calories with null safety
    kilojoules = score.get('kilojoule', 0) or 0
    calories = kilojoules / 4.184
    
    # Categorize strain level
    strain = score.get('strain', 0) or 0
    if strain >= 18:
        strain_level = "All Out (18.0-21.0)"
    elif strain >= 14:
        strain_level = "Strenuous (14.0-17.9)"
    elif strain >= 10:
        strain_level = "Moderate (10.0-13.9)"
    elif strain >= 4:
        strain_level = "Light (4.0-9.9)"
    else:
        strain_level = "Minimal (0-3.9)"
    
    return f"""
Day: {cycle_date}
Daily Strain Level: {strain_level}
Daily Strain: {strain:.1f}/21.0
Energy Expenditure: {kilojoules:.1f} kJ ({calories:.0f} kcal)
Average Heart Rate: {score.get('average_heart_rate', 0) or 0} bpm
Max Heart Rate: {score.get('max_heart_rate', 0) or 0} bpm
Status: {cycle.get('score_state', 'Unknown')}
"""

def format_profile_data(data: Dict[str, Any]) -> str:
    """Format profile data into a readable string."""
    if "error" in data:
        return f"Error fetching profile data: {data['error']}"
    
    profile = data.get("user", {})
    
    # Format member since date
    member_since = profile.get('createdAt', 'Unknown')
    if member_since != 'Unknown':
        try:
            member_dt = datetime.fromisoformat(member_since.replace('Z', '+00:00'))
            member_since = member_dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            pass
    
    return f"""
Name: {profile.get('firstName', 'Unknown')} {profile.get('lastName', 'Unknown')}
Email: {profile.get('email', 'Unknown')}
Member Since: {member_since}
"""

def format_body_measurement_data(data: Dict[str, Any]) -> str:
    """Format body measurement data into a readable string."""
    if "error" in data:
        return f"Error fetching body measurement data: {data['error']}"
    
    body = data
    
    # Convert metric to imperial with null safety
    height_m = body.get('height_meter', 0) or 0
    height_cm = height_m * 100
    height_inches = height_m * 39.37
    height_feet = int(height_inches / 12)
    height_inches_remainder = round(height_inches % 12)
    
    weight_kg = body.get('weight_kilogram', 0) or 0
    weight_lbs = weight_kg * 2.20462
    
    return f"""
Height: {height_cm:.1f} cm ({height_feet}'{height_inches_remainder}")
Weight: {weight_kg:.1f} kg ({weight_lbs:.1f} lbs)
Max Heart Rate: {body.get('max_heart_rate', 0) or 0} bpm
"""

# Authentication tools
@mcp.tool()
async def authenticate_with_whoop() -> str:
    """Authenticate with WHOOP using OAuth2 flow.
    
    This will open your browser to authorize the app and automatically exchange the code for a token.
    """
    global auth_code, auth_error, auth_state, auth_completed, expected_state
    
    # Reset auth flow state
    auth_code = None
    auth_error = None
    auth_state = None
    auth_completed.clear()
    
    # Generate a secure state parameter
    expected_state = generate_state_parameter(32)
    
    # Start callback server if not already running
    if not server_thread or not server_thread.is_alive():
        start_callback_server()
    
    # Create authorization URL
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement",
        "state": expected_state
    }
    
    auth_url = f"{WHOOP_AUTH_URL}?{urlencode(params)}"
    
    # Open browser for authorization
    webbrowser.open(auth_url)
    
    # Wait for auth to complete (with timeout)
    result = auth_completed.wait(timeout=300)  # 5 minute timeout
    if not result:
        return "Authentication timed out. Please try again."
    
    if auth_error:
        return f"Authentication failed: {auth_error}"
    
    if not auth_code:
        return "No authorization code received. Please try again."
    
    # Verify state parameter
    if auth_state != expected_state:
        return "State parameter mismatch. This could be a CSRF attack. Please try again."
    
    # Exchange code for token
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Use a direct httpx request instead of make_whoop_request for token exchange
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                WHOOP_TOKEN_URL, 
                headers=headers, 
                data=data,  # Use data parameter instead of json
                timeout=30.0
            )
            response.raise_for_status()
            response_data = response.json()
        except httpx.HTTPStatusError as e:
            return f"Error exchanging code for token: HTTP error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            return f"Error exchanging code for token: {str(e)}"
    
    if "error" in response_data:
        return f"Error exchanging code for token: {response_data['error']}"
    
    # Save token to a file for future use
    with open("whoop_token.json", "w") as f:
        json.dump(response_data, f)
    
    return f"""
Successfully authenticated with WHOOP!
Access token saved to whoop_token.json

Token expires in {response_data.get('expires_in', 0)} seconds.
You can now use the other tools to fetch data from WHOOP.
"""

@mcp.tool()
def check_authentication_status() -> str:
    """Check if you are authenticated with WHOOP."""
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
        
        return f"""
You are authenticated with WHOOP.
Access token: {token_data.get('access_token', 'Not found')[:10]}...
Token type: {token_data.get('token_type', 'Not found')}
"""
    except FileNotFoundError:
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    except json.JSONDecodeError:
        return "Error decoding token file. The file might be corrupted. Please authenticate again."

# WHOOP API tools
@mcp.tool()
async def get_sleep_data(date: Optional[str] = None) -> str:
    """Get sleep data from WHOOP.
    
    Args:
        date: Optional date in YYYY-MM-DD format. If not provided, returns most recent data.
    """
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Use the correct endpoint from the API specification
    url = f"{WHOOP_API_BASE}/v1/activity/sleep"
    
    # Convert date to proper query parameters if provided
    if date:
        # Format: 2023-05-20T00:00:00Z
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    return format_sleep_data(data)

@mcp.tool()
async def get_recovery_data(date: Optional[str] = None) -> str:
    """Get recovery data from WHOOP.
    
    Args:
        date: Optional date in YYYY-MM-DD format. If not provided, returns most recent data.
    """
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Use the correct endpoint from the API specification
    url = f"{WHOOP_API_BASE}/v1/recovery"
    
    # Convert date to proper query parameters if provided
    if date:
        # Format: 2023-05-20T00:00:00Z
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    return format_recovery_data(data)

@mcp.tool()
async def get_workout_data(workout_id: Optional[str] = None) -> str:
    """Get workout data from WHOOP.
    
    Args:
        workout_id: Optional workout ID. If not provided, returns most recent workout.
    """
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    if workout_id:
        url = f"{WHOOP_API_BASE}/v1/activity/workout/{workout_id}"
    else:
        url = f"{WHOOP_API_BASE}/v1/activity/workout?limit=1"
    
    data = await make_whoop_request(url, headers)
    return await format_workout_data(data, access_token)

@mcp.tool()
async def get_cycle_data(date: Optional[str] = None) -> str:
    """Get daily cycle data from WHOOP (includes strain).
    
    Args:
        date: Optional date in YYYY-MM-DD format. If not provided, returns most recent data.
    """
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v1/cycle"
    
    # Convert date to proper query parameters if provided
    if date:
        # Format: 2023-05-20T00:00:00Z
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    return await format_cycle_data(data, access_token)

@mcp.tool()
async def get_profile_data() -> str:
    """Get user profile data from WHOOP."""
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v1/user/profile/basic"
    
    data = await make_whoop_request(url, headers)
    return format_profile_data(data)

@mcp.tool()
async def get_body_measurement_data() -> str:
    """Get body measurement data from WHOOP."""
    try:
        with open("whoop_token.json", "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v1/user/measurement/body"
    
    data = await make_whoop_request(url, headers)
    return format_body_measurement_data(data)

@mcp.tool()
async def get_sports_mapping() -> str:
    """Get a mapping of sport IDs to sport names."""
    try:
        # First, make sure we're authenticated
        try:
            with open("whoop_token.json", "r") as f:
                token_data = json.load(f)
                access_token = token_data.get("access_token")
        except (FileNotFoundError, json.JSONDecodeError):
            return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
        
        # Fetch recent workouts to discover sport IDs
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Request a larger set of workouts to discover different sports
        url = f"{WHOOP_API_BASE}/v1/activity/workout?limit=25"
        
        data = await make_whoop_request(url, headers)
        
        if "error" in data:
            return f"Error fetching workout data: {data['error']}"
        
        # Get all workouts
        records = data.get("records", [])
        
        # Extract unique sport IDs from workouts
        for workout in records:
            sport_id = workout.get("sport_id")
            if sport_id is not None and sport_id not in sport_name_cache:
                # Store in our cache
                sport_name_cache[sport_id] = f"Sport {sport_id}"
        
        if not sport_name_cache:
            return "No sports found in your recent workout history. Try working out with different sports to build the mapping."
        
        # Format the output
        result = "WHOOP Sports from your workout history:\n\n"
        for sport_id, sport_name in sorted(sport_name_cache.items()):
            result += f"ID {sport_id}: {sport_name}\n"
        
        result += "\nNote: WHOOP API does not provide human-readable sport names, so we can only identify by ID number."
        return result
        
    except Exception as e:
        return f"Error retrieving sports mapping: {str(e)}"

@mcp.tool()
async def search_whoop_sports(query: str) -> str:
    """Search for information about WHOOP sports.
    
    Args:
        query: Search term to look for information about a specific sport
    """
    # Common sports based on research
    common_sports = {
        0: "Other",
        1: "Running",
        2: "Cycling", 
        3: "Weightlifting",
        4: "Swimming",
        9: "Walking",
        12: "Tennis",
        27: "Basketball",
        33: "Football",
        41: "Soccer",
        45: "HIIT",
        47: "Yoga",
        55: "Pilates",
        71: "Golf",
        103: "Meditation",
        104: "CrossFit",
        124: "Strength Training"
    }
    
    # Look for matches in our cache first
    matches = []
    query_lower = query.lower()
    
    # First check user's known sports from cache
    for sport_id, sport_name in sport_name_cache.items():
        if query_lower in sport_name.lower():
            matches.append((sport_id, sport_name))
    
    # Then check common sports
    for sport_id, sport_name in common_sports.items():
        if sport_id not in sport_name_cache and query_lower in sport_name.lower():
            matches.append((sport_id, sport_name))
    
    # Format the result
    if not matches:
        return f"No matching sports found for '{query}'. Note that WHOOP sport names are based on community knowledge, not official API data."
    
    result = f"WHOOP sports matching '{query}':\n\n"
    for sport_id, sport_name in sorted(matches):
        result += f"ID {sport_id}: {sport_name}\n"
    
    result += "\nNote: These are community-identified sport IDs and may not be 100% accurate."
    return result

if __name__ == "__main__":
    # Initialize auth event
    auth_completed = threading.Event()
    
    # Start callback server for authentication
    start_callback_server()
    
    try:
        # Initialize and run the server
        mcp.run(transport='stdio')
    finally:
        # Stop callback server when MCP exits
        stop_callback_server() 
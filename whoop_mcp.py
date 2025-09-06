from typing import Any, Dict, List, Optional
import httpx
import json
import os
import pytz
import re
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from mcp.server.fastmcp import FastMCP
import secrets
import string
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("whoop")

# Path to store custom prompt (use absolute path for production)
CUSTOM_PROMPT_FILE = os.path.join(os.path.expanduser("~"), ".whoop_custom_prompt.json")

# Constants
WHOOP_API_BASE = "https://api.prod.whoop.com/developer"
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")

# Use different redirect URI for production vs development
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:8000/whoop/callback")

# Token file path (use user's home directory for better compatibility)
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".whoop_token.json")


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

async def refresh_access_token() -> bool:
    """Attempt to refresh the access token using the refresh token."""
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            refresh_token = token_data.get("refresh_token")
            
        if not refresh_token:
            return False
            
        # Use standard OAuth2 refresh flow
        refresh_data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WHOOP_TOKEN_URL,
                headers=headers,
                data=refresh_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                new_token_data = response.json()
                # Save the new token data
                with open(TOKEN_FILE, "w") as f:
                    json.dump(new_token_data, f)
                return True
            else:
                return False
                
    except Exception:
        return False

async def make_whoop_request(url: str, headers: Dict[str, str], method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Make a request to the WHOOP API with proper error handling and automatic token refresh."""
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # If we get a 401, try to refresh the token and retry once
            if e.response.status_code == 401:
                refresh_success = await refresh_access_token()
                if refresh_success:
                    # Update the Authorization header with the new token
                    try:
                        with open(TOKEN_FILE, "r") as f:
                            token_data = json.load(f)
                            new_access_token = token_data.get("access_token")
                        
                        if new_access_token:
                            headers["Authorization"] = f"Bearer {new_access_token}"
                            
                            # Retry the original request with new token
                            if method.upper() == "GET":
                                response = await client.get(url, headers=headers, timeout=30.0)
                            elif method.upper() == "POST":
                                response = await client.post(url, headers=headers, json=data, timeout=30.0)
                            
                            response.raise_for_status()
                            return response.json()
                    except Exception:
                        pass  # Fall through to return original error
            
            # Provide helpful error message for authentication failures
            if e.response.status_code == 401:
                return {"error": f"HTTP error {e.response.status_code}: {e.response.text}. Your WHOOP token has expired. Please use the authenticate_with_whoop tool to re-authenticate."}
            else:
                return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}


def format_date(date_str: str, format_str: str = "%A, %b %d, %Y") -> str:
    """Format a date string in a more human-readable format."""
    if date_str == "Unknown":
        return date_str
    
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return date_str

def format_date_est(date_str: str, include_time: bool = False) -> str:
    """Format a date string in EST timezone with US formatting."""
    if date_str == "Unknown":
        return date_str
    
    try:
        # Parse UTC datetime
        dt_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        # Convert to EST (UTC-5, or UTC-4 during daylight saving time)
        from datetime import timezone, timedelta
        est = timezone(timedelta(hours=-5))  # EST is UTC-5
        dt_est = dt_utc.astimezone(est)
        
        if include_time:
            # Format with time: "Monday, Jan 15, 2025 - 10:30 PM EST"
            date_part = dt_est.strftime("%A, %b %d, %Y")
            time_part = dt_est.strftime("%I:%M %p EST")
            return f"{date_part} - {time_part}"
        else:
            # Format date only: "Monday, Jan 15, 2025"
            return dt_est.strftime("%A, %b %d, %Y")
    except (ValueError, TypeError):
        return date_str

def format_time_duration(minutes: float) -> str:
    """Format time duration in minutes to human-readable format."""
    hours = int(minutes / 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"

async def get_workout_details(workout_id: int, access_token: str) -> Dict[str, Any]:
    """Get detailed information about a workout by its ID."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/activity/workout/{workout_id}"
    
    return await make_whoop_request(url, headers)

async def get_cycle_details(cycle_id: int, access_token: str) -> Dict[str, Any]:
    """Get detailed information about a cycle by its ID."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/cycle/{cycle_id}"
    
    return await make_whoop_request(url, headers)

async def get_sleep_details(sleep_id: int, access_token: str) -> Dict[str, Any]:
    """Get detailed information about a sleep session by its ID."""
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/activity/sleep/{sleep_id}"
    
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
    
    # Format the date in human-readable EST format
    sleep_date = format_date_est(start_time) if start_time != "Unknown" else "Unknown Date"
    
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
    
    # Add enhanced sleep metrics from v2 API
    sleep_latency = stage_summary.get('sleep_latency_milli', 0) or 0
    sleep_efficiency_score = stage_summary.get('sleep_efficiency_score', 0) or 0
    sleep_consistency_score = stage_summary.get('sleep_consistency_score', 0) or 0
    sleep_need_score = stage_summary.get('sleep_need_score', 0) or 0
    
    # Create enhanced sleep quality info
    enhanced_sleep_info = ""
    if sleep_latency > 0:
        enhanced_sleep_info += f"Sleep Latency: {format_time_duration(sleep_latency/60000)}\n"
    if sleep_efficiency_score > 0:
        enhanced_sleep_info += f"Sleep Efficiency Score: {sleep_efficiency_score}%\n"
    if sleep_consistency_score > 0:
        enhanced_sleep_info += f"Sleep Consistency Score: {sleep_consistency_score}%\n"
    if sleep_need_score > 0:
        enhanced_sleep_info += f"Sleep Need Score: {sleep_need_score}%\n"
    
    # Create a more human-friendly description for the sleep session
    sleep_description = "Night Sleep" if not sleep.get("nap", False) else "Nap"
    
    return f"""
Sleep: {sleep_description} on {sleep_date}
Sleep Performance: {score.get('sleep_performance_percentage', 0) or 0}%
Sleep Efficiency: {score.get('sleep_efficiency_percentage', 0) or 0:.1f}%
Sleep Duration: {sleep_hours}h {sleep_minutes}m ({total_sleep_hours:.2f} hours)
Time in Bed: {bed_hours}h {bed_minutes}m ({total_in_bed_hours:.2f} hours)
{enhanced_sleep_info}Started: {format_date_est(start_time, include_time=True) if start_time != 'Unknown' else start_time}
Ended: {format_date_est(end_time, include_time=True) if end_time != 'Unknown' else end_time}
Light Sleep: {format_time_duration(light_sleep/60000)}
Deep Sleep: {format_time_duration(deep_sleep/60000)}
REM Sleep: {format_time_duration(rem_sleep/60000)}
Awake: {format_time_duration(awake_time/60000)}
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
    
    # Convert temperature if available with null safety - prioritize US units
    skin_temp_c = score.get('skin_temp_celsius')
    
    # Handle temperature display based on availability
    if skin_temp_c is not None:
        skin_temp_f = skin_temp_c * 9/5 + 32
        temp_display = f"{skin_temp_f:.1f}°F ({skin_temp_c:.1f}°C)"
    else:
        temp_display = "N/A"
    
    # Get sleep ID for reference
    sleep_id = recovery.get('sleep_id', 'Unknown')
    sleep_description = "Last Sleep Session"
    
    # Get a friendly date for this recovery
    created_at = recovery.get('created_at', 'Unknown')
    recovery_date = format_date_est(created_at) if created_at != "Unknown" else "Unknown Date"
    
    # Categorize recovery score
    recovery_score = score.get('recovery_score', 0) or 0
    if recovery_score >= 67:
        recovery_category = "Green (High)"
    elif recovery_score >= 34:
        recovery_category = "Yellow (Medium)" 
    else:
        recovery_category = "Red (Low)"
    
    # Add enhanced recovery metrics from v2 API
    cardiovascular_load = score.get('cardiovascular_load', 0) or 0
    musculoskeletal_load = score.get('musculoskeletal_load', 0) or 0
    metabolic_load = score.get('metabolic_load', 0) or 0
    recovery_quality_score = score.get('recovery_quality_score', 0) or 0
    recovery_need_score = score.get('recovery_need_score', 0) or 0
    
    # Create enhanced recovery load info
    enhanced_recovery_info = ""
    if cardiovascular_load > 0 or musculoskeletal_load > 0 or metabolic_load > 0:
        enhanced_recovery_info += "Load Analysis:\n"
        if cardiovascular_load > 0:
            enhanced_recovery_info += f"  Cardiovascular Load: {cardiovascular_load}%\n"
        if musculoskeletal_load > 0:
            enhanced_recovery_info += f"  Musculoskeletal Load: {musculoskeletal_load}%\n"
        if metabolic_load > 0:
            enhanced_recovery_info += f"  Metabolic Load: {metabolic_load}%\n"
    
    if recovery_quality_score > 0:
        enhanced_recovery_info += f"Recovery Quality Score: {recovery_quality_score}%\n"
    if recovery_need_score > 0:
        enhanced_recovery_info += f"Recovery Need Score: {recovery_need_score}%\n"
    
    return f"""
Recovery Status: {recovery_category}
Recovery Score: {recovery_score}%
Date: {recovery_date}
Resting Heart Rate: {score.get('resting_heart_rate', 0) or 0} bpm
Heart Rate Variability: {score.get('hrv_rmssd_milli', 0) or 0} ms
SPO2: {score.get('spo2_percentage', 'N/A')}%
Skin Temperature: {temp_display}
{enhanced_recovery_info}Based on: {sleep_description}
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
    workout_date = format_date_est(start_time) if start_time != "Unknown" else "Unknown Date"
    
    # Get sport name from ID (v2 API provides sport_name directly)
    sport_id = workout.get('sport_id', 0)
    sport_name = workout.get('sport_name', f"Sport {sport_id}")
    
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
    
    # Convert distance if available with null safety - prioritize US units
    distance_meters = score.get('distance_meter')
    distance_info = ""
    if distance_meters is not None:
        distance_miles = distance_meters / 1609.34
        # Format with commas for readability
        distance_info = f"Distance: {distance_miles:.2f} miles ({distance_meters:,.0f}m)\n"
    
    # Add elevation data if available - prioritize US units
    altitude_gain_meters = score.get('altitude_gain_meter')
    altitude_change_meters = score.get('altitude_change_meter')
    elevation_info = ""
    if altitude_gain_meters is not None or altitude_change_meters is not None:
        elevation_parts = []
        if altitude_gain_meters is not None:
            elevation_gain_feet = altitude_gain_meters * 3.28084
            elevation_parts.append(f"Elevation Gain: {elevation_gain_feet:.0f}ft ({altitude_gain_meters:.0f}m)")
        if altitude_change_meters is not None:
            elevation_change_feet = altitude_change_meters * 3.28084
            elevation_parts.append(f"Net Elevation: {elevation_change_feet:+.0f}ft ({altitude_change_meters:+.0f}m)")
        elevation_info = "\n".join(elevation_parts) + "\n" if elevation_parts else ""
    
    # Get zone durations with null safety (including Zone 0 for v2)
    zone_data = score.get("zone_duration", {}) or {}
    z0 = zone_data.get('zone_zero_milli', 0) or 0  # Zone 0: Rest/Recovery
    z1 = zone_data.get('zone_one_milli', 0) or 0
    z2 = zone_data.get('zone_two_milli', 0) or 0
    z3 = zone_data.get('zone_three_milli', 0) or 0
    z4 = zone_data.get('zone_four_milli', 0) or 0
    z5 = zone_data.get('zone_five_milli', 0) or 0
    
    # Add data quality indicator
    percent_recorded = score.get('percent_recorded', 100) or 100
    data_quality_info = ""
    if percent_recorded < 100:
        data_quality_info = f"Data Quality: {percent_recorded}% recorded\n"
    
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
Duration: {dur_hours}h {dur_minutes}m ({duration_minutes:.1f} minutes)
Calories Burned: {calories:.0f} kcal ({kilojoules:.0f} kJ)
{distance_info}{elevation_info}{data_quality_info}Started: {format_date_est(start_time, include_time=True) if start_time != 'Unknown' else start_time}
Ended: {format_date_est(end_time, include_time=True) if end_time != 'Unknown' else end_time}
Zone 0 (Rest): {format_time_duration(z0/60000)}
Zone 1 (50-60%): {format_time_duration(z1/60000)}
Zone 2 (60-70%): {format_time_duration(z2/60000)}
Zone 3 (70-80%): {format_time_duration(z3/60000)}
Zone 4 (80-90%): {format_time_duration(z4/60000)}
Zone 5 (90-100%): {format_time_duration(z5/60000)}
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
    cycle_date = format_date_est(start_time) if start_time != "Unknown" else "Unknown Date"
    
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
    
    # WHOOP API v2 structure: data is directly in root, not nested under "user"
    user_id = data.get('user_id', 'Unknown')
    first_name = data.get('first_name', 'Unknown')
    last_name = data.get('last_name', 'Unknown') 
    email = data.get('email', 'Unknown')
    
    return f"""
Name: {first_name} {last_name}
Email: {email}
User ID: {user_id}
"""

def format_body_measurement_data(data: Dict[str, Any]) -> str:
    """Format body measurement data into a readable string."""
    if "error" in data:
        return f"Error fetching body measurement data: {data['error']}"
    
    body = data
    
    # Convert metric to imperial with null safety - prioritize US units
    height_m = body.get('height_meter', 0) or 0
    height_cm = height_m * 100
    height_inches = height_m * 39.37
    height_feet = int(height_inches / 12)
    height_inches_remainder = round(height_inches % 12)
    
    weight_kg = body.get('weight_kilogram', 0) or 0
    weight_lbs = weight_kg * 2.20462
    
    # Add enhanced body metrics from v2 API
    vo2_max = body.get('vo2_max', 0) or 0
    resting_hr = body.get('resting_heart_rate', 0) or 0
    hrv_baseline = body.get('hrv_baseline', 0) or 0
    body_fat_pct = body.get('body_fat_percentage', 0) or 0
    muscle_mass_kg = body.get('muscle_mass_kg', 0) or 0
    bone_mass_kg = body.get('bone_mass_kg', 0) or 0
    hydration_pct = body.get('hydration_percentage', 0) or 0
    
    # Create enhanced metrics info
    enhanced_body_info = ""
    if vo2_max > 0:
        enhanced_body_info += f"VO2 Max: {vo2_max} ml/kg/min\n"
    if resting_hr > 0:
        enhanced_body_info += f"RHR: {resting_hr} bpm\n"
    if hrv_baseline > 0:
        enhanced_body_info += f"HRV Baseline: {hrv_baseline} ms\n"
    
    # Body composition info
    composition_info = ""
    if body_fat_pct > 0 or muscle_mass_kg > 0 or bone_mass_kg > 0 or hydration_pct > 0:
        composition_info += "Body Composition:\n"
        if body_fat_pct > 0:
            composition_info += f"  Body Fat: {body_fat_pct:.1f}%\n"
        if muscle_mass_kg > 0:
            muscle_mass_lbs = muscle_mass_kg * 2.20462
            composition_info += f"  Muscle Mass: {muscle_mass_lbs:.1f} lbs ({muscle_mass_kg:.1f} kg)\n"
        if bone_mass_kg > 0:
            bone_mass_lbs = bone_mass_kg * 2.20462
            composition_info += f"  Bone Mass: {bone_mass_lbs:.1f} lbs ({bone_mass_kg:.1f} kg)\n"
        if hydration_pct > 0:
            composition_info += f"  Hydration: {hydration_pct:.1f}%\n"
    
    return f"""
Height: {height_feet}'{height_inches_remainder}" ({height_cm:.1f} cm)
Weight: {weight_lbs:.1f} lbs ({weight_kg:.1f} kg)
Max Heart Rate: {body.get('max_heart_rate', 0) or 0} bpm
{enhanced_body_info}{composition_info}
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
    
    # Save token to a file for future use (use absolute path for production)
    with open(TOKEN_FILE, "w") as f:
        json.dump(response_data, f)
    
    return f"""
Successfully authenticated with WHOOP!
Access token saved to {TOKEN_FILE}

Token expires in {response_data.get('expires_in', 0)} seconds.
You can now use the other tools to fetch data from WHOOP.
"""

@mcp.tool()
def check_authentication_status() -> str:
    """Check if you are authenticated with WHOOP."""
    try:
        with open(TOKEN_FILE, "r") as f:
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
async def get_sleep_daily(date: Optional[str] = None) -> str:
    """Get detailed sleep data for a single night from WHOOP.
    
    This tool provides comprehensive sleep metrics for one specific night including:
    - Sleep stages (light, deep, REM sleep duration)
    - Sleep efficiency and performance scores
    - Respiratory rate and sleep consistency
    
    For multi-day sleep analysis, use 'get_sleep_trends' instead.
    
    Args:
        date: Optional date in YYYY-MM-DD format (e.g., '2024-01-15'). 
              If not provided, returns most recent sleep data.
              
    Example Usage:
        - get_single_night_sleep_data() → Latest night's sleep
        - get_single_night_sleep_data('2024-01-15') → January 15th sleep data
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Use the correct endpoint from the API specification
    url = f"{WHOOP_API_BASE}/v2/activity/sleep"
    
    # Convert date to proper query parameters if provided
    if date:
        # Format: 2023-05-20T00:00:00Z
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    return format_sleep_data(data)

@mcp.tool()
async def get_recovery_daily(date: Optional[str] = None) -> str:
    """Get detailed recovery metrics for a single day from WHOOP.
    
    This tool provides comprehensive recovery assessment for one specific day including:
    - Recovery score (0-100%)
    - Heart Rate Variability (HRV) in milliseconds
    - Resting Heart Rate (RHR)
    - Skin temperature and SpO2 levels
    
    For multi-day recovery trends, use 'get_recovery_trends' instead.
    
    Args:
        date: Optional date in YYYY-MM-DD format (e.g., '2024-01-15'). 
              If not provided, returns most recent recovery data.
              
    Example Usage:
        - get_single_day_recovery_data() → Today's recovery metrics
        - get_single_day_recovery_data('2024-01-15') → January 15th recovery
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Use the correct endpoint from the API specification
    url = f"{WHOOP_API_BASE}/v2/recovery"
    
    # Convert date to proper query parameters if provided
    if date:
        # Format: 2023-05-20T00:00:00Z
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    return format_recovery_data(data)

@mcp.tool()
async def get_workout_daily(workout_id: Optional[str] = None) -> str:
    """Get detailed data for a single workout from WHOOP.
    
    This tool provides comprehensive metrics for one specific workout including:
    - Workout strain score (0-21)
    - Average and maximum heart rate
    - Calories burned and duration
    - Sport type and workout zones
    
    For multi-day workout analysis, consider using 'get_strain_trends' or the upcoming 'get_workout_trends'.
    
    Args:
        workout_id: Optional workout ID (UUID string). 
                   If not provided, returns most recent workout.
                   
    Example Usage:
        - get_single_workout_data() → Latest workout details
        - get_single_workout_data('abc123-def456') → Specific workout by ID
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    if workout_id:
        url = f"{WHOOP_API_BASE}/v2/activity/workout/{workout_id}"
    else:
        url = f"{WHOOP_API_BASE}/v2/activity/workout?limit=1"
    
    data = await make_whoop_request(url, headers)
    return await format_workout_data(data, access_token)

@mcp.tool()
async def get_cycle_daily(date: Optional[str] = None) -> str:
    """Get daily strain and physiological cycle data for a single day from WHOOP.
    
    This tool provides comprehensive daily metrics including:
    - Daily strain score (cardiovascular load)
    - Average and maximum heart rate for the day
    - Total calories burned (kilojoules converted to kcal)
    - Physiological cycle timing
    
    For multi-day strain analysis, use 'get_strain_trends' instead.
    
    Args:
        date: Optional date in YYYY-MM-DD format (e.g., '2024-01-15'). 
              If not provided, returns most recent cycle data.
              
    Example Usage:
        - get_single_day_strain_data() → Today's strain metrics
        - get_single_day_strain_data('2024-01-15') → January 15th strain data
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/cycle"
    
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
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/user/profile/basic"
    
    data = await make_whoop_request(url, headers)
    return format_profile_data(data)

@mcp.tool()
async def get_body_measurement_data() -> str:
    """Get body measurement data from WHOOP."""
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/user/measurement/body"
    
    data = await make_whoop_request(url, headers)
    return format_body_measurement_data(data)

@mcp.tool()
async def get_sports_mapping() -> str:
    """Get a mapping of sport IDs to sport names from your workout history."""
    try:
        # First, make sure we're authenticated
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                access_token = token_data.get("access_token")
        except (FileNotFoundError, json.JSONDecodeError):
            return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
        
        # Fetch recent workouts to discover sport IDs and names
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Request a larger set of workouts to discover different sports
        url = f"{WHOOP_API_BASE}/v2/activity/workout?limit=25"
        
        data = await make_whoop_request(url, headers)
        
        if "error" in data:
            return f"Error fetching workout data: {data['error']}"
        
        # Get all workouts
        records = data.get("records", [])
        
        # Extract unique sport ID and name pairs from workouts
        sports_mapping = {}
        for workout in records:
            sport_id = workout.get("sport_id")
            sport_name = workout.get("sport_name", f"Sport {sport_id}")
            if sport_id is not None:
                sports_mapping[sport_id] = sport_name
        
        if not sports_mapping:
            return "No sports found in your recent workout history. Try working out with different sports to build the mapping."
        
        # Format the output
        result = "WHOOP Sports from your workout history:\n\n"
        for sport_id, sport_name in sorted(sports_mapping.items()):
            result += f"ID {sport_id}: {sport_name}\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving sports mapping: {str(e)}"

@mcp.tool()
async def get_workout_analysis(workout_id: Optional[str] = None) -> str:
    """Get detailed workout analysis with elevation, zones, and quality metrics.
    
    Args:
        workout_id: Optional workout ID. If not provided, analyzes most recent workout.
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    if workout_id:
        url = f"{WHOOP_API_BASE}/v2/activity/workout/{workout_id}"
    else:
        url = f"{WHOOP_API_BASE}/v2/activity/workout?limit=1"
    
    data = await make_whoop_request(url, headers)
    
    if "error" in data:
        return f"Error fetching workout data: {data['error']}"
    
    # Use the enhanced format_workout_data which now includes all v2 features
    formatted_data = await format_workout_data(data, access_token)
    
    # Add additional analysis
    workout = data.get("records", [data])[0] if "records" in data else data
    score = workout.get("score", {}) or {}
    
    # Zone analysis
    zone_data = score.get("zone_duration", {}) or {}
    total_zones_time = sum([
        zone_data.get('zone_zero_milli', 0) or 0,
        zone_data.get('zone_one_milli', 0) or 0,
        zone_data.get('zone_two_milli', 0) or 0,
        zone_data.get('zone_three_milli', 0) or 0,
        zone_data.get('zone_four_milli', 0) or 0,
        zone_data.get('zone_five_milli', 0) or 0
    ])
    
    analysis = f"""
{formatted_data}
=== WORKOUT ANALYSIS ===
Zone Distribution:
  Zone 0 (Rest): {((zone_data.get('zone_zero_milli', 0) or 0) / total_zones_time * 100):.1f}% of workout
  Zone 1-2 (Aerobic): {(((zone_data.get('zone_one_milli', 0) or 0) + (zone_data.get('zone_two_milli', 0) or 0)) / total_zones_time * 100):.1f}% of workout
  Zone 3-4 (Anaerobic): {(((zone_data.get('zone_three_milli', 0) or 0) + (zone_data.get('zone_four_milli', 0) or 0)) / total_zones_time * 100):.1f}% of workout
  Zone 5 (Max Effort): {((zone_data.get('zone_five_milli', 0) or 0) / total_zones_time * 100):.1f}% of workout

Training Focus: {"High Intensity" if ((zone_data.get('zone_four_milli', 0) or 0) + (zone_data.get('zone_five_milli', 0) or 0)) / total_zones_time > 0.3 else "Moderate Intensity" if ((zone_data.get('zone_three_milli', 0) or 0) + (zone_data.get('zone_four_milli', 0) or 0)) / total_zones_time > 0.3 else "Low Intensity/Recovery"}
"""
    
    return analysis

@mcp.tool()
async def get_sleep_quality_analysis(date: Optional[str] = None) -> str:
    """Get comprehensive sleep quality analysis with efficiency and consistency scores.
    
    Args:
        date: Optional date in YYYY-MM-DD format. If not provided, analyzes most recent sleep.
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/activity/sleep"
    
    if date:
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    
    if "error" in data:
        return f"Error fetching sleep data: {data['error']}"
    
    # Use the enhanced format_sleep_data which now includes all v2 features
    formatted_data = format_sleep_data(data)
    
    # Add additional sleep analysis
    records = data.get("records", [])
    if not records:
        return "No sleep data found for analysis."
    
    sleep = records[0]
    score = sleep.get("score", {}) or {}
    stage_summary = score.get("stage_summary", {}) or {}
    
    # Calculate sleep stage percentages
    light_sleep = stage_summary.get('total_light_sleep_time_milli', 0) or 0
    deep_sleep = stage_summary.get('total_slow_wave_sleep_time_milli', 0) or 0
    rem_sleep = stage_summary.get('total_rem_sleep_time_milli', 0) or 0
    total_sleep = light_sleep + deep_sleep + rem_sleep
    
    # Sleep quality assessment
    sleep_efficiency = score.get('sleep_efficiency_percentage', 0) or 0
    sleep_latency = stage_summary.get('sleep_latency_milli', 0) or 0
    disturbances = stage_summary.get('disturbance_count', 0) or 0
    
    analysis = f"""
{formatted_data}
=== SLEEP QUALITY ANALYSIS ===
Sleep Stage Distribution:
  Light Sleep: {(light_sleep / total_sleep * 100):.1f}% (Optimal: 45-55%)
  Deep Sleep: {(deep_sleep / total_sleep * 100):.1f}% (Optimal: 15-20%)
  REM Sleep: {(rem_sleep / total_sleep * 100):.1f}% (Optimal: 20-25%)

Sleep Quality Assessment:
  Overall Quality: {"Excellent" if sleep_efficiency > 85 else "Good" if sleep_efficiency > 75 else "Fair" if sleep_efficiency > 65 else "Poor"}
  Sleep Latency: {"Fast" if sleep_latency < 900000 else "Normal" if sleep_latency < 1800000 else "Slow"} ({format_time_duration(sleep_latency/60000)})
  Sleep Continuity: {"Excellent" if disturbances < 2 else "Good" if disturbances < 4 else "Fair" if disturbances < 6 else "Poor"} ({disturbances} disturbances)

Recommendations:
{"• Great sleep quality! Maintain current sleep habits." if sleep_efficiency > 85 and disturbances < 3 else "• Consider improving sleep environment to reduce disturbances." if disturbances > 4 else "• Focus on consistent bedtime routine to improve sleep latency." if sleep_latency > 1800000 else "• Consider sleep hygiene improvements for better efficiency."}
"""
    
    return analysis

@mcp.tool()
async def get_recovery_load_analysis(date: Optional[str] = None) -> str:
    """Get detailed recovery load analysis with cardiovascular, musculoskeletal, and metabolic stress.
    
    Args:
        date: Optional date in YYYY-MM-DD format. If not provided, analyzes most recent recovery data.
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    url = f"{WHOOP_API_BASE}/v2/recovery"
    
    if date:
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        url += f"?start={start_date}&end={end_date}&limit=1"
    
    data = await make_whoop_request(url, headers)
    
    if "error" in data:
        return f"Error fetching recovery data: {data['error']}"
    
    # Use the enhanced format_recovery_data which now includes all v2 features
    formatted_data = format_recovery_data(data)
    
    # Add additional recovery load analysis
    records = data.get("records", [])
    if not records:
        return "No recovery data found for analysis."
    
    recovery = records[0]
    score = recovery.get("score", {}) or {}
    
    # Load metrics
    cardio_load = score.get('cardiovascular_load', 0) or 0
    muscle_load = score.get('musculoskeletal_load', 0) or 0
    metabolic_load = score.get('metabolic_load', 0) or 0
    recovery_score = score.get('recovery_score', 0) or 0
    
    # HRV and RHR analysis
    hrv = score.get('hrv_rmssd_milli', 0) or 0
    rhr = score.get('resting_heart_rate', 0) or 0
    
    analysis = f"""
{formatted_data}
=== RECOVERY LOAD ANALYSIS ===
System Load Breakdown:
  Cardiovascular System: {"High" if cardio_load > 70 else "Moderate" if cardio_load > 40 else "Low"} Load ({cardio_load}%)
  Musculoskeletal System: {"High" if muscle_load > 70 else "Moderate" if muscle_load > 40 else "Low"} Load ({muscle_load}%)
  Metabolic System: {"High" if metabolic_load > 70 else "Moderate" if metabolic_load > 40 else "Low"} Load ({metabolic_load}%)

Recovery Readiness:
  Overall Status: {"Ready" if recovery_score > 67 else "Caution" if recovery_score > 34 else "Not Ready"}
  Primary Limiting Factor: {"Cardiovascular" if cardio_load == max(cardio_load, muscle_load, metabolic_load) else "Musculoskeletal" if muscle_load == max(cardio_load, muscle_load, metabolic_load) else "Metabolic"}
  
Training Recommendations:
{"• Full intensity training recommended" if recovery_score > 67 else "• Light to moderate training recommended" if recovery_score > 50 else "• Recovery day recommended - focus on sleep and nutrition" if recovery_score > 34 else "• Active recovery only - prioritize rest"}

Recovery Strategies:
{"• Focus on cardiovascular recovery (gentle aerobic activity, breathing exercises)" if cardio_load > max(muscle_load, metabolic_load) else "• Focus on musculoskeletal recovery (stretching, massage, gentle movement)" if muscle_load > max(cardio_load, metabolic_load) else "• Focus on metabolic recovery (nutrition, hydration, adequate sleep)"}
"""
    
    return analysis

@mcp.tool()
async def get_training_readiness(date: Optional[str] = None) -> str:
    """Get comprehensive training readiness assessment combining recovery, sleep, and strain data.
    
    This advanced tool provides intelligent training recommendations by analyzing:
    - Recovery score and cardiovascular readiness
    - Sleep quality impact on performance capacity
    - Recent strain load and fatigue levels
    - Personalized training intensity recommendations
    - Risk assessment for overtraining
    
    Perfect for making informed decisions about workout intensity and training planning.
    
    Args:
        date: Optional date in YYYY-MM-DD format (e.g., '2024-01-15'). 
              If not provided, analyzes most recent data for current readiness.
              
    Example Usage:
        - get_comprehensive_training_readiness() → Current training readiness
        - get_comprehensive_training_readiness('2024-01-15') → January 15th readiness
    """
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Fetch recovery, sleep, and cycle data
    recovery_url = f"{WHOOP_API_BASE}/v2/recovery"
    sleep_url = f"{WHOOP_API_BASE}/v2/activity/sleep"
    cycle_url = f"{WHOOP_API_BASE}/v2/cycle"
    
    if date:
        start_date = f"{date}T00:00:00Z"
        end_date = f"{date}T23:59:59Z"
        recovery_url += f"?start={start_date}&end={end_date}&limit=1"
        sleep_url += f"?start={start_date}&end={end_date}&limit=1"
        cycle_url += f"?start={start_date}&end={end_date}&limit=1"
    
    # Fetch all data
    recovery_data = await make_whoop_request(recovery_url, headers)
    sleep_data = await make_whoop_request(sleep_url, headers)
    cycle_data = await make_whoop_request(cycle_url, headers)
    
    # Check for errors
    if "error" in recovery_data:
        return f"Error fetching recovery data: {recovery_data['error']}"
    if "error" in sleep_data:
        return f"Error fetching sleep data: {sleep_data['error']}"
    if "error" in cycle_data:
        return f"Error fetching cycle data: {cycle_data['error']}"
    
    # Extract data
    recovery_records = recovery_data.get("records", [])
    sleep_records = sleep_data.get("records", [])
    cycle_records = cycle_data.get("records", [])
    
    if not recovery_records or not sleep_records or not cycle_records:
        return "Insufficient data for training readiness assessment."
    
    recovery = recovery_records[0]
    sleep = sleep_records[0]
    cycle = cycle_records[0]
    
    # Extract key metrics
    recovery_score = recovery.get("score", {}).get('recovery_score', 0) or 0
    sleep_performance = sleep.get("score", {}).get('sleep_performance_percentage', 0) or 0
    sleep_efficiency = sleep.get("score", {}).get('sleep_efficiency_percentage', 0) or 0
    strain = cycle.get("score", {}).get('strain', 0) or 0
    
    # Calculate readiness score (weighted average)
    readiness_score = (recovery_score * 0.4 + sleep_performance * 0.3 + sleep_efficiency * 0.2 + min(100, (21 - strain) * 4.76) * 0.1)
    
    # Determine readiness level
    if readiness_score >= 80:
        readiness_level = "Excellent"
        training_advice = "Perfect day for high-intensity training or competition"
    elif readiness_score >= 65:
        readiness_level = "Good"
        training_advice = "Good for moderate to high-intensity training"
    elif readiness_score >= 50:
        readiness_level = "Fair"
        training_advice = "Light to moderate training recommended"
    else:
        readiness_level = "Poor"
        training_advice = "Recovery day recommended - focus on rest and recovery"
    
    analysis = f"""
=== TRAINING READINESS ASSESSMENT ===
Date: {format_date_est(recovery.get('created_at', 'Unknown')) if recovery.get('created_at') != 'Unknown' else 'Today'}

Overall Readiness: {readiness_level} ({readiness_score:.1f}/100)

Key Metrics:
  Recovery Score: {recovery_score}% (Weight: 40%)
  Sleep Performance: {sleep_performance}% (Weight: 30%)
  Sleep Efficiency: {sleep_efficiency:.1f}% (Weight: 20%)
  Previous Day Strain: {strain:.1f}/21 (Weight: 10%)

Training Recommendation: {training_advice}

Detailed Breakdown:
  {"🟢" if recovery_score > 67 else "🟡" if recovery_score > 34 else "🔴"} Recovery: {"Ready" if recovery_score > 67 else "Caution" if recovery_score > 34 else "Not Ready"}
  {"🟢" if sleep_performance > 80 else "🟡" if sleep_performance > 60 else "🔴"} Sleep Quality: {"Excellent" if sleep_performance > 80 else "Good" if sleep_performance > 60 else "Poor"}
  {"🟢" if strain < 15 else "🟡" if strain < 18 else "🔴"} Strain Load: {"Low" if strain < 15 else "Moderate" if strain < 18 else "High"}

Focus Areas:
{"• All systems optimal - maintain current routines" if readiness_score >= 80 else "• Prioritize sleep quality for better readiness" if sleep_performance < 70 else "• Focus on recovery strategies to improve readiness" if recovery_score < 60 else "• Monitor training load to prevent overreaching"}
"""
    
    return analysis

@mcp.tool()
async def search_whoop_sports(query: str) -> str:
    """Search for sports in your WHOOP workout history.
    
    Args:
        query: Search term to look for information about a specific sport
    """
    try:
        # First, make sure we're authenticated
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
                access_token = token_data.get("access_token")
        except (FileNotFoundError, json.JSONDecodeError):
            return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
        
        # Fetch recent workouts to get real sport data
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Request a larger set of workouts to search through
        url = f"{WHOOP_API_BASE}/v2/activity/workout?limit=50"
        
        data = await make_whoop_request(url, headers)
        
        if "error" in data:
            return f"Error fetching workout data: {data['error']}"
        
        # Get all workouts
        records = data.get("records", [])
        
        # Extract unique sport ID and name pairs from workouts
        sports_mapping = {}
        for workout in records:
            sport_id = workout.get("sport_id")
            sport_name = workout.get("sport_name", f"Sport {sport_id}")
            if sport_id is not None:
                sports_mapping[sport_id] = sport_name
        
        # Search for matches
        matches = []
        query_lower = query.lower()
        
        for sport_id, sport_name in sports_mapping.items():
            if query_lower in sport_name.lower():
                matches.append((sport_id, sport_name))
        
        # Format the result
        if not matches:
            return f"No matching sports found for '{query}' in your workout history."
        
        result = f"WHOOP sports matching '{query}' from your workout history:\n\n"
        for sport_id, sport_name in sorted(matches):
            result += f"ID {sport_id}: {sport_name}\n"
        
        return result
        
    except Exception as e:
        return f"Error searching sports: {str(e)}"

def resolve_date_input(date_input: Optional[str]) -> Optional[str]:
    """Resolve relative date terms like 'yesterday', 'today' to YYYY-MM-DD format.
    
    Args:
        date_input: User input like 'yesterday', 'today', or specific date
        
    Returns:
        YYYY-MM-DD format date string or None for 'today'/current cycle
    """
    if not date_input or date_input.lower() in ['today']:
        return None  # Use current cycle
    
    import pytz
    user_timezone = pytz.timezone('America/New_York')
    now_in_timezone = datetime.now(user_timezone)
    
    if date_input.lower() == 'yesterday':
        yesterday = now_in_timezone.date() - timedelta(days=1)
        return yesterday.strftime('%Y-%m-%d')
    
    # If it's already in YYYY-MM-DD format or other format, return as-is
    return date_input

@mcp.tool()
async def get_daily_summary(date: Optional[str] = None) -> str:
    """Get a comprehensive daily health summary combining all WHOOP metrics with smart recommendations.
    
    This intelligent tool provides a complete daily overview including:
    - Recovery status and readiness for training
    - Sleep quality and efficiency analysis
    - Strain and training load assessment
    - Time-aware recommendations (adapts to current time of day)
    - Actionable insights based on your personal patterns
    
    This tool synthesizes data from multiple sources to provide holistic health insights.
    Perfect for daily check-ins and understanding your overall wellness status.
    
    Args:
        date: Optional date in YYYY-MM-DD format (e.g., '2024-01-15'), or relative terms like 'yesterday', 'today'. 
              If not provided, uses current cycle as fallback with real-time insights.
              
    Example Usage:
        - get_daily_summary() → Today's complete health overview
        - get_daily_summary('2024-01-15') → January 15th summary
        - get_daily_summary('yesterday') → Yesterday's analysis
    
    Technical Features:
        - Composition Architecture: Uses existing working tools as building blocks
        - Current Cycle Priority: Always prioritizes your current physiological cycle as "today"
        - Intelligent Fallback: When historical data isn't available, falls back to current cycle
        - Time-Aware Content: Adapts recommendations based on current time (daytime vs evening)
    """
    # Resolve date input (handles 'yesterday', 'today', etc.)
    resolved_date = resolve_date_input(date)
    
    # Use existing working tools to get data (composition approach)
    try:
        # Get all data using proven working tools
        cycle_result = await get_cycle_daily(resolved_date)
        sleep_result = await get_sleep_daily(resolved_date)
        recovery_result = await get_recovery_daily(resolved_date)
        workout_result = await get_workout_daily()  # Recent workouts
        
        # If any core data is missing, try without date (fallback to current cycle)
        if not resolved_date and any("error" in str(result) or "Could not" in str(result) for result in [cycle_result, sleep_result, recovery_result]):
            # Already trying current cycle, return what we have
            pass
        elif resolved_date and any("error" in str(result) or "Could not" in str(result) for result in [cycle_result, sleep_result, recovery_result]):
            # Historical date failed, try current cycle as fallback
            cycle_result = await get_cycle_daily()
            sleep_result = await get_sleep_daily()
            recovery_result = await get_recovery_daily()
            resolved_date = None  # Mark as current cycle
        
        # Create comprehensive summary from individual tool results
        return format_comprehensive_summary(cycle_result, sleep_result, recovery_result, workout_result, resolved_date)
        
    except Exception as e:
        return f"Error generating daily summary: {str(e)}. Please ensure you are authenticated with WHOOP."

def calculate_date_range(days: int, end_date: Optional[str] = None) -> tuple[str, str]:
    """Calculate start and end dates for trend analysis."""
    if end_date:
        end_dt = datetime.fromisoformat(end_date).date()
    else:
        # Use current date in EST timezone
        import pytz
        user_timezone = pytz.timezone('America/New_York')
        end_dt = datetime.now(user_timezone).date()
    
    start_dt = end_dt - timedelta(days=days-1)  # Include end date in range
    
    return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')

async def fetch_multi_day_data(endpoint: str, days: int, access_token: str, end_date: Optional[str] = None) -> list:
    """Fetch multiple days of data from WHOOP API with pagination support."""
    start_date, end_date_final = calculate_date_range(days, end_date)
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Build URL with date range
    start_iso = f"{start_date}T00:00:00Z"
    end_iso = f"{end_date_final}T23:59:59Z"
    url = f"{WHOOP_API_BASE}/v2/{endpoint}?start={start_iso}&end={end_iso}&limit=25"
    
    all_records = []
    next_token = None
    
    while True:
        current_url = url
        if next_token:
            current_url += f"&nextToken={next_token}"
        
        data = await make_whoop_request(current_url, headers)
        
        if "error" in data:
            break
        
        records = data.get("records", [])
        all_records.extend(records)
        
        # Check for pagination
        next_token = data.get("nextToken")
        if not next_token:
            break
    
    return all_records

def generate_ascii_chart(values: list, title: str, width: int = 50) -> str:
    """Generate a simple ASCII chart for trend visualization."""
    if not values or len(values) < 2:
        return f"{title}\nInsufficient data for chart visualization."
    
    # Normalize values to chart width
    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val
    
    if val_range == 0:  # All values are the same
        chart_values = [width // 2] * len(values)
    else:
        chart_values = [int((v - min_val) / val_range * (width - 1)) for v in values]
    
    # Create chart
    chart_lines = []
    
    # Header
    chart_lines.append(f"{title}")
    chart_lines.append("=" * len(title))
    
    # Y-axis labels and chart
    chart_height = 10
    for row in range(chart_height, -1, -1):
        line = ""
        y_threshold = row * (width - 1) / chart_height
        
        # Y-axis label
        if row == chart_height:
            line += f"{max_val:6.1f} |"
        elif row == 0:
            line += f"{min_val:6.1f} |"
        elif row == chart_height // 2:
            line += f"{(max_val + min_val) / 2:6.1f} |"
        else:
            line += "       |"
        
        # Chart data
        for i, chart_val in enumerate(chart_values):
            if chart_val >= y_threshold - 1 and chart_val <= y_threshold + 1:
                line += "●"
            elif i > 0 and ((chart_values[i-1] <= y_threshold <= chart_val) or 
                          (chart_val <= y_threshold <= chart_values[i-1])):
                line += "●"
            else:
                line += " "
        
        chart_lines.append(line)
    
    # X-axis
    x_axis = "       +" + "-" * width
    chart_lines.append(x_axis)
    
    # Add trend indication
    if len(values) > 1:
        trend = (values[-1] - values[0]) / (len(values) - 1)
        if abs(trend) < 0.01:
            trend_str = "Stable"
        elif trend > 0:
            trend_str = f"↗ Improving (+{trend:.2f}/day)"
        else:
            trend_str = f"↘ Declining ({trend:.2f}/day)"
        
        chart_lines.append(f"Trend: {trend_str}")
    
    return "\n".join(chart_lines)

def calculate_trend_statistics(values: list) -> dict:
    """Calculate statistical metrics for trend analysis."""
    if not values:
        return {"error": "No data provided"}
    
    # Filter out None values
    clean_values = [v for v in values if v is not None]
    
    if not clean_values:
        return {"error": "No valid data points"}
    
    count = len(clean_values)
    average = sum(clean_values) / count
    minimum = min(clean_values)
    maximum = max(clean_values)
    
    # Calculate trend (simple linear trend)
    if count > 1:
        # Simple trend calculation: (last_value - first_value) / period
        trend = (clean_values[-1] - clean_values[0]) / (count - 1)
        
        # Trend direction
        if abs(trend) < 0.1:
            trend_direction = "stable"
        elif trend > 0:
            trend_direction = "improving"
        else:
            trend_direction = "declining"
    else:
        trend = 0
        trend_direction = "insufficient_data"
    
    # Calculate variance for stability metric
    if count > 1:
        variance = sum((x - average) ** 2 for x in clean_values) / count
        stability = "high" if variance < (average * 0.1) ** 2 else "moderate" if variance < (average * 0.2) ** 2 else "low"
    else:
        variance = 0
        stability = "unknown"
    
    return {
        "count": count,
        "average": round(average, 2),
        "minimum": minimum,
        "maximum": maximum,
        "trend": round(trend, 3),
        "trend_direction": trend_direction,
        "variance": round(variance, 2),
        "stability": stability
    }

def format_metric_value(value: str, metric_type: str) -> str:
    """Format metric values for better readability."""
    if not value or value == 'Unknown':
        return value
    
    try:
        # Convert to float first to handle decimal values
        float_val = float(value)
        
        if metric_type in ['hrv', 'hrv_alt']:
            # HRV: Convert from decimal seconds to milliseconds if needed
            if float_val < 1:  # Likely in seconds, convert to ms
                return str(int(float_val * 1000))
            else:  # Already in ms
                return str(int(float_val))
        elif metric_type in ['rhr', 'avg_hr', 'max_hr']:
            # Heart rates: always whole numbers
            return str(int(float_val))
        elif metric_type in ['sleep_efficiency', 'sleep_performance']:
            # Percentages: one decimal place
            return f"{float_val:.1f}"
        elif metric_type in ['strain', 'strain_score']:
            # Strain: one decimal place
            return f"{float_val:.1f}"
        else:
            # Default: return as-is
            return value
    except (ValueError, TypeError):
        return value

def extract_key_metrics(text: str) -> dict:
    """Extract key metrics from formatted tool output strings."""
    metrics = {}
    
    # Extract numeric values with regex patterns
    patterns = {
        'strain': r'Daily Strain: ([\d.]+)',
        'strain_score': r'Strain Score: ([\d.]+)',
        'recovery_score': r'Recovery Score: (\d+)%',
        'recovery_status': r'Recovery Score: \d+% \(([^)]+)\)',
        'sleep_duration': r'Duration: ([\dh ]+m)',
        'sleep_efficiency': r'Efficiency: ([\d.]+)%',
        'sleep_performance': r'Performance: ([\d.]+)%',
        'hrv': r'HRV: ([\d.]+)ms',
        'hrv_alt': r'Heart Rate Variability: ([\d.]+) ms',
        'rhr': r'Resting Heart Rate: (\d+) bpm',
        'avg_hr': r'Average Heart Rate: (\d+) bpm',
        'max_hr': r'Max Heart Rate: (\d+) bpm',
        'calories': r'(\d+) kcal',
        'workouts_count': r'(\d+) workout',
        'sport_name': r'Workout: ([^\\n]+) on',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            raw_value = match.group(1)
            # Format the value based on its type
            metrics[key] = format_metric_value(raw_value, key)
    
    return metrics

def format_comprehensive_summary(cycle_result: str, sleep_result: str, recovery_result: str, workout_result: str, resolved_date: Optional[str]) -> str:
    """Create a comprehensive summary by combining results from individual working tools."""
    
    # Set up time-aware context
    user_timezone = pytz.timezone('America/New_York')
    current_time = datetime.now(user_timezone)
    current_time_str = current_time.strftime("%I:%M %p")
    # Fix time logic: evening = 6 PM to 11 PM, night = 11 PM to 6 AM, day = 6 AM to 6 PM
    current_hour = current_time.hour
    if 6 <= current_hour < 18:
        time_period = "day"
        time_emoji = "☀️ DAYTIME"
    elif 18 <= current_hour < 23:
        time_period = "evening"
        time_emoji = "🌙 EVENING"
    else:
        time_period = "night"
        time_emoji = "🌙 NIGHTTIME"
    
    # Determine display context
    if resolved_date:
        display_title = f"Summary for {resolved_date}"
        context_note = f"📅 **HISTORICAL DATA**: Showing data for {resolved_date}"
    else:
        display_title = "Today's Summary"
        context_note = f"🟢 **CURRENT CYCLE**: Your most recent physiological cycle\nCurrent Time: {current_time_str} EST"
    
    # Extract key metrics from each tool result
    cycle_metrics = extract_key_metrics(cycle_result)
    sleep_metrics = extract_key_metrics(sleep_result)
    recovery_metrics = extract_key_metrics(recovery_result)
    workout_metrics = extract_key_metrics(workout_result)
    
    # Build comprehensive summary
    summary = f"""
{'='*60}
📅 {display_title}
{'='*60}

{context_note}

"""
    
    # SLEEP SECTION
    summary += "😴 SLEEP DATA\n"
    if "error" in sleep_result.lower() or "no sleep data" in sleep_result.lower():
        summary += "Sleep data not available for this period.\n\n"
    else:
        duration = sleep_metrics.get('sleep_duration', 'Unknown')
        efficiency = sleep_metrics.get('sleep_efficiency', 'Unknown')
        performance = sleep_metrics.get('sleep_performance', 'Unknown')
        
        summary += f"Duration: {duration}\n"
        if efficiency != 'Unknown':
            formatted_efficiency = format_metric_value(efficiency, 'sleep_efficiency')
            summary += f"Efficiency: {formatted_efficiency}%\n"
        if performance != 'Unknown':
            formatted_performance = format_metric_value(performance, 'sleep_performance')
            summary += f"Performance: {formatted_performance}%\n"
        
        # Sleep quality assessment
        if efficiency != 'Unknown':
            try:
                eff_val = float(efficiency)
                quality = "Excellent" if eff_val > 85 else "Good" if eff_val > 75 else "Fair" if eff_val > 65 else "Poor"
                summary += f"Quality: {quality}\n"
            except:
                pass
        summary += "\n"
    
    # RECOVERY SECTION
    summary += "💚 RECOVERY\n"
    if "error" in recovery_result.lower() or "no recovery data" in recovery_result.lower():
        summary += "Recovery data not available for this period.\n\n"
    else:
        recovery_score = recovery_metrics.get('recovery_score', 'Unknown')
        recovery_status = recovery_metrics.get('recovery_status', 'Unknown')
        hrv = recovery_metrics.get('hrv', recovery_metrics.get('hrv_alt', 'Unknown'))
        rhr = recovery_metrics.get('rhr', 'Unknown')
        
        if recovery_score != 'Unknown':
            try:
                score_val = int(recovery_score)
                if score_val >= 67:
                    heart_emoji = "💚"  # Green heart for good recovery
                    status = "Ready"
                elif score_val >= 34:
                    heart_emoji = "💛"  # Yellow heart for moderate recovery
                    status = "Caution"
                else:
                    heart_emoji = "❤️"  # Red heart for low recovery
                    status = "Not Ready"
                
                if recovery_status != 'Unknown':
                    summary += f"Recovery Score: {heart_emoji} {recovery_score}% ({recovery_status})\n"
                else:
                    summary += f"Recovery Score: {heart_emoji} {recovery_score}% ({status})\n"
            except:
                summary += f"Recovery Score: {recovery_score}%\n"
        elif "Recovery Status:" in recovery_result:
            # Extract status from different format
            import re
            status_match = re.search(r'Recovery Status: ([^\n]+)', recovery_result)
            if status_match:
                summary += f"Recovery Status: {status_match.group(1).strip()}\n"
        
        if hrv != 'Unknown':
            # Format HRV as a clean number
            formatted_hrv = format_metric_value(hrv, 'hrv')
            summary += f"HRV: {formatted_hrv}ms\n"
        if rhr != 'Unknown':
            # Format RHR as whole number
            formatted_rhr = format_metric_value(rhr, 'rhr')
            summary += f"Resting Heart Rate: {formatted_rhr} bpm\n"
        
        # If we still don't have data, show what we can extract
        if recovery_score == 'Unknown' and hrv == 'Unknown' and rhr == 'Unknown':
            # Try to extract any recovery info from the raw text
            recovery_lines = [line.strip() for line in recovery_result.split('\n') if line.strip() and not line.startswith('=')]
            if recovery_lines:
                summary += "Available recovery data:\n"
                for line in recovery_lines[:3]:  # Show first 3 meaningful lines
                    if line and not line.startswith('Recovery') and not line.startswith('Error'):
                        summary += f"{line}\n"
        
        summary += "\n"
    
    # STRAIN SECTION
    summary += "🔥 STRAIN\n"
    if "error" in cycle_result.lower() or "no cycle data" in cycle_result.lower():
        summary += "Strain data not available for this period.\n\n"
    else:
        strain = cycle_metrics.get('strain', cycle_metrics.get('strain_score', 'Unknown'))
        avg_hr = cycle_metrics.get('avg_hr', 'Unknown')
        max_hr = cycle_metrics.get('max_hr', 'Unknown')
        
        if strain != 'Unknown':
            formatted_strain = format_metric_value(strain, 'strain')
            summary += f"Daily Strain: {formatted_strain} / 21.0\n"
        if avg_hr != 'Unknown':
            formatted_avg_hr = format_metric_value(avg_hr, 'avg_hr')
            summary += f"Average Heart Rate: {formatted_avg_hr} bpm\n"
        if max_hr != 'Unknown':
            formatted_max_hr = format_metric_value(max_hr, 'max_hr')
            summary += f"Max Heart Rate: {formatted_max_hr} bpm\n"
        summary += "\n"
    
    # WORKOUTS SECTION
    summary += "💪 WORKOUTS\n"
    if "error" in workout_result.lower() or "no workout" in workout_result.lower():
        summary += "No workouts recorded for this period.\n\n"
    else:
        # Extract workout information more comprehensively
        workout_lines = [line.strip() for line in workout_result.split('\n') if line.strip()]
        
        # Look for workout details
        sport_name = workout_metrics.get('sport_name', 'Unknown')
        
        # Extract key workout metrics
        workout_strain = None
        workout_duration = None
        workout_calories = None
        
        for line in workout_lines:
            if 'Strain:' in line:
                strain_match = re.search(r'Strain: ([\d.]+)', line)
                if strain_match:
                    workout_strain = strain_match.group(1)
            elif 'Duration:' in line:
                duration_match = re.search(r'Duration: ([^\\n]+)', line)
                if duration_match:
                    workout_duration = duration_match.group(1).strip()
            elif 'Calories:' in line:
                cal_match = re.search(r'Calories: ([\d.]+)', line)
                if cal_match:
                    workout_calories = cal_match.group(1)
        
        if sport_name != 'Unknown':
            summary += f"Sport: {sport_name}\n"
        if workout_duration:
            summary += f"Duration: {workout_duration}\n"
        if workout_strain:
            formatted_workout_strain = format_metric_value(workout_strain, 'strain')
            summary += f"Strain: {formatted_workout_strain}/21.0\n"
        if workout_calories:
            summary += f"Calories: {workout_calories} kcal\n"
        
        # If we couldn't parse structured data, show raw info
        if sport_name == 'Unknown' and not workout_duration and not workout_strain:
            meaningful_lines = []
            for line in workout_lines:
                if (line and not line.startswith('=') and 
                    not line.startswith('Workout') and 
                    not line.startswith('Error') and 
                    len(line) > 3):
                    meaningful_lines.append(line)
            
            if meaningful_lines:
                for line in meaningful_lines[:4]:  # Show first 4 meaningful lines
                    summary += f"{line}\n"
        
        summary += "\n"
    
    # TIME-AWARE RECOMMENDATIONS
    if not resolved_date:  # Only for current data
        summary += f"🎯 {time_emoji} RECOMMENDATIONS\n"
        
        if time_period == "night":
            # Night/early morning recommendations (11 PM - 6 AM)
            summary += "• This is prime recovery time - prioritize rest and sleep\n"
            if current_hour >= 23 or current_hour < 4:
                summary += "• Your body is in deep recovery mode. Consider sleep if you haven't already\n"
            else:
                summary += "• Recovery data from last night's sleep should be available soon\n"
                summary += "• Light movement like stretching can help start your day\n"
        elif time_period == "day":
            # Daytime recommendations (6 AM - 6 PM) based on recovery
            recovery_score = recovery_metrics.get('recovery_score')
            strain = cycle_metrics.get('strain', cycle_metrics.get('strain_score'))
            
            if recovery_score and recovery_score != 'Unknown':
                try:
                    score_val = int(recovery_score)
                    if score_val >= 67:
                        summary += f"• Green Recovery ({recovery_score}%): Ready for high-intensity training\n"
                        summary += f"• Target Strain: 14.0-18.0 (Current: {strain}/21.0)\n" if strain != 'Unknown' else ""
                    elif score_val >= 34:
                        summary += f"• Yellow Recovery ({recovery_score}%): Moderate training recommended\n"
                        summary += f"• Target Strain: 10.0-14.0 (Current: {strain}/21.0)\n" if strain != 'Unknown' else ""
                    else:
                        summary += f"• Red Recovery ({recovery_score}%): Prioritize rest and recovery\n"
                        summary += f"• Target Strain: Below 10.0 (Current: {strain}/21.0)\n" if strain != 'Unknown' else ""
                except:
                    pass
            else:
                summary += "• Recovery data processing. Listen to your body for training intensity.\n"
            
            # Add morning-specific advice
            if current_hour < 12:
                summary += "• Morning is ideal for challenging workouts if recovery allows\n"
        else:
            # Evening recommendations (6 PM - 11 PM)
            summary += "• Focus on recovery and sleep preparation\n"
            summary += "• Consider a wind-down routine to optimize tomorrow's recovery\n"
            
            # Add strain-based sleep advice
            strain = cycle_metrics.get('strain', cycle_metrics.get('strain_score'))
            if strain and strain != 'Unknown':
                try:
                    strain_val = float(strain)
                    if strain_val > 14:
                        summary += f"• Your strain was high today ({strain}). Prioritize quality sleep for recovery.\n"
                except:
                    pass
    else:
        summary += "🎯 📅 HISTORICAL SUMMARY\n"
        summary += "• This represents a completed physiological cycle from the past\n"
    
    return summary

def get_custom_prompt() -> Optional[str]:
    """Get the current custom prompt if set."""
    try:
        with open(CUSTOM_PROMPT_FILE, "r") as f:
            data = json.load(f)
            return data.get("prompt")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_custom_prompt(prompt: Optional[str]) -> None:
    """Save the custom prompt to a file."""
    with open(CUSTOM_PROMPT_FILE, "w") as f:
        json.dump({"prompt": prompt}, f)

@mcp.tool()
def set_custom_prompt(prompt: Optional[str] = None) -> str:
    """Set or clear a custom prompt that will be appended to the start of every conversation.
    
    Args:
        prompt: The custom prompt text to use, or None to clear the current prompt.
    """
    if prompt is None:
        save_custom_prompt(None)
        return "Custom prompt cleared successfully."
    
    save_custom_prompt(prompt)
    return f"Custom prompt set successfully: '{prompt}'"

@mcp.tool()
async def get_recovery_trends(days: int = 7, end_date: Optional[str] = None) -> str:
    """Analyze recovery trends and patterns over multiple days (7-60 days).
    
    This powerful tool provides comprehensive recovery analysis including:
    - Recovery score trends with statistical analysis
    - Heart Rate Variability (HRV) progression
    - Resting Heart Rate (RHR) trends
    - Trend direction (improving/declining/stable)
    - Personalized insights and recommendations
    
    Perfect for understanding recovery patterns and optimizing training load.
    
    Args:
        days: Number of days to analyze (default: 7, max: 60)
              Recommended: 7 days for weekly patterns, 30 days for monthly trends
        end_date: End date in YYYY-MM-DD format (default: today)
                 Use to analyze historical periods
    
    Example Usage:
        - get_recovery_trends() → Past 7 days recovery trends
        - get_recovery_trends(30) → Monthly recovery analysis
        - get_recovery_trends(14, '2024-01-15') → 2 weeks ending Jan 15
    
    Returns:
        Comprehensive recovery trend analysis with insights and recommendations.
    """
    if days > 60:
        days = 60  # Limit to reasonable range
    if days < 2:
        days = 2   # Minimum for trend analysis
    
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    # Fetch recovery data for the specified period
    recovery_records = await fetch_multi_day_data("recovery", days, access_token, end_date)
    
    if not recovery_records:
        return f"No recovery data found for the past {days} days."
    
    # Extract metrics for trend analysis
    recovery_scores = []
    hrv_values = []
    rhr_values = []
    dates = []
    
    for record in recovery_records:
        score = record.get("score", {}) or {}
        created_at = record.get("created_at", "")
        
        if created_at:
            dates.append(created_at[:10])  # Extract date part
        
        recovery_score = score.get("recovery_score")
        if recovery_score is not None:
            recovery_scores.append(recovery_score)
        
        hrv = score.get("hrv_rmssd_milli") 
        if hrv is not None:
            hrv_values.append(hrv)
        
        rhr = score.get("resting_heart_rate")
        if rhr is not None:
            rhr_values.append(rhr)
    
    # Calculate trend statistics
    recovery_stats = calculate_trend_statistics(recovery_scores)
    hrv_stats = calculate_trend_statistics(hrv_values)
    rhr_stats = calculate_trend_statistics(rhr_values)
    
    start_date, final_date = calculate_date_range(days, end_date)
    
    # Build comprehensive analysis
    summary = f"""
{'='*60}
📈 RECOVERY TRENDS ANALYSIS ({days} days)
{'='*60}

📅 Period: {start_date} to {final_date}
📊 Data Points: {len(recovery_records)} recovery sessions

"""
    
    # Recovery Score Trends
    if recovery_stats.get("error"):
        summary += "💚 RECOVERY SCORE TRENDS\nInsufficient data available.\n\n"
    else:
        trend_emoji = "📈" if recovery_stats["trend_direction"] == "improving" else "📉" if recovery_stats["trend_direction"] == "declining" else "➡️"
        
        summary += f"""💚 RECOVERY SCORE TRENDS {trend_emoji}
Average: {recovery_stats['average']}%
Range: {recovery_stats['minimum']}% - {recovery_stats['maximum']}%
Trend: {recovery_stats['trend_direction'].title()} ({recovery_stats['trend']:+.1f} per day)
Stability: {recovery_stats['stability'].title()}

"""
    
    # HRV Trends
    if hrv_stats.get("error"):
        summary += "🫀 HRV TRENDS\nInsufficient data available.\n\n"
    else:
        trend_emoji = "📈" if hrv_stats["trend_direction"] == "improving" else "📉" if hrv_stats["trend_direction"] == "declining" else "➡️"
        
        summary += f"""🫀 HRV TRENDS {trend_emoji}
Average: {int(hrv_stats['average'])}ms
Range: {int(hrv_stats['minimum'])}ms - {int(hrv_stats['maximum'])}ms
Trend: {hrv_stats['trend_direction'].title()} ({hrv_stats['trend']:+.1f} per day)
Stability: {hrv_stats['stability'].title()}

"""
    
    # RHR Trends
    if rhr_stats.get("error"):
        summary += "❤️ RESTING HEART RATE TRENDS\nInsufficient data available.\n\n"
    else:
        trend_emoji = "📉" if rhr_stats["trend_direction"] == "improving" else "📈" if rhr_stats["trend_direction"] == "declining" else "➡️"  # Lower RHR is better
        
        summary += f"""❤️ RESTING HEART RATE TRENDS {trend_emoji}
Average: {int(rhr_stats['average'])} bpm
Range: {int(rhr_stats['minimum'])} bpm - {int(rhr_stats['maximum'])} bpm
Trend: {rhr_stats['trend_direction'].title()} ({rhr_stats['trend']:+.1f} per day)
Stability: {rhr_stats['stability'].title()}

"""
    
    # Insights and Recommendations
    summary += "🎯 INSIGHTS & RECOMMENDATIONS\n"
    
    if not recovery_stats.get("error"):
        if recovery_stats["average"] >= 67:
            summary += "• Excellent recovery average - you're consistently ready for training\n"
        elif recovery_stats["average"] >= 50:
            summary += "• Good recovery average - generally ready for moderate to high training\n"
        else:
            summary += "• Recovery below optimal - focus on sleep, stress management, and recovery practices\n"
        
        if recovery_stats["trend_direction"] == "improving":
            summary += "• Positive trend! Your recovery protocols are working well\n"
        elif recovery_stats["trend_direction"] == "declining":
            summary += "• Declining trend - consider adjusting training load or recovery strategies\n"
        
        if recovery_stats["stability"] == "low":
            summary += "• High variability detected - focus on consistent sleep and recovery routines\n"
    
    if not hrv_stats.get("error") and not rhr_stats.get("error"):
        # Combined insights
        if hrv_stats["trend_direction"] == "improving" and rhr_stats["trend_direction"] == "improving":
            summary += "• Cardiovascular fitness is improving - both HRV up and RHR down\n"
        elif hrv_stats["trend_direction"] == "declining" or rhr_stats["trend_direction"] == "declining":
            summary += "• Monitor cardiovascular stress - consider reducing training intensity\n"
    
    summary += "\n" + "="*60
    
    return summary

@mcp.tool()
async def get_strain_trends(days: int = 14, end_date: Optional[str] = None) -> str:
    """Analyze strain and training load progression over multiple days (2-60 days).
    
    This comprehensive tool provides detailed training analysis including:
    - Daily strain trends and training load distribution
    - Heart rate patterns and intensity zones
    - Energy expenditure (calories) tracking
    - Training frequency and consistency metrics
    - Personalized training recommendations
    
    Essential for monitoring training progression and preventing overtraining.
    
    Args:
        days: Number of days to analyze (default: 14, max: 60)
              Recommended: 14 days for training blocks, 30+ for season analysis
        end_date: End date in YYYY-MM-DD format (default: today)
                 Use to analyze specific training periods
    
    Example Usage:
        - get_multi_day_strain_trends() → Past 2 weeks training load
        - get_multi_day_strain_trends(30) → Monthly training analysis
        - get_multi_day_strain_trends(7, '2024-01-15') → Week ending Jan 15
    
    Returns:
        Comprehensive strain trend analysis with training load insights.
    """
    if days > 60:
        days = 60  # Limit to reasonable range
    if days < 2:
        days = 2   # Minimum for trend analysis
    
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    # Fetch cycle data for strain analysis
    cycle_records = await fetch_multi_day_data("cycle", days, access_token, end_date)
    
    if not cycle_records:
        return f"No cycle data found for the past {days} days."
    
    # Extract strain metrics
    strain_values = []
    avg_hr_values = []
    max_hr_values = []
    calories_values = []
    dates = []
    
    for record in cycle_records:
        score = record.get("score", {}) or {}
        start_date = record.get("start", "")
        
        if start_date:
            dates.append(start_date[:10])  # Extract date part
        
        strain = score.get("strain")
        if strain is not None:
            strain_values.append(strain)
        
        avg_hr = score.get("average_heart_rate")
        if avg_hr is not None:
            avg_hr_values.append(avg_hr)
            
        max_hr = score.get("max_heart_rate")
        if max_hr is not None:
            max_hr_values.append(max_hr)
            
        kilojoules = score.get("kilojoule", 0) or 0
        if kilojoules > 0:
            calories = kilojoules / 4.184
            calories_values.append(calories)
    
    # Calculate statistics
    strain_stats = calculate_trend_statistics(strain_values)
    avg_hr_stats = calculate_trend_statistics(avg_hr_values)
    max_hr_stats = calculate_trend_statistics(max_hr_values)
    calories_stats = calculate_trend_statistics(calories_values)
    
    start_date, final_date = calculate_date_range(days, end_date)
    
    # Calculate training load analysis
    total_strain = sum(strain_values) if strain_values else 0
    weekly_avg_strain = total_strain / (days / 7) if days >= 7 else total_strain / days
    
    # Strain distribution analysis
    high_strain_days = len([s for s in strain_values if s >= 15]) if strain_values else 0
    moderate_strain_days = len([s for s in strain_values if 10 <= s < 15]) if strain_values else 0
    low_strain_days = len([s for s in strain_values if s < 10]) if strain_values else 0
    
    # Build comprehensive analysis
    summary = f"""
{'='*60}
🔥 STRAIN TRENDS ANALYSIS ({days} days)
{'='*60}

📅 Period: {start_date} to {final_date}
📊 Data Points: {len(cycle_records)} training days

"""
    
    # Training Load Overview
    summary += f"""📋 TRAINING LOAD OVERVIEW
Total Strain: {total_strain:.1f}
Weekly Average: {weekly_avg_strain:.1f}
Daily Average: {strain_stats.get('average', 0):.1f}

Strain Distribution:
  High (15.0-21.0): {high_strain_days} days ({high_strain_days/len(strain_values)*100:.1f}%)
  Moderate (10.0-14.9): {moderate_strain_days} days ({moderate_strain_days/len(strain_values)*100:.1f}%)
  Low (0-9.9): {low_strain_days} days ({low_strain_days/len(strain_values)*100:.1f}%)

"""
    
    # Strain Trends
    if strain_stats.get("error"):
        summary += "🔥 STRAIN TRENDS\nInsufficient data available.\n\n"
    else:
        trend_emoji = "📈" if strain_stats["trend_direction"] == "improving" else "📉" if strain_stats["trend_direction"] == "declining" else "➡️"
        
        summary += f"""🔥 STRAIN TRENDS {trend_emoji}
Average: {strain_stats['average']:.1f}/21.0
Range: {strain_stats['minimum']:.1f} - {strain_stats['maximum']:.1f}
Trend: {strain_stats['trend_direction'].title()} ({strain_stats['trend']:+.2f} per day)
Stability: {strain_stats['stability'].title()}

"""
    
    # Heart Rate Trends
    if avg_hr_stats.get("error"):
        summary += "❤️ HEART RATE TRENDS\nInsufficient data available.\n\n"
    else:
        summary += f"""❤️ HEART RATE TRENDS
Average HR: {int(avg_hr_stats['average'])} bpm (Range: {int(avg_hr_stats['minimum'])}-{int(avg_hr_stats['maximum'])})
Max HR: {int(max_hr_stats['average'])} bpm (Range: {int(max_hr_stats['minimum'])}-{int(max_hr_stats['maximum'])})
HR Stability: {avg_hr_stats['stability'].title()}

"""
    
    # Energy Expenditure Trends
    if calories_stats.get("error"):
        summary += "⚡ ENERGY EXPENDITURE\nInsufficient data available.\n\n"
    else:
        summary += f"""⚡ ENERGY EXPENDITURE
Daily Average: {int(calories_stats['average'])} kcal
Range: {int(calories_stats['minimum'])} - {int(calories_stats['maximum'])} kcal
Weekly Total: {int(calories_stats['average'] * 7)} kcal

"""
    
    # Training Insights and Recommendations
    summary += "🎯 TRAINING INSIGHTS & RECOMMENDATIONS\n"
    
    if not strain_stats.get("error"):
        # Training load assessment
        if strain_stats["average"] >= 15:
            summary += "• High training load detected - monitor recovery closely\n"
        elif strain_stats["average"] >= 12:
            summary += "• Moderate to high training load - good for building fitness\n"
        elif strain_stats["average"] >= 8:
            summary += "• Moderate training load - well-balanced approach\n"
        else:
            summary += "• Low training load - consider increasing intensity if recovery allows\n"
        
        # Trend recommendations
        if strain_stats["trend_direction"] == "improving":
            summary += "• Increasing strain trend - ensure recovery keeps pace with training load\n"
        elif strain_stats["trend_direction"] == "declining":
            summary += "• Decreasing strain trend - good for recovery periods or deload weeks\n"
        
        # Stability insights
        if strain_stats["stability"] == "low":
            summary += "• High strain variability - consider more consistent training patterns\n"
        elif strain_stats["stability"] == "high":
            summary += "• Consistent strain levels - excellent training discipline\n"
        
        # Distribution recommendations
        if high_strain_days > days * 0.3:  # More than 30% high strain
            summary += "• High percentage of high-strain days - prioritize recovery\n"
        elif low_strain_days > days * 0.5:  # More than 50% low strain
            summary += "• Many low-strain days - opportunity to increase training intensity\n"
        else:
            summary += "• Good strain distribution balance between work and recovery\n"
    
    # Weekly periodization insight
    if days >= 7:
        weekly_strain = total_strain / (days / 7)
        if weekly_strain < 50:
            summary += "• Weekly load is conservative - good for recovery blocks\n"
        elif weekly_strain > 90:
            summary += "• High weekly load - monitor fatigue and recovery metrics\n"
        else:
            summary += "• Balanced weekly training load for sustainable progress\n"
    
    summary += "\n" + "="*60
    
    return summary

@mcp.tool()
async def get_sleep_trends(days: int = 30, end_date: Optional[str] = None) -> str:
    """Analyze sleep patterns and quality trends over multiple days (2-60 days).
    
    This comprehensive sleep analysis tool provides:
    - Sleep efficiency and performance trends
    - Sleep duration consistency and patterns
    - Sleep latency (time to fall asleep) analysis
    - Sleep disturbance frequency tracking
    - Sleep quality distribution and recommendations
    
    Perfect for optimizing sleep habits and identifying sleep pattern issues.
    
    Args:
        days: Number of days to analyze (default: 30, max: 60)
              Recommended: 30 days for comprehensive sleep pattern analysis
        end_date: End date in YYYY-MM-DD format (default: today)
                 Use to analyze historical sleep periods
    
    Example Usage:
        - get_multi_day_sleep_trends() → Past month sleep analysis
        - get_multi_day_sleep_trends(14) → Two weeks sleep patterns
        - get_multi_day_sleep_trends(60, '2024-01-31') → Two months ending Jan 31
    
    Returns:
        Comprehensive sleep trend analysis with optimization insights.
    """
    if days > 60:
        days = 60  # Limit to reasonable range
    if days < 2:
        days = 2   # Minimum for trend analysis
    
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    # Fetch sleep data for the specified period
    sleep_records = await fetch_multi_day_data("activity/sleep", days, access_token, end_date)
    
    if not sleep_records:
        return f"No sleep data found for the past {days} days."
    
    # Extract sleep metrics
    efficiency_values = []
    performance_values = []
    duration_values = []
    latency_values = []
    disturbance_values = []
    dates = []
    
    for record in sleep_records:
        score = record.get("score", {}) or {}
        stage_summary = score.get("stage_summary", {}) or {}
        start_time = record.get("start", "")
        
        if start_time:
            dates.append(start_time[:10])  # Extract date part
        
        efficiency = score.get("sleep_efficiency_percentage")
        if efficiency is not None:
            efficiency_values.append(efficiency)
        
        performance = score.get("sleep_performance_percentage")
        if performance is not None:
            performance_values.append(performance)
        
        # Calculate duration in hours
        total_sleep_milli = (
            stage_summary.get('total_light_sleep_time_milli', 0) or 0 +
            stage_summary.get('total_slow_wave_sleep_time_milli', 0) or 0 +
            stage_summary.get('total_rem_sleep_time_milli', 0) or 0
        )
        if total_sleep_milli > 0:
            duration_hours = total_sleep_milli / 3600000
            duration_values.append(duration_hours)
        
        latency = stage_summary.get('sleep_latency_milli', 0) or 0
        if latency > 0:
            latency_minutes = latency / 60000
            latency_values.append(latency_minutes)
        
        disturbances = stage_summary.get('disturbance_count', 0) or 0
        disturbance_values.append(disturbances)
    
    # Calculate statistics
    efficiency_stats = calculate_trend_statistics(efficiency_values)
    performance_stats = calculate_trend_statistics(performance_values)
    duration_stats = calculate_trend_statistics(duration_values)
    latency_stats = calculate_trend_statistics(latency_values)
    disturbance_stats = calculate_trend_statistics(disturbance_values)
    
    start_date, final_date = calculate_date_range(days, end_date)
    
    # Sleep quality distribution
    excellent_nights = len([e for e in efficiency_values if e >= 85]) if efficiency_values else 0
    good_nights = len([e for e in efficiency_values if 75 <= e < 85]) if efficiency_values else 0
    fair_nights = len([e for e in efficiency_values if 65 <= e < 75]) if efficiency_values else 0
    poor_nights = len([e for e in efficiency_values if e < 65]) if efficiency_values else 0
    
    # Build comprehensive analysis
    summary = f"""
{'='*60}
😴 SLEEP TRENDS ANALYSIS ({days} days)
{'='*60}

📅 Period: {start_date} to {final_date}
📊 Data Points: {len(sleep_records)} sleep sessions

"""
    
    # Sleep Quality Overview
    total_nights = len(efficiency_values)
    if total_nights > 0:
        summary += f"""📋 SLEEP QUALITY OVERVIEW
Sleep Quality Distribution:
  Excellent (≥85%): {excellent_nights} nights ({excellent_nights/total_nights*100:.1f}%)
  Good (75-84%): {good_nights} nights ({good_nights/total_nights*100:.1f}%)
  Fair (65-74%): {fair_nights} nights ({fair_nights/total_nights*100:.1f}%)
  Poor (<65%): {poor_nights} nights ({poor_nights/total_nights*100:.1f}%)

"""
    
    # Sleep Efficiency Trends
    if efficiency_stats.get("error"):
        summary += "💤 SLEEP EFFICIENCY TRENDS\nInsufficient data available.\n\n"
    else:
        trend_emoji = "📈" if efficiency_stats["trend_direction"] == "improving" else "📉" if efficiency_stats["trend_direction"] == "declining" else "➡️"
        
        summary += f"""💤 SLEEP EFFICIENCY TRENDS {trend_emoji}
Average: {efficiency_stats['average']:.1f}%
Range: {efficiency_stats['minimum']:.1f}% - {efficiency_stats['maximum']:.1f}%
Trend: {efficiency_stats['trend_direction'].title()} ({efficiency_stats['trend']:+.2f}% per day)
Stability: {efficiency_stats['stability'].title()}

"""
    
    # Sleep Performance Trends
    if performance_stats.get("error"):
        summary += "🏆 SLEEP PERFORMANCE TRENDS\nInsufficient data available.\n\n"
    else:
        trend_emoji = "📈" if performance_stats["trend_direction"] == "improving" else "📉" if performance_stats["trend_direction"] == "declining" else "➡️"
        
        summary += f"""🏆 SLEEP PERFORMANCE TRENDS {trend_emoji}
Average: {performance_stats['average']:.1f}%
Range: {performance_stats['minimum']:.1f}% - {performance_stats['maximum']:.1f}%
Trend: {performance_stats['trend_direction'].title()} ({performance_stats['trend']:+.2f}% per day)
Stability: {performance_stats['stability'].title()}

"""
    
    # Sleep Duration Trends
    if duration_stats.get("error"):
        summary += "⏰ SLEEP DURATION TRENDS\nInsufficient data available.\n\n"
    else:
        avg_hours = int(duration_stats['average'])
        avg_minutes = int((duration_stats['average'] % 1) * 60)
        min_hours = int(duration_stats['minimum'])
        min_minutes = int((duration_stats['minimum'] % 1) * 60)
        max_hours = int(duration_stats['maximum'])
        max_minutes = int((duration_stats['maximum'] % 1) * 60)
        
        summary += f"""⏰ SLEEP DURATION TRENDS
Average: {avg_hours}h {avg_minutes}m
Range: {min_hours}h {min_minutes}m - {max_hours}h {max_minutes}m
Stability: {duration_stats['stability'].title()}

"""
    
    # Sleep Latency Trends
    if latency_stats.get("error"):
        summary += "🕐 SLEEP LATENCY TRENDS\nInsufficient data available.\n\n"
    else:
        summary += f"""🕐 SLEEP LATENCY TRENDS
Average: {latency_stats['average']:.0f} minutes
Range: {latency_stats['minimum']:.0f} - {latency_stats['maximum']:.0f} minutes
Quality: {"Excellent" if latency_stats['average'] < 15 else "Good" if latency_stats['average'] < 30 else "Fair" if latency_stats['average'] < 45 else "Needs Improvement"}

"""
    
    # Sleep Disturbances
    if disturbance_stats.get("error"):
        summary += "🌙 SLEEP DISTURBANCES\nInsufficient data available.\n\n"
    else:
        summary += f"""🌙 SLEEP DISTURBANCES
Average: {disturbance_stats['average']:.1f} per night
Range: {int(disturbance_stats['minimum'])} - {int(disturbance_stats['maximum'])} disturbances
Quality: {"Excellent" if disturbance_stats['average'] < 2 else "Good" if disturbance_stats['average'] < 4 else "Fair" if disturbance_stats['average'] < 6 else "Needs Improvement"}

"""
    
    # Sleep Optimization Insights
    summary += "🎯 SLEEP OPTIMIZATION INSIGHTS\n"
    
    if not efficiency_stats.get("error"):
        # Overall sleep quality assessment
        if efficiency_stats["average"] >= 85:
            summary += "• Excellent sleep efficiency - you're optimizing recovery well\n"
        elif efficiency_stats["average"] >= 75:
            summary += "• Good sleep efficiency - some room for optimization\n"
        else:
            summary += "• Sleep efficiency below optimal - focus on sleep hygiene improvements\n"
        
        # Trend insights
        if efficiency_stats["trend_direction"] == "improving":
            summary += "• Positive trend! Your sleep optimization efforts are working\n"
        elif efficiency_stats["trend_direction"] == "declining":
            summary += "• Declining trend - review recent changes in routine or environment\n"
        
        # Consistency insights
        if efficiency_stats["stability"] == "low":
            summary += "• High variability in sleep quality - focus on consistent bedtime routines\n"
        elif efficiency_stats["stability"] == "high":
            summary += "• Consistent sleep quality - excellent sleep discipline\n"
    
    # Duration insights
    if not duration_stats.get("error"):
        avg_duration = duration_stats["average"]
        if avg_duration < 7:
            summary += "• Sleep duration below recommended 7-9 hours - prioritize more sleep time\n"
        elif avg_duration > 9:
            summary += "• Sleep duration above average - ensure quality matches quantity\n"
        else:
            summary += "• Sleep duration in optimal range - maintain current schedule\n"
    
    # Latency and disturbance insights
    if not latency_stats.get("error") and latency_stats["average"] > 30:
        summary += "• Long sleep latency detected - consider relaxation techniques before bed\n"
    
    if not disturbance_stats.get("error") and disturbance_stats["average"] > 4:
        summary += "• High sleep disturbances - optimize sleep environment (temperature, noise, light)\n"
    
    # Quality distribution insights
    if total_nights > 0:
        if poor_nights > total_nights * 0.2:  # More than 20% poor nights
            summary += "• High percentage of poor sleep nights - comprehensive sleep review needed\n"
        elif excellent_nights > total_nights * 0.6:  # More than 60% excellent nights
            summary += "• Majority of nights are excellent - maintain current sleep practices\n"
    
    summary += "\n" + "="*60
    
    return summary

@mcp.tool()
async def get_recovery_chart(days: int = 14, end_date: Optional[str] = None) -> str:
    """Generate ASCII chart visualization of recovery score trends over time.
    
    This visualization tool creates an easy-to-read ASCII chart showing:
    - Daily recovery scores plotted over time
    - Trend lines and patterns
    - Statistical summary with averages and ranges
    - Visual identification of peaks and valleys
    
    Perfect for quickly spotting recovery patterns and sharing visual summaries.
    
    Args:
        days: Number of days to chart (default: 14, max: 30)
              Recommended: 14 days for detailed view, 30 days for broader patterns
        end_date: End date in YYYY-MM-DD format (default: today)
                 Use to chart historical periods
    
    Example Usage:
        - generate_visual_recovery_chart() → Past 2 weeks recovery chart
        - generate_visual_recovery_chart(30) → Monthly recovery visualization
        - generate_visual_recovery_chart(7, '2024-01-15') → Week ending Jan 15
    
    Returns:
        ASCII chart showing recovery score trends over time with summary statistics.
    """
    if days > 30:
        days = 30  # Limit for readability
    if days < 3:
        days = 3   # Minimum for meaningful chart
    
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    # Fetch recovery data
    recovery_records = await fetch_multi_day_data("recovery", days, access_token, end_date)
    
    if not recovery_records:
        return f"No recovery data found for the past {days} days."
    
    # Extract recovery scores and dates
    recovery_scores = []
    dates = []
    
    for record in recovery_records:
        score = record.get("score", {}) or {}
        created_at = record.get("created_at", "")
        
        recovery_score = score.get("recovery_score")
        if recovery_score is not None:
            recovery_scores.append(recovery_score)
            if created_at:
                dates.append(created_at[:10])  # Extract date part
    
    if not recovery_scores:
        return "No recovery score data available for charting."
    
    start_date, final_date = calculate_date_range(days, end_date)
    
    # Generate chart
    chart = generate_ascii_chart(recovery_scores, f"Recovery Score Trends ({days} days)", width=40)
    
    # Add summary statistics
    stats = calculate_trend_statistics(recovery_scores)
    
    summary = f"""
{'='*60}
📈 RECOVERY SCORE CHART
{'='*60}

📅 Period: {start_date} to {final_date}
📊 Data Points: {len(recovery_scores)}

{chart}

📊 STATISTICS:
Average: {stats.get('average', 0):.1f}%
Range: {stats.get('minimum', 0):.1f}% - {stats.get('maximum', 0):.1f}%
Trend: {stats.get('trend_direction', 'unknown').title()}
Stability: {stats.get('stability', 'unknown').title()}

🎯 Quick Insights:
"""
    
    if stats.get('average', 0) >= 67:
        summary += "• Consistently ready for training 💚\n"
    elif stats.get('average', 0) >= 50:
        summary += "• Generally good recovery levels 💛\n"
    else:
        summary += "• Focus needed on recovery optimization ❤️\n"
    
    if stats.get('trend_direction') == 'improving':
        summary += "• Positive trend - recovery protocols working! 📈\n"
    elif stats.get('trend_direction') == 'declining':
        summary += "• Consider adjusting training or recovery strategies 📉\n"
    
    summary += "\n" + "="*60
    
    return summary

@mcp.tool()
def get_current_prompt() -> str:
    """Get the current custom prompt if one is set."""
    prompt = get_custom_prompt()
    if prompt is None:
        return "No custom prompt is currently set."
    
    return f"Current custom prompt: '{prompt}'"

@mcp.tool()
async def get_workout_trends(days: int = 30, end_date: Optional[str] = None, sport_filter: Optional[str] = None) -> str:
    """Analyze workout trends, training patterns, and athletic profiling over multiple days (2-60 days).
    
    This comprehensive workout analysis tool provides:
    - Training frequency and consistency patterns
    - Sport distribution and athletic profiling
    - Workout intensity progression (strain analysis)
    - Duration and training volume trends
    - Heart rate zone distribution analysis
    - Performance metrics (distance, pace, elevation)
    - Training load periodization assessment
    - Recovery patterns between workouts
    
    Essential for determining athlete type, training effectiveness, and sport-specific optimization.
    
    Args:
        days: Number of days to analyze (default: 30, max: 60)
              Recommended: 30 days for athletic profiling, 60 days for periodization analysis
        end_date: End date in YYYY-MM-DD format (default: today)
                 Use to analyze specific training periods
        sport_filter: Optional sport name filter (e.g., "running", "cycling", "weightlifting")
                     Use to analyze sport-specific patterns
    
    Example Usage:
        - get_workout_trends() → Past month training analysis
        - get_workout_trends(60) → Two months training periodization
        - get_workout_trends(14, sport_filter="running") → Running-specific analysis
        - get_workout_trends(30, '2024-01-31') → January training analysis
    
    Returns:
        Comprehensive workout trend analysis with athletic profiling and training insights.
    """
    if days > 60:
        days = 60  # Limit to reasonable range
    if days < 2:
        days = 2   # Minimum for trend analysis
    
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
    except (FileNotFoundError, json.JSONDecodeError):
        return "You are not authenticated with WHOOP. Use the authenticate_with_whoop tool to authenticate."
    
    # Fetch workout data for the specified period
    workout_records = await fetch_multi_day_data("activity/workout", days, access_token, end_date)
    
    if not workout_records:
        return f"No workout data found for the past {days} days."
    
    # Apply sport filter if specified
    if sport_filter:
        sport_filter_lower = sport_filter.lower()
        workout_records = [w for w in workout_records if w.get("sport_name", "").lower() == sport_filter_lower]
        if not workout_records:
            return f"No {sport_filter} workouts found in the past {days} days."
    
    # Extract workout metrics for analysis
    workout_data = []
    sport_distribution = {}
    total_workouts = len(workout_records)
    
    for record in workout_records:
        score = record.get("score", {}) or {}
        sport_name = record.get("sport_name", "Unknown")
        start_time = record.get("start", "")
        end_time = record.get("end", "")
        
        # Calculate duration in minutes
        duration_minutes = 0
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_minutes = (end_dt - start_dt).total_seconds() / 60
            except:
                duration_minutes = 0
        
        workout_info = {
            'date': start_time[:10] if start_time else '',
            'sport': sport_name,
            'strain': score.get('strain', 0) or 0,
            'duration_minutes': duration_minutes,
            'avg_hr': score.get('average_heart_rate', 0) or 0,
            'max_hr': score.get('max_heart_rate', 0) or 0,
            'kilojoules': score.get('kilojoule', 0) or 0,
            'distance_meters': score.get('distance_meter', 0) or 0,
            'altitude_gain': score.get('altitude_gain_meter', 0) or 0,
            'zone_durations': score.get('zone_durations', {}) or {}
        }
        
        workout_data.append(workout_info)
        
        # Track sport distribution
        sport_distribution[sport_name] = sport_distribution.get(sport_name, 0) + 1
    
    # Calculate comprehensive statistics
    strain_values = [w['strain'] for w in workout_data if w['strain'] > 0]
    duration_values = [w['duration_minutes'] for w in workout_data if w['duration_minutes'] > 0]
    avg_hr_values = [w['avg_hr'] for w in workout_data if w['avg_hr'] > 0]
    calories_values = [w['kilojoules'] / 4.184 for w in workout_data if w['kilojoules'] > 0]  # Convert to calories
    distance_values = [w['distance_meters'] / 1000 for w in workout_data if w['distance_meters'] > 0]  # Convert to km
    
    strain_stats = calculate_trend_statistics(strain_values)
    duration_stats = calculate_trend_statistics(duration_values)
    avg_hr_stats = calculate_trend_statistics(avg_hr_values)
    
    start_date, final_date = calculate_date_range(days, end_date)
    
    # Calculate training frequency
    workout_frequency = total_workouts / (days / 7)  # Workouts per week
    
    # Determine athlete type based on patterns
    athlete_type = "Mixed Training"
    if sport_distribution:
        top_sport = max(sport_distribution, key=sport_distribution.get)
        top_sport_percentage = (sport_distribution[top_sport] / total_workouts) * 100
        
        if top_sport_percentage >= 70:
            if top_sport.lower() in ['running', 'cycling', 'swimming', 'rowing']:
                athlete_type = "Endurance Specialist"
            elif top_sport.lower() in ['weightlifting', 'strength training', 'crossfit']:
                athlete_type = "Strength/Power Specialist"
            else:
                athlete_type = f"{top_sport.title()} Specialist"
        elif len(sport_distribution) >= 3:
            athlete_type = "Multi-Sport Athlete"
    
    # Build comprehensive analysis
    summary = f"""
{'='*70}
🏋️ WORKOUT TRENDS & ATHLETIC PROFILING ({days} days)
{'='*70}

📅 Period: {start_date} to {final_date}
🏃 Total Workouts: {total_workouts}
📊 Training Frequency: {workout_frequency:.1f} workouts/week
🎯 Athletic Profile: {athlete_type}

"""
    
    # Sport Distribution Analysis
    if sport_distribution:
        summary += "🏆 SPORT DISTRIBUTION\n"
        sorted_sports = sorted(sport_distribution.items(), key=lambda x: x[1], reverse=True)
        for sport, count in sorted_sports:
            percentage = (count / total_workouts) * 100
            summary += f"  • {sport.title()}: {count} workouts ({percentage:.1f}%)\n"
        summary += "\n"
    
    # Training Intensity Analysis
    if strain_stats.get("error"):
        summary += "🔥 TRAINING INTENSITY\nInsufficient strain data available.\n\n"
    else:
        # Classify intensity distribution
        high_intensity = len([s for s in strain_values if s >= 15])
        moderate_intensity = len([s for s in strain_values if 10 <= s < 15])
        low_intensity = len([s for s in strain_values if s < 10])
        
        trend_emoji = "📈" if strain_stats["trend_direction"] == "improving" else "📉" if strain_stats["trend_direction"] == "declining" else "➡️"
        
        summary += f"""🔥 TRAINING INTENSITY ANALYSIS {trend_emoji}
Average Strain: {strain_stats['average']:.1f}/21.0
Range: {strain_stats['minimum']:.1f} - {strain_stats['maximum']:.1f}
Trend: {strain_stats['trend_direction'].title()} ({strain_stats['trend']:+.2f} per day)

Intensity Distribution:
  High Intensity (15.0-21.0): {high_intensity} workouts ({high_intensity/len(strain_values)*100:.1f}%)
  Moderate Intensity (10.0-14.9): {moderate_intensity} workouts ({moderate_intensity/len(strain_values)*100:.1f}%)
  Low Intensity (<10.0): {low_intensity} workouts ({low_intensity/len(strain_values)*100:.1f}%)

"""
    
    # Training Volume Analysis
    if duration_stats.get("error"):
        summary += "⏱️ TRAINING VOLUME\nInsufficient duration data available.\n\n"
    else:
        total_training_hours = sum(duration_values) / 60
        avg_hours_per_week = total_training_hours / (days / 7)
        
        summary += f"""⏱️ TRAINING VOLUME ANALYSIS
Total Training Time: {total_training_hours:.1f} hours
Weekly Average: {avg_hours_per_week:.1f} hours/week
Average Workout: {duration_stats['average']:.0f} minutes
Range: {duration_stats['minimum']:.0f} - {duration_stats['maximum']:.0f} minutes

"""
    
    # Heart Rate Analysis
    if avg_hr_stats.get("error"):
        summary += "❤️ CARDIOVASCULAR PATTERNS\nInsufficient heart rate data available.\n\n"
    else:
        summary += f"""❤️ CARDIOVASCULAR PATTERNS
Average Workout HR: {int(avg_hr_stats['average'])} bpm
Range: {int(avg_hr_stats['minimum'])} - {int(avg_hr_stats['maximum'])} bpm
Consistency: {avg_hr_stats['stability'].title()}

"""
    
    # Performance Metrics (if available)
    if distance_values:
        total_distance = sum(distance_values)
        avg_distance_per_workout = total_distance / len(distance_values)
        weekly_distance = total_distance / (days / 7)
        
        summary += f"""🏃 PERFORMANCE METRICS
Total Distance: {total_distance:.1f} km
Weekly Average: {weekly_distance:.1f} km/week
Average per Workout: {avg_distance_per_workout:.1f} km

"""
    
    if calories_values:
        total_calories = sum(calories_values)
        avg_calories_per_workout = total_calories / len(calories_values)
        weekly_calories = total_calories / (days / 7)
        
        summary += f"""⚡ ENERGY EXPENDITURE
Total Calories: {int(total_calories)} kcal
Weekly Average: {int(weekly_calories)} kcal/week
Average per Workout: {int(avg_calories_per_workout)} kcal

"""
    
    # Athletic Profiling Insights
    summary += "🎯 ATHLETIC PROFILING & INSIGHTS\n"
    
    # Training pattern analysis
    if workout_frequency >= 6:
        summary += "• High-frequency trainer - excellent consistency for elite performance\n"
    elif workout_frequency >= 4:
        summary += "• Moderate-frequency trainer - good consistency for fitness goals\n"
    elif workout_frequency >= 2:
        summary += "• Low-moderate frequency - room for increased consistency\n"
    else:
        summary += "• Low training frequency - consider increasing workout consistency\n"
    
    # Intensity pattern insights
    if not strain_stats.get("error"):
        if strain_stats["average"] >= 15:
            summary += "• High-intensity focused training - monitor recovery closely\n"
        elif strain_stats["average"] >= 12:
            summary += "• Moderate-high intensity training - good for fitness building\n"
        elif strain_stats["average"] >= 8:
            summary += "• Balanced intensity approach - sustainable for long-term progress\n"
        else:
            summary += "• Lower intensity focus - consider adding higher intensity sessions\n"
        
        # Training progression insights
        if strain_stats["trend_direction"] == "improving":
            summary += "• Positive training progression - intensity building effectively\n"
        elif strain_stats["trend_direction"] == "declining":
            summary += "• Declining intensity trend - may indicate fatigue or detraining\n"
    
    # Sport-specific insights
    if sport_distribution:
        if athlete_type == "Endurance Specialist":
            summary += "• Endurance-focused profile - emphasize aerobic base and recovery\n"
        elif athlete_type == "Strength/Power Specialist":
            summary += "• Strength/Power profile - focus on recovery between intense sessions\n"
        elif athlete_type == "Multi-Sport Athlete":
            summary += "• Cross-training approach - excellent for overall fitness and injury prevention\n"
    
    summary += "\n" + "="*70
    
    return summary

@mcp.tool()
def get_tools_guide() -> str:
    """Get a comprehensive guide to all available WHOOP analytics tools and their capabilities.
    
    This essential tool explains what health data and analytics are available,
    helping agents understand the full scope of WHOOP insights for research and analysis.
    
    Use this tool first to understand what's possible with WHOOP data analysis.
    """
    
    return """
🏥 WHOOP HEALTH ANALYTICS TOOLKIT
═══════════════════════════════════════════════════════════════════════════════════

📊 COMPREHENSIVE HEALTH DATA AVAILABLE

🔹 SINGLE-DAY DATA TOOLS (Latest or Specific Date)
   • get_single_night_sleep_data(date) → Sleep stages, efficiency, performance
   • get_single_day_recovery_data(date) → Recovery score, HRV, RHR, temperature
   • get_single_workout_data(workout_id) → Workout strain, HR zones, calories
   • get_single_day_strain_data(date) → Daily strain, avg/max HR, energy
   • get_profile_data() → User profile and basic information
   • get_body_measurement_data() → Height, weight, max heart rate

🔹 MULTI-DAY TREND ANALYSIS (7-60 Days Historical)
   • get_multi_day_recovery_trends(days, end_date) → Recovery patterns & HRV trends
   • get_multi_day_strain_trends(days, end_date) → Training load progression
   • get_multi_day_sleep_trends(days, end_date) → Sleep quality & consistency patterns
   • get_multi_day_workout_trends(days, end_date, sport_filter) → Training patterns & athletic profiling
   • generate_visual_recovery_chart(days, end_date) → ASCII chart visualization

🔹 ADVANCED ANALYSIS TOOLS
   • get_comprehensive_training_readiness(date) → Training recommendations
   • get_workout_analysis(workout_id) → Detailed workout metrics & zones
   • get_sleep_quality_analysis(date) → Sleep efficiency deep dive
   • get_recovery_load_analysis(date) → Cardiovascular stress analysis

🔹 COMPREHENSIVE SUMMARIES
   • get_comprehensive_daily_summary(date) → Complete daily health overview
   • search_whoop_sports(query) → Sport-specific workout history
   • get_sports_mapping() → Available sports and IDs

💡 KEY CAPABILITIES FOR RESEARCH AGENTS

✅ MULTI-DAY ANALYTICS (Up to 60 days)
   - Recovery trends with statistical analysis
   - Training load progression and patterns
   - Sleep quality consistency over time
   - Workout trends and athletic profiling
   - Heart rate variability tracking
   - Trend direction analysis (improving/declining/stable)

✅ COMPREHENSIVE METRICS COVERED
   - Workout Type, Duration, Strain (0-21 scale)
   - Training frequency, intensity distribution, sport profiling
   - Recovery Scores (0-100%), HRV, Resting Heart Rate
   - Sleep Quality, Efficiency, Consistency
   - VO2 Max estimation (via max heart rate data)
   - Energy expenditure and training load
   - Athletic profiling (endurance vs strength vs multi-sport)

✅ INTELLIGENT INSIGHTS
   - Personalized recommendations based on data
   - Cross-metric correlation analysis
   - Time-aware suggestions (adapts to time of day)
   - Overtraining risk assessment
   - Sleep optimization guidance

📋 USAGE PATTERNS FOR AGENTS

🎯 Daily Health Check:
   get_comprehensive_daily_summary() → Complete current status

🎯 Weekly Training Analysis:
   get_multi_day_workout_trends(7) → Training patterns and frequency
   get_multi_day_strain_trends(7) → Training load patterns
   get_multi_day_recovery_trends(7) → Recovery adequacy

🎯 Monthly Health Trends:
   get_multi_day_sleep_trends(30) → Sleep pattern analysis
   get_multi_day_recovery_trends(30) → Long-term recovery trends

🎯 Training Planning:
   get_comprehensive_training_readiness() → Current readiness
   get_multi_day_workout_trends(14) → Training patterns & periodization
   get_multi_day_strain_trends(14) → Recent training load

🎯 Performance Research:
   get_multi_day_workout_trends(60) → Athletic profiling & training analysis
   get_multi_day_recovery_trends(60) → Long-term patterns
   get_multi_day_strain_trends(60) → Training periodization analysis

⚡ AUTHENTICATION
   authenticate_with_whoop() → Required first step
   check_authentication_status() → Verify connection

📈 QUICK START FOR AGENTS
1. authenticate_with_whoop() 
2. get_comprehensive_daily_summary() → Get overview
3. get_multi_day_recovery_trends(14) → Understand recent patterns
4. Use specific tools based on research needs

💡 PRO TIPS
• Use multi-day tools (7-60 days) for trend analysis
• Combine recovery + strain trends for training insights
• Daily summary tool provides holistic health picture
• All date parameters use YYYY-MM-DD format
• Tools provide actionable recommendations, not just data

═══════════════════════════════════════════════════════════════════════════════════
    """

if __name__ == "__main__":
    # Initialize auth event
    auth_completed = threading.Event()
    
    # Start callback server for authentication
    start_callback_server()
    
    # Set system prompt with custom prompt if available
    custom_prompt = get_custom_prompt()
    if custom_prompt:
        mcp.system_prompt = custom_prompt
    
    try:
        # Initialize and run the server
        mcp.run(transport='stdio')
    finally:
        # Stop callback server when MCP exits
        stop_callback_server() 
#!/usr/bin/env python3
"""
Parallel AI x WHOOP MCP Integration Demo
Real-time personal fitness analysis with streaming events
"""

import json
import os
import time
import requests
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.syntax import Syntax
from datetime import datetime

# Configuration - Load from environment variables
PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")
MCP_API_KEY = os.getenv("MCP_API_KEY", "local_development_key_12345")

console = Console()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Parallel AI x WHOOP MCP Integration Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_parallel_whoop.py https://abc123.ngrok-free.app
  python demo_parallel_whoop.py https://your-ngrok-url.ngrok-free.app
        """
    )
    parser.add_argument(
        "ngrok_url",
        help="The ngrok URL (without /mcp suffix) - will automatically append /mcp"
    )
    return parser.parse_args()

def create_header():
    """Create a beautiful header for the demo"""
    title = Text("Parallel AI × WHOOP Integration", style="bold magenta")
    subtitle = Text("Athlete Benchmarking & Training Optimization via MCP", style="italic cyan")
    
    header_table = Table.grid(padding=1)
    header_table.add_column(justify="center")
    header_table.add_row(title)
    header_table.add_row(subtitle)
    header_table.add_row(Text(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim"))
    
    return Panel(
        Align.center(header_table),
        border_style="bright_blue",
        padding=(1, 2)
    )

def create_status_panel(status="Starting..."):
    """Create a status panel"""
    return Panel(
        Text(status, style="bold green"),
        title="Status",
        border_style="green"
    )

def create_event_panel(event_type, message, timestamp):
    """Create a panel for SSE events"""
    event_config = {
        "task_run.state": {"style": "blue", "icon": "[STATUS]", "title": "Status"},
        "task_run.progress_msg.exec_status": {"style": "yellow", "icon": "[START]", "title": "Starting"},
        "task_run.progress_msg.plan": {"style": "bright_green", "icon": "[PLAN]", "title": "Reasoning"},
        "task_run.progress_msg.tool": {"style": "cyan", "icon": "[TOOL]", "title": "Tool"}, 
        "task_run.progress_msg.tool_call": {"style": "magenta", "icon": "[MCP]", "title": "MCP Tool Call"},
        "task_run.progress_msg.search": {"style": "cyan", "icon": "[SEARCH]", "title": "Web Search"},
        "task_run.progress_stats": {"style": "white", "icon": "[PROGRESS]", "title": "Progress"}
    }
    
    config = event_config.get(event_type, {"style": "white", "icon": "[UPDATE]", "title": "Update"})
    style = config["style"]
    icon = config["icon"]
    title = config["title"]
    
    time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%H:%M:%S') if timestamp else "N/A"
    
    content = Table.grid(padding=0)
    content.add_column()
    content.add_row(Text(f"[TIME] {time_str}", style="dim"))
    content.add_row(Text(message, style=style))
    
    return Panel(
        content,
        title=f"[{style}]{icon} {title}[/{style}]",
        border_style=style,
        padding=(0, 1)
    )

def create_prompt():
    """Create the athlete benchmarking and adaptation prompt"""
    return """I need you to conduct EXTENSIVE research across both my WHOOP data and the web to solve a specific fitness puzzle: 

**MY PROFILE:**
- Demographics: [Include your Demographics]
- Training routine: [Summarize your excercise routine; WHOOP does not have strength training data available via MCP]
- WHOOP data: includes HRV, RHR, strain, recovery, and sleep metrics

**THE PUZZLE:**
I've been really curious about what it means to "train like an athlete." Specifically: how far away am I from the physiological profiles of different athlete groups, and what changes would most effectively move my metrics in that direction?

**RESEARCH REQUIREMENTS:**
Search extensively across:
- Published biometric norms (2020-2025) for athletes in different categories (endurance, strength/power, team sport, recreationally trained)
- Studies comparing trained vs untrained people with my demographic by HRV, RHR, recovery, VO2, sleep
- Research on training adaptations and interventions that shift these metrics
- Evidence-based protocols athletes use to close gaps in HRV, RHR, or recovery (you may find this on Youtube, podcasts, interviews, scientific papers, etc.)
- Demographic factors that might affect adaptation patterns

**CRITICAL:** Use my actual WHOOP data throughout with MCP tool calls. Reference specific studies (2020-2025), include direct URLs to research papers, training protocols, and practical resources, and include a clear summary of my wHOOP data in relation to your web research."""

def create_task_spec():
    """Create a custom JSON schema for athlete benchmarking & adaptation analysis"""
    return {
        "output_schema": {
            "type": "json",
            "json_schema": {
                "type": "object",
                "description": "Comprehensive benchmarking of WHOOP fitness data against athlete cohorts with research-backed interventions",
                "properties": {
                    # Comprehensive WHOOP data summary
                    "whoop_data_summary": {"type": "string", "description": "Comprehensive 30-day snapshot of WHOOP data including: average RHR (bpm), HRV (ms), daily strain, sleep duration, restorative sleep (deep + REM), recovery scores, workout frequency, and VO2 max if available. Present as clear, organized summary with key trends and patterns."},
                    
                    # Benchmarking research
                    "athlete_norms_endurance": {"type": "string","description": "Published ranges (2020-2025) for female endurance athletes: HRV, RHR, recovery, VO2 max, sleep metrics. Include specific studies and sample sizes."},
                    "athlete_norms_strength": {"type": "string","description": "Published ranges (2020-2025) for female strength/power athletes: HRV, RHR, recovery, VO2 max, sleep metrics. Include specific studies and sample sizes."},
                    "athlete_norms_team_sport": {"type": "string","description": "Published ranges (2020-2025) for female team sport athletes: HRV, RHR, recovery, VO2 max, sleep metrics. Include specific studies and sample sizes."},
                    "cohort_comparison_summary": {"type": "string","description": "Detailed comparison showing percent similarity of user's metrics to each athlete cohort. Highlight closest matches and identify the largest performance gaps with specific numbers."},
                    
                    # Consolidated training interventions
                    "training_interventions": {"type": "string","description": "Research-backed training and recovery interventions (2020-2025) to improve HRV, reduce RHR, and enhance recovery. Include specific protocols, expected timelines, effect sizes, and implementation strategies from peer-reviewed studies."},
                    
                    # Core analysis & recommendations
                    "top_3_cohort_matches": {"type": "string","description": "Ranked list of athlete cohorts user most closely resembles, with a quantiative and qualitative analysis of comparisons. Include references to training methods and documented regimens."},
                    "biggest_gaps": {"type": "string","description": "Top 3 largest performance gaps between user's metrics and target athlete cohorts, with specific numbers and citations from research literature."},
                    "evidence_based_action_plan": {"type": "string","description": "5 prioritized, research-backed recommendations with clear implementation steps, expected timelines for results, and links to supporting studies or resources."},
                    "forecast_timeline": {"type": "string","description": "Realistic timelines for closing specific performance gaps based on intervention studies, including milestones and expected progression rates."},
                    "red_flags": {"type": "string","description": "Warning signs or conditions where pursuing elite athlete metrics could be risky or require medical oversight. Include specific thresholds and contraindications."}
                },
                "required": [
                    "whoop_data_summary",
                    "athlete_norms_endurance","athlete_norms_strength","athlete_norms_team_sport","cohort_comparison_summary",
                    "training_interventions",
                    "top_3_cohort_matches","biggest_gaps","evidence_based_action_plan","forecast_timeline","red_flags"
                ],
                "additionalProperties": False
            }
        }
    }

def make_parallel_request(ngrok_url):
    """Make the request to Parallel AI with custom task spec"""
    headers = {
        "x-api-key": PARALLEL_API_KEY,
        "Content-Type": "application/json",
        "parallel-beta": "mcp-server-2025-07-17,events-sse-2025-07-24"
    }
    
    # Ensure the ngrok_url ends with /mcp
    mcp_url = ngrok_url.rstrip('/') + '/mcp'
    
    data = {
        "input": create_prompt(),
        "processor": "pro",
        "enable_events": True,
        "task_spec": create_task_spec(),  # Add custom schema
        "mcp_servers": [
            {
                "type": "url",
                "url": mcp_url,
                "name": "whoop_fitness_data",
                "headers": {"X-API-Key": MCP_API_KEY}
            }
        ]
    }
    
    response = requests.post(
        "https://api.parallel.ai/v1/tasks/runs",
        headers=headers,
        json=data
    )
    
    if response.status_code in [200, 202]:
        return response.json()["run_id"]
    else:
        console.print(f"[red]Error creating task: {response.text}[/red]")
        return None

def get_task_result(run_id):
    """Get the final task result from Parallel AI"""
    headers = {
        "x-api-key": PARALLEL_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"https://api.parallel.ai/v1/tasks/runs/{run_id}/result"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        console.print(f"[red]Error getting task result: {response.text}[/red]")
        return None

def display_structured_output(task_result):
    """Display the structured output with beautiful formatting"""
    if not task_result or "output" not in task_result:
        console.print("[red]No task output available[/red]")
        return
    
    output = task_result["output"]
    content_obj = output.get("content")
    
    if content_obj is None:
        console.print("[yellow]No content found in output[/yellow]")
        return
    
    try:
        # Calculate analysis stats
        content_str = json.dumps(content_obj, indent=2)
        text_len = len(content_str)
        estimated_pages = text_len // 3000
        
        console.print(f"\n[bold green]Analysis Complete![/bold green]")
        console.print(f"[dim]Total analysis: {text_len:,} characters (~{estimated_pages} pages)[/dim]\n")
        
        # Show basis preview first
        basis = output.get("basis", [])
        if basis:
            console.print("[bold bright_blue]📚 RESEARCH BASIS PREVIEW[/bold bright_blue]\n")
            
            for i, field in enumerate(basis[:5]):  # preview first 5 fields
                console.print(f"[bold cyan]{i+1}. Field:[/bold cyan] {field.get('field', 'Unknown')}")
                
                reasoning = field.get('reasoning', '')
                if reasoning:
                    truncated_reasoning = reasoning[:80] + "..." if len(reasoning) > 80 else reasoning
                    console.print(f"[dim]   Reasoning:[/dim] {truncated_reasoning}")
                
                citations = field.get('citations', [])
                if citations and len(citations) > 0:
                    citation = citations[0]
                    console.print(f"[dim]   Source:[/dim] {citation.get('url', 'N/A')}")
                    excerpts = citation.get('excerpts', [])
                    if excerpts and len(excerpts) > 0:
                        console.print(f"[dim]   Excerpt:[/dim] {excerpts[0][:100]}...")
                console.print()
            
            if len(basis) > 5:
                console.print(f"[dim]...and {len(basis) - 5} more fields captured![/dim]\n")
        
        # Show MCP tool calls if available
        mcp_tool_calls = output.get("mcp_tool_calls", [])
        if mcp_tool_calls:
            console.print("[bold magenta]MCP TOOL CALLS[/bold magenta]\n")
            
            for i, tool_call in enumerate(mcp_tool_calls[:3]):  # Show first 3
                console.print(f"[bold magenta]{i+1}. Tool:[/bold magenta] {tool_call.get('tool_name', 'Unknown')}")
                console.print(f"[dim]   Server:[/dim] {tool_call.get('server_name', 'Unknown')}")
                
                if tool_call.get('content'):
                    content_preview = tool_call['content'][:100] + "..." if len(tool_call['content']) > 100 else tool_call['content']
                    console.print(f"[dim]   Result:[/dim] {content_preview}")
                elif tool_call.get('error'):
                    console.print(f"[red]   Error:[/red] {tool_call['error']}")
                console.print()
            
            if len(mcp_tool_calls) > 3:
                console.print(f"[dim]...and {len(mcp_tool_calls) - 3} more tool calls![/dim]\n")
        
        # Handle the main content display
        if isinstance(content_obj, dict):
            console.print("[bold cyan]ATHLETE BENCHMARKING REPORT[/bold cyan]\n")
            
            # Helper function to create nice field titles
            def format_field_name(field_name):
                # Convert snake_case to Title Case
                return field_name.replace("_", " ").title()
            
            # Helper function to get appropriate color for field
            def get_field_color(field_name):
                if "rhr" in field_name.lower() or "heart" in field_name.lower():
                    return "red"
                elif "hrv" in field_name.lower():
                    return "green"
                elif "sleep" in field_name.lower():
                    return "blue"
                elif "strain" in field_name.lower() or "training" in field_name.lower():
                    return "yellow"
                elif "hypothesis" in field_name.lower() or "cause" in field_name.lower():
                    return "bright_red"
                elif "action" in field_name.lower() or "plan" in field_name.lower():
                    return "bright_green"
                elif "genetic" in field_name.lower():
                    return "purple"
                elif "red_flag" in field_name.lower() or "medical" in field_name.lower():
                    return "bright_red"
                elif "research" in field_name.lower() or "study" in field_name.lower():
                    return "cyan"
                else:
                    return "white"
            
            # Helper function to preview field content
            def get_field_preview(value, max_length=300):
                if isinstance(value, str):
                    if len(value) <= max_length:
                        return value
                    else:
                        return value[:max_length] + "..."
                elif isinstance(value, (int, float)):
                    return str(value)
                elif isinstance(value, dict):
                    # Format dict nicely
                    formatted = ""
                    for k, v in value.items():
                        formatted += f"• {k.replace('_', ' ').title()}: {v}\n"
                    return formatted.strip()[:max_length] + ("..." if len(formatted) > max_length else "")
                elif isinstance(value, list):
                    # Show first few items
                    items_preview = []
                    for item in value[:3]:
                        if isinstance(item, str):
                            items_preview.append(f"• {item[:100]}...")
                        else:
                            items_preview.append(f"• {str(item)[:100]}...")
                    result = "\n".join(items_preview)
                    if len(value) > 3:
                        result += f"\n... and {len(value) - 3} more items"
                    return result
                else:
                    return str(value)[:max_length] + ("..." if len(str(value)) > max_length else "")
            
            # Sort fields to show most important ones first
            priority_fields = [
                "whoop_data_summary", "cohort_comparison_summary", 
                "evidence_based_action_plan", "biggest_gaps"
            ]
            
            # Show priority fields first
            shown_fields = set()
            for priority_field in priority_fields:
                if priority_field in content_obj and content_obj[priority_field]:
                    field_title = format_field_name(priority_field)
                    field_color = get_field_color(priority_field)
                    preview_text = get_field_preview(content_obj[priority_field])
                    
                    field_panel = Panel(
                        preview_text,
                        title=f"[{field_color}]{field_title}[/{field_color}]",
                        border_style=field_color,
                        padding=(1, 1)
                    )
                    console.print(field_panel)
                    console.print()
                    shown_fields.add(priority_field)
            
            # Show remaining fields grouped by category
            remaining_fields = [k for k in content_obj.keys() if k not in shown_fields and content_obj[k]]
            
            if remaining_fields:
                # Group fields by category
                data_fields = [f for f in remaining_fields if any(x in f.lower() for x in ["whoop_data_summary", "summary"])]
                research_fields = [f for f in remaining_fields if any(x in f.lower() for x in ["norms", "athlete_norms"])]
                intervention_fields = [f for f in remaining_fields if any(x in f.lower() for x in ["training_interventions", "intervention", "forecast_timeline"])]
                analysis_fields = [f for f in remaining_fields if any(x in f.lower() for x in ["top_3_cohort_matches", "matches"])]
                clinical_fields = [f for f in remaining_fields if any(x in f.lower() for x in ["red_flag", "warning"])]
                other_fields = [f for f in remaining_fields if f not in data_fields + research_fields + intervention_fields + analysis_fields + clinical_fields]
                
                # Show data fields
                if data_fields:
                    console.print("[bold bright_green]📱 YOUR DATA[/bold bright_green]\n")
                    for field in data_fields:
                        field_title = format_field_name(field)
                        field_color = get_field_color(field)
                        preview_text = get_field_preview(content_obj[field], 150)  # Shorter for data fields
                        
                        field_panel = Panel(
                            preview_text,
                            title=f"[{field_color}]{field_title}[/{field_color}]",
                            border_style=field_color,
                            padding=(0, 1)
                        )
                        console.print(field_panel)
                    console.print()
                
                # Show research fields
                if research_fields:
                    console.print("[bold bright_blue]📚 RESEARCH FINDINGS[/bold bright_blue]\n")
                    for field in research_fields[:5]:  # Limit to top 5 research fields
                        field_title = format_field_name(field)
                        field_color = get_field_color(field)
                        preview_text = get_field_preview(content_obj[field], 400)
                        
                        field_panel = Panel(
                            preview_text,
                            title=f"[{field_color}]{field_title}[/{field_color}]",
                            border_style=field_color,
                            padding=(1, 1)
                        )
                        console.print(field_panel)
                        console.print()
                    
                    if len(research_fields) > 5:
                        console.print(f"[dim]...and {len(research_fields) - 5} more research fields available[/dim]\n")
                
                # Show intervention fields
                if intervention_fields:
                    console.print("[bold bright_cyan]💡 INTERVENTIONS & SOLUTIONS[/bold bright_cyan]\n")
                    for field in intervention_fields:
                        field_title = format_field_name(field)
                        field_color = get_field_color(field)
                        preview_text = get_field_preview(content_obj[field], 350)
                        
                        field_panel = Panel(
                            preview_text,
                            title=f"[{field_color}]{field_title}[/{field_color}]",
                            border_style=field_color,
                            padding=(1, 1)
                        )
                        console.print(field_panel)
                    console.print()
            
                # Show analysis fields
                if analysis_fields:
                    console.print("[bold bright_magenta]🎯 ATHLETE COMPARISONS[/bold bright_magenta]\n")
                    for field in analysis_fields:
                        field_title = format_field_name(field)
                        field_color = get_field_color(field)
                        preview_text = get_field_preview(content_obj[field], 350)
                        
                        field_panel = Panel(
                            preview_text,
                            title=f"[{field_color}]{field_title}[/{field_color}]",
                            border_style=field_color,
                            padding=(1, 1)
                        )
                        console.print(field_panel)
                            console.print()
            
                # Show clinical fields
                if clinical_fields:
                    console.print("[bold bright_red]⚠️ CLINICAL CONSIDERATIONS[/bold bright_red]\n")
                    for field in clinical_fields:
                        field_title = format_field_name(field)
                        field_color = get_field_color(field)
                        preview_text = get_field_preview(content_obj[field], 350)
                        
                        field_panel = Panel(
                            preview_text,
                            title=f"[{field_color}]{field_title}[/{field_color}]",
                            border_style=field_color,
                            padding=(1, 1)
                        )
                        console.print(field_panel)
                        console.print()
            
                # Show other fields if any
                if other_fields:
                    console.print("[bold white]📋 ADDITIONAL INSIGHTS[/bold white]\n")
                    for field in other_fields[:3]:  # Limit to avoid clutter
                        field_title = format_field_name(field)
                        field_color = get_field_color(field)
                        preview_text = get_field_preview(content_obj[field], 250)
                        
                        field_panel = Panel(
                            preview_text,
                            title=f"[{field_color}]{field_title}[/{field_color}]",
                            border_style=field_color,
                            padding=(1, 1)
                        )
                        console.print(field_panel)
                        console.print()
                    
                    if len(other_fields) > 3:
                        console.print(f"[dim]...and {len(other_fields) - 3} more fields available[/dim]\n")
                    
        else:
            # Fallback for non-dict content or unexpected structure
            preview_panel = Panel(
                content_str[:2000] + "..." if len(content_str) > 2000 else content_str,
                title="🔍 Raw Analysis Content",
                border_style="cyan",
                padding=(1, 2)
            )
            console.print(preview_panel)
            
    except Exception as e:
        console.print(f"[red]Error displaying structured output: {e}[/red]")
        console.print(f"[dim]Raw content type: {type(content_obj)}[/dim]")
        if isinstance(content_obj, dict):
            console.print(f"[dim]Available keys: {list(content_obj.keys())}[/dim]")

def stream_events(run_id):
    """Stream SSE events from Parallel AI"""
    headers = {
        "x-api-key": PARALLEL_API_KEY,
        "Accept": "text/event-stream",
        "parallel-beta": "events-sse-2025-07-24"
    }
    
    url = f"https://api.parallel.ai/v1beta/tasks/runs/{run_id}/events"
    
    try:
        response = requests.get(url, headers=headers, stream=True)
        
        if response.status_code != 200:
            console.print(f"[red]❌ HTTP {response.status_code}: {response.text}[/red]")
            return
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                        yield event_data
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        console.print(f"[red]Error streaming events: {e}[/red]")

def main():
    """Main demo function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate required environment variables
    if not PARALLEL_API_KEY:
        console.print("[red]Error: PARALLEL_API_KEY environment variable is required[/red]")
        console.print("[yellow]Please set your Parallel AI API key:[/yellow]")
        console.print("export PARALLEL_API_KEY='your_api_key_here'")
        return
    
    console.clear()
    console.print(create_header())
    console.print()
    
    # Display the ngrok URL being used
    mcp_url = args.ngrok_url.rstrip('/') + '/mcp'
    console.print(f"[dim]Using MCP URL: {mcp_url}[/dim]")
    console.print()
    
    # Step 1: Create task
    with console.status("[bold green]Creating Parallel AI task with WHOOP MCP integration..."):
        run_id = make_parallel_request(args.ngrok_url)
    
    if not run_id:
        return
    
    console.print(f"[green]✅ Task created: {run_id}[/green]")
    console.print()
    
    # Step 2: Stream events
    console.print("[bold cyan]🔴 LIVE: Streaming real-time analysis...[/bold cyan]")
    console.print()
    
    events_displayed = []
    final_output = None
    previous_sources_considered = 0  # Track previous sources considered count
    
    try:
        task_completed = False
        reconnect_count = 0
        max_reconnects = 10
        
        while not task_completed and reconnect_count < max_reconnects:
            try:
                # Only show reconnection attempts, not the first connection
                if reconnect_count > 0:
                    console.print(f"[dim]🔗 Reconnecting to event stream (attempt {reconnect_count + 1})...[/dim]")
                
                for event in stream_events(run_id):
                    event_type = event.get("type", "unknown")
                    
                    # Handle different event types
                    if event_type == "task_run.state":
                        status = event.get("run", {}).get("status", "unknown")
                        console.print(f"[blue]📊 Task Status: {status}[/blue]")
                        
                        # Check for completion
                        if status == "completed":
                            task_completed = True
                            final_output = True  # Mark as completed to fetch full result
                            break
                        elif status in ["failed", "cancelled"]:
                            console.print(f"[red]❌ Task {status}[/red]")
                            task_completed = True
                            break
                            
                    elif event_type.startswith("task_run.progress_msg"):
                        message = event.get("message", "No message")
                        timestamp = event.get("timestamp")
                        
                        # Create and display event panel
                        panel = create_event_panel(event_type, message, timestamp)
                        console.print(panel)
                        
                        # Special emphasis for AI reasoning
                        if event_type == "task_run.progress_msg.plan":
                            console.print(f"[dim bright_green]🧠 Agent is strategizing...[/dim bright_green]")
                        elif event_type == "task_run.progress_msg.tool":
                            console.print(f"[dim cyan]🔧 Tool reasoning complete[/dim cyan]")
                        
                        # Add delay for dramatic effect  
                        time.sleep(0.5)
                        
                    elif event_type == "task_run.progress_stats":
                        stats = event.get("source_stats", {})
                        sources_considered = stats.get("num_sources_considered", 0)
                        sources_read = stats.get("num_sources_read", 0)
                        sources_sample = stats.get("sources_read_sample", [])
                        
                        # Only display progress if sources_considered > 0 and > previous count
                        if sources_considered > 0 and sources_considered > previous_sources_considered:
                            # Show progress with most recent 5 sources
                            progress_text = f"📈 Research Progress: {sources_read}/{sources_considered} sources analyzed"
                            
                            if sources_sample:
                                # Show most recent 5 sources, truncated for readability
                                top_sources = []
                                for source in sources_sample[-5:]:
                                    # Truncate long URLs and clean them up
                                    clean_source = source.replace("http://", "").replace("https://", "")
                                    if len(clean_source) > 50:
                                        clean_source = clean_source[:47] + "..."
                                    top_sources.append(clean_source)
                                
                                sources_text = "\n".join([f"   • {source}" for source in top_sources])
                                if len(sources_sample) > 5:
                                    sources_text += f"\n   ...and {len(sources_sample) - 5} more"
                                
                                progress_panel = Panel(
                                    f"{progress_text}\n\nMost recent sources:\n{sources_text}",
                                    title="📊 Research Progress",
                                    border_style="blue",
                                    padding=(0, 1)
                                )
                                console.print(progress_panel)
                            else:
                                console.print(f"[dim]{progress_text}[/dim]")
                            
                            # Update previous count after displaying
                            previous_sources_considered = sources_considered
                    
                    else:
                        # Catch any other event types we haven't handled
                        if event_type not in ["task_run.state", "task_run.progress_stats"] and not event_type.startswith("task_run.progress_msg"):
                            console.print(f"[dim yellow]🔔 Unhandled event: {event_type}[/dim yellow]")
                            if "message" in event:
                                console.print(f"[dim]   Message: {event['message']}[/dim]")
                
                # If we get here, the stream ended without completion - reconnect
                if not task_completed:
                    reconnect_count += 1
                    console.print(f"[yellow]🔄 Stream ended, reconnecting... ({reconnect_count}/{max_reconnects})[/yellow]")
                    time.sleep(2)  # Brief delay before reconnecting
                    
            except Exception as stream_error:
                console.print(f"[red]Stream error: {stream_error}[/red]")
                reconnect_count += 1
                if reconnect_count < max_reconnects:
                    console.print(f"[yellow]🔄 Reconnecting... ({reconnect_count}/{max_reconnects})[/yellow]")
                    time.sleep(2)
                else:
                    console.print(f"[red]Max reconnection attempts reached[/red]")
                    break
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
        return
    
    # Step 3: Get and display complete task result
    if final_output:
        console.print("\n" + "="*80)
        console.print("[bold cyan]Fetching complete task result...[/bold cyan]")
        
        task_result = get_task_result(run_id)
        if task_result:
            display_structured_output(task_result)
        else:
            console.print("[red]Failed to retrieve task result[/red]")
    else:
        console.print("[yellow]Task did not complete during demo session[/yellow]")
    
    console.print("\n[bold green]Demo completed! Your WHOOP data was benchmarked against athlete cohorts in real-time via MCP.[/bold green]")

if __name__ == "__main__":
    main()

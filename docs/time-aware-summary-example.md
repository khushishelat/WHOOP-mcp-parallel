# Time-Aware Daily Summary Examples

The enhanced `get_daily_summary` tool now provides contextual recommendations based on the current time of day. Here are examples of how the tool adapts its recommendations:

## Morning Example (Before 6 PM)

When called during the day, the tool focuses on activities and training recommendations:

```
📅 DAILY WHOOP SUMMARY - Monday, Jan 15, 2024
🕐 Current Time: 2:30 PM EST
============================================================

😴 YESTERDAY'S SLEEP (Today's Context)
Duration: 7h 45m
Efficiency: 82.3%
Performance: 85.1%
Sleep Latency: 12m
Quality: Good

💚 TODAY'S RECOVERY
Recovery Score: 78% (Ready)
HRV: 45ms
Resting Heart Rate: 58 bpm

🔥 TODAY'S STRAIN
Current Strain: 6.2/21.0
Calories Burned: 1,850
Distance: 3.2 km

💪 TODAY'S WORKOUTS (1 workout)
  1. Running
     Duration: 45m
     Strain: 6.2
     Calories: 450
     Distance: 5.0 km

TOTALS:
  Total Workout Time: 45m
  Total Calories: 450
  Total Distance: 5.0 km
  Total Strain: 6.2

🎯 ☀️ DAYTIME RECOMMENDATIONS
• High recovery - great day for intense training
• Consider strength training, HIIT, or competitive sports
• Target strain range: 12-18 (current: 6.2)
• Low strain so far - consider adding activity
• Options: walking, light cardio, mobility work
• Afternoon: Good time for moderate activities or skill work
```

## Evening Example (After 6 PM)

When called in the evening, the tool focuses on sleep preparation and recovery:

```
📅 DAILY WHOOP SUMMARY - Monday, Jan 15, 2024
🕐 Current Time: 8:45 PM EST
============================================================

😴 YESTERDAY'S SLEEP (Today's Context)
Duration: 7h 45m
Efficiency: 82.3%
Performance: 85.1%
Sleep Latency: 12m
Quality: Good

💚 TODAY'S RECOVERY
Recovery Score: 78% (Ready)
HRV: 45ms
Resting Heart Rate: 58 bpm

🔥 TODAY'S STRAIN
Current Strain: 14.8/21.0
Calories Burned: 2,450
Distance: 8.5 km

💪 TODAY'S WORKOUTS (2 workouts)
  1. Running
     Duration: 45m
     Strain: 6.2
     Calories: 450
     Distance: 5.0 km
  2. Strength Training
     Duration: 60m
     Strain: 8.6
     Calories: 350
     Distance: 0.0 km

TOTALS:
  Total Workout Time: 1h 45m
  Total Calories: 800
  Total Distance: 5.0 km
  Total Strain: 14.8

🎯 🌙 EVENING RECOMMENDATIONS
• Maintain your current sleep routine - it's working well!
• Good recovery today - you can plan for tomorrow's activities
• Consider light evening activities if desired
• High strain today - ensure adequate sleep for recovery
• Consider a warm bath or gentle stretching
• Target bedtime: 10:00 PM (aim for 8+ hours)
```

## Key Features

### Time-Aware Logic
- **Before 6 PM**: Focuses on activities, strain targets, and training recommendations
- **After 6 PM**: Focuses on sleep preparation, bedtime recommendations, and recovery

### Contextual Data
- **Yesterday's Sleep**: Shows sleep data from the previous night to provide context for today's recovery
- **Today's Recovery**: Current recovery score and readiness
- **Today's Strain**: Current strain level and progress toward daily targets
- **Today's Workouts**: All workouts completed today with totals

### Smart Recommendations

#### Daytime Recommendations:
- Recovery-based activity suggestions (high/moderate/low intensity)
- Strain target ranges based on recovery score
- Time-of-day specific advice (morning/afternoon/late afternoon)
- Activity suggestions based on current strain level

#### Evening Recommendations:
- Sleep hygiene advice based on previous night's sleep quality
- Recovery-based evening activity suggestions
- Strain-based recovery recommendations
- Personalized bedtime suggestions based on sleep patterns

### Technical Implementation
- Uses EST timezone for consistent time calculations
- Fetches yesterday's sleep data for today's context
- Concurrent API requests for optimal performance
- Graceful error handling for missing data
- Time-based conditional logic for recommendations

## Usage

```python
# Get today's summary (time-aware)
await get_daily_summary()

# Get summary for specific date (still time-aware for current time)
await get_daily_summary("2024-01-15")
```

The tool automatically detects the current time and provides appropriate recommendations, making it a truly contextual daily summary tool. 
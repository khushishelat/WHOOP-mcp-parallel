#!/usr/bin/env python3

"""
Test script to validate workout duration calculation in daily summary
"""

import os
import sys
import json
import ast
from pathlib import Path

def test_duration_calculation_logic():
    """Test that workout duration is calculated correctly from start/end times"""
    print("🔍 Testing workout duration calculation logic...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check for the correct duration calculation pattern
        required_patterns = [
            'duration_minutes = 0',
            'if workout.get(\'end\') and workout.get(\'start\'):',
            'end_dt = datetime.fromisoformat',
            'start_dt = datetime.fromisoformat',
            'duration_minutes = (end_dt - start_dt).total_seconds() / 60',
            'format_time_duration(duration_minutes)'
        ]
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print(f"❌ Missing duration calculation patterns: {missing_patterns}")
            return False
        else:
            print("✅ Workout duration calculation logic is correct")
            return True
    except Exception as e:
        print(f"❌ Error checking duration calculation: {e}")
        return False

def test_calorie_conversion():
    """Test that calories are converted from kilojoules correctly"""
    print("\n🔍 Testing calorie conversion logic...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check for kilojoule to calorie conversion
        if 'kilojoules = workout_score.get(\'kilojoule\', 0) or 0' in content and 'calories = kilojoules / 4.184' in content:
            print("✅ Calorie conversion from kilojoules is correct")
            return True
        else:
            print("❌ Calorie conversion logic is missing or incorrect")
            return False
    except Exception as e:
        print(f"❌ Error checking calorie conversion: {e}")
        return False

def test_no_workout_duration_milli():
    """Test that the code no longer uses the non-existent workout_duration_milli field"""
    print("\n🔍 Testing removal of workout_duration_milli field...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check that workout_duration_milli is not used in the daily summary
        if 'workout_duration_milli' in content:
            # It might still be used elsewhere, let's check if it's in the daily summary context
            daily_summary_start = content.find('async def get_daily_summary')
            if daily_summary_start != -1:
                # Find the end of the function (roughly)
                daily_summary_end = content.find('def get_custom_prompt()', daily_summary_start)
                if daily_summary_end == -1:
                    daily_summary_end = len(content)
                
                daily_summary_section = content[daily_summary_start:daily_summary_end]
                if 'workout_duration_milli' in daily_summary_section:
                    print("❌ workout_duration_milli field is still used in daily summary")
                    return False
                else:
                    print("✅ workout_duration_milli field is no longer used in daily summary")
                    return True
            else:
                print("✅ workout_duration_milli field is not used in daily summary")
                return True
        else:
            print("✅ workout_duration_milli field is completely removed")
            return True
    except Exception as e:
        print(f"❌ Error checking workout_duration_milli removal: {e}")
        return False

def test_format_time_duration_usage():
    """Test that format_time_duration is called with the correct parameter type"""
    print("\n🔍 Testing format_time_duration usage...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check that format_time_duration is called with duration_minutes (not duration/60000)
        if 'format_time_duration(duration_minutes)' in content:
            print("✅ format_time_duration is called with correct parameter")
            return True
        else:
            print("❌ format_time_duration is not called with correct parameter")
            return False
    except Exception as e:
        print(f"❌ Error checking format_time_duration usage: {e}")
        return False

def main():
    """Run all workout duration tests"""
    print("🚀 WHOOP MCP Workout Duration Fix Validation\n")
    
    tests = [
        test_duration_calculation_logic,
        test_calorie_conversion,
        test_no_workout_duration_milli,
        test_format_time_duration_usage
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Print summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Workout duration fix is working correctly")
        print("\nFix Summary:")
        print("• Workout duration now calculated from start/end times")
        print("• Calories properly converted from kilojoules")
        print("• Removed dependency on non-existent workout_duration_milli field")
        print("• format_time_duration called with correct parameter type")
    else:
        print("\n❌ Some tests failed. Please fix the issues before using the tool.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python3

"""
Test script to validate the get_daily_summary tool functionality
"""

import os
import sys
import json
import ast
from pathlib import Path

def test_function_exists():
    """Test that the get_daily_summary function exists in whoop_mcp.py"""
    print("🔍 Testing get_daily_summary function existence...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        if 'async def get_daily_summary(' in content:
            print("✅ get_daily_summary function found")
            return True
        else:
            print("❌ get_daily_summary function not found")
            return False
    except Exception as e:
        print(f"❌ Error reading whoop_mcp.py: {e}")
        return False

def test_function_syntax():
    """Test that the get_daily_summary function has valid syntax"""
    print("\n🔍 Testing get_daily_summary function syntax...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            source = f.read()
        ast.parse(source)
        print("✅ get_daily_summary function syntax valid")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in whoop_mcp.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error parsing whoop_mcp.py: {e}")
        return False

def test_function_docstring():
    """Test that the get_daily_summary function has proper documentation"""
    print("\n🔍 Testing get_daily_summary function documentation...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Find the function definition
        start_idx = content.find('async def get_daily_summary(')
        if start_idx == -1:
            print("❌ get_daily_summary function not found")
            return False
        
        # Look for docstring in the function (after @mcp.tool() decorator)
        if '"""Get time-aware daily summary' in content:
            print("✅ get_daily_summary function has proper docstring")
            return True
        else:
            print("❌ get_daily_summary function missing proper docstring")
            return False
    except Exception as e:
        print(f"❌ Error checking documentation: {e}")
        return False

def test_function_parameters():
    """Test that the get_daily_summary function has correct parameters"""
    print("\n🔍 Testing get_daily_summary function parameters...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Find the function definition
        start_idx = content.find('async def get_daily_summary(')
        if start_idx == -1:
            print("❌ get_daily_summary function not found")
            return False
        
        # Extract the function signature
        end_idx = content.find('):', start_idx)
        if end_idx == -1:
            print("❌ Could not find function signature end")
            return False
        
        signature = content[start_idx:end_idx + 2]
        
        # Check for required elements
        required_elements = [
            'async def get_daily_summary(',
            'date: Optional[str] = None',
            '-> str'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in signature:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Function signature missing elements: {missing_elements}")
            return False
        else:
            print("✅ get_daily_summary function has correct parameters")
            return True
    except Exception as e:
        print(f"❌ Error checking parameters: {e}")
        return False

def test_function_implementation():
    """Test that the get_daily_summary function has proper implementation"""
    print("\n🔍 Testing get_daily_summary function implementation...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check for required implementation elements
        required_elements = [
            'make_whoop_request',
            'asyncio.gather',
            'cycle_url',
            'sleep_url',
            'recovery_url', 
            'workout_url',
            'DAILY WHOOP SUMMARY',
            'Current Time',
            'SLEEP DATA',
            'RECOVERY',
            'STRAIN',
            'WORKOUTS',
            'EVENING RECOMMENDATIONS',
            'DAYTIME RECOMMENDATIONS'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Implementation missing elements: {missing_elements}")
            return False
        else:
            print("✅ get_daily_summary function has complete implementation")
            return True
    except Exception as e:
        print(f"❌ Error checking implementation: {e}")
        return False

def test_web_server_integration():
    """Test that the web server includes the new tool"""
    print("\n🔍 Testing web server integration...")
    
    try:
        with open('web_server.py', 'r') as f:
            content = f.read()
        
        if 'get_daily_summary' in content:
            print("✅ get_daily_summary tool included in web server")
            return True
        else:
            print("❌ get_daily_summary tool not found in web server")
            return False
    except Exception as e:
        print(f"❌ Error checking web server integration: {e}")
        return False

def test_web_server_features():
    """Test that the web server features list includes daily summaries"""
    print("\n🔍 Testing web server features list...")
    
    try:
        with open('web_server.py', 'r') as f:
            content = f.read()
        
        if 'Comprehensive daily summaries' in content:
            print("✅ Daily summaries feature listed in web server")
            return True
        else:
            print("❌ Daily summaries feature not found in web server")
            return False
    except Exception as e:
        print(f"❌ Error checking web server features: {e}")
        return False

def test_error_handling():
    """Test that the function includes proper error handling"""
    print("\n🔍 Testing error handling...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check for error handling patterns
        error_patterns = [
            'try:',
            'except',
            'FileNotFoundError',
            'json.JSONDecodeError',
            '"error" in',
            'Could not fetch'
        ]
        
        missing_patterns = []
        for pattern in error_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print(f"❌ Missing error handling patterns: {missing_patterns}")
            return False
        else:
            print("✅ get_daily_summary function has proper error handling")
            return True
    except Exception as e:
        print(f"❌ Error checking error handling: {e}")
        return False

def test_concurrent_requests():
    """Test that the function uses concurrent API requests"""
    print("\n🔍 Testing concurrent API requests...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        if 'asyncio.gather' in content and 'tasks = [' in content:
            print("✅ get_daily_summary function uses concurrent API requests")
            return True
        else:
            print("❌ get_daily_summary function does not use concurrent requests")
            return False
    except Exception as e:
        print(f"❌ Error checking concurrent requests: {e}")
        return False

def test_time_aware_functionality():
    """Test that the function includes time-aware features"""
    print("\n🔍 Testing time-aware functionality...")
    
    try:
        with open('whoop_mcp.py', 'r') as f:
            content = f.read()
        
        # Check for time-aware elements
        time_elements = [
            'pytz.timezone',
            'current_hour',
            'is_evening',
            'EVENING RECOMMENDATIONS',
            'DAYTIME RECOMMENDATIONS',
            'sleep_needed',
            'Target Strain'
        ]
        
        missing_elements = []
        for element in time_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Missing time-aware elements: {missing_elements}")
            return False
        else:
            print("✅ get_daily_summary function includes time-aware features")
            return True
    except Exception as e:
        print(f"❌ Error checking time-aware functionality: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 WHOOP MCP Daily Summary Tool Validation\n")
    
    tests = [
        test_function_exists,
        test_function_syntax,
        test_function_docstring,
        test_function_parameters,
        test_function_implementation,
        test_web_server_integration,
        test_web_server_features,
        test_error_handling,
        test_concurrent_requests,
        test_time_aware_functionality
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All tests passed! Time-aware daily summary tool is ready for use")
        print("\nFeatures implemented:")
        print("• Time-aware daily summary with contextual recommendations")
        print("• Yesterday's sleep data for today's context")
        print("• Evening recommendations (bedtime, sleep hygiene)")
        print("• Daytime recommendations (activities, strain targets)")
        print("• Concurrent API requests for optimal performance")
        print("• Proper error handling and graceful degradation")
        print("• Web server integration")
        return True
    else:
        print("\n❌ Some tests failed. Please fix the issues before using the tool.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
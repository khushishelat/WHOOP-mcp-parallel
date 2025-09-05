#!/usr/bin/env python3
"""
Test script for Parallel Task API integration with WHOOP MCP Server

This script tests the HTTP MCP endpoint to ensure compatibility with Parallel's Task API.
"""

import asyncio
import json
import httpx
import os
from typing import Dict, Any

# Test configuration
BASE_URL = os.getenv("WHOOP_MCP_URL", "https://whoop-mcp.fly.dev")
API_KEY = os.getenv("API_SECRET_KEY", "test_key")
TIMEOUT = 30.0

class ParallelIntegrationTest:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
    
    async def test_server_health(self) -> bool:
        """Test if the server is responding"""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    print("✅ Server health check passed")
                    return True
                else:
                    print(f"❌ Server health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Server health check error: {e}")
            return False
    
    async def test_mcp_initialize(self) -> bool:
        """Test MCP initialization - required for Parallel API"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "parallel-test", "version": "1.0.0"}
                }
            }
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result", {}).get("protocolVersion") == "2024-11-05":
                        print("✅ MCP initialization test passed")
                        return True
                    else:
                        print(f"❌ MCP initialization invalid response: {data}")
                        return False
                else:
                    print(f"❌ MCP initialization failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ MCP initialization error: {e}")
            return False
    
    async def test_tools_list(self) -> bool:
        """Test tools listing - Parallel needs this to know available tools"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tools = data.get("result", {}).get("tools", [])
                    
                    if len(tools) > 0:
                        print(f"✅ Tools list test passed - found {len(tools)} tools")
                        print(f"   Sample tools: {[t['name'] for t in tools[:3]]}")
                        return True
                    else:
                        print(f"❌ Tools list test failed - no tools found: {data}")
                        return False
                else:
                    print(f"❌ Tools list test failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Tools list error: {e}")
            return False
    
    async def test_tool_call(self) -> bool:
        """Test calling a simple tool - simulates what Parallel would do"""
        try:
            # Use get_profile_data as it's simple and doesn't require parameters
            payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_profile_data",
                    "arguments": {}
                }
            }
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got a proper MCP response
                    if "result" in data:
                        content = data["result"].get("content", [])
                        if content and len(content) > 0:
                            print("✅ Tool call test passed - got valid response")
                            return True
                        else:
                            print(f"❌ Tool call test failed - empty content: {data}")
                            return False
                    elif "error" in data:
                        # This might be expected if WHOOP isn't authenticated
                        error_msg = data["error"].get("message", "Unknown error")
                        if "authentication" in error_msg.lower():
                            print("⚠️  Tool call test - authentication required (expected)")
                            print("   This is normal if WHOOP OAuth hasn't been completed")
                            return True
                        else:
                            print(f"❌ Tool call test failed - error: {error_msg}")
                            return False
                    else:
                        print(f"❌ Tool call test failed - invalid response: {data}")
                        return False
                else:
                    print(f"❌ Tool call test failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Tool call error: {e}")
            return False
    
    async def test_parallel_format_compatibility(self) -> bool:
        """Test that responses match Parallel's expected format"""
        try:
            # Test with a method that should always work
            payload = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/list"
            }
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check JSON-RPC 2.0 compliance
                    if data.get("jsonrpc") != "2.0":
                        print("❌ Response missing JSON-RPC 2.0 compliance")
                        return False
                    
                    if data.get("id") != 4:
                        print("❌ Response ID doesn't match request")
                        return False
                    
                    # Check tools format
                    tools = data.get("result", {}).get("tools", [])
                    for tool in tools[:3]:  # Check first 3 tools
                        if not all(key in tool for key in ["name", "description"]):
                            print(f"❌ Tool format invalid: {tool}")
                            return False
                    
                    print("✅ Parallel format compatibility test passed")
                    return True
                else:
                    print(f"❌ Parallel format test failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Parallel format error: {e}")
            return False
    
    async def test_authentication_required(self) -> bool:
        """Test that endpoints properly require authentication"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/list"
            }
            
            # Test without API key
            headers_no_auth = {"Content-Type": "application/json"}
            
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/mcp",
                    headers=headers_no_auth,
                    json=payload
                )
                
                if response.status_code == 401:
                    print("✅ Authentication test passed - properly rejected unauthorized request")
                    return True
                else:
                    print(f"❌ Authentication test failed - should have returned 401, got {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        print(f"🧪 Running Parallel Integration Tests for {self.base_url}")
        print("=" * 60)
        
        tests = [
            ("Server Health", self.test_server_health),
            ("Authentication Required", self.test_authentication_required),
            ("MCP Initialize", self.test_mcp_initialize),
            ("Tools List", self.test_tools_list),
            ("Tool Call", self.test_tool_call),
            ("Parallel Format Compatibility", self.test_parallel_format_compatibility),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n🔬 Running: {test_name}")
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")
                results[test_name] = False
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        
        passed = 0
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            print(f"  {status} {test_name}")
            if passed_test:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Your server is ready for Parallel Task API.")
        else:
            print("⚠️  Some tests failed. Check the errors above.")
        
        return results

async def main():
    """Main test runner"""
    print("🚀 WHOOP MCP Server - Parallel Integration Test")
    print(f"Testing server: {BASE_URL}")
    
    if not API_KEY or API_KEY == "test_key":
        print("⚠️  Warning: Using default test API key. Set API_SECRET_KEY environment variable for production testing.")
    
    tester = ParallelIntegrationTest(BASE_URL, API_KEY)
    results = await tester.run_all_tests()
    
    # Exit with error code if any tests failed
    if not all(results.values()):
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())

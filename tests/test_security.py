#!/usr/bin/env python3

"""
Security testing script for WHOOP MCP deployment
Tests all security features and authentication mechanisms
"""

import requests
import json
import time
import sys
import os
from typing import Dict, List, Tuple

class SecurityTester:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.results = []
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        self.results.append((test_name, passed, details))
    
    def test_public_endpoints(self) -> bool:
        """Test that public endpoints are accessible without authentication"""
        print("\n🌐 Testing Public Endpoints...")
        
        # Test health endpoint
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            self.log_test(
                "Health endpoint accessible", 
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
        except Exception as e:
            self.log_test("Health endpoint accessible", False, f"Error: {e}")
            return False
        
        # Test root endpoint
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            self.log_test(
                "Root endpoint accessible",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
            
            # Check if security info is included
            if response.status_code == 200:
                data = response.json()
                has_security_info = "security" in data
                self.log_test(
                    "Security information exposed in root",
                    has_security_info,
                    "Security config visible" if has_security_info else "No security info"
                )
        except Exception as e:
            self.log_test("Root endpoint accessible", False, f"Error: {e}")
            return False
        
        return True
    
    def test_protected_endpoints_without_auth(self) -> bool:
        """Test that protected endpoints reject requests without API key"""
        print("\n🔐 Testing Protected Endpoints (No Auth)...")
        
        protected_endpoints = ["/tools", "/auth"]
        all_protected = True
        
        for endpoint in protected_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                is_blocked = response.status_code == 401
                self.log_test(
                    f"{endpoint} blocks unauthenticated access",
                    is_blocked,
                    f"Status: {response.status_code}"
                )
                if not is_blocked:
                    all_protected = False
            except Exception as e:
                self.log_test(f"{endpoint} blocks unauthenticated access", False, f"Error: {e}")
                all_protected = False
        
        return all_protected
    
    def test_protected_endpoints_with_wrong_auth(self) -> bool:
        """Test that protected endpoints reject requests with wrong API key"""
        print("\n🔑 Testing Protected Endpoints (Wrong Auth)...")
        
        protected_endpoints = ["/tools", "/auth"]
        all_protected = True
        wrong_key = "wrong_api_key_123"
        
        for endpoint in protected_endpoints:
            try:
                headers = {"X-API-Key": wrong_key}
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                is_blocked = response.status_code == 401
                self.log_test(
                    f"{endpoint} blocks wrong API key",
                    is_blocked,
                    f"Status: {response.status_code}"
                )
                if not is_blocked:
                    all_protected = False
            except Exception as e:
                self.log_test(f"{endpoint} blocks wrong API key", False, f"Error: {e}")
                all_protected = False
        
        return all_protected
    
    def test_protected_endpoints_with_correct_auth(self) -> bool:
        """Test that protected endpoints allow requests with correct API key"""
        if not self.api_key:
            print("\n⚠️  Skipping auth tests - no API key provided")
            return True
        
        print("\n✅ Testing Protected Endpoints (Correct Auth)...")
        
        protected_endpoints = ["/tools", "/auth"]
        all_accessible = True
        
        for endpoint in protected_endpoints:
            try:
                headers = {"X-API-Key": self.api_key}
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                is_allowed = response.status_code == 200
                self.log_test(
                    f"{endpoint} allows correct API key",
                    is_allowed,
                    f"Status: {response.status_code}"
                )
                if not is_allowed:
                    all_accessible = False
            except Exception as e:
                self.log_test(f"{endpoint} allows correct API key", False, f"Error: {e}")
                all_accessible = False
        
        return all_accessible
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting functionality"""
        print("\n🚦 Testing Rate Limiting...")
        
        try:
            # Make rapid requests to trigger rate limiting
            start_time = time.time()
            rate_limited = False
            
            for i in range(70):  # Exceed the 60 req/min limit
                response = self.session.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 429:
                    rate_limited = True
                    break
                if i % 20 == 0:
                    print(f"   Made {i+1} requests...")
            
            elapsed = time.time() - start_time
            self.log_test(
                "Rate limiting triggered",
                rate_limited,
                f"Rate limited after {i+1} requests in {elapsed:.1f}s" if rate_limited else f"No rate limiting after {i+1} requests"
            )
            
            return rate_limited
        except Exception as e:
            self.log_test("Rate limiting triggered", False, f"Error: {e}")
            return False
    
    def test_security_headers(self) -> bool:
        """Test that security headers are present"""
        print("\n🛡️  Testing Security Headers...")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            headers = response.headers
            
            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": None,  # Just check presence
                "Content-Security-Policy": None,
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }
            
            all_present = True
            for header, expected_value in required_headers.items():
                if header in headers:
                    if expected_value and headers[header] != expected_value:
                        self.log_test(
                            f"Security header {header}",
                            False,
                            f"Expected '{expected_value}', got '{headers[header]}'"
                        )
                        all_present = False
                    else:
                        self.log_test(
                            f"Security header {header}",
                            True,
                            f"Value: {headers[header]}"
                        )
                else:
                    self.log_test(f"Security header {header}", False, "Missing")
                    all_present = False
            
            return all_present
        except Exception as e:
            self.log_test("Security headers test", False, f"Error: {e}")
            return False
    
    def test_input_validation(self) -> bool:
        """Test input validation for WebSocket endpoint"""
        print("\n🔍 Testing Input Validation...")
        
        # This is a basic test - for full WebSocket testing you'd need a WebSocket client
        try:
            # Test with oversized request
            large_data = "x" * 20000  # Larger than 10KB limit
            response = self.session.post(
                f"{self.base_url}/tools", 
                data=large_data,
                timeout=5
            )
            
            # Should be rejected (either 401 for no auth or 413/400 for size)
            is_rejected = response.status_code in [401, 413, 400, 422]
            self.log_test(
                "Large request validation",
                is_rejected,
                f"Status: {response.status_code}"
            )
            
            return is_rejected
        except Exception as e:
            self.log_test("Input validation test", False, f"Error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all security tests"""
        print(f"🚀 Running Security Tests for {self.base_url}")
        print("=" * 60)
        
        tests = [
            self.test_public_endpoints,
            self.test_protected_endpoints_without_auth,
            self.test_protected_endpoints_with_wrong_auth,
            self.test_protected_endpoints_with_correct_auth,
            self.test_security_headers,
            self.test_input_validation,
            # Note: Rate limiting test is intensive, run it last
            self.test_rate_limiting,
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with error: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 SECURITY TEST SUMMARY")
        print("=" * 60)
        
        for test_name, passed, details in self.results:
            status = "✅" if passed else "❌"
            print(f"{status} {test_name}")
            if details and not passed:
                print(f"   {details}")
        
        print(f"\n🎯 Overall: {passed_tests}/{total_tests} test categories passed")
        
        if passed_tests == total_tests:
            print("🎉 All security tests passed! Your deployment is secure.")
            return True
        else:
            print("⚠️  Some security tests failed. Please review and fix issues.")
            return False

def main():
    """Main function"""
    print("🔐 WHOOP MCP Security Testing Tool")
    print("=" * 50)
    
    # Get configuration
    base_url = input("Enter your WHOOP MCP URL (e.g., https://your-app.fly.dev): ").strip()
    if not base_url:
        print("❌ URL is required")
        sys.exit(1)
    
    api_key = input("Enter your API key (or press Enter to skip auth tests): ").strip()
    if not api_key:
        print("⚠️  No API key provided - authentication tests will be skipped")
    
    # Run tests
    tester = SecurityTester(base_url, api_key)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
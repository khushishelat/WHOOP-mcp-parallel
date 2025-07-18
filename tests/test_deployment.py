#!/usr/bin/env python3

"""
Test script to validate WHOOP MCP deployment setup
"""

import os
import sys
import json
import ast
from pathlib import Path

def test_file_structure():
    """Test that all required files exist"""
    print("🔍 Testing file structure...")
    
    required_files = [
        'whoop_mcp.py',
        'web_server.py', 
        'requirements.txt',
        'Dockerfile',
        'fly.toml',
        'deploy.sh',
        'DEPLOYMENT.md',
        '.env.example'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing_files.append(file)
            print(f"❌ {file}")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def test_syntax():
    """Test Python file syntax"""
    print("\n🔍 Testing Python syntax...")
    
    python_files = ['whoop_mcp.py', 'web_server.py']
    
    for file in python_files:
        try:
            with open(file, 'r') as f:
                source = f.read()
            ast.parse(source)
            print(f"✅ {file} syntax valid")
        except SyntaxError as e:
            print(f"❌ {file} syntax error: {e}")
            return False
        except Exception as e:
            print(f"❌ {file} error: {e}")
            return False
    
    print("✅ All Python files have valid syntax")
    return True

def test_configuration():
    """Test configuration files"""
    print("\n🔍 Testing configuration files...")
    
    # Test fly.toml
    try:
        with open('fly.toml', 'r') as f:
            content = f.read()
        if 'whoop-mcp' in content and 'PORT = "8080"' in content:
            print("✅ fly.toml configuration valid")
        else:
            print("❌ fly.toml missing required configuration")
            return False
    except Exception as e:
        print(f"❌ fly.toml error: {e}")
        return False
    
    # Test requirements.txt
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        required_deps = ['fastapi', 'uvicorn', 'httpx', 'mcp', 'fastmcp']
        missing_deps = []
        for dep in required_deps:
            if dep not in content:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ requirements.txt missing: {missing_deps}")
            return False
        else:
            print("✅ requirements.txt contains required dependencies")
    except Exception as e:
        print(f"❌ requirements.txt error: {e}")
        return False
    
    print("✅ Configuration files valid")
    return True

def test_environment_setup():
    """Test environment variable setup"""
    print("\n🔍 Testing environment setup...")
    
    # Check .env.example
    try:
        with open('.env.example', 'r') as f:
            content = f.read()
        
        required_vars = ['WHOOP_CLIENT_ID', 'WHOOP_CLIENT_SECRET', 'PORT']
        missing_vars = []
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ .env.example missing variables: {missing_vars}")
            return False
        else:
            print("✅ .env.example contains required variables")
    except Exception as e:
        print(f"❌ .env.example error: {e}")
        return False
    
    print("✅ Environment setup valid")
    return True

def test_docker_config():
    """Test Docker configuration"""
    print("\n🔍 Testing Docker configuration...")
    
    try:
        with open('Dockerfile', 'r') as f:
            content = f.read()
        
        required_elements = [
            'FROM python:3.11-slim',
            'COPY requirements.txt',
            'RUN pip install',
            'EXPOSE 8080',
            'CMD ["python", "web_server.py"]'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Dockerfile missing elements: {missing_elements}")
            return False
        else:
            print("✅ Dockerfile configuration valid")
    except Exception as e:
        print(f"❌ Dockerfile error: {e}")
        return False
    
    print("✅ Docker configuration valid")
    return True

def main():
    """Run all tests"""
    print("🚀 WHOOP MCP Deployment Validation\n")
    
    tests = [
        test_file_structure,
        test_syntax,
        test_configuration,
        test_environment_setup,
        test_docker_config
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All tests passed! Ready for deployment to fly.io")
        print("\nNext steps:")
        print("1. Install flyctl: curl -L https://fly.io/install.sh | sh")
        print("2. Login: flyctl auth login") 
        print("3. Deploy: ./deploy.sh")
        print("4. Set secrets: flyctl secrets set WHOOP_CLIENT_ID=... WHOOP_CLIENT_SECRET=...")
        return True
    else:
        print("\n❌ Some tests failed. Please fix the issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
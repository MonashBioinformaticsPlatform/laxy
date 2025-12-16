#!/usr/bin/env python3
"""
Integration Test Suite Runner for Laxy

Runs all integration tests with proper environment setup and reporting.

Usage:
    python tests/integration/run_integration_tests.py
    
Environment Requirements:
    - Laxy development environment must be running
    - API accessible at http://localhost:8001 (or API_BASE_URL)
"""

import os
import sys
import subprocess
import time
from datetime import datetime

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Test modules to run
TEST_MODULES = [
    'test_jwt_auth',
    'test_file_operations',
    'test_external_integrations'
]

def log(message: str, level: str = 'INFO'):
    """Log with timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {level}: {message}")

def check_api_connectivity():
    """Check if API is accessible"""
    try:
        import requests
        api_url = os.environ.get('API_BASE_URL', 'http://localhost:8001')
        response = requests.get(f"{api_url}/api/v1/ping/", timeout=5)
        if response.status_code == 200:
            log(f"✅ API accessible: {api_url}")
            return True
        else:
            log(f"❌ API returned {response.status_code}: {api_url}")
            return False
    except Exception as e:
        log(f"❌ Cannot connect to API: {e}", 'ERROR')
        return False

def run_test_module(module_name: str) -> bool:
    """Run a single test module"""
    try:
        log(f"Running {module_name}...")
        
        # Import and run the test
        test_module = __import__(module_name, fromlist=['main'])
        
        # Capture stdout to check for failures
        import io
        import contextlib
        
        # Redirect stdout to capture output
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        
        try:
            # Run the test module's main function
            test_module.main()
            success = True
        except SystemExit as e:
            success = (e.code == 0)
        finally:
            # Restore stdout
            sys.stdout = old_stdout
            output = captured_output.getvalue()
        
        # Print the output
        print(output)
        
        if success:
            log(f"✅ {module_name}: PASSED")
        else:
            log(f"❌ {module_name}: FAILED", 'ERROR')
            
        return success
        
    except Exception as e:
        log(f"❌ {module_name}: ERROR - {e}", 'ERROR')
        return False

def main():
    """Main test runner"""
    print("=" * 60)
    print("🧪 LAXY INTEGRATION TEST SUITE")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Check prerequisites
    log("Checking prerequisites...")
    
    if not check_api_connectivity():
        log("❌ API not accessible. Start Laxy development environment:", 'ERROR')
        log("   export LAXY_ENV=local-dev", 'ERROR')
        log("   docker compose -f docker-compose.yml -f docker-compose.local-dev.yml up -d", 'ERROR')
        sys.exit(1)
    
    # Run all test modules
    results = {}
    
    for module_name in TEST_MODULES:
        log(f"Starting {module_name}...")
        print("-" * 40)
        
        results[module_name] = run_test_module(module_name)
        
        print("-" * 40)
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("=" * 60)
    print("📊 INTEGRATION TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for module_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {module_name:<30} {status}")
    
    print(f"\nOverall Results: {passed_tests}/{total_tests} test suites passed")
    print(f"Total Duration: {duration}")
    
    if passed_tests == total_tests:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        sys.exit(0)
    else:
        print("⚠️  SOME INTEGRATION TESTS FAILED")
        sys.exit(1)

if __name__ == '__main__':
    main() 
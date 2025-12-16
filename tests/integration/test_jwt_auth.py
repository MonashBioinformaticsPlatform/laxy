#!/usr/bin/env python3
"""
JWT Authentication Testing Script for Laxy

Tests the djangorestframework-simplejwt implementation after migration 
from rest_framework_jwt.

Usage:
    python test_jwt_auth.py

Environment:
    Set API_BASE_URL environment variable or it defaults to http://localhost:8001
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple

# Add tests/integration to path for imports
_test_dir = os.path.dirname(os.path.abspath(__file__))
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from test_user_manager import TestUserManager

# Configuration
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8001')

class JWTAuthTester:
    def __init__(self, base_url: str, credentials):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.credentials = credentials
        
    def log(self, message: str, level: str = 'INFO'):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def test_csrf_token_endpoint(self) -> bool:
        """Test CSRF token endpoint"""
        try:
            self.log("Testing CSRF token endpoint...")
            response = self.session.get(f"{self.base_url}/api/v1/auth/csrftoken/")
            
            if response.status_code == 200:
                self.log("✅ CSRF token endpoint accessible")
                # Extract CSRF token from cookies
                csrf_token = self.session.cookies.get('csrftoken')
                if csrf_token:
                    self.log(f"✅ CSRF token received: {csrf_token[:20]}...")
                    return True
                else:
                    self.log("⚠️  CSRF token not found in cookies", 'WARNING')
                    return False
            else:
                self.log(f"❌ CSRF endpoint failed: {response.status_code}", 'ERROR')
                return False
        except Exception as e:
            self.log(f"❌ CSRF token test failed: {e}", 'ERROR')
            return False
    
    def test_jwt_token_obtain(self) -> Tuple[bool, Optional[Dict]]:
        """Test JWT token obtain endpoint (POST /api/v1/auth/jwt/get/)"""
        try:
            self.log("Testing JWT token obtain...")
            
            # Get CSRF token first
            self.test_csrf_token_endpoint()
            
            url = f"{self.base_url}/api/v1/auth/jwt/get/"
            data = {
                'username': self.credentials.username,
                'password': self.credentials.password
            }
            
            # Set headers for JWT request
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': self.session.cookies.get('csrftoken', '')
            }
            
            response = self.session.post(url, json=data, headers=headers)
            
            self.log(f"JWT obtain response: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access')
                self.refresh_token = token_data.get('refresh')
                
                if self.access_token and self.refresh_token:
                    self.log("✅ JWT tokens obtained successfully")
                    self.log(f"✅ Access token: {self.access_token[:50]}...")
                    self.log(f"✅ Refresh token: {self.refresh_token[:50]}...")
                    return True, token_data
                else:
                    self.log("❌ JWT tokens missing in response", 'ERROR')
                    return False, None
            elif response.status_code == 401:
                self.log("❌ Authentication failed - check credentials", 'ERROR')
                self.log(f"Response: {response.text}")
                return False, None
            elif response.status_code == 405:
                self.log("✅ JWT endpoint rejects GET (expected), accepts POST", 'INFO')
                # Try the actual POST request
                return self.test_jwt_token_obtain()
            else:
                self.log(f"❌ JWT obtain failed: {response.status_code}", 'ERROR')
                self.log(f"Response: {response.text}")
                return False, None
                
        except Exception as e:
            self.log(f"❌ JWT obtain test failed: {e}", 'ERROR')
            return False, None
    
    def test_jwt_token_verify(self) -> bool:
        """Test JWT token verify endpoint"""
        if not self.access_token:
            self.log("❌ No access token available for verification", 'ERROR')
            return False
            
        try:
            self.log("Testing JWT token verification...")
            
            url = f"{self.base_url}/api/v1/auth/jwt/verify/"
            data = {'token': self.access_token}
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': self.session.cookies.get('csrftoken', '')
            }
            
            response = self.session.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                self.log("✅ JWT token verification successful")
                return True
            else:
                self.log(f"❌ JWT verification failed: {response.status_code}", 'ERROR')
                self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ JWT verification test failed: {e}", 'ERROR')
            return False
    
    def test_jwt_token_refresh(self) -> bool:
        """Test JWT token refresh endpoint"""
        if not self.refresh_token:
            self.log("❌ No refresh token available", 'ERROR')
            return False
            
        try:
            self.log("Testing JWT token refresh...")
            
            url = f"{self.base_url}/api/v1/auth/jwt/refresh/"
            data = {'refresh': self.refresh_token}
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': self.session.cookies.get('csrftoken', '')
            }
            
            response = self.session.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get('access')
                
                if new_access_token:
                    self.log("✅ JWT token refresh successful")
                    self.log(f"✅ New access token: {new_access_token[:50]}...")
                    self.access_token = new_access_token  # Update for further tests
                    return True
                else:
                    self.log("❌ New access token missing in refresh response", 'ERROR')
                    return False
            else:
                self.log(f"❌ JWT refresh failed: {response.status_code}", 'ERROR')
                self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ JWT refresh test failed: {e}", 'ERROR')
            return False
    
    def test_authenticated_api_access(self) -> bool:
        """Test API access using JWT Bearer token"""
        if not self.access_token:
            self.log("❌ No access token available for API testing", 'ERROR')
            return False
            
        try:
            self.log("Testing authenticated API access...")
            
            # Test user profile endpoint (requires authentication)
            url = f"{self.base_url}/api/v1/user/profile/"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                profile_data = response.json()
                self.log("✅ Authenticated API access successful")
                self.log("✅ User profile retrieved successfully")
                return True
            elif response.status_code == 401:
                self.log("❌ API access denied - token invalid", 'ERROR')
                return False
            else:
                self.log(f"❌ API access failed: {response.status_code}", 'ERROR')
                self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Authenticated API test failed: {e}", 'ERROR')
            return False
    
    def test_jobs_api_with_auth(self) -> bool:
        """Test jobs API endpoint with authentication"""
        if not self.access_token:
            self.log("❌ No access token available for jobs API testing", 'ERROR')
            return False
            
        try:
            self.log("Testing jobs API with authentication...")
            
            url = f"{self.base_url}/api/v1/jobs/"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                jobs_data = response.json()
                self.log("✅ Jobs API access successful")
                self.log(f"✅ Jobs count: {jobs_data.get('count', 0)}")
                return True
            else:
                self.log(f"❌ Jobs API access failed: {response.status_code}", 'ERROR')
                self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Jobs API test failed: {e}", 'ERROR')
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all JWT authentication tests"""
        self.log("🔐 Starting JWT Authentication Tests")
        self.log("=" * 50)
        
        results = {}
        
        # Test 1: CSRF Token
        results['csrf_token'] = self.test_csrf_token_endpoint()
        
        # Test 2: JWT Token Obtain  
        results['jwt_obtain'], token_data = self.test_jwt_token_obtain()
        
        # Test 3: JWT Token Verify
        results['jwt_verify'] = self.test_jwt_token_verify()
        
        # Test 4: JWT Token Refresh
        results['jwt_refresh'] = self.test_jwt_token_refresh()
        
        # Test 5: Authenticated API Access
        results['api_access'] = self.test_authenticated_api_access()
        
        # Test 6: Jobs API Access
        results['jobs_api'] = self.test_jobs_api_with_auth()
        
        # Summary
        self.log("=" * 50)
        self.log("🔐 JWT Authentication Test Results:")
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            self.log(f"  {test_name}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        self.log(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            self.log("🎉 All JWT authentication tests PASSED!")
        else:
            self.log("⚠️  Some JWT authentication tests FAILED")
        
        return results

def main():
    """Main test execution"""
    print("JWT Authentication Testing for Laxy")
    print("===================================")
    
    # Check API connectivity first
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/ping/", timeout=5)
        if response.status_code == 200:
            print(f"✅ API connectivity confirmed: {API_BASE_URL}")
        else:
            print(f"❌ API connectivity failed: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        sys.exit(1)
    
    # Run JWT tests with test user context manager
    with TestUserManager() as user_creds:
        tester = JWTAuthTester(API_BASE_URL, user_creds)
        results = tester.run_all_tests()
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main() 
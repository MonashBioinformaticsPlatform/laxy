#!/usr/bin/env python3
"""
Test User Manager for Integration Tests

Provides a context manager that creates a random test user before tests
and deletes it after tests complete. This prevents accumulation of dummy
user accounts in production or development environments.

Usage:
    from tests.integration.test_user_manager import TestUserManager
    
    with TestUserManager() as user:
        username = user.username
        password = user.password
        email = user.email
        # Run tests using these credentials
"""

import os
import subprocess
import secrets
import string
import time
from typing import NamedTuple, Optional


def generate_random_string(length: int = 12) -> str:
    """Generate a random alphanumeric string"""
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_random_password(length: int = 32) -> str:
    """Generate a random password with letters, digits, and special characters"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class TestUserCredentials(NamedTuple):
    """Container for test user credentials"""
    username: str
    password: str
    email: str


class TestUserManager:
    """Context manager for creating and cleaning up test users"""
    
    def __init__(self, log_func=None):
        """
        Initialize the test user manager.
        
        Args:
            log_func: Optional logging function that accepts (message, level) arguments.
                     If None, uses print with timestamp.
        """
        self.log_func = log_func or self._default_log
        self.credentials: Optional[TestUserCredentials] = None
        self._created = False
        
    def _default_log(self, message: str, level: str = 'INFO'):
        """Default logging function"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def log(self, message: str, level: str = 'INFO'):
        """Log a message using the configured log function"""
        self.log_func(message, level)
    
    def _execute_manage_command(self, command: str) -> bool:
        """
        Execute a Django management command via manage.py shell.
        
        Assumes we're running inside the container or on bare-metal with manage.py available.
        Uses a temporary Python script to avoid shell escaping issues.
        
        Args:
            command: Python code to execute in Django shell
            
        Returns:
            True if command succeeded, False otherwise
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Write command to a temporary script file to avoid shell escaping issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("from django.contrib.auth import get_user_model\n")
            f.write(command)
            f.write("\nprint('Success')\n")
            temp_script = f.name
        
        try:
            # Always run manage.py directly (assumes we're in container or bare-metal)
            with open(temp_script, 'r') as script_file:
                result = subprocess.run(
                    ['python3', 'manage.py', 'shell'],
                    cwd=project_root,
                    stdin=script_file,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0 or 'Success' in output
            return success
            
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            self.log(f"⚠️  Could not execute command: {e}", 'WARNING')
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_script)
            except OSError:
                pass
    
    def _create_user(self) -> bool:
        """Create the test user in Django"""
        if not self.credentials:
            return False
        
        # Use repr() to safely escape strings for Python code
        username_repr = repr(self.credentials.username)
        email_repr = repr(self.credentials.email)
        password_repr = repr(self.credentials.password)
        
        command = (
            f"User = get_user_model(); "
            f"user, created = User.objects.get_or_create(username={username_repr}, defaults={{'email': {email_repr}, 'is_active': True}}); "
            f"user.set_password({password_repr}); "
            f"user.is_active = True; "
            f"user.save();"
        )
        
        return self._execute_manage_command(command)
    
    def _delete_user(self) -> bool:
        """Delete the test user from Django"""
        if not self.credentials:
            return False
        
        # Use repr() to safely escape strings for Python code
        username_repr = repr(self.credentials.username)
        
        command = (
            f"User = get_user_model(); "
            f"User.objects.filter(username={username_repr}).delete();"
        )
        
        return self._execute_manage_command(command)
    
    def __enter__(self) -> TestUserCredentials:
        """Create test user and return credentials"""
        # Generate random credentials
        username = f'test_user_{generate_random_string(8)}'
        password = generate_random_password(32)
        email = f'{username}@example.com'
        
        self.credentials = TestUserCredentials(
            username=username,
            password=password,
            email=email
        )
        
        self.log("Creating test user...")
        if self._create_user():
            self._created = True
            self.log("✅ Test user created successfully")
            # Small delay to ensure database transaction is committed
            time.sleep(0.5)
        else:
            self.log("⚠️  Failed to create test user", 'WARNING')
        
        return self.credentials
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up test user"""
        if self._created and self.credentials:
            self.log("Cleaning up test user...")
            if self._delete_user():
                self.log("✅ Test user deleted successfully")
            else:
                self.log("⚠️  Failed to delete test user", 'WARNING')
        
        return False  # Don't suppress exceptions


# For backward compatibility, provide module-level constants
# These will be set when the context manager is used
TEST_USERNAME = None
TEST_PASSWORD = None
TEST_EMAIL = None

"""
Security utilities for FPL AI Pro API
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def is_allowed(self, identifier: str, limit: int, window: int = 3600) -> bool:
        """Check if request is allowed under rate limit"""
        current_time = time.time()
        
        # Cleanup old entries
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time - window)
            self.last_cleanup = current_time
        
        # Get or create entry for this identifier
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < window
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < limit:
            self.requests[identifier].append(current_time)
            return True
        
        return False
    
    def _cleanup_old_entries(self, cutoff_time: float):
        """Remove old entries from memory"""
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff_time
            ]
            if not self.requests[identifier]:
                del self.requests[identifier]

class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format"""
        if not api_key or len(api_key) < 32:
            return False
        
        # Check for common patterns that might indicate test/demo keys
        dangerous_patterns = ['test', 'demo', 'sample', '123', 'abc']
        api_key_lower = api_key.lower()
        
        for pattern in dangerous_patterns:
            if pattern in api_key_lower:
                logger.warning(f"Potentially insecure API key pattern detected: {pattern}")
        
        return True
    
    @staticmethod
    def sanitize_input(input_string: str, max_length: int = 255) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_string, str):
            return ""
        
        # Truncate to max length
        sanitized = input_string[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def generate_secure_token() -> str:
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        combined = f"{salt}{data}"
        hashed = hashlib.sha256(combined.encode()).hexdigest()
        return f"{salt}:{hashed}"
    
    @staticmethod
    def verify_hashed_data(data: str, hashed_data: str) -> bool:
        """Verify hashed data"""
        try:
            salt, expected_hash = hashed_data.split(':', 1)
            combined = f"{salt}{data}"
            actual_hash = hashlib.sha256(combined.encode()).hexdigest()
            return hmac.compare_digest(expected_hash, actual_hash)
        except ValueError:
            return False

class RequestLogger:
    """Log security-relevant requests"""
    
    def __init__(self):
        self.security_logger = logging.getLogger('security')
        handler = logging.FileHandler('security.log')
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.INFO)
    
    def log_failed_auth(self, ip_address: str, user_agent: str, token_prefix: str):
        """Log failed authentication attempt"""
        self.security_logger.warning(
            f"Failed auth - IP: {ip_address}, UA: {user_agent[:100]}, Token: {token_prefix}..."
        )
    
    def log_rate_limit_exceeded(self, ip_address: str, endpoint: str):
        """Log rate limit exceeded"""
        self.security_logger.warning(
            f"Rate limit exceeded - IP: {ip_address}, Endpoint: {endpoint}"
        )
    
    def log_suspicious_activity(self, ip_address: str, details: str):
        """Log suspicious activity"""
        self.security_logger.error(
            f"Suspicious activity - IP: {ip_address}, Details: {details}"
        )

# Global instances
rate_limiter = RateLimiter()
security_validator = SecurityValidator()
request_logger = RequestLogger()
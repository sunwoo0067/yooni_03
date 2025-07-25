"""
Session Manager - Manage marketplace login sessions and cookies
"""
import json
import pickle
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession


class SessionManager:
    """Manages marketplace login sessions and authentication"""
    
    def __init__(self, encryption_key: str = None):
        # Initialize encryption for sensitive data
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Generate a new key (in production, this should be stored securely)
            self.cipher = Fernet(Fernet.generate_key())
        
        self.active_sessions = {}  # marketplace_account -> session_data
        self.session_timeouts = {
            "coupang": 1800,    # 30 minutes
            "naver": 2400,      # 40 minutes
            "11st": 3600,       # 60 minutes
            "default": 1800     # 30 minutes
        }
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception:
            return data  # Fallback to unencrypted if encryption fails
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return encrypted_data  # Fallback if decryption fails
    
    def create_session(
        self, 
        marketplace: str, 
        account_id: str, 
        cookies: List[Dict[str, Any]],
        user_agent: str,
        additional_data: Dict[str, Any] = None
    ) -> str:
        """Create a new session"""
        
        session_key = f"{marketplace}:{account_id}"
        
        session_data = {
            "marketplace": marketplace,
            "account_id": account_id,
            "cookies": cookies,
            "user_agent": user_agent,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "request_count": 0,
            "additional_data": additional_data or {}
        }
        
        # Set expiration time
        timeout = self.session_timeouts.get(marketplace, self.session_timeouts["default"])
        session_data["expires_at"] = datetime.utcnow() + timedelta(seconds=timeout)
        
        self.active_sessions[session_key] = session_data
        
        return session_key
    
    def get_session(self, marketplace: str, account_id: str) -> Optional[Dict[str, Any]]:
        """Get existing session"""
        
        session_key = f"{marketplace}:{account_id}"
        session_data = self.active_sessions.get(session_key)
        
        if not session_data:
            return None
        
        # Check if session is expired
        if datetime.utcnow() > session_data["expires_at"]:
            self.invalidate_session(marketplace, account_id)
            return None
        
        # Update last used time
        session_data["last_used"] = datetime.utcnow()
        session_data["request_count"] += 1
        
        return session_data
    
    def update_session(
        self, 
        marketplace: str, 
        account_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update session data"""
        
        session_key = f"{marketplace}:{account_id}"
        session_data = self.active_sessions.get(session_key)
        
        if not session_data:
            return False
        
        # Update session data
        session_data.update(updates)
        session_data["last_used"] = datetime.utcnow()
        
        return True
    
    def extend_session(self, marketplace: str, account_id: str) -> bool:
        """Extend session expiration time"""
        
        session_key = f"{marketplace}:{account_id}"
        session_data = self.active_sessions.get(session_key)
        
        if not session_data:
            return False
        
        # Extend expiration
        timeout = self.session_timeouts.get(marketplace, self.session_timeouts["default"])
        session_data["expires_at"] = datetime.utcnow() + timedelta(seconds=timeout)
        session_data["last_used"] = datetime.utcnow()
        
        return True
    
    def invalidate_session(self, marketplace: str, account_id: str) -> bool:
        """Invalidate a session"""
        
        session_key = f"{marketplace}:{account_id}"
        
        if session_key in self.active_sessions:
            del self.active_sessions[session_key]
            return True
        
        return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        
        now = datetime.utcnow()
        expired_keys = []
        
        for session_key, session_data in self.active_sessions.items():
            if now > session_data["expires_at"]:
                expired_keys.append(session_key)
        
        for key in expired_keys:
            del self.active_sessions[key]
        
        return len(expired_keys)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        
        now = datetime.utcnow()
        active_count = 0
        expired_count = 0
        marketplace_counts = {}
        
        for session_data in self.active_sessions.values():
            marketplace = session_data["marketplace"]
            
            if now <= session_data["expires_at"]:
                active_count += 1
            else:
                expired_count += 1
            
            marketplace_counts[marketplace] = marketplace_counts.get(marketplace, 0) + 1
        
        return {
            "total_sessions": len(self.active_sessions),
            "active_sessions": active_count,
            "expired_sessions": expired_count,
            "by_marketplace": marketplace_counts
        }
    
    def serialize_cookies(self, cookies: List[Dict[str, Any]]) -> str:
        """Serialize cookies for storage"""
        
        try:
            cookies_json = json.dumps(cookies)
            return self.encrypt_data(cookies_json)
        except Exception:
            return ""
    
    def deserialize_cookies(self, cookies_data: str) -> List[Dict[str, Any]]:
        """Deserialize cookies from storage"""
        
        try:
            decrypted_data = self.decrypt_data(cookies_data)
            return json.loads(decrypted_data)
        except Exception:
            return []
    
    def cookies_to_selenium_format(self, cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert cookies to Selenium-compatible format"""
        
        selenium_cookies = []
        
        for cookie in cookies:
            selenium_cookie = {
                "name": cookie.get("name", ""),
                "value": cookie.get("value", ""),
                "domain": cookie.get("domain", ""),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", False),
                "httpOnly": cookie.get("httpOnly", False)
            }
            
            # Add expiry if present
            if "expiry" in cookie:
                selenium_cookie["expiry"] = cookie["expiry"]
            
            selenium_cookies.append(selenium_cookie)
        
        return selenium_cookies
    
    def cookies_to_requests_format(self, cookies: List[Dict[str, Any]]) -> Dict[str, str]:
        """Convert cookies to requests library format"""
        
        requests_cookies = {}
        
        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if name and value:
                requests_cookies[name] = value
        
        return requests_cookies
    
    def validate_session_health(self, marketplace: str, account_id: str) -> Dict[str, Any]:
        """Validate session health and return status"""
        
        session_data = self.get_session(marketplace, account_id)
        
        if not session_data:
            return {
                "healthy": False,
                "reason": "Session not found",
                "action": "create_new_session"
            }
        
        now = datetime.utcnow()
        
        # Check expiration
        if now > session_data["expires_at"]:
            return {
                "healthy": False,
                "reason": "Session expired",
                "action": "create_new_session"
            }
        
        # Check if session is about to expire (within 5 minutes)
        warning_time = session_data["expires_at"] - timedelta(minutes=5)
        if now > warning_time:
            return {
                "healthy": True,
                "warning": "Session expiring soon",
                "action": "extend_session",
                "expires_in_seconds": (session_data["expires_at"] - now).total_seconds()
            }
        
        # Check request count for rate limiting
        if session_data["request_count"] > 1000:  # High request count
            return {
                "healthy": True,
                "warning": "High request count",
                "action": "monitor_rate_limiting",
                "request_count": session_data["request_count"]
            }
        
        return {
            "healthy": True,
            "expires_in_seconds": (session_data["expires_at"] - now).total_seconds(),
            "request_count": session_data["request_count"]
        }
    
    def get_marketplace_sessions(self, marketplace: str) -> List[Dict[str, Any]]:
        """Get all sessions for a specific marketplace"""
        
        marketplace_sessions = []
        
        for session_key, session_data in self.active_sessions.items():
            if session_data["marketplace"] == marketplace:
                # Add session key to the data
                session_info = session_data.copy()
                session_info["session_key"] = session_key
                marketplace_sessions.append(session_info)
        
        return marketplace_sessions
    
    def rotate_sessions(self, marketplace: str) -> int:
        """Rotate (invalidate) all sessions for a marketplace"""
        
        invalidated_count = 0
        keys_to_remove = []
        
        for session_key, session_data in self.active_sessions.items():
            if session_data["marketplace"] == marketplace:
                keys_to_remove.append(session_key)
        
        for key in keys_to_remove:
            del self.active_sessions[key]
            invalidated_count += 1
        
        return invalidated_count
    
    def backup_sessions(self) -> str:
        """Create a backup of current sessions"""
        
        try:
            # Convert datetime objects to strings for JSON serialization
            backup_data = {}
            
            for session_key, session_data in self.active_sessions.items():
                serializable_data = session_data.copy()
                
                # Convert datetime objects
                for key in ["created_at", "last_used", "expires_at"]:
                    if key in serializable_data:
                        serializable_data[key] = serializable_data[key].isoformat()
                
                backup_data[session_key] = serializable_data
            
            # Serialize and encrypt
            backup_json = json.dumps(backup_data)
            return self.encrypt_data(backup_json)
            
        except Exception as e:
            print(f"Error creating session backup: {e}")
            return ""
    
    def restore_sessions(self, backup_data: str) -> bool:
        """Restore sessions from backup"""
        
        try:
            # Decrypt and deserialize
            decrypted_data = self.decrypt_data(backup_data)
            backup_sessions = json.loads(decrypted_data)
            
            # Restore sessions
            for session_key, session_data in backup_sessions.items():
                # Convert string datetime back to datetime objects
                for key in ["created_at", "last_used", "expires_at"]:
                    if key in session_data:
                        session_data[key] = datetime.fromisoformat(session_data[key])
                
                # Only restore non-expired sessions
                if datetime.utcnow() <= session_data["expires_at"]:
                    self.active_sessions[session_key] = session_data
            
            return True
            
        except Exception as e:
            print(f"Error restoring sessions: {e}")
            return False
    
    def get_session_activity_log(self, marketplace: str, account_id: str) -> List[Dict[str, Any]]:
        """Get activity log for a session"""
        
        session_data = self.get_session(marketplace, account_id)
        
        if not session_data:
            return []
        
        # Return session activity information
        return [
            {
                "timestamp": session_data["created_at"],
                "action": "session_created",
                "details": {"marketplace": marketplace, "account_id": account_id}
            },
            {
                "timestamp": session_data["last_used"],
                "action": "last_activity",
                "details": {"request_count": session_data["request_count"]}
            }
        ]
    
    def estimate_session_load(self) -> Dict[str, Any]:
        """Estimate current session load and capacity"""
        
        now = datetime.utcnow()
        active_sessions = 0
        requests_per_minute = 0
        
        # Calculate active sessions and request rate
        for session_data in self.active_sessions.values():
            if now <= session_data["expires_at"]:
                active_sessions += 1
                
                # Estimate requests per minute based on recent activity
                time_since_creation = (now - session_data["created_at"]).total_seconds()
                if time_since_creation > 0:
                    rate = (session_data["request_count"] / time_since_creation) * 60
                    requests_per_minute += rate
        
        return {
            "active_sessions": active_sessions,
            "total_sessions": len(self.active_sessions),
            "estimated_requests_per_minute": requests_per_minute,
            "capacity_usage": min(1.0, active_sessions / 100),  # Assume 100 session capacity
            "recommendations": self._get_load_recommendations(active_sessions, requests_per_minute)
        }
    
    def _get_load_recommendations(self, active_sessions: int, requests_per_minute: float) -> List[str]:
        """Get recommendations based on current load"""
        
        recommendations = []
        
        if active_sessions > 50:
            recommendations.append("Consider reducing concurrent sessions")
        
        if requests_per_minute > 500:
            recommendations.append("High request rate detected - implement rate limiting")
        
        if active_sessions > 80:
            recommendations.append("Near session capacity - consider scaling")
        
        if not recommendations:
            recommendations.append("Session load is within normal parameters")
        
        return recommendations
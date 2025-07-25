"""
Rate Limiter - Prevent abuse and ensure stable operation
"""
import time
import redis
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, deque
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int = 10
    window_size: int = 60  # seconds


@dataclass
class RateLimitResult:
    """Rate limit check result"""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None


class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client
        self.memory_store = defaultdict(lambda: defaultdict(deque))
        
        # Default rate limits by service/endpoint
        self.rate_limits = {
            "default": RateLimit(60, 1000, 10000, 10),
            "data_collection": RateLimit(30, 500, 2000, 5),
            "ai_processing": RateLimit(100, 2000, 20000, 20),
            "marketplace_api": RateLimit(20, 300, 1000, 3),
            "pipeline_execution": RateLimit(10, 100, 500, 2),
            "analytics": RateLimit(50, 800, 5000, 15),
            
            # Per-marketplace limits
            "coupang_scraping": RateLimit(20, 200, 800, 3),
            "naver_scraping": RateLimit(25, 300, 1000, 4),
            "11st_scraping": RateLimit(30, 400, 1200, 5),
            
            # User-based limits
            "user_api": RateLimit(200, 2000, 20000, 50),
            "admin_api": RateLimit(500, 5000, 50000, 100),
        }
        
        # IP-based rate limiting
        self.ip_limits = {
            "suspicious_ip": RateLimit(5, 50, 200, 2),
            "normal_ip": RateLimit(100, 1000, 10000, 20),
            "trusted_ip": RateLimit(500, 5000, 50000, 100),
        }
        
        # Temporary blocks and penalties
        self.blocked_ips = {}  # ip -> unblock_time
        self.penalties = {}    # key -> penalty_multiplier
    
    async def check_rate_limit(
        self, 
        key: str, 
        service: str = "default",
        ip_address: str = None,
        user_id: str = None
    ) -> RateLimitResult:
        """Check if request is within rate limits"""
        
        now = datetime.utcnow()
        
        # Check IP blocks first
        if ip_address and self._is_ip_blocked(ip_address, now):
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=self.blocked_ips[ip_address],
                retry_after=int((self.blocked_ips[ip_address] - now).total_seconds())
            )
        
        # Get rate limit configuration
        rate_limit = self.rate_limits.get(service, self.rate_limits["default"])
        
        # Apply penalties if any
        if key in self.penalties:
            rate_limit = self._apply_penalty(rate_limit, self.penalties[key])
        
        # Check different time windows
        windows = [
            ("minute", 60, rate_limit.requests_per_minute),
            ("hour", 3600, rate_limit.requests_per_hour),
            ("day", 86400, rate_limit.requests_per_day)
        ]
        
        for window_name, window_seconds, limit in windows:
            result = await self._check_window(key, window_name, window_seconds, limit, now)
            if not result.allowed:
                return result
        
        # Check burst limit
        burst_result = await self._check_burst_limit(key, rate_limit.burst_size, now)
        if not burst_result.allowed:
            return burst_result
        
        # Check IP-based limits if provided
        if ip_address:
            ip_result = await self._check_ip_limits(ip_address, now)
            if not ip_result.allowed:
                return ip_result
        
        # All checks passed
        await self._record_request(key, now)
        if ip_address:
            await self._record_ip_request(ip_address, now)
        
        return RateLimitResult(
            allowed=True,
            remaining=rate_limit.requests_per_minute - await self._get_window_count(key, "minute", 60, now),
            reset_time=now + timedelta(minutes=1)
        )
    
    async def _check_window(
        self, 
        key: str, 
        window_name: str, 
        window_seconds: int, 
        limit: int, 
        now: datetime
    ) -> RateLimitResult:
        """Check rate limit for a specific time window"""
        
        count = await self._get_window_count(key, window_name, window_seconds, now)
        
        if count >= limit:
            reset_time = now + timedelta(seconds=window_seconds)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=window_seconds
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=limit - count,
            reset_time=now + timedelta(seconds=window_seconds)
        )
    
    async def _get_window_count(
        self, 
        key: str, 
        window_name: str, 
        window_seconds: int, 
        now: datetime
    ) -> int:
        """Get request count for a time window"""
        
        window_key = f"{key}:{window_name}"
        cutoff_time = now - timedelta(seconds=window_seconds)
        
        if self.redis:
            # Use Redis for persistent storage
            return await self._get_redis_window_count(window_key, cutoff_time, now)
        else:
            # Use in-memory storage
            return self._get_memory_window_count(window_key, cutoff_time)
    
    async def _get_redis_window_count(
        self, 
        window_key: str, 
        cutoff_time: datetime, 
        now: datetime
    ) -> int:
        """Get count using Redis sorted sets"""
        
        try:
            # Remove old entries
            await self.redis.zremrangebyscore(
                window_key, 
                0, 
                cutoff_time.timestamp()
            )
            
            # Get current count
            count = await self.redis.zcard(window_key)
            
            # Set expiration for cleanup
            await self.redis.expire(window_key, 86400)  # 24 hours
            
            return count
            
        except Exception:
            # Fallback to memory storage
            return self._get_memory_window_count(window_key, cutoff_time)
    
    def _get_memory_window_count(self, window_key: str, cutoff_time: datetime) -> int:
        """Get count using in-memory storage"""
        
        requests = self.memory_store[window_key]["requests"]
        
        # Remove old requests
        while requests and requests[0] < cutoff_time:
            requests.popleft()
        
        return len(requests)
    
    async def _check_burst_limit(
        self, 
        key: str, 
        burst_size: int, 
        now: datetime
    ) -> RateLimitResult:
        """Check burst rate limit (requests in last 10 seconds)"""
        
        burst_key = f"{key}:burst"
        cutoff_time = now - timedelta(seconds=10)
        
        count = await self._get_window_count(burst_key, "burst", 10, now)
        
        if count >= burst_size:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + timedelta(seconds=10),
                retry_after=10
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=burst_size - count,
            reset_time=now + timedelta(seconds=10)
        )
    
    async def _check_ip_limits(self, ip_address: str, now: datetime) -> RateLimitResult:
        """Check IP-based rate limits"""
        
        # Determine IP category
        ip_category = self._categorize_ip(ip_address)
        ip_limit = self.ip_limits.get(ip_category, self.ip_limits["normal_ip"])
        
        # Check IP rate limits
        ip_key = f"ip:{ip_address}"
        return await self._check_window(ip_key, "minute", 60, ip_limit.requests_per_minute, now)
    
    def _categorize_ip(self, ip_address: str) -> str:
        """Categorize IP address for rate limiting"""
        
        # Check if IP is in blocked list
        if ip_address in self.blocked_ips:
            return "suspicious_ip"
        
        # Check if IP has high error rate or suspicious patterns
        # This would be enhanced with ML-based detection
        
        # For now, simple categorization
        return "normal_ip"
    
    async def _record_request(self, key: str, now: datetime):
        """Record a request for rate limiting tracking"""
        
        if self.redis:
            await self._record_redis_request(key, now)
        else:
            self._record_memory_request(key, now)
    
    async def _record_redis_request(self, key: str, now: datetime):
        """Record request in Redis"""
        
        try:
            # Record for different windows
            for window in ["minute", "hour", "day", "burst"]:
                window_key = f"{key}:{window}"
                await self.redis.zadd(
                    window_key, 
                    {str(now.timestamp()): now.timestamp()}
                )
            
        except Exception:
            # Fallback to memory
            self._record_memory_request(key, now)
    
    def _record_memory_request(self, key: str, now: datetime):
        """Record request in memory"""
        
        for window in ["minute", "hour", "day", "burst"]:
            window_key = f"{key}:{window}"
            self.memory_store[window_key]["requests"].append(now)
            
            # Keep only recent requests to prevent memory bloat
            max_items = {"minute": 100, "hour": 1000, "day": 10000, "burst": 50}
            requests = self.memory_store[window_key]["requests"]
            
            if len(requests) > max_items.get(window, 1000):
                # Remove oldest 20%
                remove_count = len(requests) // 5
                for _ in range(remove_count):
                    requests.popleft()
    
    async def _record_ip_request(self, ip_address: str, now: datetime):
        """Record IP request"""
        
        ip_key = f"ip:{ip_address}"
        await self._record_request(ip_key, now)
    
    def _is_ip_blocked(self, ip_address: str, now: datetime) -> bool:
        """Check if IP is currently blocked"""
        
        if ip_address not in self.blocked_ips:
            return False
        
        unblock_time = self.blocked_ips[ip_address]
        if now >= unblock_time:
            # Block expired, remove it
            del self.blocked_ips[ip_address]
            return False
        
        return True
    
    def _apply_penalty(self, rate_limit: RateLimit, penalty_multiplier: float) -> RateLimit:
        """Apply penalty to rate limits"""
        
        return RateLimit(
            requests_per_minute=int(rate_limit.requests_per_minute / penalty_multiplier),
            requests_per_hour=int(rate_limit.requests_per_hour / penalty_multiplier),
            requests_per_day=int(rate_limit.requests_per_day / penalty_multiplier),
            burst_size=max(1, int(rate_limit.burst_size / penalty_multiplier))
        )
    
    async def block_ip(
        self, 
        ip_address: str, 
        duration_minutes: int = 60, 
        reason: str = None
    ):
        """Block an IP address temporarily"""
        
        unblock_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.blocked_ips[ip_address] = unblock_time
        
        # Log the block
        print(f"Blocked IP {ip_address} until {unblock_time}. Reason: {reason}")
    
    async def apply_penalty(
        self, 
        key: str, 
        penalty_multiplier: float, 
        duration_minutes: int = 30
    ):
        """Apply penalty to a key"""
        
        self.penalties[key] = penalty_multiplier
        
        # Schedule penalty removal
        asyncio.create_task(self._remove_penalty_after_delay(key, duration_minutes * 60))
    
    async def _remove_penalty_after_delay(self, key: str, delay_seconds: int):
        """Remove penalty after delay"""
        
        await asyncio.sleep(delay_seconds)
        self.penalties.pop(key, None)
    
    async def get_rate_limit_status(self, key: str, service: str = "default") -> Dict[str, Any]:
        """Get current rate limit status for a key"""
        
        now = datetime.utcnow()
        rate_limit = self.rate_limits.get(service, self.rate_limits["default"])
        
        # Get counts for different windows
        minute_count = await self._get_window_count(key, "minute", 60, now)
        hour_count = await self._get_window_count(key, "hour", 3600, now)
        day_count = await self._get_window_count(key, "day", 86400, now)
        burst_count = await self._get_window_count(key, "burst", 10, now)
        
        return {
            "key": key,
            "service": service,
            "limits": {
                "requests_per_minute": rate_limit.requests_per_minute,
                "requests_per_hour": rate_limit.requests_per_hour,
                "requests_per_day": rate_limit.requests_per_day,
                "burst_size": rate_limit.burst_size
            },
            "current_usage": {
                "minute": minute_count,
                "hour": hour_count,
                "day": day_count,
                "burst": burst_count
            },
            "remaining": {
                "minute": max(0, rate_limit.requests_per_minute - minute_count),
                "hour": max(0, rate_limit.requests_per_hour - hour_count),
                "day": max(0, rate_limit.requests_per_day - day_count),
                "burst": max(0, rate_limit.burst_size - burst_count)
            },
            "reset_times": {
                "minute": now + timedelta(minutes=1),
                "hour": now + timedelta(hours=1),
                "day": now + timedelta(days=1),
                "burst": now + timedelta(seconds=10)
            },
            "has_penalty": key in self.penalties,
            "penalty_multiplier": self.penalties.get(key, 1.0)
        }
    
    async def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """Get list of currently blocked IPs"""
        
        now = datetime.utcnow()
        blocked_list = []
        
        for ip, unblock_time in list(self.blocked_ips.items()):
            if now >= unblock_time:
                # Remove expired blocks
                del self.blocked_ips[ip]
            else:
                blocked_list.append({
                    "ip_address": ip,
                    "unblock_time": unblock_time,
                    "remaining_seconds": int((unblock_time - now).total_seconds())
                })
        
        return blocked_list
    
    async def clear_rate_limit_data(self, key: str):
        """Clear rate limit data for a key"""
        
        if self.redis:
            # Clear Redis data
            try:
                for window in ["minute", "hour", "day", "burst"]:
                    await self.redis.delete(f"{key}:{window}")
            except Exception:
                pass
        
        # Clear memory data
        for window in ["minute", "hour", "day", "burst"]:
            window_key = f"{key}:{window}"
            if window_key in self.memory_store:
                del self.memory_store[window_key]
        
        # Remove penalties
        self.penalties.pop(key, None)
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        
        now = datetime.utcnow()
        
        # Count active rate limit entries
        active_keys = len(self.memory_store)
        
        if self.redis:
            try:
                # Get Redis stats
                redis_keys = await self.redis.keys("*:minute")
                active_keys = len(redis_keys)
            except Exception:
                pass
        
        # Count blocked IPs and penalties
        blocked_ips_count = len([
            ip for ip, unblock_time in self.blocked_ips.items() 
            if now < unblock_time
        ])
        
        active_penalties = len(self.penalties)
        
        return {
            "active_rate_limit_keys": active_keys,
            "blocked_ips": blocked_ips_count,
            "active_penalties": active_penalties,
            "total_services": len(self.rate_limits),
            "memory_usage": {
                "memory_store_keys": len(self.memory_store),
                "blocked_ips": len(self.blocked_ips),
                "penalties": len(self.penalties)
            }
        }
    
    async def cleanup_expired_data(self):
        """Clean up expired rate limit data"""
        
        now = datetime.utcnow()
        
        # Clean up blocked IPs
        expired_ips = [
            ip for ip, unblock_time in self.blocked_ips.items()
            if now >= unblock_time
        ]
        for ip in expired_ips:
            del self.blocked_ips[ip]
        
        # Clean up memory store (keep only recent data)
        for key, windows in list(self.memory_store.items()):
            for window_name, data in windows.items():
                if "requests" in data:
                    requests = data["requests"]
                    # Keep only last hour of data
                    cutoff = now - timedelta(hours=1)
                    while requests and requests[0] < cutoff:
                        requests.popleft()
                    
                    # Remove empty entries
                    if not requests:
                        del self.memory_store[key][window_name]
            
            # Remove completely empty keys
            if not self.memory_store[key]:
                del self.memory_store[key]
        
        return {
            "expired_ips_removed": len(expired_ips),
            "memory_entries_cleaned": "completed"
        }
    
    def configure_service_limits(
        self, 
        service: str, 
        rate_limit: RateLimit
    ):
        """Configure rate limits for a service"""
        
        self.rate_limits[service] = rate_limit
    
    def configure_ip_limits(
        self, 
        category: str, 
        rate_limit: RateLimit
    ):
        """Configure rate limits for IP category"""
        
        self.ip_limits[category] = rate_limit
    
    async def whitelist_ip(self, ip_address: str):
        """Add IP to whitelist (trusted category)"""
        
        # Remove from blocked list if present
        self.blocked_ips.pop(ip_address, None)
        
        # This would be enhanced to maintain a persistent whitelist
        print(f"IP {ip_address} added to whitelist")
    
    async def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect rate limiting anomalies and potential attacks"""
        
        anomalies = []
        now = datetime.utcnow()
        
        # Check for high request rates
        for key, windows in self.memory_store.items():
            if ":minute" in key:
                continue  # Skip window-specific keys
            
            minute_requests = len(windows.get("minute", {}).get("requests", []))
            
            if minute_requests > 100:  # Unusually high rate
                anomalies.append({
                    "type": "high_request_rate",
                    "key": key,
                    "requests_per_minute": minute_requests,
                    "severity": "medium" if minute_requests < 200 else "high"
                })
        
        # Check for patterns in blocked IPs
        recent_blocks = len([
            ip for ip, unblock_time in self.blocked_ips.items()
            if (unblock_time - now).total_seconds() < 3600  # Blocked in last hour
        ])
        
        if recent_blocks > 10:
            anomalies.append({
                "type": "multiple_ip_blocks",
                "blocked_count": recent_blocks,
                "severity": "high"
            })
        
        return anomalies
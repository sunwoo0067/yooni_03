"""Rate limiter for API calls"""
import asyncio
import time
from collections import deque
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds (default 60)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self, wait: bool = True) -> bool:
        """
        Acquire permission to make a call
        
        Args:
            wait: Whether to wait if rate limit is exceeded
            
        Returns:
            True if permission granted, False otherwise
        """
        async with self._lock:
            now = time.time()
            
            # Remove old calls outside the time window
            while self.calls and self.calls[0] <= now - self.time_window:
                self.calls.popleft()
            
            # Check if we can make a call
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            if not wait:
                return False
            
            # Calculate wait time
            oldest_call = self.calls[0]
            wait_time = oldest_call + self.time_window - now
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return await self.acquire(wait=False)
            
            return True
    
    def reset(self):
        """Reset the rate limiter"""
        self.calls.clear()
    
    @property
    def available_calls(self) -> int:
        """Get number of available calls"""
        now = time.time()
        
        # Remove old calls
        while self.calls and self.calls[0] <= now - self.time_window:
            self.calls.popleft()
        
        return self.max_calls - len(self.calls)
    
    @property
    def next_available_time(self) -> Optional[float]:
        """Get time when next call will be available"""
        if self.available_calls > 0:
            return time.time()
        
        if not self.calls:
            return time.time()
        
        oldest_call = self.calls[0]
        return oldest_call + self.time_window
"""
Anti-Detection Manager - Stealth browsing and bot detection avoidance
"""
import random
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5


class AntiDetectionManager:
    """Manages anti-detection measures for web scraping"""
    
    def __init__(self):
        self.user_agents = self._load_user_agents()
        self.proxy_pool = []
        self.current_proxy_index = 0
        self.fingerprint_cache = {}
        
        # Rate limiting configuration
        self.rate_limits = {
            "default": {"requests_per_minute": 30, "burst_size": 5},
            "coupang": {"requests_per_minute": 20, "burst_size": 3},
            "naver": {"requests_per_minute": 25, "burst_size": 4},
            "11st": {"requests_per_minute": 30, "burst_size": 5}
        }
        
        # Request timing
        self.last_requests = {}  # domain -> list of request timestamps
    
    def _load_user_agents(self) -> List[str]:
        """Load realistic user agent strings"""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            
            # Chrome on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
            
            # Safari on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        ]
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent string"""
        return random.choice(self.user_agents)
    
    def add_proxy(self, proxy: ProxyConfig):
        """Add proxy to the pool"""
        self.proxy_pool.append(proxy)
    
    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next proxy from pool (round-robin)"""
        if not self.proxy_pool:
            return None
        
        proxy = self.proxy_pool[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_pool)
        return proxy
    
    def get_random_proxy(self) -> Optional[ProxyConfig]:
        """Get a random proxy from pool"""
        if not self.proxy_pool:
            return None
        return random.choice(self.proxy_pool)
    
    def should_wait_for_rate_limit(self, domain: str) -> bool:
        """Check if we should wait due to rate limiting"""
        now = datetime.utcnow()
        
        # Get rate limit config for domain
        rate_config = self.rate_limits.get(domain, self.rate_limits["default"])
        
        # Get recent requests for this domain
        if domain not in self.last_requests:
            self.last_requests[domain] = []
        
        recent_requests = self.last_requests[domain]
        
        # Remove old requests (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        recent_requests = [req_time for req_time in recent_requests if req_time > cutoff]
        self.last_requests[domain] = recent_requests
        
        # Check if we exceed rate limit
        if len(recent_requests) >= rate_config["requests_per_minute"]:
            return True
        
        # Check burst limit (last 10 seconds)
        burst_cutoff = now - timedelta(seconds=10)
        burst_requests = [req_time for req_time in recent_requests if req_time > burst_cutoff]
        
        return len(burst_requests) >= rate_config["burst_size"]
    
    def record_request(self, domain: str):
        """Record a request for rate limiting"""
        now = datetime.utcnow()
        
        if domain not in self.last_requests:
            self.last_requests[domain] = []
        
        self.last_requests[domain].append(now)
    
    def get_wait_time(self, domain: str) -> float:
        """Get recommended wait time before next request"""
        if not self.should_wait_for_rate_limit(domain):
            # Random delay between 1-3 seconds for normal requests
            return random.uniform(1.0, 3.0)
        
        # If rate limited, wait longer
        rate_config = self.rate_limits.get(domain, self.rate_limits["default"])
        base_wait = 60.0 / rate_config["requests_per_minute"]  # Base interval
        
        # Add some randomness
        return base_wait + random.uniform(0.5, 2.0)
    
    def get_browser_fingerprint(self, user_agent: str) -> Dict[str, Any]:
        """Generate browser fingerprint based on user agent"""
        
        if user_agent in self.fingerprint_cache:
            return self.fingerprint_cache[user_agent]
        
        # Extract browser info from user agent
        is_chrome = "Chrome" in user_agent
        is_firefox = "Firefox" in user_agent
        is_safari = "Safari" in user_agent and "Chrome" not in user_agent
        is_edge = "Edg" in user_agent
        
        is_windows = "Windows" in user_agent
        is_mac = "Macintosh" in user_agent
        is_linux = "Linux" in user_agent
        
        # Generate fingerprint
        fingerprint = {
            "user_agent": user_agent,
            "language": random.choice(["ko-KR,ko;q=0.9,en;q=0.8", "ko-KR,ko;q=0.9", "ko;q=0.9,en;q=0.8"]),
            "platform": self._get_platform(is_windows, is_mac, is_linux),
            "screen_resolution": random.choice([
                "1920x1080", "1366x768", "1536x864", "1440x900", "1280x720"
            ]),
            "timezone": "Asia/Seoul",
            "webgl_vendor": self._get_webgl_vendor(is_chrome, is_firefox, is_safari),
            "color_depth": random.choice([24, 32]),
            "device_memory": random.choice([4, 8, 16]),
            "hardware_concurrency": random.choice([4, 8, 12, 16]),
            "connection_type": random.choice(["4g", "wifi", "ethernet"])
        }
        
        self.fingerprint_cache[user_agent] = fingerprint
        return fingerprint
    
    def _get_platform(self, is_windows: bool, is_mac: bool, is_linux: bool) -> str:
        """Get platform string"""
        if is_windows:
            return "Win32"
        elif is_mac:
            return "MacIntel"
        elif is_linux:
            return "Linux x86_64"
        else:
            return "Win32"  # Default
    
    def _get_webgl_vendor(self, is_chrome: bool, is_firefox: bool, is_safari: bool) -> str:
        """Get WebGL vendor string"""
        if is_chrome:
            return random.choice([
                "Google Inc. (NVIDIA)",
                "Google Inc. (Intel)",
                "Google Inc. (AMD)"
            ])
        elif is_firefox:
            return random.choice([
                "Mozilla (NVIDIA Corporation)",
                "Mozilla (Intel Inc.)",
                "Mozilla (AMD)"
            ])
        elif is_safari:
            return "Apple Inc."
        else:
            return "Google Inc. (NVIDIA)"
    
    def get_request_headers(self, user_agent: str, referer: str = None) -> Dict[str, str]:
        """Generate realistic request headers"""
        
        fingerprint = self.get_browser_fingerprint(user_agent)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": fingerprint["language"],
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        if referer:
            headers["Referer"] = referer
        
        # Add browser-specific headers
        if "Chrome" in user_agent:
            headers["sec-ch-ua"] = '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = f'"{fingerprint["platform"]}"'
        
        return headers
    
    def get_selenium_options(self, user_agent: str, proxy: ProxyConfig = None) -> Dict[str, Any]:
        """Get Selenium Chrome options with anti-detection measures"""
        
        fingerprint = self.get_browser_fingerprint(user_agent)
        
        options = {
            "arguments": [
                f"--user-agent={user_agent}",
                f"--window-size={fingerprint['screen_resolution'].replace('x', ',')}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # Speed up loading
                "--disable-javascript",  # Only if not needed
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-translate",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                f"--lang={fingerprint['language'].split(',')[0]}"
            ],
            "experimental_options": {
                "excludeSwitches": ["enable-automation"],
                "useAutomationExtension": False,
                "prefs": {
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.managed_default_content_settings.images": 2  # Block images
                }
            }
        }
        
        # Add proxy if provided
        if proxy:
            if proxy.protocol == "http":
                options["arguments"].append(f"--proxy-server=http://{proxy.host}:{proxy.port}")
            elif proxy.protocol == "socks5":
                options["arguments"].append(f"--proxy-server=socks5://{proxy.host}:{proxy.port}")
        
        return options
    
    def get_stealth_scripts(self) -> List[str]:
        """Get JavaScript scripts to hide automation"""
        
        return [
            # Hide webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Hide automation indicators
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            """,
            
            # Mock languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            """,
            
            # Mock permissions
            """
            const originalQuery = window.navigator.permissions.query;
            return window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,
            
            # Override getUserMedia
            """
            navigator.mediaDevices.getUserMedia = navigator.mediaDevices.getUserMedia || undefined;
            if (navigator.mediaDevices.getUserMedia === undefined) {
                navigator.mediaDevices.getUserMedia = () => Promise.reject(new Error('Not allowed'));
            }
            """
        ]
    
    def simulate_human_behavior(self) -> Dict[str, Any]:
        """Generate human-like behavior parameters"""
        
        return {
            "scroll_pause_time": random.uniform(0.5, 2.0),
            "click_delay": random.uniform(0.1, 0.5),
            "typing_speed": random.uniform(0.05, 0.2),  # Delay between keystrokes
            "mouse_movement_duration": random.uniform(0.2, 0.8),
            "page_view_time": random.uniform(3.0, 10.0),  # Time to spend on page
            "random_actions": random.choice([True, False]),  # Whether to perform random actions
            "scroll_behavior": {
                "direction": random.choice(["down", "up", "both"]),
                "speed": random.choice(["slow", "medium", "fast"]),
                "pause_probability": random.uniform(0.2, 0.6)
            }
        }
    
    def detect_captcha_challenge(self, page_source: str) -> bool:
        """Detect if page contains CAPTCHA challenge"""
        
        captcha_indicators = [
            "captcha", "recaptcha", "grecaptcha",
            "robot", "human", "verify",
            "challenge", "security check",
            "suspicious activity",
            "I'm not a robot"
        ]
        
        page_lower = page_source.lower()
        
        for indicator in captcha_indicators:
            if indicator in page_lower:
                return True
        
        return False
    
    def detect_rate_limiting(self, page_source: str, status_code: int) -> bool:
        """Detect if request was rate limited"""
        
        # Check HTTP status codes
        if status_code in [429, 503, 509]:
            return True
        
        # Check page content
        rate_limit_indicators = [
            "rate limit", "too many requests",
            "slow down", "try again later",
            "temporarily blocked",
            "exceeded", "quota"
        ]
        
        page_lower = page_source.lower()
        
        for indicator in rate_limit_indicators:
            if indicator in page_lower:
                return True
        
        return False
    
    def detect_ip_block(self, page_source: str, status_code: int) -> bool:
        """Detect if IP is blocked"""
        
        # Check HTTP status codes
        if status_code in [403, 451]:
            return True
        
        # Check page content
        block_indicators = [
            "blocked", "banned", "forbidden",
            "access denied", "ip blocked",
            "region", "country", "location"
        ]
        
        page_lower = page_source.lower()
        
        for indicator in block_indicators:
            if indicator in page_lower:
                return True
        
        return False
    
    def get_recovery_strategy(self, detection_type: str) -> Dict[str, Any]:
        """Get recovery strategy for detected issues"""
        
        strategies = {
            "captcha": {
                "action": "wait_and_retry",
                "wait_time": random.uniform(300, 600),  # 5-10 minutes
                "change_user_agent": True,
                "change_proxy": True,
                "reduce_rate": True
            },
            "rate_limit": {
                "action": "exponential_backoff",
                "base_wait_time": 60,  # 1 minute
                "max_wait_time": 3600,  # 1 hour
                "change_proxy": True,
                "reduce_rate": True
            },
            "ip_block": {
                "action": "change_ip",
                "change_proxy": True,
                "wait_time": random.uniform(1800, 3600),  # 30-60 minutes
                "change_user_agent": True
            },
            "general_error": {
                "action": "retry",
                "wait_time": random.uniform(30, 120),  # 30 seconds - 2 minutes
                "max_retries": 3
            }
        }
        
        return strategies.get(detection_type, strategies["general_error"])
    
    def cleanup_fingerprints(self):
        """Clean up cached fingerprints periodically"""
        # Remove old fingerprints to avoid memory buildup
        if len(self.fingerprint_cache) > 100:
            # Keep only the most recent 50
            items = list(self.fingerprint_cache.items())
            self.fingerprint_cache = dict(items[-50:])
    
    def get_session_config(self, marketplace: str) -> Dict[str, Any]:
        """Get optimized session configuration for specific marketplace"""
        
        configs = {
            "coupang": {
                "max_concurrent_sessions": 1,
                "request_interval": (3, 7),
                "session_duration": 1800,  # 30 minutes
                "use_proxy": True,
                "rotate_user_agent": True
            },
            "naver": {
                "max_concurrent_sessions": 2,
                "request_interval": (2, 5),
                "session_duration": 2400,  # 40 minutes
                "use_proxy": True,
                "rotate_user_agent": True
            },
            "11st": {
                "max_concurrent_sessions": 2,
                "request_interval": (2, 6),
                "session_duration": 3600,  # 60 minutes
                "use_proxy": False,
                "rotate_user_agent": False
            }
        }
        
        return configs.get(marketplace, configs["coupang"])
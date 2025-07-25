"""
IP Rotation Service - Manage IP rotation for marketplace data collection
"""
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ProxyServer:
    """Proxy server configuration"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, socks5
    country: Optional[str] = None
    provider: Optional[str] = None
    is_active: bool = True
    last_used: Optional[datetime] = None
    success_rate: float = 1.0
    response_time: float = 0.0
    error_count: int = 0
    total_requests: int = 0


@dataclass
class IPRotationResult:
    """Result of IP rotation"""
    proxy: Optional[ProxyServer]
    current_ip: Optional[str]
    rotation_reason: str
    success: bool


class IPRotationService:
    """Manages IP rotation for secure data collection"""
    
    def __init__(self):
        self.proxy_pools = {
            "premium": [],      # High-quality, fast proxies
            "standard": [],     # Regular proxies
            "backup": []        # Fallback proxies
        }
        
        self.current_proxies = {}  # marketplace -> current_proxy
        self.rotation_history = {}  # marketplace -> [(timestamp, proxy, reason)]
        self.blacklisted_ips = set()
        self.marketplace_requirements = {
            "coupang": {
                "preferred_countries": ["KR"],
                "rotation_interval": 300,  # 5 minutes
                "max_requests_per_ip": 50,
                "preferred_pool": "premium"
            },
            "naver": {
                "preferred_countries": ["KR"],
                "rotation_interval": 420,  # 7 minutes
                "max_requests_per_ip": 60,
                "preferred_pool": "standard"
            },
            "11st": {
                "preferred_countries": ["KR"],
                "rotation_interval": 600,  # 10 minutes
                "max_requests_per_ip": 80,
                "preferred_pool": "standard"
            }
        }
        
        # Rotation triggers
        self.rotation_triggers = {
            "time_based": True,
            "request_count": True,
            "error_rate": True,
            "detection_risk": True,
            "manual": True
        }
    
    async def add_proxy_server(
        self, 
        proxy: ProxyServer, 
        pool: str = "standard"
    ) -> bool:
        """Add a proxy server to the pool"""
        
        try:
            # Validate proxy before adding
            is_valid = await self._validate_proxy(proxy)
            
            if is_valid:
                self.proxy_pools[pool].append(proxy)
                return True
            else:
                print(f"Proxy validation failed: {proxy.host}:{proxy.port}")
                return False
                
        except Exception as e:
            print(f"Error adding proxy: {e}")
            return False
    
    async def _validate_proxy(self, proxy: ProxyServer) -> bool:
        """Validate proxy server connectivity and anonymity"""
        
        try:
            # Create proxy URL
            if proxy.username and proxy.password:
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
            
            # Test connectivity
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                
                # Test with IP check service
                start_time = datetime.utcnow()
                
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        proxy_ip = data.get("origin", "")
                        
                        # Update proxy info
                        response_time = (datetime.utcnow() - start_time).total_seconds()
                        proxy.response_time = response_time
                        
                        # Check if IP is not blacklisted
                        if proxy_ip not in self.blacklisted_ips:
                            return True
            
            return False
            
        except Exception as e:
            print(f"Proxy validation error: {e}")
            return False
    
    async def get_proxy_for_marketplace(
        self, 
        marketplace: str,
        force_rotation: bool = False
    ) -> IPRotationResult:
        """Get optimal proxy for marketplace"""
        
        requirements = self.marketplace_requirements.get(
            marketplace, 
            self.marketplace_requirements["naver"]  # Default
        )
        
        current_proxy = self.current_proxies.get(marketplace)
        rotation_reason = "initial_assignment"
        
        # Check if rotation is needed
        if current_proxy and not force_rotation:
            needs_rotation, reason = await self._needs_rotation(marketplace, current_proxy)
            if not needs_rotation:
                return IPRotationResult(
                    proxy=current_proxy,
                    current_ip=await self._get_proxy_ip(current_proxy),
                    rotation_reason="no_rotation_needed",
                    success=True
                )
            rotation_reason = reason
        
        # Get new proxy
        new_proxy = await self._select_optimal_proxy(marketplace, requirements)
        
        if new_proxy:
            # Update current proxy
            self.current_proxies[marketplace] = new_proxy
            new_proxy.last_used = datetime.utcnow()
            
            # Record rotation
            await self._record_rotation(marketplace, new_proxy, rotation_reason)
            
            # Get current IP
            current_ip = await self._get_proxy_ip(new_proxy)
            
            return IPRotationResult(
                proxy=new_proxy,
                current_ip=current_ip,
                rotation_reason=rotation_reason,
                success=True
            )
        else:
            return IPRotationResult(
                proxy=None,
                current_ip=None,
                rotation_reason="no_available_proxy",
                success=False
            )
    
    async def _needs_rotation(
        self, 
        marketplace: str, 
        current_proxy: ProxyServer
    ) -> Tuple[bool, str]:
        """Check if proxy rotation is needed"""
        
        requirements = self.marketplace_requirements.get(marketplace, {})
        now = datetime.utcnow()
        
        # Time-based rotation
        if current_proxy.last_used:
            time_since_rotation = (now - current_proxy.last_used).total_seconds()
            rotation_interval = requirements.get("rotation_interval", 300)
            
            if time_since_rotation > rotation_interval:
                return True, "time_based_rotation"
        
        # Request count rotation
        max_requests = requirements.get("max_requests_per_ip", 50)
        if current_proxy.total_requests >= max_requests:
            return True, "request_count_limit"
        
        # Error rate rotation
        if current_proxy.total_requests > 10:
            error_rate = current_proxy.error_count / current_proxy.total_requests
            if error_rate > 0.3:  # 30% error rate
                return True, "high_error_rate"
        
        # Success rate rotation
        if current_proxy.success_rate < 0.7:  # Below 70% success rate
            return True, "low_success_rate"
        
        # IP blacklisted
        current_ip = await self._get_proxy_ip(current_proxy)
        if current_ip in self.blacklisted_ips:
            return True, "ip_blacklisted"
        
        return False, "no_rotation_needed"
    
    async def _select_optimal_proxy(
        self, 
        marketplace: str, 
        requirements: Dict[str, Any]
    ) -> Optional[ProxyServer]:
        """Select optimal proxy based on requirements"""
        
        preferred_pool = requirements.get("preferred_pool", "standard")
        preferred_countries = requirements.get("preferred_countries", [])
        
        # Get candidate proxies
        candidates = []
        
        # Try preferred pool first
        pool_proxies = self.proxy_pools.get(preferred_pool, [])
        candidates.extend([p for p in pool_proxies if p.is_active])
        
        # Add other pools if needed
        if len(candidates) < 5:
            for pool_name, proxies in self.proxy_pools.items():
                if pool_name != preferred_pool:
                    candidates.extend([p for p in proxies if p.is_active])
        
        # Filter by country if specified
        if preferred_countries:
            country_filtered = [
                p for p in candidates 
                if p.country in preferred_countries
            ]
            if country_filtered:
                candidates = country_filtered
        
        # Filter out recently used proxies
        candidates = await self._filter_recently_used(marketplace, candidates)
        
        # Filter out blacklisted IPs
        candidates = await self._filter_blacklisted(candidates)
        
        if not candidates:
            return None
        
        # Score and rank proxies
        scored_proxies = await self._score_proxies(candidates)
        
        # Select best proxy with some randomization
        if len(scored_proxies) > 1:
            # Use weighted random selection for top 3 proxies
            top_proxies = scored_proxies[:3]
            weights = [3, 2, 1][:len(top_proxies)]
            selected = random.choices(top_proxies, weights=weights)[0]
            return selected[1]  # Return proxy from (score, proxy) tuple
        else:
            return scored_proxies[0][1]
    
    async def _filter_recently_used(
        self, 
        marketplace: str, 
        candidates: List[ProxyServer]
    ) -> List[ProxyServer]:
        """Filter out recently used proxies"""
        
        history = self.rotation_history.get(marketplace, [])
        
        # Get proxies used in last 30 minutes
        recent_cutoff = datetime.utcnow() - timedelta(minutes=30)
        recently_used = set()
        
        for timestamp, proxy, _ in history:
            if timestamp > recent_cutoff:
                proxy_id = f"{proxy.host}:{proxy.port}"
                recently_used.add(proxy_id)
        
        # Filter out recently used
        filtered = []
        for proxy in candidates:
            proxy_id = f"{proxy.host}:{proxy.port}"
            if proxy_id not in recently_used:
                filtered.append(proxy)
        
        return filtered if filtered else candidates  # Return all if no alternatives
    
    async def _filter_blacklisted(
        self, 
        candidates: List[ProxyServer]
    ) -> List[ProxyServer]:
        """Filter out blacklisted proxies"""
        
        filtered = []
        
        for proxy in candidates:
            proxy_ip = await self._get_proxy_ip(proxy)
            if proxy_ip not in self.blacklisted_ips:
                filtered.append(proxy)
        
        return filtered
    
    async def _score_proxies(
        self, 
        candidates: List[ProxyServer]
    ) -> List[Tuple[float, ProxyServer]]:
        """Score proxies for selection"""
        
        scored = []
        
        for proxy in candidates:
            score = 0.0
            
            # Success rate (0-40 points)
            score += proxy.success_rate * 40
            
            # Response time (0-20 points, faster is better)
            if proxy.response_time > 0:
                # Score decreases as response time increases
                time_score = max(0, 20 - (proxy.response_time * 2))
                score += time_score
            else:
                score += 10  # Default for untested
            
            # Request history (0-20 points, prefer less used)
            if proxy.total_requests < 10:
                score += 20
            elif proxy.total_requests < 50:
                score += 15
            elif proxy.total_requests < 100:
                score += 10
            else:
                score += 5
            
            # Error count penalty
            if proxy.error_count > 0:
                error_penalty = min(15, proxy.error_count * 2)
                score -= error_penalty
            
            # Last used bonus (prefer less recently used)
            if proxy.last_used:
                hours_since_use = (datetime.utcnow() - proxy.last_used).total_seconds() / 3600
                if hours_since_use > 24:
                    score += 10
                elif hours_since_use > 6:
                    score += 5
            else:
                score += 15  # Never used bonus
            
            scored.append((score, proxy))
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored
    
    async def _get_proxy_ip(self, proxy: ProxyServer) -> Optional[str]:
        """Get current IP for proxy"""
        
        try:
            # Create proxy URL
            if proxy.username and proxy.password:
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
            
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return data.get("origin", "")
            
            return None
            
        except Exception:
            return None
    
    async def _record_rotation(
        self, 
        marketplace: str, 
        proxy: ProxyServer, 
        reason: str
    ):
        """Record proxy rotation"""
        
        if marketplace not in self.rotation_history:
            self.rotation_history[marketplace] = []
        
        self.rotation_history[marketplace].append((
            datetime.utcnow(),
            proxy,
            reason
        ))
        
        # Keep only last 100 rotations
        if len(self.rotation_history[marketplace]) > 100:
            self.rotation_history[marketplace] = self.rotation_history[marketplace][-100:]
    
    async def record_proxy_success(
        self, 
        marketplace: str, 
        success: bool, 
        response_time: Optional[float] = None
    ):
        """Record proxy usage result"""
        
        proxy = self.current_proxies.get(marketplace)
        if not proxy:
            return
        
        proxy.total_requests += 1
        
        if success:
            # Update success rate
            old_success_count = proxy.success_rate * (proxy.total_requests - 1)
            new_success_count = old_success_count + 1
            proxy.success_rate = new_success_count / proxy.total_requests
            
            # Update response time
            if response_time is not None:
                if proxy.response_time > 0:
                    # Moving average
                    proxy.response_time = (proxy.response_time * 0.7) + (response_time * 0.3)
                else:
                    proxy.response_time = response_time
        else:
            proxy.error_count += 1
            # Update success rate
            old_success_count = proxy.success_rate * (proxy.total_requests - 1)
            proxy.success_rate = old_success_count / proxy.total_requests
    
    async def blacklist_ip(self, ip_address: str, reason: str = None):
        """Add IP to blacklist"""
        
        self.blacklisted_ips.add(ip_address)
        print(f"Blacklisted IP: {ip_address}. Reason: {reason}")
        
        # Force rotation for any marketplace using this IP
        for marketplace, proxy in self.current_proxies.items():
            current_ip = await self._get_proxy_ip(proxy)
            if current_ip == ip_address:
                await self.get_proxy_for_marketplace(marketplace, force_rotation=True)
    
    async def force_rotation(self, marketplace: str) -> IPRotationResult:
        """Force proxy rotation for marketplace"""
        
        return await self.get_proxy_for_marketplace(marketplace, force_rotation=True)
    
    async def get_rotation_stats(self, marketplace: str = None) -> Dict[str, Any]:
        """Get rotation statistics"""
        
        if marketplace:
            # Stats for specific marketplace
            history = self.rotation_history.get(marketplace, [])
            current_proxy = self.current_proxies.get(marketplace)
            
            return {
                "marketplace": marketplace,
                "current_proxy": {
                    "host": current_proxy.host if current_proxy else None,
                    "port": current_proxy.port if current_proxy else None,
                    "success_rate": current_proxy.success_rate if current_proxy else 0,
                    "total_requests": current_proxy.total_requests if current_proxy else 0,
                    "last_used": current_proxy.last_used if current_proxy else None
                },
                "rotation_count_24h": len([
                    h for h in history 
                    if h[0] > datetime.utcnow() - timedelta(hours=24)
                ]),
                "total_rotations": len(history),
                "rotation_reasons": self._analyze_rotation_reasons(history)
            }
        else:
            # Global stats
            total_proxies = sum(len(pool) for pool in self.proxy_pools.values())
            active_proxies = sum(
                len([p for p in pool if p.is_active]) 
                for pool in self.proxy_pools.values()
            )
            
            return {
                "total_proxies": total_proxies,
                "active_proxies": active_proxies,
                "blacklisted_ips": len(self.blacklisted_ips),
                "active_marketplaces": len(self.current_proxies),
                "proxy_pools": {
                    pool: len(proxies) 
                    for pool, proxies in self.proxy_pools.items()
                },
                "rotation_activity_24h": sum(
                    len([
                        h for h in history 
                        if h[0] > datetime.utcnow() - timedelta(hours=24)
                    ])
                    for history in self.rotation_history.values()
                )
            }
    
    def _analyze_rotation_reasons(self, history: List[Tuple]) -> Dict[str, int]:
        """Analyze rotation reasons from history"""
        
        reasons = {}
        for _, _, reason in history:
            reasons[reason] = reasons.get(reason, 0) + 1
        
        return reasons
    
    async def health_check_proxies(self) -> Dict[str, Any]:
        """Perform health check on all proxies"""
        
        results = {
            "total_checked": 0,
            "healthy": 0,
            "unhealthy": 0,
            "removed": 0,
            "details": []
        }
        
        for pool_name, proxies in self.proxy_pools.items():
            for proxy in proxies[:]:  # Create copy for safe iteration
                results["total_checked"] += 1
                
                is_healthy = await self._validate_proxy(proxy)
                
                if is_healthy:
                    results["healthy"] += 1
                    proxy.is_active = True
                else:
                    results["unhealthy"] += 1
                    proxy.is_active = False
                    
                    # Remove proxy if it has failed multiple times
                    if proxy.error_count > 10:
                        self.proxy_pools[pool_name].remove(proxy)
                        results["removed"] += 1
                
                results["details"].append({
                    "host": proxy.host,
                    "port": proxy.port,
                    "pool": pool_name,
                    "healthy": is_healthy,
                    "success_rate": proxy.success_rate,
                    "error_count": proxy.error_count
                })
        
        return results
    
    async def optimize_proxy_pools(self):
        """Optimize proxy pools based on performance"""
        
        optimizations = {
            "promoted": 0,
            "demoted": 0,
            "rebalanced": 0
        }
        
        all_proxies = []
        for pool_name, proxies in self.proxy_pools.items():
            for proxy in proxies:
                all_proxies.append((proxy, pool_name))
        
        # Sort by performance score
        scored_proxies = await self._score_proxies([p[0] for p in all_proxies])
        
        # Redistribute to pools based on performance
        new_pools = {"premium": [], "standard": [], "backup": []}
        
        total_proxies = len(scored_proxies)
        
        for i, (score, proxy) in enumerate(scored_proxies):
            old_pool = next(pool for p, pool in all_proxies if p == proxy)
            
            # Top 20% go to premium
            if i < total_proxies * 0.2:
                new_pool = "premium"
            # Next 60% go to standard
            elif i < total_proxies * 0.8:
                new_pool = "standard"
            # Bottom 20% go to backup
            else:
                new_pool = "backup"
            
            new_pools[new_pool].append(proxy)
            
            if old_pool != new_pool:
                if old_pool == "backup" and new_pool in ["standard", "premium"]:
                    optimizations["promoted"] += 1
                elif old_pool in ["standard", "premium"] and new_pool == "backup":
                    optimizations["demoted"] += 1
                else:
                    optimizations["rebalanced"] += 1
        
        # Update proxy pools
        self.proxy_pools = new_pools
        
        return optimizations
    
    async def get_marketplace_config(self, marketplace: str) -> Dict[str, Any]:
        """Get marketplace rotation configuration"""
        
        return self.marketplace_requirements.get(
            marketplace, 
            self.marketplace_requirements["naver"]
        )
    
    async def update_marketplace_config(
        self, 
        marketplace: str, 
        config: Dict[str, Any]
    ):
        """Update marketplace rotation configuration"""
        
        if marketplace not in self.marketplace_requirements:
            self.marketplace_requirements[marketplace] = {}
        
        self.marketplace_requirements[marketplace].update(config)
    
    async def export_proxy_list(self, pool: str = None) -> List[Dict[str, Any]]:
        """Export proxy list for backup or migration"""
        
        proxies = []
        
        pools_to_export = [pool] if pool else self.proxy_pools.keys()
        
        for pool_name in pools_to_export:
            if pool_name in self.proxy_pools:
                for proxy in self.proxy_pools[pool_name]:
                    proxies.append({
                        "host": proxy.host,
                        "port": proxy.port,
                        "username": proxy.username,
                        "password": proxy.password,
                        "protocol": proxy.protocol,
                        "country": proxy.country,
                        "provider": proxy.provider,
                        "pool": pool_name,
                        "is_active": proxy.is_active,
                        "success_rate": proxy.success_rate,
                        "total_requests": proxy.total_requests,
                        "error_count": proxy.error_count
                    })
        
        return proxies
    
    async def import_proxy_list(self, proxy_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """Import proxy list from backup"""
        
        results = {"imported": 0, "skipped": 0, "errors": 0}
        
        for proxy_data in proxy_list:
            try:
                proxy = ProxyServer(
                    host=proxy_data["host"],
                    port=proxy_data["port"],
                    username=proxy_data.get("username"),
                    password=proxy_data.get("password"),
                    protocol=proxy_data.get("protocol", "http"),
                    country=proxy_data.get("country"),
                    provider=proxy_data.get("provider"),
                    is_active=proxy_data.get("is_active", True)
                )
                
                # Restore performance data
                proxy.success_rate = proxy_data.get("success_rate", 1.0)
                proxy.total_requests = proxy_data.get("total_requests", 0)
                proxy.error_count = proxy_data.get("error_count", 0)
                
                pool = proxy_data.get("pool", "standard")
                
                # Check if proxy already exists
                existing = any(
                    p.host == proxy.host and p.port == proxy.port
                    for p in self.proxy_pools.get(pool, [])
                )
                
                if not existing:
                    success = await self.add_proxy_server(proxy, pool)
                    if success:
                        results["imported"] += 1
                    else:
                        results["errors"] += 1
                else:
                    results["skipped"] += 1
                    
            except Exception as e:
                print(f"Error importing proxy: {e}")
                results["errors"] += 1
        
        return results
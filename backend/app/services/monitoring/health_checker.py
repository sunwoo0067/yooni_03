"""
System Health Checker Service
Monitors the health of various system components
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import psutil
import time

from app.core.config import settings
from app.core.logging import logger

class HealthChecker:
    def __init__(self):
        self.health_cache = {}
        self.last_check_times = {}
        self.check_interval = 30  # seconds
        self.redis_client = None
        
    async def _get_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
        
    async def check_all_services(self, db: AsyncSession) -> Dict[str, Any]:
        """Check health of all services"""
        tasks = [
            self.check_database(db),
            self.check_redis(),
            self.check_external_apis(),
            self.check_internal_services(),
            self.check_system_resources()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        database_health = results[0] if not isinstance(results[0], Exception) else self._error_response("database")
        redis_health = results[1] if not isinstance(results[1], Exception) else self._error_response("redis")
        external_apis = results[2] if not isinstance(results[2], Exception) else []
        internal_services = results[3] if not isinstance(results[3], Exception) else []
        system_resources = results[4] if not isinstance(results[4], Exception) else {}
        
        # Determine overall status
        all_healthy = (
            database_health.get("status") == "healthy" and
            redis_health.get("status") == "healthy" and
            all(api.get("status") == "healthy" for api in external_apis) and
            all(service.get("status") == "healthy" for service in internal_services)
        )
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow(),
            "database": database_health,
            "redis": redis_health,
            "external_apis": external_apis,
            "services": internal_services,
            "system_resources": system_resources
        }
        
    async def check_database(self, db: AsyncSession) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = time.time()
            
            # Simple query to check connectivity
            result = await db.execute(text("SELECT 1"))
            result.scalar()
            
            # Get connection pool stats (if available)
            pool_status = {
                "size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "total": 0
            }
            
            if hasattr(db.bind, "pool"):
                pool = db.bind.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "total": pool.total_connections()
                }
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "response_time": round(response_time, 2),
                "connections": pool_status["checked_out"],
                "max_connections": pool_status["size"],
                "pool_status": pool_status
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connections": 0,
                "max_connections": 0
            }
            
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            start_time = time.time()
            redis_client = await self._get_redis()
            
            # Ping Redis
            await redis_client.ping()
            
            # Get Redis info
            info = await redis_client.info()
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "response_time": round(response_time, 2),
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_days": info.get("uptime_in_days", 0)
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "memory_usage": 0,
                "connected_clients": 0
            }
            
    async def check_external_apis(self) -> List[Dict[str, Any]]:
        """Check external API health"""
        apis = [
            {
                "name": "Coupang API",
                "url": "https://api-gateway.coupang.com/health",
                "timeout": 5
            },
            {
                "name": "Naver API",
                "url": "https://openapi.naver.com/v1/util/health",
                "timeout": 5
            },
            {
                "name": "Google Gemini",
                "url": "https://generativelanguage.googleapis.com/v1beta/models",
                "timeout": 5
            }
        ]
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            for api in apis:
                try:
                    start_time = time.time()
                    async with session.get(
                        api["url"],
                        timeout=aiohttp.ClientTimeout(total=api["timeout"])
                    ) as response:
                        response_time = (time.time() - start_time) * 1000  # ms
                        
                        results.append({
                            "name": api["name"],
                            "status": "healthy" if response.status < 500 else "degraded",
                            "response_time": round(response_time, 2),
                            "status_code": response.status,
                            "last_success": datetime.utcnow()
                        })
                        
                except asyncio.TimeoutError:
                    results.append({
                        "name": api["name"],
                        "status": "timeout",
                        "error": "Request timed out",
                        "last_success": self.last_check_times.get(api["name"])
                    })
                    
                except Exception as e:
                    results.append({
                        "name": api["name"],
                        "status": "unhealthy",
                        "error": str(e),
                        "last_success": self.last_check_times.get(api["name"])
                    })
                    
        # Update last success times
        for result in results:
            if result["status"] == "healthy":
                self.last_check_times[result["name"]] = datetime.utcnow()
                
        return results
        
    async def check_internal_services(self) -> List[Dict[str, Any]]:
        """Check internal service health"""
        services = []
        
        # Check if key services are responsive
        service_checks = [
            {
                "name": "Authentication Service",
                "check": self._check_auth_service
            },
            {
                "name": "Product Service",
                "check": self._check_product_service
            },
            {
                "name": "Order Service",
                "check": self._check_order_service
            },
            {
                "name": "AI Service",
                "check": self._check_ai_service
            }
        ]
        
        for service in service_checks:
            try:
                start_time = time.time()
                is_healthy = await service["check"]()
                response_time = (time.time() - start_time) * 1000  # ms
                
                services.append({
                    "name": service["name"],
                    "status": "healthy" if is_healthy else "unhealthy",
                    "response_time": round(response_time, 2),
                    "last_check": datetime.utcnow()
                })
                
            except Exception as e:
                services.append({
                    "name": service["name"],
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.utcnow()
                })
                
        return services
        
    async def _check_auth_service(self) -> bool:
        """Check if auth service is working"""
        # This would typically check if JWT validation is working
        # For now, return True if Redis is accessible (used for sessions)
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True
        except:
            return False
            
    async def _check_product_service(self) -> bool:
        """Check if product service is working"""
        # Check if we can access product cache
        try:
            redis_client = await self._get_redis()
            # Try to get a product cache key
            await redis_client.get("product:cache:test")
            return True
        except:
            return False
            
    async def _check_order_service(self) -> bool:
        """Check if order service is working"""
        # Check if order queue is accessible
        try:
            redis_client = await self._get_redis()
            # Check order queue length
            await redis_client.llen("order:queue")
            return True
        except:
            return False
            
    async def _check_ai_service(self) -> bool:
        """Check if AI service is working"""
        # Check if AI service cache is accessible
        try:
            redis_client = await self._get_redis()
            await redis_client.get("ai:service:status")
            return True
        except:
            return False
            
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {str(e)}")
            return {}
            
    def _error_response(self, service_name: str) -> Dict[str, Any]:
        """Generate error response for failed health check"""
        return {
            "status": "error",
            "error": f"{service_name} health check failed",
            "timestamp": datetime.utcnow()
        }
        
    async def monitor_health(self) -> None:
        """Background task to continuously monitor health"""
        while True:
            try:
                # Perform health checks
                # This would store results in Redis for quick access
                redis_client = await self._get_redis()
                
                # Store current health status
                health_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "services": await self._quick_health_check()
                }
                
                await redis_client.setex(
                    "health:current",
                    60,  # 1 minute TTL
                    json.dumps(health_data)
                )
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {str(e)}")
                await asyncio.sleep(self.check_interval)
                
    async def _quick_health_check(self) -> Dict[str, str]:
        """Quick health check for monitoring"""
        results = {}
        
        # Quick Redis check
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            results["redis"] = "healthy"
        except:
            results["redis"] = "unhealthy"
            
        # Quick system check
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            results["system"] = "healthy" if cpu < 90 else "degraded"
        except:
            results["system"] = "unknown"
            
        return results

# Global instance
health_checker = HealthChecker()

import json
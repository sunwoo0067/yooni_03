"""
Enhanced Market Account Manager for multi-platform dropshipping
Supports account management, batch operations, and prioritized registration
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.platform_account import PlatformAccount, PlatformType, AccountStatus
from app.models.product_registration import (
    ProductRegistrationBatch, ProductRegistration, PlatformProductRegistration,
    RegistrationStatus, RegistrationPriority, RegistrationQueue
)
from app.utils.encryption import encrypt_sensitive_data, decrypt_sensitive_data
from app.core.config import settings

logger = logging.getLogger(__name__)


class MarketAccountManager:
    """Enhanced market account manager with prioritization and batch support"""
    
    # Platform priority order (higher number = higher priority)
    PLATFORM_PRIORITIES = {
        PlatformType.COUPANG: 100,
        PlatformType.NAVER: 80,
        PlatformType.ELEVEN_ST: 60,
        PlatformType.GMARKET: 40,
        PlatformType.AUCTION: 30,
        PlatformType.TMON: 20,
        PlatformType.WE_MAKE_PRICE: 15,
        PlatformType.INTERPARK: 10
    }
    
    def __init__(self, db_session: AsyncSession, redis_client=None):
        """Initialize Market Account Manager
        
        Args:
            db_session: Database session
            redis_client: Redis client for caching and queuing
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self._account_cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def create_account(
        self,
        user_id: str,
        platform_type: PlatformType,
        account_data: Dict[str, Any]
    ) -> PlatformAccount:
        """Create new platform account with encryption
        
        Args:
            user_id: User ID
            platform_type: Platform type
            account_data: Account information including credentials
            
        Returns:
            Created platform account
        """
        try:
            # Encrypt sensitive credentials
            encrypted_credentials = await self._encrypt_account_credentials(account_data)
            
            # Create account
            account = PlatformAccount(
                user_id=user_id,
                platform_type=platform_type,
                account_name=account_data.get("account_name"),
                account_id=account_data.get("account_id"),
                api_key=encrypted_credentials.get("api_key"),
                api_secret=encrypted_credentials.get("api_secret"),
                access_token=encrypted_credentials.get("access_token"),
                refresh_token=encrypted_credentials.get("refresh_token"),
                seller_id=account_data.get("seller_id"),
                store_name=account_data.get("store_name"),
                store_url=account_data.get("store_url"),
                platform_settings=account_data.get("platform_settings", {}),
                commission_rate=account_data.get("commission_rate"),
                monthly_fee=account_data.get("monthly_fee"),
                currency=account_data.get("currency", "KRW"),
                daily_api_quota=account_data.get("daily_api_quota"),
                rate_limit_per_minute=account_data.get("rate_limit_per_minute", 60)
            )
            
            self.db_session.add(account)
            await self.db_session.commit()
            await self.db_session.refresh(account)
            
            # Clear cache
            self._clear_account_cache(user_id)
            
            logger.info(f"Created platform account: {platform_type.value} for user {user_id}")
            return account
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to create account: {e}")
            raise
    
    async def get_active_accounts(
        self,
        user_id: str,
        platforms: Optional[List[PlatformType]] = None,
        prioritized: bool = True
    ) -> List[PlatformAccount]:
        """Get active platform accounts with optional prioritization
        
        Args:
            user_id: User ID
            platforms: Specific platforms to filter
            prioritized: Whether to sort by platform priority
            
        Returns:
            List of active platform accounts
        """
        cache_key = f"accounts_{user_id}_{platforms}_{prioritized}"
        
        # Check cache first
        if cache_key in self._account_cache:
            cache_data = self._account_cache[cache_key]
            if cache_data["expires"] > datetime.utcnow():
                return cache_data["accounts"]
        
        # Build query
        query = select(PlatformAccount).where(
            and_(
                PlatformAccount.user_id == user_id,
                PlatformAccount.status == AccountStatus.ACTIVE,
                PlatformAccount.sync_enabled == True
            )
        )
        
        if platforms:
            query = query.where(PlatformAccount.platform_type.in_(platforms))
        
        result = await self.db_session.execute(query)
        accounts = result.scalars().all()
        
        # Sort by priority if requested
        if prioritized:
            accounts = sorted(
                accounts,
                key=lambda x: self.PLATFORM_PRIORITIES.get(x.platform_type, 0),
                reverse=True
            )
        
        # Cache results
        self._account_cache[cache_key] = {
            "accounts": accounts,
            "expires": datetime.utcnow() + timedelta(seconds=self._cache_ttl)
        }
        
        return accounts
    
    async def get_account_by_platform(
        self,
        user_id: str,
        platform_type: PlatformType,
        account_name: Optional[str] = None
    ) -> Optional[PlatformAccount]:
        """Get specific platform account
        
        Args:
            user_id: User ID
            platform_type: Platform type
            account_name: Optional account name for multi-account platforms
            
        Returns:
            Platform account or None
        """
        query = select(PlatformAccount).where(
            and_(
                PlatformAccount.user_id == user_id,
                PlatformAccount.platform_type == platform_type,
                PlatformAccount.status == AccountStatus.ACTIVE
            )
        )
        
        if account_name:
            query = query.where(PlatformAccount.account_name == account_name)
        
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def validate_account_health(self, account: PlatformAccount) -> Dict[str, Any]:
        """Validate account health and update status
        
        Args:
            account: Platform account to validate
            
        Returns:
            Health check results
        """
        health_result = {
            "account_id": str(account.id),
            "platform": account.platform_type.value,
            "healthy": False,
            "issues": [],
            "last_check": datetime.utcnow().isoformat()
        }
        
        try:
            # Check token expiration
            if account.is_token_expired():
                health_result["issues"].append("access_token_expired")
            
            # Check API quota
            if account.daily_api_quota and account.daily_api_used >= account.daily_api_quota:
                health_result["issues"].append("daily_quota_exceeded")
            
            # Check consecutive errors
            if account.consecutive_errors >= 5:
                health_result["issues"].append("high_error_rate")
            
            # Check last sync time
            if account.last_sync_at:
                time_since_sync = datetime.utcnow() - account.last_sync_at
                if time_since_sync.total_seconds() > 3600:  # 1 hour
                    health_result["issues"].append("sync_delay")
            
            # Test API connection if possible
            # This would require the actual platform API integration
            # For now, we'll skip the actual API test
            
            # Update health status
            if not health_result["issues"]:
                health_result["healthy"] = True
                account.health_status = "healthy"
                account.reset_error_count()
            else:
                account.health_status = "warning" if len(health_result["issues"]) <= 2 else "error"
            
            account.last_health_check_at = datetime.utcnow()
            await self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Health check failed for account {account.id}: {e}")
            health_result["issues"].append(f"health_check_failed: {str(e)}")
            account.health_status = "error"
            account.increment_error_count()
            await self.db_session.commit()
        
        return health_result
    
    async def bulk_health_check(self, user_id: str) -> Dict[str, Any]:
        """Perform health check on all user accounts
        
        Args:
            user_id: User ID
            
        Returns:
            Bulk health check results
        """
        accounts = await self.get_active_accounts(user_id, prioritized=False)
        
        # Run health checks concurrently
        tasks = [self.validate_account_health(account) for account in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile summary
        summary = {
            "total_accounts": len(accounts),
            "healthy_accounts": 0,
            "warning_accounts": 0,
            "error_accounts": 0,
            "results": []
        }
        
        for result in results:
            if isinstance(result, Exception):
                summary["error_accounts"] += 1
                summary["results"].append({
                    "error": str(result),
                    "healthy": False
                })
            else:
                summary["results"].append(result)
                if result["healthy"]:
                    summary["healthy_accounts"] += 1
                elif len(result["issues"]) <= 2:
                    summary["warning_accounts"] += 1
                else:
                    summary["error_accounts"] += 1
        
        return summary
    
    async def get_optimal_account_distribution(
        self,
        user_id: str,
        product_count: int,
        target_platforms: Optional[List[PlatformType]] = None
    ) -> Dict[str, Any]:
        """Calculate optimal account distribution for batch registration
        
        Args:
            user_id: User ID
            product_count: Number of products to register
            target_platforms: Target platforms
            
        Returns:
            Optimal distribution plan
        """
        accounts = await self.get_active_accounts(user_id, target_platforms, prioritized=True)
        
        if not accounts:
            raise ValueError("No active accounts available")
        
        # Calculate distribution based on:
        # 1. Platform priority
        # 2. API quotas and limits
        # 3. Account health
        # 4. Recent error rates
        
        distribution = {
            "total_products": product_count,
            "accounts": [],
            "estimated_time": 0,
            "recommendations": []
        }
        
        remaining_products = product_count
        
        for account in accounts:
            if remaining_products <= 0:
                break
            
            # Calculate account capacity
            daily_quota = account.daily_api_quota or 1000
            remaining_quota = max(0, daily_quota - account.daily_api_used)
            rate_limit = account.rate_limit_per_minute
            
            # Health factor (0.0 to 1.0)
            if account.health_status == "healthy":
                health_factor = 1.0
            elif account.health_status == "warning":
                health_factor = 0.7
            else:
                health_factor = 0.3
            
            # Calculate optimal allocation
            max_allocation = min(
                remaining_products,
                int(remaining_quota * health_factor),
                int(rate_limit * 60 * 2)  # 2 hours worth of rate limit
            )
            
            if max_allocation > 0:
                allocation = min(max_allocation, max(1, remaining_products // len(accounts)))
                
                distribution["accounts"].append({
                    "account_id": str(account.id),
                    "platform": account.platform_type.value,
                    "account_name": account.account_name,
                    "allocated_products": allocation,
                    "priority_score": self.PLATFORM_PRIORITIES.get(account.platform_type, 0),
                    "health_status": account.health_status,
                    "estimated_time_minutes": allocation / (rate_limit / 60) if rate_limit > 0 else 0
                })
                
                remaining_products -= allocation
        
        # Add recommendations
        if remaining_products > 0:
            distribution["recommendations"].append(
                f"Warning: {remaining_products} products cannot be allocated due to quota/health limitations"
            )
        
        # Calculate total estimated time
        distribution["estimated_time"] = max(
            acc["estimated_time_minutes"] for acc in distribution["accounts"]
        ) if distribution["accounts"] else 0
        
        return distribution
    
    async def update_api_usage(
        self,
        account_id: str,
        api_calls: int,
        success: bool = True
    ):
        """Update API usage statistics for account
        
        Args:
            account_id: Account ID
            api_calls: Number of API calls made
            success: Whether the calls were successful
        """
        try:
            account = await self.db_session.get(PlatformAccount, account_id)
            if not account:
                return
            
            account.daily_api_used += api_calls
            
            if success:
                account.reset_error_count()
            else:
                account.increment_error_count()
            
            await self.db_session.commit()
            
            # Clear cache for this account's user
            self._clear_account_cache(str(account.user_id))
            
        except Exception as e:
            logger.error(f"Failed to update API usage for account {account_id}: {e}")
            await self.db_session.rollback()
    
    async def rotate_tokens_if_needed(self, account: PlatformAccount) -> bool:
        """Rotate tokens if they're expired or expiring soon
        
        Args:
            account: Platform account
            
        Returns:
            True if tokens were refreshed
        """
        if not account.refresh_token or not account.token_expires_at:
            return False
        
        # Check if token expires within 1 hour
        expires_soon = (
            account.token_expires_at - datetime.utcnow()
        ).total_seconds() < 3600
        
        if account.is_token_expired() or expires_soon:
            try:
                # This would call the platform-specific token refresh logic
                # For now, we'll just update the timestamp
                account.token_expires_at = datetime.utcnow() + timedelta(hours=24)
                await self.db_session.commit()
                
                logger.info(f"Refreshed tokens for account {account.id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to refresh tokens for account {account.id}: {e}")
                account.increment_error_count()
                await self.db_session.commit()
        
        return False
    
    async def get_account_performance_metrics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for all user accounts
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Performance metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get account performance data
        query = select(PlatformAccount).where(
            and_(
                PlatformAccount.user_id == user_id,
                PlatformAccount.created_at >= start_date
            )
        ).options(selectinload(PlatformAccount.sync_logs))
        
        result = await self.db_session.execute(query)
        accounts = result.scalars().all()
        
        metrics = {
            "period_days": days,
            "total_accounts": len(accounts),
            "platforms": {},
            "overall": {
                "total_api_calls": 0,
                "success_rate": 0.0,
                "average_response_time": 0.0
            }
        }
        
        for account in accounts:
            platform = account.platform_type.value
            
            if platform not in metrics["platforms"]:
                metrics["platforms"][platform] = {
                    "accounts": 0,
                    "total_api_calls": 0,
                    "successful_calls": 0,
                    "error_count": 0,
                    "health_status": "unknown"
                }
            
            platform_metrics = metrics["platforms"][platform]
            platform_metrics["accounts"] += 1
            platform_metrics["total_api_calls"] += account.daily_api_used
            platform_metrics["error_count"] += account.error_count
            platform_metrics["health_status"] = account.health_status
            
            # Calculate success rate
            if account.daily_api_used > 0:
                platform_metrics["successful_calls"] = (
                    account.daily_api_used - account.error_count
                )
        
        # Calculate overall metrics
        total_calls = sum(p["total_api_calls"] for p in metrics["platforms"].values())
        total_errors = sum(p["error_count"] for p in metrics["platforms"].values())
        
        metrics["overall"]["total_api_calls"] = total_calls
        if total_calls > 0:
            metrics["overall"]["success_rate"] = (
                (total_calls - total_errors) / total_calls
            ) * 100
        
        return metrics
    
    async def _encrypt_account_credentials(self, account_data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Encrypt sensitive account credentials"""
        credentials = {}
        
        sensitive_fields = ["api_key", "api_secret", "access_token", "refresh_token", "password"]
        
        for field in sensitive_fields:
            value = account_data.get(field)
            if value:
                credentials[field] = encrypt_sensitive_data(value)
            else:
                credentials[field] = None
        
        return credentials
    
    def _clear_account_cache(self, user_id: str):
        """Clear cached account data for user"""
        keys_to_remove = [
            key for key in self._account_cache.keys()
            if key.startswith(f"accounts_{user_id}")
        ]
        for key in keys_to_remove:
            del self._account_cache[key]
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.db_session.close()
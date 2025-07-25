"""
Business logic service for platform account management
"""
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from ..crud.platform_account import get_platform_account_crud, get_platform_sync_log_crud
from ..models.platform_account import PlatformAccount, AccountStatus, PlatformType
from ..schemas.platform_account import (
    PlatformAccountCreate,
    PlatformAccountUpdate,
    PlatformAccountConnectionTest,
    PlatformInfo,
    PlatformAccountStats,
    BulkOperationResponse
)
from ..utils.encryption import mask_sensitive_value, generate_audit_log_entry
import logging

logger = logging.getLogger(__name__)


class PlatformAccountService:
    """Service for managing platform accounts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.account_crud = get_platform_account_crud(db)
        self.sync_log_crud = get_platform_sync_log_crud(db)
    
    async def create_account(
        self, 
        user_id: UUID, 
        account_data: PlatformAccountCreate
    ) -> Tuple[PlatformAccount, bool]:
        """
        Create a new platform account with validation and testing
        
        Args:
            user_id: ID of the user creating the account
            account_data: Account creation data
            
        Returns:
            Tuple of (created account, connection test success)
        """
        try:
            # Create the account
            account = self.account_crud.create(user_id, account_data)
            
            # Test the connection
            test_result = await self.test_connection(account.id, user_id)
            
            # Update account status based on test result
            if test_result.success:
                self.account_crud.update_status(
                    account.id, 
                    AccountStatus.ACTIVE, 
                    "healthy"
                )
                account.status = AccountStatus.ACTIVE
                account.health_status = "healthy"
            else:
                self.account_crud.update_status(
                    account.id, 
                    AccountStatus.ERROR, 
                    "error"
                )
                account.status = AccountStatus.ERROR
                account.health_status = "error"
                account.last_error_message = test_result.message
            
            # Log the creation
            audit_entry = generate_audit_log_entry(
                str(user_id),
                "create_platform_account",
                str(account.id),
                {
                    "platform_type": account_data.platform_type.value,
                    "account_name": account_data.account_name,
                    "connection_test_success": test_result.success
                }
            )
            logger.info(f"Platform account created: {audit_entry}")
            
            return account, test_result.success
            
        except Exception as e:
            logger.error(f"Failed to create platform account: {e}")
            raise
    
    def get_account(self, account_id: UUID, user_id: UUID) -> Optional[PlatformAccount]:
        """Get platform account by ID with user authorization"""
        return self.account_crud.get_by_id(account_id, user_id)
    
    def get_user_accounts(
        self,
        user_id: UUID,
        platform_type: Optional[str] = None,
        status: Optional[AccountStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PlatformAccount]:
        """Get platform accounts for a user with filters"""
        return self.account_crud.get_by_user(
            user_id, platform_type, status, skip, limit
        )
    
    def update_account(
        self,
        account_id: UUID,
        user_id: UUID,
        update_data: PlatformAccountUpdate
    ) -> Optional[PlatformAccount]:
        """Update platform account with audit logging"""
        try:
            # Get original account for comparison
            original_account = self.account_crud.get_by_id(account_id, user_id)
            if not original_account:
                return None
            
            # Update the account
            updated_account = self.account_crud.update(account_id, user_id, update_data)
            if not updated_account:
                return None
            
            # Log the update
            changes = {}
            for field, value in update_data.dict(exclude_unset=True).items():
                if field != 'credentials':
                    original_value = getattr(original_account, field, None)
                    if original_value != value:
                        changes[field] = {"from": original_value, "to": value}
            
            if update_data.credentials:
                changes["credentials"] = "updated"
            
            audit_entry = generate_audit_log_entry(
                str(user_id),
                "update_platform_account",
                str(account_id),
                {"changes": changes}
            )
            logger.info(f"Platform account updated: {audit_entry}")
            
            return updated_account
            
        except Exception as e:
            logger.error(f"Failed to update platform account {account_id}: {e}")
            raise
    
    def delete_account(self, account_id: UUID, user_id: UUID) -> bool:
        """Delete platform account with audit logging"""
        try:
            # Get account details for logging
            account = self.account_crud.get_by_id(account_id, user_id)
            if not account:
                return False
            
            # Delete the account
            success = self.account_crud.delete(account_id, user_id)
            
            if success:
                # Log the deletion
                audit_entry = generate_audit_log_entry(
                    str(user_id),
                    "delete_platform_account",
                    str(account_id),
                    {
                        "platform_type": account.platform_type.value,
                        "account_name": account.account_name
                    }
                )
                logger.info(f"Platform account deleted: {audit_entry}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete platform account {account_id}: {e}")
            return False
    
    async def test_connection(
        self, 
        account_id: UUID, 
        user_id: UUID
    ) -> PlatformAccountConnectionTest:
        """
        Test platform account connection
        
        Args:
            account_id: Account ID to test
            user_id: User ID for authorization
            
        Returns:
            Connection test result
        """
        start_time = datetime.utcnow()
        
        try:
            # Get account and credentials
            account = self.account_crud.get_by_id(account_id, user_id)
            if not account:
                return PlatformAccountConnectionTest(
                    success=False,
                    message="Account not found",
                    tested_at=start_time
                )
            
            credentials = self.account_crud.get_decrypted_credentials(account_id, user_id)
            if not credentials:
                return PlatformAccountConnectionTest(
                    success=False,
                    message="Unable to retrieve credentials",
                    tested_at=start_time
                )
            
            # Test connection based on platform type
            test_result = await self._test_platform_connection(account.platform_type, credentials)
            
            # Calculate response time
            end_time = datetime.utcnow()
            response_time = int((end_time - start_time).total_seconds() * 1000)
            
            # Update account health status
            if test_result["success"]:
                self.account_crud.update_status(account_id, account.status, "healthy")
                account.reset_error_count()
            else:
                self.account_crud.update_status(account_id, account.status, "error")
                account.increment_error_count()
                account.last_error_message = test_result["message"]
            
            return PlatformAccountConnectionTest(
                success=test_result["success"],
                message=test_result["message"],
                response_time_ms=response_time,
                api_version=test_result.get("api_version"),
                rate_limit_remaining=test_result.get("rate_limit_remaining"),
                error_details=test_result.get("error_details"),
                tested_at=start_time
            )
            
        except Exception as e:
            logger.error(f"Connection test failed for account {account_id}: {e}")
            return PlatformAccountConnectionTest(
                success=False,
                message=f"Connection test error: {str(e)}",
                tested_at=start_time,
                error_details={"exception": str(e)}
            )
    
    async def _test_platform_connection(
        self, 
        platform_type: PlatformType, 
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test connection for specific platform
        
        Args:
            platform_type: Platform type
            credentials: Decrypted credentials
            
        Returns:
            Test result dictionary
        """
        try:
            if platform_type == PlatformType.COUPANG:
                return await self._test_coupang_connection(credentials)
            elif platform_type == PlatformType.NAVER:
                return await self._test_naver_connection(credentials)
            elif platform_type == PlatformType.ELEVEN_ST:
                return await self._test_11st_connection(credentials)
            else:
                return await self._test_generic_connection(platform_type, credentials)
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Platform connection test failed: {str(e)}",
                "error_details": {"exception": str(e)}
            }
    
    async def _test_coupang_connection(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test Coupang API connection"""
        try:
            # Coupang API test endpoint (mock implementation)
            async with httpx.AsyncClient(timeout=30.0) as client:
                # This would be the actual Coupang API endpoint
                url = "https://api-gateway.coupang.com/v2/providers/affiliate_open_api/apis/openapi/v1/products/categories"
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {credentials.get('access_key', '')}"
                }
                
                # Note: In production, you would use proper Coupang API authentication
                # This is a simplified mock test
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Coupang connection successful",
                        "api_version": "v1",
                        "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining")
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Coupang API error: {response.status_code}",
                        "error_details": {"status_code": response.status_code, "response": response.text}
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Coupang API connection timeout",
                "error_details": {"error_type": "timeout"}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Coupang connection error: {str(e)}",
                "error_details": {"exception": str(e)}
            }
    
    async def _test_naver_connection(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test Naver Commerce API connection"""
        try:
            # Naver Commerce API test (mock implementation)
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://api.commerce.naver.com/external/v1/categories"
                
                headers = {
                    "Content-Type": "application/json",
                    "X-Naver-Client-Id": credentials.get('api_key', ''),
                    "X-Naver-Client-Secret": credentials.get('api_secret', '')
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Naver connection successful",
                        "api_version": "v1"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Naver API error: {response.status_code}",
                        "error_details": {"status_code": response.status_code}
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"Naver connection error: {str(e)}",
                "error_details": {"exception": str(e)}
            }
    
    async def _test_11st_connection(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test 11st API connection"""
        try:
            # 11st API test (mock implementation)
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = "https://openapi.11st.co.kr/rest/auth/getAuth"
                
                data = {
                    "key": credentials.get('api_key', ''),
                    "secret": credentials.get('api_secret', '')
                }
                
                response = await client.post(url, json=data)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "11st connection successful",
                        "api_version": "v1"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"11st API error: {response.status_code}",
                        "error_details": {"status_code": response.status_code}
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"11st connection error: {str(e)}",
                "error_details": {"exception": str(e)}
            }
    
    async def _test_generic_connection(
        self, 
        platform_type: PlatformType, 
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test generic platform connection"""
        # For platforms without specific API test endpoints
        # we can do basic credential validation
        required_fields = ["api_key", "api_secret", "seller_id"]
        
        for field in required_fields:
            if field not in credentials or not credentials[field]:
                return {
                    "success": False,
                    "message": f"Missing required credential: {field}",
                    "error_details": {"missing_field": field}
                }
        
        # If all required fields are present, assume success
        # In production, you would implement actual API tests
        return {
            "success": True,
            "message": f"{platform_type.value} credentials validated",
            "api_version": "unknown"
        }
    
    def get_supported_platforms(self) -> List[PlatformInfo]:
        """Get list of supported platforms with their information"""
        platforms = [
            PlatformInfo(
                platform_type="coupang",
                display_name="쿠팡",
                description="대한민국 대표 이커머스 플랫폼",
                website_url="https://www.coupang.com",
                api_documentation_url="https://developers.coupang.com",
                required_credentials=["access_key", "secret_key", "vendor_id"],
                optional_credentials=["store_name"],
                supports_oauth=False,
                rate_limits={"requests_per_minute": 100, "daily_quota": 10000},
                features=["product_management", "order_management", "inventory_sync"]
            ),
            PlatformInfo(
                platform_type="naver",
                display_name="네이버 스마트스토어",
                description="네이버 쇼핑 플랫폼",
                website_url="https://smartstore.naver.com",
                api_documentation_url="https://developers.naver.com/docs/commerce",
                required_credentials=["client_id", "client_secret", "store_id"],
                optional_credentials=["store_name"],
                supports_oauth=True,
                rate_limits={"requests_per_minute": 60, "daily_quota": 5000},
                features=["product_management", "order_management", "review_management"]
            ),
            PlatformInfo(
                platform_type="11st",
                display_name="11번가",
                description="SK 그룹의 종합 온라인 쇼핑몰",
                website_url="https://www.11st.co.kr",
                api_documentation_url="https://openapi.11st.co.kr",
                required_credentials=["api_key", "secret_key", "seller_id"],
                optional_credentials=["store_name"],
                supports_oauth=False,
                rate_limits={"requests_per_minute": 80, "daily_quota": 8000},
                features=["product_management", "order_management", "promotion_management"]
            ),
            PlatformInfo(
                platform_type="gmarket",
                display_name="G마켓",
                description="이베이 코리아의 온라인 쇼핑몰",
                website_url="https://www.gmarket.co.kr",
                required_credentials=["api_key", "secret_key", "seller_id"],
                optional_credentials=["store_name"],
                supports_oauth=False,
                rate_limits={"requests_per_minute": 60, "daily_quota": 6000},
                features=["product_management", "order_management"]
            ),
            PlatformInfo(
                platform_type="auction",
                display_name="옥션",
                description="이베이 코리아의 온라인 경매 및 쇼핑몰",
                website_url="https://www.auction.co.kr",
                required_credentials=["api_key", "secret_key", "seller_id"],
                optional_credentials=["store_name"],
                supports_oauth=False,
                rate_limits={"requests_per_minute": 60, "daily_quota": 6000},
                features=["product_management", "order_management"]
            )
        ]
        
        return platforms
    
    def get_user_account_statistics(self, user_id: UUID) -> PlatformAccountStats:
        """Get comprehensive account statistics for a user"""
        stats_data = self.account_crud.get_user_account_stats(user_id)
        
        return PlatformAccountStats(
            total_accounts=stats_data["total_accounts"],
            active_accounts=stats_data["active_accounts"],
            healthy_accounts=stats_data["healthy_accounts"],
            accounts_with_errors=stats_data["accounts_with_errors"],
            platform_breakdown=stats_data["platform_breakdown"],
            last_updated=stats_data["last_updated"]
        )
    
    async def bulk_test_connections(
        self, 
        account_ids: List[UUID], 
        user_id: UUID
    ) -> BulkOperationResponse:
        """Test connections for multiple accounts"""
        started_at = datetime.utcnow()
        results = []
        successful_tests = 0
        
        for account_id in account_ids:
            try:
                test_result = await self.test_connection(account_id, user_id)
                results.append({
                    "account_id": str(account_id),
                    "success": test_result.success,
                    "message": test_result.message,
                    "response_time_ms": test_result.response_time_ms
                })
                
                if test_result.success:
                    successful_tests += 1
                    
            except Exception as e:
                results.append({
                    "account_id": str(account_id),
                    "success": False,
                    "message": f"Test failed: {str(e)}",
                    "error": str(e)
                })
        
        completed_at = datetime.utcnow()
        
        return BulkOperationResponse(
            operation="connection_test",
            total_accounts=len(account_ids),
            successful_accounts=successful_tests,
            failed_accounts=len(account_ids) - successful_tests,
            results=results,
            started_at=started_at,
            completed_at=completed_at
        )
    
    def bulk_update_sync_settings(
        self, 
        account_ids: List[UUID], 
        user_id: UUID,
        sync_enabled: bool,
        auto_pricing_enabled: Optional[bool] = None,
        auto_inventory_sync: Optional[bool] = None
    ) -> BulkOperationResponse:
        """Bulk update sync settings for multiple accounts"""
        started_at = datetime.utcnow()
        results = []
        successful_updates = 0
        
        for account_id in account_ids:
            try:
                update_data = PlatformAccountUpdate(
                    sync_enabled=sync_enabled,
                    auto_pricing_enabled=auto_pricing_enabled,
                    auto_inventory_sync=auto_inventory_sync
                )
                
                updated_account = self.account_crud.update(account_id, user_id, update_data)
                
                if updated_account:
                    results.append({
                        "account_id": str(account_id),
                        "success": True,
                        "message": "Sync settings updated successfully"
                    })
                    successful_updates += 1
                else:
                    results.append({
                        "account_id": str(account_id),
                        "success": False,
                        "message": "Account not found or access denied"
                    })
                    
            except Exception as e:
                results.append({
                    "account_id": str(account_id),
                    "success": False,
                    "message": f"Update failed: {str(e)}",
                    "error": str(e)
                })
        
        completed_at = datetime.utcnow()
        
        return BulkOperationResponse(
            operation="bulk_sync_settings_update",
            total_accounts=len(account_ids),
            successful_accounts=successful_updates,
            failed_accounts=len(account_ids) - successful_updates,
            results=results,
            started_at=started_at,
            completed_at=completed_at
        )
    
    async def perform_health_checks(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Perform health checks on accounts that need it"""
        try:
            # Get accounts that need health check
            accounts_to_check = self.account_crud.get_accounts_needing_health_check()
            
            if user_id:
                # Filter by user if specified
                accounts_to_check = [acc for acc in accounts_to_check if acc.user_id == user_id]
            
            health_check_results = []
            
            for account in accounts_to_check:
                try:
                    test_result = await self.test_connection(account.id, account.user_id)
                    health_check_results.append({
                        "account_id": str(account.id),
                        "platform_type": account.platform_type.value,
                        "account_name": account.account_name,
                        "success": test_result.success,
                        "message": test_result.message,
                        "response_time_ms": test_result.response_time_ms
                    })
                except Exception as e:
                    health_check_results.append({
                        "account_id": str(account.id),
                        "platform_type": account.platform_type.value,
                        "account_name": account.account_name,
                        "success": False,
                        "message": f"Health check error: {str(e)}"
                    })
            
            successful_checks = sum(1 for result in health_check_results if result["success"])
            
            return {
                "total_checked": len(health_check_results),
                "successful_checks": successful_checks,
                "failed_checks": len(health_check_results) - successful_checks,
                "results": health_check_results,
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check operation failed: {e}")
            return {
                "total_checked": 0,
                "successful_checks": 0,
                "failed_checks": 0,
                "results": [],
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }


def get_platform_account_service(db: Session) -> PlatformAccountService:
    """Get platform account service instance"""
    return PlatformAccountService(db)
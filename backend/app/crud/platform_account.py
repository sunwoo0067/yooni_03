"""
CRUD operations for platform accounts
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import IntegrityError

from ..models.platform_account import PlatformAccount, PlatformSyncLog, PlatformType, AccountStatus
from ..schemas.platform_account import (
    PlatformAccountCreate, 
    PlatformAccountUpdate,
    PlatformCredentials
)
from ..utils.encryption import get_encryption_manager
import logging

logger = logging.getLogger(__name__)


class PlatformAccountCRUD:
    """CRUD operations for platform accounts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.encryption_manager = get_encryption_manager()
    
    def create(self, user_id: UUID, account_data: PlatformAccountCreate) -> PlatformAccount:
        """
        Create a new platform account
        
        Args:
            user_id: ID of the user creating the account
            account_data: Account creation data
            
        Returns:
            Created platform account
            
        Raises:
            ValueError: If account creation fails
        """
        try:
            # Encrypt credentials
            encrypted_credentials = self._encrypt_credentials(account_data.credentials)
            
            # Create account instance
            db_account = PlatformAccount(
                id=uuid4(),
                user_id=user_id,
                platform_type=PlatformType(account_data.platform_type.value),
                account_name=account_data.account_name,
                account_id=account_data.account_id,
                seller_id=account_data.seller_id,
                store_name=account_data.store_name,
                store_url=account_data.store_url,
                
                # Set encrypted credentials
                **encrypted_credentials,
                
                # Configuration
                sync_enabled=account_data.sync_enabled,
                auto_pricing_enabled=account_data.auto_pricing_enabled,
                auto_inventory_sync=account_data.auto_inventory_sync,
                platform_settings=account_data.platform_settings,
                
                # Rate limiting
                daily_api_quota=account_data.daily_api_quota,
                rate_limit_per_minute=account_data.rate_limit_per_minute,
                
                # Financial
                commission_rate=account_data.commission_rate,
                monthly_fee=account_data.monthly_fee,
                currency=account_data.currency,
                
                # Status
                status=AccountStatus.PENDING_APPROVAL,
                health_status="unknown",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(db_account)
            self.db.commit()
            self.db.refresh(db_account)
            
            logger.info(f"Created platform account {db_account.id} for user {user_id}")
            return db_account
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create platform account: {e}")
            raise ValueError("Failed to create account - duplicate or invalid data")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating platform account: {e}")
            raise ValueError(f"Failed to create account: {str(e)}")
    
    def get_by_id(self, account_id: UUID, user_id: Optional[UUID] = None) -> Optional[PlatformAccount]:
        """
        Get platform account by ID
        
        Args:
            account_id: Account ID to retrieve
            user_id: Optional user ID for access control
            
        Returns:
            Platform account if found, None otherwise
        """
        query = self.db.query(PlatformAccount).filter(PlatformAccount.id == account_id)
        
        if user_id:
            query = query.filter(PlatformAccount.user_id == user_id)
        
        return query.first()
    
    def get_by_user(
        self, 
        user_id: UUID, 
        platform_type: Optional[str] = None,
        status: Optional[AccountStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PlatformAccount]:
        """
        Get platform accounts for a user
        
        Args:
            user_id: User ID
            platform_type: Optional platform type filter
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of platform accounts
        """
        query = self.db.query(PlatformAccount).filter(PlatformAccount.user_id == user_id)
        
        if platform_type:
            query = query.filter(PlatformAccount.platform_type == PlatformType(platform_type))
        
        if status:
            query = query.filter(PlatformAccount.status == status)
        
        return query.order_by(desc(PlatformAccount.created_at)).offset(skip).limit(limit).all()
    
    def update(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        update_data: PlatformAccountUpdate
    ) -> Optional[PlatformAccount]:
        """
        Update platform account
        
        Args:
            account_id: Account ID to update
            user_id: User ID for access control
            update_data: Update data
            
        Returns:
            Updated platform account if successful, None otherwise
        """
        try:
            # Get existing account
            db_account = self.get_by_id(account_id, user_id)
            if not db_account:
                return None
            
            # Update basic fields
            update_dict = update_data.dict(exclude_unset=True, exclude={'credentials'})
            
            for field, value in update_dict.items():
                if hasattr(db_account, field):
                    setattr(db_account, field, value)
            
            # Update credentials if provided
            if update_data.credentials:
                encrypted_credentials = self._encrypt_credentials(update_data.credentials)
                for field, value in encrypted_credentials.items():
                    if hasattr(db_account, field):
                        setattr(db_account, field, value)
            
            # Update timestamp
            db_account.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_account)
            
            logger.info(f"Updated platform account {account_id}")
            return db_account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update platform account {account_id}: {e}")
            raise ValueError(f"Failed to update account: {str(e)}")
    
    def delete(self, account_id: UUID, user_id: UUID) -> bool:
        """
        Delete platform account
        
        Args:
            account_id: Account ID to delete
            user_id: User ID for access control
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            db_account = self.get_by_id(account_id, user_id)
            if not db_account:
                return False
            
            self.db.delete(db_account)
            self.db.commit()
            
            logger.info(f"Deleted platform account {account_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete platform account {account_id}: {e}")
            return False
    
    def update_status(
        self, 
        account_id: UUID, 
        status: AccountStatus, 
        health_status: Optional[str] = None
    ) -> Optional[PlatformAccount]:
        """
        Update account status
        
        Args:
            account_id: Account ID
            status: New account status
            health_status: Optional new health status
            
        Returns:
            Updated account if successful
        """
        try:
            db_account = self.db.query(PlatformAccount).filter(
                PlatformAccount.id == account_id
            ).first()
            
            if not db_account:
                return None
            
            db_account.status = status
            if health_status:
                db_account.health_status = health_status
            db_account.last_health_check_at = datetime.utcnow()
            db_account.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_account)
            
            return db_account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update account status {account_id}: {e}")
            return None
    
    def update_sync_timestamp(self, account_id: UUID) -> bool:
        """
        Update last sync timestamp
        
        Args:
            account_id: Account ID
            
        Returns:
            True if updated successfully
        """
        try:
            db_account = self.db.query(PlatformAccount).filter(
                PlatformAccount.id == account_id
            ).first()
            
            if not db_account:
                return False
            
            db_account.last_sync_at = datetime.utcnow()
            db_account.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update sync timestamp for {account_id}: {e}")
            return False
    
    def increment_api_usage(self, account_id: UUID, count: int = 1) -> bool:
        """
        Increment daily API usage counter
        
        Args:
            account_id: Account ID
            count: Number of API calls to add
            
        Returns:
            True if updated successfully
        """
        try:
            db_account = self.db.query(PlatformAccount).filter(
                PlatformAccount.id == account_id
            ).first()
            
            if not db_account:
                return False
            
            db_account.daily_api_used += count
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to increment API usage for {account_id}: {e}")
            return False
    
    def reset_daily_api_usage(self, user_id: Optional[UUID] = None) -> int:
        """
        Reset daily API usage counters
        
        Args:
            user_id: Optional user ID to reset only specific user's accounts
            
        Returns:
            Number of accounts updated
        """
        try:
            query = self.db.query(PlatformAccount)
            
            if user_id:
                query = query.filter(PlatformAccount.user_id == user_id)
            
            updated_count = query.update({"daily_api_used": 0})
            self.db.commit()
            
            logger.info(f"Reset daily API usage for {updated_count} accounts")
            return updated_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset daily API usage: {e}")
            return 0
    
    def get_accounts_needing_health_check(self, interval_minutes: int = 30) -> List[PlatformAccount]:
        """
        Get accounts that need health check
        
        Args:
            interval_minutes: Health check interval in minutes
            
        Returns:
            List of accounts needing health check
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=interval_minutes)
        
        return self.db.query(PlatformAccount).filter(
            and_(
                PlatformAccount.status == AccountStatus.ACTIVE,
                or_(
                    PlatformAccount.last_health_check_at.is_(None),
                    PlatformAccount.last_health_check_at < cutoff_time
                )
            )
        ).all()
    
    def get_user_account_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get account statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing account statistics
        """
        query = self.db.query(PlatformAccount).filter(PlatformAccount.user_id == user_id)
        
        total_accounts = query.count()
        active_accounts = query.filter(PlatformAccount.status == AccountStatus.ACTIVE).count()
        healthy_accounts = query.filter(PlatformAccount.health_status == "healthy").count()
        error_accounts = query.filter(PlatformAccount.consecutive_errors > 0).count()
        
        # Platform breakdown
        platform_stats = self.db.query(
            PlatformAccount.platform_type,
            func.count(PlatformAccount.id).label('count')
        ).filter(
            PlatformAccount.user_id == user_id
        ).group_by(PlatformAccount.platform_type).all()
        
        platform_breakdown = {stat.platform_type.value: stat.count for stat in platform_stats}
        
        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "healthy_accounts": healthy_accounts,
            "accounts_with_errors": error_accounts,
            "platform_breakdown": platform_breakdown,
            "last_updated": datetime.utcnow()
        }
    
    def bulk_update_status(
        self, 
        account_ids: List[UUID], 
        user_id: UUID, 
        status: AccountStatus
    ) -> Dict[str, Any]:
        """
        Bulk update account status
        
        Args:
            account_ids: List of account IDs to update
            user_id: User ID for access control
            status: New status to set
            
        Returns:
            Dictionary with operation results
        """
        try:
            updated_count = self.db.query(PlatformAccount).filter(
                and_(
                    PlatformAccount.id.in_(account_ids),
                    PlatformAccount.user_id == user_id
                )
            ).update({
                "status": status,
                "updated_at": datetime.utcnow()
            }, synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Bulk updated {updated_count} accounts to status {status.value}")
            
            return {
                "total_requested": len(account_ids),
                "updated_count": updated_count,
                "success": True
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to bulk update account status: {e}")
            return {
                "total_requested": len(account_ids),
                "updated_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def _encrypt_credentials(self, credentials: PlatformCredentials) -> Dict[str, Optional[str]]:
        """
        Encrypt sensitive credential data
        
        Args:
            credentials: Credentials to encrypt
            
        Returns:
            Dictionary with encrypted credential fields
        """
        credential_dict = credentials.dict(exclude_unset=True)
        encrypted_dict = {}
        
        # Map credential fields to database fields
        field_mapping = {
            'api_key': 'api_key',
            'api_secret': 'api_secret',
            'secret_key': 'api_secret',  # Alias
            'access_key': 'api_key',  # For Coupang
            'client_id': 'api_key',   # For Naver
            'client_secret': 'api_secret',  # For Naver
            'access_token': 'access_token',
            'refresh_token': 'refresh_token',
            'vendor_id': 'seller_id',  # For Coupang
            'store_id': 'seller_id',   # For Naver
            'seller_id': 'seller_id',
            'token_expires_at': 'token_expires_at'
        }
        
        for cred_field, db_field in field_mapping.items():
            if cred_field in credential_dict and credential_dict[cred_field]:
                value = credential_dict[cred_field]
                
                # Don't encrypt datetime fields
                if cred_field == 'token_expires_at':
                    encrypted_dict[db_field] = value
                else:
                    # Encrypt sensitive string fields
                    encrypted_dict[db_field] = self.encryption_manager.encrypt(str(value))
        
        return encrypted_dict
    
    def get_decrypted_credentials(self, account_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get decrypted credentials for an account
        
        Args:
            account_id: Account ID
            user_id: User ID for access control
            
        Returns:
            Dictionary with decrypted credentials if authorized
        """
        try:
            db_account = self.get_by_id(account_id, user_id)
            if not db_account:
                return None
            
            credentials = {}
            
            # Decrypt fields if they exist
            if db_account.api_key:
                credentials['api_key'] = self.encryption_manager.decrypt(db_account.api_key)
            if db_account.api_secret:
                credentials['api_secret'] = self.encryption_manager.decrypt(db_account.api_secret)
            if db_account.access_token:
                credentials['access_token'] = self.encryption_manager.decrypt(db_account.access_token)
            if db_account.refresh_token:
                credentials['refresh_token'] = self.encryption_manager.decrypt(db_account.refresh_token)
            if db_account.seller_id:
                credentials['seller_id'] = db_account.seller_id
            if db_account.token_expires_at:
                credentials['token_expires_at'] = db_account.token_expires_at
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for account {account_id}: {e}")
            return None


# Sync log CRUD operations
class PlatformSyncLogCRUD:
    """CRUD operations for platform sync logs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_sync_log(
        self, 
        platform_account_id: UUID, 
        sync_type: str
    ) -> PlatformSyncLog:
        """Create a new sync log entry"""
        sync_log = PlatformSyncLog(
            id=uuid4(),
            platform_account_id=platform_account_id,
            sync_type=sync_type,
            started_at=datetime.utcnow(),
            status="running"
        )
        
        self.db.add(sync_log)
        self.db.commit()
        self.db.refresh(sync_log)
        
        return sync_log
    
    def complete_sync_log(
        self, 
        sync_log_id: UUID, 
        success_count: int = 0,
        error_count: int = 0,
        error_message: Optional[str] = None,
        sync_details: Optional[Dict[str, Any]] = None
    ) -> Optional[PlatformSyncLog]:
        """Complete a sync log entry"""
        try:
            sync_log = self.db.query(PlatformSyncLog).filter(
                PlatformSyncLog.id == sync_log_id
            ).first()
            
            if not sync_log:
                return None
            
            sync_log.completed_at = datetime.utcnow()
            sync_log.status = "completed" if error_count == 0 else "failed"
            sync_log.success_count = success_count
            sync_log.error_count = error_count
            sync_log.total_items = success_count + error_count
            sync_log.processed_items = success_count + error_count
            
            if sync_log.started_at:
                time_diff = sync_log.completed_at - sync_log.started_at
                sync_log.processing_time_seconds = int(time_diff.total_seconds())
            
            if error_message:
                sync_log.error_message = error_message
            
            if sync_details:
                sync_log.sync_details = sync_details
            
            self.db.commit()
            self.db.refresh(sync_log)
            
            return sync_log
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to complete sync log {sync_log_id}: {e}")
            return None
    
    def get_recent_sync_logs(
        self, 
        platform_account_id: UUID, 
        limit: int = 10
    ) -> List[PlatformSyncLog]:
        """Get recent sync logs for an account"""
        return self.db.query(PlatformSyncLog).filter(
            PlatformSyncLog.platform_account_id == platform_account_id
        ).order_by(desc(PlatformSyncLog.started_at)).limit(limit).all()


def get_platform_account_crud(db: Session) -> PlatformAccountCRUD:
    """Get platform account CRUD instance"""
    return PlatformAccountCRUD(db)


def get_platform_sync_log_crud(db: Session) -> PlatformSyncLogCRUD:
    """Get platform sync log CRUD instance"""
    return PlatformSyncLogCRUD(db)
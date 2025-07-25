"""
도매처 관련 CRUD 연산
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from app.crud.base import CRUDBase
from app.models.wholesaler import (
    WholesalerAccount,
    WholesalerProduct,
    CollectionLog,
    ScheduledCollection,
    ExcelUploadLog,
    WholesalerType,
    ConnectionStatus,
    CollectionStatus
)
from app.schemas.wholesaler import (
    WholesalerAccountCreate,
    WholesalerAccountUpdate,
    WholesalerProductCreate,
    WholesalerProductUpdate
)

logger = logging.getLogger(__name__)


class CRUDWholesalerAccount(CRUDBase[WholesalerAccount, WholesalerAccountCreate, WholesalerAccountUpdate]):
    """도매처 계정 CRUD"""
    
    def get_by_user_id(self, db: Session, user_id: int) -> List[WholesalerAccount]:
        """사용자 ID로 도매처 계정 목록 조회"""
        return db.query(self.model).filter(
            WholesalerAccount.user_id == user_id,
            WholesalerAccount.is_active == True
        ).all()
    
    def get_by_wholesaler_type(self, db: Session, user_id: int, 
                              wholesaler_type: WholesalerType) -> List[WholesalerAccount]:
        """도매처 유형별 계정 조회"""
        return db.query(self.model).filter(
            WholesalerAccount.user_id == user_id,
            WholesalerAccount.wholesaler_type == wholesaler_type,
            WholesalerAccount.is_active == True
        ).all()
    
    def get_active_accounts(self, db: Session, skip: int = 0, limit: int = 100) -> List[WholesalerAccount]:
        """활성 도매처 계정 조회"""
        return db.query(self.model).filter(
            WholesalerAccount.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_by_connection_status(self, db: Session, status: ConnectionStatus) -> List[WholesalerAccount]:
        """연결 상태별 계정 조회"""
        return db.query(self.model).filter(
            WholesalerAccount.connection_status == status,
            WholesalerAccount.is_active == True
        ).all()
    
    def update_connection_status(self, db: Session, account_id: int, 
                               status: ConnectionStatus, error_message: str = None) -> Optional[WholesalerAccount]:
        """연결 상태 업데이트"""
        account = self.get(db, account_id)
        if account:
            account.connection_status = status
            account.last_connected_at = datetime.utcnow() if status == ConnectionStatus.CONNECTED else account.last_connected_at
            account.last_error_message = error_message
            db.commit()
            db.refresh(account)
        return account
    
    def enable_auto_collect(self, db: Session, account_id: int, 
                           interval_hours: int = 24) -> Optional[WholesalerAccount]:
        """자동 수집 활성화"""
        account = self.get(db, account_id)
        if account:
            account.auto_collect_enabled = True
            account.collect_interval_hours = interval_hours
            db.commit()
            db.refresh(account)
        return account
    
    def disable_auto_collect(self, db: Session, account_id: int) -> Optional[WholesalerAccount]:
        """자동 수집 비활성화"""
        account = self.get(db, account_id)
        if account:
            account.auto_collect_enabled = False
            db.commit()
            db.refresh(account)
        return account


class CRUDWholesalerProduct(CRUDBase[WholesalerProduct, WholesalerProductCreate, WholesalerProductUpdate]):
    """도매처 상품 CRUD"""
    
    def get_by_wholesaler_account(self, db: Session, wholesaler_account_id: int,
                                 skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """도매처 계정별 상품 조회"""
        return db.query(self.model).filter(
            WholesalerProduct.wholesaler_account_id == wholesaler_account_id,
            WholesalerProduct.is_active == True
        ).order_by(desc(WholesalerProduct.last_updated_at)).offset(skip).limit(limit).all()
    
    def get_by_sku(self, db: Session, wholesaler_account_id: int, sku: str) -> Optional[WholesalerProduct]:
        """SKU로 상품 조회"""
        return db.query(self.model).filter(
            WholesalerProduct.wholesaler_account_id == wholesaler_account_id,
            WholesalerProduct.wholesaler_sku == sku,
            WholesalerProduct.is_active == True
        ).first()
    
    def get_by_product_id(self, db: Session, wholesaler_account_id: int, 
                         product_id: str) -> Optional[WholesalerProduct]:
        """도매처 상품 ID로 조회"""
        return db.query(self.model).filter(
            WholesalerProduct.wholesaler_account_id == wholesaler_account_id,
            WholesalerProduct.wholesaler_product_id == product_id,
            WholesalerProduct.is_active == True
        ).first()
    
    def get_recent_products(self, db: Session, wholesaler_account_id: int = None,
                           days: int = 7, skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """최근 수집된 상품 조회"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(self.model).filter(
            WholesalerProduct.first_collected_at >= cutoff_date,
            WholesalerProduct.is_active == True
        )
        
        if wholesaler_account_id:
            query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
        
        return query.order_by(desc(WholesalerProduct.first_collected_at)).offset(skip).limit(limit).all()
    
    def get_by_category(self, db: Session, category_path: str, 
                       wholesaler_account_id: int = None, skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """카테고리별 상품 조회"""
        query = db.query(self.model).filter(
            WholesalerProduct.category_path.ilike(f"%{category_path}%"),
            WholesalerProduct.is_active == True
        )
        
        if wholesaler_account_id:
            query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_price_range(self, db: Session, min_price: int, max_price: int,
                          wholesaler_account_id: int = None, skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """가격대별 상품 조회"""
        query = db.query(self.model).filter(
            WholesalerProduct.wholesale_price >= min_price,
            WholesalerProduct.wholesale_price <= max_price,
            WholesalerProduct.is_active == True
        )
        
        if wholesaler_account_id:
            query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
        
        return query.offset(skip).limit(limit).all()
    
    def get_low_stock_products(self, db: Session, threshold: int = 10,
                              wholesaler_account_id: int = None, skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """재고 부족 상품 조회"""
        query = db.query(self.model).filter(
            WholesalerProduct.stock_quantity <= threshold,
            WholesalerProduct.is_active == True
        )
        
        if wholesaler_account_id:
            query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
        
        return query.order_by(asc(WholesalerProduct.stock_quantity)).offset(skip).limit(limit).all()
    
    def get_out_of_stock_products(self, db: Session, wholesaler_account_id: int = None,
                                 skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """품절 상품 조회"""
        query = db.query(self.model).filter(
            or_(
                WholesalerProduct.stock_quantity == 0,
                WholesalerProduct.is_in_stock == False
            ),
            WholesalerProduct.is_active == True
        )
        
        if wholesaler_account_id:
            query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
        
        return query.offset(skip).limit(limit).all()
    
    def search_products(self, db: Session, keyword: str, wholesaler_account_id: int = None,
                       skip: int = 0, limit: int = 100) -> List[WholesalerProduct]:
        """상품명으로 검색"""
        query = db.query(self.model).filter(
            WholesalerProduct.name.ilike(f"%{keyword}%"),
            WholesalerProduct.is_active == True
        )
        
        if wholesaler_account_id:
            query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
        
        return query.offset(skip).limit(limit).all()
    
    def bulk_update_stock(self, db: Session, updates: List[Dict]) -> int:
        """재고 대량 업데이트"""
        updated_count = 0
        for update in updates:
            product = self.get_by_sku(db, update['wholesaler_account_id'], update['sku'])
            if product:
                product.stock_quantity = update['stock_quantity']
                product.is_in_stock = update.get('is_in_stock', product.stock_quantity > 0)
                product.last_updated_at = datetime.utcnow()
                updated_count += 1
        
        db.commit()
        return updated_count
    
    def bulk_update_prices(self, db: Session, updates: List[Dict]) -> int:
        """가격 대량 업데이트"""
        updated_count = 0
        for update in updates:
            product = self.get_by_sku(db, update['wholesaler_account_id'], update['sku'])
            if product:
                if 'wholesale_price' in update:
                    product.wholesale_price = update['wholesale_price']
                if 'retail_price' in update:
                    product.retail_price = update['retail_price']
                product.last_updated_at = datetime.utcnow()
                updated_count += 1
        
        db.commit()
        return updated_count


class CRUDCollectionLog(CRUDBase[CollectionLog, dict, dict]):
    """수집 로그 CRUD"""
    
    def get_by_wholesaler_account(self, db: Session, wholesaler_account_id: int,
                                 skip: int = 0, limit: int = 100) -> List[CollectionLog]:
        """도매처 계정별 수집 로그 조회"""
        return db.query(self.model).filter(
            CollectionLog.wholesaler_account_id == wholesaler_account_id
        ).order_by(desc(CollectionLog.started_at)).offset(skip).limit(limit).all()
    
    def get_by_status(self, db: Session, status: CollectionStatus,
                     skip: int = 0, limit: int = 100) -> List[CollectionLog]:
        """상태별 수집 로그 조회"""
        return db.query(self.model).filter(
            CollectionLog.status == status
        ).order_by(desc(CollectionLog.started_at)).offset(skip).limit(limit).all()
    
    def get_recent_logs(self, db: Session, days: int = 7,
                       skip: int = 0, limit: int = 100) -> List[CollectionLog]:
        """최근 수집 로그 조회"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return db.query(self.model).filter(
            CollectionLog.started_at >= cutoff_date
        ).order_by(desc(CollectionLog.started_at)).offset(skip).limit(limit).all()
    
    def get_failed_logs(self, db: Session, wholesaler_account_id: int = None,
                       skip: int = 0, limit: int = 100) -> List[CollectionLog]:
        """실패한 수집 로그 조회"""
        query = db.query(self.model).filter(
            CollectionLog.status == CollectionStatus.FAILED
        )
        
        if wholesaler_account_id:
            query = query.filter(CollectionLog.wholesaler_account_id == wholesaler_account_id)
        
        return query.order_by(desc(CollectionLog.started_at)).offset(skip).limit(limit).all()
    
    def get_statistics(self, db: Session, wholesaler_account_id: int = None, days: int = 30) -> Dict:
        """수집 통계 조회"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(self.model).filter(CollectionLog.started_at >= cutoff_date)
        
        if wholesaler_account_id:
            query = query.filter(CollectionLog.wholesaler_account_id == wholesaler_account_id)
        
        logs = query.all()
        
        return {
            'total_collections': len(logs),
            'successful_collections': len([log for log in logs if log.status == CollectionStatus.COMPLETED]),
            'failed_collections': len([log for log in logs if log.status == CollectionStatus.FAILED]),
            'running_collections': len([log for log in logs if log.status == CollectionStatus.RUNNING]),
            'total_products_collected': sum(log.products_collected or 0 for log in logs),
            'total_products_updated': sum(log.products_updated or 0 for log in logs),
            'total_products_failed': sum(log.products_failed or 0 for log in logs),
            'avg_duration_seconds': sum(log.duration_seconds or 0 for log in logs if log.duration_seconds) / 
                                  len([log for log in logs if log.duration_seconds]) if logs else 0
        }


class CRUDScheduledCollection(CRUDBase[ScheduledCollection, dict, dict]):
    """스케줄 수집 CRUD"""
    
    def get_by_wholesaler_account(self, db: Session, wholesaler_account_id: int) -> List[ScheduledCollection]:
        """도매처 계정별 스케줄 조회"""
        return db.query(self.model).filter(
            ScheduledCollection.wholesaler_account_id == wholesaler_account_id
        ).order_by(desc(ScheduledCollection.created_at)).all()
    
    def get_active_schedules(self, db: Session, skip: int = 0, limit: int = 100) -> List[ScheduledCollection]:
        """활성 스케줄 조회"""
        return db.query(self.model).filter(
            ScheduledCollection.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_by_cron_pattern(self, db: Session, pattern: str) -> List[ScheduledCollection]:
        """크론 패턴별 스케줄 조회"""
        return db.query(self.model).filter(
            ScheduledCollection.cron_expression == pattern,
            ScheduledCollection.is_active == True
        ).all()
    
    def activate_schedule(self, db: Session, schedule_id: int) -> Optional[ScheduledCollection]:
        """스케줄 활성화"""
        schedule = self.get(db, schedule_id)
        if schedule:
            schedule.is_active = True
            schedule.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(schedule)
        return schedule
    
    def deactivate_schedule(self, db: Session, schedule_id: int) -> Optional[ScheduledCollection]:
        """스케줄 비활성화"""
        schedule = self.get(db, schedule_id)
        if schedule:
            schedule.is_active = False
            schedule.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(schedule)
        return schedule
    
    def update_run_statistics(self, db: Session, schedule_id: int, success: bool) -> Optional[ScheduledCollection]:
        """실행 통계 업데이트"""
        schedule = self.get(db, schedule_id)
        if schedule:
            schedule.total_runs += 1
            if success:
                schedule.successful_runs += 1
            else:
                schedule.failed_runs += 1
            schedule.last_run_at = datetime.utcnow()
            schedule.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(schedule)
        return schedule


class CRUDExcelUploadLog(CRUDBase[ExcelUploadLog, dict, dict]):
    """엑셀 업로드 로그 CRUD"""
    
    def get_by_wholesaler_account(self, db: Session, wholesaler_account_id: int,
                                 skip: int = 0, limit: int = 100) -> List[ExcelUploadLog]:
        """도매처 계정별 업로드 로그 조회"""
        return db.query(self.model).filter(
            ExcelUploadLog.wholesaler_account_id == wholesaler_account_id
        ).order_by(desc(ExcelUploadLog.uploaded_at)).offset(skip).limit(limit).all()
    
    def get_by_status(self, db: Session, status: CollectionStatus,
                     skip: int = 0, limit: int = 100) -> List[ExcelUploadLog]:
        """상태별 업로드 로그 조회"""
        return db.query(self.model).filter(
            ExcelUploadLog.status == status
        ).order_by(desc(ExcelUploadLog.uploaded_at)).offset(skip).limit(limit).all()
    
    def get_by_file_hash(self, db: Session, file_hash: str, 
                        wholesaler_account_id: int) -> Optional[ExcelUploadLog]:
        """파일 해시로 업로드 로그 조회 (중복 확인용)"""
        return db.query(self.model).filter(
            ExcelUploadLog.file_hash == file_hash,
            ExcelUploadLog.wholesaler_account_id == wholesaler_account_id
        ).first()
    
    def get_processing_logs(self, db: Session, skip: int = 0, limit: int = 100) -> List[ExcelUploadLog]:
        """처리 중인 업로드 로그 조회"""
        return db.query(self.model).filter(
            ExcelUploadLog.status.in_([CollectionStatus.PENDING, CollectionStatus.RUNNING])
        ).order_by(desc(ExcelUploadLog.uploaded_at)).offset(skip).limit(limit).all()
    
    def get_statistics(self, db: Session, wholesaler_account_id: int = None, days: int = 30) -> Dict:
        """업로드 통계 조회"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(self.model).filter(ExcelUploadLog.uploaded_at >= cutoff_date)
        
        if wholesaler_account_id:
            query = query.filter(ExcelUploadLog.wholesaler_account_id == wholesaler_account_id)
        
        logs = query.all()
        
        return {
            'total_uploads': len(logs),
            'successful_uploads': len([log for log in logs if log.status == CollectionStatus.COMPLETED]),
            'failed_uploads': len([log for log in logs if log.status == CollectionStatus.FAILED]),
            'processing_uploads': len([log for log in logs if log.status in [CollectionStatus.PENDING, CollectionStatus.RUNNING]]),
            'total_rows_processed': sum(log.processed_rows or 0 for log in logs),
            'total_successful_rows': sum(log.success_rows or 0 for log in logs),
            'total_failed_rows': sum(log.failed_rows or 0 for log in logs),
            'total_file_size': sum(log.file_size or 0 for log in logs)
        }


# CRUD 인스턴스 생성
crud_wholesaler_account = CRUDWholesalerAccount(WholesalerAccount)
crud_wholesaler_product = CRUDWholesalerProduct(WholesalerProduct)
crud_collection_log = CRUDCollectionLog(CollectionLog)
crud_scheduled_collection = CRUDScheduledCollection(ScheduledCollection)
crud_excel_upload_log = CRUDExcelUploadLog(ExcelUploadLog)
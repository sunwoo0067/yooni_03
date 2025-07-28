from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Product, CollectionLog
from collectors.base_collector import BaseCollector, CollectionResult
from utils.logger import app_logger

class IncrementalSync:
    """증분 수집 관리자"""
    
    def __init__(self):
        self.logger = app_logger
        
    def get_last_sync_time(self, supplier: str, db: Session) -> Optional[datetime]:
        """마지막 성공적인 수집 시간 조회"""
        last_log = db.query(CollectionLog).filter(
            CollectionLog.supplier == supplier,
            CollectionLog.status == 'completed',
            CollectionLog.collection_type == 'incremental'
        ).order_by(CollectionLog.end_time.desc()).first()
        
        if last_log and last_log.end_time:
            return last_log.end_time
            
        # 증분 수집 기록이 없으면 전체 수집의 마지막 시간 확인
        last_full = db.query(CollectionLog).filter(
            CollectionLog.supplier == supplier,
            CollectionLog.status == 'completed',
            CollectionLog.collection_type == 'full'
        ).order_by(CollectionLog.end_time.desc()).first()
        
        if last_full and last_full.end_time:
            return last_full.end_time
            
        # 아무 기록도 없으면 24시간 전부터
        return datetime.now() - timedelta(days=1)
        
    def get_changed_products(self, supplier: str, since: datetime, db: Session) -> List[str]:
        """특정 시간 이후 변경된 상품 코드 목록 조회"""
        
        # 실제 구현에서는 도매처 API의 변경 상품 조회 기능을 사용
        # 여기서는 데이터베이스의 updated_at 기준으로 시뮬레이션
        
        changed_products = db.query(Product.product_code).filter(
            Product.supplier == supplier,
            Product.updated_at >= since
        ).all()
        
        return [p[0] for p in changed_products]
        
    def sync_incremental(self, collector: BaseCollector, db: Session) -> CollectionResult:
        """증분 수집 실행"""
        
        supplier = collector.supplier_code
        self.logger.info(f"{supplier} 증분 수집 시작")
        
        # 수집 로그 생성
        collection_log = CollectionLog(
            supplier=supplier,
            collection_type='incremental',
            status='running',
            start_time=datetime.now()
        )
        db.add(collection_log)
        db.commit()
        
        result = CollectionResult(
            success=False,
            start_time=datetime.now()
        )
        
        try:
            # 마지막 동기화 시간 확인
            last_sync = self.get_last_sync_time(supplier, db)
            self.logger.info(f"마지막 동기화: {last_sync}")
            
            # 변경된 상품 확인 (실제로는 API 호출)
            if supplier == 'zentrade':
                # 젠트레이드는 전체 수집만 지원
                self.logger.info("젠트레이드는 전체 수집만 지원합니다")
                changed_count = 0
            else:
                # 테스트용: 임의로 몇 개 상품을 "변경됨"으로 표시
                changed_count = self._simulate_changed_products(supplier, last_sync, db)
                
            # 수집기의 증분 수집 실행
            if collector.authenticate():
                product_count = 0
                new_count = 0
                updated_count = 0
                
                # 증분 모드로 수집
                for product_data in collector.collect_products(incremental=True):
                    product_count += 1
                    
                    # 기존 상품 확인
                    existing = db.query(Product).filter(
                        Product.product_code == product_data.product_code
                    ).first()
                    
                    if existing:
                        # 업데이트
                        existing.product_info = product_data.product_info
                        existing.updated_at = datetime.now()
                        updated_count += 1
                        self.logger.debug(f"상품 업데이트: {product_data.product_code}")
                    else:
                        # 신규
                        new_product = Product(
                            product_code=product_data.product_code,
                            product_info=product_data.product_info,
                            supplier=product_data.supplier
                        )
                        db.add(new_product)
                        new_count += 1
                        self.logger.debug(f"신규 상품: {product_data.product_code}")
                    
                    # 배치 커밋 (100개마다)
                    if product_count % 100 == 0:
                        db.commit()
                        self.logger.info(f"진행 상황: {product_count}개 처리")
                
                # 최종 커밋
                db.commit()
                
                result.success = True
                result.total_count = product_count
                result.new_count = new_count
                result.updated_count = updated_count
                
                self.logger.info(
                    f"{supplier} 증분 수집 완료: "
                    f"총 {product_count}개 (신규 {new_count}, 업데이트 {updated_count})"
                )
            else:
                result.error_message = "인증 실패"
                
        except Exception as e:
            db.rollback()
            result.error_message = str(e)
            result.error_count = 1
            self.logger.error(f"{supplier} 증분 수집 실패: {e}")
            
        finally:
            result.end_time = datetime.now()
            
            # 수집 로그 업데이트
            collection_log.end_time = result.end_time
            collection_log.status = 'completed' if result.success else 'failed'
            collection_log.total_count = result.total_count
            collection_log.new_count = result.new_count
            collection_log.updated_count = result.updated_count
            collection_log.error_count = result.error_count
            collection_log.error_message = result.error_message
            db.commit()
            
        return result
        
    def _simulate_changed_products(self, supplier: str, since: datetime, db: Session) -> int:
        """테스트용: 변경된 상품 시뮬레이션"""
        
        # 최근 상품 중 일부를 "변경됨"으로 표시
        recent_products = db.query(Product).filter(
            Product.supplier == supplier
        ).order_by(Product.created_at.desc()).limit(3).all()
        
        changed_count = 0
        for product in recent_products:
            # updated_at을 현재 시간으로 변경
            product.updated_at = datetime.now()
            
            # 상품 정보에 증분 수집 표시 추가
            if isinstance(product.product_info, dict):
                product.product_info['last_incremental_sync'] = datetime.now().isoformat()
                product.product_info['sync_type'] = 'incremental'
                
            changed_count += 1
            
        db.commit()
        
        self.logger.info(f"{supplier} 테스트용 변경 상품: {changed_count}개")
        return changed_count
        
    def get_sync_status(self, db: Session) -> Dict[str, Any]:
        """전체 동기화 상태 조회"""
        
        status = {
            'suppliers': []
        }
        
        for supplier in ['zentrade', 'ownerclan', 'domeggook']:
            # 마지막 전체 수집
            last_full = db.query(CollectionLog).filter(
                CollectionLog.supplier == supplier,
                CollectionLog.status == 'completed',
                CollectionLog.collection_type == 'full'
            ).order_by(CollectionLog.end_time.desc()).first()
            
            # 마지막 증분 수집
            last_incremental = db.query(CollectionLog).filter(
                CollectionLog.supplier == supplier,
                CollectionLog.status == 'completed',
                CollectionLog.collection_type == 'incremental'
            ).order_by(CollectionLog.end_time.desc()).first()
            
            # 총 상품 수
            product_count = db.query(Product).filter(
                Product.supplier == supplier
            ).count()
            
            supplier_status = {
                'supplier': supplier,
                'product_count': product_count,
                'last_full_sync': last_full.end_time.isoformat() if last_full and last_full.end_time else None,
                'last_incremental_sync': last_incremental.end_time.isoformat() if last_incremental and last_incremental.end_time else None,
                'full_sync_count': db.query(CollectionLog).filter(
                    CollectionLog.supplier == supplier,
                    CollectionLog.collection_type == 'full'
                ).count(),
                'incremental_sync_count': db.query(CollectionLog).filter(
                    CollectionLog.supplier == supplier,
                    CollectionLog.collection_type == 'incremental'
                ).count()
            }
            
            status['suppliers'].append(supplier_status)
            
        return status
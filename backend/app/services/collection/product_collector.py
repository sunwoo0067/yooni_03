import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..wholesalers.base_wholesaler import CollectionType, ProductData, CollectionResult
from ..wholesalers.wholesaler_manager import WholesalerManager, get_wholesaler_manager
from ...models.wholesaler import WholesalerAccount, CollectionLog, CollectionStatus, WholesalerProduct
from ...database import get_db
from .data_normalizer import DataNormalizer


class ProductCollector:
    """상품 수집기 - 도매처별 상품 수집 및 저장 관리"""
    
    def __init__(self, db: Session = None, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.wholesaler_manager = get_wholesaler_manager()
        self.data_normalizer = DataNormalizer(logger=self.logger)
        self._collection_cache: Dict[int, Set[str]] = {}  # 중복 방지 캐시
        
    async def collect_products_from_account(
        self,
        account: WholesalerAccount,
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products: int = 1000,
        save_to_db: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> CollectionResult:
        """단일 도매처 계정에서 상품 수집"""
        
        # 수집 로그 생성
        collection_log = self._create_collection_log(account, collection_type, filters)
        
        try:
            self.logger.info(
                f"상품 수집 시작: {account.account_name} "
                f"(타입: {collection_type.value}, 최대: {max_products}개)"
            )
            
            # 도매처 매니저를 통해 상품 수집
            result = await self.wholesaler_manager.collect_products(
                account=account,
                collection_type=collection_type,
                filters=filters,
                max_products=max_products
            )
            
            if result.success:
                # 데이터 정규화 및 저장
                if save_to_db and result.products:
                    saved_count = await self._save_products_to_db(
                        account, result.products, progress_callback
                    )
                    
                    # 수집 로그 업데이트
                    collection_log.products_collected = saved_count
                    collection_log.status = CollectionStatus.COMPLETED
                    
                    self.logger.info(f"상품 저장 완료: {saved_count}개")
                else:
                    collection_log.products_collected = len(result.products)
                    collection_log.status = CollectionStatus.COMPLETED
                    
                # 성공 시 로그 업데이트
                collection_log.completed_at = datetime.utcnow()
                collection_log.duration_seconds = int(result.execution_time.total_seconds())
                collection_log.collection_summary = result.summary
                
            else:
                # 실패 시 로그 업데이트
                collection_log.status = CollectionStatus.FAILED
                collection_log.error_message = '; '.join(result.errors)
                collection_log.completed_at = datetime.utcnow()
                
            # 로그 저장
            if self.db:
                self.db.add(collection_log)
                self.db.commit()
                
            return result
            
        except Exception as e:
            error_msg = f"상품 수집 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            
            # 실패 로그 저장
            collection_log.status = CollectionStatus.FAILED
            collection_log.error_message = error_msg
            collection_log.completed_at = datetime.utcnow()
            
            if self.db:
                self.db.add(collection_log)
                self.db.commit()
                
            # 실패 결과 반환
            failed_result = CollectionResult()
            failed_result.errors.append(error_msg)
            return failed_result
            
    async def collect_from_multiple_accounts(
        self,
        accounts: List[WholesalerAccount],
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products_per_account: int = 1000,
        concurrent: bool = True,
        save_to_db: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[int, CollectionResult]:
        """여러 도매처 계정에서 상품 수집"""
        
        self.logger.info(f"다중 계정 상품 수집 시작: {len(accounts)}개 계정")
        
        results = {}
        
        if concurrent:
            # 비동기 동시 수집
            tasks = []
            for account in accounts:
                # 각 계정별 진행률 콜백
                account_progress_callback = None
                if progress_callback:
                    account_progress_callback = lambda current, total, acc_name=account.account_name: \
                        progress_callback(acc_name, current, total)
                        
                task = self.collect_products_from_account(
                    account=account,
                    collection_type=collection_type,
                    filters=filters,
                    max_products=max_products_per_account,
                    save_to_db=save_to_db,
                    progress_callback=account_progress_callback
                )
                tasks.append((account.id, task))
                
            # 모든 태스크 실행
            completed_tasks = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            
            # 결과 정리
            for i, (account_id, _) in enumerate(tasks):
                result = completed_tasks[i]
                if isinstance(result, Exception):
                    # 예외 발생한 경우
                    error_result = CollectionResult()
                    error_result.errors.append(str(result))
                    results[account_id] = error_result
                else:
                    results[account_id] = result
                    
        else:
            # 순차 수집
            for account in accounts:
                try:
                    account_progress_callback = None
                    if progress_callback:
                        account_progress_callback = lambda current, total, acc_name=account.account_name: \
                            progress_callback(acc_name, current, total)
                            
                    result = await self.collect_products_from_account(
                        account=account,
                        collection_type=collection_type,
                        filters=filters,
                        max_products=max_products_per_account,
                        save_to_db=save_to_db,
                        progress_callback=account_progress_callback
                    )
                    results[account.id] = result
                    
                    # 계정 간 대기 시간
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_result = CollectionResult()
                    error_result.errors.append(str(e))
                    results[account.id] = error_result
                    
        # 전체 결과 요약
        total_collected = sum(len(result.products) for result in results.values() if result.products)
        total_errors = sum(len(result.errors) for result in results.values())
        
        self.logger.info(
            f"다중 계정 수집 완료: 총 {total_collected}개 상품, {total_errors}개 오류"
        )
        
        return results
        
    async def collect_recent_products(
        self,
        accounts: List[WholesalerAccount],
        days: int = 7,
        max_products_per_account: int = 1000,
        save_to_db: bool = True
    ) -> Dict[int, CollectionResult]:
        """최근 상품 수집"""
        
        filters = {'days': days}
        
        return await self.collect_from_multiple_accounts(
            accounts=accounts,
            collection_type=CollectionType.RECENT,
            filters=filters,
            max_products_per_account=max_products_per_account,
            save_to_db=save_to_db
        )
        
    async def collect_category_products(
        self,
        accounts: List[WholesalerAccount],
        category_filters: Dict[int, List[str]],  # account_id -> category_list
        max_products_per_account: int = 1000,
        save_to_db: bool = True
    ) -> Dict[int, CollectionResult]:
        """카테고리별 상품 수집"""
        
        results = {}
        
        for account in accounts:
            if account.id in category_filters:
                categories = category_filters[account.id]
                filters = {'categories': categories}
                
                result = await self.collect_products_from_account(
                    account=account,
                    collection_type=CollectionType.CATEGORY,
                    filters=filters,
                    max_products=max_products_per_account,
                    save_to_db=save_to_db
                )
                
                results[account.id] = result
                
                # 계정 간 대기
                await asyncio.sleep(1)
                
        return results
        
    async def _save_products_to_db(
        self,
        account: WholesalerAccount,
        products: List[ProductData],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """상품 데이터를 데이터베이스에 저장"""
        
        if not self.db:
            self.logger.warning("데이터베이스 세션이 없어 상품을 저장할 수 없습니다")
            return 0
            
        saved_count = 0
        batch_size = 100
        
        # 중복 방지를 위한 기존 상품 ID 조회
        existing_product_ids = set()
        try:
            existing_products = self.db.query(WholesalerProduct.wholesaler_product_id)\
                .filter(WholesalerProduct.wholesaler_account_id == account.id)\
                .all()
            existing_product_ids = {p.wholesaler_product_id for p in existing_products}
        except Exception as e:
            self.logger.error(f"기존 상품 ID 조회 실패: {str(e)}")
            
        # 배치 단위로 처리
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            try:
                for product_data in batch:
                    # 정규화
                    normalized_data = self.data_normalizer.normalize_product_data(
                        product_data, account.wholesaler_type
                    )
                    
                    # 중복 확인
                    if normalized_data['wholesaler_product_id'] in existing_product_ids:
                        # 기존 상품 업데이트
                        existing_product = self.db.query(WholesalerProduct)\
                            .filter(
                                WholesalerProduct.wholesaler_account_id == account.id,
                                WholesalerProduct.wholesaler_product_id == normalized_data['wholesaler_product_id']
                            ).first()
                            
                        if existing_product:
                            self._update_existing_product(existing_product, normalized_data)
                    else:
                        # 새 상품 생성
                        new_product = WholesalerProduct(
                            wholesaler_account_id=account.id,
                            **normalized_data
                        )
                        self.db.add(new_product)
                        existing_product_ids.add(normalized_data['wholesaler_product_id'])
                        
                    saved_count += 1
                    
                # 배치 커밋
                self.db.commit()
                
                # 진행률 콜백
                if progress_callback:
                    progress_callback(min(i + batch_size, len(products)), len(products))
                    
            except Exception as e:
                self.logger.error(f"상품 저장 배치 실패 (인덱스 {i}-{i+batch_size}): {str(e)}")
                self.db.rollback()
                continue
                
        return saved_count
        
    def _update_existing_product(
        self,
        existing_product: WholesalerProduct,
        normalized_data: Dict[str, Any]
    ):
        """기존 상품 정보 업데이트"""
        
        # 업데이트 가능한 필드들
        updateable_fields = [
            'name', 'description', 'wholesale_price', 'retail_price',
            'discount_rate', 'stock_quantity', 'is_in_stock',
            'main_image_url', 'additional_images', 'options', 'variants',
            'shipping_info', 'raw_data'
        ]
        
        for field in updateable_fields:
            if field in normalized_data:
                setattr(existing_product, field, normalized_data[field])
                
        existing_product.last_updated_at = datetime.utcnow()
        
    def _create_collection_log(
        self,
        account: WholesalerAccount,
        collection_type: CollectionType,
        filters: Optional[Dict[str, Any]] = None
    ) -> CollectionLog:
        """수집 로그 생성"""
        
        collection_log = CollectionLog(
            wholesaler_account_id=account.id,
            collection_type=collection_type.value,
            status=CollectionStatus.RUNNING,
            filters=filters,
            started_at=datetime.utcnow()
        )
        
        return collection_log
        
    async def get_collection_statistics(
        self,
        account_ids: Optional[List[int]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """수집 통계 조회"""
        
        if not self.db:
            return {}
            
        try:
            # 기본 쿼리
            query = self.db.query(CollectionLog)
            
            # 계정 필터
            if account_ids:
                query = query.filter(CollectionLog.wholesaler_account_id.in_(account_ids))
                
            # 기간 필터
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(CollectionLog.started_at >= cutoff_date)
            
            logs = query.all()
            
            # 통계 계산
            stats = {
                'total_collections': len(logs),
                'successful_collections': len([log for log in logs if log.status == CollectionStatus.COMPLETED]),
                'failed_collections': len([log for log in logs if log.status == CollectionStatus.FAILED]),
                'total_products_collected': sum(log.products_collected or 0 for log in logs),
                'average_collection_time': 0,
                'by_account': {},
                'by_collection_type': {},
                'recent_logs': []
            }
            
            # 평균 수집 시간
            completed_logs = [log for log in logs if log.status == CollectionStatus.COMPLETED and log.duration_seconds]
            if completed_logs:
                stats['average_collection_time'] = sum(log.duration_seconds for log in completed_logs) / len(completed_logs)
                
            # 계정별 통계
            account_stats = {}
            for log in logs:
                account_id = log.wholesaler_account_id
                if account_id not in account_stats:
                    account_stats[account_id] = {
                        'total': 0,
                        'successful': 0,
                        'products_collected': 0
                    }
                    
                account_stats[account_id]['total'] += 1
                if log.status == CollectionStatus.COMPLETED:
                    account_stats[account_id]['successful'] += 1
                    account_stats[account_id]['products_collected'] += log.products_collected or 0
                    
            stats['by_account'] = account_stats
            
            # 수집 타입별 통계
            type_stats = {}
            for log in logs:
                collection_type = log.collection_type
                if collection_type not in type_stats:
                    type_stats[collection_type] = {
                        'total': 0,
                        'successful': 0,
                        'products_collected': 0
                    }
                    
                type_stats[collection_type]['total'] += 1
                if log.status == CollectionStatus.COMPLETED:
                    type_stats[collection_type]['successful'] += 1
                    type_stats[collection_type]['products_collected'] += log.products_collected or 0
                    
            stats['by_collection_type'] = type_stats
            
            # 최근 로그 (최대 10개)
            recent_logs = sorted(logs, key=lambda x: x.started_at, reverse=True)[:10]
            stats['recent_logs'] = [
                {
                    'id': log.id,
                    'account_id': log.wholesaler_account_id,
                    'collection_type': log.collection_type,
                    'status': log.status.value,
                    'products_collected': log.products_collected,
                    'started_at': log.started_at.isoformat(),
                    'duration_seconds': log.duration_seconds
                }
                for log in recent_logs
            ]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"수집 통계 조회 실패: {str(e)}")
            return {}
            
    async def cleanup_old_logs(self, days: int = 90):
        """오래된 수집 로그 정리"""
        
        if not self.db:
            return
            
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = self.db.query(CollectionLog)\
                .filter(CollectionLog.started_at < cutoff_date)\
                .delete()
                
            self.db.commit()
            
            self.logger.info(f"오래된 수집 로그 {deleted_count}개 삭제 완료")
            
        except Exception as e:
            self.logger.error(f"로그 정리 실패: {str(e)}")
            self.db.rollback()
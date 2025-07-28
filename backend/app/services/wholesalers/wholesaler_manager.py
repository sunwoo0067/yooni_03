"""도매처 통합 관리 서비스"""
import asyncio
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
import logging

from .base_wholesaler import BaseWholesaler, CollectionType, ProductData
from .zentrade_api import ZentradeAPIFixed as ZentradeAPI
from .ownerclan_api import OwnerClanAPIFixed as OwnerClanAPI
from .domeggook_api import DomeggookAPIFixed as DomeggookAPI
from ...models.wholesaler import WholesalerType
from ...core.config import settings
from ...crud.wholesaler import crud_wholesaler_account
from ...schemas.wholesaler import WholesalerAccountCreate, WholesalerAccountUpdate
from sqlalchemy.orm import Session


class WholesalerManager:
    """도매처 통합 관리자"""
    
    # 도매처 타입과 API 클래스 매핑
    WHOLESALER_CLASSES: Dict[WholesalerType, Type[BaseWholesaler]] = {
        WholesalerType.ZENTRADE: ZentradeAPI,
        WholesalerType.OWNERCLAN: OwnerClanAPI,
        WholesalerType.DOMEGGOOK: DomeggookAPI,
    }
    
    def __init__(self, db: Session = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self._instances: Dict[int, BaseWholesaler] = {}
        self._active_collections: Dict[int, asyncio.Task] = {}
        
    def _get_api_instance(self, wholesaler_id: int) -> Optional[BaseWholesaler]:
        """도매처 API 인스턴스 반환 (캐싱)"""
        if wholesaler_id in self._instances:
            return self._instances[wholesaler_id]
            
        if not self.db:
            self.logger.error("데이터베이스 세션이 필요합니다")
            return None
            
        # DB에서 도매처 정보 조회
        wholesaler = crud_wholesaler.get(self.db, id=wholesaler_id)
        if not wholesaler:
            self.logger.error(f"도매처를 찾을 수 없습니다: {wholesaler_id}")
            return None
            
        # API 클래스 확인
        api_class = self.WHOLESALER_CLASSES.get(wholesaler.wholesaler_type)
        if not api_class:
            self.logger.error(f"지원하지 않는 도매처 타입: {wholesaler.wholesaler_type}")
            return None
            
        # API 인스턴스 생성
        try:
            credentials = wholesaler.api_credentials or {}
            instance = api_class(credentials, logger=self.logger)
            self._instances[wholesaler_id] = instance
            return instance
            
        except Exception as e:
            self.logger.error(f"API 인스턴스 생성 실패: {str(e)}")
            return None
            
    async def test_connection(self, wholesaler_id: int) -> Dict[str, Any]:
        """도매처 연결 테스트"""
        api = self._get_api_instance(wholesaler_id)
        if not api:
            return {
                'success': False,
                'message': '도매처 API 인스턴스를 생성할 수 없습니다',
                'error_details': {'error_type': 'instance_creation_failed'}
            }
            
        result = await api.test_connection()
        
        # 연결 상태 DB 업데이트
        if self.db and result['success']:
            wholesaler = crud_wholesaler.get(self.db, id=wholesaler_id)
            if wholesaler:
                update_data = WholesalerUpdate(
                    is_active=True,
                    last_sync_at=datetime.utcnow()
                )
                crud_wholesaler.update(self.db, db_obj=wholesaler, obj_in=update_data)
                
        return result
        
    async def collect_products(
        self,
        wholesaler_id: int,
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products: int = 1000,
        callback=None
    ) -> Dict[str, Any]:
        """도매처 상품 수집"""
        api = self._get_api_instance(wholesaler_id)
        if not api:
            return {
                'success': False,
                'message': '도매처 API 인스턴스를 생성할 수 없습니다',
                'collected_count': 0
            }
            
        collected_products = []
        errors = []
        start_time = datetime.now()
        
        try:
            # 기존 수집 작업이 있으면 취소
            if wholesaler_id in self._active_collections:
                self._active_collections[wholesaler_id].cancel()
                
            # 새로운 수집 작업 시작
            async def collect():
                async for product in api.collect_products(
                    collection_type=collection_type,
                    filters=filters,
                    max_products=max_products
                ):
                    collected_products.append(product)
                    
                    # 콜백 함수 실행 (진행 상황 알림 등)
                    if callback:
                        await callback({
                            'wholesaler_id': wholesaler_id,
                            'product': product,
                            'collected_count': len(collected_products),
                            'progress': len(collected_products) / max_products * 100
                        })
                        
            # 수집 작업을 태스크로 실행
            task = asyncio.create_task(collect())
            self._active_collections[wholesaler_id] = task
            
            await task
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 수집 결과 DB 업데이트
            if self.db:
                wholesaler = crud_wholesaler.get(self.db, id=wholesaler_id)
                if wholesaler:
                    update_data = WholesalerUpdate(
                        last_sync_at=datetime.utcnow(),
                        product_count=len(collected_products)
                    )
                    crud_wholesaler.update(self.db, db_obj=wholesaler, obj_in=update_data)
                    
            return {
                'success': True,
                'message': f'{len(collected_products)}개 상품 수집 완료',
                'collected_count': len(collected_products),
                'duration_seconds': duration,
                'products': collected_products,
                'errors': errors
            }
            
        except asyncio.CancelledError:
            return {
                'success': False,
                'message': '수집 작업이 취소되었습니다',
                'collected_count': len(collected_products),
                'products': collected_products
            }
            
        except Exception as e:
            self.logger.error(f"상품 수집 중 오류 발생: {str(e)}")
            return {
                'success': False,
                'message': f'수집 중 오류 발생: {str(e)}',
                'collected_count': len(collected_products),
                'products': collected_products,
                'errors': [str(e)]
            }
            
        finally:
            # 작업 목록에서 제거
            if wholesaler_id in self._active_collections:
                del self._active_collections[wholesaler_id]
                
    async def collect_all_wholesalers(
        self,
        collection_type: CollectionType = CollectionType.ALL,
        filters: Optional[Dict[str, Any]] = None,
        max_products_per_wholesaler: int = 1000
    ) -> Dict[str, Any]:
        """모든 활성 도매처에서 상품 수집"""
        if not self.db:
            return {
                'success': False,
                'message': '데이터베이스 세션이 필요합니다',
                'results': {}
            }
            
        # 활성 도매처 목록 조회
        wholesalers = crud_wholesaler.get_active_wholesalers(self.db)
        
        if not wholesalers:
            return {
                'success': True,
                'message': '활성 도매처가 없습니다',
                'results': {}
            }
            
        # 병렬로 수집 실행
        tasks = []
        for wholesaler in wholesalers:
            task = self.collect_products(
                wholesaler_id=wholesaler.id,
                collection_type=collection_type,
                filters=filters,
                max_products=max_products_per_wholesaler
            )
            tasks.append((wholesaler.id, task))
            
        # 모든 작업 완료 대기
        results = {}
        total_collected = 0
        total_errors = 0
        
        for wholesaler_id, task in tasks:
            try:
                result = await task
                results[wholesaler_id] = result
                total_collected += result.get('collected_count', 0)
                if not result['success']:
                    total_errors += 1
                    
            except Exception as e:
                self.logger.error(f"도매처 {wholesaler_id} 수집 실패: {str(e)}")
                results[wholesaler_id] = {
                    'success': False,
                    'message': str(e),
                    'collected_count': 0
                }
                total_errors += 1
                
        return {
            'success': total_errors == 0,
            'message': f'총 {total_collected}개 상품 수집 완료 (오류: {total_errors}개 도매처)',
            'total_collected': total_collected,
            'total_errors': total_errors,
            'results': results
        }
        
    async def get_stock_info(
        self,
        wholesaler_id: int,
        product_codes: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """재고 정보 조회"""
        api = self._get_api_instance(wholesaler_id)
        if not api:
            return {
                code: {
                    'stock_quantity': 0,
                    'is_in_stock': False,
                    'error': 'API instance not available'
                }
                for code in product_codes
            }
            
        return await api.get_stock_info(product_codes)
        
    async def get_product_detail(
        self,
        wholesaler_id: int,
        product_code: str
    ) -> Optional[ProductData]:
        """상품 상세 정보 조회"""
        api = self._get_api_instance(wholesaler_id)
        if not api:
            return None
            
        return await api.get_product_detail(product_code)
        
    async def get_categories(self, wholesaler_id: int) -> List[Dict[str, Any]]:
        """카테고리 목록 조회"""
        api = self._get_api_instance(wholesaler_id)
        if not api:
            return []
            
        return await api.get_categories()
        
    def get_collection_status(self, wholesaler_id: int) -> Dict[str, Any]:
        """수집 작업 상태 조회"""
        if wholesaler_id not in self._active_collections:
            return {
                'is_running': False,
                'message': '실행 중인 수집 작업이 없습니다'
            }
            
        task = self._active_collections[wholesaler_id]
        return {
            'is_running': not task.done(),
            'is_cancelled': task.cancelled() if task.done() else False,
            'has_error': task.exception() is not None if task.done() else False
        }
        
    def cancel_collection(self, wholesaler_id: int) -> bool:
        """수집 작업 취소"""
        if wholesaler_id not in self._active_collections:
            return False
            
        task = self._active_collections[wholesaler_id]
        task.cancel()
        return True
        
    async def cleanup(self):
        """리소스 정리"""
        # 모든 활성 수집 작업 취소
        for task in self._active_collections.values():
            task.cancel()
            
        # 작업 완료 대기
        if self._active_collections:
            await asyncio.gather(
                *self._active_collections.values(),
                return_exceptions=True
            )
            
        self._active_collections.clear()
        self._instances.clear()
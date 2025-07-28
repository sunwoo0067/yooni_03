"""
도매처 상품 동기화 서비스
전체 도매처 카탈로그를 DB에 동기화하는 배치 작업
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...models.collected_product import CollectedProduct, CollectionBatch, WholesalerSource, CollectionStatus
from ...models.collected_product_history import CollectedProductHistory, ChangeType
from ...services.database.database import get_db
from ...services.wholesalers.wholesaler_manager import WholesalerManager
from ...services.wholesalers.base_wholesaler import CollectionType, ProductData, CollectionResult
from .category_mapper import category_mapper


class WholesalerSyncService:
    """도매처 상품 동기화 서비스"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.wholesaler_manager = WholesalerManager()
        
    async def sync_all_wholesalers(
        self,
        collection_type: CollectionType = CollectionType.ALL,
        max_products_per_wholesaler: int = 10000
    ) -> Dict[str, CollectionResult]:
        """모든 도매처에서 상품 동기화"""
        results = {}
        
        # 활성화된 도매처 목록 조회
        active_wholesalers = await self.wholesaler_manager.get_active_wholesalers()
        
        for wholesaler_type in active_wholesalers:
            try:
                self.logger.info(f"{wholesaler_type.value} 동기화 시작")
                
                result = await self.sync_wholesaler(
                    wholesaler_type, 
                    collection_type,
                    max_products_per_wholesaler
                )
                results[wholesaler_type.value] = result
                
                self.logger.info(
                    f"{wholesaler_type.value} 동기화 완료: "
                    f"{result.collected}개 수집, {result.updated}개 업데이트, "
                    f"{result.failed}개 실패"
                )
                
            except Exception as e:
                error_msg = f"{wholesaler_type.value} 동기화 중 오류: {str(e)}"
                self.logger.error(error_msg)
                
                # 실패 결과 생성
                failed_result = CollectionResult()
                failed_result.success = False
                failed_result.errors.append(error_msg)
                results[wholesaler_type.value] = failed_result
                
        return results
    
    async def sync_wholesaler(
        self,
        wholesaler_type: WholesalerSource,
        collection_type: CollectionType = CollectionType.ALL,
        max_products: int = 10000
    ) -> CollectionResult:
        """특정 도매처 상품 동기화"""
        start_time = datetime.utcnow()
        result = CollectionResult()
        
        # 배치 ID 생성
        batch_id = f"sync_{wholesaler_type.value}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 도매처 API 클라이언트 생성
            wholesaler_client = await self.wholesaler_manager.get_client(wholesaler_type)
            if not wholesaler_client:
                raise Exception(f"{wholesaler_type.value} API 클라이언트 생성 실패")
            
            # DB 세션 생성
            db = next(get_db())
            
            # 배치 정보 생성
            collection_batch = CollectionBatch(
                batch_id=batch_id,
                source=wholesaler_type,
                keyword="전체동기화",  # 전체 동기화는 키워드가 없음
                max_products=max_products,
                filters={"collection_type": collection_type.value},
                status="running",
                started_at=start_time
            )
            
            db.add(collection_batch)
            db.commit()
            
            async with wholesaler_client:
                # 연결 테스트
                connection_test = await wholesaler_client.test_connection()
                if not connection_test['success']:
                    raise Exception(f"연결 실패: {connection_test['message']}")
                
                # 전체 상품 수집 시작
                collected_count = 0
                updated_count = 0
                failed_count = 0
                
                self.logger.info(f"{wholesaler_type.value} 상품 수집 시작 (최대 {max_products}개)")
                
                async for product_data in wholesaler_client.collect_products(
                    collection_type=collection_type,
                    max_products=max_products
                ):
                    try:
                        # DB에서 기존 상품 확인
                        existing_product = db.query(CollectedProduct).filter(
                            and_(
                                CollectedProduct.source == wholesaler_type,
                                CollectedProduct.supplier_id == product_data.wholesaler_product_id
                            )
                        ).first()
                        
                        if existing_product:
                            # 기존 상품 업데이트
                            if self._should_update_product(existing_product, product_data):
                                self._update_collected_product(existing_product, product_data, batch_id, db)
                                updated_count += 1
                                result.updated += 1
                        else:
                            # 새 상품 추가
                            new_product = self._create_collected_product(
                                product_data, wholesaler_type, batch_id
                            )
                            db.add(new_product)
                            db.flush()  # ID 생성을 위해 flush
                            
                            # 신규 수집 이력 생성
                            new_collection_history = CollectedProductHistory(
                                collected_product_id=new_product.id,
                                source=wholesaler_type,
                                supplier_id=product_data.wholesaler_product_id,
                                change_type=ChangeType.NEW_COLLECTION,
                                new_price=product_data.wholesale_price,
                                new_stock_quantity=product_data.stock_quantity,
                                new_stock_status="available" if product_data.is_in_stock else "out_of_stock",
                                changes_summary={'action': 'new_product_collected'},
                                batch_id=batch_id
                            )
                            db.add(new_collection_history)
                            
                            collected_count += 1
                            result.collected += 1
                        
                        # 배치 커밋 (100개씩)
                        if (collected_count + updated_count) % 100 == 0:
                            db.commit()
                            self.logger.info(
                                f"진행률: 수집 {collected_count}개, 업데이트 {updated_count}개"
                            )
                        
                    except Exception as e:
                        failed_count += 1
                        result.failed += 1
                        error_msg = f"상품 처리 실패 ({product_data.wholesaler_product_id}): {str(e)}"
                        result.errors.append(error_msg)
                        self.logger.error(error_msg)
                        continue
                
                # 최종 커밋
                db.commit()
                
                # 배치 완료 처리
                collection_batch.status = "completed"
                collection_batch.completed_at = datetime.utcnow()
                collection_batch.total_collected = collected_count + updated_count
                collection_batch.successful_collections = collected_count + updated_count
                collection_batch.failed_collections = failed_count
                
                db.commit()
                
                result.success = True
                result.total_found = collected_count + updated_count + failed_count
                
        except Exception as e:
            error_msg = f"{wholesaler_type.value} 동기화 실패: {str(e)}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
            
            # 배치 실패 처리
            try:
                db = next(get_db())
                collection_batch = db.query(CollectionBatch).filter(
                    CollectionBatch.batch_id == batch_id
                ).first()
                if collection_batch:
                    collection_batch.status = "failed"
                    collection_batch.error_message = error_msg
                    collection_batch.completed_at = datetime.utcnow()
                    db.commit()
            except:
                pass
        
        finally:
            result.execution_time = datetime.utcnow() - start_time
            result.summary = {
                'wholesaler': wholesaler_type.value,
                'collection_type': collection_type.value,
                'batch_id': batch_id,
                'execution_time_seconds': result.execution_time.total_seconds(),
                'success_rate': (result.collected + result.updated) / max(result.total_found, 1) * 100
            }
        
        return result
    
    def _should_update_product(
        self, 
        existing_product: CollectedProduct, 
        new_data: ProductData
    ) -> bool:
        """상품 업데이트 필요 여부 확인"""
        # 가격이 변경된 경우
        if existing_product.price != new_data.wholesale_price:
            return True
        
        # 재고 상태가 변경된 경우
        if existing_product.stock_quantity != new_data.stock_quantity:
            return True
        
        # 상품명이 변경된 경우
        if existing_product.name != new_data.name:
            return True
        
        # 이미지가 변경된 경우
        if existing_product.main_image_url != new_data.main_image_url:
            return True
        
        # 24시간 이상 지난 경우 업데이트
        if datetime.utcnow() - existing_product.updated_at > timedelta(hours=24):
            return True
        
        return False
    
    def _update_collected_product(
        self,
        existing_product: CollectedProduct,
        new_data: ProductData,
        batch_id: str,
        db: Session = None
    ):
        """기존 상품 정보 업데이트 및 변경 이력 추적"""
        changes_summary = {}
        
        # 가격 변경 확인
        if existing_product.price != new_data.wholesale_price:
            old_price = float(existing_product.price) if existing_product.price else 0
            new_price = float(new_data.wholesale_price)
            price_change = new_price - old_price
            price_change_pct = (price_change / old_price * 100) if old_price > 0 else 0
            
            changes_summary['price'] = {
                'old': old_price,
                'new': new_price,
                'change': price_change,
                'change_pct': round(price_change_pct, 2)
            }
            
            # 가격 변경 이력 생성
            if db:
                price_history = CollectedProductHistory(
                    collected_product_id=existing_product.id,
                    source=existing_product.source,
                    supplier_id=existing_product.supplier_id,
                    change_type=ChangeType.PRICE_CHANGE,
                    old_price=existing_product.price,
                    new_price=new_data.wholesale_price,
                    price_change_amount=price_change,
                    price_change_percentage=price_change_pct,
                    changes_summary=changes_summary,
                    batch_id=batch_id
                )
                db.add(price_history)
        
        # 재고 변경 확인
        old_stock_status = existing_product.stock_status
        new_stock_status = "available" if new_data.is_in_stock else "out_of_stock"
        
        if (existing_product.stock_quantity != new_data.stock_quantity or 
            old_stock_status != new_stock_status):
            
            changes_summary['stock'] = {
                'old_quantity': existing_product.stock_quantity,
                'new_quantity': new_data.stock_quantity,
                'old_status': old_stock_status,
                'new_status': new_stock_status
            }
            
            # 재고 변경 이력 생성
            if db:
                stock_history = CollectedProductHistory(
                    collected_product_id=existing_product.id,
                    source=existing_product.source,
                    supplier_id=existing_product.supplier_id,
                    change_type=ChangeType.STOCK_CHANGE,
                    old_stock_quantity=existing_product.stock_quantity,
                    new_stock_quantity=new_data.stock_quantity,
                    old_stock_status=old_stock_status,
                    new_stock_status=new_stock_status,
                    changes_summary=changes_summary,
                    batch_id=batch_id
                )
                db.add(stock_history)
        
        # 기존 업데이트 로직
        existing_product.name = new_data.name
        existing_product.description = new_data.description
        existing_product.price = new_data.wholesale_price
        existing_product.original_price = new_data.retail_price
        existing_product.wholesale_price = new_data.wholesale_price
        existing_product.stock_quantity = new_data.stock_quantity
        existing_product.stock_status = new_stock_status
        existing_product.main_image_url = new_data.main_image_url
        existing_product.image_urls = new_data.additional_images
        existing_product.specifications = new_data.options
        existing_product.attributes = new_data.variants
        existing_product.shipping_info = new_data.shipping_info
        existing_product.raw_data = new_data.raw_data
        existing_product.collection_batch_id = batch_id
        existing_product.updated_at = datetime.utcnow()
        
        # 만료된 상품이면 다시 활성화
        if existing_product.status == CollectionStatus.EXPIRED:
            existing_product.status = CollectionStatus.COLLECTED
            
            # 상태 변경 이력 생성
            if db:
                status_history = CollectedProductHistory(
                    collected_product_id=existing_product.id,
                    source=existing_product.source,
                    supplier_id=existing_product.supplier_id,
                    change_type=ChangeType.STATUS_CHANGE,
                    old_status="expired",
                    new_status="collected",
                    changes_summary={'status_reactivated': True},
                    batch_id=batch_id
                )
                db.add(status_history)
    
    def _create_collected_product(
        self,
        product_data: ProductData,
        wholesaler_type: WholesalerSource,
        batch_id: str
    ) -> CollectedProduct:
        """새 상품 정보 생성"""
        # 카테고리 매핑
        standard_category, category_confidence = category_mapper.map_category(
            wholesaler_type,
            product_data.category_path,
            product_data.name
        )
        
        return CollectedProduct(
            source=wholesaler_type,
            collection_keyword="전체동기화",
            collection_batch_id=batch_id,
            supplier_id=product_data.wholesaler_product_id,
            supplier_name=wholesaler_type.value,
            supplier_url=self._build_product_url(wholesaler_type, product_data.wholesaler_product_id),
            name=product_data.name,
            description=product_data.description,
            brand=None,  # 도매처 API에서 브랜드 정보 제공 시 추가
            category=product_data.category_path,
            price=product_data.wholesale_price,
            original_price=product_data.retail_price,
            wholesale_price=product_data.wholesale_price,
            minimum_order_quantity=1,  # 기본값
            stock_status="available" if product_data.is_in_stock else "out_of_stock",
            stock_quantity=product_data.stock_quantity,
            main_image_url=product_data.main_image_url,
            image_urls=product_data.additional_images,
            specifications=product_data.options,
            attributes={
                **(product_data.variants or {}),
                "standard_category": standard_category.value,
                "category_confidence": category_confidence
            },
            shipping_info=product_data.shipping_info,
            status=CollectionStatus.COLLECTED,
            quality_score=self._calculate_quality_score(product_data),
            popularity_score=None,  # 나중에 계산 로직 추가
            raw_data=product_data.raw_data,
            collected_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)  # 30일 후 만료
        )
    
    def _build_product_url(self, wholesaler_type: WholesalerSource, product_id: str) -> str:
        """상품 URL 생성"""
        url_templates = {
            WholesalerSource.OWNERCLAN: f"https://www.ownerclan.com/goods/{product_id}",
            WholesalerSource.DOMEME: f"https://domeme.co.kr/product/{product_id}",
            WholesalerSource.GENTRADE: f"https://www.gentrade.co.kr/product/{product_id}"
        }
        return url_templates.get(wholesaler_type, f"https://{wholesaler_type.value}.com/product/{product_id}")
    
    def _calculate_quality_score(self, product_data: ProductData) -> float:
        """상품 품질 점수 계산"""
        score = 5.0  # 기본 점수
        
        # 이미지가 있으면 +1점
        if product_data.main_image_url:
            score += 1.0
        
        # 상세 설명이 있으면 +1점
        if product_data.description and len(product_data.description) > 20:
            score += 1.0
        
        # 재고가 있으면 +1점
        if product_data.is_in_stock and product_data.stock_quantity > 0:
            score += 1.0
        
        # 옵션이 있으면 +1점
        if product_data.variants and len(product_data.variants) > 1:
            score += 1.0
        
        # 추가 이미지가 있으면 +0.5점
        if product_data.additional_images and len(product_data.additional_images) > 0:
            score += 0.5
        
        return min(score, 10.0)  # 최대 10점
    
    async def cleanup_expired_products(self, days_to_keep: int = 30):
        """만료된 상품 정리"""
        try:
            db = next(get_db())
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # 만료된 상품들을 EXPIRED 상태로 변경
            expired_count = db.query(CollectedProduct).filter(
                and_(
                    CollectedProduct.updated_at < cutoff_date,
                    CollectedProduct.status == CollectionStatus.COLLECTED
                )
            ).update({
                CollectedProduct.status: CollectionStatus.EXPIRED
            })
            
            db.commit()
            
            self.logger.info(f"{expired_count}개 상품을 만료 처리했습니다")
            
            return expired_count
            
        except Exception as e:
            self.logger.error(f"만료 상품 정리 중 오류: {str(e)}")
            return 0
    
    async def get_sync_statistics(self) -> Dict[str, Any]:
        """동기화 통계 조회"""
        try:
            db = next(get_db())
            
            # 전체 수집된 상품 수
            total_products = db.query(CollectedProduct).count()
            
            # 도매처별 상품 수
            by_source = {}
            for source in WholesalerSource:
                count = db.query(CollectedProduct).filter(
                    CollectedProduct.source == source
                ).count()
                by_source[source.value] = count
            
            # 상태별 상품 수
            by_status = {}
            for status in CollectionStatus:
                count = db.query(CollectedProduct).filter(
                    CollectedProduct.status == status
                ).count()
                by_status[status.value] = count
            
            # 최근 배치 정보
            recent_batches = db.query(CollectionBatch).order_by(
                CollectionBatch.started_at.desc()
            ).limit(5).all()
            
            batch_info = []
            for batch in recent_batches:
                batch_info.append({
                    'batch_id': batch.batch_id,
                    'source': batch.source.value,
                    'status': batch.status,
                    'total_collected': batch.total_collected,
                    'started_at': batch.started_at.isoformat() if batch.started_at else None,
                    'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                    'error_message': batch.error_message
                })
            
            return {
                'total_products': total_products,
                'by_source': by_source,
                'by_status': by_status,
                'recent_batches': batch_info,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"통계 조회 중 오류: {str(e)}")
            return {
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat()
            }
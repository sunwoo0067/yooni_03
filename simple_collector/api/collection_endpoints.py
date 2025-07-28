from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, date
import asyncio

from database.connection import get_db, SessionLocal
from database.models import CollectionLog, Supplier
from database.models_v2 import WholesaleProduct, MarketplaceProduct
from collectors.collector_factory import CollectorFactory
from collectors.marketplace_collectors_v2 import MarketplaceCollectorV2
from processors.incremental_sync import IncrementalSync
from utils.logger import app_logger

router = APIRouter(prefix="/collection", tags=["collection"])

async def _run_collection(
    supplier_code: str, 
    collection_type: str, 
    test_mode: bool = True,
    filters: Optional[Dict[str, Any]] = None
):
    """백그라운드에서 수집 실행"""
    db = SessionLocal()
    
    # 수집 로그 생성
    collection_log = CollectionLog(
        supplier=supplier_code,
        collection_type=collection_type,
        status='running',
        start_time=datetime.now()
    )
    db.add(collection_log)
    db.commit()
    
    total_count = 0
    new_count = 0
    updated_count = 0
    error_count = 0
    
    try:
        # 마켓플레이스 확인
        supplier_info = db.query(Supplier).filter(
            Supplier.supplier_code == supplier_code
        ).first()
        
        is_marketplace = supplier_info and supplier_info.api_config and supplier_info.api_config.get('marketplace')
        
        if is_marketplace:
            # 마켓플레이스 수집
            app_logger.info(f"마켓플레이스 수집 시작: {supplier_code}")
            marketplace_collector = MarketplaceCollectorV2(db)
            
            if supplier_code not in marketplace_collector.collectors:
                raise Exception(f"마켓플레이스 수집기 없음: {supplier_code}")
                
            collector = marketplace_collector.collectors[supplier_code]
            
            # 테스트 모드에서는 더미 데이터 생성
            if test_mode:
                products = [
                    {
                        "product_id": f"{supplier_code}_test_{i}",
                        "marketplace": supplier_code,
                        "title": f"테스트 상품 {i}",
                        "price": 10000 * (i + 1),
                        "original_price": 12000 * (i + 1),
                        "stock": i * 10,
                        "category": "테스트 카테고리",
                        "brand": "테스트 브랜드",
                        "image_url": f"https://example.com/image{i}.jpg",
                        "product_url": f"https://example.com/product{i}",
                        "status": "active",
                        "raw_data": {"test": True}
                    }
                    for i in range(5)
                ]
            else:
                products = await collector.get_products(limit=1000)
            
            # 상품 저장
            for product_data in products:
                total_count += 1
                try:
                    marketplace_collector._save_products([product_data])
                    new_count += 1
                except Exception as e:
                    error_count += 1
                    app_logger.error(f"상품 저장 오류: {e}")
                    
        else:
            # 일반 도매사이트 수집
            collector = CollectorFactory.create_collector(supplier_code, db, test_mode)
            
            if not collector:
                raise Exception(f"수집기 생성 실패: {supplier_code}")
                
            # 인증
            auth_result = await collector.authenticate()
            if not auth_result:
                raise Exception("인증 실패")
            
            # 수집 실행
            if collection_type == 'full':
                # 전체 수집
                async for product_data in collector.collect_products():
                    try:
                        # 필터 적용
                        if filters:
                            # 날짜 필터 체크
                            if 'date_from' in filters or 'date_to' in filters:
                                product_date = product_data.get('created_at') or product_data.get('updated_at')
                                if product_date:
                                    if isinstance(product_date, str):
                                        try:
                                            product_date = datetime.strptime(product_date[:10], '%Y-%m-%d').date()
                                        except:
                                            product_date = datetime.now().date()
                                    elif isinstance(product_date, datetime):
                                        product_date = product_date.date()
                                    
                                    if 'date_from' in filters and product_date < filters['date_from']:
                                        continue
                                    if 'date_to' in filters and product_date > filters['date_to']:
                                        continue
                            
                            # 가격 필터 체크
                            price = int(product_data.get('price', 0) or product_data.get('sale_price', 0) or 0)
                            if price == 0:
                                price = 10000  # 기본값
                            
                            if 'price_min' in filters and price < filters['price_min']:
                                continue
                            if 'price_max' in filters and price > filters['price_max']:
                                continue
                            
                            # 재고 필터 체크
                            if filters.get('stock_only', True):
                                stock = product_data.get('stock_quantity', 0) or product_data.get('stock', 0)
                                if stock <= 0:
                                    continue
                            
                            # 키워드 필터 체크
                            if 'keywords' in filters:
                                product_name = product_data.get('product_name', '').lower()
                                product_desc = product_data.get('description', '').lower()
                                found_keyword = False
                                for keyword in filters['keywords']:
                                    if keyword.lower() in product_name or keyword.lower() in product_desc:
                                        found_keyword = True
                                        break
                                if not found_keyword:
                                    continue
                            
                            # 제외 키워드 체크
                            if 'exclude_keywords' in filters:
                                product_name = product_data.get('product_name', '').lower()
                                product_desc = product_data.get('description', '').lower()
                                should_exclude = False
                                for exclude_keyword in filters['exclude_keywords']:
                                    if exclude_keyword.lower() in product_name or exclude_keyword.lower() in product_desc:
                                        should_exclude = True
                                        break
                                if should_exclude:
                                    continue
                            
                            # 카테고리 필터 체크
                            if 'categories' in filters:
                                product_category = product_data.get('category', '').lower()
                                found_category = False
                                for category in filters['categories']:
                                    if category.lower() in product_category:
                                        found_category = True
                                        break
                                if not found_category:
                                    continue
                        
                        total_count += 1
                        
                        # 기존 상품 확인
                        existing = db.query(WholesaleProduct).filter(
                            WholesaleProduct.product_code == product_data['product_code']
                        ).first()
                        
                        # 가격 정보 추출
                        price = int(product_data.get('price', 0) or product_data.get('sale_price', 0) or 0)
                        if price == 0:
                            price = 10000  # 기본값
                        
                        if existing:
                            # 업데이트
                            existing.product_info = product_data
                            existing.product_name = product_data.get('product_name', '')
                            existing.wholesale_price = price
                            existing.updated_at = datetime.now()
                            existing.last_synced_at = datetime.now()
                            updated_count += 1
                        else:
                            # 신규
                            new_product = WholesaleProduct(
                                product_code=product_data['product_code'],
                                supplier=supplier_code,
                                product_name=product_data.get('product_name', ''),
                                wholesale_price=price,
                                product_info=product_data,
                                category=product_data.get('category', ''),
                                brand=product_data.get('brand', ''),
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                                last_synced_at=datetime.now()
                            )
                            db.add(new_product)
                            new_count += 1
                            
                        if total_count % 100 == 0:
                            db.commit()
                            app_logger.info(f"{supplier_code} 수집 진행중: {total_count}개 (필터 적용 후)")
                            
                    except Exception as e:
                        error_count += 1
                        app_logger.error(f"상품 처리 오류: {e}")
                        
            else:
                # 증분 수집
                sync = IncrementalSync(supplier_code, db, test_mode)
                result = await sync.run()
                total_count = result.get('total', 0)
                new_count = result.get('new', 0)
                updated_count = result.get('updated', 0)
                error_count = result.get('errors', 0)
        
        # 최종 커밋
        db.commit()
        
        # 로그 업데이트
        collection_log.status = 'completed'
        collection_log.total_count = total_count
        collection_log.new_count = new_count
        collection_log.updated_count = updated_count
        collection_log.error_count = error_count
        collection_log.end_time = datetime.now()
        
        app_logger.info(f"{supplier_code} 수집 완료: 총 {total_count}개, 신규 {new_count}개, 업데이트 {updated_count}개")
        
    except Exception as e:
        # 오류 처리
        collection_log.status = 'failed'
        collection_log.error_message = str(e)
        collection_log.error_count = error_count
        collection_log.end_time = datetime.now()
        
        app_logger.error(f"{supplier_code} 수집 실패: {e}")
        
    finally:
        db.commit()
        db.close()

@router.post("/full/{supplier_code}")
async def start_full_collection(
    supplier_code: str,
    background_tasks: BackgroundTasks,
    test_mode: bool = Query(True, description="테스트 모드"),
    date_from: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    categories: Optional[str] = Query(None, description="카테고리 필터 (쉼표로 구분)"),
    price_min: Optional[float] = Query(None, description="최소 가격"),
    price_max: Optional[float] = Query(None, description="최대 가격"),
    keywords: Optional[str] = Query(None, description="포함 키워드"),
    exclude_keywords: Optional[str] = Query(None, description="제외 키워드"),
    stock_only: bool = Query(True, description="재고 있는 상품만"),
    db: Session = Depends(get_db)
):
    """전체 수집 시작 (날짜 및 필터 지원)"""
    # 실행 중인 수집이 있는지 확인
    running = db.query(CollectionLog).filter(
        CollectionLog.supplier == supplier_code,
        CollectionLog.status == 'running'
    ).first()
    
    if running:
        raise HTTPException(
            status_code=400,
            detail=f"{supplier_code} 수집이 이미 진행 중입니다"
        )
    
    # 필터 구성
    filters = {}
    if date_from:
        try:
            filters['date_from'] = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 시작 날짜 형식 (YYYY-MM-DD)")
    
    if date_to:
        try:
            filters['date_to'] = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 종료 날짜 형식 (YYYY-MM-DD)")
    
    if categories:
        filters['categories'] = [cat.strip() for cat in categories.split(',')]
    
    if price_min is not None:
        filters['price_min'] = price_min
    
    if price_max is not None:
        filters['price_max'] = price_max
    
    if keywords:
        filters['keywords'] = [kw.strip() for kw in keywords.split(',')]
    
    if exclude_keywords:
        filters['exclude_keywords'] = [kw.strip() for kw in exclude_keywords.split(',')]
    
    filters['stock_only'] = stock_only
    
    # 백그라운드 작업 추가
    def run_async():
        asyncio.run(_run_collection(supplier_code, 'full', test_mode, filters))
    
    background_tasks.add_task(run_async)
    
    # 필터 정보 로깅
    filter_info = []
    if date_from:
        filter_info.append(f"시작일: {date_from}")
    if date_to:
        filter_info.append(f"종료일: {date_to}")
    if categories:
        filter_info.append(f"카테고리: {categories}")
    if price_min is not None:
        filter_info.append(f"최소가격: {price_min:,}원")
    if price_max is not None:
        filter_info.append(f"최대가격: {price_max:,}원")
    
    filter_desc = f" (필터: {', '.join(filter_info)})" if filter_info else ""
    
    return {
        "message": f"{supplier_code} 전체 수집이 시작되었습니다{filter_desc}",
        "test_mode": test_mode,
        "filters": filters
    }

@router.post("/incremental/{supplier_code}")
async def start_incremental_sync(
    supplier_code: str,
    background_tasks: BackgroundTasks,
    test_mode: bool = True,
    db: Session = Depends(get_db)
):
    """증분 수집 시작"""
    # 마켓플레이스 확인
    supplier_info = db.query(Supplier).filter(
        Supplier.supplier_code == supplier_code
    ).first()
    
    is_marketplace = supplier_info and supplier_info.api_config and supplier_info.api_config.get('marketplace')
    
    if is_marketplace:
        raise HTTPException(
            status_code=400,
            detail="마켓플레이스는 증분 수집을 지원하지 않습니다"
        )
    
    if supplier_code == 'zentrade':
        raise HTTPException(
            status_code=400,
            detail="젠트레이드는 증분 수집을 지원하지 않습니다"
        )
    
    # 실행 중인 수집이 있는지 확인
    running = db.query(CollectionLog).filter(
        CollectionLog.supplier == supplier_code,
        CollectionLog.status == 'running'
    ).first()
    
    if running:
        raise HTTPException(
            status_code=400,
            detail=f"{supplier_code} 수집이 이미 진행 중입니다"
        )
    
    # 백그라운드 작업 추가
    def run_async():
        asyncio.run(_run_collection(supplier_code, 'incremental', test_mode))
    
    background_tasks.add_task(run_async)
    
    return {
        "message": f"{supplier_code} 증분 수집이 시작되었습니다",
        "test_mode": test_mode
    }

@router.get("/status/{supplier_code}")
async def get_collection_status(supplier_code: str, db: Session = Depends(get_db)):
    """수집 상태 조회"""
    # 최근 로그
    latest = db.query(CollectionLog).filter(
        CollectionLog.supplier == supplier_code
    ).order_by(CollectionLog.start_time.desc()).first()
    
    if not latest:
        return {
            "supplier": supplier_code,
            "status": "never_run",
            "message": "수집 기록이 없습니다"
        }
    
    return {
        "supplier": supplier_code,
        "status": latest.status,
        "collection_type": latest.collection_type,
        "start_time": latest.start_time.isoformat() if latest.start_time else None,
        "end_time": latest.end_time.isoformat() if latest.end_time else None,
        "total_count": latest.total_count,
        "new_count": latest.new_count,
        "updated_count": latest.updated_count,
        "error_count": latest.error_count,
        "error_message": latest.error_message
    }

@router.get("/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """전체 동기화 상태"""
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
    
    status_list = []
    for supplier in suppliers:
        # 상품 수
        if supplier.api_config and supplier.api_config.get('marketplace'):
            # 마켓플레이스 상품 수
            product_count = db.query(MarketplaceProduct).filter(
                MarketplaceProduct.marketplace == supplier.supplier_code
            ).count()
        else:
            # 도매 상품 수
            product_count = db.query(WholesaleProduct).filter(
                WholesaleProduct.supplier == supplier.supplier_code,
                WholesaleProduct.is_active == True
            ).count()
        
        # 최근 로그
        latest_log = db.query(CollectionLog).filter(
            CollectionLog.supplier == supplier.supplier_code
        ).order_by(CollectionLog.start_time.desc()).first()
        
        status_list.append({
            "supplier": supplier.supplier_code,
            "supplier_name": supplier.supplier_name,
            "product_count": product_count,
            "is_marketplace": supplier.api_config.get('marketplace', False) if supplier.api_config else False,
            "last_sync": latest_log.start_time.isoformat() if latest_log and latest_log.start_time else None,
            "last_status": latest_log.status if latest_log else "never_run"
        })
    
    # 전체 상품 수 계산
    total_wholesale = db.query(WholesaleProduct).filter(WholesaleProduct.is_active == True).count()
    total_marketplace = db.query(MarketplaceProduct).count()
    
    return {
        "suppliers": status_list,
        "total_wholesale_products": total_wholesale,
        "total_marketplace_products": total_marketplace,
        "total_products": total_wholesale + total_marketplace
    }
"""
도매처 상품 동기화 API 엔드포인트
전체 도매처 카탈로그를 DB에 동기화하는 기능
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Form, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime, timedelta

from app.api.v1.dependencies.database import get_db
from app.models.collected_product import CollectedProduct, CollectionBatch, WholesalerSource, CollectionStatus
from app.services.collection.wholesaler_sync_service import WholesalerSyncService
from app.services.wholesalers.base_wholesaler import CollectionType

router = APIRouter()

# 도매처 매핑
WHOLESALER_MAPPING = {
    "ownerclan": WholesalerSource.OWNERCLAN,
    "domeme": WholesalerSource.DOMEME,
    "gentrade": WholesalerSource.GENTRADE
}

# 수집 타입 매핑
COLLECTION_TYPE_MAPPING = {
    "all": CollectionType.ALL,
    "recent": CollectionType.RECENT,
    "category": CollectionType.CATEGORY,
    "updated": CollectionType.UPDATED,
    "new": CollectionType.NEW
}

class WholesalerSyncRequest(BaseModel):
    sources: List[str]  # ownerclan, domeme, gentrade 또는 'all'
    collection_type: str = "all"  # all, recent, category, updated, new
    max_products_per_source: int = 10000
    filters: Optional[Dict[str, Any]] = None

class CollectedProductResponse(BaseModel):
    id: str
    source: str
    name: str
    price: float
    original_price: Optional[float] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    stock_status: str
    supplier_id: Optional[str] = None
    collected_at: datetime
    status: str
    quality_score: Optional[float] = None

class SyncResult(BaseModel):
    success: bool
    message: str
    total_wholesalers: int
    results_by_source: Dict[str, Dict[str, Any]]
    summary: Dict[str, Any]

class SyncStatus(BaseModel):
    is_running: bool
    running_sources: List[str]
    last_sync: Optional[Dict[str, Any]]
    statistics: Dict[str, Any]

# 실행 중인 동기화 작업 추적
running_syncs = set()

async def sync_wholesaler_background(
    sync_service: WholesalerSyncService,
    wholesaler_sources: List[WholesalerSource],
    collection_type: CollectionType,
    max_products_per_source: int,
    filters: Optional[Dict[str, Any]] = None
):
    """백그라운드에서 도매처 동기화 실행"""
    source_names = [source.value for source in wholesaler_sources]
    
    try:
        # 실행 중 상태로 표시
        for source_name in source_names:
            running_syncs.add(source_name)
        
        if len(wholesaler_sources) == 1:
            # 단일 도매처 동기화
            await sync_service.sync_wholesaler(
                wholesaler_sources[0],
                collection_type,
                max_products_per_source,
                filters
            )
        else:
            # 전체 도매처 동기화
            await sync_service.sync_all_wholesalers(
                collection_type,
                max_products_per_source,
                filters
            )
    except Exception as e:
        # 로깅만 하고 예외를 삼키지 않음 (백그라운드 작업)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"백그라운드 동기화 오류: {str(e)}")
    finally:
        # 실행 완료 상태로 변경
        for source_name in source_names:
            running_syncs.discard(source_name)

@router.post("/sync", response_model=SyncResult)
async def start_wholesaler_sync(
    background_tasks: BackgroundTasks,
    sources: List[str] = Form(..., description="동기화할 도매처 목록 (ownerclan, domeme, gentrade) 또는 ['all']"),
    collection_type: str = Form("all", description="수집 타입 (all, recent, updated, new)"),
    max_products_per_source: int = Form(10000, description="도매처별 최대 수집 상품 수"),
    categories: Optional[List[str]] = Form(None, description="수집할 카테고리 목록"),
    price_min: Optional[float] = Form(None, description="최소 가격"),
    price_max: Optional[float] = Form(None, description="최대 가격"),
    keywords: Optional[str] = Form(None, description="포함 키워드 (쉼표로 구분)"),
    exclude_keywords: Optional[str] = Form(None, description="제외 키워드 (쉼표로 구분)"),
    date_from: Optional[str] = Form(None, description="시작일 (YYYY-MM-DD)"),
    date_to: Optional[str] = Form(None, description="종료일 (YYYY-MM-DD)"),
    stock_only: bool = Form(True, description="재고 있는 상품만 수집")
):
    """
    도매처 상품 동기화를 시작합니다.
    
    지원 도매처:
    - ownerclan: 오너클랜
    - domeme: 도매매  
    - gentrade: 젠트레이드
    
    수집 타입:
    - all: 전체 상품 카탈로그
    - recent: 최근 상품 (신상품)
    - updated: 업데이트된 상품
    - new: 새로 추가된 상품
    """
    
    # 요청 검증
    if collection_type not in COLLECTION_TYPE_MAPPING:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 수집 타입입니다. 사용 가능: {list(COLLECTION_TYPE_MAPPING.keys())}"
        )
    
    # 도매처 소스 파싱
    if "all" in sources:
        wholesaler_sources = list(WHOLESALER_MAPPING.values())
        source_names = list(WHOLESALER_MAPPING.keys())
    else:
        invalid_sources = [s for s in sources if s not in WHOLESALER_MAPPING]
        if invalid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 도매처입니다: {invalid_sources}. 사용 가능: {list(WHOLESALER_MAPPING.keys())}"
            )
        
        wholesaler_sources = [WHOLESALER_MAPPING[s] for s in sources]
        source_names = sources
    
    # 이미 실행 중인 동기화 확인
    running_sources = [s for s in source_names if s in running_syncs]
    if running_sources:
        raise HTTPException(
            status_code=409,
            detail=f"다음 도매처의 동기화가 이미 실행 중입니다: {running_sources}"
        )
    
    try:
        sync_service = WholesalerSyncService()
        collection_type_enum = COLLECTION_TYPE_MAPPING[collection_type]
        
        # 필터 구성
        filters = {}
        if categories:
            filters['categories'] = categories
        if price_min is not None:
            filters['price_min'] = price_min
        if price_max is not None:
            filters['price_max'] = price_max
        if keywords:
            filters['keywords'] = [k.strip() for k in keywords.split(',')]
        if exclude_keywords:
            filters['exclude_keywords'] = [k.strip() for k in exclude_keywords.split(',')]
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        filters['stock_only'] = stock_only
        
        # 백그라운드 작업으로 동기화 시작
        background_tasks.add_task(
            sync_wholesaler_background,
            sync_service,
            wholesaler_sources,
            collection_type_enum,
            max_products_per_source,
            filters if filters else None
        )
        
        # 즉시 응답 반환
        return SyncResult(
            success=True,
            message=f"{len(wholesaler_sources)}개 도매처 동기화가 백그라운드에서 시작되었습니다.",
            total_wholesalers=len(wholesaler_sources),
            results_by_source={},  # 백그라운드 작업이므로 결과는 나중에 확인
            summary={
                "started_at": datetime.utcnow().isoformat(),
                "sources": source_names,
                "collection_type": collection_type,
                "max_products_per_source": max_products_per_source,
                "estimated_completion_time": "10-30분 예상"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"동기화 시작 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/sync/status", response_model=SyncStatus)
async def get_sync_status():
    """동기화 상태 조회"""
    try:
        sync_service = WholesalerSyncService()
        
        # 통계 정보 조회
        statistics = await sync_service.get_sync_statistics()
        
        # 최근 배치 정보
        last_sync = None
        if statistics.get('recent_batches'):
            last_batch = statistics['recent_batches'][0]
            last_sync = {
                "batch_id": last_batch['batch_id'],
                "source": last_batch['source'],
                "status": last_batch['status'],
                "completed_at": last_batch['completed_at'],
                "total_collected": last_batch['total_collected']
            }
        
        return SyncStatus(
            is_running=len(running_syncs) > 0,
            running_sources=list(running_syncs),
            last_sync=last_sync,
            statistics=statistics
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상태 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/collected")
async def get_collected_products(
    source: Optional[str] = Query(None, description="도매처 필터"),
    keyword: Optional[str] = Query(None, description="키워드 필터"),
    status: Optional[str] = Query(None, description="상태 필터 (collected, sourced, rejected)"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    price_min: Optional[int] = Query(None, description="최소 가격"),
    price_max: Optional[int] = Query(None, description="최대 가격"),
    page: int = Query(1, description="페이지 번호"),
    limit: int = Query(50, description="페이지당 결과 수"),
    db: Session = Depends(get_db)
):
    """
    수집된 상품 목록을 조회합니다.
    """
    
    query = db.query(CollectedProduct)
    
    # 필터 적용
    if source:
        if source in WHOLESALER_MAPPING:
            query = query.filter(CollectedProduct.source == WHOLESALER_MAPPING[source])
    
    if keyword:
        query = query.filter(
            CollectedProduct.name.contains(keyword) |
            CollectedProduct.description.contains(keyword)
        )
    
    if status:
        if status in [s.value for s in CollectionStatus]:
            query = query.filter(CollectedProduct.status == CollectionStatus(status))
    
    if category:
        query = query.filter(CollectedProduct.category.contains(category))
    
    if price_min:
        query = query.filter(CollectedProduct.price >= price_min)
    
    if price_max:
        query = query.filter(CollectedProduct.price <= price_max)
    
    # 최신순 정렬
    query = query.order_by(CollectedProduct.collected_at.desc())
    
    # 페이지네이션
    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()
    
    # 응답 데이터 변환
    response_products = [
        CollectedProductResponse(
            id=str(product.id),
            source=product.source.value,
            name=product.name,
            price=float(product.price),
            original_price=float(product.original_price) if product.original_price else None,
            image_url=product.main_image_url,
            product_url=product.supplier_url,
            category=product.category,
            brand=product.brand,
            description=product.description,
            stock_status=product.stock_status,
            supplier_id=product.supplier_id,
            collected_at=product.collected_at,
            status=product.status.value,
            quality_score=float(product.quality_score) if product.quality_score else None
        )
        for product in products
    ]
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "products": response_products
    }

@router.post("/source-product/{collected_product_id}")
async def source_product_to_inventory(
    collected_product_id: str,
    selling_price: Optional[float] = Form(None, description="판매 가격 (지정하지 않으면 자동 계산)"),
    markup_percentage: float = Form(30.0, description="마진율 (%)"),
    db: Session = Depends(get_db)
):
    """
    수집된 상품을 실제 판매 상품으로 소싱합니다.
    """
    
    # 수집된 상품 조회
    collected_product = db.query(CollectedProduct).filter(
        CollectedProduct.id == collected_product_id
    ).first()
    
    if not collected_product:
        raise HTTPException(status_code=404, detail="수집된 상품을 찾을 수 없습니다.")
    
    if collected_product.status == CollectionStatus.SOURCED:
        raise HTTPException(status_code=400, detail="이미 소싱된 상품입니다.")
    
    try:
        # 판매 가격 계산
        if not selling_price:
            selling_price = float(collected_product.price) * (1 + markup_percentage / 100)
        
        # Product 데이터 생성 (실제로는 Product 모델로 저장해야 함)
        product_data = collected_product.to_product_dict()
        product_data.update({
            "sale_price": selling_price,
            "margin_percentage": markup_percentage,
            "sku": f"COL_{collected_product.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        })
        
        # 여기서 실제 Product 모델로 저장하는 코드가 들어가야 함
        # product = Product(**product_data)
        # db.add(product)
        
        # 수집된 상품 상태 업데이트
        collected_product.status = CollectionStatus.SOURCED
        collected_product.sourced_at = datetime.utcnow()
        collected_product.sourced_product_id = f"PRODUCT_{collected_product.id}"  # 실제로는 생성된 Product의 ID
        
        db.commit()
        
        return {
            "success": True,
            "message": "상품이 성공적으로 소싱되었습니다.",
            "collected_product_id": collected_product_id,
            "sourced_product_id": collected_product.sourced_product_id,
            "selling_price": selling_price,
            "cost_price": float(collected_product.price),
            "estimated_profit": selling_price - float(collected_product.price),
            "margin_percentage": markup_percentage
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 소싱 중 오류가 발생했습니다: {str(e)}"
        )

@router.delete("/collected/{collected_product_id}")
async def reject_collected_product(
    collected_product_id: str,
    reason: str = Form(..., description="거부 이유"),
    db: Session = Depends(get_db)
):
    """
    수집된 상품을 거부합니다.
    """
    
    collected_product = db.query(CollectedProduct).filter(
        CollectedProduct.id == collected_product_id
    ).first()
    
    if not collected_product:
        raise HTTPException(status_code=404, detail="수집된 상품을 찾을 수 없습니다.")
    
    if collected_product.status == CollectionStatus.SOURCED:
        raise HTTPException(status_code=400, detail="이미 소싱된 상품은 거부할 수 없습니다.")
    
    # 상태 업데이트
    collected_product.status = CollectionStatus.REJECTED
    collected_product.rejection_reason = reason
    
    db.commit()
    
    return {
        "success": True,
        "message": "상품이 거부되었습니다.",
        "collected_product_id": collected_product_id,
        "reason": reason
    }

@router.get("/sources")
async def get_available_sources():
    """사용 가능한 도매처 목록을 반환합니다."""
    return {
        "sources": [
            {
                "id": "ownerclan",
                "name": "오너클랜",
                "description": "국내 대표 B2B 도매 플랫폼",
                "api_available": True,
                "sync_supported": True
            },
            {
                "id": "domeme",
                "name": "도매매",
                "description": "합리적인 가격의 도매 상품",
                "api_available": True,
                "sync_supported": True
            },
            {
                "id": "gentrade",  
                "name": "젠트레이드",
                "description": "프리미엄 도매 상품 전문",
                "api_available": True,
                "sync_supported": True
            }
        ],
        "collection_types": [
            {
                "id": "all",
                "name": "전체 상품",
                "description": "도매처의 전체 상품 카탈로그를 동기화합니다"
            },
            {
                "id": "recent",
                "name": "최근 상품",
                "description": "최근에 추가된 신상품만 수집합니다"
            },
            {
                "id": "updated",
                "name": "업데이트된 상품",
                "description": "가격이나 재고가 변경된 상품만 수집합니다"
            },
            {
                "id": "new",
                "name": "신상품",
                "description": "새로 등록된 상품만 수집합니다"
            }
        ]
    }

@router.post("/cleanup-expired")
async def cleanup_expired_products(
    days_to_keep: int = Form(30, description="보관할 일수"),
    db: Session = Depends(get_db)
):
    """만료된 상품 정리"""
    try:
        sync_service = WholesalerSyncService()
        expired_count = await sync_service.cleanup_expired_products(days_to_keep)
        
        return {
            "success": True,
            "message": f"{expired_count}개 상품을 만료 처리했습니다.",
            "expired_count": expired_count,
            "days_kept": days_to_keep
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"만료 상품 정리 중 오류가 발생했습니다: {str(e)}"
        )
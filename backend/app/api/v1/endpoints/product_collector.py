"""
상품 수집 API 엔드포인트
도매처에서 상품을 수집하여 DB에 저장하는 기능
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Form, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime, timedelta
import random
import uuid
import logging

from app.api.v1.dependencies.database import get_db
from app.models.collected_product import CollectedProduct, CollectionBatch, WholesalerSource, CollectionStatus

logger = logging.getLogger(__name__)

router = APIRouter()

class ProductCollectionRequest(BaseModel):
    source: str  # ownerclan, domeme, gentrade
    keyword: str
    category: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    limit: int = 50
    page: int = 1

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
    stock_status: str = "available"
    supplier_id: Optional[str] = None
    collected_at: datetime
    status: str
    quality_score: Optional[float] = None

class CollectionResult(BaseModel):
    success: bool
    message: str
    batch_id: str
    total_collected: int
    total_saved: int
    products: List[CollectedProductResponse]
    search_info: Dict[str, Any]

# 도매처별 기본 데이터 (데모용)
DEMO_PRODUCTS = {
    "ownerclan": [
        {
            "name": "블루투스 무선이어폰 TWS-01",
            "price": 15000,
            "original_price": 25000,
            "category": "전자제품",
            "brand": "테크노",
            "description": "고품질 무선 블루투스 이어폰",
            "image_url": "https://example.com/product1.jpg",
            "supplier_id": "OC001"
        },
        {
            "name": "프리미엄 무선충전 이어폰",
            "price": 22000,
            "original_price": 35000,
            "category": "전자제품",
            "brand": "프로오디오",
            "description": "무선충전 지원 프리미엄 이어폰",
            "image_url": "https://example.com/product2.jpg",
            "supplier_id": "OC002"
        },
        {
            "name": "게이밍 무선이어폰 GX-100",
            "price": 18000,
            "original_price": 30000,
            "category": "전자제품",
            "brand": "게이머프로",
            "description": "저지연 게이밍 전용 무선이어폰",
            "image_url": "https://example.com/product3.jpg",
            "supplier_id": "OC003"
        }
    ],
    "domeme": [
        {
            "name": "도매매 스타일 무선이어폰",
            "price": 12000,
            "original_price": 20000,
            "category": "전자제품",
            "brand": "사운드킹",
            "description": "합리적인 가격의 무선이어폰",
            "image_url": "https://example.com/domeme1.jpg",
            "supplier_id": "DM001"
        },
        {
            "name": "휴대용 블루투스 헤드셋",
            "price": 16000,
            "original_price": 28000,
            "category": "전자제품",
            "brand": "모바일프로",
            "description": "장시간 사용 가능한 헤드셋",
            "image_url": "https://example.com/domeme2.jpg",
            "supplier_id": "DM002"
        }
    ],
    "gentrade": [
        {
            "name": "젠트레이드 프리미엄 이어폰",
            "price": 25000,
            "original_price": 40000,
            "category": "전자제품",
            "brand": "젠오디오",
            "description": "프리미엄 음질의 무선이어폰",
            "image_url": "https://example.com/gentrade1.jpg",
            "supplier_id": "GT001"
        }
    ]
}

async def simulate_collection_and_save(
    source: str, 
    keyword: str, 
    limit: int, 
    batch_id: str,
    db: Session,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None
) -> List[CollectedProduct]:
    """상품 수집 시뮬레이션 후 DB에 저장"""
    await asyncio.sleep(1)  # 실제 수집 시간 시뮬레이션
    
    base_products = DEMO_PRODUCTS.get(source, [])
    
    # 키워드가 포함된 상품 필터링
    filtered_products = []
    saved_products = []
    
    for product in base_products:
        if keyword.lower() in product["name"].lower() or keyword.lower() in product["description"].lower():
            # 가격에 약간의 랜덤성 추가 (시장 변동 시뮬레이션)
            price_variation = random.randint(-1000, 2000)
            final_price = max(1000, product["price"] + price_variation)
            
            # 가격 필터링
            if price_min and final_price < price_min:
                continue
            if price_max and final_price > price_max:
                continue
                
            # CollectedProduct 인스턴스 생성
            collected_product = CollectedProduct(
                source=WholesalerSource(source),
                collection_keyword=keyword,
                collection_batch_id=batch_id,
                supplier_id=product["supplier_id"],
                supplier_url=f"https://{source}.com/product/{product['supplier_id']}",
                name=product["name"],
                description=product["description"],
                brand=product["brand"],
                category=product["category"],
                price=final_price,
                original_price=product.get("original_price"),
                main_image_url=product["image_url"],
                stock_status="available",
                quality_score=random.uniform(6.0, 9.5),  # 임의의 품질 점수
                popularity_score=random.uniform(1.0, 10.0),  # 임의의 인기도 점수
                expires_at=datetime.utcnow() + timedelta(days=7),  # 7일 후 만료
                status=CollectionStatus.COLLECTED
            )
            
            # DB에 저장
            db.add(collected_product)
            saved_products.append(collected_product)
            
            if len(saved_products) >= limit:
                break
    
    # 변경사항 커밋
    db.commit()
    
    # 저장된 객체들을 새로고침하여 ID 등을 가져옴
    for product in saved_products:
        db.refresh(product)
    
    return saved_products

@router.post("/collect", response_model=CollectionResult)
async def collect_products(
    background_tasks: BackgroundTasks,
    source: str = Form(..., description="수집할 도매처 (ownerclan, domeme, gentrade)"),
    keyword: str = Form(..., description="검색할 키워드"),
    category: Optional[str] = Form(None, description="상품 카테고리"),
    price_min: Optional[int] = Form(None, description="최소 가격"),
    price_max: Optional[int] = Form(None, description="최대 가격"),
    limit: int = Form(50, description="수집할 상품 수"),
    page: int = Form(1, description="페이지 번호"),
    db: Session = Depends(get_db)
):
    """
    도매처에서 상품을 수집합니다.
    
    지원 도매처:
    - ownerclan: 오너클랜
    - domeme: 도매매  
    - gentrade: 젠트레이드
    """
    
    if source not in ["ownerclan", "domeme", "gentrade"]:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 도매처입니다. (ownerclan, domeme, gentrade 중 선택)"
        )
    
    try:
        # 배치 ID 생성
        batch_id = f"batch_{source}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 배치 정보 생성
        collection_batch = CollectionBatch(
            batch_id=batch_id,
            source=WholesalerSource(source),
            keyword=keyword,
            max_products=limit,
            filters={
                "category": category,
                "price_min": price_min,
                "price_max": price_max
            },
            status="running",
            started_at=datetime.utcnow()
        )
        
        db.add(collection_batch)
        db.commit()
        
        # 상품 수집 및 DB 저장
        collected_products = await simulate_collection_and_save(
            source, keyword, limit, batch_id, db, price_min, price_max
        )
        
        # 배치 상태 업데이트
        collection_batch.status = "completed"
        collection_batch.completed_at = datetime.utcnow()
        collection_batch.total_collected = len(collected_products)
        collection_batch.successful_collections = len(collected_products)
        collection_batch.failed_collections = 0
        
        db.commit()
        
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
            for product in collected_products
        ]
        
        return CollectionResult(
            success=True,
            message=f"{source}에서 '{keyword}' 키워드로 {len(collected_products)}개 상품을 수집하여 DB에 저장했습니다.",
            batch_id=batch_id,
            total_collected=len(collected_products),
            total_saved=len(collected_products),
            products=response_products,
            search_info={
                "source": source,
                "keyword": keyword,
                "category": category,
                "price_range": {
                    "min": price_min,
                    "max": price_max
                },
                "page": page,
                "limit": limit,
                "batch_id": batch_id,
                "collected_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        # 배치 상태를 실패로 업데이트
        try:
            collection_batch.status = "failed"
            collection_batch.error_message = str(e)
            collection_batch.completed_at = datetime.utcnow()
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update collection batch status: {db_error}")
            db.rollback()
            
        raise HTTPException(
            status_code=500,
            detail=f"상품 수집 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/sources")
async def get_available_sources():
    """사용 가능한 도매처 목록을 반환합니다."""
    return {
        "sources": [
            {
                "id": "ownerclan",
                "name": "오너클랜",
                "description": "국내 대표 B2B 도매 플랫폼",
                "categories": ["전자제품", "패션", "생활용품", "스포츠"]
            },
            {
                "id": "domeme",
                "name": "도매매",
                "description": "합리적인 가격의 도매 상품",
                "categories": ["전자제품", "생활용품", "건강식품"]
            },
            {
                "id": "gentrade",  
                "name": "젠트레이드",
                "description": "프리미엄 도매 상품 전문",
                "categories": ["전자제품", "패션", "뷰티"]
            }
        ]
    }

@router.get("/search-suggestions")
async def get_search_suggestions(q: str = Query(..., description="검색어")):
    """검색어 자동완성 제안을 반환합니다."""
    
    # 인기 검색어 데이터
    suggestions = [
        "무선이어폰", "블루투스 헤드폰", "스마트워치", "휴대폰 케이스",
        "무선충전기", "보조배터리", "USB 케이블", "차량용품",
        "노트북 가방", "마우스", "키보드", "모니터"
    ]
    
    # 입력한 글자와 유사한 검색어 필터링
    filtered_suggestions = [
        suggestion for suggestion in suggestions
        if q.lower() in suggestion.lower()
    ]
    
    return {
        "suggestions": filtered_suggestions[:10],  # 최대 10개
        "popular_keywords": ["무선이어폰", "스마트워치", "휴대폰케이스", "보조배터리", "블루투스헤드폰"]
    }

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
        query = query.filter(CollectedProduct.source == WholesalerSource(source))
    
    if keyword:
        query = query.filter(
            CollectedProduct.name.contains(keyword) |
            CollectedProduct.description.contains(keyword)
        )
    
    if status:
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
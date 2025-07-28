"""
Product management endpoints with V2 patterns.
V2 패턴이 적용된 상품 관리 엔드포인트.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.validators import ProductCreateValidator, ProductUpdateValidator
from app.core.logging_utils import get_logger
from app.api.v1.dependencies.auth import get_current_user
from app.services.database.database import get_async_db
from app.services.product.product_service_v2 import ProductServiceV2
from app.services.ai.ai_service_v2 import AIServiceV2
from app.services.cache.cache_service import get_cache_service
from app.schemas.product import ProductResponse, ProductListResponse
from app.models.user import User


router = APIRouter()
logger = get_logger("ProductAPIV2")


# 의존성 주입
async def get_product_service(
    db: AsyncSession = Depends(get_async_db),
    cache_service = Depends(get_cache_service)
) -> ProductServiceV2:
    """상품 서비스 의존성"""
    return ProductServiceV2(db, cache_service)


async def get_ai_service(
    cache_service = Depends(get_cache_service)
) -> AIServiceV2:
    """AI 서비스 의존성"""
    from app.core.config import settings
    from app.services.ai.ai_service_v2 import GeminiProvider, OllamaProvider
    
    providers = []
    if settings.GEMINI_API_KEY:
        providers.append(GeminiProvider(settings.GEMINI_API_KEY))
    if settings.OLLAMA_BASE_URL:
        providers.append(OllamaProvider(settings.OLLAMA_BASE_URL))
        
    return AIServiceV2(providers, cache_service)


@router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("created_at", enum=["created_at", "price", "name"]),
    order: str = Query("desc", enum=["asc", "desc"]),
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    상품 목록 조회 (V2).
    
    - 페이지네이션 지원
    - 필터링 및 정렬
    - 캐싱 적용
    """
    logger.info(
        "Fetching products",
        page=page,
        per_page=per_page,
        category=category,
        filters={
            "min_price": min_price,
            "max_price": max_price,
            "sort_by": sort_by,
            "order": order
        }
    )
    
    try:
        # 필터 구성
        filters = {}
        if category:
            filters["category"] = category
        if min_price is not None:
            filters["min_price"] = Decimal(str(min_price))
        if max_price is not None:
            filters["max_price"] = Decimal(str(max_price))
            
        # 서비스 호출
        result = await service.search_products(
            page=page,
            per_page=per_page,
            filters=filters,
            sort_by=sort_by,
            order=order
        )
        
        return ProductListResponse(
            results=result["items"],
            total=result["total"],
            page=page,
            per_page=per_page,
            pages=result["pages"]
        )
        
    except Exception as e:
        logger.error("Failed to fetch products", error=str(e))
        raise


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    상품 검색 (V2).
    
    - 전문 검색 지원
    - 자동 완성 제안
    - 검색 결과 캐싱
    """
    logger.info("Searching products", query=q, page=page)
    
    try:
        result = await service.search_products(
            query=q,
            page=page,
            per_page=per_page
        )
        
        return {
            "query": q,
            "results": result["items"],
            "total": result["total"],
            "suggestions": result.get("suggestions", [])
        }
        
    except Exception as e:
        logger.error("Search failed", query=q, error=str(e))
        raise


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    상품 상세 조회 (V2).
    
    - 캐시 우선 조회
    - 조회수 증가 (백그라운드)
    - 연관 상품 포함
    """
    logger.info("Fetching product detail", product_id=product_id)
    
    try:
        product = await service.get_product_detail(
            product_id,
            use_cache=True
        )
        
        if not product:
            raise NotFoundError("Product", product_id)
            
        return ProductResponse.from_orm(product)
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to fetch product", product_id=product_id, error=str(e))
        raise


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreateValidator,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: ProductServiceV2 = Depends(get_product_service),
    ai_service: AIServiceV2 = Depends(get_ai_service)
):
    """
    상품 생성 (V2).
    
    - 입력 검증
    - AI 기반 카테고리 분류
    - SEO 최적화
    - 백그라운드 처리
    """
    logger.info("Creating product", user_id=current_user.id, product_name=product_data.name)
    
    try:
        # AI 카테고리 추천
        if not product_data.category:
            category = await ai_service.classify_product(product_data.dict())
            product_data.category = category
            
        # 상품 생성
        product = await service.create_product(product_data.dict())
        
        # 백그라운드 작업
        background_tasks.add_task(
            process_product_after_creation,
            product.id,
            service,
            ai_service
        )
        
        return ProductResponse.from_orm(product)
        
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error("Failed to create product", error=str(e))
        raise


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdateValidator,
    current_user: User = Depends(get_current_user),
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    상품 수정 (V2).
    
    - 부분 업데이트 지원
    - 변경 이력 추적
    - 캐시 무효화
    """
    logger.info(
        "Updating product",
        product_id=product_id,
        user_id=current_user.id,
        changes=product_data.dict(exclude_unset=True)
    )
    
    try:
        # 권한 확인
        existing = await service.get_product_detail(product_id, use_cache=False)
        if not existing:
            raise NotFoundError("Product", product_id)
            
        if existing.user_id != current_user.id and not current_user.is_admin:
            raise ValidationError("권한이 없습니다.")
            
        # 업데이트
        product = await service.update_product(
            product_id,
            product_data.dict(exclude_unset=True)
        )
        
        return ProductResponse.from_orm(product)
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to update product", product_id=product_id, error=str(e))
        raise


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    상품 삭제 (V2).
    
    - Soft delete
    - 관련 데이터 정리
    - 캐시 무효화
    """
    logger.info("Deleting product", product_id=product_id, user_id=current_user.id)
    
    try:
        # 권한 확인
        existing = await service.get_product_detail(product_id, use_cache=False)
        if not existing:
            raise NotFoundError("Product", product_id)
            
        if existing.user_id != current_user.id and not current_user.is_admin:
            raise ValidationError("권한이 없습니다.")
            
        # 삭제
        await service.delete_product(product_id)
        
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to delete product", product_id=product_id, error=str(e))
        raise


@router.post("/{product_id}/analyze")
async def analyze_product(
    product_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: ProductServiceV2 = Depends(get_product_service),
    ai_service: AIServiceV2 = Depends(get_ai_service)
):
    """
    상품 AI 분석 (V2).
    
    - 가격 최적화 분석
    - 경쟁 상품 분석
    - 수요 예측
    - SEO 개선 제안
    """
    logger.info("Analyzing product", product_id=product_id, user_id=current_user.id)
    
    try:
        # 상품 조회
        product = await service.get_product_detail(product_id)
        if not product:
            raise NotFoundError("Product", product_id)
            
        # 권한 확인
        if product.user_id != current_user.id and not current_user.is_admin:
            raise ValidationError("권한이 없습니다.")
            
        # AI 분석 (백그라운드)
        analysis_id = f"analysis_{product_id}_{datetime.utcnow().timestamp()}"
        
        background_tasks.add_task(
            run_product_analysis,
            product_id,
            analysis_id,
            service,
            ai_service
        )
        
        return {
            "message": "분석이 시작되었습니다.",
            "analysis_id": analysis_id,
            "status": "processing",
            "estimated_time": "2-3분"
        }
        
    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to start analysis", product_id=product_id, error=str(e))
        raise


@router.get("/{product_id}/analysis/{analysis_id}")
async def get_analysis_result(
    product_id: str,
    analysis_id: str,
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    분석 결과 조회 (V2).
    
    - 분석 상태 확인
    - 결과 캐싱
    - 실시간 업데이트
    """
    try:
        # 캐시에서 결과 조회
        cache_key = f"analysis:{analysis_id}"
        result = await service.cache_service.get(cache_key)
        
        if not result:
            return {
                "analysis_id": analysis_id,
                "status": "processing",
                "message": "분석이 진행 중입니다."
            }
            
        return result
        
    except Exception as e:
        logger.error("Failed to get analysis result", analysis_id=analysis_id, error=str(e))
        raise


@router.post("/{product_id}/stock/update")
async def update_stock(
    product_id: str,
    quantity_change: int,
    reason: str = Query(..., description="재고 변경 사유"),
    current_user: User = Depends(get_current_user),
    service: ProductServiceV2 = Depends(get_product_service)
):
    """
    재고 업데이트 (V2).
    
    - 트랜잭션 보장
    - 재고 이력 추적
    - 실시간 알림
    """
    logger.info(
        "Updating stock",
        product_id=product_id,
        quantity_change=quantity_change,
        reason=reason,
        user_id=current_user.id
    )
    
    try:
        result = await service.update_stock(
            product_id,
            quantity_change,
            reason=reason,
            user_id=current_user.id
        )
        
        return {
            "product_id": product_id,
            "previous_stock": result["previous_stock"],
            "new_stock": result["new_stock"],
            "change": quantity_change,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to update stock", product_id=product_id, error=str(e))
        raise


# 백그라운드 작업 함수들
async def process_product_after_creation(
    product_id: str,
    service: ProductServiceV2,
    ai_service: AIServiceV2
):
    """상품 생성 후 백그라운드 처리"""
    try:
        # SEO 최적화
        product = await service.get_product_detail(product_id)
        if product:
            seo_data = await ai_service.generate_seo_content(product.dict())
            await service.update_product(product_id, seo_data)
            
        # 이미지 최적화
        # TODO: 이미지 처리 로직
        
        logger.info("Background processing completed", product_id=product_id)
        
    except Exception as e:
        logger.error("Background processing failed", product_id=product_id, error=str(e))


async def run_product_analysis(
    product_id: str,
    analysis_id: str,
    service: ProductServiceV2,
    ai_service: AIServiceV2
):
    """상품 분석 백그라운드 작업"""
    try:
        # 상품 데이터 조회
        product = await service.get_product_detail(product_id)
        if not product:
            return
            
        # AI 분석 실행
        analysis_result = await ai_service.analyze_product(product.dict())
        
        # 결과 저장
        result = {
            "analysis_id": analysis_id,
            "product_id": product_id,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "results": analysis_result
        }
        
        # 캐시에 저장 (24시간)
        cache_key = f"analysis:{analysis_id}"
        await service.cache_service.set(cache_key, result, ttl=86400)
        
        logger.info("Product analysis completed", analysis_id=analysis_id)
        
    except Exception as e:
        logger.error("Product analysis failed", analysis_id=analysis_id, error=str(e))
        
        # 실패 상태 저장
        error_result = {
            "analysis_id": analysis_id,
            "product_id": product_id,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        cache_key = f"analysis:{analysis_id}"
        await service.cache_service.set(cache_key, error_result, ttl=3600)
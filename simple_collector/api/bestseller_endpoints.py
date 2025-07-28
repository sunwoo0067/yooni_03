"""
베스트셀러 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from database.connection import get_db, engine
from collectors.bestseller_collector import BestsellerData, CoupangBestsellerCollector, NaverShoppingCollector
from utils.logger import app_logger

router = APIRouter(prefix="/bestseller", tags=["bestseller"])

# 테이블 생성
BestsellerData.metadata.create_all(bind=engine)


@router.post("/collect/{marketplace}")
async def collect_bestsellers(
    marketplace: str,
    background_tasks: BackgroundTasks,
    category: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """베스트셀러 수집 시작"""
    
    if marketplace not in ["coupang", "naver", "all"]:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 마켓플레이스입니다. coupang, naver, all 중 선택하세요."
        )
    
    async def _collect():
        """백그라운드에서 수집 실행"""
        try:
            collected_data = []
            
            if marketplace in ["coupang", "all"]:
                # 쿠팡 수집
                try:
                    collector = CoupangBestsellerCollector()
                    products = await collector.get_bestsellers(
                        category_id=category,
                        limit=limit
                    )
                    collected_data.extend(products)
                    app_logger.info(f"쿠팡 베스트셀러 {len(products)}개 수집 완료")
                except Exception as e:
                    app_logger.error(f"쿠팡 수집 오류: {e}")
            
            if marketplace in ["naver", "all"]:
                # 네이버 수집
                try:
                    collector = NaverShoppingCollector()
                    products = await collector.get_bestsellers(
                        category=category,
                        limit=limit
                    )
                    collected_data.extend(products)
                    app_logger.info(f"네이버 베스트셀러 {len(products)}개 수집 완료")
                except Exception as e:
                    app_logger.error(f"네이버 수집 오류: {e}")
            
            # DB 저장
            db_session = Session(bind=engine)
            try:
                for product in collected_data:
                    bestseller = BestsellerData(
                        marketplace=product['marketplace'],
                        rank=product['rank'],
                        category=product.get('category'),
                        category_id=product.get('category_id'),
                        product_id=product['product_id'],
                        product_name=product['product_name'],
                        brand=product.get('brand'),
                        price=product['price'],
                        review_count=product['review_count'],
                        rating=product['rating'],
                        product_data=product
                    )
                    db_session.add(bestseller)
                
                db_session.commit()
                app_logger.info(f"베스트셀러 데이터 {len(collected_data)}개 저장 완료")
                
            except Exception as e:
                db_session.rollback()
                app_logger.error(f"DB 저장 오류: {e}")
            finally:
                db_session.close()
                
        except Exception as e:
            app_logger.error(f"베스트셀러 수집 오류: {e}")
    
    background_tasks.add_task(_collect)
    
    return {
        "message": f"{marketplace} 베스트셀러 수집이 시작되었습니다",
        "category": category,
        "limit": limit
    }


@router.get("/list")
async def get_bestsellers(
    marketplace: Optional[str] = None,
    category: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """베스트셀러 목록 조회"""
    
    query = db.query(BestsellerData)
    
    # 마켓플레이스 필터
    if marketplace:
        query = query.filter(BestsellerData.marketplace == marketplace)
    
    # 카테고리 필터
    if category:
        query = query.filter(BestsellerData.category == category)
    
    # 날짜 필터 (최근 N일)
    since_date = datetime.now() - timedelta(days=days)
    query = query.filter(BestsellerData.collected_at >= since_date)
    
    # 최신 데이터 우선, 순위별 정렬
    query = query.order_by(
        desc(BestsellerData.collected_at),
        BestsellerData.rank
    )
    
    bestsellers = query.limit(limit).all()
    
    return {
        "total": len(bestsellers),
        "marketplace": marketplace,
        "category": category,
        "days": days,
        "bestsellers": [
            {
                "id": item.id,
                "marketplace": item.marketplace,
                "rank": item.rank,
                "category": item.category,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "brand": item.brand,
                "price": item.price,
                "review_count": item.review_count,
                "rating": item.rating,
                "collected_at": item.collected_at.isoformat()
            }
            for item in bestsellers
        ]
    }


@router.get("/trends")
async def get_bestseller_trends(
    marketplace: Optional[str] = None,
    product_id: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """베스트셀러 트렌드 분석"""
    
    query = db.query(
        BestsellerData.product_id,
        BestsellerData.product_name,
        BestsellerData.marketplace,
        func.avg(BestsellerData.rank).label('avg_rank'),
        func.min(BestsellerData.rank).label('best_rank'),
        func.max(BestsellerData.rank).label('worst_rank'),
        func.count().label('appearance_count')
    )
    
    # 마켓플레이스 필터
    if marketplace:
        query = query.filter(BestsellerData.marketplace == marketplace)
    
    # 특정 상품 필터
    if product_id:
        query = query.filter(BestsellerData.product_id == product_id)
    
    # 날짜 필터
    since_date = datetime.now() - timedelta(days=days)
    query = query.filter(BestsellerData.collected_at >= since_date)
    
    # 그룹화
    query = query.group_by(
        BestsellerData.product_id,
        BestsellerData.product_name,
        BestsellerData.marketplace
    )
    
    # 평균 순위로 정렬
    query = query.order_by('avg_rank')
    
    trends = query.limit(100).all()
    
    return {
        "marketplace": marketplace,
        "days": days,
        "total": len(trends),
        "trends": [
            {
                "product_id": trend.product_id,
                "product_name": trend.product_name,
                "marketplace": trend.marketplace,
                "avg_rank": round(trend.avg_rank, 1),
                "best_rank": trend.best_rank,
                "worst_rank": trend.worst_rank,
                "appearance_count": trend.appearance_count,
                "stability_score": round(100 - (trend.worst_rank - trend.best_rank), 1)
            }
            for trend in trends
        ]
    }


@router.get("/categories")
async def get_categories(
    marketplace: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """수집된 카테고리 목록"""
    
    query = db.query(
        BestsellerData.category,
        BestsellerData.category_id,
        func.count().label('product_count')
    ).filter(
        BestsellerData.category.isnot(None)
    )
    
    if marketplace:
        query = query.filter(BestsellerData.marketplace == marketplace)
    
    query = query.group_by(
        BestsellerData.category,
        BestsellerData.category_id
    ).order_by(desc('product_count'))
    
    categories = query.all()
    
    return {
        "marketplace": marketplace,
        "total": len(categories),
        "categories": [
            {
                "category": cat.category,
                "category_id": cat.category_id,
                "product_count": cat.product_count
            }
            for cat in categories
        ]
    }
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import asyncio
import os
import shutil
from pathlib import Path
import pandas as pd

from config.settings import settings
from database.connection import get_db, create_tables
from database.models import Supplier, CollectionLog, init_suppliers, ExcelUpload
from database.models_v2 import WholesaleProduct, MarketplaceProduct
from collectors.zentrade_collector import ZentradeCollector
from collectors.ownerclan_collector import OwnerClanCollector
from utils.logger import app_logger
from api.excel_endpoints import router as excel_router
from api.supplier_settings import router as settings_router
from api.marketplace_settings import router as marketplace_router

# FastAPI 앱 생성
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 개발용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 추가
app.include_router(excel_router)
app.include_router(settings_router)
app.include_router(marketplace_router)

# collection_endpoints 라우터 추가
from api.collection_endpoints import router as collection_router
app.include_router(collection_router)

# bestseller_endpoints 라우터 추가
from api.bestseller_endpoints import router as bestseller_router
app.include_router(bestseller_router)

# image_endpoints 라우터 추가
from api.image_endpoints import router as image_router
app.include_router(image_router)

# ai_sourcing_endpoints 라우터 추가
from api.ai_sourcing_endpoints import router as ai_sourcing_router
app.include_router(ai_sourcing_router)

# scheduler_endpoints 라우터 추가
from api.scheduler_endpoints import router as scheduler_router
app.include_router(scheduler_router)

# 정적 파일 서빙 설정
static_path = Path("static")
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    app_logger.info("Simple Product Collector 시작")
    
    # 데이터베이스 테이블 생성
    create_tables()
    app_logger.info("데이터베이스 테이블 생성 완료")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Simple Product Collector API",
        "version": settings.API_VERSION,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/suppliers")
async def get_suppliers(db: Session = Depends(get_db)):
    """공급사 목록 조회"""
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
    return [
        {
            "supplier_code": s.supplier_code,
            "supplier_name": s.supplier_name,
            "is_active": s.is_active,
            "api_config": s.api_config
        }
        for s in suppliers
    ]

@app.post("/suppliers/init")
async def init_suppliers_endpoint(db: Session = Depends(get_db)):
    """기본 공급사 데이터 초기화"""
    try:
        init_suppliers(db)
        return {"message": "공급사 데이터 초기화 완료"}
    except Exception as e:
        app_logger.error(f"공급사 초기화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products")
async def get_products(
    supplier: str = None,
    product_type: str = "wholesale",  # wholesale or marketplace
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """상품 목록 조회"""
    if product_type == "wholesale":
        # 도매 상품 조회
        query = db.query(WholesaleProduct).filter(WholesaleProduct.is_active == True)
        
        if supplier:
            query = query.filter(WholesaleProduct.supplier == supplier)
            
        products = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return {
            "product_type": "wholesale",
            "products": [
                {
                    "product_code": p.product_code,
                    "supplier": p.supplier,
                    "product_name": p.product_name,
                    "wholesale_price": p.wholesale_price,
                    "product_info": p.product_info,
                    "category": p.category,
                    "brand": p.brand,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in products
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    else:
        # 마켓플레이스 상품 조회
        query = db.query(MarketplaceProduct)
        
        if supplier:  # 여기서는 marketplace로 필터링
            query = query.filter(MarketplaceProduct.marketplace == supplier)
            
        products = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return {
            "product_type": "marketplace",
            "products": [
                {
                    "marketplace_product_id": p.marketplace_product_id,
                    "marketplace": p.marketplace,
                    "product_name": p.product_name,
                    "selling_price": p.selling_price,
                    "wholesale_product_code": p.wholesale_product_code,
                    "status": p.status,
                    "stock_quantity": p.stock_quantity,
                    "marketplace_url": p.marketplace_url,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in products
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

@app.get("/products/{product_code}")
async def get_product(product_code: str, db: Session = Depends(get_db)):
    """특정 상품 조회"""
    product = db.query(Product).filter(Product.product_code == product_code).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
    return {
        "product_code": product.product_code,
        "supplier": product.supplier,
        "product_info": product.product_info,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat()
    }

@app.get("/collection-logs")
async def get_collection_logs(
    supplier: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """수집 로그 조회"""
    query = db.query(CollectionLog).order_by(CollectionLog.start_time.desc())
    
    if supplier:
        query = query.filter(CollectionLog.supplier == supplier)
        
    logs = query.limit(limit).all()
    
    return [
        {
            "id": log.id,
            "supplier": log.supplier,
            "collection_type": log.collection_type,
            "status": log.status,
            "total_count": log.total_count,
            "new_count": log.new_count,
            "updated_count": log.updated_count,
            "error_count": log.error_count,
            "error_message": log.error_message,
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None
        }
        for log in logs
    ]

# 테스트용 수집 엔드포인트들
@app.post("/test/zentrade")
async def test_zentrade_collection(background_tasks: BackgroundTasks):
    """젠트레이드 수집 테스트 (백그라운드 실행)"""
    
    def run_zentrade_test():
        asyncio.run(_test_zentrade_collection())
    
    background_tasks.add_task(run_zentrade_test)
    
    return {
        "message": "젠트레이드 수집 테스트가 백그라운드에서 시작되었습니다",
        "check_logs": "/collection-logs?supplier=zentrade"
    }

async def _test_zentrade_collection():
    """젠트레이드 수집 테스트 실행"""
    try:
        app_logger.info("젠트레이드 수집 테스트 시작")
        
        # 테스트용 인증 정보 (실제로는 환경변수나 DB에서 가져와야 함)
        credentials = {
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        }
        
        collector = ZentradeCollector(credentials)
        
        # 인증 테스트
        auth_result = await collector.authenticate()
        app_logger.info(f"젠트레이드 인증 결과: {auth_result}")
        
        if not auth_result:
            app_logger.error("젠트레이드 인증 실패 - 실제 API 키가 필요합니다")
            return
            
        # 전체 수집 테스트 (실제로는 너무 오래 걸리므로 스킵)
        app_logger.info("젠트레이드 전체 수집은 실제 API 키가 있을 때만 가능합니다")
        
    except Exception as e:
        app_logger.error(f"젠트레이드 테스트 중 오류: {e}")

@app.post("/test/ownerclan")
async def test_ownerclan_collection(background_tasks: BackgroundTasks):
    """오너클랜 수집 테스트 (백그라운드 실행)"""
    
    def run_ownerclan_test():
        asyncio.run(_test_ownerclan_collection())
    
    background_tasks.add_task(run_ownerclan_test)
    
    return {
        "message": "오너클랜 수집 테스트가 백그라운드에서 시작되었습니다",
        "check_logs": "/collection-logs?supplier=ownerclan"
    }

async def _test_ownerclan_collection():
    """오너클랜 수집 테스트 실행"""
    try:
        app_logger.info("오너클랜 수집 테스트 시작")
        
        # 테스트용 인증 정보
        credentials = {
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api-sandbox.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth-sandbox.ownerclan.com/auth'
        }
        
        collector = OwnerClanCollector(credentials)
        
        # 인증 테스트
        auth_result = await collector.authenticate()
        app_logger.info(f"오너클랜 인증 결과: {auth_result}")
        
        if not auth_result:
            app_logger.error("오너클랜 인증 실패 - 실제 계정 정보가 필요합니다")
            return
            
        app_logger.info("오너클랜 2단계 수집은 실제 계정 정보가 있을 때만 가능합니다")
        
    except Exception as e:
        app_logger.error(f"오너클랜 테스트 중 오류: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
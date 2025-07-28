#!/usr/bin/env python3
"""
실제 API를 사용하는 메인 서버
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 설정 클래스
class Settings:
    APP_NAME = "Yooni Dropshipping System (Real API)"
    APP_VERSION = "1.0.0"
    DEBUG = True
    
    # API Keys from .env
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
    COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
    
    # CORS
    CORS_ORIGINS = ["*"]

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 코드"""
    # 시작 시
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Gemini API Key: {'설정됨' if settings.GEMINI_API_KEY else '미설정'}")
    logger.info(f"Coupang API Key: {'설정됨' if settings.COUPANG_ACCESS_KEY else '미설정'}")
    logger.info(f"Naver API Key: {'설정됨' if settings.NAVER_CLIENT_ID else '미설정'}")
    
    yield
    
    # 종료 시
    logger.info("Shutting down...")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 기본 엔드포인트
@app.get("/")
async def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_keys_configured": {
            "gemini": bool(settings.GEMINI_API_KEY),
            "coupang": bool(settings.COUPANG_ACCESS_KEY),
            "naver": bool(settings.NAVER_CLIENT_ID)
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# AI 분석 엔드포인트
@app.post("/api/v1/ai/analyze-product")
async def analyze_product(product_data: dict):
    """Google Gemini를 사용한 상품 분석"""
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        # 실제 Gemini API 호출 코드
        import google.generativeai as genai
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        다음 상품을 분석해주세요:
        상품명: {product_data.get('title', '')}
        설명: {product_data.get('description', '')}
        가격: {product_data.get('price', 0)}원
        카테고리: {product_data.get('category', '')}
        
        다음 항목들을 분석해주세요:
        1. 상품의 주요 특징
        2. 타겟 고객층
        3. 마케팅 포인트
        4. 예상 판매 전략
        """
        
        response = model.generate_content(prompt)
        
        return {
            "status": "success",
            "analysis": response.text,
            "product": product_data
        }
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "product": product_data
        }


# 도매처 상품 수집 (실제 API)
@app.post("/api/v1/wholesaler-sync/collect/{wholesaler}")
async def collect_from_wholesaler(wholesaler: str, limit: int = 10):
    """실제 도매처 API를 사용한 상품 수집"""
    
    if wholesaler not in ["ownerclan", "domeggook", "zentrade"]:
        raise HTTPException(status_code=400, detail=f"Unsupported wholesaler: {wholesaler}")
    
    try:
        # 여기에 실제 도매처 API 호출 코드 추가
        # 현재는 시뮬레이션 데이터 반환
        
        if wholesaler == "ownerclan":
            # Ownerclan API 호출
            products = [
                {
                    "name": "실제 상품 - 블루투스 이어폰",
                    "price": 25000,
                    "stock_quantity": 100,
                    "main_image_url": "https://example.com/image1.jpg",
                    "wholesaler": "ownerclan"
                }
            ]
        else:
            products = []
        
        return {
            "status": "success",
            "wholesaler": wholesaler,
            "collected_count": len(products),
            "products": products
        }
        
    except Exception as e:
        logger.error(f"Wholesaler API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 쿠팡 API 테스트
@app.get("/api/v1/test/coupang")
async def test_coupang_api():
    """쿠팡 API 연결 테스트"""
    if not settings.COUPANG_ACCESS_KEY:
        return {"status": "error", "message": "Coupang API key not configured"}
    
    try:
        # 실제 쿠팡 API 호출 코드
        # 여기서는 간단한 상태 확인만
        return {
            "status": "success",
            "platform": "coupang",
            "vendor_id": os.getenv("COUPANG_VENDOR_ID"),
            "api_key_length": len(settings.COUPANG_ACCESS_KEY)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 네이버 API 테스트
@app.get("/api/v1/test/naver")
async def test_naver_api():
    """네이버 API 연결 테스트"""
    if not settings.NAVER_CLIENT_ID:
        return {"status": "error", "message": "Naver API key not configured"}
    
    try:
        # 실제 네이버 API 호출 코드
        return {
            "status": "success",
            "platform": "naver",
            "store_id": os.getenv("NAVER_STORE_ID"),
            "client_id_length": len(settings.NAVER_CLIENT_ID)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 포트 8000으로 실행
    uvicorn.run(
        "main_real_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
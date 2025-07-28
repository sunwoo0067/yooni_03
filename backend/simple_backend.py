"""
간단한 백엔드 서버 - 상품 수집 API만 제공
"""
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import uvicorn
import sqlite3
import uuid
import json

app = FastAPI(title="Simple Product Collector API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL DB 연결
def get_db():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database="yoni_03",
        user="postgres",
        password="1234",
        cursor_factory=RealDictCursor
    )
    return conn

# 도매처 목록
SOURCES = {
    "ownerclan": {
        "id": "ownerclan",
        "name": "오너클랜",
        "description": "국내 대표 B2B 도매 플랫폼",
        "categories": ["전자제품", "패션", "생활용품", "스포츠"]
    },
    "domeme": {
        "id": "domeme",
        "name": "도매매",
        "description": "합리적인 가격의 도매 상품",
        "categories": ["전자제품", "생활용품", "건강식품"]
    },
    "gentrade": {
        "id": "gentrade",
        "name": "젠트레이드",
        "description": "프리미엄 도매 상품 전문",
        "categories": ["전자제품", "패션", "뷰티"]
    }
}

# 샘플 상품 데이터
SAMPLE_PRODUCTS = {
    "ownerclan": {
        "이어폰": [
            {"name": "프리미엄 무선이어폰 ANC", "price": 35000, "stock": 120},
            {"name": "게이밍 이어폰 RGB", "price": 28000, "stock": 85},
            {"name": "스포츠 블루투스 이어폰", "price": 22000, "stock": 200},
        ],
        "스마트워치": [
            {"name": "스마트워치 Ultra", "price": 89000, "stock": 50},
            {"name": "피트니스 밴드 5", "price": 45000, "stock": 150},
        ]
    },
    "domeme": {
        "이어폰": [
            {"name": "일반 유선 이어폰", "price": 8000, "stock": 500},
            {"name": "초경량 무선이어폰", "price": 19000, "stock": 250},
        ]
    },
    "gentrade": {
        "이어폰": [
            {"name": "럭셔리 하이파이 이어폰", "price": 150000, "stock": 20},
        ]
    }
}

@app.get("/")
async def root():
    return {"message": "Simple Product Collector API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/product-collector/sources")
async def get_sources():
    """도매처 목록 조회"""
    return {"sources": list(SOURCES.values())}

@app.post("/api/v1/product-collector/collect")
async def collect_products(
    source: str = Form(...),
    keyword: str = Form(...),
    category: Optional[str] = Form(None),
    price_min: Optional[int] = Form(None),
    price_max: Optional[int] = Form(None),
    limit: int = Form(50)
):
    """상품 수집"""
    if source not in SOURCES:
        raise HTTPException(status_code=400, detail="지원하지 않는 도매처입니다")
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 배치 ID 생성
        batch_id = f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # 샘플 상품 필터링
        collected_products = []
        source_products = SAMPLE_PRODUCTS.get(source, {})
        
        # 키워드에 맞는 상품 찾기
        for category, products in source_products.items():
            if keyword.lower() in category.lower():
                for product in products[:limit]:
                    # 가격 필터
                    if price_min and product["price"] < price_min:
                        continue
                    if price_max and product["price"] > price_max:
                        continue
                    
                    # DB에 저장
                    product_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO collected_products (
                            id, source, name, price, stock_quantity,
                            category, collection_keyword, collection_batch_id,
                            supplier_id, main_image_url, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        product_id,
                        source,
                        product["name"],
                        product["price"],
                        product["stock"],
                        category,
                        keyword,
                        batch_id,
                        f"{source}_{len(collected_products)+1}",
                        f"https://example.com/image_{product_id}.jpg",
                        "collected"
                    ))
                    
                    collected_products.append({
                        "id": product_id,
                        "source": source,
                        "name": product["name"],
                        "price": product["price"],
                        "stock_quantity": product["stock"],
                        "category": category,
                        "image_url": f"https://example.com/image_{product_id}.jpg",
                        "collected_at": datetime.now().isoformat(),
                        "status": "collected"
                    })
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"{len(collected_products)}개 상품을 수집했습니다",
            "batch_id": batch_id,
            "total_collected": len(collected_products),
            "total_saved": len(collected_products),
            "products": collected_products,
            "search_info": {
                "source": source,
                "keyword": keyword,
                "collected_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/v1/product-collector/collected")
async def get_collected_products(
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """수집된 상품 조회"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # 쿼리 작성
        query = "SELECT * FROM collected_products WHERE 1=1"
        params = []
        
        if source:
            query += " AND source = %s"
            params.append(source)
        if keyword:
            query += " AND (name LIKE %s OR collection_keyword LIKE %s)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if status:
            query += " AND status = %s"
            params.append(status)
            
        # 전체 개수
        count_query = query.replace("*", "COUNT(*)")
        total = cursor.execute(count_query, params).fetchone()[0]
        
        # 페이지네이션
        offset = (page - 1) * limit
        query += f" ORDER BY collected_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # 상품 조회
        rows = cursor.execute(query, params).fetchall()
        
        products = []
        for row in rows:
            product = dict(row)
            # SQLite는 datetime을 문자열로 저장하므로 그대로 사용
            products.append(product)
        
        return {
            "success": True,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
            "products": products
        }
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("\n=== Simple Product Collector API (PostgreSQL) ===")
    print("서버 시작: http://localhost:8002")
    print("API 문서: http://localhost:8002/docs")
    print("종료하려면 Ctrl+C를 누르세요\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
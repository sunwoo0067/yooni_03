import os
"""
Simple FastAPI server for development testing with real data connection.
AI services are temporarily disabled to focus on core functionality.
"""
import logging
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
import asyncio
from typing import Dict, Set
from wholesaler_collector import KoreanWholesalerCollector

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Simple settings
class Settings:
    APP_NAME = "Yooni Dropshipping System"
    APP_VERSION = "1.0.0"
    DEBUG = True
    DATABASE_URL = "sqlite:///./yooni_dropshipping.db"
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3006", "http://127.0.0.1:3006"]

settings = Settings()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        # Remove from all subscriptions
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(websocket)
        logger.info("WebSocket client disconnected")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.add(connection)
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_topic(self, topic: str, message: str):
        if topic not in self.subscriptions:
            return
        disconnected = set()
        for connection in self.subscriptions[topic]:
            try:
                await connection.send_text(message)
            except:
                disconnected.add(connection)
        # Clean up disconnected clients
        for conn in disconnected:
            self.subscriptions[topic].discard(conn)
    
    def subscribe(self, websocket: WebSocket, topic: str):
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(websocket)
        logger.info(f"Client subscribed to topic: {topic}")
    
    def unsubscribe(self, websocket: WebSocket, topic: str):
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(websocket)
            logger.info(f"Client unsubscribed from topic: {topic}")

manager = ConnectionManager()

# Pydantic models
class Product(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: float
    cost: Optional[float] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    stock_quantity: Optional[int] = 0
    status: str = "active"
    main_image_url: Optional[str] = None
    platform_listings: Optional[List] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class PlatformAccount(BaseModel):
    id: Optional[str] = None
    platform: str
    name: str
    account_id: str
    status: str = "inactive"
    is_connected: bool = False
    last_sync: Optional[str] = None
    sync_status: str = "idle"
    sync_interval: int = 60
    auto_sync: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class Order(BaseModel):
    id: Optional[str] = None
    order_number: str
    customer_name: str
    customer_email: str
    customer_phone: str
    total_amount: float
    status: str = "pending"
    payment_status: str = "pending"
    platform: str
    order_date: Optional[str] = None
    items: Optional[List] = []

# Database initialization
def init_database():
    """Initialize SQLite database with basic tables."""
    db_path = Path("yooni_dropshipping.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            cost REAL,
            category TEXT,
            sku TEXT,
            stock_quantity INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            main_image_url TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Create platform_accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS platform_accounts (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            name TEXT NOT NULL,
            account_id TEXT NOT NULL,
            status TEXT DEFAULT 'inactive',
            is_connected BOOLEAN DEFAULT FALSE,
            last_sync TEXT,
            sync_status TEXT DEFAULT 'idle',
            sync_interval INTEGER DEFAULT 60,
            auto_sync BOOLEAN DEFAULT TRUE,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Create orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            order_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT,
            customer_phone TEXT,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'pending',
            platform TEXT NOT NULL,
            order_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

# Database helper functions
def get_db_connection():
    return sqlite3.connect("yooni_dropshipping.db")

def generate_id():
    from datetime import datetime
    import random
    import string
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="드롭시핑 관리 시스템 - 실제 데이터 연결",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    logger.info(f"🚀 {settings.APP_NAME} started successfully!")
    logger.info(f"📊 Database: SQLite (yooni_dropshipping.db)")
    logger.info(f"🌐 API Docs: http://localhost:8000/docs")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.APP_VERSION,
        "database": "connected"
    }

@app.get("/")
async def root():
    return {
        "message": f"🎉 {settings.APP_NAME} API Server",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "database": "SQLite (Real Data)",
        "frontend": "http://localhost:3000"
    }

# Products API
@app.get("/api/v1/products", response_model=List[Product])
async def get_products():
    """실제 데이터베이스에서 상품 목록 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    products = []
    for row in rows:
        products.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "cost": row[4],
            "category": row[5],
            "sku": row[6],
            "stock_quantity": row[7],
            "status": row[8],
            "main_image_url": row[9],
            "created_at": row[10],
            "updated_at": row[11],
            "platform_listings": []
        })
    
    conn.close()
    logger.info(f"📦 Retrieved {len(products)} products from database")
    return products

# ========================================
# 도매처 상품 수집 API
# ========================================

# 도매처별 데모 상품 데이터
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

@app.post("/api/v1/collect/products")
async def collect_products(
    source: str = Form(..., description="수집할 도매처"),
    keyword: str = Form(..., description="검색 키워드"),
    limit: int = Form(50, description="수집할 상품 수")
):
    """도매처에서 상품을 수집합니다."""
    
    if source not in ["ownerclan", "domeme", "gentrade"]:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 도매처입니다. (ownerclan, domeme, gentrade 중 선택)"
        )
    
    # 1초 지연 (실제 수집 시뮬레이션)
    await asyncio.sleep(1)
    
    # 도매처별 상품 데이터 가져오기
    base_products = DEMO_PRODUCTS.get(source, [])
    
    # 키워드로 필터링
    filtered_products = []
    for product in base_products:
        if keyword.lower() in product["name"].lower() or keyword.lower() in product["description"].lower():
            # 약간의 가격 변동 시뮬레이션
            import random
            product_copy = product.copy()
            price_variation = random.randint(-1000, 2000)
            product_copy["price"] = max(1000, product["price"] + price_variation)
            product_copy["source"] = source
            product_copy["collected_at"] = datetime.now().isoformat()
            product_copy["product_url"] = f"https://{source}.com/product/{product.get('supplier_id', 'unknown')}"
            filtered_products.append(product_copy)
    
    result_products = filtered_products[:limit]
    
    logger.info(f"📦 {source}에서 '{keyword}' 키워드로 {len(result_products)}개 상품 수집 완료")
    
    return {
        "success": True,
        "message": f"{source}에서 '{keyword}' 키워드로 {len(result_products)}개 상품을 수집했습니다.",
        "total_found": len(result_products),
        "products": result_products,
        "search_info": {
            "source": source,
            "keyword": keyword,
            "limit": limit,
            "collected_at": datetime.now().isoformat()
        }
    }

@app.get("/api/v1/collect/sources")
async def get_collection_sources():
    """사용 가능한 도매처 목록"""
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

@app.post("/api/v1/products", response_model=Product)
async def create_product(product: Product):
    """새 상품을 실제 데이터베이스에 저장"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    product_id = generate_id()
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO products (
            id, name, description, price, cost, category, sku, 
            stock_quantity, status, main_image_url, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product_id, product.name, product.description, product.price,
        product.cost, product.category, product.sku, product.stock_quantity,
        product.status, product.main_image_url, now, now
    ))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Created new product: {product.name} (ID: {product_id})")
    
    product.id = product_id
    product.created_at = now
    product.updated_at = now
    
    # Broadcast the change
    await broadcast_data_change("product_created", product.dict())
    
    return product

@app.delete("/api/v1/products/{product_id}")
async def delete_product(product_id: str):
    """상품 삭제"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    
    conn.commit()
    conn.close()
    
    logger.info(f"🗑️ Deleted product: {product_id}")
    
    # Broadcast the change
    await broadcast_data_change("product_deleted", {"id": product_id})
    
    return {"message": "Product deleted successfully"}

# Platform Accounts API
@app.get("/api/v1/platforms", response_model=List[PlatformAccount])
async def get_platform_accounts():
    """플랫폼 계정 목록 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM platform_accounts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    accounts = []
    for row in rows:
        accounts.append({
            "id": row[0],
            "platform": row[1],
            "name": row[2],
            "account_id": row[3],
            "status": row[4],
            "is_connected": bool(row[5]),
            "last_sync": row[6],
            "sync_status": row[7],
            "sync_interval": row[8],
            "auto_sync": bool(row[9]),
            "created_at": row[10],
            "updated_at": row[11]
        })
    
    conn.close()
    logger.info(f"🔗 Retrieved {len(accounts)} platform accounts from database")
    return accounts

@app.post("/api/v1/platforms", response_model=PlatformAccount)
async def create_platform_account(account: PlatformAccount):
    """새 플랫폼 계정 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    account_id = generate_id()
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO platform_accounts (
            id, platform, name, account_id, status, is_connected,
            sync_status, sync_interval, auto_sync, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        account_id, account.platform, account.name, account.account_id,
        account.status, account.is_connected, account.sync_status,
        account.sync_interval, account.auto_sync, now, now
    ))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Created new platform account: {account.name} (ID: {account_id})")
    
    account.id = account_id
    account.created_at = now
    account.updated_at = now
    return account

# Platform sync API
@app.post("/api/v1/platforms/{platform_id}/sync")
async def sync_platform(platform_id: str):
    """플랫폼 동기화 (시뮬레이션)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 플랫폼 정보 조회
    cursor.execute("SELECT * FROM platform_accounts WHERE id = ?", (platform_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Platform account not found")
    
    platform_name = row[2]  # name 컬럼
    
    # 동기화 상태 업데이트
    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE platform_accounts 
        SET sync_status = 'syncing', updated_at = ? 
        WHERE id = ?
    """, (now, platform_id))
    conn.commit()
    
    # 동기화 시작 브로드캐스트
    await broadcast_data_change("platform_sync", {
        "platform_id": platform_id,
        "platform": platform_name,
        "status": "started",
        "timestamp": now
    })
    
    # 비동기 작업 시뮬레이션
    async def simulate_sync():
        import random
        await asyncio.sleep(random.randint(3, 8))  # 3-8초 대기
        
        # 동기화 완료
        conn2 = get_db_connection()
        cursor2 = conn2.cursor()
        
        success = random.random() > 0.1  # 90% 성공률
        sync_status = "success" if success else "error"
        
        cursor2.execute("""
            UPDATE platform_accounts 
            SET sync_status = ?, last_sync = ?, updated_at = ? 
            WHERE id = ?
        """, (sync_status, now, now, platform_id))
        
        # 임의의 상품 업데이트 시뮬레이션
        if success:
            cursor2.execute("SELECT id, stock_quantity FROM products ORDER BY RANDOM() LIMIT 3")
            products = cursor2.fetchall()
            
            for product_id, current_stock in products:
                new_stock = current_stock + random.randint(-5, 10)
                if new_stock < 0:
                    new_stock = 0
                    
                cursor2.execute("""
                    UPDATE products 
                    SET stock_quantity = ?, updated_at = ? 
                    WHERE id = ?
                """, (new_stock, now, product_id))
        
        conn2.commit()
        conn2.close()
        
        # 동기화 완료 브로드캐스트
        await broadcast_data_change("platform_sync", {
            "platform_id": platform_id,
            "platform": platform_name,
            "status": "completed" if success else "failed",
            "timestamp": now
        })
        
        if success:
            await broadcast_data_change("inventory_updated", {
                "platform": platform_name,
                "updated_count": len(products) if 'products' in locals() else 0
            })
    
    # 백그라운드에서 동기화 실행
    asyncio.create_task(simulate_sync())
    
    conn.close()
    
    return {
        "message": f"{platform_name} 동기화가 시작되었습니다.",
        "platform_id": platform_id,
        "status": "syncing"
    }

# Orders API
@app.get("/api/v1/orders", response_model=List[Order])
async def get_orders():
    """주문 목록 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    orders = []
    for row in rows:
        orders.append({
            "id": row[0],
            "order_number": row[1],
            "customer_name": row[2],
            "customer_email": row[3],
            "customer_phone": row[4],
            "total_amount": row[5],
            "status": row[6],
            "payment_status": row[7],
            "platform": row[8],
            "order_date": row[9],
            "items": []
        })
    
    conn.close()
    logger.info(f"📋 Retrieved {len(orders)} orders from database")
    return orders

@app.post("/api/v1/orders", response_model=Order)
async def create_order(order: Order):
    """새 주문 생성 (테스트용)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    order_id = generate_id()
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO orders (
            id, order_number, customer_name, customer_email, customer_phone,
            total_amount, status, payment_status, platform, order_date, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id, order.order_number, order.customer_name, order.customer_email,
        order.customer_phone, order.total_amount, order.status, order.payment_status,
        order.platform, order.order_date or now, now, now
    ))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Created new order: {order.order_number} (ID: {order_id})")
    
    order.id = order_id
    order.order_date = order.order_date or now
    return order

# Dashboard statistics API
@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """대시보드 통계 데이터"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 상품 통계
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE status = 'active'")
    active_products = cursor.fetchone()[0]
    
    # 주문 통계
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_amount) FROM orders WHERE status IN ('completed', 'delivered')")
    total_revenue = cursor.fetchone()[0] or 0
    
    # 플랫폼 통계
    cursor.execute("SELECT COUNT(*) FROM platform_accounts")
    total_platforms = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM platform_accounts WHERE is_connected = 1")
    connected_platforms = cursor.fetchone()[0]
    
    conn.close()
    
    stats = {
        "products": {
            "total": total_products,
            "active": active_products,
            "inactive": total_products - active_products
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "revenue": total_revenue
        },
        "platforms": {
            "total": total_platforms,
            "connected": connected_platforms,
            "disconnected": total_platforms - connected_platforms
        },
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"📊 Generated dashboard stats: {stats}")
    return stats

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "subscribe":
                topic = message.get("topic")
                if topic:
                    manager.subscribe(websocket, topic)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "topic": topic
                    }))
            
            elif message.get("type") == "unsubscribe":
                topic = message.get("topic")
                if topic:
                    manager.unsubscribe(websocket, topic)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "topic": topic
                    }))
            
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Helper function to broadcast data changes
async def broadcast_data_change(change_type: str, data: dict):
    """Broadcast data changes to all connected clients"""
    message = json.dumps({
        "type": "data_change",
        "changeType": change_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })
    
    # Broadcast to all clients
    await manager.broadcast(message)
    
    # Also broadcast to specific topic subscribers
    await manager.broadcast_to_topic(change_type, message)

# Product collection endpoints
@app.post("/api/v1/collect/products")
async def collect_products(
    source: str = Form(...),
    keyword: str = Form(...),
    category: Optional[str] = Form(None),
    price_min: Optional[int] = Form(None),
    price_max: Optional[int] = Form(None),
    limit: int = Form(50),
    page: int = Form(1)
):
    """한국 도매 사이트에서 상품 수집"""
    logger.info(f"상품 수집 요청: {source} - {keyword}")
    
    # 지원하는 도매 사이트 확인
    supported_sources = ['ownerclan', 'domeme', 'gentrade']
    if source not in supported_sources:
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 도매 사이트: {source}. 지원 사이트: {', '.join(supported_sources)}"
        )
    
    # 수집 시작 알림
    await broadcast_data_change("collection_started", {
        "source": source,
        "keyword": keyword,
        "status": "started"
    })
    
    try:
        # 한국 도매 사이트 수집기 사용
        collector = KoreanWholesalerCollector()
        products = await collector.collect_products(source, keyword, page)
        
        # 가격 필터링
        if price_min or price_max:
            filtered_products = []
            for product in products:
                price = product.get('price', 0)
                if price_min and price < price_min:
                    continue
                if price_max and price > price_max:
                    continue
                filtered_products.append(product)
            products = filtered_products
        
        # 카테고리 설정
        if category:
            for product in products:
                product['category'] = category
        
        # 수집 개수 제한
        products = products[:limit]
        
        # 데이터베이스에 저장
        conn = get_db_connection()
        cursor = conn.cursor()
        
        saved_count = 0
        for product in products:
            try:
                product_id = generate_id()
                now = datetime.now().isoformat()
                
                # 중복 확인 (이름과 가격으로)
                cursor.execute(
                    "SELECT id FROM products WHERE name = ? AND price = ?",
                    (product['name'], product['price'])
                )
                
                if cursor.fetchone():
                    logger.info(f"중복 상품 스킵: {product['name']}")
                    continue
                
                cursor.execute("""
                    INSERT INTO products (
                        id, name, description, price, cost, category, sku,
                        stock_quantity, status, main_image_url, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_id, 
                    product['name'],
                    f"도매처: {product.get('seller', source)} | 원본 URL: {product.get('url', '')}",
                    product['price'],
                    product.get('wholesale_price', product['price'] * 0.7),  # 도매가가 없으면 70%로 추정
                    product.get('category', category or '미분류'),
                    f"{source.upper()}-{product_id[:8]}",
                    product.get('min_order', 1),
                    'active',
                    product.get('image', ''),
                    now, now
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"상품 저장 실패: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        # 수집 완료 알림
        await broadcast_data_change("collection_completed", {
            "source": source,
            "keyword": keyword,
            "total": len(products),
            "saved": saved_count,
            "status": "completed"
        })
        
        return {
            "success": True,
            "source": source,
            "keyword": keyword,
            "total": len(products),
            "saved": saved_count,
            "products": products[:10]  # 미리보기용 10개만 반환
        }
        
    except Exception as e:
        logger.error(f"상품 수집 실패: {e}")
        
        # 수집 실패 알림
        await broadcast_data_change("collection_failed", {
            "source": source,
            "keyword": keyword,
            "status": "failed",
            "error": str(e)
        })
        
        raise HTTPException(status_code=500, detail=f"상품 수집 실패: {str(e)}")

@app.get("/api/v1/collect/sources")
async def get_collection_sources():
    """지원하는 도매 사이트 목록"""
    return {
        "sources": [
            {
                "id": "ownerclan",
                "name": "오너클랜",
                "description": "국내 최대 온라인 도매 플랫폼",
                "supported": True,
                "features": ["상품검색", "카테고리별 조회", "실시간 재고"]
            },
            {
                "id": "domeme",
                "name": "도매매",
                "description": "패션 전문 도매 사이트",
                "supported": True,
                "features": ["상품검색", "도매가 정보", "최소주문수량"]
            },
            {
                "id": "gentrade",
                "name": "젠트레이드",
                "description": "종합 도매 플랫폼",
                "supported": True,
                "features": ["상품검색", "브랜드별 조회", "상세 이미지"]
            }
        ]
    }

# Sample data endpoints for testing
@app.post("/api/v1/sample-data/create")
async def create_sample_data():
    """샘플 데이터 생성 (테스트용)"""
    
    # 샘플 상품 생성
    sample_products = [
        {
            "name": "무선 이어폰 프로",
            "description": "고품질 노이즈 캔슬링 무선 이어폰",
            "price": 89000,
            "cost": 45000,
            "category": "전자제품",
            "sku": "WEP-001",
            "stock_quantity": 50,
            "status": "active"
        },
        {
            "name": "스마트워치 울트라",
            "description": "최신 건강 모니터링 스마트워치",
            "price": 299000,
            "cost": 150000,
            "category": "전자제품", 
            "sku": "SW-002",
            "stock_quantity": 25,
            "status": "active"
        },
        {
            "name": "블루투스 스피커",
            "description": "휴대용 방수 블루투스 스피커",
            "price": 59000,
            "cost": 30000,
            "category": "전자제품",
            "sku": "BS-003",
            "stock_quantity": 100,
            "status": "active"
        }
    ]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    created_products = []
    for product_data in sample_products:
        product_id = generate_id()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO products (
                id, name, description, price, cost, category, sku,
                stock_quantity, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id, product_data["name"], product_data["description"],
            product_data["price"], product_data["cost"], product_data["category"],
            product_data["sku"], product_data["stock_quantity"], product_data["status"],
            now, now
        ))
        created_products.append(product_data["name"])
    
    # 샘플 플랫폼 계정 생성
    sample_accounts = [
        {
            "platform": "coupang",
            "name": "쿠팡 메인 계정",
            "account_id": "COUPANG001",
            "status": "active",
            "is_connected": True
        },
        {
            "platform": "naver",
            "name": "네이버 스마트스토어",
            "account_id": "NAVER001", 
            "status": "active",
            "is_connected": True
        }
    ]
    
    created_accounts = []
    for account_data in sample_accounts:
        account_id = generate_id()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO platform_accounts (
                id, platform, name, account_id, status, is_connected,
                sync_status, sync_interval, auto_sync, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, account_data["platform"], account_data["name"],
            account_data["account_id"], account_data["status"], account_data["is_connected"],
            "success", 60, True, now, now
        ))
        created_accounts.append(account_data["name"])
    
    conn.commit()
    conn.close()
    
    logger.info(f"🎯 Created sample data: {len(created_products)} products, {len(created_accounts)} accounts")
    
    return {
        "message": "샘플 데이터가 성공적으로 생성되었습니다!",
        "created": {
            "products": created_products,
            "accounts": created_accounts
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0", 
        port=8003,
        reload=True,
        access_log=True,
        log_level="info"
    )
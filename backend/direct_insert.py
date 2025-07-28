"""
직접 SQL로 도매처 상품 저장
"""
import sqlite3
from datetime import datetime, timezone, timedelta
import uuid

# SQLite DB 연결
conn = sqlite3.connect('yooni_dropshipping.db')
cursor = conn.cursor()

# collected_products 테이블이 있는지 확인
cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='collected_products'
""")

if not cursor.fetchone():
    print("collected_products 테이블 생성 중...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collected_products (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            collection_keyword TEXT,
            collection_batch_id TEXT,
            supplier_id TEXT,
            supplier_name TEXT,
            supplier_url TEXT,
            name TEXT NOT NULL,
            description TEXT,
            brand TEXT,
            category TEXT,
            price REAL NOT NULL,
            original_price REAL,
            wholesale_price REAL,
            minimum_order_quantity INTEGER DEFAULT 1,
            stock_status TEXT DEFAULT 'available',
            stock_quantity INTEGER,
            main_image_url TEXT,
            status TEXT DEFAULT 'collected',
            quality_score REAL,
            popularity_score REAL,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_deleted BOOLEAN DEFAULT 0,
            deleted_at TIMESTAMP,
            metadata TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    print("테이블 생성 완료!")

# 샘플 상품 데이터
sample_products = [
    {
        "source": "ownerclan",
        "name": "프리미엄 블루투스 무선이어폰 TWS-X100",
        "price": 25000,
        "category": "전자제품/이어폰",
        "supplier_id": "OC_TWS_001",
        "brand": "SoundPro",
        "description": "최신 블루투스 5.3 지원, 노이즈 캔슬링 기능",
        "stock_quantity": 150
    },
    {
        "source": "ownerclan",
        "name": "게이밍 무선이어폰 GX-2000",
        "price": 32000,
        "category": "전자제품/이어폰",
        "supplier_id": "OC_GX_002",
        "brand": "GameAudio",
        "description": "초저지연 게이밍 모드, RGB LED",
        "stock_quantity": 80
    },
    {
        "source": "domeme",
        "name": "스마트워치 프로 2024",
        "price": 45000,
        "category": "전자제품/스마트워치",
        "supplier_id": "DM_SW_001",
        "brand": "TechWatch",
        "description": "심박수 측정, GPS, 방수 기능",
        "stock_quantity": 200
    },
    {
        "source": "domeme",
        "name": "무선충전 보조배터리 20000mAh",
        "price": 28000,
        "category": "전자제품/충전기",
        "supplier_id": "DM_PB_002",
        "brand": "PowerBank",
        "description": "고속충전 지원, 무선충전 패드 내장",
        "stock_quantity": 120
    },
    {
        "source": "gentrade",
        "name": "프리미엄 가죽 스마트폰 케이스",
        "price": 15000,
        "category": "액세서리/케이스",
        "supplier_id": "GT_CASE_001",
        "brand": "LuxCase",
        "description": "진짜 가죽 소재, 카드 수납 가능",
        "stock_quantity": 300
    }
]

print("\n=== 도매처 상품 저장 시작 ===\n")

batch_id = f"manual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
saved_count = 0

for product in sample_products:
    try:
        # UUID 생성
        product_id = str(uuid.uuid4())
        
        # 만료일 계산
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        # 데이터 삽입
        cursor.execute("""
            INSERT INTO collected_products (
                id, source, collection_keyword, collection_batch_id,
                supplier_id, supplier_name, supplier_url,
                name, description, brand, category,
                price, original_price, wholesale_price,
                stock_status, stock_quantity, main_image_url,
                quality_score, popularity_score, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            product["source"],
            "manual_test",
            batch_id,
            product["supplier_id"],
            f"{product['source']} 공급업체",
            f"https://{product['source']}.com/product/{product['supplier_id']}",
            product["name"],
            product["description"],
            product["brand"],
            product["category"],
            product["price"],
            int(product["price"] * 1.3),  # original_price
            int(product["price"] * 0.8),  # wholesale_price
            "available",
            product["stock_quantity"],
            f"https://example.com/images/{product['supplier_id']}.jpg",
            8.5,  # quality_score
            7.0,  # popularity_score
            expires_at.isoformat()
        ))
        
        saved_count += 1
        print(f"[OK] 저장됨: {product['name']}")
        print(f"  - 도매처: {product['source']}")
        print(f"  - 가격: {product['price']:,}원")
        print(f"  - 재고: {product['stock_quantity']}개")
        print(f"  - ID: {product_id}\n")
        
    except Exception as e:
        print(f"[FAIL] 실패: {product['name']} - {str(e)}\n")

# 커밋
conn.commit()

print(f"\n총 {saved_count}개 상품 저장 완료!")

# 저장된 상품 조회
print("\n=== 저장된 상품 목록 ===")
cursor.execute("""
    SELECT id, name, source, price, stock_quantity, collected_at 
    FROM collected_products 
    ORDER BY collected_at DESC
""")

rows = cursor.fetchall()
for i, row in enumerate(rows, 1):
    print(f"\n{i}. {row[1]}")
    print(f"   ID: {row[0]}")
    print(f"   도매처: {row[2]}")
    print(f"   가격: {row[3]:,}원")
    print(f"   재고: {row[4]}개")
    print(f"   수집시간: {row[5]}")

# 통계
print("\n=== 수집 통계 ===")
cursor.execute("SELECT source, COUNT(*) FROM collected_products GROUP BY source")
stats = cursor.fetchall()
for source, count in stats:
    print(f"- {source}: {count}개")

cursor.execute("SELECT COUNT(*) FROM collected_products")
total = cursor.fetchone()[0]
print(f"\n전체: {total}개")

# 연결 종료
conn.close()

print("\n=== 완료 ===")
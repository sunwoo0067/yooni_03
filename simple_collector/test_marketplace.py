"""
마켓플레이스 API 테스트
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import SessionLocal
from database.models import ApiCredential
from collectors.marketplace_collectors import MarketplaceCollector

async def test_marketplace_apis():
    """마켓플레이스 API 테스트"""
    print("마켓플레이스 API 테스트 시작")
    print("=" * 50)
    
    db = SessionLocal()
    
    # 테스트용 API 크레덴셜 설정
    test_credentials = [
        {
            "supplier_code": "coupang",
            "api_config": {
                "access_key": "YOUR_COUPANG_ACCESS_KEY",
                "secret_key": "YOUR_COUPANG_SECRET_KEY",
                "vendor_id": "YOUR_VENDOR_ID"
            }
        },
        {
            "supplier_code": "naver",
            "api_config": {
                "client_id": "YOUR_NAVER_CLIENT_ID",
                "client_secret": "YOUR_NAVER_CLIENT_SECRET"
            }
        },
        {
            "supplier_code": "11st",
            "api_config": {
                "api_key": "YOUR_11ST_API_KEY"
            }
        }
    ]
    
    # API 크레덴셜 저장
    for cred_data in test_credentials:
        existing = db.query(ApiCredential).filter(
            ApiCredential.supplier_code == cred_data["supplier_code"]
        ).first()
        
        if not existing:
            credential = ApiCredential(
                supplier_code=cred_data["supplier_code"],
                api_config=cred_data["api_config"],
                is_active=True
            )
            db.add(credential)
        else:
            print(f"{cred_data['supplier_code']} 크레덴셜이 이미 존재합니다.")
    
    db.commit()
    
    # 마켓플레이스 수집 테스트
    try:
        collector = MarketplaceCollector(db)
        
        # 각 마켓플레이스별로 테스트
        for marketplace in ["coupang", "naver", "11st"]:
            print(f"\n{marketplace} 테스트 중...")
            
            if marketplace in collector.collectors:
                try:
                    products = await collector.collectors[marketplace].get_products(limit=5)
                    print(f"  [OK] {marketplace}: {len(products)}개 상품 수집")
                    
                    if products:
                        print(f"  예시: {products[0]['title'][:50]}...")
                        print(f"  가격: {products[0]['price']:,}원")
                        
                except Exception as e:
                    print(f"  [FAIL] {marketplace} 오류: {e}")
            else:
                print(f"  [SKIP] {marketplace}: API 키가 설정되지 않음")
                
    except Exception as e:
        print(f"테스트 실패: {e}")
        
    finally:
        db.close()
        
    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("\n실제 API 키를 설정하려면:")
    print("1. http://localhost:4173 접속")
    print("2. 설정 메뉴로 이동")
    print("3. 각 마켓플레이스 탭에서 API 키 입력")

if __name__ == "__main__":
    asyncio.run(test_marketplace_apis())
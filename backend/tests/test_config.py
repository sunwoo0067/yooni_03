"""
테스트 설정 파일
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 테스트 환경 설정
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///test_dropshipping.db"

# Mock 설정
MOCK_EXTERNAL_APIS = True
MOCK_DATABASE = True

# 테스트 데이터
TEST_DATA = {
    "zentrade_product": {
        "product_id": "Z123",
        "name": "테스트 상품",
        "price": 10000,
        "stock": 100,
        "category": "의류"
    },
    "ownerclan_product": {
        "product_code": "OC456",
        "product_name": "오너클랜 상품",
        "selling_price": 15000,
        "inventory": 50,
        "category_name": "전자제품"
    },
    "domeggook_product": {
        "id": "D789",
        "title": "도매꾹 상품",
        "price": 20000,
        "sold_count": 1000,
        "rating": 4.5
    }
}
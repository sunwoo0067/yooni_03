"""
간단한 테스트 설정
"""
import pytest
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_api():
    """API 모킹 fixture"""
    from unittest.mock import Mock
    return Mock()


@pytest.fixture
def sample_product():
    """샘플 상품 데이터"""
    return {
        "id": "TEST123",
        "name": "테스트 상품",
        "price": 30000,
        "stock": 100
    }
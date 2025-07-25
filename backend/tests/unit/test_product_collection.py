"""
상품수집 시스템 유닛 테스트
- Zentrade, OwnerClan, Domeggook API 연동 테스트
- 중복 상품 탐지 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from app.services.wholesalers.zentrade_api import ZentradeAPI
from app.services.wholesalers.ownerclan_api import OwnerClanAPI
from app.services.wholesalers.domeggook_api import DomeggookAPI
from app.services.collection.product_collector import ProductCollector
from app.services.collection.duplicate_finder import DuplicateFinder
from app.services.collection.data_normalizer import DataNormalizer


class TestZentradeAPI:
    """Zentrade API 테스트"""
    
    @pytest.fixture
    def zentrade_api(self):
        return ZentradeAPI(api_key="test_key", api_secret="test_secret")
    
    @patch('requests.get')
    def test_get_products_success(self, mock_get, zentrade_api):
        """상품 목록 조회 성공 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "products": [
                    {
                        "product_id": "Z123",
                        "name": "테스트 상품",
                        "price": 10000,
                        "stock": 100,
                        "category": "의류"
                    }
                ],
                "total": 1
            }
        }
        mock_get.return_value = mock_response
        
        products = zentrade_api.get_products(page=1, limit=10)
        
        assert len(products) == 1
        assert products[0]["product_id"] == "Z123"
        assert products[0]["price"] == 10000
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_products_api_error(self, mock_get, zentrade_api):
        """API 에러 처리 테스트"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            zentrade_api.get_products()
        
        assert "Unauthorized" in str(exc_info.value)
    
    @patch('requests.get')
    def test_get_product_detail(self, mock_get, zentrade_api):
        """상품 상세 정보 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "product_id": "Z123",
                "name": "테스트 상품",
                "description": "상세 설명",
                "images": ["image1.jpg", "image2.jpg"],
                "options": [
                    {"name": "색상", "values": ["빨강", "파랑"]}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        product = zentrade_api.get_product_detail("Z123")
        
        assert product["product_id"] == "Z123"
        assert len(product["images"]) == 2
        assert len(product["options"]) == 1
    
    def test_rate_limiting(self, zentrade_api):
        """Rate limiting 테스트"""
        # Rate limiter가 제대로 동작하는지 테스트
        with patch.object(zentrade_api, '_check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False  # Rate limit 초과
            
            with pytest.raises(Exception) as exc_info:
                zentrade_api.get_products()
            
            assert "Rate limit" in str(exc_info.value)


class TestOwnerClanAPI:
    """OwnerClan API 테스트"""
    
    @pytest.fixture
    def ownerclan_api(self):
        return OwnerClanAPI(client_id="test_id", client_secret="test_secret")
    
    @patch('requests.post')
    def test_authentication(self, mock_post, ownerclan_api):
        """인증 토큰 획득 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        token = ownerclan_api._get_access_token()
        
        assert token == "test_token"
        mock_post.assert_called_once()
    
    @patch('requests.get')
    def test_get_categories(self, mock_get, ownerclan_api):
        """카테고리 목록 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "categories": [
                {"id": "C1", "name": "의류", "parent_id": None},
                {"id": "C2", "name": "전자제품", "parent_id": None}
            ]
        }
        mock_get.return_value = mock_response
        
        with patch.object(ownerclan_api, '_get_headers', return_value={"Authorization": "Bearer test"}):
            categories = ownerclan_api.get_categories()
        
        assert len(categories) == 2
        assert categories[0]["name"] == "의류"
    
    @patch('requests.get')
    def test_search_products(self, mock_get, ownerclan_api):
        """상품 검색 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "products": [
                {
                    "product_code": "OC456",
                    "product_name": "검색된 상품",
                    "selling_price": 15000,
                    "inventory": 50
                }
            ],
            "total_count": 1
        }
        mock_get.return_value = mock_response
        
        with patch.object(ownerclan_api, '_get_headers', return_value={"Authorization": "Bearer test"}):
            products = ownerclan_api.search_products(keyword="테스트")
        
        assert len(products) == 1
        assert products[0]["product_code"] == "OC456"
        assert "테스트" in mock_get.call_args[1]["params"]["keyword"]


class TestDomeggookAPI:
    """Domeggook API 테스트"""
    
    @pytest.fixture
    def domeggook_api(self):
        return DomeggookAPI(api_key="test_key")
    
    @patch('requests.get')
    def test_get_best_products(self, mock_get, domeggook_api):
        """베스트 상품 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": "D789",
                    "title": "베스트 상품",
                    "price": 20000,
                    "sold_count": 1000,
                    "rating": 4.5
                }
            ]
        }
        mock_get.return_value = mock_response
        
        products = domeggook_api.get_best_products()
        
        assert len(products) == 1
        assert products[0]["id"] == "D789"
        assert products[0]["sold_count"] == 1000
    
    @patch('requests.get')
    def test_get_new_arrivals(self, mock_get, domeggook_api):
        """신상품 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": "D999",
                    "title": "신상품",
                    "price": 25000,
                    "created_at": "2025-01-25T10:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        products = domeggook_api.get_new_arrivals()
        
        assert len(products) == 1
        assert products[0]["id"] == "D999"
    
    def test_error_handling(self, domeggook_api):
        """에러 처리 테스트"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            with pytest.raises(Exception) as exc_info:
                domeggook_api.get_products()
            
            assert "Network error" in str(exc_info.value)


class TestProductCollector:
    """상품 수집기 통합 테스트"""
    
    @pytest.fixture
    def product_collector(self):
        return ProductCollector()
    
    def test_collect_from_all_sources(self, product_collector):
        """모든 소스에서 상품 수집 테스트"""
        mock_zentrade = Mock()
        mock_zentrade.get_products.return_value = [
            {"product_id": "Z1", "name": "Zentrade 상품", "price": 10000}
        ]
        
        mock_ownerclan = Mock()
        mock_ownerclan.get_products.return_value = [
            {"product_code": "O1", "product_name": "OwnerClan 상품", "selling_price": 15000}
        ]
        
        mock_domeggook = Mock()
        mock_domeggook.get_products.return_value = [
            {"id": "D1", "title": "Domeggook 상품", "price": 20000}
        ]
        
        with patch.object(product_collector, 'zentrade_api', mock_zentrade):
            with patch.object(product_collector, 'ownerclan_api', mock_ownerclan):
                with patch.object(product_collector, 'domeggook_api', mock_domeggook):
                    products = product_collector.collect_all()
        
        assert len(products) == 3
        assert any(p["source"] == "zentrade" for p in products)
        assert any(p["source"] == "ownerclan" for p in products)
        assert any(p["source"] == "domeggook" for p in products)
    
    def test_error_recovery(self, product_collector):
        """에러 발생 시 복구 테스트"""
        mock_zentrade = Mock()
        mock_zentrade.get_products.side_effect = Exception("API Error")
        
        mock_ownerclan = Mock()
        mock_ownerclan.get_products.return_value = [
            {"product_code": "O1", "product_name": "OwnerClan 상품", "selling_price": 15000}
        ]
        
        with patch.object(product_collector, 'zentrade_api', mock_zentrade):
            with patch.object(product_collector, 'ownerclan_api', mock_ownerclan):
                products = product_collector.collect_all(continue_on_error=True)
        
        # Zentrade에서 에러가 발생해도 OwnerClan 상품은 수집되어야 함
        assert len(products) == 1
        assert products[0]["source"] == "ownerclan"


class TestDuplicateFinder:
    """중복 상품 탐지 테스트"""
    
    @pytest.fixture
    def duplicate_finder(self):
        return DuplicateFinder()
    
    def test_find_exact_duplicates(self, duplicate_finder):
        """정확한 중복 상품 탐지 테스트"""
        products = [
            {"id": "1", "name": "동일한 상품", "price": 10000},
            {"id": "2", "name": "동일한 상품", "price": 10000},
            {"id": "3", "name": "다른 상품", "price": 15000}
        ]
        
        duplicates = duplicate_finder.find_duplicates(products)
        
        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2  # 2개가 중복
        assert all(p["name"] == "동일한 상품" for p in duplicates[0])
    
    def test_find_similar_products(self, duplicate_finder):
        """유사 상품 탐지 테스트"""
        products = [
            {"id": "1", "name": "나이키 운동화 270", "price": 100000},
            {"id": "2", "name": "나이키 운동화 270 에어맥스", "price": 105000},
            {"id": "3", "name": "아디다스 운동화", "price": 90000}
        ]
        
        similar = duplicate_finder.find_similar_products(products, threshold=0.8)
        
        assert len(similar) > 0
        # 나이키 운동화들이 유사 상품으로 탐지되어야 함
        nike_group = similar[0]
        assert all("나이키" in p["name"] for p in nike_group)
    
    def test_duplicate_by_barcode(self, duplicate_finder):
        """바코드 기준 중복 탐지 테스트"""
        products = [
            {"id": "1", "name": "상품 A", "barcode": "1234567890"},
            {"id": "2", "name": "상품 B", "barcode": "1234567890"},
            {"id": "3", "name": "상품 C", "barcode": "0987654321"}
        ]
        
        duplicates = duplicate_finder.find_duplicates_by_barcode(products)
        
        assert len(duplicates) == 1
        assert len(duplicates["1234567890"]) == 2


class TestDataNormalizer:
    """데이터 정규화 테스트"""
    
    @pytest.fixture
    def data_normalizer(self):
        return DataNormalizer()
    
    def test_normalize_zentrade_data(self, data_normalizer):
        """Zentrade 데이터 정규화 테스트"""
        raw_data = {
            "product_id": "Z123",
            "name": "테스트 상품",
            "price": 10000,
            "stock": 100,
            "category": "의류/상의"
        }
        
        normalized = data_normalizer.normalize_zentrade(raw_data)
        
        assert normalized["id"] == "Z123"
        assert normalized["title"] == "테스트 상품"
        assert normalized["price"] == 10000
        assert normalized["quantity"] == 100
        assert normalized["source"] == "zentrade"
    
    def test_normalize_ownerclan_data(self, data_normalizer):
        """OwnerClan 데이터 정규화 테스트"""
        raw_data = {
            "product_code": "OC456",
            "product_name": "테스트 상품",
            "selling_price": 15000,
            "inventory": 50,
            "category_name": "전자제품"
        }
        
        normalized = data_normalizer.normalize_ownerclan(raw_data)
        
        assert normalized["id"] == "OC456"
        assert normalized["title"] == "테스트 상품"
        assert normalized["price"] == 15000
        assert normalized["quantity"] == 50
        assert normalized["source"] == "ownerclan"
    
    def test_normalize_with_missing_fields(self, data_normalizer):
        """필수 필드 누락 시 처리 테스트"""
        raw_data = {
            "product_id": "Z123",
            "name": "테스트 상품"
            # price와 stock 누락
        }
        
        normalized = data_normalizer.normalize_zentrade(raw_data)
        
        assert normalized["price"] == 0  # 기본값
        assert normalized["quantity"] == 0  # 기본값


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
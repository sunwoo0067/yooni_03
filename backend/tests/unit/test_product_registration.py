"""
상품등록 시스템 유닛 테스트
- 쿠팡/네이버/11번가 API 등록 테스트
- 멀티계정 관리 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any

from app.services.platforms.coupang_api import CoupangAPI
from app.services.platforms.naver_api import NaverAPI
from app.services.platforms.eleventh_street_api import EleventhStreetAPI
from app.services.platforms.platform_manager import PlatformManager
from app.services.account.market_account_manager import MarketAccountManager
from app.services.registration.product_registration_engine import ProductRegistrationEngine


class TestCoupangAPI:
    """쿠팡 API 테스트"""
    
    @pytest.fixture
    def coupang_api(self):
        return CoupangAPI(
            access_key="test_key",
            secret_key="test_secret",
            vendor_id="test_vendor"
        )
    
    @patch('requests.post')
    def test_register_product_success(self, mock_post, coupang_api):
        """상품 등록 성공 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "SUCCESS",
            "data": {
                "productId": "CP123456",
                "sellerProductId": "SP123456",
                "status": "ACTIVE"
            }
        }
        mock_post.return_value = mock_response
        
        product_data = {
            "displayCategoryCode": 123,
            "sellerProductName": "테스트 상품",
            "vendorId": "test_vendor",
            "saleStartedAt": "2025-01-25",
            "items": [{
                "itemName": "기본",
                "originalPrice": 30000,
                "salePrice": 25000,
                "outboundShippingTimeDay": 2
            }]
        }
        
        result = coupang_api.register_product(product_data)
        
        assert result["code"] == "SUCCESS"
        assert result["data"]["productId"] == "CP123456"
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_register_product_validation_error(self, mock_post, coupang_api):
        """상품 등록 검증 오류 테스트"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": "VALIDATION_ERROR",
            "message": "필수 항목이 누락되었습니다",
            "data": {
                "errors": [
                    {"field": "displayCategoryCode", "message": "카테고리 코드는 필수입니다"}
                ]
            }
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            coupang_api.register_product({})
        
        assert "VALIDATION_ERROR" in str(exc_info.value)
    
    @patch('requests.put')
    def test_update_product_price(self, mock_put, coupang_api):
        """상품 가격 업데이트 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "SUCCESS",
            "message": "가격이 업데이트되었습니다"
        }
        mock_put.return_value = mock_response
        
        result = coupang_api.update_price("CP123456", 20000)
        
        assert result["code"] == "SUCCESS"
        mock_put.assert_called_once()
    
    @patch('requests.get')
    def test_get_product_status(self, mock_get, coupang_api):
        """상품 상태 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "SUCCESS",
            "data": {
                "productId": "CP123456",
                "status": "ACTIVE",
                "items": [
                    {"itemId": "CI123", "saleStatus": "ON_SALE", "stock": 100}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        status = coupang_api.get_product_status("CP123456")
        
        assert status["data"]["status"] == "ACTIVE"
        assert status["data"]["items"][0]["saleStatus"] == "ON_SALE"
    
    def test_hmac_signature_generation(self, coupang_api):
        """HMAC 서명 생성 테스트"""
        method = "POST"
        path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        
        signature = coupang_api._generate_hmac_signature(method, path)
        
        assert len(signature) > 0
        assert isinstance(signature, str)


class TestNaverAPI:
    """네이버 쇼핑 API 테스트"""
    
    @pytest.fixture
    def naver_api(self):
        return NaverAPI(
            client_id="test_client",
            client_secret="test_secret"
        )
    
    @patch('requests.post')
    def test_create_product(self, mock_post, naver_api):
        """상품 생성 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "timestamp": "2025-01-25T10:00:00",
            "traceId": "trace123",
            "originProductNo": "NP123456"
        }
        mock_post.return_value = mock_response
        
        product_data = {
            "name": "네이버 테스트 상품",
            "detailContent": "상세 설명",
            "salePrice": 35000,
            "stockQuantity": 50,
            "images": {
                "representativeImage": {"url": "http://image.url"}
            }
        }
        
        result = naver_api.create_product(product_data)
        
        assert result["originProductNo"] == "NP123456"
        mock_post.assert_called_once()
    
    @patch('requests.get')
    def test_get_categories(self, mock_get, naver_api):
        """카테고리 목록 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "contents": [
                {
                    "id": "50000000",
                    "name": "패션의류",
                    "wholeCategoryName": "패션의류"
                },
                {
                    "id": "50000001",
                    "name": "패션잡화",
                    "wholeCategoryName": "패션잡화"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        categories = naver_api.get_categories()
        
        assert len(categories["contents"]) == 2
        assert categories["contents"][0]["name"] == "패션의류"
    
    @patch('requests.put')
    def test_update_product_status(self, mock_put, naver_api):
        """상품 상태 변경 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "timestamp": "2025-01-25T10:00:00",
            "message": "상태가 변경되었습니다"
        }
        mock_put.return_value = mock_response
        
        result = naver_api.update_status("NP123456", "SALE")
        
        assert "message" in result
        mock_put.assert_called_once()
    
    @patch('requests.get')
    def test_search_products(self, mock_get, naver_api):
        """상품 검색 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "contents": [
                {
                    "originProductNo": "NP123456",
                    "name": "검색된 상품",
                    "salePrice": 25000,
                    "statusType": "SALE"
                }
            ],
            "total": 1
        }
        mock_get.return_value = mock_response
        
        results = naver_api.search_products("테스트")
        
        assert len(results["contents"]) == 1
        assert results["contents"][0]["name"] == "검색된 상품"


class TestEleventhStreetAPI:
    """11번가 API 테스트"""
    
    @pytest.fixture
    def eleventh_api(self):
        return EleventhStreetAPI(
            api_key="test_api_key"
        )
    
    @patch('requests.post')
    def test_register_product(self, mock_post, eleventh_api):
        """상품 등록 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <ProductResponse>
            <productNo>11ST123456</productNo>
            <productStatus>103</productStatus>
            <message>상품이 등록되었습니다</message>
        </ProductResponse>
        """
        mock_post.return_value = mock_response
        
        product_data = {
            "productName": "11번가 테스트 상품",
            "productPrice": 40000,
            "productQty": 30,
            "productDescription": "상품 설명"
        }
        
        result = eleventh_api.register_product(product_data)
        
        assert "11ST123456" in result
        mock_post.assert_called_once()
    
    @patch('requests.get')
    def test_get_product_info(self, mock_get, eleventh_api):
        """상품 정보 조회 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <Product>
            <productNo>11ST123456</productNo>
            <productName>테스트 상품</productName>
            <productPrice>40000</productPrice>
            <productStatus>103</productStatus>
        </Product>
        """
        mock_get.return_value = mock_response
        
        info = eleventh_api.get_product_info("11ST123456")
        
        assert "11ST123456" in info
        assert "40000" in info
    
    @patch('requests.put')
    def test_update_stock(self, mock_put, eleventh_api):
        """재고 업데이트 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <Response>
            <resultCode>0</resultCode>
            <message>재고가 업데이트되었습니다</message>
        </Response>
        """
        mock_put.return_value = mock_response
        
        result = eleventh_api.update_stock("11ST123456", 50)
        
        assert "재고가 업데이트되었습니다" in result
        mock_put.assert_called_once()
    
    def test_parse_xml_response(self, eleventh_api):
        """XML 응답 파싱 테스트"""
        xml_string = """
        <Product>
            <productNo>12345</productNo>
            <productName>테스트</productName>
            <options>
                <option>
                    <optionName>색상</optionName>
                    <optionValue>빨강</optionValue>
                </option>
                <option>
                    <optionName>사이즈</optionName>
                    <optionValue>L</optionValue>
                </option>
            </options>
        </Product>
        """
        
        parsed = eleventh_api._parse_xml(xml_string)
        
        assert "productNo" in parsed
        assert "options" in parsed
        assert len(parsed["options"]) == 2


class TestMarketAccountManager:
    """멀티계정 관리 테스트"""
    
    @pytest.fixture
    def account_manager(self):
        return MarketAccountManager()
    
    def test_add_account(self, account_manager):
        """계정 추가 테스트"""
        account = {
            "platform": "coupang",
            "account_name": "테스트계정1",
            "credentials": {
                "access_key": "key1",
                "secret_key": "secret1",
                "vendor_id": "vendor1"
            }
        }
        
        result = account_manager.add_account(account)
        
        assert result["success"] == True
        assert result["account_id"] is not None
    
    def test_get_available_account(self, account_manager):
        """사용 가능한 계정 조회 테스트"""
        # 계정 추가
        accounts = [
            {
                "platform": "coupang",
                "account_name": f"계정{i}",
                "daily_limit": 100,
                "current_usage": i * 30
            }
            for i in range(3)
        ]
        
        for acc in accounts:
            account_manager.add_account(acc)
        
        # 사용량이 가장 적은 계정 선택
        available = account_manager.get_available_account("coupang")
        
        assert available is not None
        assert available["account_name"] == "계정0"
    
    def test_account_rotation(self, account_manager):
        """계정 로테이션 테스트"""
        # 3개 계정 추가
        for i in range(3):
            account_manager.add_account({
                "platform": "naver",
                "account_name": f"네이버{i}",
                "daily_limit": 50
            })
        
        # 순차적으로 계정 선택
        selected_accounts = []
        for _ in range(6):
            account = account_manager.get_next_account("naver")
            selected_accounts.append(account["account_name"])
        
        # 모든 계정이 균등하게 선택되었는지 확인
        assert selected_accounts.count("네이버0") == 2
        assert selected_accounts.count("네이버1") == 2
        assert selected_accounts.count("네이버2") == 2
    
    def test_account_limit_check(self, account_manager):
        """계정 한도 체크 테스트"""
        account = {
            "platform": "11st",
            "account_name": "한도테스트",
            "daily_limit": 100,
            "current_usage": 95
        }
        
        account_manager.add_account(account)
        
        # 한도 초과 체크
        can_use = account_manager.check_limit("한도테스트", 10)
        assert can_use == False
        
        can_use = account_manager.check_limit("한도테스트", 5)
        assert can_use == True
    
    def test_update_usage_statistics(self, account_manager):
        """사용량 통계 업데이트 테스트"""
        account_id = account_manager.add_account({
            "platform": "coupang",
            "account_name": "통계테스트"
        })["account_id"]
        
        # 사용량 업데이트
        account_manager.update_usage(account_id, {
            "products_registered": 10,
            "api_calls": 50,
            "errors": 2
        })
        
        stats = account_manager.get_account_stats(account_id)
        
        assert stats["products_registered"] == 10
        assert stats["api_calls"] == 50
        assert stats["errors"] == 2


class TestProductRegistrationEngine:
    """상품 등록 엔진 통합 테스트"""
    
    @pytest.fixture
    def registration_engine(self):
        return ProductRegistrationEngine()
    
    @patch.object(PlatformManager, 'get_platform_api')
    def test_register_to_single_platform(self, mock_get_api, registration_engine):
        """단일 플랫폼 등록 테스트"""
        mock_api = Mock()
        mock_api.register_product.return_value = {
            "productId": "TEST123",
            "status": "SUCCESS"
        }
        mock_get_api.return_value = mock_api
        
        product = {
            "name": "테스트 상품",
            "price": 30000,
            "description": "설명",
            "images": ["url1", "url2"]
        }
        
        result = registration_engine.register_product(product, "coupang")
        
        assert result["status"] == "SUCCESS"
        assert result["productId"] == "TEST123"
        mock_api.register_product.assert_called_once()
    
    @patch.object(PlatformManager, 'get_platform_api')
    def test_register_to_multiple_platforms(self, mock_get_api, registration_engine):
        """다중 플랫폼 등록 테스트"""
        # 각 플랫폼별 Mock API 생성
        mock_apis = {
            "coupang": Mock(),
            "naver": Mock(),
            "11st": Mock()
        }
        
        for platform, api in mock_apis.items():
            api.register_product.return_value = {
                "productId": f"{platform.upper()}123",
                "status": "SUCCESS"
            }
        
        mock_get_api.side_effect = lambda p: mock_apis[p]
        
        product = {
            "name": "멀티플랫폼 상품",
            "price": 40000
        }
        
        results = registration_engine.register_to_all_platforms(product)
        
        assert len(results) == 3
        for platform, result in results.items():
            assert result["status"] == "SUCCESS"
            assert platform.upper() in result["productId"]
    
    def test_retry_on_failure(self, registration_engine):
        """실패 시 재시도 테스트"""
        mock_api = Mock()
        mock_api.register_product.side_effect = [
            Exception("일시적 오류"),
            Exception("또 다른 오류"),
            {"productId": "SUCCESS123", "status": "SUCCESS"}
        ]
        
        with patch.object(registration_engine, '_get_api', return_value=mock_api):
            result = registration_engine.register_with_retry({}, "coupang", max_retries=3)
        
        assert result["status"] == "SUCCESS"
        assert mock_api.register_product.call_count == 3
    
    def test_validation_before_registration(self, registration_engine):
        """등록 전 유효성 검사 테스트"""
        # 필수 필드 누락
        invalid_product = {
            "name": "상품명만 있는 상품"
            # price, images 등 누락
        }
        
        with pytest.raises(ValueError) as exc_info:
            registration_engine.validate_product(invalid_product)
        
        assert "필수 필드" in str(exc_info.value)
        
        # 유효한 상품
        valid_product = {
            "name": "유효한 상품",
            "price": 30000,
            "description": "설명",
            "images": ["url1"],
            "category": "의류"
        }
        
        assert registration_engine.validate_product(valid_product) == True
    
    def test_platform_specific_formatting(self, registration_engine):
        """플랫폼별 데이터 포맷팅 테스트"""
        base_product = {
            "name": "기본 상품",
            "price": 25000,
            "description": "기본 설명",
            "options": [
                {"name": "색상", "values": ["빨강", "파랑"]}
            ]
        }
        
        # 쿠팡 포맷
        coupang_format = registration_engine.format_for_platform(base_product, "coupang")
        assert "sellerProductName" in coupang_format
        assert "items" in coupang_format
        
        # 네이버 포맷
        naver_format = registration_engine.format_for_platform(base_product, "naver")
        assert "detailContent" in naver_format
        assert "salePrice" in naver_format
        
        # 11번가 포맷
        eleventh_format = registration_engine.format_for_platform(base_product, "11st")
        assert "productName" in eleventh_format
        assert "productPrice" in eleventh_format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
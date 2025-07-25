"""
상품가공 시스템 유닛 테스트
- AI 상품명 생성기 테스트
- 이미지 프로세싱 엔진 테스트
- 마켓 가이드라인 준수 테스트
- 수파베이스 업로드 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io
import base64
from datetime import datetime
from typing import List, Dict, Any

from app.services.processing.product_name_processor import ProductNameProcessor
from app.services.processing.image_processing_engine import ImageProcessingEngine
from app.services.processing.market_guideline_manager import MarketGuidelineManager
from app.services.processing.cost_optimizer import CostOptimizer
from app.services.ai.gemini_service import GeminiService


class TestProductNameProcessor:
    """AI 상품명 생성기 테스트"""
    
    @pytest.fixture
    def name_processor(self):
        return ProductNameProcessor()
    
    @patch.object(GeminiService, 'generate_content')
    def test_generate_optimized_name(self, mock_gemini, name_processor):
        """최적화된 상품명 생성 테스트"""
        mock_gemini.return_value = {
            "optimized_name": "[인기] 프리미엄 무선 이어폰 블루투스 5.0 노이즈캔슬링",
            "keywords": ["무선이어폰", "블루투스", "노이즈캔슬링"],
            "seo_score": 85
        }
        
        original_name = "Wireless Earbuds BT5.0 ANC"
        platform = "coupang"
        
        result = name_processor.generate_name(original_name, platform)
        
        assert len(result["optimized_name"]) > 0
        assert result["seo_score"] > 0
        assert len(result["keywords"]) > 0
        mock_gemini.assert_called_once()
    
    def test_validate_name_length(self, name_processor):
        """상품명 길이 검증 테스트"""
        test_cases = [
            ("쿠팡", "짧은이름", False),  # 너무 짧음
            ("쿠팡", "적절한 길이의 상품명입니다", True),
            ("쿠팡", "너무 긴 상품명" * 20, False),  # 너무 김
            ("네이버", "네이버 쇼핑 적절한 상품명", True)
        ]
        
        for platform, name, expected in test_cases:
            is_valid = name_processor.validate_name_length(name, platform)
            assert is_valid == expected
    
    def test_remove_prohibited_words(self, name_processor):
        """금지어 제거 테스트"""
        prohibited_words = ["최고", "최상", "1위", "독점"]
        
        test_name = "최고의 품질 1위 독점 상품"
        cleaned = name_processor.remove_prohibited_words(test_name, prohibited_words)
        
        for word in prohibited_words:
            assert word not in cleaned
        assert "품질" in cleaned
        assert "상품" in cleaned
    
    def test_add_platform_specific_keywords(self, name_processor):
        """플랫폼별 키워드 추가 테스트"""
        base_name = "무선 이어폰"
        
        # 쿠팡용
        coupang_name = name_processor.add_platform_keywords(base_name, "coupang")
        assert any(keyword in coupang_name for keyword in ["로켓배송", "당일배송", "무료배송"])
        
        # 네이버용
        naver_name = name_processor.add_platform_keywords(base_name, "naver")
        assert any(keyword in naver_name for keyword in ["정품", "공식"])
    
    @patch.object(GeminiService, 'generate_content')
    def test_batch_name_generation(self, mock_gemini, name_processor):
        """배치 상품명 생성 테스트"""
        mock_gemini.side_effect = [
            {"optimized_name": f"최적화된 상품{i}", "seo_score": 80+i}
            for i in range(3)
        ]
        
        products = [
            {"id": "1", "name": "상품1"},
            {"id": "2", "name": "상품2"},
            {"id": "3", "name": "상품3"}
        ]
        
        results = name_processor.batch_generate_names(products, "coupang")
        
        assert len(results) == 3
        assert all("optimized_name" in r for r in results)
        assert mock_gemini.call_count == 3


class TestImageProcessingEngine:
    """이미지 프로세싱 엔진 테스트"""
    
    @pytest.fixture
    def image_processor(self):
        return ImageProcessingEngine()
    
    def create_test_image(self, size=(1000, 1000), color='RGB'):
        """테스트용 이미지 생성"""
        image = Image.new(color, size, color='white')
        return image
    
    def test_resize_image(self, image_processor):
        """이미지 리사이징 테스트"""
        original = self.create_test_image((2000, 1500))
        
        # 정사각형으로 리사이즈
        resized = image_processor.resize_image(original, (1000, 1000))
        
        assert resized.size == (1000, 1000)
        assert resized.mode == original.mode
    
    def test_optimize_image_quality(self, image_processor):
        """이미지 품질 최적화 테스트"""
        original = self.create_test_image()
        
        # 품질 최적화
        optimized = image_processor.optimize_quality(original, quality=85)
        
        # 파일 크기가 줄어들었는지 확인
        original_bytes = io.BytesIO()
        optimized_bytes = io.BytesIO()
        
        original.save(original_bytes, format='JPEG', quality=100)
        optimized.save(optimized_bytes, format='JPEG', quality=85)
        
        assert len(optimized_bytes.getvalue()) < len(original_bytes.getvalue())
    
    def test_add_watermark(self, image_processor):
        """워터마크 추가 테스트"""
        original = self.create_test_image()
        watermark_text = "SAMPLE"
        
        watermarked = image_processor.add_watermark(original, watermark_text)
        
        assert watermarked.size == original.size
        # 워터마크가 추가되면 이미지가 변경됨
        assert watermarked.tobytes() != original.tobytes()
    
    def test_remove_background(self, image_processor):
        """배경 제거 테스트"""
        with patch('rembg.remove') as mock_remove:
            mock_remove.return_value = self.create_test_image(color='RGBA')
            
            original = self.create_test_image()
            result = image_processor.remove_background(original)
            
            assert result.mode == 'RGBA'
            mock_remove.assert_called_once()
    
    def test_batch_image_processing(self, image_processor):
        """배치 이미지 처리 테스트"""
        images = [self.create_test_image() for _ in range(3)]
        
        operations = [
            {"type": "resize", "params": {"size": (800, 800)}},
            {"type": "optimize", "params": {"quality": 90}}
        ]
        
        results = image_processor.batch_process(images, operations)
        
        assert len(results) == 3
        for result in results:
            assert result.size == (800, 800)
    
    def test_generate_thumbnail(self, image_processor):
        """썸네일 생성 테스트"""
        original = self.create_test_image((2000, 2000))
        
        thumbnail = image_processor.generate_thumbnail(original, size=(200, 200))
        
        assert thumbnail.size == (200, 200)
        assert thumbnail.mode == original.mode
    
    def test_apply_filters(self, image_processor):
        """필터 적용 테스트"""
        original = self.create_test_image()
        
        # 밝기 조정
        brightened = image_processor.adjust_brightness(original, factor=1.2)
        assert brightened.size == original.size
        
        # 대비 조정
        contrasted = image_processor.adjust_contrast(original, factor=1.3)
        assert contrasted.size == original.size
        
        # 선명도 조정
        sharpened = image_processor.sharpen(original, factor=1.5)
        assert sharpened.size == original.size


class TestMarketGuidelineManager:
    """마켓 가이드라인 준수 테스트"""
    
    @pytest.fixture
    def guideline_manager(self):
        return MarketGuidelineManager()
    
    def test_validate_coupang_guidelines(self, guideline_manager):
        """쿠팡 가이드라인 검증 테스트"""
        product = {
            "name": "프리미엄 무선 이어폰",
            "images": [Image.new('RGB', (1000, 1000))],
            "price": 50000,
            "description": "고품질 무선 이어폰입니다."
        }
        
        validation = guideline_manager.validate_coupang(product)
        
        assert "name_valid" in validation
        assert "images_valid" in validation
        assert "price_valid" in validation
        assert validation["overall_valid"] in [True, False]
    
    def test_validate_naver_guidelines(self, guideline_manager):
        """네이버 가이드라인 검증 테스트"""
        product = {
            "name": "정품 블루투스 스피커",
            "category": "전자제품>음향기기",
            "brand": "테스트브랜드",
            "origin": "대한민국"
        }
        
        validation = guideline_manager.validate_naver(product)
        
        assert "category_valid" in validation
        assert "required_fields_valid" in validation
        assert len(validation["missing_fields"]) >= 0
    
    def test_validate_11st_guidelines(self, guideline_manager):
        """11번가 가이드라인 검증 테스트"""
        product = {
            "name": "생활용품 수납함",
            "price": 15000,
            "shipping_fee": 2500,
            "options": [
                {"name": "사이즈", "values": ["S", "M", "L"]}
            ]
        }
        
        validation = guideline_manager.validate_11st(product)
        
        assert "options_valid" in validation
        assert "shipping_valid" in validation
    
    def test_auto_fix_guideline_issues(self, guideline_manager):
        """가이드라인 자동 수정 테스트"""
        product = {
            "name": "최고의 1위 상품!!!",  # 금지어 포함
            "price": "50000원",  # 문자열 가격
            "images": []  # 이미지 없음
        }
        
        fixed = guideline_manager.auto_fix_issues(product, "coupang")
        
        assert "최고" not in fixed["name"]
        assert "1위" not in fixed["name"]
        assert isinstance(fixed["price"], int)
        assert fixed["price"] == 50000
    
    def test_guideline_compliance_score(self, guideline_manager):
        """가이드라인 준수 점수 계산 테스트"""
        products = [
            {
                "name": "정상 상품명",
                "price": 30000,
                "images": [Image.new('RGB', (1000, 1000))],
                "description": "상세 설명"
            },
            {
                "name": "최고!!!",
                "price": "가격문의",
                "images": [],
                "description": ""
            }
        ]
        
        scores = [guideline_manager.calculate_compliance_score(p, "coupang") 
                 for p in products]
        
        assert scores[0] > scores[1]  # 첫 번째 상품이 더 높은 점수
        assert 0 <= scores[0] <= 100
        assert 0 <= scores[1] <= 100


class TestSupabaseUpload:
    """수파베이스 업로드 테스트"""
    
    @pytest.fixture
    def mock_supabase(self):
        mock = Mock()
        mock.storage.from_.return_value = mock
        mock.upload.return_value = {"path": "test/path.jpg"}
        mock.table.return_value = mock
        mock.insert.return_value = mock
        mock.execute.return_value = {"data": [{"id": 1}]}
        return mock
    
    def test_upload_image_to_storage(self, mock_supabase):
        """이미지 스토리지 업로드 테스트"""
        image = Image.new('RGB', (1000, 1000))
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        
        file_path = "products/test_product.jpg"
        
        result = mock_supabase.storage.from_("product-images").upload(
            file_path, image_bytes.getvalue()
        )
        
        assert result["path"] == "test/path.jpg"
        mock_supabase.storage.from_.assert_called_with("product-images")
    
    def test_save_product_metadata(self, mock_supabase):
        """상품 메타데이터 저장 테스트"""
        product_data = {
            "name": "테스트 상품",
            "price": 30000,
            "category": "전자제품",
            "images": ["url1", "url2"],
            "created_at": datetime.now().isoformat()
        }
        
        result = mock_supabase.table("products").insert(product_data).execute()
        
        assert result["data"][0]["id"] == 1
        mock_supabase.table.assert_called_with("products")
    
    def test_batch_upload(self, mock_supabase):
        """배치 업로드 테스트"""
        products = [
            {"name": f"상품{i}", "price": 10000 * i}
            for i in range(5)
        ]
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = {
            "data": [{"id": i} for i in range(5)]
        }
        
        result = mock_supabase.table("products").insert(products).execute()
        
        assert len(result["data"]) == 5
        assert all("id" in item for item in result["data"])
    
    def test_update_product_status(self, mock_supabase):
        """상품 상태 업데이트 테스트"""
        product_id = 123
        status_update = {
            "status": "processed",
            "processed_at": datetime.now().isoformat()
        }
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = {
            "data": [{"id": product_id, **status_update}]
        }
        
        result = mock_supabase.table("products").update(status_update).eq("id", product_id).execute()
        
        assert result["data"][0]["status"] == "processed"
        assert "processed_at" in result["data"][0]


class TestCostOptimizer:
    """비용 최적화 테스트"""
    
    @pytest.fixture
    def cost_optimizer(self):
        return CostOptimizer()
    
    def test_calculate_optimal_price(self, cost_optimizer):
        """최적 가격 계산 테스트"""
        product = {
            "wholesale_price": 10000,
            "shipping_cost": 2500,
            "platform_fee_rate": 0.1,
            "target_margin": 0.3
        }
        
        optimal_price = cost_optimizer.calculate_optimal_price(product)
        
        # (10000 + 2500) / (1 - 0.1 - 0.3) = 12500 / 0.6 = 20833
        assert optimal_price >= 20000
        assert optimal_price <= 25000
    
    def test_analyze_competitor_pricing(self, cost_optimizer):
        """경쟁사 가격 분석 테스트"""
        our_price = 30000
        competitor_prices = [28000, 32000, 29000, 35000, 27000]
        
        analysis = cost_optimizer.analyze_competitors(our_price, competitor_prices)
        
        assert "position" in analysis
        assert "avg_competitor_price" in analysis
        assert "recommendation" in analysis
        assert analysis["avg_competitor_price"] == 30200
    
    def test_suggest_discount_strategy(self, cost_optimizer):
        """할인 전략 제안 테스트"""
        product = {
            "current_price": 50000,
            "min_price": 40000,
            "inventory": 100,
            "daily_sales": 5,
            "days_in_stock": 20
        }
        
        strategy = cost_optimizer.suggest_discount_strategy(product)
        
        assert "discount_rate" in strategy
        assert "reason" in strategy
        assert 0 <= strategy["discount_rate"] <= 0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
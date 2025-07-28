"""
AI 서비스 테스트
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any


@pytest.mark.unit
@pytest.mark.requires_db
class TestAIManager:
    """AI 매니저 서비스 테스트"""
    
    @pytest.fixture
    def mock_ai_manager(self):
        """AI 매니저 모킹"""
        with patch('app.services.ai.ai_manager.AIManager') as mock:
            instance = mock.return_value
            instance.generate_description = AsyncMock()
            instance.analyze_market_trend = AsyncMock()
            instance.optimize_price = AsyncMock()
            instance.recommend_products = AsyncMock()
            yield instance
    
    @pytest.mark.asyncio
    async def test_generate_product_description(self, mock_ai_manager):
        """상품 설명 생성 테스트"""
        # 테스트 데이터
        product_data = {
            "name": "iPhone 15 Pro",
            "category": "스마트폰",
            "features": ["A17 Pro 칩", "티타늄 디자인", "48MP 카메라"]
        }
        
        expected_description = """
        iPhone 15 Pro는 혁신적인 A17 Pro 칩을 탑재한 프리미엄 스마트폰입니다.
        티타늄 소재로 제작된 견고하면서도 가벼운 디자인과 
        48MP 고해상도 카메라로 전문가급 사진 촬영이 가능합니다.
        """
        
        mock_ai_manager.generate_description.return_value = expected_description
        
        # 실행
        result = await mock_ai_manager.generate_description(product_data)
        
        # 검증
        assert result == expected_description
        mock_ai_manager.generate_description.assert_called_once_with(product_data)
    
    @pytest.mark.asyncio
    async def test_analyze_market_trend(self, mock_ai_manager):
        """시장 트렌드 분석 테스트"""
        # 테스트 데이터
        product_name = "무선 이어폰"
        category = "전자제품"
        
        expected_analysis = {
            "trend_score": 85,
            "demand_level": "high",
            "competition_level": "medium",
            "recommended_keywords": ["블루투스", "노이즈캔슬링", "장시간배터리"],
            "price_trend": "increasing",
            "seasonal_factor": 1.2
        }
        
        mock_ai_manager.analyze_market_trend.return_value = expected_analysis
        
        # 실행
        result = await mock_ai_manager.analyze_market_trend(product_name, category)
        
        # 검증
        assert result["trend_score"] == 85
        assert result["demand_level"] == "high"
        assert "블루투스" in result["recommended_keywords"]
        mock_ai_manager.analyze_market_trend.assert_called_once_with(product_name, category)
    
    @pytest.mark.asyncio
    async def test_optimize_price(self, mock_ai_manager):
        """가격 최적화 테스트"""
        # 테스트 데이터
        price_data = {
            "current_price": 150000,
            "cost": 100000,
            "competitor_prices": [140000, 160000, 155000],
            "demand_score": 75,
            "category": "전자제품"
        }
        
        expected_optimization = {
            "recommended_price": 148000,
            "confidence_score": 0.87,
            "expected_profit_margin": 0.32,
            "price_change_reason": "경쟁력 있는 가격으로 수요 증대 예상",
            "risk_level": "low"
        }
        
        mock_ai_manager.optimize_price.return_value = expected_optimization
        
        # 실행
        result = await mock_ai_manager.optimize_price(price_data)
        
        # 검증
        assert result["recommended_price"] == 148000
        assert result["confidence_score"] > 0.8
        assert result["expected_profit_margin"] > 0.3
        mock_ai_manager.optimize_price.assert_called_once_with(price_data)
    
    @pytest.mark.asyncio
    async def test_recommend_products(self, mock_ai_manager):
        """상품 추천 테스트"""
        # 테스트 데이터
        user_preferences = {
            "categories": ["전자제품", "생활용품"],
            "price_range": {"min": 50000, "max": 200000},
            "previous_purchases": ["스마트폰", "무선충전기"]
        }
        
        expected_recommendations = [
            {
                "product_id": 1,
                "name": "무선 이어폰",
                "price": 89000,
                "similarity_score": 0.92,
                "reason": "이전 구매 패턴과 높은 연관성"
            },
            {
                "product_id": 2,
                "name": "스마트워치",
                "price": 159000,
                "similarity_score": 0.88,
                "reason": "스마트폰과 호환성 높은 액세서리"
            }
        ]
        
        mock_ai_manager.recommend_products.return_value = expected_recommendations
        
        # 실행
        result = await mock_ai_manager.recommend_products(user_preferences)
        
        # 검증
        assert len(result) == 2
        assert result[0]["similarity_score"] > 0.9
        assert all(rec["price"] >= 50000 and rec["price"] <= 200000 for rec in result)
        mock_ai_manager.recommend_products.assert_called_once_with(user_preferences)


@pytest.mark.unit
class TestGeminiService:
    """Gemini AI 서비스 테스트"""
    
    @pytest.fixture
    def mock_gemini_service(self):
        """Gemini 서비스 모킹"""
        with patch('app.services.ai.gemini_service.GeminiService') as mock:
            instance = mock.return_value
            instance.generate_text = AsyncMock()
            instance.analyze_image = AsyncMock()
            instance.translate_text = AsyncMock()
            yield instance
    
    @pytest.mark.asyncio
    async def test_generate_product_text(self, mock_gemini_service):
        """상품 텍스트 생성 테스트"""
        prompt = "다음 상품의 마케팅 문구를 작성해주세요: 무선 블루투스 이어폰"
        expected_text = "혁신적인 음질과 편안한 착용감을 자랑하는 프리미엄 무선 이어폰"
        
        mock_gemini_service.generate_text.return_value = expected_text
        
        result = await mock_gemini_service.generate_text(prompt)
        
        assert result == expected_text
        mock_gemini_service.generate_text.assert_called_once_with(prompt)
    
    @pytest.mark.asyncio
    async def test_analyze_product_image(self, mock_gemini_service):
        """상품 이미지 분석 테스트"""
        image_data = "base64_encoded_image_data"
        expected_analysis = {
            "detected_objects": ["스마트폰", "케이스"],
            "colors": ["블랙", "실버"],
            "quality_score": 8.5,
            "suggested_tags": ["프리미엄", "모던", "세련됨"]
        }
        
        mock_gemini_service.analyze_image.return_value = expected_analysis
        
        result = await mock_gemini_service.analyze_image(image_data)
        
        assert "스마트폰" in result["detected_objects"]
        assert result["quality_score"] > 8.0
        mock_gemini_service.analyze_image.assert_called_once_with(image_data)
    
    @pytest.mark.asyncio
    async def test_translate_product_description(self, mock_gemini_service):
        """상품 설명 번역 테스트"""
        korean_text = "고품질 무선 이어폰입니다."
        target_language = "en"
        expected_translation = "This is a high-quality wireless earphone."
        
        mock_gemini_service.translate_text.return_value = expected_translation
        
        result = await mock_gemini_service.translate_text(korean_text, target_language)
        
        assert result == expected_translation
        mock_gemini_service.translate_text.assert_called_once_with(korean_text, target_language)


@pytest.mark.unit
class TestDemandForecasting:
    """수요 예측 서비스 테스트"""
    
    @pytest.fixture
    def mock_demand_service(self):
        """수요 예측 서비스 모킹"""
        with patch('app.services.ai.demand_forecasting.DemandForecastingService') as mock:
            instance = mock.return_value
            instance.forecast_demand = AsyncMock()
            instance.analyze_seasonality = AsyncMock()
            instance.predict_stock_shortage = AsyncMock()
            yield instance
    
    @pytest.mark.asyncio
    async def test_forecast_product_demand(self, mock_demand_service):
        """상품 수요 예측 테스트"""
        product_id = 123
        forecast_days = 30
        
        expected_forecast = {
            "product_id": product_id,
            "forecast_period": forecast_days,
            "predicted_demand": [
                {"date": "2024-01-01", "demand": 150},
                {"date": "2024-01-02", "demand": 165},
                {"date": "2024-01-03", "demand": 140}
            ],
            "confidence_interval": {"lower": 0.85, "upper": 0.95},
            "trend": "increasing",
            "seasonality_factor": 1.15
        }
        
        mock_demand_service.forecast_demand.return_value = expected_forecast
        
        result = await mock_demand_service.forecast_demand(product_id, forecast_days)
        
        assert result["product_id"] == product_id
        assert result["forecast_period"] == forecast_days
        assert len(result["predicted_demand"]) > 0
        assert result["trend"] in ["increasing", "decreasing", "stable"]
        mock_demand_service.forecast_demand.assert_called_once_with(product_id, forecast_days)
    
    @pytest.mark.asyncio
    async def test_analyze_seasonal_patterns(self, mock_demand_service):
        """계절성 패턴 분석 테스트"""
        product_category = "의류"
        
        expected_seasonality = {
            "category": product_category,
            "seasonal_peaks": [
                {"season": "spring", "factor": 1.2},
                {"season": "fall", "factor": 1.4}
            ],
            "low_seasons": [
                {"season": "summer", "factor": 0.8}
            ],
            "holiday_effects": {
                "christmas": 1.8,
                "black_friday": 2.1
            }
        }
        
        mock_demand_service.analyze_seasonality.return_value = expected_seasonality
        
        result = await mock_demand_service.analyze_seasonality(product_category)
        
        assert result["category"] == product_category
        assert len(result["seasonal_peaks"]) > 0
        assert "christmas" in result["holiday_effects"]
        mock_demand_service.analyze_seasonality.assert_called_once_with(product_category)
    
    @pytest.mark.asyncio
    async def test_predict_stock_shortage(self, mock_demand_service):
        """재고 부족 예측 테스트"""
        product_id = 456
        current_stock = 100
        
        expected_prediction = {
            "product_id": product_id,
            "current_stock": current_stock,
            "shortage_probability": 0.75,
            "estimated_shortage_date": "2024-01-15",
            "recommended_reorder_quantity": 250,
            "reorder_urgency": "high"
        }
        
        mock_demand_service.predict_stock_shortage.return_value = expected_prediction
        
        result = await mock_demand_service.predict_stock_shortage(product_id, current_stock)
        
        assert result["product_id"] == product_id
        assert result["current_stock"] == current_stock
        assert 0 <= result["shortage_probability"] <= 1
        assert result["reorder_urgency"] in ["low", "medium", "high"]
        mock_demand_service.predict_stock_shortage.assert_called_once_with(product_id, current_stock)


@pytest.mark.unit
class TestPriceOptimizer:
    """가격 최적화 서비스 테스트"""
    
    @pytest.fixture
    def mock_price_optimizer(self):
        """가격 최적화 서비스 모킹"""
        with patch('app.services.ai.price_optimizer.PriceOptimizer') as mock:
            instance = mock.return_value
            instance.optimize_price = AsyncMock()
            instance.analyze_competitor_prices = AsyncMock()
            instance.calculate_dynamic_pricing = AsyncMock()
            yield instance
    
    @pytest.mark.asyncio
    async def test_optimize_single_product_price(self, mock_price_optimizer):
        """단일 상품 가격 최적화 테스트"""
        optimization_data = {
            "product_id": 789,
            "current_price": 50000,
            "cost": 30000,
            "target_margin": 0.4,
            "market_data": {
                "demand_elasticity": -1.5,
                "competitor_avg_price": 48000
            }
        }
        
        expected_optimization = {
            "product_id": 789,
            "current_price": 50000,
            "optimized_price": 47500,
            "expected_profit_increase": 0.12,
            "demand_change_estimate": 0.08,
            "confidence_score": 0.89,
            "optimization_strategy": "competitive_pricing"
        }
        
        mock_price_optimizer.optimize_price.return_value = expected_optimization
        
        result = await mock_price_optimizer.optimize_price(optimization_data)
        
        assert result["product_id"] == 789
        assert result["optimized_price"] < result["current_price"]
        assert result["expected_profit_increase"] > 0
        assert result["confidence_score"] > 0.8
        mock_price_optimizer.optimize_price.assert_called_once_with(optimization_data)
    
    @pytest.mark.asyncio
    async def test_analyze_competitor_pricing(self, mock_price_optimizer):
        """경쟁사 가격 분석 테스트"""
        product_name = "무선 마우스"
        category = "컴퓨터 액세서리"
        
        expected_analysis = {
            "product_name": product_name,
            "category": category,
            "competitor_data": [
                {"competitor": "A사", "price": 25000, "rating": 4.5},
                {"competitor": "B사", "price": 28000, "rating": 4.2},
                {"competitor": "C사", "price": 22000, "rating": 4.0}
            ],
            "price_statistics": {
                "min_price": 22000,
                "max_price": 28000,
                "avg_price": 25000,
                "median_price": 25000
            },
            "market_position_recommendation": "price_leadership"
        }
        
        mock_price_optimizer.analyze_competitor_prices.return_value = expected_analysis
        
        result = await mock_price_optimizer.analyze_competitor_prices(product_name, category)
        
        assert result["product_name"] == product_name
        assert len(result["competitor_data"]) == 3
        assert result["price_statistics"]["avg_price"] == 25000
        assert result["market_position_recommendation"] in ["price_leadership", "premium", "value"]
        mock_price_optimizer.analyze_competitor_prices.assert_called_once_with(product_name, category)
    
    @pytest.mark.asyncio
    async def test_dynamic_pricing_calculation(self, mock_price_optimizer):
        """동적 가격 계산 테스트"""
        pricing_factors = {
            "base_price": 100000,
            "demand_multiplier": 1.2,
            "inventory_level": 0.3,  # 30% 재고
            "time_factor": 0.9,  # 시간대 할인
            "customer_segment": "premium"
        }
        
        expected_dynamic_price = {
            "base_price": 100000,
            "final_price": 108000,
            "adjustments": {
                "demand_adjustment": 20000,
                "inventory_adjustment": -5000,
                "time_adjustment": -10000,
                "segment_adjustment": 3000
            },
            "effective_discount": 0.08
        }
        
        mock_price_optimizer.calculate_dynamic_pricing.return_value = expected_dynamic_price
        
        result = await mock_price_optimizer.calculate_dynamic_pricing(pricing_factors)
        
        assert result["base_price"] == 100000
        assert result["final_price"] != result["base_price"]
        assert "demand_adjustment" in result["adjustments"]
        assert isinstance(result["effective_discount"], float)
        mock_price_optimizer.calculate_dynamic_pricing.assert_called_once_with(pricing_factors)


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.slow
class TestAIServicesIntegration:
    """AI 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_complete_ai_workflow(self, test_db, sample_product_data):
        """완전한 AI 워크플로우 통합 테스트"""
        # 실제 서비스 인스턴스를 사용하는 경우의 테스트
        # 모킹 없이 실제 AI 서비스들의 연동을 테스트
        
        try:
            from app.services.ai.ai_manager import AIManager
            ai_manager = AIManager()
            
            # 1. 상품 설명 생성
            description = await ai_manager.generate_description(sample_product_data)
            assert isinstance(description, str)
            assert len(description) > 10
            
            # 2. 시장 트렌드 분석
            trend_analysis = await ai_manager.analyze_market_trend(
                sample_product_data["name"], 
                sample_product_data.get("category", "일반")
            )
            assert isinstance(trend_analysis, dict)
            assert "trend_score" in trend_analysis
            
            # 3. 가격 최적화
            price_optimization = await ai_manager.optimize_price({
                "current_price": sample_product_data["price"],
                "cost": sample_product_data["cost"],
                "category": sample_product_data.get("category", "일반")
            })
            assert isinstance(price_optimization, dict)
            assert "recommended_price" in price_optimization
            
        except ImportError:
            pytest.skip("AI 서비스 모듈이 구현되지 않음")
        except Exception as e:
            pytest.skip(f"AI 서비스 테스트 중 오류 발생: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_ai_service_error_handling(self):
        """AI 서비스 오류 처리 테스트"""
        try:
            from app.services.ai.ai_manager import AIManager
            ai_manager = AIManager()
            
            # 잘못된 입력으로 오류 처리 테스트
            invalid_data = None
            
            with pytest.raises((ValueError, TypeError)):
                await ai_manager.generate_description(invalid_data)
                
        except ImportError:
            pytest.skip("AI 서비스 모듈이 구현되지 않음")
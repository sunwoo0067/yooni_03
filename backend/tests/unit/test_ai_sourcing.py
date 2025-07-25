"""
AI 소싱 시스템 유닛 테스트
- 마켓 데이터 수집기 테스트
- 트렌드 분석기 테스트
- AI 상품 분석기 테스트
- 스마트 소싱 엔진 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import List, Dict, Any

from app.services.sourcing.market_data_collector import MarketDataCollector
from app.services.sourcing.trend_analyzer import TrendAnalyzer
from app.services.sourcing.ai_product_analyzer import AIProductAnalyzer
from app.services.sourcing.smart_sourcing_engine import SmartSourcingEngine
from app.services.ai.gemini_service import GeminiService


class TestMarketDataCollector:
    """마켓 데이터 수집기 테스트"""
    
    @pytest.fixture
    def market_collector(self):
        return MarketDataCollector()
    
    @patch('requests.get')
    def test_collect_coupang_data(self, mock_get, market_collector):
        """쿠팡 데이터 수집 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <div class="product">
                <div class="name">인기 상품</div>
                <div class="price">50,000원</div>
                <div class="review-count">1,234</div>
                <div class="rating">4.5</div>
            </div>
        </html>
        """
        mock_get.return_value = mock_response
        
        data = market_collector.collect_coupang_bestsellers("패션")
        
        assert len(data) > 0
        assert "name" in data[0]
        assert "price" in data[0]
        assert data[0]["platform"] == "coupang"
    
    @patch('requests.get')
    def test_collect_naver_trends(self, mock_get, market_collector):
        """네이버 쇼핑 트렌드 수집 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "트렌드 상품",
                    "lprice": 30000,
                    "hprice": 35000,
                    "productType": "일반",
                    "review": 500
                }
            ]
        }
        mock_get.return_value = mock_response
        
        with patch.dict('os.environ', {'NAVER_CLIENT_ID': 'test', 'NAVER_CLIENT_SECRET': 'test'}):
            data = market_collector.collect_naver_shopping_trends("화장품")
        
        assert len(data) > 0
        assert data[0]["platform"] == "naver"
        assert "review_count" in data[0]
    
    def test_aggregate_market_data(self, market_collector):
        """마켓 데이터 집계 테스트"""
        coupang_data = [
            {"name": "상품A", "price": 10000, "sales": 100},
            {"name": "상품B", "price": 20000, "sales": 200}
        ]
        naver_data = [
            {"name": "상품A", "price": 11000, "sales": 150},
            {"name": "상품C", "price": 30000, "sales": 50}
        ]
        
        aggregated = market_collector.aggregate_data({
            "coupang": coupang_data,
            "naver": naver_data
        })
        
        assert len(aggregated) == 3  # 상품 A, B, C
        # 상품A는 두 플랫폼에서 판매되므로 평균값을 가져야 함
        product_a = next(p for p in aggregated if p["name"] == "상품A")
        assert product_a["avg_price"] == 10500
        assert product_a["total_sales"] == 250
    
    def test_calculate_market_score(self, market_collector):
        """마켓 점수 계산 테스트"""
        product_data = {
            "name": "테스트 상품",
            "price": 50000,
            "sales": 1000,
            "review_count": 500,
            "rating": 4.5,
            "platforms": ["coupang", "naver"]
        }
        
        score = market_collector.calculate_market_score(product_data)
        
        assert 0 <= score <= 100
        assert score > 50  # 좋은 지표를 가진 상품이므로 높은 점수


class TestTrendAnalyzer:
    """트렌드 분석기 테스트"""
    
    @pytest.fixture
    def trend_analyzer(self):
        return TrendAnalyzer()
    
    @patch('pytrends.request.TrendReq.build_payload')
    @patch('pytrends.request.TrendReq.interest_over_time')
    def test_analyze_google_trends(self, mock_interest, mock_build, trend_analyzer):
        """구글 트렌드 분석 테스트"""
        # Mock 데이터 생성
        dates = pd.date_range(start='2025-01-01', periods=30, freq='D')
        trend_data = pd.DataFrame({
            '테스트 키워드': np.random.randint(50, 100, size=30),
            'isPartial': [False] * 30
        }, index=dates)
        
        mock_interest.return_value = trend_data
        
        result = trend_analyzer.analyze_keyword_trend("테스트 키워드")
        
        assert "trend_score" in result
        assert "growth_rate" in result
        assert result["trend_score"] > 0
    
    def test_detect_seasonal_trends(self, trend_analyzer):
        """계절 트렌드 감지 테스트"""
        # 계절성이 있는 데이터 생성
        dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
        seasonal_data = []
        
        for date in dates:
            # 여름에 높은 값을 가지는 패턴
            if 5 <= date.month <= 8:
                value = np.random.randint(70, 100)
            else:
                value = np.random.randint(20, 50)
            seasonal_data.append({
                "date": date,
                "value": value
            })
        
        seasonality = trend_analyzer.detect_seasonality(seasonal_data)
        
        assert seasonality["has_seasonality"] == True
        assert seasonality["peak_season"] in ["summer", "여름"]
    
    def test_predict_future_trend(self, trend_analyzer):
        """미래 트렌드 예측 테스트"""
        # 상승 트렌드 데이터 생성
        historical_data = []
        for i in range(90):
            historical_data.append({
                "date": datetime.now() - timedelta(days=90-i),
                "value": 50 + i * 0.5 + np.random.randint(-5, 5)
            })
        
        prediction = trend_analyzer.predict_trend(historical_data, days=30)
        
        assert len(prediction) == 30
        assert prediction[-1]["value"] > historical_data[-1]["value"]  # 상승 트렌드
    
    def test_identify_emerging_keywords(self, trend_analyzer):
        """신규 트렌드 키워드 식별 테스트"""
        search_data = [
            {"keyword": "기존상품", "volume": 10000, "growth": 0.05},
            {"keyword": "신규트렌드", "volume": 5000, "growth": 2.5},
            {"keyword": "핫아이템", "volume": 3000, "growth": 3.0}
        ]
        
        emerging = trend_analyzer.identify_emerging_keywords(search_data)
        
        assert len(emerging) >= 2
        assert "신규트렌드" in [k["keyword"] for k in emerging]
        assert "핫아이템" in [k["keyword"] for k in emerging]


class TestAIProductAnalyzer:
    """AI 상품 분석기 테스트"""
    
    @pytest.fixture
    def ai_analyzer(self):
        return AIProductAnalyzer()
    
    @patch.object(GeminiService, 'generate_content')
    def test_analyze_product_potential(self, mock_gemini, ai_analyzer):
        """상품 잠재력 분석 테스트"""
        mock_gemini.return_value = {
            "potential_score": 85,
            "reasons": [
                "높은 검색량",
                "긍정적인 리뷰",
                "합리적인 가격"
            ],
            "risks": [
                "계절성 상품",
                "경쟁 심화"
            ]
        }
        
        product = {
            "name": "테스트 상품",
            "price": 30000,
            "category": "패션",
            "reviews": 500,
            "rating": 4.3
        }
        
        analysis = ai_analyzer.analyze_potential(product)
        
        assert analysis["potential_score"] == 85
        assert len(analysis["reasons"]) > 0
        assert len(analysis["risks"]) > 0
    
    @patch.object(GeminiService, 'generate_content')
    def test_generate_market_insights(self, mock_gemini, ai_analyzer):
        """마켓 인사이트 생성 테스트"""
        mock_gemini.return_value = {
            "insights": [
                "여성 20-30대 타겟 상품이 인기",
                "친환경 소재 선호도 증가",
                "프리미엄 제품 수요 상승"
            ],
            "recommendations": [
                "친환경 인증 제품 소싱",
                "프리미엄 라인 확대"
            ]
        }
        
        market_data = {
            "category": "화장품",
            "top_keywords": ["비건", "친환경", "프리미엄"],
            "avg_price": 45000
        }
        
        insights = ai_analyzer.generate_insights(market_data)
        
        assert len(insights["insights"]) > 0
        assert len(insights["recommendations"]) > 0
    
    @patch.object(GeminiService, 'generate_content')
    def test_predict_sales_volume(self, mock_gemini, ai_analyzer):
        """판매량 예측 테스트"""
        mock_gemini.return_value = {
            "predicted_monthly_sales": 500,
            "confidence": 0.75,
            "factors": {
                "positive": ["트렌드 상승", "좋은 리뷰"],
                "negative": ["높은 경쟁"]
            }
        }
        
        product = {
            "name": "테스트 상품",
            "price": 25000,
            "category": "생활용품",
            "competitor_count": 50,
            "market_trend": "상승"
        }
        
        prediction = ai_analyzer.predict_sales(product)
        
        assert prediction["predicted_monthly_sales"] > 0
        assert 0 <= prediction["confidence"] <= 1
        assert "factors" in prediction
    
    def test_categorize_product_risk(self, ai_analyzer):
        """상품 리스크 분류 테스트"""
        products = [
            {"name": "안전상품", "return_rate": 0.02, "complaints": 1},
            {"name": "중간위험", "return_rate": 0.08, "complaints": 5},
            {"name": "고위험", "return_rate": 0.15, "complaints": 20}
        ]
        
        for product in products:
            risk = ai_analyzer.assess_risk(product)
            
            if product["name"] == "안전상품":
                assert risk["level"] == "low"
            elif product["name"] == "고위험":
                assert risk["level"] == "high"


class TestSmartSourcingEngine:
    """스마트 소싱 엔진 테스트"""
    
    @pytest.fixture
    def sourcing_engine(self):
        return SmartSourcingEngine()
    
    def test_generate_sourcing_recommendations(self, sourcing_engine):
        """소싱 추천 생성 테스트"""
        market_analysis = {
            "trending_categories": ["패션", "뷰티"],
            "high_demand_products": [
                {"name": "상품A", "score": 90},
                {"name": "상품B", "score": 85}
            ]
        }
        
        inventory_status = {
            "low_stock": ["카테고리1"],
            "overstocked": ["카테고리2"]
        }
        
        recommendations = sourcing_engine.generate_recommendations(
            market_analysis, inventory_status
        )
        
        assert len(recommendations) > 0
        assert recommendations[0]["priority"] in ["high", "medium", "low"]
        assert "reason" in recommendations[0]
    
    def test_calculate_profit_margin(self, sourcing_engine):
        """수익 마진 계산 테스트"""
        product = {
            "wholesale_price": 10000,
            "suggested_retail_price": 25000,
            "platform_fee_rate": 0.1,
            "shipping_cost": 2500
        }
        
        margin = sourcing_engine.calculate_profit_margin(product)
        
        assert margin["gross_margin"] == 15000
        assert margin["net_margin"] == 10000  # 15000 - 2500 - 2500
        assert margin["margin_rate"] == 0.4  # 10000 / 25000
    
    def test_optimize_sourcing_portfolio(self, sourcing_engine):
        """소싱 포트폴리오 최적화 테스트"""
        products = [
            {"name": "A", "margin": 0.5, "risk": 0.2, "demand": 0.8},
            {"name": "B", "margin": 0.3, "risk": 0.1, "demand": 0.9},
            {"name": "C", "margin": 0.7, "risk": 0.6, "demand": 0.4}
        ]
        
        budget = 1000000
        
        portfolio = sourcing_engine.optimize_portfolio(products, budget)
        
        assert sum(p["allocation"] for p in portfolio) <= budget
        assert all(p["allocation"] >= 0 for p in portfolio)
        # 위험 대비 수익이 좋은 상품에 더 많이 할당되어야 함
    
    def test_sourcing_decision_making(self, sourcing_engine):
        """소싱 의사결정 테스트"""
        product_analysis = {
            "potential_score": 75,
            "risk_level": "medium",
            "profit_margin": 0.35,
            "market_demand": "high"
        }
        
        decision = sourcing_engine.make_sourcing_decision(product_analysis)
        
        assert decision["recommendation"] in ["source", "skip", "review"]
        assert "confidence" in decision
        assert "reasons" in decision
        
        # 높은 수요와 적절한 마진이면 소싱 추천
        if product_analysis["market_demand"] == "high" and product_analysis["profit_margin"] > 0.3:
            assert decision["recommendation"] == "source"


class TestIntegrationScenarios:
    """통합 시나리오 테스트"""
    
    def test_end_to_end_sourcing_flow(self):
        """전체 소싱 플로우 테스트"""
        # 1. 마켓 데이터 수집
        market_collector = MarketDataCollector()
        with patch.object(market_collector, 'collect_all_platforms') as mock_collect:
            mock_collect.return_value = [
                {"name": "트렌드상품", "sales": 1000, "price": 30000}
            ]
            market_data = market_collector.collect_all_platforms()
        
        # 2. 트렌드 분석
        trend_analyzer = TrendAnalyzer()
        with patch.object(trend_analyzer, 'analyze_market_trends') as mock_analyze:
            mock_analyze.return_value = {
                "trending_keywords": ["신상품", "인기"],
                "growth_rate": 0.25
            }
            trends = trend_analyzer.analyze_market_trends(market_data)
        
        # 3. AI 분석
        ai_analyzer = AIProductAnalyzer()
        with patch.object(ai_analyzer, 'analyze_potential') as mock_ai:
            mock_ai.return_value = {
                "potential_score": 80,
                "recommendation": "source"
            }
            ai_analysis = ai_analyzer.analyze_potential(market_data[0])
        
        # 4. 최종 소싱 결정
        sourcing_engine = SmartSourcingEngine()
        final_decision = sourcing_engine.make_final_decision(
            market_data, trends, ai_analysis
        )
        
        assert final_decision is not None
        assert "action" in final_decision
        assert final_decision["action"] in ["source", "skip", "review"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
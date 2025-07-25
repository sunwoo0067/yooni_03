"""
마켓 관리 시스템 유닛 테스트
- API 데이터 수집 테스트
- 상품 순환 등록 테스트
- 딥러닝 예측 모델 테스트
- 리뷰 감성 분석 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import List, Dict, Any

from app.services.analytics.sales_data_collector import SalesDataCollector
from app.services.analytics.performance_analyzer import PerformanceAnalyzer
from app.services.queue.registration_scheduler import RegistrationScheduler
from app.services.prediction.demand_analyzer import DemandAnalyzer
from app.services.prediction.stockout_predictor import StockoutPredictor
from app.services.ai.ai_manager import AIManager


class TestSalesDataCollector:
    """판매 데이터 수집기 테스트"""
    
    @pytest.fixture
    def sales_collector(self):
        return SalesDataCollector()
    
    @patch('app.services.platforms.coupang_api.CoupangAPI')
    def test_collect_coupang_sales_data(self, mock_coupang, sales_collector):
        """쿠팡 판매 데이터 수집 테스트"""
        mock_api = Mock()
        mock_api.get_sales_data.return_value = {
            "sales": [
                {
                    "date": "2025-01-25",
                    "productId": "CP123",
                    "quantity": 10,
                    "revenue": 300000,
                    "views": 500,
                    "conversions": 10
                }
            ],
            "total": 1
        }
        mock_coupang.return_value = mock_api
        
        sales_data = sales_collector.collect_platform_sales("coupang", 
                                                           start_date="2025-01-25",
                                                           end_date="2025-01-25")
        
        assert len(sales_data["sales"]) == 1
        assert sales_data["sales"][0]["productId"] == "CP123"
        assert sales_data["sales"][0]["conversion_rate"] == 0.02  # 10/500
    
    def test_aggregate_multi_platform_sales(self, sales_collector):
        """멀티플랫폼 판매 데이터 집계 테스트"""
        platform_data = {
            "coupang": [
                {"productId": "P1", "date": "2025-01-25", "quantity": 10, "revenue": 100000}
            ],
            "naver": [
                {"productId": "P1", "date": "2025-01-25", "quantity": 5, "revenue": 50000}
            ],
            "11st": [
                {"productId": "P1", "date": "2025-01-25", "quantity": 3, "revenue": 30000}
            ]
        }
        
        aggregated = sales_collector.aggregate_sales_data(platform_data)
        
        assert aggregated["P1"]["total_quantity"] == 18
        assert aggregated["P1"]["total_revenue"] == 180000
        assert aggregated["P1"]["platforms"] == 3
        assert aggregated["P1"]["best_platform"] == "coupang"
    
    def test_calculate_sales_metrics(self, sales_collector):
        """판매 지표 계산 테스트"""
        sales_history = [
            {"date": "2025-01-20", "quantity": 10, "revenue": 100000},
            {"date": "2025-01-21", "quantity": 12, "revenue": 120000},
            {"date": "2025-01-22", "quantity": 8, "revenue": 80000},
            {"date": "2025-01-23", "quantity": 15, "revenue": 150000},
            {"date": "2025-01-24", "quantity": 20, "revenue": 200000}
        ]
        
        metrics = sales_collector.calculate_metrics(sales_history)
        
        assert metrics["avg_daily_quantity"] == 13
        assert metrics["avg_daily_revenue"] == 130000
        assert metrics["growth_rate"] > 0  # 증가 추세
        assert metrics["volatility"] > 0  # 변동성 존재
    
    def test_identify_top_performers(self, sales_collector):
        """상위 성과 상품 식별 테스트"""
        products_data = [
            {"id": "P1", "revenue": 500000, "quantity": 50, "margin": 0.3},
            {"id": "P2", "revenue": 300000, "quantity": 100, "margin": 0.15},
            {"id": "P3", "revenue": 800000, "quantity": 40, "margin": 0.4},
            {"id": "P4", "revenue": 200000, "quantity": 30, "margin": 0.25}
        ]
        
        top_by_revenue = sales_collector.get_top_performers(products_data, 
                                                           metric="revenue", 
                                                           top_n=2)
        
        assert len(top_by_revenue) == 2
        assert top_by_revenue[0]["id"] == "P3"
        assert top_by_revenue[1]["id"] == "P1"
        
        top_by_profit = sales_collector.get_top_performers(products_data,
                                                          metric="profit",
                                                          top_n=2)
        
        assert top_by_profit[0]["id"] == "P3"  # 800000 * 0.4 = 320000


class TestRegistrationScheduler:
    """상품 순환 등록 스케줄러 테스트"""
    
    @pytest.fixture
    def scheduler(self):
        return RegistrationScheduler()
    
    def test_create_rotation_schedule(self, scheduler):
        """순환 등록 스케줄 생성 테스트"""
        products = [
            {"id": f"P{i}", "category": "의류" if i % 2 == 0 else "전자"}
            for i in range(10)
        ]
        
        platforms = ["coupang", "naver", "11st"]
        daily_limit = 20  # 플랫폼당 일일 등록 한도
        
        schedule = scheduler.create_rotation_schedule(products, platforms, daily_limit)
        
        # 모든 상품이 스케줄에 포함되어야 함
        scheduled_products = set()
        for day_schedule in schedule.values():
            for platform_products in day_schedule.values():
                scheduled_products.update(p["id"] for p in platform_products)
        
        assert len(scheduled_products) == 10
        
        # 일일 한도를 초과하지 않아야 함
        for day_schedule in schedule.values():
            for platform, products in day_schedule.items():
                assert len(products) <= daily_limit
    
    def test_optimize_registration_timing(self, scheduler):
        """등록 시간 최적화 테스트"""
        historical_data = {
            "coupang": {
                "best_hours": [10, 14, 20],  # 오전 10시, 오후 2시, 저녁 8시
                "worst_hours": [3, 4, 5]      # 새벽 시간
            },
            "naver": {
                "best_hours": [11, 15, 19],
                "worst_hours": [2, 3, 4]
            }
        }
        
        optimal_times = scheduler.get_optimal_registration_times(historical_data)
        
        assert "coupang" in optimal_times
        assert 10 in optimal_times["coupang"]
        assert 3 not in optimal_times["coupang"]
    
    def test_handle_registration_conflicts(self, scheduler):
        """등록 충돌 처리 테스트"""
        existing_products = {
            "coupang": ["P1", "P2"],
            "naver": ["P1", "P3"],
            "11st": ["P2", "P3"]
        }
        
        new_products = ["P1", "P2", "P3", "P4", "P5"]
        
        conflict_free_schedule = scheduler.resolve_conflicts(new_products, 
                                                           existing_products)
        
        # P1은 coupang과 naver에 이미 있으므로 11st에만 등록
        assert "P1" in conflict_free_schedule["11st"]
        assert "P1" not in conflict_free_schedule["coupang"]
        assert "P1" not in conflict_free_schedule["naver"]
        
        # P4, P5는 어디에도 없으므로 모든 플랫폼에 등록 가능
        for platform in ["coupang", "naver", "11st"]:
            assert any(p in ["P4", "P5"] for p in conflict_free_schedule[platform])
    
    @pytest.mark.asyncio
    async def test_auto_schedule_execution(self, scheduler):
        """자동 스케줄 실행 테스트"""
        mock_registration_func = Mock(return_value={"status": "success"})
        
        schedule = {
            datetime.now(): {
                "coupang": [{"id": "P1"}, {"id": "P2"}],
                "naver": [{"id": "P3"}]
            }
        }
        
        await scheduler.execute_schedule(schedule, mock_registration_func)
        
        # 총 3개의 상품이 등록되어야 함
        assert mock_registration_func.call_count == 3


class TestDemandAnalyzer:
    """수요 분석기 테스트"""
    
    @pytest.fixture
    def demand_analyzer(self):
        return DemandAnalyzer()
    
    def test_analyze_seasonal_demand(self, demand_analyzer):
        """계절별 수요 분석 테스트"""
        # 계절성이 있는 판매 데이터 생성
        sales_data = []
        for month in range(1, 13):
            # 여름(6-8월)에 높은 판매량
            if 6 <= month <= 8:
                base_sales = 100
            else:
                base_sales = 50
            
            sales_data.append({
                "month": month,
                "sales": base_sales + np.random.randint(-10, 10)
            })
        
        seasonality = demand_analyzer.analyze_seasonality(sales_data)
        
        assert seasonality["has_seasonality"] == True
        assert seasonality["peak_months"] == [6, 7, 8]
        assert seasonality["seasonality_strength"] > 0.5
    
    def test_predict_future_demand(self, demand_analyzer):
        """미래 수요 예측 테스트"""
        # 과거 30일 데이터
        historical_sales = []
        for i in range(30):
            date = datetime.now() - timedelta(days=30-i)
            sales = 50 + i * 2 + np.random.randint(-5, 5)  # 상승 트렌드
            historical_sales.append({
                "date": date,
                "sales": sales
            })
        
        predictions = demand_analyzer.predict_demand(historical_sales, days=7)
        
        assert len(predictions) == 7
        # 상승 트렌드이므로 예측값이 마지막 실제값보다 높아야 함
        assert predictions[-1]["predicted_sales"] > historical_sales[-1]["sales"]
        assert all("confidence_interval" in p for p in predictions)
    
    def test_identify_demand_drivers(self, demand_analyzer):
        """수요 동인 식별 테스트"""
        product_data = {
            "sales_history": [100, 120, 90, 150, 200],
            "price_history": [30000, 28000, 32000, 25000, 25000],
            "promotion_history": [False, True, False, True, True],
            "competitor_prices": [31000, 29000, 31000, 28000, 27000]
        }
        
        drivers = demand_analyzer.identify_drivers(product_data)
        
        assert "price_elasticity" in drivers
        assert drivers["price_elasticity"] < 0  # 가격이 낮을수록 수요 증가
        assert "promotion_impact" in drivers
        assert drivers["promotion_impact"] > 0  # 프로모션이 수요에 긍정적 영향
    
    def test_demand_forecasting_accuracy(self, demand_analyzer):
        """수요 예측 정확도 테스트"""
        # 실제값과 예측값
        actual = [100, 110, 105, 120, 115]
        predicted = [98, 112, 103, 118, 117]
        
        accuracy_metrics = demand_analyzer.calculate_accuracy(actual, predicted)
        
        assert "mape" in accuracy_metrics  # Mean Absolute Percentage Error
        assert "rmse" in accuracy_metrics  # Root Mean Square Error
        assert accuracy_metrics["mape"] < 0.05  # 5% 이내 오차
        assert accuracy_metrics["accuracy"] > 0.95  # 95% 이상 정확도


class TestStockoutPredictor:
    """재고 소진 예측기 테스트"""
    
    @pytest.fixture
    def stockout_predictor(self):
        return StockoutPredictor()
    
    def test_predict_stockout_date(self, stockout_predictor):
        """재고 소진일 예측 테스트"""
        inventory_data = {
            "current_stock": 100,
            "daily_sales_avg": 10,
            "daily_sales_std": 2,
            "lead_time_days": 3
        }
        
        prediction = stockout_predictor.predict_stockout(inventory_data)
        
        assert "estimated_stockout_date" in prediction
        assert "days_until_stockout" in prediction
        assert prediction["days_until_stockout"] == 10  # 100 / 10
        assert "reorder_point" in prediction
        assert prediction["reorder_point"] == 30  # 10 * 3 (lead time)
    
    def test_calculate_safety_stock(self, stockout_predictor):
        """안전재고 계산 테스트"""
        demand_variability = {
            "daily_avg": 20,
            "daily_std": 5,
            "lead_time_days": 5,
            "service_level": 0.95  # 95% 서비스 수준
        }
        
        safety_stock = stockout_predictor.calculate_safety_stock(demand_variability)
        
        assert safety_stock > 0
        # z-score(0.95) * sqrt(lead_time) * daily_std
        expected = 1.645 * np.sqrt(5) * 5
        assert abs(safety_stock - expected) < 1
    
    def test_stockout_risk_assessment(self, stockout_predictor):
        """재고 소진 위험 평가 테스트"""
        products = [
            {
                "id": "P1",
                "stock": 10,
                "daily_sales": 5,
                "importance": "high"
            },
            {
                "id": "P2",
                "stock": 100,
                "daily_sales": 2,
                "importance": "low"
            },
            {
                "id": "P3",
                "stock": 5,
                "daily_sales": 10,
                "importance": "high"
            }
        ]
        
        risk_assessment = stockout_predictor.assess_risk(products)
        
        # P3가 가장 위험 (0.5일 만에 소진 + 중요도 높음)
        assert risk_assessment[0]["id"] == "P3"
        assert risk_assessment[0]["risk_level"] == "critical"
        
        # P2가 가장 안전 (50일 재고 + 중요도 낮음)
        assert risk_assessment[-1]["id"] == "P2"
        assert risk_assessment[-1]["risk_level"] == "low"


class TestReviewSentimentAnalyzer:
    """리뷰 감성 분석기 테스트"""
    
    @pytest.fixture
    def sentiment_analyzer(self):
        return AIManager().get_sentiment_analyzer()
    
    @patch.object(AIManager, 'analyze_sentiment')
    def test_analyze_review_sentiment(self, mock_analyze, sentiment_analyzer):
        """리뷰 감성 분석 테스트"""
        mock_analyze.return_value = {
            "sentiment": "positive",
            "score": 0.85,
            "aspects": {
                "quality": "positive",
                "price": "neutral",
                "delivery": "positive"
            }
        }
        
        review = "품질이 정말 좋아요! 가격은 적당하고 배송도 빨랐습니다."
        
        result = sentiment_analyzer.analyze_review(review)
        
        assert result["sentiment"] == "positive"
        assert result["score"] > 0.8
        assert result["aspects"]["quality"] == "positive"
    
    def test_batch_sentiment_analysis(self, sentiment_analyzer):
        """배치 감성 분석 테스트"""
        reviews = [
            {"id": "R1", "text": "정말 만족스러운 제품입니다!", "rating": 5},
            {"id": "R2", "text": "품질이 별로예요. 실망했습니다.", "rating": 2},
            {"id": "R3", "text": "보통입니다. 가격대비 적당해요.", "rating": 3}
        ]
        
        with patch.object(sentiment_analyzer, 'analyze_review') as mock_analyze:
            mock_analyze.side_effect = [
                {"sentiment": "positive", "score": 0.9},
                {"sentiment": "negative", "score": 0.2},
                {"sentiment": "neutral", "score": 0.5}
            ]
            
            results = sentiment_analyzer.analyze_batch(reviews)
        
        assert len(results) == 3
        assert results[0]["sentiment"] == "positive"
        assert results[1]["sentiment"] == "negative"
        assert results[2]["sentiment"] == "neutral"
    
    def test_extract_improvement_insights(self, sentiment_analyzer):
        """개선 인사이트 추출 테스트"""
        negative_reviews = [
            "배송이 너무 늦어요",
            "포장이 허술해서 제품이 손상됐어요",
            "배송 중에 파손되었습니다",
            "색상이 사진과 달라요",
            "사이즈가 작아요"
        ]
        
        insights = sentiment_analyzer.extract_insights(negative_reviews)
        
        assert "배송" in insights["common_issues"]
        assert insights["common_issues"]["배송"] >= 3
        assert "포장" in insights["improvement_areas"]
        assert len(insights["action_items"]) > 0
    
    def test_sentiment_trend_analysis(self, sentiment_analyzer):
        """감성 트렌드 분석 테스트"""
        historical_sentiments = [
            {"date": "2025-01-20", "positive": 70, "neutral": 20, "negative": 10},
            {"date": "2025-01-21", "positive": 65, "neutral": 20, "negative": 15},
            {"date": "2025-01-22", "positive": 60, "neutral": 25, "negative": 15},
            {"date": "2025-01-23", "positive": 55, "neutral": 25, "negative": 20},
            {"date": "2025-01-24", "positive": 50, "neutral": 30, "negative": 20}
        ]
        
        trend = sentiment_analyzer.analyze_trend(historical_sentiments)
        
        assert trend["overall_trend"] == "declining"  # 긍정 비율 감소
        assert trend["alert_level"] == "warning"  # 부정 비율 증가
        assert "action_required" in trend


class TestMarketOptimization:
    """마켓 최적화 통합 테스트"""
    
    def test_integrated_market_optimization(self):
        """통합 마켓 최적화 테스트"""
        # 1. 판매 데이터 수집
        sales_collector = SalesDataCollector()
        with patch.object(sales_collector, 'collect_all_platforms') as mock_collect:
            mock_collect.return_value = {
                "P1": {"quantity": 100, "revenue": 1000000},
                "P2": {"quantity": 50, "revenue": 750000}
            }
            sales_data = sales_collector.collect_all_platforms()
        
        # 2. 수요 예측
        demand_analyzer = DemandAnalyzer()
        with patch.object(demand_analyzer, 'predict_demand') as mock_predict:
            mock_predict.return_value = [
                {"product": "P1", "predicted_demand": 120},
                {"product": "P2", "predicted_demand": 40}
            ]
            demand_forecast = demand_analyzer.predict_demand(sales_data)
        
        # 3. 재고 관리
        stockout_predictor = StockoutPredictor()
        with patch.object(stockout_predictor, 'assess_risk') as mock_assess:
            mock_assess.return_value = [
                {"product": "P1", "risk": "high", "action": "reorder"},
                {"product": "P2", "risk": "low", "action": "monitor"}
            ]
            stock_assessment = stockout_predictor.assess_risk(demand_forecast)
        
        # 4. 등록 스케줄 최적화
        scheduler = RegistrationScheduler()
        optimization_result = scheduler.optimize_based_on_performance(
            sales_data, demand_forecast, stock_assessment
        )
        
        assert optimization_result is not None
        assert "P1" in optimization_result["priority_products"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
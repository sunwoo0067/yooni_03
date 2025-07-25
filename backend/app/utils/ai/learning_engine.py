"""Machine learning engine for continuous improvement."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass, asdict
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class SalesData:
    """판매 데이터 구조"""
    product_id: str
    timestamp: datetime
    quantity: int
    price: float
    category: str
    keywords: List[str]
    platform: str
    promotion: bool
    season: str
    day_of_week: int
    hour_of_day: int


@dataclass
class PredictionResult:
    """예측 결과"""
    predicted_sales: float
    confidence_interval: Tuple[float, float]
    feature_importance: Dict[str, float]
    recommendation: str


class LearningEngine:
    """
    머신러닝 학습 엔진
    - 판매 데이터 자동 수집 및 학습
    - 패턴 인식 및 예측
    - 지속적인 모델 개선
    - A/B 테스트 분석
    """
    
    def __init__(self, model_dir: str = "backend/ml_models"):
        """Initialize learning engine."""
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # 모델 저장 경로
        self.sales_model_path = os.path.join(model_dir, "sales_predictor.pkl")
        self.price_model_path = os.path.join(model_dir, "price_optimizer.pkl")
        self.keyword_model_path = os.path.join(model_dir, "keyword_scorer.pkl")
        
        # 모델 초기화
        self.sales_predictor = None
        self.price_optimizer = None
        self.keyword_scorer = None
        
        # 스케일러
        self.scaler = StandardScaler()
        
        # 학습 데이터 버퍼
        self.training_buffer = []
        self.buffer_size = 1000
        
        # 성능 메트릭
        self.model_metrics = {
            "sales_predictor": {"mae": None, "r2": None},
            "price_optimizer": {"mae": None, "r2": None},
            "keyword_scorer": {"accuracy": None}
        }
        
        # 모델 로드
        self._load_models()
        
        logger.info("Learning Engine initialized")
    
    def _load_models(self):
        """저장된 모델 로드"""
        try:
            if os.path.exists(self.sales_model_path):
                self.sales_predictor = joblib.load(self.sales_model_path)
                logger.info("Sales predictor model loaded")
            
            if os.path.exists(self.price_model_path):
                self.price_optimizer = joblib.load(self.price_model_path)
                logger.info("Price optimizer model loaded")
            
            if os.path.exists(self.keyword_model_path):
                self.keyword_scorer = joblib.load(self.keyword_model_path)
                logger.info("Keyword scorer model loaded")
                
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
    
    async def add_sales_data(self, sales_data: SalesData):
        """판매 데이터 추가"""
        self.training_buffer.append(sales_data)
        
        # 버퍼가 가득 차면 학습 실행
        if len(self.training_buffer) >= self.buffer_size:
            await self.train_models()
    
    def prepare_features(self, data: List[SalesData]) -> Tuple[np.ndarray, np.ndarray]:
        """특징 추출 및 전처리"""
        features = []
        targets = []
        
        for item in data:
            # 특징 추출
            feature_vector = [
                item.price,
                len(item.keywords),
                1 if item.promotion else 0,
                item.day_of_week,
                item.hour_of_day,
                self._encode_season(item.season),
                self._encode_platform(item.platform),
                self._encode_category(item.category)
            ]
            
            features.append(feature_vector)
            targets.append(item.quantity)
        
        X = np.array(features)
        y = np.array(targets)
        
        # 스케일링
        X = self.scaler.fit_transform(X)
        
        return X, y
    
    async def train_models(self):
        """모든 모델 학습"""
        if len(self.training_buffer) < 100:
            logger.warning("Not enough data for training")
            return
        
        logger.info("Starting model training...")
        
        # 데이터 준비
        X, y = self.prepare_features(self.training_buffer)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 판매량 예측 모델
        await self._train_sales_predictor(X_train, y_train, X_test, y_test)
        
        # 가격 최적화 모델
        await self._train_price_optimizer(X_train, y_train, X_test, y_test)
        
        # 키워드 점수 모델
        await self._train_keyword_scorer()
        
        # 버퍼 초기화
        self.training_buffer = []
        
        logger.info("Model training completed")
    
    async def _train_sales_predictor(self, X_train, y_train, X_test, y_test):
        """판매량 예측 모델 학습"""
        try:
            # Random Forest 모델
            self.sales_predictor = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            # 학습
            await asyncio.to_thread(
                self.sales_predictor.fit, X_train, y_train
            )
            
            # 평가
            y_pred = self.sales_predictor.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            self.model_metrics["sales_predictor"] = {
                "mae": mae,
                "r2": r2
            }
            
            # 모델 저장
            joblib.dump(self.sales_predictor, self.sales_model_path)
            
            logger.info(f"Sales predictor trained - MAE: {mae:.2f}, R2: {r2:.2f}")
            
        except Exception as e:
            logger.error(f"Sales predictor training failed: {e}")
    
    async def _train_price_optimizer(self, X_train, y_train, X_test, y_test):
        """가격 최적화 모델 학습"""
        try:
            # Gradient Boosting 모델
            self.price_optimizer = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            
            # 가격과 판매량의 관계 학습
            # X_train의 첫 번째 열이 가격
            price_train = X_train[:, 0].reshape(-1, 1)
            
            await asyncio.to_thread(
                self.price_optimizer.fit, price_train, y_train
            )
            
            # 평가
            price_test = X_test[:, 0].reshape(-1, 1)
            y_pred = self.price_optimizer.predict(price_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            self.model_metrics["price_optimizer"] = {
                "mae": mae,
                "r2": r2
            }
            
            # 모델 저장
            joblib.dump(self.price_optimizer, self.price_model_path)
            
            logger.info(f"Price optimizer trained - MAE: {mae:.2f}, R2: {r2:.2f}")
            
        except Exception as e:
            logger.error(f"Price optimizer training failed: {e}")
    
    async def _train_keyword_scorer(self):
        """키워드 점수 모델 학습"""
        try:
            # 키워드별 판매량 집계
            keyword_sales = {}
            
            for item in self.training_buffer:
                for keyword in item.keywords:
                    if keyword not in keyword_sales:
                        keyword_sales[keyword] = []
                    keyword_sales[keyword].append(item.quantity)
            
            # 키워드 점수 계산 (평균 판매량)
            keyword_scores = {
                keyword: np.mean(sales) 
                for keyword, sales in keyword_sales.items()
            }
            
            # 점수 정규화 (0-100)
            max_score = max(keyword_scores.values()) if keyword_scores else 1
            keyword_scores = {
                k: (v / max_score) * 100 
                for k, v in keyword_scores.items()
            }
            
            self.keyword_scorer = keyword_scores
            
            # 저장
            joblib.dump(self.keyword_scorer, self.keyword_model_path)
            
            logger.info(f"Keyword scorer trained - {len(keyword_scores)} keywords")
            
        except Exception as e:
            logger.error(f"Keyword scorer training failed: {e}")
    
    async def predict_sales(self,
                          product_info: Dict[str, Any],
                          future_days: int = 7) -> List[PredictionResult]:
        """판매량 예측"""
        if not self.sales_predictor:
            return [PredictionResult(
                predicted_sales=0,
                confidence_interval=(0, 0),
                feature_importance={},
                recommendation="모델이 아직 학습되지 않았습니다."
            )]
        
        predictions = []
        current_date = datetime.now()
        
        for day in range(future_days):
            target_date = current_date + timedelta(days=day)
            
            # 특징 생성
            features = self._create_prediction_features(
                product_info, target_date
            )
            
            # 예측
            X = self.scaler.transform([features])
            predicted = self.sales_predictor.predict(X)[0]
            
            # 신뢰 구간 (Random Forest의 경우 각 트리의 예측값 사용)
            tree_predictions = [
                tree.predict(X)[0] 
                for tree in self.sales_predictor.estimators_
            ]
            ci_lower = np.percentile(tree_predictions, 5)
            ci_upper = np.percentile(tree_predictions, 95)
            
            # 특징 중요도
            feature_importance = self._get_feature_importance()
            
            # 추천사항 생성
            recommendation = self._generate_recommendation(
                predicted, feature_importance
            )
            
            predictions.append(PredictionResult(
                predicted_sales=predicted,
                confidence_interval=(ci_lower, ci_upper),
                feature_importance=feature_importance,
                recommendation=recommendation
            ))
        
        return predictions
    
    async def optimize_price(self,
                           product_info: Dict[str, Any],
                           cost: float,
                           target_margin: float = 0.3) -> Dict[str, Any]:
        """최적 가격 찾기"""
        if not self.price_optimizer:
            return {
                "optimal_price": cost * (1 + target_margin),
                "expected_sales": 0,
                "recommendation": "모델이 아직 학습되지 않았습니다."
            }
        
        # 가격 범위 설정
        min_price = cost * (1 + target_margin * 0.5)
        max_price = cost * (1 + target_margin * 2)
        price_range = np.linspace(min_price, max_price, 50)
        
        # 각 가격에서의 예상 판매량
        sales_predictions = []
        revenue_predictions = []
        
        for price in price_range:
            X = np.array([[price]])
            predicted_sales = self.price_optimizer.predict(X)[0]
            predicted_revenue = price * predicted_sales
            
            sales_predictions.append(predicted_sales)
            revenue_predictions.append(predicted_revenue)
        
        # 최적 가격 찾기 (수익 최대화)
        optimal_idx = np.argmax(revenue_predictions)
        optimal_price = price_range[optimal_idx]
        optimal_sales = sales_predictions[optimal_idx]
        optimal_revenue = revenue_predictions[optimal_idx]
        
        return {
            "optimal_price": optimal_price,
            "expected_sales": optimal_sales,
            "expected_revenue": optimal_revenue,
            "margin": (optimal_price - cost) / optimal_price,
            "price_elasticity": self._calculate_price_elasticity(
                price_range, sales_predictions
            ),
            "recommendation": self._generate_price_recommendation(
                optimal_price, cost, target_margin
            )
        }
    
    def score_keywords(self, keywords: List[str]) -> Dict[str, float]:
        """키워드 점수 계산"""
        if not self.keyword_scorer:
            return {k: 50.0 for k in keywords}  # 기본 점수
        
        scores = {}
        for keyword in keywords:
            if keyword in self.keyword_scorer:
                scores[keyword] = self.keyword_scorer[keyword]
            else:
                # 새로운 키워드는 평균 점수
                scores[keyword] = 50.0
        
        return scores
    
    async def analyze_ab_test(self,
                            variant_a_data: List[SalesData],
                            variant_b_data: List[SalesData]) -> Dict[str, Any]:
        """A/B 테스트 분석"""
        # 기본 통계
        a_sales = [item.quantity for item in variant_a_data]
        b_sales = [item.quantity for item in variant_b_data]
        
        a_mean = np.mean(a_sales) if a_sales else 0
        b_mean = np.mean(b_sales) if b_sales else 0
        
        # 통계적 유의성 검정
        from scipy import stats
        if len(a_sales) > 1 and len(b_sales) > 1:
            t_stat, p_value = stats.ttest_ind(a_sales, b_sales)
            significant = p_value < 0.05
        else:
            t_stat, p_value = 0, 1
            significant = False
        
        # 개선율 계산
        improvement = ((b_mean - a_mean) / a_mean * 100) if a_mean > 0 else 0
        
        # 신뢰도 계산
        confidence = (1 - p_value) * 100
        
        return {
            "variant_a": {
                "mean_sales": a_mean,
                "total_sales": sum(a_sales),
                "sample_size": len(a_sales)
            },
            "variant_b": {
                "mean_sales": b_mean,
                "total_sales": sum(b_sales),
                "sample_size": len(b_sales)
            },
            "improvement_percent": improvement,
            "p_value": p_value,
            "significant": significant,
            "confidence_percent": confidence,
            "recommendation": self._generate_ab_recommendation(
                improvement, significant, confidence
            )
        }
    
    def _create_prediction_features(self, 
                                  product_info: Dict[str, Any],
                                  target_date: datetime) -> List[float]:
        """예측을 위한 특징 생성"""
        return [
            product_info.get("price", 0),
            len(product_info.get("keywords", [])),
            1 if product_info.get("promotion", False) else 0,
            target_date.weekday(),
            12,  # 기본 시간 (정오)
            self._encode_season(self._get_season(target_date)),
            self._encode_platform(product_info.get("platform", "general")),
            self._encode_category(product_info.get("category", "general"))
        ]
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """특징 중요도 반환"""
        if not self.sales_predictor or not hasattr(self.sales_predictor, 'feature_importances_'):
            return {}
        
        feature_names = [
            "price", "keyword_count", "promotion", "day_of_week",
            "hour_of_day", "season", "platform", "category"
        ]
        
        importances = self.sales_predictor.feature_importances_
        
        return {
            name: float(importance) 
            for name, importance in zip(feature_names, importances)
        }
    
    def _calculate_price_elasticity(self, 
                                  prices: np.ndarray, 
                                  quantities: List[float]) -> float:
        """가격 탄력성 계산"""
        if len(prices) < 2:
            return 0
        
        # 로그 변환 후 선형 회귀
        log_prices = np.log(prices)
        log_quantities = np.log(np.maximum(quantities, 1))  # 0 방지
        
        # 기울기가 탄력성
        elasticity = np.polyfit(log_prices, log_quantities, 1)[0]
        
        return float(elasticity)
    
    def _encode_season(self, season: str) -> float:
        """계절 인코딩"""
        season_map = {
            "spring": 0, "summer": 1, "fall": 2, "winter": 3
        }
        return season_map.get(season.lower(), 0)
    
    def _encode_platform(self, platform: str) -> float:
        """플랫폼 인코딩"""
        platform_map = {
            "coupang": 0, "naver": 1, "gmarket": 2, "11st": 3, "general": 4
        }
        return platform_map.get(platform.lower(), 4)
    
    def _encode_category(self, category: str) -> float:
        """카테고리 인코딩 (해시 기반)"""
        return hash(category) % 100
    
    def _get_season(self, date: datetime) -> str:
        """날짜로부터 계절 추출"""
        month = date.month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        else:
            return "winter"
    
    def _generate_recommendation(self, 
                               predicted_sales: float,
                               feature_importance: Dict[str, float]) -> str:
        """예측 기반 추천사항 생성"""
        recommendations = []
        
        # 가장 중요한 특징 찾기
        if feature_importance:
            top_feature = max(feature_importance, key=feature_importance.get)
            
            if top_feature == "price":
                recommendations.append("가격이 판매량에 가장 큰 영향을 미칩니다.")
            elif top_feature == "promotion":
                recommendations.append("프로모션 진행 시 판매량이 크게 증가합니다.")
            elif top_feature == "keyword_count":
                recommendations.append("키워드 최적화가 중요합니다.")
        
        # 판매량 수준에 따른 추천
        if predicted_sales < 10:
            recommendations.append("판매량이 낮을 것으로 예상됩니다. 마케팅 강화가 필요합니다.")
        elif predicted_sales > 100:
            recommendations.append("높은 판매량이 예상됩니다. 충분한 재고를 확보하세요.")
        
        return " ".join(recommendations)
    
    def _generate_price_recommendation(self,
                                     optimal_price: float,
                                     cost: float,
                                     target_margin: float) -> str:
        """가격 최적화 추천사항"""
        actual_margin = (optimal_price - cost) / optimal_price
        
        if actual_margin < target_margin:
            return f"목표 마진({target_margin:.1%})보다 낮지만, 판매량 극대화를 위한 최적 가격입니다."
        else:
            return f"목표 마진을 달성하면서 수익을 최대화하는 가격입니다."
    
    def _generate_ab_recommendation(self,
                                  improvement: float,
                                  significant: bool,
                                  confidence: float) -> str:
        """A/B 테스트 추천사항"""
        if not significant:
            return "통계적으로 유의미한 차이가 없습니다. 더 많은 데이터가 필요합니다."
        
        if improvement > 10:
            return f"B안이 {improvement:.1f}% 개선되었습니다. B안 채택을 권장합니다."
        elif improvement < -10:
            return f"A안이 더 우수합니다. A안 유지를 권장합니다."
        else:
            return "두 안의 차이가 크지 않습니다. 다른 요소를 고려하여 결정하세요."
    
    def get_model_performance(self) -> Dict[str, Any]:
        """모델 성능 메트릭 반환"""
        return {
            "models": self.model_metrics,
            "training_data_size": len(self.training_buffer),
            "last_training": datetime.utcnow().isoformat(),
            "status": "active" if any([
                self.sales_predictor,
                self.price_optimizer,
                self.keyword_scorer
            ]) else "not_trained"
        }
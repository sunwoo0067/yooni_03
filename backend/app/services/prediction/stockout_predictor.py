"""
드롭쉬핑 품절 예측 AI 모델

판매 속도, 재고 변화, 시장 트렌드를 분석하여
품절 시점을 예측하고 사전 대응 가능하도록 지원
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from app.services.database.database import get_db


class PredictionConfidence(Enum):
    """예측 신뢰도"""
    VERY_HIGH = "very_high"  # 90% 이상
    HIGH = "high"            # 80-89%
    MEDIUM = "medium"        # 60-79%
    LOW = "low"              # 40-59%
    VERY_LOW = "very_low"    # 40% 미만


@dataclass
class StockoutPrediction:
    """품절 예측 결과"""
    product_id: int
    current_stock: int
    predicted_stockout_date: Optional[datetime]
    days_until_stockout: Optional[int]
    confidence: PredictionConfidence
    confidence_score: float
    predicted_by: str
    factors: Dict[str, float]  # 예측에 영향을 준 요인들
    recommendations: List[str]
    risk_level: str


class StockoutPredictor:
    """품절 예측 모델"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {}
        self.feature_weights = {
            'sales_velocity': 0.35,      # 판매 속도 (35%)
            'stock_trend': 0.25,         # 재고 감소 추세 (25%)
            'seasonal_factor': 0.15,     # 계절성 요인 (15%)
            'market_trend': 0.10,        # 시장 트렌드 (10%)
            'supplier_reliability': 0.10, # 공급업체 신뢰도 (10%)
            'promotion_impact': 0.05     # 프로모션 영향 (5%)
        }
        
    async def predict_stockout(self, product_id: int) -> StockoutPrediction:
        """개별 상품 품절 예측"""
        try:
            self.logger.info(f"품절 예측 시작 - 상품 {product_id}")
            
            # 예측에 필요한 데이터 수집
            features = await self._collect_prediction_features(product_id)
            if not features:
                return self._create_no_data_prediction(product_id)
                
            # 여러 예측 모델 적용
            predictions = {}
            predictions['trend_based'] = await self._trend_based_prediction(features)
            predictions['velocity_based'] = await self._velocity_based_prediction(features)
            predictions['ml_based'] = await self._ml_based_prediction(features)
            
            # 앙상블 예측 결과 생성
            final_prediction = self._ensemble_predictions(product_id, predictions, features)
            
            # 예측 결과 저장
            await self._save_prediction(final_prediction)
            
            self.logger.info(f"품절 예측 완료 - 상품 {product_id}: "
                           f"{final_prediction.days_until_stockout}일 후 품절 예상")
            
            return final_prediction
            
        except Exception as e:
            self.logger.error(f"품절 예측 실패 - 상품 {product_id}: {e}")
            return self._create_error_prediction(product_id, str(e))
            
    async def _collect_prediction_features(self, product_id: int) -> Optional[Dict]:
        """예측 특성 데이터 수집"""
        db = next(get_db())
        try:
            from app.models.product import Product
            from app.models.inventory import Inventory
            from app.models.order import Order
            
            # 기본 상품 정보
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
                
            # 현재 재고
            inventory = db.query(Inventory).filter(Inventory.product_id == product_id).first()
            current_stock = inventory.quantity if inventory else 0
            
            if current_stock <= 0:
                return None  # 이미 품절인 경우
                
            # 판매 데이터 수집 (최근 90일)
            ninety_days_ago = datetime.now() - timedelta(days=90)
            orders = db.query(Order).filter(
                Order.product_id == product_id,
                Order.created_at >= ninety_days_ago,
                Order.status.in_(['completed', 'shipped'])
            ).order_by(Order.created_at).all()
            
            # 재고 변화 데이터 수집
            stock_history = await self._get_stock_history(product_id, 30)
            
            # 공급업체 신뢰도
            supplier_reliability = await self._get_supplier_reliability(product.wholesaler_id)
            
            # 시장 트렌드 데이터
            market_trend = await self._get_market_trend(product.category)
            
            # 계절성 데이터
            seasonal_factor = self._calculate_seasonal_factor(datetime.now(), product.category)
            
            # 프로모션 데이터
            promotion_impact = await self._get_promotion_impact(product_id)
            
            return {
                'product_id': product_id,
                'current_stock': current_stock,
                'orders': orders,
                'stock_history': stock_history,
                'supplier_reliability': supplier_reliability,
                'market_trend': market_trend,
                'seasonal_factor': seasonal_factor,
                'promotion_impact': promotion_impact,
                'category': product.category,
                'price': product.selling_price
            }
            
        finally:
            db.close()
            
    async def _get_stock_history(self, product_id: int, days: int) -> List[Dict]:
        """재고 변화 이력 조회"""
        # 구현 예정: 재고 변화 이력 테이블에서 데이터 조회
        # 임시로 가상 데이터 반환
        history = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            # 가상의 재고 감소 패턴
            stock = max(0, 100 - i * 2)
            history.append({
                'date': date,
                'stock': stock
            })
        return history
        
    async def _get_supplier_reliability(self, wholesaler_id: int) -> float:
        """공급업체 신뢰도 조회"""
        db = next(get_db())
        try:
            from app.models.dropshipping import SupplierReliability
            
            reliability = db.query(SupplierReliability).filter(
                SupplierReliability.supplier_id == wholesaler_id
            ).first()
            
            return reliability.reliability_score / 100 if reliability else 0.7
            
        finally:
            db.close()
            
    async def _get_market_trend(self, category: str) -> float:
        """시장 트렌드 조회"""
        # 구현 예정: 외부 시장 데이터 또는 내부 카테고리별 트렌드 분석
        # 임시로 기본값 반환
        return 1.0
        
    def _calculate_seasonal_factor(self, current_date: datetime, category: str) -> float:
        """계절성 요인 계산"""
        month = current_date.month
        
        # 카테고리별 계절성 패턴
        seasonal_patterns = {
            '의류': {1: 0.8, 2: 0.7, 3: 1.2, 4: 1.3, 5: 1.1, 6: 0.9,
                   7: 0.8, 8: 0.9, 9: 1.2, 10: 1.4, 11: 1.3, 12: 1.1},
            '전자제품': {1: 0.9, 2: 0.8, 3: 1.0, 4: 1.0, 5: 1.1, 6: 1.0,
                     7: 0.9, 8: 1.0, 9: 1.1, 10: 1.2, 11: 1.5, 12: 1.4},
            '생활용품': {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0,
                     7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0}
        }
        
        pattern = seasonal_patterns.get(category, seasonal_patterns['생활용품'])
        return pattern.get(month, 1.0)
        
    async def _get_promotion_impact(self, product_id: int) -> float:
        """프로모션 영향도 조회"""
        # 구현 예정: 현재 진행 중인 프로모션이 판매에 미치는 영향 분석
        return 1.0
        
    async def _trend_based_prediction(self, features: Dict) -> Dict:
        """트렌드 기반 예측"""
        try:
            current_stock = features['current_stock']
            stock_history = features['stock_history']
            
            if len(stock_history) < 7:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 최근 7일간 재고 감소율 계산
            recent_history = stock_history[:7]
            stock_changes = []
            
            for i in range(1, len(recent_history)):
                prev_stock = recent_history[i]['stock']
                curr_stock = recent_history[i-1]['stock']
                change = prev_stock - curr_stock
                stock_changes.append(change)
                
            if not stock_changes:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 평균 일일 재고 감소량
            avg_daily_decrease = np.mean(stock_changes)
            
            if avg_daily_decrease <= 0:
                return {'days_until_stockout': None, 'confidence': 0.5}
                
            # 예상 품절 일수
            days_until_stockout = int(current_stock / avg_daily_decrease)
            
            # 트렌드의 일관성으로 신뢰도 계산
            std_dev = np.std(stock_changes)
            confidence = max(0.3, min(0.9, 1 - (std_dev / max(avg_daily_decrease, 1))))
            
            return {
                'days_until_stockout': days_until_stockout,
                'confidence': confidence,
                'avg_daily_decrease': avg_daily_decrease
            }
            
        except Exception as e:
            self.logger.error(f"트렌드 기반 예측 실패: {e}")
            return {'days_until_stockout': None, 'confidence': 0.2}
            
    async def _velocity_based_prediction(self, features: Dict) -> Dict:
        """판매속도 기반 예측"""
        try:
            current_stock = features['current_stock']
            orders = features['orders']
            seasonal_factor = features['seasonal_factor']
            promotion_impact = features['promotion_impact']
            
            if not orders:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 최근 30일 판매량
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_orders = [o for o in orders if o.created_at >= thirty_days_ago]
            
            if not recent_orders:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 일일 평균 판매량 계산
            daily_sales = len(recent_orders) / 30
            
            # 계절성 및 프로모션 영향 적용
            adjusted_daily_sales = daily_sales * seasonal_factor * promotion_impact
            
            if adjusted_daily_sales <= 0:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 예상 품절 일수
            days_until_stockout = int(current_stock / adjusted_daily_sales)
            
            # 판매 패턴의 일관성으로 신뢰도 계산
            # 최근 7일간 일일 판매량의 분산 계산
            week_sales = []
            for i in range(7):
                day_start = datetime.now() - timedelta(days=i+1)
                day_end = datetime.now() - timedelta(days=i)
                day_orders = [o for o in orders if day_start <= o.created_at < day_end]
                week_sales.append(len(day_orders))
                
            if week_sales:
                sales_std = np.std(week_sales)
                sales_mean = np.mean(week_sales)
                cv = sales_std / max(sales_mean, 1)  # 변동계수
                confidence = max(0.4, min(0.9, 1 - cv))
            else:
                confidence = 0.5
                
            return {
                'days_until_stockout': days_until_stockout,
                'confidence': confidence,
                'daily_sales': adjusted_daily_sales
            }
            
        except Exception as e:
            self.logger.error(f"판매속도 기반 예측 실패: {e}")
            return {'days_until_stockout': None, 'confidence': 0.2}
            
    async def _ml_based_prediction(self, features: Dict) -> Dict:
        """머신러닝 기반 예측"""
        try:
            # 간단한 선형 회귀 모델 (실제 환경에서는 더 복잡한 모델 사용)
            current_stock = features['current_stock']
            orders = features['orders']
            supplier_reliability = features['supplier_reliability']
            market_trend = features['market_trend']
            
            if not orders or len(orders) < 10:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 특성 벡터 생성
            X = []
            y = []
            
            # 과거 데이터로부터 학습 데이터 생성 (간소화된 버전)
            recent_orders = orders[-30:] if len(orders) >= 30 else orders
            
            # 매주 단위로 데이터 분할
            for i in range(0, len(recent_orders) - 7, 7):
                week_orders = recent_orders[i:i+7]
                week_sales = len(week_orders)
                
                # 특성: 주간 판매량, 공급업체 신뢰도, 시장 트렌드
                features_vec = [week_sales, supplier_reliability, market_trend]
                X.append(features_vec)
                
                # 타겟: 다음 주 판매량
                if i + 14 < len(recent_orders):
                    next_week_orders = recent_orders[i+7:i+14]
                    next_week_sales = len(next_week_orders)
                    y.append(next_week_sales)
                    
            if len(X) < 3 or len(y) < 3:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 간단한 평균 기반 예측 (실제로는 scikit-learn 등 사용)
            X = np.array(X)
            y = np.array(y)
            
            # 최근 판매 트렌드 기반 예측
            recent_avg_sales = np.mean(y[-3:]) if len(y) >= 3 else np.mean(y)
            
            if recent_avg_sales <= 0:
                return {'days_until_stockout': None, 'confidence': 0.3}
                
            # 주간 판매량을 일간으로 변환
            daily_predicted_sales = recent_avg_sales / 7
            
            # 예상 품절 일수
            days_until_stockout = int(current_stock / daily_predicted_sales)
            
            # 예측 정확도 추정 (실제로는 교차 검증 등 사용)
            prediction_errors = []
            for i in range(min(3, len(y)-1)):
                predicted = np.mean(y[:-(i+1)])
                actual = y[-(i+1)]
                error = abs(predicted - actual) / max(actual, 1)
                prediction_errors.append(error)
                
            if prediction_errors:
                avg_error = np.mean(prediction_errors)
                confidence = max(0.3, min(0.8, 1 - avg_error))
            else:
                confidence = 0.5
                
            return {
                'days_until_stockout': days_until_stockout,
                'confidence': confidence,
                'predicted_daily_sales': daily_predicted_sales
            }
            
        except Exception as e:
            self.logger.error(f"ML 기반 예측 실패: {e}")
            return {'days_until_stockout': None, 'confidence': 0.2}
            
    def _ensemble_predictions(self, product_id: int, predictions: Dict, features: Dict) -> StockoutPrediction:
        """앙상블 예측 결과 생성"""
        valid_predictions = []
        confidences = []
        methods = []
        
        # 유효한 예측 결과만 수집
        for method, pred in predictions.items():
            if pred.get('days_until_stockout') is not None:
                valid_predictions.append(pred['days_until_stockout'])
                confidences.append(pred['confidence'])
                methods.append(method)
                
        if not valid_predictions:
            return self._create_no_prediction(product_id, features['current_stock'])
            
        # 신뢰도 가중 평균으로 최종 예측
        weights = np.array(confidences)
        weights = weights / np.sum(weights)  # 정규화
        
        final_days = int(np.average(valid_predictions, weights=weights))
        final_confidence_score = np.mean(confidences)
        
        # 예측 일자 계산
        if final_days > 0:
            predicted_date = datetime.now() + timedelta(days=final_days)
        else:
            predicted_date = datetime.now()
            final_days = 0
            
        # 신뢰도 등급 결정
        confidence = self._determine_confidence_level(final_confidence_score)
        
        # 위험 수준 결정
        risk_level = self._determine_risk_level(final_days)
        
        # 영향 요인 분석
        factors = self._analyze_prediction_factors(predictions, features)
        
        # 권장사항 생성
        recommendations = self._generate_recommendations(final_days, risk_level, factors)
        
        return StockoutPrediction(
            product_id=product_id,
            current_stock=features['current_stock'],
            predicted_stockout_date=predicted_date,
            days_until_stockout=final_days,
            confidence=confidence,
            confidence_score=final_confidence_score,
            predicted_by=f"앙상블 ({', '.join(methods)})",
            factors=factors,
            recommendations=recommendations,
            risk_level=risk_level
        )
        
    def _determine_confidence_level(self, score: float) -> PredictionConfidence:
        """신뢰도 등급 결정"""
        if score >= 0.9:
            return PredictionConfidence.VERY_HIGH
        elif score >= 0.8:
            return PredictionConfidence.HIGH
        elif score >= 0.6:
            return PredictionConfidence.MEDIUM
        elif score >= 0.4:
            return PredictionConfidence.LOW
        else:
            return PredictionConfidence.VERY_LOW
            
    def _determine_risk_level(self, days_until_stockout: int) -> str:
        """위험 수준 결정"""
        if days_until_stockout <= 3:
            return "매우 높음"
        elif days_until_stockout <= 7:
            return "높음"
        elif days_until_stockout <= 14:
            return "보통"
        else:
            return "낮음"
            
    def _analyze_prediction_factors(self, predictions: Dict, features: Dict) -> Dict[str, float]:
        """예측 영향 요인 분석"""
        factors = {}
        
        # 판매 속도 영향도
        velocity_pred = predictions.get('velocity_based', {})
        if velocity_pred.get('daily_sales'):
            factors['판매속도'] = min(1.0, velocity_pred['daily_sales'] / 10)
            
        # 재고 감소 트렌드 영향도
        trend_pred = predictions.get('trend_based', {})
        if trend_pred.get('avg_daily_decrease'):
            factors['재고감소트렌드'] = min(1.0, trend_pred['avg_daily_decrease'] / 5)
            
        # 계절성 영향도
        factors['계절성요인'] = features.get('seasonal_factor', 1.0) - 1.0
        
        # 공급업체 신뢰도 영향도
        factors['공급업체신뢰도'] = features.get('supplier_reliability', 0.7)
        
        # 시장 트렌드 영향도
        factors['시장트렌드'] = features.get('market_trend', 1.0) - 1.0
        
        return factors
        
    def _generate_recommendations(self, days_until_stockout: int, risk_level: str, factors: Dict) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if days_until_stockout <= 3:
            recommendations.append("긴급 주문 필요 - 3일 내 품절 예상")
            recommendations.append("대체 상품 준비 권장")
        elif days_until_stockout <= 7:
            recommendations.append("재주문 검토 필요")
            recommendations.append("프로모션 중단 고려")
        elif days_until_stockout <= 14:
            recommendations.append("재고 모니터링 강화")
            
        # 요인별 권장사항
        if factors.get('판매속도', 0) > 0.8:
            recommendations.append("높은 판매속도 - 재주문량 증량 고려")
            
        if factors.get('계절성요인', 0) > 0.2:
            recommendations.append("계절적 수요 증가 - 추가 재고 확보 권장")
            
        if factors.get('공급업체신뢰도', 1.0) < 0.6:
            recommendations.append("공급업체 신뢰도 낮음 - 대체 공급업체 검토")
            
        return recommendations
        
    def _create_no_data_prediction(self, product_id: int) -> StockoutPrediction:
        """데이터 부족 시 기본 예측"""
        return StockoutPrediction(
            product_id=product_id,
            current_stock=0,
            predicted_stockout_date=None,
            days_until_stockout=None,
            confidence=PredictionConfidence.VERY_LOW,
            confidence_score=0.1,
            predicted_by="데이터 부족",
            factors={},
            recommendations=["충분한 판매 데이터 수집 필요"],
            risk_level="알 수 없음"
        )
        
    def _create_no_prediction(self, product_id: int, current_stock: int) -> StockoutPrediction:
        """예측 불가 시 기본 예측"""
        return StockoutPrediction(
            product_id=product_id,
            current_stock=current_stock,
            predicted_stockout_date=None,
            days_until_stockout=None,
            confidence=PredictionConfidence.VERY_LOW,
            confidence_score=0.2,
            predicted_by="예측 불가",
            factors={},
            recommendations=["수동 재고 관리 필요"],
            risk_level="알 수 없음"
        )
        
    def _create_error_prediction(self, product_id: int, error_msg: str) -> StockoutPrediction:
        """오류 시 기본 예측"""
        return StockoutPrediction(
            product_id=product_id,
            current_stock=0,
            predicted_stockout_date=None,
            days_until_stockout=None,
            confidence=PredictionConfidence.VERY_LOW,
            confidence_score=0.0,
            predicted_by=f"오류: {error_msg}",
            factors={},
            recommendations=["시스템 오류 - 수동 확인 필요"],
            risk_level="알 수 없음"
        )
        
    async def _save_prediction(self, prediction: StockoutPrediction):
        """예측 결과 저장"""
        db = next(get_db())
        try:
            from app.models.dropshipping import StockoutPredictionHistory
            
            history = StockoutPredictionHistory(
                product_id=prediction.product_id,
                current_stock=prediction.current_stock,
                predicted_stockout_date=prediction.predicted_stockout_date,
                days_until_stockout=prediction.days_until_stockout,
                confidence_level=prediction.confidence.value,
                confidence_score=prediction.confidence_score,
                predicted_by=prediction.predicted_by,
                risk_level=prediction.risk_level,
                factors=str(prediction.factors),
                recommendations=str(prediction.recommendations),
                predicted_at=datetime.now()
            )
            
            db.add(history)
            db.commit()
            
        finally:
            db.close()
            
    # 배치 예측 메서드
    async def predict_multiple_products(self, product_ids: List[int]) -> List[StockoutPrediction]:
        """여러 상품 품절 예측"""
        predictions = []
        
        for product_id in product_ids:
            try:
                prediction = await self.predict_stockout(product_id)
                predictions.append(prediction)
            except Exception as e:
                self.logger.error(f"상품 {product_id} 예측 실패: {e}")
                error_prediction = self._create_error_prediction(product_id, str(e))
                predictions.append(error_prediction)
                
        return predictions
        
    async def get_high_risk_products(self, days_threshold: int = 7) -> List[StockoutPrediction]:
        """고위험 상품 조회"""
        db = next(get_db())
        try:
            from app.models.product import Product, ProductStatus
            
            # 활성 상품 중 예측이 필요한 상품들
            active_products = db.query(Product).filter(
                Product.status == ProductStatus.ACTIVE,
                Product.is_deleted == False,
                Product.is_dropshipping == True
            ).all()
            
            high_risk_predictions = []
            
            for product in active_products:
                prediction = await self.predict_stockout(product.id)
                
                if (prediction.days_until_stockout is not None and 
                    prediction.days_until_stockout <= days_threshold):
                    high_risk_predictions.append(prediction)
                    
            # 위험도 순으로 정렬
            high_risk_predictions.sort(
                key=lambda x: (x.days_until_stockout or 999, -x.confidence_score)
            )
            
            return high_risk_predictions
            
        finally:
            db.close()
            
    async def get_prediction_accuracy(self, days_back: int = 30) -> Dict:
        """예측 정확도 분석"""
        db = next(get_db())
        try:
            from app.models.dropshipping import StockoutPredictionHistory, OutOfStockHistory
            
            # 과거 예측 결과 조회
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            past_predictions = db.query(StockoutPredictionHistory).filter(
                StockoutPredictionHistory.predicted_at >= cutoff_date,
                StockoutPredictionHistory.predicted_stockout_date.isnot(None)
            ).all()
            
            if not past_predictions:
                return {"error": "분석할 예측 데이터가 없습니다"}
                
            # 실제 품절 이벤트와 비교
            accuracy_results = []
            
            for prediction in past_predictions:
                actual_stockout = db.query(OutOfStockHistory).filter(
                    OutOfStockHistory.product_id == prediction.product_id,
                    OutOfStockHistory.out_of_stock_time >= prediction.predicted_at,
                    OutOfStockHistory.out_of_stock_time <= prediction.predicted_at + timedelta(days=30)
                ).first()
                
                if actual_stockout:
                    # 예측 정확도 계산
                    predicted_date = prediction.predicted_stockout_date
                    actual_date = actual_stockout.out_of_stock_time
                    
                    day_difference = abs((actual_date - predicted_date).days)
                    accuracy = max(0, 1 - (day_difference / 7))  # 7일 오차까지 허용
                    
                    accuracy_results.append({
                        'product_id': prediction.product_id,
                        'predicted_date': predicted_date,
                        'actual_date': actual_date,
                        'day_difference': day_difference,
                        'accuracy': accuracy,
                        'confidence': prediction.confidence_score
                    })
                    
            if not accuracy_results:
                return {"error": "매칭되는 품절 이벤트가 없습니다"}
                
            # 전체 정확도 통계
            overall_accuracy = np.mean([r['accuracy'] for r in accuracy_results])
            avg_day_difference = np.mean([r['day_difference'] for r in accuracy_results])
            
            # 신뢰도별 정확도
            high_confidence = [r for r in accuracy_results if r['confidence'] >= 0.7]
            low_confidence = [r for r in accuracy_results if r['confidence'] < 0.7]
            
            return {
                "analysis_period_days": days_back,
                "total_predictions": len(past_predictions),
                "validated_predictions": len(accuracy_results),
                "overall_accuracy": round(overall_accuracy, 3),
                "avg_day_difference": round(avg_day_difference, 1),
                "high_confidence_accuracy": round(np.mean([r['accuracy'] for r in high_confidence]), 3) if high_confidence else None,
                "low_confidence_accuracy": round(np.mean([r['accuracy'] for r in low_confidence]), 3) if low_confidence else None,
                "accuracy_distribution": {
                    "excellent": len([r for r in accuracy_results if r['accuracy'] >= 0.9]),
                    "good": len([r for r in accuracy_results if 0.7 <= r['accuracy'] < 0.9]),
                    "fair": len([r for r in accuracy_results if 0.5 <= r['accuracy'] < 0.7]),
                    "poor": len([r for r in accuracy_results if r['accuracy'] < 0.5])
                }
            }
            
        finally:
            db.close()
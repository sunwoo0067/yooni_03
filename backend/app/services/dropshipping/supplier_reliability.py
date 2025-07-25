"""
드롭쉬핑 공급업체 신뢰도 분석 서비스

공급업체별 재고 안정성, 품절 빈도, 응답 속도를 분석하여
신뢰도 점수를 산출하고 불안정한 공급업체를 식별
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.services.database.database import get_db


class ReliabilityGrade(Enum):
    """신뢰도 등급"""
    EXCELLENT = "excellent"  # 90-100점
    GOOD = "good"           # 80-89점
    AVERAGE = "average"     # 60-79점
    POOR = "poor"          # 40-59점
    VERY_POOR = "very_poor" # 0-39점


@dataclass
class SupplierMetrics:
    """공급업체 지표"""
    supplier_id: int
    supplier_name: str
    total_products: int
    outofstock_rate: float
    avg_outofstock_duration: float
    response_time_avg: float
    restock_speed_avg: float
    price_stability: float
    reliability_score: float
    grade: ReliabilityGrade
    risk_level: str
    last_analyzed: datetime


@dataclass
class SupplierComparison:
    """공급업체 비교"""
    product_category: str
    suppliers: List[Dict]
    best_supplier: Dict
    recommendations: List[str]


class SupplierReliabilityAnalyzer:
    """공급업체 신뢰도 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analysis_period_days = 90  # 분석 기간: 90일
        
        # 가중치 설정
        self.weights = {
            'outofstock_rate': 0.3,      # 품절률 (30%)
            'outofstock_duration': 0.25, # 품절 지속시간 (25%)
            'response_time': 0.15,       # 응답 속도 (15%)
            'restock_speed': 0.20,       # 재입고 속도 (20%)
            'price_stability': 0.10      # 가격 안정성 (10%)
        }
        
    async def analyze_supplier_reliability(self, supplier_id: int) -> SupplierMetrics:
        """공급업체 신뢰도 분석"""
        db = next(get_db())
        try:
            self.logger.info(f"공급업체 {supplier_id} 신뢰도 분석 시작")
            
            # 기본 정보 조회
            supplier_info = await self._get_supplier_info(db, supplier_id)
            if not supplier_info:
                raise ValueError(f"공급업체를 찾을 수 없습니다: {supplier_id}")
            
            # 각 지표 계산
            metrics = {}
            metrics['outofstock_rate'] = await self._calculate_outofstock_rate(db, supplier_id)
            metrics['avg_outofstock_duration'] = await self._calculate_avg_outofstock_duration(db, supplier_id)
            metrics['response_time_avg'] = await self._calculate_avg_response_time(db, supplier_id)
            metrics['restock_speed_avg'] = await self._calculate_avg_restock_speed(db, supplier_id)
            metrics['price_stability'] = await self._calculate_price_stability(db, supplier_id)
            
            # 신뢰도 점수 계산
            reliability_score = self._calculate_reliability_score(metrics)
            grade = self._determine_grade(reliability_score)
            risk_level = self._determine_risk_level(metrics)
            
            supplier_metrics = SupplierMetrics(
                supplier_id=supplier_id,
                supplier_name=supplier_info['name'],
                total_products=supplier_info['product_count'],
                outofstock_rate=metrics['outofstock_rate'],
                avg_outofstock_duration=metrics['avg_outofstock_duration'],
                response_time_avg=metrics['response_time_avg'],
                restock_speed_avg=metrics['restock_speed_avg'],
                price_stability=metrics['price_stability'],
                reliability_score=reliability_score,
                grade=grade,
                risk_level=risk_level,
                last_analyzed=datetime.now()
            )
            
            # 분석 결과 저장
            await self._save_reliability_analysis(db, supplier_metrics)
            
            self.logger.info(f"공급업체 {supplier_id} 신뢰도 분석 완료 - 점수: {reliability_score:.1f}")
            return supplier_metrics
            
        finally:
            db.close()
            
    async def _get_supplier_info(self, db: Session, supplier_id: int) -> Optional[Dict]:
        """공급업체 기본 정보 조회"""
        from app.models.wholesaler import Wholesaler
        from app.models.product import Product
        
        supplier = db.query(Wholesaler).filter(Wholesaler.id == supplier_id).first()
        if not supplier:
            return None
            
        product_count = db.query(Product).filter(
            Product.wholesaler_id == supplier_id,
            Product.is_deleted == False
        ).count()
        
        return {
            'name': supplier.name,
            'product_count': product_count
        }
        
    async def _calculate_outofstock_rate(self, db: Session, supplier_id: int) -> float:
        """품절률 계산"""
        from app.models.dropshipping import OutOfStockHistory
        from app.models.product import Product
        
        analysis_start = datetime.now() - timedelta(days=self.analysis_period_days)
        
        # 해당 공급업체의 총 상품 수
        total_products = db.query(Product).filter(
            Product.wholesaler_id == supplier_id,
            Product.is_deleted == False
        ).count()
        
        if total_products == 0:
            return 0.0
            
        # 분석 기간 내 품절 이벤트 수
        outofstock_events = db.query(OutOfStockHistory).filter(
            OutOfStockHistory.wholesaler_id == supplier_id,
            OutOfStockHistory.out_of_stock_time >= analysis_start
        ).count()
        
        return (outofstock_events / total_products) * 100
        
    async def _calculate_avg_outofstock_duration(self, db: Session, supplier_id: int) -> float:
        """평균 품절 지속시간 계산 (시간)"""
        from app.models.dropshipping import OutOfStockHistory
        
        analysis_start = datetime.now() - timedelta(days=self.analysis_period_days)
        
        avg_duration = db.query(func.avg(OutOfStockHistory.duration_hours)).filter(
            OutOfStockHistory.wholesaler_id == supplier_id,
            OutOfStockHistory.out_of_stock_time >= analysis_start,
            OutOfStockHistory.duration_hours.isnot(None)
        ).scalar()
        
        return avg_duration or 0.0
        
    async def _calculate_avg_response_time(self, db: Session, supplier_id: int) -> float:
        """평균 응답 시간 계산 (밀리초)"""
        from app.models.dropshipping import StockCheckLog
        
        analysis_start = datetime.now() - timedelta(days=self.analysis_period_days)
        
        avg_response_time = db.query(func.avg(StockCheckLog.response_time_ms)).filter(
            StockCheckLog.wholesaler_id == supplier_id,
            StockCheckLog.check_time >= analysis_start,
            StockCheckLog.response_time_ms.isnot(None)
        ).scalar()
        
        return avg_response_time or 0.0
        
    async def _calculate_avg_restock_speed(self, db: Session, supplier_id: int) -> float:
        """평균 재입고 속도 계산 (시간)"""
        from app.models.dropshipping import OutOfStockHistory
        
        analysis_start = datetime.now() - timedelta(days=self.analysis_period_days)
        
        # 재입고가 완료된 이벤트만 대상
        avg_restock_speed = db.query(func.avg(OutOfStockHistory.duration_hours)).filter(
            OutOfStockHistory.wholesaler_id == supplier_id,
            OutOfStockHistory.out_of_stock_time >= analysis_start,
            OutOfStockHistory.restock_time.isnot(None),
            OutOfStockHistory.duration_hours.isnot(None)
        ).scalar()
        
        return avg_restock_speed or 0.0
        
    async def _calculate_price_stability(self, db: Session, supplier_id: int) -> float:
        """가격 안정성 계산 (변동률의 역수)"""
        from app.models.dropshipping import PriceHistory
        
        analysis_start = datetime.now() - timedelta(days=self.analysis_period_days)
        
        # 가격 변동률 계산
        price_changes = db.query(PriceHistory).filter(
            PriceHistory.wholesaler_id == supplier_id,
            PriceHistory.created_at >= analysis_start
        ).all()
        
        if len(price_changes) < 2:
            return 100.0  # 가격 변동이 없으면 100% 안정
            
        total_variation = 0.0
        count = 0
        
        for i in range(1, len(price_changes)):
            prev_price = price_changes[i-1].price
            curr_price = price_changes[i].price
            
            if prev_price > 0:
                variation = abs(curr_price - prev_price) / prev_price
                total_variation += variation
                count += 1
                
        if count == 0:
            return 100.0
            
        avg_variation = total_variation / count
        stability = max(0, 100 - (avg_variation * 100))
        
        return stability
        
    def _calculate_reliability_score(self, metrics: Dict) -> float:
        """신뢰도 점수 계산 (0-100점)"""
        score = 0.0
        
        # 품절률 점수 (낮을수록 좋음)
        outofstock_score = max(0, 100 - metrics['outofstock_rate'] * 2)
        score += outofstock_score * self.weights['outofstock_rate']
        
        # 품절 지속시간 점수 (짧을수록 좋음, 24시간 기준)
        duration_score = max(0, 100 - (metrics['avg_outofstock_duration'] / 24) * 50)
        score += duration_score * self.weights['outofstock_duration']
        
        # 응답 시간 점수 (빠를수록 좋음, 1초 기준)
        response_score = max(0, 100 - (metrics['response_time_avg'] / 1000) * 20)
        score += response_score * self.weights['response_time']
        
        # 재입고 속도 점수 (빠를수록 좋음, 48시간 기준)
        restock_score = max(0, 100 - (metrics['restock_speed_avg'] / 48) * 50)
        score += restock_score * self.weights['restock_speed']
        
        # 가격 안정성 점수
        price_score = metrics['price_stability']
        score += price_score * self.weights['price_stability']
        
        return min(100, max(0, score))
        
    def _determine_grade(self, score: float) -> ReliabilityGrade:
        """점수에 따른 등급 결정"""
        if score >= 90:
            return ReliabilityGrade.EXCELLENT
        elif score >= 80:
            return ReliabilityGrade.GOOD
        elif score >= 60:
            return ReliabilityGrade.AVERAGE
        elif score >= 40:
            return ReliabilityGrade.POOR
        else:
            return ReliabilityGrade.VERY_POOR
            
    def _determine_risk_level(self, metrics: Dict) -> str:
        """위험 수준 결정"""
        if metrics['outofstock_rate'] > 50:
            return "높음"
        elif metrics['outofstock_rate'] > 20:
            return "보통"
        else:
            return "낮음"
            
    async def _save_reliability_analysis(self, db: Session, metrics: SupplierMetrics):
        """신뢰도 분석 결과 저장"""
        from app.models.dropshipping import SupplierReliability
        
        # 기존 분석 결과 업데이트 또는 새로 생성
        reliability = db.query(SupplierReliability).filter(
            SupplierReliability.supplier_id == metrics.supplier_id
        ).first()
        
        if reliability:
            reliability.outofstock_rate = metrics.outofstock_rate
            reliability.avg_outofstock_duration = metrics.avg_outofstock_duration
            reliability.response_time_avg = metrics.response_time_avg
            reliability.restock_speed_avg = metrics.restock_speed_avg
            reliability.price_stability = metrics.price_stability
            reliability.reliability_score = metrics.reliability_score
            reliability.grade = metrics.grade.value
            reliability.risk_level = metrics.risk_level
            reliability.last_analyzed = metrics.last_analyzed
        else:
            reliability = SupplierReliability(
                supplier_id=metrics.supplier_id,
                outofstock_rate=metrics.outofstock_rate,
                avg_outofstock_duration=metrics.avg_outofstock_duration,
                response_time_avg=metrics.response_time_avg,
                restock_speed_avg=metrics.restock_speed_avg,
                price_stability=metrics.price_stability,
                reliability_score=metrics.reliability_score,
                grade=metrics.grade.value,
                risk_level=metrics.risk_level,
                last_analyzed=metrics.last_analyzed
            )
            db.add(reliability)
            
        db.commit()
        
    async def analyze_all_suppliers(self) -> List[SupplierMetrics]:
        """모든 공급업체 신뢰도 분석"""
        db = next(get_db())
        try:
            from app.models.wholesaler import Wholesaler
            
            suppliers = db.query(Wholesaler).filter(Wholesaler.is_active == True).all()
            results = []
            
            for supplier in suppliers:
                try:
                    metrics = await self.analyze_supplier_reliability(supplier.id)
                    results.append(metrics)
                except Exception as e:
                    self.logger.error(f"공급업체 {supplier.id} 분석 실패: {e}")
                    
            return results
            
        finally:
            db.close()
            
    async def get_supplier_ranking(self, limit: Optional[int] = None) -> List[Dict]:
        """공급업체 신뢰도 순위"""
        db = next(get_db())
        try:
            from app.models.dropshipping import SupplierReliability
            from app.models.wholesaler import Wholesaler
            
            query = db.query(
                SupplierReliability,
                Wholesaler.name
            ).join(
                Wholesaler, SupplierReliability.supplier_id == Wholesaler.id
            ).order_by(SupplierReliability.reliability_score.desc())
            
            if limit:
                query = query.limit(limit)
            
            results = query.all()
            
            ranking = []
            for i, (reliability, supplier_name) in enumerate(results, 1):
                ranking.append({
                    "rank": i,
                    "supplier_id": reliability.supplier_id,
                    "supplier_name": supplier_name,
                    "reliability_score": reliability.reliability_score,
                    "grade": reliability.grade,
                    "risk_level": reliability.risk_level,
                    "outofstock_rate": reliability.outofstock_rate
                })
                
            return ranking
            
        finally:
            db.close()
            
    async def identify_unreliable_suppliers(self, threshold_score: float = 60.0) -> List[Dict]:
        """불안정한 공급업체 식별"""
        db = next(get_db())
        try:
            from app.models.dropshipping import SupplierReliability
            from app.models.wholesaler import Wholesaler
            
            unreliable = db.query(
                SupplierReliability,
                Wholesaler.name
            ).join(
                Wholesaler, SupplierReliability.supplier_id == Wholesaler.id
            ).filter(
                SupplierReliability.reliability_score < threshold_score
            ).order_by(SupplierReliability.reliability_score.asc()).all()
            
            results = []
            for reliability, supplier_name in unreliable:
                results.append({
                    "supplier_id": reliability.supplier_id,
                    "supplier_name": supplier_name,
                    "reliability_score": reliability.reliability_score,
                    "grade": reliability.grade,
                    "outofstock_rate": reliability.outofstock_rate,
                    "avg_outofstock_duration": reliability.avg_outofstock_duration,
                    "risk_level": reliability.risk_level,
                    "recommendations": self._generate_improvement_recommendations(reliability)
                })
                
            return results
            
        finally:
            db.close()
            
    def _generate_improvement_recommendations(self, reliability) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []
        
        if reliability.outofstock_rate > 30:
            recommendations.append("품절률이 높습니다. 재고 관리 개선이 필요합니다.")
            
        if reliability.avg_outofstock_duration > 48:
            recommendations.append("품절 지속시간이 깁니다. 재입고 프로세스 점검이 필요합니다.")
            
        if reliability.response_time_avg > 2000:
            recommendations.append("API 응답시간이 느립니다. 시스템 성능 개선이 필요합니다.")
            
        if reliability.price_stability < 80:
            recommendations.append("가격 변동이 큽니다. 가격 정책 안정화가 필요합니다.")
            
        return recommendations
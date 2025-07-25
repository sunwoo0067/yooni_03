"""
드롭쉬핑 수익 보호 서비스

가격 변동, 품절로 인한 수익 손실 방지
마진 보호, 경쟁력 유지를 위한 자동화 시스템
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from app.services.database.database import get_db
from app.models.product import Product


class ProfitRisk(Enum):
    """수익 위험도"""
    LOW = "low"           # 낮음
    MEDIUM = "medium"     # 보통
    HIGH = "high"         # 높음
    CRITICAL = "critical" # 심각


@dataclass
class ProfitAnalysis:
    """수익 분석 결과"""
    product_id: int
    current_margin: float
    target_margin: float
    margin_gap: float
    risk_level: ProfitRisk
    recommended_action: str
    estimated_loss_per_day: float
    competitor_price_avg: float
    market_position: str


class ProfitProtector:
    """수익 보호 서비스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.analysis_interval = 3600  # 1시간 간격
        
        # 수익 보호 설정
        self.min_margin_rate = 0.15      # 최소 마진율 15%
        self.target_margin_rate = 0.25   # 목표 마진율 25%
        self.max_price_adjustment = 0.10 # 최대 가격 조정 10%
        
    async def start_protection(self):
        """수익 보호 시작"""
        if self.is_running:
            self.logger.warning("수익 보호가 이미 실행 중입니다")
            return
            
        self.is_running = True
        self.logger.info("수익 보호 서비스 시작")
        
        # 백그라운드 태스크로 실행
        asyncio.create_task(self._protection_loop())
        
    async def stop_protection(self):
        """수익 보호 중지"""
        self.is_running = False
        self.logger.info("수익 보호 서비스 중지")
        
    async def _protection_loop(self):
        """수익 보호 루프"""
        while self.is_running:
            try:
                await self._analyze_and_protect_profits()
                await asyncio.sleep(self.analysis_interval)
            except Exception as e:
                self.logger.error(f"수익 보호 처리 오류: {e}")
                await asyncio.sleep(300)  # 오류 시 5분 대기
                
    async def _analyze_and_protect_profits(self):
        """수익 분석 및 보호 처리"""
        db = next(get_db())
        try:
            # 활성 상품 조회
            from app.models.product import ProductStatus
            
            active_products = db.query(Product).filter(
                Product.status == ProductStatus.ACTIVE,
                Product.is_deleted == False,
                Product.is_dropshipping == True
            ).all()
            
            high_risk_products = []
            
            for product in active_products:
                analysis = await self._analyze_product_profit(product)
                
                if analysis.risk_level in [ProfitRisk.HIGH, ProfitRisk.CRITICAL]:
                    high_risk_products.append(analysis)
                    await self._apply_profit_protection(analysis)
                    
            if high_risk_products:
                self.logger.warning(f"수익 위험 상품 {len(high_risk_products)}개 처리")
                await self._send_profit_risk_alert(high_risk_products)
                
        finally:
            db.close()
            
    async def _analyze_product_profit(self, product: Product) -> ProfitAnalysis:
        """개별 상품 수익 분석"""
        # 현재 마진 계산
        current_margin = (product.selling_price - product.wholesale_price) / product.selling_price
        margin_gap = self.target_margin_rate - current_margin
        
        # 위험도 결정
        risk_level = self._determine_risk_level(current_margin, margin_gap)
        
        # 경쟁사 가격 분석
        competitor_price_avg = await self._get_competitor_average_price(product)
        market_position = self._analyze_market_position(product.selling_price, competitor_price_avg)
        
        # 일일 예상 손실 계산
        estimated_loss = await self._calculate_daily_loss(product, margin_gap)
        
        # 권장 액션 결정
        recommended_action = self._get_recommended_action(current_margin, competitor_price_avg, product.selling_price)
        
        return ProfitAnalysis(
            product_id=product.id,
            current_margin=current_margin,
            target_margin=self.target_margin_rate,
            margin_gap=margin_gap,
            risk_level=risk_level,
            recommended_action=recommended_action,
            estimated_loss_per_day=estimated_loss,
            competitor_price_avg=competitor_price_avg,
            market_position=market_position
        )
        
    def _determine_risk_level(self, current_margin: float, margin_gap: float) -> ProfitRisk:
        """위험도 결정"""
        if current_margin < 0:
            return ProfitRisk.CRITICAL  # 손실
        elif current_margin < self.min_margin_rate:
            return ProfitRisk.HIGH      # 최소 마진 미달
        elif margin_gap > 0.1:
            return ProfitRisk.MEDIUM    # 목표 마진 대비 10% 이상 차이
        else:
            return ProfitRisk.LOW       # 안전
            
    async def _get_competitor_average_price(self, product: Product) -> float:
        """경쟁사 평균 가격 조회"""
        try:
            # 경쟁사 가격 조회 (외부 API 또는 크롤링)
            # 구현 예정: 네이버쇼핑, 쿠팡 등에서 유사 상품 가격 수집
            
            # 임시로 현재 가격의 90-110% 범위로 설정
            import random
            return product.selling_price * random.uniform(0.9, 1.1)
            
        except Exception as e:
            self.logger.error(f"경쟁사 가격 조회 실패 - 상품 {product.id}: {e}")
            return product.selling_price
            
    def _analyze_market_position(self, our_price: float, competitor_avg: float) -> str:
        """시장 포지션 분석"""
        if competitor_avg == 0:
            return "데이터 없음"
            
        ratio = our_price / competitor_avg
        
        if ratio < 0.9:
            return "저가 포지션"
        elif ratio < 1.1:
            return "경쟁적 포지션"
        else:
            return "고가 포지션"
            
    async def _calculate_daily_loss(self, product: Product, margin_gap: float) -> float:
        """일일 예상 손실 계산"""
        try:
            # 최근 30일 평균 일일 판매량 조회
            db = next(get_db())
            try:
                from app.models.order import Order
                
                thirty_days_ago = datetime.now() - timedelta(days=30)
                daily_sales = db.query(Order).filter(
                    Order.product_id == product.id,
                    Order.created_at >= thirty_days_ago,
                    Order.status.in_(['completed', 'shipped'])
                ).count() / 30
                
                # 마진 부족으로 인한 일일 손실
                loss_per_item = product.selling_price * margin_gap
                return daily_sales * loss_per_item
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"일일 손실 계산 실패 - 상품 {product.id}: {e}")
            return 0.0
            
    def _get_recommended_action(self, current_margin: float, competitor_avg: float, our_price: float) -> str:
        """권장 액션 결정"""
        if current_margin < 0:
            return "즉시 가격 인상 또는 판매 중단"
        elif current_margin < self.min_margin_rate:
            if our_price < competitor_avg * 0.95:
                return "가격 인상 (경쟁력 유지 범위 내)"
            else:
                return "비용 절감 또는 대체 공급업체 검토"
        elif competitor_avg > 0 and our_price > competitor_avg * 1.15:
            return "가격 인하 고려 (경쟁력 향상)"
        else:
            return "현재 가격 유지"
            
    async def _apply_profit_protection(self, analysis: ProfitAnalysis):
        """수익 보호 조치 적용"""
        db = next(get_db())
        try:
            product = db.query(Product).filter(Product.id == analysis.product_id).first()
            if not product:
                return
                
            action_taken = False
            
            # 심각한 수익 위험 시 자동 조치
            if analysis.risk_level == ProfitRisk.CRITICAL:
                if analysis.current_margin < 0:
                    # 손실 상품 - 즉시 비활성화
                    await self._emergency_deactivate(product, "손실 발생으로 인한 긴급 비활성화")
                    action_taken = True
                    
            elif analysis.risk_level == ProfitRisk.HIGH:
                # 자동 가격 조정 시도
                if await self._auto_adjust_price(product, analysis):
                    action_taken = True
                    
            # 수익 보호 로그 저장
            await self._log_profit_protection(analysis, action_taken)
            
        finally:
            db.close()
            
    async def _emergency_deactivate(self, product: Product, reason: str):
        """긴급 비활성화"""
        try:
            from app.services.automation.product_status_automation import ProductStatusAutomation
            
            automation = ProductStatusAutomation()
            parameters = {"platforms": "all", "notify": True}
            await automation._deactivate_product(product, parameters)
            
            self.logger.warning(f"긴급 비활성화 - 상품 {product.id}: {reason}")
            
        except Exception as e:
            self.logger.error(f"긴급 비활성화 실패 - 상품 {product.id}: {e}")
            
    async def _auto_adjust_price(self, product: Product, analysis: ProfitAnalysis) -> bool:
        """자동 가격 조정"""
        try:
            # 목표 마진을 맞추기 위한 가격 계산
            target_price = product.wholesale_price / (1 - self.target_margin_rate)
            
            # 최대 조정 범위 확인
            max_increase = product.selling_price * (1 + self.max_price_adjustment)
            max_decrease = product.selling_price * (1 - self.max_price_adjustment)
            
            # 조정 범위 내에서만 가격 변경
            if target_price > max_increase:
                new_price = max_increase
            elif target_price < max_decrease:
                new_price = max_decrease
            else:
                new_price = target_price
                
            # 경쟁력 확인
            if analysis.competitor_price_avg > 0:
                if new_price > analysis.competitor_price_avg * 1.2:
                    # 경쟁가보다 20% 이상 높으면 조정 제한
                    new_price = min(new_price, analysis.competitor_price_avg * 1.15)
                    
            # 가격 변경이 의미있는 경우에만 적용
            if abs(new_price - product.selling_price) / product.selling_price > 0.02:  # 2% 이상 변경
                # 가격 업데이트
                old_price = product.selling_price
                product.selling_price = new_price
                product.price_updated_at = datetime.now()
                
                # 플랫폼별 가격 동기화
                await self._sync_price_to_platforms(product)
                
                db = next(get_db())
                try:
                    db.commit()
                finally:
                    db.close()
                    
                self.logger.info(f"자동 가격 조정 - 상품 {product.id}: {old_price:,}원 → {new_price:,}원")
                
                # 가격 변경 알림
                await self._send_price_adjustment_notification(product.id, old_price, new_price, "수익 보호")
                
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"자동 가격 조정 실패 - 상품 {product.id}: {e}")
            return False
            
    async def _sync_price_to_platforms(self, product: Product):
        """플랫폼별 가격 동기화"""
        from app.services.platforms.platform_manager import PlatformManager
        
        platform_manager = PlatformManager()
        
        for platform_product in product.platform_products:
            if platform_product.is_active:
                try:
                    platform = platform_manager.get_platform(platform_product.platform_type)
                    await platform.update_product_price(
                        platform_product.platform_product_id,
                        product.selling_price
                    )
                except Exception as e:
                    self.logger.error(f"플랫폼 가격 동기화 실패 - {platform_product.platform_type}: {e}")
                    
    async def _log_profit_protection(self, analysis: ProfitAnalysis, action_taken: bool):
        """수익 보호 로그 저장"""
        db = next(get_db())
        try:
            from app.models.dropshipping import ProfitProtectionLog
            
            log = ProfitProtectionLog(
                product_id=analysis.product_id,
                current_margin=analysis.current_margin,
                target_margin=analysis.target_margin,
                risk_level=analysis.risk_level.value,
                recommended_action=analysis.recommended_action,
                estimated_loss_per_day=analysis.estimated_loss_per_day,
                competitor_price_avg=analysis.competitor_price_avg,
                action_taken=action_taken,
                analyzed_at=datetime.now()
            )
            
            db.add(log)
            db.commit()
            
        finally:
            db.close()
            
    async def _send_profit_risk_alert(self, high_risk_products: List[ProfitAnalysis]):
        """수익 위험 알림"""
        from app.services.dashboard.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        critical_count = sum(1 for p in high_risk_products if p.risk_level == ProfitRisk.CRITICAL)
        high_count = len(high_risk_products) - critical_count
        
        message = f"수익 위험 상품 감지 - 심각: {critical_count}개, 높음: {high_count}개"
        
        await notification_service.send_profit_alert(high_risk_products, message)
        
    async def _send_price_adjustment_notification(self, product_id: int, old_price: float, new_price: float, reason: str):
        """가격 조정 알림"""
        from app.services.dashboard.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        message = f"가격 자동 조정: {old_price:,}원 → {new_price:,}원 ({reason})"
        
        await notification_service.send_price_change_notification(product_id, message)
        
    # 분석 및 통계 메서드
    async def analyze_profit_trends(self, days: int = 30) -> Dict:
        """수익 트렌드 분석"""
        db = next(get_db())
        try:
            from app.models.dropshipping import ProfitProtectionLog
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 기간별 위험 상품 수 추이
            risk_trends = db.query(
                db.func.date(ProfitProtectionLog.analyzed_at).label('date'),
                ProfitProtectionLog.risk_level,
                db.func.count(ProfitProtectionLog.id).label('count')
            ).filter(
                ProfitProtectionLog.analyzed_at >= start_date
            ).group_by(
                db.func.date(ProfitProtectionLog.analyzed_at),
                ProfitProtectionLog.risk_level
            ).all()
            
            # 평균 마진율 추이
            margin_trends = db.query(
                db.func.date(ProfitProtectionLog.analyzed_at).label('date'),
                db.func.avg(ProfitProtectionLog.current_margin).label('avg_margin')
            ).filter(
                ProfitProtectionLog.analyzed_at >= start_date
            ).group_by(
                db.func.date(ProfitProtectionLog.analyzed_at)
            ).all()
            
            # 총 예상 손실
            total_estimated_loss = db.query(
                db.func.sum(ProfitProtectionLog.estimated_loss_per_day)
            ).filter(
                ProfitProtectionLog.analyzed_at >= start_date
            ).scalar() or 0
            
            return {
                "period_days": days,
                "risk_trends": [
                    {
                        "date": str(trend.date),
                        "risk_level": trend.risk_level,
                        "count": trend.count
                    }
                    for trend in risk_trends
                ],
                "margin_trends": [
                    {
                        "date": str(trend.date),
                        "avg_margin": float(trend.avg_margin or 0)
                    }
                    for trend in margin_trends
                ],
                "total_estimated_loss": float(total_estimated_loss)
            }
            
        finally:
            db.close()
            
    async def get_protection_statistics(self) -> Dict:
        """수익 보호 통계"""
        db = next(get_db())
        try:
            from app.models.dropshipping import ProfitProtectionLog
            
            # 최근 24시간 통계
            last_24h = datetime.now() - timedelta(hours=24)
            
            total_analyzed = db.query(ProfitProtectionLog).filter(
                ProfitProtectionLog.analyzed_at >= last_24h
            ).count()
            
            actions_taken = db.query(ProfitProtectionLog).filter(
                ProfitProtectionLog.analyzed_at >= last_24h,
                ProfitProtectionLog.action_taken == True
            ).count()
            
            critical_products = db.query(ProfitProtectionLog).filter(
                ProfitProtectionLog.analyzed_at >= last_24h,
                ProfitProtectionLog.risk_level == ProfitRisk.CRITICAL.value
            ).count()
            
            avg_margin = db.query(
                db.func.avg(ProfitProtectionLog.current_margin)
            ).filter(
                ProfitProtectionLog.analyzed_at >= last_24h
            ).scalar() or 0
            
            return {
                "protection_running": self.is_running,
                "analyzed_products_24h": total_analyzed,
                "actions_taken_24h": actions_taken,
                "critical_products_24h": critical_products,
                "avg_margin_24h": float(avg_margin),
                "action_rate": (actions_taken / total_analyzed * 100) if total_analyzed > 0 else 0
            }
            
        finally:
            db.close()
            
    def update_protection_settings(self, 
                                 min_margin: Optional[float] = None,
                                 target_margin: Optional[float] = None,
                                 max_adjustment: Optional[float] = None):
        """수익 보호 설정 업데이트"""
        if min_margin is not None:
            self.min_margin_rate = min_margin
            
        if target_margin is not None:
            self.target_margin_rate = target_margin
            
        if max_adjustment is not None:
            self.max_price_adjustment = max_adjustment
            
        self.logger.info(f"수익 보호 설정 업데이트 - 최소마진: {self.min_margin_rate:.1%}, "
                        f"목표마진: {self.target_margin_rate:.1%}, 최대조정: {self.max_price_adjustment:.1%}")
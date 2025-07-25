"""
고객 행동 분석 엔진
구매 패턴, 웹사이트 행동, 선호도 등을 분석하여 고객 인사이트 제공
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict, Counter
import json

from ...models.crm import Customer, CustomerBehavior, CustomerPreference
from ...models.order import Order
from ...models.product import Product


class BehaviorAnalyzer:
    """고객 행동 분석을 수행하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_purchase_patterns(self, customer_id: int, days: int = 365) -> Dict:
        """
        고객의 구매 패턴 분석
        
        Args:
            customer_id: 고객 ID
            days: 분석할 일수
            
        Returns:
            구매 패턴 분석 결과
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # 고객 주문 데이터 조회
        orders = self.db.query(Order).filter(
            and_(
                Order.customer_id == customer_id,
                Order.order_date >= start_date,
                Order.order_status != 'cancelled'
            )
        ).all()
        
        if not orders:
            return {"message": "주문 데이터가 없습니다."}
        
        # 구매 패턴 분석
        purchase_analysis = {
            "총_주문수": len(orders),
            "총_구매금액": sum(order.total_amount for order in orders),
            "평균_주문금액": sum(order.total_amount for order in orders) / len(orders),
        }
        
        # 시간대별 구매 패턴
        hourly_purchases = defaultdict(int)
        daily_purchases = defaultdict(int)
        monthly_purchases = defaultdict(int)
        
        for order in orders:
            hour = order.order_date.hour
            day_of_week = order.order_date.weekday()  # 0=월요일, 6=일요일
            month = order.order_date.month
            
            hourly_purchases[hour] += 1
            daily_purchases[day_of_week] += 1
            monthly_purchases[month] += 1
        
        # 선호 시간대 분석
        preferred_hours = sorted(hourly_purchases.items(), key=lambda x: x[1], reverse=True)[:3]
        preferred_days = sorted(daily_purchases.items(), key=lambda x: x[1], reverse=True)[:3]
        
        day_names = ["월", "화", "수", "목", "금", "토", "일"]
        
        purchase_analysis.update({
            "선호_구매시간": [{"시간": f"{hour}시", "구매수": count} for hour, count in preferred_hours],
            "선호_구매요일": [{"요일": day_names[day], "구매수": count} for day, count in preferred_days],
            "월별_구매분포": dict(monthly_purchases),
            "구매_간격_분석": self._analyze_purchase_intervals(orders)
        })
        
        return purchase_analysis
    
    def _analyze_purchase_intervals(self, orders: List[Order]) -> Dict:
        """구매 간격 분석"""
        if len(orders) < 2:
            return {"평균_구매간격": None, "구매간격_패턴": None}
        
        # 주문을 날짜순으로 정렬
        sorted_orders = sorted(orders, key=lambda x: x.order_date)
        
        intervals = []
        for i in range(1, len(sorted_orders)):
            interval = (sorted_orders[i].order_date - sorted_orders[i-1].order_date).days
            intervals.append(interval)
        
        if not intervals:
            return {"평균_구매간격": None, "구매간격_패턴": None}
        
        avg_interval = sum(intervals) / len(intervals)
        
        # 간격 패턴 분류
        if avg_interval <= 7:
            pattern = "매우_활발한_구매"
        elif avg_interval <= 30:
            pattern = "활발한_구매"
        elif avg_interval <= 90:
            pattern = "정기적_구매"
        elif avg_interval <= 180:
            pattern = "비정기적_구매"
        else:
            pattern = "드문_구매"
        
        return {
            "평균_구매간격": round(avg_interval, 2),
            "구매간격_패턴": pattern,
            "최소_간격": min(intervals),
            "최대_간격": max(intervals),
            "간격_표준편차": round(pd.Series(intervals).std(), 2) if len(intervals) > 1 else 0
        }
    
    def analyze_product_preferences(self, customer_id: int, days: int = 365) -> Dict:
        """
        고객의 상품 선호도 분석
        
        Args:
            customer_id: 고객 ID
            days: 분석할 일수
            
        Returns:
            상품 선호도 분석 결과
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # 고객의 구매 상품 조회
        purchased_products = self.db.query(
            Product.category,
            Product.brand,
            Product.price,
            func.count(Order.id).label('purchase_count'),
            func.sum(Order.total_amount).label('total_spent')
        ).join(Order, Order.product_id == Product.id).filter(
            and_(
                Order.customer_id == customer_id,
                Order.order_date >= start_date,
                Order.order_status != 'cancelled'
            )
        ).group_by(Product.category, Product.brand, Product.price).all()
        
        if not purchased_products:
            return {"message": "구매 상품 데이터가 없습니다."}
        
        # 카테고리별 선호도
        category_prefs = defaultdict(lambda: {"count": 0, "spent": 0})
        brand_prefs = defaultdict(lambda: {"count": 0, "spent": 0})
        price_ranges = []
        
        for product in purchased_products:
            category_prefs[product.category]["count"] += product.purchase_count
            category_prefs[product.category]["spent"] += float(product.total_spent)
            
            if product.brand:
                brand_prefs[product.brand]["count"] += product.purchase_count
                brand_prefs[product.brand]["spent"] += float(product.total_spent)
            
            price_ranges.extend([product.price] * product.purchase_count)
        
        # Top 카테고리 및 브랜드
        top_categories = sorted(
            category_prefs.items(), 
            key=lambda x: x[1]["spent"], 
            reverse=True
        )[:5]
        
        top_brands = sorted(
            brand_prefs.items(), 
            key=lambda x: x[1]["spent"], 
            reverse=True
        )[:5]
        
        # 가격대 분석
        price_analysis = self._analyze_price_preferences(price_ranges)
        
        preference_analysis = {
            "선호_카테고리": [
                {
                    "카테고리": cat,
                    "구매횟수": data["count"],
                    "총구매금액": data["spent"],
                    "평균단가": round(data["spent"] / data["count"], 2)
                }
                for cat, data in top_categories
            ],
            "선호_브랜드": [
                {
                    "브랜드": brand,
                    "구매횟수": data["count"],
                    "총구매금액": data["spent"],
                    "평균단가": round(data["spent"] / data["count"], 2)
                }
                for brand, data in top_brands
            ],
            "가격대_선호도": price_analysis
        }
        
        return preference_analysis
    
    def _analyze_price_preferences(self, prices: List[float]) -> Dict:
        """가격대 선호도 분석"""
        if not prices:
            return {}
        
        prices_series = pd.Series(prices)
        
        # 가격대 구간 정의
        price_ranges = {
            "1만원_미만": len([p for p in prices if p < 10000]),
            "1-3만원": len([p for p in prices if 10000 <= p < 30000]),
            "3-5만원": len([p for p in prices if 30000 <= p < 50000]),
            "5-10만원": len([p for p in prices if 50000 <= p < 100000]),
            "10만원_이상": len([p for p in prices if p >= 100000])
        }
        
        return {
            "평균_구매가격": round(prices_series.mean(), 2),
            "중간_구매가격": round(prices_series.median(), 2),
            "최저_구매가격": round(prices_series.min(), 2),
            "최고_구매가격": round(prices_series.max(), 2),
            "가격대별_구매분포": price_ranges,
            "가격_표준편차": round(prices_series.std(), 2)
        }
    
    def analyze_website_behavior(self, customer_id: int, days: int = 30) -> Dict:
        """
        웹사이트 행동 분석
        
        Args:
            customer_id: 고객 ID
            days: 분석할 일수
            
        Returns:
            웹사이트 행동 분석 결과
        """
        start_date = datetime.now() - timedelta(days=days)
        
        behaviors = self.db.query(CustomerBehavior).filter(
            and_(
                CustomerBehavior.customer_id == customer_id,
                CustomerBehavior.timestamp >= start_date
            )
        ).all()
        
        if not behaviors:
            return {"message": "행동 데이터가 없습니다."}
        
        # 행동 유형별 분석
        action_counts = Counter([b.action_type for b in behaviors])
        device_usage = Counter([b.device_type for b in behaviors])
        platform_usage = Counter([b.platform for b in behaviors])
        
        # 세션 분석
        sessions = defaultdict(list)
        for behavior in behaviors:
            sessions[behavior.session_id].append(behavior)
        
        session_analysis = self._analyze_sessions(sessions)
        
        # 시간대별 활동 분석
        hourly_activity = defaultdict(int)
        for behavior in behaviors:
            hour = behavior.timestamp.hour
            hourly_activity[hour] += 1
        
        behavior_analysis = {
            "총_행동수": len(behaviors),
            "행동유형별_분포": dict(action_counts),
            "디바이스_사용현황": dict(device_usage),
            "플랫폼_사용현황": dict(platform_usage),
            "세션_분석": session_analysis,
            "시간대별_활동": dict(hourly_activity),
            "활동_패턴": self._identify_activity_patterns(behaviors)
        }
        
        return behavior_analysis
    
    def _analyze_sessions(self, sessions: Dict) -> Dict:
        """세션 분석"""
        if not sessions:
            return {}
        
        session_durations = []
        pages_per_session = []
        
        for session_id, session_behaviors in sessions.items():
            if len(session_behaviors) > 1:
                # 세션 시간 계산
                session_behaviors.sort(key=lambda x: x.timestamp)
                duration = (session_behaviors[-1].timestamp - session_behaviors[0].timestamp).total_seconds() / 60
                session_durations.append(duration)
            
            pages_per_session.append(len(session_behaviors))
        
        return {
            "총_세션수": len(sessions),
            "평균_세션시간_분": round(sum(session_durations) / len(session_durations), 2) if session_durations else 0,
            "평균_페이지뷰_세션": round(sum(pages_per_session) / len(pages_per_session), 2),
            "최장_세션시간_분": round(max(session_durations), 2) if session_durations else 0,
            "바운스_세션수": len([s for s in sessions.values() if len(s) == 1])
        }
    
    def _identify_activity_patterns(self, behaviors: List[CustomerBehavior]) -> Dict:
        """활동 패턴 식별"""
        if not behaviors:
            return {}
        
        # 구매 전환 행동 패턴 분석
        conversion_funnel = {
            "view": 0,
            "click": 0,
            "add_to_cart": 0,
            "purchase": 0
        }
        
        for behavior in behaviors:
            if behavior.action_type in conversion_funnel:
                conversion_funnel[behavior.action_type] += 1
        
        # 전환율 계산
        conversion_rates = {}
        if conversion_funnel["view"] > 0:
            conversion_rates["click_rate"] = round(conversion_funnel["click"] / conversion_funnel["view"] * 100, 2)
            conversion_rates["cart_rate"] = round(conversion_funnel["add_to_cart"] / conversion_funnel["view"] * 100, 2)
            conversion_rates["purchase_rate"] = round(conversion_funnel["purchase"] / conversion_funnel["view"] * 100, 2)
        
        return {
            "전환_퍼널": conversion_funnel,
            "전환율": conversion_rates,
            "주요_활동시간": self._get_peak_activity_hours(behaviors),
            "브라우징_패턴": self._analyze_browsing_pattern(behaviors)
        }
    
    def _get_peak_activity_hours(self, behaviors: List[CustomerBehavior]) -> List[int]:
        """활동이 가장 많은 시간대 반환"""
        hourly_counts = defaultdict(int)
        for behavior in behaviors:
            hourly_counts[behavior.timestamp.hour] += 1
        
        # 상위 3개 시간대 반환
        top_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        return [hour for hour, count in top_hours]
    
    def _analyze_browsing_pattern(self, behaviors: List[CustomerBehavior]) -> str:
        """브라우징 패턴 분류"""
        view_count = len([b for b in behaviors if b.action_type == "view"])
        purchase_count = len([b for b in behaviors if b.action_type == "purchase"])
        
        if view_count == 0:
            return "데이터_부족"
        
        browse_to_purchase_ratio = view_count / (purchase_count + 1)
        
        if browse_to_purchase_ratio < 5:
            return "결정적_구매자"  # 적게 보고 빠르게 구매
        elif browse_to_purchase_ratio < 15:
            return "신중한_구매자"   # 적당히 보고 구매
        elif browse_to_purchase_ratio < 30:
            return "탐색적_구매자"   # 많이 보고 구매
        else:
            return "브라우징_중심"   # 많이 보지만 구매는 적음
    
    def update_customer_preferences(self, customer_id: int) -> Dict:
        """
        고객 선호도 정보 업데이트
        
        Args:
            customer_id: 고객 ID
            
        Returns:
            업데이트 결과
        """
        # 구매 패턴 분석
        purchase_patterns = self.analyze_purchase_patterns(customer_id)
        product_preferences = self.analyze_product_preferences(customer_id)
        website_behavior = self.analyze_website_behavior(customer_id)
        
        # CustomerPreference 레코드 조회 또는 생성
        preference = self.db.query(CustomerPreference).filter(
            CustomerPreference.customer_id == customer_id
        ).first()
        
        if not preference:
            preference = CustomerPreference(customer_id=customer_id)
            self.db.add(preference)
        
        # 선호도 데이터 업데이트
        if "선호_카테고리" in product_preferences:
            category_prefs = {}
            for cat_data in product_preferences["선호_카테고리"]:
                category_prefs[cat_data["카테고리"]] = {
                    "score": cat_data["총구매금액"],
                    "count": cat_data["구매횟수"]
                }
            preference.preferred_categories = category_prefs
        
        if "선호_브랜드" in product_preferences:
            brand_prefs = {}
            for brand_data in product_preferences["선호_브랜드"]:
                brand_prefs[brand_data["브랜드"]] = {
                    "score": brand_data["총구매금액"],
                    "count": brand_data["구매횟수"]
                }
            preference.preferred_brands = brand_prefs
        
        if "가격대_선호도" in product_preferences:
            price_prefs = product_preferences["가격대_선호도"]
            preference.preferred_price_ranges = {
                "avg_price": price_prefs.get("평균_구매가격", 0),
                "price_range_distribution": price_prefs.get("가격대별_구매분포", {})
            }
        
        # 구매 패턴 선호도
        if "선호_구매시간" in purchase_patterns:
            time_prefs = {}
            for time_data in purchase_patterns["선호_구매시간"]:
                hour = int(time_data["시간"].replace("시", ""))
                time_prefs[str(hour)] = time_data["구매수"]
            preference.preferred_time_of_day = time_prefs
        
        if "선호_구매요일" in purchase_patterns:
            day_prefs = {}
            day_mapping = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
            for day_data in purchase_patterns["선호_구매요일"]:
                day_num = day_mapping.get(day_data["요일"])
                if day_num is not None:
                    day_prefs[str(day_num)] = day_data["구매수"]
            preference.preferred_day_of_week = day_prefs
        
        # 디바이스 선호도
        if "디바이스_사용현황" in website_behavior:
            device_usage = website_behavior["디바이스_사용현황"]
            total_usage = sum(device_usage.values())
            if total_usage > 0:
                mobile_rate = device_usage.get("mobile", 0) / total_usage
                
                # Customer 테이블의 mobile_usage_rate 업데이트
                customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
                if customer:
                    customer.mobile_usage_rate = mobile_rate
        
        preference.last_updated = datetime.now()
        preference.confidence_score = self._calculate_confidence_score(purchase_patterns, product_preferences)
        
        self.db.commit()
        
        return {
            "customer_id": customer_id,
            "updated_at": preference.last_updated.isoformat(),
            "confidence_score": preference.confidence_score,
            "message": "고객 선호도가 성공적으로 업데이트되었습니다."
        }
    
    def _calculate_confidence_score(self, purchase_patterns: Dict, product_preferences: Dict) -> float:
        """선호도 예측 신뢰도 점수 계산"""
        score = 0.0
        max_score = 1.0
        
        # 구매 데이터가 많을수록 신뢰도 증가
        if "총_주문수" in purchase_patterns:
            order_count = purchase_patterns["총_주문수"]
            score += min(order_count / 10, 0.4)  # 최대 0.4점
        
        # 카테고리 다양성
        if "선호_카테고리" in product_preferences:
            category_count = len(product_preferences["선호_카테고리"])
            score += min(category_count / 5, 0.3)  # 최대 0.3점
        
        # 데이터 기간 (최근 데이터일수록 높은 점수)
        score += 0.3  # 기본 점수
        
        return round(min(score, max_score), 2)
    
    def get_customer_behavior_summary(self, customer_id: int) -> Dict:
        """
        고객 행동 종합 요약
        
        Args:
            customer_id: 고객 ID
            
        Returns:
            고객 행동 종합 분석 결과
        """
        summary = {
            "customer_id": customer_id,
            "구매_패턴": self.analyze_purchase_patterns(customer_id, days=365),
            "상품_선호도": self.analyze_product_preferences(customer_id, days=365),
            "웹사이트_행동": self.analyze_website_behavior(customer_id, days=90),
            "분석_일시": datetime.now().isoformat()
        }
        
        return summary
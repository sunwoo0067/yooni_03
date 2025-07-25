"""
고객 생애주기 분석 엔진
고객의 생애주기 단계를 추적하고 단계별 맞춤 전략을 제공
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from enum import Enum

from ...models.crm import (Customer, CustomerLifecycleStage, CustomerLifecycleEvent, 
                          CustomerSegment)
from ...models.order import Order


class LifecycleAnalyzer:
    """고객 생애주기 분석을 수행하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 생애주기 단계별 정의
        self.lifecycle_definitions = {
            CustomerLifecycleStage.NEW: {
                "description": "최근 등록한 신규 고객",
                "criteria": "등록 후 30일 이내, 구매 경험 1회 이하",
                "next_actions": ["웰컴 메시지", "첫 구매 인센티브", "상품 추천"]
            },
            CustomerLifecycleStage.ACTIVE: {
                "description": "정기적으로 구매하는 활성 고객",
                "criteria": "최근 90일 내 2회 이상 구매",
                "next_actions": ["크로스셀링", "로열티 프로그램", "개인화 추천"]
            },
            CustomerLifecycleStage.ENGAGED: {
                "description": "높은 참여도를 보이는 우수 고객",
                "criteria": "월 1회 이상 구매, 높은 주문 금액",
                "next_actions": ["VIP 서비스", "조기 액세스", "피드백 요청"]
            },
            CustomerLifecycleStage.AT_RISK: {
                "description": "이탈 위험이 있는 고객",
                "criteria": "과거 활성 고객이었으나 최근 구매 감소",
                "next_actions": ["특별 할인", "개인화 오퍼", "리타겟팅"]
            },
            CustomerLifecycleStage.DORMANT: {
                "description": "휴면 상태의 고객",
                "criteria": "90일 이상 구매 없음",
                "next_actions": ["재활성화 캠페인", "컴백 오퍼", "설문조사"]
            },
            CustomerLifecycleStage.CHURNED: {
                "description": "이탈한 고객",
                "criteria": "180일 이상 구매 없음, 서비스 이용 중단",
                "next_actions": ["윈백 캠페인", "특별 혜택", "피드백 수집"]
            },
            CustomerLifecycleStage.VIP: {
                "description": "최고 가치 고객",
                "criteria": "높은 CLV, 빈번한 구매, 높은 만족도",
                "next_actions": ["개인 담당자", "독점 혜택", "우선 지원"]
            }
        }
    
    def analyze_customer_lifecycle_stage(self, customer_id: int) -> Dict:
        """
        고객의 현재 생애주기 단계 분석
        
        Args:
            customer_id: 고객 ID
            
        Returns:
            생애주기 분석 결과
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        # 고객 주문 데이터 조회
        orders = self.db.query(Order).filter(
            and_(
                Order.customer_id == customer_id,
                Order.order_status != 'cancelled'
            )
        ).order_by(Order.order_date.desc()).all()
        
        current_stage = self._determine_lifecycle_stage(customer, orders)
        stage_metrics = self._calculate_stage_metrics(customer, orders)
        recommendations = self._get_stage_recommendations(current_stage, stage_metrics)
        
        # 단계 변화 감지
        stage_changed = customer.lifecycle_stage != current_stage
        
        analysis_result = {
            "customer_id": customer_id,
            "current_stage": current_stage.value,
            "previous_stage": customer.lifecycle_stage.value if customer.lifecycle_stage else None,
            "stage_changed": stage_changed,
            "stage_description": self.lifecycle_definitions[current_stage]["description"],
            "stage_criteria": self.lifecycle_definitions[current_stage]["criteria"],
            "metrics": stage_metrics,
            "recommendations": recommendations,
            "analysis_date": datetime.now().isoformat()
        }
        
        # 단계 변화가 있다면 고객 테이블 업데이트 및 이벤트 기록
        if stage_changed:
            self._update_customer_stage(customer, current_stage, stage_metrics)
            self._record_lifecycle_event(customer_id, customer.lifecycle_stage, current_stage, stage_metrics)
        
        return analysis_result
    
    def _determine_lifecycle_stage(self, customer: Customer, orders: List[Order]) -> CustomerLifecycleStage:
        """고객의 생애주기 단계 결정"""
        now = datetime.now()
        registration_days = (now - customer.registration_date).days
        
        if not orders:
            # 주문이 없는 경우
            if registration_days <= 30:
                return CustomerLifecycleStage.NEW
            else:
                return CustomerLifecycleStage.DORMANT
        
        # 주문 분석
        total_orders = len(orders)
        total_spent = sum(order.total_amount for order in orders)
        last_order_date = orders[0].order_date
        days_since_last_order = (now - last_order_date).days
        
        # 최근 90일 주문
        recent_orders = [o for o in orders if (now - o.order_date).days <= 90]
        recent_order_count = len(recent_orders)
        recent_spent = sum(order.total_amount for order in recent_orders)
        
        # VIP 고객 조건 확인
        if (total_spent > 500000 and  # 총 구매액 50만원 이상
            total_orders >= 10 and    # 총 주문 10회 이상
            days_since_last_order <= 60):  # 최근 60일 내 구매
            return CustomerLifecycleStage.VIP
        
        # 이탈 고객 조건
        if days_since_last_order > 180:
            return CustomerLifecycleStage.CHURNED
        
        # 휴면 고객 조건
        if days_since_last_order > 90:
            return CustomerLifecycleStage.DORMANT
        
        # 이탈 위험 고객 조건
        if (days_since_last_order > 60 and 
            total_orders >= 3 and 
            recent_order_count == 0):
            return CustomerLifecycleStage.AT_RISK
        
        # 참여 고객 조건
        if (recent_order_count >= 3 and 
            recent_spent >= 100000):  # 최근 90일 내 3회 이상, 10만원 이상
            return CustomerLifecycleStage.ENGAGED
        
        # 활성 고객 조건
        if recent_order_count >= 2:
            return CustomerLifecycleStage.ACTIVE
        
        # 신규 고객 조건
        if registration_days <= 30 or total_orders <= 1:
            return CustomerLifecycleStage.NEW
        
        # 기본값
        return CustomerLifecycleStage.ACTIVE
    
    def _calculate_stage_metrics(self, customer: Customer, orders: List[Order]) -> Dict:
        """단계별 지표 계산"""
        now = datetime.now()
        
        if not orders:
            return {
                "총_주문수": 0,
                "총_구매금액": 0,
                "평균_주문금액": 0,
                "마지막_구매일": None,
                "구매_빈도": 0,
                "고객가치점수": 0
            }
        
        # 기본 지표
        total_orders = len(orders)
        total_spent = sum(order.total_amount for order in orders)
        avg_order_value = total_spent / total_orders
        last_order_date = orders[0].order_date
        days_since_last_order = (now - last_order_date).days
        
        # 구매 빈도 계산 (월 평균)
        customer_lifetime_days = (now - customer.registration_date).days
        if customer_lifetime_days > 0:
            purchase_frequency = (total_orders / customer_lifetime_days) * 30  # 월 평균
        else:
            purchase_frequency = 0
        
        # 고객 가치 점수 계산 (0-100)
        value_score = self._calculate_customer_value_score(customer, orders)
        
        # 최근 90일 활동
        recent_orders = [o for o in orders if (now - o.order_date).days <= 90]
        recent_activity = {
            "최근90일_주문수": len(recent_orders),
            "최근90일_구매금액": sum(order.total_amount for order in recent_orders),
            "최근90일_평균주문금액": sum(order.total_amount for order in recent_orders) / len(recent_orders) if recent_orders else 0
        }
        
        return {
            "총_주문수": total_orders,
            "총_구매금액": total_spent,
            "평균_주문금액": round(avg_order_value, 2),
            "마지막_구매일": last_order_date.isoformat(),
            "마지막_구매_경과일": days_since_last_order,
            "구매_빈도_월평균": round(purchase_frequency, 2),
            "고객가치점수": value_score,
            "고객_등록일": customer.registration_date.isoformat(),
            "고객_생애기간_일": customer_lifetime_days,
            **recent_activity
        }
    
    def _calculate_customer_value_score(self, customer: Customer, orders: List[Order]) -> int:
        """고객 가치 점수 계산 (0-100)"""
        if not orders:
            return 0
        
        now = datetime.now()
        total_spent = sum(order.total_amount for order in orders)
        total_orders = len(orders)
        last_order_date = orders[0].order_date
        days_since_last_order = (now - last_order_date).days
        
        # 점수 계산 요소
        # 1. 총 구매 금액 (0-40점)
        monetary_score = min(total_spent / 10000, 40)  # 1만원당 1점, 최대 40점
        
        # 2. 구매 빈도 (0-30점)
        frequency_score = min(total_orders * 3, 30)  # 주문 1회당 3점, 최대 30점
        
        # 3. 최근성 (0-30점)
        if days_since_last_order <= 30:
            recency_score = 30
        elif days_since_last_order <= 60:
            recency_score = 20
        elif days_since_last_order <= 90:
            recency_score = 10
        else:
            recency_score = 0
        
        total_score = monetary_score + frequency_score + recency_score
        return min(int(total_score), 100)
    
    def _get_stage_recommendations(self, stage: CustomerLifecycleStage, metrics: Dict) -> List[Dict]:
        """단계별 권장 액션 제공"""
        base_actions = self.lifecycle_definitions[stage]["next_actions"]
        
        recommendations = []
        for action in base_actions:
            priority = self._determine_action_priority(stage, action, metrics)
            recommendations.append({
                "action": action,
                "priority": priority,
                "description": self._get_action_description(action, stage, metrics)
            })
        
        # 우선순위별 정렬
        recommendations.sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True)
        
        return recommendations
    
    def _determine_action_priority(self, stage: CustomerLifecycleStage, action: str, metrics: Dict) -> str:
        """액션의 우선순위 결정"""
        # 단계별 우선순위 로직
        if stage == CustomerLifecycleStage.AT_RISK:
            if action in ["특별 할인", "개인화 오퍼"]:
                return "high"
            return "medium"
        elif stage == CustomerLifecycleStage.VIP:
            if action in ["개인 담당자", "독점 혜택"]:
                return "high"
            return "medium"
        elif stage == CustomerLifecycleStage.NEW:
            if action == "웰컴 메시지":
                return "high"
            return "medium"
        elif stage == CustomerLifecycleStage.CHURNED:
            if action == "윈백 캠페인":
                return "high"
            return "medium"
        
        return "medium"
    
    def _get_action_description(self, action: str, stage: CustomerLifecycleStage, metrics: Dict) -> str:
        """액션에 대한 상세 설명 제공"""
        descriptions = {
            "웰컴 메시지": f"신규 고객 환영 메시지 및 사이트 이용 가이드 발송",
            "첫 구매 인센티브": f"첫 구매를 위한 {metrics.get('평균_주문금액', 30000) * 0.1:.0f}원 할인 쿠폰 제공",
            "상품 추천": f"고객 프로필 기반 개인화 상품 추천",
            "크로스셀링": f"구매 이력 기반 관련 상품 추천 및 번들 할인",
            "로열티 프로그램": f"포인트 적립 및 등급 혜택 안내",
            "개인화 추천": f"AI 기반 맞춤형 상품 추천",
            "VIP 서비스": f"전용 고객센터 및 우선 배송 서비스 제공",
            "조기 액세스": f"신상품 및 특별 세일 조기 접근 권한 제공",
            "피드백 요청": f"상품 및 서비스 개선을 위한 고객 의견 수집",
            "특별 할인": f"이탈 방지를 위한 개인화 할인 혜택 제공",
            "개인화 오퍼": f"고객 선호도 기반 맞춤형 프로모션",
            "리타겟팅": f"관심 상품 기반 광고 재타겟팅 실행",
            "재활성화 캠페인": f"휴면 고객 대상 컴백 이벤트 및 할인 혜택",
            "컴백 오퍼": f"복귀 고객 전용 특가 혜택 제공",
            "설문조사": f"서비스 개선을 위한 고객 만족도 조사",
            "윈백 캠페인": f"이탈 고객 대상 강력한 인센티브 제공",
            "특별 혜택": f"복귀 유도를 위한 파격 할인 및 혜택",
            "피드백 수집": f"이탈 사유 파악을 위한 설문 및 인터뷰",
            "개인 담당자": f"VIP 고객 전담 매니저 배정",
            "독점 혜택": f"VIP 고객만의 특별 혜택 및 이벤트",
            "우선 지원": f"24시간 우선 고객 지원 서비스"
        }
        
        return descriptions.get(action, f"{action} 실행")
    
    def _update_customer_stage(self, customer: Customer, new_stage: CustomerLifecycleStage, metrics: Dict):
        """고객의 생애주기 단계 업데이트"""
        customer.lifecycle_stage = new_stage
        customer.updated_at = datetime.now()
        
        # 고객 가치 등급도 함께 업데이트
        value_score = metrics.get("고객가치점수", 0)
        if value_score >= 80:
            customer.customer_value_tier = "platinum"
        elif value_score >= 60:
            customer.customer_value_tier = "gold"
        elif value_score >= 40:
            customer.customer_value_tier = "silver"
        else:
            customer.customer_value_tier = "bronze"
        
        self.db.commit()
    
    def _record_lifecycle_event(self, customer_id: int, previous_stage: CustomerLifecycleStage, 
                               current_stage: CustomerLifecycleStage, metrics: Dict):
        """생애주기 변화 이벤트 기록"""
        # 단계 변화 트리거 요인 분석
        trigger_factor = self._analyze_stage_change_trigger(previous_stage, current_stage, metrics)
        
        # 권장 액션 생성
        recommended_actions = self._get_stage_recommendations(current_stage, metrics)
        
        event = CustomerLifecycleEvent(
            customer_id=customer_id,
            event_type="stage_change",
            event_description=f"고객 생애주기 단계 변경: {previous_stage.value} → {current_stage.value}",
            previous_stage=previous_stage,
            current_stage=current_stage,
            trigger_factor=trigger_factor,
            trigger_data=metrics,
            action_required=True,
            recommended_actions=[{"actions": recommended_actions}],
            event_date=datetime.now()
        )
        
        self.db.add(event)
        self.db.commit()
    
    def _analyze_stage_change_trigger(self, previous_stage: CustomerLifecycleStage, 
                                    current_stage: CustomerLifecycleStage, metrics: Dict) -> str:
        """단계 변화의 트리거 요인 분석"""
        if not previous_stage:
            return "initial_classification"
        
        # 긍정적 변화
        if (previous_stage == CustomerLifecycleStage.NEW and 
            current_stage == CustomerLifecycleStage.ACTIVE):
            return "successful_onboarding"
        
        if (previous_stage == CustomerLifecycleStage.ACTIVE and 
            current_stage == CustomerLifecycleStage.ENGAGED):
            return "increased_engagement"
        
        if current_stage == CustomerLifecycleStage.VIP:
            return "high_value_achievement"
        
        # 부정적 변화
        if current_stage == CustomerLifecycleStage.AT_RISK:
            return "decreased_activity"
        
        if current_stage == CustomerLifecycleStage.DORMANT:
            return "inactivity_period"
        
        if current_stage == CustomerLifecycleStage.CHURNED:
            return "customer_churn"
        
        return "natural_progression"
    
    def get_lifecycle_distribution(self) -> Dict:
        """전체 고객의 생애주기 분포 조회"""
        stage_counts = self.db.query(
            Customer.lifecycle_stage,
            func.count(Customer.id).label('count')
        ).filter(
            Customer.is_active == True
        ).group_by(Customer.lifecycle_stage).all()
        
        total_customers = sum(count for _, count in stage_counts)
        
        distribution = {}
        for stage, count in stage_counts:
            if stage:
                distribution[stage.value] = {
                    "count": count,
                    "percentage": round((count / total_customers) * 100, 2) if total_customers > 0 else 0,
                    "description": self.lifecycle_definitions[stage]["description"]
                }
        
        return {
            "total_customers": total_customers,
            "distribution": distribution,
            "analysis_date": datetime.now().isoformat()
        }
    
    def get_stage_transition_analysis(self, days: int = 30) -> Dict:
        """최근 단계 전환 분석"""
        start_date = datetime.now() - timedelta(days=days)
        
        transitions = self.db.query(CustomerLifecycleEvent).filter(
            and_(
                CustomerLifecycleEvent.event_type == "stage_change",
                CustomerLifecycleEvent.event_date >= start_date
            )
        ).all()
        
        # 전환 패턴 분석
        transition_patterns = {}
        for transition in transitions:
            if transition.previous_stage and transition.current_stage:
                pattern = f"{transition.previous_stage.value}→{transition.current_stage.value}"
                transition_patterns[pattern] = transition_patterns.get(pattern, 0) + 1
        
        # 가장 일반적인 전환 패턴
        top_transitions = sorted(transition_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "analysis_period_days": days,
            "total_transitions": len(transitions),
            "transition_patterns": transition_patterns,
            "top_transitions": [{"pattern": pattern, "count": count} for pattern, count in top_transitions],
            "analysis_date": datetime.now().isoformat()
        }
    
    def update_all_customer_lifecycle_stages(self) -> Dict:
        """모든 고객의 생애주기 단계 업데이트"""
        customers = self.db.query(Customer).filter(Customer.is_active == True).all()
        
        updated_count = 0
        stage_changes = {}
        
        for customer in customers:
            result = self.analyze_customer_lifecycle_stage(customer.id)
            if result.get("stage_changed", False):
                updated_count += 1
                stage = result["current_stage"]
                stage_changes[stage] = stage_changes.get(stage, 0) + 1
        
        return {
            "total_customers_analyzed": len(customers),
            "customers_with_stage_changes": updated_count,
            "stage_change_distribution": stage_changes,
            "analysis_date": datetime.now().isoformat()
        }
"""
통합 고객 분석 엔진
RFM, 행동, 생애주기 분석을 통합하여 고객에 대한 종합적인 인사이트 제공
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .rfm_analyzer import RFMAnalyzer
from .behavior_analyzer import BehaviorAnalyzer
from .lifecycle_analyzer import LifecycleAnalyzer
from ...models.crm import Customer, CustomerSegment, CustomerLifecycleStage


class CustomerAnalyzer:
    """통합 고객 분석을 수행하는 메인 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rfm_analyzer = RFMAnalyzer(db)
        self.behavior_analyzer = BehaviorAnalyzer(db)
        self.lifecycle_analyzer = LifecycleAnalyzer(db)
    
    def get_comprehensive_customer_analysis(self, customer_id: int) -> Dict:
        """
        고객에 대한 종합 분석 제공
        
        Args:
            customer_id: 고객 ID
            
        Returns:
            종합 고객 분석 결과
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        # 병렬로 각 분석 수행
        with ThreadPoolExecutor(max_workers=3) as executor:
            # RFM 분석
            rfm_future = executor.submit(self.rfm_analyzer.get_customer_rfm_profile, customer_id)
            
            # 행동 분석
            behavior_future = executor.submit(self.behavior_analyzer.get_customer_behavior_summary, customer_id)
            
            # 생애주기 분석
            lifecycle_future = executor.submit(self.lifecycle_analyzer.analyze_customer_lifecycle_stage, customer_id)
            
            # 결과 수집
            rfm_analysis = rfm_future.result()
            behavior_analysis = behavior_future.result()
            lifecycle_analysis = lifecycle_future.result()
        
        # 종합 인사이트 생성
        insights = self._generate_customer_insights(customer, rfm_analysis, behavior_analysis, lifecycle_analysis)
        
        # 액션 우선순위 결정
        action_plan = self._create_action_plan(customer, rfm_analysis, behavior_analysis, lifecycle_analysis)
        
        return {
            "customer_profile": {
                "customer_id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "registration_date": customer.registration_date.isoformat(),
                "customer_value_tier": customer.customer_value_tier,
                "total_spent": customer.total_spent,
                "total_orders": customer.total_orders,
                "lifetime_value": customer.lifetime_value
            },
            "rfm_analysis": rfm_analysis,
            "behavior_analysis": behavior_analysis,
            "lifecycle_analysis": lifecycle_analysis,
            "insights": insights,
            "action_plan": action_plan,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _generate_customer_insights(self, customer: Customer, rfm_analysis: Dict, 
                                  behavior_analysis: Dict, lifecycle_analysis: Dict) -> Dict:
        """고객 데이터를 바탕으로 인사이트 생성"""
        insights = {
            "value_assessment": self._assess_customer_value(customer, rfm_analysis),
            "risk_factors": self._identify_risk_factors(customer, behavior_analysis, lifecycle_analysis),
            "opportunities": self._identify_opportunities(customer, rfm_analysis, behavior_analysis),
            "behavioral_patterns": self._analyze_behavioral_patterns(behavior_analysis),
            "engagement_level": self._assess_engagement_level(behavior_analysis, lifecycle_analysis)
        }
        
        return insights
    
    def _assess_customer_value(self, customer: Customer, rfm_analysis: Dict) -> Dict:
        """고객 가치 평가"""
        total_spent = customer.total_spent or 0
        total_orders = customer.total_orders or 0
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0
        
        # 가치 등급 결정
        if total_spent >= 500000 and total_orders >= 10:
            value_grade = "high"
            value_description = "고가치 고객"
        elif total_spent >= 200000 and total_orders >= 5:
            value_grade = "medium"
            value_description = "중간가치 고객"
        elif total_spent >= 50000 and total_orders >= 2:
            value_grade = "low"
            value_description = "기본가치 고객"
        else:
            value_grade = "very_low"
            value_description = "신규/저가치 고객"
        
        # CLV 예측
        predicted_clv = self._predict_customer_lifetime_value(customer, rfm_analysis)
        
        return {
            "current_value": total_spent,
            "order_count": total_orders,
            "average_order_value": round(avg_order_value, 2),
            "value_grade": value_grade,
            "value_description": value_description,
            "predicted_lifetime_value": predicted_clv,
            "value_tier": customer.customer_value_tier,
            "rfm_segment": rfm_analysis.get("segment")
        }
    
    def _identify_risk_factors(self, customer: Customer, behavior_analysis: Dict, 
                             lifecycle_analysis: Dict) -> List[Dict]:
        """고객 이탈 위험 요소 식별"""
        risk_factors = []
        
        # 생애주기 기반 위험 요소
        current_stage = lifecycle_analysis.get("current_stage")
        if current_stage in ["at_risk", "dormant", "churned"]:
            risk_factors.append({
                "factor": "lifecycle_stage",
                "severity": "high" if current_stage == "churned" else "medium",
                "description": f"고객이 {current_stage} 단계에 있음",
                "recommended_action": "즉시 리텐션 캠페인 실행 필요"
            })
        
        # 구매 패턴 기반 위험 요소
        purchase_patterns = behavior_analysis.get("구매_패턴", {})
        if purchase_patterns:
            last_purchase_days = lifecycle_analysis.get("metrics", {}).get("마지막_구매_경과일", 0)
            if last_purchase_days > 90:
                risk_factors.append({
                    "factor": "purchase_recency",
                    "severity": "high" if last_purchase_days > 180 else "medium",
                    "description": f"마지막 구매 후 {last_purchase_days}일 경과",
                    "recommended_action": "재구매 유도 캠페인 필요"
                })
            
            # 구매 빈도 감소
            purchase_frequency = lifecycle_analysis.get("metrics", {}).get("구매_빈도_월평균", 0)
            if purchase_frequency < 0.5:  # 월 0.5회 미만
                risk_factors.append({
                    "factor": "low_frequency",
                    "severity": "medium",
                    "description": f"구매 빈도가 낮음 (월 {purchase_frequency:.2f}회)",
                    "recommended_action": "구매 빈도 증가를 위한 인센티브 제공"
                })
        
        # 웹사이트 행동 기반 위험 요소
        website_behavior = behavior_analysis.get("웹사이트_행동", {})
        if website_behavior and website_behavior != {"message": "행동 데이터가 없습니다."}:
            activity_pattern = website_behavior.get("활동_패턴", {})
            browsing_pattern = activity_pattern.get("브라우징_패턴")
            
            if browsing_pattern == "브라우징_중심":
                risk_factors.append({
                    "factor": "low_conversion",
                    "severity": "medium",
                    "description": "많이 탐색하지만 구매 전환율이 낮음",
                    "recommended_action": "구매 전환을 위한 특별 혜택 제공"
                })
        
        return risk_factors
    
    def _identify_opportunities(self, customer: Customer, rfm_analysis: Dict, 
                              behavior_analysis: Dict) -> List[Dict]:
        """고객 관련 기회 요소 식별"""
        opportunities = []
        
        # 세그먼트 기반 기회
        segment = rfm_analysis.get("segment")
        if segment in ["potential_loyalists", "promising"]:
            opportunities.append({
                "opportunity": "loyalty_conversion",
                "potential": "high",
                "description": "충성 고객으로 전환 가능성이 높음",
                "strategy": "로열티 프로그램 참여 유도 및 개인화 서비스 제공"
            })
        
        # 구매 패턴 기반 기회
        product_preferences = behavior_analysis.get("상품_선호도", {})
        if product_preferences and "선호_카테고리" in product_preferences:
            preferred_categories = product_preferences["선호_카테고리"]
            if len(preferred_categories) >= 2:
                opportunities.append({
                    "opportunity": "cross_selling",
                    "potential": "medium",
                    "description": f"다양한 카테고리 구매 이력 ({len(preferred_categories)}개 카테고리)",
                    "strategy": "교차 판매를 통한 객단가 증대"
                })
        
        # 가격대 기반 기회
        if product_preferences and "가격대_선호도" in product_preferences:
            price_prefs = product_preferences["가격대_선호도"]
            avg_price = price_prefs.get("평균_구매가격", 0)
            
            if avg_price > 50000:
                opportunities.append({
                    "opportunity": "premium_upselling",
                    "potential": "high",
                    "description": f"고가 상품 구매 성향 (평균 {avg_price:,.0f}원)",
                    "strategy": "프리미엄 상품 및 럭셔리 라인 추천"
                })
        
        # 구매 주기 기반 기회
        purchase_patterns = behavior_analysis.get("구매_패턴", {})
        if purchase_patterns and "구매_간격_분석" in purchase_patterns:
            interval_analysis = purchase_patterns["구매_간격_분석"]
            if interval_analysis.get("구매간격_패턴") == "정기적_구매":
                opportunities.append({
                    "opportunity": "subscription_model",
                    "potential": "medium",
                    "description": "정기적인 구매 패턴을 보임",
                    "strategy": "구독 서비스 또는 정기 배송 제안"
                })
        
        return opportunities
    
    def _analyze_behavioral_patterns(self, behavior_analysis: Dict) -> Dict:
        """행동 패턴 분석 요약"""
        patterns = {}
        
        # 구매 패턴
        purchase_patterns = behavior_analysis.get("구매_패턴", {})
        if purchase_patterns:
            patterns["구매_특성"] = {
                "주문수": purchase_patterns.get("총_주문수", 0),
                "평균_주문금액": purchase_patterns.get("평균_주문금액", 0),
                "선호_구매시간": purchase_patterns.get("선호_구매시간", []),
                "선호_구매요일": purchase_patterns.get("선호_구매요일", [])
            }
        
        # 상품 선호도
        product_preferences = behavior_analysis.get("상품_선호도", {})
        if product_preferences:
            patterns["상품_선호도"] = {
                "주요_카테고리": product_preferences.get("선호_카테고리", [])[:3],
                "주요_브랜드": product_preferences.get("선호_브랜드", [])[:3],
                "가격대": product_preferences.get("가격대_선호도", {}).get("평균_구매가격", 0)
            }
        
        # 웹사이트 행동
        website_behavior = behavior_analysis.get("웹사이트_행동", {})
        if website_behavior and website_behavior != {"message": "행동 데이터가 없습니다."}:
            patterns["온라인_행동"] = {
                "주요_디바이스": max(website_behavior.get("디바이스_사용현황", {}), 
                                   key=website_behavior.get("디바이스_사용현황", {}).get, default="desktop"),
                "활동_패턴": website_behavior.get("활동_패턴", {}).get("브라우징_패턴", "데이터_부족")
            }
        
        return patterns
    
    def _assess_engagement_level(self, behavior_analysis: Dict, lifecycle_analysis: Dict) -> Dict:
        """고객 참여도 평가"""
        engagement_score = 0
        max_score = 100
        factors = []
        
        # 생애주기 단계 기반 점수
        stage = lifecycle_analysis.get("current_stage")
        stage_scores = {
            "vip": 90,
            "engaged": 80,
            "active": 60,
            "new": 40,
            "promising": 50,
            "at_risk": 30,
            "dormant": 20,
            "churned": 10
        }
        
        stage_score = stage_scores.get(stage, 30)
        engagement_score += stage_score * 0.4  # 40% 가중치
        factors.append(f"생애주기 단계 ({stage}): {stage_score}점")
        
        # 구매 빈도 기반 점수
        metrics = lifecycle_analysis.get("metrics", {})
        purchase_frequency = metrics.get("구매_빈도_월평균", 0)
        frequency_score = min(purchase_frequency * 20, 40)  # 월 2회면 40점
        engagement_score += frequency_score * 0.3  # 30% 가중치
        factors.append(f"구매 빈도 (월 {purchase_frequency:.2f}회): {frequency_score:.1f}점")
        
        # 최근 활동 기반 점수
        last_purchase_days = metrics.get("마지막_구매_경과일", 365)
        if last_purchase_days <= 30:
            recency_score = 30
        elif last_purchase_days <= 90:
            recency_score = 20
        elif last_purchase_days <= 180:
            recency_score = 10
        else:
            recency_score = 0
        
        engagement_score += recency_score * 0.3  # 30% 가중치
        factors.append(f"최근 구매 ({last_purchase_days}일 전): {recency_score}점")
        
        # 참여도 등급 결정
        if engagement_score >= 80:
            engagement_level = "매우 높음"
        elif engagement_score >= 60:
            engagement_level = "높음"
        elif engagement_score >= 40:
            engagement_level = "보통"
        elif engagement_score >= 20:
            engagement_level = "낮음"
        else:
            engagement_level = "매우 낮음"
        
        return {
            "engagement_score": round(engagement_score, 1),
            "engagement_level": engagement_level,
            "scoring_factors": factors,
            "improvement_suggestions": self._get_engagement_improvement_suggestions(engagement_score, stage)
        }
    
    def _get_engagement_improvement_suggestions(self, score: float, stage: str) -> List[str]:
        """참여도 개선 제안"""
        suggestions = []
        
        if score < 40:
            suggestions.extend([
                "개인화된 상품 추천 메일 발송",
                "특별 할인 쿠폰 제공",
                "고객 관심사 기반 콘텐츠 제공"
            ])
        
        if score < 60:
            suggestions.extend([
                "로열티 포인트 프로그램 안내",
                "신상품 출시 알림 서비스",
                "맞춤형 이벤트 참여 유도"
            ])
        
        if stage in ["at_risk", "dormant"]:
            suggestions.extend([
                "윈백 캠페인 실행",
                "고객 피드백 수집",
                "개인 맞춤 서비스 제안"
            ])
        
        return suggestions
    
    def _predict_customer_lifetime_value(self, customer: Customer, rfm_analysis: Dict) -> float:
        """고객 생애 가치 예측"""
        # 단순한 CLV 예측 모델
        total_spent = customer.total_spent or 0
        total_orders = customer.total_orders or 0
        
        if total_orders == 0:
            return 0
        
        avg_order_value = total_spent / total_orders
        customer_lifetime_days = (datetime.now() - customer.registration_date).days
        
        if customer_lifetime_days == 0:
            return avg_order_value
        
        # 예상 생애기간 (2년으로 가정)
        estimated_lifetime_days = 730
        
        # 구매 빈도 (일 단위)
        purchase_frequency_per_day = total_orders / customer_lifetime_days
        
        # 예상 미래 주문 수
        estimated_future_orders = purchase_frequency_per_day * estimated_lifetime_days
        
        # CLV 계산
        predicted_clv = estimated_future_orders * avg_order_value
        
        return round(predicted_clv, 2)
    
    def _create_action_plan(self, customer: Customer, rfm_analysis: Dict, 
                           behavior_analysis: Dict, lifecycle_analysis: Dict) -> Dict:
        """고객별 액션 플랜 생성"""
        # 생애주기 기반 권장 액션
        lifecycle_actions = lifecycle_analysis.get("recommendations", [])
        
        # 위험 요소 기반 액션
        insights = self._generate_customer_insights(customer, rfm_analysis, behavior_analysis, lifecycle_analysis)
        risk_factors = insights.get("risk_factors", [])
        opportunities = insights.get("opportunities", [])
        
        # 우선순위별 액션 분류
        immediate_actions = []  # 즉시 실행
        short_term_actions = []  # 1주일 내
        long_term_actions = []   # 1개월 내
        
        # 위험 요소 대응 액션 (즉시 실행)
        for risk in risk_factors:
            if risk["severity"] == "high":
                immediate_actions.append({
                    "action": risk["recommended_action"],
                    "reason": risk["description"],
                    "priority": "urgent"
                })
        
        # 생애주기 기반 액션
        for action in lifecycle_actions[:3]:  # 상위 3개만
            if action["priority"] == "high":
                immediate_actions.append({
                    "action": action["action"],
                    "reason": action["description"],
                    "priority": "high"
                })
            else:
                short_term_actions.append({
                    "action": action["action"],
                    "reason": action["description"],
                    "priority": action["priority"]
                })
        
        # 기회 요소 기반 액션 (장기)
        for opportunity in opportunities:
            long_term_actions.append({
                "action": opportunity["strategy"],
                "reason": opportunity["description"],
                "priority": opportunity["potential"]
            })
        
        return {
            "immediate_actions": immediate_actions,
            "short_term_actions": short_term_actions,
            "long_term_actions": long_term_actions,
            "total_actions": len(immediate_actions) + len(short_term_actions) + len(long_term_actions),
            "next_review_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
    
    def get_customer_cohort_analysis(self, months: int = 12) -> Dict:
        """고객 코호트 분석"""
        # 월별 신규 고객 코호트 생성
        cohorts = {}
        current_date = datetime.now()
        
        for i in range(months):
            cohort_start = current_date - timedelta(days=30*(i+1))
            cohort_end = current_date - timedelta(days=30*i)
            
            # 해당 월 신규 고객 조회
            new_customers = self.db.query(Customer).filter(
                and_(
                    Customer.registration_date >= cohort_start,
                    Customer.registration_date < cohort_end
                )
            ).all()
            
            if not new_customers:
                continue
            
            cohort_key = cohort_start.strftime("%Y-%m")
            cohort_size = len(new_customers)
            
            # 각 고객의 현재 상태 분석
            active_customers = 0
            total_revenue = 0
            
            for customer in new_customers:
                if customer.last_purchase_date and (current_date - customer.last_purchase_date).days <= 90:
                    active_customers += 1
                total_revenue += customer.total_spent or 0
            
            cohorts[cohort_key] = {
                "cohort_size": cohort_size,
                "active_customers": active_customers,
                "retention_rate": round((active_customers / cohort_size) * 100, 2),
                "total_revenue": total_revenue,
                "revenue_per_customer": round(total_revenue / cohort_size, 2),
                "cohort_start_date": cohort_start.isoformat(),
                "cohort_end_date": cohort_end.isoformat()
            }
        
        return {
            "cohorts": cohorts,
            "analysis_date": current_date.isoformat(),
            "period_months": months
        }
    
    def bulk_customer_analysis_update(self, batch_size: int = 100) -> Dict:
        """대량 고객 분석 업데이트"""
        total_customers = self.db.query(Customer).filter(Customer.is_active == True).count()
        updated_customers = 0
        errors = []
        
        # 배치 단위로 처리
        for offset in range(0, total_customers, batch_size):
            customers = self.db.query(Customer).filter(
                Customer.is_active == True
            ).offset(offset).limit(batch_size).all()
            
            for customer in customers:
                try:
                    # RFM 분석 업데이트
                    self.rfm_analyzer.update_customer_rfm_data()
                    
                    # 행동 분석 업데이트
                    self.behavior_analyzer.update_customer_preferences(customer.id)
                    
                    # 생애주기 분석 업데이트
                    self.lifecycle_analyzer.analyze_customer_lifecycle_stage(customer.id)
                    
                    updated_customers += 1
                    
                except Exception as e:
                    errors.append({
                        "customer_id": customer.id,
                        "error": str(e)
                    })
        
        return {
            "total_customers": total_customers,
            "updated_customers": updated_customers,
            "error_count": len(errors),
            "errors": errors[:10],  # 최대 10개 에러만 반환
            "update_date": datetime.now().isoformat()
        }
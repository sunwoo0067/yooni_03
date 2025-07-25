"""
고객 유지 관리 시스템
이탈 위험 고객 식별, 리텐션 캠페인, 윈백 전략 관리
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from collections import defaultdict
import json

from ...models.crm import (Customer, CustomerLifecycleStage, CustomerSegment, 
                          CustomerInteraction, CustomerCampaign, CustomerLifecycleEvent)
from ...models.order import Order
from ..customer_analysis.customer_analyzer import CustomerAnalyzer


class RetentionManager:
    """고객 유지 관리를 위한 메인 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.customer_analyzer = CustomerAnalyzer(db)
        
        # 이탈 위험 기준 정의
        self.churn_risk_criteria = {
            "high_risk": {
                "days_since_last_purchase": 90,
                "purchase_frequency_decline": 50,  # 50% 감소
                "engagement_score_threshold": 30
            },
            "medium_risk": {
                "days_since_last_purchase": 60,
                "purchase_frequency_decline": 30,
                "engagement_score_threshold": 50
            },
            "low_risk": {
                "days_since_last_purchase": 30,
                "purchase_frequency_decline": 20,
                "engagement_score_threshold": 70
            }
        }
        
        # 리텐션 전략 정의
        self.retention_strategies = {
            "discount_offer": {
                "name": "할인 혜택 제공",
                "description": "개인화된 할인 쿠폰으로 재구매 유도",
                "target_segments": ["at_risk", "dormant"],
                "effectiveness": 0.25
            },
            "personalized_recommendation": {
                "name": "맞춤 상품 추천",
                "description": "구매 이력 기반 개인화 상품 추천",
                "target_segments": ["active", "engaged"],
                "effectiveness": 0.30
            },
            "loyalty_program": {
                "name": "로열티 프로그램",
                "description": "포인트 적립 및 등급별 혜택 제공",
                "target_segments": ["loyal_customers", "champions"],
                "effectiveness": 0.35
            },
            "win_back_campaign": {
                "name": "윈백 캠페인",
                "description": "이탈 고객 대상 특별 혜택 제공",
                "target_segments": ["hibernating", "lost"],
                "effectiveness": 0.20
            },
            "engagement_content": {
                "name": "참여 콘텐츠",
                "description": "교육적/엔터테인먼트 콘텐츠 제공",
                "target_segments": ["new", "promising"],
                "effectiveness": 0.15
            }
        }
    
    def identify_churn_risk_customers(self, risk_level: str = "all") -> Dict:
        """
        이탈 위험 고객 식별
        
        Args:
            risk_level: 위험 수준 (high, medium, low, all)
            
        Returns:
            이탈 위험 고객 목록
        """
        now = datetime.now()
        risk_customers = {
            "high_risk": [],
            "medium_risk": [],
            "low_risk": []
        }
        
        # 활성 고객 중에서 이탈 위험 분석
        active_customers = self.db.query(Customer).filter(
            and_(
                Customer.is_active == True,
                Customer.total_orders > 0  # 최소 1회 이상 구매 이력
            )
        ).all()
        
        for customer in active_customers:
            risk_assessment = self._assess_churn_risk(customer, now)
            
            if risk_assessment["risk_level"] != "no_risk":
                customer_info = {
                    "customer_id": customer.id,
                    "name": customer.name,
                    "email": customer.email,
                    "last_purchase_date": customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
                    "days_since_last_purchase": risk_assessment["days_since_last_purchase"],
                    "total_spent": customer.total_spent,
                    "total_orders": customer.total_orders,
                    "churn_probability": risk_assessment["churn_probability"],
                    "risk_factors": risk_assessment["risk_factors"],
                    "lifecycle_stage": customer.lifecycle_stage.value if customer.lifecycle_stage else None,
                    "segment": customer.segment.value if customer.segment else None
                }
                
                risk_customers[risk_assessment["risk_level"]].append(customer_info)
        
        # 위험 수준별 정렬 (확률 높은 순)
        for level in risk_customers:
            risk_customers[level].sort(key=lambda x: x["churn_probability"], reverse=True)
        
        result = {
            "analysis_date": now.isoformat(),
            "total_customers_analyzed": len(active_customers),
            "summary": {
                "high_risk_count": len(risk_customers["high_risk"]),
                "medium_risk_count": len(risk_customers["medium_risk"]),
                "low_risk_count": len(risk_customers["low_risk"])
            }
        }
        
        if risk_level == "all":
            result.update(risk_customers)
        elif risk_level in risk_customers:
            result[f"{risk_level}_customers"] = risk_customers[risk_level]
        
        return result
    
    def _assess_churn_risk(self, customer: Customer, analysis_date: datetime) -> Dict:
        """개별 고객의 이탈 위험 평가"""
        risk_factors = []
        risk_score = 0
        
        # 1. 마지막 구매일 기준 위험도
        if customer.last_purchase_date:
            days_since_last = (analysis_date - customer.last_purchase_date).days
        else:
            days_since_last = (analysis_date - customer.registration_date).days
        
        if days_since_last >= self.churn_risk_criteria["high_risk"]["days_since_last_purchase"]:
            risk_score += 40
            risk_factors.append(f"마지막 구매 후 {days_since_last}일 경과")
        elif days_since_last >= self.churn_risk_criteria["medium_risk"]["days_since_last_purchase"]:
            risk_score += 25
            risk_factors.append(f"마지막 구매 후 {days_since_last}일 경과")
        elif days_since_last >= self.churn_risk_criteria["low_risk"]["days_since_last_purchase"]:
            risk_score += 10
            risk_factors.append(f"마지막 구매 후 {days_since_last}일 경과")
        
        # 2. 구매 빈도 감소
        if customer.purchase_frequency and customer.purchase_frequency < 0.5:  # 월 0.5회 미만
            risk_score += 30
            risk_factors.append(f"구매 빈도 낮음 (월 {customer.purchase_frequency:.2f}회)")
        
        # 3. 생애주기 단계 기반 위험도
        if customer.lifecycle_stage == CustomerLifecycleStage.AT_RISK:
            risk_score += 35
            risk_factors.append("이탈 위험 단계로 분류됨")
        elif customer.lifecycle_stage == CustomerLifecycleStage.DORMANT:
            risk_score += 45
            risk_factors.append("휴면 고객으로 분류됨")
        elif customer.lifecycle_stage == CustomerLifecycleStage.CHURNED:
            risk_score += 80
            risk_factors.append("이탈 고객으로 분류됨")
        
        # 4. 주문 금액 감소 (최근 3개월 vs 이전 3개월 비교)
        recent_orders_value = self._get_recent_orders_value(customer.id, 90)
        previous_orders_value = self._get_previous_orders_value(customer.id, 90, 180)
        
        if previous_orders_value > 0:
            value_change = (recent_orders_value - previous_orders_value) / previous_orders_value
            if value_change < -0.5:  # 50% 이상 감소
                risk_score += 25
                risk_factors.append(f"주문 금액 {abs(value_change)*100:.1f}% 감소")
        
        # 5. 고객 참여도 (상호작용 빈도)
        recent_interactions = self._get_recent_interactions_count(customer.id, 30)
        if recent_interactions == 0:
            risk_score += 15
            risk_factors.append("최근 30일간 상호작용 없음")
        
        # 위험 수준 결정
        if risk_score >= 70:
            risk_level = "high_risk"
        elif risk_score >= 40:
            risk_level = "medium_risk"
        elif risk_score >= 20:
            risk_level = "low_risk"
        else:
            risk_level = "no_risk"
        
        churn_probability = min(risk_score / 100, 0.95)  # 최대 95%
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "churn_probability": round(churn_probability, 3),
            "risk_factors": risk_factors,
            "days_since_last_purchase": days_since_last
        }
    
    def _get_recent_orders_value(self, customer_id: int, days: int) -> float:
        """최근 N일간 주문 금액 합계"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        result = self.db.query(func.sum(Order.total_amount)).filter(
            and_(
                Order.customer_id == customer_id,
                Order.order_date >= cutoff_date,
                Order.order_status != 'cancelled'
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    def _get_previous_orders_value(self, customer_id: int, period_days: int, start_days_ago: int) -> float:
        """이전 기간 주문 금액 합계"""
        end_date = datetime.now() - timedelta(days=start_days_ago)
        start_date = end_date - timedelta(days=period_days)
        
        result = self.db.query(func.sum(Order.total_amount)).filter(
            and_(
                Order.customer_id == customer_id,
                Order.order_date >= start_date,
                Order.order_date < end_date,
                Order.order_status != 'cancelled'
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    def _get_recent_interactions_count(self, customer_id: int, days: int) -> int:
        """최근 N일간 상호작용 횟수"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return self.db.query(CustomerInteraction).filter(
            and_(
                CustomerInteraction.customer_id == customer_id,
                CustomerInteraction.created_at >= cutoff_date
            )
        ).count()
    
    def create_retention_campaign(self, campaign_data: Dict) -> Dict:
        """
        리텐션 캠페인 생성
        
        Args:
            campaign_data: 캠페인 정보
            
        Returns:
            생성된 캠페인 정보
        """
        # 타겟 고객 식별
        target_criteria = campaign_data.get("target_criteria", {})
        target_customers = self._get_target_customers(target_criteria)
        
        if not target_customers:
            return {"error": "타겟 조건에 맞는 고객이 없습니다."}
        
        # 캠페인 정보 생성
        campaign_info = {
            "campaign_id": f"retention_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "campaign_name": campaign_data.get("name", "리텐션 캠페인"),
            "campaign_type": campaign_data.get("type", "retention"),
            "strategy": campaign_data.get("strategy", "discount_offer"),
            "target_count": len(target_customers),
            "target_criteria": target_criteria,
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }
        
        # 개별 고객별 캠페인 레코드 생성
        customer_campaigns = []
        for customer in target_customers:
            # 개인화된 콘텐츠 생성
            personalized_content = self._generate_personalized_campaign_content(
                customer, campaign_data.get("strategy", "discount_offer")
            )
            
            customer_campaign = CustomerCampaign(
                customer_id=customer.id,
                campaign_id=campaign_info["campaign_id"],
                campaign_name=campaign_info["campaign_name"],
                campaign_type=campaign_info["campaign_type"],
                personalized_content=personalized_content,
                segment_targeted=customer.segment.value if customer.segment else "general"
            )
            
            self.db.add(customer_campaign)
            customer_campaigns.append({
                "customer_id": customer.id,
                "customer_name": customer.name,
                "personalized_content": personalized_content
            })
        
        self.db.commit()
        
        campaign_info["customer_campaigns"] = customer_campaigns
        return campaign_info
    
    def _get_target_customers(self, criteria: Dict) -> List[Customer]:
        """타겟 조건에 맞는 고객 조회"""
        query = self.db.query(Customer).filter(Customer.is_active == True)
        
        # 위험 수준별 필터링
        if "risk_level" in criteria:
            risk_levels = criteria["risk_level"]
            if not isinstance(risk_levels, list):
                risk_levels = [risk_levels]
            
            # 이탈 위험 고객 식별 후 필터링
            if "high_risk" in risk_levels:
                query = query.filter(Customer.lifecycle_stage.in_([
                    CustomerLifecycleStage.AT_RISK,
                    CustomerLifecycleStage.DORMANT,
                    CustomerLifecycleStage.CHURNED
                ]))
        
        # 생애주기 단계 필터링
        if "lifecycle_stages" in criteria:
            stages = [CustomerLifecycleStage(stage) for stage in criteria["lifecycle_stages"]]
            query = query.filter(Customer.lifecycle_stage.in_(stages))
        
        # 세그먼트 필터링
        if "segments" in criteria:
            segments = [CustomerSegment(segment) for segment in criteria["segments"]]
            query = query.filter(Customer.segment.in_(segments))
        
        # 마지막 구매일 기준
        if "days_since_last_purchase_min" in criteria:
            cutoff_date = datetime.now() - timedelta(days=criteria["days_since_last_purchase_min"])
            query = query.filter(Customer.last_purchase_date <= cutoff_date)
        
        # 총 구매금액 기준
        if "total_spent_min" in criteria:
            query = query.filter(Customer.total_spent >= criteria["total_spent_min"])
        if "total_spent_max" in criteria:
            query = query.filter(Customer.total_spent <= criteria["total_spent_max"])
        
        return query.all()
    
    def _generate_personalized_campaign_content(self, customer: Customer, strategy: str) -> Dict:
        """개인화된 캠페인 콘텐츠 생성"""
        content = {
            "customer_name": customer.name or "고객님",
            "strategy": strategy
        }
        
        if strategy == "discount_offer":
            # 고객 가치에 따른 할인율 결정
            if customer.total_spent and customer.total_spent > 500000:
                discount_rate = 25
            elif customer.total_spent and customer.total_spent > 200000:
                discount_rate = 20
            else:
                discount_rate = 15
            
            content.update({
                "discount_rate": discount_rate,
                "message": f"{customer.name or '고객'}님만을 위한 특별 {discount_rate}% 할인 혜택을 드립니다!",
                "cta": f"{discount_rate}% 할인 쿠폰 받기"
            })
        
        elif strategy == "personalized_recommendation":
            # 선호 카테고리 기반 추천
            preferred_categories = customer.preferred_categories or ["인기상품"]
            if isinstance(preferred_categories, dict):
                preferred_categories = list(preferred_categories.keys())
            
            content.update({
                "recommended_categories": preferred_categories[:3],
                "message": f"{customer.name or '고객'}님이 좋아하실 만한 {', '.join(preferred_categories[:2])} 상품을 추천드립니다!",
                "cta": "맞춤 추천 상품 보기"
            })
        
        elif strategy == "win_back_campaign":
            days_since_last_purchase = (datetime.now() - customer.last_purchase_date).days if customer.last_purchase_date else 365
            
            content.update({
                "days_absent": days_since_last_purchase,
                "comeback_offer": 30,  # 30% 할인
                "message": f"{customer.name or '고객'}님, 다시 만나서 반가워요! 돌아오신 것을 환영하며 특별 30% 할인을 드립니다.",
                "cta": "컴백 혜택 받기"
            })
        
        elif strategy == "loyalty_program":
            content.update({
                "points_bonus": customer.total_orders * 100 if customer.total_orders else 500,
                "tier_upgrade": True if customer.customer_value_tier == "bronze" else False,
                "message": f"{customer.name or '고객'}님의 충성도에 감사드리며 보너스 포인트를 드립니다!",
                "cta": "로열티 혜택 확인하기"
            })
        
        else:  # engagement_content
            content.update({
                "content_type": "educational",
                "message": f"{customer.name or '고객'}님을 위한 특별한 콘텐츠를 준비했습니다!",
                "cta": "콘텐츠 보기"
            })
        
        return content
    
    def execute_retention_campaign(self, campaign_id: str, send_immediately: bool = False) -> Dict:
        """
        리텐션 캠페인 실행
        
        Args:
            campaign_id: 캠페인 ID
            send_immediately: 즉시 발송 여부
            
        Returns:
            실행 결과
        """
        # 캠페인 대상 고객 조회
        customer_campaigns = self.db.query(CustomerCampaign).filter(
            CustomerCampaign.campaign_id == campaign_id
        ).all()
        
        if not customer_campaigns:
            return {"error": "캠페인을 찾을 수 없습니다."}
        
        execution_results = {
            "campaign_id": campaign_id,
            "execution_date": datetime.now().isoformat(),
            "total_targets": len(customer_campaigns),
            "sent_count": 0,
            "failed_count": 0,
            "results": []
        }
        
        for customer_campaign in customer_campaigns:
            try:
                # 발송 시뮬레이션 (실제 구현시 이메일/SMS 서비스 연동)
                send_result = self._simulate_campaign_send(customer_campaign)
                
                # 캠페인 레코드 업데이트
                customer_campaign.sent_at = datetime.now()
                customer_campaign.delivery_status = "sent" if send_result["success"] else "failed"
                
                if send_result["success"]:
                    execution_results["sent_count"] += 1
                else:
                    execution_results["failed_count"] += 1
                
                execution_results["results"].append({
                    "customer_id": customer_campaign.customer_id,
                    "status": customer_campaign.delivery_status,
                    "message": send_result["message"]
                })
                
            except Exception as e:
                execution_results["failed_count"] += 1
                execution_results["results"].append({
                    "customer_id": customer_campaign.customer_id,
                    "status": "error",
                    "message": str(e)
                })
        
        self.db.commit()
        
        execution_results["success_rate"] = (execution_results["sent_count"] / execution_results["total_targets"]) * 100
        
        return execution_results
    
    def _simulate_campaign_send(self, customer_campaign: CustomerCampaign) -> Dict:
        """캠페인 발송 시뮬레이션"""
        # 실제 구현시에는 이메일/SMS 서비스와 연동
        import random
        
        # 90% 성공률로 시뮬레이션
        success = random.random() < 0.9
        
        if success:
            return {
                "success": True,
                "message": f"캠페인이 고객 ID {customer_campaign.customer_id}에게 성공적으로 발송되었습니다."
            }
        else:
            return {
                "success": False,
                "message": "발송 실패: 이메일 주소 오류"
            }
    
    def track_campaign_performance(self, campaign_id: str, days: int = 30) -> Dict:
        """
        캠페인 성과 추적
        
        Args:
            campaign_id: 캠페인 ID
            days: 추적 기간 (일)
            
        Returns:
            캠페인 성과 데이터
        """
        # 캠페인 정보 조회
        customer_campaigns = self.db.query(CustomerCampaign).filter(
            CustomerCampaign.campaign_id == campaign_id
        ).all()
        
        if not customer_campaigns:
            return {"error": "캠페인을 찾을 수 없습니다."}
        
        # 성과 집계
        total_sent = len([c for c in customer_campaigns if c.sent_at])
        total_opened = len([c for c in customer_campaigns if c.opened_at])
        total_clicked = len([c for c in customer_campaigns if c.clicked_at])
        total_converted = len([c for c in customer_campaigns if c.converted_at])
        total_revenue = sum(c.revenue_attributed or 0 for c in customer_campaigns)
        
        # 캠페인 이후 고객 행동 분석
        campaign_start_date = min(c.sent_at for c in customer_campaigns if c.sent_at)
        analysis_end_date = campaign_start_date + timedelta(days=days)
        
        customer_ids = [c.customer_id for c in customer_campaigns]
        
        # 캠페인 이후 구매 분석
        post_campaign_orders = self.db.query(Order).filter(
            and_(
                Order.customer_id.in_(customer_ids),
                Order.order_date >= campaign_start_date,
                Order.order_date <= analysis_end_date,
                Order.order_status != 'cancelled'
            )
        ).all()
        
        # 리텐션 효과 측정
        retained_customers = len(set(order.customer_id for order in post_campaign_orders))
        retention_rate = (retained_customers / total_sent) * 100 if total_sent > 0 else 0
        
        performance_data = {
            "campaign_id": campaign_id,
            "analysis_period": f"{campaign_start_date.isoformat()} ~ {analysis_end_date.isoformat()}",
            "delivery_metrics": {
                "total_sent": total_sent,
                "delivery_rate": (total_sent / len(customer_campaigns)) * 100 if customer_campaigns else 0
            },
            "engagement_metrics": {
                "total_opened": total_opened,
                "total_clicked": total_clicked,
                "open_rate": (total_opened / total_sent) * 100 if total_sent > 0 else 0,
                "click_rate": (total_clicked / total_sent) * 100 if total_sent > 0 else 0,
                "click_through_rate": (total_clicked / total_opened) * 100 if total_opened > 0 else 0
            },
            "conversion_metrics": {
                "total_conversions": total_converted,
                "conversion_rate": (total_converted / total_sent) * 100 if total_sent > 0 else 0,
                "revenue_generated": total_revenue,
                "revenue_per_recipient": total_revenue / total_sent if total_sent > 0 else 0
            },
            "retention_metrics": {
                "retained_customers": retained_customers,
                "retention_rate": round(retention_rate, 2),
                "post_campaign_orders": len(post_campaign_orders),
                "avg_orders_per_retained_customer": len(post_campaign_orders) / retained_customers if retained_customers > 0 else 0
            }
        }
        
        return performance_data
    
    def get_retention_insights(self, period_days: int = 90) -> Dict:
        """
        리텐션 인사이트 제공
        
        Args:
            period_days: 분석 기간 (일)
            
        Returns:
            리텐션 인사이트
        """
        insights = {
            "analysis_period_days": period_days,
            "generated_at": datetime.now().isoformat()
        }
        
        # 1. 전체 리텐션 현황
        retention_overview = self._get_retention_overview(period_days)
        insights["retention_overview"] = retention_overview
        
        # 2. 세그먼트별 리텐션 분석
        segment_retention = self._analyze_segment_retention(period_days)
        insights["segment_retention"] = segment_retention
        
        # 3. 이탈 패턴 분석
        churn_patterns = self._analyze_churn_patterns(period_days)
        insights["churn_patterns"] = churn_patterns
        
        # 4. 리텐션 전략 효과성 분석
        strategy_effectiveness = self._analyze_strategy_effectiveness(period_days)
        insights["strategy_effectiveness"] = strategy_effectiveness
        
        # 5. 액션 권장사항
        recommendations = self._generate_retention_recommendations(insights)
        insights["recommendations"] = recommendations
        
        return insights
    
    def _get_retention_overview(self, period_days: int) -> Dict:
        """리텐션 전체 현황"""
        start_date = datetime.now() - timedelta(days=period_days)
        
        # 기간 내 활성 고객 수
        active_customers = self.db.query(Customer).filter(
            and_(
                Customer.is_active == True,
                Customer.last_purchase_date >= start_date
            )
        ).count()
        
        # 총 고객 수
        total_customers = self.db.query(Customer).filter(Customer.is_active == True).count()
        
        # 이탈 위험 고객 수
        churn_risk_analysis = self.identify_churn_risk_customers()
        high_risk_count = churn_risk_analysis["summary"]["high_risk_count"]
        medium_risk_count = churn_risk_analysis["summary"]["medium_risk_count"]
        
        return {
            "total_active_customers": total_customers,
            "recently_active_customers": active_customers,
            "activity_rate": (active_customers / total_customers) * 100 if total_customers > 0 else 0,
            "high_churn_risk_customers": high_risk_count,
            "medium_churn_risk_customers": medium_risk_count,
            "total_at_risk": high_risk_count + medium_risk_count,
            "retention_health_score": self._calculate_retention_health_score(active_customers, total_customers, high_risk_count)
        }
    
    def _analyze_segment_retention(self, period_days: int) -> Dict:
        """세그먼트별 리텐션 분석"""
        start_date = datetime.now() - timedelta(days=period_days)
        
        segment_data = {}
        
        for segment in CustomerSegment:
            segment_customers = self.db.query(Customer).filter(
                and_(
                    Customer.segment == segment,
                    Customer.is_active == True
                )
            ).all()
            
            if not segment_customers:
                continue
            
            # 최근 활성 고객 수
            active_in_period = len([
                c for c in segment_customers 
                if c.last_purchase_date and c.last_purchase_date >= start_date
            ])
            
            segment_data[segment.value] = {
                "total_customers": len(segment_customers),
                "active_customers": active_in_period,
                "retention_rate": (active_in_period / len(segment_customers)) * 100,
                "avg_clv": sum(c.lifetime_value or 0 for c in segment_customers) / len(segment_customers),
                "avg_orders": sum(c.total_orders or 0 for c in segment_customers) / len(segment_customers)
            }
        
        return segment_data
    
    def _analyze_churn_patterns(self, period_days: int) -> Dict:
        """이탈 패턴 분석"""
        # 이탈 고객 (최근 180일간 구매 없음)
        churn_cutoff = datetime.now() - timedelta(days=180)
        
        churned_customers = self.db.query(Customer).filter(
            and_(
                Customer.is_active == True,
                or_(
                    Customer.last_purchase_date < churn_cutoff,
                    Customer.last_purchase_date.is_(None)
                )
            )
        ).all()
        
        # 이탈 시점 분석
        churn_timeline = defaultdict(int)
        for customer in churned_customers:
            if customer.last_purchase_date:
                days_since_last = (datetime.now() - customer.last_purchase_date).days
                
                if days_since_last < 30:
                    period = "30일_이내"
                elif days_since_last < 90:
                    period = "30-90일"
                elif days_since_last < 180:
                    period = "90-180일"
                else:
                    period = "180일_이상"
                
                churn_timeline[period] += 1
        
        # 이탈 요인 분석
        churn_factors = {
            "저빈도_구매": len([c for c in churned_customers if (c.total_orders or 0) < 3]),
            "저금액_구매": len([c for c in churned_customers if (c.total_spent or 0) < 50000]),
            "신규고객_이탈": len([c for c in churned_customers if (datetime.now() - c.registration_date).days < 60])
        }
        
        return {
            "total_churned_customers": len(churned_customers),
            "churn_timeline": dict(churn_timeline),
            "churn_factors": churn_factors,
            "churn_rate": (len(churned_customers) / self.db.query(Customer).filter(Customer.is_active == True).count()) * 100
        }
    
    def _analyze_strategy_effectiveness(self, period_days: int) -> Dict:
        """리텐션 전략 효과성 분석"""
        # 최근 캠페인 성과 분석
        recent_campaigns = self.db.query(CustomerCampaign).filter(
            CustomerCampaign.sent_at >= datetime.now() - timedelta(days=period_days)
        ).all()
        
        if not recent_campaigns:
            return {"message": "분석할 캠페인 데이터가 없습니다."}
        
        # 캠페인 타입별 성과
        campaign_performance = defaultdict(lambda: {
            "total_sent": 0,
            "total_conversions": 0,
            "total_revenue": 0
        })
        
        for campaign in recent_campaigns:
            campaign_type = campaign.campaign_type or "general"
            campaign_performance[campaign_type]["total_sent"] += 1
            
            if campaign.converted_at:
                campaign_performance[campaign_type]["total_conversions"] += 1
            
            if campaign.revenue_attributed:
                campaign_performance[campaign_type]["total_revenue"] += campaign.revenue_attributed
        
        # 전환율 및 ROI 계산
        effectiveness_data = {}
        for campaign_type, metrics in campaign_performance.items():
            effectiveness_data[campaign_type] = {
                "conversion_rate": (metrics["total_conversions"] / metrics["total_sent"]) * 100 if metrics["total_sent"] > 0 else 0,
                "revenue_per_campaign": metrics["total_revenue"] / metrics["total_sent"] if metrics["total_sent"] > 0 else 0,
                "total_campaigns": metrics["total_sent"],
                "total_revenue": metrics["total_revenue"]
            }
        
        return effectiveness_data
    
    def _calculate_retention_health_score(self, active_customers: int, total_customers: int, high_risk_count: int) -> int:
        """리텐션 건강도 점수 계산 (0-100)"""
        if total_customers == 0:
            return 0
        
        # 활성도 점수 (0-50)
        activity_score = (active_customers / total_customers) * 50
        
        # 위험 고객 비율에 따른 감점 (0-50)
        risk_ratio = high_risk_count / total_customers
        risk_score = max(0, 50 - (risk_ratio * 100))
        
        return min(int(activity_score + risk_score), 100)
    
    def _generate_retention_recommendations(self, insights: Dict) -> List[Dict]:
        """리텐션 개선 권장사항 생성"""
        recommendations = []
        
        retention_overview = insights.get("retention_overview", {})
        health_score = retention_overview.get("retention_health_score", 0)
        
        # 건강도 점수 기반 권장사항
        if health_score < 50:
            recommendations.append({
                "priority": "high",
                "category": "urgent_action",
                "title": "긴급 리텐션 프로그램 실행",
                "description": "리텐션 건강도가 낮습니다. 즉시 포괄적인 고객 유지 프로그램을 실행하세요.",
                "actions": [
                    "이탈 위험 고객 대상 긴급 윈백 캠페인",
                    "고객 만족도 조사 실시",
                    "개인화된 혜택 제공"
                ]
            })
        
        # 이탈 위험 고객 대응
        high_risk_count = retention_overview.get("high_churn_risk_customers", 0)
        if high_risk_count > 0:
            recommendations.append({
                "priority": "high",
                "category": "churn_prevention",
                "title": "고위험 고객 즉시 대응",
                "description": f"{high_risk_count}명의 고위험 이탈 고객에 대한 즉시 대응이 필요합니다.",
                "actions": [
                    "개인별 맞춤 할인 혜택 제공",
                    "고객 상담 연결",
                    "특별 서비스 제안"
                ]
            })
        
        # 세그먼트별 권장사항
        segment_retention = insights.get("segment_retention", {})
        for segment, data in segment_retention.items():
            if data["retention_rate"] < 60:  # 60% 미만인 세그먼트
                recommendations.append({
                    "priority": "medium",
                    "category": "segment_improvement",
                    "title": f"{segment} 세그먼트 리텐션 개선",
                    "description": f"{segment} 세그먼트의 리텐션율이 {data['retention_rate']:.1f}%로 낮습니다.",
                    "actions": [
                        f"{segment} 특화 캠페인 기획",
                        "세그먼트별 맞춤 혜택 개발",
                        "고객 여정 분석 및 개선"
                    ]
                })
        
        return recommendations
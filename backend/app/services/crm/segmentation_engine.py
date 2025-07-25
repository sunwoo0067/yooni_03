"""
고객 세분화 엔진
다양한 기준으로 고객을 세분화하고 타겟 그룹을 생성하는 시스템
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, text
from collections import defaultdict
import json

from ...models.crm import Customer, CustomerSegment, CustomerLifecycleStage, CustomerBehavior
from ...models.order import Order
from ...models.product import Product


class SegmentationEngine:
    """고객 세분화를 수행하는 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 사전 정의된 세분화 규칙
        self.predefined_segments = {
            "high_value_customers": {
                "name": "고가치 고객",
                "description": "총 구매액이 높고 충성도가 높은 고객들",
                "criteria": {
                    "total_spent_min": 500000,
                    "total_orders_min": 5,
                    "lifecycle_stage": ["vip", "engaged", "active"]
                }
            },
            "at_risk_customers": {
                "name": "이탈 위험 고객",
                "description": "과거 활성 고객이었으나 최근 활동이 감소한 고객들",
                "criteria": {
                    "lifecycle_stage": ["at_risk"],
                    "churn_probability_min": 0.6
                }
            },
            "new_customers": {
                "name": "신규 고객",
                "description": "최근 가입한 신규 고객들",
                "criteria": {
                    "lifecycle_stage": ["new"],
                    "registration_days_max": 30
                }
            },
            "loyal_customers": {
                "name": "충성 고객",
                "description": "지속적으로 구매하는 충성도 높은 고객들",
                "criteria": {
                    "segment": ["champions", "loyal_customers"],
                    "purchase_frequency_min": 2.0  # 월 2회 이상
                }
            },
            "dormant_customers": {
                "name": "휴면 고객",
                "description": "장기간 구매하지 않은 휴면 고객들",
                "criteria": {
                    "lifecycle_stage": ["dormant", "hibernating"],
                    "days_since_last_purchase_min": 90
                }
            },
            "mobile_users": {
                "name": "모바일 사용자",
                "description": "주로 모바일에서 구매하는 고객들",
                "criteria": {
                    "mobile_usage_rate_min": 0.7
                }
            },
            "price_sensitive": {
                "name": "가격 민감 고객",
                "description": "저가 상품을 주로 구매하는 고객들",
                "criteria": {
                    "average_order_value_max": 30000
                }
            },
            "premium_buyers": {
                "name": "프리미엄 구매자",
                "description": "고가 상품을 선호하는 고객들",
                "criteria": {
                    "average_order_value_min": 100000
                }
            }
        }
    
    def create_custom_segment(self, segment_name: str, criteria: Dict, 
                            description: str = None) -> Dict:
        """
        커스텀 고객 세그먼트 생성
        
        Args:
            segment_name: 세그먼트 이름
            criteria: 세분화 기준
            description: 세그먼트 설명
            
        Returns:
            생성된 세그먼트 정보
        """
        # 세그먼트에 속하는 고객 조회
        customers = self._get_customers_by_criteria(criteria)
        
        segment_info = {
            "segment_name": segment_name,
            "description": description or f"{segment_name} 세그먼트",
            "criteria": criteria,
            "customer_count": len(customers),
            "customer_ids": [c.id for c in customers],
            "created_at": datetime.now().isoformat()
        }
        
        # 세그먼트 통계 생성
        segment_stats = self._calculate_segment_statistics(customers)
        segment_info.update(segment_stats)
        
        return segment_info
    
    def get_predefined_segment(self, segment_key: str) -> Dict:
        """
        사전 정의된 세그먼트 조회
        
        Args:
            segment_key: 세그먼트 키
            
        Returns:
            세그먼트 정보
        """
        if segment_key not in self.predefined_segments:
            return {"error": f"'{segment_key}' 세그먼트를 찾을 수 없습니다."}
        
        segment_config = self.predefined_segments[segment_key]
        customers = self._get_customers_by_criteria(segment_config["criteria"])
        
        segment_info = {
            "segment_key": segment_key,
            "segment_name": segment_config["name"],
            "description": segment_config["description"],
            "criteria": segment_config["criteria"],
            "customer_count": len(customers),
            "customer_ids": [c.id for c in customers],
            "updated_at": datetime.now().isoformat()
        }
        
        # 세그먼트 통계
        segment_stats = self._calculate_segment_statistics(customers)
        segment_info.update(segment_stats)
        
        return segment_info
    
    def _get_customers_by_criteria(self, criteria: Dict) -> List[Customer]:
        """기준에 따라 고객 필터링"""
        query = self.db.query(Customer).filter(Customer.is_active == True)
        
        # 총 구매금액 기준
        if "total_spent_min" in criteria:
            query = query.filter(Customer.total_spent >= criteria["total_spent_min"])
        if "total_spent_max" in criteria:
            query = query.filter(Customer.total_spent <= criteria["total_spent_max"])
        
        # 주문 수 기준
        if "total_orders_min" in criteria:
            query = query.filter(Customer.total_orders >= criteria["total_orders_min"])
        if "total_orders_max" in criteria:
            query = query.filter(Customer.total_orders <= criteria["total_orders_max"])
        
        # 평균 주문금액 기준
        if "average_order_value_min" in criteria:
            query = query.filter(Customer.average_order_value >= criteria["average_order_value_min"])
        if "average_order_value_max" in criteria:
            query = query.filter(Customer.average_order_value <= criteria["average_order_value_max"])
        
        # 생애주기 단계 기준
        if "lifecycle_stage" in criteria:
            stages = criteria["lifecycle_stage"]
            if isinstance(stages, str):
                stages = [stages]
            stage_enums = [CustomerLifecycleStage(stage) for stage in stages]
            query = query.filter(Customer.lifecycle_stage.in_(stage_enums))
        
        # RFM 세그먼트 기준
        if "segment" in criteria:
            segments = criteria["segment"]
            if isinstance(segments, str):
                segments = [segments]
            segment_enums = [CustomerSegment(segment) for segment in segments]
            query = query.filter(Customer.segment.in_(segment_enums))
        
        # 가치 등급 기준
        if "customer_value_tier" in criteria:
            tiers = criteria["customer_value_tier"]
            if isinstance(tiers, str):
                tiers = [tiers]
            query = query.filter(Customer.customer_value_tier.in_(tiers))
        
        # 이탈 확률 기준
        if "churn_probability_min" in criteria:
            query = query.filter(Customer.churn_probability >= criteria["churn_probability_min"])
        if "churn_probability_max" in criteria:
            query = query.filter(Customer.churn_probability <= criteria["churn_probability_max"])
        
        # 모바일 사용률 기준
        if "mobile_usage_rate_min" in criteria:
            query = query.filter(Customer.mobile_usage_rate >= criteria["mobile_usage_rate_min"])
        if "mobile_usage_rate_max" in criteria:
            query = query.filter(Customer.mobile_usage_rate <= criteria["mobile_usage_rate_max"])
        
        # 가입일 기준
        if "registration_days_max" in criteria:
            cutoff_date = datetime.now() - timedelta(days=criteria["registration_days_max"])
            query = query.filter(Customer.registration_date >= cutoff_date)
        if "registration_days_min" in criteria:
            cutoff_date = datetime.now() - timedelta(days=criteria["registration_days_min"])
            query = query.filter(Customer.registration_date <= cutoff_date)
        
        # 마지막 구매일 기준
        if "days_since_last_purchase_min" in criteria:
            cutoff_date = datetime.now() - timedelta(days=criteria["days_since_last_purchase_min"])
            query = query.filter(Customer.last_purchase_date <= cutoff_date)
        if "days_since_last_purchase_max" in criteria:
            cutoff_date = datetime.now() - timedelta(days=criteria["days_since_last_purchase_max"])
            query = query.filter(Customer.last_purchase_date >= cutoff_date)
        
        # 구매 빈도 기준
        if "purchase_frequency_min" in criteria:
            query = query.filter(Customer.purchase_frequency >= criteria["purchase_frequency_min"])
        if "purchase_frequency_max" in criteria:
            query = query.filter(Customer.purchase_frequency <= criteria["purchase_frequency_max"])
        
        # 도시 기준
        if "cities" in criteria:
            query = query.filter(Customer.city.in_(criteria["cities"]))
        
        # 유입 채널 기준
        if "acquisition_channels" in criteria:
            query = query.filter(Customer.acquisition_channel.in_(criteria["acquisition_channels"]))
        
        # 연령 기준
        if "age_min" in criteria:
            query = query.filter(Customer.age >= criteria["age_min"])
        if "age_max" in criteria:
            query = query.filter(Customer.age <= criteria["age_max"])
        
        # 성별 기준
        if "gender" in criteria:
            genders = criteria["gender"]
            if isinstance(genders, str):
                genders = [genders]
            query = query.filter(Customer.gender.in_(genders))
        
        return query.all()
    
    def _calculate_segment_statistics(self, customers: List[Customer]) -> Dict:
        """세그먼트 통계 계산"""
        if not customers:
            return {
                "statistics": {
                    "평균_총구매금액": 0,
                    "평균_주문수": 0,
                    "평균_주문금액": 0,
                    "평균_생애가치": 0
                }
            }
        
        total_spent_sum = sum(c.total_spent or 0 for c in customers)
        total_orders_sum = sum(c.total_orders or 0 for c in customers)
        lifetime_value_sum = sum(c.lifetime_value or 0 for c in customers)
        
        customer_count = len(customers)
        
        # 생애주기 분포
        lifecycle_distribution = defaultdict(int)
        for customer in customers:
            stage = customer.lifecycle_stage.value if customer.lifecycle_stage else "미분류"
            lifecycle_distribution[stage] += 1
        
        # 세그먼트 분포
        segment_distribution = defaultdict(int)
        for customer in customers:
            segment = customer.segment.value if customer.segment else "미분류"
            segment_distribution[segment] += 1
        
        # 가치 등급 분포
        tier_distribution = defaultdict(int)
        for customer in customers:
            tier = customer.customer_value_tier or "미분류"
            tier_distribution[tier] += 1
        
        # 성별 분포
        gender_distribution = defaultdict(int)
        for customer in customers:
            gender = customer.gender or "미분류"
            gender_distribution[gender] += 1
        
        # 연령대 분포
        age_distribution = defaultdict(int)
        for customer in customers:
            if customer.age:
                if customer.age < 20:
                    age_group = "10대"
                elif customer.age < 30:
                    age_group = "20대"
                elif customer.age < 40:
                    age_group = "30대"
                elif customer.age < 50:
                    age_group = "40대"
                elif customer.age < 60:
                    age_group = "50대"
                else:
                    age_group = "60대이상"
            else:
                age_group = "미분류"
            age_distribution[age_group] += 1
        
        return {
            "statistics": {
                "평균_총구매금액": round(total_spent_sum / customer_count, 2),
                "평균_주문수": round(total_orders_sum / customer_count, 2),
                "평균_주문금액": round(total_spent_sum / total_orders_sum, 2) if total_orders_sum > 0 else 0,
                "평균_생애가치": round(lifetime_value_sum / customer_count, 2),
                "총_구매금액": total_spent_sum,
                "총_주문수": total_orders_sum
            },
            "distributions": {
                "생애주기_분포": dict(lifecycle_distribution),
                "세그먼트_분포": dict(segment_distribution),
                "가치등급_분포": dict(tier_distribution),
                "성별_분포": dict(gender_distribution),
                "연령대_분포": dict(age_distribution)
            }
        }
    
    def compare_segments(self, segment_configs: List[Dict]) -> Dict:
        """
        여러 세그먼트 비교 분석
        
        Args:
            segment_configs: 비교할 세그먼트 설정들
            
        Returns:
            세그먼트 비교 결과
        """
        comparison_results = {}
        
        for config in segment_configs:
            segment_name = config.get("name", "Unnamed Segment")
            criteria = config.get("criteria", {})
            
            customers = self._get_customers_by_criteria(criteria)
            stats = self._calculate_segment_statistics(customers)
            
            comparison_results[segment_name] = {
                "customer_count": len(customers),
                "criteria": criteria,
                **stats
            }
        
        # 세그먼트 간 중복 분석
        overlap_analysis = self._analyze_segment_overlap(segment_configs)
        
        return {
            "segment_comparison": comparison_results,
            "overlap_analysis": overlap_analysis,
            "comparison_date": datetime.now().isoformat()
        }
    
    def _analyze_segment_overlap(self, segment_configs: List[Dict]) -> Dict:
        """세그먼트 간 중복 분석"""
        if len(segment_configs) < 2:
            return {"message": "중복 분석을 위해서는 최소 2개의 세그먼트가 필요합니다."}
        
        # 각 세그먼트의 고객 ID 집합 생성
        segment_customers = {}
        for config in segment_configs:
            segment_name = config.get("name", "Unnamed Segment")
            criteria = config.get("criteria", {})
            customers = self._get_customers_by_criteria(criteria)
            segment_customers[segment_name] = set(c.id for c in customers)
        
        # 중복 분석
        overlap_matrix = {}
        segment_names = list(segment_customers.keys())
        
        for i, segment1 in enumerate(segment_names):
            overlap_matrix[segment1] = {}
            for j, segment2 in enumerate(segment_names):
                if i != j:
                    # 교집합 계산
                    intersection = segment_customers[segment1] & segment_customers[segment2]
                    union = segment_customers[segment1] | segment_customers[segment2]
                    
                    overlap_count = len(intersection)
                    overlap_percentage = (overlap_count / len(segment_customers[segment1])) * 100 if segment_customers[segment1] else 0
                    jaccard_index = len(intersection) / len(union) if union else 0
                    
                    overlap_matrix[segment1][segment2] = {
                        "overlap_count": overlap_count,
                        "overlap_percentage": round(overlap_percentage, 2),
                        "jaccard_index": round(jaccard_index, 3)
                    }
        
        return {
            "overlap_matrix": overlap_matrix,
            "총_고유고객수": len(set.union(*segment_customers.values())) if segment_customers else 0
        }
    
    def get_segment_evolution(self, segment_config: Dict, days: int = 90) -> Dict:
        """
        세그먼트 변화 추이 분석
        
        Args:
            segment_config: 세그먼트 설정
            days: 분석할 일수
            
        Returns:
            세그먼트 변화 추이
        """
        end_date = datetime.now()
        evolution_data = []
        
        # 주간 단위로 세그먼트 크기 추적
        for week in range(0, days // 7):
            analysis_date = end_date - timedelta(days=week * 7)
            
            # 해당 시점의 고객 데이터로 세그먼트 분석
            # 실제로는 시계열 데이터가 필요하지만, 현재는 단순화된 버전
            customers = self._get_customers_by_criteria(segment_config["criteria"])
            
            # 해당 시점까지의 고객만 필터링 (단순화)
            filtered_customers = [
                c for c in customers 
                if c.registration_date <= analysis_date
            ]
            
            evolution_data.append({
                "date": analysis_date.strftime("%Y-%m-%d"),
                "customer_count": len(filtered_customers),
                "week": week
            })
        
        # 트렌드 분석
        if len(evolution_data) >= 2:
            first_count = evolution_data[-1]["customer_count"]  # 가장 오래된 데이터
            last_count = evolution_data[0]["customer_count"]    # 가장 최근 데이터
            
            if first_count > 0:
                growth_rate = ((last_count - first_count) / first_count) * 100
            else:
                growth_rate = 0
            
            trend = "증가" if growth_rate > 5 else "감소" if growth_rate < -5 else "안정"
        else:
            growth_rate = 0
            trend = "데이터 부족"
        
        return {
            "segment_name": segment_config.get("name", "Unnamed Segment"),
            "evolution_data": list(reversed(evolution_data)),  # 시간순 정렬
            "growth_rate_percentage": round(growth_rate, 2),
            "trend": trend,
            "analysis_period_days": days,
            "current_size": evolution_data[0]["customer_count"] if evolution_data else 0
        }
    
    def get_actionable_segments(self) -> Dict:
        """
        액션 가능한 세그먼트 제안
        
        Returns:
            액션 가능한 세그먼트 목록과 권장 액션
        """
        actionable_segments = {}
        
        # 각 사전 정의 세그먼트에 대한 액션 제안
        for segment_key, segment_config in self.predefined_segments.items():
            segment_info = self.get_predefined_segment(segment_key)
            
            if "error" not in segment_info and segment_info["customer_count"] > 0:
                # 세그먼트별 권장 액션 정의
                recommended_actions = self._get_segment_actions(segment_key, segment_info)
                
                actionable_segments[segment_key] = {
                    "segment_name": segment_info["segment_name"],
                    "customer_count": segment_info["customer_count"],
                    "description": segment_info["description"],
                    "recommended_actions": recommended_actions,
                    "priority": self._calculate_segment_priority(segment_key, segment_info)
                }
        
        # 우선순위별 정렬
        sorted_segments = dict(sorted(
            actionable_segments.items(),
            key=lambda x: {"high": 3, "medium": 2, "low": 1}[x[1]["priority"]],
            reverse=True
        ))
        
        return {
            "actionable_segments": sorted_segments,
            "total_segments": len(sorted_segments),
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_segment_actions(self, segment_key: str, segment_info: Dict) -> List[Dict]:
        """세그먼트별 권장 액션 반환"""
        actions_map = {
            "high_value_customers": [
                {"action": "VIP 프로그램 초대", "type": "retention", "urgency": "medium"},
                {"action": "개인 맞춤 서비스 제공", "type": "engagement", "urgency": "low"},
                {"action": "신상품 우선 안내", "type": "upselling", "urgency": "low"}
            ],
            "at_risk_customers": [
                {"action": "즉시 리텐션 캠페인 실행", "type": "retention", "urgency": "high"},
                {"action": "개인화된 할인 쿠폰 발송", "type": "promotion", "urgency": "high"},
                {"action": "고객 피드백 수집", "type": "feedback", "urgency": "medium"}
            ],
            "new_customers": [
                {"action": "온보딩 시퀀스 발송", "type": "onboarding", "urgency": "high"},
                {"action": "첫 구매 인센티브 제공", "type": "promotion", "urgency": "high"},
                {"action": "상품 추천 시스템 활성화", "type": "recommendation", "urgency": "medium"}
            ],
            "loyal_customers": [
                {"action": "로열티 포인트 보너스", "type": "reward", "urgency": "medium"},
                {"action": "추천 프로그램 참여 유도", "type": "referral", "urgency": "low"},
                {"action": "브랜드 앰버서더 프로그램 초대", "type": "engagement", "urgency": "low"}
            ],
            "dormant_customers": [
                {"action": "윈백 캠페인 실행", "type": "reactivation", "urgency": "high"},
                {"action": "특별 복귀 혜택 제공", "type": "promotion", "urgency": "high"},
                {"action": "관심사 기반 콘텐츠 발송", "type": "content", "urgency": "medium"}
            ],
            "mobile_users": [
                {"action": "모바일 앱 푸시 알림 최적화", "type": "optimization", "urgency": "medium"},
                {"action": "모바일 전용 할인 제공", "type": "promotion", "urgency": "medium"},
                {"action": "모바일 결제 편의성 강화", "type": "ux_improvement", "urgency": "low"}
            ],
            "price_sensitive": [
                {"action": "가격 할인 프로모션", "type": "promotion", "urgency": "medium"},
                {"action": "번들 상품 제안", "type": "bundling", "urgency": "medium"},
                {"action": "적립금/포인트 혜택 강화", "type": "reward", "urgency": "low"}
            ],
            "premium_buyers": [
                {"action": "프리미엄 상품 라인 추천", "type": "upselling", "urgency": "medium"},
                {"action": "럭셔리 브랜드 협업 안내", "type": "partnership", "urgency": "low"},
                {"action": "컨시어지 서비스 제공", "type": "premium_service", "urgency": "low"}
            ]
        }
        
        return actions_map.get(segment_key, [
            {"action": "개인화 마케팅", "type": "marketing", "urgency": "medium"}
        ])
    
    def _calculate_segment_priority(self, segment_key: str, segment_info: Dict) -> str:
        """세그먼트 우선순위 계산"""
        customer_count = segment_info["customer_count"]
        
        # 긴급도가 높은 세그먼트
        if segment_key in ["at_risk_customers", "dormant_customers"]:
            return "high"
        
        # 가치가 높은 세그먼트
        if segment_key in ["high_value_customers", "loyal_customers"] and customer_count > 100:
            return "high"
        
        # 기회가 큰 세그먼트
        if segment_key in ["new_customers", "premium_buyers"] and customer_count > 50:
            return "medium"
        
        # 고객 수가 적으면 우선순위 낮음
        if customer_count < 10:
            return "low"
        
        return "medium"
    
    def export_segment_customers(self, segment_config: Dict, 
                               export_fields: List[str] = None) -> Dict:
        """
        세그먼트 고객 목록 내보내기
        
        Args:
            segment_config: 세그먼트 설정
            export_fields: 내보낼 필드 목록
            
        Returns:
            내보내기 데이터
        """
        if not export_fields:
            export_fields = [
                "customer_id", "name", "email", "phone", "total_spent",
                "total_orders", "lifecycle_stage", "segment", "registration_date"
            ]
        
        customers = self._get_customers_by_criteria(segment_config["criteria"])
        
        exported_data = []
        for customer in customers:
            customer_data = {}
            for field in export_fields:
                value = getattr(customer, field, None)
                
                # 특별 처리가 필요한 필드들
                if field in ["lifecycle_stage", "segment"] and value:
                    value = value.value
                elif field in ["registration_date", "last_purchase_date", "first_purchase_date"] and value:
                    value = value.isoformat()
                
                customer_data[field] = value
            
            exported_data.append(customer_data)
        
        return {
            "segment_name": segment_config.get("name", "Custom Segment"),
            "export_date": datetime.now().isoformat(),
            "customer_count": len(exported_data),
            "export_fields": export_fields,
            "customers": exported_data
        }
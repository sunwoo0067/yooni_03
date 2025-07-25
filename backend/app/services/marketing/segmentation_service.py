"""
세그멘테이션 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
import json

from app.models.marketing import MarketingSegment
from app.models.crm import Customer, CustomerSegment, RFMAnalysis
from app.models.order import Order
from app.services.crm.segmentation_engine import SegmentationEngine
from app.core.exceptions import BusinessException


class SegmentationService:
    """세그멘테이션 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.segmentation_engine = SegmentationEngine(db)
    
    async def create_segment(self, segment_data: Dict[str, Any]) -> MarketingSegment:
        """세그먼트 생성"""
        try:
            segment = MarketingSegment(
                name=segment_data['name'],
                description=segment_data.get('description'),
                segment_type=segment_data.get('segment_type', 'dynamic'),
                rules=segment_data.get('rules', {}),
                is_active=segment_data.get('is_active', True)
            )
            
            # SQL 쿼리 생성 (동적 세그먼트)
            if segment.segment_type == 'dynamic':
                segment.sql_query = self._generate_segment_query(segment.rules)
            
            # 초기 고객 수 계산
            segment.customer_count = await self._calculate_segment_size(segment)
            segment.last_calculated = datetime.utcnow()
            
            # 세그먼트 특성 계산
            await self._calculate_segment_characteristics(segment)
            
            self.db.add(segment)
            self.db.commit()
            self.db.refresh(segment)
            
            return segment
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"세그먼트 생성 실패: {str(e)}")
    
    async def update_segment(self, segment_id: int, update_data: Dict[str, Any]) -> MarketingSegment:
        """세그먼트 수정"""
        try:
            segment = self.db.query(MarketingSegment).filter(
                MarketingSegment.id == segment_id
            ).first()
            
            if not segment:
                raise BusinessException("세그먼트를 찾을 수 없습니다")
            
            if segment.is_system:
                raise BusinessException("시스템 세그먼트는 수정할 수 없습니다")
            
            # 업데이트 가능한 필드
            updateable_fields = ['name', 'description', 'rules', 'is_active']
            
            for field in updateable_fields:
                if field in update_data:
                    setattr(segment, field, update_data[field])
            
            # 규칙이 변경된 경우 SQL 쿼리 재생성
            if 'rules' in update_data and segment.segment_type == 'dynamic':
                segment.sql_query = self._generate_segment_query(segment.rules)
            
            # 고객 수 재계산
            segment.customer_count = await self._calculate_segment_size(segment)
            segment.last_calculated = datetime.utcnow()
            
            # 세그먼트 특성 재계산
            await self._calculate_segment_characteristics(segment)
            
            segment.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(segment)
            
            return segment
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"세그먼트 수정 실패: {str(e)}")
    
    async def get_segment_customers(self, segment_id: int, 
                                  offset: int = 0, 
                                  limit: int = 100) -> Dict[str, Any]:
        """세그먼트 고객 목록 조회"""
        try:
            segment = self.db.query(MarketingSegment).filter(
                MarketingSegment.id == segment_id
            ).first()
            
            if not segment:
                raise BusinessException("세그먼트를 찾을 수 없습니다")
            
            # 세그먼트 유형에 따른 고객 조회
            if segment.segment_type == 'dynamic':
                customers_query = self._build_dynamic_segment_query(segment.rules)
            else:
                # 정적 세그먼트의 경우 저장된 고객 ID 사용
                customer_ids = segment.rules.get('customer_ids', [])
                customers_query = self.db.query(Customer).filter(
                    Customer.id.in_(customer_ids)
                )
            
            total = customers_query.count()
            customers = customers_query.offset(offset).limit(limit).all()
            
            return {
                'segment_id': segment_id,
                'segment_name': segment.name,
                'total': total,
                'offset': offset,
                'limit': limit,
                'customers': [
                    {
                        'id': customer.id,
                        'name': customer.name,
                        'email': customer.email,
                        'lifecycle_stage': customer.lifecycle_stage.value if customer.lifecycle_stage else None,
                        'segment': customer.segment.value if customer.segment else None,
                        'lifetime_value': customer.lifetime_value
                    }
                    for customer in customers
                ]
            }
            
        except Exception as e:
            raise BusinessException(f"세그먼트 고객 조회 실패: {str(e)}")
    
    async def refresh_segment(self, segment_id: int) -> MarketingSegment:
        """세그먼트 새로고침"""
        try:
            segment = self.db.query(MarketingSegment).filter(
                MarketingSegment.id == segment_id
            ).first()
            
            if not segment:
                raise BusinessException("세그먼트를 찾을 수 없습니다")
            
            if segment.segment_type != 'dynamic':
                raise BusinessException("동적 세그먼트만 새로고침할 수 있습니다")
            
            # 고객 수 재계산
            segment.customer_count = await self._calculate_segment_size(segment)
            segment.last_calculated = datetime.utcnow()
            
            # 세그먼트 특성 재계산
            await self._calculate_segment_characteristics(segment)
            
            self.db.commit()
            self.db.refresh(segment)
            
            return segment
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"세그먼트 새로고침 실패: {str(e)}")
    
    async def create_smart_segments(self) -> List[MarketingSegment]:
        """스마트 세그먼트 자동 생성"""
        try:
            smart_segments = []
            
            # 1. 고가치 고객 세그먼트
            high_value_segment = await self._create_high_value_segment()
            if high_value_segment:
                smart_segments.append(high_value_segment)
            
            # 2. 이탈 위험 세그먼트
            churn_risk_segment = await self._create_churn_risk_segment()
            if churn_risk_segment:
                smart_segments.append(churn_risk_segment)
            
            # 3. 신규 고객 세그먼트
            new_customer_segment = await self._create_new_customer_segment()
            if new_customer_segment:
                smart_segments.append(new_customer_segment)
            
            # 4. 휴면 고객 세그먼트
            dormant_segment = await self._create_dormant_segment()
            if dormant_segment:
                smart_segments.append(dormant_segment)
            
            # 5. 빈번 구매자 세그먼트
            frequent_buyer_segment = await self._create_frequent_buyer_segment()
            if frequent_buyer_segment:
                smart_segments.append(frequent_buyer_segment)
            
            # 6. 할인 민감 고객 세그먼트
            discount_sensitive_segment = await self._create_discount_sensitive_segment()
            if discount_sensitive_segment:
                smart_segments.append(discount_sensitive_segment)
            
            return smart_segments
            
        except Exception as e:
            raise BusinessException(f"스마트 세그먼트 생성 실패: {str(e)}")
    
    async def analyze_segment_overlap(self, segment_ids: List[int]) -> Dict[str, Any]:
        """세그먼트 중복 분석"""
        try:
            if len(segment_ids) < 2:
                raise BusinessException("최소 2개의 세그먼트가 필요합니다")
            
            segments = self.db.query(MarketingSegment).filter(
                MarketingSegment.id.in_(segment_ids)
            ).all()
            
            if len(segments) != len(segment_ids):
                raise BusinessException("일부 세그먼트를 찾을 수 없습니다")
            
            # 각 세그먼트의 고객 ID 수집
            segment_customers = {}
            for segment in segments:
                customers = await self._get_segment_customer_ids(segment)
                segment_customers[segment.id] = set(customers)
            
            # 중복 분석
            overlap_matrix = {}
            for i, seg1 in enumerate(segments):
                overlap_matrix[seg1.id] = {}
                for j, seg2 in enumerate(segments):
                    if i != j:
                        overlap = len(
                            segment_customers[seg1.id] & segment_customers[seg2.id]
                        )
                        overlap_rate = (overlap / len(segment_customers[seg1.id]) * 100) \
                                     if segment_customers[seg1.id] else 0
                        
                        overlap_matrix[seg1.id][seg2.id] = {
                            'overlap_count': overlap,
                            'overlap_rate': round(overlap_rate, 2)
                        }
            
            # 전체 통계
            all_customers = set()
            for customers in segment_customers.values():
                all_customers.update(customers)
            
            return {
                'segments': [
                    {
                        'id': segment.id,
                        'name': segment.name,
                        'customer_count': len(segment_customers[segment.id])
                    }
                    for segment in segments
                ],
                'overlap_matrix': overlap_matrix,
                'total_unique_customers': len(all_customers),
                'recommendations': self._generate_overlap_recommendations(
                    segments, overlap_matrix
                )
            }
            
        except Exception as e:
            raise BusinessException(f"세그먼트 중복 분석 실패: {str(e)}")
    
    def _generate_segment_query(self, rules: Dict[str, Any]) -> str:
        """세그먼트 규칙을 SQL 쿼리로 변환"""
        # 기본 쿼리
        query_parts = ["SELECT id FROM crm_customers WHERE 1=1"]
        
        # 규칙별 조건 추가
        if 'lifecycle_stage' in rules:
            stages = rules['lifecycle_stage']
            if isinstance(stages, list):
                stage_list = "','".join(stages)
                query_parts.append(f"AND lifecycle_stage IN ('{stage_list}')")
            else:
                query_parts.append(f"AND lifecycle_stage = '{stages}'")
        
        if 'segment' in rules:
            segments = rules['segment']
            if isinstance(segments, list):
                segment_list = "','".join(segments)
                query_parts.append(f"AND segment IN ('{segment_list}')")
            else:
                query_parts.append(f"AND segment = '{segments}'")
        
        if 'value_tier' in rules:
            tiers = rules['value_tier']
            if isinstance(tiers, list):
                tier_list = "','".join(tiers)
                query_parts.append(f"AND customer_value_tier IN ('{tier_list}')")
            else:
                query_parts.append(f"AND customer_value_tier = '{tiers}'")
        
        if 'total_spent' in rules:
            spent_rule = rules['total_spent']
            if 'min' in spent_rule:
                query_parts.append(f"AND total_spent >= {spent_rule['min']}")
            if 'max' in spent_rule:
                query_parts.append(f"AND total_spent <= {spent_rule['max']}")
        
        if 'order_count' in rules:
            order_rule = rules['order_count']
            if 'min' in order_rule:
                query_parts.append(f"AND total_orders >= {order_rule['min']}")
            if 'max' in order_rule:
                query_parts.append(f"AND total_orders <= {order_rule['max']}")
        
        if 'last_purchase_days' in rules:
            days = rules['last_purchase_days']
            query_parts.append(
                f"AND last_purchase_date >= DATE_SUB(NOW(), INTERVAL {days} DAY)"
            )
        
        if 'registration_days' in rules:
            reg_rule = rules['registration_days']
            if 'min' in reg_rule:
                query_parts.append(
                    f"AND registration_date <= DATE_SUB(NOW(), INTERVAL {reg_rule['min']} DAY)"
                )
            if 'max' in reg_rule:
                query_parts.append(
                    f"AND registration_date >= DATE_SUB(NOW(), INTERVAL {reg_rule['max']} DAY)"
                )
        
        return " ".join(query_parts)
    
    def _build_dynamic_segment_query(self, rules: Dict[str, Any]):
        """동적 세그먼트 쿼리 빌드"""
        query = self.db.query(Customer)
        
        # 생애주기 단계
        if 'lifecycle_stage' in rules:
            stages = rules['lifecycle_stage']
            if isinstance(stages, list):
                query = query.filter(Customer.lifecycle_stage.in_(stages))
            else:
                query = query.filter(Customer.lifecycle_stage == stages)
        
        # RFM 세그먼트
        if 'segment' in rules:
            segments = rules['segment']
            if isinstance(segments, list):
                query = query.filter(Customer.segment.in_(segments))
            else:
                query = query.filter(Customer.segment == segments)
        
        # 고객 가치 티어
        if 'value_tier' in rules:
            tiers = rules['value_tier']
            if isinstance(tiers, list):
                query = query.filter(Customer.customer_value_tier.in_(tiers))
            else:
                query = query.filter(Customer.customer_value_tier == tiers)
        
        # 총 구매 금액
        if 'total_spent' in rules:
            spent_rule = rules['total_spent']
            if 'min' in spent_rule:
                query = query.filter(Customer.total_spent >= spent_rule['min'])
            if 'max' in spent_rule:
                query = query.filter(Customer.total_spent <= spent_rule['max'])
        
        # 주문 수
        if 'order_count' in rules:
            order_rule = rules['order_count']
            if 'min' in order_rule:
                query = query.filter(Customer.total_orders >= order_rule['min'])
            if 'max' in order_rule:
                query = query.filter(Customer.total_orders <= order_rule['max'])
        
        # 마지막 구매일
        if 'last_purchase_days' in rules:
            days = rules['last_purchase_days']
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Customer.last_purchase_date >= cutoff_date)
        
        # 가입일
        if 'registration_days' in rules:
            reg_rule = rules['registration_days']
            if 'min' in reg_rule:
                min_date = datetime.utcnow() - timedelta(days=reg_rule['min'])
                query = query.filter(Customer.registration_date <= min_date)
            if 'max' in reg_rule:
                max_date = datetime.utcnow() - timedelta(days=reg_rule['max'])
                query = query.filter(Customer.registration_date >= max_date)
        
        # 이메일 마케팅 동의
        if 'email_consent' in rules:
            query = query.filter(Customer.email_marketing_consent == rules['email_consent'])
        
        # SMS 마케팅 동의
        if 'sms_consent' in rules:
            query = query.filter(Customer.sms_marketing_consent == rules['sms_consent'])
        
        # 활성 상태
        if 'is_active' in rules:
            query = query.filter(Customer.is_active == rules['is_active'])
        
        return query
    
    async def _calculate_segment_size(self, segment: MarketingSegment) -> int:
        """세그먼트 크기 계산"""
        if segment.segment_type == 'dynamic':
            query = self._build_dynamic_segment_query(segment.rules)
            return query.count()
        else:
            # 정적 세그먼트
            customer_ids = segment.rules.get('customer_ids', [])
            return len(customer_ids)
    
    async def _calculate_segment_characteristics(self, segment: MarketingSegment):
        """세그먼트 특성 계산"""
        try:
            # 세그먼트 고객 쿼리
            if segment.segment_type == 'dynamic':
                customers_query = self._build_dynamic_segment_query(segment.rules)
            else:
                customer_ids = segment.rules.get('customer_ids', [])
                customers_query = self.db.query(Customer).filter(
                    Customer.id.in_(customer_ids)
                )
            
            # 평균 LTV
            avg_ltv = customers_query.with_entities(
                func.avg(Customer.lifetime_value)
            ).scalar() or 0
            segment.average_ltv = round(avg_ltv, 2)
            
            # 평균 주문 금액
            avg_aov = customers_query.with_entities(
                func.avg(Customer.average_order_value)
            ).scalar() or 0
            segment.average_order_value = round(avg_aov, 2)
            
            # 이탈률 (이탈 위험이 높은 고객 비율)
            churn_count = customers_query.filter(
                Customer.churn_probability > 0.7
            ).count()
            total_count = customers_query.count()
            segment.churn_rate = (churn_count / total_count * 100) if total_count > 0 else 0
            
            # 참여도 점수 (최근 활동 기반)
            active_count = customers_query.filter(
                Customer.last_engagement_date >= datetime.utcnow() - timedelta(days=30)
            ).count()
            segment.engagement_score = (active_count / total_count * 100) if total_count > 0 else 0
            
        except Exception as e:
            print(f"세그먼트 특성 계산 오류: {str(e)}")
    
    async def _create_high_value_segment(self) -> Optional[MarketingSegment]:
        """고가치 고객 세그먼트 생성"""
        # 기존 세그먼트 확인
        existing = self.db.query(MarketingSegment).filter(
            MarketingSegment.name == "고가치 고객",
            MarketingSegment.is_system == True
        ).first()
        
        if existing:
            return None
        
        # 상위 20% LTV 고객
        ltv_threshold = self.db.query(
            func.percentile_cont(0.8).within_group(Customer.lifetime_value)
        ).scalar() or 0
        
        rules = {
            'total_spent': {'min': ltv_threshold},
            'segment': ['CHAMPIONS', 'LOYAL_CUSTOMERS'],
            'value_tier': ['gold', 'platinum']
        }
        
        segment = MarketingSegment(
            name="고가치 고객",
            description="높은 생애가치를 가진 우수 고객",
            segment_type="dynamic",
            rules=rules,
            is_system=True,
            is_active=True
        )
        
        segment.sql_query = self._generate_segment_query(rules)
        segment.customer_count = await self._calculate_segment_size(segment)
        segment.last_calculated = datetime.utcnow()
        
        await self._calculate_segment_characteristics(segment)
        
        self.db.add(segment)
        self.db.commit()
        
        return segment
    
    async def _create_churn_risk_segment(self) -> Optional[MarketingSegment]:
        """이탈 위험 세그먼트 생성"""
        existing = self.db.query(MarketingSegment).filter(
            MarketingSegment.name == "이탈 위험 고객",
            MarketingSegment.is_system == True
        ).first()
        
        if existing:
            return None
        
        rules = {
            'lifecycle_stage': ['AT_RISK', 'DORMANT'],
            'segment': ['AT_RISK', 'CANNOT_LOSE_THEM', 'HIBERNATING'],
            'last_purchase_days': 90  # 90일 이상 구매 없음
        }
        
        segment = MarketingSegment(
            name="이탈 위험 고객",
            description="이탈 위험이 높은 고객",
            segment_type="dynamic",
            rules=rules,
            is_system=True,
            is_active=True
        )
        
        segment.sql_query = self._generate_segment_query(rules)
        segment.customer_count = await self._calculate_segment_size(segment)
        segment.last_calculated = datetime.utcnow()
        
        await self._calculate_segment_characteristics(segment)
        
        self.db.add(segment)
        self.db.commit()
        
        return segment
    
    async def _create_new_customer_segment(self) -> Optional[MarketingSegment]:
        """신규 고객 세그먼트 생성"""
        existing = self.db.query(MarketingSegment).filter(
            MarketingSegment.name == "신규 고객",
            MarketingSegment.is_system == True
        ).first()
        
        if existing:
            return None
        
        rules = {
            'lifecycle_stage': ['NEW'],
            'registration_days': {'max': 30},  # 30일 이내 가입
            'order_count': {'max': 1}  # 주문 1회 이하
        }
        
        segment = MarketingSegment(
            name="신규 고객",
            description="최근 가입한 신규 고객",
            segment_type="dynamic",
            rules=rules,
            is_system=True,
            is_active=True
        )
        
        segment.sql_query = self._generate_segment_query(rules)
        segment.customer_count = await self._calculate_segment_size(segment)
        segment.last_calculated = datetime.utcnow()
        
        await self._calculate_segment_characteristics(segment)
        
        self.db.add(segment)
        self.db.commit()
        
        return segment
    
    async def _create_dormant_segment(self) -> Optional[MarketingSegment]:
        """휴면 고객 세그먼트 생성"""
        existing = self.db.query(MarketingSegment).filter(
            MarketingSegment.name == "휴면 고객",
            MarketingSegment.is_system == True
        ).first()
        
        if existing:
            return None
        
        rules = {
            'lifecycle_stage': ['DORMANT', 'CHURNED'],
            'last_purchase_days': 180  # 180일 이상 구매 없음
        }
        
        segment = MarketingSegment(
            name="휴면 고객",
            description="오랫동안 활동이 없는 휴면 고객",
            segment_type="dynamic",
            rules=rules,
            is_system=True,
            is_active=True
        )
        
        segment.sql_query = self._generate_segment_query(rules)
        segment.customer_count = await self._calculate_segment_size(segment)
        segment.last_calculated = datetime.utcnow()
        
        await self._calculate_segment_characteristics(segment)
        
        self.db.add(segment)
        self.db.commit()
        
        return segment
    
    async def _create_frequent_buyer_segment(self) -> Optional[MarketingSegment]:
        """빈번 구매자 세그먼트 생성"""
        existing = self.db.query(MarketingSegment).filter(
            MarketingSegment.name == "빈번 구매자",
            MarketingSegment.is_system == True
        ).first()
        
        if existing:
            return None
        
        # 평균 주문 수 계산
        avg_orders = self.db.query(
            func.avg(Customer.total_orders)
        ).scalar() or 0
        
        rules = {
            'order_count': {'min': int(avg_orders * 2)},  # 평균의 2배 이상
            'last_purchase_days': 60  # 60일 이내 구매
        }
        
        segment = MarketingSegment(
            name="빈번 구매자",
            description="자주 구매하는 활성 고객",
            segment_type="dynamic",
            rules=rules,
            is_system=True,
            is_active=True
        )
        
        segment.sql_query = self._generate_segment_query(rules)
        segment.customer_count = await self._calculate_segment_size(segment)
        segment.last_calculated = datetime.utcnow()
        
        await self._calculate_segment_characteristics(segment)
        
        self.db.add(segment)
        self.db.commit()
        
        return segment
    
    async def _create_discount_sensitive_segment(self) -> Optional[MarketingSegment]:
        """할인 민감 고객 세그먼트 생성"""
        existing = self.db.query(MarketingSegment).filter(
            MarketingSegment.name == "할인 민감 고객",
            MarketingSegment.is_system == True
        ).first()
        
        if existing:
            return None
        
        # 할인 민감도가 높은 고객 (실제 구현에서는 더 정교한 로직 필요)
        rules = {
            'segment': ['PRICE_SENSITIVE', 'NEED_ATTENTION'],
            'value_tier': ['bronze', 'silver']
        }
        
        segment = MarketingSegment(
            name="할인 민감 고객",
            description="가격과 할인에 민감한 고객",
            segment_type="dynamic",
            rules=rules,
            is_system=True,
            is_active=True
        )
        
        segment.sql_query = self._generate_segment_query(rules)
        segment.customer_count = await self._calculate_segment_size(segment)
        segment.last_calculated = datetime.utcnow()
        
        await self._calculate_segment_characteristics(segment)
        
        self.db.add(segment)
        self.db.commit()
        
        return segment
    
    async def _get_segment_customer_ids(self, segment: MarketingSegment) -> List[int]:
        """세그먼트의 고객 ID 목록 가져오기"""
        if segment.segment_type == 'dynamic':
            customers = self._build_dynamic_segment_query(segment.rules).all()
            return [c.id for c in customers]
        else:
            return segment.rules.get('customer_ids', [])
    
    def _generate_overlap_recommendations(self, segments: List[MarketingSegment], 
                                        overlap_matrix: Dict[int, Dict[int, Dict[str, Any]]]) -> List[str]:
        """세그먼트 중복 기반 권장사항"""
        recommendations = []
        
        for seg1_id, overlaps in overlap_matrix.items():
            for seg2_id, overlap_data in overlaps.items():
                if overlap_data['overlap_rate'] > 50:
                    seg1_name = next(s.name for s in segments if s.id == seg1_id)
                    seg2_name = next(s.name for s in segments if s.id == seg2_id)
                    
                    recommendations.append(
                        f"{seg1_name}와 {seg2_name} 세그먼트가 {overlap_data['overlap_rate']:.1f}% 중복됩니다. "
                        "세그먼트 통합을 고려하세요."
                    )
        
        return recommendations
"""
고객 관리 시스템
고객 정보 관리, 프로필 업데이트, 고객 검색 및 필터링 기능 제공
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc
import uuid

from ...models.crm import Customer, CustomerLifecycleStage, CustomerSegment, CustomerInteraction
from ...models.order import Order
from ..customer_analysis.customer_analyzer import CustomerAnalyzer


class CustomerManager:
    """고객 관리를 위한 메인 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.customer_analyzer = CustomerAnalyzer(db)
    
    def create_customer(self, customer_data: Dict) -> Dict:
        """
        새 고객 생성
        
        Args:
            customer_data: 고객 정보
            
        Returns:
            생성된 고객 정보
        """
        # 이메일 중복 확인
        existing_customer = self.db.query(Customer).filter(
            Customer.email == customer_data.get("email")
        ).first()
        
        if existing_customer:
            return {"error": "이미 존재하는 이메일입니다."}
        
        # 새 고객 생성
        customer = Customer(
            customer_uuid=str(uuid.uuid4()),
            name=customer_data.get("name"),
            email=customer_data.get("email"),
            phone=customer_data.get("phone"),
            gender=customer_data.get("gender"),
            age=customer_data.get("age"),
            birth_date=customer_data.get("birth_date"),
            address=customer_data.get("address"),
            city=customer_data.get("city"),
            postal_code=customer_data.get("postal_code"),
            acquisition_channel=customer_data.get("acquisition_channel", "직접"),
            lifecycle_stage=CustomerLifecycleStage.NEW,
            customer_value_tier="bronze",
            email_marketing_consent=customer_data.get("email_marketing_consent", True),
            sms_marketing_consent=customer_data.get("sms_marketing_consent", True),
            push_notification_consent=customer_data.get("push_notification_consent", True)
        )
        
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        
        # 웰컴 상호작용 기록
        self._record_welcome_interaction(customer.id)
        
        return {
            "customer_id": customer.id,
            "customer_uuid": customer.customer_uuid,
            "name": customer.name,
            "email": customer.email,
            "lifecycle_stage": customer.lifecycle_stage.value,
            "registration_date": customer.registration_date.isoformat(),
            "message": "고객이 성공적으로 생성되었습니다."
        }
    
    def update_customer(self, customer_id: int, update_data: Dict) -> Dict:
        """
        고객 정보 업데이트
        
        Args:
            customer_id: 고객 ID
            update_data: 업데이트할 데이터
            
        Returns:
            업데이트 결과
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        # 업데이트 가능한 필드들
        updatable_fields = [
            'name', 'phone', 'gender', 'age', 'birth_date',
            'address', 'city', 'postal_code', 'preferred_contact_time',
            'email_marketing_consent', 'sms_marketing_consent', 
            'push_notification_consent', 'notes'
        ]
        
        updated_fields = []
        for field in updatable_fields:
            if field in update_data:
                setattr(customer, field, update_data[field])
                updated_fields.append(field)
        
        customer.updated_at = datetime.now()
        self.db.commit()
        
        return {
            "customer_id": customer_id,
            "updated_fields": updated_fields,
            "updated_at": customer.updated_at.isoformat(),
            "message": "고객 정보가 성공적으로 업데이트되었습니다."
        }
    
    def get_customer_profile(self, customer_id: int, include_analysis: bool = True) -> Dict:
        """
        고객 프로필 조회
        
        Args:
            customer_id: 고객 ID
            include_analysis: 분석 데이터 포함 여부
            
        Returns:
            고객 프로필 정보
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        # 기본 프로필 정보
        profile = {
            "customer_id": customer.id,
            "customer_uuid": customer.customer_uuid,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "gender": customer.gender,
            "age": customer.age,
            "birth_date": customer.birth_date.isoformat() if customer.birth_date else None,
            "address": customer.address,
            "city": customer.city,
            "postal_code": customer.postal_code,
            "registration_date": customer.registration_date.isoformat(),
            "last_login": customer.last_login.isoformat() if customer.last_login else None,
            "is_active": customer.is_active,
            "lifecycle_stage": customer.lifecycle_stage.value if customer.lifecycle_stage else None,
            "segment": customer.segment.value if customer.segment else None,
            "customer_value_tier": customer.customer_value_tier,
            "rfm_score": customer.rfm_score,
            "total_orders": customer.total_orders,
            "total_spent": customer.total_spent,
            "average_order_value": customer.average_order_value,
            "lifetime_value": customer.lifetime_value,
            "first_purchase_date": customer.first_purchase_date.isoformat() if customer.first_purchase_date else None,
            "last_purchase_date": customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
            "acquisition_channel": customer.acquisition_channel,
            "preferred_platform": customer.preferred_platform,
            "mobile_usage_rate": customer.mobile_usage_rate,
            "nps_score": customer.nps_score,
            "satisfaction_score": customer.satisfaction_score,
            "churn_probability": customer.churn_probability,
            "tags": customer.tags,
            "notes": customer.notes
        }
        
        # 분석 데이터 포함
        if include_analysis:
            analysis_result = self.customer_analyzer.get_comprehensive_customer_analysis(customer_id)
            if "error" not in analysis_result:
                profile["analysis"] = analysis_result
        
        return profile
    
    def search_customers(self, search_params: Dict, page: int = 1, 
                        page_size: int = 50, sort_by: str = "registration_date", 
                        sort_order: str = "desc") -> Dict:
        """
        고객 검색 및 필터링
        
        Args:
            search_params: 검색 조건
            page: 페이지 번호
            page_size: 페이지 크기
            sort_by: 정렬 필드
            sort_order: 정렬 순서 (asc/desc)
            
        Returns:
            검색 결과
        """
        query = self.db.query(Customer).filter(Customer.is_active == True)
        
        # 검색 조건 적용
        if "name" in search_params:
            query = query.filter(Customer.name.ilike(f"%{search_params['name']}%"))
        
        if "email" in search_params:
            query = query.filter(Customer.email.ilike(f"%{search_params['email']}%"))
        
        if "phone" in search_params:
            query = query.filter(Customer.phone.ilike(f"%{search_params['phone']}%"))
        
        if "lifecycle_stage" in search_params:
            stages = search_params["lifecycle_stage"]
            if isinstance(stages, str):
                stages = [stages]
            stage_enums = [CustomerLifecycleStage(stage) for stage in stages]
            query = query.filter(Customer.lifecycle_stage.in_(stage_enums))
        
        if "segment" in search_params:
            segments = search_params["segment"]
            if isinstance(segments, str):
                segments = [segments]
            segment_enums = [CustomerSegment(segment) for segment in segments]
            query = query.filter(Customer.segment.in_(segment_enums))
        
        if "customer_value_tier" in search_params:
            query = query.filter(Customer.customer_value_tier.in_(search_params["customer_value_tier"]))
        
        if "city" in search_params:
            query = query.filter(Customer.city.in_(search_params["city"]))
        
        if "acquisition_channel" in search_params:
            query = query.filter(Customer.acquisition_channel.in_(search_params["acquisition_channel"]))
        
        # 날짜 범위 필터
        if "registration_date_from" in search_params:
            query = query.filter(Customer.registration_date >= search_params["registration_date_from"])
        
        if "registration_date_to" in search_params:
            query = query.filter(Customer.registration_date <= search_params["registration_date_to"])
        
        if "last_purchase_date_from" in search_params:
            query = query.filter(Customer.last_purchase_date >= search_params["last_purchase_date_from"])
        
        if "last_purchase_date_to" in search_params:
            query = query.filter(Customer.last_purchase_date <= search_params["last_purchase_date_to"])
        
        # 구매 금액 범위
        if "total_spent_min" in search_params:
            query = query.filter(Customer.total_spent >= search_params["total_spent_min"])
        
        if "total_spent_max" in search_params:
            query = query.filter(Customer.total_spent <= search_params["total_spent_max"])
        
        # 주문 수 범위
        if "total_orders_min" in search_params:
            query = query.filter(Customer.total_orders >= search_params["total_orders_min"])
        
        if "total_orders_max" in search_params:
            query = query.filter(Customer.total_orders <= search_params["total_orders_max"])
        
        # 이탈 확률 범위
        if "churn_probability_min" in search_params:
            query = query.filter(Customer.churn_probability >= search_params["churn_probability_min"])
        
        if "churn_probability_max" in search_params:
            query = query.filter(Customer.churn_probability <= search_params["churn_probability_max"])
        
        # 총 개수
        total_count = query.count()
        
        # 정렬
        sort_column = getattr(Customer, sort_by, Customer.registration_date)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # 페이징
        offset = (page - 1) * page_size
        customers = query.offset(offset).limit(page_size).all()
        
        # 결과 변환
        customer_list = []
        for customer in customers:
            customer_list.append({
                "customer_id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "lifecycle_stage": customer.lifecycle_stage.value if customer.lifecycle_stage else None,
                "segment": customer.segment.value if customer.segment else None,
                "customer_value_tier": customer.customer_value_tier,
                "total_spent": customer.total_spent,
                "total_orders": customer.total_orders,
                "registration_date": customer.registration_date.isoformat(),
                "last_purchase_date": customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
                "churn_probability": customer.churn_probability
            })
        
        return {
            "customers": customer_list,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "search_params": search_params
        }
    
    def get_customer_statistics(self) -> Dict:
        """
        고객 통계 정보 조회
        
        Returns:
            고객 통계
        """
        # 기본 통계
        total_customers = self.db.query(Customer).filter(Customer.is_active == True).count()
        
        # 생애주기별 분포
        lifecycle_stats = self.db.query(
            Customer.lifecycle_stage,
            func.count(Customer.id).label('count')
        ).filter(Customer.is_active == True).group_by(Customer.lifecycle_stage).all()
        
        # 세그먼트별 분포
        segment_stats = self.db.query(
            Customer.segment,
            func.count(Customer.id).label('count')
        ).filter(Customer.is_active == True).group_by(Customer.segment).all()
        
        # 가치 등급별 분포
        tier_stats = self.db.query(
            Customer.customer_value_tier,
            func.count(Customer.id).label('count')
        ).filter(Customer.is_active == True).group_by(Customer.customer_value_tier).all()
        
        # 신규 고객 (최근 30일)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_customers_30d = self.db.query(Customer).filter(
            and_(
                Customer.registration_date >= thirty_days_ago,
                Customer.is_active == True
            )
        ).count()
        
        # 이탈 위험 고객
        at_risk_customers = self.db.query(Customer).filter(
            and_(
                Customer.lifecycle_stage == CustomerLifecycleStage.AT_RISK,
                Customer.is_active == True
            )
        ).count()
        
        # 평균 지표
        avg_stats = self.db.query(
            func.avg(Customer.total_spent).label('avg_spent'),
            func.avg(Customer.total_orders).label('avg_orders'),
            func.avg(Customer.average_order_value).label('avg_order_value')
        ).filter(Customer.is_active == True).first()
        
        return {
            "총_고객수": total_customers,
            "신규_고객_30일": new_customers_30d,
            "이탈_위험_고객": at_risk_customers,
            "평균_총구매금액": round(avg_stats.avg_spent or 0, 2),
            "평균_주문수": round(avg_stats.avg_orders or 0, 2),
            "평균_주문금액": round(avg_stats.avg_order_value or 0, 2),
            "생애주기별_분포": {
                stage.value if stage else "미분류": count 
                for stage, count in lifecycle_stats
            },
            "세그먼트별_분포": {
                segment.value if segment else "미분류": count 
                for segment, count in segment_stats
            },
            "가치등급별_분포": {
                tier: count for tier, count in tier_stats
            },
            "통계_생성일시": datetime.now().isoformat()
        }
    
    def record_customer_interaction(self, customer_id: int, interaction_data: Dict) -> Dict:
        """
        고객 상호작용 기록
        
        Args:
            customer_id: 고객 ID
            interaction_data: 상호작용 데이터
            
        Returns:
            기록 결과
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        interaction = CustomerInteraction(
            customer_id=customer_id,
            interaction_type=interaction_data.get("interaction_type"),
            channel=interaction_data.get("channel"),
            direction=interaction_data.get("direction", "inbound"),
            subject=interaction_data.get("subject"),
            content=interaction_data.get("content"),
            sentiment=interaction_data.get("sentiment"),
            status=interaction_data.get("status", "completed"),
            priority=interaction_data.get("priority", "medium"),
            agent_id=interaction_data.get("agent_id"),
            department=interaction_data.get("department"),
            resolution=interaction_data.get("resolution"),
            satisfaction_rating=interaction_data.get("satisfaction_rating")
        )
        
        self.db.add(interaction)
        
        # 고객의 마지막 상호작용 날짜 업데이트
        customer.last_engagement_date = datetime.now()
        
        self.db.commit()
        self.db.refresh(interaction)
        
        return {
            "interaction_id": interaction.id,
            "customer_id": customer_id,
            "interaction_type": interaction.interaction_type,
            "created_at": interaction.created_at.isoformat(),
            "message": "상호작용이 성공적으로 기록되었습니다."
        }
    
    def get_customer_interactions(self, customer_id: int, limit: int = 50, 
                                interaction_type: str = None) -> Dict:
        """
        고객 상호작용 이력 조회
        
        Args:
            customer_id: 고객 ID
            limit: 조회할 최대 개수
            interaction_type: 상호작용 유형 필터
            
        Returns:
            상호작용 이력
        """
        query = self.db.query(CustomerInteraction).filter(
            CustomerInteraction.customer_id == customer_id
        )
        
        if interaction_type:
            query = query.filter(CustomerInteraction.interaction_type == interaction_type)
        
        interactions = query.order_by(
            desc(CustomerInteraction.created_at)
        ).limit(limit).all()
        
        interaction_list = []
        for interaction in interactions:
            interaction_list.append({
                "interaction_id": interaction.id,
                "interaction_type": interaction.interaction_type,
                "channel": interaction.channel,
                "direction": interaction.direction,
                "subject": interaction.subject,
                "content": interaction.content,
                "sentiment": interaction.sentiment,
                "status": interaction.status,
                "priority": interaction.priority,
                "agent_id": interaction.agent_id,
                "department": interaction.department,
                "resolution": interaction.resolution,
                "satisfaction_rating": interaction.satisfaction_rating,
                "created_at": interaction.created_at.isoformat(),
                "resolved_at": interaction.resolved_at.isoformat() if interaction.resolved_at else None
            })
        
        return {
            "customer_id": customer_id,
            "interactions": interaction_list,
            "total_interactions": len(interaction_list),
            "interaction_type_filter": interaction_type
        }
    
    def _record_welcome_interaction(self, customer_id: int):
        """웰컴 상호작용 기록"""
        welcome_interaction = CustomerInteraction(
            customer_id=customer_id,
            interaction_type="welcome",
            channel="system",
            direction="outbound",
            subject="신규 고객 환영",
            content="드롭쉬핑 서비스에 가입해 주셔서 감사합니다. 최고의 쇼핑 경험을 제공하겠습니다.",
            sentiment="positive",
            status="completed",
            priority="low",
            department="marketing"
        )
        
        self.db.add(welcome_interaction)
    
    def deactivate_customer(self, customer_id: int, reason: str = None) -> Dict:
        """
        고객 비활성화
        
        Args:
            customer_id: 고객 ID
            reason: 비활성화 사유
            
        Returns:
            비활성화 결과
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        customer.is_active = False
        customer.updated_at = datetime.now()
        
        # 비활성화 사유 기록
        if reason:
            deactivation_interaction = CustomerInteraction(
                customer_id=customer_id,
                interaction_type="deactivation",
                channel="system",
                direction="outbound",
                subject="계정 비활성화",
                content=f"계정 비활성화 사유: {reason}",
                status="completed",
                priority="medium",
                department="system"
            )
            self.db.add(deactivation_interaction)
        
        self.db.commit()
        
        return {
            "customer_id": customer_id,
            "is_active": False,
            "deactivation_date": customer.updated_at.isoformat(),
            "reason": reason,
            "message": "고객이 성공적으로 비활성화되었습니다."
        }
    
    def reactivate_customer(self, customer_id: int, reason: str = None) -> Dict:
        """
        고객 재활성화
        
        Args:
            customer_id: 고객 ID
            reason: 재활성화 사유
            
        Returns:
            재활성화 결과
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": "고객을 찾을 수 없습니다."}
        
        customer.is_active = True
        customer.updated_at = datetime.now()
        
        # 재활성화 사유 기록
        if reason:
            reactivation_interaction = CustomerInteraction(
                customer_id=customer_id,
                interaction_type="reactivation",
                channel="system",
                direction="outbound",
                subject="계정 재활성화",
                content=f"계정 재활성화 사유: {reason}",
                status="completed",
                priority="medium",
                department="system"
            )
            self.db.add(reactivation_interaction)
        
        self.db.commit()
        
        return {
            "customer_id": customer_id,
            "is_active": True,
            "reactivation_date": customer.updated_at.isoformat(),
            "reason": reason,
            "message": "고객이 성공적으로 재활성화되었습니다."
        }
"""
캠페인 관리 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import uuid
import json

from app.models.marketing import (
    MarketingCampaign, MarketingSegment, MarketingMessage,
    CampaignType, CampaignStatus, MessageStatus,
    campaign_segments
)
from app.models.crm import Customer
from app.core.exceptions import BusinessException
from app.services.crm.segmentation_engine import SegmentationEngine
from app.services.ai.ai_manager import AIManager


class CampaignManager:
    """캠페인 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.segmentation_engine = SegmentationEngine(db)
        self.ai_manager = AIManager()
    
    async def create_campaign(self, campaign_data: Dict[str, Any]) -> MarketingCampaign:
        """캠페인 생성"""
        try:
            # 캠페인 객체 생성
            campaign = MarketingCampaign(
                name=campaign_data['name'],
                description=campaign_data.get('description'),
                campaign_type=CampaignType(campaign_data['campaign_type']),
                status=CampaignStatus.DRAFT,
                start_date=campaign_data.get('start_date'),
                end_date=campaign_data.get('end_date'),
                schedule_type=campaign_data.get('schedule_type', 'immediate'),
                schedule_config=campaign_data.get('schedule_config'),
                subject=campaign_data.get('subject'),
                preview_text=campaign_data.get('preview_text'),
                content_template=campaign_data.get('content_template'),
                personalization_tags=campaign_data.get('personalization_tags', []),
                budget=campaign_data.get('budget', 0),
                goal_type=campaign_data.get('goal_type'),
                goal_value=campaign_data.get('goal_value'),
                created_by=campaign_data.get('created_by')
            )
            
            # A/B 테스트 설정
            if campaign_data.get('is_ab_test'):
                campaign.is_ab_test = True
                campaign.ab_test_config = campaign_data.get('ab_test_config')
                campaign.control_group_size = campaign_data.get('control_group_size', 0.1)
            
            # 타겟 세그먼트 연결
            if campaign_data.get('target_segment_ids'):
                segments = self.db.query(MarketingSegment).filter(
                    MarketingSegment.id.in_(campaign_data['target_segment_ids'])
                ).all()
                campaign.target_segments = segments
            
            # 타겟 조건 설정
            if campaign_data.get('target_conditions'):
                campaign.target_conditions = campaign_data['target_conditions']
            
            # 예상 수신자 수 계산
            campaign.expected_recipients = await self._calculate_recipients(campaign)
            
            self.db.add(campaign)
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"캠페인 생성 실패: {str(e)}")
    
    async def update_campaign(self, campaign_id: int, update_data: Dict[str, Any]) -> MarketingCampaign:
        """캠페인 수정"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
                raise BusinessException("실행 중이거나 완료된 캠페인은 수정할 수 없습니다")
            
            # 업데이트 가능한 필드만 수정
            updateable_fields = [
                'name', 'description', 'start_date', 'end_date',
                'subject', 'preview_text', 'content_template',
                'personalization_tags', 'budget', 'goal_type', 'goal_value'
            ]
            
            for field in updateable_fields:
                if field in update_data:
                    setattr(campaign, field, update_data[field])
            
            # 세그먼트 업데이트
            if 'target_segment_ids' in update_data:
                segments = self.db.query(MarketingSegment).filter(
                    MarketingSegment.id.in_(update_data['target_segment_ids'])
                ).all()
                campaign.target_segments = segments
            
            # 예상 수신자 수 재계산
            campaign.expected_recipients = await self._calculate_recipients(campaign)
            
            campaign.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"캠페인 수정 실패: {str(e)}")
    
    async def start_campaign(self, campaign_id: int) -> MarketingCampaign:
        """캠페인 시작"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            if campaign.status != CampaignStatus.SCHEDULED and campaign.status != CampaignStatus.DRAFT:
                raise BusinessException("이미 실행 중이거나 완료된 캠페인입니다")
            
            # 캠페인 검증
            await self._validate_campaign(campaign)
            
            # 상태 변경
            campaign.status = CampaignStatus.RUNNING
            if not campaign.start_date:
                campaign.start_date = datetime.utcnow()
            
            # 즉시 실행 캠페인인 경우 메시지 생성
            if campaign.schedule_type == 'immediate':
                await self._create_campaign_messages(campaign)
            
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"캠페인 시작 실패: {str(e)}")
    
    async def pause_campaign(self, campaign_id: int) -> MarketingCampaign:
        """캠페인 일시중지"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            if campaign.status != CampaignStatus.RUNNING:
                raise BusinessException("실행 중인 캠페인만 일시중지할 수 있습니다")
            
            campaign.status = CampaignStatus.PAUSED
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"캠페인 일시중지 실패: {str(e)}")
    
    async def resume_campaign(self, campaign_id: int) -> MarketingCampaign:
        """캠페인 재개"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            if campaign.status != CampaignStatus.PAUSED:
                raise BusinessException("일시중지된 캠페인만 재개할 수 있습니다")
            
            campaign.status = CampaignStatus.RUNNING
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"캠페인 재개 실패: {str(e)}")
    
    async def complete_campaign(self, campaign_id: int) -> MarketingCampaign:
        """캠페인 종료"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            if campaign.status == CampaignStatus.COMPLETED:
                raise BusinessException("이미 완료된 캠페인입니다")
            
            # 캠페인 성과 집계
            await self._calculate_campaign_performance(campaign)
            
            campaign.status = CampaignStatus.COMPLETED
            campaign.end_date = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"캠페인 종료 실패: {str(e)}")
    
    async def get_campaign_performance(self, campaign_id: int) -> Dict[str, Any]:
        """캠페인 성과 조회"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            # 실시간 성과 집계
            await self._calculate_campaign_performance(campaign)
            
            performance = {
                'campaign_id': campaign.id,
                'campaign_name': campaign.name,
                'status': campaign.status.value,
                'metrics': {
                    'sent': campaign.sent_count,
                    'delivered': campaign.delivered_count,
                    'opened': campaign.opened_count,
                    'clicked': campaign.clicked_count,
                    'converted': campaign.converted_count,
                    'unsubscribed': campaign.unsubscribed_count
                },
                'rates': {
                    'delivery_rate': campaign.delivery_rate or 0,
                    'open_rate': campaign.open_rate or 0,
                    'click_rate': campaign.click_rate or 0,
                    'conversion_rate': campaign.conversion_rate or 0
                },
                'financial': {
                    'budget': campaign.budget or 0,
                    'spent': campaign.spent_amount or 0,
                    'revenue': campaign.revenue_generated or 0,
                    'roi': campaign.roi or 0,
                    'average_order_value': campaign.average_order_value or 0
                },
                'goal': {
                    'type': campaign.goal_type,
                    'target': campaign.goal_value,
                    'achieved': self._calculate_goal_achievement(campaign)
                }
            }
            
            # A/B 테스트 결과 포함
            if campaign.is_ab_test and campaign.ab_variants:
                performance['ab_test_results'] = [
                    {
                        'variant': variant.variant_name,
                        'open_rate': variant.open_rate or 0,
                        'click_rate': variant.click_rate or 0,
                        'conversion_rate': variant.conversion_rate or 0,
                        'is_winner': variant.is_winner
                    }
                    for variant in campaign.ab_variants
                ]
            
            return performance
            
        except Exception as e:
            raise BusinessException(f"캠페인 성과 조회 실패: {str(e)}")
    
    async def get_campaign_recipients(self, campaign_id: int, 
                                    status: Optional[str] = None,
                                    offset: int = 0, 
                                    limit: int = 100) -> Dict[str, Any]:
        """캠페인 수신자 목록 조회"""
        try:
            query = self.db.query(MarketingMessage).filter(
                MarketingMessage.campaign_id == campaign_id
            )
            
            if status:
                query = query.filter(MarketingMessage.status == MessageStatus(status))
            
            total = query.count()
            messages = query.offset(offset).limit(limit).all()
            
            recipients = []
            for msg in messages:
                customer = self.db.query(Customer).filter(
                    Customer.id == msg.customer_id
                ).first()
                
                recipients.append({
                    'message_id': msg.id,
                    'customer_id': msg.customer_id,
                    'customer_name': customer.name if customer else None,
                    'customer_email': customer.email if customer else None,
                    'status': msg.status.value,
                    'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
                    'opened_at': msg.opened_at.isoformat() if msg.opened_at else None,
                    'clicked_at': msg.clicked_at.isoformat() if msg.clicked_at else None,
                    'converted_at': msg.converted_at.isoformat() if msg.converted_at else None
                })
            
            return {
                'total': total,
                'offset': offset,
                'limit': limit,
                'recipients': recipients
            }
            
        except Exception as e:
            raise BusinessException(f"수신자 목록 조회 실패: {str(e)}")
    
    async def _calculate_recipients(self, campaign: MarketingCampaign) -> int:
        """예상 수신자 수 계산"""
        try:
            # 세그먼트 기반 고객 수
            segment_customers = set()
            for segment in campaign.target_segments:
                customers = await self.segmentation_engine.get_segment_customers(segment.id)
                segment_customers.update([c.id for c in customers])
            
            # 추가 조건 적용
            if campaign.target_conditions:
                # TODO: 조건 기반 필터링 구현
                pass
            
            return len(segment_customers)
            
        except Exception as e:
            return 0
    
    async def _validate_campaign(self, campaign: MarketingCampaign):
        """캠페인 유효성 검증"""
        if not campaign.content_template:
            raise BusinessException("캠페인 콘텐츠가 설정되지 않았습니다")
        
        if campaign.campaign_type == CampaignType.EMAIL and not campaign.subject:
            raise BusinessException("이메일 캠페인은 제목이 필요합니다")
        
        if campaign.expected_recipients == 0:
            raise BusinessException("캠페인 수신자가 없습니다")
        
        if campaign.start_date and campaign.end_date:
            if campaign.start_date >= campaign.end_date:
                raise BusinessException("종료일은 시작일보다 늦어야 합니다")
    
    async def _create_campaign_messages(self, campaign: MarketingCampaign):
        """캠페인 메시지 생성"""
        try:
            # 타겟 고객 목록 가져오기
            target_customers = set()
            for segment in campaign.target_segments:
                customers = await self.segmentation_engine.get_segment_customers(segment.id)
                target_customers.update(customers)
            
            # 각 고객에 대한 메시지 생성
            for customer in target_customers:
                # 개인화된 콘텐츠 생성
                personalized_content = await self._personalize_content(
                    campaign.content_template,
                    customer,
                    campaign.personalization_tags
                )
                
                message = MarketingMessage(
                    campaign_id=campaign.id,
                    customer_id=customer.id,
                    message_type=campaign.campaign_type.value,
                    channel=campaign.campaign_type.value,
                    personalized_subject=await self._personalize_content(
                        campaign.subject, customer, campaign.personalization_tags
                    ) if campaign.subject else None,
                    personalized_content=personalized_content,
                    scheduled_at=campaign.start_date or datetime.utcnow(),
                    status=MessageStatus.PENDING
                )
                
                self.db.add(message)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"메시지 생성 실패: {str(e)}")
    
    async def _personalize_content(self, template: str, customer: Customer, 
                                 tags: List[str]) -> str:
        """콘텐츠 개인화"""
        try:
            personalized = template
            
            # 기본 태그 치환
            replacements = {
                '{{name}}': customer.name or '고객님',
                '{{email}}': customer.email or '',
                '{{phone}}': customer.phone or '',
                '{{first_name}}': customer.name.split()[0] if customer.name else '고객님',
                '{{city}}': customer.city or '',
                '{{total_orders}}': str(customer.total_orders or 0),
                '{{lifetime_value}}': f"{customer.lifetime_value or 0:,.0f}원"
            }
            
            for tag, value in replacements.items():
                personalized = personalized.replace(tag, value)
            
            # AI 기반 고급 개인화
            if '{{ai_recommendation}}' in personalized:
                recommendation = await self.ai_manager.generate_personalized_recommendation(
                    customer_id=customer.id,
                    context='marketing_campaign'
                )
                personalized = personalized.replace('{{ai_recommendation}}', recommendation)
            
            return personalized
            
        except Exception as e:
            return template  # 개인화 실패 시 원본 반환
    
    async def _calculate_campaign_performance(self, campaign: MarketingCampaign):
        """캠페인 성과 계산"""
        try:
            # 메시지 상태별 집계
            status_counts = self.db.query(
                MarketingMessage.status,
                func.count(MarketingMessage.id)
            ).filter(
                MarketingMessage.campaign_id == campaign.id
            ).group_by(MarketingMessage.status).all()
            
            status_dict = {status.value: count for status, count in status_counts}
            
            # 기본 지표 업데이트
            campaign.sent_count = status_dict.get(MessageStatus.SENT.value, 0) + \
                                status_dict.get(MessageStatus.DELIVERED.value, 0) + \
                                status_dict.get(MessageStatus.OPENED.value, 0) + \
                                status_dict.get(MessageStatus.CLICKED.value, 0) + \
                                status_dict.get(MessageStatus.CONVERTED.value, 0)
            
            campaign.delivered_count = campaign.sent_count - status_dict.get(MessageStatus.BOUNCED.value, 0)
            campaign.opened_count = status_dict.get(MessageStatus.OPENED.value, 0) + \
                                  status_dict.get(MessageStatus.CLICKED.value, 0) + \
                                  status_dict.get(MessageStatus.CONVERTED.value, 0)
            campaign.clicked_count = status_dict.get(MessageStatus.CLICKED.value, 0) + \
                                   status_dict.get(MessageStatus.CONVERTED.value, 0)
            campaign.converted_count = status_dict.get(MessageStatus.CONVERTED.value, 0)
            campaign.unsubscribed_count = status_dict.get(MessageStatus.UNSUBSCRIBED.value, 0)
            
            # 비율 계산
            if campaign.sent_count > 0:
                campaign.delivery_rate = (campaign.delivered_count / campaign.sent_count) * 100
                campaign.open_rate = (campaign.opened_count / campaign.delivered_count) * 100 if campaign.delivered_count > 0 else 0
                campaign.click_rate = (campaign.clicked_count / campaign.opened_count) * 100 if campaign.opened_count > 0 else 0
                campaign.conversion_rate = (campaign.converted_count / campaign.clicked_count) * 100 if campaign.clicked_count > 0 else 0
            
            # 수익 계산
            revenue_data = self.db.query(
                func.sum(MarketingMessage.attributed_revenue),
                func.avg(MarketingMessage.conversion_value)
            ).filter(
                MarketingMessage.campaign_id == campaign.id,
                MarketingMessage.status == MessageStatus.CONVERTED
            ).first()
            
            campaign.revenue_generated = revenue_data[0] or 0
            campaign.average_order_value = revenue_data[1] or 0
            
            # ROI 계산
            if campaign.spent_amount and campaign.spent_amount > 0:
                campaign.roi = ((campaign.revenue_generated - campaign.spent_amount) / campaign.spent_amount) * 100
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"성과 계산 실패: {str(e)}")
    
    def _calculate_goal_achievement(self, campaign: MarketingCampaign) -> float:
        """목표 달성률 계산"""
        if not campaign.goal_type or not campaign.goal_value:
            return 0
        
        if campaign.goal_type == 'revenue':
            return (campaign.revenue_generated / campaign.goal_value) * 100
        elif campaign.goal_type == 'conversion':
            return (campaign.converted_count / campaign.goal_value) * 100
        elif campaign.goal_type == 'engagement':
            engagement = campaign.opened_count + campaign.clicked_count
            return (engagement / campaign.goal_value) * 100
        
        return 0
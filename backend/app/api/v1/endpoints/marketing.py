"""
마케팅 자동화 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.dependencies import get_db, get_current_user
from app.schemas.marketing import (
    # Campaign schemas
    MarketingCampaignCreate, MarketingCampaignUpdate, MarketingCampaignResponse,
    CampaignPerformance, MarketingAnalyticsRequest, MarketingAnalyticsResponse,
    
    # Segment schemas
    MarketingSegmentCreate, MarketingSegmentUpdate, MarketingSegmentResponse,
    
    # Promotion schemas
    PromotionCodeCreate, PromotionCodeUpdate, PromotionCodeResponse,
    PromotionValidation, PromotionValidationResponse, BulkPromotionCodeRequest,
    
    # Automation schemas
    AutomationWorkflowCreate, AutomationWorkflowUpdate, AutomationWorkflowResponse,
    WorkflowExecutionStart, WorkflowExecutionResponse,
    AutomationTriggerCreate, AutomationTriggerResponse, TriggerEventRequest,
    
    # A/B Testing schemas
    ABTestVariantCreate, ABTestVariantResponse, ABTestAnalysis,
    
    # Social Media schemas
    SocialMediaPostCreate, SocialMediaPostUpdate, SocialMediaPostResponse,
    BulkEmailScheduleRequest,
    
    # Service schemas
    EmailSendRequest, SMSSendRequest, EmailTemplateValidation, SMSContentValidation,
    
    # Analytics schemas
    MarketingDashboardRequest, CustomerJourneyRequest,
    
    # Personalization schemas
    PersonalizationRequest, ProductRecommendationRequest, PersonalizationInsightsResponse,
    
    # Retargeting schemas
    CartAbandonmentCampaignRequest, BrowseAbandonmentCampaignRequest,
    CustomerWinbackCampaignRequest, PostPurchaseCampaignRequest,
    RetargetingAnalysisRequest
)
from app.services.marketing import (
    CampaignManager, EmailService, SMSService, AutomationEngine,
    ABTestingService, PersonalizationEngine, MarketingAnalyticsService,
    SegmentationService, PromotionService, SocialMediaService,
    RetargetingService
)

router = APIRouter(prefix="/marketing", tags=["marketing"])


# Campaign endpoints
@router.post("/campaigns", response_model=MarketingCampaignResponse)
async def create_campaign(
    campaign_data: MarketingCampaignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """마케팅 캠페인 생성"""
    try:
        campaign_manager = CampaignManager(db)
        campaign = await campaign_manager.create_campaign(campaign_data.model_dump())
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns", response_model=List[MarketingCampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    campaign_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 목록 조회"""
    try:
        query = db.query(MarketingCampaign)
        
        if status:
            query = query.filter(MarketingCampaign.status == status)
        if campaign_type:
            query = query.filter(MarketingCampaign.campaign_type == campaign_type)
        
        campaigns = query.offset(skip).limit(limit).all()
        return campaigns
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
async def get_campaign(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 상세 조회"""
    campaign = db.query(MarketingCampaign).filter(
        MarketingCampaign.id == campaign_id
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다")
    
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=MarketingCampaignResponse)
async def update_campaign(
    campaign_id: int = Path(..., gt=0),
    update_data: MarketingCampaignUpdate = ...,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 수정"""
    try:
        campaign_manager = CampaignManager(db)
        campaign = await campaign_manager.update_campaign(
            campaign_id, 
            update_data.model_dump(exclude_unset=True)
        )
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/start", response_model=MarketingCampaignResponse)
async def start_campaign(
    campaign_id: int = Path(..., gt=0),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 시작"""
    try:
        campaign_manager = CampaignManager(db)
        campaign = await campaign_manager.start_campaign(campaign_id)
        
        # 백그라운드에서 메시지 발송
        if campaign.campaign_type in ['email', 'sms']:
            background_tasks.add_task(
                send_campaign_messages,
                campaign_id,
                campaign.campaign_type,
                db
            )
        
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/pause", response_model=MarketingCampaignResponse)
async def pause_campaign(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 일시중지"""
    try:
        campaign_manager = CampaignManager(db)
        campaign = await campaign_manager.pause_campaign(campaign_id)
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/resume", response_model=MarketingCampaignResponse)
async def resume_campaign(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 재개"""
    try:
        campaign_manager = CampaignManager(db)
        campaign = await campaign_manager.resume_campaign(campaign_id)
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/complete", response_model=MarketingCampaignResponse)
async def complete_campaign(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 종료"""
    try:
        campaign_manager = CampaignManager(db)
        campaign = await campaign_manager.complete_campaign(campaign_id)
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns/{campaign_id}/performance", response_model=CampaignPerformance)
async def get_campaign_performance(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 성과 조회"""
    try:
        campaign_manager = CampaignManager(db)
        performance = await campaign_manager.get_campaign_performance(campaign_id)
        return performance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns/{campaign_id}/recipients")
async def get_campaign_recipients(
    campaign_id: int = Path(..., gt=0),
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 수신자 목록 조회"""
    try:
        campaign_manager = CampaignManager(db)
        recipients = await campaign_manager.get_campaign_recipients(
            campaign_id, status, skip, limit
        )
        return recipients
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Segment endpoints
@router.post("/segments", response_model=MarketingSegmentResponse)
async def create_segment(
    segment_data: MarketingSegmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """마케팅 세그먼트 생성"""
    try:
        segmentation_service = SegmentationService(db)
        segment = await segmentation_service.create_segment(segment_data.model_dump())
        return segment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/segments", response_model=List[MarketingSegmentResponse])
async def list_segments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """세그먼트 목록 조회"""
    try:
        query = db.query(MarketingSegment)
        
        if is_active is not None:
            query = query.filter(MarketingSegment.is_active == is_active)
        
        segments = query.offset(skip).limit(limit).all()
        return segments
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/segments/{segment_id}", response_model=MarketingSegmentResponse)
async def get_segment(
    segment_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """세그먼트 상세 조회"""
    segment = db.query(MarketingSegment).filter(
        MarketingSegment.id == segment_id
    ).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail="세그먼트를 찾을 수 없습니다")
    
    return segment


@router.put("/segments/{segment_id}", response_model=MarketingSegmentResponse)
async def update_segment(
    segment_id: int = Path(..., gt=0),
    update_data: MarketingSegmentUpdate = ...,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """세그먼트 수정"""
    try:
        segmentation_service = SegmentationService(db)
        segment = await segmentation_service.update_segment(
            segment_id,
            update_data.model_dump(exclude_unset=True)
        )
        return segment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/segments/{segment_id}/customers")
async def get_segment_customers(
    segment_id: int = Path(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """세그먼트 고객 목록 조회"""
    try:
        segmentation_service = SegmentationService(db)
        customers = await segmentation_service.get_segment_customers(
            segment_id, skip, limit
        )
        return customers
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/segments/{segment_id}/refresh", response_model=MarketingSegmentResponse)
async def refresh_segment(
    segment_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """세그먼트 새로고침"""
    try:
        segmentation_service = SegmentationService(db)
        segment = await segmentation_service.refresh_segment(segment_id)
        return segment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/segments/smart", response_model=List[MarketingSegmentResponse])
async def create_smart_segments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """스마트 세그먼트 자동 생성"""
    try:
        segmentation_service = SegmentationService(db)
        segments = await segmentation_service.create_smart_segments()
        return segments
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/segments/analyze-overlap")
async def analyze_segment_overlap(
    segment_ids: List[int],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """세그먼트 중복 분석"""
    try:
        segmentation_service = SegmentationService(db)
        analysis = await segmentation_service.analyze_segment_overlap(segment_ids)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Promotion endpoints
@router.post("/promotions", response_model=PromotionCodeResponse)
async def create_promotion_code(
    promotion_data: PromotionCodeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """프로모션 코드 생성"""
    try:
        promotion_service = PromotionService(db)
        promotion = await promotion_service.create_promotion_code(
            promotion_data.model_dump()
        )
        return promotion
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/promotions/bulk", response_model=List[PromotionCodeResponse])
async def create_bulk_promotion_codes(
    bulk_data: BulkPromotionCodeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """대량 프로모션 코드 생성"""
    try:
        promotion_service = PromotionService(db)
        promotions = await promotion_service.create_bulk_promotion_codes(
            bulk_data.model_dump()
        )
        return promotions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/promotions/validate", response_model=PromotionValidationResponse)
async def validate_promotion_code(
    validation_data: PromotionValidation,
    db: Session = Depends(get_db)
):
    """프로모션 코드 검증"""
    try:
        promotion_service = PromotionService(db)
        result = await promotion_service.validate_promotion_code(
            validation_data.code,
            validation_data.customer_id,
            validation_data.order_data
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/promotions/{code}/apply")
async def apply_promotion_code(
    code: str,
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db)
):
    """프로모션 코드 적용"""
    try:
        promotion_service = PromotionService(db)
        result = await promotion_service.apply_promotion_code(
            code, customer_id, order_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/promotions", response_model=List[PromotionCodeResponse])
async def list_promotion_codes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """프로모션 코드 목록 조회"""
    try:
        query = db.query(PromotionCode)
        
        if is_active is not None:
            query = query.filter(PromotionCode.is_active == is_active)
        
        promotions = query.offset(skip).limit(limit).all()
        return promotions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/promotions/{promotion_id}", response_model=PromotionCodeResponse)
async def get_promotion_code(
    promotion_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """프로모션 코드 상세 조회"""
    promotion = db.query(PromotionCode).filter(
        PromotionCode.id == promotion_id
    ).first()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="프로모션 코드를 찾을 수 없습니다")
    
    return promotion


@router.put("/promotions/{promotion_id}", response_model=PromotionCodeResponse)
async def update_promotion_code(
    promotion_id: int = Path(..., gt=0),
    update_data: PromotionCodeUpdate = ...,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """프로모션 코드 수정"""
    try:
        promotion = db.query(PromotionCode).filter(
            PromotionCode.id == promotion_id
        ).first()
        
        if not promotion:
            raise HTTPException(status_code=404, detail="프로모션 코드를 찾을 수 없습니다")
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(promotion, field, value)
        
        promotion.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(promotion)
        
        return promotion
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/promotions/{promotion_id}/deactivate", response_model=PromotionCodeResponse)
async def deactivate_promotion_code(
    promotion_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """프로모션 코드 비활성화"""
    try:
        promotion_service = PromotionService(db)
        promotion = await promotion_service.deactivate_promotion_code(promotion_id)
        return promotion
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/promotions/{promotion_id}/analytics")
async def get_promotion_analytics(
    promotion_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """프로모션 분석 데이터"""
    try:
        promotion_service = PromotionService(db)
        analytics = await promotion_service.get_promotion_analytics(promotion_id)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Automation endpoints
@router.post("/workflows", response_model=AutomationWorkflowResponse)
async def create_workflow(
    workflow_data: AutomationWorkflowCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """자동화 워크플로우 생성"""
    try:
        automation_engine = AutomationEngine(db)
        workflow = await automation_engine.create_workflow(workflow_data.model_dump())
        return workflow
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows", response_model=List[AutomationWorkflowResponse])
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """워크플로우 목록 조회"""
    try:
        query = db.query(AutomationWorkflow)
        
        if is_active is not None:
            query = query.filter(AutomationWorkflow.is_active == is_active)
        
        workflows = query.offset(skip).limit(limit).all()
        return workflows
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows/{workflow_id}", response_model=AutomationWorkflowResponse)
async def get_workflow(
    workflow_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """워크플로우 상세 조회"""
    workflow = db.query(AutomationWorkflow).filter(
        AutomationWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="워크플로우를 찾을 수 없습니다")
    
    return workflow


@router.put("/workflows/{workflow_id}", response_model=AutomationWorkflowResponse)
async def update_workflow(
    workflow_id: int = Path(..., gt=0),
    update_data: AutomationWorkflowUpdate = ...,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """워크플로우 수정"""
    try:
        automation_engine = AutomationEngine(db)
        workflow = await automation_engine.update_workflow(
            workflow_id,
            update_data.model_dump(exclude_unset=True)
        )
        return workflow
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: int = Path(..., gt=0),
    execution_data: WorkflowExecutionStart = ...,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """워크플로우 실행"""
    try:
        automation_engine = AutomationEngine(db)
        execution = await automation_engine.start_workflow_execution(
            workflow_id,
            execution_data.customer_id,
            execution_data.context
        )
        return execution
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/triggers", response_model=AutomationTriggerResponse)
async def create_trigger(
    trigger_data: AutomationTriggerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """자동화 트리거 생성"""
    try:
        trigger = AutomationTrigger(**trigger_data.model_dump())
        db.add(trigger)
        db.commit()
        db.refresh(trigger)
        return trigger
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/triggers/event")
async def trigger_event(
    event_data: TriggerEventRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """이벤트 트리거"""
    try:
        automation_engine = AutomationEngine(db)
        background_tasks.add_task(
            automation_engine.trigger_workflow,
            event_data.model_dump()
        )
        return {"message": "이벤트가 트리거되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# A/B Testing endpoints
@router.post("/campaigns/{campaign_id}/ab-test", response_model=List[ABTestVariantResponse])
async def create_ab_test(
    campaign_id: int = Path(..., gt=0),
    variants: List[ABTestVariantCreate] = ...,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """A/B 테스트 생성"""
    try:
        ab_testing_service = ABTestingService(db)
        test_variants = await ab_testing_service.create_ab_test(
            campaign_id,
            [v.model_dump() for v in variants]
        )
        return test_variants
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns/{campaign_id}/ab-test/analysis", response_model=ABTestAnalysis)
async def analyze_ab_test(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """A/B 테스트 분석"""
    try:
        ab_testing_service = ABTestingService(db)
        analysis = await ab_testing_service.analyze_ab_test(campaign_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/ab-test/apply-winner", response_model=MarketingCampaignResponse)
async def apply_ab_test_winner(
    campaign_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """A/B 테스트 승자 적용"""
    try:
        ab_testing_service = ABTestingService(db)
        campaign = await ab_testing_service.apply_winner(campaign_id)
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Email/SMS service endpoints
@router.post("/email/send")
async def send_emails(
    send_request: EmailSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """이메일 발송"""
    try:
        email_service = EmailService(db)
        background_tasks.add_task(
            email_service.send_campaign_emails,
            send_request.message_ids,
            send_request.batch_size
        )
        return {"message": "이메일 발송이 시작되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/email/validate-template")
async def validate_email_template(
    validation_data: EmailTemplateValidation,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """이메일 템플릿 검증"""
    try:
        email_service = EmailService(db)
        result = email_service.validate_email_template(validation_data.template)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/email/track/open/{message_id}")
async def track_email_open(
    message_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """이메일 오픈 추적"""
    try:
        email_service = EmailService(db)
        await email_service.track_email_open(message_id)
        # 1x1 투명 픽셀 반환
        return Response(
            content=base64.b64decode(
                "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
            ),
            media_type="image/gif"
        )
    except Exception as e:
        # 오류가 발생해도 픽셀은 반환
        return Response(
            content=base64.b64decode(
                "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
            ),
            media_type="image/gif"
        )


@router.get("/email/track/click")
async def track_email_click(
    message_id: int = Query(..., gt=0),
    url: str = Query(...),
    db: Session = Depends(get_db)
):
    """이메일 클릭 추적 및 리다이렉트"""
    try:
        email_service = EmailService(db)
        await email_service.track_email_click(message_id, url)
        return RedirectResponse(url=url)
    except Exception as e:
        return RedirectResponse(url=url)


@router.post("/sms/send")
async def send_sms(
    send_request: SMSSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """SMS 발송"""
    try:
        sms_service = SMSService(db)
        background_tasks.add_task(
            sms_service.send_campaign_sms,
            send_request.message_ids,
            send_request.batch_size
        )
        return {"message": "SMS 발송이 시작되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sms/validate-content")
async def validate_sms_content(
    validation_data: SMSContentValidation,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """SMS 내용 검증"""
    try:
        sms_service = SMSService(db)
        result = sms_service.validate_sms_content(validation_data.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Social Media endpoints
@router.post("/social/posts", response_model=SocialMediaPostResponse)
async def create_social_post(
    post_data: SocialMediaPostCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """소셜미디어 게시물 생성"""
    try:
        social_media_service = SocialMediaService(db)
        post = await social_media_service.create_social_post(post_data.model_dump())
        return post
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/social/posts/bulk-schedule", response_model=List[SocialMediaPostResponse])
async def bulk_schedule_posts(
    bulk_data: BulkEmailScheduleRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """대량 게시물 스케줄링"""
    try:
        social_media_service = SocialMediaService(db)
        posts = await social_media_service.schedule_posts(
            [p.model_dump() for p in bulk_data.posts_data]
        )
        return posts
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/social/posts/{post_id}/publish")
async def publish_social_post(
    post_id: int = Path(..., gt=0),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """소셜미디어 게시물 발행"""
    try:
        social_media_service = SocialMediaService(db)
        result = await social_media_service.publish_post(post_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/social/posts/{post_id}/metrics", response_model=SocialMediaPostResponse)
async def update_social_metrics(
    post_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """소셜미디어 지표 업데이트"""
    try:
        social_media_service = SocialMediaService(db)
        post = await social_media_service.update_post_metrics(post_id)
        return post
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/social/calendar")
async def get_social_calendar(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """소셜미디어 캘린더 조회"""
    try:
        social_media_service = SocialMediaService(db)
        calendar = await social_media_service.get_social_media_calendar(
            start_date, end_date
        )
        return calendar
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/social/content-variations")
async def generate_content_variations(
    base_content: str,
    platforms: List[str],
    count: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """AI 콘텐츠 변형 생성"""
    try:
        social_media_service = SocialMediaService(db)
        variations = await social_media_service.generate_content_variations(
            base_content, platforms, count
        )
        return variations
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Analytics endpoints
@router.post("/analytics/campaign", response_model=MarketingAnalyticsResponse)
async def analyze_campaign(
    request_data: MarketingAnalyticsRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """캠페인 분석"""
    try:
        analytics_service = MarketingAnalyticsService(db)
        analysis = await analytics_service.generate_campaign_analytics(
            request_data.campaign_id
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analytics/dashboard")
async def get_marketing_dashboard(
    request_data: MarketingDashboardRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """마케팅 대시보드"""
    try:
        analytics_service = MarketingAnalyticsService(db)
        dashboard = await analytics_service.generate_marketing_dashboard(
            {"start_date": request_data.start_date, "end_date": request_data.end_date}
        )
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analytics/customer-journey")
async def analyze_customer_journey(
    request_data: CustomerJourneyRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """고객 여정 분석"""
    try:
        analytics_service = MarketingAnalyticsService(db)
        journey = await analytics_service.analyze_customer_journey(
            request_data.customer_id
        )
        return journey
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Personalization endpoints
@router.post("/personalization/content")
async def personalize_content(
    request_data: PersonalizationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """콘텐츠 개인화"""
    try:
        personalization_engine = PersonalizationEngine(db)
        content = await personalization_engine.generate_personalized_content(
            request_data.customer_id,
            request_data.template,
            request_data.context
        )
        return {"personalized_content": content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/personalization/recommendations")
async def get_product_recommendations(
    request_data: ProductRecommendationRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """상품 추천"""
    try:
        personalization_engine = PersonalizationEngine(db)
        recommendations = await personalization_engine.generate_product_recommendations(
            request_data.customer_id,
            request_data.recommendation_type,
            request_data.limit
        )
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/personalization/insights/{customer_id}", response_model=PersonalizationInsightsResponse)
async def get_personalization_insights(
    customer_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """개인화 인사이트"""
    try:
        personalization_engine = PersonalizationEngine(db)
        insights = await personalization_engine.get_personalization_insights(customer_id)
        return insights
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Retargeting endpoints
@router.post("/retargeting/cart-abandonment", response_model=MarketingCampaignResponse)
async def create_cart_abandonment_campaign(
    request_data: CartAbandonmentCampaignRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """장바구니 이탈 캠페인 생성"""
    try:
        retargeting_service = RetargetingService(db)
        campaign = await retargeting_service.create_cart_abandonment_campaign(
            request_data.model_dump()
        )
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retargeting/browse-abandonment", response_model=MarketingCampaignResponse)
async def create_browse_abandonment_campaign(
    request_data: BrowseAbandonmentCampaignRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """상품 조회 이탈 캠페인 생성"""
    try:
        retargeting_service = RetargetingService(db)
        campaign = await retargeting_service.create_browse_abandonment_campaign(
            request_data.model_dump()
        )
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retargeting/customer-winback", response_model=MarketingCampaignResponse)
async def create_customer_winback_campaign(
    request_data: CustomerWinbackCampaignRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """고객 재활성화 캠페인 생성"""
    try:
        retargeting_service = RetargetingService(db)
        campaign = await retargeting_service.create_customer_winback_campaign(
            request_data.model_dump()
        )
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retargeting/post-purchase", response_model=MarketingCampaignResponse)
async def create_post_purchase_campaign(
    request_data: PostPurchaseCampaignRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """구매 후 리타겟팅 캠페인 생성"""
    try:
        retargeting_service = RetargetingService(db)
        campaign = await retargeting_service.create_post_purchase_campaign(
            request_data.model_dump()
        )
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retargeting/analyze")
async def analyze_retargeting_performance(
    request_data: RetargetingAnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """리타겟팅 성과 분석"""
    try:
        retargeting_service = RetargetingService(db)
        analysis = await retargeting_service.analyze_retargeting_performance(
            request_data.campaign_ids
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Background task functions
async def send_campaign_messages(campaign_id: int, campaign_type: str, db: Session):
    """캠페인 메시지 발송 (백그라운드)"""
    try:
        # 메시지 ID 수집
        messages = db.query(MarketingMessage).filter(
            MarketingMessage.campaign_id == campaign_id,
            MarketingMessage.status == MessageStatus.PENDING
        ).all()
        
        message_ids = [msg.id for msg in messages]
        
        if campaign_type == 'email':
            email_service = EmailService(db)
            await email_service.send_campaign_emails(message_ids)
        elif campaign_type == 'sms':
            sms_service = SMSService(db)
            await sms_service.send_campaign_sms(message_ids)
            
    except Exception as e:
        print(f"메시지 발송 실패: {str(e)}")


# Additional imports needed
from fastapi.responses import Response, RedirectResponse
import base64
from app.models.marketing import (
    MarketingCampaign, MarketingSegment, PromotionCode,
    AutomationWorkflow, AutomationTrigger, MarketingMessage
)
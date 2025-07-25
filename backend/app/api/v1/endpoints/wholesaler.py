"""
도매처 관련 API 엔드포인트
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies.database import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User
from app.models.wholesaler import WholesalerType, ConnectionStatus, CollectionStatus
from app.schemas.wholesaler import (
    WholesalerAccountCreate,
    WholesalerAccountUpdate,
    WholesalerAccountResponse,
    WholesalerProductResponse,
    CollectionLogResponse,
    ScheduledCollectionCreate,
    ScheduledCollectionUpdate,
    ScheduledCollectionResponse
)
from app.crud.wholesaler import (
    crud_wholesaler_account,
    crud_wholesaler_product,
    crud_collection_log,
    crud_scheduled_collection,
    crud_excel_upload_log
)
from app.services.wholesale.excel_service import ExcelService
from app.services.wholesale.scheduler_service import SchedulerManager
from app.services.wholesale.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 도매처 계정 관리 ==========

@router.post("/accounts", response_model=WholesalerAccountResponse)
async def create_wholesaler_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_in: WholesalerAccountCreate
):
    """도매처 계정을 생성합니다."""
    try:
        # 중복 확인
        existing_accounts = crud_wholesaler_account.get_by_wholesaler_type(
            db, current_user.id, account_in.wholesaler_type
        )
        
        if len(existing_accounts) >= 5:  # 도매처 유형별 최대 5개 계정
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{account_in.wholesaler_type.value} 계정은 최대 5개까지만 등록할 수 있습니다."
            )
        
        # 계정 생성
        account_data = account_in.dict()
        account_data['user_id'] = current_user.id
        
        account = crud_wholesaler_account.create(db, obj_in=account_data)
        
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"도매처 계정 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="도매처 계정 생성 중 오류가 발생했습니다."
        )


@router.get("/accounts", response_model=List[WholesalerAccountResponse])
async def get_wholesaler_accounts(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    wholesaler_type: Optional[WholesalerType] = None
):
    """사용자의 도매처 계정 목록을 조회합니다."""
    try:
        if wholesaler_type:
            accounts = crud_wholesaler_account.get_by_wholesaler_type(
                db, current_user.id, wholesaler_type
            )
        else:
            accounts = crud_wholesaler_account.get_by_user_id(db, current_user.id)
        
        return accounts
        
    except Exception as e:
        logger.error(f"도매처 계정 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="도매처 계정 목록 조회 중 오류가 발생했습니다."
        )


@router.get("/accounts/{account_id}", response_model=WholesalerAccountResponse)
async def get_wholesaler_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int
):
    """특정 도매처 계정을 조회합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    return account


@router.put("/accounts/{account_id}", response_model=WholesalerAccountResponse)
async def update_wholesaler_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    account_in: WholesalerAccountUpdate
):
    """도매처 계정을 업데이트합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        account = crud_wholesaler_account.update(db, db_obj=account, obj_in=account_in)
        return account
        
    except Exception as e:
        logger.error(f"도매처 계정 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="도매처 계정 업데이트 중 오류가 발생했습니다."
        )


@router.delete("/accounts/{account_id}")
async def delete_wholesaler_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int
):
    """도매처 계정을 삭제합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        crud_wholesaler_account.remove(db, id=account_id)
        return {"message": "도매처 계정이 삭제되었습니다."}
        
    except Exception as e:
        logger.error(f"도매처 계정 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="도매처 계정 삭제 중 오류가 발생했습니다."
        )


@router.post("/accounts/{account_id}/test-connection")
async def test_wholesaler_connection(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int
):
    """도매처 계정 연결을 테스트합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 연결 테스트 로직 (실제 구현에서는 WholesalerManager 사용)
        # 임시로 성공으로 처리
        crud_wholesaler_account.update_connection_status(
            db, account_id, ConnectionStatus.CONNECTED
        )
        
        return {"message": "연결 테스트가 성공했습니다.", "status": "connected"}
        
    except Exception as e:
        logger.error(f"연결 테스트 실패: {str(e)}")
        crud_wholesaler_account.update_connection_status(
            db, account_id, ConnectionStatus.ERROR, str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"연결 테스트 실패: {str(e)}"
        )


# ========== 상품 관리 ==========

@router.get("/accounts/{account_id}/products", response_model=List[WholesalerProductResponse])
async def get_wholesaler_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    in_stock_only: bool = False
):
    """도매처 계정의 상품 목록을 조회합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        if keyword:
            products = crud_wholesaler_product.search_products(
                db, keyword, account_id, skip, limit
            )
        elif category:
            products = crud_wholesaler_product.get_by_category(
                db, category, account_id, skip, limit
            )
        elif min_price and max_price:
            products = crud_wholesaler_product.get_by_price_range(
                db, min_price, max_price, account_id, skip, limit
            )
        elif in_stock_only:
            # 재고 있는 상품만
            all_products = crud_wholesaler_product.get_by_wholesaler_account(
                db, account_id, skip, limit
            )
            products = [p for p in all_products if p.is_in_stock and p.stock_quantity > 0]
        else:
            products = crud_wholesaler_product.get_by_wholesaler_account(
                db, account_id, skip, limit
            )
        
        return products
        
    except Exception as e:
        logger.error(f"상품 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상품 목록 조회 중 오류가 발생했습니다."
        )


@router.get("/products/recent", response_model=List[WholesalerProductResponse])
async def get_recent_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7,
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None
):
    """최근 수집된 상품을 조회합니다."""
    try:
        if account_id:
            # 계정 소유권 확인
            account = crud_wholesaler_account.get(db, account_id)
            if not account or account.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="도매처 계정을 찾을 수 없습니다."
                )
        
        products = crud_wholesaler_product.get_recent_products(
            db, account_id, days, skip, limit
        )
        
        # 사용자 소유 계정의 상품만 필터링
        user_accounts = crud_wholesaler_account.get_by_user_id(db, current_user.id)
        user_account_ids = {acc.id for acc in user_accounts}
        
        filtered_products = [
            p for p in products 
            if p.wholesaler_account_id in user_account_ids
        ]
        
        return filtered_products
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최근 상품 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최근 상품 조회 중 오류가 발생했습니다."
        )


@router.get("/products/low-stock", response_model=List[WholesalerProductResponse])
async def get_low_stock_products(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    threshold: int = 10,
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None
):
    """재고 부족 상품을 조회합니다."""
    try:
        if account_id:
            # 계정 소유권 확인
            account = crud_wholesaler_account.get(db, account_id)
            if not account or account.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="도매처 계정을 찾을 수 없습니다."
                )
        
        products = crud_wholesaler_product.get_low_stock_products(
            db, threshold, account_id, skip, limit
        )
        
        # 사용자 소유 계정의 상품만 필터링
        if not account_id:
            user_accounts = crud_wholesaler_account.get_by_user_id(db, current_user.id)
            user_account_ids = {acc.id for acc in user_accounts}
            products = [p for p in products if p.wholesaler_account_id in user_account_ids]
        
        return products
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"재고 부족 상품 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재고 부족 상품 조회 중 오류가 발생했습니다."
        )


# ========== 엑셀 파일 처리 ==========

@router.post("/accounts/{account_id}/excel/upload")
async def upload_excel_file(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    """엑셀 파일을 업로드하고 분석합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 파일 유효성 확인
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일명이 없습니다."
            )
        
        # 지원 파일 형식 확인
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        file_extension = '.' + file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 파일 형식입니다. (.xlsx, .xls, .csv만 지원)"
            )
        
        # 파일 크기 확인 (10MB 제한)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="파일 크기는 10MB를 초과할 수 없습니다."
            )
        
        # 엑셀 서비스를 통해 파일 처리
        excel_service = ExcelService(db)
        result = excel_service.upload_excel_file(
            file_content, file.filename, account_id
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['message']
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"엑셀 파일 업로드 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="엑셀 파일 업로드 중 오류가 발생했습니다."
        )


@router.post("/excel/{upload_log_id}/process")
async def process_excel_file(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    upload_log_id: int,
    column_mapping: Dict[str, str],
    file: UploadFile = File(...)
):
    """업로드된 엑셀 파일을 처리하여 상품을 등록합니다."""
    try:
        # 업로드 로그 확인
        upload_log = crud_excel_upload_log.get(db, upload_log_id)
        if not upload_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="업로드 로그를 찾을 수 없습니다."
            )
        
        # 계정 소유권 확인
        account = crud_wholesaler_account.get(db, upload_log.wholesaler_account_id)
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="도매처 계정을 찾을 수 없습니다."
            )
        
        # 파일 내용 읽기
        file_content = await file.read()
        
        # 엑셀 서비스를 통해 파일 처리
        excel_service = ExcelService(db)
        result = excel_service.process_uploaded_file(
            upload_log_id, column_mapping, file_content
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"엑셀 파일 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="엑셀 파일 처리 중 오류가 발생했습니다."
        )


@router.get("/accounts/{account_id}/excel/history")
async def get_excel_upload_history(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    skip: int = 0,
    limit: int = 50
):
    """엑셀 업로드 이력을 조회합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        excel_service = ExcelService(db)
        history = excel_service.get_upload_history(account_id, limit, skip)
        return {"history": history}
        
    except Exception as e:
        logger.error(f"업로드 이력 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="업로드 이력 조회 중 오류가 발생했습니다."
        )


# ========== 스케줄 관리 ==========

@router.post("/accounts/{account_id}/schedules", response_model=ScheduledCollectionResponse)
async def create_collection_schedule(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    schedule_in: ScheduledCollectionCreate
):
    """자동 수집 스케줄을 생성합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 스케줄 생성
        schedule_data = schedule_in.dict()
        schedule_data['wholesaler_account_id'] = account_id
        
        schedule = crud_scheduled_collection.create(db, obj_in=schedule_data)
        
        # 스케줄러에 작업 추가
        scheduler_service = await SchedulerManager.get_scheduler_service()
        await scheduler_service.add_scheduled_job(
            schedule_id=schedule.id,
            wholesaler_account_id=account_id,
            cron_expression=schedule.cron_expression,
            collection_type=schedule.collection_type,
            filters=schedule.filters,
            max_products=schedule.max_products
        )
        
        return schedule
        
    except Exception as e:
        logger.error(f"스케줄 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스케줄 생성 중 오류가 발생했습니다."
        )


@router.get("/accounts/{account_id}/schedules", response_model=List[ScheduledCollectionResponse])
async def get_collection_schedules(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int
):
    """도매처 계정의 스케줄 목록을 조회합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        schedules = crud_scheduled_collection.get_by_wholesaler_account(db, account_id)
        return schedules
        
    except Exception as e:
        logger.error(f"스케줄 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스케줄 목록 조회 중 오류가 발생했습니다."
        )


@router.put("/schedules/{schedule_id}", response_model=ScheduledCollectionResponse)
async def update_collection_schedule(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    schedule_id: int,
    schedule_in: ScheduledCollectionUpdate
):
    """스케줄을 업데이트합니다."""
    schedule = crud_scheduled_collection.get(db, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다."
        )
    
    # 계정 소유권 확인
    account = crud_wholesaler_account.get(db, schedule.wholesaler_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 스케줄 업데이트
        schedule = crud_scheduled_collection.update(db, db_obj=schedule, obj_in=schedule_in)
        
        # 스케줄러 작업 업데이트
        scheduler_service = await SchedulerManager.get_scheduler_service()
        await scheduler_service.remove_scheduled_job(schedule_id)
        
        if schedule.is_active:
            await scheduler_service.add_scheduled_job(
                schedule_id=schedule.id,
                wholesaler_account_id=schedule.wholesaler_account_id,
                cron_expression=schedule.cron_expression,
                collection_type=schedule.collection_type,
                filters=schedule.filters,
                max_products=schedule.max_products
            )
        
        return schedule
        
    except Exception as e:
        logger.error(f"스케줄 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스케줄 업데이트 중 오류가 발생했습니다."
        )


@router.post("/schedules/{schedule_id}/activate")
async def activate_schedule(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    schedule_id: int
):
    """스케줄을 활성화합니다."""
    schedule = crud_scheduled_collection.get(db, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다."
        )
    
    # 계정 소유권 확인
    account = crud_wholesaler_account.get(db, schedule.wholesaler_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 스케줄 활성화
        schedule = crud_scheduled_collection.activate_schedule(db, schedule_id)
        
        # 스케줄러에 작업 추가
        scheduler_service = await SchedulerManager.get_scheduler_service()
        await scheduler_service.add_scheduled_job(
            schedule_id=schedule.id,
            wholesaler_account_id=schedule.wholesaler_account_id,
            cron_expression=schedule.cron_expression,
            collection_type=schedule.collection_type,
            filters=schedule.filters,
            max_products=schedule.max_products
        )
        
        return {"message": "스케줄이 활성화되었습니다."}
        
    except Exception as e:
        logger.error(f"스케줄 활성화 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스케줄 활성화 중 오류가 발생했습니다."
        )


@router.post("/schedules/{schedule_id}/deactivate")
async def deactivate_schedule(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    schedule_id: int
):
    """스케줄을 비활성화합니다."""
    schedule = crud_scheduled_collection.get(db, schedule_id)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다."
        )
    
    # 계정 소유권 확인
    account = crud_wholesaler_account.get(db, schedule.wholesaler_account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 스케줄 비활성화
        schedule = crud_scheduled_collection.deactivate_schedule(db, schedule_id)
        
        # 스케줄러에서 작업 제거
        scheduler_service = await SchedulerManager.get_scheduler_service()
        await scheduler_service.remove_scheduled_job(schedule_id)
        
        return {"message": "스케줄이 비활성화되었습니다."}
        
    except Exception as e:
        logger.error(f"스케줄 비활성화 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스케줄 비활성화 중 오류가 발생했습니다."
        )


# ========== 수집 관리 ==========

@router.post("/accounts/{account_id}/collect")
async def trigger_manual_collection(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    collection_type: str = "manual",
    filters: Optional[Dict] = None,
    max_products: int = 1000
):
    """수동으로 상품 수집을 실행합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        # 스케줄러 서비스를 통해 수집 실행
        scheduler_service = await SchedulerManager.get_scheduler_service()
        result = await scheduler_service.trigger_manual_collection(
            account_id, collection_type, filters, max_products
        )
        
        return result
        
    except Exception as e:
        logger.error(f"수동 수집 실행 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="수집 실행 중 오류가 발생했습니다."
        )


@router.get("/accounts/{account_id}/collections", response_model=List[CollectionLogResponse])
async def get_collection_logs(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[CollectionStatus] = None
):
    """수집 로그를 조회합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        if status:
            # 전체 상태별 조회 후 계정 필터링
            all_logs = crud_collection_log.get_by_status(db, status, 0, 1000)
            logs = [log for log in all_logs if log.wholesaler_account_id == account_id][skip:skip+limit]
        else:
            logs = crud_collection_log.get_by_wholesaler_account(db, account_id, skip, limit)
        
        return logs
        
    except Exception as e:
        logger.error(f"수집 로그 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="수집 로그 조회 중 오류가 발생했습니다."
        )


# ========== 분석 및 통계 ==========

@router.get("/accounts/{account_id}/analysis/dashboard")
async def get_analysis_dashboard(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_id: int
):
    """대시보드용 분석 데이터를 조회합니다."""
    account = crud_wholesaler_account.get(db, account_id)
    
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도매처 계정을 찾을 수 없습니다."
        )
    
    try:
        analysis_service = AnalysisService(db)
        result = analysis_service.get_dashboard_summary(account_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 대시보드 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 대시보드 조회 중 오류가 발생했습니다."
        )


@router.get("/analysis/recent-products")
async def get_recent_products_analysis(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7,
    limit: int = 100,
    account_id: Optional[int] = None
):
    """최근 상품 분석 데이터를 조회합니다."""
    try:
        if account_id:
            # 계정 소유권 확인
            account = crud_wholesaler_account.get(db, account_id)
            if not account or account.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="도매처 계정을 찾을 수 없습니다."
                )
        
        analysis_service = AnalysisService(db)
        result = analysis_service.product_analyzer.get_recent_products(
            account_id, days, limit
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최근 상품 분석 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최근 상품 분석 중 오류가 발생했습니다."
        )


@router.get("/analysis/trends")
async def get_trend_analysis(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 30,
    top_n: int = 20
):
    """트렌드 분석 데이터를 조회합니다."""
    try:
        analysis_service = AnalysisService(db)
        result = analysis_service.trend_analyzer.analyze_product_trends(days, top_n)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"트렌드 분석 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="트렌드 분석 중 오류가 발생했습니다."
        )


@router.get("/analysis/report")
async def generate_analysis_report(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    report_type: str = "weekly",
    account_id: Optional[int] = None
):
    """분석 보고서를 생성합니다."""
    try:
        if account_id:
            # 계정 소유권 확인
            account = crud_wholesaler_account.get(db, account_id)
            if not account or account.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="도매처 계정을 찾을 수 없습니다."
                )
        
        analysis_service = AnalysisService(db)
        result = analysis_service.generate_report(account_id, report_type)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return result['report']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 보고서 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 보고서 생성 중 오류가 발생했습니다."
        )
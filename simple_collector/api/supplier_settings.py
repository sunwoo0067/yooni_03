from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from database.connection import get_db
from database.models import Supplier
from config.settings import settings
from utils.logger import app_logger

router = APIRouter(prefix="/settings", tags=["settings"])

class SupplierSettings(BaseModel):
    """공급사 설정 모델"""
    api_config: Dict[str, Any]
    is_active: bool

class ZentradeSettings(BaseModel):
    """젠트레이드 설정"""
    api_id: str
    api_key: str
    enabled: bool

class OwnerClanSettings(BaseModel):
    """오너클랜 설정"""
    username: str
    password: str
    enabled: bool

class DomeggookSettings(BaseModel):
    """도매꾹 설정"""
    api_key: str
    enabled: bool

@router.get("/suppliers/{supplier_code}")
async def get_supplier_settings(supplier_code: str, db: Session = Depends(get_db)):
    """공급사 설정 조회"""
    supplier = db.query(Supplier).filter(Supplier.supplier_code == supplier_code).first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="공급사를 찾을 수 없습니다")
    
    # 민감한 정보는 마스킹 처리
    masked_config = {}
    if supplier.api_config:
        for key, value in supplier.api_config.items():
            if isinstance(value, str) and len(value) > 10:
                # API 키 등은 앞 4자리만 표시
                masked_config[key] = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked_config[key] = value
    
    return {
        "supplier_code": supplier.supplier_code,
        "supplier_name": supplier.supplier_name,
        "is_active": supplier.is_active,
        "api_config": masked_config,
        "has_credentials": bool(supplier.api_config)
    }

@router.put("/suppliers/zentrade")
async def update_zentrade_settings(
    settings_data: ZentradeSettings,
    db: Session = Depends(get_db)
):
    """젠트레이드 설정 업데이트"""
    supplier = db.query(Supplier).filter(Supplier.supplier_code == "zentrade").first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="젠트레이드 공급사를 찾을 수 없습니다")
    
    # API 설정 업데이트
    supplier.api_config = {
        "api_id": settings_data.api_id,
        "api_key": settings_data.api_key,
        "base_url": settings.ZENTRADE_BASE_URL
    }
    supplier.is_active = settings_data.enabled
    
    db.commit()
    app_logger.info("젠트레이드 설정 업데이트 완료")
    
    return {"message": "설정이 저장되었습니다"}

@router.put("/suppliers/ownerclan")
async def update_ownerclan_settings(
    settings_data: OwnerClanSettings,
    db: Session = Depends(get_db)
):
    """오너클랜 설정 업데이트"""
    supplier = db.query(Supplier).filter(Supplier.supplier_code == "ownerclan").first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="오너클랜 공급사를 찾을 수 없습니다")
    
    # API 설정 업데이트
    supplier.api_config = {
        "username": settings_data.username,
        "password": settings_data.password,
        "api_url": settings.OWNERCLAN_API_URL,
        "auth_url": settings.OWNERCLAN_AUTH_URL
    }
    supplier.is_active = settings_data.enabled
    
    db.commit()
    app_logger.info("오너클랜 설정 업데이트 완료")
    
    return {"message": "설정이 저장되었습니다"}

@router.put("/suppliers/domeggook")
async def update_domeggook_settings(
    settings_data: DomeggookSettings,
    db: Session = Depends(get_db)
):
    """도매꾹 설정 업데이트"""
    supplier = db.query(Supplier).filter(Supplier.supplier_code == "domeggook").first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="도매꾹 공급사를 찾을 수 없습니다")
    
    # API 설정 업데이트
    supplier.api_config = {
        "api_key": settings_data.api_key,
        "base_url": settings.DOMEGGOOK_BASE_URL
    }
    supplier.is_active = settings_data.enabled
    
    db.commit()
    app_logger.info("도매꾹 설정 업데이트 완료")
    
    return {"message": "설정이 저장되었습니다"}

@router.post("/test-connection/{supplier_code}")
async def test_supplier_connection(supplier_code: str, db: Session = Depends(get_db)):
    """공급사 API 연결 테스트"""
    supplier = db.query(Supplier).filter(Supplier.supplier_code == supplier_code).first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="공급사를 찾을 수 없습니다")
    
    if not supplier.api_config:
        raise HTTPException(status_code=400, detail="API 설정이 없습니다")
    
    try:
        # 실제 연결 테스트
        if supplier_code == "zentrade":
            from collectors.zentrade_collector_simple import ZentradeCollector
            collector = ZentradeCollector(supplier.api_config)
            collector.test_mode = False
            success = collector.authenticate()
            
        elif supplier_code == "ownerclan":
            from collectors.ownerclan_collector_simple import OwnerClanCollector
            collector = OwnerClanCollector(supplier.api_config)
            collector.test_mode = False
            success = collector.authenticate()
            
        elif supplier_code == "domeggook":
            from collectors.domeggook_collector_simple import DomeggookCollector
            collector = DomeggookCollector(supplier.api_config)
            collector.test_mode = False
            success = collector.authenticate()
            
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 공급사입니다")
        
        if success:
            return {"status": "success", "message": "연결 테스트 성공"}
        else:
            return {"status": "failed", "message": "인증 실패"}
            
    except Exception as e:
        app_logger.error(f"{supplier_code} 연결 테스트 실패: {e}")
        return {"status": "error", "message": str(e)}
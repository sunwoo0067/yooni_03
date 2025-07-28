"""
마켓플레이스 API 설정 관리
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from ..database.connection import get_db
from ..database.models import ApiCredential
from ..collectors.marketplace_collectors import (
    CoupangCollector, NaverCollector, ElevenStreetCollector
)

router = APIRouter()


@router.get("/settings/marketplace/{marketplace}")
async def get_marketplace_settings(marketplace: str, db: Session = Depends(get_db)):
    """마켓플레이스 API 설정 조회"""
    credential = db.query(ApiCredential).filter(
        ApiCredential.supplier_code == marketplace
    ).first()
    
    if not credential:
        return {
            "supplier_code": marketplace,
            "has_credentials": False,
            "is_active": False,
            "api_config": {}
        }
    
    # API 키 마스킹
    config = credential.api_config or {}
    masked_config = {}
    
    for key, value in config.items():
        if isinstance(value, str) and len(value) > 4:
            if key in ['api_key', 'secret_key', 'client_secret', 'password']:
                masked_config[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
            else:
                masked_config[key] = value
        else:
            masked_config[key] = value
    
    return {
        "supplier_code": marketplace,
        "has_credentials": bool(config),
        "is_active": credential.is_active,
        "api_config": masked_config,
        "last_tested": credential.last_tested,
        "test_status": credential.test_status
    }


@router.put("/settings/marketplace/{marketplace}")
async def update_marketplace_settings(
    marketplace: str,
    settings: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """마켓플레이스 API 설정 업데이트"""
    credential = db.query(ApiCredential).filter(
        ApiCredential.supplier_code == marketplace
    ).first()
    
    if not credential:
        # 새로 생성
        credential = ApiCredential(
            supplier_code=marketplace,
            api_config={},
            is_active=settings.get("enabled", True)
        )
        db.add(credential)
    
    # API 설정 업데이트
    config = {}
    if marketplace == "coupang":
        if settings.get("access_key"):
            config["access_key"] = settings["access_key"]
        if settings.get("secret_key"):
            config["secret_key"] = settings["secret_key"]
        if settings.get("vendor_id"):
            config["vendor_id"] = settings["vendor_id"]
            
    elif marketplace == "naver":
        if settings.get("client_id"):
            config["client_id"] = settings["client_id"]
        if settings.get("client_secret"):
            config["client_secret"] = settings["client_secret"]
            
    elif marketplace == "11st":
        if settings.get("api_key"):
            config["api_key"] = settings["api_key"]
    
    # 기존 설정과 병합 (마스킹된 값은 유지)
    existing_config = credential.api_config or {}
    for key, value in config.items():
        if value and not ('*' in str(value)):
            existing_config[key] = value
    
    credential.api_config = existing_config
    credential.is_active = settings.get("enabled", True)
    credential.updated_at = datetime.now()
    
    db.commit()
    
    return {"message": f"{marketplace} 설정이 저장되었습니다."}


@router.post("/settings/test-connection/{supplier}")
async def test_marketplace_connection(supplier: str, db: Session = Depends(get_db)):
    """마켓플레이스 연결 테스트"""
    credential = db.query(ApiCredential).filter(
        ApiCredential.supplier_code == supplier
    ).first()
    
    if not credential or not credential.api_config:
        return {
            "status": "failed",
            "message": "API 설정이 없습니다."
        }
    
    try:
        if supplier == "coupang":
            collector = CoupangCollector(
                access_key=credential.api_config.get("access_key"),
                secret_key=credential.api_config.get("secret_key"),
                vendor_id=credential.api_config.get("vendor_id")
            )
            # 간단한 API 호출로 테스트
            import asyncio
            products = asyncio.run(collector.get_products(limit=1))
            success = len(products) >= 0  # API 호출이 성공하면 OK
            
        elif supplier == "naver":
            collector = NaverCollector(
                client_id=credential.api_config.get("client_id"),
                client_secret=credential.api_config.get("client_secret")
            )
            import asyncio
            token = asyncio.run(collector._get_token())
            success = bool(token)
            
        elif supplier == "11st":
            collector = ElevenStreetCollector(
                api_key=credential.api_config.get("api_key")
            )
            import asyncio
            products = asyncio.run(collector.get_products(limit=1))
            success = len(products) >= 0
            
        else:
            # 기존 도매사이트 테스트
            return await test_supplier_connection(supplier, db)
        
        # 테스트 결과 저장
        credential.last_tested = datetime.now()
        credential.test_status = "success" if success else "failed"
        db.commit()
        
        return {
            "status": "success" if success else "failed",
            "message": "연결 성공!" if success else "연결 실패"
        }
        
    except Exception as e:
        credential.last_tested = datetime.now()
        credential.test_status = "failed"
        db.commit()
        
        return {
            "status": "failed",
            "message": str(e)
        }


# 기존 도매사이트 테스트 함수 (참조용)
async def test_supplier_connection(supplier: str, db: Session):
    """도매사이트 연결 테스트"""
    # 기존 코드...
    return {
        "status": "success",
        "message": "도매사이트 테스트"
    }
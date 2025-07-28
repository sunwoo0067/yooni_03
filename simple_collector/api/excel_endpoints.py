from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import os
import shutil
from pathlib import Path
import pandas as pd

from config.settings import settings
from database.connection import get_db
from database.models import Product, ExcelUpload
from processors.excel_processor import ExcelProcessor
from utils.logger import app_logger

router = APIRouter(prefix="/excel", tags=["Excel"])

# 업로드 디렉토리 설정
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload/{supplier}")
async def upload_excel(
    supplier: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """엑셀 파일 업로드 및 처리"""
    
    # 파일 확장자 확인
    allowed_extensions = ['.xlsx', '.xls', '.csv']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용: {', '.join(allowed_extensions)}"
        )
    
    # 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_filename = f"{supplier}_{timestamp}_{file.filename}"
    save_path = UPLOAD_DIR / save_filename
    
    try:
        # 파일 저장
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        app_logger.info(f"엑셀 파일 저장 완료: {save_path}")
        
        # 백그라운드에서 처리
        def process_file():
            processor = ExcelProcessor(str(UPLOAD_DIR))
            result = processor.process_excel_file(
                file_path=str(save_path),
                supplier=supplier,
                file_name=file.filename
            )
            app_logger.info(f"엑셀 처리 결과: {result}")
            
        background_tasks.add_task(process_file)
        
        return {
            "message": "파일 업로드가 완료되었습니다. 백그라운드에서 처리 중입니다.",
            "filename": file.filename,
            "supplier": supplier,
            "saved_as": save_filename,
            "check_status": f"/excel/uploads?supplier={supplier}"
        }
        
    except Exception as e:
        # 파일 저장 실패 시 삭제
        if save_path.exists():
            save_path.unlink()
            
        app_logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@router.get("/uploads")
async def get_excel_uploads(
    supplier: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """엑셀 업로드 이력 조회"""
    query = db.query(ExcelUpload).order_by(ExcelUpload.upload_time.desc())
    
    if supplier:
        query = query.filter(ExcelUpload.supplier == supplier)
        
    uploads = query.limit(limit).all()
    
    return [
        {
            "id": upload.id,
            "supplier": upload.supplier,
            "filename": upload.filename,
            "total_rows": upload.total_rows,
            "processed_rows": upload.processed_rows,
            "error_rows": upload.error_rows,
            "status": upload.status,
            "upload_time": upload.upload_time.isoformat() if upload.upload_time else None,
            "process_time": upload.process_time.isoformat() if upload.process_time else None
        }
        for upload in uploads
    ]

@router.get("/template/{supplier}")
async def download_template(supplier: str):
    """공급사별 엑셀 템플릿 다운로드"""
    
    try:
        # 템플릿 생성
        processor = ExcelProcessor()
        df = processor.get_template(supplier)
        
        # 임시 파일로 저장
        temp_file = UPLOAD_DIR / f"template_{supplier}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(temp_file, index=False)
        
        # 파일 응답
        return FileResponse(
            path=str(temp_file),
            filename=f"{supplier}_upload_template.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        app_logger.error(f"템플릿 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"템플릿 생성 실패: {str(e)}")

@router.post("/process-sample")
async def process_sample_excel(background_tasks: BackgroundTasks):
    """샘플 엑셀 파일 처리 테스트"""
    
    # 샘플 데이터 생성
    sample_data = {
        'zentrade': pd.DataFrame([
            {
                '상품코드': 'ZT_SAMPLE_001',
                '상품명': '젠트레이드 샘플 상품 1',
                '가격': 15000,
                '공급가': 10000,
                '카테고리': '의류/여성의류',
                '브랜드': '샘플브랜드',
                '모델명': 'MODEL-001',
                '설명': '샘플 상품 설명입니다',
                '재고': 100,
                '배송비': 3000,
                '반품비': 3000
            },
            {
                '상품코드': 'ZT_SAMPLE_002',
                '상품명': '젠트레이드 샘플 상품 2',
                '가격': 25000,
                '공급가': 18000,
                '카테고리': '잡화/가방',
                '브랜드': '샘플브랜드',
                '모델명': 'MODEL-002',
                '설명': '두 번째 샘플 상품입니다',
                '재고': 50,
                '배송비': 3000,
                '반품비': 3000
            }
        ]),
        'ownerclan': pd.DataFrame([
            {
                '상품코드': 'OC_SAMPLE_001',
                '상품명': '오너클랜 샘플 상품',
                '가격': 30000,
                '공급가': 22000,
                '카테고리': '패션잡화',
                '브랜드명': '오너샘플',
                '재고수량': 200,
                '상품상태': 'active',
                '옵션': '[{"name":"색상","values":["블랙","화이트"]}]',
                '설명': '오너클랜 샘플 상품입니다'
            }
        ]),
        'domeggook': pd.DataFrame([
            {
                '상품코드': 'DG_SAMPLE_001',
                '상품명': '도매꾹 샘플 상품',
                '공급가': 8000,
                '소비자가': 15000,
                '카테고리코드': '01_01_00_00_00',
                '카테고리': '여성의류',
                '벤더코드': 'V001',
                '최소주문수량': 5,
                '재고': 300,
                '설명': '도매꾹 샘플 상품입니다'
            }
        ])
    }
    
    results = {}
    
    for supplier, df in sample_data.items():
        # 임시 파일 생성
        temp_file = UPLOAD_DIR / f"sample_{supplier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(temp_file, index=False)
        
        # 처리
        def process_supplier_file(sup=supplier, file_path=str(temp_file)):
            processor = ExcelProcessor(str(UPLOAD_DIR))
            result = processor.process_excel_file(
                file_path=file_path,
                supplier=sup,
                file_name=f"sample_{sup}.xlsx"
            )
            app_logger.info(f"샘플 {sup} 처리 결과: {result}")
            
            # 처리 후 임시 파일 삭제
            try:
                Path(file_path).unlink()
            except:
                pass
                
        background_tasks.add_task(process_supplier_file)
        
    return {
        "message": "샘플 엑셀 파일 처리가 시작되었습니다",
        "suppliers": list(sample_data.keys()),
        "check_uploads": "/excel/uploads",
        "check_products": "/products"
    }

@router.get("/stats")
async def get_excel_stats(db: Session = Depends(get_db)):
    """엑셀 업로드 통계"""
    
    # 전체 통계
    total_uploads = db.query(ExcelUpload).count()
    completed_uploads = db.query(ExcelUpload).filter(ExcelUpload.status == 'completed').count()
    failed_uploads = db.query(ExcelUpload).filter(ExcelUpload.status == 'failed').count()
    
    # 공급사별 통계
    supplier_stats = []
    for supplier in ['zentrade', 'ownerclan', 'domeggook']:
        uploads = db.query(ExcelUpload).filter(ExcelUpload.supplier == supplier)
        stats = {
            'supplier': supplier,
            'total_uploads': uploads.count(),
            'total_rows': sum(u.total_rows or 0 for u in uploads),
            'processed_rows': sum(u.processed_rows or 0 for u in uploads),
            'error_rows': sum(u.error_rows or 0 for u in uploads)
        }
        supplier_stats.append(stats)
    
    return {
        'total_uploads': total_uploads,
        'completed_uploads': completed_uploads,
        'failed_uploads': failed_uploads,
        'processing_uploads': total_uploads - completed_uploads - failed_uploads,
        'supplier_stats': supplier_stats
    }
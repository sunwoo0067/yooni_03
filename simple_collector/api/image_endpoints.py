"""
이미지 처리 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
import json

from database.connection import get_db
from database.models_v2 import WholesaleProduct, MarketplaceProduct
from services.image.image_processor import ImageProcessor
from services.image.image_hosting import ImageHostingService
from utils.logger import app_logger

router = APIRouter(prefix="/images", tags=["images"])


class ImageProcessRequest(BaseModel):
    """이미지 처리 요청"""
    product_code: str
    image_urls: List[str]
    marketplace: str = 'coupang'
    add_watermark: bool = False
    resize_only: bool = False


class ImageBatchRequest(BaseModel):
    """배치 이미지 처리 요청"""
    products: List[Dict[str, any]]
    marketplace: str = 'coupang'
    add_watermark: bool = False


@router.post("/process/{product_code}")
async def process_product_images(
    product_code: str,
    background_tasks: BackgroundTasks,
    request: ImageProcessRequest,
    db: Session = Depends(get_db)
):
    """상품 이미지 처리"""
    try:
        # 상품 확인
        product = db.query(WholesaleProduct).filter(
            WholesaleProduct.product_code == product_code
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        
        # 백그라운드 작업 추가
        background_tasks.add_task(
            process_images_task,
            product_code=product_code,
            image_urls=request.image_urls,
            marketplace=request.marketplace,
            add_watermark=request.add_watermark,
            db=db
        )
        
        return {
            "status": "processing",
            "message": "이미지 처리가 시작되었습니다",
            "product_code": product_code,
            "image_count": len(request.image_urls)
        }
        
    except Exception as e:
        app_logger.error(f"이미지 처리 요청 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_images_task(
    product_code: str,
    image_urls: List[str],
    marketplace: str,
    add_watermark: bool,
    db: Session
):
    """백그라운드 이미지 처리 작업"""
    try:
        # 이미지 프로세서 초기화
        processor = ImageProcessor()
        hosting_service = ImageHostingService(db)
        
        # 이미지 처리
        processed_paths = await processor.process_product_images(
            product_code=product_code,
            image_urls=image_urls,
            marketplace=marketplace,
            add_watermark=add_watermark
        )
        
        # 호스팅
        hosted_urls = hosting_service.host_product_images(
            product_code=product_code,
            marketplace=marketplace,
            image_paths=processed_paths
        )
        
        # 상품 이미지 URL 업데이트
        product = db.query(WholesaleProduct).filter(
            WholesaleProduct.product_code == product_code
        ).first()
        
        if product and hosted_urls.get('main'):
            # 기존 이미지 URL 업데이트
            all_images = hosted_urls.get('main', []) + hosted_urls.get('detail', [])
            product.images = all_images
            db.commit()
        
        app_logger.info(f"이미지 처리 완료: {product_code}")
        
    except Exception as e:
        app_logger.error(f"이미지 처리 작업 오류: {e}")


@router.post("/batch-process")
async def batch_process_images(
    background_tasks: BackgroundTasks,
    request: ImageBatchRequest,
    db: Session = Depends(get_db)
):
    """여러 상품 이미지 일괄 처리"""
    try:
        processed_count = 0
        
        for product_data in request.products:
            product_code = product_data.get('product_code')
            image_urls = product_data.get('image_urls', [])
            
            if product_code and image_urls:
                background_tasks.add_task(
                    process_images_task,
                    product_code=product_code,
                    image_urls=image_urls,
                    marketplace=request.marketplace,
                    add_watermark=request.add_watermark,
                    db=db
                )
                processed_count += 1
        
        return {
            "status": "processing",
            "message": f"{processed_count}개 상품의 이미지 처리가 시작되었습니다",
            "total_products": processed_count
        }
        
    except Exception as e:
        app_logger.error(f"배치 이미지 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_image(
    product_code: str = Form(...),
    marketplace: str = Form('coupang'),
    image_type: str = Form('main'),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """이미지 직접 업로드"""
    try:
        # 파일 저장
        file_path = f"static/images/upload/{product_code}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 호스팅
        hosting_service = ImageHostingService(db)
        hosted_url = hosting_service.host_image(
            product_code=product_code,
            marketplace=marketplace,
            local_path=file_path,
            image_type=image_type
        )
        
        if not hosted_url:
            raise HTTPException(status_code=500, detail="이미지 호스팅 실패")
        
        return {
            "status": "success",
            "hosted_url": hosted_url,
            "product_code": product_code,
            "image_type": image_type
        }
        
    except Exception as e:
        app_logger.error(f"이미지 업로드 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hosted/{product_code}")
async def get_hosted_images(
    product_code: str,
    marketplace: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """호스팅된 이미지 조회"""
    try:
        hosting_service = ImageHostingService(db)
        images = hosting_service.get_hosted_images(
            product_code=product_code,
            marketplace=marketplace
        )
        
        return {
            "status": "success",
            "product_code": product_code,
            "images": images
        }
        
    except Exception as e:
        app_logger.error(f"이미지 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/stats")
async def get_storage_stats(db: Session = Depends(get_db)):
    """스토리지 사용 현황"""
    try:
        hosting_service = ImageHostingService(db)
        stats = hosting_service.get_storage_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        app_logger.error(f"스토리지 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_images(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """오래된 이미지 정리"""
    try:
        processor = ImageProcessor()
        hosting_service = ImageHostingService(db)
        
        # 프로세서 정리
        processor.cleanup_old_images(days)
        
        # 호스팅 서비스 정리
        hosting_service.cleanup_unused_images(days)
        
        return {
            "status": "success",
            "message": f"{days}일 이상 된 이미지가 정리되었습니다"
        }
        
    except Exception as e:
        app_logger.error(f"이미지 정리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-wholesale-images")
async def process_wholesale_images(
    background_tasks: BackgroundTasks,
    supplier: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """도매 상품 이미지 일괄 처리"""
    try:
        query = db.query(WholesaleProduct).filter(
            WholesaleProduct.is_active == True
        )
        
        if supplier:
            query = query.filter(WholesaleProduct.supplier == supplier)
        
        # 이미지가 있는 상품만
        products = query.filter(
            WholesaleProduct.images != None
        ).limit(limit).all()
        
        processed_count = 0
        
        for product in products:
            if product.images:
                background_tasks.add_task(
                    process_images_task,
                    product_code=product.product_code,
                    image_urls=product.images,
                    marketplace='coupang',  # 기본값
                    add_watermark=False,
                    db=db
                )
                processed_count += 1
        
        return {
            "status": "processing",
            "message": f"{processed_count}개 도매 상품의 이미지 처리가 시작되었습니다",
            "supplier": supplier,
            "total_products": processed_count
        }
        
    except Exception as e:
        app_logger.error(f"도매 이미지 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
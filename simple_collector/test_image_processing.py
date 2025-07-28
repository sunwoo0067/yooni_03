"""
이미지 처리 시스템 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import requests

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from database.connection import SessionLocal
from database.models_v2 import WholesaleProduct
from services.image.image_processor import ImageProcessor
from services.image.image_hosting import ImageHostingService
from utils.logger import app_logger


async def test_image_processor():
    """이미지 프로세서 테스트"""
    app_logger.info("=== 이미지 프로세서 테스트 시작 ===")
    
    processor = ImageProcessor()
    
    # 테스트 이미지 URL (예시)
    test_images = [
        "https://via.placeholder.com/500x500/FF0000/FFFFFF?text=Test+Image+1",
        "https://via.placeholder.com/600x400/00FF00/FFFFFF?text=Test+Image+2",
        "https://via.placeholder.com/400x600/0000FF/FFFFFF?text=Test+Image+3"
    ]
    
    # 이미지 처리
    result = await processor.process_product_images(
        product_code="TEST001",
        image_urls=test_images,
        marketplace='coupang',
        add_watermark=True
    )
    
    app_logger.info(f"처리 결과:")
    app_logger.info(f"  원본: {len(result['original'])}개")
    app_logger.info(f"  처리됨: {len(result['processed'])}개")
    app_logger.info(f"  썸네일: {len(result['thumbnail'])}개")
    
    return result


def test_image_hosting(processed_paths: dict):
    """이미지 호스팅 테스트"""
    app_logger.info("\n=== 이미지 호스팅 테스트 시작 ===")
    
    db = SessionLocal()
    try:
        hosting_service = ImageHostingService(db)
        
        # 이미지 호스팅
        hosted_urls = hosting_service.host_product_images(
            product_code="TEST001",
            marketplace='coupang',
            image_paths=processed_paths
        )
        
        app_logger.info(f"호스팅 결과:")
        for image_type, urls in hosted_urls.items():
            app_logger.info(f"  {image_type}: {len(urls)}개")
            for url in urls:
                app_logger.info(f"    - {url}")
        
        # 호스팅된 이미지 조회
        retrieved = hosting_service.get_hosted_images("TEST001", 'coupang')
        app_logger.info(f"\n조회된 이미지:")
        for image_type, urls in retrieved.items():
            app_logger.info(f"  {image_type}: {len(urls)}개")
        
        # 스토리지 통계
        stats = hosting_service.get_storage_stats()
        app_logger.info(f"\n스토리지 통계:")
        app_logger.info(f"  총 크기: {stats['total_size_mb']} MB")
        app_logger.info(f"  파일 수: {stats['file_count']}")
        app_logger.info(f"  활성 이미지: {stats['active_images']}")
        
    finally:
        db.close()


async def test_api_endpoint():
    """API 엔드포인트 테스트"""
    app_logger.info("\n=== API 엔드포인트 테스트 시작 ===")
    
    # API 서버 확인
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            app_logger.error("API 서버가 실행되지 않았습니다.")
            return
    except:
        app_logger.error("API 서버에 연결할 수 없습니다.")
        return
    
    # 이미지 처리 요청
    request_data = {
        "product_code": "TEST002",
        "image_urls": [
            "https://via.placeholder.com/800x800/FF00FF/FFFFFF?text=API+Test+1",
            "https://via.placeholder.com/700x700/FFFF00/000000?text=API+Test+2"
        ],
        "marketplace": "naver",
        "add_watermark": True
    }
    
    response = requests.post(
        "http://localhost:8000/images/process/TEST002",
        json=request_data
    )
    
    if response.status_code == 200:
        app_logger.info(f"API 요청 성공: {response.json()}")
        
        # 잠시 대기 후 결과 확인
        await asyncio.sleep(3)
        
        # 호스팅된 이미지 조회
        response = requests.get("http://localhost:8000/images/hosted/TEST002")
        if response.status_code == 200:
            result = response.json()
            app_logger.info(f"호스팅된 이미지: {result['images']}")
    else:
        app_logger.error(f"API 요청 실패: {response.status_code}")


async def test_wholesale_images():
    """실제 도매 상품 이미지 처리 테스트"""
    app_logger.info("\n=== 도매 상품 이미지 처리 테스트 ===")
    
    db = SessionLocal()
    try:
        # 이미지가 있는 상품 찾기
        products = db.query(WholesaleProduct).filter(
            WholesaleProduct.images != None,
            WholesaleProduct.is_active == True
        ).limit(3).all()
        
        if not products:
            app_logger.warning("이미지가 있는 상품이 없습니다.")
            return
        
        processor = ImageProcessor()
        hosting_service = ImageHostingService(db)
        
        for product in products:
            app_logger.info(f"\n상품: {product.product_name}")
            app_logger.info(f"코드: {product.product_code}")
            app_logger.info(f"이미지 수: {len(product.images)}")
            
            # 이미지 처리
            result = await processor.process_product_images(
                product_code=product.product_code,
                image_urls=product.images[:3],  # 최대 3개만
                marketplace='coupang',
                add_watermark=False
            )
            
            # 호스팅
            hosted_urls = hosting_service.host_product_images(
                product_code=product.product_code,
                marketplace='coupang',
                image_paths=result
            )
            
            app_logger.info(f"처리 완료:")
            for image_type, urls in hosted_urls.items():
                if urls:
                    app_logger.info(f"  {image_type}: {urls[0]}")
        
    except Exception as e:
        app_logger.error(f"도매 상품 이미지 처리 오류: {e}")
    finally:
        db.close()


async def main():
    """메인 테스트 함수"""
    app_logger.info(f"이미지 처리 테스트 시작: {datetime.now()}")
    
    # 1. 이미지 프로세서 테스트
    processed_paths = await test_image_processor()
    
    # 2. 이미지 호스팅 테스트
    test_image_hosting(processed_paths)
    
    # 3. API 엔드포인트 테스트
    await test_api_endpoint()
    
    # 4. 실제 도매 상품 이미지 테스트
    await test_wholesale_images()
    
    app_logger.info("\n=== 테스트 완료 ===")
    app_logger.info("처리된 이미지는 static/images 디렉토리에서 확인할 수 있습니다.")


if __name__ == "__main__":
    asyncio.run(main())
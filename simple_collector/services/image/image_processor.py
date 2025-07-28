"""
이미지 가공 처리 서비스
- 이미지 다운로드
- 크기 조정
- 워터마크 추가
- 최적화
"""

import os
import hashlib
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import io
from datetime import datetime
import numpy as np

from utils.logger import app_logger


class ImageProcessor:
    """이미지 처리 클래스"""
    
    def __init__(self, base_path: str = "static/images"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 마켓플레이스별 이미지 요구사항
        self.marketplace_specs = {
            'coupang': {
                'main_size': (500, 500),
                'max_size': (1000, 1000),
                'format': 'JPEG',
                'quality': 85
            },
            'naver': {
                'main_size': (500, 500),
                'max_size': (1300, 1300),
                'format': 'JPEG',
                'quality': 90
            },
            '11st': {
                'main_size': (400, 400),
                'max_size': (800, 800),
                'format': 'JPEG',
                'quality': 85
            }
        }
        
        # 워터마크 설정
        self.watermark_text = "Simple Collector"
        self.watermark_opacity = 0.3
    
    async def process_product_images(self, 
                                   product_code: str,
                                   image_urls: List[str],
                                   marketplace: str = 'coupang',
                                   add_watermark: bool = False) -> Dict[str, List[str]]:
        """상품 이미지 일괄 처리
        
        Returns:
            {
                'original': ['path1', 'path2', ...],
                'processed': ['path1', 'path2', ...],
                'thumbnail': ['path1', 'path2', ...]
            }
        """
        result = {
            'original': [],
            'processed': [],
            'thumbnail': []
        }
        
        # 상품별 디렉토리 생성
        product_dir = self.base_path / marketplace / product_code
        product_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, url in enumerate(image_urls):
            try:
                # 이미지 다운로드
                image_data = await self.download_image(url)
                if not image_data:
                    continue
                
                # 파일명 생성 (URL 해시)
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                base_filename = f"{product_code}_{idx}_{url_hash}"
                
                # 원본 저장
                original_path = product_dir / f"{base_filename}_original.jpg"
                with open(original_path, 'wb') as f:
                    f.write(image_data)
                result['original'].append(str(original_path))
                
                # PIL 이미지로 변환
                image = Image.open(io.BytesIO(image_data))
                
                # RGBA를 RGB로 변환
                if image.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = rgb_image
                
                # 메인 이미지 처리
                processed_image = self.resize_image(
                    image,
                    self.marketplace_specs[marketplace]['main_size']
                )
                
                # 워터마크 추가
                if add_watermark:
                    processed_image = self.add_watermark(processed_image)
                
                # 최적화 및 저장
                processed_path = product_dir / f"{base_filename}_processed.jpg"
                self.save_optimized_image(
                    processed_image,
                    processed_path,
                    self.marketplace_specs[marketplace]['quality']
                )
                result['processed'].append(str(processed_path))
                
                # 썸네일 생성
                thumbnail = self.create_thumbnail(image, (150, 150))
                thumbnail_path = product_dir / f"{base_filename}_thumb.jpg"
                thumbnail.save(thumbnail_path, 'JPEG', quality=85)
                result['thumbnail'].append(str(thumbnail_path))
                
                app_logger.info(f"이미지 처리 완료: {base_filename}")
                
            except Exception as e:
                app_logger.error(f"이미지 처리 오류 ({url}): {e}")
                continue
        
        return result
    
    async def download_image(self, url: str, timeout: int = 10) -> Optional[bytes]:
        """이미지 다운로드"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # 이미지 유효성 검사
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                app_logger.warning(f"이미지가 아닌 컨텐츠: {url}")
                return None
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            app_logger.error(f"이미지 다운로드 실패 ({url}): {e}")
            return None
    
    def resize_image(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """이미지 크기 조정 (비율 유지)"""
        # 원본 비율 유지하면서 리사이즈
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # 정사각형 캔버스에 중앙 정렬
        if size[0] == size[1]:  # 정사각형인 경우
            new_image = Image.new('RGB', size, (255, 255, 255))
            paste_x = (size[0] - image.size[0]) // 2
            paste_y = (size[1] - image.size[1]) // 2
            new_image.paste(image, (paste_x, paste_y))
            return new_image
        
        return image
    
    def add_watermark(self, image: Image.Image, 
                     position: str = 'bottom-right') -> Image.Image:
        """워터마크 추가"""
        # 이미지 복사
        watermarked = image.copy()
        
        # 워터마크 레이어 생성
        watermark_layer = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark_layer)
        
        # 폰트 크기 계산 (이미지 크기의 5%)
        font_size = max(12, min(watermarked.size) // 20)
        
        try:
            # 시스템 폰트 사용 시도
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # 기본 폰트 사용
            font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), self.watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 위치 계산
        margin = 10
        if position == 'bottom-right':
            x = watermarked.size[0] - text_width - margin
            y = watermarked.size[1] - text_height - margin
        elif position == 'bottom-left':
            x = margin
            y = watermarked.size[1] - text_height - margin
        elif position == 'top-right':
            x = watermarked.size[0] - text_width - margin
            y = margin
        else:  # top-left
            x = margin
            y = margin
        
        # 워터마크 그리기
        draw.text((x, y), self.watermark_text, 
                 fill=(255, 255, 255, int(255 * self.watermark_opacity)), 
                 font=font)
        
        # 원본 이미지와 합성
        watermarked = Image.alpha_composite(watermarked.convert('RGBA'), watermark_layer)
        
        return watermarked.convert('RGB')
    
    def create_thumbnail(self, image: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """썸네일 생성"""
        thumbnail = image.copy()
        thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
        return thumbnail
    
    def save_optimized_image(self, image: Image.Image, path: Path, quality: int = 85):
        """이미지 최적화 및 저장"""
        # EXIF 데이터 제거 (개인정보 보호)
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        
        # 최적화 저장
        image_without_exif.save(
            path,
            'JPEG',
            quality=quality,
            optimize=True,
            progressive=True
        )
    
    def enhance_image(self, image: Image.Image) -> Image.Image:
        """이미지 품질 향상"""
        # 밝기 조정
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        # 대비 조정
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        # 선명도 조정
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image
    
    def remove_background(self, image: Image.Image, 
                         threshold: int = 240) -> Image.Image:
        """간단한 흰색 배경 제거"""
        # RGBA로 변환
        image = image.convert("RGBA")
        data = np.array(image)
        
        # 흰색 픽셀을 투명하게
        white_pixels = (data[:, :, 0] > threshold) & \
                      (data[:, :, 1] > threshold) & \
                      (data[:, :, 2] > threshold)
        data[white_pixels] = [255, 255, 255, 0]
        
        return Image.fromarray(data, mode='RGBA')
    
    def create_composite_image(self, images: List[Image.Image], 
                             layout: str = 'grid') -> Image.Image:
        """여러 이미지를 하나로 합성"""
        if not images:
            return None
        
        if layout == 'grid':
            # 2x2 그리드 레이아웃
            grid_size = 2
            cell_size = 250
            
            composite = Image.new('RGB', 
                                (cell_size * grid_size, cell_size * grid_size), 
                                (255, 255, 255))
            
            for idx, img in enumerate(images[:4]):
                # 리사이즈
                img_resized = self.resize_image(img, (cell_size, cell_size))
                
                # 위치 계산
                row = idx // grid_size
                col = idx % grid_size
                x = col * cell_size
                y = row * cell_size
                
                composite.paste(img_resized, (x, y))
            
            return composite
        
        elif layout == 'horizontal':
            # 가로 나열
            width = sum(img.size[0] for img in images)
            height = max(img.size[1] for img in images)
            
            composite = Image.new('RGB', (width, height), (255, 255, 255))
            
            x_offset = 0
            for img in images:
                composite.paste(img, (x_offset, 0))
                x_offset += img.size[0]
            
            return composite
        
        return images[0]
    
    def generate_image_hash(self, image_path: str) -> str:
        """이미지 파일의 해시 생성 (중복 검사용)"""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def cleanup_old_images(self, days: int = 30):
        """오래된 이미지 정리"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for marketplace_dir in self.base_path.iterdir():
            if not marketplace_dir.is_dir():
                continue
            
            for product_dir in marketplace_dir.iterdir():
                if not product_dir.is_dir():
                    continue
                
                # 디렉토리 수정 시간 확인
                mtime = datetime.fromtimestamp(product_dir.stat().st_mtime)
                if mtime < cutoff_time:
                    # 오래된 디렉토리 삭제
                    import shutil
                    shutil.rmtree(product_dir)
                    app_logger.info(f"오래된 이미지 삭제: {product_dir}")
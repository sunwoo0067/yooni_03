"""
이미지 가공 엔진

목표: 상세페이지에서 최적 대표이미지 자동 생성
방법: AI 기반 최적 영역 탐지 + 마켓별 규격 적용
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal
from io import BytesIO
import base64

import aiohttp
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from sqlalchemy.orm import Session

from app.models.product_processing import (
    ImageProcessingHistory,
    MarketGuideline,
    ProcessingCostTracking
)
from app.models.product import Product
from app.services.ai.ai_manager import AIManager
from app.services.ai.ollama_service import OllamaService
from app.core.config import settings


class ImageProcessingEngine:
    """AI 기반 이미지 가공 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_manager = AIManager()
        self.ollama_service = OllamaService()
        
        # 시간대별 AI 모델 선택
        self.current_hour = datetime.now().hour
        self.is_night_time = 22 <= self.current_hour or self.current_hour <= 6
        
        # Supabase 설정 (실제 환경에서는 환경변수에서 가져옴)
        self.supabase_url = getattr(settings, 'SUPABASE_URL', '')
        self.supabase_key = getattr(settings, 'SUPABASE_ANON_KEY', '')
    
    async def scrape_product_details(self, product_url: str) -> Dict:
        """상세페이지 스크래핑"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(product_url, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"HTTP {response.status}"}
                    
                    html_content = await response.text()
                    
                    # AI를 사용한 이미지 URL 추출
                    extraction_prompt = f"""
                    다음 HTML 콘텐츠에서 상품 이미지 URL들을 추출해주세요.
                    
                    우선순위:
                    1. 메인 상품 이미지
                    2. 상세 설명 이미지
                    3. 썸네일 이미지
                    
                    결과를 JSON 형태로 반환:
                    {{
                        "main_images": ["url1", "url2"],
                        "detail_images": ["url3", "url4"],
                        "thumbnail_images": ["url5", "url6"]
                    }}
                    
                    HTML 내용 (처음 2000자):
                    {html_content[:2000]}
                    """
                    
                    if self.is_night_time:
                        result = await self.ollama_service.generate_text(
                            extraction_prompt, model="llama3.1:8b"
                        )
                        ai_model_used = "ollama_llama3.1_8b"
                        cost = 0.0
                    else:
                        result = await self.ai_manager.generate_text(
                            extraction_prompt, model="gpt-4o-mini"
                        )
                        ai_model_used = "gpt-4o-mini"
                        cost = 0.002
                    
                    try:
                        image_data = json.loads(result)
                    except json.JSONDecodeError:
                        # JSON 파싱 실패 시 정규식으로 추출
                        image_data = self._extract_images_with_regex(html_content)
                    
                    # 비용 추적
                    await self._track_processing_cost(
                        "image_extraction", ai_model_used, 1, cost
                    )
                    
                    return image_data
                    
        except Exception as e:
            print(f"스크래핑 오류: {e}")
            return {"error": str(e)}
    
    async def detect_optimal_regions(
        self, 
        image_urls: List[str], 
        marketplace: str
    ) -> List[Dict]:
        """AI 기반 최적 영역 탐지"""
        
        optimal_regions = []
        
        for image_url in image_urls:
            try:
                # 이미지 다운로드
                image_data = await self._download_image(image_url)
                if not image_data:
                    continue
                
                # 이미지 분석
                analysis_result = await self._analyze_image_composition(
                    image_data, marketplace
                )
                
                optimal_regions.append({
                    "original_url": image_url,
                    "analysis": analysis_result,
                    "optimal_crops": analysis_result.get("optimal_crops", []),
                    "quality_score": analysis_result.get("quality_score", 0)
                })
                
            except Exception as e:
                print(f"이미지 분석 오류 {image_url}: {e}")
                continue
        
        return optimal_regions
    
    async def apply_market_specifications(
        self, 
        image_data: bytes, 
        marketplace: str,
        crop_region: Optional[Dict] = None
    ) -> bytes:
        """마켓별 이미지 규격 적용"""
        
        # 마켓 가이드라인 조회
        guidelines = await self._get_market_guidelines(marketplace)
        image_specs = guidelines.get("image_specs", {})
        
        # PIL 이미지로 변환
        image = Image.open(BytesIO(image_data))
        
        # 크롭 적용 (지정된 경우)
        if crop_region:
            x1, y1, x2, y2 = (
                crop_region.get("x1", 0),
                crop_region.get("y1", 0),
                crop_region.get("x2", image.width),
                crop_region.get("y2", image.height)
            )
            image = image.crop((x1, y1, x2, y2))
        
        # 마켓별 규격 적용
        target_width = image_specs.get("width", 800)
        target_height = image_specs.get("height", 800)
        max_size_mb = image_specs.get("max_size_mb", 10)
        
        # 비율 유지 리사이징 (왜곡 방지)
        processed_image = await self._resize_maintain_ratio(
            image, target_width, target_height
        )
        
        # 마켓별 최적화 적용
        if marketplace == "coupang":
            processed_image = await self._apply_coupang_optimization(processed_image)
        elif marketplace == "naver":
            processed_image = await self._apply_naver_optimization(processed_image)
        elif marketplace == "11st":
            processed_image = await self._apply_11st_optimization(processed_image)
        
        # 용량 최적화
        processed_image = await self._optimize_file_size(
            processed_image, max_size_mb
        )
        
        # 바이트로 변환
        output_buffer = BytesIO()
        format_type = image_specs.get("format", ["jpg"])[0].upper()
        if format_type == "JPG":
            format_type = "JPEG"
        
        processed_image.save(
            output_buffer, 
            format=format_type, 
            quality=90,
            optimize=True
        )
        
        return output_buffer.getvalue()
    
    async def upload_to_supabase(self, image_data: bytes, filename: str) -> str:
        """수파베이스 이미지 호스팅"""
        
        if not self.supabase_url or not self.supabase_key:
            # Supabase 설정이 없으면 로컬 저장
            return await self._save_locally(image_data, filename)
        
        try:
            upload_url = f"{self.supabase_url}/storage/v1/object/product-images/{filename}"
            
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "image/jpeg"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    upload_url, 
                    data=image_data, 
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return f"{self.supabase_url}/storage/v1/object/public/product-images/{filename}"
                    else:
                        print(f"Supabase 업로드 실패: {response.status}")
                        return await self._save_locally(image_data, filename)
                        
        except Exception as e:
            print(f"Supabase 업로드 오류: {e}")
            return await self._save_locally(image_data, filename)
    
    async def process_product_images(
        self, 
        product: Product, 
        marketplace: str,
        source_urls: Optional[List[str]] = None
    ) -> Dict:
        """상품 이미지 전체 가공 프로세스"""
        
        start_time = datetime.now()
        
        try:
            # 1. 소스 이미지 수집
            if source_urls:
                image_urls = source_urls
            else:
                # 상품에서 이미지 URL 추출
                image_urls = []
                if product.main_image_url:
                    image_urls.append(product.main_image_url)
                if product.image_urls:
                    if isinstance(product.image_urls, list):
                        image_urls.extend(product.image_urls)
                    elif isinstance(product.image_urls, dict):
                        image_urls.extend(product.image_urls.get("urls", []))
            
            if not image_urls:
                return {"error": "처리할 이미지가 없습니다"}
            
            # 2. 최적 영역 탐지
            optimal_regions = await self.detect_optimal_regions(
                image_urls, marketplace
            )
            
            if not optimal_regions:
                return {"error": "최적 영역을 찾을 수 없습니다"}
            
            # 3. 가장 좋은 이미지 선택
            best_image = max(
                optimal_regions, 
                key=lambda x: x.get("quality_score", 0)
            )
            
            # 4. 이미지 다운로드 및 가공
            original_image_data = await self._download_image(
                best_image["original_url"]
            )
            
            if not original_image_data:
                return {"error": "이미지 다운로드 실패"}
            
            # 5. 마켓별 규격 적용
            processed_images = []
            
            # 메인 이미지 (최적 크롭 영역)
            best_crop = None
            if best_image["optimal_crops"]:
                best_crop = max(
                    best_image["optimal_crops"],
                    key=lambda x: x.get("score", 0)
                )
            
            main_processed = await self.apply_market_specifications(
                original_image_data, marketplace, best_crop
            )
            
            # 6. Supabase 업로드
            timestamp = int(datetime.now().timestamp())
            main_filename = f"{product.sku}_{marketplace}_main_{timestamp}.jpg"
            main_url = await self.upload_to_supabase(main_processed, main_filename)
            
            processed_images.append({
                "type": "main",
                "url": main_url,
                "crop_region": best_crop,
                "file_size": len(main_processed)
            })
            
            # 7. 추가 변형 이미지 생성 (필요한 경우)
            variations = await self._generate_image_variations(
                original_image_data, marketplace, product
            )
            
            for i, variation in enumerate(variations):
                var_filename = f"{product.sku}_{marketplace}_var{i}_{timestamp}.jpg"
                var_url = await self.upload_to_supabase(variation["data"], var_filename)
                
                processed_images.append({
                    "type": f"variation_{i}",
                    "url": var_url,
                    "description": variation["description"],
                    "file_size": len(variation["data"])
                })
            
            # 8. 처리 이력 저장
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            processing_history = ImageProcessingHistory(
                product_id=product.id,
                original_image_url=best_image["original_url"],
                processed_image_url=main_url,
                processing_steps={
                    "detection": best_image["analysis"],
                    "crops": best_image["optimal_crops"],
                    "variations": len(variations)
                },
                market_specifications=await self._get_market_guidelines(marketplace),
                supabase_path=main_filename,
                processing_time_ms=int(processing_time),
                image_quality_score=best_image.get("quality_score", 0),
                compression_ratio=len(main_processed) / len(original_image_data),
                success=True,
                created_at=datetime.now()
            )
            
            self.db.add(processing_history)
            self.db.commit()
            
            return {
                "success": True,
                "main_image_url": main_url,
                "processed_images": processed_images,
                "quality_score": best_image.get("quality_score", 0),
                "processing_time_ms": int(processing_time),
                "original_size": len(original_image_data),
                "compressed_size": len(main_processed),
                "compression_ratio": len(main_processed) / len(original_image_data)
            }
            
        except Exception as e:
            # 오류 이력 저장
            processing_history = ImageProcessingHistory(
                product_id=product.id,
                original_image_url=image_urls[0] if image_urls else "",
                processing_steps={"error": str(e)},
                market_specifications={},
                success=False,
                error_message=str(e),
                created_at=datetime.now()
            )
            
            self.db.add(processing_history)
            self.db.commit()
            
            return {"error": str(e)}
    
    async def _download_image(self, url: str) -> Optional[bytes]:
        """이미지 다운로드"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.read()
                    return None
                    
        except Exception as e:
            print(f"이미지 다운로드 오류 {url}: {e}")
            return None
    
    async def _analyze_image_composition(
        self, 
        image_data: bytes, 
        marketplace: str
    ) -> Dict:
        """이미지 구성 분석"""
        
        try:
            # OpenCV로 이미지 분석
            nparr = np.frombuffer(image_data, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if cv_image is None:
                return {"error": "이미지 로드 실패"}
            
            height, width = cv_image.shape[:2]
            
            # 기본 품질 점수 계산
            quality_score = await self._calculate_quality_score(cv_image)
            
            # 최적 크롭 영역 탐지
            optimal_crops = await self._detect_crop_regions(cv_image, marketplace)
            
            # 색상 분석
            color_analysis = await self._analyze_colors(cv_image)
            
            # 텍스트 영역 탐지
            text_regions = await self._detect_text_regions(cv_image)
            
            return {
                "image_size": {"width": width, "height": height},
                "quality_score": quality_score,
                "optimal_crops": optimal_crops,
                "color_analysis": color_analysis,
                "text_regions": text_regions,
                "aspect_ratio": width / height
            }
            
        except Exception as e:
            print(f"이미지 분석 오류: {e}")
            return {"error": str(e)}
    
    async def _calculate_quality_score(self, cv_image: np.ndarray) -> float:
        """이미지 품질 점수 계산"""
        
        # 1. 선명도 (Laplacian variance)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 2. 밝기 분포
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 128) / 128
        
        # 3. 대비
        contrast = gray.std()
        contrast_score = min(contrast / 50, 1.0)
        
        # 4. 노이즈 수준
        noise = cv2.medianBlur(gray, 5)
        noise_diff = cv2.absdiff(gray, noise)
        noise_score = 1.0 - min(np.mean(noise_diff) / 20, 1.0)
        
        # 종합 점수 (0-10)
        total_score = (
            min(sharpness / 100, 1.0) * 3 +  # 선명도 30%
            brightness_score * 2 +            # 밝기 20%
            contrast_score * 3 +              # 대비 30%
            noise_score * 2                   # 노이즈 20%
        ) * 10
        
        return round(total_score, 2)
    
    async def _detect_crop_regions(
        self, 
        cv_image: np.ndarray, 
        marketplace: str
    ) -> List[Dict]:
        """최적 크롭 영역 탐지"""
        
        height, width = cv_image.shape[:2]
        regions = []
        
        # 마켓별 선호 비율
        ratios = {
            "coupang": [1.0],  # 정사각형
            "naver": [1.0, 4/3],  # 정사각형, 4:3
            "11st": [1.0, 3/4]   # 정사각형, 3:4
        }
        
        target_ratios = ratios.get(marketplace, [1.0])
        
        for ratio in target_ratios:
            # 중앙 크롭
            if ratio == 1.0:  # 정사각형
                size = min(width, height)
                x1 = (width - size) // 2
                y1 = (height - size) // 2
                x2 = x1 + size
                y2 = y1 + size
            else:
                if width / height > ratio:
                    # 가로가 더 긴 경우
                    new_width = int(height * ratio)
                    x1 = (width - new_width) // 2
                    y1 = 0
                    x2 = x1 + new_width
                    y2 = height
                else:
                    # 세로가 더 긴 경우
                    new_height = int(width / ratio)
                    x1 = 0
                    y1 = (height - new_height) // 2
                    x2 = width
                    y2 = y1 + new_height
            
            # 크롭 영역 품질 평가
            crop_region = cv_image[y1:y2, x1:x2]
            crop_quality = await self._calculate_quality_score(crop_region)
            
            regions.append({
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "ratio": ratio,
                "score": crop_quality,
                "type": "center_crop"
            })
        
        # 관심 영역 기반 크롭 (얼굴, 객체 등)
        interest_regions = await self._detect_interest_regions(cv_image)
        for region in interest_regions:
            regions.append(region)
        
        # 점수 순으로 정렬
        regions.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return regions[:5]  # 상위 5개만 반환
    
    async def _detect_interest_regions(self, cv_image: np.ndarray) -> List[Dict]:
        """관심 영역 탐지 (얼굴, 객체 등)"""
        
        regions = []
        
        try:
            # 1. 얼굴 탐지
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in faces:
                # 얼굴 주변으로 확장
                margin = min(w, h) // 2
                x1 = max(0, x - margin)
                y1 = max(0, y - margin)
                x2 = min(cv_image.shape[1], x + w + margin)
                y2 = min(cv_image.shape[0], y + h + margin)
                
                regions.append({
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "score": 8.5,  # 얼굴은 높은 점수
                    "type": "face_region"
                })
            
            # 2. 윤곽선 기반 객체 탐지
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 큰 윤곽선들만 선택
            large_contours = [c for c in contours if cv2.contourArea(c) > 1000]
            
            for contour in large_contours[:3]:  # 상위 3개
                x, y, w, h = cv2.boundingRect(contour)
                
                # 적절한 크기인지 확인
                if w > 50 and h > 50:
                    regions.append({
                        "x1": x, "y1": y, "x2": x + w, "y2": y + h,
                        "score": 7.0,
                        "type": "object_region"
                    })
            
        except Exception as e:
            print(f"관심 영역 탐지 오류: {e}")
        
        return regions
    
    async def _analyze_colors(self, cv_image: np.ndarray) -> Dict:
        """색상 분석"""
        
        # RGB로 변환
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        
        # 주요 색상 추출
        pixels = rgb_image.reshape(-1, 3)
        
        # K-means 클러스터링으로 주요 색상 찾기
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=5, random_state=42)
        kmeans.fit(pixels)
        
        colors = kmeans.cluster_centers_.astype(int)
        percentages = np.bincount(kmeans.labels_) / len(kmeans.labels_)
        
        dominant_colors = []
        for color, percentage in zip(colors, percentages):
            dominant_colors.append({
                "rgb": color.tolist(),
                "hex": "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2]),
                "percentage": float(percentage)
            })
        
        # 색상 온도 계산
        avg_color = np.mean(pixels, axis=0)
        color_temp = "warm" if avg_color[0] > avg_color[2] else "cool"
        
        return {
            "dominant_colors": dominant_colors,
            "average_color": avg_color.tolist(),
            "color_temperature": color_temp,
            "brightness": float(np.mean(cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)))
        }
    
    async def _detect_text_regions(self, cv_image: np.ndarray) -> List[Dict]:
        """텍스트 영역 탐지"""
        
        try:
            import pytesseract
            
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 텍스트 영역 탐지
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
            
            text_regions = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 30:  # 신뢰도 30% 이상
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    text_regions.append({
                        "x1": x, "y1": y, "x2": x + w, "y2": y + h,
                        "text": data['text'][i],
                        "confidence": int(data['conf'][i])
                    })
            
            return text_regions
            
        except ImportError:
            print("Tesseract가 설치되지 않음")
            return []
        except Exception as e:
            print(f"텍스트 탐지 오류: {e}")
            return []
    
    async def _resize_maintain_ratio(
        self, 
        image: Image.Image, 
        target_width: int, 
        target_height: int
    ) -> Image.Image:
        """비율 유지 리사이징 (왜곡 방지)"""
        
        original_width, original_height = image.size
        
        # 비율 계산
        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        
        # 작은 비율을 선택 (이미지가 잘리지 않도록)
        ratio = min(width_ratio, height_ratio)
        
        # 새 크기 계산
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # 리사이징
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 캔버스 생성 (배경색: 흰색)
        canvas = Image.new('RGB', (target_width, target_height), 'white')
        
        # 중앙에 배치
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        
        canvas.paste(resized_image, (x_offset, y_offset))
        
        return canvas
    
    async def _apply_coupang_optimization(self, image: Image.Image) -> Image.Image:
        """쿠팡 최적화 적용"""
        
        # 1. 색상 보정 (쿠팡은 색상 보정 허용)
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)  # 채도 10% 증가
        
        # 2. 대비 향상
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.05)  # 대비 5% 증가
        
        # 3. 선명도 향상
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)  # 선명도 10% 증가
        
        return image
    
    async def _apply_naver_optimization(self, image: Image.Image) -> Image.Image:
        """네이버 최적화 적용"""
        
        # 1. 자연스러운 색상 유지
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.05)  # 채도 약간 증가
        
        # 2. 밝기 조정
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.02)  # 밝기 약간 증가
        
        return image
    
    async def _apply_11st_optimization(self, image: Image.Image) -> Image.Image:
        """11번가 최적화 적용"""
        
        # 1. 고해상도 유지 (DPI 96 이하)
        # PIL은 DPI 메타데이터만 설정, 실제 해상도는 변경 안함
        
        # 2. 압축 최적화
        # 11번가는 파일 크기에 민감
        
        return image
    
    async def _optimize_file_size(
        self, 
        image: Image.Image, 
        max_size_mb: float
    ) -> Image.Image:
        """파일 크기 최적화"""
        
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # 품질을 조정하면서 크기 확인
        for quality in range(90, 30, -10):
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            
            if buffer.tell() <= max_size_bytes:
                break
        
        # 여전히 크면 크기 조정
        if buffer.tell() > max_size_bytes:
            width, height = image.size
            scale_factor = (max_size_bytes / buffer.tell()) ** 0.5
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    async def _generate_image_variations(
        self, 
        original_data: bytes, 
        marketplace: str, 
        product: Product
    ) -> List[Dict]:
        """이미지 변형 생성"""
        
        variations = []
        
        try:
            image = Image.open(BytesIO(original_data))
            
            # 1. 라이프스타일 이미지 (상황 연출)
            lifestyle_image = await self._create_lifestyle_variation(image, product)
            if lifestyle_image:
                buffer = BytesIO()
                lifestyle_image.save(buffer, format='JPEG', quality=85)
                variations.append({
                    "data": buffer.getvalue(),
                    "description": "라이프스타일 이미지"
                })
            
            # 2. 클로즈업 이미지
            closeup_image = await self._create_closeup_variation(image)
            if closeup_image:
                buffer = BytesIO()
                closeup_image.save(buffer, format='JPEG', quality=85)
                variations.append({
                    "data": buffer.getvalue(),
                    "description": "클로즈업 이미지"
                })
            
        except Exception as e:
            print(f"변형 이미지 생성 오류: {e}")
        
        return variations
    
    async def _create_lifestyle_variation(
        self, 
        image: Image.Image, 
        product: Product
    ) -> Optional[Image.Image]:
        """라이프스타일 변형 생성"""
        
        # 실제로는 AI 모델을 사용하여 상황에 맞는 배경 합성
        # 여기서는 간단한 효과만 적용
        
        try:
            # 부드러운 필터 적용
            filtered_image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # 따뜻한 톤 적용
            enhancer = ImageEnhance.Color(filtered_image)
            warm_image = enhancer.enhance(1.2)
            
            return warm_image
            
        except Exception:
            return None
    
    async def _create_closeup_variation(self, image: Image.Image) -> Optional[Image.Image]:
        """클로즈업 변형 생성"""
        
        try:
            width, height = image.size
            
            # 중앙 70% 영역을 크롭
            crop_margin = min(width, height) * 0.15
            x1, y1 = int(crop_margin), int(crop_margin)
            x2, y2 = int(width - crop_margin), int(height - crop_margin)
            
            cropped = image.crop((x1, y1, x2, y2))
            
            # 원본 크기로 확대
            closeup = cropped.resize((width, height), Image.Resampling.LANCZOS)
            
            return closeup
            
        except Exception:
            return None
    
    async def _save_locally(self, image_data: bytes, filename: str) -> str:
        """로컬 저장 (Supabase 대체)"""
        
        upload_dir = "uploads/processed_images"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        return f"/uploads/processed_images/{filename}"
    
    async def _get_market_guidelines(self, marketplace: str) -> Dict:
        """마켓 가이드라인 조회"""
        
        guideline = self.db.query(MarketGuideline).filter(
            MarketGuideline.marketplace == marketplace,
            MarketGuideline.is_active == True
        ).first()
        
        if guideline:
            return {
                "image_specs": guideline.image_specs,
                "naming_rules": guideline.naming_rules,
                "description_rules": guideline.description_rules,
                "prohibited_keywords": guideline.prohibited_keywords or [],
                "required_fields": guideline.required_fields or []
            }
        
        # 기본 가이드라인
        return {
            "coupang": {
                "image_specs": {
                    "width": 780, "height": 780, "format": ["jpg"],
                    "max_size_mb": 10
                }
            },
            "naver": {
                "image_specs": {
                    "width": 640, "height": 640, "format": ["jpg", "png"],
                    "max_size_mb": 20
                }
            },
            "11st": {
                "image_specs": {
                    "width": 1000, "height": 1000, "format": ["jpg"],
                    "max_size_mb": 5, "dpi": 96
                }
            }
        }.get(marketplace, {})
    
    def _extract_images_with_regex(self, html_content: str) -> Dict:
        """정규식으로 이미지 URL 추출"""
        
        import re
        
        # 다양한 이미지 URL 패턴
        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
            r'data-src=["\']([^"\']+)["\']',
            r'data-original=["\']([^"\']+)["\']',
            r'background-image:\s*url\(["\']?([^"\')+)["\']?\)'
        ]
        
        all_urls = []
        for pattern in patterns:
            urls = re.findall(pattern, html_content, re.IGNORECASE)
            all_urls.extend(urls)
        
        # URL 필터링 및 분류
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        filtered_urls = []
        
        for url in all_urls:
            if any(ext in url.lower() for ext in image_extensions):
                # 상대 URL을 절대 URL로 변환 (필요시)
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    # 도메인 정보가 필요하지만 여기서는 스킵
                    continue
                
                filtered_urls.append(url)
        
        return {
            "main_images": filtered_urls[:5],
            "detail_images": filtered_urls[5:15] if len(filtered_urls) > 5 else [],
            "thumbnail_images": filtered_urls[15:] if len(filtered_urls) > 15 else []
        }
    
    async def _track_processing_cost(
        self, 
        processing_type: str, 
        ai_model: str, 
        request_count: int, 
        cost: float
    ):
        """가공 비용 추적"""
        
        from sqlalchemy import and_
        
        today = datetime.now().date()
        
        cost_tracking = self.db.query(ProcessingCostTracking).filter(
            and_(
                ProcessingCostTracking.date == today,
                ProcessingCostTracking.processing_type == processing_type,
                ProcessingCostTracking.ai_model == ai_model
            )
        ).first()
        
        if cost_tracking:
            cost_tracking.total_requests += request_count
            cost_tracking.total_cost += Decimal(str(cost))
            cost_tracking.average_cost_per_request = (
                cost_tracking.total_cost / cost_tracking.total_requests
            )
            cost_tracking.cost_optimization_used = self.is_night_time
        else:
            cost_tracking = ProcessingCostTracking(
                date=datetime.now(),
                processing_type=processing_type,
                ai_model=ai_model,
                total_requests=request_count,
                total_cost=Decimal(str(cost)),
                average_cost_per_request=Decimal(str(cost)),
                cost_optimization_used=self.is_night_time
            )
            self.db.add(cost_tracking)
        
        self.db.commit()
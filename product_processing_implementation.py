"""
드랍쉬핑 상품가공 시스템 구현 예제
- 상품명 AI 생성기
- 이미지 프로세싱 엔진  
- 상세페이지 분석기
"""

import asyncio
import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import openai
import supabase
import redis
from dataclasses import dataclass
from abc import ABC, abstractmethod

# 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketConfig:
    """마켓별 설정"""
    name: str
    title_length: Tuple[int, int]
    keywords: List[str]
    avoid_words: List[str]
    image_size: Tuple[int, int]
    image_format: str
    image_quality: int

# 마켓 설정
MARKET_CONFIGS = {
    'coupang': MarketConfig(
        name='coupang',
        title_length=(40, 80),
        keywords=['특가', '베스트', '인기', '할인'],
        avoid_words=['카탈로그', '아임템위너', '가격비교'],
        image_size=(800, 800),
        image_format='JPEG',
        image_quality=85
    ),
    'naver': MarketConfig(
        name='naver',
        title_length=(30, 60),
        keywords=['추천', '신상', '할인', '품질'],
        avoid_words=['가격비교', '최저가'],
        image_size=(700, 700),
        image_format='JPEG',
        image_quality=90
    ),
    '11st': MarketConfig(
        name='11st',
        title_length=(35, 70),
        keywords=['할인', '특가', '인기', '가성비'],
        avoid_words=['최저가', '카탈로그'],
        image_size=(750, 750),
        image_format='JPEG',
        image_quality=80
    )
}

class AIModelManager:
    """AI 모델 관리자 - 비용 최적화"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.cost_tracker = {}
        self.current_hour = datetime.now().hour
        
    def get_optimal_model(self, urgency='normal', account_priority='normal'):
        """시간대와 우선순위에 따른 최적 모델 선택"""
        
        # 주력 계정 또는 긴급한 경우 프리미엄 모델
        if account_priority == 'high' or urgency == 'urgent':
            return 'gpt-4o-mini'
        
        # 야간 시간대 (19:00 - 08:00) - 로컬 모델 활용
        if 19 <= self.current_hour or self.current_hour <= 8:
            return 'ollama_local'
        
        # 주간 시간대 - 비용 효율 모델
        return 'gpt-4o-mini'
    
    async def generate_with_cost_tracking(self, prompt: str, model: str = None):
        """비용 추적과 함께 텍스트 생성"""
        
        if not model:
            model = self.get_optimal_model()
        
        start_time = datetime.now()
        
        if model == 'ollama_local':
            # 로컬 모델 사용 (비용 없음)
            result = await self._generate_with_ollama(prompt)
            cost = 0
        else:
            # OpenAI 모델 사용
            result = await self._generate_with_openai(prompt, model)
            cost = self._calculate_openai_cost(prompt, result, model)
        
        # 비용 추적
        self._track_cost(model, cost, datetime.now() - start_time)
        
        return result
    
    async def _generate_with_ollama(self, prompt: str):
        """Ollama 로컬 모델로 생성"""
        # 실제 구현에서는 ollama API 호출
        return f"[로컬 모델 생성 결과] {prompt[:50]}..."
    
    async def _generate_with_openai(self, prompt: str, model: str):
        """OpenAI 모델로 생성"""
        # 실제 구현에서는 OpenAI API 호출
        return f"[OpenAI 생성 결과] {prompt[:50]}..."
    
    def _calculate_openai_cost(self, prompt: str, result: str, model: str):
        """OpenAI 비용 계산"""
        # 토큰 기반 비용 계산 로직
        input_tokens = len(prompt.split()) * 1.3  # 추정
        output_tokens = len(result.split()) * 1.3
        
        if model == 'gpt-4o-mini':
            cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
        
        return cost
    
    def _track_cost(self, model: str, cost: float, duration):
        """비용 및 성능 추적"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"cost:{today}:{model}"
        
        current_cost = float(self.redis_client.get(key) or 0)
        self.redis_client.set(key, current_cost + cost, ex=86400)  # 24시간 만료

class BestsellerPatternAnalyzer:
    """베스트셀러 패턴 분석기"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=1)
        
    def analyze_patterns(self, market: str, category: str) -> Dict:
        """베스트셀러 패턴 분석"""
        
        cache_key = f"patterns:{market}:{category}"
        cached = self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # 베스트셀러 데이터 수집 및 분석
        patterns = self._collect_and_analyze_bestsellers(market, category)
        
        # 캐시 저장 (6시간)
        self.redis_client.set(cache_key, json.dumps(patterns), ex=21600)
        
        return patterns
    
    def _collect_and_analyze_bestsellers(self, market: str, category: str) -> Dict:
        """베스트셀러 데이터 수집 및 분석"""
        
        # 실제 구현에서는 웹 스크래핑 또는 API 호출
        patterns = {
            'title_patterns': [
                '베스트 {상품명}',
                '{브랜드} {상품명} 특가',
                '인기 {상품명} 추천'
            ],
            'keyword_frequency': {
                '특가': 0.8,
                '베스트': 0.7,
                '추천': 0.6,
                '할인': 0.5
            },
            'successful_structures': [
                '{브랜드} {상품명} {특징} {혜택}',
                '{키워드} {상품명} {용도} {추천}'
            ]
        }
        
        return patterns

class ProductNameGenerator:
    """상품명 AI 생성기"""
    
    def __init__(self):
        self.ai_manager = AIModelManager()
        self.pattern_analyzer = BestsellerPatternAnalyzer()
        
    async def generate_title(self, product_info: Dict, market: str, 
                           account_priority: str = 'normal') -> List[str]:
        """상품명 생성"""
        
        # 베스트셀러 패턴 분석
        patterns = self.pattern_analyzer.analyze_patterns(
            market, product_info.get('category', 'general')
        )
        
        # 마켓 설정 가져오기
        config = MARKET_CONFIGS.get(market, MARKET_CONFIGS['coupang'])
        
        # 프롬프트 생성
        prompt = self._create_title_prompt(product_info, config, patterns)
        
        # AI 모델로 생성
        result = await self.ai_manager.generate_with_cost_tracking(
            prompt, 
            urgency='normal',
        )
        
        # 결과 파싱 및 검증
        titles = self._parse_and_validate_titles(result, config)
        
        return titles
    
    def _create_title_prompt(self, product_info: Dict, config: MarketConfig, 
                           patterns: Dict) -> str:
        """상품명 생성 프롬프트 작성"""
        
        prompt = f"""
        마켓플랫폼: {config.name}
        원본 상품명: {product_info.get('original_title', '')}
        카테고리: {product_info.get('category', '')}
        주요 특징: {product_info.get('features', '')}
        
        마켓별 요구사항:
        - 제목 길이: {config.title_length[0]}-{config.title_length[1]}자
        - 선호 키워드: {', '.join(config.keywords)}
        - 회피 단어: {', '.join(config.avoid_words)}
        
        베스트셀러 패턴:
        {json.dumps(patterns['successful_structures'], ensure_ascii=False)}
        
        요구사항:
        1. 가격비교 사이트 탐지 회피
        2. 마켓 베스트셀러 패턴 적용
        3. SEO 키워드 최적화
        4. 클릭률 향상을 위한 매력적인 표현
        5. 소비자 관심을 끄는 혜택 강조
        
        JSON 형식으로 3개의 상품명 생성:
        {{
            "titles": ["제목1", "제목2", "제목3"],
            "reasoning": "생성 근거"
        }}
        """
        
        return prompt
    
    def _parse_and_validate_titles(self, result: str, config: MarketConfig) -> List[str]:
        """생성된 제목 파싱 및 검증"""
        
        try:
            parsed = json.loads(result)
            titles = parsed.get('titles', [])
        except:
            # JSON 파싱 실패 시 텍스트에서 추출
            titles = [line.strip() for line in result.split('\n') 
                     if line.strip() and not line.startswith('{')][:3]
        
        # 제목 검증 및 필터링
        validated_titles = []
        for title in titles:
            if self._validate_title(title, config):
                validated_titles.append(title)
        
        return validated_titles[:3]
    
    def _validate_title(self, title: str, config: MarketConfig) -> bool:
        """제목 유효성 검사"""
        
        # 길이 체크
        if not (config.title_length[0] <= len(title) <= config.title_length[1]):
            return False
        
        # 금지 단어 체크
        for avoid_word in config.avoid_words:
            if avoid_word in title:
                return False
        
        return True

class ProductPageScraper:
    """상품 페이지 스크래핑"""
    
    def __init__(self):
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Selenium 드라이버 설정"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=options)
    
    def extract_product_images(self, url: str) -> List[str]:
        """상품 이미지 추출"""
        
        try:
            self.driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
            
            # 스크롤하여 모든 이미지 로드
            self._scroll_to_load_images()
            
            # 상품 이미지 찾기
            image_urls = self._find_product_images()
            
            return image_urls
            
        except Exception as e:
            logger.error(f"이미지 추출 오류: {e}")
            return []
    
    def _scroll_to_load_images(self):
        """스크롤하여 모든 이미지 로드"""
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # 페이지 끝까지 스크롤
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 로딩 대기
            asyncio.sleep(2)
            
            # 새로운 높이 계산
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
                
            last_height = new_height
    
    def _find_product_images(self) -> List[str]:
        """상품 이미지 URL 찾기"""
        
        image_urls = []
        
        # 다양한 선택자로 이미지 찾기
        selectors = [
            "img[src*='product']",
            "img[alt*='상품']",
            ".product-image img",
            ".item-image img",
            ".detail-image img"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    src = element.get_attribute('src')
                    if src and self._is_valid_image_url(src):
                        image_urls.append(src)
            except:
                continue
        
        return list(set(image_urls))  # 중복 제거
    
    def _is_valid_image_url(self, url: str) -> bool:
        """유효한 이미지 URL 체크"""
        
        if not url or url.startswith('data:'):
            return False
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        return any(ext in url.lower() for ext in valid_extensions)
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()

class OptimalImageDetector:
    """최적 이미지 영역 탐지"""
    
    def __init__(self):
        # 실제 구현에서는 YOLO 모델 로드
        pass
    
    def find_best_crop_area(self, image_array: np.ndarray) -> Tuple[int, int, int, int]:
        """최적 크롭 영역 탐지"""
        
        # 실제 구현에서는 YOLO 또는 객체 탐지 모델 사용
        # 여기서는 간단한 휴리스틱 사용
        
        height, width = image_array.shape[:2]
        
        # 중앙 영역을 기본으로 설정
        margin_x = width // 8
        margin_y = height // 8
        
        x1 = margin_x
        y1 = margin_y
        x2 = width - margin_x
        y2 = height - margin_y
        
        # 상품이 있을 가능성이 높은 영역 탐지
        crop_area = self._detect_product_area(image_array, x1, y1, x2, y2)
        
        return crop_area
    
    def _detect_product_area(self, image: np.ndarray, x1: int, y1: int, 
                           x2: int, y2: int) -> Tuple[int, int, int, int]:
        """상품 영역 탐지 (휴리스틱)"""
        
        # 엣지 탐지
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 컨투어 찾기
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 가장 큰 컨투어 찾기
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 바운딩 박스 조정
            padding = 20
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image.shape[1], x + w + padding)
            y2 = min(image.shape[0], y + h + padding)
            
            return (x1, y1, x2, y2)
        
        return (x1, y1, x2, y2)

class MarketImageOptimizer:
    """마켓별 이미지 최적화"""
    
    def __init__(self):
        self.detector = OptimalImageDetector()
    
    def optimize_for_market(self, image_url: str, market: str) -> Image.Image:
        """마켓별 이미지 최적화"""
        
        config = MARKET_CONFIGS.get(market, MARKET_CONFIGS['coupang'])
        
        # 이미지 다운로드
        image = self._download_image(image_url)
        if not image:
            return None
        
        # 최적 영역 탐지
        image_array = np.array(image)
        crop_area = self.detector.find_best_crop_area(image_array)
        
        # 크롭 적용
        cropped = image.crop(crop_area)
        
        # 마켓 규격에 맞게 리사이징 (왜곡 방지)
        resized = self._resize_maintain_ratio(cropped, config.image_size)
        
        # 배경 패딩 추가
        final_image = self._add_smart_padding(resized, config.image_size)
        
        # 품질 최적화
        optimized = self._optimize_quality(final_image, config)
        
        return optimized
    
    def _download_image(self, url: str) -> Optional[Image.Image]:
        """이미지 다운로드"""
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            image = Image.open(response.content)
            return image.convert('RGB')
            
        except Exception as e:
            logger.error(f"이미지 다운로드 실패: {e}")
            return None
    
    def _resize_maintain_ratio(self, image: Image.Image, 
                             target_size: Tuple[int, int]) -> Image.Image:
        """비율을 유지하며 리사이징"""
        
        original_width, original_height = image.size
        target_width, target_height = target_size
        
        # 비율 계산
        width_ratio = target_width / original_width
        height_ratio = target_height / original_height
        
        # 작은 비율 사용 (이미지가 타겟 사이즈를 넘지 않도록)
        ratio = min(width_ratio, height_ratio)
        
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _add_smart_padding(self, image: Image.Image, 
                          target_size: Tuple[int, int]) -> Image.Image:
        """스마트 패딩 추가"""
        
        target_width, target_height = target_size
        current_width, current_height = image.size
        
        # 패딩 계산
        pad_width = target_width - current_width
        pad_height = target_height - current_height
        
        # 배경색 자동 감지 (가장자리 픽셀의 평균)
        background_color = self._detect_background_color(image)
        
        # 새 이미지 생성
        new_image = Image.new('RGB', target_size, background_color)
        
        # 중앙에 원본 이미지 배치
        paste_x = pad_width // 2
        paste_y = pad_height // 2
        new_image.paste(image, (paste_x, paste_y))
        
        return new_image
    
    def _detect_background_color(self, image: Image.Image) -> Tuple[int, int, int]:
        """배경색 자동 감지"""
        
        # 가장자리 픽셀들의 평균색 계산
        width, height = image.size
        
        edge_pixels = []
        
        # 상하 가장자리
        for x in range(width):
            edge_pixels.append(image.getpixel((x, 0)))
            edge_pixels.append(image.getpixel((x, height - 1)))
        
        # 좌우 가장자리
        for y in range(height):
            edge_pixels.append(image.getpixel((0, y)))
            edge_pixels.append(image.getpixel((width - 1, y)))
        
        # 평균 계산
        avg_r = sum(pixel[0] for pixel in edge_pixels) // len(edge_pixels)
        avg_g = sum(pixel[1] for pixel in edge_pixels) // len(edge_pixels)
        avg_b = sum(pixel[2] for pixel in edge_pixels) // len(edge_pixels)
        
        return (avg_r, avg_g, avg_b)
    
    def _optimize_quality(self, image: Image.Image, config: MarketConfig) -> Image.Image:
        """이미지 품질 최적화"""
        
        # 약간의 선명도 향상
        enhancer = ImageEnhance.Sharpness(image)
        sharpened = enhancer.enhance(1.1)
        
        # 대비 약간 향상
        enhancer = ImageEnhance.Contrast(sharpened)
        contrasted = enhancer.enhance(1.05)
        
        return contrasted

class AlternativeUseAnalyzer:
    """대체 용도 분석기"""
    
    def __init__(self):
        self.ai_manager = AIModelManager()
    
    async def analyze_alternative_uses(self, product_description: str, 
                                     category: str) -> List[Dict]:
        """제품의 대체 용도 분석"""
        
        prompt = f"""
        제품 설명: {product_description}
        현재 카테고리: {category}
        
        이 제품의 대체 용도를 분석하여 새로운 마케팅 기회를 찾아주세요.
        
        분석 요구사항:
        1. 제품의 물리적 특성 분석
        2. 다른 용도로 사용 가능한 시나리오 발굴
        3. 타겟 고객층 확장 가능성
        4. 경쟁력 있는 포지셔닝 방안
        
        JSON 형식으로 응답:
        {{
            "alternative_uses": [
                {{
                    "use_case": "용도명",
                    "description": "상세 설명",
                    "target_audience": "타겟 고객",
                    "market_potential": "시장 잠재력 (1-10)"
                }}
            ],
            "positioning_suggestions": ["포지셔닝 제안1", "포지셔닝 제안2"],
            "marketing_angles": ["마케팅 앵글1", "마케팅 앵글2"]
        }}
        """
        
        result = await self.ai_manager.generate_with_cost_tracking(prompt)
        
        try:
            parsed = json.loads(result)
            return parsed.get('alternative_uses', [])
        except:
            return []

class SupabaseImageUploader:
    """Supabase 이미지 업로더"""
    
    def __init__(self, url: str, key: str):
        self.client = supabase.create_client(url, key)
        self.bucket_name = 'product-images'
    
    def upload_image(self, image: Image.Image, filename: str) -> Optional[str]:
        """이미지 업로드"""
        
        try:
            # 이미지를 바이트로 변환
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()
            
            # Supabase에 업로드
            result = self.client.storage.from_(self.bucket_name).upload(
                filename, img_byte_arr
            )
            
            if result.error:
                logger.error(f"업로드 오류: {result.error}")
                return None
            
            # 공개 URL 생성
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            return public_url
            
        except Exception as e:
            logger.error(f"이미지 업로드 실패: {e}")
            return None

class NightBatchProcessor:
    """야간 배치 처리 시스템"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=2)
        self.name_generator = ProductNameGenerator()
        self.image_optimizer = MarketImageOptimizer()
        self.uploader = SupabaseImageUploader(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY')
        )
    
    async def process_night_batch(self):
        """야간 배치 처리"""
        
        logger.info("야간 배치 처리 시작")
        
        # 대기 중인 작업 가져오기
        pending_jobs = self._get_pending_jobs()
        
        if not pending_jobs:
            logger.info("처리할 작업이 없습니다")
            return
        
        # 우선순위별 정렬
        sorted_jobs = self._prioritize_jobs(pending_jobs)
        
        # 배치 처리
        for job in sorted_jobs:
            try:
                await self._process_single_job(job)
                logger.info(f"작업 완료: {job['id']}")
            except Exception as e:
                logger.error(f"작업 실패: {job['id']}, 오류: {e}")
                self._mark_job_failed(job['id'], str(e))
        
        logger.info("야간 배치 처리 완료")
    
    def _get_pending_jobs(self) -> List[Dict]:
        """대기 중인 작업 가져오기"""
        
        job_keys = self.redis_client.keys("job:pending:*")
        jobs = []
        
        for key in job_keys:
            job_data = self.redis_client.get(key)
            if job_data:
                jobs.append(json.loads(job_data))
        
        return jobs
    
    def _prioritize_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """작업 우선순위 정렬"""
        
        def priority_score(job):
            score = 0
            
            # 계정 우선순위
            if job.get('account_priority') == 'high':
                score += 100
            
            # 작업 생성 시간 (오래된 것 우선)
            created_time = datetime.fromisoformat(job.get('created_at', ''))
            hours_old = (datetime.now() - created_time).total_seconds() / 3600
            score += hours_old
            
            return score
        
        return sorted(jobs, key=priority_score, reverse=True)
    
    async def _process_single_job(self, job: Dict):
        """단일 작업 처리"""
        
        job_type = job.get('type')
        
        if job_type == 'generate_title':
            await self._process_title_generation(job)
        elif job_type == 'optimize_image':
            await self._process_image_optimization(job)
        elif job_type == 'analyze_alternative_uses':
            await self._process_alternative_analysis(job)
        
        # 완료 마크
        self._mark_job_completed(job['id'])
    
    async def _process_title_generation(self, job: Dict):
        """상품명 생성 작업 처리"""
        
        product_info = job['data']['product_info']
        market = job['data']['market']
        
        titles = await self.name_generator.generate_title(
            product_info, market, account_priority='normal'
        )
        
        # 결과 저장
        self._save_job_result(job['id'], {'titles': titles})
    
    async def _process_image_optimization(self, job: Dict):
        """이미지 최적화 작업 처리"""
        
        image_url = job['data']['image_url']
        market = job['data']['market']
        product_id = job['data']['product_id']
        
        # 이미지 최적화
        optimized_image = self.image_optimizer.optimize_for_market(image_url, market)
        
        if optimized_image:
            # Supabase에 업로드
            filename = f"{product_id}_{market}_{datetime.now().timestamp()}.jpg"
            uploaded_url = self.uploader.upload_image(optimized_image, filename)
            
            # 결과 저장
            self._save_job_result(job['id'], {'optimized_url': uploaded_url})
    
    async def _process_alternative_analysis(self, job: Dict):
        """대체 용도 분석 작업 처리"""
        
        description = job['data']['description']
        category = job['data']['category']
        
        analyzer = AlternativeUseAnalyzer()
        alternative_uses = await analyzer.analyze_alternative_uses(description, category)
        
        # 결과 저장
        self._save_job_result(job['id'], {'alternative_uses': alternative_uses})
    
    def _mark_job_completed(self, job_id: str):
        """작업 완료 마크"""
        
        # pending에서 제거
        self.redis_client.delete(f"job:pending:{job_id}")
        
        # completed로 이동
        self.redis_client.set(
            f"job:completed:{job_id}",
            json.dumps({'completed_at': datetime.now().isoformat()}),
            ex=86400  # 24시간 후 삭제
        )
    
    def _mark_job_failed(self, job_id: str, error: str):
        """작업 실패 마크"""
        
        # pending에서 제거
        self.redis_client.delete(f"job:pending:{job_id}")
        
        # failed로 이동
        self.redis_client.set(
            f"job:failed:{job_id}",
            json.dumps({
                'failed_at': datetime.now().isoformat(),
                'error': error
            }),
            ex=86400  # 24시간 후 삭제
        )
    
    def _save_job_result(self, job_id: str, result: Dict):
        """작업 결과 저장"""
        
        self.redis_client.set(
            f"job:result:{job_id}",
            json.dumps(result),
            ex=604800  # 7일 후 삭제
        )

class ComplianceChecker:
    """컴플라이언스 검증기"""
    
    def __init__(self):
        self.prohibited_keywords = self._load_prohibited_keywords()
        self.brand_whitelist = self._load_brand_whitelist()
    
    def check_compliance(self, product_data: Dict) -> Tuple[bool, Dict]:
        """컴플라이언스 검증"""
        
        checks = {
            'trademark_safe': self._check_trademark_safety(product_data),
            'description_accurate': self._verify_description_accuracy(product_data),
            'image_legal': self._check_image_legality(product_data),
            'platform_compliant': self._check_platform_rules(product_data)
        }
        
        all_passed = all(checks.values())
        
        return all_passed, checks
    
    def _check_trademark_safety(self, product_data: Dict) -> bool:
        """상표권 안전성 검사"""
        
        title = product_data.get('title', '').lower()
        
        # 브랜드명이 화이트리스트에 있는지 확인
        for brand in self.brand_whitelist:
            if brand.lower() in title:
                return True
        
        # 금지된 키워드 확인
        for keyword in self.prohibited_keywords:
            if keyword.lower() in title:
                return False
        
        return True
    
    def _verify_description_accuracy(self, product_data: Dict) -> bool:
        """상품 설명 정확성 검증"""
        
        # 과장 광고 표현 체크
        exaggerated_terms = ['100%', '완벽한', '최고의', '세계 최초']
        description = product_data.get('description', '').lower()
        
        for term in exaggerated_terms:
            if term in description:
                return False
        
        return True
    
    def _check_image_legality(self, product_data: Dict) -> bool:
        """이미지 법적 문제 검사"""
        
        # 이미지가 충분히 변형되었는지 확인
        # 실제 구현에서는 이미지 유사도 검사
        
        return True
    
    def _check_platform_rules(self, product_data: Dict) -> bool:
        """플랫폼 규정 준수 검사"""
        
        market = product_data.get('market', '')
        title = product_data.get('title', '')
        
        config = MARKET_CONFIGS.get(market)
        if not config:
            return False
        
        # 제목 길이 체크
        if not (config.title_length[0] <= len(title) <= config.title_length[1]):
            return False
        
        # 금지 단어 체크
        for avoid_word in config.avoid_words:
            if avoid_word in title:
                return False
        
        return True
    
    def _load_prohibited_keywords(self) -> List[str]:
        """금지 키워드 로드"""
        
        return [
            '카탈로그', '아임템위너', '가격비교', '최저가',
            '복사품', '짝퉁', '모조품'
        ]
    
    def _load_brand_whitelist(self) -> List[str]:
        """브랜드 화이트리스트 로드"""
        
        return [
            # 허용된 브랜드명들
            '삼성', 'LG', '나이키', '아디다스'
        ]

# 사용 예제
async def main():
    """메인 실행 함수"""
    
    # 상품 정보
    product_info = {
        'original_title': '플라스틱 보관함 대용량',
        'category': '생활용품',
        'features': '투명, 뚜껑 포함, 쌓기 가능',
        'description': '다양한 용도로 사용 가능한 플라스틱 보관함'
    }
    
    # 1. 상품명 생성
    name_generator = ProductNameGenerator()
    titles = await name_generator.generate_title(product_info, 'coupang')
    print("생성된 상품명:", titles)
    
    # 2. 이미지 최적화
    image_optimizer = MarketImageOptimizer()
    # optimized_image = image_optimizer.optimize_for_market(
    #     'https://example.com/product.jpg', 'coupang'
    # )
    
    # 3. 대체 용도 분석
    alternative_analyzer = AlternativeUseAnalyzer()
    alternative_uses = await alternative_analyzer.analyze_alternative_uses(
        product_info['description'], product_info['category']
    )
    print("대체 용도:", alternative_uses)
    
    # 4. 컴플라이언스 검증
    compliance_checker = ComplianceChecker()
    is_compliant, checks = compliance_checker.check_compliance({
        'title': titles[0] if titles else '테스트 상품명',
        'market': 'coupang',
        'description': product_info['description']
    })
    print("컴플라이언스 통과:", is_compliant, checks)

if __name__ == "__main__":
    import os
    asyncio.run(main())
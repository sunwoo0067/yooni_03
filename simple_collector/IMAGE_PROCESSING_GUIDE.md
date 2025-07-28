# 이미지 가공 및 호스팅 시스템 가이드

## 시스템 개요

이미지 처리 시스템은 도매처 상품 이미지를 마켓플레이스 요구사항에 맞게 가공하고 호스팅하는 기능을 제공합니다.

### 주요 기능
- ✅ 이미지 다운로드 및 리사이즈
- ✅ 마켓플레이스별 최적화
- ✅ 워터마크 추가
- ✅ 썸네일 생성
- ✅ 로컬 호스팅
- ✅ 중복 제거
- ✅ 스토리지 관리

## 설치 및 설정

### 1. 필요 라이브러리 설치
```bash
pip install -r requirements_image.txt
```

### 2. 디렉토리 구조
```
static/
├── images/
│   ├── original/      # 원본 이미지
│   ├── processed/     # 처리된 이미지
│   │   ├── coupang/   # 마켓플레이스별
│   │   ├── naver/
│   │   └── 11st/
│   └── thumbnail/     # 썸네일
```

## 웹 UI 사용법

### 이미지 관리 페이지
http://localhost:4173/images

#### 기능별 사용법

1. **단일 상품 이미지 처리**
   - "이미지 처리" 버튼 클릭
   - 상품 코드 입력
   - 마켓플레이스 선택
   - 이미지 URL 입력 (줄바꿈으로 구분)
   - 워터마크 옵션 선택
   - "처리 시작" 클릭

2. **도매 상품 일괄 처리**
   - "도매 상품 일괄 처리" 버튼 클릭
   - 50개 상품씩 배치 처리

3. **스토리지 관리**
   - 현재 사용량 확인
   - "오래된 이미지 정리" (30일 이상)

## API 사용법

### 1. 단일 상품 이미지 처리
```bash
curl -X POST "http://localhost:8000/images/process/PRODUCT001" \
  -H "Content-Type: application/json" \
  -d '{
    "product_code": "PRODUCT001",
    "image_urls": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ],
    "marketplace": "coupang",
    "add_watermark": true
  }'
```

### 2. 호스팅된 이미지 조회
```bash
curl "http://localhost:8000/images/hosted/PRODUCT001?marketplace=coupang"
```

### 3. 스토리지 통계
```bash
curl "http://localhost:8000/images/storage/stats"
```

### 4. 도매 상품 일괄 처리
```bash
curl -X POST "http://localhost:8000/images/process-wholesale-images" \
  -H "Content-Type: application/json" \
  -d '{
    "supplier": "zentrade",
    "limit": 100
  }'
```

## 프로그래밍 사용법

### 이미지 프로세서 직접 사용
```python
from services.image.image_processor import ImageProcessor

processor = ImageProcessor()

# 이미지 처리
result = await processor.process_product_images(
    product_code="TEST001",
    image_urls=["https://example.com/image.jpg"],
    marketplace='coupang',
    add_watermark=True
)

print(result)
# {
#   'original': ['path/to/original.jpg'],
#   'processed': ['path/to/processed.jpg'],
#   'thumbnail': ['path/to/thumb.jpg']
# }
```

### 이미지 호스팅 서비스 사용
```python
from services.image.image_hosting import ImageHostingService
from database.connection import SessionLocal

db = SessionLocal()
hosting = ImageHostingService(db)

# 이미지 호스팅
hosted_url = hosting.host_image(
    product_code="TEST001",
    marketplace="coupang",
    local_path="path/to/image.jpg",
    image_type="main"
)

print(f"호스팅 URL: {hosted_url}")
```

## 마켓플레이스별 최적화

### 쿠팡
- 메인 이미지: 500x500px
- 최대 크기: 1000x1000px
- 포맷: JPEG
- 품질: 85%

### 네이버 스마트스토어
- 메인 이미지: 500x500px
- 최대 크기: 1300x1300px
- 포맷: JPEG
- 품질: 90%

### 11번가
- 메인 이미지: 400x400px
- 최대 크기: 800x800px
- 포맷: JPEG
- 품질: 85%

## 테스트

### 종합 테스트 실행
```bash
python test_image_processing.py
```

테스트 항목:
1. ✅ 이미지 다운로드
2. ✅ 크기 조정
3. ✅ 워터마크 추가
4. ✅ 호스팅 URL 생성
5. ✅ API 엔드포인트
6. ✅ 실제 도매 상품 처리

## 모니터링

### 스토리지 사용량 확인
- 웹 UI에서 실시간 확인
- API로 자동 모니터링 가능

### 로그 확인
```bash
tail -f logs/app.log | grep "이미지"
```

## 문제 해결

### 이미지 다운로드 실패
- URL 유효성 확인
- 네트워크 연결 확인
- User-Agent 헤더 문제

### 메모리 부족
- 대용량 이미지 배치 처리 시
- 처리 개수 제한 (limit 파라미터)

### 디스크 공간 부족
- 정기적인 정리 작업 실행
- 오래된 이미지 삭제

## 성능 최적화

### 배치 처리
- 동시 처리 수 제한
- 메모리 사용량 모니터링

### 캐싱
- 중복 이미지 제거
- 해시 기반 중복 검사

### CDN 연동 (선택사항)
```python
# CDN 마이그레이션 예시
def upload_to_cdn(local_path):
    # CDN 업로드 로직
    return "https://cdn.example.com/image.jpg"

hosting.migrate_to_cdn(upload_to_cdn, batch_size=100)
```

## 자동화

### 스케줄링된 처리
```python
# 매일 새로운 상품 이미지 처리
import schedule

def process_new_images():
    # 새로운 상품 이미지 처리 로직
    pass

schedule.every().day.at("02:00").do(process_new_images)
```

### 정리 작업
```python
# 주 단위 정리 작업
schedule.every().week.do(lambda: hosting.cleanup_unused_images(7))
```

## 보안 고려사항

1. **이미지 검증**: 악성 파일 업로드 방지
2. **접근 제어**: 호스팅된 이미지 접근 제한
3. **용량 제한**: 파일 크기 및 개수 제한
# 도매처 상품 수집 및 다운로드 가이드

## 빠른 시작

### 1. API 키 설정 확인 및 수집
```bash
# 현재 상태 확인 및 수집 시작
python check_and_collect.py
```

### 2. 전체 상품 다운로드
```bash
# 모든 도매처 상품을 엑셀로 다운로드
python download_wholesale_products.py --all
```

## 상세 사용법

### 도매처별 API 키 설정

1. 웹 브라우저에서 http://localhost:4173/settings 접속
2. 각 도매처별 API 키 입력:
   - **Zentrade**: API ID 입력
   - **Ownerclan**: 사용자명 입력
   - **Domeggook**: API 키 입력
   - **Domomae**: API 키 입력
3. 저장 버튼 클릭

### 상품 수집 옵션

#### 전체 도매처 수집 (실제 API)
```bash
python collect_all_wholesale.py
```

#### 테스트 모드로 수집
```bash
python collect_all_wholesale.py --test
```

#### 특정 도매처만 수집
```bash
python collect_all_wholesale.py --supplier zentrade
python collect_all_wholesale.py --supplier ownerclan
```

#### 수집 결과 요약 보기
```bash
python collect_all_wholesale.py --summary
```

### 상품 다운로드 옵션

#### 전체 상품 다운로드
```bash
python download_wholesale_products.py --all
```

생성되는 파일:
- `zentrade_products_YYYYMMDD_HHMMSS.xlsx` - Zentrade 상품
- `ownerclan_products_YYYYMMDD_HHMMSS.xlsx` - Ownerclan 상품
- `domeggook_products_YYYYMMDD_HHMMSS.xlsx` - 도매꾹 상품
- `domomae_products_YYYYMMDD_HHMMSS.xlsx` - 도모매 상품
- `all_wholesale_products_YYYYMMDD_HHMMSS.xlsx` - 전체 통합
- `coupang_upload_format_YYYYMMDD_HHMMSS.xlsx` - 쿠팡 업로드용
- `naver_upload_format_YYYYMMDD_HHMMSS.xlsx` - 네이버 업로드용

#### 필터링 다운로드
```bash
# 특정 도매처
python download_wholesale_products.py --supplier zentrade

# 특정 카테고리
python download_wholesale_products.py --category "전자제품"

# 가격 범위
python download_wholesale_products.py --min-price 10000 --max-price 50000

# 조합
python download_wholesale_products.py --supplier ownerclan --category "패션의류" --output fashion_products.xlsx
```

## 웹 UI에서 확인

### 수집 진행 상황
http://localhost:4173/collection

### 상품 목록
http://localhost:4173/products

### AI 기반 상품 추천
http://localhost:4173/ai-sourcing

## 문제 해결

### API 서버가 실행되지 않았을 때
```bash
cd simple_collector
python api/main.py
```

### 프론트엔드 서버가 실행되지 않았을 때
```bash
cd simple_collector/frontend
npm run dev
```

### 수집이 실패할 때
1. API 키가 올바른지 확인
2. 인터넷 연결 확인
3. 도매처 서버 상태 확인
4. 로그 파일 확인: `logs/collection.log`

## 자동화 (Windows 작업 스케줄러)

매일 자동 수집을 원한다면:

1. `auto_collect.bat` 파일 생성:
```batch
@echo off
cd /d D:\new\win_with_claude\yooni_03\simple_collector
python collect_all_wholesale.py
python download_wholesale_products.py --all
```

2. Windows 작업 스케줄러에 등록
3. 매일 원하는 시간에 실행 설정

## 주의사항

1. **API 사용 제한**: 각 도매처별로 API 사용 제한이 있을 수 있습니다
2. **대용량 수집**: 상품이 많을 경우 시간이 오래 걸릴 수 있습니다
3. **저장 공간**: 이미지를 포함한 전체 데이터는 상당한 저장 공간이 필요합니다
4. **동시 실행 금지**: 여러 수집을 동시에 실행하지 마세요
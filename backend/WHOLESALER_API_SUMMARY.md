# 도매처 API 연동 요약

## 1. 연동 현황

### ✅ OwnerClan
- **상태**: 부분 성공 (인증 성공, 상품 조회 실패)
- **API 형식**: GraphQL
- **인증 방식**: JWT Bearer Token
- **문제점**: 400 에러 - GraphQL 쿼리 또는 권한 문제로 추정
- **해결 방안**: API 문서 재확인 및 쿼리 수정 필요

### ✅ Zentrade
- **상태**: 부분 성공 (이전에는 성공, 현재 404 에러)
- **API 형식**: XML (EUC-KR 인코딩)
- **인증 방식**: API Key + Secret
- **문제점**: 서버 측 API 엔드포인트 변경 또는 일시적 오류
- **해결 방안**: API 제공업체 문의 필요

### ❌ Domeggook (도매매)
- **상태**: 실패
- **API 형식**: JSON (예상)
- **인증 방식**: API Key
- **문제점**: 
  - API 엔드포인트 404 에러
  - API 키가 활성화되지 않았거나 승인 필요
- **해결 방안**: 
  - 도매매 고객센터 문의
  - API 사용 승인 절차 확인
  - 현재는 샘플 데이터로 대체

## 2. 데이터베이스 현황

### 수집된 상품 현황
```
총 15개 상품 (2025-07-27 기준)
- OwnerClan: 5개 (주얼리)
- Zentrade: 5개 (주방용품)
- Domeggook: 5개 (샘플 데이터 - 의류, 가방, 액세서리 등)
```

### 도매처별 특징
| 도매처 | 평균 가격 | 주력 카테고리 | 총 재고 |
|--------|-----------|---------------|----------|
| OwnerClan | 41,624원 | 주얼리 | 275개 |
| Zentrade | 2,042원 | 주방용품 | 1,400개 |
| Domeggook | 19,700원 | 패션잡화 | 580개 |

## 3. API 연동 코드 위치

### 구현된 API 클라이언트
- `app/services/wholesalers/ownerclan_api.py` - 원본
- `app/services/wholesalers/ownerclan_api_fixed.py` - 수정 버전
- `app/services/wholesalers/domeggook_api.py` - 원본
- `app/services/wholesalers/domeggook_api_fixed.py` - 수정 버전
- `app/services/wholesalers/zentrade_api.py` - 원본

### 테스트 스크립트
- `test_final_apis.py` - 최종 API 테스트
- `test_domeggook_api.py` - 도매매 API 테스트
- `test_domeggook_simple.py` - 도매매 간단 테스트
- `collect_all_wholesalers.py` - 모든 도매처 통합 수집

## 4. 문제 해결 가이드

### OwnerClan 문제 해결
```python
# 현재 문제: 400 Bad Request
# 가능한 원인:
# 1. GraphQL 쿼리 구조 변경
# 2. 필수 필드 누락
# 3. 권한 부족

# 해결 방법:
# 1. 최신 API 문서 확인
# 2. 간단한 쿼리부터 테스트
query { 
  viewer { 
    id 
    email 
  } 
}
```

### Zentrade 문제 해결
```python
# 현재 문제: 404 Not Found
# 가능한 원인:
# 1. API URL 변경
# 2. 서버 점검

# 대체 URL 시도:
# - https://www.zentrade.co.kr/shop/proc/product_api.php
# - http://zentrade.co.kr/api/product_list.php
```

### Domeggook 문제 해결
```
1. 도매매 사이트 로그인
2. 마이페이지 > API 관리
3. API 키 확인 및 활성화 상태 점검
4. API 사용 신청 (필요시)
5. 올바른 엔드포인트 확인:
   - https://openapi.domeggook.com/api/v4.1/
   - 인증 헤더 형식 확인
```

## 5. 샘플 데이터 활용

도매매 API가 작동하지 않을 때 사용할 수 있는 샘플 데이터:
- 파일: `domeggook_sample_data_*.json`
- 카테고리: 의류, 가방, 액세서리, 신발, 화장품
- 각 카테고리별 1개씩 총 5개 상품

## 6. 다음 단계 권장사항

1. **API 안정화**
   - 각 도매처 기술지원팀 문의
   - API 문서 최신 버전 확보
   - 에러 처리 및 재시도 로직 강화

2. **데이터 확장**
   - 더 많은 카테고리 추가
   - 상품 이미지 수집 기능 구현
   - 상품 옵션 정보 처리

3. **자동화 구현**
   - 정기적인 상품 업데이트 스케줄러
   - 재고 변동 실시간 모니터링
   - 가격 변동 추적 시스템

4. **통합 대시보드**
   - 도매처별 상품 현황 시각화
   - 수익성 분석 도구
   - 재고 관리 알림 시스템
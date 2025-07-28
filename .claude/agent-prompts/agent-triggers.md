# Dropshipping Project - Subagent Auto-Trigger Rules

이 문서는 드롭쉬핑 프로젝트에서 Claude Code가 자동으로 서브에이전트를 활용하는 조건을 정의합니다.

## 🚀 General-Purpose Agent 자동 실행 조건

### 1. 파일 검색 범위
- 3개 이상의 파일/디렉토리 검색 필요 시
- "전체", "모든", "시스템 전반" 등의 키워드 포함 시

### 2. 복잡한 비즈니스 로직
**트리거 키워드:**
- "주문 처리 플로우"
- "재고 동기화"
- "가격 계산 로직"
- "도매처 연동"
- "멀티 플랫폼"

**예시:**
```
"주문이 들어왔을 때 전체 처리 과정을 설명해줘"
"모든 도매처에서 상품을 수집하는 로직을 구현해줘"
```

### 3. 시스템 분석
**트리거 패턴:**
- "어떻게 구성되어 있는지"
- "구조 분석"
- "아키텍처 설명"
- "연관된 모든 파일"

## 🔍 Code-Reviewer Agent 자동 실행 조건

### 1. 코드 작성 완료
- 100줄 이상의 새 코드 작성
- 새로운 API 엔드포인트 추가
- 데이터베이스 모델 변경

### 2. 금융 관련 코드
**자동 리뷰 대상:**
- 가격 계산 함수
- 마진 계산 로직
- 결제 처리 코드
- 환불 처리 로직

### 3. 보안 민감 영역
- 인증/인가 코드
- API 키 관리
- 사용자 데이터 처리

## 🧪 Test-Automator Agent 자동 실행 조건

### 1. 새 기능 추가
- 새 서비스 클래스 생성
- 새 API 엔드포인트 추가
- 비즈니스 로직 함수 추가

### 2. 테스트 요청 키워드
- "테스트 작성"
- "테스트 커버리지"
- "E2E 테스트"
- "통합 테스트"

### 3. 버그 수정 후
- 버그 수정 완료 시 회귀 테스트 자동 생성

## 🔒 Security-Auditor Agent 자동 실행 조건

### 1. 보안 키워드
- "보안 검토"
- "취약점 검사"
- "인증", "권한"
- "API 키", "시크릿"

### 2. 민감 파일 수정
- `auth.py`, `security.py` 수정
- 환경 변수 파일 변경
- 인증 미들웨어 수정

## ⚡ Performance-Engineer Agent 자동 실행 조건

### 1. 성능 이슈 키워드
- "느려", "최적화"
- "성능 개선"
- "응답 시간"
- "병목", "bottleneck"

### 2. 대용량 처리
- "대량", "벌크"
- "동시 처리"
- "배치 작업"

## 📊 프로젝트별 특수 트리거

### 도매처 API 작업
```
키워드: "ownerclan", "zentrade", "domeggook"
→ general-purpose + test-automator 자동 실행
```

### 마켓플레이스 작업
```
키워드: "쿠팡", "네이버", "11번가", "marketplace"
→ general-purpose + code-reviewer 자동 실행
```

### 주문 처리 작업
```
키워드: "주문", "order", "결제", "배송"
→ general-purpose + security-auditor + test-automator
```

## 🎯 복합 시나리오 예시

### 시나리오 1: "쿠팡 API 연동이 자꾸 실패해"
```
자동 실행:
1. general-purpose: 에러 원인 분석
2. security-auditor: 인증 문제 확인
3. code-reviewer: 수정 사항 검토
4. test-automator: 통합 테스트 추가
```

### 시나리오 2: "상품 등록 API가 너무 느려"
```
자동 실행:
1. performance-engineer: 병목 지점 분석
2. general-purpose: 최적화 구현
3. test-automator: 성능 테스트 추가
4. code-reviewer: 최종 검토
```

### 시나리오 3: "새로운 도매처 API 추가해줘"
```
자동 실행:
1. general-purpose: 기존 패턴 분석 및 구현
2. test-automator: 통합 테스트 작성
3. security-auditor: API 키 관리 확인
4. code-reviewer: 전체 코드 리뷰
```

## 🔄 연속 작업 패턴

### 개발 → 테스트 → 리뷰
```
1단계: 기능 구현 (general-purpose)
2단계: 테스트 작성 (test-automator)
3단계: 코드 리뷰 (code-reviewer)
4단계: 보안 검토 (security-auditor) - 필요시
```

### 디버깅 → 수정 → 검증
```
1단계: 버그 분석 (general-purpose)
2단계: 수정 구현 (general-purpose)
3단계: 테스트 추가 (test-automator)
4단계: 성능 영향 확인 (performance-engineer)
```

## 💡 효율적인 활용 팁

1. **명시적 요청 우선**: "보안 검토도 해줘"라고 명시하면 해당 에이전트 우선 실행
2. **컨텍스트 제공**: 더 많은 정보를 제공할수록 적절한 에이전트 선택
3. **단계별 접근**: 복잡한 작업은 단계를 나누어 요청

이러한 트리거 규칙에 따라 Claude Code는 자동으로 최적의 서브에이전트를 선택하여 작업을 수행합니다.
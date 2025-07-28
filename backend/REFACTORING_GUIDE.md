# 리팩토링 가이드

## 현재 진행 상황

### 1단계: 백엔드 진입점 통합 ✅
- `main_unified.py` 생성 완료
- 개발/프로덕션 모드를 환경 변수로 제어
- `.env.example` 업데이트

### 사용 방법

#### 개발 모드로 실행
```bash
# .env 파일 설정
APP_MODE=development
APP_PORT=8000

# 실행
python main_unified.py
```

#### 프로덕션 모드로 실행
```bash
# .env 파일 설정
APP_MODE=production
APP_PORT=8000

# 실행
python main_unified.py
```

## 리팩토링 계획

### 2단계: V2 파일 정리 ✅
- [x] config.py와 config_v2.py 통합 - V2 기반으로 통합 완료
- [x] smart_sourcing_engine.py와 v2 통합 - V2를 메인으로 사용
- [x] market_data_collector.py와 v2 통합 - V2를 메인으로 사용
- [x] order_processor_v2.py - 메인으로 사용
- [x] 구 버전 파일을 `legacy/` 디렉토리로 이동

### 3단계: 테스트 구조 정리 ✅
- [x] 루트의 테스트 파일들을 `tests/` 디렉토리로 이동
- [x] 테스트 타입별 분류 (unit/, integration/, e2e/)
- [x] pytest.ini 설정 파일 생성
- [x] conftest.py로 공통 픽스처 정의

### 4단계: 서비스 모듈 통합
- [ ] order_processing과 order_automation 통합
- [ ] dropshipping 관련 모듈 통합
- [ ] 중복 기능 제거

### 5단계: 의존성 관리
- [ ] pyproject.toml로 일원화
- [ ] requirements.txt는 자동 생성
- [ ] 개발/프로덕션 의존성 분리

### 6단계: 마이그레이션 정리
- [ ] 중복된 003 버전 마이그레이션 해결
- [ ] 순차적 버전 번호 재정리
- [ ] 마이그레이션 히스토리 문서화

## 개선 효과

1. **단순화된 시작**: 한 명령으로 개발/프로덕션 모드 실행
2. **명확한 구조**: 중복 제거, 일관된 디렉토리 구조
3. **유지보수성**: 코드 위치 파악 용이
4. **확장성**: 새 기능 추가 위치 명확

## 마이그레이션 전략

### 기존 시스템에서 이전
1. 데이터베이스 백업
2. `.env` 파일을 새 형식으로 업데이트
3. `main_unified.py`로 전환
4. 기능 테스트
5. 기존 main.py, simple_main.py 제거

### 주의사항
- WebSocket 연결 확인
- 프론트엔드 API 엔드포인트 호환성
- 데이터베이스 마이그레이션 순서
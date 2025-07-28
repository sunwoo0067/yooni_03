# 기존 PostgreSQL 사용하기

## 현재 상황

기존 프로젝트(backend)와 새 프로젝트(simple_collector) 모두 PostgreSQL을 사용합니다:

- **기존 backend**: `postgresql://postgres:1234@localhost:5433/yoni_03`
- **새 simple_collector**: `postgresql://postgres:1234@localhost:5433/simple_collector`

## 옵션 1: 같은 데이터베이스 사용 (권장)

기존 yoni_03 데이터베이스를 그대로 사용:

```bash
# .env 파일 수정
DATABASE_URL=postgresql://postgres:1234@localhost:5433/yoni_03
```

### 장점
- 데이터 통합 관리
- 기존 데이터 활용 가능
- 하나의 DB만 관리

### 설정 방법
```python
# config/settings.py 수정
DATABASE_URL: str = "postgresql://postgres:1234@localhost:5433/yoni_03"
```

## 옵션 2: 별도 데이터베이스 사용

simple_collector용 새 데이터베이스 생성:

```bash
# PostgreSQL 접속
psql -U postgres -p 5433 -h localhost

# 데이터베이스 생성
CREATE DATABASE simple_collector;
```

### 장점
- 독립적인 개발/테스트
- 기존 시스템 영향 없음
- 깔끔한 시작

## 현재 PostgreSQL 상태 확인

```bash
# PostgreSQL 실행 중인지 확인
netstat -an | findstr :5433

# psql로 접속 테스트
psql -U postgres -p 5433 -h localhost -d yoni_03

# 비밀번호: 1234
```

## 권장 사항

1. **개발/테스트**: 별도 DB (simple_collector) 사용
2. **프로덕션 통합**: 기존 DB (yoni_03) 사용

현재는 simple_collector DB를 사용하도록 설정되어 있습니다.
# PostgreSQL 설정 가이드

## 1. PostgreSQL 설치 및 실행

### Docker를 사용하는 방법 (권장)
```bash
# PostgreSQL과 pgAdmin 실행
docker-compose up -d

# 실행 확인
docker ps

# 로그 확인
docker-compose logs postgres
```

- PostgreSQL: localhost:5432
- pgAdmin: http://localhost:5050
  - Email: admin@example.com
  - Password: admin

### 로컬 설치 방법
1. PostgreSQL 15 다운로드: https://www.postgresql.org/download/
2. 설치 시 비밀번호: `password`로 설정
3. 포트: 5432 (기본값)

## 2. 환경 설정

### .env 파일 생성
```bash
# .env.example을 복사
cp .env.example .env
```

### .env 파일 편집
```env
# PostgreSQL 연결 정보
DATABASE_URL=postgresql://postgres:password@localhost:5432/simple_collector

# API 키 설정 (선택사항)
ZENTRADE_API_ID=your_api_id
ZENTRADE_API_KEY=your_api_key
# ... 기타 API 키
```

## 3. 데이터베이스 초기화

### 자동 설정 (권장)
```bash
# PostgreSQL 설정 및 마이그레이션
python setup_postgresql.py
```

이 명령은 다음을 수행합니다:
- 데이터베이스 생성
- 테이블 생성
- 기본 데이터 초기화
- SQLite 데이터 마이그레이션 (있는 경우)

### 수동 설정
```bash
# 1. 데이터베이스 생성 (psql 사용)
psql -U postgres -c "CREATE DATABASE simple_collector;"

# 2. Python에서 테이블 생성
python
>>> from database.connection import create_tables
>>> from database.models import init_suppliers
>>> from database.connection import SessionLocal
>>> create_tables()
>>> db = SessionLocal()
>>> init_suppliers(db)
>>> db.close()
```

## 4. 데이터 마이그레이션

### SQLite에서 PostgreSQL로
기존 SQLite 데이터가 있다면 자동으로 마이그레이션됩니다:
```bash
python setup_postgresql.py
```

### 수동 마이그레이션
```bash
# SQLite 데이터 내보내기
python
>>> # SQLite에서 데이터 읽기
>>> # PostgreSQL로 데이터 쓰기
```

## 5. 서버 실행

```bash
# API 서버 실행
python main.py
# 메뉴에서 "2. API 서버 시작" 선택

# 또는 직접 실행
uvicorn api.main:app --reload
```

## 6. 데이터베이스 관리

### pgAdmin 사용
1. http://localhost:5050 접속
2. 서버 추가:
   - Host: postgres (Docker) 또는 localhost (로컬)
   - Port: 5432
   - Username: postgres
   - Password: password

### psql 명령어
```bash
# Docker 환경
docker exec -it simple_collector_db psql -U postgres -d simple_collector

# 로컬 환경
psql -U postgres -d simple_collector

# 유용한 명령어
\dt              # 테이블 목록
\d products      # 테이블 구조
\q               # 종료
```

## 7. 문제 해결

### 연결 오류
```
could not connect to server: Connection refused
```
- PostgreSQL이 실행 중인지 확인
- 포트 5432가 사용 가능한지 확인
- 방화벽 설정 확인

### 인증 오류
```
FATAL: password authentication failed
```
- .env 파일의 비밀번호 확인
- PostgreSQL 사용자 비밀번호 재설정

### Docker 관련
```bash
# 컨테이너 재시작
docker-compose restart postgres

# 데이터 초기화 (주의!)
docker-compose down -v
docker-compose up -d
```

## 8. 성능 최적화

### PostgreSQL 설정 (postgresql.conf)
```
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
```

### 인덱스 추가
```sql
-- 공급사별 조회 최적화
CREATE INDEX idx_products_supplier ON products(supplier);

-- JSON 필드 인덱스 (GIN)
CREATE INDEX idx_products_info ON products USING GIN (product_info);
```

## 9. 백업 및 복구

### 백업
```bash
# Docker
docker exec simple_collector_db pg_dump -U postgres simple_collector > backup.sql

# 로컬
pg_dump -U postgres simple_collector > backup.sql
```

### 복구
```bash
# Docker
docker exec -i simple_collector_db psql -U postgres simple_collector < backup.sql

# 로컬
psql -U postgres simple_collector < backup.sql
```
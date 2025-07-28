#!/bin/bash
set -e

# 데이터베이스 연결 대기
echo "Waiting for database..."
python -c "
import time
import psycopg2
import os
from urllib.parse import urlparse

database_url = os.getenv('DATABASE_URL')
if database_url:
    parsed = urlparse(database_url)
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]
            )
            conn.close()
            print('Database is ready!')
            break
        except psycopg2.OperationalError:
            attempt += 1
            print(f'Database not ready, attempt {attempt}/{max_attempts}')
            time.sleep(2)
    else:
        print('Could not connect to database')
        exit(1)
"

# Redis 연결 대기
echo "Waiting for Redis..."
python -c "
import time
import redis
import os
from urllib.parse import urlparse

redis_url = os.getenv('REDIS_URL')
if redis_url:
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            r = redis.from_url(redis_url)
            r.ping()
            print('Redis is ready!')
            break
        except redis.ConnectionError:
            attempt += 1
            print(f'Redis not ready, attempt {attempt}/{max_attempts}')
            time.sleep(2)
    else:
        print('Could not connect to Redis')
        exit(1)
"

# 데이터베이스 마이그레이션 실행
echo "Running database migrations..."
alembic upgrade head

# 초기 데이터 로드 (있는 경우)
if [ -f "scripts/init_market_guidelines.py" ]; then
    echo "Loading initial data..."
    python scripts/init_market_guidelines.py
fi

# 로그 디렉토리 권한 확인
mkdir -p logs uploads backups
chmod 755 logs uploads backups

echo "Starting application..."
exec "$@"
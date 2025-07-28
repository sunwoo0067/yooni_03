# 멀티 스테이지 빌드를 사용한 프로덕션 이미지
FROM python:3.11-slim as builder

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt requirements-dev.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# 프로덕션 이미지
FROM python:3.11-slim

# 런타임 의존성 설치
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 비루트 사용자 생성
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

# 작업 디렉토리 설정
WORKDIR /app

# 빌더에서 설치한 패키지 복사
COPY --from=builder /root/.local /home/appuser/.local

# 환경 변수 설정
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production

# 필요한 디렉토리 생성
RUN mkdir -p logs uploads backups && \
    chown -R appuser:appgroup logs uploads backups

# 애플리케이션 코드 복사
COPY --chown=appuser:appgroup . .

# 데이터베이스 마이그레이션 준비
RUN chown -R appuser:appgroup alembic/

# 사용자 전환
USER appuser

# 헬스체크 (더 강건한 체크)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# 포트 노출
EXPOSE 8000

# 엔트리포인트 스크립트 생성
COPY --chown=appuser:appgroup docker-entrypoint.sh /docker-entrypoint.sh
USER root
RUN chmod +x /docker-entrypoint.sh
USER appuser

# 엔트리포인트 실행
ENTRYPOINT ["/docker-entrypoint.sh"]

# 기본 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
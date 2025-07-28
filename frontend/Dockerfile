# 멀티 스테이지 빌드를 사용한 React 애플리케이션
FROM node:18-alpine as builder

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사
COPY package*.json ./

# 의존성 설치
RUN npm ci --only=production

# 소스 코드 복사
COPY . .

# 빌드 실행
RUN npm run build

# Nginx를 사용한 프로덕션 이미지
FROM nginx:alpine

# 보안을 위한 비루트 사용자 설정
RUN addgroup -g 1001 -S nodejs && \
    adduser -S reactjs -u 1001

# 빌드된 파일을 Nginx 정적 파일 디렉토리로 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# 커스텀 Nginx 설정 복사
COPY nginx.conf /etc/nginx/nginx.conf

# 포트 노출
EXPOSE 80

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]
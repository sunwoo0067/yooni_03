# SSL 인증서 설정 가이드

이 디렉토리는 SSL 인증서 파일들을 저장하는 곳입니다.

## Let's Encrypt를 사용한 자동 SSL 인증서 설정

### 1. Certbot 설치 및 설정

```bash
# Certbot 설치
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 도메인 인증서 발급
sudo certbot certonly --webroot -w /var/www/certbot -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Nginx 설정과 함께 인증서 발급 (자동 설정)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 2. Docker를 사용한 Certbot 설정

```bash
# 인증서 발급
docker run -it --rm --name certbot \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  -v "/var/www/certbot:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com
```

### 3. 자동 갱신 설정

```bash
# crontab 편집
sudo crontab -e

# 매일 오전 2시에 인증서 갱신 확인
0 2 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx
```

### 4. Docker Compose에서 SSL 설정

docker-compose.yml에 다음 서비스 추가:

```yaml
  certbot:
    image: certbot/certbot
    container_name: certbot
    volumes:
      - ./ssl:/etc/letsencrypt
      - ./nginx/certbot:/var/www/certbot
    command: certonly --webroot -w /var/www/certbot --force-renewal --email admin@yourdomain.com -d yourdomain.com --agree-tos
    profiles:
      - ssl
```

## 필요한 인증서 파일들

운영환경에서는 다음 파일들이 필요합니다:

```
ssl/
├── fullchain.pem      # 인증서 + 중간 인증서
├── privkey.pem        # 개인키
├── chain.pem          # 중간 인증서
└── cert.pem           # 인증서만
```

## 개발환경용 자체 서명 인증서 생성

개발환경에서 테스트용 SSL 인증서를 생성하려면:

```bash
# 개인키 생성
openssl genrsa -out privkey.pem 2048

# 인증서 서명 요청 생성
openssl req -new -key privkey.pem -out cert.csr -subj "/C=KR/ST=Seoul/L=Seoul/O=Development/CN=localhost"

# 자체 서명 인증서 생성
openssl x509 -req -days 365 -in cert.csr -signkey privkey.pem -out cert.pem

# fullchain.pem 생성 (개발환경에서는 cert.pem과 동일)
cp cert.pem fullchain.pem
cp cert.pem chain.pem
```

## 보안 설정

### 1. Diffie-Hellman 파라미터 생성

```bash
openssl dhparam -out dhparam.pem 2048
```

### 2. OCSP Stapling 설정

Nginx 설정에서 OCSP stapling을 활성화하면 SSL 성능이 향상됩니다:

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

## 인증서 모니터링

인증서 만료 모니터링을 위한 스크립트:

```bash
#!/bin/bash
# ssl_check.sh

DOMAIN="yourdomain.com"
DAYS_WARN=30

EXPIRE_DATE=$(echo | openssl s_client -connect ${DOMAIN}:443 -servername ${DOMAIN} 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
EXPIRE_SECONDS=$(date -d "${EXPIRE_DATE}" +%s)
CURRENT_SECONDS=$(date +%s)
DAYS_LEFT=$(( (EXPIRE_SECONDS - CURRENT_SECONDS) / 86400 ))

if [ ${DAYS_LEFT} -lt ${DAYS_WARN} ]; then
    echo "WARNING: SSL certificate for ${DOMAIN} will expire in ${DAYS_LEFT} days"
    # 알림 전송 (Slack, 이메일 등)
fi
```

## 문제 해결

### 인증서 갱신 실패 시

1. 웹 서버가 정상 실행 중인지 확인
2. 방화벽에서 80, 443 포트가 열려있는지 확인
3. DNS 레코드가 올바른지 확인
4. 로그 확인: `/var/log/letsencrypt/letsencrypt.log`

### 권한 문제 해결

```bash
# SSL 디렉토리 권한 설정
sudo chown -R root:root /etc/letsencrypt
sudo chmod -R 644 /etc/letsencrypt
sudo chmod 600 /etc/letsencrypt/archive/*/privkey*.pem
```
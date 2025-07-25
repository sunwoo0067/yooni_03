# 드랍쉬핑 자동화 시스템 운영 가이드

## 📋 목차
1. [일일 운영 체크리스트](#일일-운영-체크리스트)
2. [성과 모니터링](#성과-모니터링)
3. [비용 최적화](#비용-최적화)
4. [보안 관리](#보안-관리)
5. [백업 및 복구](#백업-및-복구)
6. [트러블슈팅](#트러블슈팅)
7. [스케일링 전략](#스케일링-전략)
8. [법적 준수사항](#법적-준수사항)

## ✅ 일일 운영 체크리스트

### 🌅 오전 체크리스트 (9:00-10:00)

#### 1. 시스템 상태 확인
```bash
# 시스템 헬스 체크
python scripts/health_check.py

# 서비스 상태 확인
systemctl status dropshipping-*
docker ps --filter "name=dropshipping"

# 로그 확인
tail -n 100 logs/system.log | grep ERROR
```

#### 2. 데이터베이스 상태 점검
```sql
-- 연결 수 확인
SELECT count(*) FROM pg_stat_activity;

-- 테이블 크기 확인
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 느린 쿼리 확인
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

#### 3. 야간 작업 결과 확인
```python
# scripts/daily_morning_check.py
import asyncio
from src.monitoring.daily_report import DailyReportGenerator

async def morning_check():
    report_gen = DailyReportGenerator()
    
    # 야간 상품 수집 결과
    collection_report = await report_gen.get_collection_summary()
    print(f"수집된 상품: {collection_report['total_products']}개")
    print(f"성공률: {collection_report['success_rate']}%")
    
    # 등록 현황
    registration_report = await report_gen.get_registration_summary()
    print(f"등록된 상품: {registration_report['total_registered']}개")
    
    # 주문 현황
    order_report = await report_gen.get_order_summary()
    print(f"신규 주문: {order_report['new_orders']}건")
    print(f"처리 대기: {order_report['pending_orders']}건")
    
    return {
        'collection': collection_report,
        'registration': registration_report,
        'orders': order_report
    }

if __name__ == "__main__":
    report = asyncio.run(morning_check())
    
    # 이상 상황 알림
    if report['collection']['success_rate'] < 90:
        send_alert("상품 수집 성공률 저하", report['collection'])
    
    if report['orders']['pending_orders'] > 50:
        send_alert("처리 대기 주문 증가", report['orders'])
```

#### 4. 계정 상태 확인
```python
# scripts/account_status_check.py
from src.security.account_manager import AccountManager

async def check_account_status():
    account_manager = AccountManager()
    
    # 각 플랫폼별 계정 상태
    platforms = ['coupang', 'naver', '11st']
    
    for platform in platforms:
        accounts = await account_manager.get_platform_accounts(platform)
        
        for account in accounts:
            status = await account_manager.check_account_health(account['id'])
            
            print(f"{platform} - {account['name']}:")
            print(f"  상태: {status['status']}")
            print(f"  일일 사용량: {status['daily_usage']}/{status['daily_limit']}")
            print(f"  API 응답시간: {status['avg_response_time']}ms")
            
            if status['status'] != 'active':
                send_alert(f"{platform} 계정 문제", status)
```

### 🕐 주간 체크리스트 (월요일 오전)

#### 1. 성과 분석 리포트
```python
# scripts/weekly_performance_analysis.py
from src.performance_analysis.sales_analyzer import SalesAnalyzer
from datetime import datetime, timedelta

async def weekly_analysis():
    analyzer = SalesAnalyzer()
    
    # 지난 주 성과
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    weekly_report = await analyzer.generate_weekly_report(start_date, end_date)
    
    print("=== 주간 성과 리포트 ===")
    print(f"총 매출: {weekly_report['total_revenue']:,}원")
    print(f"순이익: {weekly_report['net_profit']:,}원")
    print(f"ROI: {weekly_report['roi']}%")
    print(f"신규 고객: {weekly_report['new_customers']}명")
    
    # 베스트/워스트 상품
    print("\n=== 베스트 상품 TOP 5 ===")
    for i, product in enumerate(weekly_report['best_products'][:5], 1):
        print(f"{i}. {product['name']} - {product['revenue']:,}원")
    
    print("\n=== 개선 필요 상품 ===")
    for product in weekly_report['underperforming_products']:
        print(f"- {product['name']} (매출: {product['revenue']:,}원)")
    
    return weekly_report
```

#### 2. 재고 관리
```python
# scripts/inventory_management.py
async def inventory_check():
    from src.inventory.stock_manager import StockManager
    
    stock_manager = StockManager()
    
    # 재고 부족 상품
    low_stock = await stock_manager.get_low_stock_products()
    print(f"재고 부족 상품: {len(low_stock)}개")
    
    # 자동 재고 보충
    for product in low_stock:
        if product['auto_reorder']:
            await stock_manager.create_reorder(product['id'])
            print(f"자동 발주: {product['name']}")
    
    # 과재고 상품
    overstock = await stock_manager.get_overstock_products()
    print(f"과재고 상품: {len(overstock)}개")
    
    # 할인 이벤트 제안
    for product in overstock:
        suggested_discount = await stock_manager.suggest_discount(product)
        print(f"할인 제안: {product['name']} - {suggested_discount}% 할인")
```

### 🌙 저녁 체크리스트 (18:00-19:00)

#### 1. 일일 매출 정산
```python
# scripts/daily_settlement.py
async def daily_settlement():
    from src.order_processing.settlement_manager import SettlementManager
    
    settlement_manager = SettlementManager()
    today = datetime.now().date()
    
    # 일일 정산
    daily_summary = await settlement_manager.process_daily_settlement(today)
    
    print("=== 일일 정산 결과 ===")
    print(f"총 주문: {daily_summary['total_orders']}건")
    print(f"총 매출: {daily_summary['total_revenue']:,}원")
    print(f"총 비용: {daily_summary['total_costs']:,}원")
    print(f"순이익: {daily_summary['net_profit']:,}원")
    print(f"이익률: {daily_summary['profit_margin']:.2f}%")
    
    # 플랫폼별 분석
    for platform, data in daily_summary['by_platform'].items():
        print(f"\n{platform}:")
        print(f"  주문: {data['orders']}건")
        print(f"  매출: {data['revenue']:,}원")
        print(f"  수수료: {data['fees']:,}원")
```

#### 2. 내일 스케줄 확인
```python
# scripts/tomorrow_schedule.py
async def check_tomorrow_schedule():
    from src.scheduling.task_scheduler import TaskScheduler
    
    scheduler = TaskScheduler()
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    scheduled_tasks = await scheduler.get_daily_schedule(tomorrow)
    
    print("=== 내일 예정 작업 ===")
    for task in scheduled_tasks:
        print(f"{task['time']} - {task['name']}")
        print(f"  설명: {task['description']}")
        print(f"  예상 소요시간: {task['estimated_duration']}분")
    
    # 리소스 사용량 예측
    resource_forecast = await scheduler.forecast_resource_usage(tomorrow)
    print(f"\n예상 CPU 사용률: {resource_forecast['cpu']}%")
    print(f"예상 메모리 사용률: {resource_forecast['memory']}%")
```

## 📊 성과 모니터링

### 실시간 대시보드 구성

#### KPI 대시보드
```python
# src/monitoring/kpi_dashboard.py
class KPIDashboard:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    async def get_realtime_kpis(self):
        return {
            # 매출 지표
            'revenue': {
                'today': await self.get_daily_revenue(),
                'this_month': await self.get_monthly_revenue(),
                'growth_rate': await self.calculate_growth_rate()
            },
            
            # 운영 지표
            'operations': {
                'active_products': await self.count_active_products(),
                'pending_orders': await self.count_pending_orders(),
                'system_uptime': await self.get_system_uptime(),
                'api_response_time': await self.get_avg_response_time()
            },
            
            # 고객 지표
            'customers': {
                'new_today': await self.count_new_customers_today(),
                'repeat_rate': await self.calculate_repeat_rate(),
                'satisfaction_score': await self.get_satisfaction_score()
            }
        }
    
    async def generate_alerts(self):
        kpis = await self.get_realtime_kpis()
        alerts = []
        
        # 매출 감소 알림
        if kpis['revenue']['growth_rate'] < -10:
            alerts.append({
                'level': 'warning',
                'message': f"매출 성장률 {kpis['revenue']['growth_rate']}% 감소"
            })
        
        # 시스템 성능 알림
        if kpis['operations']['api_response_time'] > 2000:
            alerts.append({
                'level': 'critical',
                'message': f"API 응답시간 {kpis['operations']['api_response_time']}ms 초과"
            })
        
        return alerts
```

#### 매출 트래킹
```python
# src/monitoring/revenue_tracker.py
class RevenueTracker:
    def __init__(self):
        self.db = DatabaseManager()
    
    async def track_hourly_revenue(self):
        """시간별 매출 추적"""
        query = """
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            SUM(total_amount) as revenue,
            COUNT(*) as order_count
        FROM orders 
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY hour
        ORDER BY hour
        """
        
        return await self.db.fetch_all(query)
    
    async def compare_with_last_week(self):
        """전주 동일 시간대 비교"""
        today_revenue = await self.get_today_revenue()
        last_week_revenue = await self.get_last_week_same_day_revenue()
        
        growth_rate = ((today_revenue - last_week_revenue) / last_week_revenue) * 100
        
        return {
            'today': today_revenue,
            'last_week': last_week_revenue,
            'growth_rate': growth_rate,
            'trend': 'up' if growth_rate > 0 else 'down'
        }
```

### 알림 시스템

#### 텔레그램 알림
```python
# src/monitoring/telegram_notifier.py
import asyncio
import aiohttp

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_daily_report(self, report_data):
        message = f"""
📊 **일일 운영 리포트**
📅 {report_data['date']}

💰 **매출 현황**
• 오늘 매출: {report_data['revenue']:,}원
• 주문 수: {report_data['orders']}건
• 평균 주문액: {report_data['avg_order']:,}원

📦 **상품 현황**
• 활성 상품: {report_data['active_products']}개
• 신규 등록: {report_data['new_products']}개
• 재고 부족: {report_data['low_stock']}개

⚠️ **주의사항**
{chr(10).join(f"• {alert}" for alert in report_data['alerts'])}
        """
        
        await self.send_message(message)
    
    async def send_alert(self, level, title, details):
        emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        
        message = f"""
{emoji.get(level, 'ℹ️')} **{title}**

{details}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self.send_message(message)
    
    async def send_message(self, text):
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=data)
```

#### 이메일 알림
```python
# src/monitoring/email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailNotifier:
    def __init__(self, smtp_config):
        self.smtp_config = smtp_config
    
    async def send_weekly_report(self, recipients, report_data):
        html_content = self.generate_html_report(report_data)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"주간 드랍쉬핑 성과 리포트 - {report_data['week']}"
        msg['From'] = self.smtp_config['from_email']
        msg['To'] = ', '.join(recipients)
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            server.send_message(msg)
    
    def generate_html_report(self, data):
        return f"""
        <html>
        <body>
            <h1>주간 성과 리포트</h1>
            <h2>매출 현황</h2>
            <p>총 매출: {data['revenue']:,}원</p>
            <p>성장률: {data['growth_rate']}%</p>
            
            <h2>베스트 상품</h2>
            <ul>
            {''.join(f"<li>{product['name']} - {product['revenue']:,}원</li>" 
                    for product in data['best_products'])}
            </ul>
        </body>
        </html>
        """
```

## 💰 비용 최적화

### 서버 비용 최적화

#### 자동 스케일링
```python
# src/optimization/auto_scaler.py
class AutoScaler:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.cloud_provider = CloudProviderManager()
    
    async def monitor_and_scale(self):
        """리소스 사용량 모니터링 및 자동 스케일링"""
        while True:
            metrics = await self.metrics_collector.get_current_metrics()
            
            # CPU 사용률 기반 스케일링
            if metrics['cpu_usage'] > 80:
                await self.scale_up()
            elif metrics['cpu_usage'] < 30:
                await self.scale_down()
            
            # 메모리 사용률 체크
            if metrics['memory_usage'] > 85:
                await self.add_memory()
            
            await asyncio.sleep(300)  # 5분마다 체크
    
    async def schedule_cost_optimization(self):
        """비용 최적화 스케줄링"""
        # 야간 시간대 리소스 축소
        if 1 <= datetime.now().hour <= 6:
            await self.scale_down_for_night()
        
        # 주말 리소스 조정
        if datetime.now().weekday() in [5, 6]:
            await self.weekend_optimization()
```

#### 클라우드 비용 관리
```python
# src/optimization/cost_manager.py
class CloudCostManager:
    def __init__(self):
        self.aws_client = boto3.client('ce')  # Cost Explorer
    
    async def get_daily_costs(self, days=7):
        """일일 비용 추적"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        response = self.aws_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(start_date),
                'End': str(end_date)
            },
            Granularity='DAILY',
            Metrics=['BlendedCost']
        )
        
        return response['ResultsByTime']
    
    async def optimize_storage_costs(self):
        """스토리지 비용 최적화"""
        # 오래된 로그 파일 아카이브
        old_logs = await self.find_old_log_files()
        for log_file in old_logs:
            await self.archive_to_glacier(log_file)
        
        # 사용하지 않는 이미지 정리
        unused_images = await self.find_unused_images()
        for image in unused_images:
            await self.delete_image(image)
```

### API 비용 최적화

#### API 호출 최적화
```python
# src/optimization/api_optimizer.py
class APIOptimizer:
    def __init__(self):
        self.cache = Redis()
        self.call_tracker = APICallTracker()
    
    async def optimize_ai_calls(self):
        """AI API 호출 최적화"""
        # 배치 처리로 비용 절감
        pending_requests = await self.get_pending_ai_requests()
        
        if len(pending_requests) >= 10:
            # 10개 이상 쌓이면 배치 처리
            await self.process_batch_ai_requests(pending_requests)
        
    async def implement_smart_caching(self):
        """스마트 캐싱 전략"""
        # 상품 정보 캐싱 (24시간)
        # 이미지 처리 결과 캐싱 (7일)
        # AI 분석 결과 캐싱 (6시간)
        
        cache_strategies = {
            'product_info': {'ttl': 86400, 'compress': True},
            'image_processing': {'ttl': 604800, 'compress': True},
            'ai_analysis': {'ttl': 21600, 'compress': False}
        }
        
        for key_type, strategy in cache_strategies.items():
            await self.optimize_cache_strategy(key_type, strategy)
```

#### 비용 모니터링
```python
# src/optimization/cost_monitor.py
class CostMonitor:
    def __init__(self):
        self.cost_tracker = CostTracker()
    
    async def generate_cost_report(self):
        """비용 리포트 생성"""
        costs = await self.cost_tracker.get_monthly_costs()
        
        report = {
            'total_cost': costs['total'],
            'breakdown': {
                'server': costs['server'],
                'ai_api': costs['ai_api'],
                'storage': costs['storage'],
                'bandwidth': costs['bandwidth']
            },
            'optimization_suggestions': await self.get_optimization_suggestions(costs)
        }
        
        return report
    
    async def set_cost_alerts(self):
        """비용 알림 설정"""
        monthly_budget = 500000  # 월 50만원 예산
        
        current_cost = await self.get_current_monthly_cost()
        
        if current_cost > monthly_budget * 0.8:
            await self.send_budget_alert(current_cost, monthly_budget)
        
        # 일일 비용이 급증한 경우
        daily_cost = await self.get_daily_cost()
        avg_daily_cost = await self.get_avg_daily_cost()
        
        if daily_cost > avg_daily_cost * 1.5:
            await self.send_spike_alert(daily_cost, avg_daily_cost)
```

## 🔐 보안 관리

### 접근 제어

#### 다중 인증 시스템
```python
# src/security/mfa_manager.py
class MFAManager:
    def __init__(self):
        self.totp = pyotp.TOTP
        self.db = DatabaseManager()
    
    async def setup_mfa_for_user(self, user_id):
        """사용자 MFA 설정"""
        secret = pyotp.random_base32()
        
        # QR 코드 생성
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=f"user_{user_id}",
            issuer_name="Dropshipping System"
        )
        
        qr_code = self.generate_qr_code(totp_uri)
        
        # 비밀키 저장 (암호화)
        await self.store_encrypted_secret(user_id, secret)
        
        return qr_code
    
    async def verify_mfa_token(self, user_id, token):
        """MFA 토큰 검증"""
        secret = await self.get_user_secret(user_id)
        totp = pyotp.TOTP(secret)
        
        return totp.verify(token, valid_window=1)
```

#### IP 화이트리스트 관리
```python
# src/security/ip_manager.py
class IPWhitelistManager:
    def __init__(self):
        self.redis = Redis()
        self.db = DatabaseManager()
    
    async def add_trusted_ip(self, ip_address, description):
        """신뢰할 수 있는 IP 추가"""
        await self.db.execute(
            "INSERT INTO trusted_ips (ip_address, description, created_at) VALUES (?, ?, ?)",
            ip_address, description, datetime.now()
        )
        
        # Redis에 캐시
        await self.redis.sadd("trusted_ips", ip_address)
    
    async def check_ip_access(self, ip_address):
        """IP 접근 권한 확인"""
        # Redis에서 빠른 확인
        is_trusted = await self.redis.sismember("trusted_ips", ip_address)
        
        if not is_trusted:
            # 의심스러운 접근 로깅
            await self.log_suspicious_access(ip_address)
            return False
        
        return True
```

### 데이터 암호화

#### 민감정보 암호화
```python
# src/security/encryption_manager.py
from cryptography.fernet import Fernet
import base64

class EncryptionManager:
    def __init__(self):
        self.key = self.load_or_generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_sensitive_data(self, data):
        """민감 데이터 암호화"""
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data):
        """민감 데이터 복호화"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    async def rotate_encryption_key(self):
        """암호화 키 로테이션"""
        old_key = self.key
        new_key = Fernet.generate_key()
        
        # 모든 암호화된 데이터 재암호화
        await self.reencrypt_all_data(old_key, new_key)
        
        self.key = new_key
        self.cipher = Fernet(new_key)
```

### 보안 모니터링

#### 침입 탐지 시스템
```python
# src/security/intrusion_detection.py
class IntrusionDetectionSystem:
    def __init__(self):
        self.failed_attempts = defaultdict(int)
        self.suspicious_patterns = []
    
    async def monitor_login_attempts(self):
        """로그인 시도 모니터링"""
        while True:
            failed_logins = await self.get_recent_failed_logins()
            
            for attempt in failed_logins:
                ip = attempt['ip_address']
                self.failed_attempts[ip] += 1
                
                # 5회 이상 실패시 IP 차단
                if self.failed_attempts[ip] >= 5:
                    await self.block_ip(ip)
                    await self.send_security_alert(f"IP {ip} 차단됨 - 반복 로그인 실패")
            
            await asyncio.sleep(60)
    
    async def detect_unusual_activity(self):
        """비정상 활동 탐지"""
        # API 호출 패턴 분석
        api_calls = await self.get_recent_api_calls()
        
        for user_id, calls in api_calls.items():
            if len(calls) > 1000:  # 시간당 1000회 이상 호출
                await self.flag_suspicious_user(user_id)
            
            # 비정상적인 시간대 접근
            night_calls = [c for c in calls if 2 <= c.hour <= 5]
            if len(night_calls) > 50:
                await self.flag_night_activity(user_id)
```

## 💾 백업 및 복구

### 자동 백업 시스템

#### 데이터베이스 백업
```bash
#!/bin/bash
# scripts/backup_database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
DB_NAME="dropshipping_db"

# PostgreSQL 덤프
pg_dump $DB_NAME > "$BACKUP_DIR/db_backup_$DATE.sql"

# 압축
gzip "$BACKUP_DIR/db_backup_$DATE.sql"

# S3에 업로드
aws s3 cp "$BACKUP_DIR/db_backup_$DATE.sql.gz" s3://dropshipping-backups/database/

# 로컬 파일 7일 후 삭제
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# 백업 결과 로깅
if [ $? -eq 0 ]; then
    echo "$(date): 데이터베이스 백업 성공 - $DATE" >> /var/log/backup.log
else
    echo "$(date): 데이터베이스 백업 실패" >> /var/log/backup.log
    # 알림 발송
    python /scripts/send_backup_alert.py "database_backup_failed"
fi
```

#### 파일 시스템 백업
```python
# src/backup/file_backup_manager.py
import boto3
import os
from datetime import datetime

class FileBackupManager:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'dropshipping-file-backups'
    
    async def backup_critical_files(self):
        """중요 파일 백업"""
        critical_paths = [
            'config/',
            'logs/',
            'uploads/product_images/',
            'data/cache/',
            '.env'
        ]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for path in critical_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    await self.backup_single_file(path, timestamp)
                else:
                    await self.backup_directory(path, timestamp)
    
    async def backup_single_file(self, file_path, timestamp):
        """단일 파일 백업"""
        s3_key = f"files/{timestamp}/{file_path}"
        
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            print(f"백업 완료: {file_path} -> {s3_key}")
        except Exception as e:
            print(f"백업 실패: {file_path} - {str(e)}")
    
    async def backup_directory(self, dir_path, timestamp):
        """디렉토리 백업"""
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path)
                await self.backup_single_file(relative_path, timestamp)
```

### 복구 절차

#### 데이터베이스 복구
```python
# src/backup/recovery_manager.py
class RecoveryManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.s3_client = boto3.client('s3')
    
    async def restore_database(self, backup_date):
        """데이터베이스 복구"""
        print(f"데이터베이스 복구 시작: {backup_date}")
        
        # 1. 백업 파일 다운로드
        backup_file = f"db_backup_{backup_date}.sql.gz"
        s3_key = f"database/{backup_file}"
        
        self.s3_client.download_file(
            'dropshipping-backups', 
            s3_key, 
            f"/tmp/{backup_file}"
        )
        
        # 2. 압축 해제
        os.system(f"gunzip /tmp/{backup_file}")
        
        # 3. 현재 데이터베이스 백업 (안전장치)
        current_backup = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        os.system(f"pg_dump dropshipping_db > /tmp/{current_backup}")
        
        # 4. 데이터베이스 복구
        sql_file = f"/tmp/db_backup_{backup_date}.sql"
        restore_command = f"psql dropshipping_db < {sql_file}"
        
        result = os.system(restore_command)
        
        if result == 0:
            print("데이터베이스 복구 완료")
            return True
        else:
            print("데이터베이스 복구 실패")
            # 원본 상태로 롤백
            os.system(f"psql dropshipping_db < /tmp/{current_backup}")
            return False
    
    async def restore_files(self, backup_timestamp):
        """파일 시스템 복구"""
        print(f"파일 복구 시작: {backup_timestamp}")
        
        # S3에서 백업 파일 목록 조회
        response = self.s3_client.list_objects_v2(
            Bucket='dropshipping-file-backups',
            Prefix=f'files/{backup_timestamp}/'
        )
        
        for obj in response.get('Contents', []):
            s3_key = obj['Key']
            local_path = s3_key.replace(f'files/{backup_timestamp}/', '')
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 파일 다운로드
            self.s3_client.download_file(
                'dropshipping-file-backups',
                s3_key,
                local_path
            )
            
            print(f"복구 완료: {local_path}")
```

#### 재해 복구 계획
```python
# src/backup/disaster_recovery.py
class DisasterRecoveryPlan:
    def __init__(self):
        self.recovery_steps = [
            self.assess_damage,
            self.restore_critical_services,
            self.restore_database,
            self.restore_files,
            self.verify_integrity,
            self.resume_operations
        ]
    
    async def execute_recovery_plan(self):
        """재해 복구 계획 실행"""
        print("=== 재해 복구 계획 실행 시작 ===")
        
        for step_num, step_func in enumerate(self.recovery_steps, 1):
            print(f"Step {step_num}: {step_func.__name__}")
            
            try:
                success = await step_func()
                if not success:
                    print(f"Step {step_num} 실패 - 복구 중단")
                    return False
                print(f"Step {step_num} 완료")
            except Exception as e:
                print(f"Step {step_num} 오류: {str(e)}")
                return False
        
        print("=== 재해 복구 계획 완료 ===")
        return True
    
    async def assess_damage(self):
        """피해 상황 평가"""
        # 시스템 상태 확인
        # 데이터 무결성 확인
        # 복구 우선순위 결정
        return True
    
    async def restore_critical_services(self):
        """핵심 서비스 복구"""
        # 데이터베이스 서버 시작
        # 웹 서버 시작
        # 캐시 서버 시작
        return True
```

## 🚀 스케일링 전략

### 수평적 확장

#### 마이크로서비스 분리
```python
# src/scaling/service_splitter.py
class ServiceSplitter:
    def __init__(self):
        self.services = {
            'product_collection': ['gentrade', 'ownersclan', 'domemegguk'],
            'ai_processing': ['analysis', 'naming', 'optimization'],
            'marketplace_api': ['coupang', 'naver', '11st'],
            'order_processing': ['monitoring', 'fulfillment', 'tracking']
        }
    
    async def split_services(self):
        """서비스 분리 및 배포"""
        for service_name, components in self.services.items():
            await self.create_service_container(service_name, components)
            await self.setup_load_balancer(service_name)
            await self.configure_auto_scaling(service_name)
    
    async def create_service_container(self, service_name, components):
        """서비스 컨테이너 생성"""
        dockerfile_content = self.generate_dockerfile(service_name, components)
        
        with open(f"docker/{service_name}/Dockerfile", 'w') as f:
            f.write(dockerfile_content)
        
        # Docker 이미지 빌드 및 배포
        build_command = f"docker build -t {service_name}:latest docker/{service_name}/"
        os.system(build_command)
```

#### 로드 밸런싱
```python
# src/scaling/load_balancer.py
class LoadBalancer:
    def __init__(self):
        self.servers = {}
        self.health_checker = HealthChecker()
    
    async def distribute_requests(self, service_name, request):
        """요청 분산"""
        available_servers = await self.get_healthy_servers(service_name)
        
        if not available_servers:
            raise Exception(f"No healthy servers for {service_name}")
        
        # 라운드 로빈 방식
        server = self.select_server_round_robin(available_servers)
        
        # 서버 부하 고려
        if server['load'] > 80:
            server = self.select_least_loaded_server(available_servers)
        
        return await self.forward_request(server, request)
    
    async def auto_scale_servers(self, service_name):
        """자동 서버 확장"""
        metrics = await self.get_service_metrics(service_name)
        
        if metrics['avg_cpu'] > 70 and metrics['avg_memory'] > 80:
            await self.add_server_instance(service_name)
        
        elif metrics['avg_cpu'] < 20 and metrics['avg_memory'] < 30:
            await self.remove_server_instance(service_name)
```

### 수직적 확장

#### 리소스 모니터링
```python
# src/scaling/resource_monitor.py
class ResourceMonitor:
    def __init__(self):
        self.thresholds = {
            'cpu': {'scale_up': 80, 'scale_down': 20},
            'memory': {'scale_up': 85, 'scale_down': 30},
            'disk': {'scale_up': 90, 'scale_down': 50}
        }
    
    async def monitor_resources(self):
        """리소스 모니터링"""
        while True:
            resources = await self.get_current_resources()
            
            for resource_type, usage in resources.items():
                await self.check_scaling_needs(resource_type, usage)
            
            await asyncio.sleep(300)  # 5분마다 체크
    
    async def check_scaling_needs(self, resource_type, usage):
        """스케일링 필요성 확인"""
        thresholds = self.thresholds[resource_type]
        
        if usage > thresholds['scale_up']:
            await self.trigger_scale_up(resource_type)
        elif usage < thresholds['scale_down']:
            await self.trigger_scale_down(resource_type)
```

## ⚖️ 법적 준수사항

### 개인정보보호

#### GDPR 준수
```python
# src/compliance/gdpr_manager.py
class GDPRComplianceManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.encryption = EncryptionManager()
    
    async def handle_data_request(self, user_id, request_type):
        """개인정보 요청 처리"""
        if request_type == "access":
            return await self.provide_user_data(user_id)
        elif request_type == "deletion":
            return await self.delete_user_data(user_id)
        elif request_type == "portability":
            return await self.export_user_data(user_id)
    
    async def anonymize_old_data(self):
        """오래된 데이터 익명화"""
        cutoff_date = datetime.now() - timedelta(days=730)  # 2년
        
        # 개인정보 익명화
        await self.db.execute("""
            UPDATE customers 
            SET name = 'ANONYMIZED', 
                email = CONCAT('anon_', id, '@example.com'),
                phone = NULL,
                address = NULL
            WHERE created_at < %s
        """, cutoff_date)
```

### 전자상거래법 준수

#### 표시광고법 준수
```python
# src/compliance/advertising_compliance.py
class AdvertisingComplianceChecker:
    def __init__(self):
        self.prohibited_terms = [
            "100% 효과", "즉시 효과", "부작용 없음",
            "세계 최초", "세계 유일", "완치"
        ]
    
    async def check_product_description(self, description):
        """상품 설명 준수성 검사"""
        violations = []
        
        for term in self.prohibited_terms:
            if term in description:
                violations.append(f"금지 용어 사용: {term}")
        
        # 과장 광고 탐지
        if self.detect_exaggeration(description):
            violations.append("과장 광고 의심")
        
        return {
            'compliant': len(violations) == 0,
            'violations': violations
        }
    
    def detect_exaggeration(self, text):
        """과장 광고 탐지"""
        exaggeration_patterns = [
            r'\d+%\s*효과',
            r'즉시|바로|당장',
            r'최고|최대|최상'
        ]
        
        for pattern in exaggeration_patterns:
            if re.search(pattern, text):
                return True
        
        return False
```

### 세금 관리

#### 부가가치세 계산
```python
# src/compliance/tax_manager.py
class TaxManager:
    def __init__(self):
        self.vat_rate = 0.10  # 10%
        self.db = DatabaseManager()
    
    async def calculate_monthly_vat(self, year, month):
        """월별 부가가치세 계산"""
        sales_data = await self.get_monthly_sales(year, month)
        purchase_data = await self.get_monthly_purchases(year, month)
        
        sales_vat = sum(sale['amount'] * self.vat_rate for sale in sales_data)
        purchase_vat = sum(purchase['amount'] * self.vat_rate for purchase in purchase_data)
        
        net_vat = sales_vat - purchase_vat
        
        return {
            'sales_vat': sales_vat,
            'purchase_vat': purchase_vat,
            'net_vat': net_vat,
            'payment_due': max(0, net_vat)
        }
    
    async def generate_tax_report(self, quarter):
        """분기별 세무 보고서 생성"""
        months = self.get_quarter_months(quarter)
        quarterly_data = {}
        
        for month in months:
            monthly_vat = await self.calculate_monthly_vat(2024, month)
            quarterly_data[f"month_{month}"] = monthly_vat
        
        return self.format_tax_report(quarterly_data)
```

이 운영 가이드를 통해 드랍쉬핑 자동화 시스템을 안정적이고 효율적으로 운영할 수 있습니다. 정기적인 모니터링과 최적화를 통해 지속적인 성장을 달성하시기 바랍니다.
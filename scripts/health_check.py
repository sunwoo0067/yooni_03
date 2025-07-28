#!/usr/bin/env python3
"""
시스템 헬스 체크 스크립트
배포 후 또는 주기적으로 시스템 상태를 점검
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
import psycopg2
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import subprocess

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthChecker:
    """헬스 체크 관리 클래스"""
    
    def __init__(self, config_file: str = 'health_check_config.json'):
        self.config = self.load_config(config_file)
        self.results = {}
        self.start_time = datetime.now()
    
    def load_config(self, config_file: str) -> Dict:
        """헬스 체크 설정 로드"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일 {config_file}을 찾을 수 없습니다. 기본값을 사용합니다.")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """기본 헬스 체크 설정"""
        return {
            "endpoints": {
                "api_health": {
                    "url": "http://localhost:8000/health",
                    "timeout": 30,
                    "expected_status": 200,
                    "expected_response": {"status": "healthy"}
                },
                "frontend": {
                    "url": "http://localhost:3000/health",
                    "timeout": 30,
                    "expected_status": 200
                },
                "api_status": {
                    "url": "http://localhost:8000/api/v1/system/status",
                    "timeout": 30,
                    "expected_status": 200
                }
            },
            "database": {
                "url": os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname"),
                "timeout": 10,
                "test_query": "SELECT 1",
                "check_tables": ["users", "products", "orders"]
            },
            "redis": {
                "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                "timeout": 5,
                "test_key": "health_check_test"
            },
            "docker": {
                "check_containers": True,
                "required_containers": [
                    "dropshipping_backend",
                    "dropshipping_frontend", 
                    "dropshipping_db",
                    "dropshipping_redis"
                ]
            },
            "system": {
                "check_disk_space": True,
                "disk_threshold": 80,  # 80% 이상 시 경고
                "check_memory": True,
                "memory_threshold": 85,  # 85% 이상 시 경고
                "check_load": True,
                "load_threshold": 2.0  # Load average 2.0 이상 시 경고
            },
            "thresholds": {
                "response_time_warning": 1000,  # ms
                "response_time_critical": 5000,  # ms
                "error_rate_warning": 0.01,  # 1%
                "error_rate_critical": 0.05   # 5%
            },
            "notifications": {
                "slack_webhook": os.getenv("SLACK_WEBHOOK"),
                "email_enabled": False,
                "notify_on_warning": True,
                "notify_on_critical": True
            }
        }
    
    def check_http_endpoint(self, name: str, config: Dict) -> Tuple[bool, Dict]:
        """HTTP 엔드포인트 헬스 체크"""
        logger.info(f"HTTP 엔드포인트 체크: {name}")
        
        result = {
            "name": name,
            "type": "http",
            "status": "unknown",
            "response_time": None,
            "status_code": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            start_time = time.time()
            response = requests.get(
                config['url'],
                timeout=config.get('timeout', 30),
                verify=False  # SSL 검증 비활성화 (개발환경용)
            )
            response_time = (time.time() - start_time) * 1000  # ms
            
            result["response_time"] = response_time
            result["status_code"] = response.status_code
            
            # 상태 코드 확인
            expected_status = config.get('expected_status', 200)
            if response.status_code != expected_status:
                result["status"] = "critical"
                result["error"] = f"Unexpected status code: {response.status_code}"
                return False, result
            
            # 응답 내용 확인 (있는 경우)
            if 'expected_response' in config:
                try:
                    response_json = response.json()
                    expected = config['expected_response']
                    for key, value in expected.items():
                        if response_json.get(key) != value:
                            result["status"] = "warning"
                            result["error"] = f"Unexpected response: {key}={response_json.get(key)}"
                            break
                except Exception as e:
                    result["status"] = "warning"
                    result["error"] = f"Failed to parse JSON response: {e}"
            
            # 응답 시간 평가
            warning_threshold = self.config['thresholds']['response_time_warning']
            critical_threshold = self.config['thresholds']['response_time_critical']
            
            if response_time > critical_threshold:
                result["status"] = "critical"
            elif response_time > warning_threshold:
                result["status"] = "warning"
            else:
                result["status"] = "healthy"
            
            return result["status"] in ["healthy", "warning"], result
            
        except requests.exceptions.Timeout:
            result["status"] = "critical"
            result["error"] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result["status"] = "critical"
            result["error"] = "Connection error"
        except Exception as e:
            result["status"] = "critical"
            result["error"] = str(e)
        
        return False, result
    
    def check_database(self) -> Tuple[bool, Dict]:
        """데이터베이스 헬스 체크"""
        logger.info("데이터베이스 체크")
        
        result = {
            "name": "database",
            "type": "database", 
            "status": "unknown",
            "response_time": None,
            "error": None,
            "table_checks": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            db_config = self.config['database']
            start_time = time.time()
            
            # 데이터베이스 연결 테스트
            conn = psycopg2.connect(
                db_config['url'],
                connect_timeout=db_config.get('timeout', 10)
            )
            
            with conn.cursor() as cursor:
                # 기본 쿼리 테스트
                cursor.execute(db_config.get('test_query', 'SELECT 1'))
                cursor.fetchone()
                
                # 테이블 존재 확인
                check_tables = db_config.get('check_tables', [])
                for table in check_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} LIMIT 1")
                        count = cursor.fetchone()[0]
                        result["table_checks"][table] = {"exists": True, "count": count}
                    except Exception as e:
                        result["table_checks"][table] = {"exists": False, "error": str(e)}
            
            conn.close()
            
            response_time = (time.time() - start_time) * 1000
            result["response_time"] = response_time
            result["status"] = "healthy"
            
            return True, result
            
        except psycopg2.OperationalError as e:
            result["status"] = "critical"
            result["error"] = f"Database connection error: {e}"
        except Exception as e:
            result["status"] = "critical"
            result["error"] = str(e)
        
        return False, result
    
    def check_redis(self) -> Tuple[bool, Dict]:
        """Redis 헬스 체크"""
        logger.info("Redis 체크")
        
        result = {
            "name": "redis",
            "type": "redis",
            "status": "unknown",
            "response_time": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            redis_config = self.config['redis']
            start_time = time.time()
            
            # Redis 연결
            r = redis.from_url(
                redis_config['url'],
                socket_timeout=redis_config.get('timeout', 5)
            )
            
            # 기본 연결 테스트
            r.ping()
            
            # 쓰기/읽기 테스트
            test_key = redis_config.get('test_key', 'health_check_test')
            test_value = f"health_check_{int(time.time())}"
            
            r.set(test_key, test_value, ex=60)  # 60초 후 만료
            retrieved_value = r.get(test_key)
            
            if retrieved_value.decode() != test_value:
                raise Exception("Redis read/write test failed")
            
            r.delete(test_key)  # 정리
            
            response_time = (time.time() - start_time) * 1000
            result["response_time"] = response_time
            result["status"] = "healthy"
            
            return True, result
            
        except redis.ConnectionError as e:
            result["status"] = "critical"
            result["error"] = f"Redis connection error: {e}"
        except Exception as e:
            result["status"] = "critical"
            result["error"] = str(e)
        
        return False, result
    
    def check_docker_containers(self) -> Tuple[bool, Dict]:
        """Docker 컨테이너 상태 체크"""
        logger.info("Docker 컨테이너 체크")
        
        result = {
            "name": "docker_containers",
            "type": "docker",
            "status": "unknown",
            "containers": {},
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        if not self.config['docker']['check_containers']:
            result["status"] = "skipped"
            return True, result
        
        try:
            # docker ps 명령으로 컨테이너 상태 확인
            cmd_result = subprocess.run(
                ['docker', 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            running_containers = []
            for line in cmd_result.stdout.strip().split('\n'):
                if line:
                    container_info = json.loads(line)
                    running_containers.append(container_info['Names'])
            
            # 필수 컨테이너 확인
            required_containers = self.config['docker']['required_containers']
            all_healthy = True
            
            for container_name in required_containers:
                if container_name in running_containers:
                    # 개별 컨테이너 헬스 체크
                    try:
                        health_cmd = subprocess.run(
                            ['docker', 'inspect', '--format', '{{.State.Health.Status}}', container_name],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        health_status = health_cmd.stdout.strip()
                        
                        if health_status == 'healthy' or health_status == '':
                            result["containers"][container_name] = {"status": "healthy", "running": True}
                        else:
                            result["containers"][container_name] = {"status": health_status, "running": True}
                            if health_status != 'starting':
                                all_healthy = False
                    except subprocess.CalledProcessError:
                        # 헬스체크가 정의되지 않은 컨테이너
                        result["containers"][container_name] = {"status": "unknown", "running": True}
                else:
                    result["containers"][container_name] = {"status": "not_running", "running": False}
                    all_healthy = False
            
            result["status"] = "healthy" if all_healthy else "critical"
            return all_healthy, result
            
        except subprocess.CalledProcessError as e:
            result["status"] = "critical"
            result["error"] = f"Docker command failed: {e}"
        except Exception as e:
            result["status"] = "critical"
            result["error"] = str(e)
        
        return False, result
    
    def check_system_resources(self) -> Tuple[bool, Dict]:
        """시스템 리소스 체크"""
        logger.info("시스템 리소스 체크")
        
        result = {
            "name": "system_resources",
            "type": "system",
            "status": "healthy",
            "disk_usage": {},
            "memory_usage": {},
            "load_average": {},
            "warnings": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            system_config = self.config['system']
            is_healthy = True
            
            # 디스크 사용량 체크
            if system_config.get('check_disk_space', True):
                disk_result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
                if disk_result.returncode == 0:
                    lines = disk_result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        usage_percent = int(parts[4].rstrip('%'))
                        result["disk_usage"] = {
                            "total": parts[1],
                            "used": parts[2],
                            "available": parts[3],
                            "usage_percent": usage_percent
                        }
                        
                        threshold = system_config.get('disk_threshold', 80)
                        if usage_percent > threshold:
                            result["warnings"].append(f"Disk usage is {usage_percent}% (threshold: {threshold}%)")
                            is_healthy = False
            
            # 메모리 사용량 체크
            if system_config.get('check_memory', True):
                mem_result = subprocess.run(['free', '-m'], capture_output=True, text=True)
                if mem_result.returncode == 0:
                    lines = mem_result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        total = int(parts[1])
                        used = int(parts[2])
                        usage_percent = (used / total) * 100
                        
                        result["memory_usage"] = {
                            "total_mb": total,
                            "used_mb": used,
                            "usage_percent": round(usage_percent, 1)
                        }
                        
                        threshold = system_config.get('memory_threshold', 85)
                        if usage_percent > threshold:
                            result["warnings"].append(f"Memory usage is {usage_percent:.1f}% (threshold: {threshold}%)")
                            is_healthy = False
            
            # Load Average 체크
            if system_config.get('check_load', True):
                with open('/proc/loadavg', 'r') as f:
                    load_data = f.read().strip().split()
                    load_1min = float(load_data[0])
                    load_5min = float(load_data[1])
                    load_15min = float(load_data[2])
                    
                    result["load_average"] = {
                        "1min": load_1min,
                        "5min": load_5min,
                        "15min": load_15min
                    }
                    
                    threshold = system_config.get('load_threshold', 2.0)
                    if load_1min > threshold:
                        result["warnings"].append(f"Load average (1min) is {load_1min} (threshold: {threshold})")
                        is_healthy = False
            
            result["status"] = "healthy" if is_healthy else "warning"
            return is_healthy, result
            
        except Exception as e:
            result["status"] = "critical"
            result["error"] = str(e)
            return False, result
    
    def send_notification(self, results: Dict, overall_status: str):
        """헬스 체크 결과 알림"""
        webhook_url = self.config['notifications'].get('slack_webhook')
        if not webhook_url:
            return
        
        notify_config = self.config['notifications']
        should_notify = False
        
        if overall_status == "critical" and notify_config.get('notify_on_critical', True):
            should_notify = True
        elif overall_status == "warning" and notify_config.get('notify_on_warning', True):
            should_notify = True
        
        if not should_notify:
            return
        
        # 알림 메시지 구성
        color = {
            "healthy": "good",
            "warning": "warning", 
            "critical": "danger"
        }.get(overall_status, "warning")
        
        failed_checks = [name for name, result in results.items() if result['status'] in ['warning', 'critical']]
        
        message = f"시스템 헬스 체크 결과: {overall_status.upper()}\n"
        if failed_checks:
            message += f"문제가 있는 항목: {', '.join(failed_checks)}"
        
        payload = {
            "attachments": [{
                "color": color,
                "fields": [{
                    "title": "헬스 체크 알림",
                    "value": message,
                    "short": False
                }],
                "ts": int(time.time())
            }]
        }
        
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
    
    def run_health_check(self) -> Dict:
        """전체 헬스 체크 실행"""
        logger.info("=== 헬스 체크 시작 ===")
        
        # HTTP 엔드포인트 체크
        for name, config in self.config['endpoints'].items():
            success, result = self.check_http_endpoint(name, config)
            self.results[name] = result
        
        # 데이터베이스 체크
        success, result = self.check_database()
        self.results['database'] = result
        
        # Redis 체크
        success, result = self.check_redis()
        self.results['redis'] = result
        
        # Docker 컨테이너 체크
        success, result = self.check_docker_containers()
        self.results['docker_containers'] = result
        
        # 시스템 리소스 체크
        success, result = self.check_system_resources()
        self.results['system_resources'] = result
        
        # 전체 상태 평가
        critical_count = sum(1 for result in self.results.values() if result['status'] == 'critical')
        warning_count = sum(1 for result in self.results.values() if result['status'] == 'warning')
        
        if critical_count > 0:
            overall_status = "critical"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        # 결과 요약
        summary = {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "summary": {
                "total_checks": len(self.results),
                "healthy": sum(1 for r in self.results.values() if r['status'] == 'healthy'),
                "warning": warning_count,
                "critical": critical_count,
                "skipped": sum(1 for r in self.results.values() if r['status'] == 'skipped')
            },
            "details": self.results
        }
        
        logger.info(f"헬스 체크 완료: {overall_status} (소요시간: {summary['duration']:.1f}초)")
        
        # 알림 전송
        self.send_notification(self.results, overall_status)
        
        return summary

def main():
    parser = argparse.ArgumentParser(description='시스템 헬스 체크 스크립트')
    parser.add_argument('--config', default='health_check_config.json', help='설정 파일 경로')
    parser.add_argument('--output', help='결과를 저장할 JSON 파일 경로')
    parser.add_argument('--format', choices=['json', 'table'], default='table', help='출력 형식')
    parser.add_argument('--quiet', action='store_true', help='요약 정보만 출력')
    
    args = parser.parse_args()
    
    health_checker = HealthChecker(args.config)
    results = health_checker.run_health_check()
    
    # 결과 출력
    if args.format == 'json':
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        # 테이블 형식 출력
        print(f"\n=== 헬스 체크 결과 ===")
        print(f"전체 상태: {results['overall_status'].upper()}")
        print(f"검사 시간: {results['timestamp']}")
        print(f"소요 시간: {results['duration']:.1f}초")
        print(f"\n총 {results['summary']['total_checks']}개 항목 검사:")
        print(f"  - 정상: {results['summary']['healthy']}")
        print(f"  - 경고: {results['summary']['warning']}")
        print(f"  - 위험: {results['summary']['critical']}")
        print(f"  - 건너뜀: {results['summary']['skipped']}")
        
        if not args.quiet:
            print(f"\n=== 상세 결과 ===")
            for name, result in results['details'].items():
                status_emoji = {
                    'healthy': '✅',
                    'warning': '⚠️',
                    'critical': '❌',
                    'skipped': '⏭️',
                    'unknown': '❓'
                }.get(result['status'], '❓')
                
                print(f"{status_emoji} {name}: {result['status']}")
                if result.get('response_time'):
                    print(f"   응답시간: {result['response_time']:.1f}ms")
                if result.get('error'):
                    print(f"   오류: {result['error']}")
    
    # 결과 파일 저장
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"결과를 {args.output}에 저장했습니다.")
    
    # 종료 코드 설정
    if results['overall_status'] == 'critical':
        sys.exit(2)
    elif results['overall_status'] == 'warning':
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
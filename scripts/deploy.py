#!/usr/bin/env python3
"""
배포 자동화 스크립트
운영환경 배포를 위한 통합 스크립트
"""

import os
import sys
import json
import time
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deploy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeploymentManager:
    """배포 관리 클래스"""
    
    def __init__(self, config_file: str = 'deploy_config.json'):
        self.config = self.load_config(config_file)
        self.start_time = datetime.now()
        
    def load_config(self, config_file: str) -> Dict:
        """배포 설정 로드"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일 {config_file}을 찾을 수 없습니다. 기본값을 사용합니다.")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """기본 배포 설정"""
        return {
            "environments": {
                "production": {
                    "host": os.getenv("DEPLOY_HOST", "localhost"),
                    "user": os.getenv("DEPLOY_USER", "deploy"),
                    "path": "/opt/dropshipping",
                    "compose_file": "docker-compose.prod.yml",
                    "health_check_url": "https://yourdomain.com/health",
                    "backup_before_deploy": True
                },
                "staging": {
                    "host": os.getenv("STAGING_HOST", "staging.localhost"),
                    "user": os.getenv("STAGING_USER", "deploy"),
                    "path": "/opt/dropshipping-staging",
                    "compose_file": "docker-compose.staging.yml",
                    "health_check_url": "https://staging.yourdomain.com/health",
                    "backup_before_deploy": False
                }
            },
            "deployment": {
                "max_retries": 3,
                "health_check_timeout": 300,
                "health_check_interval": 10,
                "rollback_on_failure": True,
                "cleanup_old_images": True
            },
            "notifications": {
                "slack_webhook": os.getenv("SLACK_WEBHOOK"),
                "email_enabled": False
            }
        }
    
    def run_command(self, command: str, cwd: Optional[str] = None) -> tuple:
        """명령어 실행"""
        logger.info(f"실행 중: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                cwd=cwd
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"명령어 실행 실패: {e.stderr}")
            return False, e.stderr
    
    def check_prerequisites(self, environment: str) -> bool:
        """배포 전 사전 조건 검사"""
        logger.info("배포 전 사전 조건을 검사합니다...")
        
        env_config = self.config['environments'][environment]
        
        # SSH 연결 테스트
        ssh_command = f"ssh -o ConnectTimeout=10 {env_config['user']}@{env_config['host']} 'echo \"SSH 연결 성공\"'"
        success, output = self.run_command(ssh_command)
        if not success:
            logger.error("SSH 연결에 실패했습니다.")
            return False
        
        # Docker 및 Docker Compose 확인
        docker_check = f"ssh {env_config['user']}@{env_config['host']} 'docker --version && docker compose version'"
        success, output = self.run_command(docker_check)
        if not success:
            logger.error("대상 서버에 Docker 또는 Docker Compose가 설치되어 있지 않습니다.")
            return False
        
        # 디스크 공간 확인
        disk_check = f"ssh {env_config['user']}@{env_config['host']} 'df -h {env_config[\"path\"]}'"
        success, output = self.run_command(disk_check)
        if success:
            logger.info(f"디스크 사용량:\n{output}")
        
        logger.info("사전 조건 검사가 완료되었습니다.")
        return True
    
    def backup_database(self, environment: str) -> bool:
        """데이터베이스 백업"""
        if not self.config['environments'][environment].get('backup_before_deploy', False):
            logger.info("백업이 비활성화되어 있습니다.")
            return True
        
        logger.info("데이터베이스 백업을 시작합니다...")
        env_config = self.config['environments'][environment]
        
        backup_command = f"""
        ssh {env_config['user']}@{env_config['host']} '
            cd {env_config["path"]} &&
            docker compose -f {env_config["compose_file"]} exec -T db pg_dump -U dropshipping dropshipping_db > backup_$(date +%Y%m%d_%H%M%S).sql &&
            echo "백업 완료"
        '
        """
        
        success, output = self.run_command(backup_command)
        if success:
            logger.info("데이터베이스 백업이 완료되었습니다.")
            return True
        else:
            logger.error("데이터베이스 백업에 실패했습니다.")
            return False
    
    def deploy_application(self, environment: str, tag: str = 'latest') -> bool:
        """애플리케이션 배포"""
        logger.info(f"{environment} 환경에 애플리케이션을 배포합니다...")
        
        env_config = self.config['environments'][environment]
        
        deploy_commands = [
            f"cd {env_config['path']}",
            "git fetch origin",
            f"git checkout {tag if tag != 'latest' else 'main'}",
            "git pull origin main" if tag == 'latest' else f"git reset --hard {tag}",
            f"cp .env.{environment} .env",
            f"docker compose -f {env_config['compose_file']} pull",
            f"docker compose -f {env_config['compose_file']} up -d --remove-orphans",
        ]
        
        full_command = f"""
        ssh {env_config['user']}@{env_config['host']} '
            {' && '.join(deploy_commands)}
        '
        """
        
        success, output = self.run_command(full_command)
        if success:
            logger.info("애플리케이션 배포가 완료되었습니다.")
            return True
        else:
            logger.error("애플리케이션 배포에 실패했습니다.")
            return False
    
    def health_check(self, environment: str) -> bool:
        """배포 후 헬스 체크"""
        logger.info("애플리케이션 헬스 체크를 시작합니다...")
        
        env_config = self.config['environments'][environment]
        health_url = env_config['health_check_url']
        
        max_attempts = self.config['deployment']['health_check_timeout'] // self.config['deployment']['health_check_interval']
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(health_url, timeout=30)
                if response.status_code == 200:
                    logger.info(f"헬스 체크 성공 (시도 {attempt + 1}/{max_attempts})")
                    return True
                else:
                    logger.warning(f"헬스 체크 실패: HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"헬스 체크 오류: {e}")
            
            if attempt < max_attempts - 1:
                time.sleep(self.config['deployment']['health_check_interval'])
        
        logger.error("헬스 체크에 실패했습니다.")
        return False
    
    def cleanup_old_images(self, environment: str) -> bool:
        """오래된 Docker 이미지 정리"""
        if not self.config['deployment'].get('cleanup_old_images', False):
            return True
        
        logger.info("오래된 Docker 이미지를 정리합니다...")
        env_config = self.config['environments'][environment]
        
        cleanup_command = f"""
        ssh {env_config['user']}@{env_config['host']} '
            docker system prune -f &&
            docker image prune -a -f --filter "until=72h"
        '
        """
        
        success, output = self.run_command(cleanup_command)
        if success:
            logger.info("Docker 이미지 정리가 완료되었습니다.")
        return success
    
    def rollback(self, environment: str) -> bool:
        """롤백 수행"""
        logger.warning("롤백을 수행합니다...")
        env_config = self.config['environments'][environment]
        
        rollback_command = f"""
        ssh {env_config['user']}@{env_config['host']} '
            cd {env_config["path"]} &&
            git reset --hard HEAD~1 &&
            docker compose -f {env_config["compose_file"]} up -d --remove-orphans
        '
        """
        
        success, output = self.run_command(rollback_command)
        if success:
            logger.info("롤백이 완료되었습니다.")
            # 롤백 후 헬스 체크
            return self.health_check(environment)
        else:
            logger.error("롤백에 실패했습니다.")
            return False
    
    def send_notification(self, message: str, success: bool = True):
        """알림 전송"""
        webhook_url = self.config['notifications'].get('slack_webhook')
        if not webhook_url:
            return
        
        color = "good" if success else "danger"
        payload = {
            "attachments": [{
                "color": color,
                "fields": [{
                    "title": "배포 알림",
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
    
    def deploy(self, environment: str, tag: str = 'latest', skip_checks: bool = False) -> bool:
        """전체 배포 프로세스"""
        logger.info(f"=== {environment} 환경 배포 시작 ===")
        start_time = time.time()
        
        try:
            # 1. 사전 조건 검사
            if not skip_checks and not self.check_prerequisites(environment):
                raise Exception("사전 조건 검사 실패")
            
            # 2. 백업
            if not self.backup_database(environment):
                raise Exception("데이터베이스 백업 실패")
            
            # 3. 배포
            if not self.deploy_application(environment, tag):
                raise Exception("애플리케이션 배포 실패")
            
            # 4. 헬스 체크
            if not self.health_check(environment):
                if self.config['deployment'].get('rollback_on_failure', True):
                    if self.rollback(environment):
                        raise Exception("배포 실패로 인한 롤백 완료")
                    else:
                        raise Exception("배포 실패 및 롤백 실패")
                else:
                    raise Exception("헬스 체크 실패")
            
            # 5. 정리
            self.cleanup_old_images(environment)
            
            duration = time.time() - start_time
            success_message = f"{environment} 환경 배포가 성공적으로 완료되었습니다. (소요시간: {duration:.1f}초)"
            logger.info(success_message)
            self.send_notification(success_message, True)
            
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            error_message = f"{environment} 환경 배포에 실패했습니다: {e} (소요시간: {duration:.1f}초)"
            logger.error(error_message)
            self.send_notification(error_message, False)
            
            return False

def main():
    parser = argparse.ArgumentParser(description='배포 자동화 스크립트')
    parser.add_argument('environment', choices=['production', 'staging'], help='배포 환경')
    parser.add_argument('--tag', default='latest', help='배포할 Git 태그 또는 커밋')
    parser.add_argument('--skip-checks', action='store_true', help='사전 조건 검사 생략')
    parser.add_argument('--config', default='deploy_config.json', help='설정 파일 경로')
    
    args = parser.parse_args()
    
    # 운영환경 배포 시 확인
    if args.environment == 'production':
        confirm = input("운영환경에 배포하시겠습니까? (yes/no): ")
        if confirm.lower() != 'yes':
            print("배포가 취소되었습니다.")
            sys.exit(0)
    
    deployer = DeploymentManager(args.config)
    success = deployer.deploy(args.environment, args.tag, args.skip_checks)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
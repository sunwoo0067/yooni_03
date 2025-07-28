#!/usr/bin/env python3
"""
데이터베이스 백업 및 복원 스크립트
자동화된 백업, S3 업로드, 복원 기능 제공
"""

import os
import sys
import json
import boto3
import gzip
import shutil
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import psycopg2
from urllib.parse import urlparse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupManager:
    """백업 관리 클래스"""
    
    def __init__(self, config_file: str = 'backup_config.json'):
        self.config = self.load_config(config_file)
        self.backup_dir = Path(self.config['local']['backup_dir'])
        self.backup_dir.mkdir(exist_ok=True)
        
        # AWS S3 클라이언트 초기화
        if self.config['s3']['enabled']:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config['s3']['access_key_id'],
                aws_secret_access_key=self.config['s3']['secret_access_key'],
                region_name=self.config['s3']['region']
            )
        else:
            self.s3_client = None
    
    def load_config(self, config_file: str) -> dict:
        """백업 설정 로드"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일 {config_file}을 찾을 수 없습니다. 기본값을 사용합니다.")
            return self.get_default_config()
    
    def get_default_config(self) -> dict:
        """기본 백업 설정"""
        return {
            "database": {
                "url": os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname"),
                "backup_tables": [],  # 빈 리스트면 전체 백업
                "exclude_tables": ["logs", "sessions", "temp_data"]
            },
            "local": {
                "backup_dir": "./backups",
                "retention_days": 30,
                "compress": True
            },
            "s3": {
                "enabled": bool(os.getenv("AWS_ACCESS_KEY_ID")),
                "bucket": os.getenv("BACKUP_S3_BUCKET", ""),
                "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                "region": os.getenv("AWS_REGION", "ap-northeast-2"),
                "retention_days": 90,
                "storage_class": "STANDARD_IA"
            },
            "notifications": {
                "slack_webhook": os.getenv("SLACK_WEBHOOK"),
                "email_enabled": False
            }
        }
    
    def get_db_connection(self):
        """데이터베이스 연결"""
        db_url = self.config['database']['url']
        parsed = urlparse(db_url)
        
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]
        )
    
    def generate_backup_filename(self, backup_type: str = 'full') -> str:
        """백업 파일명 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hostname = os.getenv('HOSTNAME', 'unknown')
        return f"backup_{backup_type}_{hostname}_{timestamp}.sql"
    
    def create_database_backup(self, backup_type: str = 'full') -> Optional[Path]:
        """데이터베이스 백업 생성"""
        logger.info(f"{backup_type} 백업을 시작합니다...")
        
        backup_filename = self.generate_backup_filename(backup_type)
        backup_path = self.backup_dir / backup_filename
        
        # pg_dump 명령 구성
        db_url = self.config['database']['url']
        parsed = urlparse(db_url)
        
        env = os.environ.copy()
        env['PGPASSWORD'] = parsed.password
        
        cmd = [
            'pg_dump',
            '-h', parsed.hostname,
            '-p', str(parsed.port or 5432),
            '-U', parsed.username,
            '-d', parsed.path[1:],
            '--verbose',
            '--no-owner',
            '--no-privileges'
        ]
        
        # 테이블 선택/제외 옵션 추가
        exclude_tables = self.config['database'].get('exclude_tables', [])
        for table in exclude_tables:
            cmd.extend(['--exclude-table', table])
        
        backup_tables = self.config['database'].get('backup_tables', [])
        if backup_tables:
            for table in backup_tables:
                cmd.extend(['--table', table])
        
        try:
            # 백업 실행
            with open(backup_path, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    check=True
                )
            
            # 압축
            if self.config['local']['compress']:
                compressed_path = backup_path.with_suffix('.sql.gz')
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path.unlink()  # 원본 삭제
                backup_path = compressed_path
            
            file_size = backup_path.stat().st_size
            logger.info(f"백업 완료: {backup_path} ({file_size / 1024 / 1024:.2f} MB)")
            
            return backup_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"백업 실패: {e.stderr}")
            if backup_path.exists():
                backup_path.unlink()
            return None
        except Exception as e:
            logger.error(f"백업 중 오류 발생: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return None
    
    def upload_to_s3(self, backup_path: Path) -> bool:
        """S3에 백업 파일 업로드"""
        if not self.s3_client:
            logger.info("S3 업로드가 비활성화되어 있습니다.")
            return True
        
        logger.info(f"S3에 백업 파일을 업로드합니다: {backup_path.name}")
        
        try:
            s3_key = f"database-backups/{datetime.now().strftime('%Y/%m/%d')}/{backup_path.name}"
            
            extra_args = {
                'StorageClass': self.config['s3']['storage_class'],
                'ServerSideEncryption': 'AES256',
                'Metadata': {
                    'created_at': datetime.now().isoformat(),
                    'hostname': os.getenv('HOSTNAME', 'unknown'),
                    'backup_type': 'database'
                }
            }
            
            self.s3_client.upload_file(
                str(backup_path),
                self.config['s3']['bucket'],
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"S3 업로드 완료: s3://{self.config['s3']['bucket']}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"S3 업로드 실패: {e}")
            return False
    
    def cleanup_old_backups(self):
        """오래된 백업 파일 정리"""
        logger.info("오래된 백업 파일을 정리합니다...")
        
        # 로컬 백업 정리
        retention_days = self.config['local']['retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        deleted_count = 0
        for backup_file in self.backup_dir.glob('backup_*.sql*'):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                backup_file.unlink()
                deleted_count += 1
        
        logger.info(f"로컬에서 {deleted_count}개의 오래된 백업 파일을 삭제했습니다.")
        
        # S3 백업 정리
        if self.s3_client:
            try:
                s3_retention_days = self.config['s3']['retention_days']
                s3_cutoff_date = datetime.now() - timedelta(days=s3_retention_days)
                
                response = self.s3_client.list_objects_v2(
                    Bucket=self.config['s3']['bucket'],
                    Prefix='database-backups/'
                )
                
                delete_keys = []
                for obj in response.get('Contents', []):
                    if obj['LastModified'].replace(tzinfo=None) < s3_cutoff_date:
                        delete_keys.append({'Key': obj['Key']})
                
                if delete_keys:
                    self.s3_client.delete_objects(
                        Bucket=self.config['s3']['bucket'],
                        Delete={'Objects': delete_keys}
                    )
                    logger.info(f"S3에서 {len(delete_keys)}개의 오래된 백업 파일을 삭제했습니다.")
                
            except Exception as e:
                logger.error(f"S3 백업 정리 실패: {e}")
    
    def restore_database(self, backup_path: str, target_db: Optional[str] = None) -> bool:
        """데이터베이스 복원"""
        logger.info(f"데이터베이스 복원을 시작합니다: {backup_path}")
        
        backup_file = Path(backup_path)
        if not backup_file.exists():
            logger.error(f"백업 파일을 찾을 수 없습니다: {backup_path}")
            return False
        
        # 압축 파일인 경우 압축 해제
        if backup_file.suffix == '.gz':
            temp_file = backup_file.with_suffix('')
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            restore_file = temp_file
            cleanup_temp = True
        else:
            restore_file = backup_file
            cleanup_temp = False
        
        try:
            # psql 명령 구성
            db_url = self.config['database']['url']
            parsed = urlparse(db_url)
            
            db_name = target_db or parsed.path[1:]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = parsed.password
            
            cmd = [
                'psql',
                '-h', parsed.hostname,
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', db_name,
                '-f', str(restore_file),
                '--quiet'
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("데이터베이스 복원이 완료되었습니다.")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"데이터베이스 복원 실패: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"복원 중 오류 발생: {e}")
            return False
        finally:
            if cleanup_temp and restore_file.exists():
                restore_file.unlink()
    
    def list_backups(self) -> List[dict]:
        """백업 파일 목록 조회"""
        backups = []
        
        # 로컬 백업
        for backup_file in sorted(self.backup_dir.glob('backup_*.sql*')):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime),
                'location': 'local'
            })
        
        # S3 백업
        if self.s3_client:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.config['s3']['bucket'],
                    Prefix='database-backups/'
                )
                
                for obj in response.get('Contents', []):
                    backups.append({
                        'name': obj['Key'].split('/')[-1],
                        'path': f"s3://{self.config['s3']['bucket']}/{obj['Key']}",
                        'size': obj['Size'],
                        'created_at': obj['LastModified'].replace(tzinfo=None),
                        'location': 's3'
                    })
                    
            except Exception as e:
                logger.error(f"S3 백업 목록 조회 실패: {e}")
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def send_notification(self, message: str, success: bool = True):
        """백업 결과 알림"""
        webhook_url = self.config['notifications'].get('slack_webhook')
        if not webhook_url:
            return
        
        import requests
        
        color = "good" if success else "danger"
        payload = {
            "attachments": [{
                "color": color,
                "fields": [{
                    "title": "백업 알림",
                    "value": message,
                    "short": False
                }],
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"알림 전송 실패: {e}")
    
    def run_backup(self, backup_type: str = 'full') -> bool:
        """전체 백업 프로세스 실행"""
        try:
            # 백업 생성
            backup_path = self.create_database_backup(backup_type)
            if not backup_path:
                raise Exception("백업 생성 실패")
            
            # S3 업로드
            if not self.upload_to_s3(backup_path):
                logger.warning("S3 업로드에 실패했지만 로컬 백업은 성공했습니다.")
            
            # 오래된 백업 정리
            self.cleanup_old_backups()
            
            success_message = f"백업이 성공적으로 완료되었습니다: {backup_path.name}"
            logger.info(success_message)
            self.send_notification(success_message, True)
            
            return True
            
        except Exception as e:
            error_message = f"백업 실패: {e}"
            logger.error(error_message)
            self.send_notification(error_message, False)
            return False

def main():
    parser = argparse.ArgumentParser(description='데이터베이스 백업 및 복원 스크립트')
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # 백업 명령어
    backup_parser = subparsers.add_parser('backup', help='데이터베이스 백업')
    backup_parser.add_argument('--type', default='full', choices=['full', 'incremental'], help='백업 타입')
    
    # 복원 명령어
    restore_parser = subparsers.add_parser('restore', help='데이터베이스 복원')
    restore_parser.add_argument('backup_path', help='백업 파일 경로')
    restore_parser.add_argument('--target-db', help='복원할 대상 데이터베이스명')
    
    # 목록 명령어
    list_parser = subparsers.add_parser('list', help='백업 파일 목록 조회')
    
    # 정리 명령어
    cleanup_parser = subparsers.add_parser('cleanup', help='오래된 백업 파일 정리')
    
    parser.add_argument('--config', default='backup_config.json', help='설정 파일 경로')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    backup_manager = BackupManager(args.config)
    
    if args.command == 'backup':
        success = backup_manager.run_backup(args.type)
        sys.exit(0 if success else 1)
    
    elif args.command == 'restore':
        success = backup_manager.restore_database(args.backup_path, args.target_db)
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        backups = backup_manager.list_backups()
        print(f"{'이름':<40} {'크기':<10} {'생성일시':<20} {'위치':<10}")
        print("-" * 85)
        for backup in backups:
            size_mb = backup['size'] / 1024 / 1024
            created_str = backup['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"{backup['name']:<40} {size_mb:>8.1f}MB {created_str:<20} {backup['location']:<10}")
    
    elif args.command == 'cleanup':
        backup_manager.cleanup_old_backups()

if __name__ == '__main__':
    main()
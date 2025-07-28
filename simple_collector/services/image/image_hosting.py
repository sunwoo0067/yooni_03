"""
이미지 호스팅 서비스
- 로컬 파일 서버
- CDN 연동 (선택사항)
- 이미지 URL 관리
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import hashlib
import json

from sqlalchemy.orm import Session
from database.models_v2 import Base, WholesaleProduct, MarketplaceProduct
from database.connection import engine
from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from utils.logger import app_logger


# 이미지 호스팅 정보 테이블
class ImageHosting(Base):
    __tablename__ = "image_hosting"
    
    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(200), index=True)
    marketplace = Column(String(50))
    original_url = Column(String(500))
    hosted_url = Column(String(500))
    local_path = Column(String(500))
    file_hash = Column(String(64))
    file_size = Column(Integer)
    image_type = Column(String(20))  # main, detail, thumbnail
    metadata = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# 테이블 생성
ImageHosting.__table__.create(engine, checkfirst=True)


class ImageHostingService:
    """이미지 호스팅 서비스"""
    
    def __init__(self, db: Session, base_url: str = "http://localhost:8000"):
        self.db = db
        self.base_url = base_url
        self.static_path = Path("static/images")
        self.static_path.mkdir(parents=True, exist_ok=True)
        
        # 이미지 타입별 경로
        self.paths = {
            'original': self.static_path / 'original',
            'processed': self.static_path / 'processed',
            'thumbnail': self.static_path / 'thumbnail'
        }
        
        for path in self.paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    def host_image(self, 
                   product_code: str,
                   marketplace: str,
                   local_path: str,
                   image_type: str = 'main',
                   original_url: str = None) -> Optional[str]:
        """이미지 호스팅 및 URL 반환"""
        try:
            local_path = Path(local_path)
            if not local_path.exists():
                app_logger.error(f"파일이 존재하지 않습니다: {local_path}")
                return None
            
            # 파일 해시 생성
            file_hash = self._calculate_file_hash(local_path)
            
            # 중복 확인
            existing = self.db.query(ImageHosting).filter(
                ImageHosting.file_hash == file_hash,
                ImageHosting.marketplace == marketplace
            ).first()
            
            if existing:
                app_logger.info(f"기존 호스팅 이미지 사용: {existing.hosted_url}")
                return existing.hosted_url
            
            # 호스팅 경로 생성
            file_ext = local_path.suffix
            hosted_filename = f"{marketplace}_{product_code}_{file_hash[:8]}{file_ext}"
            hosted_path = self.paths['processed'] / marketplace / hosted_filename
            hosted_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 복사
            shutil.copy2(local_path, hosted_path)
            
            # URL 생성
            relative_path = hosted_path.relative_to('static')
            hosted_url = f"{self.base_url}/static/{relative_path.as_posix()}"
            
            # DB 저장
            hosting_info = ImageHosting(
                product_code=product_code,
                marketplace=marketplace,
                original_url=original_url,
                hosted_url=hosted_url,
                local_path=str(hosted_path),
                file_hash=file_hash,
                file_size=local_path.stat().st_size,
                image_type=image_type,
                metadata={
                    'width': 0,  # PIL로 읽어서 업데이트 가능
                    'height': 0,
                    'format': file_ext[1:].upper()
                }
            )
            
            self.db.add(hosting_info)
            self.db.commit()
            
            app_logger.info(f"이미지 호스팅 완료: {hosted_url}")
            return hosted_url
            
        except Exception as e:
            app_logger.error(f"이미지 호스팅 오류: {e}")
            self.db.rollback()
            return None
    
    def host_product_images(self,
                           product_code: str,
                           marketplace: str,
                           image_paths: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """상품의 모든 이미지 호스팅
        
        Args:
            image_paths: {
                'original': [...],
                'processed': [...],
                'thumbnail': [...]
            }
        
        Returns:
            {
                'main': ['url1', 'url2', ...],
                'detail': ['url1', 'url2', ...],
                'thumbnail': ['url1', 'url2', ...]
            }
        """
        hosted_urls = {
            'main': [],
            'detail': [],
            'thumbnail': []
        }
        
        # 처리된 이미지 호스팅
        for idx, path in enumerate(image_paths.get('processed', [])):
            image_type = 'main' if idx == 0 else 'detail'
            url = self.host_image(
                product_code=product_code,
                marketplace=marketplace,
                local_path=path,
                image_type=image_type
            )
            if url:
                hosted_urls[image_type].append(url)
        
        # 썸네일 호스팅
        for path in image_paths.get('thumbnail', []):
            url = self.host_image(
                product_code=product_code,
                marketplace=marketplace,
                local_path=path,
                image_type='thumbnail'
            )
            if url:
                hosted_urls['thumbnail'].append(url)
        
        return hosted_urls
    
    def get_hosted_images(self, product_code: str, 
                         marketplace: str = None) -> Dict[str, List[str]]:
        """호스팅된 이미지 URL 조회"""
        query = self.db.query(ImageHosting).filter(
            ImageHosting.product_code == product_code,
            ImageHosting.is_active == True
        )
        
        if marketplace:
            query = query.filter(ImageHosting.marketplace == marketplace)
        
        images = query.all()
        
        result = {
            'main': [],
            'detail': [],
            'thumbnail': []
        }
        
        for img in images:
            if img.image_type in result:
                result[img.image_type].append(img.hosted_url)
        
        return result
    
    def update_product_images(self, product_code: str, 
                            marketplace: str,
                            image_urls: Dict[str, List[str]]):
        """상품 이미지 URL 업데이트"""
        try:
            # 기존 이미지 비활성화
            self.db.query(ImageHosting).filter(
                ImageHosting.product_code == product_code,
                ImageHosting.marketplace == marketplace
            ).update({'is_active': False})
            
            # 새 이미지 추가 또는 활성화
            for image_type, urls in image_urls.items():
                for url in urls:
                    # URL이 이미 호스팅된 것인지 확인
                    existing = self.db.query(ImageHosting).filter(
                        ImageHosting.hosted_url == url
                    ).first()
                    
                    if existing:
                        existing.is_active = True
                    else:
                        # 외부 URL인 경우 그대로 저장
                        hosting_info = ImageHosting(
                            product_code=product_code,
                            marketplace=marketplace,
                            original_url=url,
                            hosted_url=url,
                            image_type=image_type,
                            metadata={}
                        )
                        self.db.add(hosting_info)
            
            self.db.commit()
            
        except Exception as e:
            app_logger.error(f"이미지 URL 업데이트 오류: {e}")
            self.db.rollback()
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """파일 해시 계산"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def cleanup_unused_images(self, days: int = 30):
        """사용하지 않는 이미지 정리"""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 오래된 비활성 이미지 조회
        old_images = self.db.query(ImageHosting).filter(
            ImageHosting.is_active == False,
            ImageHosting.updated_at < cutoff_date
        ).all()
        
        for img in old_images:
            try:
                # 로컬 파일 삭제
                if img.local_path and Path(img.local_path).exists():
                    Path(img.local_path).unlink()
                
                # DB에서 삭제
                self.db.delete(img)
                
                app_logger.info(f"이미지 삭제: {img.local_path}")
                
            except Exception as e:
                app_logger.error(f"이미지 삭제 오류: {e}")
        
        self.db.commit()
    
    def get_storage_stats(self) -> Dict:
        """스토리지 사용 현황"""
        total_size = 0
        file_count = 0
        
        for path in self.paths.values():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size
        
        # DB 통계
        active_count = self.db.query(ImageHosting).filter(
            ImageHosting.is_active == True
        ).count()
        
        total_db_count = self.db.query(ImageHosting).count()
        
        return {
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'active_images': active_count,
            'total_db_records': total_db_count,
            'paths': {
                name: str(path) for name, path in self.paths.items()
            }
        }
    
    def migrate_to_cdn(self, cdn_upload_func, batch_size: int = 100):
        """CDN으로 이미지 마이그레이션"""
        images = self.db.query(ImageHosting).filter(
            ImageHosting.is_active == True,
            ImageHosting.hosted_url.like(f"{self.base_url}%")
        ).limit(batch_size).all()
        
        migrated_count = 0
        
        for img in images:
            try:
                # CDN 업로드
                if img.local_path and Path(img.local_path).exists():
                    cdn_url = cdn_upload_func(img.local_path)
                    
                    if cdn_url:
                        # URL 업데이트
                        img.hosted_url = cdn_url
                        img.metadata['cdn_migrated'] = True
                        img.metadata['migration_date'] = datetime.now().isoformat()
                        
                        migrated_count += 1
                        app_logger.info(f"CDN 마이그레이션 완료: {img.product_code}")
                
            except Exception as e:
                app_logger.error(f"CDN 마이그레이션 오류: {e}")
        
        self.db.commit()
        
        return {
            'migrated': migrated_count,
            'total': len(images)
        }
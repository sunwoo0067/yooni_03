from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from database.connection import Base, engine
from datetime import datetime
from typing import Dict, Any, Optional

class Product(Base):
    """통합 상품 모델 - 도매사이트 + 마켓플레이스"""
    __tablename__ = "products"
    
    # 기본 필드
    product_code = Column(String(100), primary_key=True, comment="상품 코드")
    product_id = Column(String(200), unique=True, index=True, comment="고유 상품 ID (marketplace_productid)")
    
    # PostgreSQL에서는 JSONB, SQLite에서는 JSON 사용
    if 'postgresql' in str(engine.url):
        product_info = Column(JSONB, nullable=False, comment="상품 정보 (JSON)")
    else:
        product_info = Column(JSON, nullable=False, comment="상품 정보 (JSON)")
    
    # 공통 필드
    supplier = Column(String(50), nullable=False, comment="공급사명")
    product_name = Column(String(500), comment="상품명")
    price = Column(Integer, comment="판매가")
    original_price = Column(Integer, comment="원가/정가")
    stock = Column(Integer, default=0, comment="재고수량")
    
    # 마켓플레이스 전용 필드
    marketplace = Column(String(50), comment="마켓플레이스 (coupang/naver/11st)")
    category = Column(String(500), comment="카테고리")
    brand = Column(String(200), comment="브랜드")
    image_url = Column(Text, comment="대표 이미지 URL")
    product_url = Column(Text, comment="상품 URL")
    status = Column(String(50), comment="상품 상태")
    
    # 메타데이터 (관리용)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    is_active = Column(Boolean, default=True, comment="활성 상태")
    
    def __repr__(self):
        return f"<Product(code={self.product_code}, supplier={self.supplier}, marketplace={self.marketplace})>"

class Supplier(Base):
    """공급사 정보 관리"""
    __tablename__ = "suppliers"
    
    supplier_code = Column(String(20), primary_key=True, comment="공급사 코드")
    supplier_name = Column(String(100), nullable=False, comment="공급사명")
    api_key = Column(Text, comment="API 키")
    api_secret = Column(Text, comment="API 시크릿")
    # PostgreSQL에서는 JSONB, SQLite에서는 JSON 사용
    if 'postgresql' in str(engine.url):
        api_config = Column(JSONB, comment="API 설정 정보")
    else:
        api_config = Column(JSON, comment="API 설정 정보")
    is_active = Column(Boolean, default=True, comment="활성 상태")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Supplier(code={self.supplier_code}, name={self.supplier_name})>"

class CollectionLog(Base):
    """수집 로그"""
    __tablename__ = "collection_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier = Column(String(50), nullable=False, comment="공급사")
    collection_type = Column(String(20), nullable=False, comment="수집 타입 (full/incremental)")
    status = Column(String(20), nullable=False, comment="상태 (running/completed/failed)")
    total_count = Column(Integer, default=0, comment="총 상품 수")
    new_count = Column(Integer, default=0, comment="신규 상품 수")
    updated_count = Column(Integer, default=0, comment="업데이트 상품 수")
    error_count = Column(Integer, default=0, comment="오류 수")
    error_message = Column(Text, comment="오류 메시지")
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), comment="종료 시간")
    
    def __repr__(self):
        return f"<CollectionLog(supplier={self.supplier}, status={self.status})>"

class ApiCredential(Base):
    """API 크레덴셜 관리"""
    __tablename__ = "api_credentials"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_code = Column(String(50), nullable=False, unique=True, comment="공급사 코드")
    
    # PostgreSQL에서는 JSONB, SQLite에서는 JSON 사용
    if 'postgresql' in str(engine.url):
        api_config = Column(JSONB, comment="API 설정 (키, 시크릿 등)")
    else:
        api_config = Column(JSON, comment="API 설정 (키, 시크릿 등)")
        
    is_active = Column(Boolean, default=True, comment="활성 상태")
    last_tested = Column(DateTime(timezone=True), comment="마지막 테스트 시간")
    test_status = Column(String(20), comment="테스트 상태 (success/fail)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ApiCredential(supplier={self.supplier_code}, active={self.is_active})>"

class ExcelUpload(Base):
    """엑셀 업로드 이력"""
    __tablename__ = "excel_uploads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier = Column(String(50), nullable=False, comment="공급사")
    filename = Column(String(255), nullable=False, comment="파일명")
    file_path = Column(String(500), comment="파일 경로")
    total_rows = Column(Integer, comment="총 행 수")
    processed_rows = Column(Integer, comment="처리된 행 수")
    error_rows = Column(Integer, comment="오류 행 수")
    status = Column(String(20), default="uploaded", comment="상태")
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    process_time = Column(DateTime(timezone=True), comment="처리 완료 시간")
    
    def __repr__(self):
        return f"<ExcelUpload(supplier={self.supplier}, filename={self.filename})>"

# 기본 공급사 데이터
DEFAULT_SUPPLIERS = [
    {
        "supplier_code": "zentrade",
        "supplier_name": "젠트레이드",
        "api_config": {
            "base_url": "https://api.zentrade.co.kr",
            "product_count": 3500,
            "collection_method": "full"
        }
    },
    {
        "supplier_code": "ownerclan", 
        "supplier_name": "오너클랜",
        "api_config": {
            "base_url": "https://api.ownerclan.com",
            "product_count": 7400000,
            "collection_method": "two_stage",
            "cache_size": 5000
        }
    },
    {
        "supplier_code": "domeggook",
        "supplier_name": "도매꾹",
        "api_config": {
            "base_url": "https://api.domeggook.com", 
            "collection_method": "category_based",
            "category_depth": 2
        }
    },
    {
        "supplier_code": "domomae",
        "supplier_name": "도매매",
        "api_config": {
            "base_url": "https://api.domomae.com",
            "collection_method": "category_based", 
            "category_depth": 2
        }
    },
    # 마켓플레이스
    {
        "supplier_code": "coupang",
        "supplier_name": "쿠팡",
        "api_config": {
            "marketplace": True,
            "api_type": "coupang_openapi",
            "base_url": "https://api-gateway.coupang.com",
            "requires": ["access_key", "secret_key", "vendor_id"]
        }
    },
    {
        "supplier_code": "naver",
        "supplier_name": "네이버 스마트스토어",
        "api_config": {
            "marketplace": True,
            "api_type": "naver_commerce",
            "base_url": "https://api.commerce.naver.com",
            "requires": ["client_id", "client_secret"]
        }
    },
    {
        "supplier_code": "11st",
        "supplier_name": "11번가",
        "api_config": {
            "marketplace": True,
            "api_type": "11st_openapi",
            "base_url": "https://api.11st.co.kr/rest",
            "requires": ["api_key"]
        }
    }
]

def init_suppliers(db_session):
    """기본 공급사 데이터 초기화"""
    for supplier_data in DEFAULT_SUPPLIERS:
        existing = db_session.query(Supplier).filter(
            Supplier.supplier_code == supplier_data["supplier_code"]
        ).first()
        
        if not existing:
            supplier = Supplier(**supplier_data)
            db_session.add(supplier)
    
    db_session.commit()
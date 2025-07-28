"""
도매처/마켓플레이스 분리 모델 (v2)
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from database.connection import Base, engine
from datetime import datetime
from typing import Dict, Any, Optional


class WholesaleProduct(Base):
    """도매 상품 (소싱용)"""
    __tablename__ = "wholesale_products"
    
    # 기본 필드
    product_code = Column(String(100), primary_key=True, comment="도매처 상품 코드")
    supplier = Column(String(50), nullable=False, index=True, comment="도매처 (zentrade/ownerclan/domeggook)")
    
    # 상품 정보
    product_name = Column(String(500), nullable=False, comment="상품명")
    wholesale_price = Column(Integer, nullable=False, comment="도매가격")
    
    # PostgreSQL에서는 JSONB, SQLite에서는 JSON 사용
    if 'postgresql' in str(engine.url):
        product_info = Column(JSONB, nullable=False, comment="상품 상세정보 (JSON)")
        price_info = Column(JSONB, comment="가격 정보 (도매가, 소비자가 등)")
        stock_info = Column(JSONB, comment="재고 정보")
        image_info = Column(JSONB, comment="이미지 정보")
    else:
        product_info = Column(JSON, nullable=False, comment="상품 상세정보 (JSON)")
        price_info = Column(JSON, comment="가격 정보 (도매가, 소비자가 등)")
        stock_info = Column(JSON, comment="재고 정보")
        image_info = Column(JSON, comment="이미지 정보")
    
    # 분류 정보
    category = Column(String(500), comment="카테고리")
    brand = Column(String(200), comment="브랜드")
    manufacturer = Column(String(200), comment="제조사")
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    last_synced_at = Column(DateTime(timezone=True), comment="마지막 동기화 시간")
    is_active = Column(Boolean, default=True, index=True, comment="활성 상태")
    
    # 관계
    marketplace_products = relationship("MarketplaceProduct", back_populates="wholesale_product")
    
    # 인덱스
    __table_args__ = (
        Index('idx_wholesale_supplier_active', 'supplier', 'is_active'),
        Index('idx_wholesale_updated', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<WholesaleProduct(code={self.product_code}, supplier={self.supplier})>"


class MarketplaceProduct(Base):
    """마켓플레이스 상품 (판매 중인 상품)"""
    __tablename__ = "marketplace_products"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, autoincrement=True)
    marketplace_product_id = Column(String(200), unique=True, nullable=False, comment="마켓플레이스 상품 ID")
    marketplace = Column(String(50), nullable=False, index=True, comment="마켓플레이스 (coupang/naver/11st)")
    
    # 연결 정보
    wholesale_product_code = Column(String(100), ForeignKey('wholesale_products.product_code'), comment="도매 상품 코드")
    
    # 상품 정보
    product_name = Column(String(500), nullable=False, comment="판매 상품명")
    selling_price = Column(Integer, nullable=False, comment="판매가격")
    
    # PostgreSQL에서는 JSONB, SQLite에서는 JSON 사용
    if 'postgresql' in str(engine.url):
        listing_info = Column(JSONB, comment="상품 등록 정보")
        price_policy = Column(JSONB, comment="가격 정책 (마진율, 할인 등)")
        stock_sync_info = Column(JSONB, comment="재고 동기화 정보")
    else:
        listing_info = Column(JSON, comment="상품 등록 정보")
        price_policy = Column(JSON, comment="가격 정책 (마진율, 할인 등)")
        stock_sync_info = Column(JSON, comment="재고 동기화 정보")
    
    # 상태 정보
    status = Column(String(50), default='active', comment="판매 상태 (active/paused/soldout)")
    stock_quantity = Column(Integer, default=0, comment="재고 수량")
    
    # 마켓플레이스별 정보
    marketplace_category = Column(String(500), comment="마켓플레이스 카테고리")
    marketplace_url = Column(Text, comment="상품 URL")
    
    # 성과 지표
    view_count = Column(Integer, default=0, comment="조회수")
    order_count = Column(Integer, default=0, comment="주문수")
    revenue = Column(Integer, default=0, comment="매출액")
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="등록일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    last_synced_at = Column(DateTime(timezone=True), comment="마지막 동기화 시간")
    
    # 관계
    wholesale_product = relationship("WholesaleProduct", back_populates="marketplace_products")
    
    # 인덱스
    __table_args__ = (
        Index('idx_marketplace_status', 'marketplace', 'status'),
        Index('idx_marketplace_wholesale', 'wholesale_product_code'),
        Index('idx_marketplace_updated', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<MarketplaceProduct(id={self.marketplace_product_id}, marketplace={self.marketplace})>"


class ProductMapping(Base):
    """도매 상품과 마켓플레이스 상품 매핑 이력"""
    __tablename__ = "product_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wholesale_product_code = Column(String(100), nullable=False, comment="도매 상품 코드")
    marketplace = Column(String(50), nullable=False, comment="마켓플레이스")
    marketplace_product_id = Column(String(200), nullable=False, comment="마켓플레이스 상품 ID")
    
    # 매핑 정보
    mapping_type = Column(String(50), default='auto', comment="매핑 타입 (auto/manual)")
    confidence_score = Column(Float, comment="자동 매핑 신뢰도")
    
    # PostgreSQL에서는 JSONB, SQLite에서는 JSON 사용
    if 'postgresql' in str(engine.url):
        mapping_data = Column(JSONB, comment="매핑 상세 데이터")
    else:
        mapping_data = Column(JSON, comment="매핑 상세 데이터")
    
    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), comment="생성자")
    is_active = Column(Boolean, default=True, comment="활성 상태")
    
    # 인덱스
    __table_args__ = (
        Index('idx_mapping_wholesale', 'wholesale_product_code'),
        Index('idx_mapping_marketplace', 'marketplace', 'marketplace_product_id'),
    )


class PriceHistory(Base):
    """가격 변동 이력"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_type = Column(String(20), nullable=False, comment="상품 타입 (wholesale/marketplace)")
    product_code = Column(String(200), nullable=False, comment="상품 코드/ID")
    
    # 가격 정보
    price_type = Column(String(50), comment="가격 유형 (wholesale/selling/special)")
    old_price = Column(Integer, comment="이전 가격")
    new_price = Column(Integer, comment="새 가격")
    change_rate = Column(Float, comment="변동률 (%)")
    
    # 메타데이터
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(100), comment="변경 출처")
    
    # 인덱스
    __table_args__ = (
        Index('idx_price_history_product', 'product_type', 'product_code'),
        Index('idx_price_history_date', 'changed_at'),
    )


class StockHistory(Base):
    """재고 변동 이력"""
    __tablename__ = "stock_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_type = Column(String(20), nullable=False, comment="상품 타입 (wholesale/marketplace)")
    product_code = Column(String(200), nullable=False, comment="상품 코드/ID")
    
    # 재고 정보
    old_stock = Column(Integer, comment="이전 재고")
    new_stock = Column(Integer, comment="새 재고")
    change_quantity = Column(Integer, comment="변동 수량")
    change_type = Column(String(50), comment="변동 유형 (sync/order/adjust)")
    
    # 메타데이터
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(100), comment="변경 출처")
    
    # 인덱스
    __table_args__ = (
        Index('idx_stock_history_product', 'product_type', 'product_code'),
        Index('idx_stock_history_date', 'changed_at'),
    )


# Supplier와 CollectionLog 모델은 기존 models.py에서 사용하므로 여기서는 제외
"""
도매처에서 수집된 상품 정보를 저장하는 모델
상품 수집(Collection) 단계에서 사용
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Text, DateTime, Integer, Numeric, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
import enum

from .base import BaseModel


class CollectionStatus(enum.Enum):
    """수집 상태"""
    COLLECTED = "collected"  # 수집됨
    SOURCED = "sourced"      # 소싱됨 (Product로 등록됨)
    REJECTED = "rejected"    # 거부됨
    EXPIRED = "expired"      # 만료됨


class WholesalerSource(enum.Enum):
    """도매처 소스"""
    OWNERCLAN = "ownerclan"    # 오너클랜
    DOMEME = "domeme"          # 도매매
    GENTRADE = "gentrade"      # 젠트레이드


class CollectedProduct(BaseModel):
    """도매처에서 수집된 상품 정보"""
    __tablename__ = "collected_products"
    
    # 수집 정보
    source = Column(SQLEnum(WholesalerSource), nullable=False, index=True)
    collection_keyword = Column(String(200), nullable=True, index=True)  # 수집 시 사용한 키워드
    collection_batch_id = Column(String(100), nullable=True, index=True)  # 배치 수집 ID
    
    # 도매처 정보
    supplier_id = Column(String(100), nullable=True, index=True)         # 도매처의 상품 ID
    supplier_name = Column(String(200), nullable=True)                   # 도매처 업체명
    supplier_url = Column(String(1000), nullable=True)                   # 도매처 상품 URL
    
    # 기본 상품 정보
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    brand = Column(String(100), nullable=True, index=True)
    model_number = Column(String(100), nullable=True)
    category = Column(String(200), nullable=True, index=True)
    
    # 가격 정보
    price = Column(Numeric(12, 2), nullable=False)                       # 현재 가격
    original_price = Column(Numeric(12, 2), nullable=True)               # 원래 가격 (할인 전)
    wholesale_price = Column(Numeric(12, 2), nullable=True)              # 도매가
    minimum_order_quantity = Column(Integer, default=1, nullable=False)   # 최소 주문 수량
    
    # 재고 정보
    stock_status = Column(String(50), default="available", nullable=False, index=True)  # available, limited, out_of_stock
    stock_quantity = Column(Integer, nullable=True)                      # 재고 수량 (알 수 있는 경우)
    
    # 이미지 및 미디어
    main_image_url = Column(String(1000), nullable=True)
    image_urls = Column(JSONB, nullable=True)                           # 추가 이미지들
    
    # 상품 속성
    specifications = Column(JSONB, nullable=True)                       # 상품 사양
    attributes = Column(JSONB, nullable=True)                           # 기타 속성 (색상, 크기 등)
    
    # 배송 정보
    shipping_info = Column(JSONB, nullable=True)                        # 배송 관련 정보
    shipping_cost = Column(Numeric(12, 2), nullable=True)               # 배송비
    
    # 수집 상태 및 메타데이터
    status = Column(SQLEnum(CollectionStatus), default=CollectionStatus.COLLECTED, nullable=False, index=True)
    quality_score = Column(Numeric(3, 2), nullable=True)                # 상품 품질 점수 (0-10)
    popularity_score = Column(Numeric(5, 2), nullable=True)             # 인기도 점수
    
    # 소싱 관련
    sourced_at = Column(DateTime, nullable=True)                        # 소싱된 시간
    sourced_product_id = Column(String(100), nullable=True, index=True) # 소싱된 상품의 ID
    rejection_reason = Column(String(500), nullable=True)               # 거부 이유
    
    # 추가 메타데이터
    raw_data = Column(JSONB, nullable=True)                            # 원본 수집 데이터
    processing_notes = Column(Text, nullable=True)                     # 처리 노트
    
    # 수집 시간 추적
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)                       # 수집 데이터 만료일
    
    def __repr__(self):
        return f"<CollectedProduct(id={self.id}, source={self.source.value}, name={self.name[:50]})>"
    
    @property
    def is_expired(self) -> bool:
        """수집 데이터가 만료되었는지 확인"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_sourced(self) -> bool:
        """이미 소싱되었는지 확인"""
        return self.status == CollectionStatus.SOURCED and self.sourced_product_id is not None
    
    @property
    def profit_margin_estimate(self) -> Optional[float]:
        """예상 수익률 계산 (간단한 추정)"""
        if not self.price:
            return None
        
        # 기본 마진율 30% 가정
        estimated_selling_price = self.price * 1.3
        return ((estimated_selling_price - self.price) / estimated_selling_price) * 100
    
    def to_product_dict(self) -> Dict[str, Any]:
        """Product 모델로 변환하기 위한 딕셔너리 생성"""
        return {
            "name": self.name,
            "description": self.description,
            "brand": self.brand,
            "model_number": self.model_number,
            "category_path": self.category,
            "cost_price": self.price,
            "wholesale_price": self.wholesale_price,
            "retail_price": self.original_price,
            "main_image_url": self.main_image_url,
            "image_urls": self.image_urls,
            "attributes": {
                "source": self.source.value,
                "supplier_id": self.supplier_id,
                "supplier_url": self.supplier_url,
                "collection_keyword": self.collection_keyword,
                "specifications": self.specifications,
                **(self.attributes or {})
            },
            "stock_quantity": self.stock_quantity or 0,
            "is_dropshipping": True,
            "requires_shipping": True
        }


class CollectionBatch(BaseModel):
    """상품 수집 배치 정보"""
    __tablename__ = "collection_batches"
    
    batch_id = Column(String(100), unique=True, nullable=False, index=True)  # 배치 고유 ID
    source = Column(SQLEnum(WholesalerSource), nullable=False, index=True)
    keyword = Column(String(200), nullable=False)
    
    # 수집 설정
    max_products = Column(Integer, default=50, nullable=False)
    filters = Column(JSONB, nullable=True)  # 가격 범위, 카테고리 등
    
    # 수집 결과
    total_collected = Column(Integer, default=0, nullable=False)
    successful_collections = Column(Integer, default=0, nullable=False)
    failed_collections = Column(Integer, default=0, nullable=False)
    
    # 상태
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    
    # 시간 추적
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<CollectionBatch(batch_id={self.batch_id}, source={self.source.value}, keyword={self.keyword})>"
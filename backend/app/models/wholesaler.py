from sqlalchemy import Column, String, DateTime, Text, Boolean, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel, get_json_type


class WholesalerType(enum.Enum):
    """도매처 유형"""
    DOMEGGOOK = "domeggook"  # 도매매(도매꾹)
    OWNERCLAN = "ownerclan"  # 오너클랜
    ZENTRADE = "zentrade"    # 젠트레이드


class ConnectionStatus(enum.Enum):
    """연결 상태"""
    CONNECTED = "connected"      # 연결됨
    DISCONNECTED = "disconnected"  # 연결 끊김
    ERROR = "error"             # 오류
    TESTING = "testing"         # 테스트 중


class CollectionStatus(enum.Enum):
    """수집 상태"""
    PENDING = "pending"         # 대기 중
    RUNNING = "running"         # 수집 중
    COMPLETED = "completed"     # 완료
    FAILED = "failed"          # 실패
    CANCELLED = "cancelled"     # 취소됨


class WholesalerAccount(BaseModel):
    """도매처 계정 정보"""
    __tablename__ = "wholesaler_accounts"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 도매처 기본 정보
    wholesaler_type = Column(Enum(WholesalerType), nullable=False)
    account_name = Column(String(100), nullable=False, comment="계정 별칭")
    
    # API 인증 정보 (암호화 저장)
    api_credentials = Column(Text, nullable=False, comment="암호화된 API 인증 정보")
    
    # 연결 상태
    connection_status = Column(Enum(ConnectionStatus), default=ConnectionStatus.DISCONNECTED)
    last_connected_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    
    # 설정 정보
    is_active = Column(Boolean, default=True)
    auto_collect_enabled = Column(Boolean, default=False, comment="자동 수집 활성화")
    collect_interval_hours = Column(Integer, default=24, comment="수집 주기(시간)")
    
    # 수집 설정
    collect_categories = Column(get_json_type(), nullable=True, comment="수집할 카테고리 목록")
    collect_recent_days = Column(Integer, default=7, comment="최근 N일 상품만 수집")
    max_products_per_collection = Column(Integer, default=1000, comment="한 번에 수집할 최대 상품 수")
    
    # 관계
    user = relationship("User", back_populates="wholesaler_accounts")
    collection_logs = relationship("CollectionLog", back_populates="wholesaler_account")
    scheduled_collections = relationship("ScheduledCollection", back_populates="wholesaler_account")
    
    # 드롭쉬핑 관련 관계 - Temporarily disabled (models not implemented)
    # outofstock_history = relationship("OutOfStockHistory", back_populates="wholesaler")
    # reliability = relationship("SupplierReliability", back_populates="supplier", uselist=False)
    # stock_check_logs = relationship("StockCheckLog", back_populates="wholesaler")
    # dropshipping_price_history = relationship("PriceHistory", back_populates="wholesaler")


class CollectionLog(BaseModel):
    """상품 수집 로그"""
    __tablename__ = "collection_logs"
    
    wholesaler_account_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)
    
    # 수집 정보
    collection_type = Column(String(50), nullable=False, comment="수집 유형 (전체/최근/카테고리)")
    status = Column(Enum(CollectionStatus), default=CollectionStatus.PENDING)
    
    # 수집 조건
    filters = Column(get_json_type(), nullable=True, comment="수집 조건 (카테고리, 날짜 등)")
    
    # 수집 결과
    total_products_found = Column(Integer, default=0, comment="발견된 총 상품 수")
    products_collected = Column(Integer, default=0, comment="실제 수집된 상품 수")
    products_updated = Column(Integer, default=0, comment="업데이트된 상품 수")
    products_failed = Column(Integer, default=0, comment="실패한 상품 수")
    
    # 실행 정보
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # 오류 정보
    error_message = Column(Text, nullable=True)
    error_details = Column(get_json_type(), nullable=True)
    
    # 수집된 데이터 요약
    collection_summary = Column(get_json_type(), nullable=True, comment="수집 결과 요약")
    
    # 관계
    wholesaler_account = relationship("WholesalerAccount", back_populates="collection_logs")


class ScheduledCollection(BaseModel):
    """자동 수집 스케줄"""
    __tablename__ = "scheduled_collections"
    
    wholesaler_account_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)
    
    # 스케줄 설정
    schedule_name = Column(String(100), nullable=False, comment="스케줄 이름")
    collection_type = Column(String(50), nullable=False, comment="수집 유형")
    
    # 실행 조건
    cron_expression = Column(String(100), nullable=False, comment="크론 표현식")
    timezone = Column(String(50), default="Asia/Seoul")
    
    # 수집 설정
    filters = Column(get_json_type(), nullable=True, comment="수집 조건")
    max_products = Column(Integer, default=1000)
    
    # 상태
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    # 실행 결과
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # 관계
    wholesaler_account = relationship("WholesalerAccount", back_populates="scheduled_collections")


class WholesalerProduct(BaseModel):
    """도매처에서 수집된 상품 정보"""
    __tablename__ = "wholesaler_products"
    
    wholesaler_account_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)
    
    # 도매처 상품 정보
    wholesaler_product_id = Column(String(100), nullable=False, comment="도매처 상품 ID")
    wholesaler_sku = Column(String(100), nullable=True, comment="도매처 SKU")
    
    # 기본 정보
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category_path = Column(String(500), nullable=True, comment="카테고리 경로")
    
    # 가격 정보
    wholesale_price = Column(Integer, nullable=False, comment="도매가")
    retail_price = Column(Integer, nullable=True, comment="소매가")
    discount_rate = Column(Integer, nullable=True, comment="할인율")
    
    # 재고 정보
    stock_quantity = Column(Integer, default=0)
    is_in_stock = Column(Boolean, default=True)
    
    # 이미지 정보
    main_image_url = Column(String(1000), nullable=True)
    additional_images = Column(get_json_type(), nullable=True, comment="추가 이미지 URL 목록")
    
    # 옵션 정보
    options = Column(get_json_type(), nullable=True, comment="상품 옵션 정보")
    variants = Column(get_json_type(), nullable=True, comment="상품 변형 정보")
    
    # 배송 정보
    shipping_info = Column(get_json_type(), nullable=True, comment="배송 정보")
    
    # 도매처별 추가 정보
    raw_data = Column(get_json_type(), nullable=True, comment="원본 데이터")
    
    # 상태 정보
    is_active = Column(Boolean, default=True)
    is_collected = Column(Boolean, default=True, comment="수집 완료 여부")
    
    # 메타데이터 - BaseModel의 created_at, updated_at 사용
    # first_collected_at는 created_at로 대체 가능
    # last_updated_at는 updated_at로 대체 가능
    
    # 관계
    wholesaler_account = relationship("WholesalerAccount")


class ExcelUploadLog(BaseModel):
    """엑셀 업로드 로그"""
    __tablename__ = "excel_upload_logs"
    
    wholesaler_account_id = Column(UUID(as_uuid=True), ForeignKey("wholesaler_accounts.id"), nullable=False)
    
    # 파일 정보
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False, comment="파일 해시")
    
    # 처리 결과
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    success_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # 상태
    status = Column(Enum(CollectionStatus), default=CollectionStatus.PENDING)
    error_message = Column(Text, nullable=True)
    
    # 처리 시간 - BaseModel의 created_at, updated_at 사용
    # uploaded_at는 created_at로 대체 가능
    processed_at = Column(DateTime, nullable=True)
    
    # 결과 상세
    processing_log = Column(get_json_type(), nullable=True, comment="처리 로그")
    failed_rows_detail = Column(get_json_type(), nullable=True, comment="실패한 행 상세 정보")
    
    # 관계
    wholesaler_account = relationship("WholesalerAccount")
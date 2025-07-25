"""
SQLAlchemy models for multi-platform e-commerce management system
"""

# Import base classes
from .base import Base, BaseModel, TimestampMixin, SoftDeleteMixin, UUIDMixin, MetadataMixin

# Import user and authentication models
from .user import (
    User, UserRole, UserStatus, UserSession, UserAPIKey
)

# Import platform account models
from .platform_account import (
    PlatformAccount, PlatformType, AccountStatus, PlatformSyncLog, WholesaleAccount
)

# Import product models
from .product import (
    Product, ProductVariant, PlatformListing, ProductPriceHistory, ProductCategory,
    ProductStatus, ProductType, PricingStrategy
)

# Import order models
from .order import (
    Order, OrderItem, OrderPayment, OrderShipment, OrderShipmentItem, OrderStatusHistory,
    OrderStatus, PaymentStatus, ShippingStatus
)

# Import inventory models
from .inventory import (
    Warehouse, InventoryItem, InventoryMovement, StockAdjustment, StockAdjustmentItem,
    StockCount, StockCountItem, MovementType, InventoryStatus
)

# Import AI models
from .ai_log import (
    AILog, AITrainingData, AIModel, AIPrediction, AIExperiment,
    AIOperationType, AIModelType, ExecutionStatus
)

# Import wholesaler models
from .wholesaler import (
    WholesalerAccount, WholesalerType, ConnectionStatus, CollectionStatus,
    CollectionLog, ScheduledCollection, WholesalerProduct, ExcelUploadLog
)

# Import dropshipping models
from .dropshipping import (
    OutOfStockHistory, SupplierReliability, RestockHistory, StockCheckLog,
    PriceHistory, ProfitProtectionLog, StockoutPredictionHistory, DemandAnalysisHistory,
    AutomationRule, AutomationExecution, AlternativeRecommendation, DropshippingSettings
)

# Import CRM models
from .crm import (
    Customer, CustomerLifecycleStage, CustomerSegment, CustomerBehavior,
    RFMAnalysis, CustomerInteraction, CustomerRecommendation, CustomerCampaign,
    CustomerLifecycleEvent, CustomerPreference
)

# Import marketing models
from .marketing import (
    MarketingCampaign, MarketingSegment, MarketingMessage, MarketingAnalytics,
    PromotionCode, AutomationWorkflow, WorkflowNode, WorkflowExecution,
    AutomationTrigger, ABTestVariant, SocialMediaPost,
    CampaignType, CampaignStatus, MessageStatus, TriggerType
)

# Import market trend models
from .market import MarketTrend

# Import pipeline models
from .pipeline import (
    PipelineExecution, PipelineStep, PipelineProductResult, WorkflowTemplate,
    PipelineAlert, PipelineSchedule, WorkflowStatus, StepStatus
)

# Import sales analytics models
from .sales_analytics import (
    SalesAnalytics, MarketplaceSession, TrafficSource, SearchKeyword,
    CompetitorAnalysis, PerformanceReport, DataCollectionLog,
    MarketplaceType, DataCollectionStatus
)

# All models for easy import
__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin", 
    "UUIDMixin",
    "MetadataMixin",
    
    # User models
    "User",
    "UserRole",
    "UserStatus",
    "UserSession",
    "UserAPIKey",
    
    # Platform account models
    "PlatformAccount",
    "PlatformType",
    "AccountStatus",
    "PlatformSyncLog",
    "WholesaleAccount",
    
    # Product models
    "Product",
    "ProductVariant",
    "PlatformListing",
    "ProductPriceHistory",
    "ProductCategory",
    "ProductStatus",
    "ProductType",
    "PricingStrategy",
    
    # Order models
    "Order",
    "OrderItem",
    "OrderPayment",
    "OrderShipment",
    "OrderShipmentItem",
    "OrderStatusHistory",
    "OrderStatus",
    "PaymentStatus",
    "ShippingStatus",
    
    # Inventory models
    "Warehouse",
    "InventoryItem",
    "InventoryMovement",
    "StockAdjustment",
    "StockAdjustmentItem",
    "StockCount",
    "StockCountItem",
    "MovementType",
    "InventoryStatus",
    
    # AI models
    "AILog",
    "AITrainingData",
    "AIModel",
    "AIPrediction",
    "AIExperiment",
    "AIOperationType",
    "AIModelType",
    "ExecutionStatus",
    
    # Wholesaler models
    "WholesalerAccount",
    "WholesalerType",
    "ConnectionStatus",
    "CollectionStatus",
    "CollectionLog",
    "ScheduledCollection", 
    "WholesalerProduct",
    "ExcelUploadLog",
    
    # Dropshipping models
    "OutOfStockHistory",
    "SupplierReliability",
    "RestockHistory",
    "StockCheckLog",
    "PriceHistory",
    "ProfitProtectionLog",
    "StockoutPredictionHistory",
    "DemandAnalysisHistory",
    "AutomationRule",
    "AutomationExecution",
    "AlternativeRecommendation",
    "DropshippingSettings",
    
    # CRM models
    "Customer",
    "CustomerLifecycleStage",
    "CustomerSegment",
    "CustomerBehavior",
    "RFMAnalysis",
    "CustomerInteraction",
    "CustomerRecommendation",
    "CustomerCampaign",
    "CustomerLifecycleEvent",
    "CustomerPreference",
    
    # Marketing models
    "MarketingCampaign",
    "MarketingSegment",
    "MarketingMessage",
    "MarketingAnalytics",
    "PromotionCode",
    "AutomationWorkflow",
    "WorkflowNode",
    "WorkflowExecution",
    "AutomationTrigger",
    "ABTestVariant",
    "SocialMediaPost",
    "CampaignType",
    "CampaignStatus",
    "MessageStatus",
    "TriggerType",
    
    # Market trend models
    "MarketTrend",
    
    # Pipeline models
    "PipelineExecution",
    "PipelineStep", 
    "PipelineProductResult",
    "WorkflowTemplate",
    "PipelineAlert",
    "PipelineSchedule",
    "WorkflowStatus",
    "StepStatus",
    
    # Sales analytics models
    "SalesAnalytics",
    "MarketplaceSession",
    "TrafficSource",
    "SearchKeyword",
    "CompetitorAnalysis",
    "PerformanceReport",
    "DataCollectionLog",
    "MarketplaceType",
    "DataCollectionStatus",
]

# Model registry for database operations
MODELS = [
    # User models
    User,
    UserSession,
    UserAPIKey,
    
    # Platform models
    PlatformAccount,
    PlatformSyncLog,
    WholesaleAccount,
    
    # Product models
    ProductCategory,
    Product,
    ProductVariant,
    PlatformListing,
    ProductPriceHistory,
    
    # Order models
    Order,
    OrderItem,
    OrderPayment,
    OrderShipment,
    OrderShipmentItem,
    OrderStatusHistory,
    
    # Inventory models
    Warehouse,
    InventoryItem,
    InventoryMovement,
    StockAdjustment,
    StockAdjustmentItem,
    StockCount,
    StockCountItem,
    
    # AI models
    AIModel,
    AILog,
    AITrainingData,
    AIPrediction,
    AIExperiment,
    
    # Wholesaler models
    WholesalerAccount,
    CollectionLog,
    ScheduledCollection,
    WholesalerProduct,
    ExcelUploadLog,
    
    # Dropshipping models
    OutOfStockHistory,
    SupplierReliability,
    RestockHistory,
    StockCheckLog,
    PriceHistory,
    ProfitProtectionLog,
    StockoutPredictionHistory,
    DemandAnalysisHistory,
    AutomationRule,
    AutomationExecution,
    AlternativeRecommendation,
    DropshippingSettings,
    
    # CRM models
    Customer,
    CustomerBehavior,
    RFMAnalysis,
    CustomerInteraction,
    CustomerRecommendation,
    CustomerCampaign,
    CustomerLifecycleEvent,
    CustomerPreference,
    
    # Marketing models
    MarketingCampaign,
    MarketingSegment,
    MarketingMessage,
    MarketingAnalytics,
    PromotionCode,
    AutomationWorkflow,
    WorkflowNode,
    WorkflowExecution,
    AutomationTrigger,
    ABTestVariant,
    SocialMediaPost,
    
    # Market trend models
    MarketTrend,
    
    # Pipeline models
    PipelineExecution,
    PipelineStep,
    PipelineProductResult,
    WorkflowTemplate,
    PipelineAlert,
    PipelineSchedule,
    
    # Sales analytics models
    SalesAnalytics,
    MarketplaceSession,
    TrafficSource,
    SearchKeyword,
    CompetitorAnalysis,
    PerformanceReport,
    DataCollectionLog,
]

# Utility function to create all tables
def create_all_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

# Utility function to drop all tables
def drop_all_tables(engine):
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)
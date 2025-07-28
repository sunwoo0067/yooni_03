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

# Import order models - Core models only for Phase 1
from .order_core import (
    Order, OrderItem, OrderPayment, OrderShipment, OrderShipmentItem, OrderStatusHistory,
    OrderStatus, PaymentStatus, ShippingStatus
)

# Import inventory models - REACTIVATED IN PHASE 2.1
from .inventory import (
    Warehouse, InventoryItem, InventoryMovement, StockAdjustment, StockAdjustmentItem,
    StockCount, StockCountItem, MovementType, InventoryStatus
)

# Import AI models - REACTIVATED IN PHASE 2.2
from .ai_log import (
    AILog, AITrainingData, AIModel, AIPrediction, AIExperiment,
    AIOperationType, AIModelType, ExecutionStatus
)

# Import wholesaler models - REACTIVATED IN PHASE 2.3
from .wholesaler import (
    WholesalerAccount, WholesalerType, ConnectionStatus, CollectionStatus,
    CollectionLog, ScheduledCollection, WholesalerProduct, ExcelUploadLog
)

# Import dropshipping models - REACTIVATED IN PHASE 2.3
from .dropshipping import (
    OutOfStockHistory, SupplierReliability, RestockHistory, StockCheckLog,
    PriceHistory, ProfitProtectionLog, StockoutPredictionHistory, DemandAnalysisHistory,
    AutomationRule, AutomationExecution, AlternativeRecommendation, DropshippingSettings,
    DuplicateProductGroup, DuplicateProduct
)

# Import collected product models
from .collected_product import CollectedProduct, CollectionBatch, CollectionStatus as CollectedProductStatus, WholesalerSource
from .collected_product_history import CollectedProductHistory, PriceAlert, ChangeType

# Import security and audit models
from .security_audit import (
    SecurityAuditLog, TokenBlacklist, LoginAttempt, PasswordResetToken
)

# Import RBAC models
from .rbac import (
    Permission, Role, PermissionCategory, PermissionAction, ResourceScope,
    PermissionCondition, UserPermissionAudit, AccessRequest, PermissionDelegation,
    role_permission_association, user_permission_override
)

# Import CRM models - TEMPORARILY DISABLED FOR REFACTORING
# from .crm import (
#     Customer, CustomerLifecycleStage, CustomerSegment, CustomerBehavior,
#     RFMAnalysis, CustomerInteraction, CustomerRecommendation, CustomerCampaign,
#     CustomerLifecycleEvent, CustomerPreference
# )

# Import marketing models - TEMPORARILY DISABLED FOR REFACTORING
# from .marketing import (
#     MarketingCampaign, MarketingSegment, MarketingMessage, MarketingAnalytics,
#     PromotionCode, AutomationWorkflow, WorkflowNode, WorkflowExecution,
#     AutomationTrigger, ABTestVariant, SocialMediaPost,
#     CampaignType, CampaignStatus, MessageStatus, TriggerType
# )

# Import market trend models - TEMPORARILY DISABLED FOR REFACTORING
# from .market import MarketTrend

# Import pipeline models - REACTIVATED IN PHASE 2.4
from .pipeline import (
    PipelineExecution, PipelineStep, PipelineProductResult, WorkflowTemplate,
    PipelineAlert, PipelineSchedule, WorkflowStatus, StepStatus
)

# Import sales analytics models - TEMPORARILY DISABLED FOR REFACTORING
# from .sales_analytics import (
#     SalesAnalytics, MarketplaceSession, TrafficSource, SearchKeyword,
#     CompetitorAnalysis, PerformanceReport, DataCollectionLog,
#     MarketplaceType, DataCollectionStatus
# )

# Core models for Phase 1 - Essential functionality only
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
    
    # Inventory models - REACTIVATED IN PHASE 2.1
    "Warehouse",
    "InventoryItem",
    "InventoryMovement",
    "StockAdjustment",
    "StockAdjustmentItem",
    "StockCount",
    "StockCountItem",
    "MovementType",
    "InventoryStatus",
    
    # AI models - REACTIVATED IN PHASE 2.2
    "AILog",
    "AITrainingData",
    "AIModel",
    "AIPrediction",
    "AIExperiment",
    "AIOperationType",
    "AIModelType",
    "ExecutionStatus",
    
    # Wholesaler models - REACTIVATED IN PHASE 2.3
    "WholesalerAccount",
    "WholesalerType",
    "ConnectionStatus",
    "CollectionStatus",
    "CollectionLog",
    "ScheduledCollection",
    "WholesalerProduct",
    "ExcelUploadLog",
    
    # Dropshipping models - REACTIVATED IN PHASE 2.3
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
    "DuplicateProductGroup",
    "DuplicateProduct",
    
    # Pipeline models - REACTIVATED IN PHASE 2.4
    "PipelineExecution",
    "PipelineStep", 
    "PipelineProductResult",
    "WorkflowTemplate",
    "PipelineAlert",
    "PipelineSchedule",
    "WorkflowStatus",
    "StepStatus",
    
    # Collected product models
    "CollectedProduct",
    "CollectionBatch",
    "CollectedProductStatus",
    "WholesalerSource",
    "CollectedProductHistory",
    "PriceAlert",
    "ChangeType",
    
    # Security and audit models
    "SecurityAuditLog",
    "TokenBlacklist", 
    "LoginAttempt",
    "PasswordResetToken",
    
    # RBAC models
    "Permission",
    "Role",
    "PermissionCategory",
    "PermissionAction",
    "ResourceScope",
    "PermissionCondition",
    "UserPermissionAudit",
    "AccessRequest",
    "PermissionDelegation",
    "role_permission_association",
    "user_permission_override",
    
    # Additional models will be added in Phase 2.4
]

# Core model registry for Phase 1 - Essential functionality only
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
    
    # Inventory models - REACTIVATED IN PHASE 2.1
    Warehouse,
    InventoryItem,
    InventoryMovement,
    StockAdjustment,
    StockAdjustmentItem,
    StockCount,
    StockCountItem,
    
    # AI models - REACTIVATED IN PHASE 2.2
    AILog,
    AITrainingData,
    AIModel,
    AIPrediction,
    AIExperiment,
    
    # Wholesaler models - REACTIVATED IN PHASE 2.3
    WholesalerAccount,
    CollectionLog,
    ScheduledCollection,
    WholesalerProduct,
    ExcelUploadLog,
    
    # Dropshipping models - REACTIVATED IN PHASE 2.3
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
    DuplicateProductGroup,
    DuplicateProduct,
    
    # Pipeline models - REACTIVATED IN PHASE 2.4
    PipelineExecution,
    PipelineStep,
    PipelineProductResult,
    WorkflowTemplate,
    PipelineAlert,
    PipelineSchedule,
    
    # Collected product models
    CollectedProduct,
    CollectionBatch,
    CollectedProductHistory,
    PriceAlert,
    
    # Security and audit models
    SecurityAuditLog,
    TokenBlacklist,
    LoginAttempt,
    PasswordResetToken,
    
    # RBAC models
    Permission,
    Role,
    UserPermissionAudit,
    AccessRequest,
    PermissionDelegation,
    
    # Additional models will be added in Phase 2.4
]

# Utility function to create all tables
def create_all_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

# Utility function to drop all tables
def drop_all_tables(engine):
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)
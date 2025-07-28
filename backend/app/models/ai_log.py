"""
AI optimization and learning models
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import BaseModel, get_json_type


class AIOperationType(enum.Enum):
    """AI operation type enumeration"""
    PRICE_OPTIMIZATION = "price_optimization"
    INVENTORY_PREDICTION = "inventory_prediction"
    DEMAND_FORECASTING = "demand_forecasting"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    TITLE_OPTIMIZATION = "title_optimization"
    DESCRIPTION_GENERATION = "description_generation"
    CATEGORY_CLASSIFICATION = "category_classification"
    IMAGE_ANALYSIS = "image_analysis"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    MARKET_ANALYSIS = "market_analysis"
    CUSTOMER_SEGMENTATION = "customer_segmentation"
    FRAUD_DETECTION = "fraud_detection"


class AIModelType(enum.Enum):
    """AI model type enumeration"""
    NEURAL_NETWORK = "neural_network"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    SVM = "svm"
    CLUSTERING = "clustering"
    NLP_TRANSFORMER = "nlp_transformer"
    COMPUTER_VISION = "computer_vision"


class ExecutionStatus(enum.Enum):
    """AI execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AILog(BaseModel):
    """AI operation logging and tracking"""
    __tablename__ = "ai_logs"
    
    # User and Context
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Operation Details
    operation_type = Column(SQLEnum(AIOperationType), nullable=False, index=True)
    model_type = Column(SQLEnum(AIModelType), nullable=True, index=True)
    model_name = Column(String(200), nullable=True)
    model_version = Column(String(50), nullable=True)
    
    # Execution Information
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Input/Output Data
    input_data = Column(get_json_type(), nullable=True)
    output_data = Column(get_json_type(), nullable=True)
    parameters = Column(get_json_type(), nullable=True)
    
    # Results and Metrics
    confidence_score = Column(Numeric(5, 4), nullable=True)  # 0.0 to 1.0
    accuracy_score = Column(Numeric(5, 4), nullable=True)
    precision_score = Column(Numeric(5, 4), nullable=True)
    recall_score = Column(Numeric(5, 4), nullable=True)
    f1_score = Column(Numeric(5, 4), nullable=True)
    
    # Business Impact
    predicted_impact = Column(get_json_type(), nullable=True)  # Predicted business impact
    actual_impact = Column(get_json_type(), nullable=True)     # Measured actual impact
    roi_estimate = Column(Numeric(10, 4), nullable=True)  # ROI percentage
    
    # Error Information
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Resource Usage
    cpu_usage_percent = Column(Numeric(5, 2), nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    gpu_usage_percent = Column(Numeric(5, 2), nullable=True)
    
    # Context Information
    context_data = Column(get_json_type(), nullable=True)  # Additional context
    environment = Column(String(20), default="production", nullable=False)  # production, staging, development
    
    # Relationships
    user = relationship("User", back_populates="ai_logs")
    training_data = relationship("AITrainingData", back_populates="ai_log", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AILog(operation={self.operation_type.value}, status={self.status.value})>"
    
    def calculate_duration(self):
        """Calculate and set duration"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
    
    def set_completed(self, output_data: Dict[str, Any] = None):
        """Mark operation as completed"""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
        self.calculate_duration()
    
    def set_failed(self, error_message: str, error_stack: str = None):
        """Mark operation as failed"""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_stack = error_stack
        self.calculate_duration()


class AITrainingData(BaseModel):
    """AI model training data and features"""
    __tablename__ = "ai_training_data"
    
    # Reference to AI operation
    ai_log_id = Column(UUID(as_uuid=True), ForeignKey("ai_logs.id"), nullable=False, index=True)
    
    # Data Classification
    data_type = Column(String(50), nullable=False, index=True)  # feature, label, validation
    feature_name = Column(String(200), nullable=True, index=True)
    
    # Data Content
    data_value = Column(get_json_type(), nullable=False)
    data_source = Column(String(200), nullable=True)  # Source of the data
    
    # Quality Metrics
    data_quality_score = Column(Numeric(5, 4), nullable=True)  # 0.0 to 1.0
    is_validated = Column(Boolean, default=False, nullable=False)
    validation_method = Column(String(100), nullable=True)
    
    # Processing Information
    preprocessing_applied = Column(get_json_type(), nullable=True)  # Preprocessing steps
    normalization_params = Column(get_json_type(), nullable=True)
    
    # Temporal Information
    data_timestamp = Column(DateTime, nullable=True, index=True)  # When the data was collected
    expiry_date = Column(DateTime, nullable=True, index=True)     # When the data expires
    
    # Usage Tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    ai_log = relationship("AILog", back_populates="training_data")
    
    def __repr__(self):
        return f"<AITrainingData(feature_name={self.feature_name}, data_type={self.data_type})>"


class AIModel(BaseModel):
    """AI model registry and versioning"""
    __tablename__ = "ai_models"
    
    # Model Identity
    name = Column(String(200), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    model_type = Column(SQLEnum(AIModelType), nullable=False, index=True)
    operation_type = Column(SQLEnum(AIOperationType), nullable=False, index=True)
    
    # Model Description
    description = Column(Text, nullable=True)
    tags = Column(get_json_type(), nullable=True)  # Array of tags
    
    # Model Files and Configuration
    model_path = Column(String(1000), nullable=True)  # Path to model file
    config_path = Column(String(1000), nullable=True)  # Path to configuration
    weights_path = Column(String(1000), nullable=True)  # Path to weights
    
    # Model Metadata
    input_schema = Column(get_json_type(), nullable=True)   # Expected input format
    output_schema = Column(get_json_type(), nullable=True)  # Expected output format
    hyperparameters = Column(get_json_type(), nullable=True)
    
    # Training Information
    training_dataset_size = Column(Integer, nullable=True)
    training_duration_minutes = Column(Integer, nullable=True)
    training_completed_at = Column(DateTime, nullable=True)
    
    # Performance Metrics
    accuracy = Column(Numeric(5, 4), nullable=True)
    precision = Column(Numeric(5, 4), nullable=True)
    recall = Column(Numeric(5, 4), nullable=True)
    f1_score = Column(Numeric(5, 4), nullable=True)
    
    # Validation Metrics
    validation_accuracy = Column(Numeric(5, 4), nullable=True)
    cross_validation_score = Column(Numeric(5, 4), nullable=True)
    
    # Deployment Information
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    deployment_date = Column(DateTime, nullable=True)
    
    # Usage Statistics
    prediction_count = Column(Integer, default=0, nullable=False)
    average_response_time_ms = Column(Integer, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Model Performance in Production
    production_accuracy = Column(Numeric(5, 4), nullable=True)
    drift_score = Column(Numeric(5, 4), nullable=True)  # Model drift detection
    
    def __repr__(self):
        return f"<AIModel(name={self.name}, version={self.version})>"
    
    @property
    def model_id(self) -> str:
        """Generate unique model identifier"""
        return f"{self.name}:{self.version}"


class AIPrediction(BaseModel):
    """AI prediction results and tracking"""
    __tablename__ = "ai_predictions"
    
    # Model Information
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=False, index=True)
    operation_type = Column(SQLEnum(AIOperationType), nullable=False, index=True)
    
    # Input/Output
    input_data = Column(get_json_type(), nullable=False)
    prediction_result = Column(get_json_type(), nullable=False)
    
    # Confidence and Quality
    confidence_score = Column(Numeric(5, 4), nullable=True)
    prediction_quality = Column(String(20), nullable=True)  # high, medium, low
    
    # Context
    context_id = Column(String(100), nullable=True, index=True)  # Product ID, Order ID, etc.
    context_type = Column(String(50), nullable=True)  # product, order, customer
    
    # Timing
    prediction_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Feedback and Validation
    actual_outcome = Column(get_json_type(), nullable=True)  # Actual result for comparison
    feedback_score = Column(Numeric(5, 4), nullable=True)  # User feedback
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_at = Column(DateTime, nullable=True)
    
    # Business Impact
    business_value = Column(Numeric(12, 2), nullable=True)  # Monetary value generated
    action_taken = Column(String(200), nullable=True)  # Action taken based on prediction
    
    # Relationships
    model = relationship("AIModel")
    
    def __repr__(self):
        return f"<AIPrediction(operation={self.operation_type.value}, confidence={self.confidence_score})>"


class AIExperiment(BaseModel):
    """AI experimentation and A/B testing"""
    __tablename__ = "ai_experiments"
    
    # Experiment Details
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)
    
    # Experiment Configuration
    experiment_type = Column(String(50), nullable=False)  # ab_test, multivariate, etc.
    operation_type = Column(SQLEnum(AIOperationType), nullable=False, index=True)
    
    # Models being tested
    control_model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id"), nullable=True)
    test_models = Column(get_json_type(), nullable=True)  # Array of model IDs
    
    # Experiment Parameters
    traffic_split = Column(get_json_type(), nullable=False)  # Traffic allocation
    success_metrics = Column(get_json_type(), nullable=False)  # Metrics to track
    
    # Status and Timeline
    status = Column(String(20), default="draft", nullable=False, index=True)  # draft, running, completed, cancelled
    start_date = Column(DateTime, nullable=True, index=True)
    end_date = Column(DateTime, nullable=True, index=True)
    
    # Results
    results = Column(get_json_type(), nullable=True)
    statistical_significance = Column(Numeric(5, 4), nullable=True)
    winner_model_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Sample Size
    target_sample_size = Column(Integer, nullable=True)
    actual_sample_size = Column(Integer, default=0, nullable=False)
    
    # Relationships
    control_model = relationship("AIModel", foreign_keys=[control_model_id])
    
    def __repr__(self):
        return f"<AIExperiment(name={self.name}, status={self.status})>"
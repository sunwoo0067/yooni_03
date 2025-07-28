"""
Pipeline execution and workflow management models
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel, get_json_type


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineExecution(BaseModel):
    """Main pipeline execution tracking"""
    __tablename__ = "pipeline_executions"
    
    workflow_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    workflow_name = Column(String(100), nullable=False)
    status = Column(String(20), default=WorkflowStatus.PENDING, nullable=False, index=True)
    
    # Execution timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)
    
    # Progress tracking
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    
    # Product processing
    total_products_to_process = Column(Integer, default=0)
    products_processed = Column(Integer, default=0)
    products_succeeded = Column(Integer, default=0)
    products_failed = Column(Integer, default=0)
    
    # Performance metrics
    success_rate = Column(Numeric(5, 2), default=0.00)
    processing_rate = Column(Numeric(10, 2), default=0.00)  # products per minute
    error_rate = Column(Numeric(5, 2), default=0.00)
    
    # Configuration and results
    execution_config = Column(get_json_type(), nullable=True)  # Original config used
    results_summary = Column(get_json_type(), nullable=True)   # Final results
    error_log = Column(Text, nullable=True)
    
    # Resource usage
    cpu_usage_avg = Column(Numeric(5, 2), nullable=True)
    memory_usage_avg = Column(Numeric(10, 2), nullable=True)  # MB
    
    # Relationships
    steps = relationship("PipelineStep", back_populates="execution", cascade="all, delete-orphan")
    product_results = relationship("PipelineProductResult", back_populates="execution")
    
    def calculate_progress(self) -> float:
        """Calculate overall progress percentage"""
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate"""
        if self.products_processed == 0:
            return 0.0
        return (self.products_succeeded / self.products_processed) * 100
    
    def get_estimated_time_remaining(self) -> Optional[int]:
        """Get estimated minutes remaining"""
        if not self.started_at or self.processing_rate <= 0:
            return None
        
        remaining_products = self.total_products_to_process - self.products_processed
        return int(remaining_products / self.processing_rate)


class PipelineStep(BaseModel):
    """Individual pipeline step tracking"""
    __tablename__ = "pipeline_steps"
    
    execution_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_executions.id"), nullable=False)
    step_name = Column(String(100), nullable=False)
    step_type = Column(String(50), nullable=False)  # sourcing, processing, registration, etc.
    step_order = Column(Integer, nullable=False)
    
    status = Column(String(20), default=StepStatus.PENDING, nullable=False)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Progress
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    succeeded_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Configuration and results
    step_config = Column(get_json_type(), nullable=True)
    step_results = Column(get_json_type(), nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Performance
    processing_rate = Column(Numeric(10, 2), default=0.00)
    resource_usage = Column(get_json_type(), nullable=True)
    
    # Relationships
    execution = relationship("PipelineExecution", back_populates="steps")
    
    def calculate_duration(self):
        """Calculate and set duration"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())


class PipelineProductResult(BaseModel):
    """Results for individual products in pipeline"""
    __tablename__ = "pipeline_product_results"
    
    execution_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_executions.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    product_code = Column(String(100), nullable=True)
    
    # Processing status for each stage
    sourcing_status = Column(String(20), default="pending")
    processing_status = Column(String(20), default="pending")
    registration_status = Column(String(20), default="pending")
    
    # Timing for each stage
    sourcing_completed_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    registration_completed_at = Column(DateTime, nullable=True)
    
    # Results for each stage
    sourcing_score = Column(Numeric(5, 2), nullable=True)
    sourcing_reasons = Column(get_json_type(), nullable=True)
    
    processing_changes = Column(get_json_type(), nullable=True)
    processing_quality_score = Column(Numeric(5, 2), nullable=True)
    
    registration_platforms = Column(get_json_type(), nullable=True)
    registration_results = Column(get_json_type(), nullable=True)
    
    # Overall result
    final_status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    total_processing_time = Column(Integer, nullable=True)  # seconds
    
    # Relationships
    execution = relationship("PipelineExecution", back_populates="product_results")


class WorkflowTemplate(BaseModel):
    """Predefined workflow templates"""
    __tablename__ = "workflow_templates"
    
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0")
    
    # Template configuration
    steps_config = Column(get_json_type(), nullable=False)  # Step definitions
    default_config = Column(get_json_type(), nullable=True)  # Default parameters
    
    # Metadata
    category = Column(String(50), nullable=True)
    tags = Column(get_json_type(), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()


class PipelineAlert(BaseModel):
    """Pipeline alerts and notifications"""
    __tablename__ = "pipeline_alerts"
    
    execution_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_executions.id"), nullable=True)
    alert_type = Column(String(50), nullable=False)  # error, warning, info, success
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Alert details
    component = Column(String(100), nullable=True)  # Which component triggered
    step_name = Column(String(100), nullable=True)
    product_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Status
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Action taken
    action_required = Column(Boolean, default=False)
    action_taken = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Additional data
    alert_data = Column(get_json_type(), nullable=True)
    
    # Relationships
    execution = relationship("PipelineExecution")
    
    def acknowledge(self, user: str):
        """Acknowledge the alert"""
        self.is_acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = datetime.utcnow()
    
    def resolve(self, action_description: str):
        """Mark alert as resolved"""
        self.action_taken = action_description
        self.resolved_at = datetime.utcnow()


class PipelineSchedule(BaseModel):
    """Scheduled pipeline executions"""
    __tablename__ = "pipeline_schedules"
    
    name = Column(String(100), nullable=False)
    workflow_template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=False)
    
    # Schedule configuration
    is_active = Column(Boolean, default=True)
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), default="UTC")
    
    # Execution limits
    max_parallel_executions = Column(Integer, default=1)
    timeout_minutes = Column(Integer, default=120)
    
    # Configuration
    execution_config = Column(get_json_type(), nullable=True)
    
    # Status tracking
    last_execution_at = Column(DateTime, nullable=True)
    next_execution_at = Column(DateTime, nullable=True)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Relationships
    template = relationship("WorkflowTemplate")
    
    def calculate_success_rate(self) -> float:
        """Calculate execution success rate"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
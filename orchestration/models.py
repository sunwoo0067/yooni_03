"""
Workflow orchestration models for managing automated workflows and business processes.
"""
import json
from typing import Any, Dict, Optional, List
from datetime import timedelta, datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField


class Workflow(models.Model):
    """
    Defines workflow templates for various business processes.
    Each workflow contains a series of steps that are executed in order.
    """
    
    # Workflow types
    WORKFLOW_TYPE_CHOICES = [
        ('product_import', 'Product Import'),
        ('listing_creation', 'Listing Creation'),
        ('inventory_sync', 'Inventory Sync'),
        ('order_processing', 'Order Processing'),
        ('price_optimization', 'Price Optimization'),
        ('data_enrichment', 'Data Enrichment'),
        ('custom', 'Custom Workflow'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('draft', 'Draft'),
        ('deprecated', 'Deprecated'),
    ]
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Workflow template name"
    )
    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique identifier code"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of what this workflow does"
    )
    workflow_type = models.CharField(
        max_length=50,
        choices=WORKFLOW_TYPE_CHOICES,
        help_text="Type of workflow"
    )
    
    # Configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workflow-specific configuration"
    )
    
    # Execution Settings
    max_retries = models.IntegerField(
        default=3,
        help_text="Maximum retry attempts for failed steps"
    )
    retry_delay_seconds = models.IntegerField(
        default=300,
        help_text="Delay between retry attempts in seconds"
    )
    timeout_minutes = models.IntegerField(
        default=60,
        help_text="Maximum execution time in minutes"
    )
    
    # Scheduling
    is_scheduled = models.BooleanField(
        default=False,
        help_text="Whether this workflow runs on a schedule"
    )
    schedule_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Schedule configuration (cron expression, frequency, etc.)"
    )
    
    # Status and Metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    version = models.IntegerField(
        default=1,
        help_text="Workflow version number"
    )
    
    # Tracking
    total_executions = models.IntegerField(
        default=0,
        help_text="Total number of executions"
    )
    successful_executions = models.IntegerField(
        default=0,
        help_text="Number of successful executions"
    )
    failed_executions = models.IntegerField(
        default=0,
        help_text="Number of failed executions"
    )
    average_duration_seconds = models.FloatField(
        default=0.0,
        help_text="Average execution duration in seconds"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflows_created'
    )
    
    class Meta:
        db_table = 'workflows'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['workflow_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.workflow_type})"
    
    def save(self, *args, **kwargs):
        """Override save to ensure code is lowercase."""
        self.code = self.code.lower()
        super().save(*args, **kwargs)
    
    def get_steps(self):
        """Get all steps for this workflow in order."""
        return self.steps.all().order_by('order')
    
    def can_execute(self) -> bool:
        """Check if workflow can be executed."""
        return self.status == 'active' and self.steps.exists()


class WorkflowStep(models.Model):
    """
    Defines individual steps within a workflow.
    Each step represents a specific action or operation.
    """
    
    # Step types
    STEP_TYPE_CHOICES = [
        ('data_fetch', 'Fetch Data'),
        ('data_transform', 'Transform Data'),
        ('data_validate', 'Validate Data'),
        ('api_call', 'API Call'),
        ('database_query', 'Database Query'),
        ('condition_check', 'Conditional Check'),
        ('parallel_process', 'Parallel Process'),
        ('notification', 'Send Notification'),
        ('ai_process', 'AI Processing'),
        ('custom', 'Custom Step'),
    ]
    
    # Relationships
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text="Step name"
    )
    step_type = models.CharField(
        max_length=50,
        choices=STEP_TYPE_CHOICES,
        help_text="Type of step"
    )
    description = models.TextField(
        blank=True,
        help_text="What this step does"
    )
    
    # Execution Order
    order = models.IntegerField(
        help_text="Execution order (lower numbers execute first)"
    )
    
    # Configuration
    config = models.JSONField(
        default=dict,
        help_text="Step-specific configuration"
    )
    
    # Dependencies
    depends_on_steps = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependent_steps',
        help_text="Steps that must complete before this one"
    )
    
    # Execution Settings
    is_optional = models.BooleanField(
        default=False,
        help_text="Whether failure of this step should stop the workflow"
    )
    can_retry = models.BooleanField(
        default=True,
        help_text="Whether this step can be retried on failure"
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="Maximum retry attempts (overrides workflow setting)"
    )
    timeout_seconds = models.IntegerField(
        default=300,
        help_text="Step timeout in seconds"
    )
    
    # Conditional Execution
    condition = models.JSONField(
        default=dict,
        blank=True,
        help_text="Conditions that must be met for step to execute"
    )
    
    # Parallel Execution
    can_run_parallel = models.BooleanField(
        default=False,
        help_text="Whether this step can run in parallel with others"
    )
    parallel_group = models.CharField(
        max_length=50,
        blank=True,
        help_text="Group identifier for parallel execution"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_steps'
        unique_together = [['workflow', 'order']]
        ordering = ['workflow', 'order']
        indexes = [
            models.Index(fields=['workflow', 'order']),
            models.Index(fields=['step_type']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - Step {self.order}: {self.name}"
    
    def get_executor_class(self):
        """Get the appropriate executor class for this step type."""
        from .executors import get_step_executor
        return get_step_executor(self.step_type)


class WorkflowExecution(models.Model):
    """
    Tracks individual workflow execution instances.
    Each execution represents one run of a workflow.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('paused', 'Paused'),
    ]
    
    # Trigger types
    TRIGGER_TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('scheduled', 'Scheduled'),
        ('api', 'API Trigger'),
        ('event', 'Event Triggered'),
        ('webhook', 'Webhook'),
    ]
    
    # Relationships
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    triggered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_executions_triggered'
    )
    
    # Execution Information
    execution_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique execution identifier"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_TYPE_CHOICES,
        help_text="How the workflow was triggered"
    )
    
    # Input/Output
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Input parameters for the workflow"
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output/results from the workflow"
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Shared context data between steps"
    )
    
    # Progress Tracking
    total_steps = models.IntegerField(
        default=0,
        help_text="Total number of steps in workflow"
    )
    completed_steps = models.IntegerField(
        default=0,
        help_text="Number of completed steps"
    )
    current_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_executions',
        help_text="Currently executing step"
    )
    
    # Timing
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution completed"
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Total execution duration in seconds"
    )
    
    # Error Handling
    error_message = models.TextField(
        blank=True,
        help_text="Error message if execution failed"
    )
    error_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='failed_executions',
        help_text="Step where error occurred"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    
    # Metadata
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Tags for categorizing executions"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this execution"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['execution_id']),
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['trigger_type']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.execution_id}"
    
    def save(self, *args, **kwargs):
        """Generate execution ID if not set."""
        if not self.execution_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.execution_id = f"{self.workflow.code}-{timestamp}"
        super().save(*args, **kwargs)
    
    @property
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status == 'running'
    
    @property
    def is_complete(self) -> bool:
        """Check if execution has completed (successfully or not)."""
        return self.status in ['completed', 'failed', 'cancelled']
    
    def start_execution(self):
        """Mark execution as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete_execution(self, success: bool = True, error_message: str = ''):
        """Mark execution as completed."""
        self.status = 'completed' if success else 'failed'
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'duration_seconds', 'error_message', 'updated_at'])
    
    def update_progress(self, completed_steps: int, current_step: Optional[WorkflowStep] = None):
        """Update execution progress."""
        self.completed_steps = completed_steps
        if current_step:
            self.current_step = current_step
        self.save(update_fields=['completed_steps', 'current_step', 'updated_at'])


class WorkflowStepExecution(models.Model):
    """
    Tracks execution of individual workflow steps.
    Each record represents one step execution within a workflow execution.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('retrying', 'Retrying'),
    ]
    
    # Relationships
    workflow_execution = models.ForeignKey(
        WorkflowExecution,
        on_delete=models.CASCADE,
        related_name='step_executions'
    )
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    
    # Execution Information
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    execution_order = models.IntegerField(
        help_text="Actual execution order"
    )
    
    # Input/Output
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Input data for this step"
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output data from this step"
    )
    
    # Timing
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When step execution started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When step execution completed"
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Step execution duration in seconds"
    )
    
    # Error Handling
    error_message = models.TextField(
        blank=True,
        help_text="Error message if step failed"
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed error information"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts for this step"
    )
    
    # Metrics
    metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Step-specific metrics (e.g., records processed)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workflow_step_executions'
        unique_together = [['workflow_execution', 'workflow_step']]
        ordering = ['workflow_execution', 'execution_order']
        indexes = [
            models.Index(fields=['workflow_execution', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.workflow_execution.execution_id} - {self.workflow_step.name}"
    
    def start_step(self):
        """Mark step as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete_step(self, success: bool = True, output_data: Dict[str, Any] = None, 
                     error_message: str = '', metrics: Dict[str, Any] = None):
        """Mark step as completed."""
        self.status = 'completed' if success else 'failed'
        self.completed_at = timezone.now()
        
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        if output_data:
            self.output_data = output_data
        
        if error_message:
            self.error_message = error_message
        
        if metrics:
            self.metrics = metrics
        
        self.save(update_fields=['status', 'completed_at', 'duration_seconds', 
                               'output_data', 'error_message', 'metrics', 'updated_at'])
    
    def retry_step(self):
        """Mark step for retry."""
        self.status = 'retrying'
        self.retry_count += 1
        self.save(update_fields=['status', 'retry_count', 'updated_at'])


class WorkflowSchedule(models.Model):
    """
    Manages scheduled execution of workflows.
    Supports various scheduling patterns (cron, interval, specific times).
    """
    
    # Schedule type choices
    SCHEDULE_TYPE_CHOICES = [
        ('cron', 'Cron Expression'),
        ('interval', 'Fixed Interval'),
        ('daily', 'Daily at Specific Time'),
        ('weekly', 'Weekly on Specific Days'),
        ('monthly', 'Monthly on Specific Days'),
    ]
    
    # Relationships
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    
    # Schedule Information
    name = models.CharField(
        max_length=255,
        help_text="Schedule name"
    )
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPE_CHOICES,
        help_text="Type of schedule"
    )
    
    # Schedule Configuration
    cron_expression = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cron expression (for cron type)"
    )
    interval_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Interval in minutes (for interval type)"
    )
    time_of_day = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of day for daily schedules"
    )
    days_of_week = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="Days of week (0=Monday, 6=Sunday)"
    )
    days_of_month = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="Days of month (1-31)"
    )
    
    # Execution Settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether schedule is active"
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Timezone for schedule"
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default input data for scheduled executions"
    )
    
    # Tracking
    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last scheduled execution"
    )
    next_run_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Next scheduled execution"
    )
    total_runs = models.IntegerField(
        default=0,
        help_text="Total number of scheduled runs"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_schedules_created'
    )
    
    class Meta:
        db_table = 'workflow_schedules'
        ordering = ['workflow', 'name']
        indexes = [
            models.Index(fields=['is_active', 'next_run_at']),
            models.Index(fields=['workflow', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.name}"
    
    def calculate_next_run(self) -> Optional[datetime]:
        """Calculate the next run time based on schedule configuration."""
        # This would be implemented based on schedule type
        # For now, return None
        return None
    
    def is_due(self) -> bool:
        """Check if schedule is due for execution."""
        if not self.is_active or not self.next_run_at:
            return False
        return timezone.now() >= self.next_run_at

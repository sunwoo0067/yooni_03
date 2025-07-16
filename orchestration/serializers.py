"""
Serializers for the orchestration app.
"""
from rest_framework import serializers

from .models import (
    Workflow, WorkflowStep, WorkflowExecution, 
    WorkflowStepExecution, WorkflowSchedule
)


class WorkflowStepSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowStep model."""
    
    class Meta:
        model = WorkflowStep
        fields = [
            'id', 'name', 'step_type', 'description', 'order', 'config',
            'is_optional', 'can_retry', 'max_retries', 'timeout_seconds',
            'can_run_parallel', 'parallel_group', 'condition',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowSerializer(serializers.ModelSerializer):
    """Serializer for Workflow model."""
    
    steps = WorkflowStepSerializer(many=True, read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'code', 'description', 'workflow_type', 'status',
            'config', 'max_retries', 'retry_delay_seconds', 'timeout_minutes',
            'is_scheduled', 'schedule_config', 'version',
            'total_executions', 'successful_executions', 'failed_executions',
            'average_duration_seconds', 'success_rate', 'steps',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_executions', 'successful_executions', 'failed_executions',
            'average_duration_seconds', 'created_at', 'updated_at'
        ]
    
    def get_success_rate(self, obj):
        """Calculate success rate percentage."""
        if obj.total_executions > 0:
            return round((obj.successful_executions / obj.total_executions) * 100, 2)
        return 0.0


class WorkflowStepExecutionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowStepExecution model."""
    
    step_name = serializers.CharField(source='workflow_step.name', read_only=True)
    step_type = serializers.CharField(source='workflow_step.step_type', read_only=True)
    
    class Meta:
        model = WorkflowStepExecution
        fields = [
            'id', 'workflow_step', 'step_name', 'step_type', 'status',
            'execution_order', 'input_data', 'output_data', 'metrics',
            'started_at', 'completed_at', 'duration_seconds',
            'error_message', 'error_details', 'retry_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'step_name', 'step_type', 'started_at', 'completed_at',
            'duration_seconds', 'created_at', 'updated_at'
        ]


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowExecution model."""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    workflow_type = serializers.CharField(source='workflow.workflow_type', read_only=True)
    step_executions = WorkflowStepExecutionSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'workflow_name', 'workflow_type', 'execution_id',
            'status', 'trigger_type', 'triggered_by', 'input_data', 'output_data',
            'context_data', 'total_steps', 'completed_steps', 'current_step',
            'progress_percentage', 'started_at', 'completed_at', 'duration_seconds',
            'error_message', 'error_step', 'retry_count', 'tags', 'notes',
            'step_executions', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'workflow_name', 'workflow_type', 'execution_id',
            'progress_percentage', 'started_at', 'completed_at', 'duration_seconds',
            'step_executions', 'created_at', 'updated_at'
        ]
    
    def get_progress_percentage(self, obj):
        """Calculate progress percentage."""
        if obj.total_steps > 0:
            return round((obj.completed_steps / obj.total_steps) * 100, 1)
        return 0.0


class WorkflowScheduleSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowSchedule model."""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    
    class Meta:
        model = WorkflowSchedule
        fields = [
            'id', 'workflow', 'workflow_name', 'name', 'schedule_type',
            'cron_expression', 'interval_minutes', 'time_of_day',
            'days_of_week', 'days_of_month', 'is_active', 'timezone',
            'input_data', 'last_run_at', 'next_run_at', 'total_runs',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'workflow_name', 'last_run_at', 'total_runs',
            'created_at', 'updated_at'
        ]
"""
Django admin configuration for orchestration models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    Workflow, WorkflowStep, WorkflowExecution, 
    WorkflowStepExecution, WorkflowSchedule
)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin interface for Workflow model."""
    
    list_display = [
        'name', 'workflow_type', 'status', 'total_executions', 
        'successful_executions', 'failed_executions', 'success_rate',
        'average_duration', 'created_at'
    ]
    list_filter = ['workflow_type', 'status', 'is_scheduled', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = [
        'total_executions', 'successful_executions', 'failed_executions',
        'average_duration_seconds', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'workflow_type', 'status')
        }),
        ('Configuration', {
            'fields': ('config', 'max_retries', 'retry_delay_seconds', 'timeout_minutes')
        }),
        ('Scheduling', {
            'fields': ('is_scheduled', 'schedule_config'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'total_executions', 'successful_executions', 'failed_executions',
                'average_duration_seconds'
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('version', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def success_rate(self, obj):
        """Calculate success rate percentage."""
        if obj.total_executions > 0:
            rate = (obj.successful_executions / obj.total_executions) * 100
            color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, rate
            )
        return '-'
    success_rate.short_description = 'Success Rate'
    
    def average_duration(self, obj):
        """Format average duration."""
        if obj.average_duration_seconds > 0:
            minutes = int(obj.average_duration_seconds // 60)
            seconds = int(obj.average_duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        return '-'
    average_duration.short_description = 'Avg Duration'


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowStep model."""
    
    list_display = [
        'workflow', 'order', 'name', 'step_type', 'is_optional', 
        'can_retry', 'can_run_parallel', 'timeout_seconds'
    ]
    list_filter = ['step_type', 'is_optional', 'can_retry', 'can_run_parallel']
    search_fields = ['name', 'description', 'workflow__name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workflow', 'name', 'step_type', 'description', 'order')
        }),
        ('Configuration', {
            'fields': ('config',)
        }),
        ('Dependencies', {
            'fields': ('depends_on_steps',)
        }),
        ('Execution Settings', {
            'fields': (
                'is_optional', 'can_retry', 'max_retries', 'timeout_seconds'
            )
        }),
        ('Parallel Execution', {
            'fields': ('can_run_parallel', 'parallel_group'),
            'classes': ('collapse',)
        }),
        ('Conditions', {
            'fields': ('condition',),
            'classes': ('collapse',)
        })
    )


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowExecution model."""
    
    list_display = [
        'execution_id', 'workflow', 'status', 'trigger_type', 'progress',
        'duration', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'trigger_type', 'workflow__workflow_type', 'created_at']
    search_fields = ['execution_id', 'workflow__name', 'triggered_by__username']
    readonly_fields = [
        'execution_id', 'started_at', 'completed_at', 'duration_seconds',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Execution Information', {
            'fields': (
                'workflow', 'execution_id', 'status', 'trigger_type', 'triggered_by'
            )
        }),
        ('Progress', {
            'fields': ('total_steps', 'completed_steps', 'current_step')
        }),
        ('Data', {
            'fields': ('input_data', 'output_data', 'context_data'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_step', 'retry_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('tags', 'notes'),
            'classes': ('collapse',)
        })
    )
    
    def progress(self, obj):
        """Show progress as a percentage bar."""
        if obj.total_steps > 0:
            percentage = (obj.completed_steps / obj.total_steps) * 100
            color = 'green' if obj.status == 'completed' else 'blue' if obj.status == 'running' else 'red'
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
                '{}/{}</div></div>',
                percentage, color, obj.completed_steps, obj.total_steps
            )
        return '-'
    progress.short_description = 'Progress'
    
    def duration(self, obj):
        """Format execution duration."""
        if obj.duration_seconds:
            minutes = int(obj.duration_seconds // 60)
            seconds = int(obj.duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        elif obj.started_at and not obj.completed_at:
            from django.utils import timezone
            running_time = (timezone.now() - obj.started_at).total_seconds()
            minutes = int(running_time // 60)
            seconds = int(running_time % 60)
            return f"{minutes}m {seconds}s (running)"
        return '-'
    duration.short_description = 'Duration'


@admin.register(WorkflowStepExecution)
class WorkflowStepExecutionAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowStepExecution model."""
    
    list_display = [
        'workflow_execution', 'workflow_step', 'status', 'execution_order',
        'duration', 'retry_count', 'started_at'
    ]
    list_filter = ['status', 'workflow_step__step_type', 'created_at']
    search_fields = [
        'workflow_execution__execution_id', 'workflow_step__name',
        'workflow_execution__workflow__name'
    ]
    readonly_fields = [
        'started_at', 'completed_at', 'duration_seconds', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Step Information', {
            'fields': ('workflow_execution', 'workflow_step', 'status', 'execution_order')
        }),
        ('Data', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_details', 'retry_count'),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': ('metrics',),
            'classes': ('collapse',)
        })
    )
    
    def duration(self, obj):
        """Format step duration."""
        if obj.duration_seconds:
            if obj.duration_seconds < 60:
                return f"{obj.duration_seconds:.1f}s"
            else:
                minutes = int(obj.duration_seconds // 60)
                seconds = obj.duration_seconds % 60
                return f"{minutes}m {seconds:.1f}s"
        return '-'
    duration.short_description = 'Duration'


@admin.register(WorkflowSchedule)
class WorkflowScheduleAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowSchedule model."""
    
    list_display = [
        'workflow', 'name', 'schedule_type', 'is_active', 'next_run_at',
        'last_run_at', 'total_runs'
    ]
    list_filter = ['schedule_type', 'is_active', 'workflow__workflow_type']
    search_fields = ['name', 'workflow__name']
    readonly_fields = ['last_run_at', 'total_runs', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workflow', 'name', 'schedule_type', 'is_active')
        }),
        ('Schedule Configuration', {
            'fields': (
                'cron_expression', 'interval_minutes', 'time_of_day',
                'days_of_week', 'days_of_month'
            )
        }),
        ('Execution Settings', {
            'fields': ('timezone', 'input_data')
        }),
        ('Tracking', {
            'fields': ('last_run_at', 'next_run_at', 'total_runs'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

"""
Celery tasks for workflow orchestration and execution.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from celery import shared_task, group, chain, chord
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    Workflow, WorkflowExecution, WorkflowStep, 
    WorkflowStepExecution, WorkflowSchedule
)
from .engine import WorkflowEngine
from .executors import get_step_executor

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def execute_workflow(self, workflow_id: int, input_data: Dict[str, Any] = None, 
                    triggered_by_user_id: Optional[int] = None, 
                    trigger_type: str = 'manual') -> Dict[str, Any]:
    """
    Execute a complete workflow.
    
    Args:
        workflow_id: ID of the workflow to execute
        input_data: Input data for the workflow
        triggered_by_user_id: ID of user who triggered the workflow
        trigger_type: How the workflow was triggered
        
    Returns:
        Dictionary with execution results
    """
    try:
        workflow = Workflow.objects.get(id=workflow_id)
        logger.info(f"Starting execution of workflow: {workflow.name}")
        
        if not workflow.can_execute():
            return {
                'success': False,
                'error': 'Workflow cannot be executed (inactive or no steps)',
                'workflow_id': workflow_id
            }
        
        # Create workflow execution record
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by_id=triggered_by_user_id,
            trigger_type=trigger_type,
            input_data=input_data or {},
            total_steps=workflow.steps.count()
        )
        
        logger.info(f"Created execution: {execution.execution_id}")
        
        # Start execution
        execution.start_execution()
        
        # Initialize workflow engine
        engine = WorkflowEngine(execution)
        
        try:
            # Execute workflow
            result = engine.execute()
            
            # Update execution status
            if result.get('success', False):
                execution.complete_execution(success=True)
                execution.output_data = result.get('output_data', {})
                execution.save(update_fields=['output_data'])
                
                # Update workflow statistics
                workflow.total_executions += 1
                workflow.successful_executions += 1
                if execution.duration_seconds:
                    # Update average duration
                    total_duration = (workflow.average_duration_seconds * 
                                    (workflow.successful_executions - 1) + 
                                    execution.duration_seconds)
                    workflow.average_duration_seconds = total_duration / workflow.successful_executions
                workflow.save(update_fields=[
                    'total_executions', 'successful_executions', 'average_duration_seconds'
                ])
                
                logger.info(f"Workflow execution completed successfully: {execution.execution_id}")
            else:
                error_message = result.get('error', 'Unknown execution error')
                execution.complete_execution(success=False, error_message=error_message)
                execution.error_step = result.get('error_step')
                execution.save(update_fields=['error_step'])
                
                # Update workflow statistics
                workflow.total_executions += 1
                workflow.failed_executions += 1
                workflow.save(update_fields=['total_executions', 'failed_executions'])
                
                logger.error(f"Workflow execution failed: {execution.execution_id} - {error_message}")
            
            return {
                'success': result.get('success', False),
                'execution_id': execution.execution_id,
                'workflow_id': workflow_id,
                'workflow_name': workflow.name,
                'output_data': result.get('output_data', {}),
                'error': result.get('error'),
                'duration_seconds': execution.duration_seconds
            }
            
        except Exception as e:
            error_message = f"Workflow execution error: {str(e)}"
            execution.complete_execution(success=False, error_message=error_message)
            
            workflow.total_executions += 1
            workflow.failed_executions += 1
            workflow.save(update_fields=['total_executions', 'failed_executions'])
            
            logger.error(f"Workflow execution exception: {execution.execution_id} - {error_message}")
            
            return {
                'success': False,
                'execution_id': execution.execution_id,
                'workflow_id': workflow_id,
                'error': error_message
            }
        
    except Workflow.DoesNotExist:
        error_msg = f"Workflow with ID {workflow_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'workflow_id': workflow_id
        }
        
    except Exception as e:
        error_msg = f"Error executing workflow {workflow_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def execute_workflow_step(self, step_execution_id: int) -> Dict[str, Any]:
    """
    Execute a single workflow step.
    
    Args:
        step_execution_id: ID of the step execution
        
    Returns:
        Dictionary with step execution results
    """
    try:
        step_execution = WorkflowStepExecution.objects.get(id=step_execution_id)
        workflow_step = step_execution.workflow_step
        
        logger.info(f"Executing step: {workflow_step.name} (ID: {step_execution_id})")
        
        # Start step execution
        step_execution.start_step()
        
        try:
            # Get executor for this step type
            executor_class = get_step_executor(workflow_step.step_type)
            if not executor_class:
                raise ValueError(f"No executor found for step type: {workflow_step.step_type}")
            
            # Initialize executor
            executor = executor_class(
                step=workflow_step,
                execution=step_execution.workflow_execution,
                step_execution=step_execution
            )
            
            # Execute the step
            result = executor.execute(step_execution.input_data)
            
            # Handle result
            if result.get('success', False):
                step_execution.complete_step(
                    success=True,
                    output_data=result.get('output_data', {}),
                    metrics=result.get('metrics', {})
                )
                logger.info(f"Step completed successfully: {workflow_step.name}")
            else:
                error_message = result.get('error', 'Unknown step execution error')
                step_execution.complete_step(
                    success=False,
                    error_message=error_message
                )
                logger.error(f"Step failed: {workflow_step.name} - {error_message}")
            
            return {
                'success': result.get('success', False),
                'step_execution_id': step_execution_id,
                'step_name': workflow_step.name,
                'output_data': result.get('output_data', {}),
                'error': result.get('error'),
                'metrics': result.get('metrics', {}),
                'duration_seconds': step_execution.duration_seconds
            }
            
        except Exception as e:
            error_message = f"Step execution error: {str(e)}"
            step_execution.complete_step(success=False, error_message=error_message)
            logger.error(f"Step execution exception: {workflow_step.name} - {error_message}")
            
            return {
                'success': False,
                'step_execution_id': step_execution_id,
                'step_name': workflow_step.name,
                'error': error_message
            }
        
    except WorkflowStepExecution.DoesNotExist:
        error_msg = f"WorkflowStepExecution with ID {step_execution_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'step_execution_id': step_execution_id
        }
        
    except Exception as e:
        error_msg = f"Error executing workflow step {step_execution_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise self.retry(exc=e, countdown=30)


@shared_task
def execute_parallel_workflow_steps(step_execution_ids: List[int]) -> Dict[str, Any]:
    """
    Execute multiple workflow steps in parallel.
    
    Args:
        step_execution_ids: List of step execution IDs to run in parallel
        
    Returns:
        Dictionary with parallel execution results
    """
    logger.info(f"Executing {len(step_execution_ids)} steps in parallel")
    
    # Create parallel task group
    job = group(execute_workflow_step.s(step_id) for step_id in step_execution_ids)
    result = job.apply_async()
    
    # Wait for all tasks to complete
    results = result.get()
    
    # Aggregate results
    successful_steps = sum(1 for r in results if r.get('success', False))
    failed_steps = len(results) - successful_steps
    
    return {
        'success': failed_steps == 0,
        'total_steps': len(step_execution_ids),
        'successful_steps': successful_steps,
        'failed_steps': failed_steps,
        'step_results': results
    }


@shared_task
def schedule_workflow_executions() -> Dict[str, Any]:
    """
    Check for scheduled workflows and trigger executions.
    
    Returns:
        Dictionary with scheduling results
    """
    logger.info("Checking for scheduled workflow executions")
    
    # Get active schedules that are due
    due_schedules = WorkflowSchedule.objects.filter(
        is_active=True,
        workflow__status='active'
    )
    
    executions_started = []
    
    for schedule in due_schedules:
        try:
            if schedule.is_due():
                # Start workflow execution
                result = execute_workflow.delay(
                    workflow_id=schedule.workflow.id,
                    input_data=schedule.input_data,
                    trigger_type='scheduled'
                )
                
                # Update schedule
                schedule.last_run_at = timezone.now()
                schedule.total_runs += 1
                schedule.next_run_at = schedule.calculate_next_run()
                schedule.save(update_fields=['last_run_at', 'total_runs', 'next_run_at'])
                
                executions_started.append({
                    'schedule_id': schedule.id,
                    'workflow_id': schedule.workflow.id,
                    'workflow_name': schedule.workflow.name,
                    'task_id': result.id
                })
                
                logger.info(f"Started scheduled execution for workflow: {schedule.workflow.name}")
                
        except Exception as e:
            logger.error(f"Error scheduling workflow {schedule.workflow.name}: {e}")
    
    return {
        'success': True,
        'schedules_checked': due_schedules.count(),
        'executions_started': len(executions_started),
        'started_executions': executions_started
    }


@shared_task
def retry_failed_workflow_execution(execution_id: int) -> Dict[str, Any]:
    """
    Retry a failed workflow execution.
    
    Args:
        execution_id: ID of the execution to retry
        
    Returns:
        Dictionary with retry results
    """
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        
        if execution.status != 'failed':
            return {
                'success': False,
                'error': 'Execution is not in failed state',
                'execution_id': execution_id
            }
        
        if execution.retry_count >= execution.workflow.max_retries:
            return {
                'success': False,
                'error': 'Maximum retry attempts exceeded',
                'execution_id': execution_id
            }
        
        logger.info(f"Retrying failed execution: {execution.execution_id}")
        
        # Increment retry count
        execution.retry_count += 1
        execution.status = 'pending'
        execution.error_message = ''
        execution.save(update_fields=['retry_count', 'status', 'error_message'])
        
        # Start new execution task
        result = execute_workflow.delay(
            workflow_id=execution.workflow.id,
            input_data=execution.input_data,
            triggered_by_user_id=execution.triggered_by_id,
            trigger_type='retry'
        )
        
        return {
            'success': True,
            'execution_id': execution_id,
            'retry_count': execution.retry_count,
            'new_task_id': result.id
        }
        
    except WorkflowExecution.DoesNotExist:
        error_msg = f"WorkflowExecution with ID {execution_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'execution_id': execution_id
        }
        
    except Exception as e:
        error_msg = f"Error retrying workflow execution {execution_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'execution_id': execution_id
        }


@shared_task
def cancel_workflow_execution(execution_id: int) -> Dict[str, Any]:
    """
    Cancel a running workflow execution.
    
    Args:
        execution_id: ID of the execution to cancel
        
    Returns:
        Dictionary with cancellation results
    """
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        
        if execution.status not in ['pending', 'running']:
            return {
                'success': False,
                'error': 'Execution is not in cancellable state',
                'execution_id': execution_id
            }
        
        logger.info(f"Cancelling execution: {execution.execution_id}")
        
        # Update execution status
        execution.status = 'cancelled'
        execution.completed_at = timezone.now()
        if execution.started_at:
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        execution.save(update_fields=['status', 'completed_at', 'duration_seconds'])
        
        # Cancel any running step executions
        running_steps = execution.step_executions.filter(status='running')
        for step_execution in running_steps:
            step_execution.status = 'cancelled'
            step_execution.completed_at = timezone.now()
            if step_execution.started_at:
                step_execution.duration_seconds = (
                    step_execution.completed_at - step_execution.started_at
                ).total_seconds()
            step_execution.save(update_fields=['status', 'completed_at', 'duration_seconds'])
        
        return {
            'success': True,
            'execution_id': execution_id,
            'cancelled_steps': running_steps.count()
        }
        
    except WorkflowExecution.DoesNotExist:
        error_msg = f"WorkflowExecution with ID {execution_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'execution_id': execution_id
        }
        
    except Exception as e:
        error_msg = f"Error cancelling workflow execution {execution_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'execution_id': execution_id
        }


@shared_task
def cleanup_old_executions(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old workflow executions and their step executions.
    
    Args:
        days_old: Remove executions older than this many days
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting cleanup of workflow executions older than {days_old} days")
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Get old executions to clean up
    old_executions = WorkflowExecution.objects.filter(
        completed_at__lt=cutoff_date,
        status__in=['completed', 'failed', 'cancelled']
    )
    
    executions_count = old_executions.count()
    
    # Count step executions that will be deleted
    step_executions_count = WorkflowStepExecution.objects.filter(
        workflow_execution__in=old_executions
    ).count()
    
    # Delete old executions (cascade will delete step executions)
    old_executions.delete()
    
    logger.info(f"Cleaned up {executions_count} executions and {step_executions_count} step executions")
    
    return {
        'success': True,
        'executions_deleted': executions_count,
        'step_executions_deleted': step_executions_count,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def monitor_workflow_performance() -> Dict[str, Any]:
    """
    Monitor workflow performance and identify issues.
    
    Returns:
        Dictionary with monitoring results
    """
    logger.info("Monitoring workflow performance")
    
    # Get performance metrics for the last 24 hours
    since = timezone.now() - timedelta(hours=24)
    
    recent_executions = WorkflowExecution.objects.filter(
        started_at__gte=since
    )
    
    performance_data = []
    
    # Analyze each active workflow
    for workflow in Workflow.objects.filter(status='active'):
        workflow_executions = recent_executions.filter(workflow=workflow)
        
        if not workflow_executions.exists():
            continue
        
        total_executions = workflow_executions.count()
        successful_executions = workflow_executions.filter(status='completed').count()
        failed_executions = workflow_executions.filter(status='failed').count()
        
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        # Calculate average duration
        completed_executions = workflow_executions.filter(
            status='completed',
            duration_seconds__isnull=False
        )
        avg_duration = completed_executions.aggregate(
            avg_duration=models.Avg('duration_seconds')
        )['avg_duration'] or 0
        
        performance_data.append({
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': round(success_rate, 2),
            'average_duration_seconds': round(avg_duration, 2),
            'needs_attention': success_rate < 80 or avg_duration > workflow.timeout_minutes * 60 * 0.8
        })
    
    # Identify workflows that need attention
    attention_needed = [w for w in performance_data if w['needs_attention']]
    
    logger.info(f"Monitored {len(performance_data)} workflows, {len(attention_needed)} need attention")
    
    return {
        'success': True,
        'monitoring_period_hours': 24,
        'workflows_monitored': len(performance_data),
        'workflows_need_attention': len(attention_needed),
        'performance_data': performance_data,
        'attention_needed': attention_needed
    }


@shared_task
def execute_workflow_by_code(workflow_code: str, input_data: Dict[str, Any] = None,
                           triggered_by_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a workflow by its code identifier.
    
    Args:
        workflow_code: Code of the workflow to execute
        input_data: Input data for the workflow
        triggered_by_user_id: ID of user who triggered the workflow
        
    Returns:
        Dictionary with execution results
    """
    try:
        workflow = Workflow.objects.get(code=workflow_code, status='active')
        
        return execute_workflow.delay(
            workflow_id=workflow.id,
            input_data=input_data,
            triggered_by_user_id=triggered_by_user_id,
            trigger_type='api'
        ).get()
        
    except Workflow.DoesNotExist:
        error_msg = f"Active workflow with code '{workflow_code}' not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'workflow_code': workflow_code
        }
        
    except Exception as e:
        error_msg = f"Error executing workflow by code {workflow_code}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'workflow_code': workflow_code
        }
"""
Workflow engine core for orchestrating workflow executions.
"""
import logging
import asyncio
import traceback
from typing import Any, Dict, List, Optional, Type
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Workflow, WorkflowStep, WorkflowExecution, 
    WorkflowStepExecution, WorkflowSchedule
)
from .executors import get_step_executor


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Main workflow engine that orchestrates workflow execution.
    Handles step execution, error handling, retries, and state management.
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize the workflow engine.
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
        self.executor_pool = ThreadPoolExecutor(max_workers=max_workers)
    
    def execute_workflow(self, workflow: Workflow, input_data: Dict[str, Any] = None,
                        triggered_by=None, trigger_type: str = 'manual') -> WorkflowExecution:
        """
        Execute a workflow synchronously.
        
        Args:
            workflow: The workflow to execute
            input_data: Input data for the workflow
            triggered_by: User who triggered the workflow
            trigger_type: How the workflow was triggered
            
        Returns:
            WorkflowExecution instance
        """
        # Validate workflow can be executed
        if not workflow.can_execute():
            raise ValidationError(f"Workflow {workflow.name} cannot be executed")
        
        # Create workflow execution record
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            input_data=input_data or {},
            total_steps=workflow.steps.count()
        )
        
        try:
            # Start execution
            execution.start_execution()
            logger.info(f"Starting workflow execution: {execution.execution_id}")
            
            # Initialize context with input data
            context = {
                'workflow_id': workflow.id,
                'execution_id': execution.execution_id,
                'input_data': input_data or {},
                'step_outputs': {}
            }
            
            # Get workflow steps
            steps = workflow.get_steps()
            
            # Execute steps
            self._execute_steps(execution, steps, context)
            
            # Complete execution
            execution.output_data = context.get('output_data', {})
            execution.context_data = context
            execution.complete_execution(success=True)
            
            # Update workflow statistics
            self._update_workflow_stats(workflow, execution)
            
            logger.info(f"Workflow execution completed: {execution.execution_id}")
            
        except Exception as e:
            # Handle execution failure
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            execution.complete_execution(success=False, error_message=error_msg)
            
            # Update workflow statistics
            self._update_workflow_stats(workflow, execution)
            
            raise
        
        return execution
    
    async def execute_workflow_async(self, workflow: Workflow, input_data: Dict[str, Any] = None,
                                   triggered_by=None, trigger_type: str = 'manual') -> WorkflowExecution:
        """
        Execute a workflow asynchronously.
        
        Args:
            workflow: The workflow to execute
            input_data: Input data for the workflow
            triggered_by: User who triggered the workflow
            trigger_type: How the workflow was triggered
            
        Returns:
            WorkflowExecution instance
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute_workflow,
            workflow,
            input_data,
            triggered_by,
            trigger_type
        )
    
    def _execute_steps(self, execution: WorkflowExecution, steps: List[WorkflowStep], 
                      context: Dict[str, Any]):
        """
        Execute workflow steps in order, handling dependencies and parallel execution.
        
        Args:
            execution: The workflow execution instance
            steps: List of workflow steps to execute
            context: Shared context dictionary
        """
        completed_steps = set()
        step_executions = {}
        
        # Create step execution records
        for idx, step in enumerate(steps):
            step_exec = WorkflowStepExecution.objects.create(
                workflow_execution=execution,
                workflow_step=step,
                execution_order=idx + 1
            )
            step_executions[step.id] = step_exec
        
        # Group steps by parallel execution capability
        parallel_groups = self._group_parallel_steps(steps)
        
        for group in parallel_groups:
            if len(group) == 1:
                # Execute single step
                step = group[0]
                self._execute_single_step(
                    execution, step, step_executions[step.id], 
                    context, completed_steps
                )
                completed_steps.add(step.id)
            else:
                # Execute parallel steps
                self._execute_parallel_steps(
                    execution, group, step_executions, 
                    context, completed_steps
                )
                completed_steps.update(s.id for s in group)
            
            # Update progress
            execution.update_progress(len(completed_steps))
    
    def _execute_single_step(self, execution: WorkflowExecution, step: WorkflowStep,
                           step_execution: WorkflowStepExecution, context: Dict[str, Any],
                           completed_steps: set):
        """
        Execute a single workflow step.
        
        Args:
            execution: The workflow execution instance
            step: The workflow step to execute
            step_execution: The step execution record
            context: Shared context dictionary
            completed_steps: Set of completed step IDs
        """
        # Check dependencies
        if not self._check_dependencies(step, completed_steps):
            step_execution.complete_step(
                success=False,
                error_message="Dependencies not met"
            )
            raise ValidationError(f"Dependencies not met for step: {step.name}")
        
        # Check conditions
        if not self._check_conditions(step, context):
            logger.info(f"Skipping step {step.name} due to conditions")
            step_execution.status = 'skipped'
            step_execution.save()
            return
        
        # Update current step
        execution.current_step = step
        execution.save(update_fields=['current_step'])
        
        # Execute with retries
        retry_count = 0
        max_retries = step.max_retries if step.can_retry else 0
        
        while retry_count <= max_retries:
            try:
                # Start step execution
                step_execution.start_step()
                
                # Get executor and execute
                executor_class = step.get_executor_class()
                executor = executor_class(step, context)
                
                # Prepare input data
                input_data = self._prepare_step_input(step, context)
                step_execution.input_data = input_data
                step_execution.save(update_fields=['input_data'])
                
                # Execute step
                output_data = executor.execute(input_data)
                
                # Store output in context
                context['step_outputs'][step.id] = output_data
                
                # Complete step
                metrics = executor.get_metrics()
                step_execution.complete_step(
                    success=True,
                    output_data=output_data,
                    metrics=metrics
                )
                
                logger.info(f"Step {step.name} completed successfully")
                break
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Step {step.name} failed: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                
                if retry_count > max_retries:
                    # Final failure
                    step_execution.complete_step(
                        success=False,
                        error_message=error_msg,
                        error_details={'traceback': traceback.format_exc()}
                    )
                    
                    if not step.is_optional:
                        raise
                    else:
                        logger.warning(f"Optional step {step.name} failed, continuing workflow")
                        break
                else:
                    # Retry
                    step_execution.retry_step()
                    logger.info(f"Retrying step {step.name} (attempt {retry_count}/{max_retries})")
                    
                    # Wait before retry
                    import time
                    time.sleep(execution.workflow.retry_delay_seconds)
    
    def _execute_parallel_steps(self, execution: WorkflowExecution, steps: List[WorkflowStep],
                               step_executions: Dict[int, WorkflowStepExecution],
                               context: Dict[str, Any], completed_steps: set):
        """
        Execute multiple steps in parallel.
        
        Args:
            execution: The workflow execution instance
            steps: List of steps to execute in parallel
            step_executions: Dictionary of step executions
            context: Shared context dictionary
            completed_steps: Set of completed step IDs
        """
        futures = {}
        
        # Submit steps for parallel execution
        for step in steps:
            future = self.executor_pool.submit(
                self._execute_single_step,
                execution,
                step,
                step_executions[step.id],
                context.copy(),  # Each parallel step gets its own context copy
                completed_steps
            )
            futures[future] = step
        
        # Wait for completion and merge results
        for future in as_completed(futures):
            step = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Parallel step {step.name} failed: {str(e)}")
                if not step.is_optional:
                    # Cancel remaining futures
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    raise
    
    def _group_parallel_steps(self, steps: List[WorkflowStep]) -> List[List[WorkflowStep]]:
        """
        Group steps based on parallel execution capability.
        
        Args:
            steps: List of workflow steps
            
        Returns:
            List of step groups
        """
        groups = []
        current_group = []
        current_parallel_group = None
        
        for step in steps:
            if step.can_run_parallel and step.parallel_group:
                if current_parallel_group == step.parallel_group:
                    current_group.append(step)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [step]
                    current_parallel_group = step.parallel_group
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_parallel_group = None
                groups.append([step])
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _check_dependencies(self, step: WorkflowStep, completed_steps: set) -> bool:
        """
        Check if all step dependencies are satisfied.
        
        Args:
            step: The workflow step
            completed_steps: Set of completed step IDs
            
        Returns:
            True if dependencies are met
        """
        dependencies = step.depends_on_steps.all()
        return all(dep.id in completed_steps for dep in dependencies)
    
    def _check_conditions(self, step: WorkflowStep, context: Dict[str, Any]) -> bool:
        """
        Check if step conditions are met.
        
        Args:
            step: The workflow step
            context: Execution context
            
        Returns:
            True if conditions are met
        """
        if not step.condition:
            return True
        
        # Simple condition evaluation
        # In a real implementation, this would be more sophisticated
        condition_type = step.condition.get('type')
        
        if condition_type == 'expression':
            # Evaluate expression condition
            expression = step.condition.get('expression')
            # Safe evaluation of simple expressions
            # This is a simplified version - real implementation would need proper sandboxing
            try:
                return eval(expression, {'context': context})
            except:
                logger.error(f"Failed to evaluate condition for step {step.name}")
                return False
        
        elif condition_type == 'value_check':
            # Check specific value in context
            path = step.condition.get('path')
            expected_value = step.condition.get('value')
            operator = step.condition.get('operator', 'equals')
            
            # Get value from context path
            value = context
            for key in path.split('.'):
                value = value.get(key, {})
            
            # Compare values
            if operator == 'equals':
                return value == expected_value
            elif operator == 'not_equals':
                return value != expected_value
            elif operator == 'greater_than':
                return value > expected_value
            elif operator == 'less_than':
                return value < expected_value
            elif operator == 'contains':
                return expected_value in value
            elif operator == 'not_contains':
                return expected_value not in value
        
        return True
    
    def _prepare_step_input(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare input data for a step based on configuration and context.
        
        Args:
            step: The workflow step
            context: Execution context
            
        Returns:
            Prepared input data dictionary
        """
        input_data = {}
        
        # Get input mapping from step config
        input_mapping = step.config.get('input_mapping', {})
        
        for target_key, source_path in input_mapping.items():
            # Navigate context to get value
            value = context
            for key in source_path.split('.'):
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break
            
            if value is not None:
                input_data[target_key] = value
        
        # Add default inputs from step config
        default_inputs = step.config.get('default_inputs', {})
        for key, value in default_inputs.items():
            if key not in input_data:
                input_data[key] = value
        
        return input_data
    
    def _update_workflow_stats(self, workflow: Workflow, execution: WorkflowExecution):
        """
        Update workflow statistics after execution.
        
        Args:
            workflow: The workflow
            execution: The completed execution
        """
        with transaction.atomic():
            workflow.total_executions += 1
            
            if execution.status == 'completed':
                workflow.successful_executions += 1
            else:
                workflow.failed_executions += 1
            
            # Update average duration
            if execution.duration_seconds:
                total_duration = (workflow.average_duration_seconds * 
                                (workflow.total_executions - 1) + 
                                execution.duration_seconds)
                workflow.average_duration_seconds = total_duration / workflow.total_executions
            
            workflow.save()
    
    def shutdown(self):
        """Shutdown the workflow engine and cleanup resources."""
        self.executor_pool.shutdown(wait=True)


class WorkflowScheduler:
    """
    Handles scheduled workflow execution.
    Manages cron-based and interval-based scheduling.
    """
    
    def __init__(self, engine: WorkflowEngine):
        """
        Initialize the scheduler.
        
        Args:
            engine: The workflow engine instance
        """
        self.engine = engine
        self.running = False
    
    async def start(self):
        """Start the scheduler."""
        self.running = True
        logger.info("Workflow scheduler started")
        
        while self.running:
            try:
                # Check for due schedules
                await self._check_schedules()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Workflow scheduler stopped")
    
    async def _check_schedules(self):
        """Check for due workflow schedules and execute them."""
        # Get active schedules that are due
        due_schedules = WorkflowSchedule.objects.filter(
            is_active=True,
            next_run_at__lte=timezone.now()
        ).select_related('workflow')
        
        for schedule in due_schedules:
            try:
                # Execute workflow
                logger.info(f"Executing scheduled workflow: {schedule.workflow.name}")
                
                execution = await self.engine.execute_workflow_async(
                    workflow=schedule.workflow,
                    input_data=schedule.input_data,
                    trigger_type='scheduled'
                )
                
                # Update schedule
                schedule.last_run_at = timezone.now()
                schedule.total_runs += 1
                schedule.next_run_at = schedule.calculate_next_run()
                schedule.save()
                
            except Exception as e:
                logger.error(f"Failed to execute scheduled workflow {schedule.workflow.name}: {str(e)}")
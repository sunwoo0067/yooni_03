"""
State Manager - Workflow state management and persistence
"""
import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ...models.pipeline import PipelineExecution, PipelineStep, WorkflowStatus, StepStatus


class StateManager:
    """Manages workflow execution state and recovery"""
    
    def __init__(self, db_session: AsyncSession, redis_client: redis.Redis = None):
        self.db = db_session
        self.redis = redis_client
        self.state_cache = {}  # In-memory cache as fallback
    
    async def save_execution_state(
        self, 
        execution_id: str, 
        state_data: Dict[str, Any]
    ):
        """Save execution state"""
        state_key = f"execution_state:{execution_id}"
        
        # Add timestamp
        state_data["last_updated"] = datetime.utcnow().isoformat()
        
        try:
            if self.redis:
                # Save to Redis with TTL
                await self.redis.setex(
                    state_key, 
                    timedelta(days=7),  # Keep state for 7 days
                    json.dumps(state_data, default=str)
                )
            else:
                # Fallback to in-memory cache
                self.state_cache[state_key] = state_data
                
        except Exception as e:
            # Log error but don't fail the workflow
            print(f"Failed to save state for {execution_id}: {e}")
    
    async def load_execution_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Load execution state"""
        state_key = f"execution_state:{execution_id}"
        
        try:
            if self.redis:
                state_data = await self.redis.get(state_key)
                if state_data:
                    return json.loads(state_data)
            else:
                # Fallback to in-memory cache
                return self.state_cache.get(state_key)
                
        except Exception as e:
            print(f"Failed to load state for {execution_id}: {e}")
        
        return None
    
    async def clear_execution_state(self, execution_id: str):
        """Clear execution state"""
        state_key = f"execution_state:{execution_id}"
        
        try:
            if self.redis:
                await self.redis.delete(state_key)
            else:
                self.state_cache.pop(state_key, None)
                
        except Exception as e:
            print(f"Failed to clear state for {execution_id}: {e}")
    
    async def save_step_checkpoint(
        self, 
        execution_id: str, 
        step_name: str, 
        checkpoint_data: Dict[str, Any]
    ):
        """Save step checkpoint for recovery"""
        checkpoint_key = f"checkpoint:{execution_id}:{step_name}"
        
        checkpoint_data.update({
            "execution_id": execution_id,
            "step_name": step_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        try:
            if self.redis:
                await self.redis.setex(
                    checkpoint_key,
                    timedelta(days=3),  # Keep checkpoints for 3 days
                    json.dumps(checkpoint_data, default=str)
                )
            else:
                self.state_cache[checkpoint_key] = checkpoint_data
                
        except Exception as e:
            print(f"Failed to save checkpoint for {execution_id}:{step_name}: {e}")
    
    async def load_step_checkpoint(
        self, 
        execution_id: str, 
        step_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load step checkpoint"""
        checkpoint_key = f"checkpoint:{execution_id}:{step_name}"
        
        try:
            if self.redis:
                checkpoint_data = await self.redis.get(checkpoint_key)
                if checkpoint_data:
                    return json.loads(checkpoint_data)
            else:
                return self.state_cache.get(checkpoint_key)
                
        except Exception as e:
            print(f"Failed to load checkpoint for {execution_id}:{step_name}: {e}")
        
        return None
    
    async def get_recovery_candidates(self) -> List[Dict[str, Any]]:
        """Get executions that can be recovered"""
        # Get executions that were running but haven't been updated recently
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        result = await self.db.execute(
            select(PipelineExecution).where(
                and_(
                    PipelineExecution.status.in_([WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]),
                    PipelineExecution.updated_at < cutoff_time
                )
            )
        )
        
        executions = result.scalars().all()
        recovery_candidates = []
        
        for execution in executions:
            # Check if state exists in cache/redis
            state = await self.load_execution_state(str(execution.workflow_id))
            if state:
                recovery_candidates.append({
                    "execution_id": str(execution.workflow_id),
                    "execution": execution,
                    "state": state,
                    "last_update": execution.updated_at
                })
        
        return recovery_candidates
    
    async def recover_execution(self, execution_id: str) -> bool:
        """Recover a failed execution"""
        try:
            # Load execution state
            state = await self.load_execution_state(execution_id)
            if not state:
                return False
            
            # Get execution from database
            result = await self.db.execute(
                select(PipelineExecution).where(
                    PipelineExecution.workflow_id == execution_id
                )
            )
            execution = result.scalar_one_or_none()
            if not execution:
                return False
            
            # Determine recovery strategy based on last known state
            current_step = state.get("current_step", 0)
            workflow_steps = state.get("workflow_steps", [])
            
            if current_step < len(workflow_steps):
                # Resume from current step
                execution.status = WorkflowStatus.RUNNING
                await self.db.commit()
                
                # The orchestrator will pick this up and continue
                return True
            
        except Exception as e:
            print(f"Failed to recover execution {execution_id}: {e}")
        
        return False
    
    async def mark_execution_for_cleanup(self, execution_id: str):
        """Mark execution for cleanup after completion"""
        cleanup_key = f"cleanup:{execution_id}"
        
        try:
            if self.redis:
                # Schedule cleanup after 24 hours
                await self.redis.setex(
                    cleanup_key,
                    timedelta(hours=24),
                    "cleanup_scheduled"
                )
            
        except Exception as e:
            print(f"Failed to schedule cleanup for {execution_id}: {e}")
    
    async def get_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get real-time execution metrics"""
        try:
            # Get from database
            result = await self.db.execute(
                select(PipelineExecution).where(
                    PipelineExecution.workflow_id == execution_id
                )
            )
            execution = result.scalar_one_or_none()
            
            if not execution:
                return {}
            
            # Get step details
            steps_result = await self.db.execute(
                select(PipelineStep).where(
                    PipelineStep.execution_id == execution.id
                ).order_by(PipelineStep.step_order)
            )
            steps = steps_result.scalars().all()
            
            # Calculate metrics
            total_duration = None
            if execution.started_at and execution.completed_at:
                total_duration = (execution.completed_at - execution.started_at).total_seconds()
            elif execution.started_at:
                total_duration = (datetime.utcnow() - execution.started_at).total_seconds()
            
            step_metrics = []
            for step in steps:
                step_duration = None
                if step.started_at and step.completed_at:
                    step_duration = (step.completed_at - step.started_at).total_seconds()
                
                step_metrics.append({
                    "name": step.step_name,
                    "status": step.status,
                    "duration_seconds": step_duration,
                    "items_processed": step.processed_items,
                    "success_rate": (step.succeeded_items / step.total_items * 100) if step.total_items > 0 else 0,
                    "processing_rate": step.processing_rate
                })
            
            return {
                "execution_id": execution_id,
                "status": execution.status,
                "progress_percentage": execution.calculate_progress(),
                "total_duration_seconds": total_duration,
                "products_processed": execution.products_processed,
                "products_succeeded": execution.products_succeeded,
                "success_rate": execution.calculate_success_rate(),
                "processing_rate": execution.processing_rate,
                "steps": step_metrics,
                "last_updated": execution.updated_at.isoformat()
            }
            
        except Exception as e:
            print(f"Failed to get metrics for {execution_id}: {e}")
            return {}
    
    async def save_error_context(
        self, 
        execution_id: str, 
        step_name: str, 
        error: Exception,
        context: Dict[str, Any] = None
    ):
        """Save error context for debugging"""
        error_key = f"error:{execution_id}:{step_name}"
        
        error_data = {
            "execution_id": execution_id,
            "step_name": step_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        try:
            if self.redis:
                await self.redis.setex(
                    error_key,
                    timedelta(days=7),  # Keep error data for 7 days
                    json.dumps(error_data, default=str)
                )
            else:
                self.state_cache[error_key] = error_data
                
        except Exception as e:
            print(f"Failed to save error context: {e}")
    
    async def get_error_history(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get error history for an execution"""
        error_pattern = f"error:{execution_id}:*"
        errors = []
        
        try:
            if self.redis:
                error_keys = await self.redis.keys(error_pattern)
                for key in error_keys:
                    error_data = await self.redis.get(key)
                    if error_data:
                        errors.append(json.loads(error_data))
            else:
                # Search in-memory cache
                for key, value in self.state_cache.items():
                    if key.startswith(f"error:{execution_id}:"):
                        errors.append(value)
            
            # Sort by timestamp
            errors.sort(key=lambda x: x.get("timestamp", ""))
            
        except Exception as e:
            print(f"Failed to get error history for {execution_id}: {e}")
        
        return errors
    
    async def update_execution_progress(
        self, 
        execution_id: str, 
        progress_data: Dict[str, Any]
    ):
        """Update execution progress in real-time"""
        progress_key = f"progress:{execution_id}"
        
        progress_data.update({
            "last_updated": datetime.utcnow().isoformat()
        })
        
        try:
            if self.redis:
                await self.redis.setex(
                    progress_key,
                    timedelta(hours=12),  # Keep progress data for 12 hours
                    json.dumps(progress_data, default=str)
                )
            else:
                self.state_cache[progress_key] = progress_data
                
        except Exception as e:
            print(f"Failed to update progress for {execution_id}: {e}")
    
    async def get_execution_progress(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time execution progress"""
        progress_key = f"progress:{execution_id}"
        
        try:
            if self.redis:
                progress_data = await self.redis.get(progress_key)
                if progress_data:
                    return json.loads(progress_data)
            else:
                return self.state_cache.get(progress_key)
                
        except Exception as e:
            print(f"Failed to get progress for {execution_id}: {e}")
        
        return None
    
    async def cleanup_old_states(self):
        """Clean up old execution states and checkpoints"""
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        try:
            if self.redis:
                # Redis handles TTL automatically, but we can clean up manually too
                pattern = "execution_state:*"
                keys = await self.redis.keys(pattern)
                
                for key in keys:
                    data = await self.redis.get(key)
                    if data:
                        state = json.loads(data)
                        last_updated = datetime.fromisoformat(state.get("last_updated", ""))
                        if last_updated < cutoff_time:
                            await self.redis.delete(key)
            else:
                # Clean up in-memory cache
                keys_to_remove = []
                for key, value in self.state_cache.items():
                    if "last_updated" in value:
                        last_updated = datetime.fromisoformat(value["last_updated"])
                        if last_updated < cutoff_time:
                            keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.state_cache[key]
                    
        except Exception as e:
            print(f"Failed to cleanup old states: {e}")
    
    async def get_active_executions(self) -> List[Dict[str, Any]]:
        """Get all currently active executions"""
        result = await self.db.execute(
            select(PipelineExecution).where(
                PipelineExecution.status.in_([
                    WorkflowStatus.RUNNING, 
                    WorkflowStatus.PAUSED
                ])
            ).order_by(PipelineExecution.started_at.desc())
        )
        
        executions = result.scalars().all()
        active_list = []
        
        for execution in executions:
            # Get real-time state if available
            state = await self.load_execution_state(str(execution.workflow_id))
            progress = await self.get_execution_progress(str(execution.workflow_id))
            
            active_list.append({
                "execution_id": str(execution.workflow_id),
                "workflow_name": execution.workflow_name,
                "status": execution.status,
                "started_at": execution.started_at,
                "progress": execution.calculate_progress(),
                "real_time_state": state,
                "real_time_progress": progress
            })
        
        return active_list
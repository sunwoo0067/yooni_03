"""
Progress Tracker - Real-time progress tracking and estimation
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from collections import deque

from ...models.pipeline import PipelineExecution, PipelineStep, PipelineProductResult


class ProgressTracker:
    """Tracks and estimates workflow progress in real-time"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.progress_history = {}  # execution_id -> deque of progress points
        self.processing_rates = {}  # execution_id -> processing rate history
        self.estimations = {}  # execution_id -> estimation data
    
    async def start_tracking(self, execution_id: str, total_items: int):
        """Start tracking an execution"""
        self.progress_history[execution_id] = deque(maxlen=100)  # Keep last 100 progress points
        self.processing_rates[execution_id] = deque(maxlen=20)   # Keep last 20 rate measurements
        
        # Initial progress point
        self._add_progress_point(execution_id, 0, total_items, datetime.utcnow())
        
        self.estimations[execution_id] = {
            "total_items": total_items,
            "start_time": datetime.utcnow(),
            "estimated_completion": None,
            "confidence": 0.0
        }
    
    async def update_progress(
        self, 
        execution_id: str, 
        completed_items: int, 
        current_step: str = None,
        step_details: Dict[str, Any] = None
    ):
        """Update progress for an execution"""
        now = datetime.utcnow()
        
        if execution_id not in self.progress_history:
            return
        
        # Add progress point
        total_items = self.estimations[execution_id]["total_items"]
        self._add_progress_point(execution_id, completed_items, total_items, now)
        
        # Calculate processing rate
        rate = self._calculate_processing_rate(execution_id)
        if rate > 0:
            self.processing_rates[execution_id].append({
                "timestamp": now,
                "rate": rate,
                "step": current_step
            })
        
        # Update estimation
        await self._update_estimation(execution_id, completed_items, current_step)
        
        # Update database
        await self._update_database_progress(execution_id, completed_items, step_details)
    
    def _add_progress_point(
        self, 
        execution_id: str, 
        completed: int, 
        total: int, 
        timestamp: datetime
    ):
        """Add a progress measurement point"""
        progress_point = {
            "timestamp": timestamp,
            "completed": completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0
        }
        
        self.progress_history[execution_id].append(progress_point)
    
    def _calculate_processing_rate(self, execution_id: str) -> float:
        """Calculate current processing rate (items per minute)"""
        history = self.progress_history[execution_id]
        
        if len(history) < 2:
            return 0.0
        
        # Use last few points to calculate rate
        recent_points = list(history)[-5:]  # Last 5 points
        
        if len(recent_points) < 2:
            return 0.0
        
        first_point = recent_points[0]
        last_point = recent_points[-1]
        
        time_diff = (last_point["timestamp"] - first_point["timestamp"]).total_seconds()
        items_diff = last_point["completed"] - first_point["completed"]
        
        if time_diff <= 0:
            return 0.0
        
        # Rate in items per minute
        rate = (items_diff / time_diff) * 60
        return max(0, rate)
    
    async def _update_estimation(
        self, 
        execution_id: str, 
        completed_items: int, 
        current_step: str = None
    ):
        """Update completion time estimation"""
        estimation = self.estimations[execution_id]
        total_items = estimation["total_items"]
        remaining_items = total_items - completed_items
        
        if remaining_items <= 0:
            estimation["estimated_completion"] = datetime.utcnow()
            estimation["confidence"] = 1.0
            return
        
        # Calculate average rate
        rates = self.processing_rates[execution_id]
        if not rates:
            return
        
        # Weight recent rates more heavily
        weighted_rate = self._calculate_weighted_average_rate(rates)
        
        if weighted_rate <= 0:
            return
        
        # Estimate time remaining
        estimated_minutes = remaining_items / weighted_rate
        estimated_completion = datetime.utcnow() + timedelta(minutes=estimated_minutes)
        
        # Calculate confidence based on rate stability
        confidence = self._calculate_confidence(rates)
        
        estimation.update({
            "estimated_completion": estimated_completion,
            "confidence": confidence,
            "current_rate": weighted_rate,
            "remaining_items": remaining_items,
            "estimated_minutes_remaining": estimated_minutes
        })
    
    def _calculate_weighted_average_rate(self, rates: deque) -> float:
        """Calculate weighted average of processing rates"""
        if not rates:
            return 0.0
        
        # More recent rates get higher weight
        total_weight = 0
        weighted_sum = 0
        
        for i, rate_data in enumerate(rates):
            weight = i + 1  # Linear weight increase
            weighted_sum += rate_data["rate"] * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_confidence(self, rates: deque) -> float:
        """Calculate confidence in estimation based on rate stability"""
        if len(rates) < 3:
            return 0.3  # Low confidence with few data points
        
        rate_values = [r["rate"] for r in rates]
        
        # Calculate coefficient of variation
        mean_rate = sum(rate_values) / len(rate_values)
        if mean_rate == 0:
            return 0.0
        
        variance = sum((r - mean_rate) ** 2 for r in rate_values) / len(rate_values)
        std_dev = variance ** 0.5
        cv = std_dev / mean_rate
        
        # Convert to confidence (lower CV = higher confidence)
        confidence = max(0.0, min(1.0, 1.0 - cv))
        
        # Boost confidence if we have more data points
        data_bonus = min(0.2, len(rates) / 50)  # Up to 20% bonus
        confidence = min(1.0, confidence + data_bonus)
        
        return confidence
    
    async def _update_database_progress(
        self, 
        execution_id: str, 
        completed_items: int,
        step_details: Dict[str, Any] = None
    ):
        """Update progress in database"""
        try:
            # Get execution
            result = await self.db.execute(
                select(PipelineExecution).where(
                    PipelineExecution.workflow_id == execution_id
                )
            )
            execution = result.scalar_one_or_none()
            
            if not execution:
                return
            
            # Update progress
            execution.products_processed = completed_items
            
            # Update processing rate
            current_rate = self._calculate_processing_rate(execution_id)
            if current_rate > 0:
                execution.processing_rate = current_rate
            
            # Update estimation
            estimation = self.estimations.get(execution_id, {})
            if estimation.get("estimated_completion"):
                execution.estimated_completion = estimation["estimated_completion"]
            
            await self.db.commit()
            
        except Exception as e:
            print(f"Failed to update database progress for {execution_id}: {e}")
    
    async def get_progress_summary(self, execution_id: str) -> Dict[str, Any]:
        """Get comprehensive progress summary"""
        if execution_id not in self.estimations:
            return {}
        
        estimation = self.estimations[execution_id]
        history = self.progress_history.get(execution_id, deque())
        rates = self.processing_rates.get(execution_id, deque())
        
        # Current progress
        current_progress = list(history)[-1] if history else None
        
        # Rate statistics
        rate_stats = self._calculate_rate_statistics(rates)
        
        # Time statistics
        time_stats = self._calculate_time_statistics(estimation, history)
        
        return {
            "execution_id": execution_id,
            "current_progress": current_progress,
            "estimation": {
                "estimated_completion": estimation.get("estimated_completion"),
                "confidence": estimation.get("confidence", 0.0),
                "remaining_minutes": estimation.get("estimated_minutes_remaining", 0),
                "remaining_items": estimation.get("remaining_items", 0)
            },
            "processing_rate": {
                "current": estimation.get("current_rate", 0),
                "statistics": rate_stats
            },
            "timing": time_stats,
            "data_points": len(history)
        }
    
    def _calculate_rate_statistics(self, rates: deque) -> Dict[str, float]:
        """Calculate processing rate statistics"""
        if not rates:
            return {"min": 0, "max": 0, "average": 0, "latest": 0}
        
        rate_values = [r["rate"] for r in rates]
        
        return {
            "min": min(rate_values),
            "max": max(rate_values),
            "average": sum(rate_values) / len(rate_values),
            "latest": rate_values[-1] if rate_values else 0
        }
    
    def _calculate_time_statistics(
        self, 
        estimation: Dict[str, Any], 
        history: deque
    ) -> Dict[str, Any]:
        """Calculate timing statistics"""
        start_time = estimation.get("start_time")
        if not start_time:
            return {}
        
        now = datetime.utcnow()
        elapsed = (now - start_time).total_seconds()
        
        stats = {
            "start_time": start_time,
            "elapsed_seconds": elapsed,
            "elapsed_minutes": elapsed / 60
        }
        
        if estimation.get("estimated_completion"):
            total_estimated = (estimation["estimated_completion"] - start_time).total_seconds()
            stats.update({
                "estimated_total_seconds": total_estimated,
                "estimated_total_minutes": total_estimated / 60,
                "progress_percentage": (elapsed / total_estimated * 100) if total_estimated > 0 else 0
            })
        
        return stats
    
    async def get_step_progress(self, execution_id: str, step_name: str) -> Dict[str, Any]:
        """Get progress for a specific step"""
        try:
            # Get step from database
            result = await self.db.execute(
                select(PipelineStep).join(PipelineExecution).where(
                    and_(
                        PipelineExecution.workflow_id == execution_id,
                        PipelineStep.step_name == step_name
                    )
                )
            )
            step = result.scalar_one_or_none()
            
            if not step:
                return {}
            
            # Calculate step progress
            progress_percentage = 0
            if step.total_items > 0:
                progress_percentage = (step.processed_items / step.total_items) * 100
            
            # Calculate step rate
            step_rate = 0
            if step.started_at and step.processed_items > 0:
                elapsed = (datetime.utcnow() - step.started_at).total_seconds()
                if elapsed > 0:
                    step_rate = (step.processed_items / elapsed) * 60  # items per minute
            
            return {
                "step_name": step_name,
                "status": step.status,
                "progress_percentage": progress_percentage,
                "processed_items": step.processed_items,
                "total_items": step.total_items,
                "succeeded_items": step.succeeded_items,
                "failed_items": step.failed_items,
                "processing_rate": step_rate,
                "started_at": step.started_at,
                "duration_seconds": step.duration_seconds
            }
            
        except Exception as e:
            print(f"Failed to get step progress for {execution_id}:{step_name}: {e}")
            return {}
    
    async def get_product_progress(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get progress for individual products"""
        try:
            # Get product results
            result = await self.db.execute(
                select(PipelineProductResult).join(PipelineExecution).where(
                    PipelineExecution.workflow_id == execution_id
                ).order_by(PipelineProductResult.created_at)
            )
            product_results = result.scalars().all()
            
            progress_list = []
            for product_result in product_results:
                # Calculate overall product progress
                stages_completed = 0
                total_stages = 3  # sourcing, processing, registration
                
                if product_result.sourcing_status == "completed":
                    stages_completed += 1
                if product_result.processing_status == "completed":
                    stages_completed += 1
                if product_result.registration_status == "completed":
                    stages_completed += 1
                
                progress_percentage = (stages_completed / total_stages) * 100
                
                progress_list.append({
                    "product_id": str(product_result.product_id),
                    "product_code": product_result.product_code,
                    "progress_percentage": progress_percentage,
                    "final_status": product_result.final_status,
                    "sourcing_status": product_result.sourcing_status,
                    "processing_status": product_result.processing_status,
                    "registration_status": product_result.registration_status,
                    "total_processing_time": product_result.total_processing_time,
                    "error_message": product_result.error_message
                })
            
            return progress_list
            
        except Exception as e:
            print(f"Failed to get product progress for {execution_id}: {e}")
            return []
    
    async def predict_bottlenecks(self, execution_id: str) -> List[Dict[str, Any]]:
        """Predict potential bottlenecks based on current progress"""
        bottlenecks = []
        
        try:
            # Get step progress
            result = await self.db.execute(
                select(PipelineStep).join(PipelineExecution).where(
                    PipelineExecution.workflow_id == execution_id
                ).order_by(PipelineStep.step_order)
            )
            steps = result.scalars().all()
            
            for step in steps:
                if step.status == "running" and step.started_at:
                    elapsed = (datetime.utcnow() - step.started_at).total_seconds()
                    
                    # Check for slow processing
                    if step.total_items > 0 and elapsed > 300:  # 5 minutes
                        expected_items = (elapsed / 60) * 10  # Expect ~10 items per minute
                        if step.processed_items < expected_items * 0.5:  # Less than 50% expected
                            bottlenecks.append({
                                "type": "slow_processing",
                                "step_name": step.step_name,
                                "severity": "medium",
                                "message": f"Step '{step.step_name}' is processing slower than expected",
                                "details": {
                                    "elapsed_minutes": elapsed / 60,
                                    "items_processed": step.processed_items,
                                    "expected_items": expected_items,
                                    "processing_rate": step.processing_rate
                                }
                            })
                    
                    # Check for high error rate
                    if step.processed_items > 10:  # Only check after processing some items
                        error_rate = step.failed_items / step.processed_items
                        if error_rate > 0.2:  # More than 20% errors
                            bottlenecks.append({
                                "type": "high_error_rate",
                                "step_name": step.step_name,
                                "severity": "high",
                                "message": f"Step '{step.step_name}' has high error rate ({error_rate:.1%})",
                                "details": {
                                    "error_rate": error_rate,
                                    "failed_items": step.failed_items,
                                    "processed_items": step.processed_items
                                }
                            })
            
            return bottlenecks
            
        except Exception as e:
            print(f"Failed to predict bottlenecks for {execution_id}: {e}")
            return []
    
    async def stop_tracking(self, execution_id: str):
        """Stop tracking an execution"""
        self.progress_history.pop(execution_id, None)
        self.processing_rates.pop(execution_id, None)
        self.estimations.pop(execution_id, None)
    
    async def cleanup_old_tracking_data(self):
        """Clean up old tracking data"""
        # Remove tracking data for executions older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        executions_to_remove = []
        for execution_id, estimation in self.estimations.items():
            if estimation.get("start_time", datetime.utcnow()) < cutoff_time:
                executions_to_remove.append(execution_id)
        
        for execution_id in executions_to_remove:
            await self.stop_tracking(execution_id)
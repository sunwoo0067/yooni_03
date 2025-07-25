"""
Workflow Orchestrator - Main pipeline coordination service
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.pipeline import (
    PipelineExecution, PipelineStep, PipelineProductResult, 
    WorkflowTemplate, PipelineAlert, WorkflowStatus, StepStatus
)
from ...models.product import Product
from ...services.sourcing.smart_sourcing_engine import SmartSourcingEngine
from ...services.processing.product_processing_service import ProductProcessingService
from ...services.registration.product_registration_engine import ProductRegistrationEngine
from ...services.monitoring.error_handler import ErrorHandler
from .state_manager import StateManager
from .progress_tracker import ProgressTracker


class WorkflowStep:
    """Individual workflow step definition"""
    def __init__(self, name: str, step_type: str, processor: Callable, config: Dict[str, Any] = None):
        self.name = name
        self.step_type = step_type
        self.processor = processor
        self.config = config or {}
        self.dependencies = []
        self.parallel_allowed = False
    
    def add_dependency(self, step_name: str):
        """Add step dependency"""
        self.dependencies.append(step_name)
    
    def set_parallel(self, allowed: bool = True):
        """Set if step can run in parallel"""
        self.parallel_allowed = allowed


class WorkflowOrchestrator:
    """Main workflow orchestration service"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.state_manager = StateManager(db_session)
        self.progress_tracker = ProgressTracker(db_session)
        self.error_handler = ErrorHandler(db_session)
        
        # Service instances
        self.sourcing_engine = SmartSourcingEngine(db_session)
        self.processing_service = ProductProcessingService(db_session)
        self.registration_engine = ProductRegistrationEngine(db_session)
        
        # Workflow registry
        self.workflows = {}
        self.active_executions = {}
        
        # Initialize default workflows
        self._initialize_default_workflows()
    
    def _initialize_default_workflows(self):
        """Initialize default workflow templates"""
        # Complete dropshipping workflow
        complete_workflow = self._create_complete_workflow()
        self.register_workflow("complete_dropshipping", complete_workflow)
        
        # Sourcing only workflow
        sourcing_workflow = self._create_sourcing_workflow()
        self.register_workflow("sourcing_only", sourcing_workflow)
        
        # Processing only workflow
        processing_workflow = self._create_processing_workflow()
        self.register_workflow("processing_only", processing_workflow)
        
        # Registration only workflow
        registration_workflow = self._create_registration_workflow()
        self.register_workflow("registration_only", registration_workflow)
    
    def _create_complete_workflow(self) -> List[WorkflowStep]:
        """Create complete dropshipping workflow"""
        steps = [
            WorkflowStep(
                "data_preparation", 
                "preparation",
                self._prepare_data,
                {"validate_products": True, "check_inventory": True}
            ),
            WorkflowStep(
                "ai_sourcing", 
                "sourcing",
                self._execute_sourcing,
                {"use_ai": True, "score_threshold": 7.0}
            ),
            WorkflowStep(
                "product_processing", 
                "processing",
                self._execute_processing,
                {"generate_names": True, "process_images": True, "optimize_content": True}
            ),
            WorkflowStep(
                "multi_platform_registration", 
                "registration",
                self._execute_registration,
                {"platforms": ["coupang", "naver", "11st"], "parallel_upload": True}
            ),
            WorkflowStep(
                "post_registration_monitoring", 
                "monitoring",
                self._execute_monitoring,
                {"check_status": True, "validate_listings": True}
            ),
            WorkflowStep(
                "performance_analysis", 
                "analysis",
                self._execute_analysis,
                {"generate_reports": True, "update_models": True}
            )
        ]
        
        # Set dependencies
        steps[1].add_dependency("data_preparation")
        steps[2].add_dependency("ai_sourcing")
        steps[3].add_dependency("product_processing")
        steps[4].add_dependency("multi_platform_registration")
        steps[5].add_dependency("post_registration_monitoring")
        
        # Enable parallel processing where appropriate
        steps[3].set_parallel(True)  # Registration can be parallel
        
        return steps
    
    def _create_sourcing_workflow(self) -> List[WorkflowStep]:
        """Create sourcing-only workflow"""
        return [
            WorkflowStep(
                "data_preparation", 
                "preparation",
                self._prepare_data,
                {"validate_products": True}
            ),
            WorkflowStep(
                "ai_sourcing", 
                "sourcing",
                self._execute_sourcing,
                {"use_ai": True, "detailed_analysis": True}
            ),
            WorkflowStep(
                "sourcing_analysis", 
                "analysis",
                self._execute_sourcing_analysis,
                {"generate_insights": True}
            )
        ]
    
    def _create_processing_workflow(self) -> List[WorkflowStep]:
        """Create processing-only workflow"""
        return [
            WorkflowStep(
                "product_processing", 
                "processing",
                self._execute_processing,
                {"generate_names": True, "process_images": True}
            ),
            WorkflowStep(
                "quality_validation", 
                "validation",
                self._execute_quality_validation,
                {"check_guidelines": True, "score_threshold": 8.0}
            )
        ]
    
    def _create_registration_workflow(self) -> List[WorkflowStep]:
        """Create registration-only workflow"""
        return [
            WorkflowStep(
                "pre_registration_check", 
                "validation",
                self._pre_registration_check,
                {"validate_accounts": True, "check_quotas": True}
            ),
            WorkflowStep(
                "multi_platform_registration", 
                "registration",
                self._execute_registration,
                {"parallel_upload": True, "retry_failures": True}
            ),
            WorkflowStep(
                "registration_validation", 
                "validation",
                self._validate_registration,
                {"check_all_platforms": True}
            )
        ]
    
    def register_workflow(self, name: str, steps: List[WorkflowStep]):
        """Register a workflow template"""
        self.workflows[name] = steps
    
    async def start_workflow(
        self, 
        workflow_name: str, 
        product_ids: List[str] = None,
        config: Dict[str, Any] = None
    ) -> str:
        """Start a workflow execution"""
        
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        workflow_id = str(uuid.uuid4())
        
        execution = PipelineExecution(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.PENDING,
            total_steps=len(self.workflows[workflow_name]),
            execution_config=config or {}
        )
        
        # Get products to process
        if product_ids:
            products = await self._get_products_by_ids(product_ids)
        else:
            products = await self._get_products_for_processing(config)
        
        execution.total_products_to_process = len(products)
        
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        
        # Store execution reference
        self.active_executions[execution_id] = {
            "execution": execution,
            "workflow": self.workflows[workflow_name],
            "products": products,
            "config": config or {},
            "current_step": 0,
            "start_time": datetime.utcnow()
        }
        
        # Start execution in background
        asyncio.create_task(self._execute_workflow(execution_id))
        
        return execution_id
    
    async def _execute_workflow(self, execution_id: str):
        """Execute workflow steps"""
        execution_data = self.active_executions[execution_id]
        execution = execution_data["execution"]
        workflow_steps = execution_data["workflow"]
        products = execution_data["products"]
        config = execution_data["config"]
        
        try:
            # Update status to running
            execution.status = WorkflowStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await self.db.commit()
            
            # Execute each step
            for i, step in enumerate(workflow_steps):
                execution_data["current_step"] = i
                
                await self._execute_step(execution, step, products, config)
                
                # Update progress
                execution.completed_steps += 1
                execution.success_rate = execution.calculate_success_rate()
                await self.db.commit()
                
                # Check if execution was cancelled
                if execution.status == WorkflowStatus.CANCELLED:
                    break
            
            # Mark as completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            
            # Generate final report
            await self._generate_execution_report(execution)
            
        except Exception as e:
            # Handle execution failure
            execution.status = WorkflowStatus.FAILED
            execution.error_log = str(e)
            
            # Create alert
            await self._create_alert(
                execution.id,
                "error",
                "Workflow Execution Failed",
                f"Workflow '{execution.workflow_name}' failed: {str(e)}",
                {"error_type": type(e).__name__, "step": execution_data.get("current_step", 0)}
            )
            
            await self.error_handler.handle_workflow_error(execution, e)
        
        finally:
            await self.db.commit()
            # Clean up active execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _execute_step(
        self, 
        execution: PipelineExecution, 
        step: WorkflowStep, 
        products: List[Product],
        config: Dict[str, Any]
    ):
        """Execute individual workflow step"""
        
        # Create step record
        step_record = PipelineStep(
            execution_id=execution.id,
            step_name=step.name,
            step_type=step.step_type,
            step_order=execution.completed_steps + 1,
            status=StepStatus.RUNNING,
            started_at=datetime.utcnow(),
            total_items=len(products),
            step_config={**step.config, **config}
        )
        
        self.db.add(step_record)
        await self.db.commit()
        
        try:
            # Execute step processor
            step_config = {**step.config, **config}
            results = await step.processor(products, step_config)
            
            # Update step results
            step_record.status = StepStatus.COMPLETED
            step_record.completed_at = datetime.utcnow()
            step_record.step_results = results
            step_record.succeeded_items = len([r for r in results.get("product_results", []) if r.get("success", False)])
            step_record.failed_items = step_record.total_items - step_record.succeeded_items
            step_record.calculate_duration()
            
            # Update execution progress
            execution.products_processed += step_record.succeeded_items
            execution.products_failed += step_record.failed_items
            
            # Update product results
            await self._update_product_results(execution, step, results)
            
        except Exception as e:
            step_record.status = StepStatus.FAILED
            step_record.error_details = str(e)
            step_record.completed_at = datetime.utcnow()
            step_record.calculate_duration()
            
            raise e
        
        finally:
            await self.db.commit()
    
    async def _update_product_results(
        self, 
        execution: PipelineExecution, 
        step: WorkflowStep, 
        results: Dict[str, Any]
    ):
        """Update product-level results"""
        
        for product_result in results.get("product_results", []):
            product_id = product_result.get("product_id")
            
            # Find or create product result record
            existing = await self.db.execute(
                select(PipelineProductResult).where(
                    and_(
                        PipelineProductResult.execution_id == execution.id,
                        PipelineProductResult.product_id == product_id
                    )
                )
            )
            product_record = existing.scalar_one_or_none()
            
            if not product_record:
                product_record = PipelineProductResult(
                    execution_id=execution.id,
                    product_id=product_id,
                    product_code=product_result.get("product_code")
                )
                self.db.add(product_record)
            
            # Update based on step type
            if step.step_type == "sourcing":
                product_record.sourcing_status = "completed" if product_result.get("success") else "failed"
                product_record.sourcing_completed_at = datetime.utcnow()
                product_record.sourcing_score = product_result.get("score")
                product_record.sourcing_reasons = product_result.get("reasons")
            
            elif step.step_type == "processing":
                product_record.processing_status = "completed" if product_result.get("success") else "failed"
                product_record.processing_completed_at = datetime.utcnow()
                product_record.processing_changes = product_result.get("changes")
                product_record.processing_quality_score = product_result.get("quality_score")
            
            elif step.step_type == "registration":
                product_record.registration_status = "completed" if product_result.get("success") else "failed"
                product_record.registration_completed_at = datetime.utcnow()
                product_record.registration_platforms = product_result.get("platforms")
                product_record.registration_results = product_result.get("results")
            
            # Update overall status
            if product_result.get("success"):
                if product_record.final_status != "failed":
                    product_record.final_status = "completed"
            else:
                product_record.final_status = "failed"
                product_record.error_message = product_result.get("error")
    
    # Step processors
    async def _prepare_data(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for processing"""
        results = {"product_results": []}
        
        for product in products:
            try:
                # Validate product data
                if config.get("validate_products", True):
                    is_valid = await self._validate_product(product)
                    if not is_valid:
                        results["product_results"].append({
                            "product_id": str(product.id),
                            "success": False,
                            "error": "Product validation failed"
                        })
                        continue
                
                # Check inventory if required
                if config.get("check_inventory", False):
                    inventory_ok = await self._check_inventory(product)
                    if not inventory_ok:
                        results["product_results"].append({
                            "product_id": str(product.id),
                            "success": False,
                            "error": "Inventory check failed"
                        })
                        continue
                
                results["product_results"].append({
                    "product_id": str(product.id),
                    "product_code": product.code,
                    "success": True,
                    "prepared_data": {"validated": True, "inventory_checked": True}
                })
                
            except Exception as e:
                results["product_results"].append({
                    "product_id": str(product.id),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_sourcing(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI sourcing step"""
        results = {"product_results": []}
        
        for product in products:
            try:
                # Run AI sourcing analysis
                sourcing_result = await self.sourcing_engine.analyze_product_potential(product)
                
                success = sourcing_result.score >= config.get("score_threshold", 7.0)
                
                results["product_results"].append({
                    "product_id": str(product.id),
                    "product_code": product.code,
                    "success": success,
                    "score": sourcing_result.score,
                    "reasons": sourcing_result.reasons,
                    "market_data": sourcing_result.market_analysis
                })
                
            except Exception as e:
                results["product_results"].append({
                    "product_id": str(product.id),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_processing(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute product processing step"""
        results = {"product_results": []}
        
        for product in products:
            try:
                # Process product
                processing_result = await self.processing_service.process_product_complete(
                    product_id=str(product.id),
                    generate_name=config.get("generate_names", True),
                    process_images=config.get("process_images", True),
                    optimize_content=config.get("optimize_content", True)
                )
                
                results["product_results"].append({
                    "product_id": str(product.id),
                    "product_code": product.code,
                    "success": processing_result.get("success", False),
                    "changes": processing_result.get("changes", {}),
                    "quality_score": processing_result.get("quality_score", 0)
                })
                
            except Exception as e:
                results["product_results"].append({
                    "product_id": str(product.id),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_registration(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute product registration step"""
        results = {"product_results": []}
        
        platforms = config.get("platforms", ["coupang", "naver", "11st"])
        
        for product in products:
            try:
                # Register to platforms
                registration_results = {}
                for platform in platforms:
                    platform_result = await self.registration_engine.register_product(
                        product_id=str(product.id),
                        platform=platform
                    )
                    registration_results[platform] = platform_result
                
                # Check overall success
                success = any(result.get("success", False) for result in registration_results.values())
                
                results["product_results"].append({
                    "product_id": str(product.id),
                    "product_code": product.code,
                    "success": success,
                    "platforms": platforms,
                    "results": registration_results
                })
                
            except Exception as e:
                results["product_results"].append({
                    "product_id": str(product.id),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_monitoring(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute post-registration monitoring"""
        results = {"product_results": []}
        
        for product in products:
            try:
                # Monitor registration status
                monitoring_result = await self._monitor_product_registration(product)
                
                results["product_results"].append({
                    "product_id": str(product.id),
                    "product_code": product.code,
                    "success": monitoring_result.get("success", False),
                    "status_checks": monitoring_result.get("status_checks", {}),
                    "issues_found": monitoring_result.get("issues", [])
                })
                
            except Exception as e:
                results["product_results"].append({
                    "product_id": str(product.id),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_analysis(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute performance analysis"""
        results = {"product_results": []}
        
        # Generate performance analysis
        analysis_result = await self._analyze_workflow_performance(products)
        
        results["analysis"] = analysis_result
        results["product_results"] = [
            {
                "product_id": str(product.id),
                "success": True,
                "analyzed": True
            }
            for product in products
        ]
        
        return results
    
    # Helper methods
    async def _get_products_by_ids(self, product_ids: List[str]) -> List[Product]:
        """Get products by IDs"""
        result = await self.db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        return result.scalars().all()
    
    async def _get_products_for_processing(self, config: Dict[str, Any]) -> List[Product]:
        """Get products for processing based on config"""
        # Implement product selection logic based on config
        # For now, return all active products
        result = await self.db.execute(
            select(Product).where(Product.is_active == True).limit(100)
        )
        return result.scalars().all()
    
    async def _validate_product(self, product: Product) -> bool:
        """Validate product data"""
        # Implement product validation logic
        return product.name and product.price and product.code
    
    async def _check_inventory(self, product: Product) -> bool:
        """Check product inventory"""
        # Implement inventory check logic
        return True  # Placeholder
    
    async def _monitor_product_registration(self, product: Product) -> Dict[str, Any]:
        """Monitor product registration status"""
        # Implement registration monitoring
        return {"success": True, "status_checks": {}, "issues": []}
    
    async def _analyze_workflow_performance(self, products: List[Product]) -> Dict[str, Any]:
        """Analyze workflow performance"""
        # Implement performance analysis
        return {"analyzed_products": len(products), "insights": []}
    
    async def _create_alert(
        self, 
        execution_id: str, 
        alert_type: str, 
        title: str, 
        message: str, 
        data: Dict[str, Any] = None
    ):
        """Create pipeline alert"""
        alert = PipelineAlert(
            execution_id=execution_id,
            alert_type=alert_type,
            title=title,
            message=message,
            alert_data=data
        )
        self.db.add(alert)
    
    async def _generate_execution_report(self, execution: PipelineExecution):
        """Generate final execution report"""
        # Implement report generation
        execution.results_summary = {
            "completed_at": execution.completed_at.isoformat(),
            "total_duration_minutes": (execution.completed_at - execution.started_at).total_seconds() / 60,
            "success_rate": execution.calculate_success_rate(),
            "products_processed": execution.products_processed
        }
    
    # Additional step processors for specialized workflows
    async def _execute_sourcing_analysis(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute detailed sourcing analysis"""
        # Implement sourcing analysis
        return {"product_results": []}
    
    async def _execute_quality_validation(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute quality validation"""
        # Implement quality validation
        return {"product_results": []}
    
    async def _pre_registration_check(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pre-registration checks"""
        # Implement pre-registration checks
        return {"product_results": []}
    
    async def _validate_registration(self, products: List[Product], config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate registration results"""
        # Implement registration validation
        return {"product_results": []}
    
    # Workflow management methods
    async def pause_workflow(self, execution_id: str):
        """Pause workflow execution"""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]["execution"]
            execution.status = WorkflowStatus.PAUSED
            await self.db.commit()
    
    async def resume_workflow(self, execution_id: str):
        """Resume paused workflow"""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]["execution"]
            execution.status = WorkflowStatus.RUNNING
            await self.db.commit()
    
    async def cancel_workflow(self, execution_id: str):
        """Cancel workflow execution"""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]["execution"]
            execution.status = WorkflowStatus.CANCELLED
            await self.db.commit()
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        if execution_id in self.active_executions:
            execution_data = self.active_executions[execution_id]
            execution = execution_data["execution"]
            
            return {
                "execution_id": execution_id,
                "workflow_name": execution.workflow_name,
                "status": execution.status,
                "progress": execution.calculate_progress(),
                "current_step": execution_data.get("current_step", 0),
                "total_steps": execution.total_steps,
                "products_processed": execution.products_processed,
                "success_rate": execution.calculate_success_rate(),
                "started_at": execution.started_at,
                "estimated_completion": execution.estimated_completion
            }
        
        # If not in active executions, fetch from database
        result = await self.db.execute(
            select(PipelineExecution).where(PipelineExecution.workflow_id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if execution:
            return {
                "execution_id": execution_id,
                "workflow_name": execution.workflow_name,
                "status": execution.status,
                "progress": execution.calculate_progress(),
                "completed_steps": execution.completed_steps,
                "total_steps": execution.total_steps,
                "products_processed": execution.products_processed,
                "success_rate": execution.calculate_success_rate(),
                "started_at": execution.started_at,
                "completed_at": execution.completed_at
            }
        
        return None
"""
Management command to run workflows.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from orchestration.models import Workflow
from orchestration.engine import WorkflowEngine


class Command(BaseCommand):
    help = 'Run a workflow'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'workflow_code',
            type=str,
            help='Workflow code to execute'
        )
        parser.add_argument(
            '--input-data',
            type=str,
            help='JSON input data for the workflow'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID who triggered the workflow'
        )
    
    def handle(self, *args, **options):
        workflow_code = options['workflow_code']
        input_data_str = options.get('input_data', '{}')
        user_id = options.get('user_id')
        
        try:
            # Parse input data
            input_data = json.loads(input_data_str)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON input data: {e}")
        
        try:
            # Get workflow
            workflow = Workflow.objects.get(code=workflow_code)
        except Workflow.DoesNotExist:
            raise CommandError(f"Workflow '{workflow_code}' not found")
        
        # Get user if specified
        triggered_by = None
        if user_id:
            try:
                triggered_by = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f"User with ID {user_id} not found")
        
        # Create engine and execute
        engine = WorkflowEngine()
        
        try:
            self.stdout.write(f"Starting workflow: {workflow.name}")
            
            execution = engine.execute_workflow(
                workflow=workflow,
                input_data=input_data,
                triggered_by=triggered_by,
                trigger_type='manual'
            )
            
            if execution.status == 'completed':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Workflow completed successfully: {execution.execution_id}"
                    )
                )
                self.stdout.write(f"Duration: {execution.duration_seconds:.2f} seconds")
                self.stdout.write(f"Steps completed: {execution.completed_steps}/{execution.total_steps}")
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Workflow failed: {execution.error_message}"
                    )
                )
            
        except Exception as e:
            raise CommandError(f"Workflow execution failed: {e}")
        
        finally:
            engine.shutdown()
"""
Management command to create workflow templates.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from orchestration.workflows import WORKFLOW_TEMPLATES, create_workflow_from_template


class Command(BaseCommand):
    help = 'Create workflow templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            type=str,
            choices=list(WORKFLOW_TEMPLATES.keys()),
            help='Specific template to create'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID who creates the workflows'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if workflow exists'
        )
    
    def handle(self, *args, **options):
        template_name = options.get('template')
        user_id = options.get('user_id')
        force = options.get('force', False)
        
        # Get user if specified
        created_by = None
        if user_id:
            try:
                created_by = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"User with ID {user_id} not found")
                )
        
        # Create templates
        templates_to_create = [template_name] if template_name else list(WORKFLOW_TEMPLATES.keys())
        
        for template in templates_to_create:
            self.create_template(template, created_by, force)
    
    def create_template(self, template_name: str, created_by: User = None, force: bool = False):
        """Create a single workflow template."""
        try:
            # Generate workflow name
            workflow_name = f"{template_name.replace('_', ' ').title()} Template"
            
            # Check if workflow already exists
            from orchestration.models import Workflow
            existing = Workflow.objects.filter(
                workflow_type=template_name,
                name__icontains='template'
            ).first()
            
            if existing and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f"Template workflow for {template_name} already exists: {existing.name}"
                    )
                )
                return
            
            # Create workflow
            workflow = create_workflow_from_template(
                template_name=template_name,
                name=workflow_name,
                created_by=created_by
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created workflow template: {workflow.name} ({workflow.code})"
                )
            )
            
            # Display steps
            steps = workflow.get_steps()
            self.stdout.write(f"  Steps created: {steps.count()}")
            for step in steps:
                self.stdout.write(f"    {step.order}. {step.name} ({step.step_type})")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to create template {template_name}: {e}"
                )
            )
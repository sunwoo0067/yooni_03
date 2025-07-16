"""
Management command to run specific Celery tasks manually.
"""
from django.core.management.base import BaseCommand, CommandError
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Run specific Celery tasks manually'

    def add_arguments(self, parser):
        parser.add_argument(
            'task_name',
            help='Name of the task to run'
        )
        parser.add_argument(
            '--args',
            help='JSON string of positional arguments for the task'
        )
        parser.add_argument(
            '--kwargs',
            help='JSON string of keyword arguments for the task'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run task asynchronously (default is synchronous)'
        )
        parser.add_argument(
            '--queue',
            help='Specify queue to run task on'
        )
        parser.add_argument(
            '--list-tasks',
            action='store_true',
            help='List all available tasks'
        )

    def handle(self, *args, **options):
        if options['list_tasks']:
            self._list_available_tasks()
            return
        
        task_name = options['task_name']
        task_args = []
        task_kwargs = {}
        
        # Parse arguments
        if options['args']:
            try:
                task_args = json.loads(options['args'])
                if not isinstance(task_args, list):
                    raise ValueError("Args must be a JSON list")
            except (json.JSONDecodeError, ValueError) as e:
                raise CommandError(f'Invalid args JSON: {e}')
        
        if options['kwargs']:
            try:
                task_kwargs = json.loads(options['kwargs'])
                if not isinstance(task_kwargs, dict):
                    raise ValueError("Kwargs must be a JSON object")
            except (json.JSONDecodeError, ValueError) as e:
                raise CommandError(f'Invalid kwargs JSON: {e}')
        
        # Import and run the task
        try:
            task_func = self._get_task_function(task_name)
            
            if options['async']:
                # Run asynchronously
                apply_kwargs = {}
                if options['queue']:
                    apply_kwargs['queue'] = options['queue']
                
                result = task_func.delay(*task_args, **task_kwargs)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Task {task_name} started asynchronously')
                )
                self.stdout.write(f'Task ID: {result.id}')
                self.stdout.write(f'Task State: {result.state}')
                
            else:
                # Run synchronously
                self.stdout.write(f'Running task {task_name} synchronously...')
                start_time = datetime.now()
                
                result = task_func(*task_args, **task_kwargs)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Task {task_name} completed in {duration:.2f} seconds')
                )
                
                # Pretty print result
                if isinstance(result, dict):
                    self.stdout.write('Result:')
                    self.stdout.write(json.dumps(result, indent=2, default=str))
                else:
                    self.stdout.write(f'Result: {result}')
                
        except Exception as e:
            raise CommandError(f'Error running task {task_name}: {str(e)}')

    def _list_available_tasks(self):
        """List all available Celery tasks."""
        
        # Import task modules to register them
        try:
            import suppliers.tasks
            import marketplaces.tasks
            import orchestration.tasks
            import ai_agents.tasks
            import analytics.tasks
            import core.tasks
        except ImportError as e:
            self.stdout.write(
                self.style.WARNING(f'Could not import some task modules: {e}')
            )
        
        from celery import current_app
        
        # Get registered tasks
        tasks = current_app.tasks
        
        # Organize tasks by module
        task_groups = {}
        for task_name in sorted(tasks.keys()):
            if task_name.startswith('celery.'):
                continue  # Skip internal Celery tasks
            
            module_name = task_name.split('.')[0] if '.' in task_name else 'other'
            if module_name not in task_groups:
                task_groups[module_name] = []
            task_groups[module_name].append(task_name)
        
        self.stdout.write(self.style.SUCCESS('Available Celery Tasks'))
        self.stdout.write('=' * 50)
        
        for module, task_list in task_groups.items():
            self.stdout.write(f'\n{module.upper()} Tasks:')
            self.stdout.write('-' * 20)
            for task in task_list:
                self.stdout.write(f'  {task}')
        
        self.stdout.write('\nUsage examples:')
        self.stdout.write('  python manage.py run_task suppliers.tasks.sync_all_suppliers')
        self.stdout.write('  python manage.py run_task suppliers.tasks.sync_supplier_products --args "[1]" --kwargs \'{"force_full_sync": true}\'')
        self.stdout.write('  python manage.py run_task core.tasks.system_health_check --async')

    def _get_task_function(self, task_name):
        """Get the task function by name."""
        
        # Common task mappings
        task_mappings = {
            # Suppliers
            'sync_all_suppliers': 'suppliers.tasks.sync_all_suppliers',
            'sync_supplier_products': 'suppliers.tasks.sync_supplier_products',
            'test_supplier_connection': 'suppliers.tasks.test_supplier_connection',
            
            # Marketplaces
            'sync_all_marketplace_orders': 'marketplaces.tasks.sync_all_marketplace_orders',
            'sync_all_marketplace_inventory': 'marketplaces.tasks.sync_all_marketplace_inventory',
            'sync_marketplace_listings': 'marketplaces.tasks.sync_marketplace_listings',
            'sync_marketplace_orders': 'marketplaces.tasks.sync_marketplace_orders',
            
            # Orchestration
            'execute_workflow': 'orchestration.tasks.execute_workflow',
            'schedule_workflow_executions': 'orchestration.tasks.schedule_workflow_executions',
            'cleanup_old_executions': 'orchestration.tasks.cleanup_old_executions',
            
            # AI Agents
            'process_ai_task': 'ai_agents.tasks.process_ai_task',
            'analyze_product_descriptions': 'ai_agents.tasks.analyze_product_descriptions',
            
            # Analytics
            'generate_daily_reports': 'analytics.tasks.generate_daily_reports',
            'generate_supplier_performance_report': 'analytics.tasks.generate_supplier_performance_report',
            
            # Core
            'system_health_check': 'core.tasks.system_health_check',
            'cleanup_system_logs': 'core.tasks.cleanup_system_logs',
            'database_maintenance': 'core.tasks.database_maintenance',
            'backup_database': 'core.tasks.backup_database'
        }
        
        # Use mapping if available, otherwise use task_name directly
        full_task_name = task_mappings.get(task_name, task_name)
        
        # Import the task
        module_path, function_name = full_task_name.rsplit('.', 1)
        
        try:
            module = __import__(module_path, fromlist=[function_name])
            task_func = getattr(module, function_name)
            
            # Verify it's a Celery task
            if not hasattr(task_func, 'delay'):
                raise AttributeError(f'{full_task_name} is not a Celery task')
            
            return task_func
            
        except (ImportError, AttributeError) as e:
            raise CommandError(f'Could not import task {full_task_name}: {e}')
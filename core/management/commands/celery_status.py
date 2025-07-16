"""
Management command to check Celery worker and queue status.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from celery import current_app
import json


class Command(BaseCommand):
    help = 'Check Celery worker and queue status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format (table or json)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed worker information'
        )

    def handle(self, *args, **options):
        output_format = options['format']
        detailed = options['detailed']
        
        try:
            inspect = current_app.control.inspect()
            
            # Get worker information
            stats = inspect.stats()
            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()
            
            if not stats:
                self.stdout.write(
                    self.style.ERROR('No Celery workers found. Make sure workers are running.')
                )
                return
            
            if output_format == 'json':
                self._output_json(stats, active, scheduled, reserved, detailed)
            else:
                self._output_table(stats, active, scheduled, reserved, detailed)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error checking Celery status: {str(e)}')
            )

    def _output_table(self, stats, active, scheduled, reserved, detailed):
        """Output status in table format."""
        
        self.stdout.write(self.style.SUCCESS('Celery Worker Status'))
        self.stdout.write('=' * 50)
        
        for worker_name, worker_stats in stats.items():
            self.stdout.write(f'\nWorker: {worker_name}')
            self.stdout.write('-' * 30)
            
            # Basic stats
            active_tasks = len(active.get(worker_name, []))
            scheduled_tasks = len(scheduled.get(worker_name, []))
            reserved_tasks = len(reserved.get(worker_name, []))
            
            self.stdout.write(f'  Active tasks: {active_tasks}')
            self.stdout.write(f'  Scheduled tasks: {scheduled_tasks}')
            self.stdout.write(f'  Reserved tasks: {reserved_tasks}')
            
            # Pool info
            pool_info = worker_stats.get('pool', {})
            if pool_info:
                self.stdout.write(f'  Pool size: {pool_info.get("max-concurrency", "N/A")}')
                self.stdout.write(f'  Pool processes: {pool_info.get("processes", [])}')
            
            # Total completed
            total_info = worker_stats.get('total', {})
            if total_info:
                for queue, count in total_info.items():
                    self.stdout.write(f'  Total {queue}: {count}')
            
            if detailed:
                # Show active task details
                if active_tasks > 0:
                    self.stdout.write(f'  \nActive tasks:')
                    for task in active.get(worker_name, []):
                        task_name = task.get('name', 'Unknown')
                        task_id = task.get('id', 'Unknown')
                        self.stdout.write(f'    - {task_name} ({task_id})')
                
                # Resource usage
                rusage = worker_stats.get('rusage', {})
                if rusage:
                    self.stdout.write(f'  \nResource usage:')
                    for key, value in rusage.items():
                        self.stdout.write(f'    {key}: {value}')
        
        # Summary
        total_workers = len(stats)
        total_active = sum(len(active.get(w, [])) for w in stats.keys())
        total_scheduled = sum(len(scheduled.get(w, [])) for w in stats.keys())
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'Summary: {total_workers} workers, {total_active} active tasks, {total_scheduled} scheduled tasks')

    def _output_json(self, stats, active, scheduled, reserved, detailed):
        """Output status in JSON format."""
        
        output_data = {
            'timestamp': timezone.now().isoformat(),
            'workers': {},
            'summary': {
                'total_workers': len(stats),
                'total_active_tasks': sum(len(active.get(w, [])) for w in stats.keys()),
                'total_scheduled_tasks': sum(len(scheduled.get(w, [])) for w in stats.keys()),
                'total_reserved_tasks': sum(len(reserved.get(w, [])) for w in stats.keys())
            }
        }
        
        for worker_name, worker_stats in stats.items():
            worker_data = {
                'active_tasks': len(active.get(worker_name, [])),
                'scheduled_tasks': len(scheduled.get(worker_name, [])),
                'reserved_tasks': len(reserved.get(worker_name, [])),
                'pool': worker_stats.get('pool', {}),
                'total': worker_stats.get('total', {})
            }
            
            if detailed:
                worker_data.update({
                    'active_task_details': active.get(worker_name, []),
                    'scheduled_task_details': scheduled.get(worker_name, []),
                    'rusage': worker_stats.get('rusage', {})
                })
            
            output_data['workers'][worker_name] = worker_data
        
        self.stdout.write(json.dumps(output_data, indent=2))
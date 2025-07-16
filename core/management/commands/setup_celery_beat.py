"""
Management command to set up Celery Beat scheduled tasks.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up Celery Beat scheduled tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Remove all existing periodic tasks before creating new ones'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all current periodic tasks'
        )
        parser.add_argument(
            '--enable-all',
            action='store_true',
            help='Enable all periodic tasks'
        )
        parser.add_argument(
            '--disable-all',
            action='store_true',
            help='Disable all periodic tasks'
        )

    def handle(self, *args, **options):
        if options['list']:
            self._list_tasks()
            return
        
        if options['enable_all']:
            self._enable_all_tasks()
            return
        
        if options['disable_all']:
            self._disable_all_tasks()
            return
        
        if options['reset']:
            self._reset_tasks()
        
        self._create_default_tasks()

    def _list_tasks(self):
        """List all current periodic tasks."""
        
        tasks = PeriodicTask.objects.all()
        
        if not tasks:
            self.stdout.write('No periodic tasks found.')
            return
        
        self.stdout.write(self.style.SUCCESS('Current Periodic Tasks'))
        self.stdout.write('=' * 60)
        
        for task in tasks:
            status = 'ENABLED' if task.enabled else 'DISABLED'
            
            # Get schedule info
            if task.interval:
                schedule = f"Every {task.interval}"
            elif task.crontab:
                schedule = f"Cron: {task.crontab}"
            else:
                schedule = "No schedule"
            
            self.stdout.write(f'\nTask: {task.name}')
            self.stdout.write(f'  Function: {task.task}')
            self.stdout.write(f'  Schedule: {schedule}')
            self.stdout.write(f'  Status: {status}')
            self.stdout.write(f'  Last run: {task.last_run_at or "Never"}')
            
            if task.args:
                self.stdout.write(f'  Args: {task.args}')
            if task.kwargs:
                self.stdout.write(f'  Kwargs: {task.kwargs}')

    def _enable_all_tasks(self):
        """Enable all periodic tasks."""
        
        updated = PeriodicTask.objects.filter(enabled=False).update(enabled=True)
        self.stdout.write(
            self.style.SUCCESS(f'Enabled {updated} periodic tasks')
        )

    def _disable_all_tasks(self):
        """Disable all periodic tasks."""
        
        updated = PeriodicTask.objects.filter(enabled=True).update(enabled=False)
        self.stdout.write(
            self.style.SUCCESS(f'Disabled {updated} periodic tasks')
        )

    def _reset_tasks(self):
        """Remove all existing periodic tasks."""
        
        count = PeriodicTask.objects.count()
        PeriodicTask.objects.all().delete()
        
        self.stdout.write(
            self.style.WARNING(f'Removed {count} existing periodic tasks')
        )

    def _create_default_tasks(self):
        """Create default periodic tasks."""
        
        self.stdout.write('Creating default periodic tasks...')
        
        # Create schedules
        schedules = self._create_schedules()
        
        # Define default tasks
        default_tasks = [
            {
                'name': 'Sync All Suppliers Hourly',
                'task': 'suppliers.tasks.sync_all_suppliers',
                'schedule': schedules['hourly'],
                'enabled': True,
                'description': 'Synchronize all supplier data every hour'
            },
            {
                'name': 'Sync Marketplace Orders Every 15 Minutes',
                'task': 'marketplaces.tasks.sync_all_marketplace_orders',
                'schedule': schedules['every_15min'],
                'enabled': True,
                'description': 'Check for new marketplace orders every 15 minutes'
            },
            {
                'name': 'Sync Marketplace Inventory Every 30 Minutes',
                'task': 'marketplaces.tasks.sync_all_marketplace_inventory',
                'schedule': schedules['every_30min'],
                'enabled': True,
                'description': 'Synchronize inventory levels every 30 minutes'
            },
            {
                'name': 'System Health Check Every 5 Minutes',
                'task': 'core.tasks.system_health_check',
                'schedule': schedules['every_5min'],
                'enabled': True,
                'description': 'Monitor system health every 5 minutes'
            },
            {
                'name': 'Generate Daily Reports',
                'task': 'analytics.tasks.generate_daily_reports',
                'schedule': schedules['daily_midnight'],
                'enabled': True,
                'description': 'Generate daily analytics reports at midnight'
            },
            {
                'name': 'Clean Up Old Executions Daily',
                'task': 'orchestration.tasks.cleanup_old_executions',
                'schedule': schedules['daily_2am'],
                'enabled': True,
                'description': 'Clean up old workflow executions at 2 AM'
            },
            {
                'name': 'Database Maintenance Weekly',
                'task': 'core.tasks.database_maintenance',
                'schedule': schedules['weekly_sunday_3am'],
                'enabled': True,
                'description': 'Perform database maintenance every Sunday at 3 AM'
            },
            {
                'name': 'System Log Cleanup Weekly',
                'task': 'core.tasks.cleanup_system_logs',
                'schedule': schedules['weekly_sunday_4am'],
                'enabled': True,
                'kwargs': json.dumps({'days_old': 30, 'max_size_mb': 100}),
                'description': 'Clean up old system logs every Sunday at 4 AM'
            },
            {
                'name': 'Database Backup Daily',
                'task': 'core.tasks.backup_database',
                'schedule': schedules['daily_3am'],
                'enabled': True,
                'description': 'Create database backup daily at 3 AM'
            },
            {
                'name': 'AI Session Cleanup Daily',
                'task': 'ai_agents.tasks.cleanup_ai_sessions',
                'schedule': schedules['daily_1am'],
                'enabled': True,
                'kwargs': json.dumps({'days_old': 7}),
                'description': 'Clean up old AI chat sessions at 1 AM'
            }
        ]
        
        # Create tasks
        created_count = 0
        for task_config in default_tasks:
            task, created = PeriodicTask.objects.get_or_create(
                name=task_config['name'],
                defaults={
                    'task': task_config['task'],
                    'enabled': task_config['enabled'],
                    'args': task_config.get('args', '[]'),
                    'kwargs': task_config.get('kwargs', '{}'),
                }
            )
            
            # Set schedule based on type
            schedule = task_config['schedule']
            if isinstance(schedule, IntervalSchedule):
                task.interval = schedule
                task.crontab = None
            elif isinstance(schedule, CrontabSchedule):
                task.crontab = schedule
                task.interval = None
            
            task.save()
            
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {task_config["name"]}')
            else:
                self.stdout.write(f'  Updated: {task_config["name"]}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Periodic tasks setup complete. Created {created_count} new tasks.')
        )
        
        # Show next steps
        self.stdout.write('\nTo start the Celery Beat scheduler, run:')
        self.stdout.write('  celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler')

    def _create_schedules(self):
        """Create and return schedule objects."""
        
        schedules = {}
        
        # Interval schedules
        schedules['every_5min'], _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )
        
        schedules['every_15min'], _ = IntervalSchedule.objects.get_or_create(
            every=15, period=IntervalSchedule.MINUTES
        )
        
        schedules['every_30min'], _ = IntervalSchedule.objects.get_or_create(
            every=30, period=IntervalSchedule.MINUTES
        )
        
        schedules['hourly'], _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.HOURS
        )
        
        # Cron schedules
        schedules['daily_midnight'], _ = CrontabSchedule.objects.get_or_create(
            minute=0, hour=0, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        
        schedules['daily_1am'], _ = CrontabSchedule.objects.get_or_create(
            minute=0, hour=1, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        
        schedules['daily_2am'], _ = CrontabSchedule.objects.get_or_create(
            minute=0, hour=2, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        
        schedules['daily_3am'], _ = CrontabSchedule.objects.get_or_create(
            minute=0, hour=3, day_of_week='*', day_of_month='*', month_of_year='*'
        )
        
        schedules['weekly_sunday_3am'], _ = CrontabSchedule.objects.get_or_create(
            minute=0, hour=3, day_of_week=0, day_of_month='*', month_of_year='*'
        )
        
        schedules['weekly_sunday_4am'], _ = CrontabSchedule.objects.get_or_create(
            minute=0, hour=4, day_of_week=0, day_of_month='*', month_of_year='*'
        )
        
        return schedules
"""
Celery configuration for Django project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('yooni_03')

# Configure Celery using settings from Django settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Additional Celery configuration
app.conf.update(
    # Task routing
    task_routes={
        'suppliers.tasks.*': {'queue': 'suppliers'},
        'marketplaces.tasks.*': {'queue': 'marketplaces'},
        'orchestration.tasks.*': {'queue': 'workflows'},
        'ai_agents.tasks.*': {'queue': 'ai_processing'},
        'analytics.tasks.*': {'queue': 'analytics'},
        'core.tasks.*': {'queue': 'maintenance'},
    },
    
    # Task result settings
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Rate limiting
    task_annotations={
        'suppliers.tasks.sync_supplier_products': {'rate_limit': '10/m'},
        'marketplaces.tasks.sync_marketplace_listings': {'rate_limit': '20/m'},
        'marketplaces.tasks.sync_marketplace_orders': {'rate_limit': '30/m'},
        'ai_agents.tasks.process_ai_task': {'rate_limit': '5/m'},
    },
    
    # Beat scheduler settings
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
    
    # Task soft time limit (10 minutes)
    task_soft_time_limit=600,
    # Task hard time limit (15 minutes)
    task_time_limit=900,
    
    # Redis connection pool settings
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        'master_name': 'master',
        'visibility_timeout': 3600,
        'retry_on_timeout': True,
    },
)

# Define periodic tasks
app.conf.beat_schedule = {
    'sync-suppliers-hourly': {
        'task': 'suppliers.tasks.sync_all_suppliers',
        'schedule': 3600.0,  # Run every hour
        'options': {'queue': 'suppliers'}
    },
    'sync-marketplace-orders-every-15min': {
        'task': 'marketplaces.tasks.sync_all_marketplace_orders',
        'schedule': 900.0,  # Run every 15 minutes
        'options': {'queue': 'marketplaces'}
    },
    'sync-marketplace-inventory-every-30min': {
        'task': 'marketplaces.tasks.sync_all_marketplace_inventory',
        'schedule': 1800.0,  # Run every 30 minutes
        'options': {'queue': 'marketplaces'}
    },
    'cleanup-old-executions-daily': {
        'task': 'orchestration.tasks.cleanup_old_executions',
        'schedule': 86400.0,  # Run daily
        'options': {'queue': 'maintenance'}
    },
    'generate-analytics-reports-daily': {
        'task': 'analytics.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Run daily at midnight
        'options': {'queue': 'analytics'}
    },
    'health-check-every-5min': {
        'task': 'core.tasks.system_health_check',
        'schedule': 300.0,  # Run every 5 minutes
        'options': {'queue': 'maintenance'}
    },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


# Celery signal handlers for monitoring
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task start."""
    logger.info(f'Task {task.name} started: {task_id}')


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task completion."""
    logger.info(f'Task {task.name} completed: {task_id} with state: {state}')


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Handle task failure."""
    logger.error(f'Task {sender.name} failed: {task_id} - {exception}')
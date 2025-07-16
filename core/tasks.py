"""
Celery tasks for core system maintenance and monitoring.
"""
import logging
import os
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone
from django.db import connection, transaction
from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings
from django.db.models import Count

logger = logging.getLogger(__name__)


@shared_task
def system_health_check() -> Dict[str, Any]:
    """
    Perform comprehensive system health check.
    
    Returns:
        Dictionary with health check results
    """
    logger.info("Performing system health check")
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'overall_status': 'healthy',
        'checks': {}
    }
    
    try:
        # Database health check
        health_data['checks']['database'] = _check_database_health()
        
        # Redis/Cache health check
        health_data['checks']['cache'] = _check_cache_health()
        
        # Disk space check
        health_data['checks']['disk_space'] = _check_disk_space()
        
        # Memory usage check
        health_data['checks']['memory'] = _check_memory_usage()
        
        # CPU usage check
        health_data['checks']['cpu'] = _check_cpu_usage()
        
        # Celery worker check
        health_data['checks']['celery_workers'] = _check_celery_workers()
        
        # Log file size check
        health_data['checks']['log_files'] = _check_log_files()
        
        # Determine overall status
        failed_checks = [
            check for check, data in health_data['checks'].items() 
            if not data.get('healthy', True)
        ]
        
        if failed_checks:
            health_data['overall_status'] = 'degraded' if len(failed_checks) <= 2 else 'unhealthy'
            health_data['failed_checks'] = failed_checks
        
        # Generate alerts for critical issues
        critical_issues = _identify_critical_issues(health_data['checks'])
        if critical_issues:
            health_data['critical_issues'] = critical_issues
            # Here you could send alerts/notifications
        
        logger.info(f"Health check completed with status: {health_data['overall_status']}")
        
        return {
            'success': True,
            'health_data': health_data
        }
        
    except Exception as e:
        error_msg = f"Error during system health check: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'health_data': health_data
        }


def _check_database_health() -> Dict[str, Any]:
    """Check database connectivity and performance."""
    try:
        start_time = timezone.now()
        
        # Test basic connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Check connection pool
        db_connections = len(connection.queries)
        
        # Measure query time
        query_time = (timezone.now() - start_time).total_seconds() * 1000
        
        return {
            'healthy': True,
            'query_time_ms': round(query_time, 2),
            'connection_count': db_connections,
            'status': 'Connected'
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e),
            'status': 'Connection failed'
        }


def _check_cache_health() -> Dict[str, Any]:
    """Check Redis/cache connectivity and performance."""
    try:
        start_time = timezone.now()
        
        # Test cache operations
        test_key = 'health_check_test'
        test_value = 'test_value'
        
        cache.set(test_key, test_value, timeout=60)
        retrieved_value = cache.get(test_key)
        cache.delete(test_key)
        
        operation_time = (timezone.now() - start_time).total_seconds() * 1000
        
        if retrieved_value != test_value:
            raise ValueError("Cache value mismatch")
        
        return {
            'healthy': True,
            'operation_time_ms': round(operation_time, 2),
            'status': 'Connected'
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e),
            'status': 'Connection failed'
        }


def _check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        # Check main application directory
        app_disk = psutil.disk_usage(settings.BASE_DIR)
        
        # Check media directory if different
        media_disk = None
        if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
            try:
                media_disk = psutil.disk_usage(settings.MEDIA_ROOT)
            except:
                pass
        
        app_free_percent = (app_disk.free / app_disk.total) * 100
        
        disk_data = {
            'healthy': app_free_percent > 10,  # Alert if less than 10% free
            'app_directory': {
                'path': str(settings.BASE_DIR),
                'total_gb': round(app_disk.total / (1024**3), 2),
                'free_gb': round(app_disk.free / (1024**3), 2),
                'used_gb': round(app_disk.used / (1024**3), 2),
                'free_percent': round(app_free_percent, 2)
            }
        }
        
        if media_disk:
            media_free_percent = (media_disk.free / media_disk.total) * 100
            disk_data['media_directory'] = {
                'path': str(settings.MEDIA_ROOT),
                'total_gb': round(media_disk.total / (1024**3), 2),
                'free_gb': round(media_disk.free / (1024**3), 2),
                'used_gb': round(media_disk.used / (1024**3), 2),
                'free_percent': round(media_free_percent, 2)
            }
            
            if media_free_percent < 10:
                disk_data['healthy'] = False
        
        return disk_data
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_memory_usage() -> Dict[str, Any]:
    """Check system memory usage."""
    try:
        memory = psutil.virtual_memory()
        
        memory_used_percent = memory.percent
        
        return {
            'healthy': memory_used_percent < 90,  # Alert if over 90% used
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'used_percent': round(memory_used_percent, 2)
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_cpu_usage() -> Dict[str, Any]:
    """Check CPU usage."""
    try:
        # Get CPU usage over 1 second interval
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get load averages (Unix only)
        load_avg = None
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
        
        cpu_data = {
            'healthy': cpu_percent < 80,  # Alert if over 80% usage
            'usage_percent': round(cpu_percent, 2),
            'cpu_count': psutil.cpu_count()
        }
        
        if load_avg:
            cpu_data['load_average'] = {
                '1min': round(load_avg[0], 2),
                '5min': round(load_avg[1], 2),
                '15min': round(load_avg[2], 2)
            }
        
        return cpu_data
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _check_celery_workers() -> Dict[str, Any]:
    """Check Celery worker status."""
    try:
        from celery import current_app
        
        # Get active workers
        inspect = current_app.control.inspect()
        
        # Check if we can get stats (indicates workers are running)
        stats = inspect.stats()
        active = inspect.active()
        
        worker_count = len(stats) if stats else 0
        active_tasks = sum(len(tasks) for tasks in active.values()) if active else 0
        
        return {
            'healthy': worker_count > 0,
            'worker_count': worker_count,
            'active_tasks': active_tasks,
            'workers': list(stats.keys()) if stats else []
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e),
            'worker_count': 0
        }


def _check_log_files() -> Dict[str, Any]:
    """Check log file sizes."""
    try:
        log_info = []
        total_size = 0
        
        # Check Django log file
        if hasattr(settings, 'LOGGING'):
            for handler_name, handler_config in settings.LOGGING.get('handlers', {}).items():
                if handler_config.get('class') == 'logging.handlers.RotatingFileHandler':
                    filename = handler_config.get('filename')
                    if filename and os.path.exists(filename):
                        file_size = os.path.getsize(filename)
                        total_size += file_size
                        
                        log_info.append({
                            'file': filename,
                            'size_mb': round(file_size / (1024**2), 2),
                            'large': file_size > 100 * 1024 * 1024  # > 100MB
                        })
        
        # Check for any large log files in logs directory
        logs_dir = settings.BASE_DIR / 'logs'
        if logs_dir.exists():
            for log_file in logs_dir.glob('*.log'):
                if log_file.is_file():
                    file_size = log_file.stat().st_size
                    if any(info['file'] == str(log_file) for info in log_info):
                        continue  # Already checked
                    
                    total_size += file_size
                    log_info.append({
                        'file': str(log_file),
                        'size_mb': round(file_size / (1024**2), 2),
                        'large': file_size > 100 * 1024 * 1024
                    })
        
        large_files = [info for info in log_info if info['large']]
        
        return {
            'healthy': len(large_files) == 0,
            'total_size_mb': round(total_size / (1024**2), 2),
            'file_count': len(log_info),
            'large_files_count': len(large_files),
            'log_files': log_info
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e)
        }


def _identify_critical_issues(checks: Dict[str, Any]) -> List[Dict[str, str]]:
    """Identify critical issues from health checks."""
    critical_issues = []
    
    # Database issues
    if not checks.get('database', {}).get('healthy', True):
        critical_issues.append({
            'type': 'database_failure',
            'severity': 'critical',
            'description': 'Database connectivity issues detected'
        })
    
    # Cache issues
    if not checks.get('cache', {}).get('healthy', True):
        critical_issues.append({
            'type': 'cache_failure',
            'severity': 'high',
            'description': 'Cache/Redis connectivity issues detected'
        })
    
    # Disk space issues
    disk_check = checks.get('disk_space', {})
    if not disk_check.get('healthy', True):
        critical_issues.append({
            'type': 'low_disk_space',
            'severity': 'high',
            'description': 'Low disk space detected'
        })
    
    # Memory issues
    memory_check = checks.get('memory', {})
    if not memory_check.get('healthy', True):
        critical_issues.append({
            'type': 'high_memory_usage',
            'severity': 'medium',
            'description': f"High memory usage: {memory_check.get('used_percent', 0)}%"
        })
    
    # CPU issues
    cpu_check = checks.get('cpu', {})
    if not cpu_check.get('healthy', True):
        critical_issues.append({
            'type': 'high_cpu_usage',
            'severity': 'medium',
            'description': f"High CPU usage: {cpu_check.get('usage_percent', 0)}%"
        })
    
    # Celery worker issues
    worker_check = checks.get('celery_workers', {})
    if not worker_check.get('healthy', True):
        critical_issues.append({
            'type': 'no_celery_workers',
            'severity': 'critical',
            'description': 'No Celery workers detected'
        })
    
    return critical_issues


@shared_task
def cleanup_system_logs(days_old: int = 30, max_size_mb: int = 100) -> Dict[str, Any]:
    """
    Clean up old system logs and large log files.
    
    Args:
        days_old: Remove logs older than this many days
        max_size_mb: Rotate logs larger than this size
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting system log cleanup - removing logs older than {days_old} days")
    
    try:
        cleanup_results = {
            'files_removed': 0,
            'files_rotated': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # Clean up logs directory
        logs_dir = settings.BASE_DIR / 'logs'
        if logs_dir.exists():
            for log_file in logs_dir.glob('*.log*'):
                try:
                    if log_file.is_file():
                        file_stat = log_file.stat()
                        file_modified = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
                        
                        # Remove old files
                        if file_modified < cutoff_date:
                            file_size = file_stat.st_size
                            log_file.unlink()
                            cleanup_results['files_removed'] += 1
                            cleanup_results['space_freed_mb'] += file_size / (1024**2)
                            logger.info(f"Removed old log file: {log_file}")
                        
                        # Rotate large files
                        elif file_stat.st_size > max_size_bytes:
                            backup_file = log_file.with_suffix(f'.log.{timezone.now().strftime("%Y%m%d_%H%M%S")}')
                            log_file.rename(backup_file)
                            log_file.touch()  # Create new empty log file
                            cleanup_results['files_rotated'] += 1
                            logger.info(f"Rotated large log file: {log_file}")
                            
                except Exception as e:
                    error_msg = f"Error processing log file {log_file}: {str(e)}"
                    cleanup_results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"Log cleanup completed: {cleanup_results}")
        
        return {
            'success': True,
            'cleanup_results': cleanup_results
        }
        
    except Exception as e:
        error_msg = f"Error during log cleanup: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def database_maintenance() -> Dict[str, Any]:
    """
    Perform database maintenance tasks.
    
    Returns:
        Dictionary with maintenance results
    """
    logger.info("Starting database maintenance")
    
    try:
        maintenance_results = {
            'operations_completed': [],
            'statistics': {},
            'errors': []
        }
        
        # Vacuum and analyze (PostgreSQL specific)
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("VACUUM ANALYZE;")
                maintenance_results['operations_completed'].append('vacuum_analyze')
                logger.info("Completed VACUUM ANALYZE")
            except Exception as e:
                maintenance_results['errors'].append(f"VACUUM ANALYZE failed: {str(e)}")
        
        # Update table statistics
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                    FROM pg_stat_user_tables 
                    ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC 
                    LIMIT 10;
                """)
                
                table_stats = cursor.fetchall()
                maintenance_results['statistics']['most_active_tables'] = [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'inserts': row[2],
                        'updates': row[3],
                        'deletes': row[4]
                    }
                    for row in table_stats
                ]
                
        except Exception as e:
            maintenance_results['errors'].append(f"Statistics collection failed: {str(e)}")
        
        # Check for long-running queries
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
                    FROM pg_stat_activity 
                    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                    AND state = 'active';
                """)
                
                long_queries = cursor.fetchall()
                if long_queries:
                    maintenance_results['statistics']['long_running_queries'] = len(long_queries)
                    logger.warning(f"Found {len(long_queries)} long-running queries")
                
        except Exception as e:
            maintenance_results['errors'].append(f"Long query check failed: {str(e)}")
        
        # Clean up orphaned records (example)
        try:
            # This is an example - customize based on your data model
            from django.apps import apps
            
            # Count total records for major models
            model_counts = {}
            for model in apps.get_models():
                try:
                    if hasattr(model, 'objects'):
                        count = model.objects.count()
                        model_counts[f"{model._meta.app_label}.{model._meta.model_name}"] = count
                except Exception:
                    continue
            
            maintenance_results['statistics']['model_record_counts'] = model_counts
            maintenance_results['operations_completed'].append('record_count_analysis')
            
        except Exception as e:
            maintenance_results['errors'].append(f"Record analysis failed: {str(e)}")
        
        logger.info(f"Database maintenance completed: {len(maintenance_results['operations_completed'])} operations")
        
        return {
            'success': True,
            'maintenance_results': maintenance_results
        }
        
    except Exception as e:
        error_msg = f"Error during database maintenance: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def backup_database() -> Dict[str, Any]:
    """
    Create database backup.
    
    Returns:
        Dictionary with backup results
    """
    logger.info("Starting database backup")
    
    try:
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"db_backup_{timestamp}.sql"
        backup_path = backup_dir / backup_filename
        
        # Use Django's dumpdata command for a simple backup
        # For production, you might want to use pg_dump for PostgreSQL
        with open(backup_path, 'w') as backup_file:
            call_command('dumpdata', stdout=backup_file, indent=2)
        
        backup_size = backup_path.stat().st_size
        
        # Clean up old backups (keep last 7 days)
        cutoff_date = timezone.now() - timedelta(days=7)
        old_backups_removed = 0
        
        for old_backup in backup_dir.glob('db_backup_*.sql'):
            try:
                file_stat = old_backup.stat()
                file_modified = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
                
                if file_modified < cutoff_date:
                    old_backup.unlink()
                    old_backups_removed += 1
                    
            except Exception as e:
                logger.warning(f"Could not remove old backup {old_backup}: {e}")
        
        logger.info(f"Database backup completed: {backup_filename}")
        
        return {
            'success': True,
            'backup_filename': backup_filename,
            'backup_path': str(backup_path),
            'backup_size_mb': round(backup_size / (1024**2), 2),
            'old_backups_removed': old_backups_removed
        }
        
    except Exception as e:
        error_msg = f"Error during database backup: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def monitor_task_queue() -> Dict[str, Any]:
    """
    Monitor Celery task queue health and performance.
    
    Returns:
        Dictionary with queue monitoring results
    """
    logger.info("Monitoring Celery task queue")
    
    try:
        from celery import current_app
        
        inspect = current_app.control.inspect()
        
        # Get queue information
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()
        stats = inspect.stats()
        
        queue_data = {
            'workers': {},
            'overall_stats': {
                'total_workers': 0,
                'total_active_tasks': 0,
                'total_scheduled_tasks': 0,
                'total_reserved_tasks': 0
            }
        }
        
        if stats:
            queue_data['overall_stats']['total_workers'] = len(stats)
            
            for worker_name, worker_stats in stats.items():
                worker_data = {
                    'active_tasks': len(active_tasks.get(worker_name, [])),
                    'scheduled_tasks': len(scheduled_tasks.get(worker_name, [])),
                    'reserved_tasks': len(reserved_tasks.get(worker_name, [])),
                    'pool_processes': worker_stats.get('pool', {}).get('max-concurrency', 0),
                    'total_completed': worker_stats.get('total', {}),
                    'rusage': worker_stats.get('rusage', {})
                }
                
                queue_data['workers'][worker_name] = worker_data
                queue_data['overall_stats']['total_active_tasks'] += worker_data['active_tasks']
                queue_data['overall_stats']['total_scheduled_tasks'] += worker_data['scheduled_tasks']
                queue_data['overall_stats']['total_reserved_tasks'] += worker_data['reserved_tasks']
        
        # Check for queue bottlenecks
        alerts = []
        
        if queue_data['overall_stats']['total_active_tasks'] > 50:
            alerts.append({
                'type': 'high_active_tasks',
                'severity': 'medium',
                'description': f"High number of active tasks: {queue_data['overall_stats']['total_active_tasks']}"
            })
        
        if queue_data['overall_stats']['total_workers'] == 0:
            alerts.append({
                'type': 'no_workers',
                'severity': 'critical',
                'description': "No Celery workers detected"
            })
        
        queue_data['alerts'] = alerts
        
        logger.info(f"Queue monitoring completed: {queue_data['overall_stats']['total_workers']} workers")
        
        return {
            'success': True,
            'queue_data': queue_data
        }
        
    except Exception as e:
        error_msg = f"Error monitoring task queue: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def system_metrics_snapshot() -> Dict[str, Any]:
    """
    Take a snapshot of system metrics for monitoring.
    
    Returns:
        Dictionary with system metrics
    """
    logger.info("Taking system metrics snapshot")
    
    try:
        metrics = {
            'timestamp': timezone.now().isoformat(),
            'system': {},
            'application': {},
            'database': {}
        }
        
        # System metrics
        metrics['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else None,
            'uptime_seconds': (timezone.now() - datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)).total_seconds()
        }
        
        # Application metrics
        try:
            from django.apps import apps
            
            # Count active objects in major models
            model_counts = {}
            for model in apps.get_models():
                try:
                    if hasattr(model, 'objects') and hasattr(model._meta, 'app_label'):
                        app_label = model._meta.app_label
                        if app_label in ['suppliers', 'marketplaces', 'orchestration']:
                            count = model.objects.count()
                            model_counts[f"{app_label}.{model._meta.model_name}"] = count
                except Exception:
                    continue
            
            metrics['application']['model_counts'] = model_counts
            
        except Exception as e:
            metrics['application']['error'] = str(e)
        
        # Database metrics
        try:
            with connection.cursor() as cursor:
                # Database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size;
                """)
                db_size = cursor.fetchone()[0]
                
                # Connection count
                cursor.execute("""
                    SELECT count(*) FROM pg_stat_activity;
                """)
                connection_count = cursor.fetchone()[0]
                
                metrics['database'] = {
                    'size': db_size,
                    'connections': connection_count
                }
                
        except Exception as e:
            metrics['database']['error'] = str(e)
        
        logger.info("System metrics snapshot completed")
        
        return {
            'success': True,
            'metrics': metrics
        }
        
    except Exception as e:
        error_msg = f"Error taking system metrics snapshot: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }
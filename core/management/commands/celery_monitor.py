"""
Management command to monitor Celery task execution and performance.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from celery import current_app
import time
import json
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Monitor Celery task execution and performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='Monitor duration in seconds (default: 60)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Check interval in seconds (default: 5)'
        )
        parser.add_argument(
            '--output-file',
            help='Save monitoring data to JSON file'
        )
        parser.add_argument(
            '--workers',
            help='Comma-separated list of workers to monitor (default: all)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimize output (only show summary)'
        )

    def handle(self, *args, **options):
        duration = options['duration']
        interval = options['interval']
        output_file = options['output_file']
        workers_filter = options['workers'].split(',') if options['workers'] else None
        quiet = options['quiet']
        
        if not quiet:
            self.stdout.write(
                self.style.SUCCESS(f'Starting Celery monitoring for {duration} seconds...')
            )
        
        monitoring_data = {
            'start_time': timezone.now().isoformat(),
            'duration_seconds': duration,
            'interval_seconds': interval,
            'snapshots': [],
            'summary': {}
        }
        
        start_time = time.time()
        end_time = start_time + duration
        
        try:
            while time.time() < end_time:
                snapshot = self._take_snapshot(workers_filter)
                monitoring_data['snapshots'].append(snapshot)
                
                if not quiet:
                    self._display_snapshot(snapshot)
                
                time.sleep(interval)
            
            # Generate summary
            monitoring_data['summary'] = self._generate_summary(monitoring_data['snapshots'])
            
            if not quiet:
                self._display_summary(monitoring_data['summary'])
            
            # Save to file if requested
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(monitoring_data, f, indent=2, default=str)
                self.stdout.write(
                    self.style.SUCCESS(f'Monitoring data saved to {output_file}')
                )
            
        except KeyboardInterrupt:
            if not quiet:
                self.stdout.write(self.style.WARNING('\nMonitoring interrupted by user'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during monitoring: {str(e)}')
            )

    def _take_snapshot(self, workers_filter=None):
        """Take a snapshot of current Celery state."""
        
        try:
            inspect = current_app.control.inspect()
            
            stats = inspect.stats()
            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()
            
            if not stats:
                return {
                    'timestamp': timezone.now().isoformat(),
                    'error': 'No workers available',
                    'workers': {}
                }
            
            # Filter workers if specified
            if workers_filter:
                stats = {k: v for k, v in stats.items() if any(f in k for f in workers_filter)}
                active = {k: v for k, v in active.items() if any(f in k for f in workers_filter)}
                scheduled = {k: v for k, v in scheduled.items() if any(f in k for f in workers_filter)}
                reserved = {k: v for k, v in reserved.items() if any(f in k for f in workers_filter)}
            
            snapshot = {
                'timestamp': timezone.now().isoformat(),
                'workers': {}
            }
            
            for worker_name in stats.keys():
                worker_data = {
                    'active_count': len(active.get(worker_name, [])),
                    'scheduled_count': len(scheduled.get(worker_name, [])),
                    'reserved_count': len(reserved.get(worker_name, [])),
                    'active_tasks': [
                        {
                            'name': task.get('name'),
                            'id': task.get('id'),
                            'time_start': task.get('time_start')
                        }
                        for task in active.get(worker_name, [])
                    ]
                }
                
                # Add pool info
                pool_info = stats[worker_name].get('pool', {})
                worker_data['pool_size'] = pool_info.get('max-concurrency', 0)
                
                snapshot['workers'][worker_name] = worker_data
            
            return snapshot
            
        except Exception as e:
            return {
                'timestamp': timezone.now().isoformat(),
                'error': str(e),
                'workers': {}
            }

    def _display_snapshot(self, snapshot):
        """Display a monitoring snapshot."""
        
        timestamp = snapshot['timestamp']
        error = snapshot.get('error')
        
        if error:
            self.stdout.write(f'[{timestamp}] ERROR: {error}')
            return
        
        workers = snapshot['workers']
        total_active = sum(w['active_count'] for w in workers.values())
        total_scheduled = sum(w['scheduled_count'] for w in workers.values())
        
        self.stdout.write(
            f'[{timestamp}] Workers: {len(workers)} | '
            f'Active: {total_active} | Scheduled: {total_scheduled}'
        )
        
        # Show active tasks
        for worker_name, worker_data in workers.items():
            if worker_data['active_count'] > 0:
                active_tasks = ', '.join(t['name'] for t in worker_data['active_tasks'])
                self.stdout.write(f'  {worker_name}: {active_tasks}')

    def _generate_summary(self, snapshots):
        """Generate monitoring summary from snapshots."""
        
        if not snapshots:
            return {'error': 'No snapshots collected'}
        
        # Filter out error snapshots
        valid_snapshots = [s for s in snapshots if 'error' not in s]
        
        if not valid_snapshots:
            return {'error': 'No valid snapshots collected'}
        
        # Calculate statistics
        all_workers = set()
        task_counts = []
        active_task_names = []
        
        for snapshot in valid_snapshots:
            workers = snapshot['workers']
            all_workers.update(workers.keys())
            
            total_active = sum(w['active_count'] for w in workers.values())
            total_scheduled = sum(w['scheduled_count'] for w in workers.values())
            
            task_counts.append({
                'active': total_active,
                'scheduled': total_scheduled,
                'total': total_active + total_scheduled
            })
            
            # Collect task names
            for worker_data in workers.values():
                for task in worker_data['active_tasks']:
                    active_task_names.append(task['name'])
        
        # Count task occurrences
        task_frequency = {}
        for task_name in active_task_names:
            task_frequency[task_name] = task_frequency.get(task_name, 0) + 1
        
        # Calculate averages
        avg_active = sum(tc['active'] for tc in task_counts) / len(task_counts)
        avg_scheduled = sum(tc['scheduled'] for tc in task_counts) / len(task_counts)
        max_active = max(tc['active'] for tc in task_counts)
        max_scheduled = max(tc['scheduled'] for tc in task_counts)
        
        summary = {
            'snapshots_collected': len(valid_snapshots),
            'unique_workers': list(all_workers),
            'worker_count': len(all_workers),
            'task_statistics': {
                'average_active': round(avg_active, 2),
                'average_scheduled': round(avg_scheduled, 2),
                'max_active': max_active,
                'max_scheduled': max_scheduled
            },
            'most_frequent_tasks': sorted(
                task_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
        
        return summary

    def _display_summary(self, summary):
        """Display monitoring summary."""
        
        if 'error' in summary:
            self.stdout.write(self.style.ERROR(f'Summary Error: {summary["error"]}'))
            return
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('MONITORING SUMMARY'))
        self.stdout.write('=' * 60)
        
        self.stdout.write(f'Snapshots collected: {summary["snapshots_collected"]}')
        self.stdout.write(f'Workers monitored: {summary["worker_count"]}')
        
        if summary['unique_workers']:
            self.stdout.write('Workers: ' + ', '.join(summary['unique_workers']))
        
        stats = summary['task_statistics']
        self.stdout.write(f'\nTask Statistics:')
        self.stdout.write(f'  Average active tasks: {stats["average_active"]}')
        self.stdout.write(f'  Average scheduled tasks: {stats["average_scheduled"]}')
        self.stdout.write(f'  Peak active tasks: {stats["max_active"]}')
        self.stdout.write(f'  Peak scheduled tasks: {stats["max_scheduled"]}')
        
        if summary['most_frequent_tasks']:
            self.stdout.write(f'\nMost frequent tasks:')
            for task_name, count in summary['most_frequent_tasks']:
                self.stdout.write(f'  {task_name}: {count} executions')
        
        self.stdout.write('=' * 60)
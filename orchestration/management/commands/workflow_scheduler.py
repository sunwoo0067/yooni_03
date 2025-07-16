"""
Management command to run the workflow scheduler.
"""
import asyncio
import signal
import sys
from django.core.management.base import BaseCommand

from orchestration.engine import WorkflowEngine, WorkflowScheduler


class Command(BaseCommand):
    help = 'Run the workflow scheduler daemon'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = None
        self.engine = None
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--max-workers',
            type=int,
            default=5,
            help='Maximum number of parallel workers'
        )
    
    def handle(self, *args, **options):
        max_workers = options['max_workers']
        
        # Create engine and scheduler
        self.engine = WorkflowEngine(max_workers=max_workers)
        self.scheduler = WorkflowScheduler(self.engine)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stdout.write("Starting workflow scheduler...")
        self.stdout.write(f"Max workers: {max_workers}")
        
        try:
            # Run scheduler
            asyncio.run(self.scheduler.start())
        except KeyboardInterrupt:
            self.stdout.write("Received interrupt signal")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Scheduler error: {e}"))
        finally:
            self.cleanup()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.stdout.write(f"Received signal {signum}, shutting down...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.scheduler:
            self.scheduler.stop()
        
        if self.engine:
            self.engine.shutdown()
        
        self.stdout.write("Workflow scheduler stopped")
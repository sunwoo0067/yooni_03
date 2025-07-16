"""
Management command to test supplier connections.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from suppliers.models import Supplier


class Command(BaseCommand):
    help = 'Test connection to one or more suppliers'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'supplier_codes',
            nargs='*',
            help='Supplier codes to test (leave empty to test all active suppliers)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Test all suppliers regardless of status'
        )
        parser.add_argument(
            '--update-status',
            action='store_true',
            help='Update supplier sync status based on test results'
        )
    
    def handle(self, *args, **options):
        supplier_codes = options['supplier_codes']
        test_all = options['all']
        update_status = options['update_status']
        
        # Get suppliers to test
        if supplier_codes:
            suppliers = Supplier.objects.filter(code__in=supplier_codes)
            if not suppliers.exists():
                raise CommandError(f"No suppliers found with codes: {', '.join(supplier_codes)}")
        elif test_all:
            suppliers = Supplier.objects.all()
        else:
            suppliers = Supplier.objects.filter(status='active')
        
        if not suppliers.exists():
            self.stdout.write(self.style.WARNING('No suppliers to test.'))
            return
        
        self.stdout.write(f"Testing {suppliers.count()} supplier(s)...\n")
        
        success_count = 0
        failure_count = 0
        
        for supplier in suppliers:
            self.stdout.write(f"\nTesting {supplier.name} ({supplier.code})...")
            
            try:
                connector = supplier.get_connector()
                
                # Test credentials
                is_valid, cred_error = connector.validate_credentials()
                if not is_valid:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Invalid credentials: {cred_error}")
                    )
                    failure_count += 1
                    if update_status:
                        supplier.update_sync_status(False, f"Invalid credentials: {cred_error}")
                    continue
                
                self.stdout.write(self.style.SUCCESS("  ✓ Credentials valid"))
                
                # Test connection
                is_connected, conn_error = connector.test_connection()
                if not is_connected:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Connection failed: {conn_error}")
                    )
                    failure_count += 1
                    if update_status:
                        supplier.update_sync_status(False, f"Connection failed: {conn_error}")
                    continue
                
                self.stdout.write(self.style.SUCCESS("  ✓ Connection successful"))
                
                # Get rate limit info if available
                rate_info = connector.get_rate_limit_info()
                if rate_info.get('limit'):
                    self.stdout.write(
                        f"  Rate limit: {rate_info.get('requests_remaining', 'N/A')}/"
                        f"{rate_info['limit']} requests"
                    )
                
                success_count += 1
                if update_status:
                    supplier.update_sync_status(True)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Unexpected error: {str(e)}")
                )
                failure_count += 1
                if update_status:
                    supplier.update_sync_status(False, f"Test error: {str(e)}")
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Total tested: {suppliers.count()}")
        self.stdout.write(
            self.style.SUCCESS(f"Successful: {success_count}")
        )
        if failure_count > 0:
            self.stdout.write(
                self.style.ERROR(f"Failed: {failure_count}")
            )
        
        if update_status:
            self.stdout.write("\nSupplier statuses have been updated.")
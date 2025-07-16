"""
Management command to sync data with marketplaces.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from marketplaces.models import Marketplace


class Command(BaseCommand):
    help = 'Sync data with configured marketplaces'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--marketplace',
            type=str,
            help='Code of specific marketplace to sync (sync all if not provided)',
        )
        parser.add_argument(
            '--listings',
            action='store_true',
            help='Sync listings',
        )
        parser.add_argument(
            '--orders',
            action='store_true',
            help='Sync orders',
        )
        parser.add_argument(
            '--inventory',
            action='store_true',
            help='Sync inventory',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if not due',
        )
    
    def handle(self, *args, **options):
        marketplace_code = options.get('marketplace')
        sync_listings = options.get('listings', False)
        sync_orders = options.get('orders', False)
        sync_inventory = options.get('inventory', False)
        force = options.get('force', False)
        
        # If no specific sync type is specified, sync all
        if not any([sync_listings, sync_orders, sync_inventory]):
            sync_listings = sync_orders = sync_inventory = True
        
        # Get marketplaces to sync
        if marketplace_code:
            try:
                marketplaces = [Marketplace.objects.get(code=marketplace_code)]
            except Marketplace.DoesNotExist:
                raise CommandError(f'Marketplace with code "{marketplace_code}" does not exist')
        else:
            marketplaces = Marketplace.objects.filter(
                status='active',
                is_auto_sync_enabled=True
            )
        
        self.stdout.write(f'Found {len(marketplaces)} marketplace(s) to sync')
        
        for marketplace in marketplaces:
            if not force and not marketplace.is_sync_due:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping {marketplace.name} - sync not due yet'
                    )
                )
                continue
            
            self.stdout.write(f'\nSyncing {marketplace.name}...')
            
            try:
                connector = marketplace.get_connector()
                
                # Test connection first
                connected, error = connector.test_connection()
                if not connected:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Connection failed: {error}'
                        )
                    )
                    marketplace.update_sync_status(False, error)
                    continue
                
                errors = []
                
                # Sync orders
                if sync_orders:
                    self.stdout.write('  Syncing orders...')
                    try:
                        orders = connector.fetch_orders()
                        self.stdout.write(f'    Found {len(orders)} orders')
                        # Process orders here
                    except Exception as e:
                        errors.append(f'Orders sync error: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'    Error: {str(e)}')
                        )
                
                # Sync listings
                if sync_listings:
                    self.stdout.write('  Syncing listings...')
                    try:
                        listings = connector.search_listings()
                        self.stdout.write(f'    Found {len(listings)} listings')
                        # Process listings here
                    except Exception as e:
                        errors.append(f'Listings sync error: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'    Error: {str(e)}')
                        )
                
                # Sync inventory
                if sync_inventory:
                    self.stdout.write('  Syncing inventory...')
                    try:
                        inventory_items = marketplace.inventory_items.filter(
                            sync_status__in=['pending', 'error']
                        )
                        synced = 0
                        for item in inventory_items:
                            if item.sync_to_marketplace():
                                synced += 1
                        self.stdout.write(f'    Synced {synced} inventory items')
                    except Exception as e:
                        errors.append(f'Inventory sync error: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'    Error: {str(e)}')
                        )
                
                # Update sync status
                if errors:
                    marketplace.update_sync_status(False, '; '.join(errors))
                    self.stdout.write(
                        self.style.ERROR(
                            f'Sync completed with errors for {marketplace.name}'
                        )
                    )
                else:
                    marketplace.update_sync_status(True)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sync completed successfully for {marketplace.name}'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Unexpected error for {marketplace.name}: {str(e)}'
                    )
                )
                marketplace.update_sync_status(False, str(e))
        
        self.stdout.write(self.style.SUCCESS('\nMarketplace sync completed'))
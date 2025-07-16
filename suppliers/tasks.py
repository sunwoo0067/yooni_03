"""
Celery tasks for supplier data synchronization and management.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings

from .models import Supplier, SupplierProduct
from .connectors.factory import create_connector

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_supplier_products(self, supplier_id: int, force_full_sync: bool = False) -> Dict[str, Any]:
    """
    Synchronize products from a specific supplier.
    
    Args:
        supplier_id: ID of the supplier to sync
        force_full_sync: Whether to force a full sync regardless of last sync time
        
    Returns:
        Dictionary with sync results
    """
    try:
        supplier = Supplier.objects.get(id=supplier_id)
        logger.info(f"Starting product sync for supplier: {supplier.name}")
        
        # Check if supplier is active and configured
        if supplier.status != 'active':
            logger.warning(f"Supplier {supplier.name} is not active, skipping sync")
            return {
                'success': False,
                'error': 'Supplier is not active',
                'supplier_id': supplier_id
            }
        
        # Get connector for the supplier
        connector = create_connector(supplier)
        if not connector:
            error_msg = f"No connector available for supplier {supplier.name}"
            logger.error(error_msg)
            supplier.update_sync_status(False, error_msg)
            return {
                'success': False,
                'error': error_msg,
                'supplier_id': supplier_id
            }
        
        # Determine sync parameters
        last_sync = supplier.last_sync_at
        if force_full_sync or not last_sync:
            since = None
        else:
            # Only sync products updated since last sync
            since = last_sync
        
        # Fetch products from supplier
        logger.info(f"Fetching products from {supplier.name} since {since}")
        products_data = connector.get_products(since=since)
        
        if not products_data:
            logger.warning(f"No products returned from {supplier.name}")
            supplier.update_sync_status(True, "")
            return {
                'success': True,
                'products_processed': 0,
                'products_created': 0,
                'products_updated': 0,
                'supplier_id': supplier_id
            }
        
        # Process products
        stats = _process_supplier_products(supplier, products_data)
        
        # Update supplier sync status
        supplier.update_sync_status(True, "")
        supplier.total_products = SupplierProduct.objects.filter(
            supplier=supplier,
            status='active'
        ).count()
        supplier.save(update_fields=['total_products'])
        
        logger.info(f"Completed product sync for {supplier.name}: {stats}")
        
        return {
            'success': True,
            'supplier_id': supplier_id,
            'supplier_name': supplier.name,
            **stats
        }
        
    except Supplier.DoesNotExist:
        error_msg = f"Supplier with ID {supplier_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'supplier_id': supplier_id
        }
        
    except Exception as e:
        error_msg = f"Error syncing supplier {supplier_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Update supplier with error status
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            supplier.update_sync_status(False, error_msg)
        except:
            pass
            
        # Retry the task
        raise self.retry(exc=e, countdown=60)


def _process_supplier_products(supplier: Supplier, products_data: List[Dict]) -> Dict[str, int]:
    """
    Process and save supplier products data.
    
    Args:
        supplier: Supplier instance
        products_data: List of product data dictionaries
        
    Returns:
        Statistics about processed products
    """
    stats = {
        'products_processed': 0,
        'products_created': 0,
        'products_updated': 0,
        'products_errors': 0
    }
    
    with transaction.atomic():
        for product_data in products_data:
            try:
                stats['products_processed'] += 1
                
                # Get or create product
                supplier_sku = product_data.get('sku') or product_data.get('id')
                if not supplier_sku:
                    logger.warning(f"Product missing SKU/ID: {product_data}")
                    stats['products_errors'] += 1
                    continue
                
                product, created = SupplierProduct.objects.get_or_create(
                    supplier=supplier,
                    supplier_sku=supplier_sku,
                    defaults={
                        'supplier_name': product_data.get('name', ''),
                        'description': product_data.get('description', ''),
                        'category': product_data.get('category', ''),
                        'brand': product_data.get('brand', ''),
                        'cost_price': _safe_decimal(product_data.get('price')),
                        'msrp': _safe_decimal(product_data.get('msrp')),
                        'quantity_available': product_data.get('quantity', 0),
                        'min_order_quantity': product_data.get('min_order_qty', 1),
                        'weight': _safe_decimal(product_data.get('weight')),
                        'currency': product_data.get('currency', 'USD'),
                        'status': 'active' if product_data.get('available', True) else 'inactive'
                    }
                )
                
                if created:
                    stats['products_created'] += 1
                    logger.debug(f"Created new product: {supplier_sku}")
                else:
                    stats['products_updated'] += 1
                    logger.debug(f"Updated existing product: {supplier_sku}")
                
                # Update product data from supplier
                product.update_from_supplier_data(product_data)
                product.save()
                
            except Exception as e:
                logger.error(f"Error processing product {product_data}: {e}")
                stats['products_errors'] += 1
                continue
    
    return stats


def _safe_decimal(value: Any) -> Optional[Decimal]:
    """Safely convert value to Decimal."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except:
        return None


@shared_task(bind=True)
def sync_all_suppliers(self) -> Dict[str, Any]:
    """
    Sync all active suppliers that are due for synchronization.
    
    Returns:
        Dictionary with overall sync results
    """
    logger.info("Starting sync for all suppliers")
    
    # Get suppliers due for sync
    suppliers_to_sync = Supplier.objects.filter(
        status='active',
        is_auto_sync_enabled=True
    )
    
    # Filter to only those due for sync
    due_suppliers = []
    for supplier in suppliers_to_sync:
        if supplier.is_sync_due:
            due_suppliers.append(supplier)
    
    if not due_suppliers:
        logger.info("No suppliers due for sync")
        return {
            'success': True,
            'suppliers_total': suppliers_to_sync.count(),
            'suppliers_synced': 0,
            'message': 'No suppliers due for sync'
        }
    
    # Start sync tasks for each supplier
    sync_results = []
    for supplier in due_suppliers:
        try:
            result = sync_supplier_products.delay(supplier.id)
            sync_results.append({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'task_id': result.id
            })
            logger.info(f"Started sync task for supplier {supplier.name}: {result.id}")
        except Exception as e:
            logger.error(f"Failed to start sync task for supplier {supplier.name}: {e}")
    
    return {
        'success': True,
        'suppliers_total': len(due_suppliers),
        'suppliers_synced': len(sync_results),
        'sync_tasks': sync_results
    }


@shared_task(bind=True, max_retries=2)
def test_supplier_connection(self, supplier_id: int) -> Dict[str, Any]:
    """
    Test connection to a supplier's API.
    
    Args:
        supplier_id: ID of the supplier to test
        
    Returns:
        Dictionary with connection test results
    """
    try:
        supplier = Supplier.objects.get(id=supplier_id)
        logger.info(f"Testing connection to supplier: {supplier.name}")
        
        # Get connector for the supplier
        connector = create_connector(supplier)
        if not connector:
            return {
                'success': False,
                'error': 'No connector available for supplier',
                'supplier_id': supplier_id
            }
        
        # Test the connection
        test_result = connector.test_connection()
        
        if test_result.get('success', False):
            logger.info(f"Connection test successful for {supplier.name}")
            return {
                'success': True,
                'supplier_id': supplier_id,
                'supplier_name': supplier.name,
                'message': 'Connection successful',
                'details': test_result
            }
        else:
            error_msg = test_result.get('error', 'Unknown connection error')
            logger.error(f"Connection test failed for {supplier.name}: {error_msg}")
            return {
                'success': False,
                'supplier_id': supplier_id,
                'supplier_name': supplier.name,
                'error': error_msg
            }
            
    except Supplier.DoesNotExist:
        error_msg = f"Supplier with ID {supplier_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'supplier_id': supplier_id
        }
        
    except Exception as e:
        error_msg = f"Error testing supplier connection {supplier_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise self.retry(exc=e, countdown=30)


@shared_task
def update_supplier_inventory(supplier_id: int, inventory_updates: List[Dict]) -> Dict[str, Any]:
    """
    Update inventory levels for supplier products.
    
    Args:
        supplier_id: ID of the supplier
        inventory_updates: List of inventory update dictionaries
        
    Returns:
        Dictionary with update results
    """
    try:
        supplier = Supplier.objects.get(id=supplier_id)
        logger.info(f"Updating inventory for supplier: {supplier.name}")
        
        stats = {
            'updates_processed': 0,
            'updates_successful': 0,
            'updates_failed': 0
        }
        
        with transaction.atomic():
            for update in inventory_updates:
                stats['updates_processed'] += 1
                
                try:
                    supplier_sku = update.get('sku')
                    new_quantity = update.get('quantity', 0)
                    
                    if not supplier_sku:
                        stats['updates_failed'] += 1
                        continue
                    
                    # Update product quantity
                    product = SupplierProduct.objects.get(
                        supplier=supplier,
                        supplier_sku=supplier_sku
                    )
                    
                    old_quantity = product.quantity_available
                    product.quantity_available = new_quantity
                    product.last_updated_from_supplier = timezone.now()
                    product.save(update_fields=[
                        'quantity_available',
                        'last_updated_from_supplier'
                    ])
                    
                    stats['updates_successful'] += 1
                    logger.debug(f"Updated inventory for {supplier_sku}: {old_quantity} -> {new_quantity}")
                    
                except SupplierProduct.DoesNotExist:
                    logger.warning(f"Product not found for SKU: {supplier_sku}")
                    stats['updates_failed'] += 1
                    continue
                    
                except Exception as e:
                    logger.error(f"Error updating inventory for {supplier_sku}: {e}")
                    stats['updates_failed'] += 1
                    continue
        
        logger.info(f"Completed inventory update for {supplier.name}: {stats}")
        
        return {
            'success': True,
            'supplier_id': supplier_id,
            'supplier_name': supplier.name,
            **stats
        }
        
    except Supplier.DoesNotExist:
        error_msg = f"Supplier with ID {supplier_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'supplier_id': supplier_id
        }
        
    except Exception as e:
        error_msg = f"Error updating supplier inventory {supplier_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'supplier_id': supplier_id
        }


@shared_task
def cleanup_supplier_data(days_old: int = 90) -> Dict[str, Any]:
    """
    Clean up old supplier data and logs.
    
    Args:
        days_old: Remove data older than this many days
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting supplier data cleanup for items older than {days_old} days")
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Clean up discontinued products
    discontinued_products = SupplierProduct.objects.filter(
        status='discontinued',
        updated_at__lt=cutoff_date
    )
    
    products_deleted = discontinued_products.count()
    discontinued_products.delete()
    
    logger.info(f"Cleaned up {products_deleted} discontinued products")
    
    return {
        'success': True,
        'products_deleted': products_deleted,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def generate_supplier_report(supplier_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate performance report for suppliers.
    
    Args:
        supplier_id: Optional specific supplier ID, otherwise all suppliers
        
    Returns:
        Dictionary with report data
    """
    logger.info("Generating supplier performance report")
    
    try:
        if supplier_id:
            suppliers = Supplier.objects.filter(id=supplier_id)
        else:
            suppliers = Supplier.objects.filter(status='active')
        
        report_data = []
        
        for supplier in suppliers:
            products_count = supplier.products.filter(status='active').count()
            in_stock_count = supplier.products.filter(
                status='active',
                quantity_available__gt=0
            ).count()
            
            avg_cost = supplier.products.filter(
                status='active',
                cost_price__isnull=False
            ).aggregate(avg_cost=models.Avg('cost_price'))['avg_cost'] or 0
            
            report_data.append({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'total_products': products_count,
                'in_stock_products': in_stock_count,
                'out_of_stock_products': products_count - in_stock_count,
                'average_cost_price': float(avg_cost),
                'last_sync_at': supplier.last_sync_at.isoformat() if supplier.last_sync_at else None,
                'sync_status': supplier.last_sync_status
            })
        
        logger.info(f"Generated report for {len(suppliers)} suppliers")
        
        return {
            'success': True,
            'suppliers_count': len(suppliers),
            'report_data': report_data,
            'generated_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error generating supplier report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }
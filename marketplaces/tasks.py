"""
Celery tasks for marketplace data synchronization and management.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task, group
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Avg, Sum, Count

from .models import (
    Marketplace, MarketplaceListing, MarketplaceOrder, 
    MarketplaceInventory
)
from .connectors.factory import create_connector

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_marketplace_listings(self, marketplace_id: int, force_full_sync: bool = False) -> Dict[str, Any]:
    """
    Synchronize listings from a specific marketplace.
    
    Args:
        marketplace_id: ID of the marketplace to sync
        force_full_sync: Whether to force a full sync
        
    Returns:
        Dictionary with sync results
    """
    try:
        marketplace = Marketplace.objects.get(id=marketplace_id)
        logger.info(f"Starting listing sync for marketplace: {marketplace.name}")
        
        if marketplace.status != 'active':
            logger.warning(f"Marketplace {marketplace.name} is not active, skipping sync")
            return {
                'success': False,
                'error': 'Marketplace is not active',
                'marketplace_id': marketplace_id
            }
        
        # Get connector
        connector = create_connector(marketplace)
        if not connector:
            error_msg = f"No connector available for marketplace {marketplace.name}"
            logger.error(error_msg)
            marketplace.update_sync_status(False, error_msg)
            return {
                'success': False,
                'error': error_msg,
                'marketplace_id': marketplace_id
            }
        
        # Determine sync parameters
        since = None if force_full_sync else marketplace.last_sync_at
        
        # Fetch listings from marketplace
        logger.info(f"Fetching listings from {marketplace.name} since {since}")
        listings_data = connector.get_listings(since=since)
        
        if not listings_data:
            logger.warning(f"No listings returned from {marketplace.name}")
            marketplace.update_sync_status(True, "")
            return {
                'success': True,
                'listings_processed': 0,
                'listings_created': 0,
                'listings_updated': 0,
                'marketplace_id': marketplace_id
            }
        
        # Process listings
        stats = _process_marketplace_listings(marketplace, listings_data)
        
        # Update marketplace sync status
        marketplace.update_sync_status(True, "")
        marketplace.total_listings = MarketplaceListing.objects.filter(
            marketplace=marketplace,
            status='active'
        ).count()
        marketplace.save(update_fields=['total_listings'])
        
        logger.info(f"Completed listing sync for {marketplace.name}: {stats}")
        
        return {
            'success': True,
            'marketplace_id': marketplace_id,
            'marketplace_name': marketplace.name,
            **stats
        }
        
    except Marketplace.DoesNotExist:
        error_msg = f"Marketplace with ID {marketplace_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'marketplace_id': marketplace_id
        }
        
    except Exception as e:
        error_msg = f"Error syncing marketplace listings {marketplace_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        try:
            marketplace = Marketplace.objects.get(id=marketplace_id)
            marketplace.update_sync_status(False, error_msg)
        except:
            pass
            
        raise self.retry(exc=e, countdown=60)


def _process_marketplace_listings(marketplace: Marketplace, listings_data: List[Dict]) -> Dict[str, int]:
    """Process and save marketplace listings data."""
    stats = {
        'listings_processed': 0,
        'listings_created': 0,
        'listings_updated': 0,
        'listings_errors': 0
    }
    
    with transaction.atomic():
        for listing_data in listings_data:
            try:
                stats['listings_processed'] += 1
                
                listing_id = listing_data.get('listing_id') or listing_data.get('id')
                if not listing_id:
                    logger.warning(f"Listing missing ID: {listing_data}")
                    stats['listings_errors'] += 1
                    continue
                
                listing, created = MarketplaceListing.objects.get_or_create(
                    marketplace=marketplace,
                    marketplace_listing_id=listing_id,
                    defaults={
                        'marketplace_sku': listing_data.get('sku', ''),
                        'title': listing_data.get('title', ''),
                        'description': listing_data.get('description', ''),
                        'price': Decimal(str(listing_data.get('price', 0))),
                        'quantity_listed': listing_data.get('quantity', 0),
                        'status': listing_data.get('status', 'active'),
                        'marketplace_category_id': listing_data.get('category_id', ''),
                        'marketplace_category_name': listing_data.get('category_name', ''),
                        'listing_url': listing_data.get('url', ''),
                        'views': listing_data.get('views', 0),
                        'watchers': listing_data.get('watchers', 0)
                    }
                )
                
                if created:
                    stats['listings_created'] += 1
                    logger.debug(f"Created new listing: {listing_id}")
                else:
                    stats['listings_updated'] += 1
                    logger.debug(f"Updated existing listing: {listing_id}")
                
                # Update listing data from marketplace
                listing.update_from_marketplace(listing_data)
                listing.save()
                
            except Exception as e:
                logger.error(f"Error processing listing {listing_data}: {e}")
                stats['listings_errors'] += 1
                continue
    
    return stats


@shared_task(bind=True, max_retries=3)
def sync_marketplace_orders(self, marketplace_id: int, days_back: int = 7) -> Dict[str, Any]:
    """
    Synchronize orders from a specific marketplace.
    
    Args:
        marketplace_id: ID of the marketplace to sync
        days_back: Number of days back to sync orders
        
    Returns:
        Dictionary with sync results
    """
    try:
        marketplace = Marketplace.objects.get(id=marketplace_id)
        logger.info(f"Starting order sync for marketplace: {marketplace.name}")
        
        if marketplace.status != 'active':
            logger.warning(f"Marketplace {marketplace.name} is not active, skipping sync")
            return {
                'success': False,
                'error': 'Marketplace is not active',
                'marketplace_id': marketplace_id
            }
        
        # Get connector
        connector = create_connector(marketplace)
        if not connector:
            error_msg = f"No connector available for marketplace {marketplace.name}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'marketplace_id': marketplace_id
            }
        
        # Calculate date range
        since = timezone.now() - timedelta(days=days_back)
        
        # Fetch orders from marketplace
        logger.info(f"Fetching orders from {marketplace.name} since {since}")
        orders_data = connector.get_orders(since=since)
        
        if not orders_data:
            logger.info(f"No orders returned from {marketplace.name}")
            return {
                'success': True,
                'orders_processed': 0,
                'orders_created': 0,
                'orders_updated': 0,
                'marketplace_id': marketplace_id
            }
        
        # Process orders
        stats = _process_marketplace_orders(marketplace, orders_data)
        
        # Update marketplace statistics
        marketplace.total_orders = MarketplaceOrder.objects.filter(
            marketplace=marketplace
        ).count()
        
        marketplace.total_revenue = MarketplaceOrder.objects.filter(
            marketplace=marketplace,
            status__in=['shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        marketplace.save(update_fields=['total_orders', 'total_revenue'])
        
        logger.info(f"Completed order sync for {marketplace.name}: {stats}")
        
        return {
            'success': True,
            'marketplace_id': marketplace_id,
            'marketplace_name': marketplace.name,
            **stats
        }
        
    except Marketplace.DoesNotExist:
        error_msg = f"Marketplace with ID {marketplace_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'marketplace_id': marketplace_id
        }
        
    except Exception as e:
        error_msg = f"Error syncing marketplace orders {marketplace_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise self.retry(exc=e, countdown=60)


def _process_marketplace_orders(marketplace: Marketplace, orders_data: List[Dict]) -> Dict[str, int]:
    """Process and save marketplace orders data."""
    stats = {
        'orders_processed': 0,
        'orders_created': 0,
        'orders_updated': 0,
        'orders_errors': 0
    }
    
    with transaction.atomic():
        for order_data in orders_data:
            try:
                stats['orders_processed'] += 1
                
                order_id = order_data.get('order_id') or order_data.get('id')
                if not order_id:
                    logger.warning(f"Order missing ID: {order_data}")
                    stats['orders_errors'] += 1
                    continue
                
                order, created = MarketplaceOrder.objects.get_or_create(
                    marketplace=marketplace,
                    marketplace_order_id=order_id,
                    defaults={
                        'customer_name': order_data.get('customer_name', ''),
                        'customer_email': order_data.get('customer_email', ''),
                        'customer_phone': order_data.get('customer_phone', ''),
                        'shipping_address': order_data.get('shipping_address', {}),
                        'billing_address': order_data.get('billing_address', {}),
                        'order_items': order_data.get('items', []),
                        'subtotal': Decimal(str(order_data.get('subtotal', 0))),
                        'shipping_cost': Decimal(str(order_data.get('shipping_cost', 0))),
                        'tax_amount': Decimal(str(order_data.get('tax_amount', 0))),
                        'total_amount': Decimal(str(order_data.get('total_amount', 0))),
                        'status': order_data.get('status', 'pending'),
                        'marketplace_status': order_data.get('marketplace_status', ''),
                        'ordered_at': order_data.get('ordered_at', timezone.now()),
                        'shipping_method': order_data.get('shipping_method', ''),
                        'marketplace_data': order_data
                    }
                )
                
                if created:
                    stats['orders_created'] += 1
                    logger.debug(f"Created new order: {order_id}")
                    
                    # Auto-acknowledge if enabled
                    if marketplace.auto_acknowledge_orders:
                        order.acknowledge_order()
                else:
                    stats['orders_updated'] += 1
                    logger.debug(f"Updated existing order: {order_id}")
                    
                    # Update order status and details
                    order.status = order_data.get('status', order.status)
                    order.marketplace_status = order_data.get('marketplace_status', order.marketplace_status)
                    order.tracking_number = order_data.get('tracking_number', order.tracking_number)
                    order.carrier = order_data.get('carrier', order.carrier)
                    order.marketplace_data = order_data
                    order.last_synced_at = timezone.now()
                    order.save()
                
            except Exception as e:
                logger.error(f"Error processing order {order_data}: {e}")
                stats['orders_errors'] += 1
                continue
    
    return stats


@shared_task(bind=True, max_retries=3)
def sync_marketplace_inventory(self, marketplace_id: int) -> Dict[str, Any]:
    """
    Synchronize inventory between internal stock and marketplace listings.
    
    Args:
        marketplace_id: ID of the marketplace to sync
        
    Returns:
        Dictionary with sync results
    """
    try:
        marketplace = Marketplace.objects.get(id=marketplace_id)
        logger.info(f"Starting inventory sync for marketplace: {marketplace.name}")
        
        if not marketplace.inventory_sync_enabled:
            logger.info(f"Inventory sync disabled for {marketplace.name}")
            return {
                'success': True,
                'message': 'Inventory sync disabled',
                'marketplace_id': marketplace_id
            }
        
        # Get all inventory items for this marketplace
        inventory_items = MarketplaceInventory.objects.filter(
            marketplace=marketplace,
            sync_status__in=['pending', 'error']
        )
        
        stats = {
            'items_processed': 0,
            'items_synced': 0,
            'items_failed': 0
        }
        
        for item in inventory_items:
            stats['items_processed'] += 1
            
            try:
                # Skip manual overrides
                if item.manual_override:
                    continue
                
                # Sync to marketplace
                if item.sync_to_marketplace():
                    stats['items_synced'] += 1
                else:
                    stats['items_failed'] += 1
                    
            except Exception as e:
                logger.error(f"Error syncing inventory item {item.id}: {e}")
                stats['items_failed'] += 1
        
        logger.info(f"Completed inventory sync for {marketplace.name}: {stats}")
        
        return {
            'success': True,
            'marketplace_id': marketplace_id,
            'marketplace_name': marketplace.name,
            **stats
        }
        
    except Marketplace.DoesNotExist:
        error_msg = f"Marketplace with ID {marketplace_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'marketplace_id': marketplace_id
        }
        
    except Exception as e:
        error_msg = f"Error syncing marketplace inventory {marketplace_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task
def sync_all_marketplace_orders() -> Dict[str, Any]:
    """Sync orders from all active marketplaces."""
    logger.info("Starting sync for all marketplace orders")
    
    marketplaces = Marketplace.objects.filter(
        status='active',
        is_auto_sync_enabled=True
    )
    
    sync_results = []
    for marketplace in marketplaces:
        try:
            result = sync_marketplace_orders.delay(marketplace.id)
            sync_results.append({
                'marketplace_id': marketplace.id,
                'marketplace_name': marketplace.name,
                'task_id': result.id
            })
        except Exception as e:
            logger.error(f"Failed to start order sync for {marketplace.name}: {e}")
    
    return {
        'success': True,
        'marketplaces_total': marketplaces.count(),
        'sync_tasks': sync_results
    }


@shared_task
def sync_all_marketplace_inventory() -> Dict[str, Any]:
    """Sync inventory for all active marketplaces."""
    logger.info("Starting inventory sync for all marketplaces")
    
    marketplaces = Marketplace.objects.filter(
        status='active',
        inventory_sync_enabled=True
    )
    
    sync_results = []
    for marketplace in marketplaces:
        try:
            result = sync_marketplace_inventory.delay(marketplace.id)
            sync_results.append({
                'marketplace_id': marketplace.id,
                'marketplace_name': marketplace.name,
                'task_id': result.id
            })
        except Exception as e:
            logger.error(f"Failed to start inventory sync for {marketplace.name}: {e}")
    
    return {
        'success': True,
        'marketplaces_total': marketplaces.count(),
        'sync_tasks': sync_results
    }


@shared_task
def update_listing_performance(marketplace_id: int, listing_id: int, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update performance metrics for a marketplace listing.
    
    Args:
        marketplace_id: ID of the marketplace
        listing_id: ID of the listing
        metrics: Performance metrics to update
        
    Returns:
        Dictionary with update results
    """
    try:
        listing = MarketplaceListing.objects.get(
            marketplace_id=marketplace_id,
            id=listing_id
        )
        
        # Update metrics
        if 'views' in metrics:
            listing.views = metrics['views']
        if 'watchers' in metrics:
            listing.watchers = metrics['watchers']
        if 'conversion_rate' in metrics:
            listing.conversion_rate = Decimal(str(metrics['conversion_rate']))
        if 'quantity_sold' in metrics:
            listing.quantity_sold = metrics['quantity_sold']
        
        listing.last_synced_at = timezone.now()
        listing.save()
        
        logger.info(f"Updated performance metrics for listing {listing.title}")
        
        return {
            'success': True,
            'listing_id': listing_id,
            'marketplace_id': marketplace_id,
            'metrics_updated': list(metrics.keys())
        }
        
    except MarketplaceListing.DoesNotExist:
        error_msg = f"Listing not found: marketplace={marketplace_id}, listing={listing_id}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = f"Error updating listing performance: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def fulfill_marketplace_order(order_id: int, tracking_number: str, carrier: str) -> Dict[str, Any]:
    """
    Mark a marketplace order as fulfilled and update tracking information.
    
    Args:
        order_id: ID of the order to fulfill
        tracking_number: Shipment tracking number
        carrier: Shipping carrier
        
    Returns:
        Dictionary with fulfillment results
    """
    try:
        order = MarketplaceOrder.objects.get(id=order_id)
        logger.info(f"Fulfilling order: {order.internal_order_number}")
        
        # Mark as shipped
        order.mark_as_shipped(tracking_number, carrier)
        
        # Notify marketplace via API
        connector = order.marketplace.get_connector()
        if connector:
            try:
                connector.update_order_status(
                    order.marketplace_order_id,
                    'shipped',
                    tracking_number=tracking_number,
                    carrier=carrier
                )
                logger.info(f"Updated order status on marketplace for {order.internal_order_number}")
            except Exception as e:
                logger.error(f"Failed to update marketplace order status: {e}")
        
        return {
            'success': True,
            'order_id': order_id,
            'internal_order_number': order.internal_order_number,
            'tracking_number': tracking_number,
            'carrier': carrier
        }
        
    except MarketplaceOrder.DoesNotExist:
        error_msg = f"Order with ID {order_id} not found"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
        
    except Exception as e:
        error_msg = f"Error fulfilling order {order_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def generate_marketplace_report(marketplace_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
    """
    Generate performance report for marketplaces.
    
    Args:
        marketplace_id: Optional specific marketplace ID
        days: Number of days to include in the report
        
    Returns:
        Dictionary with report data
    """
    logger.info("Generating marketplace performance report")
    
    try:
        if marketplace_id:
            marketplaces = Marketplace.objects.filter(id=marketplace_id)
        else:
            marketplaces = Marketplace.objects.filter(status='active')
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        report_data = []
        
        for marketplace in marketplaces:
            # Get statistics
            total_listings = marketplace.listings.filter(status='active').count()
            total_orders = marketplace.orders.filter(ordered_at__gte=cutoff_date).count()
            
            revenue_data = marketplace.orders.filter(
                ordered_at__gte=cutoff_date,
                status__in=['shipped', 'delivered']
            ).aggregate(
                total_revenue=Sum('total_amount'),
                avg_order_value=Avg('total_amount')
            )
            
            total_revenue = revenue_data['total_revenue'] or Decimal('0.00')
            avg_order_value = revenue_data['avg_order_value'] or Decimal('0.00')
            
            # Calculate conversion rate
            total_views = marketplace.listings.aggregate(
                total_views=Sum('views')
            )['total_views'] or 0
            
            conversion_rate = (total_orders / total_views * 100) if total_views > 0 else 0
            
            report_data.append({
                'marketplace_id': marketplace.id,
                'marketplace_name': marketplace.name,
                'total_listings': total_listings,
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'average_order_value': float(avg_order_value),
                'conversion_rate': round(conversion_rate, 2),
                'last_sync_at': marketplace.last_sync_at.isoformat() if marketplace.last_sync_at else None,
                'sync_status': marketplace.last_sync_status
            })
        
        logger.info(f"Generated report for {len(marketplaces)} marketplaces")
        
        return {
            'success': True,
            'marketplaces_count': len(marketplaces),
            'report_period_days': days,
            'report_data': report_data,
            'generated_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error generating marketplace report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }
"""
Celery tasks for analytics and reporting.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Avg, Sum, Count, F, Max, Min
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_reports() -> Dict[str, Any]:
    """
    Generate daily analytics reports for all systems.
    
    Returns:
        Dictionary with report generation results
    """
    logger.info("Generating daily analytics reports")
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    reports_generated = []
    
    try:
        # Generate supplier performance report
        supplier_report = generate_supplier_performance_report.delay(
            date_from=yesterday,
            date_to=today
        )
        reports_generated.append({
            'report_type': 'supplier_performance',
            'task_id': supplier_report.id
        })
        
        # Generate marketplace performance report
        marketplace_report = generate_marketplace_performance_report.delay(
            date_from=yesterday,
            date_to=today
        )
        reports_generated.append({
            'report_type': 'marketplace_performance',
            'task_id': marketplace_report.id
        })
        
        # Generate workflow execution report
        workflow_report = generate_workflow_execution_report.delay(
            date_from=yesterday,
            date_to=today
        )
        reports_generated.append({
            'report_type': 'workflow_execution',
            'task_id': workflow_report.id
        })
        
        # Generate inventory status report
        inventory_report = generate_inventory_status_report.delay()
        reports_generated.append({
            'report_type': 'inventory_status',
            'task_id': inventory_report.id
        })
        
        logger.info(f"Started generation of {len(reports_generated)} daily reports")
        
        return {
            'success': True,
            'report_date': yesterday.isoformat(),
            'reports_generated': len(reports_generated),
            'reports': reports_generated
        }
        
    except Exception as e:
        error_msg = f"Error generating daily reports: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def generate_supplier_performance_report(date_from: str, date_to: str) -> Dict[str, Any]:
    """
    Generate supplier performance analytics report.
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        
    Returns:
        Dictionary with supplier performance data
    """
    logger.info(f"Generating supplier performance report from {date_from} to {date_to}")
    
    try:
        # Import here to avoid circular imports
        from suppliers.models import Supplier, SupplierProduct
        
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
        
        suppliers_data = []
        
        for supplier in Supplier.objects.filter(status='active'):
            # Get product statistics
            total_products = supplier.products.filter(status='active').count()
            in_stock_products = supplier.products.filter(
                status='active',
                quantity_available__gt=0
            ).count()
            
            # Get products updated in the date range
            updated_products = supplier.products.filter(
                last_updated_from_supplier__gte=start_date,
                last_updated_from_supplier__lt=end_date
            ).count()
            
            # Calculate average cost and inventory value
            avg_cost = supplier.products.filter(
                status='active',
                cost_price__isnull=False
            ).aggregate(avg_cost=Avg('cost_price'))['avg_cost'] or Decimal('0.00')
            
            inventory_value = supplier.products.filter(
                status='active',
                cost_price__isnull=False
            ).aggregate(
                total_value=Sum(F('cost_price') * F('quantity_available'))
            )['total_value'] or Decimal('0.00')
            
            # Calculate stock health
            out_of_stock_products = total_products - in_stock_products
            stock_health_score = (in_stock_products / total_products * 100) if total_products > 0 else 0
            
            # Sync performance
            sync_success_rate = 100.0 if supplier.last_sync_status == 'success' else 0.0
            hours_since_sync = 0
            if supplier.last_sync_at:
                hours_since_sync = (timezone.now() - supplier.last_sync_at).total_seconds() / 3600
            
            suppliers_data.append({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'supplier_code': supplier.code,
                'total_products': total_products,
                'in_stock_products': in_stock_products,
                'out_of_stock_products': out_of_stock_products,
                'stock_health_score': round(stock_health_score, 2),
                'updated_products': updated_products,
                'average_cost_price': float(avg_cost),
                'inventory_value': float(inventory_value),
                'last_sync_at': supplier.last_sync_at.isoformat() if supplier.last_sync_at else None,
                'hours_since_sync': round(hours_since_sync, 2),
                'sync_status': supplier.last_sync_status,
                'sync_success_rate': sync_success_rate,
                'auto_sync_enabled': supplier.is_auto_sync_enabled
            })
        
        # Calculate overall statistics
        total_suppliers = len(suppliers_data)
        active_suppliers = sum(1 for s in suppliers_data if s['sync_success_rate'] > 0)
        total_products_all = sum(s['total_products'] for s in suppliers_data)
        total_in_stock = sum(s['in_stock_products'] for s in suppliers_data)
        total_inventory_value = sum(s['inventory_value'] for s in suppliers_data)
        
        overall_stats = {
            'total_suppliers': total_suppliers,
            'active_suppliers': active_suppliers,
            'inactive_suppliers': total_suppliers - active_suppliers,
            'total_products': total_products_all,
            'total_in_stock_products': total_in_stock,
            'total_out_of_stock_products': total_products_all - total_in_stock,
            'overall_stock_health': round((total_in_stock / total_products_all * 100) if total_products_all > 0 else 0, 2),
            'total_inventory_value': total_inventory_value,
            'average_inventory_per_supplier': total_inventory_value / total_suppliers if total_suppliers > 0 else 0
        }
        
        logger.info(f"Generated supplier performance report with {total_suppliers} suppliers")
        
        return {
            'success': True,
            'report_type': 'supplier_performance',
            'date_from': date_from,
            'date_to': date_to,
            'generated_at': timezone.now().isoformat(),
            'overall_statistics': overall_stats,
            'suppliers_data': suppliers_data
        }
        
    except Exception as e:
        error_msg = f"Error generating supplier performance report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'report_type': 'supplier_performance'
        }


@shared_task
def generate_marketplace_performance_report(date_from: str, date_to: str) -> Dict[str, Any]:
    """
    Generate marketplace performance analytics report.
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        
    Returns:
        Dictionary with marketplace performance data
    """
    logger.info(f"Generating marketplace performance report from {date_from} to {date_to}")
    
    try:
        # Import here to avoid circular imports
        from marketplaces.models import Marketplace, MarketplaceListing, MarketplaceOrder
        
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
        
        marketplaces_data = []
        
        for marketplace in Marketplace.objects.filter(status='active'):
            # Get listing statistics
            total_listings = marketplace.listings.filter(status='active').count()
            active_listings = marketplace.listings.filter(
                status='active',
                quantity_listed__gt=0
            ).count()
            
            # Get orders in date range
            orders_in_period = marketplace.orders.filter(
                ordered_at__gte=start_date,
                ordered_at__lt=end_date
            )
            
            total_orders = orders_in_period.count()
            
            # Revenue statistics
            revenue_stats = orders_in_period.filter(
                status__in=['shipped', 'delivered']
            ).aggregate(
                total_revenue=Sum('total_amount'),
                avg_order_value=Avg('total_amount'),
                total_fees=Sum('marketplace_fees')
            )
            
            total_revenue = revenue_stats['total_revenue'] or Decimal('0.00')
            avg_order_value = revenue_stats['avg_order_value'] or Decimal('0.00')
            total_fees = revenue_stats['total_fees'] or Decimal('0.00')
            net_revenue = total_revenue - total_fees
            
            # Order status breakdown
            order_status_counts = orders_in_period.values('status').annotate(
                count=Count('id')
            )
            
            status_breakdown = {item['status']: item['count'] for item in order_status_counts}
            
            # Performance metrics
            fulfilled_orders = orders_in_period.filter(
                status__in=['shipped', 'delivered']
            ).count()
            
            fulfillment_rate = (fulfilled_orders / total_orders * 100) if total_orders > 0 else 0
            
            # Calculate conversion rate (orders vs views)
            total_views = marketplace.listings.filter(status='active').aggregate(
                total_views=Sum('views')
            )['total_views'] or 0
            
            conversion_rate = (total_orders / total_views * 100) if total_views > 0 else 0
            
            # Sync performance
            hours_since_sync = 0
            if marketplace.last_sync_at:
                hours_since_sync = (timezone.now() - marketplace.last_sync_at).total_seconds() / 3600
            
            marketplaces_data.append({
                'marketplace_id': marketplace.id,
                'marketplace_name': marketplace.name,
                'platform_type': marketplace.platform_type,
                'total_listings': total_listings,
                'active_listings': active_listings,
                'inactive_listings': total_listings - active_listings,
                'total_orders': total_orders,
                'fulfilled_orders': fulfilled_orders,
                'fulfillment_rate': round(fulfillment_rate, 2),
                'total_revenue': float(total_revenue),
                'net_revenue': float(net_revenue),
                'total_fees': float(total_fees),
                'average_order_value': float(avg_order_value),
                'conversion_rate': round(conversion_rate, 2),
                'order_status_breakdown': status_breakdown,
                'total_views': total_views,
                'last_sync_at': marketplace.last_sync_at.isoformat() if marketplace.last_sync_at else None,
                'hours_since_sync': round(hours_since_sync, 2),
                'sync_status': marketplace.last_sync_status,
                'auto_sync_enabled': marketplace.is_auto_sync_enabled
            })
        
        # Calculate overall statistics
        total_marketplaces = len(marketplaces_data)
        total_listings_all = sum(m['total_listings'] for m in marketplaces_data)
        total_orders_all = sum(m['total_orders'] for m in marketplaces_data)
        total_revenue_all = sum(m['total_revenue'] for m in marketplaces_data)
        total_net_revenue_all = sum(m['net_revenue'] for m in marketplaces_data)
        
        overall_stats = {
            'total_marketplaces': total_marketplaces,
            'total_listings': total_listings_all,
            'total_orders': total_orders_all,
            'total_revenue': total_revenue_all,
            'total_net_revenue': total_net_revenue_all,
            'average_revenue_per_marketplace': total_revenue_all / total_marketplaces if total_marketplaces > 0 else 0,
            'average_orders_per_marketplace': total_orders_all / total_marketplaces if total_marketplaces > 0 else 0
        }
        
        logger.info(f"Generated marketplace performance report with {total_marketplaces} marketplaces")
        
        return {
            'success': True,
            'report_type': 'marketplace_performance',
            'date_from': date_from,
            'date_to': date_to,
            'generated_at': timezone.now().isoformat(),
            'overall_statistics': overall_stats,
            'marketplaces_data': marketplaces_data
        }
        
    except Exception as e:
        error_msg = f"Error generating marketplace performance report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'report_type': 'marketplace_performance'
        }


@shared_task
def generate_workflow_execution_report(date_from: str, date_to: str) -> Dict[str, Any]:
    """
    Generate workflow execution analytics report.
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        
    Returns:
        Dictionary with workflow execution data
    """
    logger.info(f"Generating workflow execution report from {date_from} to {date_to}")
    
    try:
        # Import here to avoid circular imports
        from orchestration.models import Workflow, WorkflowExecution
        
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
        
        workflows_data = []
        
        for workflow in Workflow.objects.filter(status='active'):
            # Get executions in date range
            executions_in_period = workflow.executions.filter(
                started_at__gte=start_date,
                started_at__lt=end_date
            )
            
            total_executions = executions_in_period.count()
            
            if total_executions == 0:
                continue
            
            # Execution status breakdown
            status_counts = executions_in_period.values('status').annotate(
                count=Count('id')
            )
            
            status_breakdown = {item['status']: item['count'] for item in status_counts}
            
            successful_executions = status_breakdown.get('completed', 0)
            failed_executions = status_breakdown.get('failed', 0)
            
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
            
            # Duration statistics
            completed_executions = executions_in_period.filter(
                status='completed',
                duration_seconds__isnull=False
            )
            
            duration_stats = completed_executions.aggregate(
                avg_duration=Avg('duration_seconds'),
                min_duration=Min('duration_seconds'),
                max_duration=Max('duration_seconds')
            )
            
            avg_duration = duration_stats['avg_duration'] or 0
            min_duration = duration_stats['min_duration'] or 0
            max_duration = duration_stats['max_duration'] or 0
            
            # Trigger type breakdown
            trigger_counts = executions_in_period.values('trigger_type').annotate(
                count=Count('id')
            )
            
            trigger_breakdown = {item['trigger_type']: item['count'] for item in trigger_counts}
            
            workflows_data.append({
                'workflow_id': workflow.id,
                'workflow_name': workflow.name,
                'workflow_code': workflow.code,
                'workflow_type': workflow.workflow_type,
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'failed_executions': failed_executions,
                'success_rate': round(success_rate, 2),
                'average_duration_seconds': round(avg_duration, 2),
                'min_duration_seconds': round(min_duration, 2),
                'max_duration_seconds': round(max_duration, 2),
                'status_breakdown': status_breakdown,
                'trigger_breakdown': trigger_breakdown,
                'is_scheduled': workflow.is_scheduled,
                'total_steps': workflow.steps.count()
            })
        
        # Calculate overall statistics
        total_workflows = len(workflows_data)
        total_executions_all = sum(w['total_executions'] for w in workflows_data)
        total_successful_all = sum(w['successful_executions'] for w in workflows_data)
        total_failed_all = sum(w['failed_executions'] for w in workflows_data)
        
        overall_success_rate = (total_successful_all / total_executions_all * 100) if total_executions_all > 0 else 0
        
        overall_stats = {
            'total_workflows': total_workflows,
            'total_executions': total_executions_all,
            'total_successful': total_successful_all,
            'total_failed': total_failed_all,
            'overall_success_rate': round(overall_success_rate, 2),
            'average_executions_per_workflow': total_executions_all / total_workflows if total_workflows > 0 else 0
        }
        
        logger.info(f"Generated workflow execution report with {total_workflows} workflows")
        
        return {
            'success': True,
            'report_type': 'workflow_execution',
            'date_from': date_from,
            'date_to': date_to,
            'generated_at': timezone.now().isoformat(),
            'overall_statistics': overall_stats,
            'workflows_data': workflows_data
        }
        
    except Exception as e:
        error_msg = f"Error generating workflow execution report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'report_type': 'workflow_execution'
        }


@shared_task
def generate_inventory_status_report() -> Dict[str, Any]:
    """
    Generate current inventory status report.
    
    Returns:
        Dictionary with inventory status data
    """
    logger.info("Generating inventory status report")
    
    try:
        # Import here to avoid circular imports
        from suppliers.models import SupplierProduct
        from marketplaces.models import MarketplaceInventory
        
        # Supplier inventory analysis
        supplier_inventory = []
        
        total_products = SupplierProduct.objects.filter(status='active').count()
        in_stock_products = SupplierProduct.objects.filter(
            status='active',
            quantity_available__gt=0
        ).count()
        
        low_stock_threshold = 10  # You can make this configurable
        low_stock_products = SupplierProduct.objects.filter(
            status='active',
            quantity_available__lte=low_stock_threshold,
            quantity_available__gt=0
        ).count()
        
        out_of_stock_products = total_products - in_stock_products
        
        # Calculate total inventory value
        total_inventory_value = SupplierProduct.objects.filter(
            status='active',
            cost_price__isnull=False
        ).aggregate(
            total_value=Sum(F('cost_price') * F('quantity_available'))
        )['total_value'] or Decimal('0.00')
        
        # Top categories by inventory value
        category_values = SupplierProduct.objects.filter(
            status='active',
            cost_price__isnull=False,
            category__isnull=False
        ).exclude(category='').values('category').annotate(
            total_value=Sum(F('cost_price') * F('quantity_available')),
            product_count=Count('id')
        ).order_by('-total_value')[:10]
        
        # Marketplace inventory sync status
        marketplace_sync_stats = MarketplaceInventory.objects.values('sync_status').annotate(
            count=Count('id')
        )
        
        sync_status_breakdown = {item['sync_status']: item['count'] for item in marketplace_sync_stats}
        
        # Items needing sync
        items_needing_sync = MarketplaceInventory.objects.filter(
            sync_status__in=['pending', 'error']
        ).count()
        
        # Manual overrides
        manual_overrides = MarketplaceInventory.objects.filter(
            manual_override=True
        ).count()
        
        inventory_data = {
            'supplier_inventory': {
                'total_products': total_products,
                'in_stock_products': in_stock_products,
                'out_of_stock_products': out_of_stock_products,
                'low_stock_products': low_stock_products,
                'stock_health_percentage': round((in_stock_products / total_products * 100) if total_products > 0 else 0, 2),
                'total_inventory_value': float(total_inventory_value),
                'top_categories_by_value': [
                    {
                        'category': item['category'],
                        'total_value': float(item['total_value']),
                        'product_count': item['product_count']
                    }
                    for item in category_values
                ]
            },
            'marketplace_inventory': {
                'sync_status_breakdown': sync_status_breakdown,
                'items_needing_sync': items_needing_sync,
                'manual_overrides': manual_overrides,
                'total_marketplace_items': sum(sync_status_breakdown.values())
            }
        }
        
        # Identify critical issues
        critical_issues = []
        
        if out_of_stock_products > total_products * 0.2:  # More than 20% out of stock
            critical_issues.append({
                'type': 'high_out_of_stock',
                'description': f'{out_of_stock_products} products ({round(out_of_stock_products/total_products*100, 1)}%) are out of stock',
                'severity': 'high'
            })
        
        if low_stock_products > total_products * 0.1:  # More than 10% low stock
            critical_issues.append({
                'type': 'high_low_stock',
                'description': f'{low_stock_products} products ({round(low_stock_products/total_products*100, 1)}%) have low stock',
                'severity': 'medium'
            })
        
        if items_needing_sync > 0:
            critical_issues.append({
                'type': 'sync_issues',
                'description': f'{items_needing_sync} marketplace inventory items need synchronization',
                'severity': 'medium'
            })
        
        logger.info(f"Generated inventory status report with {len(critical_issues)} critical issues")
        
        return {
            'success': True,
            'report_type': 'inventory_status',
            'generated_at': timezone.now().isoformat(),
            'inventory_data': inventory_data,
            'critical_issues': critical_issues,
            'summary': {
                'total_products': total_products,
                'stock_health_percentage': inventory_data['supplier_inventory']['stock_health_percentage'],
                'total_inventory_value': float(total_inventory_value),
                'critical_issues_count': len(critical_issues)
            }
        }
        
    except Exception as e:
        error_msg = f"Error generating inventory status report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'report_type': 'inventory_status'
        }


@shared_task
def calculate_profitability_metrics(days: int = 30) -> Dict[str, Any]:
    """
    Calculate profitability metrics across products and marketplaces.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Dictionary with profitability data
    """
    logger.info(f"Calculating profitability metrics for the last {days} days")
    
    try:
        # Import here to avoid circular imports
        from marketplaces.models import MarketplaceOrder, MarketplaceListing
        from suppliers.models import SupplierProduct
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get orders in the period
        orders_in_period = MarketplaceOrder.objects.filter(
            ordered_at__gte=cutoff_date,
            status__in=['shipped', 'delivered']
        )
        
        profitability_data = []
        
        # Calculate profitability by marketplace
        for order in orders_in_period:
            for item in order.order_items:
                try:
                    # Find corresponding listing and supplier product
                    listing = MarketplaceListing.objects.filter(
                        marketplace=order.marketplace,
                        marketplace_sku=item.get('sku')
                    ).first()
                    
                    if not listing:
                        continue
                    
                    # Calculate profit
                    selling_price = Decimal(str(item.get('price', 0)))
                    quantity = item.get('quantity', 1)
                    total_selling_price = selling_price * quantity
                    
                    # Get cost from supplier
                    cost_price = listing.cost or Decimal('0.00')
                    total_cost = cost_price * quantity
                    
                    # Calculate marketplace fees
                    marketplace_fees = order.marketplace.calculate_marketplace_fees(total_selling_price)
                    total_fees = marketplace_fees['total_fees']
                    
                    # Calculate profit
                    gross_profit = total_selling_price - total_cost
                    net_profit = gross_profit - total_fees
                    
                    profit_margin = (net_profit / total_selling_price * 100) if total_selling_price > 0 else 0
                    
                    profitability_data.append({
                        'order_id': order.id,
                        'marketplace_id': order.marketplace.id,
                        'marketplace_name': order.marketplace.name,
                        'product_sku': item.get('sku'),
                        'quantity': quantity,
                        'selling_price': float(selling_price),
                        'total_selling_price': float(total_selling_price),
                        'cost_price': float(cost_price),
                        'total_cost': float(total_cost),
                        'marketplace_fees': float(total_fees),
                        'gross_profit': float(gross_profit),
                        'net_profit': float(net_profit),
                        'profit_margin_percentage': round(profit_margin, 2),
                        'order_date': order.ordered_at.isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error calculating profitability for order item: {e}")
                    continue
        
        # Aggregate statistics
        if profitability_data:
            total_revenue = sum(item['total_selling_price'] for item in profitability_data)
            total_cost = sum(item['total_cost'] for item in profitability_data)
            total_fees = sum(item['marketplace_fees'] for item in profitability_data)
            total_gross_profit = sum(item['gross_profit'] for item in profitability_data)
            total_net_profit = sum(item['net_profit'] for item in profitability_data)
            
            avg_profit_margin = sum(item['profit_margin_percentage'] for item in profitability_data) / len(profitability_data)
            
            # Top performing products
            product_performance = {}
            for item in profitability_data:
                sku = item['product_sku']
                if sku not in product_performance:
                    product_performance[sku] = {
                        'sku': sku,
                        'total_revenue': 0,
                        'total_profit': 0,
                        'units_sold': 0,
                        'profit_margins': []
                    }
                
                product_performance[sku]['total_revenue'] += item['total_selling_price']
                product_performance[sku]['total_profit'] += item['net_profit']
                product_performance[sku]['units_sold'] += item['quantity']
                product_performance[sku]['profit_margins'].append(item['profit_margin_percentage'])
            
            # Calculate average profit margin for each product
            for sku, data in product_performance.items():
                data['avg_profit_margin'] = sum(data['profit_margins']) / len(data['profit_margins'])
                del data['profit_margins']  # Remove the raw list
            
            # Sort by total profit
            top_products = sorted(
                product_performance.values(),
                key=lambda x: x['total_profit'],
                reverse=True
            )[:10]
            
            summary_stats = {
                'analysis_period_days': days,
                'total_orders_analyzed': len(set(item['order_id'] for item in profitability_data)),
                'total_items_analyzed': len(profitability_data),
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_marketplace_fees': total_fees,
                'total_gross_profit': total_gross_profit,
                'total_net_profit': total_net_profit,
                'average_profit_margin': round(avg_profit_margin, 2),
                'overall_profit_margin': round((total_net_profit / total_revenue * 100) if total_revenue > 0 else 0, 2)
            }
        else:
            summary_stats = {
                'analysis_period_days': days,
                'total_orders_analyzed': 0,
                'total_items_analyzed': 0,
                'message': 'No profitable orders found in the specified period'
            }
            top_products = []
        
        logger.info(f"Calculated profitability for {len(profitability_data)} order items")
        
        return {
            'success': True,
            'analysis_period_days': days,
            'generated_at': timezone.now().isoformat(),
            'summary_statistics': summary_stats,
            'top_performing_products': top_products,
            'detailed_data': profitability_data[:100]  # Limit to first 100 items for response size
        }
        
    except Exception as e:
        error_msg = f"Error calculating profitability metrics: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def send_analytics_email_report(report_type: str, recipients: List[str], 
                               report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send analytics report via email.
    
    Args:
        report_type: Type of report being sent
        recipients: List of email addresses
        report_data: Report data to include
        
    Returns:
        Dictionary with email sending results
    """
    logger.info(f"Sending {report_type} email report to {len(recipients)} recipients")
    
    try:
        # Format the report for email
        subject = f"Daily {report_type.replace('_', ' ').title()} Report - {timezone.now().strftime('%Y-%m-%d')}"
        
        # Create email content
        email_content = _format_report_for_email(report_type, report_data)
        
        # Send email
        send_mail(
            subject=subject,
            message=email_content['text'],
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=email_content.get('html'),
            fail_silently=False
        )
        
        logger.info(f"Successfully sent {report_type} email report")
        
        return {
            'success': True,
            'report_type': report_type,
            'recipients_count': len(recipients),
            'email_sent_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error sending analytics email report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg,
            'report_type': report_type
        }


def _format_report_for_email(report_type: str, report_data: Dict[str, Any]) -> Dict[str, str]:
    """Format report data for email content."""
    
    if report_type == 'supplier_performance':
        return _format_supplier_report_email(report_data)
    elif report_type == 'marketplace_performance':
        return _format_marketplace_report_email(report_data)
    elif report_type == 'workflow_execution':
        return _format_workflow_report_email(report_data)
    elif report_type == 'inventory_status':
        return _format_inventory_report_email(report_data)
    else:
        return {
            'text': f"Report data for {report_type}:\n{json.dumps(report_data, indent=2)}",
            'html': f"<h1>{report_type.title()} Report</h1><pre>{json.dumps(report_data, indent=2)}</pre>"
        }


def _format_supplier_report_email(report_data: Dict[str, Any]) -> Dict[str, str]:
    """Format supplier performance report for email."""
    
    stats = report_data.get('overall_statistics', {})
    
    text_content = f"""
Supplier Performance Report
Generated: {report_data.get('generated_at', 'N/A')}

Overall Statistics:
- Total Suppliers: {stats.get('total_suppliers', 0)}
- Active Suppliers: {stats.get('active_suppliers', 0)}
- Total Products: {stats.get('total_products', 0)}
- In Stock Products: {stats.get('total_in_stock_products', 0)}
- Stock Health: {stats.get('overall_stock_health', 0)}%
- Total Inventory Value: ${stats.get('total_inventory_value', 0):,.2f}

Top Performing Suppliers:
"""
    
    suppliers_data = report_data.get('suppliers_data', [])[:5]  # Top 5
    for supplier in suppliers_data:
        text_content += f"- {supplier['supplier_name']}: {supplier['stock_health_score']}% stock health, ${supplier['inventory_value']:,.2f} value\n"
    
    return {
        'text': text_content,
        'html': text_content.replace('\n', '<br>')
    }


def _format_marketplace_report_email(report_data: Dict[str, Any]) -> Dict[str, str]:
    """Format marketplace performance report for email."""
    
    stats = report_data.get('overall_statistics', {})
    
    text_content = f"""
Marketplace Performance Report
Generated: {report_data.get('generated_at', 'N/A')}

Overall Statistics:
- Total Marketplaces: {stats.get('total_marketplaces', 0)}
- Total Listings: {stats.get('total_listings', 0)}
- Total Orders: {stats.get('total_orders', 0)}
- Total Revenue: ${stats.get('total_revenue', 0):,.2f}
- Net Revenue: ${stats.get('total_net_revenue', 0):,.2f}

Top Performing Marketplaces:
"""
    
    marketplaces_data = report_data.get('marketplaces_data', [])[:5]  # Top 5
    for marketplace in marketplaces_data:
        text_content += f"- {marketplace['marketplace_name']}: {marketplace['total_orders']} orders, ${marketplace['total_revenue']:,.2f} revenue\n"
    
    return {
        'text': text_content,
        'html': text_content.replace('\n', '<br>')
    }


def _format_workflow_report_email(report_data: Dict[str, Any]) -> Dict[str, str]:
    """Format workflow execution report for email."""
    
    stats = report_data.get('overall_statistics', {})
    
    text_content = f"""
Workflow Execution Report
Generated: {report_data.get('generated_at', 'N/A')}

Overall Statistics:
- Total Workflows: {stats.get('total_workflows', 0)}
- Total Executions: {stats.get('total_executions', 0)}
- Successful Executions: {stats.get('total_successful', 0)}
- Failed Executions: {stats.get('total_failed', 0)}
- Success Rate: {stats.get('overall_success_rate', 0)}%

Workflow Performance:
"""
    
    workflows_data = report_data.get('workflows_data', [])[:5]  # Top 5
    for workflow in workflows_data:
        text_content += f"- {workflow['workflow_name']}: {workflow['success_rate']}% success rate, {workflow['total_executions']} executions\n"
    
    return {
        'text': text_content,
        'html': text_content.replace('\n', '<br>')
    }


def _format_inventory_report_email(report_data: Dict[str, Any]) -> Dict[str, str]:
    """Format inventory status report for email."""
    
    summary = report_data.get('summary', {})
    critical_issues = report_data.get('critical_issues', [])
    
    text_content = f"""
Inventory Status Report
Generated: {report_data.get('generated_at', 'N/A')}

Summary:
- Total Products: {summary.get('total_products', 0)}
- Stock Health: {summary.get('stock_health_percentage', 0)}%
- Total Inventory Value: ${summary.get('total_inventory_value', 0):,.2f}
- Critical Issues: {summary.get('critical_issues_count', 0)}

Critical Issues:
"""
    
    for issue in critical_issues:
        text_content += f"- {issue['description']} (Severity: {issue['severity']})\n"
    
    if not critical_issues:
        text_content += "No critical issues found.\n"
    
    return {
        'text': text_content,
        'html': text_content.replace('\n', '<br>')
    }
"""
Views for marketplace management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum

from .models import (
    Marketplace, MarketplaceListing, MarketplaceOrder, MarketplaceInventory
)
from .serializers import (
    MarketplaceSerializer, MarketplaceListingSerializer,
    MarketplaceOrderSerializer, MarketplaceInventorySerializer
)


class MarketplaceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing marketplaces."""
    
    queryset = Marketplace.objects.all()
    serializer_class = MarketplaceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'platform_type', 'currency', 'country_code']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at', 'last_sync_at']
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test marketplace connection."""
        marketplace = self.get_object()
        
        try:
            connector = marketplace.get_connector()
            success, error = connector.test_connection()
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Connection successful'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': error or 'Connection failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Trigger sync for a marketplace."""
        marketplace = self.get_object()
        sync_type = request.data.get('type', 'all')  # all, orders, listings, inventory
        
        try:
            connector = marketplace.get_connector()
            results = {
                'status': 'success',
                'synced': {}
            }
            
            if sync_type in ['all', 'orders']:
                orders = connector.fetch_orders()
                results['synced']['orders'] = len(orders)
            
            if sync_type in ['all', 'listings']:
                listings = connector.search_listings()
                results['synced']['listings'] = len(listings)
            
            if sync_type in ['all', 'inventory']:
                # Sync inventory items
                inventory_count = 0
                for item in marketplace.inventory_items.all():
                    if item.sync_to_marketplace():
                        inventory_count += 1
                results['synced']['inventory'] = inventory_count
            
            marketplace.update_sync_status(True)
            return Response(results)
            
        except Exception as e:
            marketplace.update_sync_status(False, str(e))
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get marketplace statistics."""
        marketplace = self.get_object()
        
        stats = {
            'listings': {
                'total': marketplace.listings.count(),
                'active': marketplace.listings.filter(status='active').count(),
                'pending': marketplace.listings.filter(status='pending').count(),
                'error': marketplace.listings.filter(status='error').count(),
            },
            'orders': {
                'total': marketplace.orders.count(),
                'pending': marketplace.orders.filter(status='pending').count(),
                'processing': marketplace.orders.filter(status='processing').count(),
                'shipped': marketplace.orders.filter(status='shipped').count(),
                'revenue': marketplace.orders.aggregate(
                    total=Sum('total_amount')
                )['total'] or 0,
            },
            'inventory': {
                'total_skus': marketplace.inventory_items.count(),
                'synced': marketplace.inventory_items.filter(sync_status='synced').count(),
                'pending': marketplace.inventory_items.filter(sync_status='pending').count(),
                'error': marketplace.inventory_items.filter(sync_status='error').count(),
            }
        }
        
        return Response(stats)


class MarketplaceListingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing marketplace listings."""
    
    queryset = MarketplaceListing.objects.select_related('marketplace')
    serializer_class = MarketplaceListingSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['marketplace', 'status', 'listing_type']
    search_fields = ['title', 'marketplace_sku', 'description']
    ordering_fields = ['created_at', 'price', 'quantity_listed']
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync a specific listing with marketplace."""
        listing = self.get_object()
        
        try:
            connector = listing.marketplace.get_connector()
            data = connector.get_listing(listing.marketplace_listing_id)
            
            if data:
                listing.update_from_marketplace(data)
                listing.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Listing synced successfully'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Listing not found on marketplace'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """Update listing price on marketplace."""
        listing = self.get_object()
        new_price = request.data.get('price')
        sale_price = request.data.get('sale_price')
        
        if not new_price:
            return Response({
                'status': 'error',
                'message': 'Price is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            connector = listing.marketplace.get_connector()
            success = connector.update_price(
                listing.marketplace_sku,
                new_price,
                sale_price
            )
            
            if success:
                listing.price = new_price
                if sale_price is not None:
                    listing.sale_price = sale_price
                listing.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Price updated successfully'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to update price on marketplace'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarketplaceOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing marketplace orders."""
    
    queryset = MarketplaceOrder.objects.select_related('marketplace')
    serializer_class = MarketplaceOrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['marketplace', 'status', 'customer_email']
    search_fields = ['internal_order_number', 'marketplace_order_id', 'customer_name', 'customer_email']
    ordering_fields = ['ordered_at', 'total_amount', 'status']
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an order."""
        order = self.get_object()
        
        if order.status != 'pending':
            return Response({
                'status': 'error',
                'message': 'Order is not in pending status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            connector = order.marketplace.get_connector()
            success = connector.acknowledge_order(order.marketplace_order_id)
            
            if success:
                order.acknowledge_order()
                return Response({
                    'status': 'success',
                    'message': 'Order acknowledged successfully'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to acknowledge order on marketplace'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        """Mark order as shipped."""
        order = self.get_object()
        tracking_number = request.data.get('tracking_number')
        carrier = request.data.get('carrier')
        
        if not tracking_number or not carrier:
            return Response({
                'status': 'error',
                'message': 'Tracking number and carrier are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            connector = order.marketplace.get_connector()
            success = connector.ship_order(
                order.marketplace_order_id,
                tracking_number,
                carrier
            )
            
            if success:
                order.mark_as_shipped(tracking_number, carrier)
                return Response({
                    'status': 'success',
                    'message': 'Order marked as shipped'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to update shipment on marketplace'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarketplaceInventoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing marketplace inventory."""
    
    queryset = MarketplaceInventory.objects.select_related('marketplace', 'listing')
    serializer_class = MarketplaceInventorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['marketplace', 'sync_status', 'manual_override']
    search_fields = ['internal_sku', 'marketplace_sku']
    ordering_fields = ['last_sync_at', 'available_quantity']
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync inventory item to marketplace."""
        inventory = self.get_object()
        
        try:
            success = inventory.sync_to_marketplace()
            
            if success:
                return Response({
                    'status': 'success',
                    'message': 'Inventory synced successfully',
                    'quantity': inventory.marketplace_quantity
                })
            else:
                return Response({
                    'status': 'error',
                    'message': inventory.last_sync_error or 'Sync failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_sync(self, request):
        """Bulk sync inventory items."""
        marketplace_id = request.data.get('marketplace_id')
        sku_list = request.data.get('skus', [])
        
        if not marketplace_id:
            return Response({
                'status': 'error',
                'message': 'marketplace_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset().filter(marketplace_id=marketplace_id)
        
        if sku_list:
            queryset = queryset.filter(internal_sku__in=sku_list)
        
        success_count = 0
        error_count = 0
        
        for item in queryset:
            if item.sync_to_marketplace():
                success_count += 1
            else:
                error_count += 1
        
        return Response({
            'status': 'success',
            'synced': success_count,
            'errors': error_count
        })

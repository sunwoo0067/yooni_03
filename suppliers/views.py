"""
Views for Supplier API endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Supplier, SupplierProduct
from .serializers import (
    SupplierSerializer, 
    SupplierProductSerializer,
    SupplierCredentialsSerializer,
    SupplierSyncSerializer
)


class SupplierViewSet(viewsets.ModelViewSet):
    """ViewSet for managing suppliers."""
    
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'code'
    
    def get_queryset(self):
        """Filter suppliers based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by connector type
        connector_type = self.request.query_params.get('connector_type')
        if connector_type:
            queryset = queryset.filter(connector_type=connector_type)
        
        # Filter by auto sync enabled
        auto_sync = self.request.query_params.get('auto_sync')
        if auto_sync is not None:
            queryset = queryset.filter(is_auto_sync_enabled=auto_sync.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def set_credentials(self, request, code=None):
        """Set encrypted credentials for a supplier."""
        supplier = self.get_object()
        serializer = SupplierCredentialsSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                supplier.set_credentials(serializer.validated_data['credentials'])
                supplier.save()
                return Response(
                    {'message': 'Credentials updated successfully'},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, code=None):
        """Test connection to a supplier."""
        supplier = self.get_object()
        
        try:
            connector = supplier.get_connector()
            
            # Validate credentials
            is_valid, cred_error = connector.validate_credentials()
            if not is_valid:
                return Response(
                    {
                        'success': False,
                        'error': f'Invalid credentials: {cred_error}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Test connection
            is_connected, conn_error = connector.test_connection()
            if not is_connected:
                return Response(
                    {
                        'success': False,
                        'error': f'Connection failed: {conn_error}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                {
                    'success': True,
                    'message': 'Connection successful',
                    'rate_limit': connector.get_rate_limit_info()
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Unexpected error: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def sync(self, request, code=None):
        """Trigger synchronization for a supplier."""
        supplier = self.get_object()
        serializer = SupplierSyncSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        sync_options = serializer.validated_data
        
        # Check if sync is due or forced
        if not sync_options['force'] and not supplier.is_sync_due:
            return Response(
                {
                    'message': 'Sync not due yet',
                    'next_sync_in_hours': supplier.sync_frequency_hours
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In a real implementation, this would trigger a background task
        # For now, return a placeholder response
        return Response(
            {
                'message': 'Sync triggered',
                'task_id': 'placeholder-task-id',
                'options': sync_options
            },
            status=status.HTTP_202_ACCEPTED
        )
    
    @action(detail=True, methods=['get'])
    def products(self, request, code=None):
        """Get products for a specific supplier."""
        supplier = self.get_object()
        products = supplier.products.all()
        
        # Apply filters
        status_param = request.query_params.get('status')
        if status_param:
            products = products.filter(status=status_param)
        
        category = request.query_params.get('category')
        if category:
            products = products.filter(category__icontains=category)
        
        brand = request.query_params.get('brand')
        if brand:
            products = products.filter(brand__icontains=brand)
        
        # Paginate
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = SupplierProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SupplierProductSerializer(products, many=True)
        return Response(serializer.data)


class SupplierProductViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing supplier products."""
    
    queryset = SupplierProduct.objects.select_related('supplier')
    serializer_class = SupplierProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter products based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by supplier
        supplier_code = self.request.query_params.get('supplier')
        if supplier_code:
            queryset = queryset.filter(supplier__code=supplier_code)
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Filter by brand
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        
        # Filter by in stock
        in_stock = self.request.query_params.get('in_stock')
        if in_stock is not None:
            if in_stock.lower() == 'true':
                queryset = queryset.filter(quantity_available__gt=0, status='active')
            else:
                queryset = queryset.filter(quantity_available=0) | queryset.exclude(status='active')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                supplier_name__icontains=search
            ) | queryset.filter(
                supplier_sku__icontains=search
            ) | queryset.filter(
                description__icontains=search
            )
        
        return queryset

"""
URL configuration for suppliers app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SupplierViewSet, SupplierProductViewSet

app_name = 'suppliers'

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'supplier-products', SupplierProductViewSet, basename='supplier-product')

urlpatterns = [
    path('api/', include(router.urls)),
]
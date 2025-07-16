"""
URL configuration for marketplaces app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'marketplaces'

router = DefaultRouter()
router.register(r'marketplaces', views.MarketplaceViewSet)
router.register(r'listings', views.MarketplaceListingViewSet)
router.register(r'orders', views.MarketplaceOrderViewSet)
router.register(r'inventory', views.MarketplaceInventoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
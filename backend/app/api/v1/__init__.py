"""
API v1 router.
"""
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include endpoint routers - Core endpoints first
from .endpoints import health
# Temporarily disable other endpoints due to import issues
# from .endpoints import platform_accounts, products, orders
# Temporarily disable problematic endpoints
# from .endpoints import product_collector, wholesaler_sync, monitoring, product_alerts, operations_dashboard
# from .endpoints import orders_optimized, performance_dashboard, inventory_sync
# Complex endpoints temporarily disabled due to dependency issues
# from .endpoints import sync, dashboard, wholesaler, dropshipping, marketing, performance, analytics, sourcing, product_processing, pipeline, benchmark
# AI endpoint temporarily disabled due to dependency issues
# from .endpoints import ai
# from .endpoints import auth, users, inventory, marketplace
# Advanced features temporarily disabled
# from . import websocket, ai_insights, monitoring

# Include routers - Core endpoints only
api_router.include_router(health.router, prefix="/health", tags=["Health"])
# Temporarily disable other endpoints due to import issues
# api_router.include_router(platform_accounts.router, prefix="/platform-accounts", tags=["Platform Accounts"])
# api_router.include_router(products.router, prefix="/products", tags=["Products"])
# api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
# Temporarily disable problematic endpoints
# api_router.include_router(product_collector.router, prefix="/product-collector", tags=["Product Collector"])
# api_router.include_router(wholesaler_sync.router, prefix="/wholesaler-sync", tags=["Wholesaler Sync"])
# api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
# api_router.include_router(product_alerts.router, prefix="/product-alerts", tags=["Product Alerts"])
# api_router.include_router(operations_dashboard.router, prefix="/dashboard", tags=["Operations Dashboard"])
# api_router.include_router(inventory_sync.router, prefix="/inventory-sync", tags=["Inventory Sync"])
# api_router.include_router(orders_optimized.router, prefix="/orders-optimized", tags=["Orders Optimized"])
# api_router.include_router(performance_dashboard.router, prefix="/performance", tags=["Performance Dashboard"])

# Complex endpoints temporarily disabled due to dependency issues
# api_router.include_router(ai.router, prefix="/ai", tags=["AI Services"])
# api_router.include_router(sync.router, prefix="/sync", tags=["Synchronization"])
# api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
# api_router.include_router(wholesaler.router, prefix="/wholesalers", tags=["Wholesaler"])
# api_router.include_router(dropshipping.router, prefix="/dropshipping", tags=["Dropshipping"])
# api_router.include_router(marketing.router, prefix="/marketing", tags=["Marketing"])
# api_router.include_router(performance.router, prefix="/performance", tags=["Performance"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
# api_router.include_router(sourcing.router, prefix="/sourcing", tags=["Sourcing"])
# api_router.include_router(product_processing.router, prefix="/product-processing", tags=["Product Processing"])
# api_router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline Management"])
# api_router.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])
# api_router.include_router(wholesaler_sync.router, prefix="/wholesaler-sync", tags=["Wholesaler Sync"])
# Advanced features temporarily disabled
# api_router.include_router(websocket.router, tags=["WebSocket"])
# api_router.include_router(ai_insights.router, prefix="/ai-insights", tags=["AI Insights"])
# api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
# api_router.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])

# Placeholder health endpoint
@api_router.get("/status")
async def api_status():
    """API status endpoint."""
    return {"status": "API v1 is running", "version": "1.0.0"}

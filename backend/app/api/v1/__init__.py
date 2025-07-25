"""
API v1 router.
"""
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include endpoint routers
from .endpoints import platform_accounts, products, ai, sync, dashboard, wholesaler, dropshipping, marketing, performance, orders, analytics, health, sourcing, product_processing, pipeline, benchmark
# from .endpoints import auth, users, inventory, marketplace

# Include routers when endpoints are implemented
api_router.include_router(platform_accounts.router, prefix="/platform-accounts", tags=["Platform Accounts"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Services"])
api_router.include_router(sync.router, prefix="/sync", tags=["Synchronization"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(wholesaler.router, prefix="/wholesalers", tags=["Wholesaler"])
api_router.include_router(dropshipping.router, prefix="/dropshipping", tags=["Dropshipping"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["Marketing"])
api_router.include_router(performance.router, prefix="/performance", tags=["Performance"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(sourcing.router, prefix="/sourcing", tags=["Sourcing"])
api_router.include_router(product_processing.router, prefix="/product-processing", tags=["Product Processing"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline Management"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
# api_router.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])

# Placeholder health endpoint
@api_router.get("/status")
async def api_status():
    """API status endpoint."""
    return {"status": "API v1 is running", "version": "1.0.0"}

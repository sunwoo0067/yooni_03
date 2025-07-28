"""
Simple test server to verify FastAPI is working
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime

# Create FastAPI app
app = FastAPI(
    title="Test Backend Server",
    version="1.0.0",
    description="Simple test server to verify setup"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "test-backend"
    }

# API status endpoint
@app.get("/api/v1/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "status": "/api/v1/status",
            "root": "/"
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Test Backend Server is running",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    print("Starting test server on http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
import logging
import time
from contextlib import asynccontextmanager

from .routes import api_router
from .middleware import LoggingMiddleware, RateLimitMiddleware
from .exceptions import ChatDevException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("chatdev-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Setup and teardown logic for the application
    """
    # Startup logic
    logger.info("Starting ChatDev API")
    yield
    # Shutdown logic
    logger.info("Shutting down ChatDev API")

# Initialize FastAPI app
app = FastAPI(
    title="ChatDev API",
    description="API for ChatDev software generation using LLM-powered agents",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # We'll define custom docs URL below
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Exception handler for ChatDevException
@app.exception_handler(ChatDevException)
async def chatdev_exception_handler(request: Request, exc: ChatDevException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "type": exc.error_type},
    )

# Custom documentation route
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="ChatDev API Documentation",
        swagger_favicon_url="",
    )

# Basic health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
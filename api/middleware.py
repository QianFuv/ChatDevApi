import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status
from fastapi.responses import JSONResponse
import json
from collections import defaultdict

# Configure logging
logger = logging.getLogger("chatdev-api.middleware")

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all requests and responses
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Generate a unique identifier for this request
        request_id = str(int(start_time * 1000))
        
        # Log the request
        logger.info(f"Request #{request_id} started: {request.method} {request.url.path}")
        
        # Process the request and get the response
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log the response
            logger.info(
                f"Request #{request_id} completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.3f}s"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request #{request_id} failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} - Time: {process_time:.3f}s"
            )
            
            # Return an error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error", "type": "server_error"}
            )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware
    
    Limits the number of requests that can be made in a time period.
    """
    
    def __init__(self, app, requests_limit=100, window_size=60):
        """
        Initialize the rate limiter
        
        Args:
            app: The FastAPI application
            requests_limit: Maximum number of requests allowed in the window
            window_size: Size of the time window in seconds
        """
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_size = window_size
        self.requests = defaultdict(list)  # IP -> [timestamp1, timestamp2, ...]
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Remove timestamps outside the current window
        self.requests[client_ip] = [
            timestamp for timestamp in self.requests[client_ip]
            if current_time - timestamp < self.window_size
        ]
        
        # Check if the request limit has been reached
        if len(self.requests[client_ip]) >= self.requests_limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too many requests. Please try again later.",
                    "type": "rate_limit_exceeded"
                }
            )
        
        # Add current timestamp to the list
        self.requests[client_ip].append(current_time)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_limit - len(self.requests[client_ip])
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.window_size)
        )
        
        return response
from fastapi import Depends, Header, Request
from typing import Optional
import logging
import re
import openai
import os

from .exceptions import AuthenticationError, ValidationError

# Configure logging
logger = logging.getLogger("chatdev-api.dependencies")

async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Header(None, description="OpenAI API key")
) -> str:
    """
    Dependency to verify OpenAI API key
    
    This checks if a valid API key is provided in the request.
    For simple cases, it just validates the format.
    For more advanced cases, it can attempt to verify with OpenAI.
    
    Args:
        request: The FastAPI request object
        api_key: The API key from the header
        
    Returns:
        str: The validated API key
        
    Raises:
        AuthenticationError: If no API key is provided or it's invalid
    """
    # First check header
    if api_key:
        return validate_api_key(api_key)
    
    # If not in header, try to get from request body
    try:
        body = await request.json()
        if "api_key" in body:
            return validate_api_key(body["api_key"])
    except:
        pass
    
    # No API key found
    logger.warning("API key not provided in request")
    raise AuthenticationError("API key is required")

def validate_api_key(api_key: str) -> str:
    """
    Validate an OpenAI API key
    
    Args:
        api_key: The API key to validate
        
    Returns:
        str: The validated API key
        
    Raises:
        ValidationError: If the API key format is invalid
    """
    # Basic format validation for OpenAI API key
    if not api_key:
        raise ValidationError("API key cannot be empty")
    
    # Check if it's a valid format (starts with 'sk-' and is sufficiently long)
    if not re.match(r'^sk-(?:or-v1-)?[A-Za-z0-9]{32,}$', api_key):
        raise ValidationError("Invalid API key format")
    
    # For enhanced security, optionally verify with OpenAI API
    # This is commented out to avoid unnecessary API calls
    # Uncomment to enable actual validation with OpenAI
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        client.models.list()  # Make a simple API call to check if the key works
    except Exception as e:
        logger.warning(f"API key validation failed: {str(e)}")
        raise AuthenticationError("Invalid API key: verification failed")
    """
    
    return api_key

async def get_request_body(request: Request) -> dict:
    """
    Dependency to get request body as a dictionary
    
    Args:
        request: The FastAPI request
        
    Returns:
        dict: The request body as a dictionary
    """
    try:
        return await request.json()
    except Exception as e:
        logger.warning(f"Failed to parse request body: {str(e)}")
        raise ValidationError("Invalid request body: JSON parsing failed")
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger("chatdev-api.config")

# Get the root directory (where run.py is located)
ROOT_DIR = Path(__file__).parent.parent
WAREHOUSE_DIR = ROOT_DIR / "WareHouse"

# Environment variables for configuration
API_DEBUG = os.getenv("API_DEBUG", "False").lower() in ("true", "1", "t")
API_LOG_LEVEL = os.getenv("API_LOG_LEVEL", "INFO")
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))
API_RATE_WINDOW = int(os.getenv("API_RATE_WINDOW", "60"))

# Model validation settings
VALID_MODELS = [
    "GPT_3_5_TURBO", "GPT_4", "GPT_4_TURBO", 
    "GPT_4O", "GPT_4O_MINI", "CLAUDE_3_5_SONNET", "DEEPSEEK_R1"
]

def get_venv_python() -> str:
    """
    Get the Python interpreter path from Poetry's virtual environment or system Python
    
    Returns:
        str: Path to the Python interpreter
    """
    try:
        # Try to get Poetry's virtual environment
        import subprocess
        result = subprocess.run(['poetry', 'env', 'info', '--path'], 
                              capture_output=True, 
                              text=True)
        if result.returncode == 0:
            venv_path = result.stdout.strip()
            if sys.platform == "win32":
                python_path = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                python_path = os.path.join(venv_path, "bin", "python")
            
            if os.path.exists(python_path):
                logger.debug(f"Using Poetry virtual environment Python: {python_path}")
                return python_path
    except Exception as e:
        logger.warning(f"Error detecting Poetry venv: {e}")
    
    # Fallback to system Python if Poetry env not found
    logger.debug(f"Using system Python: {sys.executable}")
    return sys.executable

def get_app_settings() -> Dict[str, Any]:
    """
    Get the application settings
    
    Returns:
        Dict[str, Any]: Application settings
    """
    return {
        "debug": API_DEBUG,
        "log_level": API_LOG_LEVEL,
        "root_dir": str(ROOT_DIR),
        "warehouse_dir": str(WAREHOUSE_DIR),
        "rate_limit": API_RATE_LIMIT,
        "rate_window": API_RATE_WINDOW,
        "valid_models": VALID_MODELS,
    }

def get_company_configs() -> Dict[str, str]:
    """
    Get the available company configurations
    
    Returns:
        Dict[str, str]: Dictionary of company configurations (name -> path)
    """
    config_dir = ROOT_DIR / "CompanyConfig"
    configs = {}
    
    if config_dir.exists() and config_dir.is_dir():
        for item in config_dir.iterdir():
            if item.is_dir():
                configs[item.name] = str(item)
    
    return configs

def validate_path(path: str) -> Optional[str]:
    """
    Validate a path for security purposes
    
    Args:
        path: The path to validate
        
    Returns:
        Optional[str]: The absolute path if valid, None otherwise
    """
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Check if path exists
        if not os.path.exists(abs_path):
            logger.warning(f"Path does not exist: {path}")
            return None
            
        # Make sure path is not outside ROOT_DIR
        if not abs_path.startswith(str(ROOT_DIR)):
            logger.warning(f"Path outside of ROOT_DIR: {path}")
            return None
            
        return abs_path
    except Exception as e:
        logger.warning(f"Error validating path {path}: {str(e)}")
        return None
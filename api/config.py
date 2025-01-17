import os
import sys
from pathlib import Path

# Get the root directory (where run.py is located)
ROOT_DIR = Path(__file__).parent.parent
WAREHOUSE_DIR = ROOT_DIR / "WareHouse"

def get_venv_python():
    """Get the Python interpreter path from Poetry's virtual environment"""
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
                return python_path
    except Exception as e:
        print(f"Error detecting Poetry venv: {e}")
    
    # Fallback to system Python if Poetry env not found
    return sys.executable
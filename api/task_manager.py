import asyncio
import os
import sys
import signal
import logging
import psutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from .database import SessionLocal, Task
from .config import get_venv_python, ROOT_DIR

# Configure logging
logger = logging.getLogger("chatdev-api.task_manager")

async def run_chatdev_task(task_id: int, request_data: Dict[str, Any]):
    """
    Run a ChatDev generation task in the background
    
    Args:
        task_id: The ID of the task in the database
        request_data: The request data containing ChatDev configuration
    """
    db = SessionLocal()
    process = None
    
    try:
        # Get task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return
        
        # Update task status to RUNNING
        task.status = "RUNNING"
        db.commit()
        
        # Prepare environment and command
        env = os.environ.copy()  # Copy current environment
        
        # Set essential environment variables
        env["OPENAI_API_KEY"] = request_data["api_key"]
        if request_data.get("base_url"):
            env["BASE_URL"] = request_data["base_url"]
            
        # Force UTF-8 encoding for Python
        env["PYTHONIOENCODING"] = "utf-8"
        if sys.platform == "win32":
            env["PYTHONUTF8"] = "1"  # Force UTF-8 on Windows
            os.system("chcp 65001")  # Set console to UTF-8 mode
        
        python_path = get_venv_python()
        run_script = str(ROOT_DIR / "run.py")
        
        # Build command
        command = (
            f'"{python_path}" "{run_script}" '
            f'--task "{request_data["task"]}" '
            f'--name "{request_data["name"]}" '
            f'--config "{request_data["config"]}" '
            f'--org "{request_data["org"]}" '
            f'--model "{request_data["model"]}"'
        )
        
        if request_data.get("path"):
            command += f' --path "{request_data["path"]}"'
            
        logger.info(f"Starting ChatDev process with command: {command}")
        
        # Execute ChatDev process
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(ROOT_DIR),
            shell=True  # Use shell for better Windows compatibility
        )
        
        # Store process ID in database for potential cancellation
        task.pid = process.pid
        db.commit()
        
        # Wait for process completion
        stdout, stderr = await process.communicate()
        
        # Decode output with UTF-8
        stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ''
        stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ''
        
        # Log output for debugging
        if stdout_str:
            logger.debug(f"Process stdout: {stdout_str[:1000]}...")
        if stderr_str:
            logger.error(f"Process stderr: {stderr_str}")
        
        # Update task status based on result
        if process.returncode == 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_path = f"WareHouse/{request_data['name']}_{request_data['org']}_{timestamp}"
            task.status = "COMPLETED"
            task.result_path = result_path
            logger.info(f"Task {task_id} completed successfully. Result at {result_path}")
        else:
            task.status = "FAILED"
            task.error_message = stderr_str or stdout_str  # Use stdout if stderr is empty
            logger.error(f"Task {task_id} failed with exit code {process.returncode}")
        
        db.commit()

    except Exception as e:
        logger.exception(f"Exception in task {task_id}: {str(e)}")
        task.status = "FAILED"
        task.error_message = str(e)
        db.commit()
    finally:
        db.close()

async def cancel_chatdev_task(task_id: int) -> bool:
    """
    Cancel a running ChatDev task
    
    Args:
        task_id: The ID of the task to cancel
        
    Returns:
        bool: True if cancellation was successful, False otherwise
    """
    db = SessionLocal()
    try:
        # Get task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.pid:
            logger.warning(f"Cannot cancel task {task_id}: Task not found or no PID")
            return False
        
        # Try to terminate the process and its children
        try:
            # Get the process
            process = psutil.Process(task.pid)
            
            # Terminate children first
            children = process.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except:
                    pass
            
            # Terminate the main process
            process.terminate()
            
            # Wait for processes to terminate
            _, alive = psutil.wait_procs(children + [process], timeout=3)
            
            # Kill any remaining processes
            for p in alive:
                try:
                    p.kill()
                except:
                    pass
                    
            logger.info(f"Successfully terminated task {task_id} (PID: {task.pid})")
            return True
            
        except psutil.NoSuchProcess:
            logger.warning(f"Process for task {task_id} (PID: {task.pid}) not found")
            return False
        except Exception as e:
            logger.error(f"Failed to terminate task {task_id}: {str(e)}")
            return False
            
    except Exception as e:
        logger.exception(f"Exception in cancel_task {task_id}: {str(e)}")
        return False
    finally:
        db.close()
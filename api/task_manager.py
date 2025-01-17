import asyncio
from datetime import datetime
from .database import SessionLocal, Task
from .config import get_venv_python, ROOT_DIR
import json
import os
import sys

async def run_chatdev_task(task_id: int, request_data: dict):
    db = SessionLocal()
    try:
        # Update task status to RUNNING
        task = db.query(Task).filter(Task.id == task_id).first()
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
        
        # Execute ChatDev process
        process = await asyncio.create_subprocess_shell(
            f'"{python_path}" "{run_script}" --task "{request_data["task"]}" '
            f'--name "{request_data["name"]}" --config "{request_data["config"]}" '
            f'--org "{request_data["org"]}" --model "{request_data["model"]}"'
            + (f' --path "{request_data["path"]}"' if request_data.get("path") else ''),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(ROOT_DIR),
            shell=True  # Use shell for better Windows compatibility
        )

        stdout, stderr = await process.communicate()

        # Decode output with UTF-8
        stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ''
        stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ''

        # Update task status based on result
        if process.returncode == 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_path = f"WareHouse/{request_data['name']}_{request_data['org']}_{timestamp}"
            task.status = "COMPLETED"
            task.result_path = result_path
        else:
            task.status = "FAILED"
            task.error_message = stderr_str or stdout_str  # Use stdout if stderr is empty

        db.commit()

    except Exception as e:
        task.status = "FAILED"
        task.error_message = str(e)
        db.commit()
    finally:
        db.close()
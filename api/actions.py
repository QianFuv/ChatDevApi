"""
GitHub Actions Interface Module for ChatDev API

This module provides functionality to run GitHub Actions workflows locally
using the 'act' command line tool. It enables the API to trigger APK builds
for generated Python applications.
"""

import os
import sys
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import shutil

from .config import ROOT_DIR, validate_path, WAREHOUSE_DIR
from .exceptions import InternalServerError, ResourceNotFoundError

# Configure logging
logger = logging.getLogger("chatdev-api.actions")

class GitHubActionsRunner:
    """
    Class to handle GitHub Actions workflow execution using 'act'
    """
    
    def __init__(self, project_dir: str):
        """
        Initialize the GitHub Actions runner
        
        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = validate_path(project_dir)
        if not self.project_dir:
            raise ValueError(f"Invalid project directory: {project_dir}")
        
        # Ensure project directory exists
        if not os.path.exists(self.project_dir):
            raise ValueError(f"Project directory does not exist: {project_dir}")
        
        # Check if act is installed
        self._check_act_installed()
        
        # Path to store workflow files
        self.workflows_dir = os.path.join(self.project_dir, ".github", "workflows")
        
    def _check_act_installed(self) -> bool:
        """
        Check if 'act' is installed in the system
        
        Returns:
            bool: True if act is installed, False otherwise
        
        Raises:
            RuntimeError: If act is not installed
        """
        try:
            result = subprocess.run(
                ["act", "--version"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            if result.returncode != 0:
                raise RuntimeError("Act command failed. Is 'act' installed and in PATH?")
            logger.info(f"Act version: {result.stdout.strip()}")
            return True
        except FileNotFoundError:
            logger.error("Act is not installed or not in PATH")
            raise RuntimeError("Act is not installed or not in PATH. Please install it first.")
    
    def setup_workflows(self, workflow_content: Optional[str] = None) -> None:
        """
        Setup GitHub Actions workflow files in the project directory
        
        Args:
            workflow_content: Optional custom workflow content. If None, a default APK build workflow will be used.
            
        Returns:
            None
        """
        # Create workflows directory if it doesn't exist
        os.makedirs(self.workflows_dir, exist_ok=True)
        
        # If no workflow content provided, use the default build.yml from the project
        if not workflow_content:
            default_workflow_path = os.path.join(ROOT_DIR, ".github", "workflows", "build.yml")
            if os.path.exists(default_workflow_path):
                with open(default_workflow_path, 'r', encoding='utf-8') as f:
                    workflow_content = f.read()
            else:
                # If no default workflow file exists, use a hardcoded basic workflow
                workflow_content = """name: Flet App Build
on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Install Flutter
        uses: flutter-actions/setup-flutter@v4
        with:
          channel: stable
      - name: Build APK
        run: |
          poetry run flet build apk
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          path: build/apk
"""
        
        # Write workflow file
        workflow_path = os.path.join(self.workflows_dir, "build.yml")
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(workflow_content)
        
        logger.info(f"Setup GitHub Actions workflow at {workflow_path}")
    
    async def run_workflow(self, 
                        workflow_id: str = "build.yml", 
                        event: str = "workflow_dispatch",
                        args: Optional[Dict[str, Any]] = None) -> Tuple[int, str, str]:
        """
        Run a GitHub Actions workflow using 'act'
        
        Args:
            workflow_id: ID or filename of the workflow to run
            event: GitHub event to trigger (default: workflow_dispatch)
            args: Additional arguments for act command
            
        Returns:
            Tuple[int, str, str]: Return code, stdout, and stderr
        """
        workflow_path = os.path.join(self.workflows_dir, workflow_id)
        if not os.path.exists(workflow_path):
            raise ValueError(f"Workflow {workflow_id} does not exist")
        
        # Prepare command
        # Instead of using -f flag, directly specify the workflow file with -W
        cmd = ["act", event, "-W", workflow_path]
        
        # Add additional arguments
        if args:
            for key, value in args.items():
                cmd.append(f"--{key}={value}")
        
        logger.info(f"Running GitHub Actions workflow: {' '.join(cmd)}")
        
        # Run the command asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.project_dir
        )
        
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        
        if process.returncode != 0:
            logger.error(f"Workflow execution failed: {stderr_str}")
        else:
            logger.info(f"Workflow execution successful")
            
        return process.returncode, stdout_str, stderr_str
    
    def get_artifacts(self) -> Dict[str, str]:
        """
        Get the list of artifacts generated from the workflow
        
        Returns:
            Dict[str, str]: Dictionary mapping artifact names to their paths
        """
        apk_dir = os.path.join(self.project_dir, "build", "apk")
        artifacts = {}
        
        if os.path.exists(apk_dir):
            for file in os.listdir(apk_dir):
                if file.endswith(".apk"):
                    artifacts[file] = os.path.join(apk_dir, file)
        
        return artifacts

def get_project_path(project_name: str, org_name: str = None, timestamp: str = None) -> Optional[str]:
    """
    Get the path to a project in the warehouse
    
    Args:
        project_name: The name of the project
        org_name: Optional organization name
        timestamp: Optional timestamp
        
    Returns:
        Optional[str]: Path to the project, or None if not found
    """
    if not os.path.exists(WAREHOUSE_DIR):
        logger.warning(f"Warehouse directory {WAREHOUSE_DIR} does not exist")
        return None
    
    # If we have the exact path components, try to find it directly
    if project_name and org_name and timestamp:
        exact_path = os.path.join(WAREHOUSE_DIR, f"{project_name}_{org_name}_{timestamp}")
        if os.path.exists(exact_path):
            return exact_path
    
    # Otherwise, search for matching projects
    for item in os.listdir(WAREHOUSE_DIR):
        item_path = os.path.join(WAREHOUSE_DIR, item)
        if os.path.isdir(item_path) and item.startswith(f"{project_name}_"):
            return item_path
    
    return None

async def setup_and_run_workflow(project_dir: str, task_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Set up and run GitHub Actions workflow for a project
    
    Args:
        project_dir: Path to the project directory
        task_id: Optional task ID to associate the build with
        
    Returns:
        Dict[str, Any]: Result with status and artifact information
    """
    if not os.path.exists(project_dir):
        raise ResourceNotFoundError(f"Project directory {project_dir} does not exist")
        
    # Check if the project has a requirements.txt file
    req_file = os.path.join(project_dir, "requirements.txt")
    if not os.path.exists(req_file):
        # Create a minimal requirements.txt file if none exists
        with open(req_file, 'w') as f:
            f.write("flet>=0.20.0\n")
            
    # Check if there's a main.py file or an app.py file (common entry points)
    main_file = os.path.join(project_dir, "main.py")
    app_file = os.path.join(project_dir, "app.py")
    
    if not os.path.exists(main_file):
        if os.path.exists(app_file):
            # Copy app.py to main.py
            shutil.copy(app_file, main_file)
        else:
            # Try to find another Python file that might be the entry point
            py_files = [f for f in os.listdir(project_dir) if f.endswith('.py')]
            if py_files:
                # Copy the first Python file to main.py if it's not already main.py
                if py_files[0] != "main.py":
                    shutil.copy(os.path.join(project_dir, py_files[0]), main_file)
            else:
                raise ResourceNotFoundError(f"No Python files found in {project_dir}")
    
    # Create a basic pyproject.toml file if one doesn't exist
    pyproject_file = os.path.join(project_dir, "pyproject.toml")
    if not os.path.exists(pyproject_file):
        with open(pyproject_file, 'w') as f:
            f.write(f"""[tool.poetry]
name = "{os.path.basename(project_dir)}"
version = "0.1.0"
description = "Generated by ChatDev"
authors = ["ChatDev <chatdev@example.com>"]

[tool.poetry.dependencies]
python = ">=3.8,<4.0"
flet = ">=0.20.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
""")

    try:
        # Initialize the GitHub Actions runner
        runner = GitHubActionsRunner(project_dir)
        
        # Setup workflow files
        runner.setup_workflows()
        
        # Run the workflow
        returncode, stdout, stderr = await runner.run_workflow()
        
        if returncode != 0:
            return {
                "success": False,
                "message": "Workflow execution failed",
                "stdout": stdout,
                "stderr": stderr
            }
        
        # Get artifacts
        artifacts = runner.get_artifacts()
        
        return {
            "success": True,
            "message": "Workflow execution successful",
            "artifacts": artifacts,
            "stdout": stdout,
            "stderr": stderr
        }
        
    except Exception as e:
        logger.exception(f"Error running GitHub Actions workflow: {str(e)}")
        raise InternalServerError(f"Failed to run GitHub Actions workflow: {str(e)}")
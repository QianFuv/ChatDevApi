from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Path, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import logging
import time
from datetime import datetime

from .models import (
    ChatDevGenerateRequest, 
    TaskResponse, 
    TaskStatus, 
    TaskList,
    TaskCancelRequest,
    BuildApkRequest,
    BuildApkResponse,
    HealthResponse,
    ErrorResponse
)
from .database import get_db, Task
from .task_manager import run_chatdev_task, cancel_chatdev_task, build_apk_for_project
from .dependencies import verify_api_key, get_request_body
from .exceptions import ResourceNotFoundError, ValidationError, TaskCancellationError, AuthenticationError
from .actions import get_project_path, setup_and_run_workflow
from . import __version__

# Configure logging
logger = logging.getLogger("chatdev-api.routes")

# Create router
api_router = APIRouter(tags=["ChatDev"])

@api_router.post(
    "/generate", 
    response_model=TaskResponse, 
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Successfully created generation task", "model": TaskResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Authentication error", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def generate_project(
    request: ChatDevGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a new ChatDev generation task
    
    This endpoint initiates a new software generation task using the provided configuration.
    The task will run asynchronously in the background, and a task ID will be returned for tracking progress.
    
    Parameters:
    - **api_key** (str, required): Your OpenAI API key for authentication
    - **base_url** (str, optional): Optional base URL for API calls (useful for proxies or alternative endpoints)
    - **task** (str, required): Description of the software to build (10-2000 characters)
    - **name** (str, required): Name of the software project (alphanumeric, underscores and hyphens only)
    - **config** (str, optional): Configuration name under CompanyConfig/ (Default, Art, Human, Flet) - Default: "Default"
    - **org** (str, optional): Organization name - Default: "DefaultOrganization"
    - **model** (str, optional): LLM model to use - Default: "CLAUDE_3_5_SONNET"
      Options: "GPT_3_5_TURBO", "GPT_4", "GPT_4_TURBO", "GPT_4O", "GPT_4O_MINI", "CLAUDE_3_5_SONNET", "DEEPSEEK_R1"
    - **path** (str, optional): Path to existing code for incremental development - Default: ""
    - **build_apk** (bool, optional): Whether to build an APK after generating the software - Default: false
    
    Returns:
    - **task_id** (int): Unique identifier for the created task
    - **status** (str): Current status of the task (PENDING)
    - **created_at** (datetime): Task creation timestamp
    """
    logger.info(f"Received generation request for project: {request.name}")
    
    try:
        # Create new task record in database
        task = Task(
            status="PENDING",
            request_data=json.loads(request.model_dump_json()),
            build_apk=request.build_apk
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Start background task for asynchronous processing
        background_tasks.add_task(
            run_chatdev_task, 
            task.id, 
            json.loads(request.model_dump_json())
        )
        
        logger.info(f"Created task ID: {task.id} for project: {request.name}")
        
        # Return task information to client
        return TaskResponse(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at
        )
    
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to create generation task: {str(e)}"
        )
    finally:
        db.close()

@api_router.get(
    "/status/{task_id}", 
    response_model=TaskStatus,
    responses={
        200: {"description": "Successfully retrieved task status", "model": TaskStatus},
        404: {"description": "Task not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_task_status(
    task_id: int = Path(..., description="The ID of the task to check", gt=0, example=1),
    db: Session = Depends(get_db)
):
    """
    Get the status of a ChatDev generation task
    
    This endpoint returns the current status and details of an existing generation task.
    
    Parameters:
    - **task_id** (int, path parameter): The unique identifier of the task to check (greater than 0)
    
    Returns:
    - **task_id** (int): Unique identifier for the task
    - **status** (str): Current status of the task (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
    - **apk_build_status** (str, optional): Status of APK build (BUILDING, BUILDED, BUILDFAILED)
    - **created_at** (datetime): Task creation timestamp
    - **updated_at** (datetime): Last update timestamp
    - **result_path** (str, optional): Path to the generated software if completed
    - **apk_path** (str, optional): Path to the generated APK if built
    - **error_message** (str, optional): Error message if failed
    """
    logger.info(f"Fetching status for task ID: {task_id}")
    
    try:
        # Query the task from database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Task with ID {task_id} not found"
            )
        
        # Return task status and details
        return TaskStatus(
            task_id=task.id,
            status=task.status,
            apk_build_status=task.apk_build_status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_path=task.result_path,
            apk_path=task.apk_path,
            error_message=task.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to retrieve task status: {str(e)}"
        )
    finally:
        db.close()

@api_router.get(
    "/tasks", 
    response_model=TaskList,
    responses={
        200: {"description": "Successfully retrieved task list", "model": TaskList},
        422: {"description": "Validation error", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def list_tasks(
    status: Optional[str] = Query(
        None, 
        description="Filter tasks by status", 
        example="RUNNING",
        regex="^(PENDING|RUNNING|COMPLETED|FAILED|CANCELLED)$"
    ),
    limit: int = Query(
        10, 
        ge=1, 
        le=100, 
        description="Maximum number of tasks to return"
    ),
    offset: int = Query(
        0, 
        ge=0, 
        description="Number of tasks to skip"
    ),
    db: Session = Depends(get_db)
):
    """
    List all ChatDev generation tasks
    
    This endpoint returns a paginated list of all generation tasks, with optional filtering by status.
    
    Parameters:
    - **status** (str, query parameter, optional): Filter tasks by status (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
    - **limit** (int, query parameter, optional): Maximum number of tasks to return (1-100) - Default: 10
    - **offset** (int, query parameter, optional): Number of tasks to skip for pagination - Default: 0
    
    Returns:
    - **tasks** (array): Array of TaskStatus objects
    - **total** (int): Total number of tasks matching the filter criteria
    """
    logger.info(f"Listing tasks with status: {status}, limit: {limit}, offset: {offset}")
    
    try:
        # Prepare database query
        query = db.query(Task)
        
        # Apply status filter if provided
        if status:
            # Status validation happens through the regex in Query parameter
            query = query.filter(Task.status == status)
        
        # Get total count for pagination info
        total = query.count()
        
        # Get paginated results
        tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
        
        # Return task list with pagination info
        return TaskList(
            tasks=[
                TaskStatus(
                    task_id=task.id,
                    status=task.status,
                    apk_build_status=task.apk_build_status,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    result_path=task.result_path,
                    apk_path=task.apk_path,
                    error_message=task.error_message
                )
                for task in tasks
            ],
            total=total
        )
    
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to list tasks: {str(e)}"
        )
    finally:
        db.close()

@api_router.post(
    "/cancel/{task_id}", 
    response_model=TaskStatus,
    responses={
        200: {"description": "Successfully cancelled task", "model": TaskStatus},
        400: {"description": "Bad request or task cancellation error", "model": ErrorResponse},
        401: {"description": "Authentication error", "model": ErrorResponse},
        404: {"description": "Task not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def cancel_task(
    task_id: int = Path(
        ..., 
        description="The ID of the task to cancel", 
        gt=0,
        example=1
    ),
    request: TaskCancelRequest = None,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Cancel a running ChatDev generation task
    
    This endpoint attempts to cancel a running or pending task. Only tasks in RUNNING or PENDING state can be cancelled.
    
    Parameters:
    - **task_id** (int, path parameter): The ID of the task to cancel
    - **api_key** (str, required): Your OpenAI API key for authentication
    
    Returns a TaskStatus object with updated status information:
    - **task_id** (int): Unique identifier for the task
    - **status** (str): Updated status of the task (CANCELLED)
    - **created_at** (datetime): Task creation timestamp
    - **updated_at** (datetime): Last update timestamp
    - **result_path** (str, optional): Path to any generated files
    - **apk_path** (str, optional): Path to the APK if built
    - **error_message** (str): Message indicating the task was cancelled
    """
    logger.info(f"Canceling task ID: {task_id}")
    
    try:
        # Find the task in database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Task with ID {task_id} not found"
            )
        
        # Verify task is in a cancellable state
        if task.status not in ["RUNNING", "PENDING"]:
            logger.warning(f"Task ID {task_id} cannot be cancelled, current status: {task.status}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Cannot cancel task with status: {task.status}. Only RUNNING or PENDING tasks can be cancelled."
            )
        
        # Attempt to cancel the task
        success = await cancel_chatdev_task(task_id)
        
        if success:
            # Update task status in database
            task.status = "CANCELLED"
            task.error_message = "Task cancelled by user"
            task.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(task)
            
            logger.info(f"Successfully cancelled task ID: {task_id}")
        else:
            raise TaskCancellationError(
                "Failed to cancel task. The process might have completed or failed already."
            )
        
        # Return updated task status
        return TaskStatus(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_path=task.result_path,
            apk_path=task.apk_path,
            error_message=task.error_message
        )
    
    except HTTPException:
        raise
    except TaskCancellationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error canceling task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to cancel task: {str(e)}"
        )
    finally:
        db.close()

@api_router.delete(
    "/task/{task_id}", 
    response_model=Dict[str, str],
    responses={
        200: {"description": "Successfully deleted task", "model": Dict[str, str]},
        401: {"description": "Authentication error", "model": ErrorResponse},
        404: {"description": "Task not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def delete_task(
    task_id: int = Path(
        ..., 
        description="The ID of the task to delete", 
        gt=0,
        example=1
    ),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Delete a ChatDev task record
    
    This endpoint deletes a task record from the database. It does not delete any files generated by the task.
    
    Parameters:
    - **task_id** (int, path parameter): The ID of the task to delete
    - **api_key** (str, header): Your OpenAI API key for authentication. Must be provided in X-API-Key header.
    
    Returns:
    - **message** (str): Confirmation message indicating the task was deleted
    """
    logger.info(f"Deleting task ID: {task_id}")
    
    try:
        # Find task in database
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Task with ID {task_id} not found"
            )
        
        # Delete task from database
        db.delete(task)
        db.commit()
        
        logger.info(f"Successfully deleted task ID: {task_id}")
        
        # Return success message
        return {"message": f"Task {task_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to delete task: {str(e)}"
        )
    finally:
        db.close()

@api_router.post(
    "/build-apk", 
    response_model=BuildApkResponse,
    responses={
        200: {"description": "APK build initiated", "model": BuildApkResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Authentication error", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def build_apk(
    request: BuildApkRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Build an APK from an existing project
    
    This endpoint builds an Android APK from an existing ChatDev project in the WareHouse directory.
    It uses GitHub Actions workflows to perform the build process.
    
    Parameters:
    - **api_key** (str, required): Your OpenAI API key for authentication
    - **project_name** (str, required): Name of the project to build
    - **organization** (str, optional): Organization name in the project path
    - **timestamp** (str, optional): Timestamp in the project path
    - **task_id** (int, optional): Task ID if building APK for an existing task
    
    Returns:
    - **success** (bool): Whether the build was successful
    - **message** (str): Status message about the build process
    - **apk_path** (str, optional): Path to the built APK file
    - **artifacts** (object, optional): Dictionary of all generated artifacts and their paths
    """
    logger.info(f"Received APK build request for project: {request.project_name}")
    
    try:
        # Find project directory
        project_dir = get_project_path(
            request.project_name,
            request.organization,
            request.timestamp
        )
        
        if not project_dir:
            raise ResourceNotFoundError(f"Project not found: {request.project_name}")
        
        # Update task status if task_id is provided
        task = None
        if request.task_id:
            task = db.query(Task).filter(Task.id == request.task_id).first()
            if task:
                task.apk_build_status = "BUILDING"
                db.commit()
                logger.info(f"Updated task {request.task_id} APK build status to BUILDING")
            else:
                logger.warning(f"Task {request.task_id} not found")
        
        # Build the APK using GitHub Actions
        result = await build_apk_for_project(
            request.project_name,
            request.organization,
            request.timestamp
        )
        
        # Extract the first APK path if available
        apk_path = None
        if result.get("success") and result.get("artifacts"):
            apk_path = list(result["artifacts"].values())[0] if result["artifacts"] else None
            logger.info(f"APK built successfully at: {apk_path}")
            
            # Update task if task_id is provided
            if task:
                task.apk_build_status = "BUILDED"
                task.apk_path = apk_path
                db.commit()
                logger.info(f"Updated task {request.task_id} APK build status to BUILDED")
        else:
            logger.warning(f"APK build failed or no artifacts produced: {result.get('message')}")
            
            # Update task if task_id is provided
            if task:
                task.apk_build_status = "BUILDFAILED"
                task.error_message = result.get('message', 'APK build failed')
                db.commit()
                logger.info(f"Updated task {request.task_id} APK build status to BUILDFAILED")
        
        # Return build results
        return BuildApkResponse(
            success=result.get("success", False),
            message=result.get("message", "APK build failed"),
            apk_path=apk_path,
            artifacts=result.get("artifacts")
        )
    
    except ResourceNotFoundError as e:
        logger.error(f"Project not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error building APK: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to build APK: {str(e)}"
        )

@api_router.get(
    "/health", 
    response_model=HealthResponse,
    responses={
        200: {"description": "API is healthy", "model": HealthResponse},
        500: {"description": "API is not healthy", "model": ErrorResponse}
    }
)
async def health_check():
    """
    API health check endpoint
    
    This endpoint returns the current status of the API and its version.
    It can be used to verify that the API is running properly.
    
    No parameters required.
    
    Returns:
    - **status** (str): Health status of the API ("healthy")
    - **version** (str): Current version of the API
    - **timestamp** (float): Current server timestamp
    """
    try:
        # Simple health check that returns API status and version
        return HealthResponse(
            status="healthy",
            version=__version__,
            timestamp=time.time()
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API health check failed: {str(e)}"
        )
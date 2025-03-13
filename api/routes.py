from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging

from .models import (
    ChatDevGenerateRequest, 
    TaskResponse, 
    TaskStatus, 
    TaskList,
    TaskCancelRequest
)
from .database import get_db, Task
from .task_manager import run_chatdev_task, cancel_chatdev_task
from .dependencies import verify_api_key

# Configure logging
logger = logging.getLogger("chatdev-api.routes")

# Create router
api_router = APIRouter(tags=["ChatDev"])

@api_router.post("/generate", response_model=TaskResponse)
async def generate_project(
    request: ChatDevGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start a new ChatDev generation task
    
    This endpoint initiates a new software generation task using the provided configuration.
    The task will run asynchronously in the background, and a task ID will be returned.
    
    - **api_key**: Your OpenAI API key
    - **task**: Description of the software to build
    - **name**: Name of the software project
    - **config**: Configuration name (Default, Art, Human)
    - **org**: Organization name
    - **model**: LLM model to use
    - **path**: Optional path for incremental development
    """
    logger.info(f"Received generation request for project: {request.name}")
    
    try:
        # Create new task record
        task = Task(
            status="PENDING",
            request_data=json.loads(request.model_dump_json())
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Start background task
        background_tasks.add_task(
            run_chatdev_task, 
            task.id, 
            json.loads(request.model_dump_json())
        )
        
        logger.info(f"Created task ID: {task.id} for project: {request.name}")
        
        return TaskResponse(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at
        )
    
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create generation task: {str(e)}"
        )
    finally:
        db.close()

@api_router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: int = Path(..., description="The ID of the task to check"),
    db: Session = Depends(get_db)
):
    """
    Get the status of a ChatDev generation task
    
    This endpoint returns the current status of a generation task.
    
    - **task_id**: The ID of the task to check
    """
    logger.info(f"Fetching status for task ID: {task_id}")
    
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} not found")
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatus(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_path=task.result_path,
            error_message=task.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task status: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve task status: {str(e)}"
        )
    finally:
        db.close()

@api_router.get("/tasks", response_model=TaskList)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter tasks by status"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    db: Session = Depends(get_db)
):
    """
    List all ChatDev generation tasks
    
    This endpoint returns a list of all generation tasks, with optional filtering by status.
    
    - **status**: Optional filter by task status (PENDING, RUNNING, COMPLETED, FAILED)
    - **limit**: Maximum number of tasks to return (default: 10, max: 100)
    - **offset**: Number of tasks to skip (default: 0)
    """
    logger.info(f"Listing tasks with status: {status}, limit: {limit}, offset: {offset}")
    
    try:
        query = db.query(Task)
        
        if status:
            query = query.filter(Task.status == status)
        
        total = query.count()
        tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
        
        return TaskList(
            tasks=[
                TaskStatus(
                    task_id=task.id,
                    status=task.status,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    result_path=task.result_path,
                    error_message=task.error_message
                )
                for task in tasks
            ],
            total=total
        )
    
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to list tasks: {str(e)}"
        )
    finally:
        db.close()

@api_router.post("/cancel/{task_id}", response_model=TaskStatus)
async def cancel_task(
    task_id: int = Path(..., description="The ID of the task to cancel"),
    request: TaskCancelRequest = None,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Cancel a running ChatDev generation task
    
    This endpoint attempts to cancel a running task.
    
    - **task_id**: The ID of the task to cancel
    - **api_key**: Your OpenAI API key for authentication
    """
    logger.info(f"Canceling task ID: {task_id}")
    
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} not found")
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status != "RUNNING":
            logger.warning(f"Task ID {task_id} is not running, current status: {task.status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel task with status: {task.status}"
            )
        
        # Cancel the task
        success = await cancel_chatdev_task(task_id)
        
        if success:
            task.status = "CANCELLED"
            task.error_message = "Task cancelled by user"
            db.commit()
            db.refresh(task)
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to cancel task. The process might have completed or failed already."
            )
        
        return TaskStatus(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_path=task.result_path,
            error_message=task.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling task: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to cancel task: {str(e)}"
        )
    finally:
        db.close()

@api_router.delete("/task/{task_id}", response_model=dict)
async def delete_task(
    task_id: int = Path(..., description="The ID of the task to delete"),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Delete a ChatDev task record
    
    This endpoint deletes a task record from the database.
    It does not delete any generated files.
    
    - **task_id**: The ID of the task to delete
    - **api_key**: Your OpenAI API key for authentication
    """
    logger.info(f"Deleting task ID: {task_id}")
    
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Task ID {task_id} not found")
            raise HTTPException(status_code=404, detail="Task not found")
        
        db.delete(task)
        db.commit()
        
        return {"message": f"Task {task_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete task: {str(e)}"
        )
    finally:
        db.close()
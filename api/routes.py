from fastapi import APIRouter, HTTPException, BackgroundTasks
from .models import ChatDevGenerateRequest, TaskResponse, TaskStatus
from .database import SessionLocal, Task
from .task_manager import run_chatdev_task
import json

router = APIRouter()

@router.post("/generate", response_model=TaskResponse)
async def generate_project(
    request: ChatDevGenerateRequest,
    background_tasks: BackgroundTasks
):
    """Start a new ChatDev generation task"""
    db = SessionLocal()
    try:
        # Create new task record
        task = Task(
            status="PENDING",
            request_data=json.loads(request.json())
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Start background task
        background_tasks.add_task(run_chatdev_task, task.id, json.loads(request.json()))

        return TaskResponse(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at
        )

    finally:
        db.close()

@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: int):
    """Get the status of a ChatDev generation task"""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskStatus(
            task_id=task.id,
            status=task.status,
            created_at=task.created_at,
            updated_at=task.updated_at,
            result_path=task.result_path,
            error_message=task.error_message
        )

    finally:
        db.close()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
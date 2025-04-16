from pydantic import BaseModel, Field, validator, EmailStr, constr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import re

class ChatDevGenerateRequest(BaseModel):
    """
    Request model: Generate a new ChatDev project
    """
    # Authentication
    api_key: str = Field(..., description="OpenAI API key for authentication")
    base_url: Optional[str] = Field(None, description="Optional base URL for API calls (for proxies or alternative endpoints)")
    
    # Project settings
    task: str = Field(..., min_length=10, max_length=2000, description="Description of the software to be generated")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the software project")
    
    # Optional configuration
    config: str = Field("Default", description="Configuration name under CompanyConfig/ (Default, Art, Human, Flet)")
    org: str = Field("DefaultOrganization", description="Name of organization")
    model: str = Field("CLAUDE_3_5_SONNET", description="LLM model to use")
    path: str = Field("", description="Path to existing code for incremental development")
    build_apk: bool = Field(False, description="Whether to build an APK after generating the software")
    
    @validator('name')
    def validate_project_name(cls, v):
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('Name must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    @validator('model')
    def validate_model(cls, v):
        valid_models = [
            "GPT_3_5_TURBO", "GPT_4", "GPT_4_TURBO", 
            "GPT_4O", "GPT_4O_MINI", "CLAUDE_3_5_SONNET", "DEEPSEEK_R1"
        ]
        if v not in valid_models:
            raise ValueError(f'Model must be one of: {", ".join(valid_models)}')
        return v
    
    @validator('config')
    def validate_config(cls, v):
        valid_configs = ["Default", "Art", "Human", "Flet", "Incremental"]
        if v not in valid_configs:
            raise ValueError(f'Config must be one of: {", ".join(valid_configs)}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "api_key": "sk-...",
                "task": "Create a simple todo list application with a GUI interface",
                "name": "TodoApp",
                "config": "Default",
                "org": "MyOrganization",
                "model": "CLAUDE_3_5_SONNET",
                "build_apk": True
            }
        }

class TaskResponse(BaseModel):
    """
    Response model: Information about the newly created task
    """
    task_id: int = Field(..., description="Unique identifier for the task")
    status: str = Field(..., description="Current status of the task")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        schema_extra = {
            "example": {
                "task_id": 1,
                "status": "PENDING",
                "created_at": "2024-03-13T14:30:00"
            }
        }

class TaskStatus(BaseModel):
    """
    Response model: Task status check
    """
    task_id: int = Field(..., description="Unique identifier for the task")
    status: str = Field(..., description="Current status of the task: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED")
    apk_build_status: Optional[str] = Field(None, description="Status of APK build: BUILDING, BUILDED, BUILDFAILED")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    result_path: Optional[str] = Field(None, description="Path to the generated software if completed")
    apk_path: Optional[str] = Field(None, description="Path to the generated APK if built")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        schema_extra = {
            "example": {
                "task_id": 1,
                "status": "COMPLETED",
                "apk_build_status": "BUILDED",
                "created_at": "2024-03-13T14:30:00",
                "updated_at": "2024-03-13T14:45:00",
                "result_path": "WareHouse/TodoApp_MyOrganization_20240313143000",
                "apk_path": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk",
                "error_message": None
            }
        }

class TaskList(BaseModel):
    """
    Response model: List of tasks
    """
    tasks: List[TaskStatus] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    
    class Config:
        schema_extra = {
            "example": {
                "tasks": [
                    {
                        "task_id": 1,
                        "status": "COMPLETED",
                        "created_at": "2024-03-13T14:30:00",
                        "updated_at": "2024-03-13T14:45:00",
                        "result_path": "WareHouse/TodoApp_MyOrganization_20240313143000",
                        "apk_path": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk",
                        "error_message": None
                    }
                ],
                "total": 1
            }
        }

class TaskCancelRequest(BaseModel):
    """
    Request model: Cancel a task
    """
    api_key: str = Field(..., description="OpenAI API key for authentication")
    
    class Config:
        schema_extra = {
            "example": {
                "api_key": "sk-..."
            }
        }

class BuildApkRequest(BaseModel):
    """
    Request model: Build an APK
    """
    api_key: str = Field(..., description="OpenAI API key for authentication")
    project_name: str = Field(..., description="Name of the project to build")
    organization: Optional[str] = Field(None, description="Organization name in the project path")
    timestamp: Optional[str] = Field(None, description="Timestamp in the project path")
    task_id: Optional[int] = Field(None, description="Task ID if building APK for an existing task")
    
    @validator('project_name')
    def validate_project_name(cls, v):
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('Project name must contain only alphanumeric characters, underscores, and hyphens')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "api_key": "sk-...",
                "project_name": "TodoApp",
                "organization": "MyOrganization",
                "timestamp": "20240313143000",
                "task_id": 1
            }
        }

class BuildApkResponse(BaseModel):
    """
    Response model: APK build result
    """
    success: bool = Field(..., description="Whether the build was successful")
    message: str = Field(..., description="Status message")
    apk_path: Optional[str] = Field(None, description="Path to the built APK file")
    artifacts: Optional[Dict[str, str]] = Field(None, description="Dictionary of generated artifacts")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "APK build completed successfully",
                "apk_path": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk",
                "artifacts": {
                    "app-release.apk": "WareHouse/TodoApp_MyOrganization_20240313143000/build/apk/app-release.apk"
                }
            }
        }

class HealthResponse(BaseModel):
    """
    Response model: Health check
    """
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    timestamp: float = Field(..., description="Current timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": 1678735200.0
            }
        }

class ErrorResponse(BaseModel):
    """
    Response model: Error information
    """
    error: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Invalid API key provided",
                "type": "authentication_error"
            }
        }
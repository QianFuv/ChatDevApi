from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatDevGenerateRequest(BaseModel):
    # Environment settings
    api_key: str
    base_url: Optional[str] = None
    
    # Project settings
    task: str
    name: str
    config: str = "Default"
    org: str = "DefaultOrganization"
    model: str = "CLAUDE_3_5_SONNET"
    path: str = ""

class TaskResponse(BaseModel):
    task_id: int
    status: str
    created_at: datetime

class TaskStatus(BaseModel):
    task_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    result_path: Optional[str] = None
    error_message: Optional[str] = None
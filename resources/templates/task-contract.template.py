"""
Plantilla: Contratos y Esquemas de Tipado con Pydantic (v2)
Define la estructura formal de tareas, estados y respuestas.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, UUID4

TaskStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]

class TaskBase(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)

class TaskCreateInput(TaskBase):
    created_by: Optional[UUID4] = None
    max_attempts: int = Field(default=3, ge=1, le=10)

class TaskStatusResponse(BaseModel):
    task_id: UUID4
    task_type: str
    status: TaskStatus
    progress: int = Field(default=0, ge=0, le=100)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    attempts: int = Field(default=0, ge=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ReportPayload(BaseModel):
    report_type: str = Field(..., description="Tipo de reporte (ej. MENSUAL, AUDITORIA)")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)

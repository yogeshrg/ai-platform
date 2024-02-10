"""Pydantic models for AI Platform."""

from typing import Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class UserRole(str, Enum):
    """User roles."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class ProjectStatus(str, Enum):
    """Project statuses."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DeploymentStatus(str, Enum):
    """Deployment statuses."""

    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


class ModelStatus(str, Enum):
    """Model statuses."""

    REGISTERED = "registered"
    VALIDATING = "validating"
    READY = "ready"
    DEPRECATED = "deprecated"


class UserCreate(BaseModel):
    """Create user request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    """User response."""

    id: UUID
    email: EmailStr
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class Token(BaseModel):
    """Authentication token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ProjectCreate(BaseModel):
    """Create project request."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    owner_id: UUID


class ProjectResponse(BaseModel):
    """Project response."""

    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class DeploymentCreate(BaseModel):
    """Create deployment request."""

    project_id: UUID
    model_id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=100)
    image: str
    replicas: int = Field(default=1, ge=1, le=100)
    resources: dict[str, Any] = Field(default_factory=dict)
    env_vars: dict[str, str] = Field(default_factory=dict)


class DeploymentResponse(BaseModel):
    """Deployment response."""

    id: UUID
    project_id: UUID
    model_id: UUID | None
    name: str
    image: str
    replicas: int
    status: DeploymentStatus
    endpoint: str | None = None
    created_at: datetime
    updated_at: datetime


class ModelCreate(BaseModel):
    """Register model request."""

    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    version: str
    description: str | None = None
    artifact_uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Model response."""

    id: UUID
    project_id: UUID
    name: str
    version: str
    status: ModelStatus
    artifact_uri: str
    metadata: dict[str, Any]
    registered_at: datetime


class AuditLogEntry(BaseModel):
    """Audit log entry."""

    id: UUID
    user_id: UUID
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
    redis: str
    active_users: int
    active_projects: int
    running_deployments: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MetricsResponse(BaseModel):
    """Metrics response."""

    cpu_usage: float
    memory_usage: float
    disk_usage: float
    gpu_usage: float | None = None
    active_requests: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
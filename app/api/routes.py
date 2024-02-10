"""API routes for AI Platform."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.config import settings
from app.core.auth import (
    get_current_user,
    create_tokens,
    refresh_access_token,
    revoke_refresh_token,
    require_role,
)
from app.core.database import get_db
from app.services.platform_service import platform_service
from app.models.schemas import (
    UserCreate,
    UserResponse,
    Token,
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    DeploymentCreate,
    DeploymentResponse,
    DeploymentStatus,
    ModelCreate,
    ModelResponse,
    ModelStatus,
    HealthResponse,
    MetricsResponse,
    AuditLogEntry,
)
from app.models.database import User, UserRole

router = APIRouter(prefix="/api/v1")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ========== Authentication ==========

@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db=Depends(get_db)):
    """Register a new user."""
    from app.core.auth import create_user
    try:
        user = await create_user(db, user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """Login and get access token."""
    from app.core.auth import authenticate_user, create_tokens
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return await create_tokens(user)


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    tokens = await refresh_access_token(refresh_token)
    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return tokens


@router.post("/auth/logout")
async def logout(refresh_token: str):
    """Revoke refresh token."""
    await revoke_refresh_token(refresh_token)
    return {"status": "logged out"}


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse.model_validate(current_user)


# ========== Health & Metrics ==========

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return await platform_service.get_health()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(current_user: User = Depends(require_role([UserRole.ADMIN]))):
    """Get platform metrics (admin only)."""
    return await platform_service.get_metrics()


# ========== Projects ==========

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    return await platform_service.create_project(project_data, current_user.id)


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    owner_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """List projects."""
    return await platform_service.list_projects(owner_id, status, limit, offset)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get a project by ID."""
    project = await platform_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Update a project."""
    project = await platform_service.update_project(project_id, name, description, status, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    success = await platform_service.delete_project(project_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted"}


# ========== Deployments ==========

@router.post("/deployments", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment_data: DeploymentCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new deployment."""
    return await platform_service.create_deployment(deployment_data, current_user.id)


@router.get("/deployments", response_model=list[DeploymentResponse])
async def list_deployments(
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """List deployments."""
    return await platform_service.list_deployments(project_id, status, limit, offset)


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get a deployment by ID."""
    deployment = await platform_service.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.put("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: UUID,
    replicas: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Update a deployment."""
    deployment = await platform_service.update_deployment(deployment_id, replicas, status, current_user.id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post("/deployments/{deployment_id}/scale", response_model=DeploymentResponse)
async def scale_deployment(
    deployment_id: UUID,
    replicas: int,
    current_user: User = Depends(get_current_user),
):
    """Scale a deployment."""
    deployment = await platform_service.scale_deployment(deployment_id, replicas, current_user.id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post("/deployments/{deployment_id}/stop", response_model=DeploymentResponse)
async def stop_deployment(
    deployment_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Stop a deployment."""
    deployment = await platform_service.stop_deployment(deployment_id, current_user.id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Delete a deployment."""
    success = await platform_service.delete_deployment(deployment_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return {"status": "deleted"}


@router.get("/deployments/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: UUID,
    lines: int = 100,
    current_user: User = Depends(get_current_user),
):
    """Get deployment logs."""
    logs = await platform_service.get_deployment_logs(deployment_id, lines)
    if logs is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return {"logs": logs}


# ========== Models ==========

@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    model_data: ModelCreate,
    current_user: User = Depends(get_current_user),
):
    """Register a new model."""
    return await platform_service.register_model(model_data, current_user.id)


@router.get("/models", response_model=list[ModelResponse])
async def list_models(
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """List models."""
    return await platform_service.list_models(project_id, status, limit, offset)


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Get a model by ID."""
    model = await platform_service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/models/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
):
    """Update a model."""
    model = await platform_service.update_model(model_id, name, description, status, metadata, current_user.id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/models/{model_id}/validate", response_model=ModelResponse)
async def validate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Validate a model."""
    model = await platform_service.validate_model(model_id, current_user.id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/models/{model_id}/deprecate", response_model=ModelResponse)
async def deprecate_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Deprecate a model."""
    model = await platform_service.deprecate_model(model_id, current_user.id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """Delete a model."""
    success = await platform_service.delete_model(model_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"status": "deleted"}


# ========== Audit & Compliance ==========

@router.get("/audit/logs")
async def get_audit_logs(
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Get audit logs (admin only)."""
    return await platform_service.get_audit_logs(
        user_id, None, resource_id, None, None, None, limit=100, offset=0
    )


@router.get("/compliance/report")
async def get_compliance_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Get compliance report (admin only)."""
    return await platform_service.get_compliance_report(start_date, end_date)
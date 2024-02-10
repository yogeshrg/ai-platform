"""Project service."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import audit_log
from app.core.database import get_db_context
from app.models.database import Project, User, ProjectStatus
from app.models.schemas import ProjectCreate, ProjectResponse, ProjectStatus as SchemaProjectStatus

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing projects."""

    async def create_project(self, project_data: ProjectCreate, user_id: UUID) -> ProjectResponse:
        """Create a new project."""
        async with get_db_context() as db:
            # Verify owner exists
            owner = await db.get(User, project_data.owner_id)
            if not owner:
                raise ValueError("Owner not found")

            project = Project(
                name=project_data.name,
                description=project_data.description,
                owner_id=project_data.owner_id,
                status=ProjectStatus.ACTIVE,
            )
            db.add(project)
            await db.flush()

            # Audit log
            await audit_log(
                db,
                user_id=user_id,
                action="create_project",
                resource_type="project",
                resource_id=str(project.id),
                details={"name": project.name},
            )

            await db.commit()
            await db.refresh(project)

            return ProjectResponse.model_validate(project)

    async def get_project(self, project_id: UUID) -> Optional[ProjectResponse]:
        """Get a project by ID."""
        async with get_db_context() as db:
            project = await db.get(Project, project_id)
            if not project:
                return None
            return ProjectResponse.model_validate(project)

    async def list_projects(
        self,
        owner_id: Optional[UUID] = None,
        status: Optional[SchemaProjectStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProjectResponse]:
        """List projects with optional filters."""
        async with get_db_context() as db:
            query = select(Project)

            if owner_id:
                query = query.where(Project.owner_id == owner_id)
            if status:
                query = query.where(Project.status == ProjectStatus(status.value))

            query = query.order_by(Project.created_at.desc()).limit(limit).offset(offset)
            result = await db.execute(query)
            projects = result.scalars().all()

            return [ProjectResponse.model_validate(p) for p in projects]

    async def update_project(
        self,
        project_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[SchemaProjectStatus] = None,
        user_id: UUID = None,
    ) -> Optional[ProjectResponse]:
        """Update a project."""
        async with get_db_context() as db:
            project = await db.get(Project, project_id)
            if not project:
                return None

            changes = {}
            if name is not None:
                project.name = name
                changes["name"] = name
            if description is not None:
                project.description = description
                changes["description"] = description
            if status:
                project.status = ProjectStatus(status.value)
                changes["status"] = status.value

            project.updated_at = datetime.utcnow()

            if changes:
                await audit_log(
                    db,
                    user_id=user_id,
                    action="update_project",
                    resource_type="project",
                    resource_id=str(project_id),
                    details=changes,
                )

            await db.commit()
            await db.refresh(project)
            return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: UUID, user_id: UUID) -> bool:
        """Delete a project (soft delete)."""
        async with get_db_context() as db:
            project = await db.get(Project, project_id)
            if not project:
                return False

            project.status = ProjectStatus.DELETED
            project.updated_at = datetime.utcnow()

            await audit_log(
                db,
                user_id=user_id,
                action="delete_project",
                resource_type="project",
                resource_id=str(project_id),
            )

            await db.commit()
            return True

    async def get_project_stats(self, project_id: UUID) -> Optional[dict]:
        """Get project statistics."""
        async with get_db_context() as db:
            project = await db.get(Project, project_id)
            if not project:
                return None

            # Count deployments
            deployments_result = await db.execute(
                select(func.count()).select_from(Deployment).where(Deployment.project_id == project_id)
            )
            deployment_count = deployments_result.scalar()

            # Count models
            models_result = await db.execute(
                select(func.count()).select_from(Model).where(Model.project_id == project_id)
            )
            model_count = models_result.scalar()

            return {
                "project_id": str(project_id),
                "name": project.name,
                "deployment_count": deployment_count,
                "model_count": model_count,
                "status": project.status.value,
            }


# Add missing imports
from typing import Optional
from sqlalchemy import func
from app.models.database import Deployment, Model
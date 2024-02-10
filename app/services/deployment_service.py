"""Deployment service."""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import audit_log
from app.core.database import get_db_context
from app.models.database import Deployment, Project, Model, User, DeploymentStatus
from app.models.schemas import DeploymentCreate, DeploymentResponse, DeploymentStatus as SchemaDeploymentStatus

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service for managing deployments."""

    async def create_deployment(self, deployment_data: DeploymentCreate, user_id: UUID) -> DeploymentResponse:
        """Create a new deployment."""
        async with get_db_context() as db:
            # Verify project exists
            project = await db.get(Project, deployment_data.project_id)
            if not project:
                raise ValueError("Project not found")

            # Verify model exists if provided
            if deployment_data.model_id:
                model = await db.get(Model, deployment_data.model_id)
                if not model:
                    raise ValueError("Model not found")

            deployment = Deployment(
                project_id=deployment_data.project_id,
                model_id=deployment_data.model_id,
                name=deployment_data.name,
                image=deployment_data.image,
                replicas=deployment_data.replicas,
                resources=deployment_data.resources,
                env_vars=deployment_data.env_vars,
                status=DeploymentStatus.PENDING,
                created_by_id=user_id,
            )
            db.add(deployment)
            await db.flush()

            # Audit log
            await audit_log(
                db,
                user_id=user_id,
                action="create_deployment",
                resource_type="deployment",
                resource_id=str(deployment.id),
                details={"name": deployment.name, "image": deployment.image},
            )

            await db.commit()
            await db.refresh(deployment)

            # In production, would trigger actual deployment (Kubernetes, etc.)
            # For now, simulate deployment
            await self._simulate_deployment(db, deployment.id)

            return DeploymentResponse.model_validate(deployment)

    async def _simulate_deployment(self, db: AsyncSession, deployment_id: UUID) -> None:
        """Simulate deployment process."""
        import asyncio
        await asyncio.sleep(0.1)  # Simulate build time

        deployment = await db.get(Deployment, deployment_id)
        if deployment:
            deployment.status = DeploymentStatus.RUNNING
            deployment.endpoint = f"https://{deployment.name}.ai-platform.example.com"
            deployment.updated_at = datetime.utcnow()
            await db.commit()

    async def get_deployment(self, deployment_id: UUID) -> Optional[DeploymentResponse]:
        """Get a deployment by ID."""
        async with get_db_context() as db:
            deployment = await db.get(Deployment, deployment_id)
            if not deployment:
                return None
            return DeploymentResponse.model_validate(deployment)

    async def list_deployments(
        self,
        project_id: Optional[UUID] = None,
        status: Optional[SchemaDeploymentStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DeploymentResponse]:
        """List deployments with optional filters."""
        async with get_db_context() as db:
            query = select(Deployment)

            if project_id:
                query = query.where(Deployment.project_id == project_id)
            if status:
                query = query.where(Deployment.status == DeploymentStatus(status.value))

            query = query.order_by(Deployment.created_at.desc()).limit(limit).offset(offset)
            result = await db.execute(query)
            deployments = result.scalars().all()

            return [DeploymentResponse.model_validate(d) for d in deployments]

    async def update_deployment(
        self,
        deployment_id: UUID,
        replicas: Optional[int] = None,
        status: Optional[SchemaDeploymentStatus] = None,
        user_id: UUID = None,
    ) -> Optional[DeploymentResponse]:
        """Update a deployment."""
        async with get_db_context() as db:
            deployment = await db.get(Deployment, deployment_id)
            if not deployment:
                return None

            changes = {}
            if replicas is not None:
                deployment.replicas = replicas
                changes["replicas"] = replicas
            if status:
                deployment.status = DeploymentStatus(status.value)
                changes["status"] = status.value

            deployment.updated_at = datetime.utcnow()

            if changes:
                await audit_log(
                    db,
                    user_id=user_id,
                    action="update_deployment",
                    resource_type="deployment",
                    resource_id=str(deployment_id),
                    details=changes,
                )

            await db.commit()
            await db.refresh(deployment)
            return DeploymentResponse.model_validate(deployment)

    async def scale_deployment(self, deployment_id: UUID, replicas: int, user_id: UUID) -> Optional[DeploymentResponse]:
        """Scale a deployment."""
        return await self.update_deployment(deployment_id, replicas=replicas, user_id=user_id)

    async def stop_deployment(self, deployment_id: UUID, user_id: UUID) -> Optional[DeploymentResponse]:
        """Stop a deployment."""
        return await self.update_deployment(deployment_id, status=SchemaDeploymentStatus.STOPPED, user_id=user_id)

    async def delete_deployment(self, deployment_id: UUID, user_id: UUID) -> bool:
        """Delete a deployment."""
        async with get_db_context() as db:
            deployment = await db.get(Deployment, deployment_id)
            if not deployment:
                return False

            await audit_log(
                db,
                user_id=user_id,
                action="delete_deployment",
                resource_type="deployment",
                resource_id=str(deployment_id),
            )

            await db.delete(deployment)
            await db.commit()
            return True

    async def get_deployment_logs(self, deployment_id: UUID, lines: int = 100) -> Optional[str]:
        """Get deployment logs (placeholder)."""
        async with get_db_context() as db:
            deployment = await db.get(Deployment, deployment_id)
            if not deployment:
                return None

            # In production, would fetch from logging system
            return f"[INFO] Deployment {deployment.name} running\n[INFO] Replicas: {deployment.replicas}\n[INFO] Status: {deployment.status.value}"


# Add missing imports
from typing import Optional, List
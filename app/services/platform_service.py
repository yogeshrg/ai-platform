"""Main platform service coordinating all sub-services."""

import logging
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.database import init_db, close_db
from app.services.project_service import ProjectService
from app.services.deployment_service import DeploymentService
from app.services.model_service import ModelService
from app.services.audit_service import audit_log, get_audit_logs, get_compliance_report
from app.models.schemas import HealthResponse, MetricsResponse

logger = logging.getLogger(__name__)


class PlatformService:
    """Unified AI Platform service."""

    def __init__(self) -> None:
        self.project_service = ProjectService()
        self.deployment_service = DeploymentService()
        self.model_service = ModelService()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all services."""
        if self._initialized:
            return

        logger.info("Initializing AI Platform...")
        await init_db()
        self._initialized = True
        logger.info("AI Platform initialized")

    async def shutdown(self) -> None:
        """Shutdown the platform."""
        await close_db()
        logger.info("AI Platform shutdown")

    # ========== Health ==========

    async def get_health(self) -> HealthResponse:
        """Get platform health status."""
        # Check database
        db_status = "healthy"
        try:
            async with get_db_context() as db:
                await db.execute("SELECT 1")
        except Exception:
            db_status = "unhealthy"

        # Check Redis
        redis_status = "healthy"
        # Would check Redis connection here

        return HealthResponse(
            status="healthy" if db_status == "healthy" else "degraded",
            version=settings.app_version,
            database=db_status,
            redis=redis_status,
            active_users=0,  # Would query from database
            active_projects=0,
            running_deployments=0,
        )

    async def get_metrics(self) -> MetricsResponse:
        """Get platform metrics."""
        # In production, would collect from monitoring system
        return MetricsResponse(
            cpu_usage=0.0,
            memory_usage=0.0,
            disk_usage=0.0,
            active_requests=0,
        )

    # ========== Projects ==========

    async def create_project(self, project_data, user_id) -> any:
        return await self.project_service.create_project(project_data, user_id)

    async def get_project(self, project_id) -> Optional[any]:
        return await self.project_service.get_project(project_id)

    async def list_projects(self, owner_id=None, status=None, limit=50, offset=0):
        return await self.project_service.list_projects(owner_id, status, limit, offset)

    async def update_project(self, project_id, name=None, description=None, status=None, user_id=None):
        return await self.project_service.update_project(project_id, name, description, status, user_id)

    async def delete_project(self, project_id, user_id):
        return await self.project_service.delete_project(project_id, user_id)

    # ========== Deployments ==========

    async def create_deployment(self, deployment_data, user_id):
        return await self.deployment_service.create_deployment(deployment_data, user_id)

    async def get_deployment(self, deployment_id):
        return await self.deployment_service.get_deployment(deployment_id)

    async def list_deployments(self, project_id=None, status=None, limit=50, offset=0):
        return await self.deployment_service.list_deployments(project_id, status, limit, offset)

    async def update_deployment(self, deployment_id, replicas=None, status=None, user_id=None):
        return await self.deployment_service.update_deployment(deployment_id, replicas, status, user_id)

    async def scale_deployment(self, deployment_id, replicas, user_id):
        return await self.deployment_service.scale_deployment(deployment_id, replicas, user_id)

    async def stop_deployment(self, deployment_id, user_id):
        return await self.deployment_service.stop_deployment(deployment_id, user_id)

    async def delete_deployment(self, deployment_id, user_id):
        return await self.deployment_service.delete_deployment(deployment_id, user_id)

    async def get_deployment_logs(self, deployment_id, lines=100):
        return await self.deployment_service.get_deployment_logs(deployment_id, lines)

    # ========== Models ==========

    async def register_model(self, model_data, user_id):
        return await self.model_service.register_model(model_data, user_id)

    async def get_model(self, model_id):
        return await self.model_service.get_model(model_id)

    async def list_models(self, project_id=None, status=None, limit=50, offset=0):
        return await self.model_service.list_models(project_id, status, limit, offset)

    async def update_model(self, model_id, name=None, description=None, status=None, metadata=None, user_id=None):
        return await self.model_service.update_model(model_id, name, description, status, metadata, user_id)

    async def validate_model(self, model_id, user_id):
        return await self.model_service.validate_model(model_id, user_id)

    async def deprecate_model(self, model_id, user_id):
        return await self.model_service.deprecate_model(model_id, user_id)

    async def delete_model(self, model_id, user_id):
        return await self.model_service.delete_model(model_id, user_id)

    # ========== Audit ==========

    async def get_audit_logs(
        self,
        user_id=None,
        resource_type=None,
        resource_id=None,
        action=None,
        start_date=None,
        end_date=None,
        limit=100,
        offset=0,
    ):
        return await get_audit_logs(user_id, resource_type, resource_id, None, None, None, limit, offset)

    async def get_compliance_report(self, start_date, end_date):
        return await get_compliance_report(start_date, end_date)


# Global instance
platform_service = PlatformService()
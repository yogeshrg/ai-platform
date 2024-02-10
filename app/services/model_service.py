"""Model service."""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import audit_log
from app.core.database import get_db_context
from app.models.database import Model, Project, ModelStatus
from app.models.schemas import ModelCreate, ModelResponse, ModelStatus as SchemaModelStatus

logger = logging.getLogger(__name__)


class ModelService:
    """Service for managing models."""

    async def register_model(self, model_data: ModelCreate, user_id: UUID) -> ModelResponse:
        """Register a new model."""
        async with get_db_context() as db:
            # Verify project exists
            project = await db.get(Project, model_data.project_id)
            if not project:
                raise ValueError("Project not found")

            model = Model(
                project_id=model_data.project_id,
                name=model_data.name,
                version=model_data.version,
                description=model_data.description,
                artifact_uri=model_data.artifact_uri,
                metadata=model_data.metadata,
                status=ModelStatus.REGISTERED,
            )
            db.add(model)
            await db.flush()

            # Audit log
            await audit_log(
                db,
                user_id=user_id,
                action="register_model",
                resource_type="model",
                resource_id=str(model.id),
                details={"name": model.name, "version": model.version},
            )

            await db.commit()
            await db.refresh(model)

            return ModelResponse.model_validate(model)

    async def get_model(self, model_id: UUID) -> Optional[ModelResponse]:
        """Get a model by ID."""
        async with get_db_context() as db:
            model = await db.get(Model, model_id)
            if not model:
                return None
            return ModelResponse.model_validate(model)

    async def list_models(
        self,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ModelResponse]:
        """List models with optional filters."""
        async with get_db_context() as db:
            query = select(Model)

            if project_id:
                query = query.where(Model.project_id == project_id)
            if status:
                query = query.where(Model.status == ModelStatus(status))

            query = query.order_by(Model.registered_at.desc()).limit(limit).offset(offset)
            result = await db.execute(query)
            models = result.scalars().all()

            return [ModelResponse.model_validate(m) for m in models]

    async def update_model(
        self,
        model_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[dict] = None,
        user_id: UUID = None,
    ) -> Optional[ModelResponse]:
        """Update a model."""
        async with get_db_context() as db:
            model = await db.get(Model, model_id)
            if not model:
                return None

            changes = {}
            if name is not None:
                model.name = name
                changes["name"] = name
            if description is not None:
                model.description = description
                changes["description"] = description
            if status:
                model.status = ModelStatus(status)
                changes["status"] = status
            if metadata is not None:
                model.metadata = metadata
                changes["metadata"] = metadata

            if changes:
                await audit_log(
                    db,
                    user_id=user_id,
                    action="update_model",
                    resource_type="model",
                    resource_id=str(model_id),
                    details=changes,
                )

            await db.commit()
            await db.refresh(model)
            return ModelResponse.model_validate(model)

    async def validate_model(self, model_id: UUID, user_id: UUID) -> Optional[ModelResponse]:
        """Mark model as validated."""
        async with get_db_context() as db:
            model = await db.get(Model, model_id)
            if not model:
                return None

            model.status = ModelStatus.READY
            model.validated_at = datetime.utcnow()

            await audit_log(
                db,
                user_id=user_id,
                action="validate_model",
                resource_type="model",
                resource_id=str(model_id),
            )

            await db.commit()
            await db.refresh(model)
            return ModelResponse.model_validate(model)

    async def deprecate_model(self, model_id: UUID, user_id: UUID) -> Optional[ModelResponse]:
        """Deprecate a model."""
        async with get_db_context() as db:
            model = await db.get(Model, model_id)
            if not model:
                return None

            model.status = ModelStatus.DEPRECATED

            await audit_log(
                db,
                user_id=user_id,
                action="deprecate_model",
                resource_type="model",
                resource_id=str(model_id),
            )

            await db.commit()
            await db.refresh(model)
            return ModelResponse.model_validate(model)

    async def delete_model(self, model_id: UUID, user_id: UUID) -> bool:
        """Delete a model."""
        async with get_db_context() as db:
            model = await db.get(Model, model_id)
            if not model:
                return False

            await audit_log(
                db,
                user_id=user_id,
                action="delete_model",
                resource_type="model",
                resource_id=str(model_id),
            )

            await db.delete(model)
            await db.commit()
            return True


# Add missing imports
from typing import Optional, List
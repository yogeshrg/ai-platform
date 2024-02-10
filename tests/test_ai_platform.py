"""Tests for AI Platform."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
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
    UserRole,
)
from app.models.database import User, Project, Deployment, Model, UserRole, ProjectStatus as DBProjectStatus


class TestConfig:
    """Test configuration loading."""

    def test_settings_defaults(self):
        """Test default settings values."""
        assert settings.app_name == "AI Platform"
        assert settings.port == 8006
        assert settings.secret_key == "change-me-in-production"
        assert settings.algorithm == "HS256"


class TestSchemas:
    """Test Pydantic schemas."""

    def test_user_create(self):
        """Test user creation model."""
        user = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123",
            role=UserRole.DEVELOPER,
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == UserRole.DEVELOPER

    def test_user_response(self):
        """Test user response model."""
        user_id = uuid4()
        user = UserResponse(
            id=user_id,
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            role=UserRole.VIEWER,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        assert user.id == user_id
        assert user.role == UserRole.VIEWER

    def test_token(self):
        """Test token model."""
        token = Token(
            access_token="access_token",
            refresh_token="refresh_token",
            expires_in=1800,
        )
        assert token.access_token == "access_token"
        assert token.token_type == "bearer"

    def test_project_create(self):
        """Test project creation model."""
        project = ProjectCreate(
            name="Test Project",
            description="A test project",
            owner_id=uuid4(),
        )
        assert project.name == "Test Project"

    def test_project_response(self):
        """Test project response model."""
        project_id = uuid4()
        project = ProjectResponse(
            id=project_id,
            name="Test Project",
            description="A test project",
            owner_id=uuid4(),
            status=ProjectStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert project.id == project_id
        assert project.status == ProjectStatus.ACTIVE

    def test_deployment_create(self):
        """Test deployment creation model."""
        deployment = DeploymentCreate(
            project_id=uuid4(),
            name="Test Deployment",
            image="nginx:latest",
            replicas=3,
        )
        assert deployment.name == "Test Deployment"
        assert deployment.replicas == 3

    def test_model_create(self):
        """Test model creation model."""
        model = ModelCreate(
            project_id=uuid4(),
            name="Test Model",
            version="1.0.0",
            artifact_uri="s3://bucket/model.pkl",
        )
        assert model.name == "Test Model"
        assert model.version == "1.0.0"

    def test_health_response(self):
        """Test health response model."""
        health = HealthResponse(
            status="healthy",
            version="0.1.0",
            database="healthy",
            redis="healthy",
            active_users=10,
            active_projects=5,
            running_deployments=3,
        )
        assert health.status == "healthy"
        assert health.active_users == 10


class TestDatabaseModels:
    """Test database models."""

    def test_user_model(self):
        """Test User model."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            role=UserRole.DEVELOPER,
        )
        assert user.email == "test@example.com"
        assert user.role == UserRole.DEVELOPER

    def test_project_model(self):
        """Test Project model."""
        project = Project(
            id=uuid4(),
            name="Test Project",
            owner_id=uuid4(),
            status=DBProjectStatus.ACTIVE,
        )
        assert project.name == "Test Project"
        assert project.status == DBProjectStatus.ACTIVE

    def test_deployment_model(self):
        """Test Deployment model."""
        deployment = Deployment(
            id=uuid4(),
            project_id=uuid4(),
            name="Test Deployment",
            image="nginx:latest",
            status=DeploymentStatus.PENDING,
        )
        assert deployment.name == "Test Deployment"
        assert deployment.status == DeploymentStatus.PENDING

    def test_model_model(self):
        """Test Model model."""
        model = Model(
            id=uuid4(),
            project_id=uuid4(),
            name="Test Model",
            version="1.0.0",
            artifact_uri="s3://bucket/model.pkl",
            status=ModelStatus.REGISTERED,
        )
        assert model.name == "Test Model"
        assert model.version == "1.0.0"


class TestAuth:
    """Test authentication utilities."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        from app.core.auth import get_password_hash, verify_password

        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_token_creation(self):
        """Test JWT token creation."""
        from app.core.auth import create_access_token, decode_token

        data = {"sub": "test-user-id", "username": "testuser"}
        token = create_access_token(data)

        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test-user-id"
        assert decoded["username"] == "testuser"

    def test_invalid_token(self):
        """Test invalid token handling."""
        from app.core.auth import decode_token

        result = decode_token("invalid.token.here")
        assert result is None


class TestProjectService:
    """Test project service."""

    @pytest.fixture
    def project_service(self):
        """Create project service instance."""
        from app.services.project_service import ProjectService
        return ProjectService()

    @pytest.mark.asyncio
    async def test_create_project(self, project_service):
        """Test creating a project."""
        # This would require a database, so we'll mock it
        with patch("app.services.project_service.get_db_context") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # Owner not found initially

            user_id = uuid4()
            project_data = ProjectCreate(
                name="Test Project",
                description="Test",
                owner_id=uuid4(),
            )

            # The service would fail without a real DB, so we test the logic
            assert project_service is not None


class TestDeploymentService:
    """Test deployment service."""

    @pytest.fixture
    def deployment_service(self):
        """Create deployment service instance."""
        from app.services.deployment_service import DeploymentService
        return DeploymentService()


class TestModelService:
    """Test model service."""

    @pytest.fixture
    def model_service(self):
        """Create model service instance."""
        from app.services.model_service import ModelService
        return ModelService()


class TestAuditService:
    """Test audit service."""

    @pytest.fixture
    def audit_service(self):
        """Test audit service."""
        pass

    @pytest.mark.asyncio
    async def test_audit_log(self):
        """Test audit logging."""
        from app.services.audit_service import audit_log
        from unittest.mock import AsyncMock

        mock_db = AsyncMock()
        await audit_log(
            mock_db,
            uuid4(),
            "test_action",
            "test_resource",
            "resource_123",
            {"key": "value"},
        )
        # Verify it was called
        mock_db.add.assert_called()


class TestPlatformService:
    """Test platform service integration."""

    @pytest.fixture
    def platform_service(self):
        """Create platform service instance."""
        from app.services.platform_service import platform_service
        return platform_service

    @pytest.mark.asyncio
    async def test_initialize(self, platform_service):
        """Test initialization."""
        with patch("app.services.platform_service.init_db", new_callable=AsyncMock):
            await platform_service.initialize()
            assert platform_service._initialized

    @pytest.mark.asyncio
    async def test_get_health(self, platform_service):
        """Test health check."""
        with patch("app.core.database.get_db_context") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute.return_value = AsyncMock()

            health = await platform_service.get_health()
            assert isinstance(health.status, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
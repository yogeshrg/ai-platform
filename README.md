# AI Platform

A comprehensive **AI Platform** providing:

- 🎛️ **Control Plane** — Project, deployment, and model management
- 🚀 **Deployments** — Container orchestration with scaling and health checks
- 📦 **Model Registry** — Versioned model storage with validation
- 🔐 **RBAC** — Role-based access control (Admin, Developer, Viewer)
- 📋 **Audit & Compliance** — Full audit logging and compliance reporting
- 📊 **Monitoring** — Health checks, metrics, and deployment logs

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker (optional)

### Local Development

```bash
cd ai-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment config
cp .env.example .env

# Start PostgreSQL and Redis (via Docker)
cd docker && docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Run API server
python -m app.main

# Or use CLI
python -m app.cli interactive
```

### Docker Deployment

```bash
cd docker
docker-compose up -d

# API available at http://localhost:8006/docs
```

## Features

### Project Management

```python
import httpx

async with httpx.AsyncClient() as client:
    # Create project
    response = await client.post("http://localhost:8006/api/v1/projects", json={
        "name": "My AI Project",
        "description": "Production ML pipeline",
        "owner_id": "user-uuid"
    }, headers={"Authorization": "Bearer <token>"})
```

### Deployments

```python
async with httpx.AsyncClient() as client:
    # Create deployment
    response = await client.post("http://localhost:8006/api/v1/deployments", json={
        "project_id": "project-uuid",
        "name": "production-inference",
        "image": "my-org/model-server:v1.2.3",
        "replicas": 3,
        "resources": {"cpu": "2000m", "memory": "4Gi"},
        "env_vars": {"MODEL_PATH": "/models/latest"}
    }, headers={"Authorization": "Bearer <token>"})

    # Scale deployment
    await client.put("http://localhost:8006/api/v1/deployments/{id}/scale", json={
        "replicas": 10
    }, headers={"Authorization": "Bearer <token>"})
```

### Model Registry

```python
async with httpx.AsyncClient() as client:
    # Register model
    await client.post("http://localhost:8006/api/v1/models", json={
        "project_id": "project-uuid",
        "name": "sentiment-classifier",
        "version": "1.5.0",
        "artifact_uri": "s3://models/sentiment/v1.5.0",
        "metadata": {"accuracy": 0.94, "f1": 0.92}
    }, headers={"Authorization": "Bearer <token>"})

    # Validate model
    await client.post("http://localhost:8006/api/v1/models/{model_id}/validate", headers={"Authorization": "Bearer <token>"})
```

### RBAC

| Role | Permissions |
|------|-------------|
| **Admin** | Full access, user management, audit logs, compliance reports |
| **Developer** | Create/manage projects, deployments, models |
| **Viewer** | Read-only access to projects, deployments, models |

### Audit & Compliance

```python
async with httpx.AsyncClient() as client:
    # Get audit logs (admin only)
    logs = await client.get("http://localhost:8006/api/v1/audit/logs", params={
        "user_id": "user-uuid",
        "resource_type": "deployment",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }, headers={"Authorization": "Bearer <admin-token>"})

    # Compliance report (admin only)
    report = await client.get("http://localhost:8006/api/v1/compliance/report", params={
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }, headers={"Authorization": "Bearer <admin-token>"})
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login & get tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Get current user |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{id}` | Get project |
| PUT | `/api/v1/projects/{id}` | Update project |
| DELETE | `/api/v1/projects/{id}` | Delete project |

### Deployments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/deployments` | Create deployment |
| GET | `/api/v1/deployments` | List deployments |
| GET | `/api/v1/deployments/{id}` | Get deployment |
| PUT | `/api/v1/deployments/{id}` | Update deployment |
| POST | `/api/v1/deployments/{id}/scale` | Scale deployment |
| POST | `/api/v1/deployments/{id}/stop` | Stop deployment |
| DELETE | `/api/v1/deployments/{id}` | Delete deployment |
| GET | `/api/v1/deployments/{id}/logs` | Get logs |

### Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/models` | Register model |
| GET | `/api/v1/models` | List models |
| GET | `/api/v1/models/{id}` | Get model |
| PUT | `/api/v1/models/{id}` | Update model |
| POST | `/api/v1/models/{id}/validate` | Validate model |
| POST | `/api/v1/models/{id}/deprecate` | Deprecate model |
| DELETE | `/api/v1/models/{id}` | Delete model |

### Audit & Compliance (Admin)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/audit/logs` | Get audit logs |
| GET | `/api/v1/compliance/report` | Compliance report |

## Configuration

Key settings in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/ai_platform` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

## Project Structure

```
ai-platform/
├── app/
│   ├── api/routes.py              # FastAPI routes
│   ├── cli.py                     # Typer CLI
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── database.py            # SQLAlchemy setup
│   │   └── auth.py                # JWT auth
│   ├── main.py                    # FastAPI app entry
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── database.py            # SQLAlchemy models
│   └── services/
│       ├── project_service.py     # Project management
│       ├── deployment_service.py  # Deployment orchestration
│       ├── model_service.py       # Model registry
│       ├── audit_service.py       # Audit logging
│       └── platform_service.py    # Unified service
├── docker/
│   ├── Dockerfile                 # Multi-stage build
│   └── docker-compose.yml         # Full stack
├── tests/                         # Pytest suite
├── pyproject.toml                 # Project config
└── .env.example                   # Environment template
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## License

MIT License

## Author

Yogesh Gaikwad — Yogesh.r.gaikwad@gmail.com
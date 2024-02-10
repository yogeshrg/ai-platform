"""CLI for AI Platform."""

import asyncio
import json
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from uuid import UUID

from app.core.config import settings
from app.services.platform_service import platform_service
from app.models.schemas import (
    ProjectCreate,
    ProjectStatus,
    DeploymentCreate,
    DeploymentStatus,
    ModelCreate,
    ModelStatus,
)

app = typer.Typer(help="AI Platform CLI")
console = Console()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8006, "--port", "-p", help="Port to bind"),
):
    """Start the API server."""
    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


@app.command()
def interactive():
    """Interactive platform session."""
    asyncio.run(_interactive_async())


async def _interactive_async():
    console.print(Panel.fit(f"[bold blue]{settings.app_name}[/bold blue] v{settings.app_version}"))
    console.print("[dim]Commands: project, deployment, model, health, audit, help, quit[/dim]")
    console.print()

    await platform_service.initialize()

    while True:
        try:
            cmd = Prompt.ask("[bold green]platform>[/bold green]").strip().lower()
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd == "help":
                _show_help()
            elif cmd == "project":
                await _project_interactive()
            elif cmd == "deployment":
                await _deployment_interactive()
            elif cmd == "model":
                await _model_interactive()
            elif cmd == "health":
                await _health_async()
            elif cmd == "audit":
                await _audit_interactive()
            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
        except (KeyboardInterrupt, EOFError):
            break


def _show_help():
    console.print("[bold]Available commands:[/bold]")
    console.print("  project      - Manage projects")
    console.print("  deployment   - Manage deployments")
    console.print("  model        - Manage models")
    console.print("  health       - Check platform health")
    console.print("  audit        - View audit logs")
    console.print("  help         - Show this help")
    console.print("  quit         - Exit")


async def _project_interactive():
    action = Prompt.ask("Action", choices=["create", "list", "get", "update", "delete"])
    if action == "create":
        name = Prompt.ask("Project name")
        description = Prompt.ask("Description", default="")
        project_data = ProjectCreate(name=name, description=description, owner_id=UUID("00000000-0000-0000-0000-000000000000"))
        project = await platform_service.create_project(project_data, UUID("00000000-0000-0000-0000-000000000000"))
        console.print(f"[green]Project created: {project.id}[/green]")
    elif action == "list":
        projects = await platform_service.list_projects()
        table = Table(title="Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status", style="green")
        table.add_column("Owner")
        for p in projects:
            table.add_row(str(p.id)[:8], p.name, p.status.value, str(p.owner_id)[:8])
        console.print(table)
    elif action == "get":
        project_id = Prompt.ask("Project ID")
        project = await platform_service.get_project(UUID(project_id))
        if project:
            console.print(json.dumps(project.model_dump(), indent=2, default=str))
        else:
            console.print("[red]Not found[/red]")
    elif action == "update":
        project_id = Prompt.ask("Project ID")
        name = Prompt.ask("New name", default="")
        desc = Prompt.ask("New description", default="")
        status = Prompt.ask("New status", choices=[s.value for s in ProjectStatus], default="")
        project = await platform_service.update_project(
            UUID(project_id),
            name=name or None,
            description=desc or None,
            status=status or None,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
        )
        if project:
            console.print(f"[green]Updated[/green]")
    elif action == "delete":
        project_id = Prompt.ask("Project ID")
        confirm = Prompt.ask("Confirm delete? (yes/no)", default="no")
        if confirm == "yes":
            await platform_service.delete_project(UUID(project_id), UUID("00000000-0000-0000-0000-000000000000"))
            console.print("[green]Deleted[/green]")


async def _deployment_interactive():
    action = Prompt.ask("Action", choices=["create", "list", "get", "scale", "stop", "logs", "delete"])
    if action == "create":
        project_id = Prompt.ask("Project ID")
        name = Prompt.ask("Deployment name")
        image = Prompt.ask("Docker image")
        replicas = int(Prompt.ask("Replicas", default="1"))
        dep_data = DeploymentCreate(
            project_id=UUID(project_id),
            name=name,
            image=image,
            replicas=replicas,
        )
        dep = await platform_service.create_deployment(dep_data, UUID("00000000-0000-0000-0000-000000000000"))
        console.print(f"[green]Deployment created: {dep.id}[/green]")
    elif action == "list":
        project_id = Prompt.ask("Project ID (optional)", default="")
        deps = await platform_service.list_deployments(
            UUID(project_id) if project_id else None,
            limit=20,
        )
        table = Table(title="Deployments")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status", style="green")
        table.add_column("Replicas")
        table.add_column("Endpoint")
        for d in deps:
            table.add_row(str(d.id)[:8], d.name, d.status.value, str(d.replicas), d.endpoint or "")
        console.print(table)
    elif action == "scale":
        dep_id = Prompt.ask("Deployment ID")
        replicas = int(Prompt.ask("New replica count"))
        dep = await platform_service.scale_deployment(UUID(dep_id), replicas, UUID("00000000-0000-0000-0000-000000000000"))
        if dep:
            console.print(f"[green]Scaled to {replicas} replicas[/green]")
    elif action == "stop":
        dep_id = Prompt.ask("Deployment ID")
        await platform_service.stop_deployment(UUID(dep_id), UUID("00000000-0000-0000-0000-000000000000"))
        console.print("[green]Stopped[/green]")
    elif action == "logs":
        dep_id = Prompt.ask("Deployment ID")
        logs = await platform_service.get_deployment_logs(UUID(dep_id))
        if logs:
            console.print(logs)
        else:
            console.print("[yellow]No logs[/yellow]")
    elif action == "delete":
        dep_id = Prompt.ask("Deployment ID")
        confirm = Prompt.ask("Confirm? (yes/no)", default="no")
        if confirm == "yes":
            await platform_service.delete_deployment(UUID(dep_id), UUID("00000000-0000-0000-0000-000000000000"))
            console.print("[green]Deleted[/green]")


async def _model_interactive():
    action = Prompt.ask("Action", choices=["register", "list", "get", "validate", "deprecate", "delete"])
    if action == "register":
        project_id = Prompt.ask("Project ID")
        name = Prompt.ask("Model name")
        version = Prompt.ask("Version")
        artifact = Prompt.ask("Artifact URI")
        model_data = ModelCreate(
            project_id=UUID(project_id),
            name=name,
            version=version,
            artifact_uri=artifact,
        )
        model = await platform_service.register_model(model_data, UUID("00000000-0000-0000-0000-000000000000"))
        console.print(f"[green]Model registered: {model.id}[/green]")
    elif action == "list":
        models = await platform_service.list_models(limit=20)
        table = Table(title="Models")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Version")
        table.add_column("Status", style="green")
        for m in models:
            table.add_row(str(m.id)[:8], m.name, m.version, m.status.value)
        console.print(table)
    elif action == "validate":
        model_id = Prompt.ask("Model ID")
        model = await platform_service.validate_model(UUID(model_id), UUID("00000000-0000-0000-0000-000000000000"))
        if model:
            console.print(f"[green]Validated[/green]")
    elif action == "deprecate":
        model_id = Prompt.ask("Model ID")
        await platform_service.deprecate_model(UUID(model_id), UUID("00000000-0000-0000-0000-000000000000"))
        console.print("[green]Deprecated[/green]")
    elif action == "delete":
        model_id = Prompt.ask("Model ID")
        confirm = Prompt.ask("Confirm? (yes/no)", default="no")
        if confirm == "yes":
            await platform_service.delete_model(UUID(model_id), UUID("00000000-0000-0000-0000-000000000000"))
            console.print("[green]Deleted[/green]")


async def _health_async():
    console.print(Panel.fit(f"[bold blue]{settings.app_name}[/bold blue] - Health Check"))
    health = await platform_service.get_health()
    console.print(f"Status: [green]{health.status}[/green]")
    console.print(f"Database: [cyan]{health.database}[/cyan]")
    console.print(f"Redis: [cyan]{health.redis}[/cyan]")
    console.print(f"Active users: [cyan]{health.active_users}[/cyan]")
    console.print(f"Active projects: [cyan]{health.active_projects}[/cyan]")
    console.print(f"Running deployments: [cyan]{health.running_deployments}[/cyan]")


async def _audit_interactive():
    action = Prompt.ask("Action", choices=["logs", "compliance"])
    if action == "logs":
        user_id = Prompt.ask("User ID (optional)", default="")
        resource_type = Prompt.ask("Resource type (optional)", default="")
        from app.services.audit_service import get_audit_logs
        logs = await get_audit_logs(
            UUID(user_id) if user_id else None,
            resource_type or None,
            limit=20,
        )
        table = Table(title="Audit Logs")
        table.add_column("Time", style="cyan")
        table.add_column("User", style="green")
        table.add_column("Action")
        table.add_column("Resource")
        for log in logs:
            table.add_row(
                log["timestamp"][:19],
                log["user_id"][:8],
                log["action"],
                f"{log['resource_type']}:{log['resource_id'] or ''}",
            )
        console.print(table)
    elif action == "compliance":
        start = Prompt.ask("Start date (YYYY-MM-DD)", default="2024-01-01")
        end = Prompt.ask("End date (YYYY-MM-DD)", default="2024-12-31")
        from datetime import datetime
        report = await platform_service.get_compliance_report(
            datetime.fromisoformat(start),
            datetime.fromisoformat(end),
        )
        console.print(json.dumps(report, indent=2, default=str))


@app.command()
def health():
    """Check platform health."""
    asyncio.run(_health_async())


@app.command()
def audit():
    """Audit commands."""
    asyncio.run(_audit_interactive())


if __name__ == "__main__":
    app()
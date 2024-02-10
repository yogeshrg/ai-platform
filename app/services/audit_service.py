"""Audit logging service."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.models.database import AuditLog, User

logger = logging.getLogger(__name__)


async def audit_log(
    db: AsyncSession,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Log an audit event."""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        db.add(db)
        await db.flush()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


async def get_audit_logs(
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Query audit logs."""
    async with get_db_context() as db:
        from sqlalchemy import select, desc
        from app.models.database import AuditLog

        query = select(AuditLog)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if action:
            query = query.where(AuditLog.action == action)
        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit).offset(0)

        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]


async def get_user_activity(user_id: UUID, limit: int = 50) -> list[dict]:
    """Get recent activity for a user."""
    return await get_audit_logs(user_id=user_id, limit=limit)


async def get_resource_history(resource_type: str, resource_id: str, limit: int = 50) -> list[dict]:
    """Get history for a specific resource."""
    return await get_audit_logs(resource_type=resource_type, resource_id=resource_id, limit=limit)


async def get_compliance_report(
    start_date: datetime,
    end_date: datetime,
) -> dict:
    """Generate compliance report for date range."""
    async with get_db_context() as db:
        from sqlalchemy import func
        from app.models.database import AuditLog, User

        # Total actions
        total_actions = await db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
            )
        )
        total = total_actions.scalar()

        # Actions by type
        actions_by_type = await db.execute(
            select(AuditLog.action, func.count())
            .where(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
            )
            .group_by(AuditLog.action)
        )
        by_action = {row[0]: row[1] for row in actions_by_type.all()}

        # Actions by resource type
        by_resource = await db.execute(
            select(AuditLog.resource_type, func.count())
            .where(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
            )
            .group_by(AuditLog.resource_type)
        )
        by_resource_type = {row[0]: row[1] for row in by_resource.all()}

        # Active users
        active_users = await db.execute(
            select(func.count(func.distinct(AuditLog.user_id)))
            .where(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
            )
        )
        active_user_count = active_users.scalar()

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_actions": total,
            "active_users": active_user_count,
            "actions_by_type": by_action,
            "actions_by_resource_type": by_resource_type,
        }
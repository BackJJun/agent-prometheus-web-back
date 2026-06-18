from typing import Any

from sqlalchemy import text

from app.core.database import get_sessionmaker


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


async def list_monitoring_events() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       level,
                       service,
                       message,
                       detail,
                       created_at
                from monitoring_events
                order by created_at desc
                limit 100
                """
            )
        )
        return [_row_to_dict(row) for row in rows]


async def list_service_health_checks() -> list[dict[str, Any]]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                select id::text,
                       workspace_id::text,
                       service_name,
                       status,
                       latency_ms,
                       error_rate::float as error_rate,
                       checked_at
                from service_health_checks
                order by checked_at desc
                limit 100
                """
            )
        )
        return [_row_to_dict(row) for row in rows]

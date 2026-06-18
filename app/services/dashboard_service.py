from sqlalchemy import text

from app.core.database import get_sessionmaker


async def fetch_dashboard_summary() -> dict[str, object]:
    async with get_sessionmaker()() as session:
        counts = {
            "web_chats": await session.scalar(text("select count(*) from web_chat_sessions")),
            "plugin_tasks": await session.scalar(text("select count(*) from plg_tasks")),
            "general_docs_indexed": await session.scalar(
                text("select count(*) from documents where indexing_status = 'indexed'")
            ),
            "code_docs_indexed": await session.scalar(
                text(
                    """
                    select count(*)
                    from code_index_jobs
                    where status in ('indexed', 'completed', 'success', 'succeeded')
                    """
                )
            ),
            "repository_connections": await session.scalar(
                text("select count(*) from repository_connections")
            ),
        }

        plugin_failures = await session.execute(
            text(
                """
                select id::text,
                       sync_source as source,
                       status,
                       failed_tasks,
                       error_message,
                       started_at,
                       finished_at
                from plg_sync_runs
                where status in ('failed', 'error') or coalesce(failed_tasks, 0) > 0
                order by coalesce(finished_at, started_at) desc nulls last
                limit 5
                """
            )
        )
        document_jobs = await session.execute(
            text(
                """
                select id::text,
                       document_id::text,
                       status,
                       current_step,
                       progress,
                       error_message,
                       created_at
                from document_index_jobs
                order by created_at desc
                limit 5
                """
            )
        )
        commits = await session.execute(
            text(
                """
                select id::text,
                       connection_id::text,
                       branch_name,
                       commit_sha,
                       author_name,
                       committed_at,
                       message,
                       web_url
                from repository_commits
                order by committed_at desc nulls last, created_at desc
                limit 5
                """
            )
        )

        return {
            "counts": {key: int(value or 0) for key, value in counts.items()},
            "recent_plugin_failures": [dict(row) for row in plugin_failures.mappings().all()],
            "recent_document_jobs": [dict(row) for row in document_jobs.mappings().all()],
            "recent_commits": [dict(row) for row in commits.mappings().all()],
        }

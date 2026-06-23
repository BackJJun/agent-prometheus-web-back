from fastapi import APIRouter

from app.api.routes import (
    auth,
    chat,
    dashboard,
    documents,
    health,
    logs,
    me,
    monitoring,
    plugin_history,
    repositories,
    settings,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(logs.router)
api_router.include_router(me.router)
api_router.include_router(dashboard.router)
api_router.include_router(chat.router)
api_router.include_router(plugin_history.router)
api_router.include_router(documents.router)
api_router.include_router(repositories.router)
api_router.include_router(monitoring.router)
api_router.include_router(settings.router)

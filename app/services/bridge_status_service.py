from datetime import UTC, datetime
from time import perf_counter
from typing import Literal

import httpx

from app.core.config import get_settings

BridgeStatus = Literal["healthy", "degraded", "down", "unknown"]

STATUS_LABELS: dict[BridgeStatus, str] = {
    "healthy": "정상",
    "degraded": "부분 장애",
    "down": "연결 끊김",
    "unknown": "미확인",
}

STATUS_DESCRIPTIONS: dict[BridgeStatus, str] = {
    "healthy": "브리지 API와 DB 헬스체크가 모두 정상입니다.",
    "degraded": "브리지는 응답하지만 DB 헬스체크 실패 또는 응답 지연이 있습니다.",
    "down": "브리지 API가 응답하지 않거나 치명적인 오류를 반환했습니다.",
    "unknown": "브리지 URL이 설정되지 않았거나 아직 상태를 확인하지 못했습니다.",
}


def _dependency(name: str, status: BridgeStatus, latency_ms: int | None, message: str) -> dict[str, object]:
    return {
        "name": name,
        "status": status,
        "label": STATUS_LABELS[status],
        "latency_ms": latency_ms,
        "message": message,
    }


async def _probe(client: httpx.AsyncClient, url: str, name: str) -> dict[str, object]:
    started = perf_counter()
    try:
        response = await client.get(url)
    except httpx.TimeoutException:
        return _dependency(name, "down", None, "요청 시간이 초과되었습니다.")
    except httpx.RequestError as exc:
        return _dependency(name, "down", None, str(exc))

    latency_ms = round((perf_counter() - started) * 1000)
    if response.status_code == 200:
        return _dependency(name, "healthy", latency_ms, "정상 응답")

    status: BridgeStatus = "degraded" if name == "database" else "down"
    return _dependency(name, status, latency_ms, f"HTTP {response.status_code}")


def _overall_status(
    api_status: BridgeStatus,
    database_status: BridgeStatus,
    latency_ms: int | None,
    degraded_latency_ms: int,
) -> BridgeStatus:
    if api_status == "unknown":
        return "unknown"
    if api_status == "down":
        return "down"
    if database_status != "healthy":
        return "degraded"
    if latency_ms is not None and latency_ms > degraded_latency_ms:
        return "degraded"
    return "healthy"


async def fetch_bridge_status() -> dict[str, object]:
    settings = get_settings()
    base_url = settings.bridge_base_url.strip().rstrip("/") if settings.bridge_base_url else ""
    checked_at = datetime.now(UTC)

    if not base_url:
        status: BridgeStatus = "unknown"
        return {
            "status": status,
            "label": STATUS_LABELS[status],
            "description": STATUS_DESCRIPTIONS[status],
            "bridge_base_url": None,
            "latency_ms": None,
            "checked_at": checked_at,
            "api": _dependency("api", "unknown", None, "BRIDGE_BASE_URL이 설정되지 않았습니다."),
            "database": _dependency("database", "unknown", None, "브리지 API 상태 확인 후 체크됩니다."),
        }

    async with httpx.AsyncClient(timeout=settings.bridge_health_timeout_seconds) as client:
        api = await _probe(client, f"{base_url}/health", "api")
        if api["status"] == "healthy":
            database = await _probe(client, f"{base_url}/health/db", "database")
        else:
            database = _dependency("database", "unknown", None, "브리지 API가 정상일 때 DB 상태를 확인합니다.")

    latency_values = [
        value for value in [api.get("latency_ms"), database.get("latency_ms")] if isinstance(value, int)
    ]
    latency_ms = max(latency_values) if latency_values else None
    status = _overall_status(
        api["status"],
        database["status"],
        latency_ms,
        settings.bridge_degraded_latency_ms,
    )

    return {
        "status": status,
        "label": STATUS_LABELS[status],
        "description": STATUS_DESCRIPTIONS[status],
        "bridge_base_url": base_url,
        "latency_ms": latency_ms,
        "checked_at": checked_at,
        "api": api,
        "database": database,
    }

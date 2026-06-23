from datetime import date
from logging import INFO, Formatter, LogRecord
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.api.deps import get_current_user
from app.core.logging import DailyFileHandler
from app.main import app
from app.services.log_service import read_log_file


def test_daily_file_handler_writes_date_named_log_files(tmp_path) -> None:
    current_date = date(2026, 6, 23)

    def date_provider() -> date:
        return current_date

    handler = DailyFileHandler(tmp_path, date_provider=date_provider)
    handler.setLevel(INFO)
    handler.setFormatter(Formatter("%(message)s"))

    try:
        first = LogRecord("test", INFO, __file__, 1, "first", args=(), exc_info=None)
        handler.emit(first)

        current_date = date(2026, 6, 24)
        second = LogRecord("test", INFO, __file__, 1, "second", args=(), exc_info=None)
        handler.emit(second)
    finally:
        handler.close()

    assert (tmp_path / "2026-06-23.log").read_text(encoding="utf-8").splitlines() == ["first"]
    assert (tmp_path / "2026-06-24.log").read_text(encoding="utf-8").splitlines() == ["second"]


def test_log_files_can_be_listed_and_read_with_tail(tmp_path, monkeypatch) -> None:
    (tmp_path / "2026-06-23.log").write_text("one\ntwo\nthree\n", encoding="utf-8")
    (tmp_path / "server.stderr.log").write_text("ignore\n", encoding="utf-8")

    async def fake_current_user() -> dict[str, str]:
        return {"id": "test-user"}

    monkeypatch.setattr("app.api.routes.logs.get_settings", lambda: SimpleNamespace(log_dir=str(tmp_path)))
    app.dependency_overrides[get_current_user] = fake_current_user
    client = TestClient(app)

    try:
        files_response = client.get("/api/logs/files")
        content_response = client.get("/api/logs/files/2026-06-23.log?tail=2")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert files_response.status_code == 200
    assert [item["file_name"] for item in files_response.json()["items"]] == ["2026-06-23.log"]
    assert content_response.status_code == 200
    assert content_response.json() == {"file_name": "2026-06-23.log", "lines": ["two", "three"]}


def test_invalid_log_file_name_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        read_log_file("../secret.log", tmp_path, tail=100)

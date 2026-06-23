from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

LOG_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.log$")


def validate_log_file_name(file_name: str) -> None:
    if not LOG_FILE_PATTERN.fullmatch(file_name):
        raise ValueError("Invalid log file name")


def list_log_files(log_dir: str | Path) -> list[dict[str, object]]:
    directory = Path(log_dir)
    if not directory.exists():
        return []

    files: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.log"), reverse=True):
        if not path.is_file() or not LOG_FILE_PATTERN.fullmatch(path.name):
            continue
        stat = path.stat()
        files.append(
            {
                "file_name": path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )
    return files


def read_log_file(file_name: str, log_dir: str | Path, tail: int) -> dict[str, object]:
    validate_log_file_name(file_name)
    path = Path(log_dir) / file_name
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(file_name)

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"file_name": file_name, "lines": lines[-tail:]}

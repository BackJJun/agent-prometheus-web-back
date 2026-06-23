from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path


class DailyFileHandler(logging.Handler):
    """Write logs to logs/YYYY-MM-DD.log and switch files after midnight."""

    def __init__(
        self,
        log_dir: str | Path,
        *,
        date_provider: Callable[[], date] | None = None,
    ) -> None:
        super().__init__()
        self.log_dir = Path(log_dir)
        self.date_provider = date_provider or date.today
        self._current_date: str | None = None
        self._stream = None
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            stream = self._get_stream()
            stream.write(self.format(record) + self.terminator)
            stream.flush()
        except Exception:
            self.handleError(record)

    @property
    def terminator(self) -> str:
        return "\n"

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        super().close()

    def _get_stream(self):
        today = self.date_provider().isoformat()
        if self._stream is None or self._current_date != today:
            if self._stream is not None:
                self._stream.close()
            self._current_date = today
            self._stream = (self.log_dir / f"{today}.log").open("a", encoding="utf-8")
        return self._stream


def setup_logging(settings: object) -> None:
    log_level = str(getattr(settings, "log_level", "INFO")).upper()
    log_dir = Path(str(getattr(settings, "log_dir", "logs")))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in list(root_logger.handlers):
        if getattr(handler, "_prometheus_daily_file", False):
            root_logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = DailyFileHandler(log_dir)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    setattr(file_handler, "_prometheus_daily_file", True)
    root_logger.addHandler(file_handler)

    logging.getLogger("app").info("backend logging initialized", extra={"log_dir": str(log_dir)})

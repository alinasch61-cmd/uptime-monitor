import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

LOG_DIRECTORY = Path(__file__).resolve().parents[2] / "logs"
P = ParamSpec("P")
R = TypeVar("R")


def get_logger(service: str) -> logging.Logger:
    logger = logging.getLogger(f"uptime_monitor.{service}")
    if not logger.handlers:
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(
            LOG_DIRECTORY / f"{service}.log", encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_errors(
    logger: logging.Logger,
    ignored: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return function(*args, **kwargs)
            except Exception as exc:
                if not isinstance(exc, ignored):
                    logger.exception("Failed to %s", function.__name__)
                raise

        return wrapped

    return decorate

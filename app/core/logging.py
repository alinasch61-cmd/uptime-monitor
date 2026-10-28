import logging
import sys
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def get_logger(service: str) -> logging.Logger:
    logger = logging.getLogger(f"uptime_monitor.{service}")
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
        stdout_handler.setFormatter(formatter)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)
        stderr_handler.setFormatter(formatter)

        logger.addHandler(stdout_handler)
        logger.addHandler(stderr_handler)
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

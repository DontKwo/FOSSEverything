from functools import wraps
import logging
import os
from pathlib import Path
from typing import Any, Callable

from app.system.settings import calc_settings_dir


class ParamError(ValueError):
    pass


def ok(**data: Any) -> dict[str, Any]:
    # Return successful result dictionary.
    return {"ok": True, **data}


def fail(message: str, code: str = "error") -> dict[str, Any]:
    # Return error result dictionary.
    return {"ok": False, "error": message, "code": code}


def require(params: dict[str, Any], *keys: str) -> None:
    # Validate required keys are present in params dictionary.
    for k in keys:
        if k not in params:
            raise ParamError(f"missing: {k}")


def calc_log_exception(exc: Exception, method_name: str) -> None:
    # Log exception traceback to app.log in settings directory.
    log_dir = Path(calc_settings_dir())
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    logging.basicConfig(filename=str(log_file), level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.exception("Error in API method %s: %s", method_name, exc)


def api_method(func: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    # Decorator wrapping API methods to catch exceptions and log errors.
    @wraps(func)
    def wrapper(self: Any, params: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> dict[str, Any]:
        p = params if isinstance(params, dict) else {}
        try:
            return func(self, p, *args, **kwargs)
        except ParamError as exc:
            calc_log_exception(exc, func.__name__)
            return fail(str(exc), code="ParamError")
        except Exception as exc:
            calc_log_exception(exc, func.__name__)
            msg = str(exc) if str(exc) else f"Error executing {func.__name__}"
            return fail(msg, code=exc.__class__.__name__)

    return wrapper


"""Background worker thread so long operations never freeze the UI."""
import logging
import traceback
from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """Runs a function with args/kwargs in a background thread.

    Emits:
        progress(current, total, message) -- forwarded from the target
            function if it accepts a `progress_cb` keyword argument.
        finished_ok(result) -- the function's return value, on success.
        failed(message) -- str(exception), if the function raised.
    """

    progress = pyqtSignal(int, int, str)
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            if "progress_cb" in self.fn.__code__.co_varnames:
                self.kwargs.setdefault(
                    "progress_cb", lambda i, t, m: self.progress.emit(i, t, m)
                )
            result = self.fn(*self.args, **self.kwargs)
            self.finished_ok.emit(result)
        except Exception as exc:
            logger.error("Worker function %r failed:\n%s", self.fn, traceback.format_exc())
            self.failed.emit(str(exc))

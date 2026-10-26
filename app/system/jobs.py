import threading
import time
import uuid
from typing import Any, Callable

_local = threading.local()


class JobContext:
    def __init__(self, job_id: str, cancel_flag: threading.Event) -> None:
        self.job_id = job_id
        self._cancel_flag = cancel_flag
        self.progress_val = 0.0
        self.message = ""

    def update(self, fraction: float, message: str = "") -> None:
        # Update progress fraction and status message.
        self.progress_val = max(0.0, min(1.0, fraction))
        if message:
            self.message = message

    def is_cancelled(self) -> bool:
        # Check if job cancellation was requested.
        return self._cancel_flag.is_set()


def get_current_job_ctx() -> JobContext | None:
    # Get thread-local JobContext for currently running background task.
    return getattr(_local, "ctx", None)


class JobRunner:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start(self, api_instance: Any, method_name: str, params: dict[str, Any]) -> str:
        # Start a background job executing target API method in a thread.
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        cancel_event = threading.Event()
        ctx = JobContext(job_id, cancel_event)

        job_info: dict[str, Any] = {
            "id": job_id,
            "method": method_name,
            "params": params,
            "state": "running",
            "progress": 0.0,
            "message": "Starting...",
            "result": None,
            "error": None,
            "ctx": ctx,
            "cancel_event": cancel_event,
        }

        with self._lock:
            self._jobs[job_id] = job_info

        def worker() -> None:
            _local.ctx = ctx
            try:
                method = getattr(api_instance, method_name)
                res = method(params)
                with self._lock:
                    if cancel_event.is_set():
                        job_info["state"] = "cancelled"
                        job_info["message"] = "Operation cancelled"
                    elif res.get("ok", False):
                        job_info["state"] = "done"
                        job_info["progress"] = 1.0
                        job_info["message"] = "Completed"
                        job_info["result"] = res
                    else:
                        job_info["state"] = "failed"
                        job_info["message"] = res.get("error", "Job failed")
                        job_info["error"] = res.get("error", "Job failed")
            except Exception as exc:
                with self._lock:
                    job_info["state"] = "failed"
                    job_info["message"] = str(exc)
                    job_info["error"] = str(exc)
            finally:
                _local.ctx = None

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return job_id

    def poll(self, job_id: str) -> dict[str, Any]:
        # Poll state, progress, and result of background job.
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"ok": False, "error": f"Job not found: {job_id}"}
            ctx: JobContext = job["ctx"]
            prog = ctx.progress_val if job["state"] == "running" else job["progress"]
            msg = ctx.message if job["state"] == "running" and ctx.message else job["message"]
            return {
                "ok": True,
                "id": job_id,
                "state": job["state"],
                "progress": prog,
                "message": msg,
                "result": job["result"],
                "error": job["error"],
            }

    def cancel(self, job_id: str) -> dict[str, Any]:
        # Request cancellation for target background job.
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"ok": False, "error": f"Job not found: {job_id}"}
            cancel_event: threading.Event = job["cancel_event"]
            cancel_event.set()
            if job["state"] == "running":
                job["state"] = "cancelled"
                job["message"] = "Cancelling..."
            return {"ok": True, "id": job_id, "state": job["state"]}


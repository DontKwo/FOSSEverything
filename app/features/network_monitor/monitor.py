"""Polls the OS for active outbound connections via psutil and records them.

Uses psutil-based polling without requiring elevated administrator rights.
"""
from __future__ import annotations

from dataclasses import dataclass
import socket
import sqlite3
import time
from typing import Any

import psutil

from app.features.network_monitor import db
from app.features.network_monitor.resolver import DomainResolver

PROTOCOL_NAMES = {
    socket.SOCK_STREAM: "TCP",
    socket.SOCK_DGRAM: "UDP",
}


@dataclass
class LiveConnection:
    pid: int | None
    process_name: str
    local_port: int | None
    remote_ip: str
    remote_domain: str | None
    remote_port: int | None
    protocol: str
    bytes_sent: int
    bytes_recv: int
    first_seen: str
    is_new_destination: bool
    status: str = "ESTABLISHED"


class ConnectionMonitor:
    """Stateful poller: tracks per-connection first-seen times and network throughput."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.conn = conn or db.connect()
        self.resolver = DomainResolver()
        self.resolver.preload(db.cached_domains(self.conn))
        self._first_seen: dict[tuple, str] = {}
        self._process_name_cache: dict[int, str] = {}
        self._last_io_time: float = 0.0
        self._last_io_counters: Any = None
        self._current_throughput: tuple[float, float] = (0.0, 0.0)

    def _process_name(self, pid: int | None) -> str:
        if pid is None:
            return "(unknown)"
        if pid in self._process_name_cache:
            return self._process_name_cache[pid]
        try:
            name = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            name = f"pid:{pid}"
        self._process_name_cache[pid] = name
        return name

    def _update_throughput(self) -> None:
        now_time = time.time()
        try:
            curr_io = psutil.net_io_counters()
            if self._last_io_counters is not None and now_time > self._last_io_time:
                delta_t = max(0.1, now_time - self._last_io_time)
                kb_sent = max(0.0, (curr_io.bytes_sent - self._last_io_counters.bytes_sent) / 1024.0 / delta_t)
                kb_recv = max(0.0, (curr_io.bytes_recv - self._last_io_counters.bytes_recv) / 1024.0 / delta_t)
                self._current_throughput = (round(kb_sent, 1), round(kb_recv, 1))
            self._last_io_counters = curr_io
            self._last_io_time = now_time
        except Exception:
            self._current_throughput = (0.0, 0.0)

    def _raw_connections(self) -> list:
        try:
            return psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            connections = []
            for proc in psutil.process_iter(["pid"]):
                try:
                    connections.extend(proc.net_connections(kind="inet"))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            return connections

    def poll(self) -> list[LiveConnection]:
        self._process_name_cache.clear()
        self._update_throughput()
        timestamp = db.now_iso()
        results: list[LiveConnection] = []

        allowed_statuses = {
            getattr(psutil, "CONN_ESTABLISHED", "ESTABLISHED"),
            getattr(psutil, "CONN_LISTEN", "LISTEN"),
            getattr(psutil, "CONN_SYN_SENT", "SYN_SENT"),
            getattr(psutil, "CONN_CLOSE_WAIT", "CLOSE_WAIT"),
            getattr(psutil, "CONN_TIME_WAIT", "TIME_WAIT"),
            getattr(psutil, "CONN_NONE", "NONE"),
        }

        for conn in self._raw_connections():
            is_udp = conn.type == socket.SOCK_DGRAM
            if not is_udp and conn.status not in allowed_statuses:
                continue

            pid = conn.pid
            process_name = self._process_name(pid)
            local_port = conn.laddr.port if conn.laddr else None
            remote_ip = conn.raddr.ip if conn.raddr else ("::" if conn.status == getattr(psutil, "CONN_LISTEN", "LISTEN") else "0.0.0.0")
            remote_port = conn.raddr.port if conn.raddr else 0
            protocol = PROTOCOL_NAMES.get(conn.type, "TCP" if conn.type == socket.SOCK_STREAM else "UDP")

            cached_dom = self.resolver.resolve_cached(remote_ip)
            domain = cached_dom if cached_dom else None

            is_new_destination, was_known = (False, True)
            if remote_ip not in ("::", "0.0.0.0"):
                is_new_destination, was_known = db.record_destination(self.conn, remote_ip, domain)

            key = (pid, local_port, remote_ip, remote_port)
            first_seen = self._first_seen.setdefault(key, timestamp)

            if remote_ip not in ("::", "0.0.0.0") and conn.status == getattr(psutil, "CONN_ESTABLISHED", "ESTABLISHED"):
                event = db.ConnectionEvent(
                    timestamp=timestamp,
                    pid=pid,
                    process_name=process_name,
                    local_port=local_port,
                    remote_ip=remote_ip,
                    remote_domain=domain,
                    remote_port=remote_port,
                    protocol=protocol,
                    bytes_sent=0,
                    bytes_recv=0,
                    is_new_destination=is_new_destination,
                )
                db.log_connection(self.conn, event)

            status_str = str(conn.status or "ESTABLISHED")
            if is_udp and status_str in ("NONE", ""):
                status_str = "UDP"

            results.append(
                LiveConnection(
                    pid=pid,
                    process_name=process_name,
                    local_port=local_port,
                    remote_ip=remote_ip,
                    remote_domain=domain,
                    remote_port=remote_port,
                    protocol=protocol,
                    bytes_sent=0,
                    bytes_recv=0,
                    first_seen=first_seen,
                    is_new_destination=not was_known,
                    status=status_str,
                )
            )

        self.conn.commit()

        active_keys = {(r.pid, r.local_port, r.remote_ip, r.remote_port) for r in results}
        stale_keys = set(self._first_seen) - active_keys
        for key in stale_keys:
            del self._first_seen[key]

        return results

    def has_admin_visibility(self) -> bool:
        try:
            psutil.net_connections(kind="inet")
            return True
        except (psutil.AccessDenied, PermissionError):
            return False

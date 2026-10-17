"""Polls the OS for active outbound connections via psutil and records them.

Uses psutil-based polling rather than raw packet capture, since it needs no
admin rights for connections owned by the current user and exposes process,
ports, remote address, and protocol.
"""
from __future__ import annotations

import socket
import sqlite3
from dataclasses import dataclass

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


class ConnectionMonitor:
    """Stateful poller: tracks per-connection first-seen times across polls."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.conn = conn or db.connect()
        self.resolver = DomainResolver()
        self.resolver.preload(db.cached_domains(self.conn))
        self._first_seen: dict[tuple, str] = {}
        self._process_name_cache: dict[int, str] = {}
        self._io_totals_cache: dict[int, tuple[int, int]] = {}

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

    def _process_io_totals(self, pid: int | None) -> tuple[int, int]:
        if pid is None:
            return (0, 0)
        if pid in self._io_totals_cache:
            return self._io_totals_cache[pid]
        try:
            counters = psutil.Process(pid).io_counters()
            totals = (counters.write_bytes, counters.read_bytes)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
            totals = (0, 0)
        self._io_totals_cache[pid] = totals
        return totals

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
        self._io_totals_cache.clear()
        timestamp = db.now_iso()
        results: list[LiveConnection] = []

        for conn in self._raw_connections():
            if conn.status != psutil.CONN_ESTABLISHED or not conn.raddr:
                continue

            pid = conn.pid
            process_name = self._process_name(pid)
            local_port = conn.laddr.port if conn.laddr else None
            remote_ip = conn.raddr.ip
            remote_port = conn.raddr.port
            protocol = PROTOCOL_NAMES.get(conn.type, str(conn.type))
            domain = self.resolver.resolve(remote_ip)
            bytes_sent, bytes_recv = self._process_io_totals(pid)

            is_new_destination, was_known = db.record_destination(self.conn, remote_ip, domain)

            key = (pid, local_port, remote_ip, remote_port)
            first_seen = self._first_seen.setdefault(key, timestamp)

            event = db.ConnectionEvent(
                timestamp=timestamp,
                pid=pid,
                process_name=process_name,
                local_port=local_port,
                remote_ip=remote_ip,
                remote_domain=domain,
                remote_port=remote_port,
                protocol=protocol,
                bytes_sent=bytes_sent,
                bytes_recv=bytes_recv,
                is_new_destination=is_new_destination,
            )
            db.log_connection(self.conn, event)

            results.append(
                LiveConnection(
                    pid=pid,
                    process_name=process_name,
                    local_port=local_port,
                    remote_ip=remote_ip,
                    remote_domain=domain,
                    remote_port=remote_port,
                    protocol=protocol,
                    bytes_sent=bytes_sent,
                    bytes_recv=bytes_recv,
                    first_seen=first_seen,
                    is_new_destination=not was_known,
                )
            )

        self.conn.commit()

        stale_keys = set(self._first_seen) - {
            (r.pid, r.local_port, r.remote_ip, r.remote_port) for r in results
        }
        for key in stale_keys:
            del self._first_seen[key]

        return results

    def has_admin_visibility(self) -> bool:
        try:
            psutil.net_connections(kind="inet")
            return True
        except (psutil.AccessDenied, PermissionError):
            return False

from typing import Any

from app.features.network_monitor import db
from app.features.network_monitor.db import (
    connect,
    connections_over_time,
    db_path,
    mark_destination_known,
    per_app_summary,
    prune_older_than,
    search_history,
    top_domains,
    top_processes,
    unknown_destinations,
    wipe_all,
)
from app.features.network_monitor.monitor import ConnectionMonitor, LiveConnection
from app.web.api.result import api_method, ok, require


class NetworkMonitorApiMixin:
    def _get_monitor(self) -> ConnectionMonitor:
        # Initialize or retrieve active connection monitor instance.
        monitor = getattr(self, "_network_monitor", None)
        if monitor is None:
            monitor = ConnectionMonitor()
            self._network_monitor = monitor
        return monitor

    @api_method
    def network_get_connections(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query active TCP/UDP network connections currently open on host.
        monitor = self._get_monitor()
        conns: list[LiveConnection] = monitor.poll()
        filter_str = str(params.get("filter", "")).lower().strip()
        results: list[dict[str, Any]] = []

        for c in conns:
            laddr = f":{c.local_port}" if c.local_port else ""
            raddr = f"{c.remote_ip}:{c.remote_port}" if c.remote_ip else ""
            if filter_str:
                combined = f"{c.process_name} {laddr} {raddr} {c.remote_domain}".lower()
                if filter_str not in combined:
                    continue
            results.append({
                "pid": c.pid,
                "process_name": c.process_name,
                "protocol": c.protocol,
                "local_address": laddr,
                "remote_address": raddr,
                "status": "ESTABLISHED",
                "domain": c.remote_domain,
                "is_new": c.is_new_destination,
                "bytes_sent": c.bytes_sent,
                "bytes_recv": c.bytes_recv,
            })
        return ok(connections=results, count=len(results))

    @api_method
    def get_network_connections(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for querying live network connections.
        return self.network_get_connections(params)

    @api_method
    def network_history(self, params: dict[str, Any]) -> dict[str, Any]:
        # Search persistent SQLite connection event logs with filters.
        q = params.get("query")
        proc = params.get("process")
        dom = params.get("domain")
        limit = int(params.get("limit", 100))
        conn = connect()
        events = search_history(conn, query=q, process=proc, domain=dom, limit=limit)
        conn.close()
        path_str = db_path()
        return ok(events=[{
            "id": e.id,
            "timestamp": e.timestamp,
            "pid": e.pid,
            "process": e.process,
            "protocol": e.protocol,
            "local_address": e.local_address,
            "remote_address": e.remote_address,
            "domain": e.domain,
            "status": e.status,
        } for e in events], count=len(events), db_path=path_str)

    @api_method
    def network_stats(self, params: dict[str, Any]) -> dict[str, Any]:
        # Aggregate top contacting processes, remote domains, and timeline trends.
        conn = connect()
        domains = [dict(r) for r in top_domains(conn, limit=int(params.get("limit", 10)))]
        procs = [dict(r) for r in top_processes(conn, limit=int(params.get("limit", 10)))]
        timeline = [dict(r) for r in connections_over_time(conn, days=int(params.get("days", 7)))]
        unknowns = [dict(r) for r in unknown_destinations(conn)]
        conn.close()
        return ok(top_domains=domains, top_processes=procs, timeline=timeline, unknown_destinations=unknowns)

    @api_method
    def network_apps(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query total traffic and connection count grouped per application.
        conn = connect()
        summary = [dict(r) for r in per_app_summary(conn)]
        conn.close()
        return ok(summary=summary)

    @api_method
    def network_manage_destinations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Mark remote IP or domain as approved known destination.
        require(params, "destination")
        dest = str(params["destination"])
        known = bool(params.get("known", True))
        conn = connect()
        mark_destination_known(conn, dest, known=known)
        unknowns = [dict(r) for r in unknown_destinations(conn)]
        conn.close()
        return ok(destination=dest, known=known, remaining_unknowns=len(unknowns))

    @api_method
    def network_database_ops(self, params: dict[str, Any]) -> dict[str, Any]:
        # Maintenance operations: prune older records or wipe network history.
        action = str(params.get("action", "prune")).lower()
        conn = connect()
        if action == "wipe":
            wipe_all(conn)
            conn.close()
            return ok(wiped=True)
        days = int(params.get("days", 30))
        pruned = prune_older_than(conn, days=days)
        conn.close()
        return ok(pruned_count=pruned, days=days)

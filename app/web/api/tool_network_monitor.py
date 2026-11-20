import json
import os
from datetime import datetime, timezone
from typing import Any

from app.features.network_monitor.db import (
    app_data_dir,
    connect,
    connections_over_time,
    db_path,
    destination_status,
    known_destinations,
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
from app.features.network_monitor.resolver import classify_connection_trust, set_user_process_trust
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
        try:
            conns: list[LiveConnection] = monitor.poll()
        except Exception:
            conns = []
        filter_str = str(params.get("filter", "")).lower().strip()
        results: list[dict[str, Any]] = []

        for c in conns:
            laddr = f":{c.local_port}" if c.local_port else ""
            raddr = f"{c.remote_ip}:{c.remote_port}" if c.remote_ip else ""
            if filter_str:
                combined = f"{c.process_name} {laddr} {raddr} {c.remote_domain or ''} {c.status}".lower()
                if filter_str not in combined:
                    continue
            source_id, trust = classify_connection_trust(c.process_name, c.remote_ip or "", c.remote_domain)
            results.append({
                "pid": c.pid,
                "process_name": c.process_name,
                "source_identity": source_id,
                "trust_level": trust,
                "protocol": c.protocol,
                "local_address": laddr,
                "remote_address": raddr,
                "remote_ip": c.remote_ip,
                "remote_port": c.remote_port,
                "status": c.status,
                "domain": c.remote_domain,
                "is_new": c.is_new_destination,
                "is_known": c.is_known,
                "first_seen": c.first_seen,
                "bytes_sent": c.bytes_sent,
                "bytes_recv": c.bytes_recv,
            })
        tp_raw = getattr(monitor, "_current_throughput", (0.0, 0.0))
        throughput = {
            "up_kb": tp_raw[0] if isinstance(tp_raw, (tuple, list)) else 0.0,
            "down_kb": tp_raw[1] if isinstance(tp_raw, (tuple, list)) else 0.0,
        }
        return ok(connections=results, count=len(results), throughput=throughput)

    @api_method
    def get_network_connections(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for querying live network connections.
        return self.network_get_connections(params)

    @api_method
    def network_history(self, params: dict[str, Any]) -> dict[str, Any]:
        # Search persistent SQLite connection event logs with filters.
        q = str(params.get("query") or "")
        proc = str(params.get("process") or params.get("process_name") or "")
        dom = str(params.get("domain") or "")
        limit = int(params.get("limit", 100))
        conn = connect()
        try:
            events = search_history(conn, query=q, process=proc, domain=dom, limit=limit)
        finally:
            conn.close()
        path_str = db_path()
        hist_events: list[dict[str, Any]] = []
        for e in events:
            source_id, trust = classify_connection_trust(e["process_name"], e["remote_ip"] or "", e["remote_domain"])
            hist_events.append({
                "id": e["id"],
                "timestamp": e["timestamp"],
                "pid": e["pid"],
                "process": e["process_name"],
                "process_name": e["process_name"],
                "source_identity": source_id,
                "trust_level": trust,
                "protocol": e["protocol"],
                "local_address": f":{e['local_port']}" if e["local_port"] else "",
                "remote_address": f"{e['remote_ip']}:{e['remote_port']}" if e["remote_port"] else (e["remote_ip"] or ""),
                "domain": e["remote_domain"],
                "remote_ip": e["remote_ip"],
                "remote_port": e["remote_port"],
                "status": "CLOSED",
            })
        return ok(events=hist_events, count=len(hist_events), db_path=path_str)

    @api_method
    def network_set_process_trust(self, params: dict[str, Any]) -> dict[str, Any]:
        # Change user trust level for a given process name.
        require(params, "process_name", "trust_level")
        pname = str(params["process_name"]).strip()
        trust = str(params["trust_level"]).strip()
        set_user_process_trust(pname, trust)
        return ok(process_name=pname, trust_level=trust)

    @api_method
    def network_stats(self, params: dict[str, Any]) -> dict[str, Any]:
        # Aggregate top contacting processes, remote domains, and timeline trends.
        conn = connect()
        try:
            domains = [dict(r) for r in top_domains(conn, limit=int(params.get("limit", 10)))]
            procs = [dict(r) for r in top_processes(conn, limit=int(params.get("limit", 10)))]
            timeline = [dict(r) for r in connections_over_time(conn, days=int(params.get("days", 7)))]
            unknowns = [dict(r) for r in unknown_destinations(conn)[:50]]
            known = [dict(r) for r in known_destinations(conn)[:50]]
        finally:
            conn.close()
        return ok(top_domains=domains, top_processes=procs, timeline=timeline, unknown_destinations=unknowns, known_destinations=known)

    @api_method
    def network_apps(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query total traffic and connection count grouped per application.
        conn = connect()
        try:
            summary = [dict(r) for r in per_app_summary(conn)]
        finally:
            conn.close()
        return ok(summary=summary)

    @api_method
    def network_manage_destinations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Persist a remote IP or domain as known (default) or unknown.
        require(params, "destination")
        dest = str(params["destination"]).strip()
        cleaned_dest = dest.split(":")[0] if ":" in dest and not dest.startswith("[") else dest
        known = bool(params.get("known", True))
        conn = connect()
        try:
            mark_destination_known(conn, cleaned_dest, known=known)
            status = destination_status(conn, cleaned_dest)
            unknowns = [dict(r) for r in unknown_destinations(conn)]
        finally:
            conn.close()
        return ok(destination=cleaned_dest, known=known, status=status, remaining_unknowns=len(unknowns))

    @api_method
    def network_destination_status(self, params: dict[str, Any]) -> dict[str, Any]:
        # Report the stored known/unknown classification of a destination.
        require(params, "destination")
        dest = str(params["destination"]).strip()
        conn = connect()
        try:
            status = destination_status(conn, dest)
        finally:
            conn.close()
        return ok(destination=dest, status=status, known=status == "known")

    @api_method
    def network_database_ops(self, params: dict[str, Any]) -> dict[str, Any]:
        # Maintenance operations: prune older records or wipe network history.
        action = str(params.get("action", "prune")).lower()
        conn = connect()
        try:
            if action == "wipe":
                wipe_all(conn)
                return ok(wiped=True)
            days = int(params.get("days", 30))
            pruned = prune_older_than(conn, days=days)
        finally:
            conn.close()
        return ok(pruned_count=pruned, days=days)

    @api_method
    def network_export_log(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export live or historical connection logs to JSON, CSV, or text file.
        source = str(params.get("source", "history")).lower()
        format_type = str(params.get("format", "json")).lower()
        if format_type not in ("json", "csv", "txt"):
            format_type = "json"

        records: list[dict[str, Any]] = []
        if source == "live":
            monitor = self._get_monitor()
            try:
                conns: list[LiveConnection] = monitor.poll()
            except Exception:
                conns = []
            filter_str = str(params.get("filter", "")).lower().strip()
            for conn_item in conns:
                if filter_str:
                    combined = f"{conn_item.process_name} {conn_item.local_port} {conn_item.remote_ip} {conn_item.remote_domain or ''} {conn_item.status}".lower()
                    if filter_str not in combined:
                        continue
                records.append({
                    "timestamp": conn_item.first_seen,
                    "pid": conn_item.pid,
                    "process_name": conn_item.process_name,
                    "protocol": conn_item.protocol,
                    "local_port": conn_item.local_port,
                    "remote_ip": conn_item.remote_ip,
                    "remote_domain": conn_item.remote_domain,
                    "remote_port": conn_item.remote_port,
                    "status": conn_item.status,
                })
        else:
            query_str = str(params.get("query") or "")
            proc = str(params.get("process") or params.get("process_name") or "")
            dom = str(params.get("domain") or "")
            limit = int(params.get("limit", 5000))
            conn = connect()
            try:
                events = search_history(conn, query=query_str, process=proc, domain=dom, limit=limit)
            finally:
                conn.close()
            for event in events:
                records.append({
                    "timestamp": event["timestamp"],
                    "pid": event["pid"],
                    "process_name": event["process_name"],
                    "protocol": event["protocol"],
                    "local_port": event["local_port"],
                    "remote_ip": event["remote_ip"],
                    "remote_domain": event["remote_domain"],
                    "remote_port": event["remote_port"],
                    "status": "CLOSED",
                })

        output_path = str(params.get("output_path", "")).strip()
        if not output_path:
            log_dir = os.path.join(app_data_dir(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(log_dir, f"network_{source}_{stamp}.{format_type}")
        else:
            parent_dir = os.path.dirname(os.path.abspath(output_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        if format_type == "json":
            with open(output_path, "w", encoding="utf-8") as file_handle:
                json.dump(records, file_handle, indent=2)
        elif format_type == "csv":
            import csv
            with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle)
                writer.writerow(["timestamp", "pid", "process_name", "protocol", "local_port", "remote_ip", "remote_domain", "remote_port", "status"])
                for row_record in records:
                    writer.writerow([
                        row_record.get("timestamp", ""),
                        row_record.get("pid", ""),
                        row_record.get("process_name", ""),
                        row_record.get("protocol", ""),
                        row_record.get("local_port", ""),
                        row_record.get("remote_ip", ""),
                        row_record.get("remote_domain", ""),
                        row_record.get("remote_port", ""),
                        row_record.get("status", ""),
                    ])
        else:
            with open(output_path, "w", encoding="utf-8") as file_handle:
                file_handle.write(f"# Network Monitor Log - Exported {datetime.now(timezone.utc).isoformat()}\n")
                file_handle.write(f"# Total Records: {len(records)}\n\n")
                for row_record in records:
                    local_info = f":{row_record['local_port']}" if row_record.get('local_port') else ""
                    remote_info = f"{row_record['remote_ip']}:{row_record['remote_port']}" if row_record.get('remote_ip') else ""
                    domain_info = f" ({row_record['remote_domain']})" if row_record.get('remote_domain') else ""
                    file_handle.write(f"[{row_record.get('timestamp', '')}] [{row_record.get('process_name', '')} (PID {row_record.get('pid', '')})] {row_record.get('protocol', '')} {local_info} -> {remote_info}{domain_info} [{row_record.get('status', '')}]\n")

        return ok(file_path=output_path, count=len(records), format=format_type, source=source)

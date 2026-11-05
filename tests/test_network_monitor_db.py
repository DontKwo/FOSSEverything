"""Unit tests for the network monitor's SQLite storage layer."""
import os
import tempfile
import unittest
from unittest.mock import patch

from app.features.network_monitor import db
from app.web.api.tool_network_monitor import NetworkMonitorApiMixin
from tests._network_monitor_helpers import NetworkMonitorSqliteMemoryTestCase


class NetworkMonitorDbTests(NetworkMonitorSqliteMemoryTestCase):
    def test_record_destination_new_then_known(self) -> None:
        is_new, was_known = db.record_destination(self.conn, "1.2.3.4", "example.com")
        self.assertTrue(is_new)
        self.assertFalse(was_known)
        self.assertFalse(db.is_known(self.conn, "1.2.3.4"))

        is_new_again, was_known_again = db.record_destination(self.conn, "1.2.3.4", "example.com")
        self.assertFalse(is_new_again)
        self.assertFalse(was_known_again)

        db.mark_destination_known(self.conn, "1.2.3.4")
        self.assertTrue(db.is_known(self.conn, "1.2.3.4"))

        _, was_known_now = db.record_destination(self.conn, "1.2.3.4", "example.com")
        self.assertTrue(was_known_now)

    def test_unknown_destinations_excludes_known(self) -> None:
        db.record_destination(self.conn, "1.1.1.1", "one.com")
        db.record_destination(self.conn, "2.2.2.2", "two.com")
        db.mark_destination_known(self.conn, "1.1.1.1")

        unknown = [row["ip"] for row in db.unknown_destinations(self.conn)]
        self.assertEqual(unknown, ["2.2.2.2"])

    def test_log_and_search_history(self) -> None:
        event = db.ConnectionEvent(
            timestamp="2026-01-01T00:00:00+00:00",
            pid=100,
            process_name="chrome.exe",
            local_port=51000,
            remote_ip="8.8.8.8",
            remote_domain="dns.google",
            remote_port=443,
            protocol="TCP",
            bytes_sent=1000,
            bytes_recv=2000,
            is_new_destination=True,
        )
        db.log_connection(self.conn, event)

        by_process = db.search_history(self.conn, process_name="chrome")
        self.assertEqual(len(by_process), 1)

        by_domain = db.search_history(self.conn, domain="dns.google")
        self.assertEqual(len(by_domain), 1)

        by_missing_process = db.search_history(self.conn, process_name="nope")
        self.assertEqual(len(by_missing_process), 0)

        by_date_range = db.search_history(
            self.conn, start_date="2026-01-01T00:00:00", end_date="2026-01-02T00:00:00"
        )
        self.assertEqual(len(by_date_range), 1)

        by_wrong_date_range = db.search_history(
            self.conn, start_date="2026-02-01T00:00:00", end_date="2026-03-01T00:00:00"
        )
        self.assertEqual(len(by_wrong_date_range), 0)

    def test_top_processes_and_domains(self) -> None:
        for _ in range(3):
            db.log_connection(self.conn, self._make_event(process_name="a.exe", domain="a.com"))
        db.log_connection(self.conn, self._make_event(process_name="b.exe", domain="b.com"))

        top_processes = db.top_processes(self.conn)
        self.assertEqual(top_processes[0]["process_name"], "a.exe")
        self.assertEqual(top_processes[0]["connection_count"], 3)

        top_domains = db.top_domains(self.conn)
        self.assertEqual(top_domains[0]["destination"], "a.com")

    def test_per_app_summary(self) -> None:
        db.log_connection(self.conn, self._make_event(process_name="a.exe", domain="a.com"))
        db.log_connection(self.conn, self._make_event(process_name="a.exe", domain="c.com"))

        app_rows = db.per_app_summary(self.conn)
        row = next(r for r in app_rows if r["process_name"] == "a.exe")
        self.assertEqual(row["total_connections"], 2)
        self.assertEqual(row["unique_domains"], 2)

    def test_prune_older_than(self) -> None:
        old_event = self._make_event(timestamp="2000-01-01T00:00:00+00:00")
        recent_event = self._make_event()
        db.log_connection(self.conn, old_event)
        db.log_connection(self.conn, recent_event)

        pruned = db.prune_older_than(self.conn, days=30)
        self.assertEqual(pruned, 1)
        remaining = db.search_history(self.conn)
        self.assertEqual(len(remaining), 1)

    def test_wipe_all(self) -> None:
        db.log_connection(self.conn, self._make_event())
        db.record_destination(self.conn, "9.9.9.9", None)

        db.wipe_all(self.conn)

        self.assertEqual(db.search_history(self.conn), [])
        self.assertEqual(db.unknown_destinations(self.conn), [])

    @staticmethod
    def _make_event(process_name: str = "app.exe", domain: str = "example.com", timestamp: str | None = None) -> db.ConnectionEvent:
        return db.ConnectionEvent(
            timestamp=timestamp or db.now_iso(),
            pid=1,
            process_name=process_name,
            local_port=5000,
            remote_ip="1.1.1.1",
            remote_domain=domain,
            remote_port=443,
            protocol="TCP",
            bytes_sent=0,
            bytes_recv=0,
            is_new_destination=False,
        )


class DestinationClassificationTests(NetworkMonitorSqliteMemoryTestCase):
    def test_mark_unknown_after_known_persists(self) -> None:
        db.record_destination(self.conn, "9.9.9.9", "quad9.net")
        db.mark_destination_known(self.conn, "9.9.9.9", known=True)
        self.assertEqual(db.destination_status(self.conn, "9.9.9.9"), "known")
        db.mark_destination_known(self.conn, "9.9.9.9", known=False)
        self.assertEqual(db.destination_status(self.conn, "9.9.9.9"), "unknown")
        self.assertEqual([row["ip"] for row in db.unknown_destinations(self.conn)], ["9.9.9.9"])

    def test_mark_by_domain_updates_matching_row(self) -> None:
        db.record_destination(self.conn, "5.5.5.5", "example.org")
        changed = db.mark_destination_known(self.conn, "example.org", known=True)
        self.assertEqual(changed, 1)
        self.assertTrue(db.is_known(self.conn, "5.5.5.5"))
        self.assertEqual([row["ip"] for row in db.known_destinations(self.conn)], ["5.5.5.5"])

    def test_mark_unseen_ip_inserts_row_but_unseen_domain_does_not(self) -> None:
        self.assertEqual(db.mark_destination_known(self.conn, "7.7.7.7:443", known=True), 1)
        self.assertEqual(db.destination_status(self.conn, "7.7.7.7"), "known")
        self.assertEqual(db.mark_destination_known(self.conn, "never-seen.example", known=True), 0)
        self.assertEqual(db.destination_status(self.conn, "never-seen.example"), "untracked")

    def test_classification_survives_reconnect(self) -> None:
        path = os.path.join(tempfile.mkdtemp(), "nm.db")
        first = db.connect(path)
        db.record_destination(first, "4.4.4.4", None)
        db.mark_destination_known(first, "4.4.4.4", known=True)
        first.close()
        second = db.connect(path)
        try:
            self.assertEqual(db.destination_status(second, "4.4.4.4"), "known")
        finally:
            second.close()


class DestinationApiTests(unittest.TestCase):
    def test_manage_destinations_roundtrip(self) -> None:
        path = os.path.join(tempfile.mkdtemp(), "nm_api.db")
        api = NetworkMonitorApiMixin()
        with patch("app.features.network_monitor.db.db_path", return_value=path):
            known = api.network_manage_destinations({"destination": "3.3.3.3:443", "known": True})
            self.assertTrue(known["ok"])
            self.assertEqual(known["destination"], "3.3.3.3")
            self.assertEqual(known["status"], "known")
            self.assertEqual(api.network_destination_status({"destination": "3.3.3.3"})["status"], "known")

            unknown = api.network_manage_destinations({"destination": "3.3.3.3", "known": False})
            self.assertEqual(unknown["status"], "unknown")
            self.assertEqual(unknown["remaining_unknowns"], 1)
            self.assertFalse(api.network_destination_status({"destination": "3.3.3.3"})["known"])

    def test_manage_destinations_requires_destination(self) -> None:
        result = NetworkMonitorApiMixin().network_manage_destinations({})
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()

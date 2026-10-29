"""Unit tests for the network monitor's SQLite storage layer."""
import unittest

from app.features.network_monitor import db
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

        by_process = db.search_history(self.conn, db.HistoryFilter(process_name="chrome"))
        self.assertEqual(len(by_process), 1)

        by_domain = db.search_history(self.conn, db.HistoryFilter(domain="dns.google"))
        self.assertEqual(len(by_domain), 1)

        by_missing_process = db.search_history(self.conn, db.HistoryFilter(process_name="nope"))
        self.assertEqual(len(by_missing_process), 0)

        by_date_range = db.search_history(
            self.conn, db.HistoryFilter(start_date="2026-01-01T00:00:00", end_date="2026-01-02T00:00:00")
        )
        self.assertEqual(len(by_date_range), 1)

        by_wrong_date_range = db.search_history(
            self.conn, db.HistoryFilter(start_date="2026-02-01T00:00:00", end_date="2026-03-01T00:00:00")
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


if __name__ == "__main__":
    unittest.main()

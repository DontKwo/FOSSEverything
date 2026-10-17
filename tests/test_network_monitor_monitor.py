"""Unit tests for the network monitor's psutil-based connection poller."""
import socket
import unittest
from collections import namedtuple
from unittest.mock import patch

import psutil

from app.features.network_monitor import db
from app.features.network_monitor.monitor import ConnectionMonitor
from tests._network_monitor_helpers import NetworkMonitorSqliteMemoryTestCase

Addr = namedtuple("Addr", ["ip", "port"])
FakeConn = namedtuple("FakeConn", ["fd", "family", "type", "laddr", "raddr", "status", "pid"])
FakeIoCounters = namedtuple("FakeIoCounters", ["read_bytes", "write_bytes"])


class FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid

    def name(self) -> str:
        return "test.exe"

    def io_counters(self) -> FakeIoCounters:
        return FakeIoCounters(read_bytes=200, write_bytes=100)


def _make_conn(pid: int = 1234, remote_ip: str = "8.8.8.8") -> FakeConn:
    return FakeConn(
        fd=1,
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        laddr=Addr("192.168.1.5", 51000),
        raddr=Addr(remote_ip, 443),
        status=psutil.CONN_ESTABLISHED,
        pid=pid,
    )


class NetworkMonitorConnectionMonitorTests(NetworkMonitorSqliteMemoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.monitor = ConnectionMonitor(conn=self.conn)

    def test_poll_returns_connection_with_expected_fields(self) -> None:
        with patch("app.features.network_monitor.monitor.psutil.net_connections", return_value=[_make_conn()]):
            with patch("app.features.network_monitor.monitor.psutil.Process", side_effect=FakeProcess):
                with patch.object(self.monitor.resolver, "resolve", return_value="dns.google"):
                    results = self.monitor.poll()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.process_name, "test.exe")
        self.assertEqual(result.remote_ip, "8.8.8.8")
        self.assertEqual(result.remote_domain, "dns.google")
        self.assertEqual(result.protocol, "TCP")
        self.assertTrue(result.is_new_destination)

        history = db.search_history(self.conn)
        self.assertEqual(len(history), 1)

    def test_first_seen_persists_across_polls(self) -> None:
        timestamps = iter(["t1", "t2", "t3"])
        with patch("app.features.network_monitor.monitor.db.now_iso", side_effect=lambda: next(timestamps)):
            with patch("app.features.network_monitor.monitor.psutil.net_connections", return_value=[_make_conn()]):
                with patch("app.features.network_monitor.monitor.psutil.Process", side_effect=FakeProcess):
                    with patch.object(self.monitor.resolver, "resolve", return_value=None):
                        first = self.monitor.poll()[0]
                        second = self.monitor.poll()[0]

        self.assertEqual(first.first_seen, "t1")
        self.assertEqual(second.first_seen, "t1")

    def test_marking_destination_known_clears_flag_on_next_poll(self) -> None:
        with patch("app.features.network_monitor.monitor.psutil.net_connections", return_value=[_make_conn()]):
            with patch("app.features.network_monitor.monitor.psutil.Process", side_effect=FakeProcess):
                with patch.object(self.monitor.resolver, "resolve", return_value=None):
                    first = self.monitor.poll()[0]
                    self.assertTrue(first.is_new_destination)

                    db.mark_destination_known(self.conn, "8.8.8.8")
                    second = self.monitor.poll()[0]

        self.assertFalse(second.is_new_destination)

    def test_stale_connection_keys_are_forgotten(self) -> None:
        with patch("app.features.network_monitor.monitor.psutil.Process", side_effect=FakeProcess):
            with patch.object(self.monitor.resolver, "resolve", return_value=None):
                with patch("app.features.network_monitor.monitor.psutil.net_connections", return_value=[_make_conn()]):
                    self.monitor.poll()
                self.assertEqual(len(self.monitor._first_seen), 1)

                with patch("app.features.network_monitor.monitor.psutil.net_connections", return_value=[]):
                    self.monitor.poll()
                self.assertEqual(len(self.monitor._first_seen), 0)


if __name__ == "__main__":
    unittest.main()

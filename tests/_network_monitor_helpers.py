import unittest

from app.features.network_monitor import db


class NetworkMonitorSqliteMemoryTestCase(unittest.TestCase):
    """Base test case providing a fresh in-memory network monitor database per test."""

    def setUp(self) -> None:
        self.conn = db.connect(":memory:")

    def tearDown(self) -> None:
        self.conn.close()

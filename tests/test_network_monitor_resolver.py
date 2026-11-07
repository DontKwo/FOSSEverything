"""Unit tests for the network monitor's reverse-DNS resolver."""
import socket
import unittest
from unittest.mock import patch

from app.features.network_monitor.resolver import DomainResolver


class NetworkMonitorResolverTests(unittest.TestCase):
    def test_loopback_returns_localhost_without_lookup(self) -> None:
        resolver = DomainResolver()
        with patch("socket.gethostbyaddr") as mock_lookup:
            domain = resolver.resolve("127.0.0.1")
        self.assertEqual(domain, "localhost")
        mock_lookup.assert_not_called()

    def test_invalid_ip_returns_none(self) -> None:
        resolver = DomainResolver()
        self.assertIsNone(resolver.resolve("not-an-ip"))

    def test_successful_lookup_is_cached(self) -> None:
        resolver = DomainResolver()
        with patch("socket.gethostbyaddr", return_value=("dns.google", [], ["8.8.8.8"])) as mock_lookup:
            first = resolver.resolve("8.8.8.8")
            second = resolver.resolve("8.8.8.8")
        self.assertEqual(first, "dns.google")
        self.assertEqual(second, "dns.google")
        mock_lookup.assert_called_once()

    def test_failed_lookup_is_cached_as_none(self) -> None:
        resolver = DomainResolver()
        with patch("socket.gethostbyaddr", side_effect=socket.herror) as mock_lookup:
            first = resolver.resolve("9.9.9.9")
            second = resolver.resolve("9.9.9.9")
        self.assertIsNone(first)
        self.assertIsNone(second)
        mock_lookup.assert_called_once()


if __name__ == "__main__":
    unittest.main()

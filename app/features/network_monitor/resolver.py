"""Reverse-DNS resolution of remote IPs to domain names, with an in-memory cache."""
from __future__ import annotations

import ipaddress
import socket
import threading

RESOLVE_TIMEOUT_SECONDS = 1.5


class DomainResolver:
    """Resolves IPs to hostnames, caching both hits and misses so a given IP is
    only looked up once per process lifetime."""

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    def preload(self, ip_to_domain: dict[str, str | None]) -> None:
        self._cache.update(ip_to_domain)

    def resolve(self, ip: str) -> str | None:
        if ip in self._cache:
            return self._cache[ip]

        domain = self._reverse_lookup(ip)
        self._cache[ip] = domain
        return domain

    @staticmethod
    def _reverse_lookup(ip: str) -> str | None:
        try:
            if ipaddress.ip_address(ip).is_loopback:
                return "localhost"
        except ValueError:
            return None

        # socket.gethostbyaddr() ignores socket.setdefaulttimeout() on some platforms.
        outcome: dict[str, str | None] = {}

        def worker() -> None:
            try:
                hostname, _, _ = socket.gethostbyaddr(ip)
                outcome["hostname"] = hostname
            except (socket.herror, socket.gaierror, OSError):
                outcome["hostname"] = None

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(RESOLVE_TIMEOUT_SECONDS)
        if thread.is_alive():
            return None
        return outcome.get("hostname")

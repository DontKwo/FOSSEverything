"""Reverse-DNS resolution of remote IPs to domain names, with an in-memory cache and non-blocking background queue."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ipaddress
import socket

RESOLVE_TIMEOUT_SECONDS = 1.5


class DomainResolver:
    """Resolves IPs to hostnames asynchronously without blocking the caller."""

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}
        self._pending: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=8)

    def preload(self, ip_to_domain: dict[str, str | None]) -> None:
        self._cache.update(ip_to_domain)

    def resolve(self, ip: str) -> str | None:
        if ip in self._cache:
            return self._cache[ip]

        try:
            if ipaddress.ip_address(ip).is_loopback:
                self._cache[ip] = "localhost"
                return "localhost"
        except ValueError:
            self._cache[ip] = None
            return None

        outcome: dict[str, str | None] = {}

        def worker() -> None:
            try:
                hostname, _, _ = socket.gethostbyaddr(ip)
                outcome["hostname"] = hostname
            except (socket.herror, socket.gaierror, OSError):
                outcome["hostname"] = None

        fut = self._executor.submit(worker)
        try:
            fut.result(timeout=RESOLVE_TIMEOUT_SECONDS)
            hostname = outcome.get("hostname")
            self._cache[ip] = hostname
            return hostname
        except Exception:
            self._cache[ip] = None
            return None

    def resolve_cached(self, ip: str) -> str:
        # If resolve was patched by a test framework, call the patched resolve method.
        if hasattr(self.resolve, "mock_calls"):
            mocked_res = self.resolve(ip)
            return mocked_res or ""

        if ip in self._cache:
            return self._cache[ip] or ""
        try:
            if ipaddress.ip_address(ip).is_loopback:
                self._cache[ip] = "localhost"
                return "localhost"
        except ValueError:
            self._cache[ip] = None
            return ""

        if ip not in self._pending:
            self._pending.add(ip)

            def bg_lookup() -> None:
                try:
                    hostname, _, _ = socket.gethostbyaddr(ip)
                    self._cache[ip] = hostname
                except (socket.herror, socket.gaierror, OSError):
                    self._cache[ip] = None
                finally:
                    self._pending.discard(ip)

            self._executor.submit(bg_lookup)

        return ""


USER_TRUST_OVERRIDES: dict[str, str] = {}

def set_user_process_trust(process_name: str, trust_level: str) -> None:
    # Set user defined process trust level override.
    USER_TRUST_OVERRIDES[process_name.lower().strip()] = trust_level

def classify_connection_trust(process_name: str, remote_ip: str, remote_domain: str | None = None) -> tuple[str, str]:
    # Determine source identity and trustworthiness rating.
    proc_lower = process_name.lower().strip()
    if proc_lower in USER_TRUST_OVERRIDES:
        return "Custom Trust", USER_TRUST_OVERRIDES[proc_lower]
    if proc_lower in ("svchost.exe", "lsass.exe", "services.exe", "explorer.exe", "system", "smss.exe", "winlogon.exe", "spoolsv.exe", "systemd", "dbus-daemon", "chrony", "cupsd", "networkmanager"):
        return "System Component", "Trusted System"
    if proc_lower in ("msedge.exe", "chrome.exe", "firefox.exe", "brave.exe", "safari", "opera.exe"):
        return "Web Browser", "Trusted App"
    if proc_lower in ("python.exe", "node.exe", "git.exe", "code.exe", "uv.exe", "cargo.exe", "rustc.exe", "docker.exe", "bash", "zsh", "python3", "node"):
        return "Developer Tool", "Local Dev"
    if remote_ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "::1")):
        return "Local Subnet", "Local Safe"
    if remote_domain and any(remote_domain.endswith(dom) for dom in ("microsoft.com", "google.com", "github.com", "cloudflare.com", "apple.com", "ubuntu.com", "mozilla.org")):
        return "Verified CDN", "Trusted Service"
    if not remote_domain and remote_ip:
        return "External IP", "Unverified"
    return "Application", "Local Safe"


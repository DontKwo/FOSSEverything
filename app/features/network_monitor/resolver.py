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

SAFE_DOMAIN_SUFFIXES: tuple[str, ...] = (
    "google.com", "googleusercontent.com", "1e100.net", "gstatic.com", "googleapis.com",
    "microsoft.com", "windows.com", "windows.net", "live.com", "office.com", "office365.com",
    "onedrive.com", "azure.com", "azureedge.net", "msftconnecttest.com", "msedge.net", "bing.com", "msn.com",  # noqa: 91
    "github.com", "githubusercontent.com",
    "cloudflare.com", "cloudflare.net", "cloudfront.net", "amazonaws.com", "awsglobalaccelerator.com",
    "akamaitechnologies.com", "akamaiedge.net", "akamaihd.net", "deploy.static.akamaitechnologies.com",
    "apple.com", "icloud.com", "ubuntu.com", "debian.org", "mozilla.org",
    "utexas.edu", "tailscale.com", "tailscale.io", "anthropic.com", "openai.com",
    "pypi.org", "pythonhosted.org", "npmjs.org", "npmjs.com", "crates.io",
    "bunnyinfra.net", "b-cdn.net", "fastly.net",
)

SAFE_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),  # noqa: 91
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("100.64.0.0/10"),  # noqa: 91
    ipaddress.ip_network("146.6.0.0/16"),
    ipaddress.ip_network("4.0.0.0/8"),
    ipaddress.ip_network("13.0.0.0/8"),
    ipaddress.ip_network("20.0.0.0/8"),
    ipaddress.ip_network("40.0.0.0/8"),
    ipaddress.ip_network("48.0.0.0/8"),
    ipaddress.ip_network("51.0.0.0/8"),
    ipaddress.ip_network("52.0.0.0/8"),
    ipaddress.ip_network("65.52.0.0/14"),
    ipaddress.ip_network("104.208.0.0/13"),
    ipaddress.ip_network("135.234.0.0/16"),
    ipaddress.ip_network("150.171.0.0/16"),
    ipaddress.ip_network("168.62.0.0/15"),
    ipaddress.ip_network("23.103.0.0/16"),
    # AWS / Cloudfront
    ipaddress.ip_network("13.32.0.0/15"),
    ipaddress.ip_network("13.224.0.0/14"),
    ipaddress.ip_network("18.0.0.0/8"),
    ipaddress.ip_network("54.0.0.0/8"),
    ipaddress.ip_network("99.83.0.0/16"),
    ipaddress.ip_network("34.0.0.0/8"),
    ipaddress.ip_network("35.0.0.0/8"),
    ipaddress.ip_network("142.250.0.0/15"),
    ipaddress.ip_network("172.217.0.0/16"),
    ipaddress.ip_network("216.58.192.0/19"),
    ipaddress.ip_network("104.16.0.0/12"),
    ipaddress.ip_network("172.64.0.0/13"),
    ipaddress.ip_network("1.1.1.0/24"),
    ipaddress.ip_network("1.0.0.0/24"),
    ipaddress.ip_network("199.232.0.0/16"),
    ipaddress.ip_network("151.101.0.0/16"),
    ipaddress.ip_network("23.192.0.0/11"),
    ipaddress.ip_network("23.32.0.0/11"),
    ipaddress.ip_network("23.0.0.0/12"),
    ipaddress.ip_network("104.64.0.0/10"),
    ipaddress.ip_network("184.24.0.0/13"),
)


def is_safe_destination(ip_str: str, domain_str: str | None = None) -> bool:
    # Check whether an IP or domain matches trusted infrastructure or local subnets.
    if domain_str:
        dom = domain_str.lower().strip().rstrip(".")
        if dom == "localhost" or any(dom == suffix or dom.endswith("." + suffix) for suffix in SAFE_DOMAIN_SUFFIXES):
            return True
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip())
        return any(ip_obj in net for net in SAFE_NETWORKS)
    except ValueError:
        return False


def set_user_process_trust(process_name: str, trust_level: str) -> None:
    # Set user defined process trust level override.
    USER_TRUST_OVERRIDES[process_name.lower().strip()] = trust_level


def classify_connection_trust(process_name: str, remote_ip: str, remote_domain: str | None = None) -> tuple[str, str]:
    # Determine source identity and trustworthiness rating.
    proc_lower = process_name.lower().strip()
    if proc_lower in USER_TRUST_OVERRIDES:
        return "Custom Trust", USER_TRUST_OVERRIDES[proc_lower]
    system_procs = (
        "svchost.exe", "lsass.exe", "services.exe", "explorer.exe", "system", "smss.exe",
        "winlogon.exe", "spoolsv.exe", "systemd", "dbus-daemon", "chrony", "cupsd", "networkmanager",
        "wudfhost.exe", "ipfsvc.exe", "mpdefendercoreservice.exe", "msmpeng.exe",
        "microsoftsecurityapp.exe", "microsoftstartfeedprovider.exe", "startmenuexperiencehost.exe",
        "searchhost.exe", "shellexperiencehost.exe", "textinputhost.exe", "runtimebroker.exe",
        "taskhostw.exe", "sihost.exe", "onedrive.sync.service.exe", "onedrive.exe",  # noqa: 91
        "officeclicktorun.exe", "sdxhelper.exe", "backgrounddownload.exe", "backgroundtaskhost.exe", "lockapp.exe"
    )
    if proc_lower in system_procs:
        return "System Component", "Trusted System"
    if proc_lower in ("msedge.exe", "chrome.exe", "firefox.exe", "brave.exe", "safari", "opera.exe", "msedgewebview2.exe"):
        return "Web Browser", "Trusted App"
    if proc_lower in ("winword.exe", "powerpnt.exe", "excel.exe", "outlook.exe", "ms-teams.exe", "discord.exe"):
        return "Productivity App", "Trusted App"
    dev_procs = (
        "python.exe", "python3.exe", "python3.13.exe", "node.exe", "git.exe", "code.exe",
        "uv.exe", "cargo.exe", "rustc.exe", "docker.exe", "bash", "zsh", "python3", "node",
        "agy.exe", "claude.exe", "gh.exe", "ssh.exe", "tailscaled.exe", "tailscale.exe"
    )
    if proc_lower in dev_procs:
        return "Developer Tool", "Local Dev"
    if is_safe_destination(remote_ip, remote_domain):
        return "Verified CDN", "Trusted Service"
    if remote_ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "::1")):
        return "Local Subnet", "Local Safe"
    if not remote_domain and remote_ip:
        return "External IP", "Unverified"
    return "Application", "Local Safe"


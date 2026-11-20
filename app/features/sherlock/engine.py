"""Sherlock username search engine for FOSSEverything.

Based on Sherlock Project (MIT License, https://github.com/sherlock-project/sherlock).
Copyright (c) 2019-2024 Siddharth Dushantha and Sherlock Project contributors.
"""
from __future__ import annotations

import concurrent.futures
import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import requests

from app.system.jobs import get_current_job_ctx

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
)

MANIFEST_URL = "https://data.sherlockproject.xyz"

WAF_HIT_PATTERNS: tuple[str, ...] = (
    r".loading-spinner{visibility:hidden}body.no-js .challenge-running{display:none}",
    r'<span id="challenge-error-text">',
    r"AwsWafIntegration.forceRefreshToken",
    r'{return l.onPageView}}),Object.defineProperty(r,"perimeterxIdentifiers",{enumerable:',
)

POPULAR_SITES: tuple[str, ...] = (
    "GitHub",
    "GitLab",
    "Reddit",
    "Twitter",
    "Instagram",
    "TikTok",
    "YouTube",
    "Pinterest",
    "Spotify",
    "Steam Community (User)",
    "Telegram",
    "Twitch",
    "Discord",
    "Medium",
    "Patreon",
    "Snapchat",
    "SoundCloud",
    "Vimeo",
    "WordPress",
    "HackerNews",
    "DeviantArt",
    "Disqus",
    "Flickr",
    "GitBook",
    "Keybase",
    "mastodon.social",
    "Pastebin",
    "BitBucket",
    "Docker Hub",
    "Hugging Face",
)


class QueryStatus(str, Enum):
    CLAIMED = "Claimed"
    AVAILABLE = "Available"
    UNKNOWN = "Unknown"
    ILLEGAL = "Illegal"
    WAF = "WAF"


def get_bundled_data_path() -> Path:
    # Resolve path to bundled site definitions JSON file.
    return Path(__file__).parent / "data.json"


def get_cached_data_path() -> Path:
    # Resolve path to downloaded and cached site definitions JSON file.
    cache_dir = Path.home() / ".fosseverything" / "sherlock"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "data.json"


def load_site_data(custom_path: str | None = None) -> dict[str, dict[str, Any]]:
    # Load site signatures from custom, cached, or bundled JSON data file.
    target_path = Path(custom_path) if custom_path else None
    if target_path is None or not target_path.is_file():
        cached_file = get_cached_data_path()
        target_path = cached_file if cached_file.is_file() else get_bundled_data_path()

    if not target_path.is_file():
        return {}

    with open(target_path, "r", encoding="utf-8") as file_handle:
        raw_data = json.load(file_handle)

    clean_sites: dict[str, dict[str, Any]] = {}
    for site_key, site_info in raw_data.items():
        if site_key.startswith("$") or not isinstance(site_info, dict):
            continue
        clean_sites[site_key] = site_info
    return clean_sites


def update_site_data(manifest_url: str = MANIFEST_URL) -> tuple[bool, int, str]:
    # Download latest site definitions from Sherlock manifest and cache locally.
    try:
        response = requests.get(manifest_url, timeout=20.0, headers={"User-Agent": DEFAULT_USER_AGENT})
        response.raise_for_status()
        downloaded_json = response.json()
        if not isinstance(downloaded_json, dict) or len(downloaded_json) < 20:
            return False, 0, "Downloaded manifest did not contain valid site definitions."
        cached_path = get_cached_data_path()
        with open(cached_path, "w", encoding="utf-8") as file_handle:
            json.dump(downloaded_json, file_handle, indent=2)
        site_count = len([key for key in downloaded_json if not key.startswith("$")])
        return True, site_count, f"Updated database with {site_count} sites."
    except Exception as exc:
        return False, 0, f"Failed to download site database: {exc}"


def interpolate_template(target_obj: Any, username: str) -> Any:
    # Replace username placeholder tokens in string, dict, or list structures.
    if isinstance(target_obj, str):
        return target_obj.replace("{}", username.replace(" ", "%20"))
    if isinstance(target_obj, dict):
        return {dict_key: interpolate_template(dict_value, username) for dict_key, dict_value in target_obj.items()}
    if isinstance(target_obj, list):
        return [interpolate_template(item, username) for item in target_obj]
    return target_obj


def probe_single_site(
    session: requests.Session,
    site_name: str,
    site_info: dict[str, Any],
    username: str,
    timeout: float = 10.0,
    proxy: str | None = None,
) -> dict[str, Any]:
    # Check existence of target username on a single site using Sherlock rules.
    url_main = str(site_info.get("urlMain", ""))
    url_template = str(site_info.get("url", ""))
    url_user = interpolate_template(url_template, username)

    regex_check = site_info.get("regexCheck")
    if regex_check and re.search(regex_check, username) is None:
        return {
            "site_name": site_name,
            "url_main": url_main,
            "url_user": url_user,
            "status": QueryStatus.ILLEGAL.value,
            "http_status": 0,
            "response_time_ms": 0.0,
            "is_nsfw": bool(site_info.get("isNSFW", False)),
            "error_context": "Username format not allowed by site regex",
        }

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if "headers" in site_info and isinstance(site_info["headers"], dict):
        headers.update(site_info["headers"])

    raw_probe = site_info.get("urlProbe")
    url_probe = interpolate_template(raw_probe, username) if raw_probe else url_user
    request_method = str(site_info.get("request_method", "")).upper()
    error_type = site_info.get("errorType", "status_code")
    if isinstance(error_type, str):
        error_types: list[str] = [error_type]
    else:
        error_types = list(error_type)

    if not request_method:
        request_method = "HEAD" if "status_code" in error_types and len(error_types) == 1 else "GET"

    allow_redirects = False if "response_url" in error_types else True
    proxies = {"http": proxy, "https": proxy} if proxy else None
    payload = interpolate_template(site_info.get("request_payload"), username) if site_info.get("request_payload") else None

    start_time = time.monotonic()
    response_code = 0
    response_body = ""
    error_context: str | None = None

    try:
        req_kwargs: dict[str, Any] = {
            "headers": headers,
            "allow_redirects": allow_redirects,
            "timeout": timeout,
            "proxies": proxies,
        }
        if payload is not None:
            req_kwargs["json"] = payload

        if request_method == "HEAD":
            resp = session.head(url_probe, **req_kwargs)
        elif request_method == "POST":
            resp = session.post(url_probe, **req_kwargs)
        elif request_method == "PUT":
            resp = session.put(url_probe, **req_kwargs)
        else:
            resp = session.get(url_probe, **req_kwargs)

        elapsed_ms = round((time.monotonic() - start_time) * 1000.0, 1)
        try:
            response_code = int(resp.status_code)
        except (TypeError, ValueError):
            response_code = 0
        response_body = str(resp.text or "")
    except requests.exceptions.Timeout:
        elapsed_ms = round((time.monotonic() - start_time) * 1000.0, 1)
        return {
            "site_name": site_name,
            "url_main": url_main,
            "url_user": url_user,
            "status": QueryStatus.UNKNOWN.value,
            "http_status": 0,
            "response_time_ms": elapsed_ms,
            "is_nsfw": bool(site_info.get("isNSFW", False)),
            "error_context": "Request timeout",
        }
    except Exception as req_exc:
        elapsed_ms = round((time.monotonic() - start_time) * 1000.0, 1)
        return {
            "site_name": site_name,
            "url_main": url_main,
            "url_user": url_user,
            "status": QueryStatus.UNKNOWN.value,
            "http_status": 0,
            "response_time_ms": elapsed_ms,
            "is_nsfw": bool(site_info.get("isNSFW", False)),
            "error_context": str(req_exc),
        }

    if any(pattern in response_body for pattern in WAF_HIT_PATTERNS):
        return {
            "site_name": site_name,
            "url_main": url_main,
            "url_user": url_user,
            "status": QueryStatus.WAF.value,
            "http_status": response_code,
            "response_time_ms": elapsed_ms,
            "is_nsfw": bool(site_info.get("isNSFW", False)),
            "error_context": "Blocked by Cloudflare/WAF",
        }

    status_verdict = QueryStatus.UNKNOWN
    for single_err_type in error_types:
        if single_err_type == "message":
            error_patterns = site_info.get("errorMsg", [])
            if isinstance(error_patterns, str):
                error_patterns = [error_patterns]
            has_error_message = any(msg in response_body for msg in error_patterns)
            status_verdict = QueryStatus.AVAILABLE if has_error_message else QueryStatus.CLAIMED
            break

        if single_err_type == "status_code":
            expected_codes = site_info.get("errorCode")
            if isinstance(expected_codes, int):
                expected_codes = [expected_codes]
            if expected_codes and response_code in expected_codes:
                status_verdict = QueryStatus.AVAILABLE
            elif 200 <= response_code < 300:
                status_verdict = QueryStatus.CLAIMED
            else:
                status_verdict = QueryStatus.AVAILABLE
            break

        if single_err_type == "response_url":
            status_verdict = QueryStatus.CLAIMED if 200 <= response_code < 300 else QueryStatus.AVAILABLE
            break

    return {
        "site_name": site_name,
        "url_main": url_main,
        "url_user": url_user,
        "status": status_verdict.value,
        "http_status": response_code,
        "response_time_ms": elapsed_ms,
        "is_nsfw": bool(site_info.get("isNSFW", False)),
        "error_context": error_context,
    }


def search_username(
    username: str,
    site_names: list[str] | None = None,
    include_nsfw: bool = False,
    max_workers: int = 15,
    timeout: float = 10.0,
    proxy: str | None = None,
    custom_data_path: str | None = None,
) -> dict[str, Any]:
    # Execute parallel username probes across chosen social networks.
    stripped_user = username.strip()
    if not stripped_user:
        return {
            "username": "",
            "total_checked": 0,
            "found_count": 0,
            "available_count": 0,
            "error_count": 0,
            "results": [],
        }

    site_data = load_site_data(custom_data_path)
    selected_sites: dict[str, dict[str, Any]] = {}

    target_filter = set(site_names) if site_names else None
    for site_key, site_dict in site_data.items():
        if target_filter and site_key not in target_filter:
            continue
        if not include_nsfw and site_dict.get("isNSFW", False):
            continue
        selected_sites[site_key] = site_dict

    total_sites = len(selected_sites)
    if total_sites == 0:
        return {
            "username": stripped_user,
            "total_checked": 0,
            "found_count": 0,
            "available_count": 0,
            "error_count": 0,
            "results": [],
        }

    job_context = get_current_job_ctx()
    results: list[dict[str, Any]] = []
    completed_count = 0
    found_count = 0

    worker_count = min(max_workers, max(1, total_sites))
    session = requests.Session()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_site = {
                executor.submit(
                    probe_single_site,
                    session,
                    name,
                    info,
                    stripped_user,
                    timeout,
                    proxy,
                ): name
                for name, info in selected_sites.items()
            }

            for future in concurrent.futures.as_completed(future_to_site):
                if job_context and job_context.is_cancelled():
                    break
                try:
                    site_res = future.result()
                    results.append(site_res)
                    if site_res["status"] == QueryStatus.CLAIMED.value:
                        found_count += 1
                except Exception as future_exc:
                    site_label = future_to_site[future]
                    results.append({
                        "site_name": site_label,
                        "url_main": "",
                        "url_user": "",
                        "status": QueryStatus.UNKNOWN.value,
                        "http_status": 0,
                        "response_time_ms": 0.0,
                        "is_nsfw": False,
                        "error_context": str(future_exc),
                    })
                completed_count += 1
                if job_context:
                    fraction = completed_count / total_sites
                    job_context.update(
                        fraction,
                        f"Checked {completed_count}/{total_sites} sites ({found_count} found)",
                    )
    finally:
        session.close()

    results.sort(key=lambda item: (item["status"] != QueryStatus.CLAIMED.value, item["site_name"].lower()))
    available_count = sum(1 for item in results if item["status"] == QueryStatus.AVAILABLE.value)
    error_count = sum(1 for item in results if item["status"] in (QueryStatus.UNKNOWN.value, QueryStatus.WAF.value))

    return {
        "username": stripped_user,
        "total_checked": len(results),
        "found_count": found_count,
        "available_count": available_count,
        "error_count": error_count,
        "results": results,
    }


def export_results(
    username: str,
    results: list[dict[str, Any]],
    output_path: str = "",
    format_type: str = "json",
) -> str:
    # Save search findings to JSON, CSV, or formatted text report file.
    norm_format = format_type.lower()
    if norm_format not in ("json", "csv", "txt"):
        norm_format = "json"

    if not output_path:
        reports_dir = Path.home() / ".fosseverything" / "sherlock_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_path = reports_dir / f"sherlock_{username}_{timestamp_str}.{norm_format}"
    else:
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

    if norm_format == "json":
        export_payload = {
            "username": username,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "FOSSEverything Sherlock Tool",
            "license": "MIT (Sherlock Project)",
            "results_count": len(results),
            "results": results,
        }
        with open(target_path, "w", encoding="utf-8") as file_handle:
            json.dump(export_payload, file_handle, indent=2)
    elif norm_format == "csv":
        with open(target_path, "w", newline="", encoding="utf-8") as file_handle:
            writer = csv.writer(file_handle)
            writer.writerow(["username", "site_name", "status", "url_user", "http_status", "response_time_ms", "is_nsfw", "error_context"])
            for row in results:
                writer.writerow([
                    username,
                    row.get("site_name", ""),
                    row.get("status", ""),
                    row.get("url_user", ""),
                    row.get("http_status", ""),
                    row.get("response_time_ms", ""),
                    row.get("is_nsfw", False),
                    row.get("error_context", "") or "",
                ])
    else:
        with open(target_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(f"# Sherlock Username Search Report: {username}\n")
            file_handle.write(f"# Generated: {datetime.now(timezone.utc).isoformat()}\n")
            file_handle.write(f"# Powered by Sherlock Project (MIT License, https://github.com/sherlock-project/sherlock)\n\n")
            found_rows = [row for row in results if row.get("status") == QueryStatus.CLAIMED.value]
            file_handle.write(f"=== Found Accounts ({len(found_rows)}) ===\n")
            for row in found_rows:
                file_handle.write(f"  [+] {row.get('site_name', '')}: {row.get('url_user', '')}\n")
            file_handle.write("\n=== Other Results ===\n")
            for row in results:
                if row.get("status") != QueryStatus.CLAIMED.value:
                    file_handle.write(f"  [-] {row.get('site_name', '')} ({row.get('status', '')}) {row.get('error_context', '') or ''}\n")

    return str(target_path)

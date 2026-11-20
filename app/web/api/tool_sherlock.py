from typing import Any

from app.features.sherlock.engine import (
    POPULAR_SITES,
    export_results,
    load_site_data,
    search_username,
    update_site_data,
)
from app.web.api.result import api_method, ok, require


class SherlockApiMixin:
    @api_method
    def sherlock_get_sites(self, params: dict[str, Any]) -> dict[str, Any]:
        # Catalog all supported social media platforms and detection options.
        site_data = load_site_data()
        sites_list: list[dict[str, Any]] = []
        for name, info in sorted(site_data.items(), key=lambda item: item[0].lower()):
            sites_list.append({
                "name": name,
                "url_main": info.get("urlMain", ""),
                "is_nsfw": bool(info.get("isNSFW", False)),
                "error_type": info.get("errorType", ""),
                "is_popular": name in POPULAR_SITES,
            })
        return ok(
            total_count=len(sites_list),
            popular_count=len([site for site in sites_list if site["is_popular"]]),
            nsfw_count=len([site for site in sites_list if site["is_nsfw"]]),
            popular_sites=list(POPULAR_SITES),
            sites=sites_list,
        )

    @api_method
    def sherlock_search(self, params: dict[str, Any]) -> dict[str, Any]:
        # Search for username across selected social networks.
        require(params, "username")
        username = str(params["username"]).strip()
        site_names = params.get("sites")
        if isinstance(site_names, list):
            target_sites = [str(item).strip() for item in site_names if str(item).strip()]
        elif params.get("mode") == "popular":
            target_sites = list(POPULAR_SITES)
        else:
            target_sites = None

        include_nsfw = bool(params.get("include_nsfw", False))
        timeout = float(params.get("timeout", 10.0))
        max_workers = int(params.get("max_workers", 15))
        proxy_val = str(params["proxy"]).strip() if params.get("proxy") else None

        result_data = search_username(
            username=username,
            site_names=target_sites,
            include_nsfw=include_nsfw,
            max_workers=max_workers,
            timeout=timeout,
            proxy=proxy_val,
        )
        return ok(**result_data)

    @api_method
    def sherlock_export(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save search results to a local file in JSON, CSV, or TXT format.
        require(params, "username", "results")
        username = str(params["username"]).strip()
        results_list = params.get("results")
        if not isinstance(results_list, list):
            results_list = []
        format_type = str(params.get("format", "json")).lower()
        output_path = str(params.get("output_path", "")).strip()
        saved_file = export_results(username, results_list, output_path=output_path, format_type=format_type)
        return ok(file_path=saved_file, count=len(results_list), format=format_type)

    @api_method
    def sherlock_update_database(self, params: dict[str, Any]) -> dict[str, Any]:
        # Download and update the latest sites definition database.
        url_param = str(params.get("url") or "").strip()
        success, count, message_text = update_site_data(url_param) if url_param else update_site_data()
        return ok(success=success, site_count=count, message=message_text)

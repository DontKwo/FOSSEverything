from pathlib import Path
from unittest.mock import MagicMock, patch

from app.features.sherlock.engine import (
    POPULAR_SITES,
    QueryStatus,
    export_results,
    interpolate_template,
    load_site_data,
    probe_single_site,
    search_username,
)
from app.web.api import WebApi


def test_load_bundled_site_data() -> None:
    # Assert bundled site database loads and contains hundreds of sites.
    sites = load_site_data()
    assert len(sites) >= 300
    assert "GitHub" in sites
    assert "Reddit" in sites
    for pop in POPULAR_SITES:
        assert pop in sites, f"Popular site {pop} missing from site definitions"


def test_interpolate_template() -> None:
    # Verify username replacement in strings, dicts, and lists.
    res_str = interpolate_template("https://example.com/{}", "test user")
    assert res_str == "https://example.com/test%20user"

    res_dict = interpolate_template({"url": "https://example.com/{}"}, "alice")
    assert res_dict["url"] == "https://example.com/alice"


def test_probe_illegal_username() -> None:
    # Verify regex check flags invalid usernames as Illegal without network calls.
    site_info = {
        "url": "https://example.com/{}",
        "urlMain": "https://example.com",
        "regexCheck": r"^[a-z0-9_]{3,10}$",
        "errorType": "status_code",
    }
    mock_session = MagicMock()
    result = probe_single_site(mock_session, "Example", site_info, "bad!name#too-long-and-invalid")
    assert result["status"] == QueryStatus.ILLEGAL.value
    assert mock_session.get.call_count == 0


def test_probe_claimed_and_available() -> None:
    # Verify status_code and message detection rules produce Claimed or Available.
    site_info_code = {
        "url": "https://example.com/{}",
        "urlMain": "https://example.com",
        "errorType": "status_code",
    }
    mock_session = MagicMock()
    mock_resp_200 = MagicMock(status_code=200, text="Profile content")
    mock_session.head.return_value = mock_resp_200
    mock_session.get.return_value = mock_resp_200

    claimed_res = probe_single_site(mock_session, "SiteCode", site_info_code, "alice")
    assert claimed_res["status"] == QueryStatus.CLAIMED.value

    mock_resp_404 = MagicMock(status_code=404, text="Not found")
    mock_session.head.return_value = mock_resp_404
    mock_session.get.return_value = mock_resp_404
    avail_res = probe_single_site(mock_session, "SiteCode", site_info_code, "alice")
    assert avail_res["status"] == QueryStatus.AVAILABLE.value


def test_search_username_mocked() -> None:
    # Test parallel search engine across selected sites with mocked network responses.
    fake_sites = {
        "GitHub": {"url": "https://github.com/{}", "urlMain": "https://github.com", "errorType": "status_code"},
        "Reddit": {"url": "https://reddit.com/user/{}", "urlMain": "https://reddit.com", "errorType": "status_code"},
    }
    with patch("app.features.sherlock.engine.load_site_data", return_value=fake_sites):
        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_resp = MagicMock(status_code=200, text="OK")
            mock_session.get.return_value = mock_resp
            mock_session.head.return_value = mock_resp
            mock_session_cls.return_value = mock_session

            res = search_username("testuser", site_names=["GitHub", "Reddit"])
            assert res["total_checked"] == 2
            assert res["found_count"] == 2
            assert len(res["results"]) == 2


def test_export_results_formats(tmp_path: Path) -> None:
    # Verify exporting results creates valid JSON, CSV, and text reports.
    sample_results = [
        {
            "site_name": "GitHub",
            "url_main": "https://github.com",
            "url_user": "https://github.com/alice",
            "status": "Claimed",
            "http_status": 200,
            "response_time_ms": 120.0,
            "is_nsfw": False,
            "error_context": None,
        },
        {
            "site_name": "UnknownSite",
            "url_main": "https://unknown.com",
            "url_user": "https://unknown.com/alice",
            "status": "Available",
            "http_status": 404,
            "response_time_ms": 80.0,
            "is_nsfw": False,
            "error_context": None,
        },
    ]

    json_path = tmp_path / "report.json"
    saved_json = export_results("alice", sample_results, output_path=str(json_path), format_type="json")
    assert Path(saved_json).is_file()
    assert "alice" in Path(saved_json).read_text(encoding="utf-8")

    csv_path = tmp_path / "report.csv"
    saved_csv = export_results("alice", sample_results, output_path=str(csv_path), format_type="csv")
    assert Path(saved_csv).is_file()
    assert "GitHub" in Path(saved_csv).read_text(encoding="utf-8")

    txt_path = tmp_path / "report.txt"
    saved_txt = export_results("alice", sample_results, output_path=str(txt_path), format_type="txt")
    assert Path(saved_txt).is_file()
    assert "=== Found Accounts" in Path(saved_txt).read_text(encoding="utf-8")


def test_sherlock_api_endpoints() -> None:
    # Verify WebApi integration for Sherlock endpoints.
    api = WebApi()

    sites_res = api.sherlock_get_sites({})
    assert sites_res["ok"] is True
    assert sites_res["total_count"] >= 300
    assert "GitHub" in sites_res["popular_sites"]

    export_res = api.sherlock_export({"username": "tester", "results": [], "format": "json"})
    assert export_res["ok"] is True
    assert Path(export_res["file_path"]).is_file()

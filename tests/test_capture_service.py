"""Tests for capture_service.draft_to_profile_app browser block emission."""

from capture_service import draft_to_profile_app, _detect_app_type


def _make_draft(launch_behavior: str, launch_details: dict | None = None) -> dict:
    return {
        "name": "Chrome",
        "path": "C:/chrome.exe",
        "window_title": "GitHub",
        "window": {"monitor": 0, "preset": "right-third",
                   "x": 0, "y": 0, "w": 1, "h": 1},
        "app_type": "chromium",
        "launch_behavior": launch_behavior,
        "launch_details": launch_details or {},
        "confidence": "high",
    }


def test_chrome_urls_with_urls_emits_browser_block():
    draft = _make_draft("chrome_urls", {"urls": ["https://x.com", "https://y.com"]})
    app = draft_to_profile_app(draft)
    assert app["args"] == []
    assert app["browser"] == {
        "restore_session": True,
        "urls": ["https://x.com", "https://y.com"],
    }


def test_chrome_urls_without_urls_emits_empty_url_list_with_restore_true():
    draft = _make_draft("chrome_urls", {})
    app = draft_to_profile_app(draft)
    assert app["args"] == []
    assert app["browser"] == {"restore_session": True, "urls": []}


def test_chrome_new_window_emits_browser_block_with_restore_false():
    draft = _make_draft("chrome_new_window")
    app = draft_to_profile_app(draft)
    assert app["args"] == []
    assert app["browser"] == {"restore_session": False, "urls": []}


def test_non_chromium_app_has_no_browser_block():
    draft = {
        "name": "Notepad",
        "path": "C:/notepad.exe",
        "window_title": "Untitled",
        "window": {"monitor": 0, "preset": "full",
                   "x": 0, "y": 0, "w": 1, "h": 1},
        "app_type": "generic",
        "launch_behavior": "plain",
        "launch_details": {},
        "confidence": "low",
    }
    app = draft_to_profile_app(draft)
    assert "browser" not in app
    assert app["args"] == []


def test_detect_app_type_maps_brave_to_chromium():
    assert _detect_app_type("C:/brave.exe", "Brave") == "chromium"


def test_detect_app_type_maps_chrome_to_chromium():
    assert _detect_app_type("C:/chrome.exe", "Chrome") == "chromium"


def test_detect_app_type_maps_edge_to_chromium():
    assert _detect_app_type("C:/msedge.exe", "Edge") == "chromium"


def test_chrome_urls_honors_restore_session_false_from_details():
    draft = _make_draft("chrome_urls", {
        "urls": ["https://x.com"],
        "restore_session": False,
    })
    app = draft_to_profile_app(draft)
    assert app["browser"] == {
        "restore_session": False,
        "urls": ["https://x.com"],
    }

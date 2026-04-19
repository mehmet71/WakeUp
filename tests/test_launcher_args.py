"""Tests for launcher._build_launch_args — browser block handling."""

from launcher import _build_launch_args


def test_no_browser_block_returns_args_unchanged():
    app = {"path": "x.exe", "args": ["--foo", "bar"]}
    assert _build_launch_args(app) == ["--foo", "bar"]


def test_missing_args_defaults_to_empty_list():
    app = {"path": "x.exe"}
    assert _build_launch_args(app) == []


def test_args_are_coerced_to_strings():
    app = {"path": "x.exe", "args": [1, 2.5]}
    assert _build_launch_args(app) == ["1", "2.5"]


def test_browser_restore_true_with_urls_appends_urls_without_new_window():
    app = {
        "path": "chrome.exe",
        "args": [],
        "browser": {
            "restore_session": True,
            "urls": ["https://music.youtube.com/x", "https://github.com"],
        },
    }
    assert _build_launch_args(app) == [
        "https://music.youtube.com/x",
        "https://github.com",
    ]


def test_browser_restore_false_with_urls_prepends_new_window():
    app = {
        "path": "chrome.exe",
        "args": [],
        "browser": {
            "restore_session": False,
            "urls": ["https://music.youtube.com/x"],
        },
    }
    assert _build_launch_args(app) == [
        "--new-window",
        "https://music.youtube.com/x",
    ]


def test_browser_restore_false_without_urls_just_new_window():
    app = {
        "path": "chrome.exe",
        "args": [],
        "browser": {"restore_session": False},
    }
    assert _build_launch_args(app) == ["--new-window"]


def test_browser_restore_true_without_urls_is_noop():
    app = {
        "path": "chrome.exe",
        "args": [],
        "browser": {"restore_session": True},
    }
    assert _build_launch_args(app) == []


def test_browser_block_preserves_existing_args():
    app = {
        "path": "chrome.exe",
        "args": ["--profile-directory=Default"],
        "browser": {
            "restore_session": False,
            "urls": ["https://x.com"],
        },
    }
    assert _build_launch_args(app) == [
        "--new-window",
        "--profile-directory=Default",
        "https://x.com",
    ]


def test_url_entries_are_coerced_to_strings():
    app = {
        "path": "chrome.exe",
        "browser": {"restore_session": True, "urls": [123]},
    }
    assert _build_launch_args(app) == ["123"]


def test_browser_restore_session_defaults_to_true_when_missing():
    app = {
        "path": "chrome.exe",
        "browser": {"urls": ["https://x.com"]},
    }
    assert _build_launch_args(app) == ["https://x.com"]

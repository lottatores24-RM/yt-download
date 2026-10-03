"""Read/write download history and user settings as JSON.

Both live under ~/.yt_downloader/ so they survive between runs.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .helpers import default_download_dir

CONFIG_DIR = Path.home() / ".yt_downloader"
HISTORY_FILE = CONFIG_DIR / "history.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

MAX_HISTORY = 50


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #
def load_history() -> list[dict[str, Any]]:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return []


def save_history(entries: list[dict[str, Any]]) -> None:
    _ensure_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as fh:
        json.dump(entries[:MAX_HISTORY], fh, indent=2, ensure_ascii=False)


def add_entry(entry: dict[str, Any]) -> None:
    """Prepend a new history record (most recent first)."""
    entry.setdefault("timestamp", time.time())
    entries = load_history()
    entries.insert(0, entry)
    save_history(entries)


def recent(n: int = 5) -> list[dict[str, Any]]:
    return load_history()[:n]


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
def default_settings() -> dict[str, Any]:
    return {
        "download_folder": str(default_download_dir()),
        "default_quality": "720p",
        "auto_open": False,
        "appearance": "dark",  # "dark" or "light"
    }


def load_settings() -> dict[str, Any]:
    settings = default_settings()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            settings.update({k: v for k, v in data.items() if k in settings})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    _ensure_dir()
    merged = default_settings()
    merged.update({k: v for k, v in settings.items() if k in merged})
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)

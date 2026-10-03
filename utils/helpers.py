"""Small, dependency-free formatting and filesystem helpers."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def format_bytes(num: float | int | None) -> str:
    """Human readable byte size, e.g. 1536000 -> '1.46 MB'."""
    if not num or num < 0:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def format_speed(bytes_per_sec: float | None) -> str:
    """Download speed, e.g. '2.34 MB/s'."""
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "—"
    return f"{format_bytes(bytes_per_sec)}/s"


def format_duration(seconds: float | int | None) -> str:
    """Seconds -> 'M:SS' or 'H:MM:SS'."""
    if seconds is None:
        return "—"
    seconds = int(seconds)
    if seconds < 0:
        return "—"
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_eta(seconds: float | int | None) -> str:
    """ETA helper that adds a trailing label."""
    if seconds is None or seconds < 0:
        return "—"
    return format_duration(seconds)


def format_count(num: float | int | None) -> str:
    """Compact count, e.g. 1530000 -> '1.5M'."""
    if num is None:
        return "—"
    num = float(num)
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if num >= threshold:
            value = num / threshold
            return f"{value:.1f}".rstrip("0").rstrip(".") + suffix
    return str(int(num))


_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str) -> str:
    """Strip characters that are illegal in Windows filenames."""
    cleaned = _INVALID_FILENAME.sub("_", name).strip(". ")
    return cleaned or "video"


def default_download_dir() -> Path:
    """Default target folder: ~/Videos/YT-Downloads."""
    return Path.home() / "Videos" / "YT-Downloads"


def ensure_dir(path: str | os.PathLike) -> Path:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_folder(path: str | os.PathLike) -> None:
    """Open a folder in the OS file manager, cross-platform."""
    p = Path(path).expanduser()
    if not p.exists():
        p = p.parent
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception:
        # Opening a folder should never crash the app.
        pass


def looks_like_url(text: str) -> bool:
    """Loose check that a string is a plausible http(s) URL."""
    if not text:
        return False
    text = text.strip()
    return bool(re.match(r"^https?://[^\s]+\.[^\s]+", text))

"""yt-dlp wrapper: info extraction, quality enumeration and threaded download.

The UI never talks to yt-dlp directly. It calls:
    extract_info(url)              -> VideoInfo
    build_quality_options(info)    -> {"video": [...], "audio": [...]}
    Downloader().start(...)        -> runs in a background thread

All user-facing errors are mapped to friendly messages via FriendlyError.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yt_dlp

from utils.helpers import ensure_dir


class FriendlyError(Exception):
    """An error whose message is safe to show directly to the user."""


@dataclass
class QualityOption:
    label: str               # what the dropdown shows, e.g. "1080p  (~52 MB)"
    selector: str            # yt-dlp format selector string
    kind: str                # "video" or "audio"
    height: int | None = None
    est_size: int | None = None


@dataclass
class VideoInfo:
    url: str
    title: str
    channel: str
    duration: int | None
    view_count: int | None
    thumbnail: str | None
    raw: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Error mapping
# --------------------------------------------------------------------------- #
def _friendly_message(exc: Exception) -> str:
    text = str(exc).lower()
    # Network / connectivity first — these strings can otherwise be mistaken
    # for content errors (e.g. "API page" matching an "age" check).
    if any(
        w in text
        for w in (
            "proxy", "tunnel", "getaddrinfo", "timed out", "timeout",
            "unable to connect", "connection refused", "connection reset",
            "failed to resolve", "name or service not known", "network is unreachable",
            "temporary failure in name resolution",
        )
    ):
        return "Network error — check your internet connection and try again."
    if "private video" in text or ("sign in" in text and "private" in text):
        return "This video is private and cannot be downloaded."
    if "video unavailable" in text or "has been removed" in text:
        return "This video is unavailable or has been removed."
    if "is not a valid url" in text or "unsupported url" in text:
        return "That doesn't look like a valid video URL."
    if "members-only" in text or "join this channel" in text:
        return "This is a members-only video and cannot be downloaded."
    if "age-restricted" in text or "confirm your age" in text or "inappropriate for some users" in text:
        return "This video is age-restricted and cannot be downloaded."
    if "ffmpeg" in text or "ffprobe" in text:
        return "ffmpeg is required for this format but was not found. Please install ffmpeg."
    if "http error 403" in text or "forbidden" in text:
        return "Access denied by the server. The video may be region-locked."
    # Fall back to a trimmed, single-line version of the raw message —
    # never a stack trace.
    raw = str(exc).replace("ERROR:", "").strip().splitlines()[0] if str(exc).strip() else ""
    return raw or "Something went wrong while processing this video."


# --------------------------------------------------------------------------- #
# Info extraction
# --------------------------------------------------------------------------- #
_BASE_OPTS: dict[str, Any] = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
}


def extract_info(url: str) -> VideoInfo:
    """Fetch metadata for a single video. Raises FriendlyError on failure."""
    url = (url or "").strip()
    if not url:
        raise FriendlyError("Please enter a video URL first.")
    try:
        with yt_dlp.YoutubeDL(dict(_BASE_OPTS)) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise FriendlyError(_friendly_message(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - convert anything to friendly text
        raise FriendlyError(_friendly_message(exc)) from exc

    if info is None:
        raise FriendlyError("Could not read any information from that URL.")

    # A playlist URL returns entries; take the first item.
    if info.get("_type") == "playlist" and info.get("entries"):
        info = info["entries"][0]

    return VideoInfo(
        url=info.get("webpage_url", url),
        title=info.get("title") or "Untitled",
        channel=info.get("uploader") or info.get("channel") or "Unknown channel",
        duration=info.get("duration"),
        view_count=info.get("view_count"),
        thumbnail=info.get("thumbnail"),
        raw=info,
    )


# --------------------------------------------------------------------------- #
# Quality enumeration
# --------------------------------------------------------------------------- #
_PREFERRED_HEIGHTS = [2160, 1440, 1080, 720, 480, 360, 240, 144]


def _best_audio_size(formats: list[dict]) -> int | None:
    audio = [
        f for f in formats
        if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
    ]
    sizes = [
        f.get("filesize") or f.get("filesize_approx")
        for f in audio
        if (f.get("filesize") or f.get("filesize_approx"))
    ]
    return max(sizes) if sizes else None


def build_quality_options(info: VideoInfo) -> dict[str, list[QualityOption]]:
    """Return concrete video/audio options available for this video."""
    formats = info.raw.get("formats") or []
    audio_size = _best_audio_size(formats)

    # ---- Video options, one per available height ----
    by_height: dict[int, int | None] = {}
    for f in formats:
        if f.get("vcodec") in (None, "none"):
            continue
        height = f.get("height")
        if not height:
            continue
        size = f.get("filesize") or f.get("filesize_approx")
        # Keep the largest known size we have seen for this height.
        prev = by_height.get(height)
        if height not in by_height or (size and (prev is None or size > prev)):
            by_height[height] = size

    video_options: list[QualityOption] = []
    for height in _PREFERRED_HEIGHTS:
        if height not in by_height:
            continue
        v_size = by_height[height]
        est = None
        if v_size:
            est = v_size + (audio_size or 0)
        from utils.helpers import format_bytes
        size_txt = f"  (~{format_bytes(est)})" if est else ""
        video_options.append(
            QualityOption(
                label=f"{height}p{size_txt}",
                selector=(
                    # Prefer H.264 video + AAC audio so the resulting MP4 plays
                    # in the default Windows player (Movies & TV / Media Player).
                    # YouTube's "best" streams are often AV1/Opus, which that
                    # player cannot decode. Fall back gracefully if H.264 isn't
                    # available at this height (e.g. 1440p/2160p).
                    f"bestvideo[height<={height}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"best[height<={height}][ext=mp4]/"
                    f"best[height<={height}]/best"
                ),
                kind="video",
                height=height,
                est_size=est,
            )
        )

    if not video_options:
        video_options.append(
            QualityOption(label="Best available", selector="best", kind="video")
        )

    # ---- Audio options (fixed MP3 bitrates) ----
    audio_options = [
        QualityOption(label="320 kbps", selector="bestaudio/best", kind="audio"),
        QualityOption(label="192 kbps", selector="bestaudio/best", kind="audio"),
        QualityOption(label="128 kbps", selector="bestaudio/best", kind="audio"),
    ]

    return {"video": video_options, "audio": audio_options}


# --------------------------------------------------------------------------- #
# Threaded download
# --------------------------------------------------------------------------- #
ProgressCallback = Callable[[dict[str, Any]], None]
DoneCallback = Callable[[dict[str, Any]], None]


class Downloader:
    """Runs a single download on a background thread."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def cancel(self) -> None:
        self._cancel.set()

    def start(
        self,
        *,
        url: str,
        option: QualityOption,
        out_dir: str,
        audio_bitrate: str = "192",
        on_progress: ProgressCallback,
        on_done: DoneCallback,
    ) -> None:
        if self.is_running:
            raise FriendlyError("A download is already in progress.")
        self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run,
            kwargs=dict(
                url=url,
                option=option,
                out_dir=out_dir,
                audio_bitrate=audio_bitrate,
                on_progress=on_progress,
                on_done=on_done,
            ),
            daemon=True,
        )
        self._thread.start()

    # -- internals ----------------------------------------------------------- #
    def _progress_hook(self, on_progress: ProgressCallback):
        def hook(d: dict[str, Any]) -> None:
            if self._cancel.is_set():
                raise FriendlyError("Download cancelled.")
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes") or 0
                percent = (downloaded / total) if total else 0.0
                on_progress(
                    {
                        "status": "downloading",
                        "percent": percent,
                        "downloaded": downloaded,
                        "total": total,
                        "speed": d.get("speed"),
                        "eta": d.get("eta"),
                    }
                )
            elif status == "finished":
                on_progress(
                    {"status": "processing", "percent": 1.0, "filename": d.get("filename")}
                )

        return hook

    def _run(
        self,
        *,
        url: str,
        option: QualityOption,
        out_dir: str,
        audio_bitrate: str,
        on_progress: ProgressCallback,
        on_done: DoneCallback,
    ) -> None:
        try:
            target = ensure_dir(out_dir)
        except OSError as exc:
            on_done({"ok": False, "error": f"Could not create folder: {exc}"})
            return

        outtmpl = os.path.join(str(target), "%(title)s.%(ext)s")
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "outtmpl": outtmpl,
            "format": option.selector,
            "progress_hooks": [self._progress_hook(on_progress)],
            "restrictfilenames": False,
            "windowsfilenames": True,
        }

        if option.kind == "audio":
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": audio_bitrate,
                }
            ]
        else:
            opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                final_path = self._resolve_final_path(ydl, info, option)
            on_done(
                {
                    "ok": True,
                    "path": final_path,
                    "folder": str(target),
                    "title": (info or {}).get("title", "video"),
                }
            )
        except FriendlyError as exc:
            on_done({"ok": False, "error": str(exc)})
        except yt_dlp.utils.DownloadError as exc:
            on_done({"ok": False, "error": _friendly_message(exc)})
        except Exception as exc:  # noqa: BLE001
            on_done({"ok": False, "error": _friendly_message(exc)})

    @staticmethod
    def _resolve_final_path(ydl, info, option: QualityOption) -> str:
        if not info:
            return ""
        try:
            path = ydl.prepare_filename(info)
        except Exception:
            return ""
        if option.kind == "audio":
            path = str(Path(path).with_suffix(".mp3"))
        else:
            path = str(Path(path).with_suffix(".mp4"))
        return path

"""Main application window."""

from __future__ import annotations

import threading
import time

import customtkinter as ctk

from . import styles as S
from .components import (
    Divider,
    FormatToggle,
    HistoryItem,
    ProgressView,
    SettingsDialog,
    Toast,
    VideoCard,
)
from downloader import (
    Downloader,
    FriendlyError,
    QualityOption,
    build_quality_options,
    extract_info,
)
from utils import history
from utils.helpers import ensure_dir, looks_like_url, open_folder

APP_TITLE = "YouTube Downloader"


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.settings = history.load_settings()
        ctk.set_appearance_mode(self.settings.get("appearance", "dark"))
        ctk.set_default_color_theme("dark-blue")  # base theme; we override colors

        self.title(APP_TITLE)
        self.geometry("720x800")
        self.minsize(560, 640)
        self.configure(fg_color=S.BG)

        self.fonts = S.Fonts()
        self.downloader = Downloader()

        # state
        self.info = None
        self.quality_options: dict[str, list[QualityOption]] = {"video": [], "audio": []}
        self._label_to_option: dict[str, QualityOption] = {}
        self._fetch_token = 0

        self._build_layout()
        self._refresh_history()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        # Scrollable body
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=S.PAD_EDGE - 8, pady=0)
        body.grid_columnconfigure(0, weight=1)
        self.body = body

        row = 0
        row = self._build_url_section(body, row)
        row = self._build_video_card(body, row)
        row = self._build_format_section(body, row)
        row = self._build_quality_section(body, row)
        row = self._build_folder_section(body, row)
        row = self._build_download_section(body, row)
        row = self._build_progress_section(body, row)
        row = self._build_history_section(body, row)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=64)
        header.grid(row=0, column=0, sticky="ew", padx=S.PAD_EDGE, pady=(S.PAD_EDGE, S.PAD))
        header.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkLabel(
            header, text=S.ICON_BRAND, font=self.fonts.icon_lg, text_color=S.ACCENT
        )
        brand.grid(row=0, column=0, padx=(0, S.PAD_SM))
        ctk.CTkLabel(
            header, text=APP_TITLE, font=self.fonts.heading, text_color=S.TEXT
        ).grid(row=0, column=1, sticky="w")

        # Appearance toggle
        self.mode_btn = ctk.CTkButton(
            header, text="☾" if self.settings.get("appearance") == "dark" else "☀",
            width=36, height=36, corner_radius=S.RADIUS_SM, font=self.fonts.icon,
            fg_color="transparent", hover_color=S.HOVER, border_width=1,
            border_color=S.BORDER, text_color=S.TEXT, command=self._toggle_mode,
        )
        self.mode_btn.grid(row=0, column=2, padx=(0, S.PAD_SM))

        ctk.CTkButton(
            header, text=S.ICON_SETTINGS, width=36, height=36, corner_radius=S.RADIUS_SM,
            font=self.fonts.icon, fg_color="transparent", hover_color=S.HOVER,
            border_width=1, border_color=S.BORDER, text_color=S.TEXT,
            command=self._open_settings,
        ).grid(row=0, column=3)

    def _build_url_section(self, parent, row: int) -> int:
        self._section_label(parent, "Video URL", row)
        row += 1
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", pady=(0, S.PAD_XS))
        wrap.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            wrap, height=S.INPUT_H, corner_radius=S.RADIUS_SM, font=self.fonts.body,
            placeholder_text="Paste a YouTube link…", border_color=S.BORDER,
            fg_color=S.SURFACE,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, S.PAD_SM))
        self.url_entry.bind("<Return>", lambda _e: self._fetch_info())

        ctk.CTkButton(
            wrap, text=f"{S.ICON_PASTE} Paste", width=90, height=S.INPUT_H,
            corner_radius=S.RADIUS_SM, font=self.fonts.body, fg_color="transparent",
            border_width=1, border_color=S.BORDER, text_color=S.TEXT,
            hover_color=S.HOVER, command=self._paste,
        ).grid(row=0, column=1)

        self.url_status = ctk.CTkLabel(
            parent, text="", font=self.fonts.small, text_color=S.TEXT_MUTED, anchor="w"
        )
        row += 1
        self.url_status.grid(row=row, column=0, sticky="w", pady=(0, S.PAD_SECTION))
        return row + 1

    def _build_video_card(self, parent, row: int) -> int:
        self.video_card = VideoCard(parent, self.fonts)
        # Hidden until info is fetched.
        self._video_card_row = row
        return row + 1

    def _build_format_section(self, parent, row: int) -> int:
        self._section_label(parent, "Format", row)
        row += 1
        self.format_toggle = FormatToggle(parent, self.fonts, command=self._on_format_change)
        self.format_toggle.grid(row=row, column=0, sticky="ew", pady=(0, S.PAD_SECTION))
        return row + 1

    def _build_quality_section(self, parent, row: int) -> int:
        self._section_label(parent, "Quality", row)
        row += 1
        self.quality_menu = ctk.CTkOptionMenu(
            parent, values=["—"], height=S.INPUT_H, corner_radius=S.RADIUS_SM,
            font=self.fonts.body, fg_color=S.SURFACE, button_color=S.SURFACE_2,
            button_hover_color=S.HOVER, text_color=S.TEXT, dropdown_font=self.fonts.body,
            dropdown_fg_color=S.SURFACE, dropdown_hover_color=S.HOVER,
            dropdown_text_color=S.TEXT,
        )
        self.quality_menu.grid(row=row, column=0, sticky="ew", pady=(0, S.PAD_SECTION))
        return row + 1

    def _build_folder_section(self, parent, row: int) -> int:
        self._section_label(parent, "Save to", row)
        row += 1
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=0, sticky="ew", pady=(0, S.PAD_SECTION))
        wrap.grid_columnconfigure(0, weight=1)
        self.folder_entry = ctk.CTkEntry(
            wrap, height=S.INPUT_H, corner_radius=S.RADIUS_SM, font=self.fonts.body,
            border_color=S.BORDER, fg_color=S.SURFACE,
        )
        self.folder_entry.insert(0, self.settings.get("download_folder", ""))
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, S.PAD_SM))
        ctk.CTkButton(
            wrap, text="Browse", width=90, height=S.INPUT_H, corner_radius=S.RADIUS_SM,
            font=self.fonts.body, fg_color="transparent", border_width=1,
            border_color=S.BORDER, text_color=S.TEXT, hover_color=S.HOVER,
            command=self._browse_folder,
        ).grid(row=0, column=1)
        return row + 1

    def _build_download_section(self, parent, row: int) -> int:
        self.download_btn = ctk.CTkButton(
            parent, text=f"{S.ICON_DOWNLOAD}  Download", height=S.BTN_PRIMARY_H,
            corner_radius=S.RADIUS_SM, font=self.fonts.subhead, fg_color=S.ACCENT,
            hover_color=S.ACCENT_HOVER, text_color=S.TEXT_ON_ACCENT,
            command=self._start_download,
        )
        self.download_btn.grid(row=row, column=0, sticky="ew", pady=(0, S.PAD_SECTION))
        return row + 1

    def _build_progress_section(self, parent, row: int) -> int:
        self.progress = ProgressView(parent, self.fonts)
        self._progress_row = row
        return row + 1

    def _build_history_section(self, parent, row: int) -> int:
        Divider(parent).grid(row=row, column=0, sticky="ew", pady=(S.PAD, S.PAD_SECTION))
        row += 1
        self._section_label(parent, "Recent downloads", row)
        row += 1
        self.history_box = ctk.CTkFrame(parent, fg_color="transparent")
        self.history_box.grid(row=row, column=0, sticky="ew", pady=(0, S.PAD_EDGE))
        self.history_box.grid_columnconfigure(0, weight=1)
        return row + 1

    def _section_label(self, parent, text: str, row: int) -> None:
        ctk.CTkLabel(
            parent, text=text, font=self.fonts.body_medium, text_color=S.TEXT_MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(0, S.PAD_SM))

    # ------------------------------------------------------------------ #
    # URL / info fetching
    # ------------------------------------------------------------------ #
    def _paste(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception:
            text = ""
        if text:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, text.strip())
            self._fetch_info()

    def _fetch_info(self) -> None:
        url = self.url_entry.get().strip()
        if not looks_like_url(url):
            self._set_url_status("Enter a valid http(s) link.", error=True)
            return
        self._fetch_token += 1
        token = self._fetch_token
        self._set_url_status("Fetching video info…", error=False)
        self._hide_video_card()

        def work():
            try:
                info = extract_info(url)
            except FriendlyError as exc:
                self.after(0, lambda: self._on_fetch_error(token, str(exc)))
                return
            self.after(0, lambda: self._on_fetch_done(token, info))

        threading.Thread(target=work, daemon=True).start()

    def _on_fetch_error(self, token: int, message: str) -> None:
        if token != self._fetch_token:
            return
        self._set_url_status(message, error=True)

    def _on_fetch_done(self, token: int, info) -> None:
        if token != self._fetch_token:
            return
        self.info = info
        self.quality_options = build_quality_options(info)
        self._set_url_status("Ready to download.", error=False)
        self.video_card.show(info)
        self._show_video_card()
        self._populate_quality(self.format_toggle.value)

    def _set_url_status(self, text: str, error: bool) -> None:
        self.url_status.configure(text=text, text_color=S.ERROR if error else S.TEXT_MUTED)

    def _show_video_card(self) -> None:
        self.video_card.grid(
            row=self._video_card_row, column=0, sticky="ew", pady=(0, S.PAD_SECTION)
        )

    def _hide_video_card(self) -> None:
        self.video_card.grid_remove()

    # ------------------------------------------------------------------ #
    # Format / quality
    # ------------------------------------------------------------------ #
    def _on_format_change(self, value: str) -> None:
        self._populate_quality(value)

    def _populate_quality(self, kind: str) -> None:
        options = self.quality_options.get(kind, [])
        if not options:
            self.quality_menu.configure(values=["—"])
            self.quality_menu.set("—")
            self._label_to_option = {}
            return
        self._label_to_option = {opt.label: opt for opt in options}
        labels = list(self._label_to_option.keys())
        self.quality_menu.configure(values=labels)
        # Prefer the user's default quality if present.
        default = self.settings.get("default_quality", "")
        chosen = next((l for l in labels if l.startswith(default)), labels[0])
        self.quality_menu.set(chosen)

    def _selected_option(self) -> QualityOption | None:
        return self._label_to_option.get(self.quality_menu.get())

    # ------------------------------------------------------------------ #
    # Folder
    # ------------------------------------------------------------------ #
    def _browse_folder(self) -> None:
        from tkinter import filedialog
        path = filedialog.askdirectory(initialdir=self.folder_entry.get() or None)
        if path:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, path)

    # ------------------------------------------------------------------ #
    # Download
    # ------------------------------------------------------------------ #
    def _start_download(self) -> None:
        if self.downloader.is_running:
            return
        if self.info is None:
            self._set_url_status("Fetch a video first.", error=True)
            return
        option = self._selected_option()
        if option is None:
            self._set_url_status("Pick a quality.", error=True)
            return
        folder = self.folder_entry.get().strip()
        try:
            ensure_dir(folder)
        except OSError as exc:
            self._set_url_status(f"Bad folder: {exc}", error=True)
            return

        bitrate = "192"
        if option.kind == "audio":
            bitrate = option.label.split()[0]  # "320 kbps" -> "320"

        self.progress.grid(row=self._progress_row, column=0, sticky="ew", pady=(0, S.PAD_SECTION))
        self.progress.reset()
        self.download_btn.configure(state="disabled", text="Downloading…")

        self._active = {
            "title": self.info.title,
            "url": self.info.url,
            "kind": option.kind,
            "quality": option.label.split()[0],
            "folder": folder,
        }

        try:
            self.downloader.start(
                url=self.info.url,
                option=option,
                out_dir=folder,
                audio_bitrate=bitrate,
                on_progress=lambda d: self.after(0, self.progress.update_progress, d),
                on_done=lambda r: self.after(0, self._on_download_done, r),
            )
        except FriendlyError as exc:
            self._reset_download_btn()
            self._set_url_status(str(exc), error=True)

    def _on_download_done(self, result: dict) -> None:
        self._reset_download_btn()
        ok = result.get("ok", False)
        if ok:
            self.progress.set_done(True, "Saved to your folder.")
            Toast(self, self.fonts, "Download complete", ok=True)
            entry = dict(self._active)
            entry.update({"status": "success", "path": result.get("path", ""),
                          "timestamp": time.time()})
            history.add_entry(entry)
            self._refresh_history()
            if self.settings.get("auto_open") and result.get("folder"):
                open_folder(result["folder"])
        else:
            msg = result.get("error", "Download failed.")
            self.progress.set_done(False, msg)
            Toast(self, self.fonts, msg, ok=False)
            entry = dict(self._active)
            entry.update({"status": "failed", "timestamp": time.time()})
            history.add_entry(entry)
            self._refresh_history()

    def _reset_download_btn(self) -> None:
        self.download_btn.configure(state="normal", text=f"{S.ICON_DOWNLOAD}  Download")

    # ------------------------------------------------------------------ #
    # History
    # ------------------------------------------------------------------ #
    def _refresh_history(self) -> None:
        for child in self.history_box.winfo_children():
            child.destroy()
        entries = history.recent(5)
        if not entries:
            ctk.CTkLabel(
                self.history_box, text="No downloads yet.", font=self.fonts.body,
                text_color=S.TEXT_MUTED, anchor="w",
            ).grid(row=0, column=0, sticky="w")
            return
        for i, entry in enumerate(entries):
            HistoryItem(self.history_box, self.fonts, entry).grid(
                row=i, column=0, sticky="ew", pady=(0, S.PAD_SM)
            )

    # ------------------------------------------------------------------ #
    # Settings / appearance
    # ------------------------------------------------------------------ #
    def _open_settings(self) -> None:
        SettingsDialog(self, self.fonts, self.settings, self._on_settings_saved)

    def _on_settings_saved(self, new_settings: dict) -> None:
        self.settings.update(new_settings)
        history.save_settings(self.settings)
        # Reflect new default folder if the field is empty/unchanged.
        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, self.settings.get("download_folder", ""))

    def _toggle_mode(self) -> None:
        new_mode = "light" if self.settings.get("appearance") == "dark" else "dark"
        self.settings["appearance"] = new_mode
        ctk.set_appearance_mode(new_mode)
        self.mode_btn.configure(text="☾" if new_mode == "dark" else "☀")
        history.save_settings(self.settings)

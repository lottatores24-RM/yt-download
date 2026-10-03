"""Reusable widgets: VideoCard, FormatToggle, ProgressView, HistoryItem,
Toast and SettingsDialog."""

from __future__ import annotations

import io
import threading
import time
from typing import Callable

import customtkinter as ctk

from . import styles as S
from utils.helpers import (
    format_bytes,
    format_count,
    format_duration,
    format_eta,
    format_speed,
    open_folder,
)

try:
    from PIL import Image
    import requests
    _IMAGING = True
except Exception:  # pragma: no cover - optional at runtime
    _IMAGING = False


# --------------------------------------------------------------------------- #
# Divider
# --------------------------------------------------------------------------- #
class Divider(ctk.CTkFrame):
    """A crisp 1px separator line."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=1, fg_color=S.BORDER, corner_radius=0, **kwargs)


# --------------------------------------------------------------------------- #
# Video preview card
# --------------------------------------------------------------------------- #
class VideoCard(ctk.CTkFrame):
    """Thumbnail (160x90) on the left, metadata on the right, 'Ready' badge."""

    def __init__(self, master, fonts: S.Fonts, **kwargs):
        super().__init__(
            master,
            fg_color=S.SURFACE,
            corner_radius=S.RADIUS,
            border_width=1,
            border_color=S.BORDER,
            **kwargs,
        )
        self.fonts = fonts
        self._thumb_image = None  # keep a reference

        self.grid_columnconfigure(1, weight=1)

        # Thumbnail placeholder
        self.thumb = ctk.CTkLabel(
            self,
            text="",
            width=S.THUMB_W,
            height=S.THUMB_H,
            fg_color=S.SURFACE_2,
            corner_radius=S.RADIUS_SM,
        )
        self.thumb.grid(row=0, column=0, rowspan=3, padx=(S.PAD, S.PAD), pady=S.PAD, sticky="nw")

        # Badge
        self.badge = ctk.CTkLabel(
            self,
            text="  Ready  ",
            font=fonts.small,
            text_color=S.TEXT_ON_ACCENT,
            fg_color=S.SUCCESS,
            corner_radius=S.RADIUS_SM,
        )
        self.badge.grid(row=0, column=1, padx=(0, S.PAD), pady=(S.PAD, 0), sticky="e")

        self.title = ctk.CTkLabel(
            self,
            text="",
            font=fonts.body_medium,
            text_color=S.TEXT,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        self.title.grid(row=0, column=1, padx=(0, S.PAD), pady=(S.PAD, 0), sticky="w")

        self.channel = ctk.CTkLabel(
            self, text="", font=fonts.body, text_color=S.TEXT_MUTED, anchor="w"
        )
        self.channel.grid(row=1, column=1, padx=(0, S.PAD), sticky="w")

        self.meta = ctk.CTkLabel(
            self, text="", font=fonts.small, text_color=S.TEXT_MUTED, anchor="w"
        )
        self.meta.grid(row=2, column=1, padx=(0, S.PAD), pady=(0, S.PAD), sticky="w")

    def show(self, info) -> None:
        self.title.configure(text=info.title)
        self.channel.configure(text=info.channel)
        meta_bits = []
        if info.duration:
            meta_bits.append(format_duration(info.duration))
        if info.view_count:
            meta_bits.append(f"{format_count(info.view_count)} views")
        self.meta.configure(text="   •   ".join(meta_bits) if meta_bits else "")
        self.thumb.configure(image=None, text="")
        if info.thumbnail and _IMAGING:
            threading.Thread(
                target=self._load_thumb, args=(info.thumbnail,), daemon=True
            ).start()

    def _load_thumb(self, url: str) -> None:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize((S.THUMB_W, S.THUMB_H))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(S.THUMB_W, S.THUMB_H))
            self._thumb_image = ctk_img
            self.thumb.after(0, lambda: self.thumb.configure(image=ctk_img, text=""))
        except Exception:
            self.thumb.after(
                0, lambda: self.thumb.configure(text=S.ICON_VIDEO, font=self.fonts.icon_lg)
            )


# --------------------------------------------------------------------------- #
# Format toggle (card-style, not radio buttons)
# --------------------------------------------------------------------------- #
class FormatToggle(ctk.CTkFrame):
    """Two selectable cards: Video (MP4) / Audio (MP3)."""

    def __init__(self, master, fonts: S.Fonts, command: Callable[[str], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.fonts = fonts
        self._command = command
        self._value = "video"

        self.grid_columnconfigure((0, 1), weight=1, uniform="fmt")

        self.card_video = self._make_card(
            0, "video", S.ICON_VIDEO, "Video", "MP4"
        )
        self.card_audio = self._make_card(
            1, "audio", S.ICON_AUDIO, "Audio", "MP3"
        )
        self._refresh()

    def _make_card(self, col, value, icon, title, subtitle):
        card = ctk.CTkFrame(
            self,
            fg_color=S.SURFACE,
            corner_radius=S.RADIUS,
            border_width=2,
            border_color=S.BORDER,
            height=64,
        )
        card.grid(row=0, column=col, padx=(0 if col == 0 else S.PAD_SM, 0), sticky="ew")
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)

        icon_lbl = ctk.CTkLabel(card, text=icon, font=self.fonts.icon, text_color=S.TEXT)
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=(S.PAD, S.PAD_SM), pady=S.PAD)
        title_lbl = ctk.CTkLabel(card, text=title, font=self.fonts.body_medium, text_color=S.TEXT, anchor="w")
        title_lbl.grid(row=0, column=1, sticky="sw", pady=(S.PAD, 0))
        sub_lbl = ctk.CTkLabel(card, text=subtitle, font=self.fonts.small, text_color=S.TEXT_MUTED, anchor="w")
        sub_lbl.grid(row=1, column=1, sticky="nw", pady=(0, S.PAD))

        widgets = (card, icon_lbl, title_lbl, sub_lbl)
        for w in widgets:
            w.bind("<Button-1>", lambda _e, v=value: self._select(v))
        card._parts = widgets  # type: ignore[attr-defined]
        return card

    def _select(self, value: str) -> None:
        if value == self._value:
            return
        self._value = value
        self._refresh()
        self._command(value)

    def _refresh(self) -> None:
        for value, card in (("video", self.card_video), ("audio", self.card_audio)):
            selected = value == self._value
            card.configure(border_color=S.ACCENT if selected else S.BORDER)
            card.configure(fg_color=S.SURFACE if selected else S.SURFACE)

    @property
    def value(self) -> str:
        return self._value


# --------------------------------------------------------------------------- #
# Progress view
# --------------------------------------------------------------------------- #
class ProgressView(ctk.CTkFrame):
    """8px progress bar + percentage, size, speed and ETA."""

    def __init__(self, master, fonts: S.Fonts, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.fonts = fonts
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        self.percent = ctk.CTkLabel(top, text="0%", font=fonts.body_medium, text_color=S.TEXT)
        self.percent.grid(row=0, column=0, sticky="w")
        self.size = ctk.CTkLabel(top, text="", font=fonts.small, text_color=S.TEXT_MUTED)
        self.size.grid(row=0, column=1, sticky="e")

        self.bar = ctk.CTkProgressBar(
            self, height=S.PROGRESS_H, corner_radius=S.PROGRESS_H,
            progress_color=S.ACCENT, fg_color=S.SURFACE_2,
        )
        self.bar.grid(row=1, column=0, sticky="ew", pady=(S.PAD_SM, S.PAD_XS))
        self.bar.set(0)

        self.stats = ctk.CTkLabel(self, text="", font=fonts.small, text_color=S.TEXT_MUTED, anchor="w")
        self.stats.grid(row=2, column=0, sticky="w")

    def reset(self) -> None:
        self.bar.set(0)
        self.percent.configure(text="0%")
        self.size.configure(text="")
        self.stats.configure(text="")

    def update_progress(self, data: dict) -> None:
        status = data.get("status")
        if status == "processing":
            self.bar.set(1.0)
            self.percent.configure(text="Processing…")
            self.stats.configure(text="Converting / merging file")
            return
        pct = data.get("percent", 0.0) or 0.0
        self.bar.set(pct)
        self.percent.configure(text=f"{pct * 100:.1f}%")
        downloaded = data.get("downloaded")
        total = data.get("total")
        if total:
            self.size.configure(text=f"{format_bytes(downloaded)} / {format_bytes(total)}")
        speed = format_speed(data.get("speed"))
        eta = format_eta(data.get("eta"))
        self.stats.configure(text=f"Speed {speed}    •    ETA {eta}")

    def set_done(self, ok: bool, message: str) -> None:
        self.bar.set(1.0 if ok else self.bar.get())
        self.percent.configure(
            text=("Done" if ok else "Failed"),
            text_color=S.SUCCESS if ok else S.ERROR,
        )
        self.bar.configure(progress_color=S.SUCCESS if ok else S.ERROR)
        self.stats.configure(text=message, text_color=S.SUCCESS if ok else S.ERROR)


# --------------------------------------------------------------------------- #
# History row
# --------------------------------------------------------------------------- #
class HistoryItem(ctk.CTkFrame):
    """One history row: status icon, title, meta, 'Open folder' button."""

    def __init__(self, master, fonts: S.Fonts, entry: dict, **kwargs):
        super().__init__(
            master, fg_color=S.SURFACE, corner_radius=S.RADIUS_SM,
            border_width=1, border_color=S.BORDER, **kwargs,
        )
        self.fonts = fonts
        self.entry = entry
        self.grid_columnconfigure(1, weight=1)

        ok = entry.get("status") == "success"
        icon = ctk.CTkLabel(
            self,
            text=S.ICON_CHECK if ok else S.ICON_CROSS,
            font=fonts.body_medium,
            text_color=S.SUCCESS if ok else S.ERROR,
            width=20,
        )
        icon.grid(row=0, column=0, rowspan=2, padx=(S.PAD_SM, S.PAD_SM), pady=S.PAD_SM)

        title = ctk.CTkLabel(
            self, text=entry.get("title", "Unknown"), font=fonts.body,
            text_color=S.TEXT, anchor="w",
        )
        title.grid(row=0, column=1, sticky="w", pady=(S.PAD_SM, 0))

        bits = [entry.get("kind", "").upper()]
        if entry.get("quality"):
            bits.append(entry["quality"])
        when = entry.get("timestamp")
        if when:
            bits.append(time.strftime("%b %d, %H:%M", time.localtime(when)))
        meta = ctk.CTkLabel(
            self, text="   •   ".join(b for b in bits if b),
            font=fonts.small, text_color=S.TEXT_MUTED, anchor="w",
        )
        meta.grid(row=1, column=1, sticky="w", pady=(0, S.PAD_SM))

        if ok and entry.get("folder"):
            btn = ctk.CTkButton(
                self, text=f"{S.ICON_FOLDER} Open folder", font=fonts.small,
                width=110, height=28, corner_radius=S.RADIUS_SM,
                fg_color="transparent", hover_color=S.HOVER,
                border_width=1, border_color=S.BORDER, text_color=S.TEXT,
                command=lambda: open_folder(entry["folder"]),
            )
            btn.grid(row=0, column=2, rowspan=2, padx=(0, S.PAD_SM))


# --------------------------------------------------------------------------- #
# Toast notification (bottom-right)
# --------------------------------------------------------------------------- #
class Toast(ctk.CTkToplevel):
    """A transient notification in the bottom-right of the parent window."""

    def __init__(self, master, fonts: S.Fonts, message: str, ok: bool = True, duration: int = 3500):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.0)
        except Exception:
            pass

        frame = ctk.CTkFrame(
            self, fg_color=S.SURFACE, corner_radius=S.RADIUS,
            border_width=1, border_color=S.BORDER,
        )
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        ctk.CTkLabel(
            frame, text=S.ICON_CHECK if ok else S.ICON_CROSS,
            font=fonts.subhead, text_color=S.SUCCESS if ok else S.ERROR,
        ).grid(row=0, column=0, padx=(S.PAD, S.PAD_SM), pady=S.PAD)
        ctk.CTkLabel(
            frame, text=message, font=fonts.body, text_color=S.TEXT, anchor="w",
        ).grid(row=0, column=1, padx=(0, S.PAD), pady=S.PAD, sticky="w")

        self.update_idletasks()
        self._place(master)
        self._fade_in()
        self.after(duration, self._fade_out)

    def _place(self, master) -> None:
        master.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = master.winfo_rootx() + master.winfo_width() - w - 24
        y = master.winfo_rooty() + master.winfo_height() - h - 24
        self.geometry(f"+{x}+{y}")

    def _fade_in(self, value: float = 0.0) -> None:
        try:
            self.attributes("-alpha", value)
        except Exception:
            return
        if value < 1.0:
            self.after(15, lambda: self._fade_in(min(value + 0.1, 1.0)))

    def _fade_out(self, value: float = 1.0) -> None:
        try:
            self.attributes("-alpha", value)
        except Exception:
            self.destroy()
            return
        if value <= 0:
            self.destroy()
            return
        self.after(15, lambda: self._fade_out(value - 0.1))


# --------------------------------------------------------------------------- #
# Settings dialog
# --------------------------------------------------------------------------- #
class SettingsDialog(ctk.CTkToplevel):
    """Modal-ish settings window."""

    def __init__(self, master, fonts: S.Fonts, settings: dict, on_save: Callable[[dict], None]):
        super().__init__(master)
        self.title("Settings")
        self.geometry("440x340")
        self.resizable(False, False)
        self.configure(fg_color=S.BG)
        self.fonts = fonts
        self._on_save = on_save
        self._settings = dict(settings)

        self.grid_columnconfigure(0, weight=1)
        pad = {"padx": S.PAD_EDGE, "pady": (S.PAD_SM, 0)}

        ctk.CTkLabel(self, text="Settings", font=fonts.heading, text_color=S.TEXT).grid(
            row=0, column=0, sticky="w", padx=S.PAD_EDGE, pady=(S.PAD_EDGE, S.PAD)
        )

        # Default folder
        ctk.CTkLabel(self, text="Default download folder", font=fonts.small,
                     text_color=S.TEXT_MUTED).grid(row=1, column=0, sticky="w", **pad)
        folder_row = ctk.CTkFrame(self, fg_color="transparent")
        folder_row.grid(row=2, column=0, sticky="ew", padx=S.PAD_EDGE)
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_entry = ctk.CTkEntry(folder_row, height=S.INPUT_H, corner_radius=S.RADIUS_SM,
                                         font=fonts.body, border_color=S.BORDER)
        self.folder_entry.insert(0, settings.get("download_folder", ""))
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, S.PAD_SM))
        ctk.CTkButton(folder_row, text="Browse", width=80, height=S.INPUT_H,
                      corner_radius=S.RADIUS_SM, font=fonts.body, fg_color="transparent",
                      border_width=1, border_color=S.BORDER, text_color=S.TEXT,
                      hover_color=S.HOVER, command=self._browse).grid(row=0, column=1)

        # Default quality
        ctk.CTkLabel(self, text="Default quality", font=fonts.small,
                     text_color=S.TEXT_MUTED).grid(row=3, column=0, sticky="w", **pad)
        self.quality_menu = ctk.CTkOptionMenu(
            self, values=["1080p", "720p", "480p", "360p", "Best available"],
            height=S.INPUT_H, corner_radius=S.RADIUS_SM, font=fonts.body,
            fg_color=S.SURFACE_2, button_color=S.SURFACE_2, button_hover_color=S.HOVER,
            text_color=S.TEXT, dropdown_font=fonts.body,
        )
        self.quality_menu.set(settings.get("default_quality", "720p"))
        self.quality_menu.grid(row=4, column=0, sticky="w", padx=S.PAD_EDGE)

        # Auto-open switch
        self.auto_open = ctk.CTkSwitch(
            self, text="Open folder automatically after download",
            font=fonts.body, text_color=S.TEXT, progress_color=S.ACCENT,
        )
        if settings.get("auto_open"):
            self.auto_open.select()
        self.auto_open.grid(row=5, column=0, sticky="w", padx=S.PAD_EDGE, pady=(S.PAD, 0))

        # Save button
        ctk.CTkButton(
            self, text="Save", height=S.BTN_SECONDARY_H, corner_radius=S.RADIUS_SM,
            font=fonts.body_medium, fg_color=S.ACCENT, hover_color=S.ACCENT_HOVER,
            text_color=S.TEXT_ON_ACCENT, command=self._save,
        ).grid(row=6, column=0, sticky="ew", padx=S.PAD_EDGE, pady=S.PAD_EDGE)

        self.after(50, self._focus)

    def _focus(self):
        try:
            self.grab_set()
            self.lift()
        except Exception:
            pass

    def _browse(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(initialdir=self.folder_entry.get() or None)
        if path:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, path)

    def _save(self):
        self._settings.update(
            {
                "download_folder": self.folder_entry.get().strip(),
                "default_quality": self.quality_menu.get(),
                "auto_open": bool(self.auto_open.get()),
            }
        )
        self._on_save(self._settings)
        self.destroy()

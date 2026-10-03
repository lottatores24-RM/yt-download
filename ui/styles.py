"""Design tokens: colors, spacing, radius and typography.

Colors are expressed as (light_mode, dark_mode) tuples, which customtkinter
resolves automatically based on the active appearance mode.
"""

from __future__ import annotations

import customtkinter as ctk

# --------------------------------------------------------------------------- #
# Brand / accent  (used ONLY for brand icon + primary buttons)
# --------------------------------------------------------------------------- #
ACCENT = "#FF0033"
ACCENT_HOVER = "#D60029"

# --------------------------------------------------------------------------- #
# Neutral surfaces  (light, dark)
# --------------------------------------------------------------------------- #
BG = ("#F4F4F5", "#0F0F0F")          # window background
SURFACE = ("#FFFFFF", "#1B1B1B")     # cards / panels
SURFACE_2 = ("#ECECEE", "#262626")   # inset elements, dropdowns
BORDER = ("#E2E2E5", "#2E2E2E")      # 1px separators / outlines
HOVER = ("#E8E8EA", "#2A2A2A")

# Text
TEXT = ("#0F0F0F", "#F2F2F2")
TEXT_MUTED = ("#5F5F66", "#A8A8A8")
TEXT_ON_ACCENT = "#FFFFFF"

# Status
SUCCESS = ("#1B873F", "#3FB95C")
ERROR = ("#C5221F", "#FF6B6B")

# --------------------------------------------------------------------------- #
# Spacing
# --------------------------------------------------------------------------- #
PAD_EDGE = 24      # window edges
PAD_SECTION = 16   # between sections
PAD = 12
PAD_SM = 8
PAD_XS = 4

# --------------------------------------------------------------------------- #
# Radius
# --------------------------------------------------------------------------- #
RADIUS = 12        # cards
RADIUS_SM = 8      # buttons, inputs

# --------------------------------------------------------------------------- #
# Sizes
# --------------------------------------------------------------------------- #
BTN_PRIMARY_H = 44
BTN_SECONDARY_H = 36
INPUT_H = 36
PROGRESS_H = 8
THUMB_W = 160
THUMB_H = 90

# --------------------------------------------------------------------------- #
# Typography
# --------------------------------------------------------------------------- #
FONT_FAMILY = "Segoe UI"
SIZE_BODY = 13
SIZE_SMALL = 12
SIZE_HEADING = 18
SIZE_SUBHEAD = 16


class Fonts:
    """CTkFont instances. Must be built after the root window exists."""

    def __init__(self) -> None:
        self.body = ctk.CTkFont(family=FONT_FAMILY, size=SIZE_BODY, weight="normal")
        self.body_medium = ctk.CTkFont(family=FONT_FAMILY, size=SIZE_BODY, weight="bold")
        self.small = ctk.CTkFont(family=FONT_FAMILY, size=SIZE_SMALL, weight="normal")
        self.heading = ctk.CTkFont(family=FONT_FAMILY, size=SIZE_HEADING, weight="bold")
        self.subhead = ctk.CTkFont(family=FONT_FAMILY, size=SIZE_SUBHEAD, weight="bold")
        self.icon = ctk.CTkFont(family=FONT_FAMILY, size=18, weight="normal")
        self.icon_lg = ctk.CTkFont(family=FONT_FAMILY, size=22, weight="normal")


# --------------------------------------------------------------------------- #
# Clean unicode glyphs used as icons (no emoji).
# Drop-in PNG icons can replace these later via CTkImage.
# --------------------------------------------------------------------------- #
ICON_DOWNLOAD = "⤓"   # ⤓ downwards arrow to bar
ICON_SETTINGS = "⚙"   # ⚙ gear
ICON_FOLDER = "▸"     # ▸ (used before "Open folder")
ICON_PASTE = "⧉"      # ⧉ two joined squares
ICON_VIDEO = "▶"      # ▶ play
ICON_AUDIO = "♪"      # ♪ note
ICON_CHECK = "✔"      # ✔
ICON_CROSS = "✖"      # ✖
ICON_BRAND = "▶"      # ▶ brand mark

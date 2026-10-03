"""Entry point for the YouTube Downloader desktop app."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from ui.app import App
    except ModuleNotFoundError as exc:
        print(
            "Missing dependency:", exc,
            "\n\nInstall requirements first:\n"
            "    pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

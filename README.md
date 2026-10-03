# YouTube Downloader

A clean, modern desktop app for downloading YouTube videos (MP4) or audio (MP3)
on Windows, built with [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
and [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Screenshots

A single-column 720×800 window:

- **Header** — red brand mark, "YouTube Downloader" title, a dark/light mode
  toggle and a settings gear.
- **Video URL** field with a *Paste* button, and a status line underneath.
- **Video preview card** — 160×90 thumbnail on the left; title, channel and
  `duration • views` on the right; a green *Ready* badge.
- **Format** — two card-style buttons (Video / Audio); the selected one gets a
  red border.
- **Quality** dropdown (e.g. `1080p (~50 MB)`) and a **Save to** folder field.
- A full-width red **Download** button, followed by the live progress bar.
- **Recent downloads** list with success/failed icons and *Open folder* buttons.

The default theme is dark; light mode is one click away. YouTube red is used
only on the brand mark, the selected-format border and the primary button.

## Features

- **Paste a link** and auto-fetch video info: thumbnail, title, channel, duration, views
- **Format toggle** — Video (MP4) or Audio (MP3) as card-style buttons
- **Dynamic quality dropdown** built from the formats the video actually offers, with estimated file size
- **Folder picker** (defaults to `~/Videos/YT-Downloads`, auto-created)
- **Full-width Download button** with a real-time **progress bar** — percentage, size (X MB / Y MB), speed (MB/s) and ETA
- **History panel** showing the last 5 downloads with success/failed status and an *Open folder* button
- **Friendly error messages** for private/unavailable videos, bad URLs and network problems — never a stack trace
- **Toast notification** in the bottom-right when a download finishes
- **Settings dialog** (gear icon): default folder, default quality, "open folder automatically after download"
- **Dark & light mode** with a one-click toggle; YouTube-red accent used only on the brand mark and primary button
- Downloads run on a background thread, so the UI never freezes

History and settings are stored in `~/.yt_downloader/` (`history.json`, `settings.json`).

## Requirements

- **Python 3.10+** (3.12 recommended). On Windows, Python from
  [python.org](https://www.python.org/downloads/) already includes Tkinter.
- **ffmpeg** — required to convert audio to MP3 and to merge high-resolution
  video + audio streams.

### Installing ffmpeg on Windows

The simplest option is winget (built into Windows 10/11):

```powershell
winget install Gyan.FFmpeg
```

Or with [Chocolatey](https://chocolatey.org/):

```powershell
choco install ffmpeg
```

Or download a build from <https://www.gyan.dev/ffmpeg/builds/>, unzip it, and
add the `bin` folder to your `PATH`. Verify with:

```powershell
ffmpeg -version
```

## Install & run

### Easiest — double-click `run.bat`

On first launch `run.bat` creates a virtual environment, installs the
dependencies, and starts the app. After that it just launches the app.

### Manual

```powershell
# from the project folder
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## How to use

1. Copy a YouTube link, then click **Paste** (or type it and press Enter).
2. The video preview card appears with the thumbnail and details.
3. Choose **Video** or **Audio**, then pick a **quality**.
4. Confirm the **Save to** folder (or click *Browse*).
5. Click **Download** and watch the progress bar.
6. When it finishes you get a toast, and the download appears in *Recent downloads*.

## Project structure

```
yt-download/
├── main.py              # entry point
├── downloader.py        # yt-dlp wrapper + threaded download
├── ui/
│   ├── app.py           # main window
│   ├── components.py    # VideoCard, FormatToggle, ProgressView, HistoryItem, Toast, SettingsDialog
│   └── styles.py        # color tokens, spacing, typography
├── utils/
│   ├── history.py       # read/write history & settings JSON
│   └── helpers.py       # format bytes/duration/speed, open folder, etc.
├── requirements.txt
├── run.bat              # Windows launcher
└── README.md
```

## Notes

- Built and visually verified on Linux (headless, via Xvfb) and designed for
  Windows. The GUI uses Tkinter under the hood, so it runs anywhere Python +
  Tkinter are available (Windows, macOS, Linux).
- yt-dlp is updated frequently; if a download fails after YouTube changes
  something, update it with `pip install -U yt-dlp`.

# Relay — System Architecture & Specifications

**Relay** is a simplified, local-first workflow engine and automation platform designed to move content between platforms (e.g., Instagram, YouTube, TikTok, Reddit) with headless or headful browser automation.

---

## 1. High-Level Directory Structure

Relay is structured into modular components:

```
relay/
├── apps/                      # Platform-specific integration layers
│   ├── instagram.py           # Instagram Reel downloads and metadata parsing
│   ├── youtube.py             # YouTube Studio upload orchestration
│   ├── tiktok.py              # TikTok-specific logic
│   └── reddit.py              # Reddit-specific logic
├── automation/                # Core automation drivers and utilities
│   ├── browser.py             # Persistent, stealth Playwright Chrome manager
│   ├── downloader.py          # yt-dlp media downloader and transcoder
│   └── uploader.py            # Automation actions and helpers
├── cli/                       # Command-line interface and interactive menus
│   └── main.py                # Typer CLI application and user inputs
├── pipelines/                 # Multi-app automated workflows
│   ├── insta_to_youtube.py    # Pipeline connecting Instagram and YouTube Studio
│   ├── tiktok_to_shorts.py    # Pipeline connecting TikTok and YouTube Shorts
│   └── custom.py              # Extensible placeholder pipeline
├── docs/                      # Project documentation
│   └── ARCHITECTURE.md        # System architecture specification (this file)
├── examples/                  # Ready-to-run configurations or definitions
├── tests/                     # Automated test suites
├── pyproject.toml             # Project dependencies and packaging settings
└── uv.lock                    # Locked python packages (via uv)
```

---

## 2. Core Components & Responsibilities

### A. Apps Layer (`apps/`)
Orchestrates high-level business flows for each platform.
- **`instagram.py`**: Extracts Reel IDs, sanitizes target names, downloads media via standard helpers, and retrieves description metadata.
- **`youtube.py`**: Interacts with YouTube Studio in headful browser sessions to upload videos, waiting dynamically for UI components to load.

### B. Automation Layer (`automation/`)
Implements low-level utility engines and browser automation wrappers.
- **`browser.py`**: Controls Chromium/Chrome via Playwright, supporting persistent contexts (`launch_persistent_context`) with real browser channels (`channel="chrome"`) and stealth scripts (stripping `navigator.webdriver` markers) to bypass bot protection.
- **`downloader.py`**: Invokes `yt-dlp` subprocesses to pull original high-quality video files and handles transcode/padding fallbacks.

### C. Pipelines Layer (`pipelines/`)
Defines the sequential flow of tasks (Download -> Transcode -> Log in -> Upload) connecting apps and automation.
- Pipelines are run dynamically based on CLI selection.

### D. CLI Layer (`cli/`)
Handles interactive user queries, URL validation, choice routing, and clean error displays.

---

## 3. Session & Data Persistence

- **Browser Sessions**: Stored persistently in `~/.relay/profiles/<profile_name>_chrome_data/` to retain Google authentication tokens, avoiding repetitive logins.
- **Media Files**: Cleaned and downloaded locally into the sandbox directory `~/.relay/media/`.

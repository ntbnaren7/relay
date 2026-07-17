# Relay — System Architecture & Specifications

**Relay** is a local-first, open-source workflow automation tool that downloads content from social media platforms and reposts it to YouTube Studio — entirely from your own machine, with no cloud servers.

---

## 1. High-Level Directory Structure

```
relay/
├── apps/                       # Platform integration adapters
│   ├── instagram.py            # Instagram Reel metadata extraction + download
│   ├── youtube.py              # YouTube Studio browser-based upload
│   └── tiktok.py               # TikTok video download
├── automation/                 # Core automation drivers and utilities
│   ├── browser.py              # Playwright Chromium manager (stealth, profiles, auto-install)
│   ├── downloader.py           # yt-dlp media downloader + FFmpeg transcoder
│   └── media_utils.py          # Upload validation and progress helpers
├── cli/                        # Command-line interface
│   ├── main.py                 # Typer CLI: run, list, vault, update commands
│   ├── update.py               # Self-update engine for standalone binaries
│   └── version.py              # Single source of truth for version string
├── pipelines/                  # Multi-step automated workflows
│   ├── insta_to_youtube.py     # Instagram Reel → YouTube Studio
│   ├── tiktok_to_shorts.py     # TikTok Video → YouTube Shorts
│   └── custom.py               # Scaffold for user-defined async pipelines
├── tests/                      # Automated test suite
├── docs/                       # Project documentation
├── examples/                   # Aspirational workflow definitions (not yet executable)
├── relay.spec                  # PyInstaller build spec for standalone binary
├── install.sh                  # One-liner installer for macOS/Linux
├── install.ps1                 # One-liner installer for Windows
├── pyproject.toml              # Project metadata and dependencies
└── uv.lock                     # Locked dependency manifest (via uv)
```

---

## 2. Core Components & Responsibilities

### A. Apps Layer (`apps/`)
High-level adapters that speak the language of each platform.

- **`instagram.py`**: Validates Instagram post URLs, extracts `og:title`/`og:description` metadata via Playwright, and delegates download to `automation/downloader.py`.
- **`youtube.py`**: Controls YouTube Studio in a real Chromium session — navigates to the Upload dialog, attaches the video file, and waits for user confirmation to publish. Requires `browser_manager` to perform a real upload.
- **`tiktok.py`**: Delegates TikTok download to `automation/downloader.py`.

### B. Automation Layer (`automation/`)
Low-level engines that do the actual work.

- **`browser.py`**: Manages Chromium via Playwright. Uses `launch_persistent_context` with a real `channel="chrome"` Chrome install and anti-bot stealth scripts (`navigator.webdriver = undefined`). Profiles (cookies/sessions) are stored in `~/.relay/profiles/<name>_chrome_data/`. Also contains `ensure_playwright_browsers()` which automatically installs Chromium on first run if not present.
- **`downloader.py`**: Uses `yt_dlp` Python library (primary) → `yt-dlp` CLI executable (secondary) → local stub bytes (offline fallback for tests). Also provides `transcode_video()` via FFmpeg with a copy-fallback.
- **`media_utils.py`**: `verify_file_for_upload()` validates file readiness; `format_progress_message()` produces consistent progress strings.

### C. Pipelines Layer (`pipelines/`)
Sequential workflow orchestrators connecting apps and automation.

Each pipeline exposes a single `async def run(url, ..., progress_callback)` coroutine:

1. **`insta_to_youtube`**: Download Reel → Transcode → Upload to YouTube Studio
2. **`tiktok_to_shorts`**: Download TikTok Video → Upload to YouTube Studio
3. **`custom`**: Scaffold for user-supplied async functions

### D. CLI Layer (`cli/`)
User-facing entry point for all operations.

| Command | Description |
|---------|-------------|
| `relay` | Interactive pipeline selector (no arguments) |
| `relay run <pipeline> --url <url>` | Run a pipeline directly |
| `relay list` | Show all available pipelines |
| `relay vault set <svc> <key> <val>` | Store a credential (OS Keyring or `~/.relay/secrets.json`) |
| `relay vault get <svc> <key>` | Retrieve a stored credential |
| `relay vault list` | List all stored services and keys |
| `relay update` | Self-update the standalone binary |
| `relay --version` | Print the installed version |

---

## 3. Session & Data Persistence

| Data | Location |
|------|----------|
| Browser sessions (cookies/auth) | `~/.relay/profiles/<name>_chrome_data/` |
| Downloaded media files | `~/.relay/media/` |
| Credentials (fallback, no keyring) | `~/.relay/secrets.json` (mode 0600) |
| Update check cache | `~/.relay/update_cache.json` |

---

## 4. Binary Distribution

Relay is distributed as a standalone PyInstaller binary. GitHub Actions builds for:
- `relay-macos-arm64` (Apple Silicon)
- `relay-macos-x64` (Intel Mac)
- `relay-ubuntu-x64` (Linux)
- `relay-windows-x64.exe` (Windows)

Playwright Chromium is **not** bundled in the binary. On first pipeline run, `_ensure_playwright_browsers()` in `cli/main.py` detects if Chromium is missing and runs `playwright install chromium` automatically (~130 MB, one-time download).

---

## 5. Credential Security Model

1. **Primary**: OS Keyring (`macOS Keychain`, `Windows Credential Manager`, `libsecret` on Linux)
2. **Fallback**: `~/.relay/secrets.json` with file permissions `0600` (owner-read-only)
3. **Migration**: On startup, any existing plaintext `secrets.json` entries are automatically migrated to the OS Keyring and the file is deleted

Passwords are never stored in plain text if the OS Keyring is available.

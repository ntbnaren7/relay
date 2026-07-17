# Relay

**Relay** is a local-first, open-source automation engine for building composable workflows across applications and services.

## 🚀 Download & Install

You don't need Python or any dependencies installed. Run this single command to download the standalone binary:

**macOS & Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/ntbnaren7/relay/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr https://raw.githubusercontent.com/ntbnaren7/relay/main/install.ps1 -useb | iex
```

Once installed, simply type `relay` in your terminal! Relay will automatically check for updates and can be upgraded seamlessly anytime by running `relay update`.

---

Rather than solving a single automation task, Relay provides a modular execution engine where every action—downloading, transforming, generating, uploading, or notifying—is represented as a reusable **Step**. Workflows are composed as Directed Acyclic Graphs (DAGs), allowing complex automations to be built from simple, independent components.

The first supported workflow is:

```text
Instagram URL
      ↓
 Download Media
      ↓
 Upload to YouTube Studio
```

…but Relay is designed to grow far beyond this into a general-purpose automation platform capable of orchestrating workflows across browsers, desktop applications, cloud services, APIs, and local tools.

## Core Principles

* 🏠 Local-first & privacy by default
* 🧩 Plugin-driven architecture
* ⚡ Event-driven execution engine
* 🔧 Composable, reusable Steps
* 🖥️ Cross-platform (Windows, macOS & Linux)
* 📦 Extensible by design

## Security & Privacy

* **100% Local-First:** All execution happens locally on your machine. Absolutely zero data, session cookies, or credentials are ever sent to external servers or cloud providers.
* **Encrypted Credential Vault:** Credentials managed via `relay vault` (`set` and `get`) are stored directly inside your operating system's built-in secure credential store (macOS Keychain, Windows Credential Manager, or Linux Secret Service) using the `keyring` library.
* **Seamless Fallback & Migration:** If an OS keychain is unavailable (e.g., in headless CI/CD containers), Relay securely falls back to a permission-locked local file (`~/.relay/secrets.json` with `0o600` permissions). Any existing plaintext credentials are automatically migrated to your OS Keyring on first access and wiped from disk.

> **Status:** 🚀 Active alpha. Core platforms (`instagram`, `youtube`, `tiktok`, `reddit`), automation engines (`browser`, `downloader`, `uploader`), and pipelines are functional.

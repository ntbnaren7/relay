# Relay

**Relay** is a local-first, open-source automation engine for building composable workflows across applications and services.

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

> **Status:** 🚀 Active alpha. Core platforms (`instagram`, `youtube`, `tiktok`, `reddit`), automation engines (`browser`, `downloader`, `uploader`), and pipelines are functional.

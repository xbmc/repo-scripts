<div align="center">
  <img src="icon.png" width="128" height="128" alt="OpenSubtitles.com Logo" />
  <h1>OpenSubtitles.com for Kodi</h1>
  <p><strong>Official subtitle add-on for Kodi media center powered by the OpenSubtitles.com REST API.</strong></p>

  <p>
    <a href="https://kodi.tv"><img src="https://img.shields.io/badge/Kodi-19%20%7C%2020%20%7C%2021%20%7C%2022-blue.svg?logo=kodi&logoColor=white" alt="Kodi Versions" /></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.x-3776AB.svg?logo=python&logoColor=white" alt="Python 3" /></a>
    <a href="https://github.com/opensubtitles-dev/service.subtitles.opensubtitles-com/releases/latest"><img src="https://img.shields.io/github/v/release/opensubtitles-dev/service.subtitles.opensubtitles-com?label=Release&color=0284c7" alt="Latest Release" /></a>
    <a href="https://github.com/opensubtitles-dev/service.subtitles.opensubtitles-com/actions/workflows/addon-check.yml"><img src="https://img.shields.io/github/actions/workflow/status/opensubtitles-dev/service.subtitles.opensubtitles-com/addon-check.yml?branch=master&label=Kodi%20Validation" alt="Validation Status" /></a>
    <a href="LICENSE.txt"><img src="https://img.shields.io/badge/License-GPL--2.0-green.svg" alt="License" /></a>
  </p>

  <p>Search and download subtitles for movies and TV shows from <a href="https://www.opensubtitles.com">OpenSubtitles.com</a>. Access over <strong>10,000,000+ subtitles</strong> across <strong>100+ languages</strong> with daily updates.</p>
</div>

---

## ✨ Features

- 🔍 **Smart Multi-Identifier Search**: Automatically searches via IMDb ID, TMDb ID, or TV show/episode metadata.
- ⚡ **Guessit Filename Analysis**: Integrates `/api/v1/utilities/guessit` with 30-day client-side caching for precise release matching.
- 👑 **VIP & Quota Management**: Built-in **Test Connection** with live VIP badge, remaining daily downloads quota counter, and 24-hour verification.
- ⏱️ **Fast Search Caching**: Configurable search cache duration (default 180 minutes) to eliminate duplicate network calls and speed up browsing.
- 🛡️ **Advanced Filters**: Customizable settings to include/exclude Hearing Impaired (HI), Foreign Parts Only, Machine Translated, and AI Translated subtitles.
- 🔒 **Security & Privacy**: Zero logging of user credentials, session tokens, or API keys in the Kodi debug log.
- 🌐 **Full UTF-8 Diacritics Support**: Unicode normalization (NFC) ensures international film and TV show titles match seamlessly.

---

## 📥 Installation

### Option A: Install via OpenSubtitles Repository (Recommended for Fast Updates)

> [!TIP]
> Installing via our official repository ensures you automatically receive instant updates, new features, and bug fixes without waiting for upstream Kodi mirror approval cycles.

1. In Kodi, enable **Unknown sources** under **Settings (⚙️) ➔ System ➔ Add-ons**.
2. Go to **Settings (⚙️) ➔ File manager**.
3. Click **Add source**.
4. Set the path to:
   ```
   https://kodi.opensubtitles.com
   ```
5. Name the source **`OpenSubtitles-repo`** and click **OK**.
6. Navigate to **Add-ons** (box icon at top left).
7. Select **Install from zip file ➔ OpenSubtitles-repo**.
8. Select **`repository.opensubtitles-com.zip`** and wait for the installation notification.
9. Go to **Install from repository ➔ OpenSubtitles.com Official Repository ➔ Subtitles ➔ OpenSubtitles.com**.
10. Click **Install**.
11. You can now disable **Unknown sources** again (step 1) — it is only needed for the one-time zip install; repository updates work without it.

---

### Option B: Install via Official Kodi Repository

1. In Kodi, go to **Add-ons ➔ Install from repository**.
2. Select **Kodi Add-on repository ➔ Subtitles ➔ OpenSubtitles.com**.
3. Click **Install**.

---

## ⚙️ Configuration & Setup

1. Open add-on **Settings (Login Details)**:
   * Enter your OpenSubtitles.com **Username** and **Password** (use your username, not your email address).
   * Click **Test Connection** to verify your account credentials, VIP status, and daily download quota.
2. In Kodi, navigate to **Settings ➔ Player ➔ Language ➔ Subtitle Services**:
   * Set **Default movie service** to **OpenSubtitles.com**.
   * Set **Default TV show service** to **OpenSubtitles.com**.

---

## 📚 Developer & Contributor Documentation

- 🛠️ [Developer Workflow & Fast Testing Guide](https://github.com/opensubtitles/service.subtitles.opensubtitles-com/blob/master/docs/DEV_WORKFLOW.md)
- 📋 [Kodi Standards & Repo Submission Rules](https://github.com/opensubtitles/service.subtitles.opensubtitles-com/blob/master/docs/KODI_STANDARDS.md)
- 🤖 [AI Agent Architecture & Guidelines](https://github.com/opensubtitles/service.subtitles.opensubtitles-com/blob/master/docs/AGENT_INSTRUCTIONS.md)
- 🗺️ [Project Roadmap & Feature Backlog](https://github.com/opensubtitles/service.subtitles.opensubtitles-com/blob/master/docs/TODO.md)
- 📜 [Full Release Changelog](https://github.com/opensubtitles/service.subtitles.opensubtitles-com/blob/master/CHANGELOG.md)

---

## 🆕 What's New — everything since the official Kodi repo version (v1.0.9)

The official Kodi repository still ships **v1.0.9**. The current release is **v1.0.90** —
forty releases of work. If you are coming from the Kodi repo version, this is
effectively a new add-on:

### 🔍 Search & matching
- **Smart release matcher** — subtitles scored against your video: exact file hash first, then release group, source/cut, resolution, codec; best match on top with a score badge. Purely reordering, nothing hidden.
- **Multi-language top picks** — the best match for each preferred language promoted first, rest grouped in your language order; **adaptive language memory** promotes the language you last downloaded.
- **Hearing-impaired (SDH) sync** with Kodi's accessibility setting.
- **TV episodes found reliably** — id type verified against the API instead of guessed, original titles used for localized libraries, non-IMDb library ids handled (fixes for Umbrella, POV and TVDB-scraped shows).
- **Filename analysis** via the OpenSubtitles `guessit` service (30-day cache); gzip-compressed search cache with configurable duration, live statistics and a Clear Cache button.
- **Robust results** — one malformed API entry no longer empties the list; atomic downloads, temp-file cleanup, timeouts on every request.

### 🔒 Account & security
- **No secrets in logs** — credentials, session tokens and API keys are never written to the Kodi debug log (the log users paste on forums).
- **Sessions refresh automatically** when the server expires them; clear error dialogs for every HTTP failure mode.
- **Account status at a glance** — status, quota, VIP and last-checked shown in settings; compact Test Connection dialog that works with credentials as typed.

### 🔄 Updates
- **Check for Updates** with a progress dialog and a definitive "Updated to vX.Y.Z" confirmation.
- **Fast-track repository awareness** — the add-on knows whether it can actually receive updates (Kodi only updates from the repository an add-on was installed from) and shows setup instructions when it cannot.

### 🧪 Compatibility
- **Verified on real Kodi 19–22** (Matrix through Piers beta) via an automated headless-Kodi test harness; shipped code held to the true Matrix floor of Python 3.6.
- New icon matching Kodi's dark skins.

See the [full changelog](https://github.com/opensubtitles/service.subtitles.opensubtitles-com/blob/master/CHANGELOG.md) for the complete release-by-release history.

---

## 📄 License

This project is licensed under the GNU General Public License v2.0 — see the [LICENSE.txt](LICENSE.txt) file for details.
OpenSubtitles REST API client originally based on [python-opensubtitles-rest-api](https://github.com/tomburke25/python-opensubtitles-rest-api) by tomburke25.
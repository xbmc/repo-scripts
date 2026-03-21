# Bingebase for Kodi

Automatically scrobble what you watch and sync your watch history between Kodi and [Bingebase](https://bingebase.com).

## Features

- **Scrobbling** — automatically track movies and TV episodes as you watch
- **Two-way sync** — import Kodi watch history to Bingebase and export Bingebase history back to Kodi
- **Scheduled sync** — periodic background sync (6h / 12h / 24h intervals)
- **Library update sync** — sync when Kodi finishes a library scan

## Installation

1. Download the latest release zip
2. In Kodi, go to **Add-ons > Install from zip file**
3. Select the downloaded zip
4. The addon will prompt you to connect your Bingebase account on first run

### Manual installation

Copy or symlink the `script.bingebase` folder into your Kodi addons directory:

- **Linux:** `~/.kodi/addons/`
- **macOS:** `~/Library/Application Support/Kodi/addons/`
- **Windows:** `%APPDATA%\Kodi\addons\`

## Setup

1. Open **Add-ons > My add-ons > Services > Bingebase**
2. Click **Configure**
3. Under **Connection**, click **Authorize** and follow the on-screen instructions
4. Adjust scrobbling and sync settings as needed

## Settings

### Scrobbling
- Enable/disable scrobbling
- Toggle movies and TV episodes independently
- Set a scrobble threshold (percentage watched before scrobbling on stop)
- Show notifications on scrobble

### Sync
- Sync on startup
- Sync on library update
- Scheduled sync interval (off / 6h / 12h / 24h)
- Sync direction: Kodi to Bingebase, Bingebase to Kodi, or both

## About Bingebase

[Bingebase](https://bingebase.com) is a free movie and TV show tracking platform. Track what you watch, build custom lists, and sync across all your devices.

## License

GPL-2.0-or-later — see [LICENSE.txt](LICENSE.txt).

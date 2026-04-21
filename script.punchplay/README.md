# PunchPlay Scrobble — Kodi Addon

Automatically tracks movies and TV episodes you watch in Kodi and posts them to your **[PunchPlay.tv](https://punchplay.tv)** account in real time.

Supported Kodi versions: **Nexus (20)** and **Omega (21)**, Python 3 only.

---

## Installation

### Option A — Direct download (recommended)

1. **[Download script.punchplay.zip](https://github.com/PunchPlay/script.punchplay/releases/latest/download/script.punchplay.zip)**
2. In Kodi: **Settings → Add-ons → Install from zip file**
3. Navigate to the downloaded zip and confirm — Kodi installs and starts the service immediately.

### Option B — Kodi addon store

Once approved, install directly from **Settings → Add-ons → Install from repository → Kodi Add-on repository → Services → PunchPlay Scrobble**.

---

## Configuration

Open **Settings → Add-ons → My add-ons → Services → PunchPlay Scrobble → Configure**.

| Setting | Default | Description |
|---|---|---|
| **Backend URL** | `https://punchplay.tv` | Base URL of the PunchPlay API. Leave as-is unless self-hosting. |
| **Watched threshold (%)** | 70 | Minimum play percentage before an item is marked as watched. |
| **Minimum file length (min)** | 5 | Files shorter than this are ignored (trailers, clips). |
| **Heartbeat interval (sec)** | 30 | How often progress is reported during playback. |
| **Scrobble movies** | On | Toggle movie tracking. |
| **Scrobble TV shows** | On | Toggle TV episode tracking. |
| **Scrobble anime** | On | Toggle anime tracking (detected by `"anime"` genre tag). |
| **Show scrobble notifications** | On | Show a Kodi notification when a watch is successfully scrobbled. |
| **Show notifications during playback** | Off | If off, scrobble notifications are suppressed while another video is playing. |

---

## Logging In

1. Open the addon settings.
2. Click **Login to PunchPlay**.
3. A dialog will show a short code and a URL:

   ```
   Visit: https://punchplay.tv/link
   Enter code: ABCD-1234
   ```

4. Open the URL on any device, sign in to your PunchPlay account, and approve the request.
5. Kodi polls automatically — you'll see a "Login successful!" notification within seconds.

Tokens are stored in the Kodi addon data directory (`userdata/addon_data/script.punchplay/`) and refreshed automatically. You only need to log in once.

To log out, click **Logout** in the addon settings.

---

## How It Works

```
Kodi player event
       │
       ▼
  PunchPlayPlayer (player.py)
       │  identify via Kodi library metadata → identifier.py
       │  fallback: regex filename parser    → identifier.py
       │  cache lookup/store                 → cache.py (SQLite)
       │
       ▼
  APIClient (api.py)
       │  POST /api/scrobble/start|pause|resume|stop|progress
       │  Bearer token attached automatically
       │  401 → refresh token and retry once
       │  network error → write to offline queue (SQLite)
       │
       ▼
  PunchPlay REST API
```

### Media identification

1. **Kodi library metadata** — if the item is in your library, Kodi provides the title, year, TMDB/TVDB IDs directly. Most accurate.
2. **Regex filename parser** — extracts title, year, and episode info from scene-style filenames (e.g. `Show.S01E02.1080p.WEB-DL.mkv`).
3. **Server-side TMDB search** — if neither method yields a TMDB ID, the server searches TMDB by title and year as a final fallback.

### Scrobble events

| Event | Endpoint | Triggered when |
|---|---|---|
| Start | `POST /api/scrobble/start` | Playback begins |
| Pause | `POST /api/scrobble/pause` | Player paused |
| Resume | `POST /api/scrobble/resume` | Player resumed |
| Progress | `POST /api/scrobble/progress` | Every N seconds during playback |
| Stop | `POST /api/scrobble/stop` | User stops or file ends |

Stop events include `"watched": true` when the play percentage meets or exceeds the configured threshold, triggering a full scrobble to your watch history. Partial stops (below threshold) save your position for the "Continue Watching" section on your profile.

All requests share the same JSON payload:

```json
{
  "media_type": "movie",
  "title": "Inception",
  "year": 2010,
  "tmdb_id": 27205,
  "imdb_id": "tt1375666",
  "progress": 0.72,
  "duration_seconds": 8880,
  "position_seconds": 6394,
  "device_id": "uuid-stored-per-device",
  "client_version": "1.0.0"
}
```

Optional fields (`imdb_id`, `tmdb_id`, `tvdb_id`, `season`, `episode`, `year`) are omitted when unavailable.

### Offline resilience

Failed POSTs are written to a local SQLite queue (capped at 200 events). The queue flushes every 60 seconds and also immediately before each new start event. Events replay in order; unrecoverable 4xx errors are discarded so they don't block the queue.

---

## File layout

```
script.punchplay/
├── addon.xml               Addon metadata and extension points
├── default.py              Entry point — launches the background service
├── service.py              xbmc.Monitor — main loop, login/logout, queue flush
├── player.py               xbmc.Player — playback events and heartbeat thread
├── api.py                  HTTP client (auth, token refresh, offline queue)
├── identifier.py           Media identification (library metadata + regex parser)
├── cache.py                SQLite: identifier cache + offline scrobble queue
├── icon.png                Addon icon (256×256)
├── fanart.jpg              Addon fanart (1280×720)
├── changelog.txt           Version history
├── LICENSE.txt             GPL-2.0
└── resources/
    ├── settings.xml        Addon settings UI
    └── language/
        └── resource.language.en_gb/
            └── strings.po  Localised UI strings
```

---

## License

GPL-2.0 — see [LICENSE.txt](LICENSE.txt).

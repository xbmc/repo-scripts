# Subtis Subtitles (Kodi)

Subtitle service add-on for Kodi that uses the [Subtis](https://subtis.io) API to search and download Spanish subtitles automatically.

## Requirements

- Kodi 19+ (Matrix) with xbmc.python 3.0.0
- Internet connection

## Installation

1. Download the add-on ZIP (release or locally packaged).
2. In Kodi: **Add-ons** → **Install from ZIP file** → select the ZIP.
3. Wait for the success notification.

### Manual packaging (if you cloned the repo)

1. Create a folder named `service.subtitles.subtis`.
2. Copy `addon.xml`, `service.py`, `README.md`, and `resources/` into it.
3. Zip the folder keeping the root structure intact.

## Usage

1. Play a movie in Kodi.
2. Open the subtitle menu (press `T` or use the OSD).
3. Select **Subtis** as the provider.
4. The subtitle downloads and is applied automatically.

**Note:** TV shows/series are not supported yet.

## How it works

### Search flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Client         │────▶│  Subtis         │────▶│  subt.is API    │
│  (Kodi Addon)   │     │  Provider       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                       │
                                │                       │
                                │  1. Hash Search       │
                                │  (OpenSubtitles hash) │
                                │──────────────────────▶│
                                │                       │
                        ┌───────┴───────┐               │
                        │  Found?       │◀──────────────│
                        └───────┬───────┘               │
                           No   │   Yes                 │
                    ┌───────────┴──────────┐            │
                    │                      │            │
                    ▼                      ▼            │
            2. Bytes Search        Return subtitle      │
            (file size)           (is_synced: true)     │
                    │                                   │
                    │──────────────────────────────────▶│
                    │                                   │
                    │◀──────────────────────────────────│
                    ▼                                   │
            3. Filename Search     Return subtitle      │
            (exact name)          (is_synced: true)     │
                    │                                   │
                    │──────────────────────────────────▶│
                    │                                   │
                    │◀──────────────────────────────────│
                    ▼                                   │
            4. Alternative Search  Return subtitle      │
            (fuzzy match)         (is_synced: false)    │
                    │                                   │
                    │──────────────────────────────────▶│
                    │                                   │
                    │◀──────────────────────────────────│
                    ▼
            Return subtitle
            (is_synced: false)
```

The add-on implements a 4-level cascading search. It tries each method in order and stops at the first success:
1. **Hash**: Search by file hash (OpenSubtitles algorithm). Most accurate.
2. **Bytes**: Search by exact file size.
3. **Filename**: Search by exact file name.
4. **Alternative**: Fuzzy match by name.

If the match comes from the alternative search, Kodi marks the subtitle as **not synchronized**.

### Add-on actions

| Action     | Description                                              |
|------------|----------------------------------------------------------|
| `search`   | Searches subtitles for the currently playing media       |
| `download` | Downloads the subtitle from `subtitle_link`              |

### API endpoints

Base URL: `https://api.subt.is/v1`

| Endpoint | Use |
|----------|-----|
| `GET /subtitle/find/file/hash/{hash}` | Match by video hash |
| `GET /subtitle/find/file/bytes/{bytes}` | Match by file size in bytes |
| `GET /subtitle/find/file/name/{filename}` | Exact match by name |
| `GET /subtitle/file/alternative/{filename}` | Fuzzy match by name |

**Successful response (200):**
```json
{
  "subtitle": {
    "subtitle_link": "https://...",
    "subtitle_file_name": "Movie.Name.2024.srt"
  },
  "title": {
    "title_name": "Movie Name",
    "year": "2024"
  }
}
```

### Storage

Downloaded subtitles are stored temporarily at:
```
{kodi_profile}/addon_data/service.subtitles.subtis/temp/
```

## Repository structure

```
.
├── addon.xml          # Add-on manifest
├── service.py         # Main logic
├── README.md          # Documentation
└── resources/
    └── icon.png       # Add-on icon
```

## Development

### Logs

Add-on logs use the `### SUBTIS ###` prefix. You can find them in:

- **Kodi** → **System** → **Logging** (enable debug).
- Log file (by OS):
  - Windows: `%APPDATA%\Kodi\kodi.log`
  - Linux: `~/.kodi/temp/kodi.log`
  - macOS: `~/Library/Logs/kodi.log`

Example log:
```
### SUBTIS ### Search requested but no media is playing
### SUBTIS ### ERROR: No subtitles found or API error (status: 404)
```

### Publishing

Before publishing, update the version in `addon.xml`:
```xml
<addon id="service.subtitles.subtis" version="X.Y.Z" ...>
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No active playback" | Make sure a movie is playing |
| "Movie not found" | The file is not in Subtis database |
| "TV shows support coming soon" | TV shows are not supported yet |
| Subtitle doesn't appear | Check logs for network or API errors |

## Current limitations

- Movies only (no series/episodes).
- Spanish subtitles only.
- Alternative subtitles may not be perfectly synchronized.


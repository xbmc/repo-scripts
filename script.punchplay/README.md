# PunchPlay

PunchPlay is a background service addon that tracks movies and TV episodes you watch in Kodi and syncs progress, watched history, and optional ratings to [PunchPlay.tv](https://punchplay.tv).

It supports Kodi Nexus 20 and Omega 21.

## What's New In 1.3.0

- Backend-assisted `/api/identify` matching for files without reliable Kodi IDs.
- Stronger local parsing for movie years, season folders, anime absolute episodes, and multi-episode files.
- Rating prompt delay plus `Later`, `Never for this title`, `Never for this show`, and `Disable rating prompts` actions.
- Preview mode for Kodi library import before sending watched history.
- Stricter backend URL validation with an explicit developer-mode override for insecure HTTP testing.
- Richer status and debug export data, including queue endpoint summaries and identify-cache state.

## Install

1. Download the latest addon zip:
   [script.punchplay.zip](https://github.com/PunchPlay/script.punchplay/releases/latest/download/script.punchplay.zip)
2. In Kodi, open **Settings -> Add-ons -> Install from zip file**.
3. Choose the downloaded zip.
4. Kodi installs the addon and starts the background service automatically.

If Kodi blocks zip installs, enable **Settings -> System -> Add-ons -> Unknown sources** first.

## Connect Your Account

1. In Kodi, open **Settings -> Add-ons -> My add-ons -> Services -> PunchPlay -> Configure**.
2. Click **Login to PunchPlay**.
3. Scan the QR code or visit `https://punchplay.tv/link`.
4. Sign in and approve the code shown in Kodi.
5. The Kodi dialog closes automatically once the device is connected.

Tokens are stored locally in Kodi's addon data directory and refreshed automatically. If you log out while unsynced events are queued, the addon warns before deleting them.

## What It Tracks

The addon sends these playback events to PunchPlay:

| Kodi event | PunchPlay endpoint | Purpose |
| --- | --- | --- |
| Playback starts | `/api/scrobble/start` | Creates or updates now-playing progress |
| Pause | `/api/scrobble/pause` | Saves the current position |
| Resume | `/api/scrobble/resume` | Marks the item active again |
| Progress heartbeat | `/api/scrobble/progress` | Updates continue-watching progress |
| Stop or end | `/api/scrobble/stop` | Saves final progress and decides watched vs continue-watching |

The default watched threshold is 70%. Playback only becomes watched when the final stop event crosses that threshold.

## Current Features

- Automatic movie and TV episode scrobbling.
- Continue-watching progress on PunchPlay.
- Backend-assisted canonical matching when Kodi metadata is incomplete.
- Post-watch rating dialog for movies and episodes with suppression options.
- Preview and import of watched Kodi library items.
- QR/device-code login.
- Token refresh on expired access tokens.
- Offline queue with retry metadata and 30-day expiry.
- Per-event `event_id` values plus stable `playback_session_id` values for backend idempotency.
- Duplicate-stop protection so repeated Kodi stop/end callbacks do not create duplicate history.
- Status, connection test, and basic/verbose debug export actions in addon settings.
- Anime handling based on Kodi genre, folder structure, and absolute-episode parsing.
- Multi-episode detection with `episode_end` and `multi_episode` payload fields.

## Settings

Open **Configure** from the addon details page.

| Setting | Default | Notes |
| --- | --- | --- |
| Login to PunchPlay | - | Starts QR/device-code login. |
| Logout | - | Warns before deleting queued unsynced events. |
| Test PunchPlay Connection | - | Checks backend reachability and login state without playing media. |
| Show Status | - | Displays account, queue, last success/error, addon version, and Kodi version. |
| Scrobble movies | On | Enables movie tracking. |
| Scrobble TV shows | On | Enables episode tracking. |
| Scrobble anime | On | Applies to episodes with the `anime` genre. |
| Anime episode format | Auto | `Auto`, `Season/Episode`, or `Absolute episodes` for anime-heavy libraries. |
| Watched threshold (%) | 90 | Minimum progress needed to log a completed watch. |
| Minimum file length (minutes) | 5 | Ignores trailers and short clips. |
| Preview Library Import | - | Runs a dry preview and can optionally continue into a real import. |
| Sync Kodi Library | - | Imports watched movies and episodes from Kodi's local library. |
| Rate after watching | On | Shows the PunchPlay rating dialog after a completed scrobble. |
| Rating prompt delay (seconds) | 2 | Lets Kodi settle before prompting, which avoids interrupting autoplay. |
| Show scrobble notifications | On | Shows Kodi notifications for completed scrobbles. |
| Show notifications during playback | Off | Keeps notifications quiet while another video is already playing. |
| Export Debug Info | - | Writes a token-safe JSON status snapshot into addon data. |
| Export Verbose Debug Info | - | Includes queued file paths after a warning prompt. |
| Clear Offline Queue | - | Clears queued events manually. |
| Developer mode | Off | Unlocks development-only backend overrides. |
| Allow insecure HTTP backend URL | Off | Only meaningful when developer mode is enabled. |
| Backend URL | `https://punchplay.tv` | Advanced override for development and staging environments. |

## Media Matching

PunchPlay identifies media in this order:

1. Kodi library metadata from `InfoTagVideo`, including TMDB, TVDB, IMDb, season, and episode IDs when Kodi has them.
2. Local filename and folder parsing for scene-style movies, season folders, anime releases, and multi-episode files.
3. Backend `/api/identify` for high-confidence canonical matching when local metadata still has no reliable IDs.
4. Raw filename fallback so the backend can still attempt matching later.

Examples handled locally include:

- `Inception.2010.1080p.BluRay.mkv`
- `Breaking.Bad.S01E02.mkv`
- `The Office/Season 2/02 - Sexual Harassment.mkv`
- `[SubsPlease] Sousou no Frieren - 07 (1080p).mkv`
- `Show.Name.S01E01-E02.mkv`

Keeping your Kodi library scraped with TMDB, TVDB, or IMDb-compatible IDs still gives the most accurate results and skips unnecessary identify calls.

## Offline Behavior

If PunchPlay cannot be reached, scrobble events are written to a local SQLite queue in Kodi addon data. The queue is replayed in order when the connection returns.

The queue is capped at 500 events, stores retry metadata, and drops entries older than 30 days. When the queue is full, the addon drops older low-value progress events before it drops authoritative stop events.

Completed playback sessions clear their older queued session events before the final stop is sent, which prevents stale progress from bringing a watched item back into continue-watching.

Progress heartbeats are sent every 15 seconds internally. This is fixed by design so public installs do not accidentally hammer the backend with overly aggressive update intervals.

## Library Sync

Use **Configure -> Library -> Preview Library Import** to preview what PunchPlay would import without modifying server history. From the preview result you can continue directly into a real import.

Real imports still use **Configure -> Library -> Sync Kodi Library**.

The sync reads watched movies and episodes from Kodi's video library using JSON-RPC, sends them in batches, and reports imported, skipped duplicate, unmatched, and failed items. When the backend returns item-level diagnostics, the addon writes a JSON diagnostics file into addon data for support.

## Status And Debug

`Show Status` now reports:

- whether the account is connected
- backend URL and backend configuration validity
- masked device ID
- offline queue size and queued endpoint summary
- last successful scrobble and last error
- identifier cache size and last identify result
- addon version, Kodi version, platform, and Python version in debug export

Basic debug export avoids tokens and file paths. Verbose debug export warns before including queued file paths.

## Troubleshooting

If nothing is scrobbling:

- Make sure you are logged in.
- Use **Test PunchPlay Connection**.
- Check that the video is longer than the configured minimum length.
- Check that movie, TV, or anime tracking is enabled for the content you are playing.
- Open **Show Status** and look for queued events or a recent error.

If a movie or episode was matched incorrectly:

- Prefer Kodi library metadata with TMDB, TVDB, or IMDb IDs when possible.
- Check whether the filename includes title, year, season, and episode clearly.
- Export debug info and include the identify result in the support report.

If anime episodes are not matching:

- Make sure the path or folder structure clearly indicates anime, or switch **Anime episode format** to `Absolute episodes`.
- Prefer season/episode mode for anime that is already scraped in Kodi with season data.

If a multi-episode file only marked one episode:

- Confirm the backend understands `episode_end` and `multi_episode`.
- The 1.3.0 addon sends enough context for backend-side expansion, but final multi-episode watch-history behavior still depends on backend handling.

If something was marked watched too early:

- Increase **Watched threshold (%)**.
- Confirm your backend only treats `/api/scrobble/stop` as authoritative for watched history.

If progress reappears after you finished something:

- Confirm the backend ignores stale progress updates once a stop event marks the session watched.
- Check **Show Status** and exported debug info for queued replay details.

If ratings keep popping up:

- Use `Later` to skip one prompt.
- Use `Never for this title` or `Never for this show` to suppress repeats.
- Increase **Rating prompt delay (seconds)** if autoplay is close to the stop event.

If library sync skipped items:

- Run **Preview Library Import** first and inspect unmatched counts.
- Export debug info or the generated library diagnostics file for backend matching review.

If Test PunchPlay Connection fails:

- Open **Advanced** and confirm the backend URL is valid.
- Leave the backend URL blank to use the default production backend.
- In developer mode, enable insecure HTTP only when you intentionally need a local test server.

## Privacy

PunchPlay receives:

- title and metadata used for matching
- playback position and duration
- watched state and watched threshold
- device ID
- ratings you explicitly submit

PunchPlay does not receive:

- video file contents
- direct local file access
- Kodi login credentials

Verbose debug export can include queued file paths, but never includes access tokens, refresh tokens, or raw Authorization headers.

## Development Checks

Before publishing a release:

```bash
export PYTHONPYCACHEPREFIX=/tmp/punchplay-pyc
python3 -m py_compile default.py resources/lib/*.py
kodi-addon-checker --branch omega .
```

Build the zip from the parent directory:

```bash
repo_dir="$(basename "$PWD")"
cd ..
zip -r /tmp/script.punchplay.zip "$repo_dir" \
  -x "$repo_dir/.git/*" \
     "$repo_dir/.github/*" \
     "$repo_dir/tests/*" \
     "$repo_dir/__pycache__/*" \
     "$repo_dir/**/__pycache__/*" \
     "$repo_dir/.DS_Store" \
     "$repo_dir/**/.DS_Store"
```

Upload the asset as `script.punchplay.zip` on the latest GitHub release. The PunchPlay website download button points at:

```text
https://github.com/PunchPlay/script.punchplay/releases/latest/download/script.punchplay.zip
```

## File Layout

```text
script.punchplay/
├── addon.xml
├── default.py
├── icon.png
├── fanart.jpg
├── changelog.txt
├── LICENSE.txt
└── resources/
    ├── lib/
    │   ├── __init__.py
    │   ├── api.py
    │   ├── cache.py
    │   ├── constants.py
    │   ├── identifier.py
    │   ├── login_dialog.py
    │   ├── player.py
    │   ├── rating_dialog.py
    │   └── service.py
    ├── settings.xml
    ├── media/background.png
    └── language/resource.language.en_gb/strings.po
```

## License

GPL-2.0-only. See [LICENSE.txt](LICENSE.txt).

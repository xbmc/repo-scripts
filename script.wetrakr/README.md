# WeTrakr for Kodi

Kodi addon that scrobbles your playback activity to [WeTrakr](https://wetrakr.com).

Marks movies and episodes as watched, syncs your viewing activity in real time, and (optionally) lets you rate after watching. Pairing is one-click via OAuth Device Code.

## Install

The addon is distributed as a single zip file. Download it from the latest [GitHub Release](https://github.com/wetrakr/wetrakr-kodi/releases) and install in Kodi:

1. In Kodi, enable installation from unknown sources: **Settings → System → Add-ons → Unknown sources**.
2. Download `script.wetrakr-X.Y.Z.zip` from the releases page.
3. **Settings → Add-ons → Install from zip file** → select the downloaded zip.
4. Open the addon (it will be available under **Add-ons → Program add-ons → WeTrakr Scrobbler**) and follow the pairing instructions.
5. A short code is shown. Open `https://wetrakr.com/activate?platform=kodi` in any browser, paste the code, confirm.
6. Done — playback events are now scrobbled.

## Uninstall

**Settings → Add-ons → My add-ons → WeTrakr Scrobbler → Uninstall.**

## What gets scrobbled

| Event | Detail |
|-------|--------|
| Playback start | Title, IMDb/TMDB/TVDB ids when available |
| Progress (periodic) | Position vs runtime |
| Pause / Resume | Detected from the player |
| Stop | Final position |
| Watched | Marked when threshold reached (configurable, default 80%) |
| Rating (optional) | Prompts after watching a movie or episode |

## Settings

| Setting | Default | Notes |
|---------|---------|-------|
| Mark as watched | on | Sends watched event when threshold is reached |
| Send 'now playing' | on | Periodic progress updates |
| Scrobble threshold | 80% | Watched threshold |
| Rate after movie | on | Prompt to rate when a movie ends |
| Rate after episode | off | Prompt to rate when an episode ends |
| Debug logging | off | Verbose logs in Kodi log |

Advanced: the API URL can be overridden in the addon settings (default: `https://api.wetrakr.com`).

## Development

The addon is pure Python (Kodi 19+, `xbmc.python` 3.0.0). No build step.

```bash
# Sideload locally
ln -s "$(pwd)" ~/.kodi/addons/script.wetrakr   # macOS / Linux
# Then enable in Kodi → My add-ons → Program add-ons.
```

Logs: `~/.kodi/temp/kodi.log`. Enable debug logging in Kodi settings + the addon's Debug setting for verbose tracing.

## Privacy

This addon talks to `https://api.wetrakr.com` only. Network traffic includes:

- The provider IDs of the content you play (IMDb / TMDB / TVDB), title, runtime, position.
- A per-device OAuth token assigned to your account during pairing.

It does **not** transmit your Kodi library, file paths, IP-based location, or other Kodi addons.

The pairing token is rotated server-side on every new pairing — re-pairing in another device invalidates older tokens.

## License

MIT — see [LICENSE](LICENSE).

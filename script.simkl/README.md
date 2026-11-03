<p align="center"><img src="resources/icon.png" width="128" alt="Simkl TV Tracker"></p>

# Simkl TV Tracker for Kodi

[![Licence GPLv3](https://img.shields.io/badge/licence-GPLv3-brightgreen.svg)][license]
[![Kodi 19+](https://img.shields.io/badge/Kodi-19%2B-blue.svg)](https://kodi.tv)
[![Latest release](https://img.shields.io/github/v/release/SIMKL/script.simkl?label=release)](https://github.com/SIMKL/script.simkl/releases)

Tracks what you watch in Kodi on [Simkl](https://simkl.com): movies, TV shows and anime. Plays are reported as they happen, watched marks flow both ways between the Kodi library and your Simkl history, and your Simkl ratings and resume points can come back into Kodi.

## Features

- **Real-time scrobbling.** Start, pause and stop reach Simkl as they happen. Finish a playback and it is marked as watched; stop early and Simkl keeps the position for later.
- **Watched marks from the Kodi library.** Mark a movie, an episode, a season or a show as watched in Kodi and it is marked on Simkl too. A single unmark is mirrored as well.
- **Sync from Simkl.** Your Simkl history marks the Kodi library, by hand or on a schedule, and only what changed since the last sync is fetched.
- **Continue watching.** Where you paused in another Simkl app becomes a resume point in Kodi (opt-in).
- **Rewatches** for Simkl Pro and VIP accounts.
- **Ratings.** A prompt after a movie, ratings made in Kodi sent to Simkl, Simkl ratings brought into the library.
- **Simkl in the context menu.** Mark as watched, remove from history, add to Plan to watch, rate, sync.
- **Works offline.** Watches and marks that could not be sent are kept and sent later with their original date.
- **Exclusions.** Live TV, HTTP streams, add-on playbacks, folders of your choice. Trailers and clips are skipped.
- **31 languages.**

## Install

1. Kodi » Settings » Add-ons » Install from repository » Kodi Add-on repository » Services » **Simkl TV Tracker** » Install. Or download the zip of the version you want from the [releases](https://github.com/SIMKL/script.simkl/releases) and use "Install from zip file".
2. Open the add-on settings (Settings » Add-ons » My add-ons » Services » Simkl TV Tracker » Configure) and press **Log in**. A code and a QR code appear: scan the QR code with your phone, or enter the code at [simkl.com/pin](https://simkl.com/pin) on any phone or computer.
3. Watch something.

**Upgrading from 3.x:** the existing login keeps working. Press **Reconnect with the new sign-in** once, with the same account (to switch accounts, log out first); the add-on reminds you every few days until you do.

## How it works

### Scrobbling

Start, pause, resume, seek and stop are sent to Simkl as they happen, so the item shows as "watching now" on your profile. A playback that ends at or past the threshold (70% by default, 50 to 100 in the settings) is marked as watched; one that stops earlier keeps its position on Simkl so you can continue in another Simkl app.

The add-on only reports what it can identify: items of the Kodi library, add-on items that carry ids (see [For add-on developers](#for-add-on-developers)), and local files or files on a network share, which Simkl's file search names by their path. Items without ids (YouTube and the like) are not guessed by title. Trailers and clips are skipped, and so are add-on streams and unnamed files shorter than the minimum length; library items are always tracked.

### Watched marks from the Kodi library

Marking a movie, an episode, a season or a show as watched in Kodi marks it on Simkl too, in one request. The episodes of a multi-episode file (S01E01E02) are watched, marked and unmarked together, as Kodi shows them.

Unmarking is mirrored with care:

- A single **episode** unmarked in Kodi is removed from the Simkl history.
- A **movie** unmarked in Kodi brings a question: remove it from Simkl (its rating and note go too), move it to Plan to watch (they stay, the watch date goes) or keep it watched. No answer within 30 seconds keeps it. A movie with rewatch sessions on Simkl is never removed.
- Unmarking a whole **season or show** is deliberately not sent. The Simkl entry of the context menu on a season or show row removes its episodes from the Simkl history on purpose.

### Sync from Simkl

"Sync updates from Simkl" marks in the Kodi library what you watched on Simkl. The first run fetches the whole history; after that only what changed on Simkl since the last sync is fetched. "Reset and sync everything again" goes through the whole history once more and refreshes the watch dates of items Kodi already has as watched.

- A title the library holds twice (two sources, 1080p and 4K) gets its marks on every copy.
- What Simkl answered is kept in the add-on's profile (`history.json`), so a run after the library grew gives the new items their marks from that copy without asking Simkl again.
- The sync never unmarks anything. What you unmarked in Kodi stays unwatched until Simkl sees a newer watch of it; a reset takes Simkl's state again.
- **On a schedule:** switch on the automatic sync and pick an interval. It runs while Kodi is on and nothing is playing; a device nobody used since the last check waits for the next use.
- **Several Kodi devices sharing one MySQL library:** switch the automatic sync on for **one** device only; the others get the marks through the shared database.
- **Continue watching (opt-in):** where you paused in another Simkl app becomes a resume point in Kodi, for items not yet watched in Kodi and only when the Simkl pause is newer than Kodi's own last play.
- **Ratings (optional):** your Simkl rating of a movie or a show becomes the Kodi library's user rating.

### Rewatches

For Simkl Pro and VIP accounts, off by default. Watching something again opens a new rewatch session on Simkl instead of keeping the first date. A playback counts as a rewatch only when at least 10% of the runtime was really watched (replaying the last minutes of something you have seen is not one); whether it is a rewatch at all, Simkl decides from your history.

### Ratings

- After a movie ends past the threshold a 1 to 10 pick appears (optional, movies only, not for a movie you rated in Kodi or watched before).
- A rating set in Kodi's own information dialog for a movie or a show goes to Simkl, except for a movie Kodi has as unwatched: Simkl files a rated movie as watched.
- The Simkl context entry rates the movie or the show of any row, with the same exception; `RunScript(script.simkl, action=rate, rating=0)` still removes its rating.
- Episodes are not rated.

### Context menu

A "Simkl" entry on movies, shows, seasons and episodes, and on video files outside the library (named through Simkl's file search, since Kodi tells add-ons nothing about its own "Mark as watched" on those). An add-on's episode needs the show's ids on its list item; without them the entry says so.

| Entry | Where |
|---|---|
| Add to Plan to watch | Everywhere, except a library movie Kodi has as watched (Simkl would take it out of your watched list) |
| Rate on Simkl | The movie, or the show of the row, 1 to 10 |
| Sync updates from Simkl | Everywhere |
| Mark as watched on Simkl | Where Kodi's own mark cannot reach Simkl: files outside the library, add-on items, the watched-marks switch off, or the tracking of that type off |
| Remove from Simkl history | Same places as above, plus every library season and show (Kodi's own unmark of a whole season or show is never sent) |

Mark and remove also set Kodi's own watched state. An episode leaves the Simkl history at once, a movie after the same question as above.

### Offline

A watch or a mark that could not be sent (offline, Simkl down) is kept on disk and sent later with its original date, for up to 30 days. A notification says when older ones had to be dropped.

## Settings

| Section | What is there |
|---|---|
| **Account** | Status, then Log in, Reconnect with the new sign-in or Log out, whichever applies |
| **Scrobbling** | Movies, TV shows and anime, the percentage, the minimum length, the notification, the rating prompt after a movie, rewatches (Pro or VIP), whether watched marks and ratings made in Kodi are sent to Simkl |
| **Sync from Simkl** | Sync updates now, automatic sync and its interval, continue watching, Simkl ratings into Kodi, the result of the last sync, reset |
| **Exclusions** | Live TV, HTTP streams, add-on playbacks, up to five folders |
| **Advanced** | Debug logging, "Show the Simkl log" (the Simkl lines of the Kodi log on screen, also saved as `simkl.log` next to the add-on's settings for a bug report), the Kodi log's location |

## For add-on developers

Items your add-on plays are tracked when they carry ids. Put a JSON object with `imdb`, `tmdb`, `tvdb`, `anidb`, `mal`, `anilist` or `simkl` keys in the `script.simkl.ids` property of the `ListItem` (for an episode the show's ids, with season and episode numbers on the item), or use Kodi's own unique ids. `script.simkl.paused` keeps the add-on out of a playback you report to Simkl yourself, `script.simkl.exclude` keeps one item out. The add-on tells you what it tracks through the `script.simkl.playing` window property and a `scrobbled` notification, and skins and keymaps can trigger its actions with `RunScript`.

The full guide with code examples, the home-window property, the file search, Up Next and a checklist for testing: **[docs/developers.md](docs/developers.md)**.

## Development

- `python tests/run_checks.py` runs the add-on's logic against stubbed Kodi modules, no Kodi needed (Python 3.8 or newer). `python tests/qr_reference.py` compares the login QR code with the `qrcode` library (`pip install qrcode`). The `tests` folder is not part of the release zip.
- Translations live in `resources/language/resource.language.<code>/strings.po`, the English source in `resource.language.en_gb`. Corrections are welcome as pull requests.

## Support

- Bugs and feature requests: [GitHub issues](https://github.com/SIMKL/script.simkl/issues)
- Discord: [discord.gg/u89XfYn](https://discord.gg/u89XfYn)
- Forum thread: [forum.kodi.tv](https://forum.kodi.tv/showthread.php?tid=389656)

Simkl TV Tracker was created by David Davó in 2016 and maintained by him until 2018; 4.0.0 is a rewrite by Simkl. Licensed under the [GPL v3][license].

[license]: https://github.com/SIMKL/script.simkl/blob/master/LICENSE.txt

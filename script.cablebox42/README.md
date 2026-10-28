# CableBox 42 — retro cable TV for Kodi 21

A FieldStation42-style channel-flipping experience that runs *inside* Kodi, on
anything Kodi 21 "Omega" runs on: Windows, macOS, Linux, Android / Android TV /
Fire TV, LibreELEC, CoreELEC, OSMC and Raspberry Pi.

Every file is played by Kodi's own player, so whatever hardware decoding your
device has (Amlogic on CoreELEC, the GPU on a PC, MediaCodec on Android TV…)
works exactly as it does for the rest of your library — no stuttering H.265 on
small boxes.

## Install

Once it's in the official repository: **Add-ons → Install from repository →
Kodi Add-on repository → Program add-ons → CableBox 42**.

To install a zip by hand:

1. Copy the `script.cablebox42` zip to the device (USB stick, network share…).
2. Kodi: **Settings → System → Add-ons → Unknown sources: On**.
3. **Settings → Add-ons → Install from zip file** → pick the zip.
4. It shows up under **Add-ons → Program add-ons / Video add-ons → CableBox 42**.
   Long-press it → *Add to favourites* (or add it to the Estuary home menu) for one-click TV.

## First run (about two minutes)

Open CableBox 42 → **Build my lineup automatically**.
It reads your Kodi library and creates:

| Ch | What |
|----|------|
| 2 | TV Guide (scrolling Prevue-style grid with promos) |
| 3 | Weather Channel (retro local forecast) |
| 4 | Your local station — every show you own |
| 5+ | One network per TV genre with 3+ shows (Comedy Channel, Sci-Fi Channel…) |
| … | Studio showcases when you have enough content (Disney Showcase, Hanna-Barbera Showcase…) |
| … | "Retro 80s"/"Retro 90s" decade networks |
| … | Movie Channel + per-genre movie channels + Classic Movies (pre-1990) |

It also asks (optionally) for your **commercials** and **bumps** folders. Then
press *Watch TV*. That's it — there is no schedule compile step.

## Remote

| Key | Does |
|-----|------|
| CH+/CH−, Up/Down, PgUp/PgDn | change channel (with static) |
| Number keys | direct tune (green VCR digits) |
| Left | last channel |
| Right | "What's on now" list |
| OK / Info | channel banner (now / next / progress) |
| Menu / Context | sleep timer, last channel, turn off |
| Back / Stop | turn off the TV |
| Pause / seek | ignored — it's live TV |

## How scheduling works (the "better way")

* **Self-building.** Every channel keeps a rolling 12-hour schedule that
  extends itself when you tune in, when the guide needs it, and every 20 min in
  the background. Edit a channel and it re-plans from *now*; episode progress
  is kept.
* **Real clock.** Programs start on :00/:30 (or the hour, :15s, or no clock).
  The gap in each half hour is cut into mid-show commercial breaks, ending with a
  bump. No commercials? The gap becomes an "Up next" card.
* **Strip programming.** "Same show same time every day" channels air a fixed
  weekday lineup while series always advance to the next episode.
* **Time blocks.** Saturday-morning cartoons, prime-time movies, a late-night
  block — pick start/end, days, and what airs.
* **Sign-off hours** show SMPTE bars until sign-on.
* **Sources:** TV shows, TV genre, decade, movies (genre / years / set), any
  folder (SMB/NFS/local — each sub-folder is a show), or a **Kodi smart
  playlist** — use Kodi's built-in rule editor for anything fancy.
* **Durations:** taken from the library; for folders/commercials the add-on reads
  MP4/MKV/AVI/TS/MPG/WMV/FLV headers itself (no ffprobe needed) and caches them.

## Weather channel

Rotating pages — Current Conditions, Local Forecast (TODAY… TONIGHT… text),
Extended Forecast and the next few hours with sunrise/sunset — over a scrolling
conditions ticker. Data comes from Kodi's weather service if one is set up
(Settings → Services → Weather), otherwise from Open-Meteo for the city in
*Settings → Weather* (free, no key). Point *Weather channel music folder* at some
smooth jazz for the full effect.

## Fine-tuning channels

* **Move shows between channels** (main menu): pick a show, tick the channels it
  should be on. Unticking hides it even when the channel's genre includes it.
* **What's on this channel** (in each channel): a checklist of everything it airs.
* While watching: **Menu → Don't air '…' on this channel**.
* **Studio / tag / title sources**: e.g. a Disney channel = studio contains
  "Disney" (movies + shows). Kodi tags work the same way (tag your Wonderful
  World of Disney episodes and Disney films "Disney").
* **Check my commercials & bumps** lists clips whose length can't be read.
* **Searchable lists.** Every long picker (tags, studios, shows, movies, genres,
  "What's on this channel") has a *Search…* row at the top: type a few letters
  (on-screen keyboard, or your phone with Kore/Yatse) and the list narrows down.
  Multi-pick lists keep a running "✔ selected" set across searches, so you can
  search "disney", tick two tags, search "christmas", tick another, then *Done*.
  Tag and studio sources accept several values at once.

## Channel numbers

Channel manager → pick a channel → **Number**, type the new one. If it's taken you
can **swap** the two channels or **slide** everything in between over by one
(Weather 24 → 3 pushes old 3-23 up to 4-24). **Rearrange channel numbers** in the
Channel manager does the same for any channel and can close gaps (2, 3, 4…).
Renumbering never rebuilds schedules — the same show keeps airing.

## Settings worth knowing

* *Turn the TV on when Kodi starts* — appliance mode.
* *Go straight to TV when opened* — skip the menu.
* *Commercial breaks per half hour* (0–4).
* *Guide channel music folder* — background music for channel 2.

## Hand-editing

Lineup: `channels.json` in the add-on's data folder,
`userdata/addon_data/script.cablebox42/` inside Kodi's data folder:

| System | Kodi data folder |
|---|---|
| LibreELEC / CoreELEC | `/storage/.kodi/` (network share: *Userdata*) |
| Windows | `%APPDATA%\Kodi\` |
| macOS | `~/Library/Application Support/Kodi/` |
| Linux / OSMC / Raspberry Pi OS | `~/.kodi/` |
| Android | `Android/data/org.xbmc.kodi/files/.kodi/` |

```json
{"id": "a1b2c3d4", "number": 7, "name": "Saturday Toons", "type": "network",
 "callsign": "TOON", "slot": 30, "lineup": "strip",
 "commercials": true, "bumps": true,
 "sources": [{"type": "tvgenre", "value": "Animation"}],
 "dayparts": [{"label": "Prime Time", "start": "20:00", "end": "23:00", "days": "all",
               "sources": [{"type": "movies", "genre": "Family"}]}],
 "offair": [{"start": "02:00", "end": "06:00"}],
 "commercials_path": "smb://nas/tv/ads/80s/"}
```

Types: `network`, `movies`, `loop`, `guide`. After hand-editing, use
*Rebuild schedules*.

## Support & source

Source and issues: https://github.com/SeadogMcGrog/script.cablebox42

Inspired by [FieldStation42](https://github.com/shane-mason/FieldStation42); not affiliated with it.
Licensed under the Mozilla Public License 2.0 (see LICENSE.txt).

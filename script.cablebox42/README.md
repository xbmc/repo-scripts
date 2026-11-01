# CableBox 42

**Retro cable TV from your own Kodi library. Flip channels, not menus.**

> **Beta:** CableBox 42 is new and actively developed. It's tested on CoreELEC
> (ODROID N2); reports from other devices are very welcome in the
> [support thread](https://forum.kodi.tv/showthread.php?tid=389521) or on
> [GitHub issues](https://github.com/SeadogMcGrog/script.cablebox42/issues).

CableBox 42 turns the movies and TV shows you already have in Kodi into a live
cable lineup. Shows air on a real clock with commercial breaks, bumpers and
station IDs. There's a scrolling program guide channel, a retro weather
channel, static between channels, a "CH 03" channel number, and a 1950s
*Please Stand By* card when a station signs off for the night. You pick up the
remote, flip to channel 5, and whatever is on is already halfway through.

It's inspired by [FieldStation42](https://github.com/shane-mason/FieldStation42),
but it's a separate implementation built for Kodi. It runs inside Kodi on
anything Kodi 21 runs on, and plays every file through Kodi's own player, so
hardware video decoding works exactly as it does for the rest of your library.

### ▶ See it in action

| Part 1: the tour | Part 2: guide and weather |
|---|---|
| [![CableBox 42 part 1: channel surfing and the tour](https://img.youtube.com/vi/38CTQFPLdgg/hqdefault.jpg)](https://youtu.be/38CTQFPLdgg) | [![CableBox 42 part 2: the TV Guide and Weather channels](https://img.youtube.com/vi/VDaUOxNVePA/hqdefault.jpg)](https://youtu.be/VDaUOxNVePA) |
| *Channel surfing and commercials* | *The TV Guide channel and the Weather Channel* |

*Click a picture to watch on YouTube.*

| | |
|---|---|
| ![Changing channel](resources/screenshots/screenshot-01.jpg) | ![Weekly planner](resources/screenshots/screenshot-02.jpg) |
| *Changing channel: static, "CH 05" and the channel banner* | *The weekly planner: pin shows to fixed times* |
| ![Off the air](resources/screenshots/screenshot-03.jpg) | ![Weather channel](resources/screenshots/screenshot-04.jpg) |
| *Off the air: the stand-by test card* | *The weather channel with the Full CRT effect* |

*The screenshots are put together from CableBox 42's own screen artwork and layouts.*

---

## Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installing](#installing)
4. [Quick start](#quick-start)
5. [Watching TV](#watching-tv)
6. [How the schedule works](#how-the-schedule-works)
7. [Building and editing channels](#building-and-editing-channels)
8. [The weekly planner](#the-weekly-planner)
9. [Commercials, bumps, station IDs and sign-off clips](#commercials-bumps-station-ids-and-sign-off-clips)
10. [Off the air](#off-the-air)
11. [Holidays](#holidays)
12. [The guide channel](#the-guide-channel)
13. [The weather channel](#the-weather-channel)
14. [CRT effect](#crt-effect)
15. [Home screen, Favourites and phone remotes](#home-screen-favourites-and-phone-remotes)
16. [Settings reference](#settings-reference)
17. [Video formats and AV1](#video-formats-and-av1)
18. [Files and hand-editing](#files-and-hand-editing)
19. [Troubleshooting](#troubleshooting)
20. [Credits and license](#credits-and-license)

---

## Features

- **No schedule to compile.** Lineups build themselves from your library and
  extend themselves as time passes.
- **Real-time channels.** Programs start on the hour and half hour. The time
  left over in each slot is cut into commercial breaks, just like real cable.
- **Automatic lineup builder.** One step creates a guide channel, a weather
  channel, an everything station, genre networks, decade channels, movie
  channels and studio showcases.
- **Weekly planner.** A 7-day grid for each channel. Pin shows to fixed times,
  for example *Seinfeld, Fridays 8 PM, in order*. Each pinned slot picks up
  where it left off the week before.
- **Time blocks.** Saturday-morning cartoons, prime-time movies, late-night
  blocks.
- **Off the air.** Sign-off hours with a 1950s stand-by card or colour bars,
  plus optional sign-off and sign-on clips.
- **Commercials, bumps and station IDs** from your own folders.
- **Guide channel.** A scrolling grid of what's on now and next, with promos.
- **Weather channel.** Current conditions, a text forecast, a 4-day outlook and
  the next few hours, with a ticker and optional background music.
- **The look of a CRT.** Static and a static sound between channels, a glowing
  green "CH 03" channel number, and an optional CRT effect: scanlines,
  curved-glass corners, a phosphor mask and a rolling hum bar.
- **Fine-tuning.** Move any show between channels, hide shows from a channel,
  and renumber channels with swap or slide.
- **Searchable pickers** for libraries with thousands of tags, studios or titles.
- **Works with your skin and your phone.** Home-menu widgets show what's on now,
  and you can tune from Yatse or Kore.
- **Safe on small boxes.** AV1 videos are skipped automatically on devices that
  can't decode them in hardware.

---

## Requirements

- **Kodi 21 "Omega"**, on any platform: Windows, macOS, Linux, Android,
  Android TV, Fire TV, LibreELEC, CoreELEC, OSMC or Raspberry Pi.
- **Your shows and movies scanned into the Kodi library.** CableBox reads
  titles, genres, years, studios, tags and running times from the library.
  Folders that aren't in the library can be used too; see *Programming sources*.
- **Optional:** folders of commercials, bumps, station IDs, sign-off and sign-on
  clips, and music for the guide and weather channels. You can collect these
  yourself; CableBox only ever plays files you have.

---

## Installing

**From the official Kodi repository** (pending approval):
*Add-ons → Install from repository → Kodi Add-on repository → Program add-ons → CableBox 42*.

**From a zip file:**

1. Download the latest `script.cablebox42-x.y.z.zip` from this repository's
   releases, or build one by zipping the `script.cablebox42` folder.
2. In Kodi: *Settings → System → Add-ons* → turn on **Unknown sources**.
3. *Settings → Add-ons → Install from zip file* → choose the zip.
4. CableBox 42 appears under *Add-ons → Program add-ons* and *Video add-ons*.

To update, install the newer zip over the top. Your channels, pinned shows and
settings are kept.

---

## Quick start

1. Open **CableBox 42**. The first time, a welcome screen asks how to start:
   **Set it all up for me** (the steps below) or **I'll set it up myself**
   (you get just the TV Guide on 2 and the Weather Channel on 3, and the
   Channel manager opens so you can add your own channels).
2. If you have folders of old commercials and bumps, point it at them. You can
   skip this and add them later in Settings.
3. Type your city for the weather channel, or skip it if Kodi's own weather
   service is already set up.
4. Untick any suggested channels you don't want.
5. Say **Yes** to the two recommended extras:
   - **Overnight sign-off:** channels go off the air from 12 AM to 5 AM with a
     *Please Stand By* card. The guide and weather channels stay on.
   - **Prime time:** from 8 to 11 PM, each channel airs its best shows in fixed
     weekly slots, and movie channels show a movie at 8.
6. Choose **Start watching**.

That's it. To fine-tune, use the **Channel manager**, the **Weekly planner**
and *Settings → Tools →* **Move shows between channels**.

---

## Watching TV

| Remote button | What it does |
|---|---|
| **CH+ / CH−**, **Up / Down**, **Page Up / Down** | Change channel, with a burst of static |
| **Number keys** | Go straight to a channel. "CH 1_" shows while you type |
| **Left** | Last channel (jump back and forth) |
| **Right** | "What's on now": every channel and its current show |
| **OK / Info** | Show or hide the channel banner (now, next, progress) |
| **Menu / Context** | What's on now, last channel, **sleep timer**, *Don't air this show here*, turn off |
| **Back / Stop** | Turn off the TV (asks first, unless you switch that off in Settings) |
| **Volume / Mute** | Work as normal |
| Pause, seek, skip | Ignored. It's live TV |

**The channel banner** slides up when you change channel. It shows the
channel number and call letters, the current show (with season, episode and
episode title), its time slot and progress, and what's on next.

**Leaving the TV.** Press Back to turn it off. If you press **Home** instead,
CableBox notices within a couple of seconds and switches itself off. It never
stops, replaces or interferes with videos you play yourself from the library.

**Your watch progress is left alone.** Kodi normally saves a resume point
and can mark an episode as watched whenever *anything* plays it, so channel
surfing would fill your "In progress" list. CableBox notes each show's
resume point, watched status and last-played date before airing it, and puts
them back afterwards (even after a crash or power cut). Turn this off in
*Settings → Viewing → Keep my watch progress untouched*. To tidy a list that
filled up before this protection existed, use **Clean up my 'In progress'
list** (*Settings → Tools*): tick what you're really watching and the rest is
cleared.

**Sleep timer.** Menu → *Sleep timer* (15 minutes to 2 hours). There's an
optional setting to put the TV into standby through HDMI-CEC when it runs out.

---

## How the schedule works

You don't build a schedule. Each channel keeps a rolling schedule, about
12 hours ahead by default, that extends itself:

- **When you tune in**, the channel's schedule is checked and topped up.
- **While you watch**, a background helper keeps every other channel ready,
  starting with the channels next to yours.
- **While the TV is off**, Kodi's background service tops up every channel
  every 20 minutes.

What airs when:

- **Programs start on a clock.** The default is :00 and :30, which you can
  change per channel to the hour, every 15 minutes, or no clock (back to back).
- **The leftover time becomes breaks.** A 22-minute sitcom in a 30-minute slot
  gets about 8 minutes of commercial breaks, spread through the show and at the
  end. Each break ends with a bump, and the last one ends with a station ID if
  the channel has them.
- **Series play in order.** Each show continues with its next episode.
- **Lineup style:**
  - *Same show same time every day*: weekdays get the same lineup each day, and
    each weekend day has its own.
  - *Shuffle*: picks change all the time.
- **Movies** don't get cut into by default. Commercials play between films
  instead.
- **Pinned shows** from the weekly planner always start on time. Automatic
  picks never run into them.
- **No commercials?** The gaps show a short *Up next* or station card instead.

Editing a channel rebuilds its schedule from now. Episode progress is kept, so
your shows carry on where they were.

### One home channel per show

Like real cable, each TV show has **one home channel**: the channel it fits
best. In order of priority:

1. Your explicit choices: shows picked by name, or ticked in *Move shows
   between channels*.
2. Specific matches: a folder, a movie collection, a tag, a smart playlist, a
   studio.
3. The show's **main genre**. Kodi lists genres most important first, so *Good
   Eats* (Documentary, Comedy) lands on the documentary channel.
4. Decade channels, then the catch-all "everything" channel, which gets
   whatever fits nowhere else.

A channel left with almost nothing is topped up with a few shows that suit it
nearly as well, so no channel runs the same two shows all day. Your pinned
slots and time blocks always air what you put there.

**Never the same show on two channels at once.** Even when a show is
allowed on several channels (because you chose that, or with repeats
allowed), CableBox checks what every other channel is airing, including their
pinned slots, before it picks. Flipping from channel to channel, you won't land
on the same episode twice.

*Settings → Programming → Shows on more than one channel*:

| Option | Behaviour |
|---|---|
| **TV shows on one channel each** (default) | Movies can still repeat across movie channels, as on real cable (never at the same time) |
| **Everything on one channel each** | Movies too |
| **Allow repeats on any channel** | The old behaviour; still never at the same time |

---

## Building and editing channels

### Main menu

| Item | What it's for |
|---|---|
| **Watch TV** | Turn the TV on |
| **What's on now** | Every channel with the show airing right now. Pick one to tune straight to it |
| **Channel manager** | Add, edit, delete and renumber channels |
| **Weekly planner** | Open a channel's 7-day grid |
| **Settings and tools** | All settings, plus the **Tools** page below |
| **Help** | |

On first run, before you have channels, the menu offers **Set up my channels** instead.

### Settings → Tools

Less-used jobs live on their own page in Settings, so the menu stays short.
Each button closes Settings and opens the tool.

| Tool | What it's for |
|---|---|
| **Build my lineup automatically** | Create a lineup from your library: replace yours, or add to it |
| **Quick setup** | For every channel at once: overnight sign-off hours on or off, and prime-time lineups built or removed, with your choice of hours |
| **Move shows between channels** | Pick a show or movie, then tick the channels it should air on. It airs exactly there |
| **Check my videos** | Lists commercials, bumps and videos that can't be used, and why |
| **Clean up my 'In progress' list** | Clears resume points left by channel surfing. You keep the ones you tick |
| **Rebuild schedules** | Plan every channel again from now (episode progress is kept) |

### What the lineup builder creates

| Channel | Contents |
|---|---|
| 2 – TV Guide | The scrolling program guide |
| 3 – Weather Channel | Your local forecast |
| 4 – Channel 4 | Every TV show you own: your local independent station |
| Genre networks | One per TV genre with 3 or more shows (Comedy Channel, Sci-Fi Channel, Cartoon Corner…) |
| Studio showcases | When you have enough from one studio (Disney Showcase, Hanna-Barbera Showcase…) |
| Retro 70s / 80s / 90s | TV shows from each decade |
| Movie channels | Movie Channel, one per big movie genre, and Classic Movies (before 1990) |

### Channel types

| Type | Behaviour |
|---|---|
| **Network** | Series and movies on a clock, with commercial breaks inside shows |
| **Movie channel** | Films on a clock, with commercials between them |
| **Loop** | Back to back, no clock, no breaks (good for music videos or cartoons) |
| **Guide channel** | The program guide |
| **Weather channel** | The local forecast |

### Programming sources

A channel can draw from any mix of these:

| Source | Example |
|---|---|
| TV shows from your library | *Seinfeld, Frasier, Cheers* |
| A TV genre | *Comedy* |
| TV shows from a decade | *the 1980s* |
| Movies by genre, years and/or collection | *Horror, 1980–1989* |
| A folder of videos | Each sub-folder is a show, or play the files in random or set order. Works with network shares (SMB/NFS) and USB drives |
| A Kodi smart playlist | Anything Kodi's own rule editor can express |
| A studio or network: movies and shows | *Disney* (matches "Walt Disney Pictures", "Walt Disney Productions"…) |
| A Kodi tag: movies and shows | Tag things in Kodi (*Manage → Manage tags*), then build a channel from the tag |
| Anything whose title contains… | *Christmas* |
| Specific movies | Pick them from a list |

Every long list, such as tags, studios, shows and movies, has a **Search…** row
at the top. Type a few letters to narrow it down. Lists where you can pick
several items keep your ticks across searches; press **Done** when finished.

### Channel options

Open a channel in the **Channel manager**:

| Option | Notes |
|---|---|
| Name, number, call letters, type | Numbers can be **swapped** or **slid** (see below) |
| Programming | The channel's sources |
| **Weekly planner** | Pinned shows and painted off-air hours |
| Time blocks | Different programming at certain times, e.g. *Prime Time 8–11 PM: movies* |
| Off-air hours | Sign-off times, the off-air screen, sign-off and sign-on clips |
| **What's on this channel** | A checklist of every show and movie the channel airs. Untick what doesn't belong |
| Commercials / Break into shows / Bumps | On or off for this channel |
| Lineup style | Same show same time every day, or shuffle |
| Programs start on | :00 and :30, the hour, every 15 minutes, or no clock |
| Channel commercials / bumps folder | Override the global folders for this channel |
| Station ID clips | "You're watching…" clips played between programs |
| Preview today's schedule | The next 12 hours as a list |

**Fine-tuning tips:**

- *Good Eats* landing on the Comedy Channel? Use **Move shows between
  channels**, pick *Good Eats* and tick only the channels it belongs on.
- While watching: **Menu → Don't air '…' on this channel**.

**Renumbering:** give a channel a number that's already taken, and CableBox
offers to **swap** the two or **slide** the channels in between along by one.
For example, moving Weather from 24 to 3 pushes the old 3–23 up to 4–24.
*Channel manager → Rearrange channel numbers* can also close gaps (2, 3, 4…).
Renumbering never interrupts what's airing.

---

## The weekly planner

*Menu → Weekly planner* (or *Channel manager → a channel → Weekly planner*).

Monday to Sunday run across the screen and half-hours run down it. The line at
the top describes the slot under the cursor. Pinned shows are coloured, time
blocks are light blue, off-air hours are grey, and empty slots are filled
automatically.

| Button | Action |
|---|---|
| Arrows | Move around (the grid scrolls through the whole day) |
| Page Up / Down, CH+ / CH− | Jump 7 hours |
| **OK** on an empty slot | *Pin a show here* or *Make off-air from here* |
| **OK** on a pinned show | Change the show, start time, length, days or order; rename; **start the series over from episode 1**; remove it from one day or every day |
| **Menu** | Copy a day's pins to other days, clear a day, off-air screen and clips, preview what airs next |
| Back | Done (changes are saved as you go) |

**Pinning a show** asks four things:

1. **What:** any programming source (usually one show).
2. **How long:** *Match the show* (rounded up to the channel's slot), 30 minutes,
   1 hour, 90 minutes, 2 or 3 hours, or a custom length. If two episodes fit,
   two air back to back.
3. **Which days:** this day only, weekdays, every day, weekends, or pick days.
4. **Order:**
   - *In order*: the slot keeps its own place in the series, so Friday's
     Seinfeld continues week after week, whatever else the channel airs.
   - *Random*: any episode.

If a new pin overlaps an existing one, CableBox asks before replacing it on
the overlapping days.

**Automatic prime time.** *Settings → Tools → Quick setup → Build prime-time lineups* (also
offered when you first build your lineup) fills 8–11 PM, or hours you choose,
with pins:
- **Network channels:** their best shows by your library's ratings, then the
  most episodes. Half-hour comedies come first and hour-long dramas later, each
  night has its own lineup, and each slot continues in order week to week.
- **Movie channels:** a *Movie at 8* every night.

These pins are labelled *(automatic prime time)* in the planner. Edit one and
it becomes yours, so rebuilding prime time later leaves it alone. Pins you made
yourself are never touched.

A show you pin can still air at other times through the channel's automatic
programming. To keep it to its pinned slot only, untick it in **What's on this
channel**.

---

## Commercials, bumps, station IDs and sign-off clips

All of these are ordinary video files in folders you choose: local drives,
USB disks or network shares.

| Kind | Where to set it | When it plays |
|---|---|---|
| **Commercials** | Settings → Programming (global), or per channel | In breaks during and between programs |
| **Bumps** | Settings → Programming (global), or per channel | At the end of each break ("…and now back to") |
| **Station IDs** | Per channel | Right before each new program ("You're watching…") |
| **Sign-off clips** | Per channel → Off-air hours | When the channel signs off (anthem, farewell) |
| **Sign-on clips** | Per channel → Off-air hours | When the channel comes back on the air |
| **Guide / weather music** | Settings | Behind the guide and weather channels |

Tips:

- **A few dozen commercials of mixed lengths** (15, 30 and 60 seconds) fill
  breaks almost exactly. Clips longer than 10 minutes are ignored.
- CableBox reads each clip's length straight from the file, so no library scan
  is needed. It can read MP4, M4V, MOV, MKV, WebM, AVI, MPEG-TS, MPG, VOB, WMV
  and FLV.
- **Check my videos** lists clips whose length can't be read (remux them to
  .mp4 or .mkv) and AV1 clips your device can't decode.

---

## Off the air

Paint off-air hours in the **weekly planner** (OK → *Make off-air from here*)
or set them in *Channel manager → channel → Off-air hours*. Each window has a
sign-off time, a sign-on time and the nights it applies to.

While a channel is off the air it shows either:

- **A 1950s "Please Stand By" test card**, with the channel number and name in
  the centre and "Programming resumes at 7:00 AM", or
- **Colour bars**.

Optionally a **sign-off clip** plays as the channel goes off the air, and a
**sign-on clip** plays just before programming resumes. A show that's still
running at sign-off time finishes first, as on real TV.

---

## Holidays

CableBox follows the holiday calendar the way the networks did
(*Settings → Seasons*, on by default):

| Season | Run-up | All-out |
|---|---|---|
| **Halloween** | October 1–30, growing toward the end of the month | October 31, all day |
| **Thanksgiving** | – | Thanksgiving Day (fourth Thursday of November) |
| **Christmas** | Day after Thanksgiving to December 23, growing toward Christmas | December 24 and 25, all day |

- **In the run-up** a share of each channel's programmes are holiday ones,
  starting small and growing toward the day. Movie channels get more.
  *How much in the weeks before* sets the share: a little, some (default)
  or lots.
- **On the big days** every channel airs its holiday programmes all day, as
  long as it has any, then goes back to its usual shows. The automatic
  prime-time lineups step aside on those days. Slots you pinned yourself
  in the weekly planner still air.
- **Holiday programmes always come from the channel's own shows and movies**,
  so a kids' channel gets *It's the Great Pumpkin* rather than a slasher film,
  and a channel with nothing seasonal just carries on as normal.
- A holiday special won't repeat on any channel within 18 hours on the big
  days, or within a week during the run-up.
- **Holiday commercials and bumps:** each season can have its own folders.
  They play in every break on the big days and in a growing share of breaks
  during the run-up. Without them, the usual folders are used.
- **The rest of the year** (*Save holiday episodes and movies for their
  season*, on by default), Christmas and Thanksgiving episodes and movies, and
  anything that's explicitly Halloween, are kept out of the automatic schedule.
  Plain horror and monster shows still air all year. Slots you pinned yourself
  are never changed.

**What counts as holiday programming** (*Settings → Seasons*, editable for each
season):

1. **Kodi tags** on movies and TV shows: the main way. Any tag containing
   one of the season's words counts, whatever the capitalisation. With the
   default *halloween*, the tags *Halloween*, *Halloween Classics* and
   *kids-halloween* all count. Defaults: *halloween, spooky, horror* ·
   *thanksgiving* · *christmas, xmas, holiday*.
2. **Kodi genres**: Horror and Mystery for Halloween, and Christmas and
   Holiday for Christmas, by default. Empty the field to leave genres out.
3. **Titles, as a safety net.** Kodi can't tag a single episode, so episode
   and movie titles such as *Treehouse of Horror* or *A Charlie Brown
   Christmas* count too.

Tagging a whole show (an anthology of Halloween specials, say) or a movie in
Kodi is the surest way to get it into the holiday lineup. Out of season, items
tagged with the holiday's own name (*halloween*, *thanksgiving*,
*christmas*/*xmas*) are held back; horror and mystery air all year.

## The guide channel

A scrolling grid of every channel with what's on now, in 30 minutes and in an
hour, and promos for upcoming movies and long programs. Press **OK** on the
guide to pick a channel. Add music under *Settings → Programming → Guide channel
music folder*, and change the title with *Guide title*.

Listings appear immediately. A channel whose listings are still being prepared
shows *Updating listings…* and fills in shortly afterwards.

---

## The weather channel

Pages rotate every 10 seconds:

- **Current conditions:** temperature, conditions, humidity, dew point, feels
  like, wind, pressure, UV index.
- **Local forecast:** an old-style TODAY… TONIGHT… TOMORROW… text forecast.
- **Extended forecast:** 4 days with icons, highs and lows.
- **The next few hours:** hourly temperatures and conditions, plus sunrise and
  sunset.

A conditions ticker scrolls along the bottom.

**Where the weather comes from** (*Settings → Weather*):

- **Automatic** (default): Kodi's own weather service if one is set up
  (*Settings → Services → Weather*), otherwise Open-Meteo.
- **Open-Meteo**: free, no account or key. Type a city (e.g. `Springfield, IL`) or
  `latitude,longitude`.
- Units follow Kodi's regional settings, or force °F or °C.

Add smooth jazz under *Weather channel music folder* for the full effect.

---

## CRT effect

*Settings → Viewing → CRT effect*:

| Setting | What you get |
|---|---|
| **Off** | A clean modern picture |
| **Subtle** | Fine scanlines and gently darkened corners |
| **Full** | Adds curved-glass corners, a faint phosphor stripe mask, and a slow rolling hum bar |

The effect is a set of transparent layers drawn over the picture. The video
itself isn't processed, so it stays light even on small boxes, and hardware
decoding is unaffected. The only ongoing cost is the moving hum bar, which
makes Kodi redraw its interface every frame. If you'd rather avoid that, use
Subtle.

The green **CH 03** channel number always has its own CRT styling: glow,
colour fringing, scanlines and a faint flicker.

---

## Home screen, Favourites and phone remotes

**Launching:**

- **Favourites:** on CableBox 42 in Add-ons, open the context menu → *Add to
  favourites*.
- **Skins with a customisable main menu** (Arctic Zephyr, Aeon Nox, Titan,
  Bello… via Skin Shortcuts): add a menu item with one of these actions.

| Action | Opens |
|---|---|
| `RunScript(script.cablebox42)` | The CableBox menu |
| `RunScript(script.cablebox42,watch)` | The TV, on the last channel |
| `RunScript(script.cablebox42,watch,5)` | The TV, on channel 5 |
| `RunScript(script.cablebox42,wizard)` | The lineup builder |

- **Appliance mode:** *Settings → Viewing → Turn the TV on when Kodi starts*.
  Combine it with *Go straight to TV when opened*.

**Home-screen widgets.** If your skin lets you put CableBox 42 on the home
menu and shows a preview widget of that item's content, the widget becomes a
**"what's on now" channel list**. Selecting a channel turns the TV on at that
channel.

**Phone remotes.** Yatse, Kore and other Kodi remotes work as CableBox remotes.
The channel and number buttons map to standard Kodi buttons. Browsing CableBox
42 from a remote's add-on section should show the same channel list, so you can
tap to tune. Yatse custom commands can call the `RunScript` actions above.

---

## Settings reference

**Programming**

| Setting | Default | |
|---|---|---|
| Commercials folder | – | Global commercials |
| Bumps / station ID folder | – | Global bumps |
| Commercial breaks per half hour | 2 | 0–4 |
| Guide channel music folder | – | Music behind the guide |
| Guide title | *CableBox 42 Program Guide* | |
| Shows on more than one channel | TV shows on one channel each | Or everything on one channel each, or allow repeats |
| Short programmes (under 12 min) | Pack several into one time slot | Back-to-back like a cartoon block (next episodes of the same series, or several short films), a break after each. Or *only where I pinned them* (skipped by the automatic schedule while anything longer is available), or *one per time slot* |
| AV1 videos | Automatic | Automatic / Always skip / Always play (see below) |
| Schedule ahead (hours) | 12 | 6, 12 or 24 |

**Viewing**

| Setting | Default | |
|---|---|---|
| Start on channel | 0 | 0 means the last channel watched |
| Show channel banner for | 6 s | 3, 6 or 10 seconds |
| Static between channels / Static sound | On / On | |
| CRT effect | Off | Off / Subtle / Full |
| Keep my watch progress untouched | On | Puts back resume points, watched status and last-played dates after CableBox plays something |
| Ask before turning off | On | |
| Go straight to TV when opened | Off | Skip the CableBox menu |
| Turn the TV on when Kodi starts | Off | Only right after Kodi starts, and never if you've already started watching something else |
| Sleep timer also puts the TV in standby (CEC) | Off | |

**Weather**

| Setting | Default | |
|---|---|---|
| Weather data from | Automatic | Automatic / Kodi weather service only / Open-Meteo only |
| City or lat,lon | – | For Open-Meteo |
| Units | Automatic | Automatic / Fahrenheit / Celsius |
| Weather channel title | *Your Local Forecast* | |
| Weather channel music folder | – | |

---

**Seasons** (see [Holidays](#holidays))

| Setting | Default | |
|---|---|---|
| Holiday programming | On | Halloween, Thanksgiving and Christmas |
| How much in the weeks before | Some | A little / Some / Lots |
| Halloween / Thanksgiving / Christmas: On | On | Each season separately |
| Holiday commercials folder | – | Optional, per season |
| Holiday bumps folder | – | Optional, per season |
| Tags | *halloween, spooky, horror* · *thanksgiving* · *christmas, xmas, holiday* | Any Kodi tag containing one of these words |
| Genres | *Horror, Mystery* · – · *Christmas, Holiday* | Empty = don't use genres |
| Save holiday episodes and movies for their season | On | Keeps Christmas episodes out of July |

**Tools**: see [Settings → Tools](#settings--tools).

## Video formats and AV1

CableBox plays whatever Kodi can play, using Kodi's own player and your
device's hardware decoding.

**AV1** is the exception worth knowing about. Many devices (for example the
ODROID N2, Raspberry Pi 4 and older Android TV boxes) can't decode AV1 in
hardware. Kodi then falls back to the CPU, which can stutter, freeze or crash.
Videos downloaded from YouTube are very often AV1.

- With *AV1 videos: Automatic*, CableBox asks the Amlogic video driver (on
  CoreELEC) whether it can decode AV1, and **skips AV1 files** if it can't.
  Other devices are assumed to cope; choose **Always skip** if yours doesn't.
- The codec comes from Kodi's library information or, for folders and clips,
  from the file's headers.
- **Check my videos** lists every AV1 file being skipped, per channel and per
  clip folder. Re-encode them to H.264 or H.265 to use them.

---

## Files and hand-editing

Everything lives in the add-on's data folder,
`userdata/addon_data/script.cablebox42/` inside Kodi's data folder:

| System | Kodi data folder |
|---|---|
| LibreELEC / CoreELEC | `/storage/.kodi/` (network share: *Userdata*) |
| Windows | `%APPDATA%\Kodi\` |
| macOS | `~/Library/Application Support/Kodi/` |
| Linux / OSMC / Raspberry Pi OS | `~/.kodi/` |
| Android | `Android/data/org.xbmc.kodi/files/.kodi/` |

| File | Contents |
|---|---|
| `channels.json` | Your lineup: channels, sources, pinned shows, time blocks, off-air hours |
| `schedules/<id>.json` | Each channel's rolling schedule and episode bookmarks (rebuilt automatically) |
| `durations.json`, `codecs.json` | Cached running times and video codecs of files |
| `state.json` | Last channel watched, weather location lookup |

**Example channel in `channels.json`:**

```json
{
  "id": "a1b2c3d4", "number": 5, "name": "Comedy Channel", "callsign": "CC",
  "type": "network", "slot": 30, "lineup": "strip",
  "commercials": true, "midroll": true, "bumps": true,
  "sources": [{"type": "tvgenre", "value": "Comedy"}],
  "exclude": ["Good Eats"],
  "slots": [
    {"id": "r1", "label": "Seinfeld", "days": [4], "start": "20:00", "minutes": 60,
     "order": "inorder", "sources": [{"type": "tvshow", "value": ["Seinfeld"]}]}
  ],
  "dayparts": [
    {"label": "Prime Time", "start": "20:00", "end": "23:00", "days": "weekends",
     "sources": [{"type": "movies", "genre": "Comedy"}]}
  ],
  "offair": [{"start": "00:00", "end": "07:00", "days": "all"}],
  "offair_style": "standby",
  "ids_path": "smb://nas/tv/station-ids/comedy/",
  "signoff_path": "smb://nas/tv/signoff/",
  "commercials_path": "smb://nas/tv/ads/80s/"
}
```

- **Days** can be `"all"`, `"weekdays"`, `"weekends"`, or a list of numbers
  (0 = Monday … 6 = Sunday).
- **Source types:** `tvshow`, `tvgenre`, `tvdecade`, `movies` (with `genre`,
  `years`, `set`, `tag`), `folder` (with `path` and `mode`: `shows`, `random`
  or `sequential`), `playlist`, `studio`, `tag`, `keyword`, `movie`.
- **Studio, tag and keyword** sources take `"what"`: `both`, `tv` or `movies`.

After editing by hand, use *Settings → Tools →* **Rebuild schedules**. Keep a copy of
the original first.

---

## Troubleshooting

**A channel shows "No programming."** Its sources found nothing. Check that
your media is scanned into the Kodi library, then check the channel's
*Programming*.

**A channel shows "Technical difficulties."** A file wouldn't play: it may be
missing, or on a network share that's offline. CableBox moves on when the next
item starts.

**"Technical difficulties", then a different show.** Kodi couldn't open the
scheduled video (a damaged file, or one it can't read). CableBox shows the
card for a few seconds, then fills the time with another show from the same
channel, picking up after each commercial break. The file is kept off the
schedule for 3 days, then tried again. *Settings → Tools → Check my videos*
lists these files and can put them back on right away once they're fixed. If a
whole drive or share is offline, its files are not taken off the schedule.

**Breaks show "Up next" cards instead of commercials.** No commercials folder
is set, or none of its clips could be read. Run **Check my videos**.

**A video plays sound but no picture, or Kodi freezes or crashes on certain
videos.** It's very likely AV1 on a device without AV1 hardware decoding. See
[Video formats and AV1](#video-formats-and-av1).

**The CableBox menu opens by itself at startup or after a movie.** Update to
the latest version. Early test builds didn't understand the content requests
that some skins make for add-ons placed on their home menu.

**The guide says "Updating listings…"** That's normal right after installing or
updating. Listings appear within a minute or two as each channel is prepared.

**Pinned shows don't appear yet.** Changes apply from now. Open *Preview
today's schedule*, or use *Rebuild schedules*.

**Getting a log for a bug report:**

1. Turn on *Settings → System → Logging → Enable debug logging*.
2. Reproduce the problem.
3. Send the `kodi.log` (and `kodi.old.log` if Kodi restarted). On
   LibreELEC/CoreELEC they're in the *Logfiles* network share or
   `/storage/.kodi/temp/`.

CableBox's lines are tagged `script.cablebox42`.

Please report issues in the
[Kodi forum support thread](https://forum.kodi.tv/showthread.php?tid=389521) or at
<https://github.com/SeadogMcGrog/script.cablebox42/issues>, with your Kodi
version, device, what you were doing, and a link to your log on
<https://paste.kodi.tv/>.

---

## Credits and license

CableBox 42 is designed, tested and maintained by **Seadog McGrog**. Much of
the code was written with the help of [Claude](https://www.anthropic.com/claude),
an AI assistant made by Anthropic. Anthropic is not affiliated with this project
and has not reviewed or endorsed it.

Inspired by [FieldStation42](https://github.com/shane-mason/FieldStation42) by
Shane Mason, which pioneered this channel-flipping way of watching your own
media. CableBox 42 is a separate implementation for Kodi and contains no
FieldStation42 code. It is not affiliated with that project.

All artwork in this add-on (test card, channel digits, backgrounds, CRT
overlays) is original. CableBox 42 plays only media you provide.

Licensed under the **Mozilla Public License 2.0**; see [LICENSE.txt](LICENSE.txt).

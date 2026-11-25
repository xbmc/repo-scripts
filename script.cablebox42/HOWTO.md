# CableBox 42 — How-To Guide

Step-by-step walkthroughs for everything CableBox 42 does, from the first
install to running your own fully branded cable lineup. Every step uses the
remote: arrows to move, **OK** to pick, **Back** to leave.

The [README](README.md) is the reference (every setting, every option). This
guide is the "how do I…?" companion.

---

## Contents

**Getting started**
1. [Before you start: get your library ready](#1-before-you-start-get-your-library-ready)
2. [Install CableBox 42](#2-install-cablebox-42)
3. [Build your first lineup](#3-build-your-first-lineup)
4. [Watch TV: the remote, the banner and the menu](#4-watch-tv-the-remote-the-banner-and-the-menu)

**Make it your own**

5. [Understand what the setup built](#5-understand-what-the-setup-built)
6. [Add, edit, rename and renumber channels](#6-add-edit-rename-and-renumber-channels)
7. [Give each channel its own logo, bumps, IDs and commercials](#7-give-each-channel-its-own-logo-bumps-ids-and-commercials)
8. [Time-of-day branding (CAM Jr. in the morning)](#8-time-of-day-branding-cam-jr-in-the-morning)
9. [Put every show on the right channel](#9-put-every-show-on-the-right-channel)
10. [Pin shows to fixed times with the weekly planner](#10-pin-shows-to-fixed-times-with-the-weekly-planner)
11. [Time blocks: Saturday morning cartoons, movie nights](#11-time-blocks-saturday-morning-cartoons-movie-nights)
12. [Sign-off hours and prime time for every channel at once](#12-sign-off-hours-and-prime-time-for-every-channel-at-once)

**Extras**

13. [Closed captions](#13-closed-captions)
14. [Commercials and bumps that fill the breaks properly](#14-commercials-and-bumps-that-fill-the-breaks-properly)
15. [The guide channel and the weather channel](#15-the-guide-channel-and-the-weather-channel)
    - [Boombox TV: a music video channel](#boombox-tv-a-music-video-channel)
    - [Music channels: songs around the clock](#music-channels-songs-around-the-clock)
16. [Holidays](#16-holidays)
    - [Plan a Turkey Day marathon](#plan-a-turkey-day-marathon)
17. [The look: static, CRT effect, turn-on and turn-off](#17-the-look-static-crt-effect-turn-on-and-turn-off)
18. [Start CableBox from the home screen, a favourite or Kodi's start-up](#18-start-cablebox-from-the-home-screen-a-favourite-or-kodis-start-up)

**When something's off**

19. [Fix-it recipes](#19-fix-it-recipes)
20. [Start over, back up, or move to a new box](#20-start-over-back-up-or-move-to-a-new-box)
21. [Report a problem](#21-report-a-problem)

---

# Getting started

## 1. Before you start: get your library ready

CableBox builds channels from **Kodi's own library**, so the better your library
is tagged, the better your lineup.

**Must have**

- Your TV shows (and movies, if you want movie channels) **scanned into the
  Kodi library**: *Videos → Files → Add videos…*, choose the folder, set the
  content type to *TV shows* or *Movies*, and let Kodi scan. Later scans (and
  *Clean library*) reach CableBox by themselves, about 30 seconds after Kodi
  finishes: new episodes and shows air from each channel's next programme.
- Each show shows up under *TV shows* with its **genres** and episodes.

**Nice to have (makes a big difference)**

| Library info | What CableBox does with it |
|---|---|
| **Genres** (Comedy, Western, Animation…) | Genre channels: Comedy Corner, Tumbleweed TV, Animation Station… |
| **Studio / network** (NBC, Nickelodeon, PBS…) | Sends a show to the station for the network it aired on: NBC → Keystone, Nickelodeon → Chameleon, PBS → PES |
| **Premiered year** | Decade channels you can add, and the "classic" movie channel |
| **Kodi tags** (*educational*, *Christmas*…) | Tag channels, PES for anything tagged *educational*, holiday programming |
| **Ratings** | The automatic prime-time lineups put your best-rated shows on first |

Most scrapers fill genres and network automatically. To check a show: open it
in Kodi → *Information*. To fix one: *Information → Refresh*, or edit its
`tvshow.nfo`.

**Optional extras to gather** (any time later is fine):

- A folder of **old commercials** (15/30/60-second clips work best). Without
  one, channels get *house breaks*: short breaks of promos for your own shows,
  ads for the guide and weather channels and made-up retro commercials
- A folder of **bumps** ("We'll be right back") and **station IDs**
- A folder of **background music** for the guide and weather channels
  (smooth jazz and elevator music are the classics)
- **Logos** for your channels — transparent PNGs look best
- **Music videos** for Boombox TV — Kodi's music video library, a folder, or both;
  name them `Artist - Title (Year).mkv` (see [Boombox TV](#boombox-tv-a-music-video-channel))
- **Movie extras** (making-of pieces, documentaries, interviews) in an `Extras`
  folder next to each movie — see below

**Movie extras**

CableBox reads disc extras the way Kodi does: from a folder named `Extras` in
the movie's own folder (for disc rips, `VIDEO_TS\Extras` or `BDMV\Extras` works
too). Subfolders are fine. CableBox only reads these folders; it never renames
or moves anything.

```
Movies\2001 A Space Odyssey (1968)\
    2001 A Space Odyssey (1968).mkv
    Extras\
        The Making Of A Myth.mp4
        Standing On The Shoulders Of Kubrick.mp4
        Theatrical Trailer.mp4          ← skipped (trailer)
        Interviews\
            title_t03.mkv               ← airs: it's in Interviews
```

- Making-of pieces, documentaries, featurettes, interviews and anything else
  with a readable name count. Deleted, extended and alternate scenes, bloopers,
  trailers and promos, galleries, music videos, short films and commentaries
  don't, and neither does anything under a minute.
- Names like `title_t03.mkv` or "Bonus 2" are skipped. To keep one, rename it,
  or put it in a subfolder of `Extras` named **Behind the scenes**, **Making of**,
  **Interviews**, **Featurettes** or **Documentaries**: everything in those
  always counts. (*Settings → Advanced → Also air extras with unrecognised
  names* counts them all.)
- Give each movie its own folder. An `Extras` folder shared by several movies
  isn't used.
- Turn **off** Kodi's *Settings → Media → Library → Video library → Ignore video
  extras on scan* (it is on by default). While it's on, an extra that has its own
  `.nfo` file is added to Kodi as a movie of its own and turns up on your movie
  channels (extras without an `.nfo` are left out). With it off, Kodi files every
  extra under its movie instead. Either way, the Behind the scenes channel finds
  them itself: it reads the `Extras` folders directly.
- CableBox looks through the folders and measures the videos in the background
  while the TV is off, so the first look at a big library can take a while.
  *Settings → Tools → **Check extras*** shows every movie's extras with their
  length and whether they air, and why not. Its summary says how many lengths
  are measured so far ("Lengths measured: 2,840 of 3,092"). While some are
  still to do it offers **Look now** (*Look for movie extras*), which does
  the rest straight away with a progress bar; *Cancel* stops it and keeps what
  was found so far. When it finishes it says how much there is to air. After
  the list it offers what's next: looking for the rest, or adding a Behind
  the scenes channel when you have enough and don't have one yet.

> **Tip:** Keep clips on the same drive as your shows. A sleeping USB drive or
> an offline network share is the most common cause of a missed break.

---

## 2. Install CableBox 42

**From the official Kodi repository (recommended — updates arrive by themselves)**

1. *Add-ons → Install from repository → Kodi Add-on repository*
2. *Program add-ons → CableBox 42 → Install*

**From a zip (test builds, or a box without the official repository)**

1. Download `script.cablebox42-x.y.z.zip` from the
   [releases page](https://github.com/SeadogMcGrog/script.cablebox42/releases).
2. *Settings → System → Add-ons* → switch on **Unknown sources**.
3. *Settings → Add-ons → Install from zip file* → pick the zip.

CableBox appears under *Add-ons → Program add-ons* and *Video add-ons*.

**Updating from a zip:** install the newer zip over the old one. Your channels,
pinned shows, folders and settings are all kept.

---

## 3. Build your first lineup

Open **CableBox 42**. The first time, a welcome screen asks how to start.

### Option A — "Build my lineup" (recommended)

1. CableBox reads your library first (about a minute; *Cancel* stops it). If
   it finds no TV shows or movies it says so straight away.
2. One screen: ***N channels found in your library***, with overnight sign-off
   (12 AM–5 AM) and prime-time lineups. Choose:
   - **Start watching** — everything is set up and the TV comes on.
   - **Customise** — the questions below, then the same lineup your way.
   - **Cancel** — nothing changes.

After *Start watching*, the main menu has **Finish setting up**: commercials,
bumps and station IDs, guide and weather music, music videos and your weather
city. Each says *not set* until you choose it or pick *I don't need this*.

**Customise** asks, in order (every answer can be changed later; nothing is
saved until the last screen's **OK**, and **Back** or **Cancel** on any screen
leaves everything as it was):

1. **"Do you have a folder of old commercials?"** — *Choose folder* and pick it,
   or *Skip*.
2. **Bumpers and station IDs** — pick one:
   - **One folder for every channel** — all channels share one folder of bumps.
   - **A folder for each channel** — choose where (your media drive is best).
     CableBox makes a folder per channel with `bumps`, `ids` and `commercials`
     inside, ready for clips. *Pick this if you want each channel to feel
     different.* (See [section 7](#7-give-each-channel-its-own-logo-bumps-ids-and-commercials).)
   - **Skip for now.**
3. **Music** for the guide and weather channels — the same folder for both, or
   one each, or skip.
   - Only when Kodi's library has no music videos: **"Do you have a folder of
     music videos?"** — *Choose folder* for a Boombox TV channel, or *Skip*.
4. **Your city** for the weather channel (e.g. `Springfield, IL`). Skip it if
   Kodi's own weather is already set up.
5. **Channel names**:
   - **CableBox's stations** — Comedy Corner, Orbit TV, Chameleon... each with
     its name, logo and call letters.
   - **Plain names, I'll brand them myself** — Comedy Channel, Sci-Fi Channel,
     Kids TV... The same shows land on each channel; there are just no stock
     names or logos. Rename them and add your own logos afterwards
     ([section 7](#7-give-each-channel-its-own-logo-bumps-ids-and-commercials)).
6. **Untick any channels you don't want** and confirm. With 30 or more
   music videos, **Boombox TV** is on the list, e.g. *Boombox TV — 210 music
   videos (136 from your library, 74 more in E:\Kodi\Music Videos)*.
7. **Extras** — both ticked; untick what you don't want:
   - **Sign off overnight** — a *Please Stand By* card from 12 AM to 5 AM, like
     real TV. The guide and weather stay on. Channels you already had keep
     their own off-air hours.
   - **Prime-time lineup** — fills 8–11 PM with fixed weekly slots of each
     channel's best shows (movie channels: a movie at 8).
8. **The last check** — e.g. *Replace your 12 channels with these 9 (2-25)?*,
   with the extras and folders you chose. **OK** saves it all; **Cancel** leaves
   your old lineup and settings untouched.
9. CableBox programmes every channel, then asks **Start watching**, **Not now**
   or **What I set up** — every channel, where its shows come from, and its
   folders. (You can see it again any time: *Channel manager → Lineup tools →
   Lineup summary*.)

### Option B — "I'll set it up myself"

You get just the **TV Guide on 2** and a plain **Weather Channel on 25**, and the
Channel manager opens so you can add channels by hand
([section 6](#6-add-edit-rename-and-renumber-channels)). You can still run the
builder later: *Channel manager → Lineup tools → Build my lineup* (it can
replace your lineup or add its channels after yours).

### What a typical automatic lineup looks like

| Channel | What it is |
|---|---|
| 2 | **TV Guide** — scrolling listings for every channel |
| 3, 4, 5 | **Keystone, Beacon, Horizon** — three broadcast networks with a network-style day (morning news, game shows, soaps, after-school cartoons, prime time, late night) |
| 6 and up | **Genre and station channels** — Comedy Corner, Animation Station, Chameleon (kids), Tumbleweed TV (westerns), Orbit TV (sci-fi and fantasy), Red Thread TV (Korean and Chinese dramas)… |
| | **Movie channels** — Popcorn TV (every movie), Picture Show (classics), The Exploration Channel (documentaries) |
| | **Station channels** — The Dexter Channel with your Disney shows and movies, Chameleon with your Nickelodeon shows, Red Thread TV with Korean and Chinese dramas, when you have enough |
| 25 | **Retrocast Weather** |
| 42 | **News 42**, if you have news shows |

Which channels you get depends on what's in your library. Every channel the
builder makes is one of the built-in stations, with its own name and logo; for
anything else (a BBC channel, a horror movie channel, a talk channel) add a
channel yourself ([section 6](#6-add-edit-rename-and-renumber-channels)). A
genre gets a channel of its own only when about five shows would call it home
(it's their best fit). A genre lots of shows list but few have first, such as Action &
Adventure, gets no channel; those shows go to their main genre's channel. Shows whose genres are too small for a
channel are placed on the biggest suitable channel — and the Finder
([section 9](#9-put-every-show-on-the-right-channel)) tells you which ones those
are.

---

## 4. Watch TV: the remote, the banner and the menu

Main menu → **Watch TV** (picks up on the channel you last watched).

| Button | What it does |
|---|---|
| **CH+ / CH−**, **Up / Down**, **Page Up / Down** | Change channel, with a burst of static |
| **Number keys** | Go straight to a channel ("CH 1_" while you type) |
| **Left** | Last channel — flip back and forth |
| **Right** | What's on now: every channel and its current show; pick one to tune there |
| **OK / Info** | Show or hide the channel banner |
| **Menu / Context** | **Closed captions**, caption options, what's on now, last channel, **sleep timer**, *Don't air this show here*, **CableBox menu**, turn off |
| **Subtitle / CC button** | Captions on or off (after a one-time setup — [section 13](#13-closed-captions)) |
| **Back / Stop** | Turn the TV off and go back where you came from (the CableBox menu, or Kodi) |
| **Volume / Mute** | Work as normal |
| Pause, seek, skip | Ignored — it's live TV |

> **The Menu button is where most things live.** The first time you switch the
> TV on, a tip in the corner reminds you: *"Press Menu for captions, sleep timer
> and more."*

**From the TV to your channels and settings:** Menu → *CableBox menu*. The TV
turns off and CableBox's main menu opens; change what you like, then *Watch TV*
turns it back on, on the channel you were watching, with the changes. This
works however you switched the TV on, even with *Skip the menu* on. Back from
the TV returns to the main menu only if you started it there (*Watch TV* or
*What's on now*); otherwise it goes to Kodi.

**The banner** slides up when you change channel: channel number, logo and call
letters, the show (season, episode and title), its time slot and progress, and
what's next.

**It's live.** Shows run on the real clock. Tune in at 7:12 and you join the
7:00 show twelve minutes in. Leftover time in each half hour becomes commercial
breaks. Series always continue with the next episode.

**Your watch progress is safe.** Channel surfing doesn't fill your *In
progress* list or mark episodes watched — CableBox puts back resume points,
watched status and last-played dates after it airs something.

**Sleep timer:** Menu → *Sleep timer* (15 minutes to 2 hours). Optionally it
also puts the TV in standby over HDMI-CEC (*Settings → Start-up & library*). When it runs
out you're left in Kodi, not in a menu.

**"I don't want this show on this channel":** while it's on, Menu → *Don't air
'…' on <channel>*. It's gone from that channel's automatic programming
straight away (bring it back in the channel's *What's on this channel* list).

---

# Make it your own

## 5. Understand what the setup built

Three places answer "what did CableBox just do?":

1. **Channel manager → Lineup summary** — every channel with its station
   identity, where its shows come from (genres, networks, folders…), any
   time-of-day names, off-air hours and pinned shows, then each channel's
   station folder and what's in it, and where to go next.
2. **Channel manager → a channel → What's on this channel** — the complete
   checklist of shows that channel airs. Untick to hide.
3. **Channel manager → Lineup tools → Shows without a good channel** — the shows that *don't*
   have an obvious home ([section 9](#9-put-every-show-on-the-right-channel)).

---

## 6. Add, edit, rename and renumber channels

Main menu → **Channel manager**.

### Add a channel

1. **+ Add a channel**
2. **What kind of channel?**
   - **A built-in station** — pick one (Comedy Corner, Orbit TV, Chameleon...).
     Stations already in your lineup are greyed out with their channel number.
     No name to type: it gets the station's name, logo, call letters and
     shows. Choose a number, see what it airs, and **Add more** or **Done**.
   - **My own channel** — choose the type (*Network*: series with commercial
     breaks; *Movie channel*: films, commercials between them; *Loop*: back to
     back, no clock), then name, number and programming, and finally
     **Give it a logo now?** (*Choose an image* / *Later*).
   - **Music videos** — Boombox: music videos on the clock with breaks between them
     ([Boombox TV](#boombox-tv-a-music-video-channel))
   - **Music channel** — songs from your own music around the clock, no breaks
     ([Music channels](#music-channels-songs-around-the-clock))
   - **TV Guide** / **Weather** — only offered while your lineup has none
   - **Behind the scenes** — making-of pieces and interviews
     from your movies' `Extras` folders ([section 1](#1-before-you-start-get-your-library-ready)).
     The suggested name is **BACKLOT**; give it another name and CableBox
     asks whether to use the BACKLOT logo and corner bug anyway (*Use them* /
     *No logo*). If you already have one, it asks before adding another
     (*Add another* / *Cancel*). It needs no programming: it airs every movie
     whose extras *Check extras* marks *Air*, one movie (or a few short ones)
     per block, with breaks only between segments. A movie gets up to an
     hour per turn; the rest of its extras continue on its next turn.
     Once the channel is added, if CableBox hasn't found any extras yet, it
     asks **Look for movie extras now?** (*Look now* / *Later*). With *Later*
     the channel shows *No programming* until CableBox has looked (in the
     background, while the TV is off). **OK** on that screen asks again
     (*Look now* / *Cancel*), and so does *Look for movie extras* in the
     TV's menu. If it has looked and found nothing to air, the screen says so
     and points to *Check extras*.
3. The **number**. If it's taken you can move that channel
   to the next free number, slide the channels from there up by one, or pick
   another number.
4. **Add programming** (*My own channel*, or *Add more* on a built-in station) — pick a source, then **Add more** as many times as you
   like, and **Done** when finished. **Back** (or **Cancel**) on any step adds
   nothing.

| Source | Example |
|---|---|
| TV shows from my library | Pick *Seinfeld*, *Frasier*, *Cheers* for a Must-See TV channel |
| A TV genre | *Western* → every western you own |
| TV shows from a decade | The 1980s |
| Movies (by genre / years / set) | Horror movies from 1980–1989; the James Bond set |
| A folder of videos | Each sub-folder is a show (in order), or play files randomly or in order |
| A Kodi smart playlist | Anything you can express as a `.xsp` |
| A studio / network | *Disney* → every Disney movie and show |
| A Kodi tag | Everything you tagged *Saturday morning* |
| Anything whose title contains… | *Star Trek* |
| Specific movies | Pick them one by one |

5. The channel editor opens so you can fine-tune it.

### The channel editor (pick a channel in the Channel manager)

Four groups, then *Preview today's schedule* and *Delete channel*. Changes save
as you go.

**Identity**

| Row | What it's for |
|---|---|
| Name / Number / Call letters | Renaming updates the call letters (unless you typed your own), asks about a station's time-of-day names (*Keep them* / *Remove them*), and offers to rename its station folder too |
| Logo | Shows the logo in use and where it comes from. Select to choose an image, use the logo folder, or no logo |
| Names by time of day | Another name and logo for part of the day ([section 8](#8-time-of-day-branding-cam-jr-in-the-morning)) |
| Station folder | The channel's own folder: look inside, create or repair it, adopt an existing folder ([section 7](#7-give-each-channel-its-own-logo-bumps-ids-and-commercials)) |
| Built-in station / Use a built-in station... | Give it a built-in station (the question lists what changes: name, call letters, logo, time-of-day names, the shows it adds), or **Make this channel my own**: the station's logo and time-of-day names go, the channel's name and all its programming stay |

**Programming**

| Row | What it's for |
|---|---|
| Type | Asks whether to use the new type's usual settings (commercials, breaks, bumps, lineup style, start times) or keep the channel's own. For Behind the scenes, Guide and Weather it says the programming sources aren't used (they're kept). A second Guide or Weather isn't offered |
| Programming | Add or remove sources (removing asks first) |
| **What's on this channel** | Checklist of every show it airs — untick to hide |

**Breaks & clips**

| Row | What it's for |
|---|---|
| Commercials / Bumps | What the channel *really* uses and where it comes from. Select to switch them on or off |
| Station IDs | The same for station ID clips. Select to choose a folder for this channel only |
| Break into shows for commercials | Mid-show breaks (off for movie channels by default) |
| Ad flavour | Which retro ads its house breaks run: *Auto*, *General*, *Kids*, *Sports*, *Movies*, *Late night* |
| Channel commercials / bumps folder | Folders for this channel only (station folders are usually easier) |

**Schedule**

| Row | What it's for |
|---|---|
| Weekly planner | Pin shows to times ([section 10](#10-pin-shows-to-fixed-times-with-the-weekly-planner)) |
| Time blocks | Saturday mornings, movie nights ([section 11](#11-time-blocks-saturday-morning-cartoons-movie-nights)) |
| Off-air hours | When this channel signs off |
| Lineup style | *Same show same time every day*, or *Shuffle* |
| Programs start on | :00 and :30, the hour, every 15 minutes, or no clock |

**Also**

| Row | What it's for |
|---|---|
| Preview today's schedule | The next 12 hours |
| Movie extras (Behind the scenes channels only) | How much there is to air; opens *Check extras*. Programming, planner, time blocks, What's on, lineup style and start times aren't shown for this type |
| Delete channel | Asks first: *Cancel* / *Delete* |

Changes apply from the channel's next programme when you close the Channel
manager: what's on air keeps playing, and every show keeps its next episode.

### Renumber

*Channel manager → Rearrange channel numbers*: pick a channel and type its new
number. If the number is taken you can **swap** the two or **slide** the
channels in between over by one. *Close the gaps* renumbers them in order from a number you choose.
Schedules belong to the channel, not the number, so nothing is rebuilt.

---

## 7. Give each channel its own logo, bumps, IDs and commercials

This is what makes channels feel like real stations. You do it with folders —
no menus needed once they're set up.

### Step 1 — Choose a stations folder (once)

*Settings → Channels → Stations folder*. Pick (or create) a folder on your media
drive, e.g. `/storage/media/Stations/` or `D:\Stations\`. If you chose *A
folder for each channel* during setup, this is already done.

### Step 2 — Let CableBox make the folders

*Channel manager → Lineup tools → **Station folders***. For every channel it makes whatever is missing and **never touches
what's already there** — an existing folder is reused, not copied. Then it shows
a report:

```
Station folders  /storage/media/Stations/
  3  Comedy Corner   Comedy Corner
        bumps 2, ids 0, commercials 0   logo: logo.png
  5  Chameleon   Chameleon
        bumps 0, ids 0, commercials 0   logo: none
        CAM Jr.: bumps 1, ids 0, commercials 0
Folders no channel uses   renamed channels? ...
  Old Tumbleweed
```

### Step 3 — Drop files in

```
Stations/
  Comedy Corner/
    logo.png            the channel's logo (transparent PNG looks best)
    bumps/              short clips before the show comes back
    ids/                station IDs, played between programmes
    commercials/        this channel's own commercials
    promos/             your own promos for its shows (optional)
  Chameleon/
    logo.png
    bumps/  ids/  commercials/
    CAM Jr./            a time block's own folder (section 8)
      logo.png  bumps/  ids/  commercials/
```

**When do new files show up?** A new or changed **logo** appears within a couple
of minutes. **Clips** go into the breaks CableBox plans from then on — it plans
each channel several hours ahead (*Settings → Advanced → Schedule ahead*),
so the programme on air keeps its breaks. Closing the Channel manager (or
*Settings → Tools → Refresh schedules*) puts new clips into breaks from each
channel's next programme.

### How CableBox matches a folder to a channel

A folder belongs to a channel when its name is **exactly** one of these
(capitals, spaces and punctuation don't matter):

1. the channel's name — `Comedy Corner`, `comedy-corner`, `COMEDYCORNER`
2. its call letters — `LOL`
3. its number — `3`, `Channel 3` or `CH 3`

So `Disney Showcase 13` will **never** be mistaken for channel 3's folder.
Time-block folders are more forgiving: `Morning - CAM Jr` counts as *CAM Jr.*

Inside a channel folder, `bumps` may also be called `bumpers`, `ids` may be
`station ids` or `idents`, and `commercials` may be `ads`.

### What wins when there's more than one source

| | First choice | Then | Then | Then |
|---|---|---|---|---|
| **Logo** | Time block's own (its folder, its picked image, an image named after it in the logo folder, its built-in logo) | Image you picked in the channel editor | Station folder's `logo.png` | The logo folder, then the built-in station logo |
| **Bumps / commercials** | Time block's folder | Channel's station folder | Channel's own folder (editor) | Shared folder in Settings |
| **Station IDs** | Time block's folder | Channel's station folder | Channel's *Station ID clips* folder | — |

An **empty** folder is skipped, so you can make the folders now and fill them
later.

> **Important:** a channel's *Commercials* and *Bumps* switches (in the channel
> editor) still apply. Clips in `Comedy Corner/commercials/` are ignored if
> Comedy Corner has commercials switched off. *Breaks & clips* warns you about
> exactly this.

### Step 4 — Check it in the channel editor

*Channel manager → a channel → **Breaks & clips*** shows the clips the channel
really uses, and where each comes from:

```
Commercials: off for this channel  Select to switch them on.
Bumps: 2 clips from the station folder
Station IDs: none                  Add clips to the channel's ids folder.
```

*Identity* shows the logo (*Logo: logo.png — From the channel's station
folder.*), and *Identity → **Station folder*** the folder itself:

```
Station folder: Comedy Corner      Select to look inside.
CAM Jr. (06:00-12:00): ...         (one row per time-of-day name)
Create or repair this channel's folders
```

From here you can:

- **Change the logo** (*Identity → Logo*)
- **Look inside** the channel's folder
- **Switch on** bumps or commercials that are off but have clips waiting
- **Create or repair** the channel's folders (adds what's missing, never deletes)
- **Use an existing folder** — adopt a folder no channel uses (typically one from
  before a rename); it's renamed to the channel's name

### Renaming a channel

Change a channel's name, call letters or station in the channel editor and, if
its folder no longer matches, CableBox asks:

> *Rename its station folder too? Old Name → New Name*

Choose **Rename folder** and everything inside comes along. CableBox never
overwrites: if a folder with the new name already exists, it tells you and
leaves both alone.

### Logos without station folders

If you'd rather keep all logos in one place: *Settings → Channels → Logo folder*,
and name each image after the channel's name, call letters or number
(`Comedy Corner.png`, `LOL.png`, `3.png`). Or pick an image directly in the
channel editor (*Identity → Logo → Choose an image*). Kodi can't show SVG — convert
to PNG.

The corner logo ("bug") is set in *Settings → On screen*: on or off, which corner,
and opacity (30–100%).

---

## 8. Time-of-day branding (CAM Jr. in the morning)

A channel can go by another name, call letters and logo for part of the day —
like a kids' channel that's *CAM Jr.* from 6 AM to noon and *Cam O Nite* after
8 PM. The banner, the corner logo and the guide switch over by themselves.

1. *Channel manager → channel → Identity → **Names by time of day***
2. **+ Add a name** → name (e.g. *CAM Jr.*), start, end. Times may cross
   midnight (20:00–06:00).
3. Optional: pick a name → *Choose logo…* (or put `CAM Jr.png` in the logo folder)
4. Optional: give it its own clips — *Identity → Station folder → Create or repair
   this channel's folders* makes `Stations/<channel>/<block>/bumps/`, `ids/`
   and `commercials/`. Drop a `logo.png` in the block's folder too.

Built-in stations like Chameleon come with theirs already set. Rename the
channel and CableBox asks whether to keep them; *Make this channel my own*
removes them and keeps the ones you made.

---

## 9. Put every show on the right channel

### How CableBox decides

By default each TV show has **one home channel**, so you never see the same
show on two channels at once. For every channel that could air a show,
CableBox scores how well it fits, and the best score wins:

| Strongest | | | | Weakest |
|---|---|---|---|---|
| Your own pick (100) | Folder (90), tag (80), playlist (75) | Network it aired on (74), studio (70) | Its genre: main 50, 2nd 40, 3rd 30 | Decade (25), catch-all channels (5) |

The network counts through the built-in stations: a Nickelodeon show goes to
Chameleon, a tvN or iQiyi drama to Red Thread TV, and anything from Disney or
Pixar (shows and movies) to The Dexter Channel, which stands in for the Disney
Channel. Red Thread TV also takes a
show whose original title (in Kodi's show information) is in Korean, or in
Chinese characters, so a K-drama Netflix made lands there too; cartoons,
documentaries and variety shows never do.

Then every channel is topped up to at least five shows, borrowing shows that
fit it from bigger channels, but never a show that is on the channel of its
main genre or its network: *Star Trek* stays on Orbit TV even when an action
channel is short. Your own picks and hidden shows always win.

The automatic sort only changes when you run *Build my lineup* again; your
current channels keep their shows until then.

*Settings → Channels → Shows on more than one channel* changes the rule:
TV shows on one channel each (movies can repeat — the default), everything on
one channel each, or allow repeats anywhere.

### Find the shows that need you — the Finder

*Channel manager → Lineup tools → **Shows without a good channel***.

It lists:

- **Not on any channel** — no channel's programming picks the show up at all.
  The reason says why: *No channel's programming includes it*, *Hidden on
  Comedy Corner*, or *only in Keystone's time blocks*.
- **Weak matches** — the show has a home, but only just: a minor genre, a
  decade or catch-all channel, the automatic list of shows whose genres were too
  small for a channel, or a show *moved here so a small channel has enough
  shows* (the reason names its best fit).

Each row reads `Title → Channel (strength)` with the reason underneath, e.g.

```
Cosmos  ->  Retro TV (very weak)
   Shows from the 1990s  ->  Retro TV
Frasier  ->  Drama Net (weak)
   Drama (2nd genre)  ->  Drama Net
Bonanza  ->  not on any channel
   Hidden on Tumbleweed TV
```

Your own picks are never listed — the Finder only shows CableBox's guesses.

**Select a show** for what to do:

| Choice | What happens |
|---|---|
| **Put it on a channel…** | Channels listed best fit first, each with its reason. It becomes your pick: airs there from now on |
| **It's fine on <channel>** | Moves it to *Marked as fine* so it stops showing up |
| **Don't air it on <channel>** | Hidden on that channel; it finds another home |
| **Don't air it on any channel automatically** | Hidden everywhere. Pinned planner slots still air it; *What's on this channel* brings it back |

The top row switches the view: *Needs a look*, *Not on any channel*, *Weak
matches*, *Marked as fine*.

> **Tip:** most "not on any channel" shows have a missing or unusual genre.
> Fix the genre in Kodi (*Information → Refresh*, or the show's `.nfo`), or just
> put the show on a channel here.

### Move a show by hand

*Channel manager → Lineup tools → Move shows between channels*: pick a show, tick every
channel it should air on. It airs **exactly** there. Unticking hides it even
where its genre would include it.

Your choice always beats the automatic sort. Fantasy shares Orbit TV with
science fiction, for example; if you'd rather have *The Storyteller* on your
family channel, tick that channel and untick Orbit TV.

### See everything one channel airs

*Channel manager → channel → What's on this channel*: a checklist of every show.
Untick what doesn't belong. (A note tells you how many more shows from its
sources air on their own home channels instead.)

---

## 10. Pin shows to fixed times with the weekly planner

Main menu → **Weekly planner** → pick a channel (or *channel editor → Weekly
planner*).

Days run across, half-hours run down. Pinned shows are coloured, time blocks
light blue, off-air hours grey; everything else is filled automatically.

**Pin Seinfeld every Friday at 8 PM, in order:**

1. Move to *Fri 8:00 PM* → **OK** → *Pin a show here*.
2. **What:** *TV shows from my library* → *Seinfeld*.
3. **How long:** *Match the show* (rounds up to the channel's slot).
4. **Which days:** *This day only*.
5. **Order:** *In order* — next Friday continues with the next episode.

| Button | Action |
|---|---|
| Arrows | Move around |
| **Right** past Sunday, **Left** past Monday | Next week, the week before |
| Page Up / Down, CH+ / CH− | Jump 7 hours |
| **OK** on a pin | Change show, time, length, days or order; rename; start the series over; remove |
| **Menu** | Copy a day to other days, clear a day, off-air screen and clips, preview |
| Back | Done (saved as you go). Back in the middle of pinning a show pins nothing |

Pinned slots always start on time — the automatic programming works around
them. A pinned show can still turn up at other times; to keep it to its slot,
untick it in *What's on this channel*.

**Stepping through the weeks.** The planner opens on *This week*. Keep pressing
**Right** past Sunday to go week by week (*Week of 23 Nov*, *Week of 30 Nov*…);
**Left** past Monday comes back. Your pins look the same in every week, because
they repeat. What changes is the [specials](#plan-a-turkey-day-marathon): in
Thanksgiving week the Thursday heading shows ★ and the special's name, and its
hours are a gold block. OK on the block → *Edit this special*. Weeks before
this one can be looked at but not changed.

---

## 11. Time blocks: Saturday morning cartoons, movie nights

A time block gives part of the week its own programming.

1. *Channel editor → Time blocks → + Add*
2. Name (*Saturday Morning Cartoons*), days (*Sat*), start/end (*07:00–12:00*)
3. Its programming (e.g. *A TV genre → Animation*)

During the block the channel airs only the block's programming. The broadcast
networks (3–5) come with a full network day of blocks already.

---

## 12. Sign-off hours and prime time for every channel at once

*Channel manager → Lineup tools → Sign-off and prime time for all channels*:

- **Sign off overnight on all channels** — choose the hours (default 12 AM–5 AM).
  If some channels already sign off at times of their own, it asks first:
  *Replace theirs*, *Only the others* or *Cancel*.
  Off-air shows a 1950s *Please Stand By* card or colour bars (silent or with
  tone), after a built-in "This concludes our broadcast day" card; the
  planner's Menu changes the screen and sets a sign-off clip of your own
  (anthem) instead of the card, or none, and a sign-on clip.
- **Never sign off** — removes off-air hours everywhere (asks first).
- **Build prime-time lineups** — fills 8–11 PM (or your hours) with fixed weekly
  slots of each channel's best-rated shows; movie channels get a *Movie at 8*.
  These appear in the planner as *(automatic prime time)*; edit one and it
  becomes yours.
- **Remove the automatic prime-time lineups** — your own pins stay.

---

# Extras

## 13. Closed captions

Captions work like a TV's CC setting: **on means on for every programme**.
They start off.

### Switch them on or off

- **Main menu → Closed captions: On / Off**, or
- **While watching: Menu → Closed captions**

Commercials and bumps never show captions; programmes pick them back up after
the break and after channel changes.

### Choose the track, load a file, search online

While a programme is on: **Menu → Caption options…**

- Choose a subtitle track (language, forced, SDH…)
- Load a subtitle file from disk
- Search online (needs a Kodi subtitle add-on, e.g. OpenSubtitles) — live TV
  doesn't pause while you search

### Use the remote's CC / subtitle button

Kodi only sends that button to its own player, so it needs a one-time setup:

1. *Settings → On screen → **Remote CC button***
2. *Yes* — CableBox adds a small keymap. Now the button switches captions in
   CableBox (and still toggles subtitles of normal videos elsewhere in Kodi).

Run the same tool again to remove it.

### Which subtitles get used

- **Subtitle files next to the video** (`Show S01E01.en.srt`) are preferred over
  the file's own tracks. `.forced.` files are treated as forced, as in Kodi.
- Until you pick a language, CableBox uses Kodi's *Preferred subtitle language*.
- **Captions off means no subtitles at all** — forced subtitles and subtitle
  files next to the video too, even when Kodi remembers subtitles as on for
  that file. Switch captions on to see them.
- **Broadcast (CEA-608) captions** are picked up when they appear a few seconds in.
- The banner shows **CC** when a programme has real captions.

### TV boxes (CoreELEC, Android, Raspberry Pi)

Many boxes only draw subtitles in Kodi's full-screen player. With *Settings →
Advanced → Captions: use Kodi's full-screen player* on (the default), programmes
play full screen with CableBox's banner, logo and channel number on top. On
CoreELEC, *Captions: rewind 1 second (embedded subtitles)* (*Automatic*, same
page) works around a Kodi 21 quirk.

---

## 14. Commercials and bumps that fill the breaks properly

1. *Settings → Breaks → Commercials folder* (shared by every channel), and
   optionally *Bumps folder*.
2. Per-channel clips go in station folders ([section 7](#7-give-each-channel-its-own-logo-bumps-ids-and-commercials)).
3. *Commercial breaks per half hour*: 0–4 (default 2).
4. Run *Settings → Tools → **Check my videos*** — for every folder: how many
   clips are usable, total minutes, shortest and longest, and which can't be
   used and why (length unreadable, longer than 10 minutes, AV1 on a box that
   can't decode it). It also lists programmes that wouldn't play.

**Getting breaks to fit:** a few dozen clips of mixed lengths (15, 30, 60
seconds) fill breaks almost exactly. Without commercials, breaks show an *Up
next* card. Station IDs play between programmes, right before the next show.

**Clips that won't read** can usually be fixed by remuxing to `.mp4` or `.mkv`
(no re-encode needed).

### Promos for what's coming up

No commercials, or want more variety? Promos are made from your own library, and
they are on from the start.

1. *Settings → Breaks → **Promos for what's coming up, in breaks*** (On; Off switches them off).
2. *How often*: every break, about half of them, or now and then.
3. *Promote*: *Up next and later today* (like a real station: breaks during a
   show tease the evening, the last one says what's up next), only what's on
   next, or only something later today.
   *Look of promos and retro ads* (under *House breaks and retro ads*): early-90s cable (bright bands, chunky italic letters, a bouncing
   time tab) or Modern (the sleek card).
4. Watch a channel. During a break you'll see the channel's name, the show's
   picture and logo, the episode, *Up next* (or when it's on, e.g. *Tonight at
   8:00*), and hear its theme.

For the best-looking promos, keep the usual artwork in each show's folder:
`fanart.jpg`, `clearlogo.png`, `theme.mp3`, and an episode `-thumb.jpg` and
`.nfo` next to each episode (most media managers save these). A show without
them still gets a clean promo: its title in CableBox's type over the station
background, with a short built-in tune.

**Real promos from the era:** put them in the show's `Extras` folder with *Promo* or
*Trailer* in the name (2 minutes at most); *Also use short promo clips from a show's
Extras folder* (on unless you switch it off) airs them now and then. Or put your own promo clips in a
channel's station folder under `promos/`; those always come first.

A change applies from each channel's next programme when you close Settings;
the programme on air keeps its breaks (a promo in them that would now be wrong is
changed to what really follows). With promos off, breaks are exactly as they were
before.

**Check a promo without waiting for a break:** *Settings → Breaks →
Preview a promo...*, pick the channel, then **Up next** (its next programme) or
**Later today** (pick from its programmes in the next 6 hours). The screen goes
black for about 2 seconds, the promo plays exactly as it airs in a break, with
its music, then 1 second of black and Settings come back — handy after adding a
`clearlogo.png` or `theme.mp3`, and clean to record. Back ends it. Previews
change nothing: no schedule, break or series moves, and they don't count
towards *How often*.

**Developer tools: a promo right now while watching.** In *Settings →
Advanced*, turn on *Developer tools* (off by default). Then, while watching a
channel, press **0 0 0** on the remote (within 2 seconds, as for a channel
number). The promo that channel's next break would air plays at once, then the
channel comes back at the live point, as after a break. Promos must be on
(*Settings → Breaks*); nothing in the schedule changes. 0 0 0 can't clash
with a channel: channel numbers start at 1, and 007 still tunes channel 7. With
Developer tools off, 0 0 0 says *Channel 0 not available*, as always.

---


### Retro ads: made-up commercials when you have none

With no commercials folder, house breaks also run made-up retro commercials:
pitch cards with a jingle, local businesses, public service announcements and
*Now on videocassette* cards for movies in your library. Nothing to set up.

- **Turn them off:** *Settings → Breaks → House breaks → Retro ads*. Breaks
  go back to promos, guide and weather ads and station IDs.
- **A kids' channel that gets grown-up ads:** *Channel manager → the channel →
  Ad flavour → Kids*. It then gets only toys, cereal and kid-safe announcements.
  *Auto* already does this for channels of children's genres.
- **More "now on video" on a movie channel:** *Ad flavour → Movies* (Auto does
  it for movie channels): up to 1 in 3 of its retro ads (General channels 1 in 6,
  the others 1 in 4), never more than one a break or in two breaks in a row.
- **Squeezed credits** need nothing: episodes whose chapters mark the end credits
  shrink into a window at the credits while *Up next* shows what's coming. To see
  which episodes do, *Tools → Check chapters* lists "credits at ..." for them.
- **Breaks in the middle of a scene:** with *Commercial breaks at chapter marks*
  on (the default), episodes with act-break chapters (most disc rips in MKV) get
  their breaks on the act breaks. *Tools → Check chapters* shows which episodes
  have them; a show can be set to *Always* or *Never* use chapters there. A
  new library takes a while to read in the background; *Read now* there does
  it all at once.
- **An odd short file airs as an episode** (an intro or trailer in a show's
  folder): *Settings → Channels → Skip episodes shorter than* (5 min by
  default) passes over it; *Tools → Check skipped episodes* lists what's skipped.
- **The Up next card** shows the next programme's picture, title, episode, synopsis
  and a live countdown; preview it with `RunScript(script.cablebox42,preview_ad,upnext:4)`
  (channel 4's next programme; `upnext:4:2` the one after).
- **The station ID card** at the end of a break uses the channel's logo (the same
  one as the corner bug) and the built-in station's tagline. No logo: the name
  takes the logo's place. Long names shrink, then wrap; they are never cut off.
- **How many:** two retro ads a break (four on movie channels), three at most in
  the run of breaks at the end of a show (four on movie channels). Promos and system ads fill the rest.
- Changes apply from each channel's next programme once you close the menu.
- **See one card now** (from a keymap or a favourite, with the TV off):
  `RunScript(script.cablebox42,preview_ad,P01)`; ids are in
  `resources/ads/ads.json`, or `video` for a videocassette card;
  `preview_ad,station:4` shows channel 4's station ID card for 20 seconds.

## 15. The guide channel and the weather channel

**TV Guide (channel 2):** listings for every channel crawl up the screen with
background music. Press **OK** on it to pick a channel. Title: *Settings → Guide &
Weather → Guide title*; music: *Guide channel music folder*; pace: *Guide
scroll speed*.

Your own "cable company" ads in the crawl: make a text file `guide.txt` in the
guide channel's station folder (e.g. `Stations/TV Guide/guide.txt`) with one ad
per line, such as `Call 555-0123 for Pay-Per-View`. Lines starting with `#` are
skipped.

**Weather channel (25):**

1. *Settings → Guide & Weather → Your city or lat,lon* (e.g. `Springfield, IL` or
   `39.8,-89.6`). Leave it empty to use Kodi's weather location.
2. *Weather data from*: Automatic, Kodi's weather service only, or Open-Meteo only.
3. *Units*, *title* (*Your Local Forecast*) and *music* (smooth jazz!).

With a city (or Kodi's weather location) set and *Automatic* or *Open-Meteo*, the
channel adds **Latest Observations** (nearby cities) and a **Regional Map**. For
background music, point *Weather channel music folder* at a folder of smooth jazz;
CableBox doesn't ship any music.

### Boombox TV: a music video channel

Music videos around the clock, the way music channels did it: half-hour blocks,
commercials between the videos (never in the middle of one), and a caption in
the lower left shortly after each video starts and again before it ends:

> **a-ha**  
> "Take On Me"  
> *Hunting High and Low*  
> Warner Bros.  
> 1985

1. **Name your videos `Artist - Title`**, with a space on each side of the
   hyphen and the year if you like: `a-ha - Take On Me (1985).mkv`. Scraping them
   into Kodi is optional: CableBox airs the ones Kodi matched *and* every other
   video in the same folders.
2. Run **Build my lineup**. With 30 or more videos it offers **Boombox TV**
   (with none in Kodi's library it asks for the folder). Or add a channel of
   type *Music videos* yourself.
3. The first time, CableBox reads each video's length, frame rate and tags in
   the background. Channel → *Check music videos* shows how many air, what's
   skipped and why, and *Read them now* does it at once.

**What the caption shows:** artist, "title", album, record label, year — from
Kodi's library first, then the file's own tags (many downloaders write album
and label into the file), then the file name. Lines CableBox doesn't know are
simply left out: a well-named file without tags shows artist, title and year; a
file with an odd name shows just its name. Don't want it? Channel → *Video
captions: Off*.

**Smooth pictures:** each block plays videos of one frame rate (23.976, 29.97,
25…), so a TV that switches refresh rate does it between blocks, inside a
break, not between every video.

**Skipped:** trailers, samples, clips under 30 seconds and videos with no sound.
CableBox never renames, moves or tags your files and writes no NFOs.

### Music channels: songs around the clock

The other half of cable music: audio-only genre channels like DMX, with songs
playing all day, no breaks, and a mostly still screen saying what's on.

1. **Channel manager → + Add a channel → Music channel.**
2. Name it (*Hip-Hop & R&B*, *80s Hits*, *Quiet Storm*) and give it a number.
3. **Songs from:** *A genre*, *A decade*, *An artist*, *An album*, *A smart
   playlist* or *A music folder*. Pick one, then **Add more** for another or
   **Done**. Back at any step adds nothing.
4. Tune in. The channel joins a song in the middle, like any channel.

In the channel editor's **Programming**, **Check songs** says how many songs and hours it
has, which artists have the most songs, how many songs have no artist tag, and
their sample rates. **Songs from** adds or removes sources.

**Tagging tips.** The screen is built from your tags, so tag before you scrape:

- **Artist**, **Title**, **Album**, **Date/Year**, **Track number** and **Genre**
  fill the bottom of the screen and most of the info panel.
- **Label** (or *Publisher* / *Organization*) and **Composer** add a panel page
  each for songs in Kodi's music library.
- Embedded or folder cover art (`cover.jpg`, `folder.jpg`) shows next to the song.
- Kodi's music scrapers are optional: when the library has an artist's
  biography or an album review, its first sentence becomes a panel page, but
  a well-tagged song looks complete without it.
- Untagged files still air: `Artist - Title.flac` shows the artist and title
  from the file name.

Rescan your music library in Kodi after changing tags (or for a music folder,
just wait: CableBox re-reads a file when its date or size changes). CableBox
never writes tags, NFOs or artwork.

---

## 16. Holidays

Main menu → *Holidays & events* (the calendar, specials and each season's page; *Settings →
Holidays & events* holds the on/off options). Halloween (October, all-out on the 31st), Thanksgiving (on
the day) and Christmas (from the day after Thanksgiving, all-out on the 24th
and 25th): each channel mixes in its own holiday episodes and movies — a few at
first, more as the day gets closer.

CableBox finds holiday content by **Kodi tags** first (any tag containing
*halloween*, *christmas*…), then **genres** (Horror for Halloween), then **titles**
(clearly Halloween ones such as *Treehouse of Horror*, *Dracula*, *haunted*). The surest way:
tag your holiday episodes in Kodi (*Information → Manage → Manage tags*).

Each holiday can have its own commercials and bumps folders. *Save holiday
episodes and movies for their season* keeps Christmas specials out of July.

**Change a season:** main menu → *Holidays & events → **Holiday seasons (automatic)***,
pick the season. For Canadian Thanksgiving: *Thanksgiving → When → Canada (2nd
Monday of October)*. For a longer Halloween: *Halloween → When → Run-up → Starts on a date... →
A date... → September → 15*. *Tags* and *Genres* tick from what's
in your library; *Show what matches* tells you what each channel will air. *Reset
to the built-in settings* undoes it all.

### Add Festivus

1. Main menu → *Holidays & events → Holiday seasons (automatic) → **+ Add a season...***
   → *Festivus* (23 December).
2. *How many big days?* → *1 day*. *Run-up* → *Starts some days before the big
   days...* → **2**.
3. *Name of the season*: keep *Festivus* → **Add season**. Its page opens.
4. *Tags*: tick the tag you gave your Festivus episodes in Kodi (or leave the
   title word *festivus* to find *The Strike*). *Show what matches* lists what
   each channel has.

On 21 and 22 December a share of each channel's Festivus shows airs (inside
Christmas's run-up), all day on the 23rd where a channel has any; nothing is
hidden the rest of the year unless you switch on *Save its shows for its season*.
For Diwali or Lunar New Year use *My own date... → Dates for each year...* and
type the dates from your calendar.

### Plan a Festivus marathon

1. Right after *Add season*, CableBox asks *Plan something for Festivus too?* →
   **Plan a special** (or later: main menu → *Holidays & events → Add a special →
   A holiday from my list... → Festivus*).
2. *How often?* → *Every year*. Pick the channel and the hours.
3. *What to air?* → *Festivus episodes of this channel's shows*: the channel's
   own episodes with Festivus's tags or title words, each once. Or *Choose
   programming...* for a whole show (all of Seinfeld).
4. **Add special.** On the 23rd that channel airs the marathon; the other
   channels keep the Festivus season.

### Plan a Turkey Day marathon

The seasons choose holiday programmes for you. When you want one exact thing
on one day, add a **special**.

1. Main menu → *Holidays & events → Calendar*. A month calendar opens; the holiday seasons
   are shaded (big days red, run-ups plum).
2. Press **CH+** until it shows November, move to the fourth Thursday and
   press **OK** → *Add a special on this day*.
3. Choose *On the 4th Thursday of November every year*, so it moves with
   Thanksgiving. (*On 26 November every year* would stay on that date.)
4. **Name:** type *Turkey Day Marathon* (or keep *Thanksgiving*).
5. **Which channel?** → your comedy channel.
6. **Which hours?** → *All day*.
7. **What to air?** → *Choose programming…* → *TV shows from my library* →
   the show.
8. **Episode order** → *Continue where last year's marathon stopped*.
9. Check the summary → **Add special**.

The day now shows ★ *Turkey Day Marathon* on the calendar. Prefer a list?
**Menu** → *Show as a list*; its **Add a special** asks for the date in words
(*When?*) instead.

That's it. On the fourth Thursday of November the channel airs the show all
day, in order; next year it carries on from where this year's marathon
stopped. The show's ordinary run on the channel doesn't move in the meantime.
In the days before, breaks promote it (*Thursday, all day*).

- **See it before the day:** the special's page → *Preview the day*. Or open
  the channel's weekly planner and press **Right** past Sunday until you reach
  Thanksgiving week.
- **More channels:** the special's page → *Add another channel*. Each channel
  has its own hours and programming, so Christmas Day can be holiday episodes
  on one channel and a movie at 8 PM on another.
- **Only the holiday episodes:** for Halloween, Thanksgiving and Christmas,
  **What to air?** also offers *… episodes of this channel's shows*. Each airs
  once on the day; if they don't fill the hours, saving tells you how much
  they cover, and the rest of the day is the channel's normal programming.
- **Part of a day:** **Which hours?** → *Choose hours…*. An end earlier than
  the start means the next morning: New Year's Eve from 6:00 PM to 6:00 AM
  runs through midnight, and through the channel's sign-off hours.
- **Change or remove it:** pick it in the list. Changes are saved as you go.

**Dates for other countries.** Nothing is tied to the US calendar. Pick the
day on the calendar and choose its rule, or use *Add a special* in the list:

| You want | Choose |
|---|---|
| Canadian Thanksgiving | *A weekday of a month…* → *2nd* → *Monday* → *October* |
| Boxing Day | *A date…* → *December* → *26* |
| Good Friday, Easter Monday | *Easter…* |
| Whit Monday, Ascension Day, Carnival | *Easter…* → *Days after Easter…* (50, 39) or *Days before Easter…* (47 for Shrove Tuesday) |
| UK late-summer bank holiday, US Memorial Day | *A weekday of a month…* → *Last* → *Monday* → *August* / *May* |
| Black Friday | *A ready-made holiday…* → *Thanksgiving (US)* → *The day after* |
| A birthday, an anniversary | *A date…* |

The rule is worked out again every year, so floating holidays land on the
right day by themselves.

**Summer reruns:** on for the broadcast networks unless you change it: *Settings → Holidays & events →
Summer reruns* → *Off*, *Broadcast networks* or *All channels*. From June to August each series reruns the
episodes of its current season it has already shown, marked *(R)* in the guide and
banner; in September it picks up with the next new episode. Your pinned slots are
never changed.

---

## 17. The look: static, CRT effect, turn-on and turn-off

*Settings → On screen*:

| Setting | Options |
|---|---|
| TV turn-on and turn-off effect (with sound) | The picture blooms on, and shrinks to a dot on the way off |
| Static between channels | On/off, with or without sound |
| Static plays as | **Automatic**; **Quick** (an interface sound over the picture); **Video clip** (most reliable sound — use it on Windows if the static is silent) |
| CRT effect | Off, Subtle (scanlines, dark corners), Full (curved glass, phosphor mask, rolling hum bar) |
| Show channel banner for | 3, 6 or 10 seconds |
| Show rating at start of programmes | The *TV-PG* box (and *CC*) top left for a show's first 15 seconds. It needs ratings in your library: Kodi's scrapers fill them in (*Information → MPAA*) |

> If your TV switches refresh rate for each video (*Kodi Settings → Player →
> Adjust display refresh rate*), keep static on **Automatic** or **Quick**: the
> video clip would blank the screen on every channel change.

---

## 18. Start CableBox from the home screen, a favourite or Kodi's start-up

- **Straight to TV:** *Settings → Start-up & library → Go straight to TV when opened*.
- **TV on when Kodi starts:** *Settings → Start-up & library → Turn the TV on when Kodi
  starts* — the box boots straight into live TV.
- **Start on a fixed channel:** *Start on channel* (0 = the last one watched).
- **Home-screen widget:** many skins can show add-on content on the home
  screen; point a widget at CableBox 42 and it lists your channels — pick one to
  tune straight in.
- **A channel as a favourite / keyboard shortcut:**
  `RunScript(script.cablebox42,watch,7)` starts the TV on channel 7.
- **Phone remotes** (Yatse, Kore): the arrow, number, OK, Menu and Back buttons
  all work; captions switched from the phone are respected.

---

# When something's off

## 19. Fix-it recipes

**A channel shows "No programming."**
Its sources found nothing. Check the show is in Kodi's library (*Videos → TV
shows*), then the channel's *Programming*. *Preview today's schedule* confirms
the fix.

**A show isn't on any channel / is on a weird channel.**
*Channel manager → Shows without a good channel* tells you why. Usually the
show's genre is missing or unusual — fix it in Kodi, or put the show on a
channel right there.

**My logo / bumps / commercials aren't showing.**
*Channel manager → channel*, then check, in order:
1. *Identity → Station folder: none yet* → the folder's name doesn't match the channel's
   name, call letters or number. Select *Use an existing folder…* or *Create or
   repair*.
2. *Breaks & clips → Bumps: off for this channel – 3 clips in its folder aren't
   used* → select the row to switch them on.
3. *Identity → Logo: … CableBox's built-in station logo* → nothing of yours was
   found: no image picked, no `logo.png` in the channel's folder (a different
   image name works, but `logo.png` is the sure thing), and no image named
   after the channel, its call letters or its number in the logo folder. A
   renamed channel needs the logo folder's file renamed too.
4. Clips listed but not playing → *Settings → Tools → Check my videos* (unreadable
   or too-long clips are skipped).
5. Just added clips? Breaks are planned hours ahead. Close the Channel manager or
   use *Settings → Tools → Refresh schedules*: the new clips are used from each
   channel's next programme.

**I renamed a channel and lost its logo and clips.**
*Identity → Station folder → Use an existing folder…* → pick the old folder; it's
renamed to match. *Channel manager → Lineup tools → Station folders* lists folders
no channel uses.

**Breaks show "Up next" cards instead of commercials.**
No commercials folder is set for that channel, its commercials are switched off,
or none of its clips can be read. *Breaks & clips* and *Check my videos*.

**No static sound when changing channel (or only the first time).**
*Settings → On screen → Static plays as → Video clip* (common on Windows).

**The sound sputters, freezes or stops after a few channel changes.**
Update to 1.1.1 or later, then restart Kodi (on CoreELEC: `systemctl restart kodi`).
Older versions switched Kodi's audio setup on every channel change, which some
HDMI boxes couldn't keep up with.

**The picture froze and there's no sound, also in Kodi's own player afterwards.**
Kodi's sound output got stuck after a DTS / DTS-HD programme: Kodi 21 can misread
the first DTS frame when a file is opened partway in, and from then on it can't
open the sound output until Kodi restarts (with passthrough on). From 1.2.0
CableBox opens DTS programmes at the start and jumps to the right place, which
avoids it. If it happens anyway, CableBox notices within a second: with the TV
on, it restarts Kodi (about 20 seconds) and comes back on the same channel; with
the TV off it asks *Restart Kodi* / *Not now*. By hand: restart Kodi (on CoreELEC:
`systemctl restart kodi`).

**Subtitles show although captions are off.**
Update to 1.2.0. Before it, two saves at the same moment (as when the TV comes
on) could empty CableBox's own settings file, and with it your captions choice,
the last channel and the backup of *Play GUI sounds*. Switch captions off once
more (*Menu → Closed captions*) and it stays off.

**I hear a click when I press a button while watching.**
That's Kodi's own button sound. While the TV is on, CableBox lets Kodi play
interface sounds (it needs them for the static and turn-off sounds), so Kodi's
clicks are heard too. To silence them: *Kodi Settings → Interface → Skin →
Navigation sounds → None* — but that also silences CableBox's static and
turn-off sounds; *Static mode → Video clip* keeps the static sound in that case.

**No sound when turning the TV off.**
Update to 1.1.0 or later. If it's still silent on a box that switches refresh
rate, try *Static between channels → Video clip*, which also makes the turn-off
a video with its own sound.

**Captions don't appear on my TV box.**
Make sure *Settings → Advanced → Captions: use Kodi's full-screen player* is on. On CoreELEC leave *rewind 1 second* on *Automatic*. Check the
programme actually has a subtitle track or a sidecar `.srt` (*Menu → Caption
options*).

**A video plays sound but no picture, or Kodi freezes on certain videos.**
Very likely AV1 on a box without AV1 hardware decoding. *Settings → Advanced
→ AV1 videos → Automatic* skips them; *Check my videos* lists them.

**"Technical difficulties, please stand by."**
A file wouldn't open (missing, damaged, or an offline share). CableBox fills
the time with another show from the same channel and keeps that file off the
air for 3 days; *Check my videos* lists such files and can put them back once
fixed. If you renamed or deleted files, run Kodi's *Clean library* (Settings →
Media → Library): until then the library lists the old names, and CableBox
skips them when planning.

**The guide says "Updating listings…"**
Normal right after installing or a big change — listings appear within a minute
or two.

**My pinned shows don't appear yet.**
Changes apply from each channel's next programme. *Preview today's schedule*, or
*Settings → Tools → Refresh schedules*.

**I want a show to start again from episode one.**
*Settings → Tools → Start series over…* → *One show* → pick it → *Start over*.
*One channel* does every show on a channel, *All shows* the whole lineup. Nothing
else ever moves a show back: changing settings or channels, moving a show to
another channel, or taking it off and adding it back later all keep its place.

**My "In progress" list filled up with half-watched episodes.**
From before the protection existed: *Settings → Start-up & library → Clean up
my 'In progress' list* — tick what you're really watching; the rest is cleared.

---

## 20. Start over, back up, or move to a new box

**Start over:** *Settings → Tools → Start over (factory reset)* deletes channels,
planner pins, schedules and show assignments (optionally all settings too) and
shows the welcome screen again. Your videos, clips and station folders are
never touched.

**Back up / move to a new box:** copy CableBox's data folder,
`userdata/addon_data/script.cablebox42/` (on LibreELEC/CoreELEC:
`/storage/.kodi/userdata/addon_data/script.cablebox42/`). The important file is
`channels.json` (your lineup and pins); `settings.xml` holds your settings.
Copy your **Stations** folder too. On the new box, install CableBox, copy the
folder back, and check the folder paths in Settings still point to the right
places.

**Hand-editing:** `channels.json` is plain JSON if you prefer a text editor —
make a copy first, and close CableBox while you edit.

---

## 21. Report a problem

1. *Kodi Settings → System → Logging → Enable debug logging*.
2. Reproduce the problem.
3. Upload the log and copy its link:
   - **CoreELEC / LibreELEC:** connect over SSH (e.g. PuTTY) and run `pastekodi`.
   - **Anything else:** install **Kodi Logfile Uploader** (*Add-ons → Install
     from repository → Kodi Add-on repository → Program add-ons*) and run it,
     or paste `kodi.log` at <https://paste.kodi.tv/>.
   - If Kodi restarted, use `kodi.old.log` — the log from before the restart.
4. Fill in the **[problem report form](https://github.com/SeadogMcGrog/script.cablebox42/discussions/new?category=bug-reports)**
   on GitHub Discussions (versions, device, what happened, the log link).
   For questions and chat, the
   [Kodi forum support thread](https://forum.kodi.tv/showthread.php?tid=389521)
   is the place.

CableBox's log lines are tagged `script.cablebox42`.

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
16. [Holidays](#16-holidays)
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
  content type to *TV shows* or *Movies*, and let Kodi scan.
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

- A folder of **old commercials** (15/30/60-second clips work best)
- A folder of **bumps** ("We'll be right back") and **station IDs**
- A folder of **background music** for the guide and weather channels
  (smooth jazz and elevator music are the classics)
- **Logos** for your channels — transparent PNGs look best

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

### Option A — "Set it all up for me" (recommended)

The lineup builder asks a few questions. Every answer can be changed later in
Settings, so don't overthink it.

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
4. **Your city** for the weather channel (e.g. `Springfield, IL`). Skip it if
   Kodi's own weather is already set up.
5. CableBox reads your library (about a minute) and proposes channels.
   **Untick any you don't want** and confirm.
6. **"Sign channels off overnight?"** — *Yes* gives you a *Please Stand By* card
   from 12 AM to 5 AM, like real TV. The guide and weather stay on.
7. **"Give channels a prime-time lineup?"** — *Yes* fills 8–11 PM with fixed
   weekly slots of each channel's best shows (movie channels: a movie at 8).
8. CableBox programmes every channel, then shows **What I set up** — every
   channel, where its shows come from, and its folders. Read it once; it's the
   map of your new lineup. (You can see it again any time: *Channel manager →
   Lineup summary*.)
9. **Start watching.**

### Option B — "I'll set it up myself"

You get just the **TV Guide on 2** and the **Weather Channel on 25**, and the
Channel manager opens so you can add channels by hand
([section 6](#6-add-edit-rename-and-renumber-channels)). You can still run the
builder later: *Settings → Tools → Build my lineup automatically* (it can
replace your lineup or add its channels after yours).

### What a typical automatic lineup looks like

| Channel | What it is |
|---|---|
| 2 | **TV Guide** — scrolling listings for every channel |
| 3, 4, 5 | **Keystone, Beacon, Horizon** — three broadcast networks with a network-style day (morning news, game shows, soaps, after-school cartoons, prime time, late night) |
| 6 and up | **Genre and station channels** — Comedy Corner, Animation Station, Chameleon (kids), Tumbleweed TV (westerns), Orbit TV (sci-fi)… |
| | **Movie channels** — Popcorn TV (every movie), Picture Show (classics), genre movie channels |
| | **Studio showcases** — e.g. a Disney channel, when you own enough |
| 25 | **Retrocast Weather** |
| 42 | **News 42**, if you have news shows |

Which channels you get depends on what's in your library: a genre needs about
five shows to get a channel of its own. Shows whose genres are too small for a
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
| **Menu / Context** | **Closed captions**, caption options, what's on now, last channel, **sleep timer**, *Don't air this show here*, turn off |
| **Subtitle / CC button** | Captions on or off (after a one-time setup — [section 13](#13-closed-captions)) |
| **Back / Stop** | Turn the TV off |
| **Volume / Mute** | Work as normal |
| Pause, seek, skip | Ignored — it's live TV |

> **The Menu button is where most things live.** The first time you switch the
> TV on, a tip in the corner reminds you: *"Press Menu for captions, sleep timer
> and more."*

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
also puts the TV in standby over HDMI-CEC (*Settings → Viewing*).

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
3. **Channel manager → Shows without a good channel** — the shows that *don't*
   have an obvious home ([section 9](#9-put-every-show-on-the-right-channel)).

---

## 6. Add, edit, rename and renumber channels

Main menu → **Channel manager**.

### Add a channel

1. **+ Add a channel**
2. **Type**:
   - *Network* — series with commercial breaks (most channels)
   - *Movie channel* — films, commercials between them
   - *Loop* — back to back, no clock (good for music videos or shorts)
   - *Guide channel* / *Weather channel*
3. **Name** and **number**.
4. **Add programming** — pick a source, then *Add more programming?* as many
   times as you like:

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

| Row | What it's for |
|---|---|
| Name / Number / Call letters | Identity. Renaming offers to rename its station folder too |
| Station | Give it a built-in station (name, call letters, logo, time blocks) or go back to its own |
| Branding by time of day | Another name and logo for part of the day ([section 8](#8-time-of-day-branding-cam-jr-in-the-morning)) |
| Station logo | Choose an image, use the logo folder, or no logo |
| **Branding & clips** | What the channel *really* uses for its logo, bumps, IDs and commercials ([section 7](#7-give-each-channel-its-own-logo-bumps-ids-and-commercials)) |
| Programming | Add or remove sources |
| Weekly planner | Pin shows to times ([section 10](#10-pin-shows-to-fixed-times-with-the-weekly-planner)) |
| Time blocks | Saturday mornings, movie nights ([section 11](#11-time-blocks-saturday-morning-cartoons-movie-nights)) |
| Off-air hours | When this channel signs off |
| **What's on this channel** | Checklist of every show it airs — untick to hide |
| Commercials / Bumps on/off | Per channel |
| Break into shows for commercials | Mid-show breaks (off for movie channels by default) |
| Lineup style | *Same show same time every day*, or *Shuffle* |
| Programs start on | :00 and :30, the hour, every 15 minutes, or no clock |
| Channel commercials / bumps folder, Station ID clips | Folders for this channel only (station folders are usually easier) |
| Preview today's schedule | The next 12 hours |
| Delete channel | Asks first |

Changes take effect immediately: the edited channel's schedule rebuilds from
now on, and episode progress is kept.

### Renumber

*Channel manager → Rearrange channel numbers*: pick a channel and type its new
number. If the number is taken you can **swap** the two or **slide** the
channels in between over by one. *Close the gaps* renumbers 2, 3, 4… in order.
Schedules belong to the channel, not the number, so nothing is rebuilt.

---

## 7. Give each channel its own logo, bumps, IDs and commercials

This is what makes channels feel like real stations. You do it with folders —
no menus needed once they're set up.

### Step 1 — Choose a stations folder (once)

*Settings → Viewing → Stations folder*. Pick (or create) a folder on your media
drive, e.g. `/storage/media/Stations/` or `D:\Stations\`. If you chose *A
folder for each channel* during setup, this is already done.

### Step 2 — Let CableBox make the folders

*Settings → Tools → **Station folders: create, repair and see what each channel
uses***. For every channel it makes whatever is missing and **never touches
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
  Chameleon/
    logo.png
    bumps/  ids/  commercials/
    CAM Jr./            a time block's own folder (section 8)
      logo.png  bumps/  ids/  commercials/
```

**When do new files show up?** A new or changed **logo** appears within a couple
of minutes. **Clips** go into the breaks CableBox plans from then on — it plans
each channel several hours ahead (*Settings → Programming → Schedule ahead*),
so breaks already planned keep their clips. To use new clips straight away:
*Settings → Tools → Rebuild schedules* (episode progress is kept).

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
| **Logo** | Time block's folder | Image you picked in the channel editor | Station folder's `logo.png` | Built-in station logo, then the logo folder |
| **Bumps / commercials** | Time block's folder | Channel's station folder | Channel's own folder (editor) | Shared folder in Settings |
| **Station IDs** | Time block's folder | Channel's station folder | Channel's *Station ID clips* folder | — |

An **empty** folder is skipped, so you can make the folders now and fill them
later.

> **Important:** a channel's *Commercials* and *Bumps* switches (in the channel
> editor) still apply. Clips in `Comedy Corner/commercials/` are ignored if
> Comedy Corner has commercials switched off. *Branding & clips* warns you about
> exactly this.

### Step 4 — Check it with Branding & clips

*Channel manager → a channel → **Branding & clips***. One screen shows what the
channel really uses, and where each thing comes from:

```
Logo: logo.png                     From the channel's station folder.
Station folder: Comedy Corner      Select to look inside.
Bumps: 2 clips from the station folder
Station IDs: none                  Add clips to the channel's ids folder.
Commercials: off for this channel  Select to switch them on.
CAM Jr. (06:00-12:00): ...         (one row per time block)
Create or repair this channel's folders
```

From here you can:

- **Change the logo** (select the logo row)
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

If you'd rather keep all logos in one place: *Settings → Viewing → Logo folder*,
and name each image after the channel's name, call letters or number
(`Comedy Corner.png`, `LOL.png`, `3.png`). Or pick an image directly in the
channel editor (*Station logo → Choose an image*). Kodi can't show SVG — convert
to PNG.

The corner logo ("bug") is set in *Settings → Viewing*: on or off, which corner,
and opacity (30–100%).

---

## 8. Time-of-day branding (CAM Jr. in the morning)

A channel can go by another name, call letters and logo for part of the day —
like a kids' channel that's *CAM Jr.* from 6 AM to noon and *Cam O Nite* after
8 PM. The banner, the corner logo and the guide switch over by themselves.

1. *Channel manager → channel → **Branding by time of day***
2. **+ Add a time block** → name (e.g. *CAM Jr.*), start, end. Blocks may cross
   midnight (20:00–06:00).
3. Optional: pick a block → *Choose logo…*
4. Optional: give the block its own clips — *Branding & clips → Create or repair
   this channel's folders* makes `Stations/<channel>/<block>/bumps/`, `ids/`
   and `commercials/`. Drop a `logo.png` in the block's folder too.

Built-in stations like Chameleon come with their blocks already set.

---

## 9. Put every show on the right channel

### How CableBox decides

By default each TV show has **one home channel**, so you never see the same
show on two channels at once. For every channel that could air a show,
CableBox scores how well it fits, and the best score wins:

| Strongest | | | | Weakest |
|---|---|---|---|---|
| Your own pick (100) | Folder (90), tag (80), playlist (75) | Network it aired on (74), studio (70) | Its genre: main 50, 2nd 40, 3rd 30 | Decade (25), catch-all channels (5) |

Then every channel is topped up to at least five shows, borrowing shows that
fit it from bigger channels. Your own picks and hidden shows always win.

*Settings → Programming → Shows on more than one channel* changes the rule:
TV shows on one channel each (movies can repeat — the default), everything on
one channel each, or allow repeats anywhere.

### Find the shows that need you — the Finder

*Channel manager → **Shows without a good channel*** (also on *Settings → Tools*).

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

*Settings → Tools → Move shows between channels*: pick a show, tick every
channel it should air on. It airs **exactly** there. Unticking hides it even
where its genre would include it.

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
| Page Up / Down, CH+ / CH− | Jump 7 hours |
| **OK** on a pin | Change show, time, length, days or order; rename; start the series over; remove |
| **Menu** | Copy a day to other days, clear a day, off-air screen and clips, preview |
| Back | Done (saved as you go) |

Pinned slots always start on time — the automatic programming works around
them. A pinned show can still turn up at other times; to keep it to its slot,
untick it in *What's on this channel*.

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

*Settings → Tools → Quick setup*:

- **Sign off overnight on all channels** — choose the hours (default 12 AM–5 AM).
  Off-air shows a 1950s *Please Stand By* card or colour bars; the planner's
  Menu sets an optional sign-off clip (anthem) and sign-on clip.
- **Never sign off** — removes off-air hours everywhere.
- **Build prime-time lineups** — fills 8–11 PM (or your hours) with fixed weekly
  slots of each channel's best-rated shows; movie channels get a *Movie at 8*.
  These appear in the planner as *(automatic prime time)*; edit one and it
  becomes yours.
- **Remove the automatic prime-time lineups** — your own pins stay.

---

# Extras

## 13. Closed captions

Captions work like a TV's CC setting: **on means on for every programme**.

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

1. *Settings → Tools → **Remote CC button***
2. *Yes* — CableBox adds a small keymap. Now the button switches captions in
   CableBox (and still toggles subtitles of normal videos elsewhere in Kodi).

Run the same tool again to remove it.

### Which subtitles get used

- **Subtitle files next to the video** (`Show S01E01.en.srt`) are preferred over
  the file's own tracks. `.forced.` files are treated as forced, as in Kodi.
- Until you pick a language, CableBox uses Kodi's *Preferred subtitle language*.
- **Forced subtitles** (foreign-language scenes in Blu-ray rips) stay on even
  with captions off — like subtitles burned into a broadcast.
- **Broadcast (CEA-608) captions** are picked up when they appear a few seconds in.
- The banner shows **CC** when a programme has real captions.

### TV boxes (CoreELEC, Android, Raspberry Pi)

Many boxes only draw subtitles in Kodi's full-screen player. With *Settings →
Viewing → Captions: show programmes in Kodi's full-screen player* on (the
default), programmes play full screen with CableBox's banner, logo and channel
number on top. On CoreELEC, *Captions: rewind 1 second so embedded subtitles
appear* (*Automatic*) works around a Kodi 21 quirk.

---

## 14. Commercials and bumps that fill the breaks properly

1. *Settings → Programming → Commercials folder* (shared by every channel), and
   optionally *Bumps / station ID folder*.
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

---

## 15. The guide channel and the weather channel

**TV Guide (channel 2):** scrolling listings for every channel with background
music. Press **OK** on it to pick a channel. Title: *Settings → Programming →
Guide title*; music: *Guide channel music folder*.

**Weather channel (25):**

1. *Settings → Weather → Your city or lat,lon* (e.g. `Springfield, IL` or
   `39.8,-89.6`). Leave it empty to use Kodi's weather location.
2. *Weather data from*: Automatic, Kodi's weather service only, or Open-Meteo only.
3. *Units*, *title* (*Your Local Forecast*) and *music* (smooth jazz!).

---

## 16. Holidays

*Settings → Seasons*. Halloween (October, all-out on the 31st), Thanksgiving (on
the day) and Christmas (from the day after Thanksgiving, all-out on the 24th
and 25th): each channel mixes in its own holiday episodes and movies — a few at
first, more as the day gets closer.

CableBox finds holiday content by **Kodi tags** first (any tag containing
*halloween*, *christmas*…), then **genres**, then **titles**. The surest way:
tag your holiday episodes in Kodi (*Information → Manage → Manage tags*).

Each holiday can have its own commercials and bumps folders. *Save holiday
episodes and movies for their season* keeps Christmas specials out of July.

---

## 17. The look: static, CRT effect, turn-on and turn-off

*Settings → Viewing*:

| Setting | Options |
|---|---|
| TV turn-on and turn-off effect (with sound) | The picture blooms on, and shrinks to a dot on the way off |
| Static between channels | On/off, with or without sound |
| Static mode | **Automatic**; **Quick** (an interface sound over the picture); **Video clip** (most reliable sound — use it on Windows if the static is silent) |
| CRT effect | Off, Subtle (scanlines, dark corners), Full (curved glass, phosphor mask, rolling hum bar) |
| Show channel banner for | 3, 6 or 10 seconds |

> If your TV switches refresh rate for each video (*Kodi Settings → Player →
> Adjust display refresh rate*), keep static on **Automatic** or **Quick**: the
> video clip would blank the screen on every channel change.

---

## 18. Start CableBox from the home screen, a favourite or Kodi's start-up

- **Straight to TV:** *Settings → Viewing → Go straight to TV when opened*.
- **TV on when Kodi starts:** *Settings → Viewing → Turn the TV on when Kodi
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
*Channel manager → channel → Branding & clips*, then check, in order:
1. *Station folder: none yet* → the folder's name doesn't match the channel's
   name, call letters or number. Select *Use an existing folder…* or *Create or
   repair*.
2. *Bumps: off for this channel – 3 clips in its folder aren't used* → select
   the row to switch them on.
3. *Logo: … (built-in station logo)* → there's no `logo.png` in the folder; a
   different image name works, but `logo.png` is the sure thing.
4. Clips listed but not playing → *Settings → Tools → Check my videos* (unreadable
   or too-long clips are skipped).
5. Just added clips? Breaks are planned hours ahead, so already-planned breaks
   keep their old clips. *Settings → Tools → Rebuild schedules* uses the new ones
   straight away.

**I renamed a channel and lost its logo and clips.**
*Branding & clips → Use an existing folder…* → pick the old folder; it's renamed
to match. *Settings → Tools → Station folders* lists folders no channel uses.

**Breaks show "Up next" cards instead of commercials.**
No commercials folder is set for that channel, its commercials are switched off,
or none of its clips can be read. *Branding & clips* and *Check my videos*.

**No static sound when changing channel (or only the first time).**
*Settings → Viewing → Static between channels → Video clip* (common on Windows).

**The sound sputters, freezes or stops after a few channel changes.**
Update to 1.1.1 or later, then restart Kodi (on CoreELEC: `systemctl restart kodi`).
Older versions switched Kodi's audio setup on every channel change, which some
HDMI boxes couldn't keep up with.

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
Make sure *Settings → Viewing → Captions: show programmes in Kodi's full-screen
player* is on. On CoreELEC leave *rewind 1 second* on *Automatic*. Check the
programme actually has a subtitle track or a sidecar `.srt` (*Menu → Caption
options*).

**A video plays sound but no picture, or Kodi freezes on certain videos.**
Very likely AV1 on a box without AV1 hardware decoding. *Settings → Programming
→ AV1 videos → Automatic* skips them; *Check my videos* lists them.

**"Technical difficulties, please stand by."**
A file wouldn't open (missing, damaged, or an offline share). CableBox fills
the time with another show and keeps that file off the air for 3 days; *Check
my videos* lists such files and can put them back once fixed.

**The guide says "Updating listings…"**
Normal right after installing or a big change — listings appear within a minute
or two.

**My pinned shows don't appear yet.**
Changes apply from now on. *Preview today's schedule*, or *Settings → Tools →
Rebuild schedules*.

**My "In progress" list filled up with half-watched episodes.**
From before the protection existed: *Settings → Tools → Clean up my 'In
progress' list* — tick what you're really watching; the rest is cleared.

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

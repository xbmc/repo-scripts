# Kofin Lyrics

Shows the lyrics stored on your Jellyfin server as a song plays, in time with
the music where the server has timings.

The lines come from [plugin.video.kofin][kofin], which fetches them on the
playback-start callback — before anything that searches for lyrics can get
there. This addon does not talk to Jellyfin and needs no login of its own.

[kofin]: https://github.com/kontell/plugin.video.kofin

## Where the lyrics get drawn

Two surfaces, never both at once:

- **A skin's own overlay**, if the skin declares one (see below). It draws in
  the window that is already active, so it takes no input and blocks nothing.
- **This addon's window**, on any other skin, the way CU LRC Lyrics works.

An addon window always becomes the *active* window, so it is only ever opened
over the visualisation screen, where there is nothing else to navigate. It is
also the only way to scroll lyrics by hand: Kodi's keymap binds the arrow keys
in the visualisation window to `StepBack`/`SkipNext`, so a list a skin draws
there never sees them, however it is focused. Pressing the skin's lyrics
button hands over to this addon's window for that, and closing it hands back.

## Supporting it in a skin

A skin that wants to draw the lyrics itself needs three things.

**1. Declare the list control** on the window that will show them, and clear it
again on unload — the addon only drives a control that is on screen:

```xml
<onload>SetProperty(kofin.lyric.control,9500,Home)</onload>
<onunload>ClearProperty(kofin.lyric.control,Home)</onunload>
```

**2. Fill a `fixedlist` from kofin's directory.** `<focusposition>` is what
holds the line being sung on one row while the song scrolls past it; the path
carries the song id, so it changes per song and Kodi re-reads it:

```xml
<control type="fixedlist" id="9500">
  <focusposition>6</focusposition>
  <scrolltime tween="sine" easing="out">350</scrolltime>
  <content>$INFO[Window(Home).Property(kofin.lyric.path)]</content>
  ...
</control>
```

**3. Gate visibility on `kofin.lyric.show`**, and hide while
`kofin.lyric.interactive` is set:

```xml
<visible>!String.IsEmpty(Window(Home).Property(kofin.lyric.show))
       + String.IsEmpty(Window(Home).Property(kofin.lyric.interactive))</visible>
```

Gate on `kofin.lyric.show`, **not** on kofin's `kofin.lyric.has`. `has` only
means kofin fetched some lyrics; `show` means this addon has decided they
belong on screen. The *Show lyrics automatically* and *Show lyrics that have
no timings* settings are both expressed by withholding `show`, so a skin
gating on anything else ignores them.

### Properties

| Property | Written by | Meaning |
|---|---|---|
| `kofin.lyric.show` | this addon | Lyrics belong on screen — the visibility gate |
| `kofin.lyric.interactive` | this addon | Our own window has taken over for scrolling; stand aside |
| `kofin.lyric.control` | the skin | Id of the list to drive |
| `kofin.lyric.path` | kofin | Directory the list is filled from; changes per song |
| `kofin.lyric.has` | kofin | Kofin has lyrics for this song (not a visibility gate) |

Only `skin.contuary` is known to implement this.

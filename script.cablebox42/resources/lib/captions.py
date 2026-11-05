"""Closed captions (subtitles) for the TV window.

Everything goes through Kodi's own player, so a caption change never stops or
restarts the programme:

  * Player.getAvailableSubtitleStreams() / getSubtitles() - what the file has
  * Player.setSubtitleStream() / showSubtitles() - choose a track, on or off
  * Player.setSubtitles(path) - add a subtitle file for this playback
  * JSON-RPC Player.GetProperties - only to *label* the tracks (name, forced,
    hard of hearing) and to see which one is on; the Python calls do the work

CableBox plays a programme in pieces (each segment between commercial breaks
is a new playback, and Kodi starts every playback with its own defaults), so
the viewer's choice is remembered - like the CC button on an old TV, it stays
on across programmes and channels - and applied again each time a programme
segment starts.  Commercials and bumps are left as Kodi plays them.

The choice (on/off and the language) is kept in state.json so it survives
turning the TV off and on.  Until the viewer touches captions, CableBox leaves
Kodi's own behaviour alone.

Kodi saves each file's subtitle on/off and track in its video database when
the file stops.  So that CableBox's choice doesn't follow the episode into the
viewer's normal library viewing, the state Kodi opened each segment with is
noted, and put back just before CableBox moves on (leave()).

The only Kodi setting ever changed is 'Pause when searching for subtitles',
switched off just while the online search is open (live TV doesn't pause) and
put back straight after - or at the next start if Kodi closed in between.
"""
import os
import time

import xbmc
import xbmcgui
import xbmcvfs

from . import kodiutil as K
from .kodiutil import _

SUB_FILES = ".srt|.ass|.ssa|.sub|.idx|.sup|.smi|.vtt|.txt"

# Broadcast captions (CEA-608 inside the video) only show up as a track a few
# seconds into playback: look again this many seconds after each try.
RETRY_GAPS = (3, 5, 7)

NUDGE_AUTO, NUDGE_ALWAYS, NUDGE_NEVER = 0, 1, 2


def _is_coreelec():
    try:
        with open("/etc/os-release", "r") as f:
            return "coreelec" in f.read().lower()
    except Exception:
        return False


def nudge_enabled():
    """CoreELEC (Kodi 21) doesn't show subtitles embedded in a file when playback
    starts partway in - which every CableBox segment does - until it's rewound
    (discourse.coreelec.org, '21.2 no SRT subtitles').  Automatic: CoreELEC only."""
    mode = K.setting_int("cc_nudge", NUDGE_AUTO)
    if mode == NUDGE_NEVER:
        return False
    return mode == NUDGE_ALWAYS or _is_coreelec()


PAUSE_SETTING = "subtitles.pauseonsearch"
PAUSE_ORIG = "cc_pause_orig"           # state.json key while the search is open

KEYMAP = "special://profile/keymaps/cablebox42-captions.xml"
KEYMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Written by CableBox 42 (Settings > Tools > Remote CC button).
     Lets the remote's subtitle button reach CableBox: Kodi normally maps it
     in its own full-screen player only.  Delete this file to undo. -->
<keymap>
  <global>
    <remote>
      <subtitle>ShowSubtitles</subtitle>
    </remote>
  </global>
</keymap>
"""


def _lang_key(code):
    """'eng', 'en', 'English' -> 'eng' (so tracks named differently still match)."""
    code = (code or "").strip()
    if not code:
        return ""
    try:
        k = xbmc.convertLanguage(code, xbmc.ISO_639_2)
        if k:
            return k.lower()
    except Exception:
        pass
    return code.lower()


def _ascii(x):
    """Safe for the log whatever the track names contain."""
    return ascii(x)[:600]


def _external_marker():
    """How Kodi tags a subtitle file found next to the video: '(External)',
    in the viewer's Kodi language (string 21602)."""
    try:
        m = xbmc.getLocalizedString(21602)
        if m:
            return m.strip().lower()
    except Exception:
        pass
    return "(external)"


def _lang_name(code):
    try:
        n = xbmc.convertLanguage(code, xbmc.ENGLISH_NAME)
        if n:
            return n
    except Exception:
        pass
    return code or _("Unknown language")


# ------------------------------------------------------------------ Kodi setting swap
def _get_setting(sid):
    try:
        return K.rpc("Settings.GetSettingValue", {"setting": sid}).get("value")
    except Exception:
        return None


def _set_setting(sid, value):
    try:
        K.rpc("Settings.SetSettingValue", {"setting": sid, "value": value})
    except Exception as exc:
        K.log_err("captions setting %s: %s" % (sid, exc))


def restore_leftovers():
    """Kodi closed while the subtitle search was open: put its setting back.
    Called when the TV starts and by the service when Kodi starts."""
    st = K.load_json(K.STATE_FILE, {})
    if PAUSE_ORIG not in st:
        return
    _set_setting(PAUSE_SETTING, bool(st.pop(PAUSE_ORIG)))
    K.save_json(K.STATE_FILE, st)


class Captions(object):
    def __init__(self, player):
        self.player = player
        restore_leftovers()
        st = K.load_json(K.STATE_FILE, {})
        self.on = st.get("cc_on")            # None: never touched -> leave Kodi alone
        self.lang = st.get("cc_lang", "")
        self.files = {}                       # video path -> subtitle file loaded for it (this session)
        self.picks = {}                       # video path -> {"lang", "name"} of the track chosen for it
        self.pending = None                   # a programme segment just started: apply on the next tick
        self.cur = None                       # {"path", "base": (enabled, index), "touched"}
        self.resync = False                   # the programme got paused: put it back on the clock
        self.seen = None                      # (enabled, index) as CableBox last left it
        self.poll_at = 0
        self.note = ""                        # for a toast: captions switched from outside
        self.showing = False                  # any subtitle on screen (forced ones too): needs full screen
        self.nudge_on = nudge_enabled()
        self.nudge_at = 0                     # when to rewind 1 s so embedded subtitles appear
        self.nudge_path = ""
        self.applied = None                   # the track apply() just switched on
        self.muted = set()                    # programmes switched off from outside, captions still on
        self.cand = None                      # an outside change seen once (must hold to count)
        self.quiet_until = 0                  # Kodi settling after CableBox's own change: not the viewer
        self.has_cc = False                   # the programme on now has real captions (banner 'CC')

    # ----------------------------------------------------------- what the file has
    def _active_video_player(self):
        try:
            for p in K.rpc("Player.GetActivePlayers", {}) or []:
                if p.get("type") == "video":
                    return p.get("playerid")
        except Exception:
            pass
        return None

    def tracks(self):
        """[{index, label, lang, name, forced, impaired}], plus (current index or None, enabled)."""
        try:
            names = list(self.player.getAvailableSubtitleStreams() or [])
        except Exception:
            names = []
        info, current, enabled = {}, None, False
        pid = self._active_video_player()
        if pid is not None:
            try:
                r = K.rpc("Player.GetProperties", {"playerid": pid,
                                                   "properties": ["subtitles", "currentsubtitle", "subtitleenabled"]})
                for s in r.get("subtitles") or []:
                    info[int(s.get("index", -1))] = s
                cur = r.get("currentsubtitle") or {}
                current = cur.get("index") if cur else None
                enabled = bool(r.get("subtitleenabled"))
            except Exception:
                pass
        out = []
        marker = _external_marker()
        for i, code in enumerate(names):
            s = info.get(i, {})
            name = (s.get("name") or "").strip()
            # a subtitle file next to the video (a sidecar .srt): Kodi names it
            # '<tag> (External)', with no language unless the file name has one
            external = marker in (name or code or "").lower()
            lang = s.get("language") or ("" if external else code)
            if external:
                tag = (name or code or "")
                tag = tag[:tag.lower().find(marker)].strip(" .-_") if marker in tag.lower() else tag
                label = (_lang_name(lang) + "  " if lang else "") + _("Subtitle file") + (": " + tag if tag else "")
                name_shown = True
            else:
                label = _lang_name(lang)
                name_shown = False
            extra = [name] if name and not name_shown and name.lower() not in (
                label.lower(), "forced", "sdh", "cc", "hi", "hearing impaired") else []
            if s.get("isforced"):
                extra.append(_("forced"))
            if s.get("isimpaired"):
                extra.append(_("hard of hearing"))
            if extra:
                label += "  (%s)" % ", ".join(extra)
            out.append({"index": i, "label": label, "lang": _lang_key(lang), "name": (name or code or "").lower(),
                        "external": external, "default": bool(s.get("isdefault")),
                        "forced": bool(s.get("isforced")), "impaired": bool(s.get("isimpaired"))})
        if pid is None:                      # no JSON-RPC answer: fall back to the Python calls
            enabled = bool(self.on) and bool(out)
            try:
                cur_code = self.player.getSubtitles()
                current = next((t["index"] for t in out if t["lang"] == _lang_key(cur_code)), None)
            except Exception:
                pass
        return out, current, enabled

    def _playing(self):
        try:
            return self.player.getPlayingFile() if self.player.isPlayingVideo() else ""
        except Exception:
            return ""

    # ----------------------------------------------------------- segment start / end
    def started(self, path):
        """A programme segment is on screen (Kodi's player thread): the work is
        done on the TV loop's next tick, away from Kodi's callback."""
        self.pending = {"path": path, "due": time.time() + 0.3, "tries": 0}
        self.quiet_until = time.time() + 3.5

    def tick(self, now):
        if self.nudge_at and now >= self.nudge_at:
            self.nudge_at = 0
            self._nudge()
        p = self.pending
        if not p:
            self._watch(now)
            return
        if now < p["due"]:
            return
        if self._playing() != p["path"]:
            self.pending = None              # moved on before we got to it
            return
        if not self.cur or self.cur["path"] != p["path"]:
            _tracks, index, enabled = self.tracks()
            self.cur = {"path": p["path"], "base": (enabled, index), "touched": False}
        self.applied = None
        result = self.apply(p["path"])
        self._snap()
        if result not in ("", "none", "file"):
            self._schedule_nudge(self.applied, 0.2)
        if not p["tries"]:
            K.log("Captions at programme start: %s" % self.describe(p["path"], result), xbmc.LOGINFO)
        if result == "none" and self.on and p["tries"] < len(RETRY_GAPS):
            p["due"] = now + RETRY_GAPS[p["tries"]]    # broadcast captions may still turn up
            p["tries"] += 1
        else:
            self.pending = None
        self.poll_at = now + 1.5

    def describe(self, path="", result=""):
        """One line for the log: what Kodi offers and what CableBox did with it."""
        try:
            names = list(self.player.getAvailableSubtitleStreams() or [])
        except Exception as exc:
            names = ["<python error: %s>" % exc]
        tracks, index, enabled = self.tracks()
        return ("%s | Kodi lists %d subtitle track(s) %s, CableBox sees %d %s | current=%s showing=%s | "
                "CC choice=%s lang=%s | did: %s" % (
                    path, len(names), _ascii(names), len(tracks), _ascii([t["label"] for t in tracks]),
                    index, enabled, self.on, self.lang or "-", result or "nothing (never touched)"))

    def _snap(self):
        """Note the state CableBox has just left the captions in."""
        tracks, index, enabled = self.tracks()
        self.seen = (enabled, index)
        self.showing = bool(enabled and index is not None)
        self.has_cc = any(not t["forced"] for t in tracks)
        self.cand = None
        self.quiet_until = time.time() + 3.0     # Kodi may still be settling (late on CoreELEC)

    def _watch(self, now):
        """Captions switched outside CableBox - a phone remote like Yatse or Kore,
        Kodi's own menus, a keymap: take that as the viewer's choice, so it
        carries on after the breaks and the picture goes full screen for it."""
        if not self.cur or now < self.poll_at:
            return
        self.poll_at = now + 1.5
        if self._playing() != self.cur["path"]:
            return
        tracks, index, enabled = self.tracks()
        state = (enabled, index)
        self.showing = bool(enabled and index is not None)
        self.has_cc = any(not t["forced"] for t in tracks)
        if self.seen is None:
            self.seen = state
            return
        if state == self.seen:
            self.cand = None
            return
        if now < self.quiet_until:
            self.seen = state                 # Kodi settling after CableBox's change - not the viewer
            return
        if self.cand != state:
            self.cand = state                 # must still be so at the next look to count
            return
        self.cand = None
        self.seen = state
        path = self.cur["path"]
        t = next((x for x in tracks if x["index"] == index), None) if enabled else None
        was = self.on
        if t and enabled:
            self._schedule_nudge(t, 0.3)      # switched on from a phone: same CoreELEC fix
        if t and not t["forced"]:            # a forced track alone is what 'captions off' shows
            self.on = True
            self.lang = t["lang"] or self.lang
            self.picks[path] = {"lang": t["lang"], "name": t["name"]}
            self.muted.discard(path)
            note = _("Captions: %s") % t["label"]
        elif self.on:
            # captions are on, like a TV's CC setting: switched off from a phone or
            # Kodi's menu, they stay off for this programme only - CableBox's own
            # CC button and menu switch them off everywhere
            self.muted.add(path)
            self._touch()
            self.note = _("Captions off for this programme")
            K.log("captions switched off outside CableBox: this programme only", xbmc.LOGINFO)
            return
        else:
            self.on = False
            note = _("Captions off")
        self._remember()
        self._touch()
        K.log("captions changed outside CableBox: %s" % note)
        if was != self.on:
            self.note = note

    def take_note(self):
        n, self.note = self.note, ""
        return n

    def leave(self):
        """CableBox is about to stop this segment (break, channel change, TV off):
        put the subtitle state back to what Kodi opened it with, so the video
        database keeps the viewer's own setting for this file."""
        cur, self.cur = self.cur, None
        self.pending = None
        self.seen = None
        self.nudge_at = 0
        self.cand = None
        self.has_cc = False
        if not cur or not cur.get("touched") or self._playing() != cur["path"]:
            return
        enabled, index = cur["base"]
        try:
            if index is not None and index >= 0:
                self.player.setSubtitleStream(int(index))
            self.player.showSubtitles(bool(enabled))
        except Exception as exc:
            K.log_err("captions leave: %s" % exc)

    def _schedule_nudge(self, track, delay):
        """Rewind 1 s shortly, if an embedded track (not a subtitle file next to
        the video, which Kodi reads whole) has just been put on screen."""
        if not (self.nudge_on and track and self.cur) or track.get("external"):
            return
        if self.on is not True or self.cur["path"] in self.muted:
            return                            # only with captions switched on
        self.nudge_at = time.time() + delay
        self.nudge_path = self.cur["path"]

    def _nudge(self):
        if self._playing() != self.nudge_path:
            return
        try:
            t = self.player.getTime()
            self.player.seekTime(max(0.0, t - 1.0))
            K.log("Captions: rewound 1 s so Kodi shows the embedded subtitles (CoreELEC fix)", xbmc.LOGINFO)
        except Exception as exc:
            K.log_err("captions rewind: %s" % exc)

    def _touch(self):
        if self.cur:
            self.cur["touched"] = True

    # ----------------------------------------------------------- choices
    def _remember(self):
        st = K.load_json(K.STATE_FILE, {})
        st["cc_on"] = self.on
        st["cc_lang"] = self.lang
        K.save_json(K.STATE_FILE, st)

    def set_off(self):
        self.on = False
        self.muted.clear()
        self._remember()
        self._touch()
        self.applied = None
        try:
            self._show_off()
        except Exception:
            pass
        self._snap()
        self._schedule_nudge(self.applied, 0.3)     # a forced track kept on

    @staticmethod
    def _full_showing(tracks, index, enabled):
        """Real captions on screen - not just a 'forced' track."""
        t = next((x for x in tracks if x["index"] == index), None) if enabled else None
        return bool(t and not t["forced"])

    _kodi_lang = None

    def want_lang(self):
        """The caption language: the viewer's last choice in CableBox, else Kodi's
        own 'Preferred subtitle language' - which, like Kodi, means the interface
        language when it's set to Original or Default."""
        if self.lang:
            return self.lang
        if self._kodi_lang is None:
            v = str(_get_setting("locale.subtitlelanguage") or "").strip()
            if v.lower() in ("", "default", "original", "none", "forced_only"):
                try:
                    v = xbmc.getLanguage(xbmc.ISO_639_2)
                except Exception:
                    v = ""
            self._kodi_lang = _lang_key(v)
        return self._kodi_lang

    def _forced_for(self, tracks):
        """The forced track that stays on with captions off.  Blu-ray rips have
        one for foreign-language scenes (the German dialogue in a war film, say):
        part of the programme, like subtitles burned into a broadcast."""
        forced = [t for t in tracks if t["forced"]]
        want = self.want_lang()
        same = [t for t in forced if want and t["lang"] == want]
        return (same or forced or [None])[0]

    def _show_off(self):
        """Captions off: only a forced track, if the file has one, stays on."""
        tracks, _i, _e = self.tracks()
        f = self._forced_for(tracks)
        if f:
            self.player.setSubtitleStream(f["index"])
            self.player.showSubtitles(True)
            self.applied = f
        else:
            self.player.showSubtitles(False)

    def set_track(self, t):
        if self.cur:
            self.muted.discard(self.cur["path"])
        self.on = True
        self.lang = t["lang"] or self.lang
        self._remember()
        self._touch()
        if self.cur:                          # this exact track again after the break
            self.picks[self.cur["path"]] = {"lang": t["lang"], "name": t["name"]}
        try:
            self.player.setSubtitleStream(t["index"])
            self.player.showSubtitles(True)
        except Exception as exc:
            K.log_err("captions: %s" % exc)
        self._snap()
        self._schedule_nudge(t, 0.3)

    def load_file(self, video_path, sub_path):
        """A subtitle file for the programme on now - added to this playback only."""
        try:
            self.player.setSubtitles(sub_path)
            self.player.showSubtitles(True)
        except Exception as exc:
            K.log_err("captions file: %s" % exc)
            return False
        self.files[video_path] = sub_path
        self.on = True
        self._remember()
        self._touch()
        self._snap()
        return True

    def _best(self, tracks, video_path=None):
        """The track to show: the one picked for this programme; then a subtitle
        file next to the video (someone put it there for a reason - often because
        the rip's own track is incomplete); then the viewer's language; full
        captions over 'forced' (which only covers foreign-language bits)."""
        if not tracks:
            return None
        pick = self.picks.get(video_path) if video_path else None
        if pick:
            t = next((t for t in tracks if t["lang"] == pick["lang"] and t["name"] == pick["name"]), None)
            if t:
                return t
        want = self.want_lang()

        def fits(t):
            # a sidecar file without a language tag counts as the viewer's language
            return not want or t["lang"] == want or (t["external"] and not t["lang"])
        # within each group, a track flagged default (a '.default.srt', say) comes first
        tracks = sorted(tracks, key=lambda t: not t.get("default"))
        full = [t for t in tracks if not t["forced"]]
        for pool in ([t for t in full if t["external"] and fits(t)],   # subtitle files the viewer added
                     [t for t in full if fits(t)],                       # the viewer's language
                     full,
                     tracks):                                            # only forced ones: better than none
            if pool:
                return pool[0]
        return None

    def apply(self, video_path):
        """A programme segment has started: put the viewer's caption choice back."""
        if self.on is None:
            return ""
        try:
            if not self.on or video_path in self.muted:
                self._touch()
                self._show_off()
                return "off" if not self.on else "muted"
            sub = self.files.get(video_path)
            if sub:
                self._touch()
                self.player.setSubtitles(sub)
                self.player.showSubtitles(True)
                return "file"
            tracks, _cur, _en = self.tracks()
            t = self._best(tracks, video_path)
            if not t:
                return "none"                  # this programme has no captions (yet): nothing to do
            self._touch()
            self.player.setSubtitleStream(t["index"])
            self.player.showSubtitles(True)
            self.applied = t
            return t["label"]
        except Exception as exc:
            K.log_err("captions apply: %s" % exc)
            return ""

    def switch(self, on):
        """The menu's 'Closed captions: On / Off' - the TV's CC setting, for every
        programme from now on.  Works any time (commercials, guide, weather); a
        programme on screen changes straight away."""
        here = bool(self.cur) and self._playing() == self.cur["path"]
        if not on:
            if here:
                self.set_off()
            else:
                self.on = False
                self.muted.clear()
                self._remember()
            return _("Captions off")
        self.on = True
        self.muted.clear()
        self._remember()
        if not here:
            return _("Captions on")
        tracks, _c, _e = self.tracks()
        t = self._best(tracks, self.cur["path"])
        if t and not t["forced"]:
            self.set_track(t)
            return _("Captions on: %s") % t["label"]
        return _("Captions on - this programme has none")

    def toggle(self):
        """The remote's CC / subtitles button: on (best track) or off."""
        tracks, cur, enabled = self.tracks()
        if not tracks:                      # nothing to show: keep the viewer's choice as it is
            return _("No captions for this programme")
        path = self.cur["path"] if self.cur else None
        # a forced track Kodi switched on by itself isn't captions: first press = on;
        # a programme switched off from a phone: the CC button brings them back
        if (self.on and path not in self.muted) or (self.on is None and self._full_showing(tracks, cur, enabled)):
            self.set_off()
            return _("Captions off")
        t = self._best(tracks, self.cur["path"] if self.cur else None)
        self.set_track(t)
        return _("Captions: %s") % t["label"]

    def next_track(self):
        """The remote's 'next subtitle' button: step through the tracks, then off."""
        tracks, cur, enabled = self.tracks()
        if not tracks:
            return _("No captions for this programme")
        if not (self.on and enabled) or cur is None:
            t = tracks[0]
        else:
            nxt = [x for x in tracks if x["index"] > cur]
            if not nxt:
                self.set_off()
                return _("Captions off")
            t = nxt[0]
        self.set_track(t)
        return _("Captions: %s") % t["label"]

    def status_label(self):
        tracks, cur, enabled = self.tracks()
        if self.on is False or not self._full_showing(tracks, cur, enabled):
            return _("Off")
        t = next((x for x in tracks if x["index"] == cur), None)
        return t["label"] if t else _("On")

    # ----------------------------------------------------------- the menu
    def menu(self, video_path, source_path=None):
        """Off / each track (current one ticked) / a subtitle file / search online.
        video_path: the file as Kodi plays it; source_path: as the library has it
        (they differ for disc images, .strm...) - 'load a file' starts there."""
        tracks, cur, enabled = self.tracks()
        showing = self.on is not False and self._full_showing(tracks, cur, enabled)
        rows, acts = [], []
        tick = lambda yes: "[B]> [/B]" if yes else "    "
        rows.append(tick(not showing) + _("Off"))
        acts.append(("off", None))
        for t in tracks:
            rows.append(tick(showing and t["index"] == cur) + t["label"])
            acts.append(("track", t))
        if not tracks:
            rows.append("[COLOR grey]    %s[/COLOR]" % _("This programme has no captions of its own"))
            acts.append(("none", None))
        rows.append("    " + _("Load a subtitle file..."))
        acts.append(("file", None))
        if self.search_available():
            rows.append("    " + _("Search online (Kodi's subtitle search)..."))
            acts.append(("search", None))
        i = xbmcgui.Dialog().select(_("Captions (CC)"), rows)
        if i < 0:
            return ""
        what, t = acts[i]
        if what == "off":
            self.set_off()
            return _("Captions off")
        if what == "track":
            self.set_track(t)
            return _("Captions: %s") % t["label"]
        if what == "file":
            src = source_path or video_path
            cut = max(src.rfind("/"), src.rfind("\\")) if src else -1
            start = src[:cut + 1] if cut > 0 else ""                # the programme's own folder
            sub = xbmcgui.Dialog().browse(1, _("Subtitle file"), "files", SUB_FILES, False, False, start)
            if sub and sub != start and self.load_file(video_path, sub):
                return _("Captions: %s") % os.path.basename(sub)
            return ""
        if what == "search":
            return self.search(video_path)
        return ""

    def search(self, video_path):
        """Kodi's own subtitle search, without pausing live TV.  Whatever it
        downloads becomes this programme's captions, after the breaks too."""
        before, before_cur, before_on = self.tracks()
        swapped = _get_setting(PAUSE_SETTING) is True
        if swapped:
            st = K.load_json(K.STATE_FILE, {})
            st[PAUSE_ORIG] = True                    # put back next start if Kodi closes meanwhile
            K.save_json(K.STATE_FILE, st)
            _set_setting(PAUSE_SETTING, False)
        mon = xbmc.Monitor()
        try:
            xbmc.executebuiltin("ActivateWindow(subtitlesearch)")
            for _i in range(30):                     # give it up to 3 s to open
                if xbmc.getCondVisibility("Window.IsActive(subtitlesearch)") or mon.waitForAbort(0.1):
                    break
            waited = 0.0
            while xbmc.getCondVisibility("Window.IsActive(subtitlesearch)") and waited < 900:
                if mon.waitForAbort(0.25):
                    break
                waited += 0.25
        finally:
            if swapped:
                _set_setting(PAUSE_SETTING, True)
                st = K.load_json(K.STATE_FILE, {})
                st.pop(PAUSE_ORIG, None)
                K.save_json(K.STATE_FILE, st)
        if xbmc.getCondVisibility("Player.Paused"):  # Kodi paused anyway: carry on, back on the clock
            try:
                self.player.pause()
            except Exception:
                pass
            self.resync = True
        mon.waitForAbort(0.5)                        # the new track settles in
        after, cur, enabled = self.tracks()
        self.seen = (enabled, cur)
        t = next((x for x in after if x["index"] == cur), None)
        unchanged = len(after) <= len(before) and cur == before_cur and enabled == before_on
        if not (enabled and t) or unchanged:
            return ""                                # nothing new was chosen
        self.on = True
        self.lang = t["lang"] or self.lang
        self._remember()
        self._touch()
        if video_path:
            self.picks[video_path] = {"lang": t["lang"], "name": t["name"]}
        return _("Captions: %s") % t["label"]

    def take_resync(self):
        r, self.resync = self.resync, False
        return r

    @staticmethod
    def search_available():
        """Kodi's online subtitle search needs a subtitle service add-on (OpenSubtitles...)."""
        try:
            r = K.rpc("Addons.GetAddons", {"type": "xbmc.subtitle.module", "enabled": True})
            return bool((r or {}).get("addons"))
        except Exception:
            return False


# ------------------------------------------------------------------ remote CC button
def keymap_tool():
    """Settings > Tools: let the remote's subtitle button reach CableBox, or undo it."""
    d = xbmcgui.Dialog()
    title = _("Remote CC button")
    if xbmcvfs.exists(KEYMAP):
        if d.yesno(title, _("The remote's subtitle button is set up for CableBox.[CR]Remove it?")):
            xbmcvfs.delete(KEYMAP)
            xbmc.executebuiltin("Action(reloadkeymaps)")
            d.notification(title, _("Removed"), time=2500)
        return
    if not d.yesno(title, _("Kodi only sends the remote's subtitle button to its own full-screen player. "
                            "Add a small keymap so it switches captions on and off in CableBox too?[CR]"
                            "Elsewhere in Kodi it toggles subtitles of a playing video.")):
        return
    folder = "special://profile/keymaps/"
    try:
        if not xbmcvfs.exists(folder):
            xbmcvfs.mkdirs(folder)
        f = xbmcvfs.File(KEYMAP, "w")
        try:
            f.write(KEYMAP_XML)
        finally:
            f.close()
    except Exception as exc:
        K.log_err("keymap: %s" % exc)
        d.ok(title, _("Couldn't write the keymap file."))
        return
    xbmc.executebuiltin("Action(reloadkeymaps)")
    d.notification(title, _("Done - press the subtitle button while watching"), time=3500)

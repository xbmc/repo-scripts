"""Music channels in the TV window: playout and the still music screen.

Playout: the songs planned from now on wait in Kodi's music playlist (played
windowed, so Kodi's own music screen never opens) and Kodi moves from song to
song by itself, gaplessly (Step 0: ~0.05 s, the player never stops).  Tuning in
starts the song on air at the real clock's point.  While the viewer stays, the
screen follows what Kodi actually plays; the playlist is only rebuilt when Kodi
stopped or is far off the plan.

Screen: mostly still, like DMX.  The song block fades when the song changes,
the info panel fades every ~20 s, and every few minutes the whole layout moves
by a few pixels (inside the 4:3 safe area) so the logo and the genre bar never
burn in.  Window properties only; the layout is in the skin XML (mode "music").
"""
import threading
import time

import xbmc
import xbmcgui

from . import kodiutil as K
from . import logos
from . import music
from . import promos
from . import stations
from .kodiutil import _

AHEAD = 8                 # songs waiting in Kodi's playlist
TOP_UP = 4                # top up when fewer than this are left after the one playing
STOP_RESTART = 3.0        # s without playback: start again from the plan
PANEL_SECS = 20
FADE = 0.45               # s, the skin's fade time (+ a little)
DRIFT_SECS = 180
DRIFT = ((0, 0), (8, 5), (-6, 9), (10, -4), (-9, -6), (4, 10), (-10, 3), (6, -9))
GROUP = 170               # the music screen's group in the skin
START_LAG = 0.3           # s: opening a song takes about this long


class MusicScreen(object):
    def __init__(self, tv):
        self.tv = tv
        self.items = []            # schedule entries now in Kodi's playlist, in order
        self.key = None            # (channel id, start) of the playout
        self.started_at = 0
        self.seek_to = None        # (index, seconds) once Kodi plays it
        self.stopped_since = 0
        self.shown = None          # start of the entry on screen
        self.fade_at = 0
        self.pages = []
        self.page = 0
        self.panel_at = 0
        self.panel_phase = ""      # "" / "out" (fading out)
        self.drift_at = 0
        self.drift_i = 0
        self.paths = {}            # channel id -> set of its song paths ("also on this album")
        self.info_token = 0

    # ------------------------------------------------------------ in/out
    def leave(self):
        self.items = []
        self.key = None
        self.seek_to = None
        self.shown = None
        self.pages = []
        for k in ("mu_son", "mu_pon"):
            self.tv.setProperty(k, "")

    def tick(self, now):
        tv = self.tv
        ch = tv.ch
        sched = tv.lineup.schedule(ch)
        e = sched.entry_at(now)
        if e is None or e.get("k") != "song":
            if tv.cur_key != ("music-none", ch["id"]):
                tv.cur_key = ("music-none", ch["id"])
                tv.cur_entry = None
                self.leave()
                tv.stop_player()
                tv.set_mode("card")
                tv.card(ch["name"], _("No songs to play"), _("Channel manager > this channel > Check songs"), "")
            return
        if tv.cur_key != ("music", ch["id"]):
            tv.cur_key = ("music", ch["id"])
            tv.cur_entry = e
            tv.unqueue()
            tv.show_bug(False)
            self.set_static(ch)
            tv.set_mode("music")
            self.start(sched, e, now)
        else:
            self.follow(sched, e, now)
        self.screen(now)

    # ------------------------------------------------------------ playout
    def _following(self, sched, after_s, n):
        out = []
        for x in sched.data["entries"]:
            if x["s"] > after_s and x.get("k") == "song":
                out.append(x)
                if len(out) >= n:
                    break
        return out

    def _li(self, x, offset=0.0):
        li = xbmcgui.ListItem(x.get("t") or "", path=x["p"])
        try:
            tag = li.getMusicInfoTag()
            tag.setTitle(x.get("t") or "")
            if x.get("a"):
                tag.setArtist(x["a"])
            if x.get("al"):
                tag.setAlbum(x["al"])
            if x.get("y"):
                tag.setYear(int(x["y"]))
        except Exception:
            pass
        if offset > 1:
            li.setProperty("StartOffset", "%.1f" % offset)
        return li

    def start(self, sched, e, now):
        """Tune-in (or a restart): the song on air at its real-clock point, the next ones queued."""
        tv = self.tv
        self.items = []
        for x in [e] + self._following(sched, e["s"], AHEAD + 6):
            if tv.file_missing(x.get("p")):
                K.log_err("Music: missing file, skipped: %s" % x.get("p"))
                continue
            self.items.append(x)
            if len(self.items) > AHEAD:
                break
        if not self.items:
            tv.stop_player()
            tv.set_mode("card")
            tv.card(tv.ch["name"], _("No songs to play"), _("Channel manager > this channel > Check songs"), "")
            return
        offset = max(0.0, time.time() - e["s"] + START_LAG) if self.items[0] is e else 0.0
        tv.tone_off()                  # from an off-air bars-and-tone channel: repeat-one off first
        pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0))
        pl.clear()
        for i, x in enumerate(self.items):
            pl.add(x["p"], self._li(x, offset if i == 0 else 0))
            tv.our_files.add(x["p"])
        self.key = (tv.ch["id"], e["s"])
        self.started_at = time.time()
        self.stopped_since = 0
        self.seek_to = (0, offset) if offset > 2 else None
        self.shown = None
        tv.play_token += 1
        tv.play_started_at = time.time()
        xbmcgui.Window(10000).setProperty("cablebox42.play_at", "%.1f" % time.time())
        tv.player.play(pl, windowed=True, startpos=0)

    def follow(self, sched, e, now):
        tv = self.tv
        try:
            playing = tv.player.isPlayingAudio() and not tv.player.isPlayingVideo()
            pos = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0)).getposition() if playing else -1
            t = tv.player.getTime() if playing else 0.0
        except Exception:
            playing, pos, t = False, -1, 0.0
        if not playing or not (0 <= pos < len(self.items)):
            if now - self.started_at < 8:
                return                          # still opening
            if not self.stopped_since:
                self.stopped_since = now
            elif now - self.stopped_since > STOP_RESTART:
                K.log("Music: playback stopped - starting again from the schedule", xbmc.LOGINFO)
                self.start(sched, e, now)
            return
        self.stopped_since = 0
        if self.seek_to and self.seek_to[0] == pos and t > 0.1:
            want = self.seek_to[1]
            self.seek_to = None
            if t < want - 3:                    # StartOffset wasn't taken: seek
                tv.player.seekTime(want)
        # Kodi a song ahead of or behind the plan is fine around a song change (the
        # library's song lengths are whole seconds); further off: back to the plan
        want = next((i for i, x in enumerate(self.items) if x["s"] == e["s"]), None)
        skipped = want is None and e["s"] < self.items[0]["s"]      # its file was missing
        if not skipped and (want is None or abs(pos - want) > 1):
            K.log("Music: Kodi is on %s, the plan says %s - back to the plan"
                  % (self.items[pos]["p"], e["p"]), xbmc.LOGINFO)
            self.start(sched, e, now)
            return
        if len(self.items) - pos - 1 < TOP_UP:
            more = self._following(sched, self.items[-1]["s"], AHEAD - (len(self.items) - pos - 1))
            pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0))
            for x in more:
                if tv.file_missing(x.get("p")):
                    K.log_err("Music: missing file, skipped: %s" % x.get("p"))
                    continue
                pl.add(x["p"], self._li(x))
                tv.our_files.add(x["p"])
                self.items.append(x)

    # ------------------------------------------------------------ screen
    def playing_item(self):
        try:
            pos = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0)).getposition()
        except Exception:
            return None
        return self.items[pos] if 0 <= pos < len(self.items) else None

    def set_static(self, ch):
        """Logo (or the name in large type) and the genre bar: once per tune-in."""
        tv = self.tv
        br = stations.brand(ch)
        logo = br["logo"] or logos.logo_for(ch)
        tv.setProperty("mu_logo", logo or "")
        name = br["name"] or ch.get("name", "")
        tv.setProperty("mu_name", name)
        tv.setProperty("mu_nfit", promos.fit_font(name, 600, promos.LADDER_60, promos.TWO_27))
        tv.setProperty("mu_name2", promos.two_lines(name))
        tv.setProperty("mu_bar", ch.get("name", ""))
        tv.setProperty("mu_gfit", promos.fit_font(ch.get("name", ""), 1180, promos.LADDER_45, promos.TWO_27))
        tv.setProperty("mu_bar2", promos.two_lines(ch.get("name", "")))
        self.drift_at = 0

    def screen(self, now):
        tv = self.tv
        cur = self.playing_item()
        if cur is not None and cur["s"] != self.shown:
            if self.shown is None:
                self.show_song(cur)               # tune-in: straight in
            elif not self.fade_at:
                tv.setProperty("mu_son", "")      # fade out, then the new song fades in
                self.fade_at = now + FADE
            elif now >= self.fade_at:
                self.fade_at = 0
                self.show_song(cur)
        self.panel_tick(now)
        if now >= self.drift_at:
            self.drift_at = now + DRIFT_SECS
            self.drift_i = (self.drift_i + 1) % len(DRIFT)
            dx, dy = DRIFT[self.drift_i]
            try:
                tv.getControl(GROUP).setPosition(dx, dy)
            except Exception:
                pass

    def show_song(self, x):
        tv = self.tv
        self.shown = x["s"]
        tv.setProperty("mu_artist", x.get("a") or "")
        tv.setProperty("mu_title", x.get("t") or "")
        al = x.get("al") or ""
        y = x.get("y") or 0
        tv.setProperty("mu_album", ("%s (%d)" % (al, y) if al and y else al or (str(y) if y else "")))
        nxt = []
        i = next((j for j, it in enumerate(self.items) if it["s"] == x["s"]), -1)
        for it in self.items[i + 1:]:
            a = it.get("a")
            if a and a not in nxt and a != x.get("a"):
                nxt.append(a)
            if len(nxt) == 2:
                break
        tv.setProperty("mu_next", (_("Coming up: %s") % u" · ".join(nxt)) if nxt else "")
        tv.setProperty("mu_son", "1")
        # the info panel: the tags straight away, the library's facts when they're read
        self.set_pages(music.panel_pages(x), first=True)
        self.info_token += 1
        threading.Thread(target=self._details, args=(x, self.info_token, tv.ch["id"], list(tv.ch["sources"])),
                         name="cablebox42-music-info").start()

    def _details(self, x, token, cid, sources):
        try:
            paths = self.paths.get(cid)
            if paths is None:
                paths = set(s["p"] for s in music.songs_for(sources))
                self.paths[cid] = paths
            album, artist, total, also = music.song_details(x, paths)
            pages = music.panel_pages(x, album, artist, total, also)
        except Exception as exc:
            K.log_err("music info: %s" % exc)
            return
        if token == self.info_token and not self.tv.closing:
            self.set_pages(pages, first=False)

    def set_pages(self, pages, first):
        self.pages = pages
        if first:
            self.page = 0
            self.panel_phase = ""
            self.show_page(time.time())
        elif not self.tv.getProperty("mu_ph") and pages:
            self.page = 0
            self.show_page(time.time())

    def show_page(self, now):
        tv = self.tv
        if not self.pages:
            tv.setProperty("mu_pon", "")
            tv.setProperty("mu_ph", "")
            tv.setProperty("mu_pt", "")
            self.panel_at = now + PANEL_SECS
            return
        h, t = self.pages[self.page % len(self.pages)]
        tv.setProperty("mu_ph", h)
        tv.setProperty("mu_pt", t)
        tv.setProperty("mu_pon", "1")
        self.panel_at = now + PANEL_SECS

    def panel_tick(self, now):
        if len(self.pages) < 2:
            return
        if self.panel_phase == "out":
            if now >= self.panel_at:
                self.panel_phase = ""
                self.page = (self.page + 1) % len(self.pages)
                self.show_page(now)
        elif now >= self.panel_at:
            self.tv.setProperty("mu_pon", "")
            self.panel_phase = "out"
            self.panel_at = now + FADE


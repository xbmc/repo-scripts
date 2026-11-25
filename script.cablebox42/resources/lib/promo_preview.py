"""Settings > Breaks > Preview a promo: one promo, full screen, exactly as it
airs in a break (same window, same card, same theme music: promos.air), with
clean black before and after it for a screen recorder.

    RunScript(script.cablebox42,preview_promo,settings)    pick a channel and a promo,
                                                            then back to Settings
    RunScript(script.cablebox42,preview_promo)             the same, without reopening Settings
    RunScript(script.cablebox42,preview_promo,<tvshowid>)  that show (contact sheet, keymaps)

Read-only: it reads the channels' saved schedules (never builds or changes
one), so "How often", the planned breaks and the series stay as they were.
"""
import math
import threading
import time

import xbmc
import xbmcgui

from . import kodiutil as K
from . import promos
from . import scheduler
from . import stations
from .kodiutil import _

LEAD_IN = 2.0           # seconds of black before the card (time to start recording)
LEAD_OUT = 1.0          # ...and after it, once the music has stopped
TOOL = "preview_promo"  # manager.TOOL_BUSY while it runs: the CableBox menu waits for it


def _first_episode(tvshowid):
    from . import library
    eps = library.episodes_for(tvshowid)
    return eps[0]["file"] if eps else ""


def _block_path(sc, b):
    """The file of a programme block (its first episode)."""
    for e in sc.data["entries"]:
        if b["s"] <= e["s"] < b["e"] and e.get("k") == "show" and e.get("p"):
            return e["p"]
    return ""


def target(tvshowid, now=None):
    """{title, path, pt, ch, later} for this show's promo (contact sheet and
    RunScript(...,preview_promo,<tvshowid>))."""
    now = now or time.time()
    d = K.rpc("VideoLibrary.GetTVShowDetails", {"tvshowid": int(tvshowid), "properties": ["title"]})
    title = (d.get("tvshowdetails") or {}).get("title") or ""
    out = {"title": title, "path": "", "pt": None, "ch": None, "later": False}
    try:
        lineup = scheduler.Lineup(K.schedule_cfg())
    except Exception as exc:
        K.log("preview promo: no lineup (%s)" % exc)
        lineup = None
    best = None
    for c in (lineup.channels if lineup else []):
        try:
            sc = lineup.schedule(c, ensure=False)          # never builds anything
        except Exception:
            continue
        for b in sc.blocks_between(now, now + 24 * 3600):
            if b["s"] > now and b.get("k") == "show" and b["t"].lower() == title.lower():
                if best is None or b["s"] < best[0]["s"]:
                    best = (b, c, sc)
                break
    if best:
        b, c, sc = best
        out.update(path=_block_path(sc, b), pt=b["s"], ch=c, later=b is not sc.next_block(now))
    else:
        home = ((lineup.assignment if lineup else None) or {}).get("home", {}).get(title.lower())
        ch = next((c for c in (lineup.channels if lineup else []) if c["id"] == home), None)
        out.update(path=_first_episode(tvshowid), pt=scheduler.ceil_slot(now + 60, 1800), ch=ch)   # "next", half past
    return out


def _window_props(ch, now):
    """What the TV window has on top of the card itself: the station logo the
    card shows, and the CRT look."""
    logo = ""
    if ch and K.setting_bool("logo_banner", True):
        logo = stations.brand(ch, now)["logo"]
    crt = K.setting_int("crt_mode", 0)
    return {"banner_logo": logo, "crt": str(crt) if crt in (1, 2) else ""}


def card_for_show(tvshowid, now=None):
    """(window properties, music path, title) of a show's promo card (the
    contact sheet draws every show's card with this)."""
    now = now or time.time()
    t = target(tvshowid, now)
    inf = promos.info(t["path"], t["title"])
    ch = t["ch"]
    name = stations.brand(ch, t["pt"])["name"] if ch else ""      # its branding at that hour
    props = promos.card(inf, t["title"], t["pt"], now, ch, name, t["later"])
    # like the TV: a logo not yet in the texture cache gives a title-only card; it
    # loads in the background meanwhile, so the next preview of this show has it
    preload = "" if props.get("promo_logo") else (inf.get("logo") or "")
    props.update(_window_props(ch, now), mode="promo", promo_preload=preload)
    return props, promos.music(inf), t["title"]


# ------------------------------------------------------------------ pickers
def _upcoming(sc, now):
    """This channel's programmes starting in the next 6 hours (promos' look-ahead)."""
    return [b for b in sc.blocks_between(now, now + scheduler.PROMO_LOOKAHEAD)
            if b["s"] > now and b.get("k") == "show"]


def pick_channel(lineup, now, last=None):
    """The channel picker: (channel, its schedule), or None for Back."""
    rows, chans = [], []
    for c in lineup.channels:
        if c.get("type") not in scheduler.PROMO_TYPES:
            continue
        try:
            sc = lineup.schedule(c, ensure=False)          # never builds anything
        except Exception:
            continue
        up = _upcoming(sc, now)
        li = xbmcgui.ListItem("%d  %s" % (c["number"], stations.brand(c, now)["name"]),
                              _("Up next: %s") % up[0]["t"] if up else
                              _("Nothing in the next 6 hours"))
        logo = stations.brand(c, now)["logo"]
        li.setArt({"thumb": logo, "icon": logo})
        rows.append(li)
        chans.append((c, sc))
    if not rows:
        xbmcgui.Dialog().ok(_("Preview promo"), _("No channels with programmes yet"))
        return None
    pre = next((i for i, (c, _sc) in enumerate(chans) if last and c["id"] == last), 0)
    i = xbmcgui.Dialog().select(_("Preview a promo for which channel?"), rows, useDetails=True, preselect=pre)
    return chans[i] if i >= 0 else None


def pick_promo(ch, sc, now):
    """Up next, or one of the programmes later today: (block, later) or None for Back."""
    up = _upcoming(sc, now)
    if not up:
        xbmcgui.Dialog().ok(_("Preview promo"), _("Nothing on %s in the next 6 hours") % ch["name"])
        return None
    nxt, later = up[0], up[1:]
    rows = [xbmcgui.ListItem(_("Up next"), "%s, %s" % (nxt["t"], promos.clock(nxt["s"])))]
    if later:
        rows.append(xbmcgui.ListItem(_("Later today"), _("Pick from %d programmes in the next 6 hours") % len(later)))
    while True:
        i = xbmcgui.Dialog().select(_("Preview which promo?"), rows, useDetails=True)
        if i < 0:
            return None
        if i == 0:
            return nxt, nxt is not sc.next_block(now)
        items = [xbmcgui.ListItem(b["t"], promos.day_phrase(b["s"], now)) for b in later]
        j = xbmcgui.Dialog().select(_("Later today"), items, useDetails=True)
        if j >= 0:
            return later[j], True


# ------------------------------------------------------------------ playing it
class PreviewWindow(xbmcgui.WindowXML):
    """The TV window's own layout: black, the promo as it airs in a break, black.
    It closes itself once the card has cut to black, the music has stopped and
    the lead-out has passed; Back, Stop or OK end it early (same clean cut)."""
    ch = None
    subj = None                  # (time, path, title, later)
    win_id = 0

    def onInit(self):
        self.win_id = xbmcgui.getCurrentWindowId()
        self.player = xbmc.Player()
        self.theme = promos.ThemeAudio(self.player)
        self.stop = threading.Event()
        self.setProperty("mode", "")                 # the window's own black background
        for k, v in _window_props(self.ch, time.time()).items():
            self.setProperty(k, v)
        threading.Thread(target=self._run, name="cablebox42-preview").start()

    def _wait(self, secs):
        """False if Back was pressed or Kodi is closing."""
        mon = xbmc.Monitor()
        end = time.time() + secs
        while time.time() < end:
            if self.stop.is_set() or mon.waitForAbort(0.05):
                return False
        return not self.stop.is_set()

    def _run(self):
        try:
            pt, path, title, later = self.subj
            # the logo loads into the texture cache during the black, so the
            # card shows it from its first frame (as tv.prefetch_promo does)
            try:
                self.setProperty("promo_preload", promos.info(path, title or "").get("logo") or "")
            except Exception as exc:
                K.log_err("preview promo: %s" % exc)
            if self._wait(LEAD_IN):
                now = time.time()
                end = now + promos.PROMO_LEN
                music = promos.air(self, self.ch, pt, path, title, later, now)
                if music:
                    self.theme.start(music, end)
                mon = xbmc.Monitor()
                while not self.stop.is_set() and time.time() < end - 0.05:
                    if time.time() < now + 4:
                        promos.close_busy_wheel()    # as the TV does while the theme starts
                    if mon.waitForAbort(0.02):
                        break
            self.setProperty("mode", "")              # cut to black...
            self.theme.stop()                         # ...and the music with it
            if not promos.wait_stopped(self.player):
                K.log("preview promo: the player didn't stop", xbmc.LOGWARNING)
            if not self.stop.is_set():
                self._wait(LEAD_OUT)
        except Exception as exc:
            K.log_err("preview promo: %s" % exc)
            self.theme.stop()
        finally:
            self.close()

    def onAction(self, action):
        if action.getId() in (10, 92, 13, 7):         # Back, Stop or OK: end it (same clean cut)
            self.stop.set()


def _settle(player, win_id, secs=5.0):
    """After the window: wait until it has really closed and the player has
    stopped, so nothing (Settings, the menu) opens over the last frame or the music."""
    mon = xbmc.Monitor()
    end = time.time() + secs
    while time.time() < end:
        try:
            gone = xbmcgui.getCurrentWindowId() != win_id
            playing = player.isPlaying()
        except Exception:
            return
        if gone and not playing:
            return
        if mon.waitForAbort(0.05):
            return
    K.log("preview promo: still busy after %.0f s" % secs, xbmc.LOGWARNING)


def play(ch, subj):
    """Black, the promo, black; returns once its window has closed and the
    player has stopped."""
    player = xbmc.Player()
    if player.isPlaying():
        if not xbmcgui.Dialog().yesno(_("Preview promo"), _("Stop what's playing to show the preview?")):
            return
        player.stop()
        promos.wait_stopped(player)
    K.log("Preview promo: %s on %s" % (subj[2], ch["name"] if ch else "-"), xbmc.LOGINFO)
    win = PreviewWindow("script-cablebox42-tv.xml", K.ADDON_PATH, "Default", "1080i")
    win.ch, win.subj = ch, subj
    win.doModal()
    win_id = win.win_id
    del win
    _settle(player, win_id)


def run(tvshowid=None, from_settings=False):
    from .manager import TOOL_BUSY
    home = xbmcgui.Window(10000)
    home.setProperty(TOOL_BUSY, TOOL)       # the CableBox menu waits instead of opening over the promo
    try:
        if home.getProperty("cablebox42.running"):
            xbmcgui.Dialog().ok(_("Preview promo"), _("Turn CableBox's TV off first"))
        elif tvshowid is not None:
            try:
                t = target(tvshowid)
            except Exception as exc:
                K.log_err("preview promo: %s" % exc)
                xbmcgui.Dialog().ok(_("Preview promo"), _("Couldn't make this show's promo (see the Kodi log)"))
            else:
                play(t["ch"], (t["pt"], t["path"], t["title"], t["later"]))
        else:
            _pick_and_play()
        if from_settings:
            K.ADDON.openSettings()          # Settings again, only now that the promo is over
    finally:
        home.clearProperty(TOOL_BUSY)


def _pick_and_play():
    try:
        lineup = scheduler.Lineup(K.schedule_cfg())
    except Exception as exc:
        K.log_err("preview promo: %s" % exc)
        xbmcgui.Dialog().ok(_("Preview promo"), _("No channels with programmes yet"))
        return
    last = None
    while True:
        now = time.time()
        got = pick_channel(lineup, now, last)
        if got is None:
            return
        ch, sc = got
        last = ch["id"]
        sel = pick_promo(ch, sc, now)
        if sel is None:
            continue                         # Back: the channel list again
        b, later = sel
        play(ch, (b["s"], _block_path(sc, b), b["t"], later))
        return


# ------------------------------------------------------------------ retro ads
# RunScript(script.cablebox42,preview_ad,P01) - one retro ad, full screen, as it
# airs in a house break (ads.card / ads.apply_card, its jingle); "video" or
# "video:<movieid>" for a Now on videocassette card.  For screenshots and
# checking cards on the box; no menu entry.
class AdPreviewWindow(xbmcgui.WindowXML):
    entry = None
    win_id = 0

    def onInit(self):
        self.win_id = xbmcgui.getCurrentWindowId()
        self.player = xbmc.Player()
        self.theme = promos.ThemeAudio(self.player)
        self.stop = threading.Event()
        self.setProperty("mode", "")
        threading.Thread(target=self._run, name="cablebox42-adpreview").start()

    def _run(self):
        from . import ads
        mon = xbmc.Monitor()
        try:
            if self.entry.get("k") in ("station", "signoff"):
                self._station()
                return
            if self.entry.get("k") == "upnext":
                self._upnext()
                return
            c = ads.card(self.entry)
            if not c:
                K.log_err("preview ad: %s can't run" % self.entry)
                return
            if mon.waitForAbort(0.5) or self.stop.is_set():
                return
            ads.apply_card(self, c, ads.Slots())
            self.setProperty("mode", "retro")
            end = time.time() + ads.length(self.entry)
            music = ads.music(c)
            if music:
                self.theme.start(music, end)
            while not self.stop.is_set() and time.time() < end - 0.05:
                if mon.waitForAbort(0.05):
                    break
            self.setProperty("mode", "")
            self.theme.stop()
            promos.wait_stopped(self.player)
        except Exception as exc:
            K.log_err("preview ad: %s" % exc)
            self.theme.stop()
        finally:
            self.close()

    def _upnext(self):
        from . import ads, stations
        from .tv import fmt_time
        mon = xbmc.Monitor()
        lineup = scheduler.Lineup(K.schedule_cfg())
        ch = next((c for c in lineup.channels if c["number"] == self.entry.get("num")), None) or lineup.channels[0]
        sched = lineup.schedule(ch, ensure=False)
        now = time.time()
        nb = sched.next_block(now)
        for _i in range(max(0, self.entry.get("idx", 1) - 1)):
            nb = sched.next_block(nb["e"] - 1) if nb else None
        if not nb:
            K.log_err("preview up next: nothing planned on %s" % ch.get("name"))
            return
        first = sched.entry_at(nb["s"] + 0.5) or {}
        br = stations.brand(ch, nb["s"])
        chlogo = br["logo"]
        c = ads.upnext_card(ch, ch["number"], br["name"], nb, nb["s"], fmt_time(nb["s"]),
                            first.get("p") if first.get("k") == "show" else "",
                            chlogo if ads.logo_usable(chlogo) else "")
        if mon.waitForAbort(0.5) or self.stop.is_set():
            return
        slots = ads.Slots()
        ads.apply_upnext(self, c, slots, time.time())
        self.setProperty("mode", "upnext")
        end, shown = time.time() + 20, None
        while not self.stop.is_set() and time.time() < end:
            left = int(math.ceil(nb["s"] - time.time()))
            if left != shown:
                shown = left
                slots.fill(self, ads.countdown(nb["s"], time.time()), (ads.SLOT_CLOCK,))
            if mon.waitForAbort(0.1):
                break
        self.setProperty("mode", "")

    def _station(self):
        from . import ads, stations
        mon = xbmc.Monitor()
        chans = scheduler.Lineup(K.schedule_cfg()).channels
        ch = next((c for c in chans if c["number"] == self.entry.get("num")), None) or chans[0]
        now = time.time()
        br = stations.brand(ch, now)
        logo = br["logo"]
        logo = logo if ads.logo_usable(logo) else ""
        if self.entry.get("k") == "signoff":
            # when this channel's next off-air hours end (else 6:00 AM, for the look)
            from .tv import fmt_time
            ends = [b["e"] for b in scheduler.Lineup(K.schedule_cfg()).schedule(ch).blocks_between(now, now + 86400)
                    if b.get("k") == "offair"]
            resume = fmt_time(ends[0]) if ends else fmt_time(time.mktime(time.localtime()[:3] + (6, 0, 0, 0, 0, -1)))
            c = ads.signoff_card(br["name"], ch["number"], logo, stations.tagline(ch, now), ads.genre_line(ch),
                                 resume)
        else:
            c = ads.station_card(br["name"], ch["number"], logo, stations.tagline(ch, now), ads.genre_line(ch))
        if mon.waitForAbort(0.5) or self.stop.is_set():
            return
        ads.apply_card(self, c, ads.Slots())
        self.setProperty("mode", "station")
        end = time.time() + 20
        while not self.stop.is_set() and time.time() < end:
            if mon.waitForAbort(0.05):
                break
        self.setProperty("mode", "")

    def onAction(self, action):
        if action.getId() in (10, 92, 13, 7):
            self.stop.set()


def run_ad(arg):
    from . import ads
    arg = (arg or "").strip()
    if arg.lower().startswith("upnext"):
        # upnext:<channel number>: that channel's Up next card for its next programme
        # upnext:<channel number>[:<k>]: the k-th programme from now (1 = the next)
        bits = arg.split(":")
        entry = {"k": "upnext", "num": int(bits[1]) if len(bits) > 1 else 0,
                 "idx": int(bits[2]) if len(bits) > 2 else 1}
    elif arg.lower().startswith("signoff"):
        # signoff:<channel number>: that channel's sign-off card for a while
        entry = {"k": "signoff", "num": int(arg.split(":", 1)[1]) if ":" in arg else 0}
    elif arg.lower().startswith("station"):
        # station:<channel number>: that channel's station ID card for a while
        entry = {"k": "station", "num": int(arg.split(":", 1)[1]) if ":" in arg else 0}
    elif arg.lower().startswith("video"):
        movies = ads.library_movies()
        mv = arg.split(":", 1)[1] if ":" in arg else (movies[0]["movieid"] if movies else 0)
        entry = {"k": "retro", "ad": "video", "mv": int(mv), "ln": 0}
    else:
        entry = {"k": "retro", "ad": arg.upper(), "ln": 0}
    if xbmcgui.Window(10000).getProperty("cablebox42.running"):
        xbmcgui.Dialog().ok(_("Preview promo"), _("Turn CableBox's TV off first"))
        return
    win = AdPreviewWindow("script-cablebox42-tv.xml", K.ADDON_PATH, "Default", "1080i")
    win.entry = entry
    win.doModal()
    win_id = win.win_id
    del win
    _settle(xbmc.Player(), win_id)

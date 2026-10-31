"""The TV set: full-screen window, remote handling and the playout loop.

Playback is plain xbmc.Player (windowed into our videowindow control), so on
every device each file goes through the same hardware decoder as it
does when you play it from the library.
"""
import random
import threading
import time

import xbmc
import xbmcgui
import xbmcvfs

from . import kodiutil as K
from . import library
from . import scheduler
from . import weather
from . import progress
from .kodiutil import _


def _a(name, default):
    return getattr(xbmcgui, name, default)


CH_UP = {_a("ACTION_CHANNEL_UP", 184), _a("ACTION_MOVE_UP", 3), _a("ACTION_PAGE_UP", 5),
         _a("ACTION_NEXT_ITEM", 14)}
CH_DOWN = {_a("ACTION_CHANNEL_DOWN", 185), _a("ACTION_MOVE_DOWN", 4), _a("ACTION_PAGE_DOWN", 6),
           _a("ACTION_PREV_ITEM", 15)}
LAST_CH = {_a("ACTION_MOVE_LEFT", 1), 186}
CH_LIST = {_a("ACTION_MOVE_RIGHT", 2)}
INFO = {_a("ACTION_SELECT_ITEM", 7), _a("ACTION_SHOW_INFO", 11), 24}
MENU = {_a("ACTION_CONTEXT_MENU", 117), 163, _a("ACTION_SHOW_GUI", 18)}
EXIT = {_a("ACTION_PREVIOUS_MENU", 10), _a("ACTION_NAV_BACK", 92), _a("ACTION_STOP", 13)}
VOL_UP = {_a("ACTION_VOLUME_UP", 88)}
VOL_DOWN = {_a("ACTION_VOLUME_DOWN", 89)}
MUTE = {_a("ACTION_MUTE", 91)}
DIGITS = dict((58 + i, i) for i in range(10))
DIGITS.update(dict((140 + i, i) for i in range(2, 10)))  # JUMP_SMS2..9 numeric keypads

VIDEO_KINDS = ("show", "ad", "bump", "clip")
LOAD_TIMEOUT = 12.0


def fmt_time(ts):
    try:
        f = xbmc.getRegion("time").replace(":%S", "")
    except Exception:
        f = "%I:%M %p"
    s = time.strftime(f, time.localtime(ts))
    return s[1:] if s.startswith("0") else s


class Player(xbmc.Player):
    def __init__(self, owner):
        xbmc.Player.__init__(self)
        self.owner = owner

    def onAVStarted(self):
        self.owner.on_av_started()

    def onPlayBackError(self):
        self.owner.on_error()


class TVWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super(TVWindow, self).__init__(*args, **kwargs)
        self.lineup = scheduler.Lineup(K.schedule_cfg())
        self.player = Player(self)
        self.monitor = xbmc.Monitor()
        self.ch = None
        self.prev_ch = None
        self.cur_key = None
        self.cur_entry = None
        self.play_token = 0
        self.play_started_at = 0
        self.av_started_token = -1
        self.retries = 0
        self.failed_key = None
        self.sub = None              # stand-in for a programme Kodi couldn't open
        self.sub_at = 0
        self.digits = ""
        self.digits_at = 0
        self.osd_until = 0
        self.banner_until = 0
        self.static_until = 0
        self.toast_until = 0
        self.sleep_at = 0
        self.guide_next = 0
        self.promo_next = 0
        self.scroll_top = 0          # first guide row on screen
        self.scroll_next = 0
        self.promos = []
        self.closing = False
        self.started = False
        self.lock = threading.RLock()
        self.banner_secs = K.setting_int("banner_secs", 6)
        self.static_on = K.setting_bool("static_effect", True)
        self.static_sound = K.setting_bool("static_sound", True)
        self.confirm_exit = K.setting_bool("confirm_exit", True)
        self.guide_music = K.setting("guide_music_path")
        self.weather_music = K.setting("weather_music_path")
        self.weather = weather.WeatherScreen(self)
        self.progress = progress.Guard()     # put the viewer's resume points back afterwards
        self.progress.release(delay=0.5)     # anything a crash left behind
        self.win_id = None
        self.guide_pending = False
        self.away_since = 0
        self.our_files = set()

    # ----------------------------------------------------------- lifecycle
    def onInit(self):
        if self.started:
            return
        self.started = True
        self.win_id = xbmcgui.getCurrentWindowId()
        xbmcgui.Window(10000).setProperty("cablebox42.running", "1")
        crt = K.setting_int("crt_mode", 0)   # 0 off, 1 subtle, 2 full
        self.setProperty("crt", str(crt) if crt in (1, 2) else "")
        xbmc.executebuiltin("InhibitScreensaver(true)")
        if not self.lineup.channels:
            self.set_mode("card")
            self.card("CableBox 42", _("No channels yet"), _("Open the add-on and choose 'Build my lineup'"), "")
            return
        start = self.start_channel()
        self.tune(start, static=True)
        threading.Thread(target=self.loop, name="cablebox42-loop").start()
        threading.Thread(target=self.builder, name="cablebox42-builder").start()

    def start_channel(self):
        if getattr(self, "wanted_channel", None):
            ch = self.lineup.by_number(self.wanted_channel)
            if ch:
                return ch
        state = K.load_json(K.STATE_FILE, {})
        fixed = K.setting_int("start_channel", 0)
        want = fixed or state.get("last_channel")
        ch = self.lineup.by_number(int(want)) if want else None
        if not fixed and state.get("last_channel_id"):
            # follow the channel itself, even if it was renumbered since
            ch = next((c for c in self.lineup.channels if c["id"] == state["last_channel_id"]), ch)
        return ch or self.lineup.channels[0]

    def playing_ours(self):
        """True if Kodi's player is currently playing something CableBox started."""
        try:
            return self.player.isPlaying() and self.player.getPlayingFile() in self.our_files
        except Exception:
            return False

    def shutdown(self):
        if self.closing:
            return
        self.closing = True
        if self.ch:
            st = K.load_json(K.STATE_FILE, {})
            st["last_channel"] = self.ch["number"]
            st["last_channel_id"] = self.ch["id"]
            K.save_json(K.STATE_FILE, st)
        if self.playing_ours():
            try:
                self.player.stop()
            except Exception:
                pass
        if self.progress.pending:
            xbmc.sleep(2500)                 # let Kodi write its resume point first, then undo it
            self.progress.release_now()
        library.durations().save()
        xbmc.executebuiltin("InhibitScreensaver(false)")
        xbmcgui.Window(10000).clearProperty("cablebox42.running")
        self.close()

    # ----------------------------------------------------------- remote
    def onAction(self, action):
        aid = action.getId()
        if aid in DIGITS:
            self.digit(DIGITS[aid])
        elif aid in CH_UP:
            self.zap(1)
        elif aid in CH_DOWN:
            self.zap(-1)
        elif aid in LAST_CH:
            if self.prev_ch:
                self.tune(self.prev_ch)
        elif aid in CH_LIST:
            self.channel_list()
        elif aid in INFO:
            if self.cur_entry and self.cur_entry.get("k") == "guide":
                self.channel_list()
            else:
                self.toggle_banner()
        elif aid in MENU:
            self.menu()
        elif aid in EXIT:
            if not self.confirm_exit or xbmcgui.Dialog().yesno("CableBox 42", _("Turn off the TV?")):
                self.shutdown()
        elif aid in VOL_UP:
            K.rpc("Application.SetVolume", {"volume": "increment"})
        elif aid in VOL_DOWN:
            K.rpc("Application.SetVolume", {"volume": "decrement"})
        elif aid in MUTE:
            K.rpc("Application.SetMute", {"mute": "toggle"})
        # everything else (pause, seek...) is ignored: it's live TV

    def digit(self, d):
        with self.lock:
            self.digits = (self.digits + str(d))[-3:]
            self.digits_at = time.time()
            self.show_digits(self.digits.ljust(2, "_") if len(self.digits) < 2 else self.digits)
            if len(self.digits) >= 3:
                self.commit_digits()

    def commit_digits(self):
        n = int(self.digits) if self.digits else 0
        self.digits = ""
        ch = self.lineup.by_number(n)
        if ch:
            self.tune(ch)
        else:
            self.show_digits(str(self.ch["number"]) if self.ch else "")
            self.toast(_("Channel %d not available") % n, 2.5)

    def zap(self, step):
        nxt = self.lineup.neighbour(self.ch, step)
        if nxt:
            self.tune(nxt)

    # ----------------------------------------------------------- tuning
    def tune(self, ch, static=True):
        with self.lock:
            if self.ch and ch["id"] != self.ch["id"]:
                self.prev_ch = self.ch
            self.ch = ch
            self.cur_key = None
            self.failed_key = None
            self.retries = 0
            self.sub = None
            self.sub_at = 0
            self.show_digits(str(ch["number"]))
            self.setProperty("ch_number", str(ch["number"]))
            self.setProperty("ch_name", ch["name"])
            self.setProperty("ch_call", ch.get("callsign") or "")
            if static and self.static_on:
                self.setProperty("static", "1")
                self.static_until = time.time() + 0.45
                if self.static_sound:
                    xbmc.playSFX(K.media("static.wav"), False)
            self.lineup.schedule(ch)
            self.tick()
            self.update_banner()
            self.banner_until = time.time() + self.banner_secs
            self.setProperty("banner", "1")

    # ----------------------------------------------------------- background builder
    def builder(self):
        """Keep every channel's schedule ready without ever blocking the picture:
        nearby channels first, then the rest; top up every few minutes."""
        while not self.closing:
            try:
                self.lineup.refresh_assignment()
            except Exception as exc:
                K.log_err("assignment: %s" % exc)
            chans = list(self.lineup.channels)
            if self.ch and self.ch in chans:
                i, n = chans.index(self.ch), len(chans)
                order = sorted(range(n), key=lambda j: min((j - i) % n, (i - j) % n))
                chans = [chans[j] for j in order]
            for c in chans:
                if self.closing or self.monitor.waitForAbort(0.05):
                    return
                try:
                    self.lineup.schedule(c)
                except Exception as exc:
                    K.log_err("background build %s: %s" % (c.get("name"), exc))
            library.durations().save()
            if self.guide_pending:
                self.guide_pending = False
                self.guide_next = 0          # redraw the guide with the new listings
            for _w in range(300):
                if self.closing or self.monitor.waitForAbort(1):
                    return

    # ----------------------------------------------------------- main loop
    def loop(self):
        while not self.closing:
            if self.monitor.waitForAbort(0.2):
                self.shutdown()
                break
            try:
                with self.lock:
                    self.tick()
            except Exception as exc:
                K.log_err("tick failed: %s" % exc)

    def left_tv(self, now):
        """The viewer navigated away (Home button etc.) - our window is no longer
        on screen.  Kodi would otherwise keep this script alive in the background."""
        if not self.win_id:
            return False
        cur = xbmcgui.getCurrentWindowId()
        here = cur == self.win_id or (cur == 12005 and self.playing_ours())
        if here:
            self.away_since = 0
            return False
        if not self.away_since:
            self.away_since = now
        return now - self.away_since > 1.5

    def tick(self):
        now = time.time()
        if self.closing or not self.ch:
            return
        if self.left_tv(now):
            K.log("TV window left - switching CableBox off")
            self.shutdown()
            return
        if self.digits and now - self.digits_at > 1.8:
            self.commit_digits()
        if self.osd_until and now > self.osd_until:
            self.osd_until = 0
            self.setProperty("osd", "")
        if self.banner_until and now > self.banner_until:
            self.banner_until = 0
            self.setProperty("banner", "")
        if self.toast_until and now > self.toast_until:
            self.toast_until = 0
            self.setProperty("toast", "")
        if self.static_until and now > self.static_until and \
                (self.av_started_token == self.play_token or not self.is_video(self.cur_entry)
                 or now > self.static_until + 4):
            self.static_until = 0
            self.setProperty("static", "")
        if self.sleep_at and now > self.sleep_at:
            self.sleep_at = 0
            if K.setting_bool("sleep_cec", False):
                xbmc.executebuiltin("CECStandby")
            self.shutdown()
            return

        sched = self.lineup.schedule(self.ch)
        e = sched.entry_at(now)
        if e is None:
            if self.cur_key != "none":
                self.cur_key = "none"
                self.stop_player()
                self.set_mode("card")
                self.card(self.ch["name"], _("Please stand by"), "", "")
            return
        key = (self.ch["id"], e["s"])
        if key != self.cur_key:
            self.start_entry(e, key, now)
        elif key == self.failed_key:
            self.cover_failure(e, now)
        elif self.is_video(e):
            self.watchdog(e, key, now)
        if e["k"] == "guide":
            self.guide_tick(now)
        elif e["k"] == "weather":
            self.weather.tick(now)
        if self.banner_until:
            self.update_progress(now)

    @staticmethod
    def is_video(e):
        return bool(e) and e.get("k") in VIDEO_KINDS

    def start_entry(self, e, key, now):
        self.save_sub_position()
        self.cur_key = key
        self.cur_entry = e
        self.retries = 0
        kind = e["k"]
        if kind in VIDEO_KINDS:
            if key == self.failed_key:
                self.trouble()
                return
            if kind == "show" and (library.is_bad(e["p"]) or (self.sub and self.sub["for"] == e["p"])):
                # a programme already known not to open: go straight to the stand-in
                self.failed_key = key
                self.sub_at = 0
                self.play_substitute(e, now)
                return
            self.play(e, now)
            self.set_mode("video")
        else:
            if kind == "guide":
                self.set_mode("guide")
                self.guide_next = 0
                self.promo_next = 0
                self.scroll_top = 0
                self.scroll_next = now + 5.0
                self.guide_tick(now)
                self.background_audio(K.setting("guide_music_path"))
            elif kind == "weather":
                self.set_mode("weather")
                self.weather.tick(now, force=True)
                self.background_audio(K.setting("weather_music_path"))
            else:
                self.stop_player()
                if kind == "offair":
                    b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
                    resume = fmt_time(b["e"]) if b else ""
                    self.setProperty("offair_line", _("Programming resumes at %s") % resume)
                    self.setProperty("offair_style", e.get("sub") or "bars")
                    self.set_mode("offair")
                else:
                    self.card_for(e, now)
        if kind == "show":
            self.update_banner()

    def play(self, e, now):
        offset = max(0.0, float(e.get("o", 0)) + (now - e["s"]))
        li = xbmcgui.ListItem(label=e.get("t") or "", path=e["p"])
        try:
            tag = li.getVideoInfoTag()
            tag.setTitle(e.get("sub") or e.get("t") or "")
            tag.setTvShowTitle(e.get("t") or "")
        except Exception:
            pass
        if offset > 1.0:
            li.setProperty("StartOffset", "%.2f" % offset)
        self.play_token += 1
        self.play_started_at = time.time()
        self.our_files.add(e["p"])
        if e.get("k") in ("show", "clip"):
            self.progress.remember(e["p"])
        self.player.play(e["p"], li, True)

    def watchdog(self, e, key, now):
        """Detect files that never started or ended early."""
        if self.closing:
            return
        if time.time() - self.play_started_at < LOAD_TIMEOUT:
            return
        if self.player.isPlaying():
            return
        if self.av_started_token == self.play_token:
            # The file finished before its slot did.  A second or two of black
            # is normal between spots; anything longer gets commercials.
            if e["e"] - now < 4:
                return
            ads = self.channel_ads()
            if ads:
                fit = [a for a in ads if a["dur"] <= e["e"] - now] or ads
                a = random.choice(fit)
                self.play({"p": a["path"], "o": 0, "s": now, "t": a.get("title")}, now)
                self.set_mode("video")
            elif self.prop_mode != "card":
                self.card_for({"k": "card", "sub": "id"}, now)
            return
        self.retries += 1
        if self.retries <= 1:
            K.log("Retrying %s" % e.get("p"))
            self.play(e, now)
        else:
            self.failed_key = key
            self.give_up(e)

    # ----------------------------------------------------------- unplayable files
    @staticmethod
    def really_bad(path):
        """The file is there (or its folder is) but Kodi can't open it.  If the
        whole folder is gone, the drive or share is probably just offline -
        don't blacklist a library's worth of files for that."""
        try:
            if xbmcvfs.exists(path):
                return True
            folder = path.replace("\\", "/").rsplit("/", 1)[0] + "/"
            return bool(folder.strip("/")) and xbmcvfs.exists(folder)
        except Exception:
            return False

    def give_up(self, e):
        """Kodi couldn't open this.  'Technical difficulties' for a few
        seconds, then something else from the channel fills the time."""
        path = e.get("p") or ""
        K.log_err("Couldn't play %s" % path)
        if self.really_bad(path):
            library.mark_bad(path, _("Kodi couldn't open it"))
        self.trouble()
        self.sub = None
        self.sub_at = time.time() + 6 if e.get("k") == "show" else 0

    def cover_failure(self, e, now):
        """While a failed programme's time runs: keep a stand-in playing."""
        if e.get("k") != "show" or not self.sub_at and not self.sub:
            return
        if self.sub is None:
            if time.time() >= self.sub_at:
                self.play_substitute(e, now)
            return
        if self.player.isPlaying() or time.time() - self.play_started_at < LOAD_TIMEOUT:
            return
        # the stand-in ended (or failed too) before the slot did: another one
        self.sub = dict(self.sub, p=None, pos=0.0, tried=self.sub.get("tried", []) + [self.sub["p"]])
        self.play_substitute(e, now)

    def _substitute_pick(self, avoid, room):
        try:
            pool = library.resolve(self.ch.get("sources") or [])
        except Exception:
            return None
        items = [ep for ser in pool["series"] for ep in ser["episodes"]] + pool["singles"]
        items = [i for i in items if i["path"] not in avoid and not library.is_bad(i["path"])]
        if not items:
            return None
        long_enough = [i for i in items if i["dur"] >= room * 0.8]
        return random.choice(long_enough or items)

    def play_substitute(self, e, now):
        sub = self.sub
        if sub is None or not sub.get("p"):
            b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
            room = (b["e"] - now) if b else 1800
            avoid = {e["p"]} | ({sub["p"]} if sub and sub.get("p") else set()) | set((sub or {}).get("tried", []))
            it = self._substitute_pick(avoid, room)
            if it is None:
                self.sub = None
                self.sub_at = 0
                self.trouble()
                return
            sub = {"for": e["p"], "p": it["path"], "pos": 0.0, "t": it.get("title") or "",
                   "s": " ".join(x for x in (it.get("label"), it.get("sub")) if x),
                   "tried": list(avoid)}
        sub["started"] = time.time()
        sub["base"] = sub["pos"]
        self.sub = sub
        self.play({"k": "show", "p": sub["p"], "o": sub["pos"], "s": now, "t": sub["t"], "sub": sub["s"]}, now)
        self.set_mode("video")
        self.setProperty("now_title", sub["t"])
        self.setProperty("now_sub", sub["s"])

    def save_sub_position(self):
        """Leaving a stand-in for a commercial break: remember where it was."""
        if not self.sub or not self.sub.get("p") or "started" not in self.sub:
            return
        pos = self.sub.get("base", 0.0) + (time.time() - self.sub["started"])
        try:
            if self.player.isPlaying() and self.player.getPlayingFile() == self.sub["p"]:
                pos = self.player.getTime()
        except Exception:
            pass
        self.sub["pos"] = max(0.0, pos - 2)
        self.sub.pop("started", None)

    def channel_ads(self):
        if not self.ch or not self.ch.get("commercials"):
            return []
        return library.filler_pool(self.ch.get("commercials_path") or K.setting("commercials_path"))

    def trouble(self):
        self.stop_player()
        self.card(_("TECHNICAL DIFFICULTIES"), _("Please stand by"), "", "")
        self.set_mode("card")

    def stop_player(self):
        try:
            if self.player.isPlaying():
                self.player.stop()
        except Exception:
            pass
        self.progress.release()

    # player callbacks (other thread)
    def on_av_started(self):
        if self.closing or not self.playing_ours():
            return
        tok = self.play_token
        self.av_started_token = tok
        try:
            self.progress.release(keep=self.player.getPlayingFile())   # the file before this one
        except Exception:
            pass
        try:
            path = self.player.getPlayingFile()
            total = self.player.getTotalTime()
            if total:
                library.durations().learn(path, total)
        except Exception:
            pass

    def on_error(self):
        if self.closing:
            return
        self.play_started_at = 0  # let the watchdog react immediately

    # ----------------------------------------------------------- screens
    prop_mode = ""

    def set_mode(self, mode):
        self.prop_mode = mode
        self.setProperty("mode", mode)

    def card(self, kicker, title, sub, line):
        self.setProperty("card_kicker", kicker)
        self.setProperty("card_title", title)
        self.setProperty("card_sub", sub)
        self.setProperty("card_line", line)

    def card_for(self, e, now):
        sched = self.lineup.schedule(self.ch, ensure=False)
        nb = sched.next_block(now)
        sub = e.get("sub")
        if sub == "nosignal":
            self.card(self.ch["name"], _("No programming"), _("Add sources to this channel in the Channel Manager"), "")
        elif sub == "next" and nb:
            t = nb["t"] + (("  -  " + nb["sub"]) if nb.get("sub") else "")
            self.card(_("UP NEXT"), t, _("at %s") % fmt_time(nb["s"]), self.ch["name"])
        else:
            line = ""
            if nb:
                line = _("Coming up at %s: %s") % (fmt_time(nb["s"]), nb["t"])
            self.card(_("You're watching"), self.ch["name"], _("We'll be right back"), line)
        self.stop_player()
        self.set_mode("card")

    def show_digits(self, text):
        """'CH 03' style: at least two digits (leading zero), left-aligned after CH."""
        text = (text or "")[-3:]
        if text.isdigit():
            text = text.zfill(2)
        names = [("digits/%s.png" % ("u" if c == "_" else c)) for c in text]
        names = names + [""] * (3 - len(names))
        for i, n in enumerate(names):
            self.setProperty("d%d" % (i + 1), n)
        self.setProperty("osd", "1")
        self.osd_until = time.time() + 3.0

    def toast(self, text, secs=3.0):
        self.setProperty("toast", text)
        self.toast_until = time.time() + secs

    def toggle_banner(self):
        if self.banner_until:
            self.banner_until = 0
            self.setProperty("banner", "")
        else:
            self.update_banner()
            self.show_digits(str(self.ch["number"]))
            self.banner_until = time.time() + self.banner_secs
            self.setProperty("banner", "1")

    def update_banner(self):
        if not self.ch:
            return
        now = time.time()
        sched = self.lineup.schedule(self.ch, ensure=False)
        b = sched.block_at(now)
        if b:
            self.setProperty("now_title", b["t"])
            sub = " ".join(x for x in (b.get("lb", ""), b.get("sub", "")) if x)
            self.setProperty("now_sub", sub)
            self.setProperty("now_time", "%s - %s" % (fmt_time(b["s"]), fmt_time(b["e"])))
        else:
            for k in ("now_title", "now_sub", "now_time"):
                self.setProperty(k, "")
        nb = sched.next_block(now)
        self.setProperty("next_line", (_("Next: %s  %s") % (fmt_time(nb["s"]), nb["t"])) if nb else "")
        self.update_progress(now)

    def update_progress(self, now):
        b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
        try:
            ctl = self.getControl(30)
            if b and b["e"] > b["s"]:
                ctl.setPercent(100.0 * (now - b["s"]) / (b["e"] - b["s"]))
        except Exception:
            pass

    # ----------------------------------------------------------- guide channel
    def guide_tick(self, now):
        if now >= self.guide_next:
            self.fill_guide(now)
            self.guide_next = min(now + 300, scheduler.floor_slot(now, 1800) + 1801)
        if now >= self.promo_next and self.promos:
            self.setProperty("guide_promo", self.promos[0])
            self.promos = self.promos[1:] + self.promos[:1]
            self.promo_next = now + 8
        if now >= self.scroll_next:
            self.guide_scroll(now)

    GUIDE_ROWS = 7          # rows visible in the guide list (620 / 88)
    SCROLL_STEP = 2.5       # seconds per row
    SCROLL_HOLD = 5.0       # pause at the bottom (and top) before moving on

    def guide_scroll(self, now):
        """Scroll one row at a time; hold at the end, then jump back to the top."""
        try:
            lst = self.getControl(50)
            n = lst.size()
        except Exception:
            return
        last_top = max(0, n - self.GUIDE_ROWS)
        if last_top == 0:                      # everything fits - nothing to scroll
            self.scroll_next = now + 30
            return
        if self.scroll_top >= last_top:        # held at the bottom long enough
            self.scroll_top = 0
            lst.selectItem(0)
            self.scroll_next = now + self.SCROLL_HOLD
            return
        self.scroll_top += 1
        # selecting the row just below the screen pushes the view down by one
        lst.selectItem(min(n - 1, self.scroll_top + self.GUIDE_ROWS - 1))
        self.scroll_next = now + (self.SCROLL_HOLD if self.scroll_top >= last_top else self.SCROLL_STEP)

    def fill_guide(self, now):
        t0 = scheduler.floor_slot(now, 1800)
        cols = [t0, t0 + 1800, t0 + 3600]
        self.setProperty("guide_title", K.setting("guide_title", _("CableBox 42 Program Guide")))
        for i, c in enumerate(cols):
            self.setProperty("g_t%d" % (i + 1), fmt_time(c))
        items = []
        promos = []
        for n, ch in enumerate(self.lineup.channels):
            if ch["type"] == "guide":
                continue
            # never build schedules here - that froze the guide after upgrades
            sched = self.lineup.schedule(ch, ensure=False)
            li = xbmcgui.ListItem(str(ch["number"]), ch["name"])
            if sched.block_at(now) is None:
                self.guide_pending = True
                li.setProperty("c1", _("Updating listings..."))
                li.setProperty("rowbg", "guide_row_a.png" if n % 2 == 0 else "guide_row_b.png")
                items.append(li)
                continue
            for i, c in enumerate(cols):
                b = sched.block_at(c + 1)
                txt = ""
                if b:
                    txt = b["t"]
                    if b["s"] < c - 60 and i == 0:
                        txt = _("(cont.) ") + txt
                    elif b["s"] < c - 60:
                        txt = ">>> " + txt
                li.setProperty("c%d" % (i + 1), txt)
            li.setProperty("rowbg", "guide_row_a.png" if n % 2 == 0 else "guide_row_b.png")
            items.append(li)
            for b in sched.blocks_between(now, now + 4 * 3600):
                if b["s"] > now and b.get("k") == "show" and b["e"] - b["s"] >= 3600:
                    promos.append(_("Coming up at %s on %s %s:  %s") % (
                        fmt_time(b["s"]), ch["number"], ch["name"], b["t"]))
                    break
        try:
            lst = self.getControl(50)
            lst.reset()
            lst.addItems(items)
            # keep the scroll position across the 5-minute refresh
            self.scroll_top = min(self.scroll_top, max(0, len(items) - self.GUIDE_ROWS))
            if self.scroll_top:
                lst.selectItem(0)
                lst.selectItem(min(len(items) - 1, self.scroll_top + self.GUIDE_ROWS - 1))
        except Exception as exc:
            K.log_err("guide list: %s" % exc)
        random.shuffle(promos)
        if not promos:
            promos = [_("Thanks for watching CableBox 42"), _("Press OK to pick a channel")]
        self.promos = promos

    def background_audio(self, folder):
        if not folder:
            self.stop_player()
            return
        files = library.folder_files(folder, library.AUDIO_EXT)
        if not files:
            self.stop_player()
            return
        pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0))
        pl.clear()
        random.shuffle(files)
        for f in files[:50]:
            pl.add(f)
            self.our_files.add(f)
        self.play_token += 1
        self.play_started_at = time.time()
        self.player.play(pl, windowed=True)

    # ----------------------------------------------------------- dialogs
    def channel_list(self):
        now = time.time()
        rows = []
        for ch in self.lineup.channels:
            b = self.lineup.schedule(ch).block_at(now)
            what = b["t"] if b else ""
            rows.append(xbmcgui.ListItem("%3d  %s" % (ch["number"], ch["name"]),
                                         _("%s   (until %s)") % (what, fmt_time(b["e"])) if b else ""))
        cur = [c["id"] for c in self.lineup.channels].index(self.ch["id"]) if self.ch else 0
        i = xbmcgui.Dialog().select(_("What's on now"), rows, preselect=cur, useDetails=True)
        if i >= 0:
            self.tune(self.lineup.channels[i])

    def menu(self):
        opts = [_("What's on now"), _("Last channel"), _("Sleep timer"), _("Turn off TV")]
        b = self.lineup.schedule(self.ch, ensure=False).block_at(time.time()) if self.ch else None
        hide = b["t"] if b and b.get("k") == "show" else None
        if hide:
            opts.append(_("Don't air '%s' on %s") % (hide, self.ch["name"]))
        i = xbmcgui.Dialog().contextmenu(opts)
        if i == 4 and hide:
            self.hide_show(hide)
        elif i == 0:
            self.channel_list()
        elif i == 1 and self.prev_ch:
            self.tune(self.prev_ch)
        elif i == 2:
            mins = [0, 15, 30, 60, 90, 120]
            labels = [_("Off")] + [_("%d minutes") % m for m in mins[1:]]
            j = xbmcgui.Dialog().select(_("Sleep timer"), labels)
            if j >= 0:
                self.sleep_at = time.time() + mins[j] * 60 if mins[j] else 0
                self.toast(_("Sleep: %s") % labels[j], 3)
        elif i == 3:
            self.shutdown()


    def hide_show(self, title):
        """Remove a show from this channel right from the couch."""
        from . import channels as C
        chans = C.load()
        for c in chans:
            if c["id"] == self.ch["id"]:
                ex = c.setdefault("exclude", [])
                if title not in ex:
                    ex.append(title)
        C.save(chans)
        self.lineup.reload_channels()
        threading.Thread(target=self.lineup.refresh_assignment, name="cablebox42-assign").start()
        ch = self.lineup.by_number(self.ch["number"])
        self.toast(_("'%s' removed from %s") % (title, ch["name"]), 4)
        self.tune(ch)


def run(channel=None):
    K.ensure_dirs()
    win = TVWindow("script-cablebox42-tv.xml", K.ADDON_PATH, "Default", "1080i")
    win.wanted_channel = channel
    win.doModal()
    win.shutdown()
    del win

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

from . import kodiutil as K
from . import library
from . import scheduler
from . import weather
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

VIDEO_KINDS = ("show", "ad", "bump")
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
        self.digits = ""
        self.digits_at = 0
        self.osd_until = 0
        self.banner_until = 0
        self.static_until = 0
        self.toast_until = 0
        self.sleep_at = 0
        self.guide_next = 0
        self.promo_next = 0
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

    # ----------------------------------------------------------- lifecycle
    def onInit(self):
        if self.started:
            return
        self.started = True
        xbmcgui.Window(10000).setProperty("cablebox42.running", "1")
        xbmc.executebuiltin("InhibitScreensaver(true)")
        if not self.lineup.channels:
            self.set_mode("card")
            self.card("CableBox 42", _("No channels yet"), _("Open the add-on and choose 'Build my lineup'"), "")
            return
        start = self.start_channel()
        self.tune(start, static=True)
        threading.Thread(target=self.loop, name="cablebox42-loop").start()

    def start_channel(self):
        state = K.load_json(K.STATE_FILE, {})
        fixed = K.setting_int("start_channel", 0)
        want = fixed or state.get("last_channel")
        ch = self.lineup.by_number(int(want)) if want else None
        if not fixed and state.get("last_channel_id"):
            # follow the channel itself, even if it was renumbered since
            ch = next((c for c in self.lineup.channels if c["id"] == state["last_channel_id"]), ch)
        return ch or self.lineup.channels[0]

    def shutdown(self):
        if self.closing:
            return
        self.closing = True
        if self.ch:
            st = K.load_json(K.STATE_FILE, {})
            st["last_channel"] = self.ch["number"]
            st["last_channel_id"] = self.ch["id"]
            K.save_json(K.STATE_FILE, st)
        try:
            self.player.stop()
        except Exception:
            pass
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

    def tick(self):
        now = time.time()
        if self.closing or not self.ch:
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
        self.cur_key = key
        self.cur_entry = e
        kind = e["k"]
        if kind in VIDEO_KINDS:
            if key == self.failed_key:
                self.trouble()
                return
            self.play(e, now)
            self.set_mode("video")
        else:
            if kind == "guide":
                self.set_mode("guide")
                self.guide_next = 0
                self.promo_next = 0
                self.guide_tick(now)
                self.background_audio(self.guide_music)
            elif kind == "weather":
                self.set_mode("weather")
                self.weather.tick(now, force=True)
                self.background_audio(self.weather_music)
            else:
                self.stop_player()
                if kind == "offair":
                    b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
                    resume = fmt_time(b["e"]) if b else ""
                    self.setProperty("offair_line", _("Programming resumes at %s") % resume)
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
        self.player.play(e["p"], li, True)

    def watchdog(self, e, key, now):
        """Detect files that never started or ended early."""
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
            self.trouble()

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

    # player callbacks (other thread)
    def on_av_started(self):
        tok = self.play_token
        self.av_started_token = tok
        try:
            path = self.player.getPlayingFile()
            total = self.player.getTotalTime()
            if total:
                library.durations().learn(path, total)
        except Exception:
            pass

    def on_error(self):
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
        text = (text or "")[-3:]
        names = [("digits/%s.png" % ("u" if c == "_" else c)) for c in text]
        names = [""] * (3 - len(names)) + names
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
            sched = self.lineup.schedule(ch)
            li = xbmcgui.ListItem(str(ch["number"]), ch["name"])
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
        ch = self.lineup.by_number(self.ch["number"])
        self.toast(_("'%s' removed from %s") % (title, ch["name"]), 4)
        self.tune(ch)


def run():
    K.ensure_dirs()
    win = TVWindow("script-cablebox42-tv.xml", K.ADDON_PATH, "Default", "1080i")
    win.doModal()
    win.shutdown()
    del win

"""The TV set: full-screen window, remote handling and the playout loop.

Playback is plain xbmc.Player (windowed into our videowindow control), so on
every device each file goes through the same hardware decoder as it
does when you play it from the library.
"""
import os
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
from . import logos
from . import stations
from . import captions
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
CC_TOGGLE = {_a("ACTION_SHOW_SUBTITLES", 25)}      # the remote's CC / subtitles button
CC_NEXT = {_a("ACTION_NEXT_SUBTITLE", 26), _a("ACTION_CYCLE_SUBTITLE", 99)}
CC_MENU = {_a("ACTION_BROWSE_SUBTITLE", 247)}
# (Kodi's default keymaps send these in its own full-screen player only:
#  Settings > Tools > Remote CC button maps the remote's subtitle key for CableBox)
DIGITS = dict((58 + i, i) for i in range(10))
DIGITS.update(dict((140 + i, i) for i in range(2, 10)))  # JUMP_SMS2..9 numeric keypads

VIDEO_KINDS = ("show", "ad", "bump", "clip")
LOAD_TIMEOUT = 12.0
STATIC_HOLD = 0.55     # Windows: seconds of the static clip before the new channel comes in
STATIC_CLIP_WAIT = 2.0  # ...or this long if the clip never starts
POWER_ON_LEN = 3.5      # the TV warming up, with the CableBox 42 title card
POWER_OFF_LEN = 1.4     # the picture shrinking to a dot
POWER_OFF_SETTLE_MS = 250   # Kodi's audio output reopening after the programme stops
# (both start with a few tenths of a second of picture and no sound: Windows
# swallows the start of the sound while it reopens its audio device)


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


FULLSCREEN = 12005               # Kodi's own full-screen video window


class Overlay(xbmcgui.WindowXMLDialog):
    """CableBox's overlays over Kodi's full-screen player (captions mode).
    Kodi gives every button to the topmost dialog, so the remote keeps working
    exactly as in the TV window - and the full-screen player's own keys
    (seeking, its OSD) never fire."""
    owner = None

    def onAction(self, action):
        if self.owner:
            self.owner.onAction(action)


class TVWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super(TVWindow, self).__init__(*args, **kwargs)
        self.lineup = scheduler.Lineup(K.schedule_cfg())
        self.player = Player(self)
        self.cc = captions.Captions(self.player)
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
        self.hold_until = 0
        self.toast_until = 0
        self.careful_static = use_static_clip()
        self.gui_sounds = GuiSounds()
        self.sleep_at = 0
        self.guide_next = 0
        self.promo_next = 0
        self.scroll_top = 0          # first guide row on screen
        self.scroll_next = 0
        self.promos = []
        self.closing = False
        self.started = False
        self.power_on = False        # the turn-on clip is playing
        self.lock = threading.RLock()
        self.banner_secs = K.setting_int("banner_secs", 6)
        self.static_on = K.setting_bool("static_effect", True)
        self.static_sound = K.setting_bool("static_sound", True)
        self.guide_music = K.setting("guide_music_path")
        self.weather_music = K.setting("weather_music_path")
        self.weather = weather.WeatherScreen(self)
        self.progress = progress.Guard()     # put the viewer's resume points back afterwards
        self.progress.release(delay=0.5)     # anything a crash left behind
        self.win_id = None
        self.guide_pending = False
        self.away_since = 0
        self.our_files = set()
        self.aliases = {}            # name Kodi plays a file under -> the path we asked for
        self.pending_play = None     # (path, when) of our last play() until its picture is on
        # captions mode: programmes in Kodi's full-screen player, our overlay on top
        self.cc_fullscreen = K.setting_bool("cc_fullscreen", True)
        self.overlay = None
        self.fs_state = "off"        # off / entering / on
        self.fs_at = 0
        self.fs_retry_at = 0

    _props = None

    def setProperty(self, key, value):
        """Every window property also goes to the overlay, so the banner, CH
        number, logo, static and CRT look the same in either window."""
        super(TVWindow, self).setProperty(key, value)
        if self._props is None:
            self._props = {}
        self._props[key] = value
        ov = self.overlay
        if ov is not None and self.fs_state == "on":
            try:
                ov.setProperty(key, value)
            except Exception:
                pass

    # ----------------------------------------------------------- lifecycle
    def onInit(self):
        if self.started:
            return
        self.started = True
        self.win_id = xbmcgui.getCurrentWindowId()
        xbmcgui.Window(10000).setProperty("cablebox42.running", "1")
        crt = K.setting_int("crt_mode", 0)   # 0 off, 1 subtle, 2 full
        self.setProperty("crt", str(crt) if crt in (1, 2) else "")
        if self.cc_fullscreen:
            # made here, on the script's main thread, so its button callbacks are delivered
            try:
                self.overlay = Overlay("script-cablebox42-overlay.xml", K.ADDON_PATH, "Default", "1080i")
                self.overlay.owner = self
            except Exception as exc:
                K.log_err("overlay: %s" % exc)
                self.overlay = None
        xbmc.executebuiltin("InhibitScreensaver(true)")
        if not self.careful_static:          # our sounds are interface sounds: on for the whole session
            self.gui_sounds.start()
        if not self.lineup.channels:
            self.set_mode("card")
            self.card("CableBox 42", _("No channels yet"), _("Open the add-on and choose 'Build my lineup'"), "")
            return
        start = self.start_channel()
        power = K.setting_bool("power_effect", True)
        if power:
            self.play_power_on()
        self.tune(start, static=not power)
        if not power:
            self.first_tip()
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

    def shutdown(self, power_off=False):
        """Switch CableBox off.  power_off: the viewer turned the TV off (not
        Kodi closing or the window being left), so play the turn-off clip."""
        if self.closing:
            return
        self.closing = True
        if self.ch:
            st = K.load_json(K.STATE_FILE, {})
            st["last_channel"] = self.ch["number"]
            st["last_channel_id"] = self.ch["id"]
            K.save_json(K.STATE_FILE, st)
        self.cc.leave()                  # the file's own caption state back before Kodi saves it
        self.fs_leave(wait=True)         # the turn-off and everything after happen in the TV window
        stopped = time.time()            # when the programme stopped playing
        self.clear_music()               # or Kodi carries on with the guide's music afterwards
        if power_off and K.setting_bool("power_effect", True):
            stopped = self.play_power_off() or stopped
        self.gui_sounds.stop()               # the viewer's own interface sound setting back
        if self.playing_ours():
            try:
                self.player.stop()
            except Exception:
                pass
        xbmc.executebuiltin("InhibitScreensaver(false)")
        xbmcgui.Window(10000).clearProperty("cablebox42.running")
        self.close()                     # back to Kodi straight away; the tidying up follows
        if self.progress.pending:
            # let Kodi write its resume point first, then undo it
            wait = 2.5 - (time.time() - stopped)
            if wait > 0:
                xbmc.sleep(int(wait * 1000))
            self.progress.release_now()
        if self.playing_ours():          # anything of ours that started up again
            try:
                self.player.stop()
            except Exception:
                pass
        self.overlay = None
        library.durations().save()

    # ----------------------------------------------------------- remote
    def onAction(self, action):
        aid = action.getId()
        if self.power_on and aid not in EXIT:
            self.end_power_on()          # any button skips the turn-on
            return
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
            self.shutdown(power_off=True)     # straight off, no "are you sure?"
        elif aid in VOL_UP:
            K.rpc("Application.SetVolume", {"volume": "increment"})
        elif aid in VOL_DOWN:
            K.rpc("Application.SetVolume", {"volume": "decrement"})
        elif aid in MUTE:
            K.rpc("Application.SetMute", {"mute": "toggle"})
        elif aid in CC_MENU:
            self.cc_menu()
        elif aid in CC_TOGGLE or aid in CC_NEXT:
            if self.programme_on():
                self.toast(self.cc.toggle() if aid in CC_TOGGLE else self.cc.next_track(), 3)
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
            if static and self.power_on:     # changing channel cuts the turn-on short
                self.power_on = False
                self.hold_until = 0
            if self.ch and ch["id"] != self.ch["id"]:
                self.prev_ch = self.ch
            self.cc.leave()                  # before the static clip replaces the programme
            self.ch = ch
            self.cur_key = None
            self.failed_key = None
            self.retries = 0
            self.sub = None
            self.sub_at = 0
            if not self.power_on:
                self.show_digits(str(ch["number"]))
            self.setProperty("ch_number", str(ch["number"]))
            self.set_logo(ch)
            if static and self.static_on and self.static_sound and self.careful_static:
                # Windows resets its audio device whenever a video starts or
                # stops, which swallows Kodi's interface sounds - so there the
                # static is a short video clip with its own sound, played through
                # the player like any programme.  The new channel follows it.
                self.play_static_clip()
            elif static and self.static_on:
                self.setProperty("static", "1")
                self.static_until = time.time() + 0.45
                if self.static_sound:
                    xbmc.playSFX(K.media("static.wav"), False)
            self.lineup.schedule(ch)
            self.tick()
            self.update_banner()
            if not self.power_on:            # after the turn-on clip instead
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

    fs_since = 0
    fs_pulled = 0

    def hide_busy_wheel(self, now):
        """A TV never shows a loading spinner: while a channel is coming in,
        close Kodi's busy wheel if it pops up (slow drive, screen recording...)."""
        if now - self.play_started_at > 4:
            return
        try:
            for dlg in ("busydialog", "busydialognocancel"):
                if xbmc.getCondVisibility("Window.IsActive(%s)" % dlg):
                    xbmc.executebuiltin("Dialog.Close(%s,true)" % dlg)
        except Exception:
            pass

    def pull_back_from_fullscreen(self, now):
        """Kodi sometimes switches our video to its own full-screen player (a key
        like Tab or Enter, or on its own when a new video starts).  There the
        arrows seek and the OSD opens - not live TV.  Bring the picture back
        into the TV window."""
        if self.fs_state != "off" or self.fs_wanted():
            return                       # full screen on purpose, for the captions
        try:
            fullscreen = xbmcgui.getCurrentWindowId() == 12005 and self.playing_ours()
        except Exception:
            return
        if not fullscreen:
            self.fs_since = 0
            return
        if not self.fs_since:
            self.fs_since = now
        if now - self.fs_pulled < 1:
            return
        self.fs_pulled = now
        K.log("Kodi went full screen - back to the TV window")
        xbmc.executebuiltin("Dialog.Close(seekbar,true)")
        xbmc.executebuiltin("Dialog.Close(videoosd,true)")
        xbmc.executebuiltin("Action(FullScreen)")
        # Up/Down skip through the video in Kodi's full-screen player: put the
        # programme back where the schedule says it is (live TV can't be skipped).
        if not self.hold_until and self.is_video(self.cur_entry) and self.cur_key != self.failed_key:
            self.cur_key = None

    # ----------------------------------------------------------- captions mode
    # On most TV boxes (CoreELEC/Amlogic, Android, Raspberry Pi) the video sits
    # on its own hardware layer and Kodi draws subtitles only in its full-screen
    # player, never in an add-on's video window.  So while captions are on, our
    # videos go full screen with the Overlay dialog on top: same picture, same
    # banner and buttons - and Kodi draws the captions.
    FS_ENTER_TIMEOUT = 3.0
    FS_RETRY = 5.0
    av_started_at = 0

    def fs_wanted(self):
        # captions on - or any subtitle on screen: Blu-ray rips switch on a 'forced'
        # track for foreign-language scenes by themselves, and those need it too
        if not (self.cc_fullscreen and self.overlay is not None and (self.cc.on or self.cc.showing)):
            return False
        if self.closing or self.power_on or self.prop_mode != "video":
            return False
        # programmes only: commercials and bumps carry no captions, and each switch
        # into full screen is a chance for the display to change mode
        if not (self.cur_entry and self.cur_entry.get("k") in ("show", "clip")):
            return False
        try:
            return self.playing_ours() and self.player.isPlayingVideo()
        except Exception:
            return False

    def fullscreen_tick(self, now):
        if self.overlay is None:
            return
        try:
            cur = xbmcgui.getCurrentWindowId()
        except Exception:
            return
        want = self.fs_wanted()
        if self.fs_state == "on":
            if cur != FULLSCREEN:
                self.fs_leave(exit_fullscreen=False)   # Kodi went back by itself (video stopped)
            elif not want:
                self.fs_leave()
            return
        if self.fs_state == "entering":
            if cur == FULLSCREEN:
                self.fs_show_overlay()
            elif now - self.fs_at > self.FS_ENTER_TIMEOUT:
                K.log("Captions mode: Kodi's full-screen player didn't open - trying again shortly",
                      xbmc.LOGINFO)
                self.fs_state = "off"
                self.fs_retry_at = now + self.FS_RETRY
            return
        if not want or now < self.fs_retry_at:
            return
        if cur == FULLSCREEN:                # Kodi went full screen on its own: keep it
            self.fs_show_overlay()
            return
        # only once the picture is on: while a file opens, Kodi's loading dialog
        # is up and Kodi would refuse the switch (with its error beep)
        if self.av_started_token != self.play_token or now - self.av_started_at < 0.5:
            return
        # Kodi's skin shows its seek bar in the full-screen player for 3 s after a
        # jump (starting partway in, the CoreELEC rewind): wait until it's past
        if self.cc.nudge_at or xbmc.getCondVisibility("Player.Seeking | Player.HasPerformedSeek(3)"):
            return
        if cur != self.win_id or xbmc.getCondVisibility("System.HasModalDialog"):
            return                           # a menu is open: Kodi would refuse (and beep)
        self.fs_state = "entering"
        self.fs_at = now
        xbmc.executebuiltin("ActivateWindow(fullscreenvideo)", True)
        if xbmcgui.getCurrentWindowId() == FULLSCREEN:
            self.fs_show_overlay()           # straight away, no tick in between
        elif xbmc.getCondVisibility("System.HasModalDialog"):
            self.fs_state = "off"            # something popped up just then: try again shortly
            self.fs_retry_at = now + 1.0

    def fs_show_overlay(self):
        ov = self.overlay
        for k, v in list((self._props or {}).items()):
            try:
                ov.setProperty(k, v)
            except Exception:
                pass
        try:
            ov.show()
        except Exception as exc:
            K.log_err("overlay: %s" % exc)
            self.fs_state = "entering"       # so fs_leave takes us out of full screen
            self.fs_leave()
            self.fs_retry_at = time.time() + 60
            return
        self.fs_state = "on"
        K.log("Captions mode: video in Kodi's full-screen player, CableBox overlay on top", xbmc.LOGINFO)
        if self.banner_until:
            self.update_progress(time.time())

    def fs_leave(self, exit_fullscreen=True, wait=False):
        """Back to the TV window.  The overlay closes first: while it's open,
        Kodi would hand it the 'back to the menus' action meant for the
        full-screen player.  Without exit_fullscreen the caller is about to stop
        the video, and Kodi goes back to the TV window by itself."""
        state, self.fs_state = self.fs_state, "off"
        if state == "off":
            return
        if state == "on" and self.overlay is not None:
            try:
                self.overlay.close()
            except Exception as exc:
                K.log_err("overlay close: %s" % exc)
        self.fs_retry_at = time.time() + 1.0
        if not exit_fullscreen:
            return
        try:
            if xbmcgui.getCurrentWindowId() != FULLSCREEN:
                return
            # synchronous, so it can't arrive after we're back (in the TV window
            # this action is the Menu button)
            xbmc.executebuiltin("Action(FullScreen)", True)
            if wait:
                for _i in range(20):
                    if xbmcgui.getCurrentWindowId() != FULLSCREEN:
                        break
                    xbmc.sleep(50)
        except Exception as exc:
            K.log_err("leaving full screen: %s" % exc)

    def tick(self):
        now = time.time()
        if self.closing or not self.ch:
            return
        if self.left_tv(now):
            K.log("TV window left - switching CableBox off")
            self.shutdown()
            return
        self.pull_back_from_fullscreen(now)
        self.gui_sounds.tick(now)
        if self.cc.nudge_at and self.fs_state != "off":
            self.fs_leave()                  # the 1 s rewind in the TV window: no seek bar
        self.cc.tick(now)
        note = self.cc.take_note()           # captions switched from Yatse, Kodi's menus...
        if note:
            self.toast(note, 3)
        # 'CC' in the banner, like a 90s TV listing: this programme has captions
        mark = "1" if self.cc.has_cc and self.cur_entry and self.cur_entry.get("k") == "show" else ""
        if mark != self.getProperty("now_cc"):
            self.setProperty("now_cc", mark)
        self.fullscreen_tick(now)
        if now - self.brand_checked > 20:          # a branding block may have started (CAM Jr. -> Chameleon)
            self.brand_checked = now
            br = stations.brand(self.ch, now)
            if (self.ch.get("id"), br["name"], br["logo"]) != self.brand_key:
                self.set_logo(self.ch, keep_bug=True)
        self.hide_busy_wheel(now)
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
        if self.static_until and now > self.static_until and not self.hold_until and \
                (self.av_started_token == self.play_token or not self.is_video(self.cur_entry)
                 or now > self.static_until + 4):
            self.static_until = 0
            self.setProperty("static", "")
        if self.sleep_at and now > self.sleep_at:
            self.sleep_at = 0
            if K.setting_bool("sleep_cec", False):
                xbmc.executebuiltin("CECStandby")
            self.shutdown(power_off=True)
            return

        if self.hold_until:
            if now < self.hold_until:
                return
            self.hold_until = 0
        if self.power_on:
            self.end_power_on()
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

    brand_key = None
    brand_checked = 0

    def set_logo(self, ch, keep_bug=False):
        """Name, call letters and logo for the banner and corner bug - the station's
        branding for this time of day (CAM Jr. in the morning, Cam O Nite at night)."""
        br = stations.brand(ch)
        self.brand_key = (ch.get("id"), br["name"], br["logo"])
        self.setProperty("ch_name", br["name"])
        self.setProperty("ch_call", br["call"] or "")
        path = br["logo"] or logos.logo_for(ch)
        on, corner, opacity = logos.bug_settings()
        was_on = self.getProperty("bug") == "1"
        self.bug_on = bool(path) and on
        self.setProperty("bug", "1" if (keep_bug and was_on and self.bug_on) else "")
        self.setProperty("bug_logo", path if self.bug_on else "")
        self.setProperty("bug_corner", corner)
        self.setProperty("bug_alpha", str(opacity))
        self.setProperty("banner_logo", path if K.setting_bool("logo_banner", True) else "")

    def show_bug(self, on):
        """The corner logo shows during programmes only - never over commercials,
        bumps, station IDs, cards or the guide, just like the real networks."""
        self.setProperty("bug", "1" if on and getattr(self, "bug_on", False) else "")

    def start_entry(self, e, key, now):
        self.cc.leave()
        if e.get("k") not in VIDEO_KINDS:
            self.fs_leave()                  # guide, weather and cards live in the TV window
        self.save_sub_position()
        self.cur_key = key
        self.cur_entry = e
        self.show_bug(e.get("k") == "show")
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
        self.clear_music()
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
            # starting partway in is a jump, and Kodi's skin shows its seek bar for
            # 3 s after any jump in its full-screen player: do it in the TV window
            self.fs_leave()
        self.play_token += 1
        self.play_started_at = time.time()
        self.our_files.add(e["p"])
        self.pending_play = (e["p"], time.time())
        if e.get("k") in ("show", "clip"):
            self.progress.remember(e["p"])
        self.play_video(e["p"], li)

    def play_video(self, path, li):
        """Every video of ours goes through Kodi's video playlist (one item, in the
        TV window).  That makes the video playlist Kodi's current one, so Kodi
        reports our programme as the video player (id 1).  Played as a single
        file right after the guide's or weather's music, Kodi kept the music
        playlist current and reported the video under the music player's id 0 -
        where phone remotes (Yatse, Kore) and CableBox's own track details found
        no subtitles or audio tracks at all."""
        pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1))
        pl.clear()
        pl.add(path, li)
        self.player.play(pl, windowed=True)

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
        self.show_bug(True)
        self.setProperty("now_title", sub["t"])
        self.setProperty("now_sub", sub["s"])

    def save_sub_position(self):
        """Leaving a stand-in for a commercial break: remember where it was."""
        if not self.sub or not self.sub.get("p") or "started" not in self.sub:
            return
        pos = self.sub.get("base", 0.0) + (time.time() - self.sub["started"])
        try:
            if self.player.isPlaying() and self.requested(self.player.getPlayingFile()) == self.sub["p"]:
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
        self.show_bug(False)
        self.stop_player()
        self.card(_("TECHNICAL DIFFICULTIES"), _("Please stand by"), "", "")
        self.set_mode("card")

    STATIC_CLIP = K.media("static_clip.mp4")

    def play_static_clip(self):
        clip = self.STATIC_CLIP
        self.play_token += 1
        self.play_started_at = time.time()
        self.our_files.add(clip)
        self.set_mode("video")
        self.hold_until = time.time() + STATIC_CLIP_WAIT   # shortened once the clip is on screen
        try:
            self.play_video(clip, xbmcgui.ListItem(path=clip))
        except Exception as exc:
            K.log_err("static clip: %s" % exc)
            self.hold_until = 0

    POWER_ON = K.media("power_on.mp4")
    POWER_OFF = K.media("power_off.mp4")

    def play_power_on(self):
        clip = self.POWER_ON
        self.power_on = True
        self.play_token += 1
        self.play_started_at = time.time()
        self.our_files.add(clip)
        self.set_mode("video")
        self.hold_until = time.time() + POWER_ON_LEN + 2.5   # shortened once the clip is on screen
        try:
            self.play_video(clip, xbmcgui.ListItem(path=clip))
        except Exception as exc:
            K.log_err("power-on clip: %s" % exc)
            self.end_power_on()

    def end_power_on(self):
        """The TV has warmed up: the first channel comes in, with its banner."""
        if not self.power_on:
            return
        self.power_on = False
        self.hold_until = 0
        if self.ch:
            self.show_digits(str(self.ch["number"]))
            self.update_banner()
            self.banner_until = time.time() + self.banner_secs
            self.setProperty("banner", "1")
        self.first_tip()

    def first_tip(self):
        """The first time the TV is switched on: where captions and the rest live."""
        try:
            st = K.load_json(K.STATE_FILE, {})
            if st.get("tip_menu"):
                return
            st["tip_menu"] = 1
            K.save_json(K.STATE_FILE, st)
            self.toast(_("Press Menu for captions, sleep timer and more"), 6)
        except Exception as exc:
            K.log_err("tip: %s" % exc)

    def play_power_off(self):
        """Returns when the programme actually stopped (quick turn-off), or None."""
        if not use_static_clip():
            # Kodi switching the TV's refresh rate for a new video blanks the
            # screen for a second or two (common on CoreELEC), which would hide
            # a clip: draw the turn-off over the picture instead, sound as an
            # interface sound - the same choice as for the static.
            #
            # Kodi mixes interface sounds into a *playing* programme's audio, or
            # into silence when no programme is open at all.  While a programme
            # is only paused there is nothing to mix into: the sound is held
            # back, then leaks out late or is thrown away when the player stops
            # (the silent turn-off).  So: pause for instant silence (no bleed),
            # start the effect, stop the programme, and play the sound once Kodi
            # has let go of the programme's audio.
            self.clear_overlays()
            try:
                if self.playing_ours() and not xbmc.getCondVisibility("Player.Paused"):
                    self.player.pause()
            except Exception:
                pass
            self.setProperty("poweroff", "1")    # the flash hides the picture going away
            stopped = self.release_audio()
            try:
                xbmc.playSFX(K.media("power_off.wav"), False)
            except Exception:
                pass
            xbmc.sleep(1100)
            return stopped
        clip = self.POWER_OFF
        self.our_files.add(clip)
        self.clear_overlays()
        self.set_mode("video")
        t0 = time.time()
        try:
            self.play_video(clip, xbmcgui.ListItem(path=clip))
        except Exception as exc:
            K.log_err("power-off clip: %s" % exc)
            return
        started = None
        while time.time() - t0 < 2.0 + POWER_OFF_LEN:
            xbmc.sleep(50)
            try:
                on = self.player.isPlaying() and os.path.basename(self.player.getPlayingFile()) == "power_off.mp4"
            except Exception:
                on = False
            if on and started is None:
                started = time.time()
            elif started is not None and (not on or time.time() - started > POWER_OFF_LEN):
                break                    # finished
            elif started is None and time.time() - t0 > 2.0:
                break                    # never started: don't keep the viewer waiting
        K.log("Turn-off clip: started after %s s, %.1f s in all" %
              ("%.1f" % (started - t0) if started else "-", time.time() - t0))

    def release_audio(self, limit=2.0):
        """Stop our programme and wait until Kodi has closed its audio, so an
        interface sound played next is heard.  Returns when it stopped."""
        t0 = time.time()
        try:
            if not self.playing_ours():
                return t0
            self.player.stop()
        except Exception:
            return t0
        while time.time() - t0 < limit:
            try:
                if not self.player.isPlaying():
                    break
            except Exception:
                break
            xbmc.sleep(20)
        stopped = time.time()
        # Kodi reopens its audio output for interface sounds just after the
        # player reports stopped; a sound sent in that moment loses its start
        xbmc.sleep(POWER_OFF_SETTLE_MS)
        K.log("Turn-off: programme audio released after %.2f s" % (stopped - t0))
        return stopped

    def clear_music(self):
        """Empty the music playlist the guide and weather music play from."""
        try:
            xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0)).clear()
        except Exception:
            pass

    def stop_player(self):
        self.cc.leave()
        self.fs_leave(exit_fullscreen=False)   # Kodi returns to the TV window when the video stops
        try:
            if self.player.isPlaying():
                self.player.stop()
        except Exception:
            pass
        self.progress.release()

    def requested(self, playing):
        """The path we asked Kodi to play, for the name Kodi says it's playing."""
        return self.aliases.get(playing, playing)

    def adopt_playing(self):
        """Kodi reports some files under another name than the one we asked for:
        disc images and Blu-ray folders (udf://, bluray://), .strm files, some
        network paths.  When our own play() has just started, remember that name,
        or the programme would look like someone else's video - no captions, no
        full screen, no 'picture is on' for the static or the durations."""
        pp, self.pending_play = self.pending_play, None
        if not pp:
            return
        try:
            actual = self.player.getPlayingFile()
        except Exception:
            return
        if actual in self.our_files or time.time() - pp[1] > LOAD_TIMEOUT + 5:
            return
        self.our_files.add(actual)
        self.aliases[actual] = pp[0]
        K.log("Kodi plays %s as %s" % (pp[0], actual), xbmc.LOGINFO)

    # player callbacks (other thread)
    def on_av_started(self):
        if not self.closing:
            self.adopt_playing()
        if self.closing or not self.playing_ours():
            return
        tok = self.play_token
        self.av_started_token = tok
        self.av_started_at = time.time()
        try:
            if self.hold_until and self.player.getPlayingFile() == self.STATIC_CLIP:
                self.hold_until = time.time() + STATIC_HOLD     # the static is on screen now
                return
            if self.power_on and self.player.getPlayingFile() == self.POWER_ON:
                self.hold_until = time.time() + POWER_ON_LEN - 0.1
                return
        except Exception:
            pass
        try:
            actual = self.player.getPlayingFile()
        except Exception:
            actual = ""
        path = self.requested(actual)
        try:
            self.progress.release(keep=path)   # the file before this one
        except Exception:
            pass
        try:
            total = self.player.getTotalTime()
            if total and path:
                library.durations().learn(path, total)
        except Exception:
            pass
        if path and path == self.programme_path():
            self.cc.started(actual)      # captions as the viewer left them, on the next tick
        elif path and self.cur_entry and self.cur_entry.get("k") == "show":
            K.log("Captions: playing %s but the programme on now is %s - not treated as the programme"
                  % (actual, self.programme_path()), xbmc.LOGINFO)

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

    def clear_overlays(self):
        """Nothing over the picture: banner, corner logo, static, toast and the
        CH number (show_digits would switch the CH display back on)."""
        self.osd_until = self.banner_until = self.toast_until = self.static_until = 0
        for prop in ("banner", "bug", "static", "toast", "osd", "d1", "d2", "d3"):
            self.setProperty(prop, "")

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
        if not (b and b["e"] > b["s"]):
            return
        pct = 100.0 * (now - b["s"]) / (b["e"] - b["s"])
        wins = [self] + ([self.overlay] if self.overlay is not None and self.fs_state == "on" else [])
        for w in wins:
            try:
                w.getControl(30).setPercent(pct)
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
            li = xbmcgui.ListItem(str(ch["number"]), stations.brand(ch, now)["name"])
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

    def programme_path(self):
        """The file of the programme on now: the scheduled show, or the stand-in
        airing in its place when the show couldn't be opened."""
        e = self.cur_entry
        if not (e and e.get("k") == "show"):
            return None
        if self.sub and self.sub.get("p") and self.cur_key == self.failed_key:
            return self.sub["p"]
        return e.get("p")

    def programme_on(self):
        """A show or movie (not a commercial, bump or card) is playing right now."""
        path = self.programme_path()
        if not (path and self.playing_ours()):
            return False
        try:
            return self.requested(self.player.getPlayingFile()) == path
        except Exception:
            return False

    def log_no_cc(self):
        """Why the menu has no captions entry right now (for the log)."""
        try:
            playing = self.player.getPlayingFile() if self.player.isPlaying() else ""
        except Exception:
            playing = ""
        e = self.cur_entry or {}
        K.log("Captions: no menu entry - on now: %s %s | playing: %s (as %s) | ours: %s" % (
            e.get("k"), self.programme_path(), playing, self.requested(playing), self.playing_ours()),
            xbmc.LOGINFO)

    def cc_menu(self):
        if not self.programme_on():          # still on after the menu was open a while
            return
        try:
            actual = self.player.getPlayingFile()
        except Exception:
            return
        # captions work with the name Kodi plays under; 'load a file' starts in the programme's folder
        note = self.cc.menu(actual, self.programme_path())
        if note:
            self.toast(note, 3)
        if self.cc.take_resync() and self.cur_key != self.failed_key:
            self.cur_key = None              # Kodi paused it for the search: back to where the schedule is

    def menu(self):
        opts = [("now", _("What's on now")), ("last", _("Last channel"))]
        cc_on = self.cc.on is True
        # the TV's CC setting: always here, flips captions for every programme
        opts.append(("cc", _("Closed captions: %s") % (_("On") if cc_on else _("Off"))))
        if self.programme_on():
            opts.append(("ccopts", _("Caption options...")))
        else:
            self.log_no_cc()
        opts += [("sleep", _("Sleep timer")), ("off", _("Turn off TV"))]
        b = self.lineup.schedule(self.ch, ensure=False).block_at(time.time()) if self.ch else None
        hide = b["t"] if b and b.get("k") == "show" else None
        if hide:
            opts.append(("hide", _("Don't air '%s' on %s") % (hide, self.ch["name"])))
        i = xbmcgui.Dialog().contextmenu([o[1] for o in opts])
        if i < 0:
            return
        key = opts[i][0]
        if key == "hide":
            self.hide_show(hide)
        elif key == "now":
            self.channel_list()
        elif key == "last" and self.prev_ch:
            self.tune(self.prev_ch)
        elif key == "cc":
            self.toast(self.cc.switch(not cc_on), 3)
        elif key == "ccopts":
            self.cc_menu()
        elif key == "sleep":
            mins = [0, 15, 30, 60, 90, 120]
            labels = [_("Off")] + [_("%d minutes") % m for m in mins[1:]]
            j = xbmcgui.Dialog().select(_("Sleep timer"), labels)
            if j >= 0:
                self.sleep_at = time.time() + mins[j] * 60 if mins[j] else 0
                self.toast(_("Sleep: %s") % labels[j], 3)
        elif key == "off":
            self.shutdown(power_off=True)

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


GUI_SOUNDS_ALWAYS = 2      # Kodi: 0 never, 1 only when playback is stopped, 2 always
GUI_SOUNDS_IDLE = 1
STATIC_AUTO, STATIC_QUICK, STATIC_CLIP = 0, 1, 2


def refresh_rate_switching():
    """Kodi's 'Adjust display refresh rate' (0 off, 1 on start/stop, 2 always)."""
    try:
        return int(K.rpc("Settings.GetSettingValue", {"setting": "videoplayer.adjustrefreshrate"})
                   .get("value") or 0) != 0
    except Exception:
        return False


def use_static_clip():
    """Static between channels as a short video clip (picture and sound in one
    file, never lost) or as an interface sound over the picture (quick)?

    Automatic: the clip on Windows, which resets its audio device between
    videos and swallows interface sounds - unless the display switches refresh
    rate per video, where an extra clip would blank the screen twice per change."""
    mode = K.setting_int("static_mode", STATIC_AUTO)
    if mode == STATIC_CLIP:
        return True
    if mode == STATIC_QUICK:
        return False
    try:
        windows = bool(xbmc.getCondVisibility("System.Platform.Windows"))
    except Exception:
        windows = False
    return windows and not refresh_rate_switching()


class GuiSounds(object):
    """Kodi's interface sounds while CableBox is on.

    The static and the turn-off sound are Kodi interface sounds, which Kodi only
    plays during a video with 'Play GUI sounds' set to Always.  CableBox sets
    Always once when the TV comes on and puts the viewer's own setting back when
    it goes off (or next time, if Kodi was closed before that).

    Never switched per channel change: in Kodi 21 every change of that setting
    rebuilds the whole audio output, and doing it twice on each channel change,
    while one programme closes and the next opens, made the sound sputter and
    could leave HDMI audio unable to reopen at all (CoreELEC) until Kodi was
    restarted.  The price is that Kodi's own button clicks are heard while the
    TV is on - like a cable box that beeps."""
    SETTING = "audiooutput.guisoundmode"

    def __init__(self):
        self.active = False
        self.orig = None

    def _get(self):
        try:
            v = K.rpc("Settings.GetSettingValue", {"setting": self.SETTING}).get("value")
            return None if v is None else int(v)
        except Exception:
            return None

    def _set(self, v):
        try:
            K.rpc("Settings.SetSettingValue", {"setting": self.SETTING, "value": int(v)})
        except Exception as exc:
            K.log_err("gui sounds: %s" % exc)

    def start(self):
        """Once, before anything plays: Always, for the whole time the TV is on."""
        cur = self._get()
        if cur is None:
            return
        st = K.load_json(K.STATE_FILE, {})
        orig = st.get("gui_sounds_orig")          # left over if Kodi closed while CableBox was on
        if orig is None:
            orig = cur
            st["gui_sounds_orig"] = orig
            K.save_json(K.STATE_FILE, st)
        self.orig = int(orig)
        if cur != GUI_SOUNDS_ALWAYS:
            self._set(GUI_SOUNDS_ALWAYS)
            xbmc.sleep(150)                         # Kodi's audio output reopens once, before any programme
        self.active = True

    def loud(self, secs):
        """Kept for the callers: interface sounds are already on for the session."""
        return

    def tick(self, now):
        return

    def stop(self):
        """Once, after the last programme has stopped: the viewer's own setting back."""
        if not self.active:
            return
        self.active = False
        if self.orig is not None and self.orig != GUI_SOUNDS_ALWAYS:
            self._set(self.orig)
        st = K.load_json(K.STATE_FILE, {})
        st.pop("gui_sounds_orig", None)
        K.save_json(K.STATE_FILE, st)


def run(channel=None):
    K.ensure_dirs()
    win = TVWindow("script-cablebox42-tv.xml", K.ADDON_PATH, "Default", "1080i")
    win.wanted_channel = channel
    win.doModal()
    win.shutdown()
    del win

"""The TV set: full-screen window, remote handling and the playout loop.

Playback is plain xbmc.Player (windowed into our videowindow control), so on
every device each file goes through the same hardware decoder as it
does when you play it from the library.
"""
import json
import math
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
from . import promos
from . import musicvideos
from . import ads
from . import guide
from . import musictv
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
#  Settings > On screen > Remote CC button maps the remote's subtitle key for CableBox)
DIGITS = dict((58 + i, i) for i in range(10))
DIGITS.update(dict((140 + i, i) for i in range(2, 10)))  # JUMP_SMS2..9 numeric keypads

VIDEO_KINDS = ("show", "ad", "bump", "clip")
QUEUE_AHEAD = 10.0      # hand Kodi the next item this many seconds before the current one ends
QUEUE_MAX = 24          # playlist length at which the next item starts a fresh playlist instead
QUEUE_EARLY = 1.0       # seconds a queued item may run ahead of its slot before we log it
QUEUE_NEAR_END = 1.5    # an item this close to its end is left to finish; Kodi moves on itself
LOAD_TIMEOUT = 12.0
SWITCH_LEAD = 0.25      # s: Kodi's switch from a programme to the break's first item (rig), asked for this early
PART_START = 1.5        # a part started within this long of its slot start: a planned start (after a break)
PART_HOLD = 4.0         # a part running behind the clock keeps the screen this long at most past its slot end
EARLY_STOP = 3.0        # a file that stops within this many seconds of starting is opened again at once (once)
STATIC_HOLD = 0.55     # Windows: seconds of the static clip before the new channel comes in
TONE_SETTLE = 0.4      # off-air tone: seconds after a video stopped or ended before asking Kodi to play it
# (the clip itself lasts 2.5 s: when it reached its end just as the next file was
# opened, Kodi's end-of-playlist handling closed the new file - a channel change
# to black until the watchdog reopened it)
STATIC_CLIP_WAIT = 2.0  # ...or this long if the clip never starts
POWER_ON_LEN = 3.5      # the TV warming up, with the CableBox 42 title card
POWER_OFF_LEN = 1.4     # the picture shrinking to a dot
POWER_OFF_SETTLE_MS = 250   # Kodi's audio output reopening after the programme stops
# (both start with a few tenths of a second of picture and no sound: Windows
# swallows the start of the sound while it reopens its audio device)


def scheduler_year(title):
    """The year a title ends in, '(1993)' -> '1993'; '' when it has none."""
    from . import titles
    return titles.split_year(title)[1]


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

    def onPlayBackStopped(self):
        self.owner.on_stopped()

    def onPlayBackEnded(self):
        self.owner.on_stopped()


FULLSCREEN = 12005               # Kodi's own full-screen video window
VISUALISATION = 12006            # Kodi's own full-screen music window


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
        self.crawl_token = 0         # the guide crawl's thread runs while this stays the same
        self.guide_shape = None      # the guide list's rows (channel ids, scroll ads) as filled
        self.promos = []
        self.closing = False
        self.exit_how = "back"       # how the TV was turned off: back / menu / sleep / away
        self.finished = threading.Event()   # shutdown has tidied up
        self.threads = []
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
        self.queued = None           # the next entry, already in Kodi's video playlist (queue_next)
        # captions mode: programmes in Kodi's full-screen player, our overlay on top
        self.cc_fullscreen = K.setting_bool("cc_fullscreen", True)
        self.overlay = None
        self.fs_state = "off"        # off / entering / on
        self.fs_at = 0
        self.fs_retry_at = 0
        self.music = musictv.MusicScreen(self)   # music channels

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
        library.listing_warm()               # guide details and ratings, read in the background
        crt =K.setting_int("crt_mode", 0)   # 0 off, 1 subtle, 2 full
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
            self.play_power_on(start)
        self.tune(start, static=not power)
        if not power:
            self.first_tip()
        for target, name in ((self.loop, "cablebox42-loop"), (self.builder, "cablebox42-builder")):
            t = threading.Thread(target=target, name=name)
            t.start()
            self.threads.append(t)

    def start_channel(self):
        if getattr(self, "wanted_channel", None):
            ch = self.lineup.by_number(self.wanted_channel)
            if ch:
                return ch
        state = K.load_state()
        fixed = K.setting_int("start_channel", 0)
        if fixed and not self.lineup.by_number(fixed):
            fixed = 0                    # no such channel (any more): the last one watched
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

    def shutdown(self, power_off=False, how="back"):
        """Switch CableBox off.  power_off: the viewer turned the TV off (not
        Kodi closing or the window being left), so play the turn-off clip.
        how: where the viewer goes next - "back" (where the TV was started from),
        "menu" (CableBox's main menu), "sleep" or "away" (Kodi)."""
        if self.closing:
            return
        self.closing = True
        self.exit_how = how
        try:
            self._shutdown(power_off)
        finally:
            self.finished.set()

    def _shutdown(self, power_off):
        self.tone_off()                      # the off-air tone: repeat off; the player is stopped below
        self.promo_stop(stop_music=False)    # forget the theme; the player is stopped below
        if self.ch:
            K.update_state({"last_channel": self.ch["number"], "last_channel_id": self.ch["id"]})
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
        xbmcgui.Window(10000).clearProperty("cablebox42.cover")
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
            elif self.extras_waiting() and not library.extras_scanned():
                self.ask_look_for_extras()      # a long job: one stray OK only opens a question
            else:
                self.toggle_banner()
        elif aid in MENU:
            self.menu()
        elif aid in EXIT:
            self.shutdown(power_off=True)     # straight off, no "are you sure?"
        elif aid in VOL_UP or aid in VOL_DOWN or aid in MUTE:
            pass    # Kodi changes the volume itself; CableBox never does (it made each press count twice)
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
            if self.digits == self.DEV_CODE and self.dev_code():
                return                       # Developer tools: a promo now (no "CH 000" on screen)
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
        self.unsqueeze()
        self.uncover()
        with self.lock:
            if static and self.power_on:     # changing channel cuts the turn-on short
                self.power_on = False
                self.hold_until = 0
            if self.ch and ch["id"] != self.ch["id"]:
                self.prev_ch = self.ch
            self.promo_stop()                # mid-promo: the theme off
            self.dev_promo_until = 0
            self.cc.leave()                  # before the static clip replaces the programme
            self.music.leave()               # a music channel's screen and queue start afresh
            self.ch = ch
            xbmcgui.Window(10000).setProperty("cablebox42.channel", str(ch.get("number", "")))  # audiowatch's restart
            self.cur_key = None
            self.failed_key = None
            self.retries = 0
            self.sub = None
            self.sub_at = 0
            if not self.power_on:
                self.show_digits(str(ch["number"]))
            self.setProperty("ch_number", str(ch["number"]))
            self.rating_clear()
            self.guide_on = None
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
            self.measure_music_videos()
            if self.guide_pending:
                self.guide_pending = False
                self.guide_next = 0          # redraw the guide with the new listings
            for _w in range(300):
                if self.closing or self.monitor.waitForAbort(1):
                    return

    def measure_music_videos(self):
        """Boombox: music videos not measured yet are read here, a few at a time
        and gently (never on a channel change); the first ones rebuild the schedule."""
        if not any(c.get("type") == "musicvideos" or any(s.get("type") == "musicvideos" for s in c.get("sources", []))
                   for c in self.lineup.channels):
            return
        try:
            first = not library.mv_measured()
            n = library.musicvideos_refresh(abort=lambda: self.closing or self.monitor.abortRequested(),
                                            pause=lambda: self.monitor.waitForAbort(0.15))
            if n and first:
                self.guide_pending = True
        except Exception as exc:
            K.log_err("music videos: %s" % exc)

    # ----------------------------------------------------------- main loop
    def loop(self):
        while not self.closing:
            if self.monitor.waitForAbort(0.2):
                self.shutdown(how="away")
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
        if cur == VISUALISATION and self.playing_ours():
            # Kodi opened its music screen for a promo's theme or the guide's music:
            # never on a TV - straight back to the TV window
            self.away_since = 0
            if now - self.vis_pulled > 1:
                self.vis_pulled = now
                K.log("Kodi opened its music visualisation - back to the TV window", xbmc.LOGINFO)
                xbmc.executebuiltin("Dialog.Close(musicosd,true)")
                xbmc.executebuiltin("Action(FullScreen)")
            return False
        here = cur == self.win_id or (cur == 12005 and self.playing_ours())
        if here:
            self.away_since = 0
            return False
        if not self.away_since:
            self.away_since = now
        return now - self.away_since > 1.5

    fs_since = 0
    fs_pulled = 0
    vis_pulled = 0

    def hide_busy_wheel(self, now):
        """A TV never shows a loading spinner: while a channel is coming in,
        close Kodi's busy wheel if it pops up (slow drive, screen recording...)."""
        if now - self.play_started_at > 4 and now - self.failed_at > 30:
            return
        promos.close_busy_wheel()
        if now - self.failed_at < 30 and xbmc.getCondVisibility("Window.IsActive(okdialog)"):
            # Kodi's own "Playback failed - check the log" box: never over the TV
            xbmc.executebuiltin("Dialog.Close(okdialog,true)")

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
        # (showing only once CableBox's own choice has applied: Kodi's remembered "on" from
        # just after a start, with CC off, went full screen and switched the display's rate)
        if not (self.cc_fullscreen and self.overlay is not None and (self.cc.on or self.cc.showing_settled())):
            return False
        if self.closing or self.power_on or self.prop_mode != "video" or self.squeezed or self.cover_mark:
            return False                 # (squeezed credits play in the TV window's video window)
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
            self.shutdown(how="away")
            return
        self.pull_back_from_fullscreen(now)
        self.gui_sounds.tick(now)
        self.promo_tick(now)
        if self.prop_mode == "upnext":
            self.upnext_tick(now)
        elif self.prop_mode == "video":
            self.squeeze_tick(now)
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
            self.shutdown(power_off=True, how="sleep")   # nobody is watching: no menu afterwards
            return

        if self.hold_until:
            if now < self.hold_until:
                return
            self.hold_until = 0
        if self.dev_promo_until:
            if now < self.dev_promo_until:
                return                       # the cheat code's promo is on
            self.end_dev_promo()
        if self.power_on:
            self.end_power_on()
        if self.ch.get("type") == "music":
            self.music.tick(now)
            if self.banner_until:
                self.update_progress(now)
            return
        sched = self.lineup.schedule(self.ch)
        e = sched.entry_at(now)
        if self.early_to:
            # a part ended at its mark by the file's position: the break is on already,
            # though the clock still says the part (end_at_mark)
            cid, ne = self.early_to
            if cid == self.ch["id"] and e is not None and now < ne["s"] and e["e"] <= ne["s"] + 0.01:
                e = ne
            else:
                self.early_to = None
        if e is None:
            if self.cur_key != "none":
                self.cur_key = "none"
                self.stop_player()
                self.set_mode("card")
                self.card(self.ch["name"], _("Please stand by"), "", "")
            return
        key = (self.ch["id"], e["s"])
        if key != self.cur_key and self.hold_part(e, now):
            e, key = self.cur_entry, self.cur_key
        if key != self.cur_key:
            self.start_entry(e, key, now)
        elif key == self.failed_key:
            self.cover_failure(e, now)
        elif self.is_video(e):
            if self.awaiting:
                self.check_awaiting(e, key, now)
            self.cover_tick()
            if not self.end_at_mark(sched, e, key, now):
                self.watchdog(e, key, now)
                self.queue_next(sched, e, key, now)
        elif e["k"] == "offair" and e.get("sub") == "bars_tone":
            self.tone_tick(now)
        self.caption_tick(now)
        self.rating_tick(now)
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
        # standby and off-air screens: the name shrinks, then wraps (never cut off)
        self.setProperty("ch_name_fsb", promos.fit_font(br["name"], 460))
        self.setProperty("ch_name_foa", promos.fit_font(br["name"], 1000, promos.LADDER_45, promos.TWO_27))
        self.setProperty("ch_name2", promos.two_lines(br["name"]))
        self.setProperty("ch_call", br["call"] or "")
        path = br["logo"]
        bug = br.get("bug") or path      # a station kit may have a simpler corner bug
        on, corner, opacity = logos.bug_settings()
        was_on = self.getProperty("bug") == "1"
        self.bug_on = bool(bug) and on
        self.setProperty("bug", "1" if (keep_bug and was_on and self.bug_on) else "")
        self.setProperty("bug_logo", bug if self.bug_on else "")
        self.setProperty("bug_corner", corner)
        self.setProperty("bug_alpha", str(opacity))
        self.setProperty("banner_logo", path if K.setting_bool("logo_banner", True) else "")

    def show_bug(self, on):
        """The corner logo shows during programmes only - never over commercials,
        bumps, station IDs, cards or the guide, just like the real networks."""
        self.setProperty("bug", "1" if on and getattr(self, "bug_on", False) else "")

    def start_entry(self, e, key, now):
        self.rating_start(e, now)
        if e.get("k") != "guide" and self.guide_on:
            self.guide_on = None             # left the guide: its top half stops with what plays next
            self.top_reset()
        self.unsqueeze()                     # a new item: the picture is full size again
        self.uncover()
        self.promo_stop()                    # a promo's theme cut with its card, before anything else plays
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
            if self.take_queued(e, key, now):
                self.set_mode("video")
            else:
                if self.file_missing(e.get("p")):
                    self.missing(e, key, now)
                    return
                self.play(e, now)
                self.set_mode("video")
        else:
            self.unqueue()
            if kind == "guide":
                self.set_mode("guide")
                self.guide_next = 0
                if self.guide_on != self.ch["id"]:
                    # tuned in: a fresh list from the top; the guide's next half-hour block
                    # on the same channel carries on (no jump, the music and video go on)
                    self.guide_on = self.ch["id"]
                    self.promo_next = 0
                    self.guide_shape = None
                    self.top_reset()
                    self.guide_tick(now)
                    self.crawl_start()
                else:
                    self.guide_tick(now)
            elif kind == "weather":
                self.set_mode("weather")
                self.weather.tick(now, force=True)
                self.background_audio(K.setting("weather_music_path"))
            elif kind == "promo":
                self.start_promo(e, now)
            elif kind == "house":
                self.start_house(e, now)
            elif kind == "retro":
                self.start_retro(e, now)
            else:
                tone = kind == "offair" and e.get("sub") == "bars_tone"
                was_playing = False
                if not (tone and self.tone_playing()):
                    was_playing = self.player.isPlaying()
                    self.stop_player()       # (the same off-air entry again: the tone carries on)
                if kind == "offair":
                    b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
                    resume = fmt_time(b["e"]) if b else ""
                    self.setProperty("offair_line", _("Programming resumes at %s") % resume)
                    self.setProperty("offair_style", e.get("sub") or "bars")
                    self.set_mode("offair")
                    if tone:
                        self.tone_start(after_stop=was_playing)
                elif kind == "signoff":
                    self.signoff(e, now)
                else:
                    self.card_for(e, now)
        if kind == "show":
            self.update_banner()
        self.prefetch_promo(e)

    # ----------------------------------------------------------- TV rating box
    # The 1997 TV Parental Guidelines box: top left, for the first 15 seconds of a
    # show or movie (not after a break, not when you tune in later), with a CC box
    # beside it when the programme has captions (the skin keys that off now_cc, the
    # same check as the banner's CC and the CC button).
    RATING_SECS = 15.0
    RATING_TUNE_IN = 10.0
    rating_at = None             # (show from, until)

    def rating_clear(self):
        self.rating_at = None
        if self.getProperty("rating"):
            self.setProperty("rating", "")

    def rating_start(self, e, now):
        self.rating_clear()
        if e.get("k") != "show" or not e.get("p") or now - e["s"] > self.RATING_TUNE_IN:
            return
        if (self.ch or {}).get("type") in ("musicvideos", "extras") or not K.setting_bool("rating_box", True):
            return
        sched = self.lineup.schedule(self.ch, ensure=False)
        b = sched.block_at(e["s"])
        first = self.block_entry(sched, b) if b else None
        if not first or first["s"] != e["s"]:
            return                           # a later part (after a break) or a later short in the block
        code = library.rating_for(e["p"])
        if not code:
            return
        self.setProperty("rating_code", code[3:])
        # from the picture's first second (Kodi opens the file meanwhile)
        self.rating_at = (max(now, e["s"]) + 1.0, e["s"] + 1.0 + self.RATING_SECS)

    def rating_tick(self, now):
        if not self.rating_at:
            return
        start, until = self.rating_at
        if now >= until:
            self.rating_clear()
            return
        want = "1" if now >= start else ""
        if self.getProperty("rating") != want:
            self.setProperty("rating", want)

    # ----------------------------------------------------------- video captions
    # Boombox's lower third, the classic music-channel way: artist, "title",
    # album, label, year - shortly after a video starts and again shortly
    # before it ends.  Lines without information are simply left out.
    cap_for = None

    def caption_tick(self, now):
        e = self.cur_entry
        on = False
        if e and e.get("cap") and e.get("k") == "show" and self.ch.get("mv_captions", True)                 and self.av_started_token == self.play_token and not self.sub and self.failed_key != self.cur_key:
            into = now - e["s"] + float(e.get("o", 0))
            dur = float(e.get("d") or (e["e"] - e["s"]))
            on = any(a <= into < b for a, b in musicvideos.caption_times(dur))
        if on and self.cap_for != (e["s"], e.get("p")):
            self.cap_for = (e["s"], e.get("p"))
            lines = dict(e["cap"])
            for role in ("artist", "title", "album", "label", "year"):
                self.setProperty("mvc_" + role, lines.get(role, ""))
        want = "1" if on else ""
        if self.getProperty("mvcap") != want:
            self.setProperty("mvcap", want)

    # ----------------------------------------------------------- promos
    # "Channel 7 - Seinfeld: The Contest - Up next": a card from the
    # show's own artwork with its theme music, between the spots of a break
    # (the card and the music themselves: promos.card / promos.ThemeAudio).
    _theme = None

    @property
    def theme(self):
        if self._theme is None:
            self._theme = promos.ThemeAudio(self.player)
        return self._theme

    @staticmethod
    def promo_subject(sched, e):
        """(time, path, title, later) of the programme a promo slot advertises."""
        pt, path, title, later = e.get("pt"), e.get("pp"), e.get("t"), e.get("pw") == "later"
        if e.get("sp"):                      # a special: still in the calendar for that time?
            return (pt if pt and TVWindow.special_still_on(sched, e) else None), path, title, True
        if e.get("xc"):                      # another channel's show: still planned there?
            try:
                if pt and not TVWindow.cross_still_on(sched, e):
                    pt = None
                tgt = sched._cross_target(e) if pt is None else None
            except Exception:
                tgt = None
            if tgt and tgt[0]:
                pt, path, title, later = tgt[0]["s"], tgt[1], tgt[0]["t"], True
            return pt, path, title, later
        if pt is None:                       # planned before the next show was known
            try:
                tgt = sched.promo_target(e, sched.gap_avoid(e) if e.get("h") else None, house=bool(e.get("h")))
            except Exception:
                tgt = None
            if tgt and tgt[0]:
                b = tgt[0]
                pt, path, title = b["s"], tgt[1], b["t"]
                later = b is not sched.next_block(e["s"])
        return pt, path, title, later

    def prefetch_promo(self, e):
        """While the item before a promo plays: look its artwork up and load its
        logo into Kodi's texture cache (the skin's promo_preload image), so the
        card can show the logo the moment it opens.  Called after the current
        entry has started, so a promo card on screen already holds its own logo."""
        nxt = None
        try:
            sched = self.lineup.schedule(self.ch, ensure=False)
            nxt = sched.entry_at(e["e"] + 0.01)
        except Exception:
            pass
        if not (nxt and nxt.get("k") == "promo" and (nxt.get("h") or K.setting_bool("promos_on", True))):
            self.setProperty("promo_preload", "")
            return
        _pt, path, title, _later = self.promo_subject(sched, nxt)
        if not path and not title:
            self.setProperty("promo_preload", "")
            return
        ch = self.ch

        def work():
            try:
                logo = promos.info(path, title or "").get("logo") or ""
            except Exception:
                logo = ""
            if self.ch == ch and not self.closing:
                self.setProperty("promo_preload", logo)
        threading.Thread(target=work, name="cablebox42-promo").start()

    def start_promo(self, e, now):
        sched = self.lineup.schedule(self.ch, ensure=False)
        pt, path, title, later = self.promo_subject(sched, e)
        house = bool(e.get("h"))             # house breaks run promos whatever the Promos setting
        if not (house or K.setting_bool("promos_on", True)) or not pt or pt < now:
            self.card_for({"k": "card", "sub": "id"}, now)     # promos switched off since: a station ID
            return
        special = {"end": e.get("pe"), "sub": e.get("sub")} if e.get("sp") else None
        if e.get("xc"):
            other = next((c for c in self.lineup.channels if c["id"] == e["xc"]), None)
            if other is None:
                self.card_for({"k": "card", "sub": "id"}, now)
                return
            self.air_promo(pt, path, title, True, now, e["e"], ch=other,
                           kicker=lambda name: promos.cross_kicker(name, other["number"]), special=special)
            return
        self.air_promo(pt, path, title, later, now, e["e"], special=special)

    @staticmethod
    def special_still_on(sched, e):
        """A special's promo: the special still starts then on that channel (it may
        have been changed or removed since the break was planned)."""
        from . import specials
        off = scheduler.specials_shift(sched.cfg)
        cid = e.get("xc") or sched.ch["id"]
        if sched.lineup is not None and not any(c["id"] == cid for c in sched.lineup.channels):
            return False
        return any(sp["id"] == e["sp"] and sp["name"] == e.get("t") and abs(st - off - e["pt"]) < 1
                   for st, _en, sp, _b in specials.between(scheduler.all_specials(), e["pt"] + off - 60,
                                                           e["pt"] + off + 60, cid))

    @staticmethod
    def cross_still_on(sched, e):
        """A cross-channel promo's show still starts at its time on that channel
        (a refresh there may have changed it): never promote what won't air."""
        ch = next((c for c in sched.lineup.channels if c["id"] == e.get("xc")), None)             if sched.lineup is not None else None
        if ch is None:
            return False
        b = sched.lineup.schedule(ch, ensure=False).block_at(e["pt"] + 1)
        return bool(b and abs(b["s"] - e["pt"]) < 1 and b.get("t") == e.get("t"))

    def start_house(self, e, now):
        """A system ad: the guide or weather channel, or what's coming up tonight.
        Only for channels that are there now; otherwise a station ID card."""
        kind = e.get("h")
        props = None
        try:
            chans = self.lineup.channels
            if kind in ("guide", "weather"):
                target = next((c for c in chans if c.get("type") == kind), None)
                if target and (kind != "weather" or weather.has_place()):
                    props = promos.house_card(kind, int(e.get("ln", 0)), target, now)
            elif kind == "lineup":
                rows = []
                for c in chans:
                    if c.get("type") not in scheduler.PROMO_TYPES:
                        continue
                    s = self.lineup.schedule(c, ensure=False)
                    nb = next((b for b in s.blocks_between(now + 300, now + 3 * 3600)
                               if b.get("k") == "show" and b["s"] >= now + 300), None)
                    if nb:
                        rows.append((nb["s"], library.on_air(nb["t"]), c["number"]))
                rows.sort(key=lambda r: (r[0], r[2]))
                if len(rows) >= 2:
                    props = promos.house_card("lineup", 0, None, now, rows[:3])
        except Exception as exc:
            K.log_err("house ad %s: %s" % (kind, exc))
            props = None
        if not props:
            self.card_for({"k": "card", "sub": "id"}, now)
            return
        music = promos.air_house(self, props)
        self.set_mode("promo")
        self.start_theme(music, e["e"])

    _ad_slots = None

    def start_retro(self, e, now):
        """A retro ad (house breaks): its card and jingle until the entry ends.
        Retro ads switched off since planning, or a movie no longer in the
        library: a station ID card instead."""
        c = None
        if K.setting_bool("retro_ads", True):
            try:
                c = ads.card(e, kids=ads.flavour(self.ch) == "K")
            except Exception as exc:
                K.log_err("retro ad %s: %s" % (e.get("ad"), exc))
        if not c:
            self.card_for({"k": "card", "sub": "id"}, now)
            return
        if self._ad_slots is None:
            self._ad_slots = ads.Slots()
        t0 = time.time()
        ads.apply_card(self, c, self._ad_slots)
        K.log("retro ad %s: lettered in %.0f ms" % (e.get("ad"), (time.time() - t0) * 1000), xbmc.LOGINFO)
        self.set_mode("retro")
        self.start_theme(ads.music(c, e["e"] - time.time()), e["e"])     # tuned in late: silent

    def air_promo(self, pt, path, title, later, now, end, ch=None, kicker=None, special=None):
        """The card and its theme until `end` (promos.air: the same for breaks,
        Preview promo and the Developer tools cheat code)."""
        music = promos.air(self, ch or self.ch, pt, path, title, later, now, kicker=kicker, special=special)
        self.set_mode("promo")
        self.start_theme(music, end)

    def start_theme(self, music, end):
        self.tone_off()
        if music:
            self.our_files.add(music)
            self.play_token += 1
            self.play_started_at = time.time()
            self.theme.start(music, end)
        else:
            self.stop_player()

    def promo_tick(self, now):
        self.theme.tick(now)

    def promo_stop(self, stop_music=True):
        self.theme.stop(stop_music)

    # Settings > Advanced > Developer tools: 0 0 0 while watching airs this
    # channel's next promo right now, then the channel again at the live point
    # (like coming back from a break).  Read-only: nothing in the schedule
    # changes, so the next real break, "How often" and series stay as they were.
    DEV_CODE = "000"
    dev_promo_until = 0

    def dev_code(self):
        """The 0 0 0 cheat code.  False when it isn't one (Developer tools off, or
        the lineup really has a channel 0): then it's ordinary channel entry."""
        if not K.setting_bool("dev_tools", False) or self.lineup.by_number(0):
            return False
        self.digits = ""
        self.clear_overlays()                # nothing on screen but the promo
        if not K.setting_bool("promos_on", True) or not self.ch or self.power_on \
                or self.ch.get("type") not in scheduler.PROMO_TYPES:
            return True                      # promos off: the code shows nothing
        now = time.time()
        try:
            subj = self.dev_promo_subject(self.lineup.schedule(self.ch, ensure=False), now)
        except Exception as exc:
            K.log_err("developer promo: %s" % exc)
            subj = None
        if not subj:
            K.log("Developer tools: nothing to promote on %s" % self.ch.get("name"), xbmc.LOGINFO)
            return True
        pt, path, title, later = subj
        K.log("Developer tools: promo now on %s for %s" % (self.ch.get("name"), title), xbmc.LOGINFO)
        self.promo_stop()
        self.stop_player()                   # the programme off (its resume point is put back)
        self.show_bug(False)
        self.cur_key = ("dev-promo", now)    # afterwards tick() starts the live entry again
        self.dev_promo_until = now + promos.PROMO_LEN
        self.air_promo(pt, path, title, later, now, self.dev_promo_until)
        return True

    def dev_promo_subject(self, sched, now):
        """(time, path, title, later) of the promo this channel's next break would
        air: its planned promo if it has one, otherwise what promo_target would
        pick for a promo there.  None when there's nothing to promote."""
        e = sched.entry_at(now)
        t = e["e"] if (e and e.get("k") in ("show", "clip")) else now    # the next break starts here
        ents = sched.data["entries"]
        for x in ents:
            if x["s"] < t - 0.05:
                continue
            if x.get("k") in ("show", "clip"):
                break                        # the break is over: no planned promo in it
            if x.get("k") == "promo":
                pt, path, title, later = self.promo_subject(sched, x)
                if pt and pt > now:
                    return pt, path, title, later
                break
        tgt = sched.promo_target({"s": t, "e": t + promos.PROMO_LEN})
        if tgt is None:                      # the schedule isn't planned that far: what's on next
            b = next((b for b in sched.blocks_between(t, t + scheduler.PROMO_LOOKAHEAD)
                      if b["s"] > t and b.get("k") == "show"), None)
            tgt = (b, None)
            if b:
                tgt = (b, next((x.get("p") for x in ents if b["s"] <= x["s"] < b["e"]
                                and x.get("k") == "show" and x.get("p")), None))
        b, path = tgt
        if not b:
            return None
        return b["s"], path, b["t"], b is not sched.next_block(t)

    def end_dev_promo(self):
        self.dev_promo_until = 0
        self.promo_stop()                    # the theme cut with the card
        self.cur_key = None                  # back to the channel at the live point

    @staticmethod
    def list_item(e, offset):
        title = library.on_air(e.get("t") or "")            # Kodi's player info and phone remotes: no year
        li = xbmcgui.ListItem(label=title, path=e["p"])
        try:
            tag = li.getVideoInfoTag()
            tag.setTitle(e.get("sub") or title)
            tag.setTvShowTitle(title)
        except Exception:
            pass
        if offset > 1.0:
            li.setProperty("StartOffset", "%.2f" % offset)
        return li

    # Starting partway into a file (tuning in mid-programme): Kodi takes a moment to
    # open the file and seek (2-3 s in the rig), so the picture would start that much
    # behind the real clock.  The delay is learned from each start (start_measured)
    # and added to the start position.  Kodi itself may start at the keyframe before
    # the position asked for (files with keyframes far apart): that part isn't ours.
    start_lag = 1.0
    start_good = []              # Kodi's open + seek time of the last good tune-ins (s)
    start_odd = []               # ...and of the last ones left out
    start_ask = None             # (path, entry, delay added) of a tune-in partway in, measured at AV start
    seek_after = None            # (token, path, entry, mark or None): a DTS file opened at 0, seek at AV start
    SEEK_LEAD = 0.4              # s Kodi's seek takes (N2)
    DTS_CODECS = ("dca", "dts", "dtshd_ma", "dtshd_hra", "dts_hd", "dtshd")
    audio_codecs = {}            # path -> the first audio track's codec ('' unknown), for this Kodi session
    pt_dts = None
    pt_read_at = 0.0

    def dts_risky(self, path):
        """True for a file whose audio is DTS with DTS passthrough on.  Opened partway in
        (StartOffset), Kodi 21 on the N2 can misread the first DTS-HD frame at some
        positions (Planet Earth II S01E03 at 19:05-19:07, every time, Kodi's own player
        too): ALSA can't open that 'layout' and Kodi's audio output stays stuck until Kodi
        restarts.  Opened at 0 and then seeked to the same spots it never did: the stream
        is already set up as DTS-HD when the seek's misread comes, and Kodi keeps it."""
        if not path:
            return False
        now = time.time()
        if now - self.pt_read_at > 60:
            self.pt_read_at = now
            try:
                on = K.rpc("Settings.GetSettingValue", {"setting": "audiooutput.passthrough"}).get("value")
                dts = K.rpc("Settings.GetSettingValue", {"setting": "audiooutput.dtspassthrough"}).get("value")
                type(self).pt_dts = bool(on) and bool(dts)
            except Exception:
                type(self).pt_dts = True     # unknown: the safe way costs only a seek
        if not self.pt_dts:
            return False
        c = self.audio_codecs.get(path)
        if c is None:
            c = ""
            try:
                raw = xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "Files.GetFileDetails",
                                                      "params": {"file": path, "media": "video",
                                                                 "properties": ["streamdetails"]}}))
                fd = (json.loads(raw).get("result") or {}).get("filedetails") or {}
                aud = (fd.get("streamdetails") or {}).get("audio") or []
                c = (aud[0].get("codec") or "").lower() if aud else ""
            except Exception:
                pass
            self.audio_codecs[path] = c
        return c in self.DTS_CODECS or c.startswith("dts")

    def seek_dts(self, path):
        """At AV start of a DTS file opened at 0 (dts_risky): to the mark, or to the
        clock's point for a tune-in."""
        sa, self.seek_after = self.seek_after, None
        if not sa or sa[0] != self.play_token or sa[1] != path:
            return
        e, mark = sa[2], sa[3]
        target = mark if mark is not None else float(e.get("o", 0)) + (time.time() - e["s"]) + self.SEEK_LEAD
        try:
            self.player.seekTime(target)
            K.log("DTS start: opened at 0, seeked to %.1f s" % target, xbmc.LOGINFO)
        except Exception as exc:
            K.log_err("DTS start: seek failed: %s" % exc)

    def play(self, e, now):
        self.clear_music()
        self.uncover()
        o, late = float(e.get("o", 0)), now - e["s"]
        offset = max(0.0, o + late)
        self.start_ask = None
        if e.get("k") == "show" and o > 1.0 and late < PART_START:
            offset = o                       # CableBox's own start of a part (after a break): at the mark exactly
            self.cover_mark = (e["p"], o, time.time() + 6.0)
            self.set_cover(True)             # Kodi starts a little before it: black until the picture gets there
        elif offset > 1.0:
            offset += self.start_lag         # a tune-in: Kodi's open and seek take a moment
            self.start_ask = (e.get("p"), e, self.start_lag)
            if e.get("k") == "show":
                # black until the first captions check has run: a file Kodi remembers
                # with subtitles on never flashes them with CC off
                self.cover_mark = (e["p"], None, time.time() + 6.0)
                self.set_cover(True)
        # DTS passthrough: never open the file at the offset (see dts_risky); open it at
        # the start and seek once the picture is up (on_av_started)
        dts = offset > 1.0 and self.dts_risky(e.get("p"))
        if dts:
            self.start_ask = None            # not a tune-in delay sample: Kodi starts at 0 here
        li = self.list_item(e, 0.0 if dts else offset)
        if offset > 1.0:
            # starting partway in is a jump, and Kodi's skin shows its seek bar for
            # 3 s after any jump in its full-screen player: do it in the TV window
            self.fs_leave()
        self.play_token += 1
        self.seek_after = (self.play_token, e["p"], e, o if late < PART_START and o > 1.0 else None) if dts else None
        self.play_started_at = time.time()
        self.our_files.add(e["p"])
        self.pending_play = (e["p"], time.time())
        if e.get("k") in ("show", "clip"):
            self.progress.remember(e["p"])
        self.play_video(e["p"], li)

    def clip_item(self, clip, ch=None):
        """The turn-on, turn-off and static clips: Kodi's player info shows the
        station's name (or CableBox 42), never the clip's file name."""
        try:
            ch = ch or self.ch
            name = stations.brand(ch)["name"] if ch else ""
        except Exception:
            name = ""
        name = name or "CableBox 42"
        li = xbmcgui.ListItem(label=name, path=clip)
        try:
            li.getVideoInfoTag().setTitle(name)
        except Exception:
            pass
        return li

    # ----------------------------------------------------------- off-air tone
    # "Color bars with tone": a 10 s 1 kHz WAV (exactly 10,000 cycles, so the loop
    # is seamless; Kodi starts the repeat of a file of 4 s or less 0.4 s before it
    # ends, doubling the level) through the music player (PAPlayer) on repeat-one - no video
    # window, so no refresh-rate switch.  Repeat goes back off whenever anything
    # else is handed to the player, so the viewer's own music player is never
    # left on repeat-one.  No audio setting is touched.
    TONE = K.media("offair_tone.wav")
    tone_active = False
    tone_at = 0.0
    tone_tries = 0

    def tone_playing(self):
        try:
            return self.tone_active and self.player.isPlayingAudio() and self.player.getPlayingFile() == self.TONE
        except Exception:
            return False

    def tone_start(self, retry=False, after_stop=False):
        if self.tone_playing():
            return
        self.tone_tries = self.tone_tries + 1 if retry else 1
        self.tone_at = time.time()
        K.log("Off-air tone: start%s" % (" (try %d)" % self.tone_tries if retry else ""), xbmc.LOGINFO)
        try:
            # Kodi drops a play request that arrives just after a video stopped or
            # ended (its own 'playback stopped' handling comes after it): give it
            # TONE_SETTLE s from the stop (rig: every flip back lost the first request)
            t0 = time.time()
            while self.player.isPlaying() and time.time() - t0 < 1.5:
                xbmc.sleep(20)
            since = time.time() - (t0 if after_stop else self.stopped_at)
            if since < TONE_SETTLE:
                xbmc.sleep(int((TONE_SETTLE - since) * 1000))
            pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0))
            pl.clear()
            pl.add(self.TONE)
            self.our_files.add(self.TONE)
            self.play_token += 1
            self.play_started_at = time.time()
            self.tone_active = True
            self.player.play(pl, windowed=True)
            # the music playlist is Kodi's current one now: repeat-one applies to it
            xbmc.executebuiltin("PlayerControl(RepeatOne)", True)
        except Exception as exc:
            K.log_err("off-air tone: %s" % exc)

    def tone_tick(self, now):
        """Kodi drops a play request that arrives while it is still closing the
        video before (the power-on clip, a programme just flipped away from):
        ask again until the tone plays."""
        if not self.tone_active or now - self.tone_at < 1.5 or self.tone_tries >= 5:
            return
        try:
            if self.player.isPlaying():
                if self.tone_playing():
                    self.tone_tries = 1          # playing: a later drop counts afresh from 1
                return
        except Exception:
            return
        self.tone_start(retry=True)

    def tone_off(self):
        """Repeat back off before anything else plays (while the music playlist is
        still Kodi's current one); the caller stops or replaces the tone."""
        if not self.tone_active:
            return
        self.tone_active = False
        K.log("Off-air tone: off, repeat off", xbmc.LOGINFO)
        try:
            xbmc.executebuiltin("PlayerControl(RepeatOff)", True)
        except Exception:
            pass

    def play_video(self, path, li):
        """Every video of ours goes through Kodi's video playlist (one item, in the
        TV window).  That makes the video playlist Kodi's current one, so Kodi
        reports our programme as the video player (id 1).  Played as a single
        file right after the guide's or weather's music, Kodi kept the music
        playlist current and reported the video under the music player's id 0 -
        where phone remotes (Yatse, Kore) and CableBox's own track details found
        no subtitles or audio tracks at all."""
        self.tone_off()
        self.queued = None
        self.awaiting = None
        pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1))
        pl.clear()
        pl.add(path, li)
        xbmcgui.Window(10000).setProperty("cablebox42.play_at", "%.1f" % time.time())  # the service's chapter reader waits
        self.player.play(pl, windowed=True)

    # ----------------------------------------------------------- queue ahead
    # One file at a time, each spot that ended on its own meant Kodi closing the
    # player and the audio device and opening them again: about half a second of
    # black and silence after every spot (more with passthrough).  So the next item
    # waits in Kodi's video playlist and Kodi moves on to it by itself, in ~0.1 s.
    # The add-on stays in charge: at every slot start it checks that Kodi is on the
    # planned item (take_queued); anything else goes the old way (play()).
    @staticmethod
    def queueable(e):
        p = (e or {}).get("p") or ""
        if e.get("k") not in VIDEO_KINDS or not p:
            return False
        if e.get("k") == "show" and float(e.get("o", 0)) > 1.0:
            return False                     # a part after a break: play() covers the picture until the mark
        low = p.lower()
        # names Kodi reports differently (adopt_playing) or that resolve elsewhere
        return not (low.endswith((".strm", ".iso", ".img")) or
                    low.startswith(("udf://", "bluray://", "plugin://", "http://", "https://", "stack://")))

    def queue_next(self, sched, e, key, now):
        """Put the entry after e in Kodi's playlist, shortly before e ends."""
        q = self.queued
        if q and q["after"] == key:
            nxt = sched.entry_at(e["e"] + 0.01)
            if nxt is not None and nxt["s"] == q["e"]["s"] and nxt.get("p") == q["e"].get("p") \
                    and abs(nxt.get("o", 0) - q["e"].get("o", 0)) < 0.05:
                return
            self.unqueue("plan changed")          # a refresh replanned the break: never a stale item
        if self.queued or e["e"] - now > QUEUE_AHEAD or self.closing:
            return
        if self.av_started_token != self.play_token or not self.player.isPlaying():
            return                                # the current item isn't on screen yet
        if self.power_on or self.hold_until or self.dev_promo_until or self.sub or key == self.failed_key:
            return
        try:
            left = self.player.getTotalTime() - self.player.getTime()
        except Exception:
            return
        if left < e["e"] - now - QUEUE_EARLY:
            return                                # the file ends well before its slot: the watchdog's case
        nxt = sched.entry_at(e["e"] + 0.01)
        if nxt is None or abs(nxt["s"] - e["e"]) > 0.05 or not self.queueable(nxt):
            return
        p = nxt["p"]
        if (nxt["k"] == "show" and library.is_bad(p)) or self.file_missing(p):
            return
        offset = float(nxt.get("o", 0))
        if offset > 1.0 and self.fs_state != "off":
            return                                # a start partway in shows Kodi's seek bar full screen
        pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1))
        try:
            size, pos = pl.size(), pl.getposition()
        except Exception:
            return
        if size >= QUEUE_MAX or pos != size - 1:
            return                                # long chains start afresh at the next slot
        self.our_files.add(p)
        pl.add(p, self.list_item(nxt, offset))
        self.queued = {"after": key, "e": nxt, "pos": size, "key": (self.ch["id"], nxt["s"])}

    def check_awaiting(self, e, key, now):
        """take_queued left an ending item to finish: Kodi should be on the queued
        one by now.  If not, play it the ordinary way."""
        akey, q, deadline = self.awaiting
        if akey != key:
            self.awaiting = None
            return
        try:
            on = xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1)).getposition() == q["pos"] and \
                self.player.isPlaying()
        except Exception:
            on = False
        if on:
            self.awaiting = None
        elif now > deadline:
            self.awaiting = None
            K.log("Kodi didn't move on to queued %s - playing it" % e.get("p"), xbmc.LOGINFO)
            if not self.file_missing(e.get("p")):
                self.play(e, now)

    def unqueue(self, why=""):
        """Take the queued item out of Kodi's playlist again."""
        q, self.queued = self.queued, None
        if not q:
            return
        try:
            pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1))
            if pl.getposition() < q["pos"] < pl.size():
                K.rpc("Playlist.Remove", {"playlistid": getattr(xbmc, "PLAYLIST_VIDEO", 1), "position": q["pos"]})
        except Exception as exc:
            K.log("unqueue: %s" % exc)
        if why:
            K.log("Queued %s dropped: %s" % (q["e"].get("p"), why), xbmc.LOGINFO)

    def take_queued(self, e, key, now):
        """The slot of e has started.  If e is the queued item, Kodi is on it
        already (the item before ended by itself) or moves to it now (the item
        before is cut at its slot end, like a network switch).  False: play() it."""
        q, self.queued = self.queued, None
        if not q:
            return False
        if q["key"] != key or q["e"].get("p") != e.get("p"):
            self.queued = q
            self.unqueue("not what is on now")
            return False
        try:
            pl = xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1))
            pos = pl.getposition()
            playing = self.player.isPlaying()
            if pos == q["pos"] - 1 and playing:
                try:
                    left = self.player.getTotalTime() - self.player.getTime()
                except Exception:
                    left = 0
                if left > QUEUE_NEAR_END:
                    self.player.playnext()        # cut what's on, like the network switching over
                else:
                    # It's ending anyway: Kodi moves on by itself in a moment.  A playnext()
                    # now crosses Kodi's own move and leaves the player stopped.
                    self.awaiting = (key, q, now + QUEUE_NEAR_END + 1.0)
                started = False
            elif pos == q["pos"] and playing:
                started = True                    # Kodi moved on by itself
            else:
                self.queued = q
                self.unqueue()
                return False
        except Exception as exc:
            K.log("queued %s: %s" % (e.get("p"), exc))
            return False
        self.clear_music()
        self.play_token += 1
        self.play_started_at = time.time()
        self.pending_play = None
        if started:
            try:
                ahead = self.player.getTime() - (float(e.get("o", 0)) + (now - e["s"]))
            except Exception:
                ahead = 0
            if ahead > QUEUE_EARLY:
                K.log("Queued %s started %.1f s before its slot" % (e["p"], ahead), xbmc.LOGINFO)
            if self.av_started_q == q["key"]:
                self.av_started_token = self.play_token   # its picture came up just before the slot
            if e.get("k") == "show" and e["p"] == self.programme_path():
                try:
                    self.cc.started(self.player.getPlayingFile())
                except Exception:
                    pass
        if e.get("k") in ("show", "clip"):
            self.progress.remember(e["p"])
        return True

    seen_playing = -1            # play_token of the last file the watchdog saw playing
    stopped_at = 0.0             # Kodi's last playback stopped / ended callback

    def watchdog(self, e, key, now):
        """Detect files that never started or ended early."""
        if self.closing:
            return
        since = time.time() - self.play_started_at
        playing = self.player.isPlaying()
        if playing:
            self.seen_playing = self.play_token
            return
        if (since < LOAD_TIMEOUT or self.av_started_token == self.play_token) and self.early_stop(e, since):
            self.retries += 1
            if self.retries <= 1 and not self.file_missing(e.get("p")):
                K.log("%s stopped %.1f s after it was opened - opening it again" % (
                    e.get("p"), self.stopped_at - self.play_started_at if self.stopped_at else since), xbmc.LOGINFO)
                self.play(e, now)
                return
            if e.get("k") == "show":
                self.failed_key = key
                self.failed_at = time.time()
                self.give_up(e, mark=False)      # the stand-in fills the slot
                return
            if self.av_started_token != self.play_token:
                self.fill_rest(e, now)       # a spot: the next commercial
                return
        if since < LOAD_TIMEOUT:
            return
        if self.av_started_token == self.play_token:
            # The file finished before its slot did.  A second or two of black
            # is normal between spots; anything longer gets commercials.
            if e["e"] - now < 4:
                return
            self.fill_rest(e, now)
            return
        self.retries += 1
        if self.retries <= 1 and not self.file_missing(e.get("p")):
            K.log("Retrying %s" % e.get("p"))
            self.play(e, now)
        elif self.file_missing(e.get("p")):
            self.missing(e, key, now)
        else:
            self.failed_key = key
            self.failed_at = time.time()
            self.give_up(e)

    def early_stop(self, e, since):
        """Kodi stopped the file it was asked for within EARLY_STOP s of opening it
        (seen playing or told so, nothing playing now), with its slot far from over.
        Kodi's own player reports a file as playing from the moment it's opening, so
        nothing playing a second after play() means it stopped - a slow drive or
        share waking up stays 'playing' and still gets LOAD_TIMEOUT."""
        now = time.time()
        if since < 1.0 or e["e"] - now < 10:
            return False
        try:
            total = library.durations().get(e.get("p"), probe_if_missing=False) or 0
        except Exception:
            total = 0
        if total and float(e.get("o", 0)) + (now - e["s"]) > total - 10:
            return False                     # the file itself is over (shorter than planned)
        told = self.stopped_at > self.play_started_at
        if self.av_started_token == self.play_token:
            # the picture came and went: stopped within EARLY_STOP s of AV start
            return told and self.stopped_at - self.av_started_at < EARLY_STOP
        return (told or self.seen_playing == self.play_token) and since < EARLY_STOP + 2

    early_to = None              # (channel id, entry) started early by end_at_mark

    cover_mark = None            # (path, mark, give-up time): the picture is covered until the mark

    def cover_tick(self):
        """Uncover a programme's picture started partway in once the first captions
        check has run on it (Kodi may show subtitles it remembers for the file) and,
        for a part after a break, the moment the picture reaches its mark."""
        cm = self.cover_mark
        if not cm:
            return
        if self.cc.checked_at < self.av_started_at and time.time() < cm[2] and \
                (self.av_started_token != self.play_token or time.time() - self.av_started_at < 1.5):
            return                           # the captions check comes ~0.3 s after AV start (1.5 s at most)
        if not self.cc.on and time.time() - self.cc.checked_at < 1.5 and time.time() < cm[2] and \
                xbmc.getCondVisibility("VideoPlayer.SubtitlesEnabled"):
            return                           # CC off: Kodi takes a moment to drop the subtitles it switched on
        if cm[1] is None:
            if self.av_started_token == self.play_token or time.time() >= cm[2]:
                self.uncover()
            return
        if (self.av_started_token != self.play_token or time.time() - self.av_started_at < 0.05) \
                and time.time() < cm[2]:
            return                           # until its picture is up, Kodi reports the position it was asked for
        try:
            if self.requested(self.player.getPlayingFile()) != cm[0]:
                raise ValueError
            left = cm[1] - self.player.getTime()
            if 0 < left <= 0.6:
                v, w = self.fresh_pos()
                left = cm[1] - (v + time.time() - w)
        except Exception:
            left = 9
        if left > 0.25 and time.time() < cm[2]:
            return
        if 0 < left <= 0.25:
            xbmc.sleep(int((left + 0.04) * 1000))    # a frame late rather than early
        self.uncover()

    def fresh_pos(self, wait=0.3):
        """(position, wall time) of Kodi's player, fresher than getTime(): Kodi moves
        the position in ~0.2 s steps, so getTime() can be that far behind the picture.
        Waits for the next step (at most `wait` s) and returns it with its time."""
        v0, t0 = self.player.getTime(), time.time()
        while time.time() - t0 < wait:
            xbmc.sleep(10)
            v = self.player.getTime()
            if v != v0:
                return v, time.time()
        return v0, t0

    def set_cover(self, on):
        self.setProperty("cover", "1" if on else "")
        xbmcgui.Window(10000).setProperty("cablebox42.cover", "1" if on else "")   # for the rig's captions test

    def uncover(self):
        if self.cover_mark:
            self.cover_mark = None
            self.set_cover(False)

    def mid_file_mark(self, e):
        """Where a show part ending in the middle of its file ends (file time), else None."""
        if not e or e.get("k") != "show":
            return None
        mark = float(e.get("o", 0)) + (e["e"] - e["s"])
        try:
            total = library.durations().get(e.get("p"), probe_if_missing=False) or 0
        except Exception:
            total = 0
        return mark if total and mark <= total - 5 else None

    def hold_part(self, e, now):
        """The clock says the break, but the part's picture hasn't reached its mark yet
        (it started late, after Kodi's open): keep it until it does (end_at_mark),
        at most PART_HOLD s - the break absorbs it."""
        cur = self.cur_entry
        if not cur or cur.get("k") != "show" or self.early_to or self.cur_key == self.failed_key or self.sub:
            return False
        if abs(e["s"] - cur["e"]) > 0.05 or now - cur["e"] > PART_HOLD or self.av_started_token != self.play_token:
            return False
        mark = self.mid_file_mark(cur)
        if mark is None:
            return False
        try:
            return self.requested(self.player.getPlayingFile()) == cur["p"] and                 self.player.getTime() < mark - SWITCH_LEAD
        except Exception:
            return False

    def end_at_mark(self, sched, e, key, now):
        """A part that ends in the middle of its file (at a chapter mark, or a timed
        break) ends by the file's position, not the clock: the break comes in when the
        picture reaches the mark (less Kodi's switch time), so no frame of the next act
        shows.  The break starts that much early; it absorbs it (its cards and the
        next part keep the real clock).  True when it switched."""
        if e.get("k") != "show" or self.early_to or e["e"] - now > 2.0 or key == self.failed_key or self.sub:
            return False
        if self.av_started_token != self.play_token or self.closing:
            return False
        mark = self.mid_file_mark(e)
        if mark is None:
            return False                     # the part ends with its file
        nxt = sched.entry_at(e["e"] + 0.01)
        if nxt is None or abs(nxt["s"] - e["e"]) > 0.05:
            return False
        try:
            if self.requested(self.player.getPlayingFile()) != e["p"]:
                return False
            left = mark - SWITCH_LEAD - self.player.getTime()
            if left > 0.6:
                return False                 # the next tick (0.2 s) is still in time
            v, w = self.fresh_pos()          # getTime() lags the picture by up to ~0.2 s
            left = mark - SWITCH_LEAD - (v + time.time() - w)
        except Exception:
            return False
        if left > 0.25:
            return False
        if left > 0:
            xbmc.sleep(int(left * 1000))
        t = time.time()
        if t < nxt["s"]:
            self.early_to = (self.ch["id"], nxt)
        K.log("Part of %s ended at its mark (%.2f s) by the picture, %+.2f s from its slot end" % (
            os.path.basename(e["p"]), mark, t - e["e"]), xbmc.LOGINFO)
        self.start_entry(nxt, (self.ch["id"], nxt["s"]), min(t, nxt["s"]))    # the break's first item from its start
        return True

    def fill_rest(self, e, now):
        """The rest of a spot's time: another commercial, or the station ID card."""
        last = self.fill_last if self.fill_last and self.fill_last[0] == e["s"] else (e["s"], e.get("p"))
        spots = [a for a in self.channel_ads() if not self.file_missing(a["path"])]
        spots = [a for a in spots if a["path"] != last[1]] or spots     # never the same spot twice in a row
        if spots:
            fit = [a for a in spots if a["dur"] <= e["e"] - now] or spots
            a = random.choice(fit)
            self.fill_last = (e["s"], a["path"])
            K.log("%s ended %.1f s before its slot: filling with %s" % (
                os.path.basename(e.get("p") or ""), e["e"] - now, a["path"]), xbmc.LOGINFO)
            self.play({"p": a["path"], "o": 0, "s": now, "t": a.get("title")}, now)
            self.set_mode("video")
        elif self.prop_mode not in ("card", "station", "upnext"):
            self.card_for({"k": "card", "sub": "id"}, now)

    # ----------------------------------------------------------- missing files
    failed_at = 0
    fill_last = None             # (slot start, path) of the watchdog's last filler spot
    av_started_q = None
    awaiting = None              # (key, queued, deadline): Kodi is about to move on to the queued item

    @staticmethod
    def file_missing(path):
        """A planned file that isn't there (deleted, renamed, moved).  Only for
        files and shares; a whole folder gone (a drive or share offline) counts
        as missing too - playing it would only fail."""
        if not path or "://" in path and not path.startswith(("smb://", "nfs://")):
            return False
        try:
            return not xbmcvfs.exists(path)
        except Exception:
            return False

    def missing(self, e, key, now):
        """A planned file isn't there.  No black screen and no Kodi error box: a
        spot goes to the next commercial; a programme's slot is planned again at
        once (rescue_slot): the same episode from the file the library has for it,
        else one stand-in for the rest of the slot, saved in the schedule so the
        parts after each break and a later tune-in play the same thing.  The file
        is kept off the schedule (unplayable list, as for files Kodi can't open)
        and the channel is planned again from its next programme on.  The menu
        says so once."""
        path = e.get("p") or ""
        K.log_err("Missing file, skipped: %s" % path)
        self.failed_at = time.time()
        if e.get("k") != "show":
            self.fill_rest(e, now)
            return
        if self.really_bad(path):            # the folder is there: the file is gone
            library.mark_bad(path, _("The file is missing"))
        K.update_state({"missing_at": time.time()})
        ch = self.ch
        ne, real = None, False
        try:
            ne, real = self.rescue_slot(ch, e)
        except Exception as exc:
            K.log_err("re-plan of the slot after a missing file: %s" % exc)
        threading.Thread(target=self._replan_after_missing, args=(ch, e["s"], path, not real),
                         name="cablebox42-missing").start()
        if ne is not None and not self.file_missing(ne.get("p")):
            self.failed_key = None
            self.sub = None
            self.sub_at = 0
            self.start_entry(ne, key, now)
            return
        self.failed_key = key                # nothing to air instead: the old stand-in way
        self.sub_at = 0
        self.play_substitute(e, now)

    def rescue_slot(self, ch, e):
        """The rest of the on-air slot after a programme's file turned out missing:
        its parts (this one and those after the breaks) point at the episode's real
        file when the library lists the same show + season + episode from a file
        that is there, else at one stand-in, played on from part to part.  Saved,
        so the TV never meets the missing file again in this slot and tuning back
        in plays the same stand-in.  Returns (the entry now at e's place or None,
        True if it's the real episode)."""
        path = e.get("p") or ""
        with self.lineup.lock:
            s = self.lineup.schedule(ch, ensure=False)
            s.reload()
            b = s.block_at(e["s"])
            if b is None:
                return None, False
            parts = [x for x in s.data["entries"] if x.get("k") == "show" and x.get("p") == path
                     and e["s"] - 0.01 <= x["s"] < b["e"]]
            if not parts:
                return None, False
            real = self._same_episode(e, path)
            if real is not None:
                for x in parts:
                    x["p"] = real["path"]
                    x.pop("cr", None)        # credits were found in the other file
                K.log("Missing file %s: the library's other file for %s %s airs instead: %s"
                      % (path, e.get("t", ""), e.get("lb", ""), real["path"]), xbmc.LOGINFO)
            else:
                need = sum(x["e"] - x["s"] for x in parts)
                it = self._substitute_pick({path}, need, e)
                if it is None:
                    return None, False
                pos = 0.0
                for x in parts:
                    if pos >= it["dur"] - 5:
                        break                # the stand-in ran out: the rest gets another
                    x.update(p=it["path"], o=round(pos, 2), t=it.get("title") or "", si=path)
                    for k, v in (("sub", it.get("sub")), ("lb", it.get("label"))):
                        if v:
                            x[k] = v
                        else:
                            x.pop(k, None)
                    for k in ("cr", "cap"):
                        x.pop(k, None)
                    pos += x["e"] - x["s"]
                b["t"] = it.get("title") or b.get("t", "")
                for k, v in (("sub", it.get("sub")), ("lb", it.get("label"))):
                    if v:
                        b[k] = v
                    else:
                        b.pop(k, None)
                K.log("Missing file %s: stand-in for the rest of the slot: %s" % (path, it["path"]),
                      xbmc.LOGINFO)
            s.save()
            here = s.entry_at(e["s"] + 0.001)
            return (here if here is not None and here.get("p") != path else None), real is not None

    @staticmethod
    def _same_episode(e, path):
        """The library's other file for the same show + season + episode, if it is there."""
        label, title = e.get("lb"), e.get("t")
        if not label or not title:
            return None
        try:
            pool = library.resolve([{"type": "tvshow", "value": title}])
        except Exception:
            return None
        for ser in pool["series"]:
            for ep in ser["episodes"]:
                if ep.get("label") == label and ep["path"] != path and not library.is_bad(ep["path"]) \
                        and not library.stale(ep["path"]) and not TVWindow.file_missing(ep["path"]):
                    return ep
        return None

    def _replan_after_missing(self, ch, ts, path, unair=True):
        try:
            with self.lineup.lock:
                s = self.lineup.schedule(ch, ensure=False)
                s.reload()
                s.cut()                      # from the next programme; ensure() plans on
                if unair:
                    s.unair(ts)              # and this episode didn't air
                s.save()
                names = [ch.get("name")]
                now = time.time()
                for c in self.lineup.channels:   # other channels with it planned later
                    if c["id"] == ch["id"]:
                        continue
                    o = self.lineup.schedule(c, ensure=False)
                    o.reload()
                    if any(e.get("p") == path and e["s"] > now for e in o.data["entries"]):
                        o.cut(now)
                        o.save()
                        names.append(c.get("name"))
            K.log("Missing file: %s planned again from the next programme" % ", ".join(names), xbmc.LOGINFO)
        except Exception as exc:
            K.log_err("replan after a missing file: %s" % exc)

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

    def give_up(self, e, mark=True):
        """Kodi couldn't open this.  'Technical difficulties' for a few
        seconds, then something else from the channel fills the time.  mark=False
        (it opened, then stopped twice): not kept off the schedules."""
        path = e.get("p") or ""
        K.log_err("Couldn't play %s" % path)
        if mark and self.really_bad(path):
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

    def _substitute_pools(self, e=None):
        """Where a stand-in may come from, best first: the shows this channel airs
        (on its schedule), the rest of what it may air (its exclusions and other
        channels' home shows left out), everything its sources give (exclusions
        still out), then shows of the missing programme's own genre.  Never
        anything else: a cooking show on a comedy channel is worse than the
        'technical difficulties' card."""
        ch = self.ch
        if ch.get("type") == "extras":       # another extra that qualifies (cache only)
            films = library.extras_programme(K.setting_bool("extras_unrecognised", False))
            return [{"series": [], "singles": [dict(s, title=ch["name"], sub=s["title"])
                                               for f in films for s in f["segs"]]}]
        full = library.without(library.resolve(ch.get("sources") or []), ch.get("exclude"))
        try:
            mine = library.keep_titles(full, scheduler.assign.allowed_fn(self.lineup.assignment, ch["id"]))
        except Exception:
            mine = full
        try:
            airs = set(b.get("t", "").lower() for b in self.lineup.schedule(ch, ensure=False).data["blocks"]
                       if b.get("k") == "show")
        except Exception:
            airs = set()
        pools = [library.keep_titles(mine, lambda t, m: t in airs), mine, full]
        title = ((e or {}).get("t") or "").lower()
        genres = []
        if title and (e or {}).get("lb"):
            try:
                genres = next((s.get("genre") or [] for s in library.all_tvshows()
                               if s.get("title", "").lower() == title), [])
            except Exception:
                genres = []
        if genres:
            pools.append(library.without(library.resolve([{"type": "tvgenre", "value": g} for g in genres]),
                                         ch.get("exclude")))
        return pools

    def _substitute_pick(self, avoid, room, e=None):
        try:
            pools = self._substitute_pools(e)
        except Exception as exc:
            K.log_err("stand-in pools: %s" % exc)
            return None
        for pool in pools:
            items = [ep for ser in pool["series"] for ep in ser["episodes"]] + pool["singles"]
            items = [i for i in items if i["path"] not in avoid and not library.is_bad(i["path"])]
            long_enough = [i for i in items if i["dur"] >= room * 0.8]
            for _try in range(5):
                if not items:
                    break
                it = random.choice(long_enough or items)
                if not self.file_missing(it["path"]) and not library.stale(it["path"]):
                    return it
                items = [i for i in items if i is not it]
                long_enough = [i for i in long_enough if i is not it]
        return None

    def play_substitute(self, e, now):
        sub = self.sub
        if sub is None or not sub.get("p"):
            b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
            room = (b["e"] - now) if b else 1800
            avoid = {e["p"]} | ({sub["p"]} if sub and sub.get("p") else set()) | set((sub or {}).get("tried", []))
            it = self._substitute_pick(avoid, room, e)
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
            self.play_video(clip, self.clip_item(clip))
        except Exception as exc:
            K.log_err("static clip: %s" % exc)
            self.hold_until = 0

    POWER_ON = K.media("power_on.mp4")
    POWER_OFF = K.media("power_off.mp4")

    def play_power_on(self, ch=None):
        clip = self.POWER_ON
        self.power_on = True
        self.play_token += 1
        self.play_started_at = time.time()
        self.our_files.add(clip)
        self.set_mode("video")
        self.hold_until = time.time() + POWER_ON_LEN + 2.5   # shortened once the clip is on screen
        try:
            self.play_video(clip, self.clip_item(clip, ch))      # the channel coming on
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
            if K.load_state().get("tip_menu"):
                return
            if K.update_state({"tip_menu": 1}) is None:
                return
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
            self.play_video(clip, self.clip_item(clip))
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
        self.tone_off()
        try:
            xbmc.PlayList(getattr(xbmc, "PLAYLIST_MUSIC", 0)).clear()
        except Exception:
            pass

    def stop_player(self):
        self.tone_off()
        self.unqueue()
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
        if self.ch and self.ch.get("type") == "music":
            return                       # songs: no captions, resume points or learned lengths
        tok = self.play_token
        self.av_started_token = tok
        self.av_started_at = time.time()
        q = self.queued
        try:
            if q and self.requested(self.player.getPlayingFile()) == q["e"].get("p") and \
                    xbmc.PlayList(getattr(xbmc, "PLAYLIST_VIDEO", 1)).getposition() == q["pos"]:
                self.av_started_q = q["key"]       # Kodi moved on to the queued item by itself
        except Exception:
            pass
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
        if self.seek_after:
            self.seek_dts(path)
        self.start_measured(path)
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

    def start_measured(self, path):
        """At AV start of a tune-in partway in: how far behind the real clock the
        picture is.  Each sample says how long Kodi's open and seek took (the delay
        added + how far behind it still was); the learned delay is the median of the
        last 10 good ones, 0-3 s.  A sample more than 1.5 s off is Kodi landing on a
        keyframe away from the position asked for - not a delay - and is left out
        (unless 3 in a row agree: the device really is that much slower or faster)."""
        ask, self.start_ask = self.start_ask, None
        if not ask or not path or ask[0] != path:
            return
        e, added = ask[1], ask[2]
        try:
            behind = float(e.get("o", 0)) + (time.time() - e["s"]) - self.player.getTime()
        except Exception:
            return
        took = added + behind
        cls = type(self)
        if abs(behind) <= 1.5:
            cls.start_odd = []
            cls.start_good = (cls.start_good + [took])[-10:]
            note = ""
        else:
            cls.start_odd = (cls.start_odd + [took])[-3:]
            if len(cls.start_odd) == 3 and max(cls.start_odd) - min(cls.start_odd) <= 0.5:
                cls.start_good = (cls.start_good + cls.start_odd)[-10:]
                cls.start_odd = []
                note = " - three alike: taken"
            else:
                note = " - Kodi started at a keyframe away from it: left out"
        if cls.start_good:
            g = sorted(cls.start_good)
            cls.start_lag = max(0.0, min(3.0, g[len(g) // 2]))
        K.log("tune-in: %.1f s behind the clock at start (start delay now %.1f s)%s" % (
            behind, self.start_lag, note), xbmc.LOGINFO)

    def on_error(self):
        if self.closing:
            return
        self.play_started_at = 0  # let the watchdog react immediately

    def on_stopped(self):
        self.stopped_at = time.time()

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

    def extras_waiting(self):
        """BACKLOT is on its 'No programming' card: no extras found yet."""
        e = self.cur_entry
        return bool(self.ch and self.ch.get("type") == "extras" and e and e.get("k") == "card"
                    and e.get("sub") == "nosignal")

    def ask_look_for_extras(self):
        """OK on BACKLOT's 'No programming' card: ask first (Look now / Cancel);
        Cancel and Back leave the card as it was."""
        from . import manager
        if manager.confirm(_("It can take a few minutes the first time."), _("Look now"),
                           heading=_("Look for movie extras now?")):
            self.look_for_extras()

    def look_for_extras(self):
        """Look for movie extras (the viewer chose it: nothing is listed or
        measured on a channel change)."""
        from . import manager
        manager.look_for_extras()
        try:
            self.lineup.schedule(self.ch)       # extras found: the schedule rebuilds once
        except Exception as exc:
            K.log_err("extras schedule: %s" % exc)
        self.cur_key = None                     # tune in again where the schedule is now
        self.guide_pending = True

    def card_for(self, e, now):
        sched = self.lineup.schedule(self.ch, ensure=False)
        nb = sched.next_block(now)
        sub = e.get("sub")
        if sub == "nosignal" and self.ch.get("type") == "extras":
            if library.extras_scanned():        # looked already: OK wouldn't help, Check extras says why
                self.card(self.ch["name"], _("No programming"), _("No movie extras to air"),
                          _("See Settings > Tools > Check extras"))
            else:
                self.card(self.ch["name"], _("No programming"), _("No movie extras to air yet"),
                          _("Press OK to look for movie extras"))
        elif sub == "nosignal":
            self.card(self.ch["name"], _("No programming"), _("Add sources to this channel in the Channel Manager"), "")
        elif sub == "next" and nb and self.up_next(nb, now):
            return
        elif sub == "next" and nb:
            t = library.on_air(nb["t"]) + (("  -  " + nb["sub"]) if nb.get("sub") else "")
            self.card(_("UP NEXT"), t, _("at %s") % fmt_time(nb["s"]), self.ch["name"])
        elif self.station_id(now):
            return
        else:
            line = ""
            if nb:
                line = _("Coming up at %s: %s") % (fmt_time(nb["s"]), library.on_air(nb["t"]))
            self.card(_("You're watching"), self.ch["name"], _("We'll be right back"), line)
        self.stop_player()
        self.set_mode("card")

    def up_next(self, nb, now):
        """The Up next card (ads.upnext_card): the next programme's picture, title,
        episode or film details, synopsis (Boombox: the block's artists), start time,
        channel and a live countdown (upnext_tick).  False if it couldn't be made."""
        try:
            sched = self.lineup.schedule(self.ch, ensure=False)
            first = sched.entry_at(nb["s"] + 0.5) or {}
            br = stations.brand(self.ch, nb["s"])
            chlogo = br["logo"]
            if not ads.logo_usable(chlogo):
                chlogo = ""
            c = ads.upnext_card(self.ch, self.ch["number"], br["name"], nb, nb["s"], fmt_time(nb["s"]),
                                first.get("p") if first.get("k") == "show" else "", chlogo)
            if self._ad_slots is None:
                self._ad_slots = ads.Slots()
            ads.apply_upnext(self, c, self._ad_slots, time.time())
        except Exception as exc:
            K.log_err("up next: %s" % exc)
            return False
        self.upnext_at = nb["s"]
        self.upnext_shown = int(math.ceil(nb["s"] - time.time()))
        self.stop_player()
        self.set_mode("upnext")
        return True

    upnext_at = 0
    upnext_shown = None
    squeezed = False
    squeeze_checked = 0

    def squeeze_tick(self, now):
        """Squeezed credits: when the episode's file reaches its end credits (the
        schedule's "cr", from its chapters) the picture shrinks into a window and the
        Up next panel comes in; the credits keep their own sound, nothing restarts.
        Tuned in mid-credits: at once.  The end break follows when the file ends."""
        if self.squeezed:
            left = int(math.ceil(self.upnext_at - now))
            if left != self.upnext_shown and self._ad_slots is not None:
                self.upnext_shown = left
                self._ad_slots.fill(self, ads.countdown(self.upnext_at, now, "squeeze"), (ads.SLOT_CLOCK,))
            return
        e = self.cur_entry
        if not e or e.get("k") != "show" or not e.get("cr") or now - self.squeeze_checked < 0.25:
            return
        self.squeeze_checked = now
        # Right after a new item starts Kodi still plays (or reports) the file before it:
        # getTime() is then that file's position (N2: 8590 s in a 1554 s episode), which
        # squeezed at tune-in.  Only this entry's file, after its AV start, at a position
        # inside it.  tune() runs a tick before start_entry: the entry is still the old
        # channel's then (cur_key None), and its file still plays.
        ck = self.cur_key
        if not isinstance(ck, tuple) or ck[0] != self.ch.get("id") or self.av_started_token != self.play_token:
            return
        try:
            if not (self.playing_ours() and self.player.isPlayingVideo()):
                return
            if self.requested(self.player.getPlayingFile()) != e.get("p"):
                return
            pos = self.player.getTime()
            total = self.player.getTotalTime()
        except Exception:
            return
        if pos < float(e["cr"]) - 0.3 or not total or pos > total + 2:
            return
        try:
            sched = self.lineup.schedule(self.ch, ensure=False)
            nb = sched.next_block(now)
            if not nb or nb.get("k") == "offair":
                self.squeeze_checked = now + 60     # nothing to announce: the station signs off
                return
            first = sched.entry_at(nb["s"] + 0.5) or {}
            br = stations.brand(self.ch, nb["s"])
            c = ads.squeeze_card(self.ch, self.ch["number"], br["name"], nb, nb["s"], fmt_time(nb["s"]),
                                 first.get("p") if first.get("k") == "show" else "")
            if self._ad_slots is None:
                self._ad_slots = ads.Slots()
            ads.apply_squeeze(self, c, self._ad_slots, now)
        except Exception as exc:
            K.log_err("squeeze: %s" % exc)
            self.squeeze_checked = now + 3600      # not again for this item
            return
        self.upnext_at = nb["s"]
        self.upnext_shown = None
        self.squeezed = True
        if self.fs_state != "off":
            self.fs_leave()                  # captions' full-screen player: back to the TV window
        self.setProperty("squeeze", "1")
        K.log("squeezed credits at %.1f s: up next %s" % (pos, nb.get("t")), xbmc.LOGINFO)

    def unsqueeze(self):
        if self.squeezed or self.getProperty("squeeze"):
            self.squeezed = False
            self.setProperty("squeeze", "")
        self.squeeze_checked = 0

    def upnext_tick(self, now):
        """The countdown, once a second while the Up next card is on."""
        left = int(math.ceil(self.upnext_at - now))
        if left == self.upnext_shown or self._ad_slots is None:
            return
        self.upnext_shown = left
        self._ad_slots.fill(self, ads.countdown(self.upnext_at, now), (ads.SLOT_CLOCK,))

    def station_id(self, now):
        """The station ID card: the channel's logo, number, name and tagline
        (ads.station_card), silent, its motion looping while the break lasts.
        False if it couldn't be made (the plain card then)."""
        try:
            br = stations.brand(self.ch, now)
            logo = br["logo"]
            if not ads.logo_usable(logo):
                logo = ""                       # missing, or web art not cached: the no-logo layout
            c = ads.station_card(br["name"], self.ch["number"], logo, stations.tagline(self.ch, now),
                                 ads.genre_line(self.ch))
            if self._ad_slots is None:
                self._ad_slots = ads.Slots()
            ads.apply_card(self, c, self._ad_slots)
        except Exception as exc:
            K.log_err("station ID: %s" % exc)
            return False
        self.stop_player()
        self.set_mode("station")
        return True

    def signoff(self, e, now):
        """The sign-off card ("This concludes our broadcast day"): the station ID
        card's layout and machinery (mode station), silent, with when the off-air
        hours end.  The plain card if it couldn't be made."""
        resume = e.get("r")
        if not resume:
            b = self.lineup.schedule(self.ch, ensure=False).block_at(now)
            resume = b["e"] if b else None
        when = fmt_time(resume) if resume else ""
        try:
            br = stations.brand(self.ch, now)
            logo = br["logo"]
            if not ads.logo_usable(logo):
                logo = ""
            c = ads.signoff_card(br["name"], self.ch["number"], logo, stations.tagline(self.ch, now),
                                 ads.genre_line(self.ch), when)
            if self._ad_slots is None:
                self._ad_slots = ads.Slots()
            ads.apply_card(self, c, self._ad_slots)
            self.set_mode("station")
        except Exception as exc:
            K.log_err("sign-off card: %s" % exc)
            self.card(self.ch["name"], _("This concludes our broadcast day"),
                      (_("We return at %s") % when) if when else "", "")
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
        for prop in ("banner", "bug", "static", "toast", "osd", "d1", "d2", "d3", "mvcap"):
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
            title = library.on_air(b["t"])
            if b.get("rr"):
                title += " " + _("(R)")           # a summer rerun
            self.setProperty("now_title", title)
            if b.get("sub"):
                sub = " ".join(x for x in (b.get("lb", ""), b["sub"]) if x)
            else:
                # no episode name: the line stays empty (never a bare "S01E02");
                # a film's year, left out of its title, goes here as small text
                sub = scheduler_year(b["t"]) if title != b["t"] else ""
            self.setProperty("now_sub", sub)
            self.setProperty("now_time", "%s - %s" % (fmt_time(b["s"]), fmt_time(b["e"])))
        else:
            for k in ("now_title", "now_sub", "now_time"):
                self.setProperty(k, "")
        nb = sched.next_block(now)
        self.setProperty("next_line", (_("Next: %s  %s") % (fmt_time(nb["s"]), library.on_air(nb["t"]))) if nb else "")
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
            if not library.listing_ready():
                self.guide_next = now + 4         # details still being read: fill them in (in place) soon
        if now >= self.promo_next and self.promos:
            self.setProperty("guide_promo", self.promos[0])
            self.promos = self.promos[1:] + self.promos[:1]
            self.promo_next = now + 8
        self.top_tick(now)

    # ----------------------------------------------------------- the guide's top half
    # Text and the guide's music, as in 1.2.0.  Guide stage 3 played trailers, promos and
    # commercials there in a small video window; dropped 18 Nov 2026: a second video
    # control halved the TV window's redraw rate on the N2 (stop motion), and the N2's
    # hardware video layer doesn't follow a zoom on the one video control
    # (.claude/CLAUDE.md, Hard-won lessons).
    guide_on = None              # the guide channel's id while it's on screen
    top = None                   # "text" once the guide's music is on

    def top_reset(self):
        self.top = None

    def top_tick(self, now):
        if self.top != "text":
            self.top = "text"
            self.background_audio(K.setting("guide_music_path"))

    def crawl_start(self):
        """The grid crawls up at a constant speed and never pauses: list 50 is a
        wraplist whose linear scroll lasts longer than a step, and this thread moves
        it one row each step by the clock, so every move takes over the one still
        running and the steps blend into one motion."""
        self.crawl_token += 1
        t = threading.Thread(target=self.crawl_loop,
                             args=(self.crawl_token, guide.speed(K.setting_int("guide_speed", 1))),
                             name="cb42-crawl")
        t.daemon = True
        t.start()

    def crawl_loop(self, token, step):
        nxt = time.time() + 1.0
        while not self.closing and token == self.crawl_token and self.prop_mode == "guide":
            wait = nxt - time.time()
            if wait > 0:
                if self.monitor.waitForAbort(min(wait, 0.5)):
                    return
                continue
            nxt += step
            if time.time() > nxt:                 # held up (a dialog, a busy box): no catching up
                nxt = time.time() + step
            try:
                # only in our own window: Control.Move goes to the window that has focus
                if xbmcgui.getCurrentWindowDialogId() == 9999 and \
                        (not self.win_id or xbmcgui.getCurrentWindowId() == self.win_id):
                    xbmc.executebuiltin("Control.Move(50,1)")
            except Exception:
                pass

    @staticmethod
    def block_entry(sched, b):
        """The first programme entry of a block (None if there's none)."""
        t = b["s"] + 0.01
        for _i in range(12):
            e = sched.entry_at(t)
            if e is None or e["s"] >= b["e"]:
                return None
            if e.get("k") == "show" and e.get("p"):
                return e
            t = e["e"] + 0.001
        return None

    def block_file(self, sched, b):
        """The first programme file of a block (for its listing details)."""
        e = self.block_entry(sched, b)
        return e["p"] if e else ""

    def listing(self, sched, b, prefix, width, kids_ch=False):
        """(text, font, two-line text, colour category) of one listing cell."""
        title = prefix + library.on_air(b["t"])
        extra, cat = [], ""
        if b.get("k") == "show":
            info = library.listing_info(self.block_file(sched, b))
            if info and info.get("kind") == "movie" and info.get("year") and \
                    title.endswith("(%s)" % info["year"]):
                info = dict(info, year=0)             # a shared name keeps its year in the title
            extra = guide.details(info, rerun=bool(b.get("rr")), special=b.get("sp") or "")
            cat = guide.category(info, kids_ch)
        return guide.fit_cell(title, extra, width) + (cat,)

    GUIDE_MIN_ROWS = 10       # the list shows 8 rows; fewer items and Kodi adds copies of its own
    ROW_KEYS = ("nfit", "name2", "rowbg", "ad", "c1", "c1f", "c12", "c1k", "c2", "c2f", "c22", "c2k",
                "c3", "c3f", "c32", "c3k")

    def fill_guide(self, now):
        t0 = scheduler.floor_slot(now, 1800)
        cols = [t0, t0 + 1800, t0 + 3600]
        title = K.setting("guide_title", _("CableBox 42 Program Guide"))
        self.setProperty("guide_title", title)
        for i, c in enumerate(cols):
            self.setProperty("g_t%d" % (i + 1), fmt_time(c))
        rows = []                     # (shape key, label, label2, {property: value})
        guide_promos = []
        guide_ch = None
        for ch in self.lineup.channels:
            if ch["type"] == "guide":
                guide_ch = guide_ch or ch
                continue
            # never build schedules here - that froze the guide after upgrades
            sched = self.lineup.schedule(ch, ensure=False)
            br = stations.brand(ch, now)
            call = guide.short_call(br["name"], br["call"])
            nfit, name2 = guide.call_fit(call)
            props = {"rt": "ch", "nfit": nfit, "name2": name2,
                     "rowbg": "guide_row_a.png" if len(rows) % 2 == 0 else "guide_row_b.png"}
            if sched.block_at(now) is None:
                self.guide_pending = True
                props["c1"] = _("Updating listings...")
                props["c1f"] = "font27"
            else:
                kids_ch = guide.kids_channel(ch)
                for i, c in enumerate(cols):
                    b = sched.block_at(c + 1)
                    if not b:
                        continue
                    prefix = ""
                    if b["s"] < c - 60:
                        prefix = _("(cont.) ") if i == 0 else ">>> "
                    txt, font, two, cat = self.listing(sched, b, prefix, guide.CELL_W[i], kids_ch)
                    props.update({"c%d" % (i + 1): txt, "c%df" % (i + 1): font, "c%d2" % (i + 1): two,
                                  "c%dk" % (i + 1): cat})
                for b in sched.blocks_between(now, now + 4 * 3600):
                    if b["s"] > now and b.get("k") == "show" and b["e"] - b["s"] >= 3600:
                        guide_promos.append(_("Coming up at %s on %s %s:  %s") % (
                            fmt_time(b["s"]), ch["number"], ch["name"], library.on_air(b["t"])))
                        break
            rows.append((ch["id"], str(ch["number"]), call, props))
        # the scroll-ad rows after the last channel: the guide's title, then 1-3 ads
        # (the viewer's own guide.txt lines first, then the built-in ones)
        count = guide.ad_count(len(rows))
        own = guide.own_ads(stations.brand(guide_ch, now)["folder"] if guide_ch else "")
        picks = random.sample(own, min(len(own), count))
        if len(picks) < count:
            picks += random.sample(guide.builtin_ads(), count - len(picks))
        rows.append(("hdr", "", "", {"rt": "hdr", "ad": title}))
        rows += [("ad%d" % i, "", "", {"rt": "ad", "ad": t}) for i, t in enumerate(picks)]
        for _k, _l, _l2, p in rows:
            for k in self.ROW_KEYS:
                p.setdefault(k, "")
        # a wraplist shorter than the screen pads itself with copies that an in-place
        # refresh doesn't reach: repeat the cycle ourselves instead
        rows = rows * int(math.ceil(float(self.GUIDE_MIN_ROWS) / len(rows)))
        shape = [r[0] for r in rows]
        try:
            lst = self.getControl(50)
            if shape == self.guide_shape and lst.size() == len(rows):
                # the same rows: change them in place, so the 5-minute refresh never jumps the crawl
                for i, (_k, label, label2, props) in enumerate(rows):
                    li = lst.getListItem(i)
                    if li.getLabel() != label:
                        li.setLabel(label)
                    if li.getLabel2() != label2:
                        li.setLabel2(label2)
                    for k, v in props.items():
                        if li.getProperty(k) != v:
                            li.setProperty(k, v)
            else:
                items = []
                for _k, label, label2, props in rows:
                    li = xbmcgui.ListItem(label, label2)
                    for k, v in props.items():
                        li.setProperty(k, v)
                    items.append(li)
                lst.reset()
                lst.addItems(items)
                self.guide_shape = shape
        except Exception as exc:
            K.log_err("guide list: %s" % exc)
        random.shuffle(guide_promos)
        if not guide_promos:
            guide_promos = [_("Thanks for watching CableBox 42"), _("Press OK to pick a channel")]
        self.promos = guide_promos

    def background_audio(self, folder):
        self.tone_off()
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
        if self.extras_waiting():
            opts.append(("measure", _("Look for movie extras")))
        opts += [("sleep", _("Sleep timer")), ("cablebox", _("CableBox menu")), ("off", _("Turn off TV"))]
        b = self.lineup.schedule(self.ch, ensure=False).block_at(time.time()) if self.ch else None
        hide = b["t"] if b and b.get("k") == "show" and self.ch.get("type") not in ("extras", "musicvideos", "music")             else None
        if hide:
            opts.append(("hide", _("Don't air '%s' on %s") % (hide, self.ch["name"])))
        i = xbmcgui.Dialog().contextmenu([o[1] for o in opts])
        if i < 0:
            return
        key = opts[i][0]
        if key == "measure":
            self.look_for_extras()          # chosen from the menu: an explicit choice, no second question
        elif key == "hide":
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
        elif key == "cablebox":
            self.shutdown(power_off=True, how="menu")   # a full turn-off; the menu never opens over the TV
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

    FILE = os.path.join(K.PROFILE, "gui_sounds.json")     # {"orig": n, "active": bool}; GuiSounds writes it alone

    def _saved(self):
        """The backup file (and, once, the old state.json key) as {"orig", "active"};
        None when the file is there but can't be read."""
        try:
            d = K._read_state(self.FILE)
        except K.StateUnreadable as exc:
            K.log_err("gui sounds: %s unreadable (%s)" % (os.path.basename(self.FILE), exc))
            return None
        legacy = K.load_state().get("gui_sounds_orig")      # builds before ~all10 kept it in state.json
        if legacy is not None and not d.get("active"):
            d = {"orig": int(legacy), "active": True}
        return d

    def start(self):
        """Once, before anything plays: Always, for the whole time the TV is on.  The
        viewer's own value goes to gui_sounds.json first (only this class writes it, so
        nothing else can wipe it); a session Kodi closed before it ended left
        "active": true there, and its "orig" is the one to keep."""
        cur = self._get()
        if cur is None:
            return
        saved = self._saved()
        if saved and saved.get("active") and saved.get("orig") is not None:
            orig = int(saved["orig"])               # left over: Kodi closed while CableBox was on
        else:
            orig = cur
        self.orig = orig
        if saved is not None:                       # never written over when it couldn't be read
            K.update_state({"orig": orig, "active": True}, path=self.FILE)
        K.update_state({"gui_sounds_orig": K.DELETE})
        K.log("gui sounds: viewer's setting %d (now %d)" % (orig, cur), xbmc.LOGINFO)
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
        orig = self.orig
        saved = self._saved()                       # read again: right even if start's read failed
        if saved and saved.get("active") and saved.get("orig") is not None:
            orig = int(saved["orig"])
        if orig is not None and orig != GUI_SOUNDS_ALWAYS:
            self._set(orig)
        if saved is not None and orig is not None:
            K.update_state({"orig": orig, "active": False}, path=self.FILE)


last_exit = None     # how the last TV session ended (see run())


def run(channel=None):
    """Turn the TV on until the viewer turns it off.  Returns how it ended:
    "back" (Back / Stop / Turn off TV: return to where it was started from),
    "menu" (Menu > CableBox menu: open the main menu), "sleep" (the sleep
    timer) or "away" (the viewer left the window, or Kodi is closing)."""
    global last_exit
    K.ensure_dirs()
    win = TVWindow("script-cablebox42-tv.xml", K.ADDON_PATH, "Default", "1080i")
    win.wanted_channel = channel
    win.doModal()
    win.shutdown()
    # a turn-off from the TV's own thread (sleep timer) may still be tidying up:
    # finish before a menu or the next TV can open, so nothing of this TV stops the next one
    win.finished.wait(6)
    for t in win.threads:
        if t is not threading.current_thread():
            t.join(3)
    how = win.exit_how
    if xbmc.Monitor().abortRequested():
        how = "away"
    del win
    last_exit = how
    return how

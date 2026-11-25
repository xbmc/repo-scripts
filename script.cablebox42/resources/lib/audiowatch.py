"""Stuck HDMI audio after a DTS passthrough start: watch Kodi's log and get the sound back.

What happens (N2, CoreELEC 21.3, 18 Nov): opening a DTS-HD MA file partway in (StartOffset) can
make Kodi's passthrough parser misread the first frame ("SyncDTS - dts stream detected (6
channels, ... syncword: 0x5b48fc8e ... framesize 3612)"; good opens of the same 8-channel
DTS-HD MA stream say "dtsHD MA ... 0x41a29547").  Planet Earth II S01E03 opened at 19:05-19:07
does it every time, in Kodi's own player too.  ALSA can't open that layout ("Unable to open the
requested channel layout"), Kodi's audio engine retries every 0.5 s for as long as Kodi runs,
whatever plays next, and the player blocks on its audio: frozen pictures, files that won't
start, and (Kodi's own player, nothing stopping the file) out of memory and a crash in minutes.

The TV no longer opens DTS files partway in (tv.dts_risky: open at 0, then seek), which never
wedged.  This is the safety net for anything else: the service tails kodi.log (`Watch`, its
own thread).  Nothing inside a running Kodi clears the wedge - passthrough off and on, and
another output device and back, were both tried on the N2 while it was stuck - so the only
cure is a restart: with the TV on, CableBox restarts Kodi at once and the service tunes the
same channel in again when Kodi is back (state `resume_tv`); with the TV off it asks."""
import os
import re
import threading
import time

import xbmc
import xbmcgui
import xbmcvfs

from . import kodiutil as K
from .kodiutil import _

WEDGE = "Unable to open the requested channel layout"
SYNC_RE = re.compile(r"CAEStreamParser::SyncDTS - (\S+(?: \S+)?) stream detected .*syncword: (0x[0-9a-f]+)")
GOOD_CORE = ("0x7ffe8001", "0xfe7f0180", "0x1fffe800", "0xff1f00e8")   # the next core frame
POLL = 0.1                   # s between log reads
TRIGGER = 4                  # layout errors in TRIGGER_WINDOW s (Kodi retries every 0.5 s) ...
TRIGGER_WINDOW = 3.0
TRIGGER_BAD_SYNC = 2         # ... or fewer right after a misread DTS frame
MAX_RESTARTS = 3             # an hour (state `audio_restarts`)
RESUME_WITHIN = 300          # s: the TV comes back on only after a restart this recent


def log_path():
    return os.path.join(xbmcvfs.translatePath("special://logpath"), "kodi.log")


def bad_sync(line):
    """A plain 'dts' read whose following word isn't the next core frame: a misread
    (DTS-HD's own reads say 'dtsHD ...' and are fine)."""
    m = SYNC_RE.search(line)
    return bool(m) and m.group(1) == "dts" and m.group(2) not in GOOD_CORE


def recover(why):
    """Restart Kodi (the TV on: at once, coming back on the same channel; off: if the
    viewer says so).  False when it didn't (said no, or too many restarts this hour)."""
    home = xbmcgui.Window(10000)
    now = time.time()
    recent = [t for t in (K.load_state().get("audio_restarts") or []) if now - t < 3600]
    if len(recent) >= MAX_RESTARTS:
        K.log_err("audio watch: %s - not restarting: %d restarts in the last hour" % (why, len(recent)))
        return False
    tv_on = home.getProperty("cablebox42.running") == "1"
    K.log("audio watch: %s - Kodi's sound output is stuck until Kodi restarts" % why, xbmc.LOGWARNING)
    if tv_on:
        ch = home.getProperty("cablebox42.channel")
        K.update_state({"resume_tv": {"ch": int(ch) if ch.isdigit() else None, "at": now},
                        "audio_restarts": recent + [now]})
        xbmcgui.Dialog().notification(K.ADDON_NAME, _("Sound output stuck - restarting Kodi"),
                                      xbmcgui.NOTIFICATION_WARNING, 4000, False)
        xbmc.sleep(2500)
    else:
        if not xbmcgui.Dialog().yesno(_("Sound output stuck"),
                                      _("Kodi's sound stopped after a DTS programme and stays off until Kodi restarts."),
                                      nolabel=_("Not now"), yeslabel=_("Restart Kodi")):
            K.log("audio watch: restart declined", xbmc.LOGINFO)
            return False
        K.update_state({"audio_restarts": recent + [now]})
    K.log("audio watch: restarting Kodi", xbmc.LOGWARNING)
    xbmc.executebuiltin("RestartApp")
    return True


def resume_tv():
    """After an audio restart with the TV on: the TV back on the same channel."""
    st = K.load_state().get("resume_tv")
    if not st:
        return None
    K.update_state({"resume_tv": K.DELETE})
    if time.time() - float(st.get("at") or 0) > RESUME_WITHIN:
        return None
    return st.get("ch") or 0


class Watch(object):
    """Tails kodi.log from its end; feed() takes lines (tests feed them directly)."""

    def __init__(self, path=None):
        self.path = path or log_path()
        self.pos = None
        self.ino = None
        self.errors = []             # times of recent layout errors
        self.bad_at = 0.0            # last misread DTS frame
        self.asked = 0.0             # last restart (or question)
        self.partial = ""

    def read(self):
        try:
            st = os.stat(self.path)
        except OSError:
            return []
        if self.pos is None or st.st_ino != self.ino or st.st_size < self.pos:
            if self.pos is None:
                self.pos = st.st_size           # start at the end: old wedges are history
            else:
                self.pos = 0                    # a new log (Kodi restarted)
            self.ino = st.st_ino
        if st.st_size == self.pos:
            return []
        with open(self.path, "rb") as f:
            f.seek(self.pos)
            data = f.read(1 << 20)
        self.pos += len(data)
        text = self.partial + data.decode("utf-8", "replace")
        lines = text.split("\n")
        self.partial = lines.pop()
        return lines

    def feed(self, lines, now=None):
        """Returns why a restart is due ('' if none)."""
        now = now or time.time()
        for l in lines:
            if "SyncDTS" in l and bad_sync(l):
                self.bad_at = now
                K.log("audio watch: Kodi misread a DTS frame: %s" % l.strip()[-140:], xbmc.LOGWARNING)
            elif WEDGE in l:
                self.errors.append(now)
        self.errors = [t for t in self.errors if now - t < TRIGGER_WINDOW]
        n = len(self.errors)
        if now - self.asked < 600:           # asked (or restarting) lately: once per 10 min
            return ""
        if n >= TRIGGER or (n >= TRIGGER_BAD_SYNC and now - self.bad_at < 5.0):
            return "DTS misread, audio output stuck" if now - self.bad_at < 5.0 else "audio output stuck"
        return ""


def run(monitor=None):
    """The service's thread: never stops before Kodi does."""
    monitor = monitor or xbmc.Monitor()
    w = Watch()
    while not monitor.abortRequested():
        try:
            why = w.feed(w.read())
            if why:
                w.asked = time.time()
                recover(why)
        except Exception as exc:
            K.log_err("audio watch: %s" % exc)
            if monitor.waitForAbort(5):
                return
        if monitor.waitForAbort(POLL):
            return


def start():
    t = threading.Thread(target=run, name="cablebox42-audiowatch")
    t.daemon = True
    t.start()
    return t

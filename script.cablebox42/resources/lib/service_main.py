"""Background helper (called from service.py): optional start-on-boot, and
keeps schedules topped up so tuning and the guide are instant."""
import os
import time

import xbmc
import xbmcgui

from . import kodiutil as K


TOOL_BUSY = "script.cablebox42.tool"     # manager.TOOL_BUSY (the menus aren't imported up front)
SPECIALS_REPLAN = os.path.join(K.PROFILE, "specials_replan.json")   # specials_editor.REPLAN_FILE


LIBRARY_SETTLE = 30         # s after the last library scan/clean before a refresh
TUNE_QUIET = 4.0            # no chapter reading this soon after the TV opened a file (a channel change)
REPLAN_EVERY = 600          # chapters read for planned episodes: re-plan once the next 6 hours are all
                            # read, or 10 min after the first one not planned with yet


class Monitor(xbmc.Monitor):
    """Notes when Kodi's video library was scanned or cleaned (start-up scans and
    add-ons scanning on CoreELEC come in bursts: one refresh after the last)."""
    library_at = 0

    def onScanFinished(self, library):
        if library == "video":
            self.library_at = time.time()

    def onCleanFinished(self, library):
        if library == "video":
            self.library_at = time.time()


def run():
    monitor = Monitor()
    home = xbmcgui.Window(10000)
    from . import audiowatch
    audiowatch.start()                       # stuck HDMI audio after a DTS start: from Kodi's start, TV on or off

    def tv_running():
        return home.getProperty("cablebox42.running") == "1"

    def topup():
        if not os.path.exists(K.CHANNELS_FILE):
            return
        from . import scheduler, library
        lineup = scheduler.Lineup(K.schedule_cfg())
        lineup.ensure_all(abort=lambda: monitor.abortRequested() or tv_running())
        library.durations().save()

    def extras(dates=False):
        # movie Extras folders: listed and measured only here, while the TV is off.
        # Returns how many folders' lists of extras changed.
        from . import library
        library.EXTRAS_LAST["changed"] = 0
        library.extras_refresh(abort=lambda: monitor.abortRequested() or tv_running(), dates=dates)
        return library.EXTRAS_LAST["changed"]

    def extras_after_scan():
        # after a library scan or clean: every Extras folder's own date is looked at
        # now (a clip added to an Extras folder doesn't change the movie's folder),
        # and a Behind the scenes channel is planned again when something changed
        chans = []
        try:
            from . import channels as C
            chans = C.load()
        except Exception:
            pass
        if not any(c.get("type") == "extras" for c in chans):
            return
        if extras(dates=True) and not tv_running() and not home.getProperty(TOOL_BUSY):
            from . import manager
            K.log("Schedules: movie extras changed - refreshing", xbmc.LOGINFO)
            manager.refresh_now(quiet=True)

    def playing_file():
        try:
            player = xbmc.Player()
            if player.isPlaying():
                return player.getPlayingFile()
        except Exception:
            pass
        return ""

    def chapters_replan():
        # chapters read for planned episodes: their parts not on air yet are planned
        # again (keep my place; what's on air stays) - at most every 10 minutes while
        # the next 6 hours are still being read.  Main loop only (never alongside a top-up)
        from . import library
        new = library.CHAPTERS_NEW
        if new["n"] <= 0 or home.getProperty(TOOL_BUSY):
            return
        if reader_left[0] and time.time() - new["first"] < REPLAN_EVERY:
            return
        n = new["n"]
        new.update(n=0, first=0.0)
        K.log("Schedules: chapters read for %d planned episodes - refreshing" % n, xbmc.LOGINFO)
        from . import manager
        manager.refresh_now(quiet=True)

    reader_left = [0]
    status_shown = [None]

    def chapters_status_line(force=False):
        # Settings > Programming: "Chapters read: X of Y" (read-only)
        from . import library
        try:
            r, total = library.chapters_status()
        except Exception:
            return
        text = K._("%d of %d") % (r, total) if total else ""
        if force or text != status_shown[0]:
            status_shown[0] = text
            # a fresh Addon object (K.set_setting), never the service's K.ADDON: an object
            # made before the viewer's last OK in Settings writes its old values of every
            # setting back with this one (Promo look went back to Early-90s, 19 Nov)
            if K.setting("chapters_status") != text:
                K.set_setting("chapters_status", text)

    def chapter_reader():
        # Commercial breaks at chapter marks: each episode file's chapters, read once
        # (a thread of its own).  Kodi idle: as fast as reads stay quick.  The TV on:
        # the planned episodes airing in the next 6 hours first, gently, never within a
        # few seconds of the TV opening a file (a channel change).  Anything else
        # playing, a tool open, a busy CPU (Linux): paused.
        from . import library
        reader = library.ChapterReader()
        was_busy = False
        chapters_status_line(force=True)
        while not monitor.abortRequested():
            wait = 5.0
            try:
                busy = bool(home.getProperty(TOOL_BUSY))
                if busy:
                    library.chapter_cache().save()
                elif was_busy:
                    library.chapter_reload()             # Read now may have added to it
                    reader.queue = []
                    chapters_status_line()
                was_busy = busy
                on = tv_running()
                playing = playing_file()
                if busy or (playing and not on):
                    pass
                elif library.load_too_high():
                    wait = 10.0
                else:
                    try:
                        since = time.time() - float(home.getProperty("cablebox42.play_at") or 0)
                    except ValueError:
                        since = TUNE_QUIET
                    if on and since < TUNE_QUIET:
                        wait = TUNE_QUIET - since + 0.1
                    else:
                        f = reader.next(on, playing) if K.setting_bool("chapter_breaks", True) else None
                        if f:
                            wait = reader.read(f, on)
                        else:
                            wait = 30.0
                            if reader.minute(force=True):
                                chapters_status_line()
                        reader_left[0] = reader.left
                if reader.minute():
                    chapters_status_line()
            except Exception as exc:
                K.log_err("chapters failed: %s" % exc)
            if monitor.waitForAbort(wait):
                break
        try:
            library.chapter_cache().save()
        except Exception:
            pass

    def specials_pending():
        # Holidays and specials: the editor saved and asked for the affected channels
        # to be planned again (it never waits for that itself): within a second
        if os.path.exists(SPECIALS_REPLAN):
            try:
                from . import specials_editor
                specials_editor.run_pending(home.getProperty(TOOL_BUSY))
            except Exception as exc:
                K.log_err("specials re-plan failed: %s" % exc)

    def music_videos():
        # Boombox: length, frame rate, audio and tags of music videos not read yet
        from . import library
        library.musicvideos_refresh(abort=lambda: monitor.abortRequested() or tv_running(), recheck=True)

    K.ensure_dirs()
    try:
        from . import progress
        progress.repair_pending()            # resume points a crash/power cut left changed
    except Exception as exc:
        K.log_err("progress repair failed: %s" % exc)
    try:
        from . import captions
        captions.restore_leftovers()         # a Kodi setting the subtitle search left changed
    except Exception as exc:
        K.log_err("captions repair failed: %s" % exc)
    for key in ("weather_source", "weather_units"):  # 1.1 stored text, 1.3 uses numbers
        if not K.ADDON.getSetting(key).isdigit():
            K.set_setting(key, "0")
    if os.path.exists(K.CHANNELS_FILE) and not home.getProperty(TOOL_BUSY):
        # a new build of the add-on: breaks planned by the old one take the new
        # layout from each channel's next programme (keep my place; what's on air stays)
        try:
            from . import manager
            manager.refresh_if_changed(clips=False, quiet=True)
        except Exception as exc:
            K.log_err("refresh after an update failed: %s" % exc)
    try:
        resume = audiowatch.resume_tv()      # Kodi restarted for stuck sound with the TV on
    except Exception as exc:
        resume = None
        K.log_err("resume after an audio restart: %s" % exc)
    if resume is not None and os.path.exists(K.CHANNELS_FILE):
        for _tick in range(60):
            if monitor.waitForAbort(1):
                return
            if xbmc.getCondVisibility("Player.HasMedia"):
                break
            if xbmc.getCondVisibility("Window.IsActive(home)") and                     not xbmc.getCondVisibility("System.HasModalDialog"):
                K.log("audio watch: Kodi is back - the TV on again%s" % (" on %d" % resume if resume else ""),
                      xbmc.LOGINFO)
                xbmc.executebuiltin("RunScript(script.cablebox42,watch%s)" % (",%d" % resume if resume else ""))
                break
    elif K.setting_bool("autostart", False) and os.path.exists(K.CHANNELS_FILE):
        # wait for the home screen, then switch the TV on
        # Only right after Kodi starts, and never once the viewer has started
        # watching something else (otherwise stopping that video would land
        # them in CableBox).
        for _tick in range(60):
            if monitor.waitForAbort(1):
                return
            if xbmc.getCondVisibility("Player.HasMedia"):
                break
            if xbmc.getCondVisibility("Window.IsActive(home)") and \
                    not xbmc.getCondVisibility("System.HasModalDialog"):
                xbmc.executebuiltin("RunScript(script.cablebox42,watch)")
                break
    for _sec in range(90):
        specials_pending()
        if monitor.waitForAbort(1):
            return
    import threading
    threading.Thread(target=chapter_reader, name="cablebox42-chapters").start()
    from . import progress
    was_on = tv_running()
    idle = 0
    extras_due = False                       # a scan or clean happened: look at the Extras folders when the TV is off
    tick = 0
    while not monitor.abortRequested():
        tick += 1
        on = tv_running()
        if was_on and not on:
            # TV just switched off: confirm every resume point is back (twice,
            # in case Kodi was still writing when the TV closed)
            for wait in (10, 60):
                if monitor.waitForAbort(wait):
                    return
                progress.repair_pending()
        was_on = on
        if tick % 3 == 0 and not on and not home.getProperty(TOOL_BUSY) and \
                not home.getProperty("cablebox42.main_menu"):
            # settings changed from Kodi's own add-on settings (the CableBox menu and
            # its tools refresh on their own): apply them, never while the TV is on
            try:
                from . import manager
                manager.refresh_if_changed(clips=False, quiet=True)
            except Exception as exc:
                K.log_err("refresh after a settings change failed: %s" % exc)
        if monitor.library_at and time.time() - monitor.library_at >= LIBRARY_SETTLE \
                and not home.getProperty(TOOL_BUSY):
            # the library changed: new episodes, shows, movies, files gone.  Works
            # with the TV on too: a refresh never touches what's on air
            monitor.library_at = 0
            extras_due = True
            try:
                from . import manager
                manager.refresh_if_changed(clips=False, quiet=True, lib=True)
            except Exception as exc:
                K.log_err("refresh after a library change failed: %s" % exc)
        if extras_due and not on and not home.getProperty(TOOL_BUSY):
            extras_due = False
            try:
                extras_after_scan()
            except Exception as exc:
                K.log_err("extras after a library change failed: %s" % exc)
        try:
            chapters_replan()
        except Exception as exc:
            K.log_err("re-plan after chapters failed: %s" % exc)
        if not on and idle <= 0:
            try:
                progress.repair_pending()
                topup()
            except Exception as exc:
                K.log_err("schedule top-up failed: %s" % exc)
            try:
                music_videos()
            except Exception as exc:
                K.log_err("music video scan failed: %s" % exc)
            try:
                extras()
            except Exception as exc:
                K.log_err("extras scan failed: %s" % exc)
            idle = 20 * 60
        for _sec in range(5):
            specials_pending()
            if monitor.waitForAbort(1):
                return
        idle -= 5

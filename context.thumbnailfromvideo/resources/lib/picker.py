"""Overlay (skins/Default/1080i/script-framethumb.xml) shown over the playing video:
seek with the slider/buttons, then "Use this frame" captures the current frame."""
import json
import os
import threading
import time
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import deinterlace, frametime, png

XML_FILE = 'script-framethumb.xml'

# control ids (see the skin XML)
SLIDER = 10
LBL_TITLE, LBL_TIME = 100, 101
BTN_PLAYPAUSE, BTN_USE, BTN_CANCEL, BTN_SETTINGS = 25, 30, 31, 32
JPG_MAX_WIDTH = 1280  # width of the <video>-thumb.jpg (Kodi's own thumbnail size)
POINTERS = (33, 34)   # little triangle joining "Make thumbnail" to the nub
USE_FACES = (35, 36)  # its face (selected / not), shown selected with the nub too
# geometry from the skin XML (1080i): nub centre runs from NUB_X0 to
# NUB_X0 + NUB_SPAN; the button is kept between PANEL_X0 and PANEL_X1
NUB_X0, NUB_SPAN = 48, 1828
USE_W, USE_Y, POINTER_Y = 260, 942, 932
PANEL_X0, PANEL_X1 = 36, 1884
# seconds, or 'frame+'/'frame-' for one-frame steps
BUTTON_SEEKS = {21: -10, 22: -1, 23: -0.1, 26: 0.1, 27: 1, 28: 10}

# Kodi action ids handled as hotkeys (navigation is left to the window)
A_PREVIOUS_MENU, A_NAV_BACK, A_STOP = 10, 92, 13
A_PAUSE, A_PLAY, A_PLAYPAUSE = 12, 79, 229
A_PAGE_UP, A_PAGE_DOWN = 5, 6
A_FORWARD, A_REWIND = 77, 78
A_NEXT_ITEM, A_PREV_ITEM = 14, 15
A_NUM_0 = 58  # 58..67 = number keys 0..9
A_SELECT = 7  # OK / Enter (a mouse click is a different action, so it still just seeks)
BACK_ACTIONS = (A_PREVIOUS_MENU, A_NAV_BACK, A_STOP)
PAUSE_ACTIONS = (A_PAUSE, A_PLAY, A_PLAYPAUSE)
HOTKEY_SEEKS = {A_PAGE_UP: 60, A_PAGE_DOWN: -60,
                A_FORWARD: 'frame+', A_REWIND: 'frame-',
                A_NEXT_ITEM: 'frame+', A_PREV_ITEM: 'frame-'}
# remote buttons Kodi also handles itself (fast forward / rewind / skip):
# for GUARD_SECONDS after one, the picker puts the video back on its frame
REMOTE_SEEKS = (A_FORWARD, A_REWIND, A_NEXT_ITEM, A_PREV_ITEM)
GUARD_SECONDS = 2.5
# Kodi's own seek handler at work (the picker's seekTime() does not set these)
KODI_SEEKING = 'Player.Seeking | Player.Forwarding | Player.Rewinding'
# Kodi's own seeks move a second or more; a smaller difference is just the
# player reporting a time a frame or so off the picker's target (correcting
# that would make the picture flip between two frames / fields)
KODI_JUMP = 0.5


DEFAULT_FOCUS = 'FF12A0C7'  # Estuary's default "button_focus"

# Home-window properties set by the backup / restore tools (folderzip.py):
# while BUSY is set the picker hides itself; EXIT makes it close.
BUSY_PROP = 'context.thumbnailfromvideo.tool_busy'
EXIT_PROP = 'context.thumbnailfromvideo.exit_picker'


def _skin_color_map(path, colors):
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return
    for node in root.iter('color'):
        if node.get('name') and node.text:
            colors[node.get('name')] = node.text.strip()


def skin_focus_color():
    """The current skin's focus colour, following its colour theme
    (Settings > Interface > Skin > Colours), e.g. red for Estuary "maroon"."""
    colors = {}
    skin_dir = xbmcvfs.translatePath('special://skin/')
    folder = os.path.join(skin_dir, 'colors')
    _skin_color_map(os.path.join(folder, 'defaults.xml'), colors)
    try:
        resp = json.loads(xbmc.executeJSONRPC(json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.GetSettingValue',
            'params': {'setting': 'lookandfeel.skincolors'}})))
        theme = resp.get('result', {}).get('value') or ''
    except Exception:
        theme = ''
    if theme and theme.upper() != 'SKINDEFAULT':
        name = theme if theme.lower().endswith('.xml') else theme + '.xml'
        _skin_color_map(os.path.join(folder, name), colors)
    value = colors.get('button_focus', DEFAULT_FOCUS)
    for _ in range(5):  # a colour may refer to another named colour
        if value in colors and colors[value] != value:
            value = colors[value]
    value = value.lstrip('#')
    if len(value) == 6:
        value = 'FF' + value
    try:
        int(value, 16)
    except ValueError:
        return DEFAULT_FOCUS
    return value.upper() if len(value) == 8 else DEFAULT_FOCUS


def set_open_video_name(player):
    """Show the open video's file name on the right of the settings button
    "Clear thumbnail cache (open video only)" (cleared with player=None)."""
    name = ''
    if player is not None:
        try:
            path = player.getPlayingFile()
        except RuntimeError:
            path = ''
        name = path.replace('\\', '/').rstrip('/').rsplit('/', 1)[-1]
    try:
        xbmcaddon.Addon().setSetting('open_video_name', name)
    except Exception:
        pass


def lighter(argb, amount=0.6):
    """Mix a colour with white (used for the focused slider knob)."""
    a, rgb = argb[:2], [int(argb[i:i + 2], 16) for i in (2, 4, 6)]
    return a + ''.join('%02X' % int(c + (255 - c) * amount) for c in rgb)


def fmt_time(t, fraction=False):
    t = max(0.0, t)
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    out = '%d:%02d:%02d' % (h, m, s) if h else '%02d:%02d' % (m, s)
    if fraction:
        out += '.%d' % int((t - int(t)) * 10)
    return out


# A full window (not a dialog over Kodi's full-screen video): it shows the
# video itself (a videowindow control in the skin XML), so Kodi's own seek
# bar and player controls, which only appear in the full-screen video window,
# never show up on top of the picker.
class FramePicker(xbmcgui.WindowXML):
    """Create with FramePicker(XML_FILE, addon_path, 'Default', '1080i'), then setup()."""

    def setup(self, player, workdir, capture_width, title, texts, auto_crop=True,
              store_time=True, want_jpg=False, local_only=False):
        self.auto_crop = auto_crop
        self.store_time = store_time  # write the frame's video time into the image
        self.want_jpg = want_jpg  # a <video>-thumb.jpg will be made from this frame
        # a plain video file: its thumbnail is always saved next to the video
        self.local_only = local_only
        self.raw = None  # (bgra, w, h) of the chosen frame
        self.raw_jpg = None  # the same frame at most JPG_MAX_WIDTH wide
        self.frame_time = None  # video time of that frame, in seconds
        self.player = player
        self.workdir = workdir
        self.capture_width = capture_width
        self.title = title
        self.texts = texts
        self.result = None
        self.closed = False
        self.target = None
        self.last_seek = 0.0
        self.capture_lock = threading.Lock()
        self.press_count = 0
        self.guard_until = 0.0  # see _guard()
        self.guard_paused = True
        try:  # the frame the picker opens on (kept if Kodi seeks by itself)
            self.target = player.getTime()
        except RuntimeError:
            pass
        self.use_pos = None
        self.busy = False
        self.total = player.getTotalTime() or 0.0
        try:
            fps = float(xbmc.getInfoLabel('Player.Process(videofps)') or 0)
        except ValueError:
            fps = 0
        self.frame = 1.0 / fps if fps > 1 else 0.04
        # the skin XML colours focus/progress with these, so they follow the
        # skin's colour theme instead of a fixed blue
        try:
            focus = skin_focus_color()
        except Exception:
            focus = DEFAULT_FOCUS
        self.setProperty('focus_color', focus)
        self.setProperty('focus_light', lighter(focus))
        # left over from a backup run outside the picker
        xbmcgui.Window(10000).clearProperty(EXIT_PROP)

    # ---- lifecycle -----------------------------------------------------
    def onInit(self):
        self.slider = self.getControl(SLIDER)
        self.getControl(LBL_TITLE).setLabel('%s  %s' % (self.texts['heading'], self.title))
        self.update_ui(force_slider=True)
        self.setFocusId(SLIDER)
        threading.Thread(target=self._watch, daemon=True).start()

    def close(self):
        self.closed = True
        super().close()

    def _watch(self):
        monitor = xbmc.Monitor()
        home = xbmcgui.Window(10000)
        tool_busy = False
        while not self.closed and not monitor.abortRequested():
            if not self.player.isPlayingVideo():
                self.close()
                break
            # a backup / restore started from Settings (tools.py, see
            # folderzip.py): hide while its window is open, leave when done
            if home.getProperty(EXIT_PROP):
                home.clearProperty(EXIT_PROP)
                self.close()
                break
            busy = bool(home.getProperty(BUSY_PROP))
            if busy != tool_busy:
                tool_busy = busy
                self.setProperty('settings_open', '1' if busy else '')
            # Kodi seeking by itself (its own seek handler, e.g. on a remote /
            # keyboard button it also acts on): keep the video on the
            # picker's frame (the picker's own seeks do not set these)
            if xbmc.getCondVisibility(KODI_SEEKING) and time.time() >= self.guard_until:
                self.guard_paused = self.is_paused()
                self.guard_until = time.time() + GUARD_SECONDS
            guarding = time.time() < self.guard_until
            if guarding:
                self._guard()
            # Kodi's own player controls (OSD) can pop up under the picker,
            # e.g. when the mouse moves: close them, the picker has its own
            if xbmc.getCondVisibility('Window.IsVisible(videoosd)'):
                xbmc.executebuiltin('Dialog.Close(videoosd,true)')
            self.update_ui()
            monitor.waitForAbort(0.1 if guarding else 0.25)

    def _guard(self):
        """While Kodi seeks by itself (its "Seeking" bar is up, or right after
        a remote fast-forward / rewind / skip button, which Kodi handles too):
        close that bar and put the video back on the picker's frame and in its
        paused state."""
        if xbmc.getCondVisibility('Window.IsVisible(seekbar)'):
            xbmc.executebuiltin('Dialog.Close(seekbar,true)')
        if self.guard_paused and not self.is_paused() and \
                xbmc.getCondVisibility('Player.Playing | Player.Forwarding | Player.Rewinding'):
            self.player.pause()  # also stops a fast-forward / rewind
        if not self.guard_paused:
            return  # playing in the picker: no fixed frame to keep
        if self.target is None or time.time() - self.last_seek < 0.4:
            return  # our own seek is still under way
        try:
            now = self.player.getTime()
        except RuntimeError:
            return
        if abs(now - self.target) > KODI_JUMP:
            log_guard = 'picker: undoing a seek by Kodi (%.3f s -> %.3f s)' % (now, self.target)
            xbmc.log('[context.thumbnailfromvideo] ' + log_guard, xbmc.LOGINFO)
            self.seek_to(self.target)

    # ---- state ---------------------------------------------------------
    def is_paused(self):
        return xbmc.getCondVisibility('Player.Paused')

    def current_time(self):
        if self.target is not None and time.time() - self.last_seek < 1.5:
            return self.target
        try:
            return self.player.getTime()
        except RuntimeError:
            return 0.0

    def set_slider(self, t):
        try:
            step = max(1.0, self.total / 100.0)
            self.slider.setFloat(t, 0.0, step, max(self.total, 1.0))
        except Exception:
            if self.total:
                self.slider.setPercent(100.0 * t / self.total)

    def update_ui(self, force_slider=False):
        if self.closed:
            return
        try:
            t = self.current_time()
            # show tenths while paused, so fine steps are visible
            self.getControl(LBL_TIME).setLabel('%s  /  %s' % (
                fmt_time(t, fraction=self.is_paused()), fmt_time(self.total)))
            # don't fight the user while they are moving the slider
            if force_slider or (self.getFocusId() != SLIDER and
                                time.time() - self.last_seek > 1.0):
                self.set_slider(t)
        except Exception:
            pass
        self.place_use_button()

    def place_use_button(self):
        """Keep "Make thumbnail" right under the slider nub."""
        if self.closed:
            return
        try:
            # the slider holds seconds (setFloat), so position = value / total
            try:
                frac = self.slider.getFloat() / max(self.total, 1.0)
            except Exception:
                frac = self.slider.getPercent() / 100.0
            cx = NUB_X0 + NUB_SPAN * min(max(frac, 0.0), 1.0)
            x = int(min(max(cx - USE_W / 2.0, PANEL_X0), PANEL_X1 - USE_W))
            px = int(min(max(cx - 10, PANEL_X0 + 14), PANEL_X1 - 34))
            if (x, px) == self.use_pos:
                return
            self.use_pos = (x, px)
            for cid in (BTN_USE,) + USE_FACES:
                self.getControl(cid).setPosition(x, USE_Y)
            for cid in POINTERS:
                self.getControl(cid).setPosition(px, POINTER_Y)
        except Exception:
            pass

    # ---- seeking -------------------------------------------------------
    def seek_to(self, t, from_slider=False):
        if self.total:
            t = min(t, self.total - 0.2)
        t = max(0.0, t)
        self.target = t
        self.last_seek = time.time()
        self.player.seekTime(t)
        if not from_slider:
            self.set_slider(t)
        self.update_ui()

    def seek_by(self, delta):
        if delta == 'frame+':
            delta = self.frame
        elif delta == 'frame-':
            delta = -self.frame
        if abs(delta) < 1 and not self.is_paused():
            self.player.pause()  # fine stepping only makes sense paused
        self.seek_to(self.current_time() + delta)

    def toggle_pause(self):
        self.player.pause()
        xbmc.sleep(100)
        if self.is_paused():
            # the frame paused on is the one to keep (see _guard)
            try:
                self.target = self.player.getTime()
            except RuntimeError:
                pass
        self.update_ui()

    # ---- capture -------------------------------------------------------
    def grab(self, width, log_crop=False):
        """Capture the video frame on screen (video only, without this window)
        at the given width, with black bars removed if enabled.
        Returns (bgra_bytes, w, h) or None."""
        got = None
        with self.capture_lock:
            try:
                aspect = xbmc.RenderCapture().getAspectRatio() or (16.0 / 9.0)
                w = int(width) & ~1
                h = int(round(w / aspect)) & ~1
                got = self.native_deinterlaced(aspect, w)
                if got is None:
                    got = self._render(w, h)
            except Exception as e:
                xbmc.log('[framethumb] capture error: %s' % e, xbmc.LOGERROR)
        if not got:
            return None
        data, w, h = got
        if self.auto_crop:
            box = png.find_content_box(data, w, h)
            if box != (0, 0, w, h):
                if log_crop:
                    xbmc.log('[framethumb] cropping black bars: %s of %dx%d' % (box, w, h),
                             xbmc.LOGINFO)
                data, w, h = png.crop_bgra(data, w, box)
        return data, w, h

    @staticmethod
    def _render(w, h):
        rc = xbmc.RenderCapture()
        rc.capture(w, h)
        data = rc.getImage(2000)
        if not data or len(data) < w * h * 4:
            return None
        return bytes(data[:w * h * 4]), w, h

    def native_deinterlaced(self, aspect, want_w):
        """Interlaced video (e.g. MPEG-2 576i/480i/1080i): a paused frame is
        captured with both fields woven together, giving horizontal lines.
        Capture at the video's own height (one image row per video line),
        check for combing and remove it. Returns (data, w, h) when the frame
        was combed, else None (then the normal capture is used)."""
        try:
            src_h = int(xbmc.getInfoLabel('Player.Process(videoheight)') or 0)
        except ValueError:
            src_h = 0
        if not 0 < src_h <= 1088:
            return None
        h = src_h & ~1
        w = int(round(h * aspect)) & ~1
        got = self._render(w, h)
        if not got:
            return None
        data = got[0]
        score = deinterlace.comb_score(data, w, h)
        if score < deinterlace.COMB_THRESHOLD:
            return None
        xbmc.log('[framethumb] interlaced frame (comb score %.2f), deinterlacing %dx%d'
                 % (score, w, h), xbmc.LOGINFO)
        return deinterlace.deinterlace(data, w, h), w, h

    def capture(self):
        """Grab the frame on screen; returns the PNG path or None."""
        if not self.is_paused():
            self.player.pause()  # freeze the exact frame the user is looking at
        wait = 0.7 - (time.time() - self.last_seek)
        if wait > 0:
            xbmc.sleep(int(wait * 1000))  # let the seeked frame render
        got = self.grab(self.capture_width, log_crop=True)
        if not got:
            xbmcgui.Dialog().notification(self.title, self.texts['capture_failed'],
                                          xbmcgui.NOTIFICATION_ERROR, 3000)
            return None
        data, w, h = got
        # PNG is fast to write (zlib is C code); a JPG, if wanted, is made from
        # the raw pixels later, after the picker has closed (see main.run)
        self.raw = (data, w, h)
        try:
            self.frame_time = self.player.getTime()
        except RuntimeError:
            self.frame_time = None
        text = (frametime.png_chunk(self.frame_time)
                if self.store_time and self.frame_time else None)
        path = os.path.join(self.workdir, 'frame-%d.png' % int(time.time() * 1000))
        png.write_bgra(path, w, h, data, text)
        # A JPG (if wanted) is encoded in Python, which is slow for big frames.
        # Kodi shows thumbnails at most 1280 px wide anyway, so take a second,
        # smaller capture of the same paused frame for it (the GPU scales it).
        self.raw_jpg = self.raw
        if self.want_jpg and w > JPG_MAX_WIDTH:
            small = self.grab(JPG_MAX_WIDTH)
            if small:
                self.raw_jpg = small
        return path

    # ---- press feedback ------------------------------------------------
    def flash(self, cid):
        """Briefly shrink/dim the pressed button. The skin XML animates a
        button while Window.Property(pressed) holds its id; clearing the
        property plays the animation back."""
        self.press_count += 1
        n = self.press_count
        self.setProperty('pressed', str(cid))

        def release():
            if n == self.press_count and not self.closed:
                self.setProperty('pressed', '')
        threading.Timer(0.15, release).start()

    # ---- input ---------------------------------------------------------
    def make_thumbnail(self):
        if self.busy:
            return
        self.busy = True
        try:
            self.flash(BTN_USE)
            xbmc.sleep(160)  # let the press show before capturing/closing
            path = self.capture()
            if path:
                self.result = path
                self.close()
        finally:
            self.busy = False

    def onClick(self, cid):
        if cid == BTN_USE:
            self.make_thumbnail()
            return
        if cid != SLIDER:
            self.flash(cid)
        if cid == SLIDER:
            try:
                t = self.slider.getFloat()
            except Exception:
                t = self.total * self.slider.getPercent() / 100.0
            self.seek_to(t, from_slider=True)
        elif cid in BUTTON_SEEKS:
            self.seek_by(BUTTON_SEEKS[cid])
        elif cid == BTN_PLAYPAUSE:
            self.toggle_pause()
        elif cid == BTN_CANCEL:
            self.close()
        elif cid == BTN_SETTINGS:
            self.open_settings()

    def open_settings(self):
        """Show the add-on settings on top of the paused video. The picker
        hides itself meanwhile (it draws above other dialogs), and settings
        that matter for capturing take effect right away."""
        if not self.is_paused():
            self.player.pause()
        self.setProperty('settings_open', '1')
        # shown on "Clear thumbnail cache (open video only)"
        set_open_video_name(self.player)
        try:
            xbmcaddon.Addon().openSettings()  # returns when the dialog closes
        finally:
            set_open_video_name(None)
            if not xbmcgui.Window(10000).getProperty(BUSY_PROP):
                self.setProperty('settings_open', '')
        settings = xbmcaddon.Addon().getSettings()
        self.auto_crop = settings.getBool('auto_crop')
        self.want_jpg = ((self.local_only or settings.getInt('save_location') == 1) and
                         settings.getInt('image_format') == 1)
        self.capture_width = settings.getInt('capture_width') or self.capture_width
        self.setFocusId(BTN_SETTINGS)

    def onAction(self, action):
        aid = action.getId()
        if aid in BACK_ACTIONS:
            self.close()
        elif aid == A_SELECT and self.getFocusId() == SLIDER:
            # OK on the slider nub = "Make thumbnail" (it is shown selected too)
            self.make_thumbnail()
            return
        elif aid in PAUSE_ACTIONS:
            self.flash(BTN_PLAYPAUSE)
            self.toggle_pause()
        elif aid in HOTKEY_SEEKS:
            if aid in REMOTE_SEEKS:
                # Kodi acts on these remote buttons as well (its own seek,
                # "Seeking +00:02" bar): undo that for a moment (see _guard)
                # they are single-frame steps, which always leave the video paused
                self.guard_paused = True
                self.guard_until = time.time() + GUARD_SECONDS
            self.seek_by(HOTKEY_SEEKS[aid])
        elif A_NUM_0 <= aid <= A_NUM_0 + 9 and self.total:
            self.seek_to(self.total * (aid - A_NUM_0) / 10.0)
        # moving the slider with left/right: let the button follow at once
        if not self.closed and self.getFocusId() == SLIDER:
            self.place_use_button()

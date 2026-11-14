"""VCR on-screen display and camcorder date stamp over Kodi's slideshow.

While a slideshow runs, PLAY, PAUSE, FF or REW shows top left as on a VCR, and
the time and date the photo or home video was taken shows bottom right, as a
camcorder stamps it on the tape. The add-on lays its own labels over the
slideshow window, in the Super-VCR Mono font from resource.font.supervcrmono,
so it works with any skin.
"""

import datetime
import os
import struct
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
MEDIA = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo("path")), "resources", "media")
SLIDESHOW = 12007

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
MP4_EPOCH = datetime.datetime(1904, 1, 1, tzinfo=datetime.timezone.utc)
# A VCR shows PLAY for a few seconds after play starts, then clears the screen
PLAY_SECONDS = 4
ACTIVE_INTERVAL = 0.2
IDLE_INTERVAL = 1.0

# Laid out on a 1920x1080 window and scaled to the slideshow window's size
DESIGN_WIDTH = 1920
FONT_SIZE = 60
FONT_SIZES = (24, 36, 40, 48, 60, 72)
# Super-VCR Mono is monospaced: every character is this wide, as a share of the font size
ADVANCE = 0.75
LINE = 65
OSD_LEFT, OSD_TOP = 120, 80
STAMP_RIGHT, STAMP_TOP = 1800, 848
ICONS = {"PLAY": ("vhs_play.png", 49), "PAUSE": ("vhs_pause.png", 39),
         "FF": ("vhs_ff.png", 103), "REW": ("vhs_rew.png", 103)}
ICON_HEIGHT = 44
ICON_TOP = 15
ICON_GAP = 18
# A dark edge, the red and cyan bleed of a worn tape, then the white text
LAYERS = [((dx, dy), "E6000000") for dx, dy in ((-3, -3), (3, -3), (-3, 3), (3, 3))]
LAYERS += [((5, 0), "80FF2A2A"), ((-5, 0), "802AE6FF"), ((0, 0), "FFF4F4EE")]
# The date is on the tape, so it shakes with the picture
JITTER = [("conditional", "effect=slide start=0,0 end=0.7,0 time=170 loop=true condition=true"),
          ("conditional", "effect=slide start=0,0 end=-0.7,0.7 time=230 loop=true condition=true")]
ALIGN_LEFT = 0x00000000
ALIGN_RIGHT = 0x00000001
ALIGN_CENTER_Y = 0x00000004


def read_boxes(file, start, stop):
    """Yield (data start, end, type) for each MP4 box between start and stop."""
    pos = start
    while pos + 8 <= stop:
        file.seek(pos, 0)
        head = bytes(file.readBytes(16))
        if len(head) < 8:
            return
        size, kind = struct.unpack(">I4s", head[:8])
        header = 8
        if size == 1 and len(head) == 16:
            size, header = struct.unpack(">Q", head[8:16])[0], 16
        elif size == 0:
            size = stop - pos
        if size < header:
            return
        yield pos + header, pos + size, kind
        pos += size


def recorded_time(path):
    """When a video was recorded, from its MP4/MOV header, in local time."""
    file = xbmcvfs.File(path)
    try:
        for start, stop, kind in read_boxes(file, 0, file.size()):
            if kind != b"moov":
                continue
            for header_start, _, header_kind in read_boxes(file, start, stop):
                if header_kind != b"mvhd":
                    continue
                file.seek(header_start, 0)
                data = bytes(file.readBytes(12))
                if len(data) < 12:
                    return None
                if data[0] == 1:
                    seconds = struct.unpack(">Q", data[4:12])[0]
                else:
                    seconds = struct.unpack(">I", data[4:8])[0]
                if not seconds:
                    return None
                recorded = MP4_EPOCH + datetime.timedelta(seconds=seconds)
                return recorded.astimezone().replace(tzinfo=None)
        return None
    except Exception:  # an unreadable or odd file just has no date
        return None
    finally:
        file.close()


def photo_time():
    """When the current picture was taken, from the EXIF time Kodi shows."""
    label = xbmc.getInfoLabel("Slideshow.EXIFTime")
    if not label:
        return None
    date = xbmc.getRegion("dateshort")
    for clock in (xbmc.getRegion("time"), xbmc.getRegion("time").replace(":%S", "")):
        try:
            return datetime.datetime.strptime(label, date + " " + clock)
        except ValueError:
            pass
    return None


class Layered:
    """One piece of text or a symbol drawn as the stack of LAYERS."""

    def __init__(self, window, scale, font):
        self.window = window
        self.scale = scale
        self.font = font
        self.controls = []

    def px(self, value):
        return round(value * self.scale)

    def alive(self, window):
        if not self.controls:
            return False
        try:
            window.getControl(self.controls[0].getId())
            return True
        except RuntimeError:
            return False

    def add(self, make, animations=None):
        for offset, colour in LAYERS:
            control = make(offset, colour)
            self.window.addControl(control)
            if animations:
                control.setAnimations(animations)
            self.controls.append(control)

    def set_visible(self, visible):
        for control in self.controls:
            control.setVisible(visible)


class TextLine(Layered):
    def __init__(self, window, scale, font, left, top, width, align, animations=None):
        super().__init__(window, scale, font)

        def make(offset, colour):
            return xbmcgui.ControlLabel(self.px(left + offset[0]), self.px(top + offset[1]),
                                        self.px(width), self.px(LINE), "", font=font,
                                        textColor=colour, alignment=align | ALIGN_CENTER_Y)

        self.add(make, animations)
        self.text = None

    def set_text(self, text):
        if text != self.text:
            for control in self.controls:
                control.setLabel(text)
            self.text = text


class Symbol(Layered):
    def __init__(self, window, scale, filename, left, top, width):
        super().__init__(window, scale, None)
        path = os.path.join(MEDIA, filename)

        def make(offset, colour):
            return xbmcgui.ControlImage(self.px(left + offset[0]), self.px(top + offset[1]),
                                        self.px(width), self.px(ICON_HEIGHT), path,
                                        colorDiffuse=colour)

        self.add(make)


class Overlay:
    """Labels and symbols laid over the slideshow window.

    Kodi keeps the slideshow window loaded, so the controls stay in it between
    slideshows. A skin reload builds the window again without them, so they
    are checked before use and added again when they have gone.
    """

    def __init__(self):
        self.parts = {}
        self.shown = {}

    def build(self):
        window = xbmcgui.Window(SLIDESHOW)
        scale = window.getWidth() / DESIGN_WIDTH
        size = min(FONT_SIZES, key=lambda s: abs(s - FONT_SIZE * scale))
        font = f"supervcrmono{size}"
        parts = {"stamp_time": TextLine(window, scale, font, STAMP_RIGHT - 800, STAMP_TOP, 800,
                                        ALIGN_RIGHT, JITTER),
                 "stamp_date": TextLine(window, scale, font, STAMP_RIGHT - 800, STAMP_TOP + LINE,
                                        800, ALIGN_RIGHT, JITTER)}
        for word, (filename, width) in ICONS.items():
            parts["osd_" + word] = TextLine(window, scale, font, OSD_LEFT, OSD_TOP, 600, ALIGN_LEFT)
            icon_left = OSD_LEFT + round(len(word) * ADVANCE * FONT_SIZE) + ICON_GAP
            parts["icon_" + word] = Symbol(window, scale, filename, icon_left, OSD_TOP + ICON_TOP,
                                           width)
        for name, part in parts.items():
            if name.startswith("osd_"):
                part.set_text(name[4:])
            part.set_visible(False)
        self.parts = parts
        self.shown = {}

    def ensure(self):
        # A new Window object asks Kodi itself: the one the controls were added through still
        # lists them after a skin reload has destroyed them
        window = xbmcgui.Window(SLIDESHOW)
        if not self.parts or not all(part.alive(window) for part in self.parts.values()):
            self.build()

    def show_osd(self, word):
        if self.shown.get("osd") == word:
            return
        self.ensure()
        for name in ICONS:
            self.parts["osd_" + name].set_visible(name == word)
            self.parts["icon_" + name].set_visible(name == word)
        self.shown["osd"] = word

    def show_stamp(self, lines):
        if self.shown.get("stamp") == lines:
            return
        self.ensure()
        for name, text in zip(("stamp_time", "stamp_date"), lines or ("", "")):
            self.parts[name].set_text(text)
            self.parts[name].set_visible(bool(lines))
        self.shown["stamp"] = lines

    def hide(self):
        if self.shown:
            self.show_osd(None)
            self.show_stamp(None)


class Stamp:
    def __init__(self):
        self.overlay = Overlay()
        self.recorded = {}
        self.mode = ""
        self.play_until = 0.0

    def video_time(self):
        filename = xbmc.getInfoLabel("Slideshow.Filename")
        path = xbmc.getInfoLabel("Slideshow.Path") + filename
        player = xbmc.Player()
        playing = player.isPlayingVideo() and os.path.basename(player.getPlayingFile()) == filename
        if playing:
            path = player.getPlayingFile()
        if path not in self.recorded:
            if len(self.recorded) > 500:
                self.recorded.clear()
            self.recorded[path] = recorded_time(path)
        recorded = self.recorded[path]
        if recorded and playing:
            recorded += datetime.timedelta(seconds=int(player.getTime()))
        return recorded

    def osd(self, now):
        video = xbmc.getCondVisibility("Player.HasVideo")
        if video and xbmc.getCondVisibility("Player.Forwarding"):
            mode = "FF"
        elif video and xbmc.getCondVisibility("Player.Rewinding"):
            mode = "REW"
        elif (video and xbmc.getCondVisibility("Player.Paused")) or xbmc.getCondVisibility(
            "Slideshow.IsPaused"
        ):
            mode = "PAUSE"
        elif xbmc.getCondVisibility("Slideshow.IsActive") or (
            video and xbmc.getCondVisibility("Slideshow.IsVideo")
        ):
            mode = "PLAY"
        else:
            mode = ""

        if mode == "PLAY" and self.mode != "PLAY":
            self.play_until = now + PLAY_SECONDS
        self.mode = mode
        if mode == "PLAY":
            return "PLAY" if now < self.play_until else ""
        return mode

    def update(self):
        if xbmc.getCondVisibility("Window.IsVisible(DialogPictureInfo.xml)"):
            self.overlay.hide()
            return

        self.overlay.show_osd(self.osd(time.monotonic()) or None)

        if xbmc.getCondVisibility("Slideshow.IsVideo"):
            taken = self.video_time()
        else:
            taken = photo_time()
        if taken:
            hour = taken.hour % 12 or 12
            meridiem = "AM" if taken.hour < 12 else "PM"
            clock = f"{meridiem} {hour}:{taken.minute:02d}:{taken.second:02d}"
            date = f"{MONTHS[taken.month - 1]}.{taken.day:>2} {taken.year}"
            self.overlay.show_stamp((clock, date))
        else:
            self.overlay.show_stamp(None)

    def clear(self):
        self.overlay.hide()
        self.mode = ""


def main():
    monitor = xbmc.Monitor()
    stamp = Stamp()
    active = False
    while not monitor.abortRequested():
        if xbmc.getCondVisibility("Window.IsActive(slideshow)"):
            stamp.update()
            active = True
            interval = ACTIVE_INTERVAL
        else:
            if active:
                stamp.clear()
                active = False
            interval = IDLE_INTERVAL
        if monitor.waitForAbort(interval):
            break
    stamp.clear()

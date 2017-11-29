# -*- coding: utf-8 -*-

import os
import re
import xbmc
import xbmcgui
from dialog import *
from utils import ADDON_PATH


def get_version_number():
    return int(xbmc.getInfoLabel("System.BuildVersion")[0:2])


def log_location(old=False):
    version_number = get_version_number()
    if version_number < 12:
        if xbmc.getCondVisibility("system.platform.osx"):
            if xbmc.getCondVisibility("system.platform.atv2"):
                log_path = "/var/mobile/Library/Preferences"
            else:
                log_path = os.path.join(os.path.expanduser("~"), "Library/Logs")
        elif xbmc.getCondVisibility("system.platform.ios"):
            log_path = "/var/mobile/Library/Preferences"
        elif xbmc.getCondVisibility("system.platform.windows"):
            log_path = xbmc.translatePath("special://home")
        elif xbmc.getCondVisibility("system.platform.linux"):
            log_path = xbmc.translatePath("special://home/temp")
        else:
            log_path = xbmc.translatePath("special://logpath")
    else:
        log_path = xbmc.translatePath("special://logpath")

    if version_number < 14:
        filename = "xbmc.log"
        filename_old = "xbmc.old.log"
    else:
        filename = "kodi.log"
        filename_old = "kodi.old.log"

    if not os.path.exists(os.path.join(log_path, filename)):
        if os.path.exists(os.path.join(log_path, "spmc.log")):
            filename = "spmc.log"
            filename_old = "spmc.old.log"
        else:
            return False

    if old:
        log_path = os.path.join(log_path, filename_old)
    else:
        log_path = os.path.join(log_path, filename)

    return log_path.decode("utf-8")


def set_styles(content):
    content = content.replace(" ERROR: ", " [COLOR red]ERROR[/COLOR]: ")
    content = content.replace(" WARNING: ", " [COLOR gold]WARNING[/COLOR]: ")

    return content


def parse_errors(content, set_style=False):
    if content == "":
        return ""

    parsed_content = []

    found_error = False
    for line in content.splitlines():
        if re.match("^\d{2}:\d{2}:\d{2}", line):
            if " ERROR: " in line:
                found_error = True
                parsed_content.append(line)
            else:
                found_error = False
        elif found_error:
            parsed_content.append(line)

    parsed_content = "\n".join(parsed_content)

    if set_style:
        parsed_content = set_styles(parsed_content)

    return parsed_content


def get_content(old=False, invert=False, line_number=0, set_style=False):
    if not invert:
        line_number = 0

    f = LogReader(log_location(old))
    content = f.read(invert, line_number)

    if set_style:
        content = set_styles(content)

    return content


def window(title, content, default=True, timeout=1000):
    if default:
        window_id = 10147
        control_label = 1
        control_textbox = 5

        xbmc.executebuiltin("ActivateWindow(%s)" % window_id)
        w = xbmcgui.Window(window_id)

        # Wait for window to open
        time_passed = 0
        while not xbmc.getCondVisibility("Window.IsVisible(%s)" % window_id) and time_passed < timeout:
            xbmc.sleep(100)
            time_passed += 100

        w.getControl(control_label).setLabel(title)
        w.getControl(control_textbox).setText(content)
    else:
        w = TextWindow("script.logviewer-textwindow-fullscreen.xml", ADDON_PATH, title=title, content=content)
        w.doModal()
        del w


class TextWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_filename, script_path, title, content):
        xbmcgui.WindowXML.__init__(self, xml_filename, script_path)
        self.title = title
        self.content = content
        # Controls IDs
        self.close_button_id = 32500
        self.title_label_id = 32501
        self.text_box_id = 32503

    def onInit(self):
        self.getControl(self.title_label_id).setLabel(self.title)
        self.getControl(self.text_box_id).setText(self.content)

    def onClick(self, control_id):
        if control_id == self.close_button_id:
            # Close Button
            self.close()

    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU]:
            self.close()


class LogReader(object):
    def __init__(self, filename, buf_size=8192):
        self.filename = filename
        self.buf_size = buf_size
        self.offset = 0

    def tail(self):
        file_size = self.file_size()
        if file_size < self.offset:
            self.offset = 0
        if file_size == self.offset:
            return ""

        with open(self.filename) as fh:
            fh.seek(self.offset)
            self.offset = file_size
            return fh.read()

    def read(self, invert=False, lines_number=0):
        return "\n".join(line for line in self.read_lines(invert, lines_number))

    def read_lines(self, invert=False, lines_number=0):
        if invert:
            return self.reverse_read_lines(lines_number)
        else:
            return self.normal_read_lines(lines_number)

    def normal_read_lines(self, lines_number=0):
        """a generator that returns the lines of a file"""
        total = 0
        with open(self.filename) as fh:
            segment = None
            file_size = self.file_size()
            while file_size - fh.tell() > 0 and (total < lines_number or lines_number == 0):
                buf = fh.read(self.buf_size)
                lines = buf.split("\n")
                # the last line of the buffer is probably not a complete line so
                # we'll save it and prepend it to the first line of the next buffer
                # we read
                if segment is not None:
                    # if the previous chunk starts right from the beginning of line
                    # do not concact the segment to the first line of new chunk
                    # instead, yield the segment first
                    if buf[-1] is not "\n":
                        lines[0] = segment + lines[0]
                    else:
                        total += 1
                        yield segment
                segment = lines[-1]
                for index in range(0, len(lines) - 1):
                    if len(lines[index]) and (total < lines_number or lines_number == 0):
                        total += 1
                        yield lines[index]
            # Don't yield None if the file was empty
            if segment is not None and (total < lines_number or lines_number == 0):
                yield segment

    def reverse_read_lines(self, lines_number=0):
        """a generator that returns the lines of a file in reverse order"""
        with open(self.filename) as fh:
            segment = None
            offset = 0
            total = 0
            fh.seek(0, os.SEEK_END)
            file_size = remaining_size = fh.tell()
            while remaining_size > 0 and (total < lines_number or lines_number == 0):
                offset = min(file_size, offset + self.buf_size)
                fh.seek(file_size - offset)
                buf = fh.read(min(remaining_size, self.buf_size))
                remaining_size -= self.buf_size
                lines = buf.split("\n")
                # the first line of the buffer is probably not a complete line so
                # we'll save it and append it to the last line of the next buffer
                # we read
                if segment is not None:
                    # if the previous chunk starts right from the beginning of line
                    # do not concact the segment to the last line of new chunk
                    # instead, yield the segment first
                    if buf[-1] is not "\n":
                        lines[-1] += segment
                    else:
                        total += 1
                        yield segment
                segment = lines[0]
                for index in range(len(lines) - 1, 0, -1):
                    if len(lines[index]) and (total < lines_number or lines_number == 0):
                        total += 1
                        yield lines[index]
            # Don't yield None if the file was empty
            if segment is not None and (total < lines_number or lines_number == 0):
                yield segment

    def file_size(self):
        return os.path.getsize(self.filename)

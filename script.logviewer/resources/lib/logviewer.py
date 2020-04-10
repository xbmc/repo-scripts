# -*- coding: utf-8 -*-

import json
import os
import re
import time

import xbmc
import xbmcgui

from resources.lib.dialog import ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU
from resources.lib.logreader import LogReader
from resources.lib.utils import ADDON_PATH, PY3, translate


def get_version_number():
    return int(xbmc.getInfoLabel("System.BuildVersion")[0:2])


def get_application_name():
    cmd = ('{"jsonrpc":"2.0", "method":"Application.GetProperties",'
           '"params": {"properties": ["name"]}, "id":1}')
    data = json.loads(xbmc.executeJSONRPC(cmd))
    if "result" in data and "name" in data["result"]:
        return data["result"]["name"]
    else:
        raise ValueError


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

    try:
        app_name = get_application_name().lower()
        filename = "{}.log".format(app_name)
        filename_old = "{}.old.log".format(app_name)
    except ValueError:
        filename_old = None
        filename = None

        for file in os.listdir(log_path):
            if file.endswith(".old.log"):
                filename_old = file
            elif file.endswith(".log"):
                filename = file

    if old:
        if filename_old is None:
            return None
        log_path = os.path.join(log_path, filename_old)
    else:
        if filename is None:
            return None
        log_path = os.path.join(log_path, filename)

    return log_path if PY3 else log_path.decode("utf-8")


def set_styles(content):
    content = content.replace(" ERROR: ", " [COLOR red]ERROR[/COLOR]: ")
    content = content.replace(" WARNING: ", " [COLOR gold]WARNING[/COLOR]: ")

    return content


log_entry_regex = re.compile(r"^(?:\d{4}-\d{2}-\d{2} )?\d{2}:\d{2}:\d{2}")


def parse_errors(content, set_style=False, exceptions_only=False):
    if content == "":
        return ""

    parsed_content = []
    found_error = False
    pattern = " ERROR: EXCEPTION " if exceptions_only else " ERROR: "

    for line in content.splitlines():
        if log_entry_regex.match(line):
            if pattern in line:
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

    path = log_location(old)
    if path is None:
        xbmcgui.Dialog().ok(translate(30016), translate(30017))
        return

    f = LogReader(path)
    content = f.read(invert, line_number)

    if set_style:
        content = set_styles(content)

    return content


def window(title, content, default=True, timeout=1):
    if default:
        window_id = 10147
        control_label = 1
        control_textbox = 5

        xbmc.executebuiltin("ActivateWindow({})".format(window_id))
        w = xbmcgui.Window(window_id)

        # Wait for window to open
        start_time = time.time()
        while (not xbmc.getCondVisibility("Window.IsVisible({})".format(window_id)) and
               time.time() - start_time < timeout):
            xbmc.sleep(100)

        w.getControl(control_label).setLabel(title)
        w.getControl(control_textbox).setText(content)
    else:
        w = TextWindow("script.logviewer-textwindow-fullscreen.xml", ADDON_PATH, title=title, content=content)
        w.doModal()
        del w


class TextWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, xml_filename, script_path, title, content):
        super(TextWindow, self).__init__(xml_filename, script_path)
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

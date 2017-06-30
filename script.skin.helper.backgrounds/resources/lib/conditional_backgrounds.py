#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    Allows the user to globally override the skin's background on certain date conditions.
    For example setup a christmas background at late december etc.
    By launching this script entrypoint the user will be presented with a dialog to add,
    delete and edit conditional overrides.
'''

from utils import log_msg, ADDON_ID, log_exception
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
from datetime import datetime
import time

CACHE_PATH = "special://profile/addon_data/script.skin.helper.backgrounds/"
CACHE_FILE = CACHE_PATH + "conditionalbackgrounds.json"
DATE_FORMAT = "%Y-%m-%d"


class ConditionalBackgrounds(xbmcgui.WindowXMLDialog):
    '''Dialog to allow the user to set multiple timeframes to override the background'''
    backgrounds_control = None
    all_backgrounds = []

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        # read all backgrounds that are setup
        self.all_backgrounds = get_cond_backgrounds()
        self.addon = xbmcaddon.Addon(ADDON_ID)
        log_msg("ConditionalBackgrounds started")

    def __del__(self):
        '''Cleanup Kodi Cpython instances'''
        del self.addon
        log_msg("ConditionalBackgrounds exited")

    def refresh_listing(self):
        '''reload the listing'''
        # clear list first
        self.backgrounds_control.reset()

        # Add CREATE entry at top of list
        listitem = xbmcgui.ListItem(label=self.addon.getLocalizedString(32073), iconImage="-")
        desc = self.addon.getLocalizedString(32074)
        listitem.setProperty("description", desc)
        listitem.setProperty("Addon.Summary", desc)
        listitem.setLabel2(desc)
        listitem.setProperty("id", "add")
        self.backgrounds_control.addItem(listitem)

        count = 0
        for background in self.all_backgrounds:
            label = background["name"]
            if time_in_range(background["startdate"], background["enddate"], datetime.now().strftime(DATE_FORMAT)):
                label = label + " " + xbmc.getLocalizedString(461)
            listitem = xbmcgui.ListItem(label=label, iconImage=background["background"])
            desc = "[B]%s:[/B] %s [CR][B]%s:[/B] %s" % (xbmc.getLocalizedString(19128),
                                                        background["startdate"],
                                                        xbmc.getLocalizedString(19129),
                                                        background["enddate"])
            listitem.setProperty("description", desc)
            listitem.setProperty("Addon.Summary", desc)
            listitem.setLabel2(desc)
            listitem.setProperty("id", str(count))
            self.backgrounds_control.addItem(listitem)
            count += 1
        xbmc.executebuiltin("Control.SetFocus(6)")

    def onInit(self):
        '''Triggers when the dialog is drawn'''
        self.backgrounds_control = self.getControl(6)
        self.getControl(1).setLabel(self.addon.getLocalizedString(32070))
        self.getControl(5).setVisible(True)
        self.getControl(3).setVisible(False)
        self.refresh_listing()

    def onAction(self, action):
        '''triggers if an kodi action is performed'''

        # exit command issued
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close_dialog()

    def close_dialog(self):
        '''called to close the dialog and write the settings to disk'''
        if not xbmcvfs.exists(CACHE_PATH):
            xbmcvfs.mkdir(CACHE_PATH)
        # write backgrounds to file
        text_file = xbmcvfs.File(CACHE_FILE, "w")
        text_file.write(repr(self.all_backgrounds))
        text_file.close()
        self.close()

    def onClick(self, controlID):
        '''called when the user clicks the dialog'''
        error = False

        if(controlID == 6):
            # edit
            item = self.backgrounds_control.getSelectedItem()
            item_id = item.getProperty("id")
            if item_id == "add":
                # add
                date_today = datetime.now().strftime(DATE_FORMAT)
                name = xbmcgui.Dialog().input(self.addon.getLocalizedString(32058), type=xbmcgui.INPUT_ALPHANUM)
                if xbmcgui.Dialog().yesno(
                        self.addon.getLocalizedString(32070),
                        self.addon.getLocalizedString(32064),
                        nolabel=self.addon.getLocalizedString(32066),
                        yeslabel=self.addon.getLocalizedString(32065)):
                    background = xbmcgui.Dialog().browse(2, self.addon.getLocalizedString(32061),
                                                         'files', mask='.jpg|.png')
                else:
                    background = xbmcgui.Dialog().browse(0, self.addon.getLocalizedString(32067), 'files')
                startdate = xbmcgui.Dialog().input(xbmc.getLocalizedString(19128) + " (yyyy-mm-dd)",
                                                   date_today, type=xbmcgui.INPUT_ALPHANUM)
                enddate = xbmcgui.Dialog().input(xbmc.getLocalizedString(19129) + " (yyyy-mm-dd)",
                                                 date_today, type=xbmcgui.INPUT_ALPHANUM)
                try:
                    # check if the dates are valid
                    date_time = datetime(*(time.strptime(startdate, DATE_FORMAT)[0:6]))
                    date_time = datetime(*(time.strptime(enddate, DATE_FORMAT)[0:6]))
                    del date_time
                except Exception as exc:
                    log_exception(__name__, exc)
                    error = True

                if not name or not background or error:
                    xbmcgui.Dialog().ok(xbmc.getLocalizedString(329), self.addon.getLocalizedString(32032))
                else:
                    self.all_backgrounds.append({"name": name, "background": background,
                                                 "startdate": startdate, "enddate": enddate})
                    self.refresh_listing()
            else:
                deleteorchange = xbmcgui.Dialog().yesno(
                    self.addon.getLocalizedString(32075),
                    self.addon.getLocalizedString(32076),
                    nolabel=self.addon.getLocalizedString(32078),
                    yeslabel=self.addon.getLocalizedString(32077))
                if not deleteorchange:
                    # delete entry
                    dialog = xbmcgui.Dialog()
                    if dialog.yesno(xbmc.getLocalizedString(122) + u" " + item.getLabel().decode("utf-8") + u" ?",
                                    xbmc.getLocalizedString(125)):
                        del self.all_backgrounds[int(item.getProperty("id"))]
                        self.refresh_listing()
                elif deleteorchange:
                    # edit entry
                    item_id = int(item_id)
                    currentvalues = self.all_backgrounds[item_id]
                    name = xbmcgui.Dialog().input(
                        self.addon.getLocalizedString(32058),
                        currentvalues["name"],
                        type=xbmcgui.INPUT_ALPHANUM)
                    background = currentvalues["background"]
                    startdate = xbmcgui.Dialog().input(xbmc.getLocalizedString(19128) + " (yyyy-mm-dd)",
                                                       currentvalues["startdate"], type=xbmcgui.INPUT_ALPHANUM)
                    enddate = xbmcgui.Dialog().input(xbmc.getLocalizedString(19129) + " (yyyy-mm-dd)",
                                                     currentvalues["enddate"], type=xbmcgui.INPUT_ALPHANUM)
                    try:
                        # check if the dates are valid
                        date_time = datetime(*(time.strptime(startdate, DATE_FORMAT)[0:6]))
                        date_time = datetime(*(time.strptime(startdate, DATE_FORMAT)[0:6]))
                    except Exception as exc:
                        log_exception(__name__, exc)
                        error = True

                    if not name or not background or error:
                        xbmcgui.Dialog().ok(xbmc.getLocalizedString(329), self.addon.getLocalizedString(32032))
                    else:
                        self.all_backgrounds[item_id] = {
                            "name": name,
                            "background": background,
                            "startdate": startdate,
                            "enddate": enddate}
                        self.refresh_listing()

        if controlID == 5:
            # close
            self.close_dialog()

# GLOBAL HELPERS - ALSO ACCESSED BY BACKGROUNDS UPDATER SERVICE


def get_cond_background():
    '''get the current active conditional background (if any) - called by the background service'''
    background = ""
    all_cond_backgrounds = get_cond_backgrounds()
    if all_cond_backgrounds:
        date_today = datetime.now().strftime(DATE_FORMAT)
        for item in all_cond_backgrounds:
            if time_in_range(item["startdate"], item["enddate"], date_today):
                background = item["background"]
                break
    return background


def get_cond_backgrounds():
    '''read all backgrounds that are setup'''
    all_backgrounds = []
    if xbmcvfs.exists(CACHE_FILE):
        text_file = xbmcvfs.File(CACHE_FILE)
        try:
            text = text_file.read()
            all_backgrounds = eval(text)
        except Exception as exc:
            log_exception(__name__, exc)
        finally:
            text_file.close()
    return all_backgrounds


def time_in_range(start, end, date_time):
    '''determine if the given time is within the range'''
    if start <= end:
        return start <= date_time <= end
    else:
        return start <= date_time or date_time <= end

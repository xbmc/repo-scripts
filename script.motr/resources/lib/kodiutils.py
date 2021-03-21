# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import sys
import logging

# read settings
ADDON = xbmcaddon.Addon()
__lang__ = ADDON.getLocalizedString

def notification(header, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)

def errornotification(message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(__lang__(30100), message, icon, time, sound)
    
def dialogok(header, line1, line2='', line3=''):
    xbmcgui.Dialog().ok(header, line1, line2, line3)

def dialogyesno(header, line1, line2='', line3=''):
    return xbmcgui.Dialog().yesno(header, line1, line2, line3) #True on yes
    
def dialogokerror(line1, line2='', line3=''):
    xbmcgui.Dialog().ok(__lang__(30101), line1 + "[CR]" + line2 + "[CR]" + line3)

def dialogstreamordownload(header):
    return xbmcgui.Dialog().select(header, [__lang__(30102), __lang__(30114), __lang__(30103), __lang__(30007)])

def dialogunpackordownload(header):
    return xbmcgui.Dialog().select(header, [__lang__(30104), __lang__(30007)])
    
def dialogqueuerunning():
    return xbmcgui.Dialog().select(__lang__(30011), [__lang__(30105), __lang__(30106), __lang__(30107)])

def dialogqueuenotrunning():
    return xbmcgui.Dialog().select(__lang__(30011), [__lang__(30108), __lang__(30109), __lang__(30110), __lang__(30111), __lang__(30112), __lang__(30113)])
    
def dialogtext(header, text):
    xbmcgui.Dialog().textviewer(header, text)
    
def show_settings():
    ADDON.openSettings()

def get_setting(setting):
    return ADDON.getSetting(setting).strip()

def set_setting(setting, value):
    ADDON.setSetting(setting, str(value))

def get_setting_as_bool(setting):
    return get_setting(setting).lower() == "true"

def get_setting_as_float(setting):
    try:
        return float(get_setting(setting))
    except ValueError:
        return 0

def get_setting_as_int(setting):
    try:
        return int(get_setting_as_float(setting))
    except ValueError:
        return 0

def get_string(string_id):
    return ADDON.getLocalizedString(string_id)


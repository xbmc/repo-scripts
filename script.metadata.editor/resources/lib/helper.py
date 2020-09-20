#!/usr/bin/python
# coding: utf-8

########################

import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmcplugin
import json
import time
import datetime
import os
import hashlib
import xml.etree.ElementTree as ET
import requests
import urllib.request as urllib
from urllib.parse import urlencode
from contextlib import contextmanager

########################

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA_PATH = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID))

NOTICE = xbmc.LOGINFO
WARNING = xbmc.LOGWARNING
DEBUG = xbmc.LOGDEBUG
ERROR = xbmc.LOGERROR
LOG_JSON = ADDON.getSettingBool('json_log')
KODI_VERSION = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

DIALOG = xbmcgui.Dialog()

########################


def log(txt,loglevel=DEBUG,json=False,force=False):
    if loglevel in [DEBUG, WARNING, ERROR] or force:
        if force:
            loglevel = NOTICE

        if json:
            txt = json_prettyprint(txt)

        message = u'[ %s ] %s' % (ADDON_ID,txt)
        xbmc.log(msg=message, level=loglevel)


def unicode_string(string):
    string = u'%s' % string
    return string


def remove_quotes(label):
    if not label:
        return ''

    if label.startswith("'") and label.endswith("'") and len(label) > 2:
        label = label[1:-1]
        if label.startswith('"') and label.endswith('"') and len(label) > 2:
            label = label[1:-1]
        elif label.startswith('&quot;') and label.endswith('&quot;'):
            label = label[6:-6]

    return label


def get_joined_items(item):
    if len(item) > 0 and item is not None:
        item = '; '.join(item)
        item = item + ';'
    else:
        item = ''

    return item


def get_list_items(string):
    return remove_empty(string.replace('; ',';').split(';'))


def get_key_item(items,key):
    try:
        return items.get(key)
    except Exception:
        return


def get_rounded_value(value):
    try:
        if not isinstance(value, str) and not isinstance(value, float):
            value = str(value)
        if not isinstance(value, float):
            value = float(value)

        return round(value,1)

    except Exception:
        return


def remove_empty(array):
    cleaned_array = []

    for item in array:
        if not item or item in ['', ';']:
            continue
        cleaned_array.append(item)

    return cleaned_array


def execute(cmd):
    xbmc.executebuiltin(cmd)


def condition(condition):
    return xbmc.getCondVisibility(condition)


def winprop(key, value=None, clear=False, window_id=10000):
    window = xbmcgui.Window(window_id)

    if clear:
        window.clearProperty(key.replace('.json', '').replace('.bool', '').replace('.str', ''))

    elif value is not None:

        if key.endswith('.json'):
            key = key.replace('.json', '')
            value = json.dumps(value)

        elif key.endswith('.bool'):
            key = key.replace('.bool', '')
            value = 'true' if value else 'false'

        elif key.endswith('.str'):
            key = key.replace('.str', '')
            value = str(value)

        window.setProperty(key, value)

    else:
        result = window.getProperty(key.replace('.json', '').replace('.bool', '').replace('.str', ''))

        if result:
            if key.endswith('.json'):
                result = json.loads(result)

            elif key.endswith('.bool'):
                result = result in ('true', '1')

            elif key.endswith('.str'):
                result = eval(result)

        return result


def json_call(method,properties=None,sort=None,query_filter=None,limit=None,params=None,item=None,options=None,limits=None,debug=False):
    json_string = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {}}

    if properties is not None:
        json_string['params']['properties'] = properties

    if limit is not None:
        json_string['params']['limits'] = {'start': 0, 'end': int(limit)}

    if sort is not None:
        json_string['params']['sort'] = sort

    if query_filter is not None:
        json_string['params']['filter'] = query_filter

    if options is not None:
        json_string['params']['options'] = options

    if limits is not None:
        json_string['params']['limits'] = limits

    if item is not None:
        json_string['params']['item'] = item

    if params is not None:
        json_string['params'].update(params)

    jsonrpc_call = json.dumps(json_string)

    result = xbmc.executeJSONRPC(jsonrpc_call)
    result = json.loads(result)

    if debug:
        log('--> JSON CALL: ' + json_prettyprint(json_string), force=True)
        log('--> JSON RESULT: ' + json_prettyprint(result), force=True)

    return result


def json_prettyprint(string):
    return json.dumps(string, sort_keys=True, indent=4, separators=(',', ': '))


def xml_prettyprint(root,level=0):
    i = '\n' + level * '    '

    if len(root):
        if not root.text or not root.text.strip():
            root.text = i + '    '

        if not root.tail or not root.tail.strip():
            root.tail = i

        for root in root:
            xml_prettyprint(root, level+1)

        if not root.tail or not root.tail.strip():
            root.tail = i

    else:
        if level and (not root.tail or not root.tail.strip()):
            root.tail = i


def notification(header=ADDON.getLocalizedString(32000),message=''):
    DIALOG.notification(header, message, icon='special://home/addons/script.metadata.editor/resources/icon.png')


def reload_widgets():
    # Notifies script.embuary.helper to reload widgets
    execute('NotifyAll(%s,Finished)' % ADDON_ID)


@contextmanager
def busy_dialog(force=False):
    if force:
        execute('ActivateWindow(busydialognocancel)')

    elif not winprop('UpdatingRatings.bool'):
        # NFO writing usually only takes < 1s. Just show BusyDialog if it takes longer for whatever reason.
        execute('AlarmClock(BusyAlarmDelay,ActivateWindow(busydialognocancel),00:02,silent)')

    try:
        yield

    finally:
        execute('CancelAlarm(BusyAlarmDelay,silent)')
        execute('Dialog.Close(busydialognocancel)')
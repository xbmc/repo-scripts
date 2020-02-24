#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import xbmc, xbmcaddon
import os, sys
__cwd__      = xbmc.translatePath( xbmcaddon.Addon().getAddonInfo('path') ).decode("utf-8")
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
sys.path.append(__resource__)

import sys
import xbmcgui
import xbmcplugin
import logging
import urlparse

import settings

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_LANGUAGE = ADDON.getLocalizedString

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='[%(levelname)-7s] %(asctime)s %(name)s: %(message)s')


def join_qs(**query_values):
    pairs = ['%s=%s' % kv for kv in list(query_values.items())]
    return '?' + '&'.join(pairs)


def menu_item(plugin, label, **query_values):
    list_item = xbmcgui.ListItem(label)
    list_item.setLabel(label)
    list_item.setLabel2(label)
    list_item.setProperty('IsPlayable', 'false')
    list_item.setThumbnailImage(__cwd__ + '/icon.png')
    list_item.setIconImage(__cwd__ + '/icon.png')
    list_item.setArt(__cwd__ + '/fanart.jpg')

    path = plugin + join_qs(**query_values)
    is_folder = True
    return path, list_item, is_folder


def alarm_menu_items(plugin, **query_values):
    items = []
    for alarm, _ in settings.getAlarms():
        items.append(menu_item(plugin, alarm.label, alarm_id=alarm.id, **query_values))
    return items


def main():
    logger.info('argv: ' + str(sys.argv))

    params = dict(urlparse.parse_qsl(sys.argv[2].lstrip('?')))
    plugin = sys.argv[0]
    items = []

    entering_subfolder = True
    if params.get('type') is None:
        if not settings.getAlarms():
            settings.edit_new_alarm()
        items.append(menu_item(plugin, 'Add Alarm',         type='add_alarm'))
        items.append(menu_item(plugin, 'Edit Alarm',        type='edit_alarm'))
        items.append(menu_item(plugin, 'Clone Alarm',       type='clone_alarm'))
        items.append(menu_item(plugin, 'Trigger Alarm Now', type='trigger_alarm'))
        items.append(menu_item(plugin, 'Delete Alarm',      type='remove_alarm'))
    elif params['type'] == 'add_alarm':
        settings.edit_new_alarm()
    elif params['type'] == 'edit_alarm':
        alarm_id = params.get('alarm_id')
        if alarm_id is not None:
            settings.edit_alarm(int(alarm_id))
            entering_subfolder = False
            del params['alarm_id']
        items += alarm_menu_items(plugin, **params)
    elif params['type'] == 'clone_alarm':
        alarm_id = params.get('alarm_id')
        if alarm_id is not None:
            settings.clone_alarm(int(alarm_id))
            entering_subfolder = False
            del params['alarm_id']
        items += alarm_menu_items(plugin, **params)
    elif params['type'] == 'trigger_alarm':
        alarm_id = params.get('alarm_id')
        if alarm_id is not None:
            settings.trigger_alarm(int(alarm_id))
        else:
            items += alarm_menu_items(plugin, **params)
    elif params['type'] == 'remove_alarm':
        alarm_id = params.get('alarm_id')
        if alarm_id is not None:
            logger.error('Remove alarm is yet to be implemented')
            settings.remove_alarm(int(alarm_id))
            entering_subfolder = False
            del params['alarm_id']
        items += alarm_menu_items(plugin, **params)
    else:
        logger.error('Invalid Parameters ' + sys.argv)

    if items:
        handle = int(sys.argv[1])
        xbmcplugin.setContent(handle, 'movies')
        xbmcplugin.addDirectoryItems(handle, items)
        xbmcplugin.endOfDirectory(handle=handle, succeeded=True, updateListing=not entering_subfolder)


logger.info('script version %s started' % ADDON_VERSION)
main()
logger.info('script version %s stopped' % ADDON_VERSION)


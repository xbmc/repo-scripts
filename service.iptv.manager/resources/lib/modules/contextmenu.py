# -*- coding: utf-8 -*-
"""Context Menu Module"""

from __future__ import absolute_import, division, unicode_literals

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta

from resources.lib import kodiutils

_LOGGER = logging.getLogger(__name__)

CHANNELS_CACHE = 'channels.json'


class ContextMenu:
    """Helper class for PVR Context Menu handling"""

    def __init__(self):
        """Initialise the Context Menu Module"""

    @staticmethod
    def get_direct_uri():
        """Retrieve a direct URI from the selected ListItem."""
        # We use a clever way / ugly hack (pick your choice) to hide the direct stream in Kodi 18.
        # Title [COLOR green]•[/COLOR][COLOR vod="plugin://plugin.video.example/play/whatever"][/COLOR]
        label = sys.listitem.getLabel()  # pylint: disable=no-member
        stream = re.search(r'\[COLOR vod="([^"]+)"\]', label)
        return stream.group(1) if stream else None

    @classmethod
    def get_uri_by_timestamp(cls):
        """Generate an URI based on the timestamp."""
        program = cls._get_selection()
        if not program:
            return None

        # Get a list of addons that can play the selected channel
        # We do the lookup based on Channel Name, since that's all we have
        try:
            addons = cls._get_addons_for_channel(program.get('channel'))
        except IOError:
            if kodiutils.yesno_dialog(message=kodiutils.localize(30713)):  # The EPG data is not up to date...
                from resources.lib.modules.addon import Addon
                Addon.refresh(True)
            return None

        if not addons:
            # Channel was not found.
            _LOGGER.debug('No Add-on was found to play %s', program.get('channel'))
            kodiutils.notification(
                message=kodiutils.localize(30710, channel=program.get('channel')))  # Could not find an Add-on...
            return None

        if len(addons) == 1:
            # Channel has one Add-on. Play it directly.
            _LOGGER.debug('One Add-on was found to play %s: %s', program.get('channel'), addons)
            return cls._format_uri(list(addons.values())[0], program)

        # Ask the user to pick an Add-on
        _LOGGER.debug('Multiple Add-on were found to play %s: %s', program.get('channel'), addons)
        addons_list = list(addons)
        ret = kodiutils.select(heading=kodiutils.localize(30711), options=addons_list)  # Select an Add-on...
        if ret == -1:
            _LOGGER.debug('The selection to play an item from %s was canceled', program.get('channel'))
            return None

        return cls._format_uri(addons.get(addons_list[ret]), program)

    @classmethod
    def _format_uri(cls, uri, program):
        """Play the selected program with the specified URI."""
        format_params = {}
        if '{date}' in uri:
            _LOGGER.warning('Using {date} is deprecated. Please use {start}.')
            format_params.update({'date': program.get('start').isoformat()})

        if '{start}' in uri:
            format_params.update({'start': program.get('start').isoformat()})

        if '{stop}' in uri:
            stop = program.get('start') + timedelta(seconds=program.get('duration'))
            format_params.update({'stop': stop.isoformat()})

        if '{duration}' in uri:
            format_params.update({'duration': program.get('duration')})

        if format_params:
            uri = uri.format(**format_params)

        return uri

    @classmethod
    def _get_selection(cls):
        """Retrieve information about the selected ListItem."""
        # The selected ListItem is available in sys.listitem, but there is not enough data that we can use to know what
        # exact item was selected. Therefore, we use xbmc.getInfoLabel(ListItem.xxx), that references the currently
        # selected ListItem. This is not always the same as the item where the Context Menu was opened on when the
        # selection was moved really quick before the Python code was started. This often happens when using the mouse,
        # but should not happen when using the keyboard or a remote control. Therefore, we do a check to see if the
        # sys.listitem.getPath is the same as xbmc.getInfoLabel(ListItem.FolderPath) before continuing.
        # For now, this is the best we can do.
        #
        # The sys.listitem.getPath() returns a string like "pvr://guide/0016/2020-05-28 09:24:47.epg". We could use the
        # date to find out what item was selected, but we can't match the channel with something that makes sense. It's
        # not the same ID as the ID in the JSON-RPC "PVR.GetChannels" or "PVR.GetChannelDetails" commands.
        #
        # The available fields are:
        # * sys.listitem.getLabel()  # Universiteit van Vlaanderen
        # * sys.listitem.getPath()   # pvr://guide/0016/2020-05-28 09:24:47.epg
        #
        # I would have preferred to use the Channel ID we use for for the epg (like een.be), but that isn't available.
        # We only have a name (ListItem.ChannelName), or the channel number (ListItem.ChannelNumberLabel).

        # Check if the selected item is also the intended item
        if sys.listitem.getPath() != kodiutils.get_info_label('ListItem.FolderPath'):  # pylint: disable=no-member
            # We are in trouble. We know that the data we want to use is invalid, but there is nothing we can do.
            kodiutils.ok_dialog(message=kodiutils.localize(30712))  # Could not determine the selected program...
            return None

        # Load information from the ListItem
        date = kodiutils.get_info_label('ListItem.Date')
        duration = kodiutils.get_info_label('ListItem.Duration')
        channel = kodiutils.to_unicode(kodiutils.get_info_label('ListItem.ChannelName'))

        # Parse begin to a datetime. The ListItem.Date doesn't contain seconds
        date_format = kodiutils.get_region('dateshort') + ' ' + kodiutils.get_region('time').replace(':%S', '')
        try:
            start = datetime.strptime(date, date_format)
        except TypeError:
            start = datetime(*(time.strptime(date, date_format)[0:6]))

        # Parse duration to seconds
        splitted = duration.split(':')
        if len(splitted) == 1:  # %S
            seconds = int(splitted[0])

        elif len(splitted) == 2:  # %M:%S
            seconds = int(splitted[0]) * 60 + int(splitted[1])

        elif len(splitted) == 3:  # %H:%M:%S
            seconds = int(splitted[0]) * 3600 + int(splitted[1]) * 60 + int(splitted[2])

        else:
            raise Exception('Unknown duration %s' % duration)

        return dict(
            start=start,
            duration=seconds,
            channel=channel,
        )

    @staticmethod
    def write_channels(channels):
        """Write the channel data to a file."""
        output_dir = kodiutils.addon_profile()

        # Make sure our output dir exists
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        channels_path = os.path.join(output_dir, CHANNELS_CACHE)
        with open(channels_path, 'w') as fdesc:
            json.dump(channels, fdesc)

    @staticmethod
    def _get_addons_for_channel(channel):
        """Returns a list of Add-ons that can play this channel."""
        channels_path = os.path.join(kodiutils.addon_profile(), CHANNELS_CACHE)
        with open(channels_path, 'r') as fdesc:
            data = json.load(fdesc)

        matches = {}
        for _addon in data:
            for _channel in _addon.get('channels', []):
                if _channel.get('name').lower() == channel.lower() and _channel.get('vod') is not None:
                    matches.update({_addon.get('addon_name'): _channel.get('vod')})

        return matches

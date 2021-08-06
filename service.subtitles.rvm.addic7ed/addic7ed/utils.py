# -*- coding: utf-8 -*-
# Module: functions
# Author: Roman V. M.
# Created on: 03.12.2014
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import absolute_import, unicode_literals
import json
import re
from collections import namedtuple
from kodi_six import xbmc
from .addon import ADDON_ID
from .exceptions import ParseError

__all__ = [
    'logger',
    'get_now_played',
    'normalize_showname',
    'get_languages',
    'parse_filename',
]

# Convert show names from TheTVDB format to Addic7ed.com format
# Keys must be all lowercase
NAME_CONVERSIONS = {
    'castle (2009)': 'castle',
    'law & order: special victims unit': 'Law and order SVU',
    'bodyguard (2018)': 'bodyguard',
}

episode_patterns = (
    re.compile(r'^(.*?)[ \.](?:\d*?[ \.])?s(\d+)[ \.]?e(\d+)\.', re.I | re.U),
    re.compile(r'^(.*?)[ \.](?:\d*?[ \.])?(\d+)x(\d+)\.', re.I | re.U),
    re.compile(r'^(.*?)[ \.](?:\d*?[ \.])?(\d{1,2}?)[ \.]?(\d{2})\.', re.I | re.U),
    )
spanish_re = re.compile(r'Spanish \(.*?\)')

LanguageData = namedtuple('LanguageData', ['kodi_lang', 'add7_lang'])


class logger(object):
    @staticmethod
    def log(message, level=xbmc.LOGDEBUG):
        xbmc.log('{0}: {1}'.format(ADDON_ID, message), level)

    @staticmethod
    def info(message):
        logger.log(message, xbmc.LOGINFO)

    @staticmethod
    def error(message):
        logger.log(message, xbmc.LOGERROR)

    @staticmethod
    def debug(message):
        logger.log(message, xbmc.LOGDEBUG)


def get_now_played():
    """
    Get info about the currently played file via JSON-RPC

    :return: currently played item's data
    :rtype: dict
    """
    request = json.dumps({
        'jsonrpc': '2.0',
        'method': 'Player.GetItem',
        'params': {
            'playerid': 1,
            'properties': ['showtitle', 'season', 'episode']
         },
        'id': '1'
    })
    item = json.loads(xbmc.executeJSONRPC(request))['result']['item']
    item['file'] = xbmc.Player().getPlayingFile()  # It provides more correct result
    return item


def normalize_showname(showname):
    """
    Normalize showname if there are differences
    between TheTVDB and Addic7ed

    :param showname: TV show name
    :return: normalized show name
    """
    showname = showname.strip().lower()
    if showname in NAME_CONVERSIONS:
        showname = NAME_CONVERSIONS[showname]
    return showname.replace(':', '')


def get_languages(languages_raw):
    """
    Create the list of pairs of language names.
    The 1st item in a pair is used by Kodi.
    The 2nd item in a pair is used by
    the addic7ed web site parser.

    :param languages_raw: the list of subtitle languages from Kodi
    :return: the list of language pairs
    """
    languages = []
    for language in languages_raw:
        kodi_lang = language
        if 'English' in kodi_lang:
            add7_lang = 'English'
        elif kodi_lang == 'Portuguese (Brazil)':
            add7_lang = 'Portuguese (Brazilian)'
        elif spanish_re.search(kodi_lang) is not None:
            add7_lang = 'Spanish (Latin America)'
        else:
            add7_lang = language
        languages.append(LanguageData(kodi_lang, add7_lang))
    return languages


def parse_filename(filename):
    """
    Filename parser for extracting show name, season # and episode # from
    a filename.

    :param filename: episode filename
    :return: parsed showname, season and episode
    :raises ParseError: if the filename does not match any episode patterns
    """
    filename = filename.replace(' ', '.')
    for regexp in episode_patterns:
        episode_data = regexp.search(filename)
        if episode_data is not None:
            showname = episode_data.group(1).replace('.', ' ')
            season = episode_data.group(2).zfill(2)
            episode = episode_data.group(3).zfill(2)
            return showname, season, episode
    raise ParseError

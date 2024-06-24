# Copyright (C) 2016, Roman Miroshnychenko aka Roman V.M.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import re
import shutil
import sys
from collections import namedtuple
from urllib import parse as urlparse

import xbmc
import xbmcgui
import xbmcplugin

from addic7ed import parser
from addic7ed.addon import ADDON, PROFILE, ICON, get_ui_string
from addic7ed.exceptions import NoSubtitlesReturned, ParseError, SubsSearchError, \
    Add7ConnectionError
from addic7ed.parser import parse_filename, normalize_showname, get_languages
from addic7ed.utils import get_now_played
from addic7ed.webclient import Session

__all__ = ['router']

logger = logging.getLogger(__name__)

TEMP_DIR = os.path.join(PROFILE, 'temp')
HANDLE = int(sys.argv[1])


VIDEOFILE_EXTENSIONS = {'.avi', '.mkv', '.mp4', '.ts', '.m2ts', '.mov'}
DIALOG = xbmcgui.Dialog()
RELEASE_RE = re.compile(r'-(.*?)(?:\[.*?\])?\.')

EpisodeData = namedtuple('EpisodeData',
                         ['showname', 'season', 'episode', 'filename'])


def _detect_synced_subs(subs_list, filename):
    """
    Try to detect if subs from Addic7ed.com match the file being played

    :param subs_list: list or generator of subtitle items
    :param filename: the name of an episode videofile being played
    :return: the generator of subtitles  "sync" property
    """
    listing = []
    for item in subs_list:
        release_match = RELEASE_RE.search(filename)
        if release_match is not None:
            release = release_match.group(1).lower()
        else:
            release = ''
        lowercase_version = item.version.lower()
        resync_pattern = rf'sync.+?{release}'
        synced = (release and
                  release in lowercase_version and
                  re.search(resync_pattern, lowercase_version, re.I) is None)
        listing.append((item, synced))
    return listing


def display_subs(subs_list, episode_url, filename):
    """
    Display the list of found subtitles

    :param subs_list: the list or generator of tuples (subs item, synced)
    :param episode_url: the URL for the episode page on addic7ed.com.
        It is needed for downloading subs as 'Referer' HTTP header.
    :param filename: the name of the video-file being played.

    Each item in the displayed list is a ListItem instance with the following
    properties:

    - label: Kodi language name (e.g. 'English')
    - label2: a descriptive text for subs
    - thumbnailImage: a 2-letter language code (e.g. 'en') to display a country
      flag.
    - 'hearing_imp': if 'true' then 'CC' icon is displayed for the list item.
    - 'sync': if 'true' then 'SYNC' icon is displayed for the list item.
    - url: a plugin call URL for downloading selected subs.
    """
    subs_list = sorted(
        _detect_synced_subs(subs_list, filename),
        key=lambda i: i[1],
        reverse=True
    )
    for item, synced in subs_list:
        if item.unfinished:
            continue
        list_item = xbmcgui.ListItem(label=item.language, label2=item.version)
        list_item.setArt(
            {'thumb': xbmc.convertLanguage(item.language, xbmc.ISO_639_1)}
        )
        if item.hi:
            list_item.setProperty('hearing_imp', 'true')
        if synced:
            list_item.setProperty('sync', 'true')
        url = '{}?{}'.format(  # pylint: disable=consider-using-f-string
            sys.argv[0],
            urlparse.urlencode(
                {'action': 'download',
                 'link': item.link,
                 'ref': episode_url,
                 'filename': filename}
            )
        )
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item,
                                    isFolder=False)


def download_subs(link, referrer, filename):
    """
    Download selected subs

    :param link: str - a download link for the subs.
    :param referrer: str - a referer URL for the episode page
        (required by addic7ed.com).
    :param filename: str - the name of the video-file being played.

    The function must add a single ListItem instance with one property:
        label - the download location for subs.
    """
    # Re-create a download location in a temporary folder
    if not os.path.exists(PROFILE):
        os.mkdir(PROFILE)
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.mkdir(TEMP_DIR)
    # Combine a path where to download the subs
    filename = os.path.splitext(filename)[0] + '.srt'
    subspath = os.path.join(TEMP_DIR, filename)
    # Download the subs from addic7ed.com
    try:
        Session().download_subs(link, referrer, subspath)
    except Add7ConnectionError:
        logger.error('Unable to connect to addic7ed.com')
        DIALOG.notification(get_ui_string(32002), get_ui_string(32005), 'error')
    except NoSubtitlesReturned:
        DIALOG.notification(get_ui_string(32002), get_ui_string(32003), 'error',
                            3000)
        logger.error('Exceeded daily limit for subs downloads.')
    else:
        # Create a ListItem for downloaded subs and pass it
        # to the Kodi subtitles engine to move the downloaded subs file
        # from the temp folder to the designated
        # location selected by 'Subtitle storage location' option
        # in 'Settings > Video > Subtitles' section.
        # A 2-letter language code will be added to subs filename.
        list_item = xbmcgui.ListItem(label=subspath)
        xbmcplugin.addDirectoryItem(handle=HANDLE,
                                    url=subspath,
                                    listitem=list_item,
                                    isFolder=False)
        DIALOG.notification(get_ui_string(32000), get_ui_string(32001), ICON,
                            3000, False)
        logger.info('Subs downloaded.')


def extract_episode_data():
    """
    Extract episode data for searching

    :return: named tuple (showname, season, episode, filename)
    :raises ParseError: if cannot determine episode data
    """
    now_played = get_now_played()
    logger.debug('Played file info: %s', now_played)
    showname = now_played['showtitle'] or xbmc.getInfoLabel('VideoPlayer.TVshowtitle')
    parsed = urlparse.urlparse(now_played['file'])
    filename = os.path.basename(parsed.path)
    if ADDON.getSetting('use_filename') == 'true' or not showname:
        # Try to get showname/season/episode data from
        # the filename if 'use_filename' setting is true
        # or if the video-file does not have library metadata.
        try:
            logger.debug('Using filename: %s', filename)
            showname, season, episode = parse_filename(filename)
        except ParseError:
            logger.debug('Filename %s failed. Trying ListItem.Label...', filename)
            try:
                filename = now_played['label']
                logger.debug('Using filename: %s', filename)
                showname, season, episode = parse_filename(filename)
            except ParseError:
                logger.error('Unable to determine episode data for %s', filename)
                DIALOG.notification(get_ui_string(32002), get_ui_string(32006),
                                    'error', 3000)
                raise
    else:
        # Get get showname/season/episode data from
        # Kodi if the video-file is being played from
        # the TV-Shows library.
        season = str(now_played['season'] if now_played['season'] > -1
                     else xbmc.getInfoLabel('VideoPlayer.Season'))
        season = season.zfill(2)
        episode = str(now_played['episode'] if now_played['episode'] > -1
                      else xbmc.getInfoLabel('VideoPlayer.Episode'))
        episode = episode.zfill(2)
        if not os.path.splitext(filename)[1].lower() in VIDEOFILE_EXTENSIONS:
            filename = f'{showname}.{season}x{episode}.foo'
        logger.debug('Using library metadata: %s - %sx%s', showname, season, episode)
    return EpisodeData(showname, season, episode, filename)


def search_subs(params):
    logger.info('Searching for subs...')
    languages = get_languages(
        urlparse.unquote_plus(params['languages']).split(',')
    )
    # Search subtitles in Addic7ed.com.
    if params['action'] == 'search':
        try:
            episode_data = extract_episode_data()
        except ParseError:
            return
        # Create a search query string
        showname = normalize_showname(episode_data.showname)
        query = f'{showname} {episode_data.season}x{episode_data.episode}'
        filename = episode_data.filename
    else:
        # Get the query string typed on the on-screen keyboard
        query = params['searchstring']
        filename = query
    if query:
        logger.debug('Search query: %s', query)
        try:
            results = parser.search_episode(query, languages)
        except Add7ConnectionError:
            logger.error('Unable to connect to addic7ed.com')
            DIALOG.notification(
                get_ui_string(32002), get_ui_string(32005), 'error'
            )
        except SubsSearchError:
            logger.info('No subs for "%s" found.', query)
        else:
            if isinstance(results, list):
                logger.info('Multiple episodes found:\n%s', results)
                i = DIALOG.select(
                    get_ui_string(32008), [item.title for item in results]
                )
                if i >= 0:
                    try:
                        results = parser.get_episode(results[i].link, languages)
                    except Add7ConnectionError:
                        logger.error('Unable to connect to addic7ed.com')
                        DIALOG.notification(get_ui_string(32002),
                                            get_ui_string(32005), 'error')
                        return
                    except SubsSearchError:
                        logger.info('No subs found.')
                        return
                else:
                    logger.info('Episode selection cancelled.')
                    return
            logger.info('Found subs for "%s"', query)
            display_subs(results.subtitles, results.episode_url, filename)


def router(paramstring):
    """
    Dispatch plugin functions depending on the call paramstring

    :param paramstring: URL-encoded plugin call parameters
    :type paramstring: str
    """
    # Get plugin call params
    params = dict(urlparse.parse_qsl(paramstring))
    if params['action'] in ('search', 'manualsearch'):
        # Search and display subs.
        search_subs(params)
    elif params['action'] == 'download':
        download_subs(
            params['link'], params['ref'],
            urlparse.unquote(params['filename'])
        )
    xbmcplugin.endOfDirectory(HANDLE)

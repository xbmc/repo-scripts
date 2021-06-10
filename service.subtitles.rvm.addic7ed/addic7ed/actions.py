# coding: utf-8
# Created on: 07.04.2016
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)

from __future__ import absolute_import, unicode_literals
import os
import sys
import re
import shutil
from collections import namedtuple
from six import PY2
from six.moves import urllib_parse as urlparse
from kodi_six import xbmc, xbmcplugin, xbmcgui
from . import parser
from .addon import addon, profile, get_ui_string, icon
from .exceptions import DailyLimitError, ParseError, SubsSearchError, \
    Add7ConnectionError
from .utils import logger, get_languages, get_now_played, parse_filename, \
    normalize_showname

__all__ = ['router']

temp_dir = os.path.join(profile, 'temp')
handle = int(sys.argv[1])


VIDEOFILES = {'.avi', '.mkv', '.mp4', '.ts', '.m2ts', '.mov'}
dialog = xbmcgui.Dialog()
release_re = re.compile(r'-(.*?)(?:\[.*?\])?\.')

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
        release_match = release_re.search(filename)
        if release_match is not None:
            release = release_match.group(1).lower()
        else:
            release = ''
        lowercase_version = item.version.lower()
        resync_pattern = r'sync.+?{}'.format(release)
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
        url = '{0}?{1}'.format(
            sys.argv[0],
            urlparse.urlencode(
                {'action': 'download',
                 'link': item.link,
                 'ref': episode_url,
                 'filename': filename}
            )
        )
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=list_item,
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
    if not os.path.exists(profile):
        os.mkdir(profile)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(temp_dir)
    # Combine a path where to download the subs
    filename = os.path.splitext(filename)[0] + '.srt'
    subspath = os.path.join(temp_dir, filename)
    # Download the subs from addic7ed.com
    try:
        parser.download_subs(link, referrer, subspath)
    except Add7ConnectionError:
        logger.error('Unable to connect to addic7ed.com')
        dialog.notification(get_ui_string(32002), get_ui_string(32005), 'error')
    except DailyLimitError:
        dialog.notification(get_ui_string(32002), get_ui_string(32003), 'error',
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
        xbmcplugin.addDirectoryItem(handle=handle,
                                    url=subspath,
                                    listitem=list_item,
                                    isFolder=False)
        dialog.notification(get_ui_string(32000), get_ui_string(32001), icon,
                            3000, False)
        logger.info('Subs downloaded.')


def extract_episode_data():
    """
    Extract episode data for searching

    :return: named tuple (showname, season, episode, filename)
    :raises ParseError: if cannot determine episode data
    """
    now_played = get_now_played()
    parsed = urlparse.urlparse(now_played['file'])
    filename = os.path.basename(parsed.path)
    if addon.getSetting('use_filename') == 'true' or not now_played['showtitle']:
        # Try to get showname/season/episode data from
        # the filename if 'use_filename' setting is true
        # or if the video-file does not have library metadata.
        try:
            logger.debug('Using filename: {0}'.format(filename))
            showname, season, episode = parse_filename(filename)
        except ParseError:
            logger.debug(
                'Filename {0} failed. Trying ListItem.Label...'.format(filename)
            )
            try:
                filename = now_played['label']
                logger.debug('Using filename: {0}'.format(filename))
                showname, season, episode = parse_filename(filename)
            except ParseError:
                logger.error(
                    'Unable to determine episode data for {0}'.format(filename)
                )
                dialog.notification(get_ui_string(32002), get_ui_string(32006),
                                    'error', 3000)
                raise
    else:
        # Get get showname/season/episode data from
        # Kodi if the video-file is being played from
        # the TV-Shows library.
        showname = now_played['showtitle']
        season = str(now_played['season']).zfill(2)
        episode = str(now_played['episode']).zfill(2)
        if not os.path.splitext(filename)[1].lower() in VIDEOFILES:
            filename = '{0}.{1}x{2}.foo'.format(
                showname, season, episode
            )
        logger.debug('Using library metadata: {0} - {1}x{2}'.format(
            showname, season, episode)
        )
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
        query = '{0} {1}x{2}'.format(
            normalize_showname(episode_data.showname),
            episode_data.season,
            episode_data.episode
        )
        filename = episode_data.filename
    else:
        # Get the query string typed on the on-screen keyboard
        query = params['searchstring']
        filename = query
    if query:
        logger.debug('Search query: {0}'.format(query))
        try:
            results = parser.search_episode(query, languages)
        except Add7ConnectionError:
            logger.error('Unable to connect to addic7ed.com')
            dialog.notification(
                get_ui_string(32002), get_ui_string(32005), 'error'
            )
        except SubsSearchError:
            logger.info('No subs for "{}" found.'.format(query))
        else:
            if isinstance(results, list):
                logger.info('Multiple episodes found:\n{0}'.format(results))
                i = dialog.select(
                    get_ui_string(32008), [item.title for item in results]
                )
                if i >= 0:
                    try:
                        results = parser.get_episode(results[i].link, languages)
                    except Add7ConnectionError:
                        logger.error('Unable to connect to addic7ed.com')
                        dialog.notification(get_ui_string(32002),
                                            get_ui_string(32005), 'error')
                        return
                    except SubsSearchError:
                        logger.info('No subs found.')
                        return
                else:
                    logger.info('Episode selection cancelled.')
                    return
            logger.info('Found subs for "{0}"'.format(query))
            display_subs(results.subtitles, results.episode_url,
                         filename)


def router(paramstring):
    """
    Dispatch plugin functions depending on the call paramstring

    :param paramstring: URL-encoded plugin call parameters
    :type paramstring: str
    """
    # Get plugin call params
    if PY2:
        paramstring = urlparse.unquote(paramstring).decode('utf-8')
    params = dict(urlparse.parse_qsl(paramstring))
    if params['action'] in ('search', 'manualsearch'):
        # Search and display subs.
        search_subs(params)
    elif params['action'] == 'download':
        download_subs(
            params['link'], params['ref'],
            urlparse.unquote(params['filename'])
        )
    xbmcplugin.endOfDirectory(handle)

# -*- coding: utf-8 -*-
import sys
import urllib
import shutil
from os import path

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import xbmcplugin

from resources.lib.bsplayer import BSPlayer
from resources.lib.utils import log, notify, get_params, get_video_path, get_languages_dict

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__ = xbmc.translatePath(path.join(__profile__, 'temp', '')).decode("utf-8")


params = get_params()
log("BSPlayer.params", "Current Action: %s." % params['action'])
if params['action'] == 'search':
    video_path = get_video_path()
    if video_path.startswith('http://') or video_path.startswith('https://'):
        notify(__scriptname__, __language__, 32001)
        log("BSPlayer.get_video_path", "Streaming not supported.")

    log("BSPlayer.video_path", "Current Video Path: %s." % video_path)
    languages = get_languages_dict(params['languages'])
    log("BSPlayer.languages", "Current Languages: %s." % languages)

    with BSPlayer() as bsp:
        subtitles = bsp.search_subtitles(video_path, language_ids=languages.keys())
        for subtitle in sorted(subtitles, key=lambda s: s['subLang']):
            list_item = xbmcgui.ListItem(
                label=languages[subtitle['subLang']],
                label2=subtitle['subName'],
                thumbnailImage=xbmc.convertLanguage(subtitle["subLang"], xbmc.ISO_639_1)
            )

            plugin_url = "plugin://{path}/?{query}".format(
                path=__scriptid__,
                query=urllib.urlencode(dict(
                    action='download',
                    link=subtitle['subDownloadLink'],
                    file_name=subtitle['subName'],
                    format=subtitle['subFormat']
                ))
            )
            log("BSPlayer.plugin_url", "Plugin Url Created: %s." % plugin_url)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=plugin_url, listitem=list_item, isFolder=False)
elif params['action'] == 'manualsearch':
    notify(__scriptname__, __language__, 32002)
    log("BSPlayer.manualsearch", "Manual search not supported.")
elif params['action'] == 'download':
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    if params['format'] in ["srt", "sub", "txt", "smi", "ssa", "ass"]:
        subtitle_path = path.join(__temp__, params['file_name'])
        if BSPlayer.download_subtitles(params['link'], subtitle_path):
            log("BSPlayer.download_subtitles", "Subtitles Download Successfully From: %s." % params['link'])
            list_item = xbmcgui.ListItem(label=subtitle_path)
            log("BSPlayer.download", "Downloaded Subtitle Path: %s" % subtitle_path)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle_path, listitem=list_item, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

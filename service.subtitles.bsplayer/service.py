# -*- coding: utf-8 -*-

import sys
import urllib
import shutil
import urlparse
from os import path

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import xbmcplugin

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

sys.path.append(__resource__)

from bsplayer import BSPlayer


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg)).encode('utf-8'), level=xbmc.LOGDEBUG)


def get_params(params_str=""):
    params_str = params_str or sys.argv[2]
    return dict(urlparse.parse_qsl(params_str.lstrip('?')))


def get_video_path(xbmc_path=''):
    xbmc_path = xbmc_path or urlparse.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))

    if xbmc_path.startswith('rar://'):
        return path.dirname(xbmc_path.replace('rar://', ''))
    elif xbmc_path.startswith('stack://'):
        return xbmc_path.split(" , ")[0].replace('stack://', '')

    return xbmc_path


def get_languages_dict(languages_param):
    langs = {}
    for lang in languages_param.split(','):
        if lang == "Portuguese (Brazil)":
            langs["pob"] = lang
        elif lang == "Greek":
            langs["ell"] = lang
        else:
            langs[xbmc.convertLanguage(lang, xbmc.ISO_639_2)] = lang
    return langs


params = get_params()
log("BSPlayers.params", "Current Action: %s." % params['action'])
if params['action'] == 'search':
    video_path = get_video_path()
    log("BSPlayers.video_path", "Current Video Path: %s." % video_path)
    languages = get_languages_dict(params['languages'])
    log("BSPlayers.languages", "Current Languages: %s." % languages)

    with BSPlayer(log=log) as bsp:
        subtitles = bsp.search_subtitles(video_path, language_ids=languages.keys())
        for subtitle in subtitles:
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
            log("BSPlayers.plugin_url", "Plugin Url Created: %s." % plugin_url)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=plugin_url, listitem=list_item, isFolder=False)
elif params['action'] == 'manualsearch':
    log("BSPlayer.manualsearch", "Cannot Search Manually.")
elif params['action'] == 'download':
    if xbmcvfs.exists(__temp__):
        shutil.rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    if params['format'] in ["srt", "sub", "txt", "smi", "ssa", "ass"]:
        subtitle_path = path.join(__temp__, params['file_name'])
        if BSPlayer.download_subtitles(params['link'], subtitle_path):
            log("BSPlayer.download_subtitles", "Subtitles Download Successfully From: %s." % params['link'])
            list_item = xbmcgui.ListItem(label=subtitle_path)
            log("BSPlayer.download", "Downloaded Subtitle Path: %s." % subtitle_path)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=subtitle_path, listitem=list_item, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))

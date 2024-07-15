# -*- coding: utf-8 -*-
"""
Subtitle add-on for Kodi 19+ derived from https://github.com/taxigps/xbmc-addons-chinese/tree/master/service.subtitles.zimuku
Copyright (C) <2021>  <root@wokanxing.info>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import os
import sys
import time
import urllib
import urllib.parse

import requests
from bs4 import BeautifulSoup
from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs

import zimuku_agent as zmkagnt
import zimuku_archive

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__resource__ = xbmcvfs.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, 'temp'))

sys.path.append(__resource__)


class Logger:
    def log(self, module, msg, level=xbmc.LOGDEBUG):
        xbmc.log("{0}::{1} - {2}".format(__scriptname__,
                 module, msg), level=level)


class Unpacker:
    def unpack(self, path):
        return zimuku_archive.unpack(path)


def Search(items):
    user_year = __addon__.getSetting("useyear")
    search_suffix = ' '+items['year'] if user_year == 'true' else ''
    if items['mansearch']:
        search_str = items['mansearchstr']
    elif items['tvshow'] != '':
        search_str = items['tvshow']+search_suffix
    else:
        search_str = items['title']+search_suffix
    logger.log(sys._getframe().f_code.co_name, "Search for [%s], item: %s" %
               (os.path.basename(items['file_original_path']), items), level=xbmc.LOGINFO)

    subtitle_list = agent.search(search_str, items)

    if len(subtitle_list) != 0:
        for s in subtitle_list:
            listitem = xbmcgui.ListItem(
                label=s["language_name"], label2=s["filename"])
            listitem.setArt({
                'icon': s["rating"],
                'thumb': s["language_flag"]
            })
            listitem.setProperty("sync", "false")
            listitem.setProperty("hearing_imp", "false")

            url = "plugin://%s/?action=download&link=%s" % (
                __scriptid__, s["link"])
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=url, listitem=listitem, isFolder=False)
    else:
        logger.log(sys._getframe().f_code.co_name, "字幕未找到，参数：%s" %
                   items, level=xbmc.LOGINFO)


def Download(url):
    """
    调用 agent 的下载功能，用户在 UI 选定之后传回给 Kodi
    """
    if not xbmcvfs.exists(__temp__.replace('\\', '/')):
        xbmcvfs.mkdirs(__temp__)
    dirs, files = xbmcvfs.listdir(__temp__)
    for file in files:
        xbmcvfs.delete(os.path.join(__temp__, file))

    logger.log(sys._getframe().f_code.co_name, "Download page: %s" % (url))

    l1, l2, l3 = agent.download(url)
    logger.log(sys._getframe().f_code.co_name, "%s; %s; %s" % (l1, l2, l3))
    sub_name_list, short_sub_name_list, sub_file_list = agent.get_preferred_subs(
        l1, l2, l3)

    if len(sub_name_list) == 0:
        # FIXME: 不应该有这问题
        return []
    if len(sub_name_list) == 1:
        selected_sub = sub_file_list[0]
    else:
        cut_fn = __addon__.getSetting("cutsubfn")
        sel = xbmcgui.Dialog().select('请选择压缩包中的字幕', short_sub_name_list if cut_fn ==
                                      'true' else sub_name_list)
        if sel == -1:
            sel = 0
        selected_sub = sub_file_list[sel]

    logger.log(sys._getframe().f_code.co_name,
               "SUB FILE TO USE: %s" % selected_sub)
    return [selected_sub]


def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


def handle_params(params):
    """
    对应界面上的按钮/功能，一个是搜索，一个是下载
    """

    if params['action'] == 'search' or params['action'] == 'manualsearch':
        item = {'temp': False, 'rar': False, 'mansearch': False}
        item['year'] = xbmc.getInfoLabel("VideoPlayer.Year")  # Year
        item['season'] = str(xbmc.getInfoLabel("VideoPlayer.Season"))  # Season
        item['episode'] = str(xbmc.getInfoLabel("VideoPlayer.Episode"))
        item['tvshow'] = xbmc.getInfoLabel("VideoPlayer.TVshowtitle")  # Show
        # try to get original title
        item['title'] = xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
        # Full path of a playing file
        item['file_original_path'] = urllib.parse.unquote(
            xbmc.Player().getPlayingFile())
        item['3let_language'] = []

        if 'searchstring' in params:
            item['mansearch'] = True
            item['mansearchstr'] = params['searchstring']

        for lang in urllib.parse.unquote(params['languages']).split(","):
            item['3let_language'].append(
                xbmc.convertLanguage(lang, xbmc.ISO_639_2))

        if item['title'] == "":
            # no original title, get just Title
            item['title'] = xbmc.getInfoLabel("VideoPlayer.Title")
            # get movie title and year if is filename
            if item['title'] == os.path.basename(xbmc.Player().getPlayingFile()):
                title, year = xbmc.getCleanMovieTitle(item['title'])
                item['title'] = title.replace('[', '').replace(']', '')
                item['year'] = year

        # Check if season is "Special"
        if item['episode'].lower().find("s") > -1:
            #
            item['season'] = "0"
            item['episode'] = item['episode'][-1:]

        if (item['file_original_path'].find("http") > -1):
            item['temp'] = True

        elif (item['file_original_path'].find("rar://") > -1):
            item['rar'] = True
            item['file_original_path'] = os.path.dirname(
                item['file_original_path'][6:])

        elif (item['file_original_path'].find("stack://") > -1):
            stackPath = item['file_original_path'].split(" , ")
            item['file_original_path'] = stackPath[0][8:]

        Search(item)

    elif params['action'] == 'download':
        subs = Download(params["link"])
        for sub in subs:
            listitem = xbmcgui.ListItem(label=sub)
            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url=sub, listitem=listitem, isFolder=False)


def run():
    global agent, logger

    # 获取参数
    params = get_params()

    logger = Logger()
    logger.log(sys._getframe().f_code.co_name, "HANDLE PARAMS：%s" % params)

    # 获取url
    zimuku_base_url = __addon__.getSetting("ZiMuKuUrl")
    tpe = __addon__.getSetting("subtype")
    lang = __addon__.getSetting("sublang")

    if __addon__.getSetting("proxy_follow_kodi") != "true":
        proxy = ("" if __addon__.getSetting("proxy_use") != "true"
                 else __addon__.getSetting("proxy_server"))
        os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = proxy

    ocrUrl= __addon__.getSetting("ocr_url")

    # 查询
    agent = zmkagnt.Zimuku_Agent(zimuku_base_url, __temp__, logger, Unpacker(),
                                 {'subtype': tpe, 'sublang': lang}, ocrUrl)

    handle_params(params)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

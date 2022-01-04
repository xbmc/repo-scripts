# -*- coding: UTF-8 -*-
# Copyright, 2020, HiGhLaNdeR, Leinad4Mind.
# This program is distributed under the terms of the GNU General Public License, version 2.
# http://www.gnu.org/licenses/gpl.txt


import os
from os.path import join as pjoin
import sys
import time
import unicodedata
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import fnmatch


_addon      = xbmcaddon.Addon()
_scriptname = _addon.getAddonInfo('name')
_language   = _addon.getLocalizedString
_dialog     = xbmcgui.Dialog()

debug   = _addon.getSetting('DEBUG')
is_android = (xbmc.getCondVisibility('system.platform.linux') and xbmc.getCondVisibility('system.platform.android'))

SUB_EXTS          = ['srt', 'sub', 'txt', 'ass', 'ssa', 'smi', 'vtt', 'xml']
HTTP_USER_AGENT   = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'


def _log(module, msg):
    s = "### [%s] - %s" % (module, msg)
    xbmc.log(s, level=xbmc.LOGDEBUG)

def log(msg):
    if debug == 'true': _log(_scriptname, msg)

def xbmc_extract(SRC, DEST):
    dd_ext, ff_ext = xbmcvfs.listdir(SRC)
    for ff in ff_ext:
        ext = os.path.splitext(ff)[1][1:].lower()
        if ext in SUB_EXTS:
            src_file = pjoin(SRC,ff).replace('\\','/')
            dst_file = pjoin(xbmc.translatePath(DEST),ff)
            success = xbmcvfs.copy(src_file,dst_file)
            if not success:
                log("Error extracting: '%s' to '%s'" % (src_file,dst_file))
            else:
                log("Extracting: '%s' to '%s'" % (src_file,dst_file))
        else:
            log("NO FILES YET...")
    for dd in dd_ext:
        dd_mk = pjoin(DEST,dd).replace('\\','/')
        success_mk = xbmcvfs.mkdir(dd_mk)
        if not success_mk:
            log("Error creating directory: '%s'" % dd_mk)
        else:
            log("Created directory: '%s'" % dd_mk)
        now_SRC = pjoin(SRC,dd,'').replace('\\','/')
        now_DEST = pjoin(DEST,dd)
        success_dd = xbmc_extract(now_SRC,now_DEST)
        if not success_dd:
            log("Error extracting inside dir: '%s' to '%s'" % (now_SRC,now_DEST))
        else:
            log("Extracting (back into the ff loop: '%s' to '%s'" % (now_SRC,now_DEST))

def recursive_glob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
        for extension in pattern:
            for filename in fnmatch.filter(files, '*.' + extension): results.append(os.path.join(base, filename))
    return results


def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params.endswith('/'):
            params = params[:-2]  # XXX: Should be [:-1] ?
        pairsofparams = cleanedparams.split('&')
        param = {}
        for pair in pairsofparams:
            splitparams = {}
            splitparams = pair.split('=')
            if len(splitparams) == 2:
                param[splitparams[0]] = splitparams[1]
    return param


def bubbleSort(subtitles_list):
    for n in range(0, len(subtitles_list)):
          for i in range(1, len(subtitles_list)):
              temp = subtitles_list[i]
              if subtitles_list[i]["sync"] > subtitles_list[i-1]["sync"]:
                  subtitles_list[i] = subtitles_list[i-1]
                  subtitles_list[i-1] = temp
    return subtitles_list


def cleanDirectory(directory):
    try:
        if xbmcvfs.exists(directory + "/"):
            for root, dirs, files in os.walk(directory):
                for f in files:
                    file = os.path.join(root, f)
                    xbmcvfs.delete(file)
                for d in dirs:
                    dir = os.path.join(root, d)
                    xbmcvfs.rmdir(dir)
    except:
        pass
    if not xbmcvfs.exists(directory):
        xbmcvfs.mkdirs(directory)

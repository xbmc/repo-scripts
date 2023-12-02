# -*- coding: UTF-8 -*-
# Copyright, 2020, HiGhLaNdeR, Leinad4Mind.
# This program is distributed under the terms of the GNU General Public License, version 2.
# http://www.gnu.org/licenses/gpl.txt


import os
from os.path import join as os_path_join
import sys
import xbmc
import xbmcaddon
import xbmcvfs
import fnmatch
import shutil


_addon      = xbmcaddon.Addon()
_scriptname = _addon.getAddonInfo('name')

debug       = _addon.getSetting('DEBUG')
is_android  = (xbmc.getCondVisibility('system.platform.linux') and xbmc.getCondVisibility('system.platform.android'))

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
            src_file = os_path_join(SRC,ff).replace('\\','/')
            dst_file = os_path_join(xbmc.translatePath(DEST),ff)
            success = xbmcvfs.copy(src_file,dst_file)
            if not success:
                log(f"Error extracting: '{src_file}' to '{dst_file}'")
            else:
                log(f"Extracting: '{src_file}' to '{dst_file}'")
        else:
            log("NO FILES YET...")
    for dd in dd_ext:
        dd_mk = os_path_join(DEST,dd).replace('\\','/')
        success_mk = xbmcvfs.mkdir(dd_mk)
        if not success_mk:
            log(f"Error creating directory: '{dd_mk}'")
        else:
            log(f"Created directory: '{dd_mk}'")
        now_SRC = os_path_join(SRC,dd,'').replace('\\','/')
        now_DEST = os_path_join(DEST,dd)
        success_dd = xbmc_extract(now_SRC,now_DEST)
        if not success_dd:
            log(f"Error extracting inside dir: '{now_SRC}' to '{now_DEST}'")
        else:
            log(f"Extracting (back into the ff loop: '{now_SRC}' to '{now_DEST}'")


def recursive_glob(treeroot, pattern):
    results = [os_path_join(base, filename) for base, dirs, files in os.walk(treeroot)
        for extension in pattern
        for filename in fnmatch.filter(files, f'*.{extension.lower()}')]
    return results

def get_params():
    paramstring = sys.argv[2]
    params = parse_qs(urlparse(paramstring).query)
    return params


def bubbleSort(subtitles_list):
    subtitles_list.sort(key=lambda s: s['sync'], reverse=True)
    return subtitles_list

def cleanDirectory(directory):
    try:
        if xbmcvfs.exists(directory + "/"):
            shutil.rmtree(directory)
    except:
        pass
    finally:
        if not xbmcvfs.exists(directory):
            xbmcvfs.mkdirs(directory)

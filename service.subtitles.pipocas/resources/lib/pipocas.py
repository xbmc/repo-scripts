# -*- coding: UTF-8 -*-
# Copyright, 2020, Leinad4Mind.
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
try:
    import simplejson as json
except:
    import json


_addon      = xbmcaddon.Addon()
_scriptname = _addon.getAddonInfo('name')
_language   = _addon.getLocalizedString
_dialog     = xbmcgui.Dialog()

debug   = _addon.getSetting('DEBUG')
is_android = (xbmc.getCondVisibility('system.platform.linux') and xbmc.getCondVisibility('system.platform.android'))

SUB_EXTS          = ['srt', 'sub', 'txt', 'ass', 'ssa', 'smi', 'vtt', 'xml']
HTTP_USER_AGENT   = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'


def _log(module, msg):
    s = u"### [%s] - %s" % (module, msg)
    xbmc.log(s.encode('utf-8'), level=xbmc.LOGDEBUG)


def log(msg=None):
    if debug == 'true': _log(_scriptname, msg)


def is_libarchive_enabled():
    q = '{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": {"addonid": "vfs.libarchive", "properties": ["enabled"]}, "id": 0 }'
    r = json.loads(xbmc.executeJSONRPC(q))
    log(xbmc.executeJSONRPC(q))
    if r.has_key("result") and r["result"].has_key("addon"):
        return r['result']["addon"]["enabled"]
    return True

def enable_libarchive():
    if not is_libarchive_enabled():
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "vfs.libarchive", "enabled": true} }')
        time.sleep(1)
        if not is_libarchive_enabled():
            ok = _dialog.ok(_language(32024).encode("utf-8"), _language(32025).encode("utf-8"), " ", _language(32026).encode("utf-8"))

def disable_libarchive():
    if is_libarchive_enabled():
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled","params":{"addonid": "vfs.libarchive", "enabled": false} }')
        time.sleep(1)


def xbmc_walk(DIR):
    LIST = []
    dirs, files = xbmcvfs.listdir(DIR)
    for file in files:
        ext = os.path.splitext(file)[1][1:].lower()
        if ext in SUB_EXTS:
            LIST.append(os.path.join(DIR,  file))
    for dir in dirs:
        LIST.extend(list(xbmc_walk(os.path.join(DIR, dir))))
    return LIST


def extract_it_all(archive_file, directory_to, archive_type, extension):
    if is_libarchive_enabled():
        if (is_android and extension == '.rar'):
            disable_libarchive()

    if not is_libarchive_enabled():
        if not (is_android and extension == '.rar'):
            enable_libarchive()

    overall_success = True
    files_out = list()
    if archive_type != '':
        archive_path = (archive_type + '%s') % urllib.quote_plus(xbmc.translatePath(archive_file))
        archive_path_temp = ('archive://%s') % urllib.quote_plus(xbmc.translatePath(archive_file))
    else:
      archive_path = archive_file

    log('-----------------------------------------------------------')
    log('---- Extracting archive URL: %s' % archive_path)
    log('---- To directory: %s' % directory_to)

    log('---- Calling xbmcvfs.listdir...')
    try:
        (dirs_in_archive, files_in_archive) = xbmcvfs.listdir(archive_path)
    except:
        (dirs_in_archive, files_in_archive) = xbmcvfs.listdir(archive_path_temp)
    log('---- xbmcvfs.listdir CALLED...')

    for ff in files_in_archive:
        log('---- File found in archive: %s' % ff)
        url_from = os.path.join(archive_path, ff).replace('\\','/')  #Windows unexpectedly requires a forward slash in the path
        log('---- URL from: %s' % url_from)
        file_to = os.path.join(xbmc.translatePath(directory_to),ff)
        log('---- File to: %s' % file_to)
        copy_success = xbmcvfs.copy(url_from, file_to) #Attempt to move the file first
        log('---- Calling xbmcvfs.copy...')

        if not copy_success:
            log('---- Copy ERROR!!!!!')
            overall_success = False
        else:
            log( (ff[-3:] != 'rar' and ff[-3:] != 'zip') )
            if (ff[-3:] != 'rar' and ff[-3:] != 'zip'):
                log('---- Copy OK')
                files_out.append(file_to)

            if ff[-3:] == 'rar':
                sub_archive_path = xbmc.translatePath(file_to)#.replace(':','%3A').replace('\\','%5C')
                log('---- Extracting sub-rar URL: %s' % sub_archive_path)
                sub_directory = os.path.join(directory_to, ff)[:-4]
                log('---- To sub-rar: %s' % sub_directory)

                files_out2, copy_success2 = extract_it_all(sub_archive_path, sub_directory, 'rar://', '.rar')

                if copy_success2:
                    log('---- Copy OK 2')
                    files_out = files_out + files_out2
                    log('---- files_out2: %s' % files_out2)
                else:
                    overall_success = False
                    log('---- Sub-rar ERROR!!!!!')

            elif ff[-3:] == 'zip':
                sub_archive_path = 'archive://'+xbmc.translatePath(file_to)
                log('---- Extracting sub-zip URL: %s' % sub_archive_path)
                sub_directory = os.path.join(directory_to, ff)[:-4]
                log('---- To sub-zip: %s' % sub_directory)

                files_out2, copy_success2 = extract_it_all(sub_archive_path, sub_directory, 'archive://', '.zip')

                if copy_success2:
                    log('---- Copy OK 2')
                    files_out = files_out + files_out2
                    log(files_out)
                else:
                    overall_success = False
                    log('---- Sub-zip ERROR!!!!!')

    for dd in dirs_in_archive:
        log('---- Directory found in archive: %s' % dd)

        dir_to_create = os.path.join(directory_to, dd)
        log('---- Directory to create: %s' % dir_to_create)

        log('---- Calling xbmcvfs.mkdir...')
        mkdir_success = xbmcvfs.mkdir(dir_to_create)

        if mkdir_success:

            log('---- Mkdir OK')

            dir_inside_archive_url = archive_path + '/' + dd + '/'
            log('---- Directory inside archive URL: %s' % dir_inside_archive_url)

            log('---- Calling extractArchiveToFolder...')
            files_out2, copy_success2 = extract_it_all(dir_inside_archive_url, dir_to_create, '', '')

            if copy_success2:
                files_out = files_out + files_out2
            else:
                overall_success = False

        else:
            overall_success = False
            log('---- Mkdir ERROR!!!!!')

        if is_libarchive_enabled():
            enable_libarchive()
        else:
            disable_libarchive()
    return files_out, overall_success


def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(str, 'utf-8')).encode('ascii', 'ignore')


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

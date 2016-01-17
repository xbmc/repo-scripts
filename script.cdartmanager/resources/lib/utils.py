# -*- coding: utf-8 -*-
import errno
import htmlentitydefs
import os
import re
import sys
import traceback
import urllib
import datetime

import xbmc
import xbmcgui

try:
    from sqlite3 import dbapi2 as sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

__language__ = sys.modules["__main__"].__language__
__scriptname__ = sys.modules["__main__"].__scriptname__
__scriptID__ = sys.modules["__main__"].__scriptID__
__author__ = sys.modules["__main__"].__author__
__credits__ = sys.modules["__main__"].__credits__
__credits2__ = sys.modules["__main__"].__credits2__
__version__ = sys.modules["__main__"].__version__
__addon__ = sys.modules["__main__"].__addon__
addon_db = sys.modules["__main__"].addon_db
addon_work_folder = sys.modules["__main__"].addon_work_folder
tempxml_folder = sys.modules["__main__"].tempxml_folder
__useragent__ = sys.modules["__main__"].__useragent__
BASE_RESOURCE_PATH = sys.modules["__main__"].BASE_RESOURCE_PATH
illegal_characters = sys.modules["__main__"].illegal_characters
replace_character = sys.modules["__main__"].replace_character
enable_replace_illegal = sys.modules["__main__"].enable_replace_illegal
notify_in_background = sys.modules["__main__"].notify_in_background
change_period_atend = sys.modules["__main__"].change_period_atend
image = sys.modules["__main__"].image

# sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from file_item import Thumbnails
from xbmcvfs import delete as delete_file
from xbmcvfs import exists as exists
from xbmcvfs import mkdir

dialog = xbmcgui.DialogProgress()


def change_characters(text):
    original = list(text)
    final = []
    if enable_replace_illegal:
        for i in original:
            if i in illegal_characters:
                final.append(replace_character)
            else:
                final.append(i)
        temp = "".join(final)
        if temp.endswith(".") and change_period_atend:
            text = temp[:len(temp) - 1] + replace_character
        else:
            text = temp
    return text


def smart_unicode(s):
    """credit : sfaxman"""
    if not s:
        return ''
    try:
        if not isinstance(s, basestring):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                s = unicode(str(s), 'UTF-8')
        elif not isinstance(s, unicode):
            s = unicode(s, 'UTF-8')
    except:
        if not isinstance(s, basestring):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                s = unicode(str(s), 'ISO-8859-1')
        elif not isinstance(s, unicode):
            s = unicode(s, 'ISO-8859-1')
    return s


def smart_utf8(s):
    return smart_unicode(s).encode('utf-8')


def get_unicode(to_decode):
    final = []
    try:
        temp_string = to_decode.encode('utf8')
        return to_decode
    except:
        while True:
            try:
                final.append(to_decode.decode('utf8'))
                break
            except UnicodeDecodeError, exc:
                # everything up to crazy character should be good
                final.append(to_decode[:exc.start].decode('utf8'))
                # crazy character is probably latin1
                final.append(to_decode[exc.start].decode('latin1'))
                # remove already encoded stuff
                to_decode = to_decode[exc.start + 1:]
        return "".join(final)


def settings_to_log(settings_path, script_heading="[utils.py]"):
    try:
        log("Settings\n", xbmc.LOGDEBUG)
        # set base watched file path
        base_path = os.path.join(settings_path, "settings.xml")
        # open path
        settings_file = open(base_path, "r")
        settings_file_read = settings_file.read()
        settings_list = settings_file_read.replace("<settings>\n", "").replace("</settings>\n", "").split("/>\n")
        # close socket
        settings_file.close()
        for setting in settings_list:
            match = re.search('    <setting id="(.*?)" value="(.*?)"', setting)
            if not match:
                match = re.search("""    <setting id="(.*?)" value='(.*?)'""", setting)
            if match:
                log("%30s: %s" % (match.group(1), str(unescape(match.group(2).decode('utf-8', 'ignore')))),
                    xbmc.LOGDEBUG)
    except:
        traceback.print_exc()


def _makedirs(_path):
    log("Building Directory", xbmc.LOGDEBUG)
    success = False
    canceled = False
    if (exists(_path)): return True
    # temp path
    tmppath = _path
    # loop thru and create each folder
    while (not exists(tmppath)):
        try:
            if (dialog.iscanceled()):
                canceled = True
                break
        except:
            pass
        success = mkdir(tmppath)
        if not success:
            tmppath = os.path.dirname(tmppath)
    # call function until path exists
    if not canceled:
        _makedirs(_path)
    else:
        return canceled


def clear_image_cache(url):
    thumb = Thumbnails().get_cached_picture_thumb(url)
    png = os.path.splitext(thumb)[0] + ".png"
    dds = os.path.splitext(thumb)[0] + ".dds"
    jpg = os.path.splitext(thumb)[0] + ".jpg"
    if exists(thumb):
        delete_file(thumb)
    if exists(png):
        delete_file(png)
    if exists(jpg):
        delete_file(jpg)
    if exists(dds):
        delete_file(dds)


def empty_tempxml_folder():
    # Helix: paths MUST end with trailing slash
    if exists(os.path.join(tempxml_folder, '')):
        for file_name in os.listdir(os.path.join(tempxml_folder, '')):
            delete_file(os.path.join(tempxml_folder, file_name))
    else:
        pass


def get_html_source(url, path, save_file=True, overwrite=False):
    """ fetch the html source """
    log("Retrieving HTML Source", xbmc.LOGDEBUG)
    log("Fetching URL: %s" % url, xbmc.LOGDEBUG)
    error = False
    htmlsource = "null"
    file_name = ""
    if save_file:
        path += ".json"
        if not exists(os.path.join(tempxml_folder, '')):
            os.mkdir(os.path.join(tempxml_folder, ''))
        file_name = os.path.join(tempxml_folder, path)

    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__

    urllib._urlopener = AppURLopener()
    for i in range(0, 4):
        try:
            if save_file:
                if exists(file_name):
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_name))
                    file_age = datetime.datetime.today() - file_mtime
                    if file_age.days > 14:  # yes i know... but this is temporary and will be configurable in a later release
                        log("Cached file is %s days old, refreshing" % file_age.days, xbmc.LOGNOTICE)
                        delete_file(file_name)

                if exists(file_name) and not overwrite:
                    log("Retrieving local source", xbmc.LOGDEBUG)
                    sock = open(file_name, "r")
                else:
                    log("Retrieving online source", xbmc.LOGDEBUG)
                    urllib.urlcleanup()
                    sock = urllib.urlopen(url)
            else:
                urllib.urlcleanup()
                sock = urllib.urlopen(url)
            htmlsource = sock.read()
            if save_file and htmlsource not in ("null", ""):
                if not exists(file_name) or overwrite:
                    file(file_name, "w").write(htmlsource)
            sock.close()
            break
        except IOError, e:
            log("error: %s" % e, xbmc.LOGERROR)
            log("e.errno: %s" % e.errno, xbmc.LOGERROR)
            if not e.errno == "socket error":
                log("errno.errorcode: %s" % errno.errorcode[e.errno], xbmc.LOGERROR)
        except:
            traceback.print_exc()
            log("!!Unable to open page %s" % url, xbmc.LOGDEBUG)
            error = True
    if error:
        return "null"
    else:
        log("HTML Source:\n%s" % htmlsource, xbmc.LOGDEBUG)
        if htmlsource == "":
            htmlsource = "null"
        return htmlsource


def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub("&#?\w+;", fixup, text)


# centralized Dialog function from Artwork Downloader
# Define dialogs
def dialog_msg(action,
               percent=0,
               heading='',
               line1='',
               line2='',
               line3='',
               background=False,
               nolabel=__language__(32179),
               yeslabel=__language__(32178)):
    # Fix possible unicode errors 
    heading = heading.encode('utf-8', 'ignore')
    line1 = line1.encode('utf-8', 'ignore')
    line2 = line2.encode('utf-8', 'ignore')
    line3 = line3.encode('utf-8', 'ignore')
    # Dialog logic
    if not heading == '':
        heading = __scriptname__ + " - " + heading
    else:
        heading = __scriptname__
    if not line1:
        line1 = ""
    if not line2:
        line2 = ""
    if not line3:
        line3 = ""
    if not background:
        if action == 'create':
            dialog.create(heading, line1, line2, line3)
        if action == 'update':
            dialog.update(percent, line1, line2, line3)
        if action == 'close':
            dialog.close()
        if action == 'iscanceled':
            if dialog.iscanceled():
                return True
            else:
                return False
        if action == 'okdialog':
            xbmcgui.Dialog().ok(heading, line1, line2, line3)
        if action == 'yesno':
            return xbmcgui.Dialog().yesno(heading, line1, line2, line3, nolabel, yeslabel)
    if background:
        if (action == 'create' or action == 'okdialog'):
            if line2 == '':
                msg = line1
            else:
                msg = line1 + ': ' + line2
            if notify_in_background:
                xbmc.executebuiltin("XBMC.Notification(%s, %s, 7500, %s)" % (heading, msg, image))


def log(text, severity=xbmc.LOGDEBUG):
    if type(text).__name__ == 'unicode':
        text = text.encode('utf-8')
    message = ('[%s] - %s' % (__scriptname__, text.__str__()))
    xbmc.log(msg=message, level=severity)

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import codecs
import copy
import fnmatch
import operator
import os
import platform
import re
import sys
import threading

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def logprint(msg='', level=0):
    if msg != '' and level > -1:
        print msg


try:
    import xbmc
    import xbmcaddon
except ImportError:
    NOXBMC = True
else:
    if xbmc.getFreeMem() == long(0):
        NOXBMC = True
    else:
        NOXBMC = False
if NOXBMC:
    log = logprint
else:
    log = xbmc.log


class KodiPo(object):
    """
    Main class for retrieving localized strings.
    Implemented as singleton
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, addonid=None, pofilepath=None):
        """

        :param addonid: Optionally provide addonid. Looks in current path if not provided.
        :type addonid: str
        :param pofilepath: Optionally provide path to native po file. Looks for Englist/strings.po if not provided.
        :type pofilepath: str
        :return: instance of class Kodipo
        :rtype: KodiPo()
        """
        if KodiPo._instance is None:
            with KodiPo._lock:
                if KodiPo._instance is None:
                    KodiPo._instance = super(KodiPo, cls).__new__(cls)
                    KodiPo.cls_init(addonid, pofilepath)
        return KodiPo._instance

    @classmethod
    def cls_init(cls, addonid, pofilepath):
        """
        Initializes class by locating master po file and reading it into PoDict object
        :param addonid:
        :type addonid: str
        :param pofilepath:
        :type pofilepath: str
        :return:
        :rtype: None
        """
        if pofilepath is None:
            cls.pofn, cls.addonid = KodiPo.getpofn(addonid)
        else:
            cls.addonid = KodiPo.findaddonid(pofilepath)
            cls.pofn = pofilepath
        cls.podict = PoDict()
        cls.podict.read_from_file(cls.pofn)
        cls.updateAlways = False

    @staticmethod
    def getpofn(addonid=None):
        """
        Retrieves po filename
        :param addonid:
        :type addonid:
        :return:
        :rtype:
        """
        if addonid is None:
            currentpath = os.path.abspath(__file__)
            addonid = KodiPo.findaddonid(currentpath)
        rootpath = addonpath(addonid)
        return os.path.join(rootpath, 'resources', 'language', 'English', 'strings.po'), addonid

    @staticmethod
    def findaddonid(testpath):
        """
        Attempts to find addon id by searching path
        :param testpath:
        :type testpath:
        :return:
        :rtype:
        """
        addonid = ''
        while True:
            head, tail = os.path.split(testpath)
            if os.path.split(head)[1] == 'addons':
                addonid = tail
                break
            elif tail == '':
                log('Could not locate addon root path')
                raise IOError('Root addon path not found')
            testpath = head
        return addonid

    def __init__(self):  # , addonid=None, pofilepath=None):
        KodiPo._instance = self

    def _(self, strToId, update=False):
        self.getLocalizedString(strToId, update)

    def getLocalizedString(self, strToId, update=False):
        """
        Retrieves localized string. First looks up Kodi string number in master po file and then gets localized version.
        Returns same string if no localized version found.
        :param strToId: String in master po file language
        :type strToId: str or unicode
        :param update: If True will update po file if string not found.
        :type update: bool
        :return: Localized string
        :rtype: unicode
        """
        idFound, strid = self.podict.has_msgid(strToId)
        if idFound:
            if self.podict.savethread.is_alive():
                self.podict.savethread.join()
            if NOXBMC:
                ret = strToId
            else:
                ret = xbmcaddon.Addon(self.addonid).getLocalizedString(int(strid))
            if ret == u'':  # Occurs with stub or undefined number
                if not NOXBMC:
                    log(u'Localized string not found for: [%s]' % str(strToId))
                ret = strToId
            return ret
        else:
            if update is True or self.updateAlways is True:

                log(msg=u'Localized string added to po for: [%s]' % strToId)
                self.updatePo(strid, strToId)
            else:
                log(msg=u'Localized string id not found for: [%s]' % strToId)
            return strToId

    def getLocalizedStringId(self, strToId, update=False):
        """

        :param strToId:
        :type strToId:
        :param update:
        :type update:
        :return:
        :rtype: int
        """
        idFound, strid = self.podict.has_msgid(strToId)
        if idFound:
            return strid
        else:
            if update is True or self.updateAlways is True:
                self.updatePo(strid, strToId)
                log(msg=u'Localized string added to po for: [%s]' % strToId)
                return strid
            else:
                log(msg=u'Localized string not found for: [%s]' % strToId)
                return 32165

    def updatePo(self, strid, txt):
        """

        :param strid:
        :type strid:
        :param txt:
        :type txt:
        :return:
        :rtype:
        """
        self.podict.addentry(strid, txt)
        self.podict.write_to_file(self.pofn)


class PoDict(object):
    """

    """
    _instance = None
    _lock = threading.Lock()
    _rlock = threading.RLock()

    def __new__(cls):
        """

        :return:
        :rtype:
        """
        if PoDict._instance is None:
            with PoDict._lock:
                if PoDict._instance is None:
                    PoDict._instance = super(PoDict, cls).__new__(cls)
        return PoDict._instance

    def __init__(self):
        """

        """
        PoDict._instance = self
        self.dict_msgctxt = dict()
        self.dict_msgid = dict()
        self.chkdict = dict()
        self.remsgid = re.compile(ur'"([^"\\]*(?:\\.[^"\\]*)*)"')
        self.savethread = threading.Thread()

    def get_new_key(self):
        """

        :return:
        :rtype:
        """
        if len(self.dict_msgctxt) > 0:
            with PoDict._rlock:
                mmax = max(self.dict_msgctxt.iteritems(), key=operator.itemgetter(0))[0]
        else:
            mmax = '32000'
        try:
            int_key = int(mmax)
        except ValueError:
            int_key = -1
        return int_key + 1

    def addentry(self, str_msgctxt, str_msgid):
        """

        :param str_msgctxt:
        :type str_msgctxt:
        :param str_msgid:
        :type str_msgid:
        :return:
        :rtype:
        """
        with PoDict._lock:
            self.dict_msgctxt[str_msgctxt] = str_msgid
            self.dict_msgid[str_msgid] = str_msgctxt

    def has_msgctxt(self, str_msgctxt):  # Returns the English string associated with the id provided
        """

        :param str_msgctxt:
        :type str_msgctxt:
        :return:
        :rtype:
        """
        with PoDict._lock:
            if str_msgctxt in self.dict_msgctxt.keys():
                return [True, self.dict_msgctxt[str_msgctxt]]
            else:
                return [False, None]

    def has_msgid(self, str_msgid):  # Returns the id in .po as a string i.e. "32000"
        """

        :param str_msgid:
        :type str_msgid:
        :return:
        :rtype:
        """
        with PoDict._lock:
            if str_msgid in self.dict_msgid.keys():
                return [True, self.dict_msgid[str_msgid]]
            else:
                return [False, str(self.get_new_key())]

    def read_from_file(self, url):
        """

        :param url:
        :type url:
        :return:
        :rtype:
        """
        if url is None:
            log(msg=u'No URL to Read PoDict From')
            return
        if os.path.exists(url):
            try:
                with codecs.open(url, 'r', 'UTF-8') as f:
                    poin = f.readlines()
                i = 0
                while i < len(poin):
                    line = poin[i]
                    if line[0:7] == u'msgctxt':
                        t = re.findall(ur'".+"', line)
                        if not t[0].startswith(u'"Addon'):
                            str_msgctxt = t[0][2:7]
                            i += 1
                            line2 = poin[i]
                            str_msgid = ''
                            while not line2.startswith(u'msgstr'):
                                str_msgid += self.remsgid.findall(line2)[0]
                                i += 1
                                line2 = poin[i]
                            try:
                                str_msgid = str_msgid.decode('unicode_escape')
                            except UnicodeEncodeError:
                                t = str_msgid.encode('utf-8')
                                t = t.decode('string_escape')
                                str_msgid = t.decode('utf-8')
                            self.dict_msgctxt[str_msgctxt] = str_msgid
                            self.dict_msgid[str_msgid] = str_msgctxt
                            self.chkdict[str_msgctxt] = False
                        else:
                            i += 1
                    i += 1
            except Exception as e:
                log(msg=u'Error reading po: %s' % e.message)
        else:
            log(msg=u'Could not locate po at %s' % url)

    def write_to_file(self, url):
        """

        :param url:
        :type url:
        :return:
        :rtype:
        """
        if self.savethread is not None:
            assert isinstance(self.savethread, threading.Thread)
            if self.savethread.is_alive():
                self.savethread.join()
        with PoDict._lock:
            tmp = copy.copy(self.dict_msgctxt)
            self.savethread = threading.Thread(target=PoDict._write_to_file, args=[tmp, url])
            self.savethread.start()

    @staticmethod
    def _write_to_file(dict_msgctxt, url):
        """

        :param dict_msgctxt:
        :type dict_msgctxt:
        :param url:
        :type url:
        :return:
        :rtype:
        """
        addoninfo = PoDict.get_addoninfo()
        with codecs.open(url, 'wb', 'UTF-8') as fo:
            PoDict.write_po_header(fo, addoninfo)
            str_max = max(dict_msgctxt.iteritems(), key=operator.itemgetter(0))[0]
            str_min = min(dict_msgctxt.iteritems(), key=operator.itemgetter(0))[0]

            fo.write(u'msgctxt "Addon Summary"\n')
            fo.write(u'msgid "%s"\n' % addoninfo['summary'].replace('\n',''))
            fo.write(u'msgstr ""\n\n')
            fo.write(u'msgctxt "Addon Description"\n')
            fo.write(u'msgid "%s"\n' % addoninfo['description'].replace('\n',''))
            fo.write(u'msgstr ""\n\n')
            fo.write(u'msgctxt "Addon Disclaimer"\n')
            fo.write(u'msgid "%s"\n' % addoninfo['disclaimer'].replace('\n',''))
            fo.write(u'msgstr ""\n\n')
            fo.write(u'#Add-on messages id=%s to %s\n\n' % (str_min, str_max))
            last = int(str_min) - 1
            for str_msgctxt in sorted(dict_msgctxt):
                if not str_msgctxt.startswith('Addon'):
                    if int(str_msgctxt) != last + 1:
                        fo.write(u'#empty strings from id %s to %s\n\n' % (str(last + 1), str(int(str_msgctxt) - 1)))
                    PoDict.write_to_po(fo, str_msgctxt, PoDict.format_string_forpo(dict_msgctxt[str_msgctxt]))
                    last = int(str_msgctxt)

    @staticmethod
    def get_addoninfo(addonid=None):
        """

        :param addonid:
        :type addonid:
        :return:
        :rtype:
        """
        ret = {}
        if addonid is None:
            fn = '../../../addon.xml'
        else:
            fn = os.path.join(addonpath(addonid), 'addon.xml')
        if os.path.isfile(fn):
            try:
                tree = ET.ElementTree(file=fn)
                root = tree.getroot()
                ret['id'] = unicode(root.attrib['id'], 'utf-8')
                ret['name'] = unicode(root.attrib['name'], 'utf-8', errors='ignore')
                ret['author'] = unicode(root.attrib['provider-name'], 'utf-8', errors='ignore')
                ret['version'] = unicode(root.attrib['version'], 'utf-8', errors='ignore')
                itrtr = tree.getiterator(tag='extension')
                for elem in itrtr:
                    if elem.attrib['point'] == u"xbmc.addon.metadata":
                        citrtr = elem.getiterator()
                        for child in citrtr:
                            if child.attrib == {'lang': 'en'}:
                                ret[child.tag] = unicode(child.text, 'utf-8', errors='ignore').strip()
            except IOError:
                log(msg=u'Error opening addon.xml file')
                return None
            except SyntaxError as e:
                log(u'Error parsing addon.xml: %s' % unicode(e))
                return None
            else:
                req_elements = ['id', 'name', 'author', 'version', 'summary', 'description', 'disclaimer']
                for elem in req_elements:
                    if not ret.has_key(elem):
                        ret[elem] = u''
                    return ret

    @staticmethod
    def format_string_forpo(mstr):
        """

        :param mstr:
        :type mstr:
        :return:
        :rtype:
        """
        out = ''
        for (i, x) in enumerate(mstr):
            if i == 1 and x == ur'"':
                out += u"\\" + x
            elif x == ur'"' and mstr[i - 1] != u"\\":
                out += u"\\" + x
            else:
                out += x
        return out

    @staticmethod
    def write_po_header(fo, addoninfo):
        """

        :param fo:
        :type fo:
        :param addoninfo:
        :type addoninfo:
        :return:
        :rtype:
        """
        fo.write(u'# Kodi Media Center language file\n')
        fo.write(u'# Addon Name: %s\n' % addoninfo['name'])
        fo.write(u'# Addon id: %s\n' % addoninfo['id'])
        fo.write(u'# Addon Provider: %s\n' % addoninfo['author'])
        fo.write(u'msgid ""\n')
        fo.write(u'msgstr ""\n')
        fo.write(u'"Project-Id-Version: XBMC Addons\\n"\n')
        fo.write(u'"Report-Msgid-Bugs-To: alanwww1@xbmc.org\\n"\n')
        fo.write(u'"POT-Creation-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n')
        fo.write(u'"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n')
        fo.write(u'"Last-Translator: Kodi Translation Team\\n"\n')
        fo.write(u'"Language-Team: English (http://www.transifex.com/projects/p/xbmc-addons/language/en/)\\n"\n')
        fo.write(u'"MIME-Version: 1.0\\n"\n')
        fo.write(u'"Content-Type: text/plain; charset=UTF-8\\n"\n')
        fo.write(u'"Content-Transfer-Encoding: 8bit\\n"\n')
        fo.write(u'"Language: en\\n"')
        fo.write(u'"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n\n')

    @staticmethod
    def write_to_po(fileobject, int_num, str_msg):
        """

        :param fileobject:
        :type fileobject:
        :param int_num:
        :type int_num:
        :param str_msg:
        :type str_msg:
        :return:
        :rtype:
        """
        w = ur'"#' + unicode(int_num) + ur'"'
        fileobject.write(u'msgctxt ' + w + u'\n')
        fileobject.write(PoDict.splitstring(str_msg))
        fileobject.write(u'msgstr ' + ur'""' + u'\n')
        fileobject.write(u'\n')

    @staticmethod
    def splitstring(s):
        """

        :param s:
        :type s:
        :return:
        :rtype:
        """
        ret = []
        if u'\n' in s:
            pass
        s = s.replace(u'\n', u'~@\n')
        split = s.split(u'\n')
        for i in xrange(0, len(split)):
            split[i] = split[i].replace(u'~@', u'\n').encode('unicode_escape') #TODO: Fix for unicode errors
            if i == 0:
                if (len(split) == 2 and split[i + 1] == u'') or split[i] == u'\\n' or len(split) == 1:
                    ret.append(u'msgid "%s"\n' % split[i])
                else:
                    ret.append(u'msgid ""\n')
                    ret.append(u'"%s"\n' % split[i])
            elif i == len(split) - 1:
                if split[i] != '':
                    ret.append(u'"%s"\n' % split[i])
            else:
                ret.append(u'"%s"\n' % split[i])
        ret = u''.join(ret)
        return ret

    def createreport(self):
        """

        :return:
        :rtype:
        """
        cnt = 0
        reportpo = []
        for x in self.chkdict:
            if not self.chkdict[x]:
                if cnt == 0:
                    reportpo = [u'No usage found for the following pairs:']
                msgid = self.dict_msgctxt[x]
                reportpo.append(u'    %s:%s' % (x, msgid))
                cnt += 1
        ret = u'\n    '.join(reportpo)
        return ret


class UpdatePo(object):
    """

    """

    def __init__(self, root_directory_to_scan, current_working_English_strings_po, exclude_directories=None,
                 exclude_files=None):
        """

        :param root_directory_to_scan:
        :type root_directory_to_scan: str
        :param current_working_English_strings_po:
        :type current_working_English_strings_po: str
        :param exclude_directories:
        :type exclude_directories: list
        :param exclude_files:
        :type exclude_files: list
        """
        if exclude_directories is None:
            exclude_directories = []
        if exclude_files is None:
            exclude_files = []
        self.root_directory_to_scan = root_directory_to_scan
        self.current_working_English_strings_po = current_working_English_strings_po
        self.podict = PoDict()
        self.podict.read_from_file(self.current_working_English_strings_po)
        self.exclude_directories = exclude_directories
        self.exclude_files = exclude_files
        self.find_localizer = re.compile(ur'^(\S+?)\s*=\s*kodipo.getLocalizedString\s*$', flags=re.MULTILINE)

    def getFileList(self):
        """
        Returns a list of .py files to scan for localized strings
        :return:
        :rtype: list
        """
        files_to_scan = []
        exclusions = []
        for direct in self.exclude_directories:
            for root, ___, filenames in os.walk(os.path.join(self.root_directory_to_scan, direct)):
                for filename in filenames:
                    exclusions.append(os.path.join(root, filename))
        for root, ___, filenames in os.walk(self.root_directory_to_scan):
            for filename in fnmatch.filter(filenames, '*.py'):
                if os.path.split(filename)[1] in self.exclude_files:
                    continue
                elif os.path.join(root, filename) in exclusions:
                    continue
                else:
                    files_to_scan.append(os.path.join(root, filename))
        return files_to_scan

    def scanPyFilesForStrings(self):
        """
        Scans all .py files in directory tree for localized strings
        :return: List of strings needing localization
        :rtype: list
        """
        files = self.getFileList()
        lstrings = []
        for myfile in files:
            with codecs.open(myfile, 'r', 'utf-8') as f:
                lines = u''.join(f.readlines())
            try:
                finds = self.find_localizer.findall(lines)
            except re.error:
                finds = []
            finally:
                if len(finds) != 1:
                    log(msg=u'Skipping file: %s, localizer not found' % myfile)
                else:
                    findstr = ur"%s\('(.+?)'\)" % finds[0]
                    find = re.compile(findstr)
                    try:
                        finds = find.findall(lines)
                    except re.error:
                        finds = []
                    lstrings += finds
        return lstrings

    def updateStringsPo(self):
        """
        Scans files for localized strings and updates po
        :return:
        :rtype: None
        """
        lstrings = self.scanPyFilesForStrings()
        for s in lstrings:
            found, strid = self.podict.has_msgid(s.decode('unicode_escape'))
            if found is False:
                self.podict.addentry(strid, s)
        self.podict.write_to_file(self.current_working_English_strings_po)


def getPlatform():
    """
    Returns three character string code representing platform running
    :return: win|ios|osx|and|nix
    :rtype: str
    """
    if sys.platform.startswith('win'):
        ret = 'win'
    elif platform.system().lower().startswith('darwin'):
        if platform.machine().startswith('iP'):
            ret = 'ios'
        else:
            ret = 'osx'
    elif 'XBMC_ANDROID_SYSTEM_LIBS' in os.environ.keys():
        ret = 'and'
    else:  # Big assumption here
        ret = 'nix'
    return ret


def addonpath(addon_id):
    """
    Returns Kodi addonpath based on addon id when Kodi not running
    :param addon_id:
    :type addon_id: str
    :return: path to addon code
    :rtype: str
    """
    path = os.path.join(*[homepath(), 'addons', addon_id])
    return path


def homepath():
    """
    Returns Kodi home path when not running Kodi
    :return: kodi home path
    :rtype: str
    """
    paths = {'win': r'%APPDATA%\Kodi', 'nix': r'$HOME/.kodi', 'osx': r'~/Library/Application Support/Kodi',
             'ios': r'/private/var/mobile/Library/Preferences/Kodi',
             'and': r' /sdcard/Android/data/org.xbmc.kodi/files/.kodi/'}
    ret = paths[getPlatform()]
    ret = os.path.expandvars(ret)
    ret = os.path.expanduser(ret)
    ret = os.path.normpath(ret)
    return ret


if __name__ == '__main__':
    kp = KodiPo()

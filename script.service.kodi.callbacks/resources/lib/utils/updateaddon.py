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
import contextlib
import datetime
import fnmatch
import json
import os
import re
import shutil
import time
import zipfile
from stat import S_ISREG, ST_MTIME, ST_MODE
from time import strftime

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.kodilogging import KodiLogger
from resources.lib.utils.copyToDir import copyToDir
from resources.lib.utils.kodipathtools import translatepath
from resources.lib.utils.poutil import KodiPo

kodipo = KodiPo()
_ = kodipo.getLocalizedString

kl = KodiLogger()
log = kl.log


class UpdateAddon(object):
    def __init__(self, addonid=None, silent=False, numbackups=5):

        self.addonid = addonid
        self.addondir = translatepath('special://addon(%s)' % self.addonid)
        self.addondatadir = translatepath('special://addondata(%s)' % self.addonid)
        self.tmpdir = translatepath('%s/temp' % self.addondatadir)
        self.backupdir = translatepath('%s/backup' % self.addondatadir)
        self.silent = silent
        self.numbackups = numbackups

    @staticmethod
    def currentversion(addonid):
        currentversion = xbmcaddon.Addon(addonid).getAddonInfo('version')
        if currentversion == u'':  # Running stub
            currentversion = '0.9.9'
        return currentversion

    @staticmethod
    def prompt(strprompt, silent=False, force=False):
        if not silent or force:
            ddialog = xbmcgui.Dialog()
            if ddialog.yesno('', strprompt):
                return True
            else:
                return False

    @staticmethod
    def notify(message, silent=False, force=False):
        log(msg=message)
        if not silent or force:
            ddialog = xbmcgui.Dialog()
            ddialog.ok('', message)

    def cleartemp(self, recreate=True):
        if os.path.exists(os.path.join(self.tmpdir, '.git')):
            shutil.rmtree(os.path.join(self.tmpdir, '.git'))
        if os.path.exists(self.tmpdir):
            try:
                shutil.rmtree(self.tmpdir, ignore_errors=True)
            except OSError:
                return False
            else:
                if recreate is True:
                    os.mkdir(self.tmpdir)
                    return True
        else:
            if recreate is True:
                os.mkdir(self.tmpdir)
                return True

    @staticmethod
    def unzip(source_filename, dest_dir):
        try:
            with contextlib.closing(zipfile.ZipFile(source_filename, "r")) as zf:
                zf.extractall(dest_dir)
        except zipfile.BadZipfile:
            log(msg='Zip File Error')
            return False
        return True

    @staticmethod
    def zipdir(dest, srcdir):
        dest = '%s.zip' % dest
        zipf = ZipArchive(dest, 'w', zipfile.ZIP_DEFLATED)
        zipf.addDir(srcdir, srcdir)
        zipf.close()

    def backup(self, src=None, destdir=None, numbackups=5):
        if src is None:
            src = self.addondir
        if destdir is None:
            destdir = self.backupdir
        ts = strftime("%Y-%m-%d-%H-%M-%S")
        destname = os.path.join(destdir, '%s-%s' % (ts, self.addonid))
        if not os.path.exists(destdir):
            os.mkdir(destdir)
        else:
            if os.path.exists(destname):
                os.remove(destname)
        self.cleartemp(recreate=True)
        archivedir = os.path.join(self.tmpdir,
                                  '%s-%s' % (os.path.split(src)[1], xbmcaddon.Addon().getSetting('installedbranch')))
        shutil.copytree(src, archivedir, ignore=shutil.ignore_patterns('*.pyc', '*.pyo', '.git', '.idea'))
        UpdateAddon.zipdir(destname, self.tmpdir)
        self.cleartemp(recreate=False)
        sorteddir = UpdateAddon.datesorteddir(destdir)
        num = len(sorteddir)
        if num > numbackups:
            for i in xrange(0, num - numbackups):
                try:
                    os.remove(sorted(sorteddir)[i][2])
                except OSError:
                    raise
        return True

    @staticmethod
    def datesorteddir(sortdir):  # oldest first
        # returns list of tuples: (index, date, path)

        # get all entries in the directory w/ stats
        entries = (os.path.join(sortdir, fn) for fn in os.listdir(sortdir))
        entries = ((os.stat(path), path) for path in entries)

        # leave only regular files, insert creation date
        entries = ((stat[ST_MTIME], path)
                   for stat, path in entries if S_ISREG(stat[ST_MODE]))
        entrylist = []
        i = 0
        for cdate, path in sorted(entries):
            entrylist.append((i, cdate, path))
            i += 1
        return entrylist

    @staticmethod
    def is_v1_gt_v2(version1, version2):
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]

        result = cmp(normalize(version1), normalize(version2))
        if result == 1:
            return True
        else:
            return False

    @staticmethod
    def checkfilematch(fn, lst):
        ret = False
        for item in lst:
            if fn == item:
                ret = True
            elif fnmatch.fnmatchcase(fn, item):
                ret = True
        return ret

    @staticmethod
    def getBranchFromFile(path):
        root = UpdateAddon.getAddonxmlPath(path)
        if root != '':
            ps = root.split('-')
            if len(ps) == 1:
                return ''
            else:
                return ps[len(ps) - 1]
        else:
            return ''

    def installFromZip(self, zipfn, dryrun=False, updateonly=None, deletezip=False, silent=False):
        if os.path.split(os.path.split(zipfn)[0])[1] == 'backup':
            log(msg='Installing from backup')
            isBackup = True
        else:
            isBackup = False
        unzipdir = os.path.join(self.addondatadir, 'tmpunzip')
        if UpdateAddon.unzip(zipfn, unzipdir) is False:
            UpdateAddon.notify(_('Downloaded file could not be extracted'))
            try:
                os.remove(zipfn)
            except OSError:
                pass
            try:
                shutil.rmtree(unzipdir)
            except OSError:
                pass
            return
        else:
            if deletezip:
                os.remove(zipfn)
        branch = UpdateAddon.getBranchFromFile(unzipdir)
        installedbranch = xbmcaddon.Addon().getSetting('installedbranch')
        if branch == '':
            branch = installedbranch
        if not isBackup:
            if self.backup(self.addondir, self.backupdir, self.numbackups) is False:
                UpdateAddon.notify(_('Backup failed, update aborted'), silent=silent)
                return
            else:
                log(msg='Backup succeeded.')
        archivedir = UpdateAddon.getAddonxmlPath(unzipdir)
        addonisGHA = UpdateAddon.isGitHubArchive(self.addondir)
        if os.path.isfile(os.path.join(archivedir, 'timestamp.json')) and not isBackup:
            fd = UpdateAddon.loadfiledates(os.path.join(archivedir, 'timestamp.json'))
            UpdateAddon.setfiledates(archivedir, fd)
            log(msg='File timestamps updated')
            if updateonly is None:
                updateonly = True
            ziptimestamped = True
        else:
            ziptimestamped = False
            if updateonly is None:
                updateonly = False
        if updateonly is True and addonisGHA:
            updateonly = False
        if updateonly is True and ziptimestamped is False and isBackup is False:
            updateonly = False
        if installedbranch != branch:
            updateonly = False
        if archivedir != '':
            try:
                fc = copyToDir(archivedir, self.addondir, updateonly=updateonly, dryrun=dryrun)
            except OSError as e:
                UpdateAddon.notify(_('Error encountered copying to addon directory: %s') % str(e), silent=silent)
                shutil.rmtree(unzipdir)
                self.cleartemp(recreate=False)
            else:
                if installedbranch != branch:
                    xbmcaddon.Addon().setSetting('installedbranch', branch)
                if len(fc) > 0:
                    self.cleartemp(recreate=False)
                    shutil.rmtree(unzipdir)
                    if silent is False:
                        if not isBackup:
                            msg = _('New version installed')
                            msg += _('\nPrevious installation backed up')
                        else:
                            msg = _('Backup restored')
                        UpdateAddon.notify(msg)
                        log(msg=_('The following files were updated: %s') % str(fc))
                        if not silent:
                            answer = UpdateAddon.prompt(_('Attempt to restart addon now?')) == True
                        else:
                            answer = True
                        if answer is True:
                            restartpath = translatepath('special://addon{%s)/restartaddon.py' % self.addonid)
                            if not os.path.isfile(restartpath):
                                self.createRestartPy(restartpath)
                            xbmc.executebuiltin('RunScript(%s, %s)' % (restartpath, self.addonid))
                else:
                    UpdateAddon.notify(_('All files are current'), silent=silent)
        else:
            self.cleartemp(recreate=False)
            shutil.rmtree(unzipdir)
            UpdateAddon.notify(_('Could not find addon.xml\nInstallation aborted'), silent=silent)

    @staticmethod
    def getAddonxmlPath(path):
        ret = ''
        for root, __, files in os.walk(path):
            if 'addon.xml' in files:
                ret = root
                break
        return ret

    @staticmethod
    def getTS(strtime):
        t_struct = time.strptime(strtime, '%Y-%m-%dT%H:%M:%SZ')
        ret = time.mktime(t_struct)
        return ret

    @staticmethod
    def setTime(path, strtime):
        ts = UpdateAddon.getTS(strtime)
        os.utime(path, (ts, ts))

    @staticmethod
    def loadfiledates(path):
        if os.path.isfile(path):
            with open(path, 'r') as f:
                try:
                    ret = json.load(f)
                except:
                    raise
                else:
                    return ret
        else:
            return {}

    @staticmethod
    def setfiledates(rootpath, filedict):
        for key in filedict.keys():
            fl = key.split(r'/')
            path = os.path.join(rootpath, *fl)
            if os.path.isfile(path):
                UpdateAddon.setTime(path, filedict[key])

    @staticmethod
    def createRestartPy(path):
        output = []
        output.append('import xbmc')
        output.append('import sys')
        output.append('addonid = sys.argv[1]')
        output.append(
            'xbmc.executeJSONRPC(\'{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":"toggle"},"id":1}\' % addonid)')
        output.append('xbmc.log(msg=\'***** Toggling addon enabled 1: %s\' % addonid)')
        output.append('xbmc.sleep(1000)')
        output.append(
            'xbmc.executeJSONRPC(\'{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled", "params":{"addonid":"%s","enabled":"toggle"},"id":1}\' % addonid)')
        output.append('xbmc.log(msg=\'***** Toggling addon enabled 2: %s\' % addonid)')
        output = '\n'.join(output)
        with open(path, 'w') as f:
            f.writelines(output)

    @staticmethod
    def getFileModTime(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def createTimeStampJson(src, dst=None, ignore=None):
        if ignore is None:
            ignore = []
        fd = {}
        if dst is None:
            dst = os.path.join(src, 'timestamp.json')
        for root, __, files in os.walk(src):
            for fn in files:
                ffn = os.path.join(root, fn)
                relpath = os.path.relpath(ffn, src).replace('\\', '/')
                if not UpdateAddon.checkfilematch(relpath, ignore):
                    fd[relpath] = UpdateAddon.getFileModTime(ffn)
        if os.path.dirname(dst) == src:
            fd[os.path.relpath(dst, src)] = strftime('%Y-%m-%dT%H:%M:%SZ')
        with open(dst, 'w') as f:
            json.dump(fd, f, ensure_ascii=False)

    @staticmethod
    def isGitHubArchive(path):
        filelist = []
        vals = []
        ignoreDirs = ['.git', '.idea']
        ignoreExts = ['.pyo', '.pyc']
        ignoredRoots = []
        for root, dirs, files in os.walk(path):
            dirName = os.path.basename(root)
            if ignoreDirs.count(dirName) > 0:
                ignoredRoots += [root]
                continue
            ignore = False
            for ignoredRoot in ignoredRoots:
                if root.startswith(ignoredRoot):
                    ignore = True
                    break
            if ignore:
                continue
            # add files
            for fn in files:
                if os.path.splitext(fn)[1] not in ignoreExts:
                    vals.append(os.path.getmtime(os.path.join(root, fn)))
                    filelist.append(os.path.join(root, fn))
        vals.sort()
        vals = vals[5:-5]
        n = len(vals)
        mean = sum(vals) / n
        stdev = ((sum((x - mean) ** 2 for x in vals)) / n) ** 0.5
        if stdev / 60.0 < 1.0:
            return True
        else:
            return False


class ZipArchive(zipfile.ZipFile):
    def __init__(self, *args, **kwargs):
        zipfile.ZipFile.__init__(self, *args, **kwargs)

    def addEmptyDir(self, path, baseToRemove="", inZipRoot=None):
        inZipPath = os.path.relpath(path, baseToRemove)
        if inZipPath == ".":  # path == baseToRemove (but still root might be added
            inZipPath = ""
        if inZipRoot is not None:
            inZipPath = os.path.join(inZipRoot, inZipPath)
        if inZipPath == "":  # nothing to add
            return
        zipInfo = zipfile.ZipInfo(os.path.join(inZipPath, ''))
        self.writestr(zipInfo, '')

    def addFile(self, filePath, baseToRemove="", inZipRoot=None):
        inZipPath = os.path.relpath(filePath, baseToRemove)
        if inZipRoot is not None:
            inZipPath = os.path.join(inZipRoot, inZipPath)
        self.write(filePath, inZipPath)

    def addDir(self, path, baseToRemove="", ignoreDirs=None, inZipRoot=None):
        if ignoreDirs is None:
            ignoreDirs = []
        ignoredRoots = []
        for root, dirs, files in os.walk(path):
            # ignore e.g. special folders
            dirName = os.path.basename(root)
            if ignoreDirs.count(dirName) > 0:
                ignoredRoots += [root]
                continue
            # ignore descendants of folders ignored above
            ignore = False
            for ignoredRoot in ignoredRoots:
                if root.startswith(ignoredRoot):
                    ignore = True
                    break
            if ignore:
                continue

            # add dir itself (needed for empty dirs)
            if len(files) <= 0:
                self.addEmptyDir(root, baseToRemove, inZipRoot)

            # add files
            for fn in files:
                self.addFile(os.path.join(root, fn), baseToRemove, inZipRoot)

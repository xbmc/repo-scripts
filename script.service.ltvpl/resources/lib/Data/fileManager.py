#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import os
import os.path
import shutil
from time import sleep

try:  # Python 3
    from enum import Enum
except ImportError:
    from enum34 import Enum

from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Network.utilities import getTimeFilteredDirList
from resources.lib.Utilities.Messaging import WRITEMODE, READMODE

__Version__ = "1.0.3"

class FileManagerMode(Enum):
    JSON=1
    PICKLE=2
    XML=3

BACKUPNUM = 0
MAXBACKUPS = 20

class fileManager(object):
    def __init__(self, dataSet, filepath, mode=FileManagerMode.PICKLE, sentinelName="sentinel.tmp"):
        self.dataSet=dataSet
        self.filePath=filepath
        self.mode = mode
        self.restoreOperationActive = False
        self.sentinelFile = os.path.join(os.path.dirname(filepath),sentinelName)
        self.dirtyflag = False

    @property
    def Dirty(self):
        return self.dirtyflag

    @Dirty.setter
    def Dirty(self, value):
        if value:
            self.dirtyflag = value

    def cleanupBackupFiles(self):
        dirname=os.path.dirname(self.filePath)
        filter = os.path.splitext(os.path.basename(self.filePath))[0] + ".bak[0-9]?"
        files = getTimeFilteredDirList(dirname, filter=filter)
        for f in files:
            DbgPrint("Deleting:" + f)
            os.remove(f)

    def addSentinel(self, dstfile):
        with open(self.sentinelFile, WRITEMODE) as fp:
            fp.write(dstfile)


    def removeSentinel(self):
        count = 5
        while count >= 0:
            try:
                os.remove(self.sentinelFile)
                break
            except Exception as e:
                DbgPrint("Waiting on sentinel file...")
                DbgPrint(e)
                sleep(1)
                count -= 1

    def restoreFromSentinel(self):
        with open(self.sentinelFile, 'r') as fp:
            dstfile = fp.read()

        os.remove(self.filePath)
        shutil.copy(dstfile, self.filePath)

    def sentinelIsPresent(self):
        return os.path.exists(self.sentinelFile)

    def renameSrcFile(self, srcfile):
        global BACKUPNUM
        try:
            if os.path.getsize(srcfile) > 5:
                dstfile = "{}.bak{:02d}".format(os.path.splitext(srcfile)[0], BACKUPNUM + 1)
                shutil.copy(srcfile, dstfile)
                BACKUPNUM = (BACKUPNUM + 1) % MAXBACKUPS
                self.addSentinel(dstfile)
        except Exception as e:
            DbgPrint(str(e))

    def backup(self):
        if not self.dirtyflag:
            return

        if not self.restoreOperationActive:
            fp = None
            try:
                self.renameSrcFile(self.filePath)
                fp = open(self.filePath, WRITEMODE)
                if self.mode == FileManagerMode.JSON:
                    self.dataSet.ExportJSON(fp)
                elif self.mode == FileManagerMode.PICKLE:
                    self.dataSet.ExportPKL(fp)
                elif self.mode == FileManagerMode.XML:
                    self.dataSet.ExportXML(fp)

            except Exception as e:
                DbgPrint(str(e))

            finally:
                if fp is not None:
                    fp.close()
                    self.dirtyflag = False
                    if self.sentinelIsPresent():
                        self.removeSentinel()
                    self.cleanupBackupFiles()

        self.dirtyflag = False

    def restore(self):
        if self.sentinelIsPresent():
            self.restoreFromSentinel()
            self.removeSentinel()

        if os.path.isfile(self.filePath):
            if os.path.getsize(self.filePath) == 0:
                DbgPrint("***Datafile is Empty***")
                return

            self.restoreOperationActive = True
            fp=open(self.filePath,READMODE)
            if self.mode==FileManagerMode.JSON:
                self.dataSet.ImportJSON(fp)
            elif self.mode == FileManagerMode.PICKLE:
                self.dataSet.ImportPKL(fp)
            elif self.mode == FileManagerMode.XML:
                self.dataSet.ImportXML(fp)

            fp.close()
            self.dirtyflag = False
            self.restoreOperationActive = False
            DbgPrint("***Restore Operation Complete...")
            # self.cleanupBackupFiles()





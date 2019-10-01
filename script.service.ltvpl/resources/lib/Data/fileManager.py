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
import xml.etree.ElementTree as ET
from enum import Enum
from resources.lib.Utilities.DebugPrint import DbgPrint
from resources.lib.Network.utilities import getTimeFilteredDirList
from resources.lib.Utilities.Messaging import WRITEMODE, READMODE, WRITEBINARYMODE, READBINARYMODE

__Version__ = "1.0.2"

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
        if value == True:
            self.dirtyflag = value

    def cleanupBackupFiles(self):
        dirname=os.path.dirname(self.filePath)
        filter = os.path.splitext(os.path.basename(self.filePath))[0] + ".bak[0-9]?"
        files = getTimeFilteredDirList(dirname, filter=filter)
        for f in files:
            DbgPrint("Deleting:" + f)
            os.remove(f)

    def addSentinel(self, dstfile):
        fp = open(self.sentinelFile, WRITEMODE)
        fp.write(dstfile)
        fp.close()

    def removeSentinel(self):
        count = 5
        while count >= 0:
            try:
                os.remove(self.sentinelFile)
                break
            except:
                DbgPrint("Waiting on sentinel file...")
                sleep(1)
                count -= 1

    def restoreFromSentinel(self):
        fp = open(self.sentinelFile, 'r')
        dstfile = fp.read()
        fp.close()
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
        if self.dirtyflag == False:
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





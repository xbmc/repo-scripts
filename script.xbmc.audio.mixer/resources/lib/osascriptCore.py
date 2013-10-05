#!/usr/bin/python
#/*
# *      Copyright (C) 2005-2013 Team XBMC
# *      http://xbmc.org
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, see
# *  <http://www.gnu.org/licenses/>.
# *
# */

import os, re, sys, time
from threading import Thread

class WorkerThread(Thread):
    def __init__ (self, execPath):
        Thread.__init__(self)
        self.execPath = execPath
        self.stdout_value = ""
        self.stderr_value = ""
        self.retCode = 0

    def readFile(self, the_file):
        f = file(the_file, 'r')
        content = f.read()
        f.close()
        return content

    def run(self):
        """
        # Not currently supported
        process = subprocess.Popen(self.execPath, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        self.stdout_value, self.stderr_value = process.communicate()
        self.retCode = process.returncode
        """

        """
        # Not currently supported
        theFile = tempfile.NamedTemporaryFile(delete=False)
        stdoutTempFileName = theFile.name
        theFile.close()
        theFile = tempfile.NamedTemporaryFile(delete=False)
        stderrTempFileName = theFile.name
        theFile.close()
        """

        # os.system always returns -1, hence the hack
        retCodeTempFileName = "/tmp/tmpRetcode"
        stdoutTempFileName = "/tmp/tmpStdout"
        stderrTempFileName = "/tmp/tmpStderr"

        os.system('bash -c "' + self.execPath + ' > ' + stdoutTempFileName + ' 2> ' + stderrTempFileName + '"; echo $? > ' + retCodeTempFileName)
        retCode = self.readFile(retCodeTempFileName)[:-1]

        self.retCode = int(retCode)
        self.stdout_value = self.readFile(stdoutTempFileName)[:-1]
        self.stderr_value = self.readFile(stderrTempFileName)[:-1]

        os.unlink(retCodeTempFileName)
        os.unlink(stdoutTempFileName)
        os.unlink(stderrTempFileName)

    def isRunning(self):
          return self.running

    def getResults(self):
          return self.retCode, self.stdout_value, self.stderr_value 

class alsaMixerCore:
    gDebugMode = 0

    def __init__( self, debugLevel):
        self.gDebugMode = debugLevel

    def hasVolume(self, aControl):
        return True
        
    def hasSwitch(self, aControl):
        return True       

    def getVolume(self, aControl):
        return str(self.volumeLevel[aControl])


    def setVolume(self, aControl, aVolume):
        if aVolume != "on":
          if aVolume == "off": aVolume = 0
          if (aControl == "input volume") and (aVolume == 0):
            cmdStr = "osascript -e 'set volume output muted true'"
          else:  
            cmdStr = "osascript -e 'set volume %s %s'" % (aControl, str(aVolume))
        else:
          cmdStr = "osascript -e 'set volume output muted false'"  
        stdErr, stdOut, retValue = self.__runSilent(cmdStr)
        print cmdStr

    def getPlaybackControls(self):
        channels = ""
        stdErr, stdOut, retValue = self.__runSilent("osascript -e 'get volume settings'")
        self.outputLines = stdOut.split(", ")

        self.volumeLevel ={}
        for aControl in self.outputLines:
            
            control, value = aControl.split(":")
            if control != "output muted" and value != "missing value":
              self.volumeLevel[control] = value
        channels = ""
        for aControl, aVolume in self.volumeLevel.items():
            channels = channels + aControl + "|"

        return channels[:(len(channels) - 1)].split("|")

    def __printDebugLine(self, aLine):
        if self.gDebugMode>0:
            print aLine

    def __runSilent(self, aCmdline):
        self.__printDebugLine("Running: " + aCmdline)
        
        execution = WorkerThread(aCmdline)
        execution.start()

        while execution.isAlive():
            time.sleep(0.001)

        retCode, stdout_value, stderr_value = execution.getResults()

        self.__printDebugLine(" -D- Return code= " + str(retCode))
        self.__printDebugLine(" -D- Results: StdOut=" + repr(stdout_value))
        self.__printDebugLine(" -D- Results: StdErr=" + repr(stderr_value))
        return stderr_value, stdout_value, retCode


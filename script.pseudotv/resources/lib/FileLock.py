import subprocess, os
import time, threading

from Globals import *


FILE_LOCK_TIMEOUT = 15.0


class FileLock:
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('FileLock: ' + msg, level)


    def lockFile(self, filename, block = False):
        self.log("lockFile " + filename)

        if block:
            timeslept = 0
            self.isFileLocked(filename, True)
        else:
            if self.isFileLocked(filename):
                self.log("lockFile return file is locked")
                return False

        filename += ".lock"

        try:
            fle = open(filename, "w")
        except:
            self.log("lockFile return unable to write to lock")
            return False

        fle.write(str(os.getpid()))
        fle.close()
        # Crappy way of doing this.  It's possible that a check is done for a lock and then the lock
        # is set by another computer.  I don't want computer 2 to write to the file until computer 1
        # finishes processing it, so an artificial delay of 250ms is added.
        time.sleep(0.25)
        return True


    def unlockFile(self, filename):
        self.log("unlockFile " + filename)
        filename += ".lock"

        try:
            os.remove(filename)
        except:
            pass


    def isFileLocked(self, filename, block = False):
        self.log("isFileLocked " + filename)
        orgname = filename
        filename += ".lock"
        sleeptime = 0.0

        while sleeptime < FILE_LOCK_TIMEOUT:
            if os.path.exists(filename) == False:
                self.log("isFileLocked return lock doesn't exist")
                return False

            try:
                fle = open(filename, "r")
            except:
                self.log("isFileLocked return unable to read lock")
                return True

            try:
                pid = int(fle.readline())
            except:
                pid = 0

            fle.close()

            if pid == os.getpid():
                self.log("isFileLocked return PID matches, unlocked")
                return False

            sleeptime += 0.2

            if block == False:
                sleeptime = FILE_LOCK_TIMEOUT
            else:
                time.sleep(0.2)

        # If blocking, then forcefully unlock
        if block == True:
            self.unlockFile(orgname)
            return False

        self.log("isFileLocked return locked")
        return True

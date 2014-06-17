# -*- coding: utf-8 -*-
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
# *  along with this program; see the file LICENSE.txt.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *

#Modules General

import os
import sys
import mmap
import time
import re
import threading
from _winreg import *
import subprocess
from xml.etree import ElementTree
from operator import itemgetter
import ctypes

user32 = ctypes.windll.user32
screenx = user32.GetSystemMetrics(0)
screeny = user32.GetSystemMetrics(1)
user32 = None

"""
debug = True
remote = False
if debug:
    if remote:
        sys.path.append(r'C:\\Users\\Ken User\\AppData\\Roaming\\XBMC\\addons\\script.ambibox\\resources\\lib\\pycharm-debug.py3k\\')
        import pydevd
        pydevd.settrace('192.168.1.103', port=51234, stdoutToServer=True, stderrToServer=True)
    else:
        sys.path.append('C:\Program Files (x86)\JetBrains\PyCharm 3.1.3\pycharm-debug-py3k.egg')
        import pydevd
        pydevd.settrace('localhost', port=51234, stdoutToServer=True, stderrToServer=True)
"""

# Modules XBMC
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

# Modules AmbiBox
from ambibox import AmbiBox

__addon__ = xbmcaddon.Addon()
__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = str(__addon__.getAddonInfo('version'))
__settings__ = xbmcaddon.Addon("script.ambibox")
__language__ = __settings__.getLocalizedString
__settingsdir__ = xbmc.translatePath(os.path.join(__cwd__, 'resources'))
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
sys.path.append(__resource__)
__usingMediaInfo__ = False
mediax = None

def chkMediaInfo():
    # Check if user has installed mediainfo.dll to resources/lib or has installed full Mediainfo package
    global __usingMediaInfo__
    global mediax
    if xbmcvfs.exists(xbmc.translatePath(os.path.join(__resource__ + 'mediainfo.dll'))):
        __usingMediaInfo__ = True
    else:
        try:
            aReg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            key = OpenKey(aReg, r'Software\Microsoft\Windows\CurrentVersion\App Paths\MediaInfo.exe')
            path = QueryValue(key, None)
            CloseKey(key)
            CloseKey(aReg)
            if path != '':
                __usingMediaInfo__ = True
        except WindowsError:
            pass
    if __usingMediaInfo__ is True:
        from media import *
        mediax = Media()

chkMediaInfo()
ambibox = AmbiBox(__settings__.getSetting("host"), int(__settings__.getSetting("port")))


def notification(text, *silence):
    """
    Display an XBMC notification box, optionally turn off sound associated with it
    @type text: str
    @type silence: bool
    """
    text = text.encode('utf-8')
    info(text)
    if __settings__.getSetting("notification") == 'true':
        icon = __settings__.getAddonInfo("icon")
        smallicon = icon.encode("utf-8")
        #xbmc.executebuiltin('Notification(AmbiBox,' + text + ',1000,' + smallicon + ')')
        dialog = xbmcgui.Dialog()
        if silence:
            dialog.notification('Ambibox', text, smallicon, 1000, False)
        else:
            dialog.notification('Ambibox', text, smallicon, 1000, True)


def debug(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u"### [%s] - %s" % (__scriptname__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)


def info(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u"### [%s] - %s" % (__scriptname__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGNOTICE)


class ProfileManager():
    def __init__(self):
        self.AmbiboxRunning = False
        self.currentProfile = ""
        self._ABP = None
        self.softoff = False

    @property
    def ABP(self):
        return self._ABP

    @ABP.setter
    def ABP(self, popobject):
        self._ABP = popobject

    @ABP.getter
    def ABP(self):
        return self._ABP

    @ABP.deleter
    def ABP(self):
        del self._ABP

    @staticmethod
    def chkAmibiboxInstalled():
        #returns number of profiles if installed, 0 if installed with no profiles, -1 not installed
        aReg = ConnectRegistry(None, HKEY_CURRENT_USER)
        try:
            key = OpenKey(aReg, r'Software\Server IR\Backlight\Profiles')
            profileCount = QueryValueEx(key, 'ProfilesCount')
            if int(profileCount[0]) == 0:
                ret = 0
            else:
                ret = int(profileCount[0])
            CloseKey(key)
        except WindowsError or EnvironmentError:
            ret = -1
        CloseKey(aReg)
        return ret


    def chkAmbiboxRunning(self):
        proclist = []
        cmd = 'WMIC PROCESS get Caption,Commandline,Processid'
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        for line in proc.stdout:
            proclist.append(str(line))
        proc.terminate()
        del proc
        proclist.sort()
        self.AmbiboxRunning = False
        for proc in proclist:
            if proc[0:7] == "AmbiBox":
                self.AmbiboxRunning = True
                break
            elif str(proc[0:1]).lower() == 'b':
                break
        return self.AmbiboxRunning

    def startAmbibox(self):
        aReg = ConnectRegistry(None, HKEY_CURRENT_USER)
        try:
            key = OpenKey(aReg, r'Software\Server IR')
            p = QueryValueEx(key, 'InstallPath')
            ambiboxpath = xbmc.translatePath(str(p[0]) + r'\Ambibox.exe')
            CloseKey(key)
            CloseKey(aReg)
        except WindowsError:
            CloseKey(aReg)
            return False
        try:
            popobj = subprocess.Popen([ambiboxpath])
            self.ABP = popobj
            pid = popobj.pid
        except WindowsError:
            return False
        else:
            if pid is not None:
                self.AmbiboxRunning = True
                return True
            else:
                return False

    @staticmethod
    def chkProfileSettings():
        __settings = xbmcaddon.Addon("script.ambibox")
        if ambibox.connect() == 0:
            pfls = ambibox.getProfiles()
            sets2chk = ['default_profile', 'audio_profile', 'video_profile']
            vidfmts = ['2D', '3DS', '3DT']
            ars = ['43', '32', '169', '185', '22', '24']
            for vidfmt in vidfmts:
                for ar in ars:
                    setn = vidfmt + '_' + ar
                    sets2chk.append(setn)
            for setn in sets2chk:
                pname = __settings.getSetting(setn)
                if pname != 'None':
                    if not(pname in pfls):
                        __settings.setSetting(setn, 'None')
                        info('Missing profile %s set to None' % setn)

    def start(self):
        __settings = xbmcaddon.Addon("script.ambibox")
        pcnt = self.chkAmibiboxInstalled()
        info('%s profiles found in registry' % pcnt)
        if (pcnt >= 0) and (__settings.getSetting('start_ambibox')) == 'true':
            if self.chkAmbiboxRunning() is False:
                success = self.startAmbibox()
                if not success:
                    notification(__language__('32008'))
                    info('Could not start AmbiBox executable')
        if pcnt == 0:
            notification(__language__('32006'))
            info('No profiles found in Ambibox')
        elif pcnt == -1:
            notification(__language__('32007'))
            info('Ambibox installation not found: terminating script')
            sys.exit()
        else:
            if self.AmbiboxRunning:
                self.updateprofilesettings()
                self.chkProfileSettings()
        self.setProfile(__settings.getSetting('default_enable'), __settings.getSetting('default_profile'), True)
        if __settings.getSetting('default_enable') == 'false':
            self.softoff = True

    @staticmethod
    def updateprofilesettings():
        # updates choices (values="..") in settings.xml with profiles present in Ambibox program
        pstrl = []
        if ambibox.connect() == 0:
            pfls = ambibox.getProfiles()
            numpfls = len(pfls)
            info('%s profile(s) retrieved from program' % numpfls)
            defpfl = 'None'
            pstrl.append('None')
            pstrl.append('|')
            for pfl in pfls:
                pstrl.append(str(pfl))
                pstrl.append('|')
                if str(pfl).lower() == 'default':
                    defpfl = str(pfl)
            del pstrl[-1]
            pstr = "".join(pstrl)
            doc = ElementTree.parse(__settingsdir__ + "\\settings.xml")
            repl = ".//setting[@type='labelenum']"
            fixg = doc.iterfind(repl)
            for fixe in fixg:
                fixe.set('values', pstr)
                fixe.set('default', defpfl)
            doc.write(__settingsdir__ + "\\settings.xml")

            xbmc.executebuiltin('UpdateLocalAddons')

    @staticmethod
    def getARProfiles():
        # Returns 3 tuples with profiles for 2D, 3DSBS and 3DTAB
        # [0] is name, [1] is the AR, [2] is the lower limit, [3] is the upper limit
        # limits are calculated as the midway point between adjacent profiles

        ARProfiles = []
        __settings = xbmcaddon.Addon("script.ambibox")
        if ambibox.connect() == 0:
            pfls = ambibox.getProfiles()
        else:
            pfls = []
        setlist2D = ['2D_43', '2D_32', '2D_169', '2D_185', '2D_22', '2D_24']
        setlist3DS = ['3DS_43', '3DS_32', '3DS_169', '3DS_185', '3DS_22', '3DS_24']
        setlist3DT = ['3DT_43', '3DT_32', '3DT_169', '3DT_185', '3DT_22', '3DT_24']
        setlists = [setlist2D, setlist3DS, setlist3DT]
        ARdict = {'43': 1.333, '32': 1.5, '69': 1.778, '85': 1.85, '22': 2.2, '24': 2.4}
        for setlist in setlists:
            tpfl = []
            for settingid in setlist:
                profl = str(__settings.getSetting(settingid))
                if profl != 'None':
                    spfl = settingid[len(settingid)-2:]
                    AR = ARdict[spfl]
                    if profl in pfls:
                        tpfl.append([profl, AR, AR, AR])
                    elif not pfls:
                        #Should never get to this statement
                        info("Profile existance not checked due to unavailability of Amibibox API")
                        tpfl.append([profl, AR, AR, AR])
                    else:
                        tpfl.append([__settings.getSetting('default'), AR, AR, AR])
                        info("Profile in settings not a valid Ambibox profile - using default")
            tpfl.sort(key=itemgetter(1))
            ARProfiles.append(tpfl)

        for tpfl in ARProfiles:
            i1 = len(tpfl)
            for i, pfl in enumerate(tpfl):
                if i == 0:
                    ll = 0.1
                else:
                    ll = float((pfl[1] + tpfl[i-1][1])/2)
                if i == i1-1:
                    ul = 99
                else:
                    ul = float((pfl[1] + tpfl[i+1][1])/2)
                pfl[2] = ll
                pfl[3] = ul
        return ARProfiles

    def setProfile(self, enable, profile, *force):
        self.currentProfile = profile
        if ambibox.connect() == 0:
            ambibox.lock()
            if enable == 'true' and profile != 'None':
                notification(__language__(32033) % profile)
                if (ambibox.getStatus() == "off" and self.softoff) or force:
                    ambibox.turnOn()
                ambibox.setProfile(profile)
                self.softoff = False
            else:
                notification(__language__(32032))
                if ambibox.getStatus() != "off":
                    self.softoff = True
                    ambibox.turnOff()
            ambibox.unlock()

    def SetAbxProfile(self, dar, vidfmt):
        """
        Sets the profile based on AR and video format
        @type dar: float
        @type vidfmt: str
        @rtype: bool
        """
        ret = False
        if ambibox.connect() == 0:
            pfls = ambibox.getProfiles()
            ARProfiles = self.getARProfiles()
            pname = self.GetProfileName(pfls, dar, vidfmt, ARProfiles)
            self.setProfile('true', pname)
            ret = True
        return ret

    @staticmethod
    def GetProfileName(pfls, DisplayAspectRatio, vidfmt, ARProfiles):
        """
        Retrieves the profile name based upon the AR and video format
        @type pfls: list of string
        @type DisplayAspectRatio: float
        @type vidfmt: str
        @type ARProfiles: list of string
        @rtype: string
        """
        __settings = xbmcaddon.Addon("script.ambibox")
        ret = ""
        if vidfmt == 'Normal':
            for pfl in ARProfiles[0]:
                if pfl[2] < DisplayAspectRatio <= pfl[3]:
                    ret = pfl[0]
                    break
        elif vidfmt == 'SBS':
            for pfl in ARProfiles[1]:
                if pfl[2] < DisplayAspectRatio <= pfl[3]:
                    ret = pfl[0]
                    break
        elif vidfmt == 'TAB':
            for pfl in ARProfiles[2]:
                if pfl[2] < DisplayAspectRatio <= pfl[3]:
                    ret = pfl[0]
                    break
        if ret != "":
            if ret in pfls:
                return ret
            else:
                info("Profile in xml not found by Ambibox - using default")
                ret = __settings.getSetting("default_profile")
                return ret
        else:
            info("No profiles have been set up for this video type - using default")
            return __settings.getSetting("default_profile")

    def close(self):
        try:
            popobj = self.ABP
            if popobj is not None:
                popobj.terminate()
                del popobj
            del self.ABP
        except Exception:
            pass


class CapturePlayer(xbmc.Player):

    def __init__(self, *args):
        xbmc.Player.__init__(self)
        self.inDataMap = None
        self.re3D = re.compile("[-. _]3d[-. _]", re.IGNORECASE)
        self.reTAB = re.compile("[-. _]h?tab[-. _]", re.IGNORECASE)
        self.reSBS = re.compile("[-. _]h?sbs[-. _]", re.IGNORECASE)
        self.onPBSfired = False

    def showmenu(self):
        menu = ambibox.getProfiles()
        menu.append(__language__(32021))
        menu.append(__language__(32022))
        off = len(menu)-2
        on = len(menu)-1
        mquit = False
        time.sleep(1)
        selected = xbmcgui.Dialog().select(__language__(32020), menu)
        while not mquit:
            if selected != -1:
                ambibox.lock()
                if (off == int(selected)):
                    ambibox.turnOff()
                elif (on == int(selected)):
                    ambibox.turnOn()
                else:
                    ambibox.turnOn()
                    pm.setProfile('true', menu[selected])
                ambibox.unlock()
            mquit = True

    def onPlayBackStarted(self):
        __settings = xbmcaddon.Addon("script.ambibox")
        ambibox.connect()
        self.onPBSfired = True

        if self.isPlayingAudio():
            pm.setProfile(__settings.getSetting("audio_enable"), __settings.getSetting("audio_profile"))

        if self.isPlayingVideo():
            xxx = self.getPlayingFile()
            if __usingMediaInfo__ is True:
                infos = mediax.getInfos(xxx)
            else:
                infos = [0, 0, 1, 0]
            if infos[3] == 0:
                rc = xbmc.RenderCapture()
                tDar = rc.getAspectRatio()
                if tDar == 0:
                    tDar = float(infos[0])/float(infos[1])
                if 0.95 < tDar < 1.05:
                    tDar = float(screenx)/float(screeny)
                infos[3] = tDar
            if __settings.getSetting('directXBMC_enable') == 'true':
                quality = __settings.getSetting('directXBMC_quality')
                if quality == '0':
                    infos[1] = 64
                elif quality == '1':
                    infos[1] = 256
                elif quality == '2':
                    infos[1] = 512
                else:
                    if infos[1] == 0:
                        infos[1] = screeny
                infos[0] = int(infos[1]*infos[3])

            m = self.re3D.search(xxx)
            vidfmt = ""
            if m and __settings.getSetting('3D_enable'):
                n = self.reTAB.search(xxx)
                if n:
                    vidfmt = "TAB"
                else:
                    n = self.reSBS.search(xxx)
                    if n:
                        vidfmt = "SBS"
                    else:
                        info("Error in 3D filename - using default settings")
                        main().pm.setProfile('true', __settings.getSetting("video_profile"))
            else:
                vidfmt = "Normal"

            videomode = __settings.getSetting("video_choice")
            try:
                videomode = int(videomode)
            except (ValueError, TypeError):
                videomode = 2

            if videomode == 0:    #Use Default Video Profile
                pm.setProfile('true', __settings.getSetting("video_profile"))
            elif videomode == 1:  #Autoswitch
                DAR = infos[3]
                if DAR != 0:
                    pm.SetAbxProfile(DAR, vidfmt)
                else:
                    info("Error retrieving DAR from video file")
            elif videomode == 2:   #Show menu
                self.showmenu()
            elif videomode == 3:   #Turn off
                ambibox.lock()
                ambibox.turnOff()
                ambibox.unlock()

            if __settings.getSetting("directXBMC_enable") == 'true':   #Added
                xd = XBMCDirect(infos, self)
                xd.run()
                xd.close()

    def onPlayBackEnded(self):
        if ambibox.connect() == 0:
            __settings = xbmcaddon.Addon("script.ambibox")
            pm.setProfile(__settings.getSetting("default_enable"), __settings.getSetting("default_profile"))
        self.onPBSfired = False

    def onPlayBackStopped(self):
        if ambibox.connect() == 0:
            __settings = xbmcaddon.Addon("script.ambibox")
            pm.setProfile(__settings.getSetting("default_enable"), __settings.getSetting("default_profile"))
        self.onPBSfired = False

    def close(self):
        if ambibox.connect() == 0:
            ambibox.lock()
            ambibox.turnOff()
            ambibox.unlock()
            ambibox.disconnect()


class XbmcMonitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.AbxAlreadyOff = False

    def onScreensaverDeactivated(self):
        self.setScreensaver(False)

    def onScreensaverActivated(self):
        self.setScreensaver(True)

    def setScreensaver(self, enabled):
        if ambibox.connect() == 0:
            __settings = xbmcaddon.Addon("script.ambibox")
            ambibox.lock()
            if __settings.getSetting("disable_on_screensaver") and enabled:
                notification(__language__(32032), False)
                if ambibox.getStatus() == "off":
                    self.AbxAlreadyOff = True
                else:
                    self.AbxAlreadyOff = False
                ambibox.turnOff()
            else:
                profile = pm.currentProfile
                notification(__language__(32033) % profile)
                if not self.AbxAlreadyOff:
                    ambibox.turnOn()
                pm.setProfile('true', profile)
            ambibox.unlock()

    def onSettingsChanged(self):
        __settings = xbmcaddon.Addon("script.ambibox")
        if __settings.getSetting('start_ambibox') == 'true' and pm.AmbiboxRunning is False:
            pm.start()
        elif pm.AmbiboxRunning is True:
            pm.chkProfileSettings()
        chkMediaInfo()


class XBMCDirect (threading.Thread):

    def __init__(self, infos, player):
        threading.Thread.__init__(self, name="XBMCDirect")
        self.infos = infos
        self.player = player
        self.running = False

    def start(self):
        self.running = True
        threading.Thread.start(self)

    def stop(self):
        self.running = False
        self.join(0.5)
        self.close()

    def close(self):
        pass

    def run(self):
        threading.Thread.run(self)
        capture = xbmc.RenderCapture()
        tw = capture.getHeight()
        th = capture.getWidth()
        tar = capture.getAspectRatio()
        width = self.infos[0]
        height = self.infos[1]
        ratio = self.infos[2]
        if (width != 0 and height != 0 and ratio != 0):
            inimap = []
            try:
                self.player.inDataMap = mmap.mmap(0, width * height * 4 + 11, 'AmbiBox_XBMC_SharedMemory', mmap.ACCESS_WRITE)
            except Exception, e:
                pass
            # get one frame to get length
            aax = None
            while not self.player.isPlayingVideo():
                xbmc.sleep(100)
                continue
            for idx in xrange(1, 10):
                xbmc.sleep(100)
                capture.capture(width, height, xbmc.CAPTURE_FLAG_CONTINUOUS)
                capture.waitForCaptureStateChangeEvent(1000)
                aax = capture.getCaptureState()
                if aax == xbmc.CAPTURE_STATE_FAILED:
                    del capture
                    capture = xbmc.RenderCapture()
                elif aax == xbmc.CAPTURE_STATE_DONE:
                    break

            if aax != xbmc.CAPTURE_STATE_FAILED:
                inimap.append(chr(0))
                inimap.append(chr(width & 0xff))
                inimap.append(chr((width >> 8) & 0xff))
                # height
                inimap.append(chr(height & 0xff))
                inimap.append(chr((height >> 8) & 0xff))
                # aspect ratio
                inimap.append(chr(int(ratio * 100)))
                # image format
                fmt = capture.getImageFormat()
                if fmt == 'RGBA':
                    inimap.append(chr(0))
                elif fmt == 'BGRA':
                    inimap.append(chr(1))
                else:
                    inimap.append(chr(2))
                image = capture.getImage()
                length = len(image)
                # datasize
                inimap.append(chr(length & 0xff))
                inimap.append(chr((length >> 8) & 0xff))
                inimap.append(chr((length >> 16) & 0xff))
                inimap.append(chr((length >> 24) & 0xff))
                inimapstr = "".join(inimap)
                notification(__language__(32034))
                info('XBMCDirect capture initiated')

                capture.capture(width, height, xbmc.CAPTURE_FLAG_CONTINUOUS)

                while self.player.isPlayingVideo():
                    capture.waitForCaptureStateChangeEvent(1000)
                    if capture.getCaptureState() == xbmc.CAPTURE_STATE_DONE:
                        image = capture.getImage()
                        newlen = len(image)
                        self.player.inDataMap.seek(0)
                        seeked = self.player.inDataMap.read_byte()
                        if ord(seeked) == 248:  #check that XBMC Direct is running
                            if newlen != length:
                                length = newlen
                                inimapnew = inimap[0:6]
                                inimapnew.append(chr(length & 0xff))
                                inimapnew.append(chr((length >> 8) & 0xff))
                                inimapnew.append(chr((length >> 16) & 0xff))
                                inimapnew.append(chr((length >> 24) & 0xff))
                                inimapstr = "".join(inimapnew)
                            self.player.inDataMap[1:10] = inimapstr[1:10]
                            self.player.inDataMap[11:(11 + length)] = str(image)
                            # write first byte to indicate we finished writing the data
                            self.player.inDataMap[0] = (chr(240))
                self.player.inDataMap.close()
                self.player.inDataMap = None
            else:
                info('Capture failed')
                notification(__language__(32035))
        else:
            info("Error retrieving video file dimensions")


def main():

    pm.start()
    monitor = XbmcMonitor()
    if ambibox.connect() == 0:
        notification(__language__(32030))
        info('Started - ver %s' % __version__)
        player = CapturePlayer()
        monitor = XbmcMonitor()
    else:
        notification(__language__(32031))
        player = None

    while not xbmc.abortRequested:
        if player is None:
            xbmc.sleep(1000)
            if ambibox.connect() == 0:
                notification(__language__(32030))
                info('Started - ver %s' % __version__)
                pm.updateprofilesettings()
                pm.chkProfileSettings()
                player = CapturePlayer()
        else:
            # This is to get around a bug where onPlayBackStarted is not fired for external players present
            # in releases up to Gotham 13.1
            if player.isPlayingVideo() and not player.onPBSfired:
                info('Firing missed onPlayBackStarted event')
                player.onPlayBackStarted()
            xbmc.sleep(100)

    pm.close()

    if player is not None:
        # set off
        notification(__language__(32032))
        player.close()
        del player
        del monitor

pm = ProfileManager()

main()

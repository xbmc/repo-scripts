# -*- coding: utf-8 -*-
import sys, os, stat, platform, subprocess
import socket
import re
import xbmc, xbmcaddon, xbmcgui
import time, datetime, random
import urllib2
from xml.dom import minidom
import smtplib
from email.message import Message

# global

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('id')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

def writeLog(message, level=xbmc.LOGDEBUG):
        xbmc.log('[%s]: %s' % (__addonname__, message.encode('utf-8')), level)

ADDONTVH = True
try:
    __addonTVH__ = xbmcaddon.Addon('pvr.hts')
except RuntimeError, e:
    writeLog('Addon \'pvr.hts\' not installed or inactive', level=xbmc.LOGERROR)
    ADDONTVH = False

SHUTDOWN_CMD = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'shutdown.sh'))
EXTGRABBER = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'epggrab_ext.sh'))

# set permissions for these files, this is required after installation or update

_sts = os.stat(SHUTDOWN_CMD)
_stg = os.stat(EXTGRABBER)
if not (_sts.st_mode & stat.S_IEXEC): os.chmod(SHUTDOWN_CMD, _sts.st_mode | stat.S_IEXEC)
if not (_stg.st_mode & stat.S_IEXEC): os.chmod(EXTGRABBER, _stg.st_mode | stat.S_IEXEC)

CYCLE = 15  # polling cycle

HOST = socket.gethostname()
OSD = xbmcgui.Dialog()

PLATFORM_OE = any(dist for dist in ('LIBREELEC', 'OPENELEC') if dist in ', '.join(platform.uname()).upper())
if PLATFORM_OE:
    if __addon__.getSetting('sudo').upper() == 'TRUE':
        __addon__.setSetting('sudo', 'false')
        writeLog('OS seems to be LibreELEC or OpenELEC, reset sudo in settings')

# binary Flags

isPWR = 0b10000
isNET = 0b01000
isPRG = 0b00100
isREC = 0b00010
isEPG = 0b00001
isUSR = 0b00000

### MAIN CLASS

class Manager(object):

    def __init__(self):

        self.__conn_established = None
        self.__xml = None
        self.__recTitles = []
        self.__wakeUp = None
        self.__wakeUpUT = None
        self.__wakeUpStrOffset = None
        self.__wakeUpMessage = ''
        self.__monitored_ports = ''
        self.__ScreensaverActive = None
        self.__windowID = None
        self.rndProcNum = random.randint(1, 1024)

        self.getSettings()
        writeLog('Settings loaded, starting service with id %s' % self.rndProcNum, level=xbmc.LOGNOTICE)
        self.establishConn()

    @classmethod
    def crypt(cls, pw, key, token):
        _pw = __addon__.getSetting(pw)
        if _pw == '' or _pw == '*':
            _key = __addon__.getSetting(key)
            _token = __addon__.getSetting(token)
            if len(_key) > 2: return "".join([chr(ord(_token[i]) ^ ord(_key[i])) for i in range(int(_key[-2:]))])
            return ''
        else:
            _key = ''
            for i in range((len(pw) / 16) + 1):
                _key += ('%016d' % int(random.random() * 10 ** 16))
            _key = _key[:-2] + ('%02d' % len(_pw))
            _tpw = _pw.ljust(len(_key), 'a')
            _token = "".join([chr(ord(_tpw[i]) ^ ord(_key[i])) for i in range(len(_key))])

            __addon__.setSetting(key, _key)
            __addon__.setSetting(token, _token)
            __addon__.setSetting(pw, '*')

            return _pw

    @classmethod
    def notifyOSD(self, header, message, icon=xbmcgui.NOTIFICATION_INFO):
        OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon)

    @classmethod
    def dialogOK(self, header, message):
        OSD.ok(header.encode('utf-8'), message.encode('utf-8'))

    ### read addon settings

    def getSettings(self):
        self.__prerun = int(re.match('\d+', __addon__.getSetting('margin_start')).group())
        self.__postrun = int(re.match('\d+', __addon__.getSetting('margin_stop')).group())
        self.__wakeup = __addon__.getSetting('wakeup_method')
        self.__shutdown = int(__addon__.getSetting('shutdown_method'))
        self.__sudo = True if __addon__.getSetting('sudo').upper() == 'TRUE' else False
        self.__counter = int(re.match('\d+', __addon__.getSetting('notification_counter')).group())
        self.__nextsched = True if __addon__.getSetting('next_schedule').upper() == 'TRUE' else False

        # TVHeadend server

        if ADDONTVH:
            self.__server = 'http://' + __addonTVH__.getSetting('host')
            self.__port = __addonTVH__.getSetting('http_port')
            self.__user = __addonTVH__.getSetting('user')
            self.__pass = __addonTVH__.getSetting('pass')
            self.__maxattempts = int(__addon__.getSetting('conn_attempts'))

        # check for network activity
        self.__network = True if __addon__.getSetting('network').upper() == 'TRUE' else False

        # transform possible ugly userinput (e.g. 'p1, p2,,   p3 p4  ') to a shapely list
        self.__monitored_ports = ' '.join(__addon__.getSetting('monitored_ports').replace(',',' ').split()).split()

        # check for processes
        self.__pp_enabled = True if __addon__.getSetting('postprocessor_enable').upper() == 'TRUE' else False

        # transform possible ugly userinput (e.g. 'p1, p2,,   p3 p4  ') to a shapely list
        self.__pp_list = ' '.join(__addon__.getSetting('processor_list').replace(',',' ').split()).split()

        # mail settings
        self.__notification = True if __addon__.getSetting('smtp_sendmail').upper() == 'TRUE' else False
        self.__smtpserver = __addon__.getSetting('smtp_server')
        self.__smtpuser = __addon__.getSetting('smtp_user')
        self.__smtppass = self.crypt('smtp_passwd', 'smtp_key', 'smtp_token')
        self.__smtpenc = __addon__.getSetting('smtp_encryption')
        self.__smtpfrom = __addon__.getSetting('smtp_from')
        self.__smtpto = __addon__.getSetting('smtp_to')
        self.__charset = __addon__.getSetting('charset')

        # EPG-Wakeup settings
        self.__epg_interval = int(__addon__.getSetting('epgtimer_interval'))
        self.__epg_time = int(__addon__.getSetting('epgtimer_time'))
        self.__epg_duration = int(re.match('\d+', __addon__.getSetting('epgtimer_duration')).group())
        self.__epg_grab_ext = True if __addon__.getSetting('epg_grab_ext').upper() == 'TRUE' else False
        self.__epg_socket = xbmc.translatePath(__addon__.getSetting('epg_socket_path'))
        self.__epg_store = True if __addon__.getSetting('store_epg').upper() == 'TRUE' else False
        self.__epg_path = xbmc.translatePath(os.path.join(__addon__.getSetting('epg_path'), 'epg.xml'))

    # Connect to TVHeadend and establish connection (log in))

    def establishConn(self):
        self.__conn_established = False
        while ADDONTVH and self.__maxattempts > 0:
            try:
                pwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                pwd_mgr.add_password(None, self.__server + ':' + self.__port + '/status.xml', self.__user, self.__pass)
                handle = urllib2.HTTPBasicAuthHandler(pwd_mgr)
                opener = urllib2.build_opener(handle)
                opener.open(self.__server + ':' + self.__port + '/status.xml')
                urllib2.install_opener(opener)
                self.__conn_established = True
                writeLog('Connection to %s established (Basic Authentication)' % (self.__server))
                break

            except urllib2.HTTPError, e:
                if e.code == 401:
                    try:
                        pwd_mgr = urllib2.HTTPDigestAuthHandler()
                        pwd_mgr.add_password('tvheadend', self.__server + ':' + self.__port + '/status.xml', self.__user, self.__pass)
                        opener = urllib2.build_opener(pwd_mgr)
                        urllib2.install_opener(opener)
                        opener.open(self.__server + ':' + self.__port + '/status.xml')
                        self.__conn_established = True
                        writeLog('Connection to %s established (Digest Authentication)' % (self.__server))
                        break
                    except Exception, e:
                        writeLog('%s Remaining connection attempt(s) to %s' % (self.__maxattempts, self.__server))
                        xbmc.sleep(5000)
                        self.__maxattempts -= 1
                        continue
                else:
                    raise

            except Exception, e:
                writeLog('%s Remaining connection attempt(s) to %s' % (self.__maxattempts, self.__server))
                xbmc.sleep(5000)
                self.__maxattempts -= 1
                continue

        if not self.__conn_established:
            if ADDONTVH:
                writeLog('Network or communication error, can\'t connect to TVH', level=xbmc.LOGERROR)
                self.notifyOSD(__LS__(30030), __LS__(30031), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                writeLog('No HTS PVR client installed or inactive', level=xbmc.LOGERROR)
                self.notifyOSD(__LS__(30030), __LS__(30032), icon=xbmcgui.NOTIFICATION_ERROR)
            xbmc.sleep(6000)

    # send email to user to inform about a successful completition

    def deliverMail(self, message):
        if self.__notification:
            try:
                __port = {'None': 25, 'SSL/TLS': 465, 'STARTTLS': 587}
                __s_msg = Message()
                __s_msg.set_charset(self.__charset)
                __s_msg.set_payload(message, charset=self.__charset)
                __s_msg["Subject"] = __LS__(30046) % (HOST)
                __s_msg["From"] = self.__smtpfrom
                __s_msg["To"] = self.__smtpto

                if self.__smtpenc == 'STARTTLS':
                    __s_conn = smtplib.SMTP(self.__smtpserver, __port[self.__smtpenc])
                    __s_conn.ehlo()
                    __s_conn.starttls()
                elif self.__smtpenc == 'SSL/TLS':
                    __s_conn = smtplib.SMTP_SSL(self.__smtpserver, __port[self.__smtpenc])
                    __s_conn.ehlo()
                else:
                    __s_conn = smtplib.SMTP(self.__smtpserver, __port[self.__smtpenc])
                __s_conn.login(self.__smtpuser, self.__smtppass)
                __s_conn.sendmail(self.__smtpfrom, self.__smtpto, __s_msg.as_string())
                __s_conn.close()
                writeLog('Mail delivered to %s.' % (self.__smtpto), level=xbmc.LOGNOTICE)
                return True
            except Exception:
                writeLog('Mail could not be delivered. Check your settings.', xbmc.LOGERROR)
                return False
        else:
            writeLog('"%s" completed, no Mail delivered.' % (message))
            return True

    def readXML(self, xmlnode):
        nodedata = []
        while self.__conn_established:
            try:
                __f = urllib2.urlopen(self.__server + ':' + self.__port + '/status.xml')
                __xmlfile = __f.read()
                self.__xml = minidom.parseString(__xmlfile)
                __f.close()
                nodes = self.__xml.getElementsByTagName(xmlnode)
                if nodes:
                    for node in nodes:
                        nodedata.append(node.childNodes[0].data)
                break
            except Exception:
                writeLog("Could not read from %s" % self.__server, xbmc.LOGERROR)
                self.establishConn()
        return nodedata

    def getSysState(self, Net=True):
        bState = isUSR

        # Check for current recordings. If there a 'status' tag,
        # and content is "Recording" current recording is in progress
        nodedata = self.readXML('status')
        if nodedata and 'Recording' in nodedata: bState |= isREC

        # Check for future recordings. If there is a 'next' tag a future recording comes up
        nodedata = self.readXML('next')
        if nodedata:
            if int(nodedata[0]) <= (self.__prerun + self.__postrun) or (self.__wakeup == "NVRAM" and int(nodedata[0]) < 11): bState |= isREC

        # Check if system started up because of actualizing EPG-Data
        if self.__epg_interval > 0:
            __curTime = datetime.datetime.now()
            __dayDelta = self.__epg_interval
            if int(__curTime.strftime('%j')) % __dayDelta == 0: __dayDelta = 0
            __epgTime = (__curTime + datetime.timedelta(days=__dayDelta) -
                         datetime.timedelta(days=int(__curTime.strftime('%j')) % self.__epg_interval)).replace(hour=self.__epg_time, minute=0, second=0)
            if __epgTime <= __curTime <= __epgTime + datetime.timedelta(minutes=self.__epg_duration): bState |= isEPG

        # Check if any watched process is running
        if self.__pp_enabled:
            for _proc in self.__pp_list:
                _pid = subprocess.Popen(['pidof', _proc], stdout=subprocess.PIPE)
                if _pid.stdout.read().strip(): bState |= isPRG

        # Check for active network connection(s)
        if self.__network and Net:
            for port in self.__monitored_ports:
                nwc = subprocess.Popen('netstat -an | grep ESTABLISHED | grep -v "127.0.0.1" | grep ":%s "' % port, stdout=subprocess.PIPE, shell=True).communicate()
                nwc = nwc[0].strip()
                if nwc and len(nwc.split('\n')) > 0:
                    bState |= isNET
                    writeLog('Connection on port %s established and active' % (port))

        # Check if screensaver is running
        self.__ScScreensaverActive = xbmc.getCondVisibility('System.ScreenSaverActive')
        return bState

    def calcNextSched(self):

        __WakeUpUTRec = 0
        __WakeUpUTEpg = 0
        __WakeEPG = 0
        __curTime = datetime.datetime.now()

        nodedata = self.readXML('next')
        if nodedata:
            self.__wakeUp = (__curTime + datetime.timedelta(minutes=int(nodedata[0]) - self.__prerun)).replace(second=0)
            __WakeUpUTRec = int(time.mktime(self.__wakeUp.timetuple()))
        else:
            writeLog('No recordings to schedule')

        if self.__epg_interval > 0:
            __dayDelta = self.__epg_interval
            if int(__curTime.strftime('%j')) % __dayDelta == 0: __dayDelta = 0
            __WakeEPG = (__curTime + datetime.timedelta(days=__dayDelta) -
                        datetime.timedelta(days=int(__curTime.strftime('%j')) % self.__epg_interval)).replace(hour=self.__epg_time, minute=0, second=0)
            if __curTime > __WakeEPG:
                __WakeEPG = __WakeEPG + datetime.timedelta(days=self.__epg_interval)

            __WakeUpUTEpg = int(time.mktime(__WakeEPG.timetuple()))

        if __WakeUpUTRec > 0 or __WakeUpUTEpg > 0:

            if __WakeUpUTRec <= __WakeUpUTEpg:
                if __WakeUpUTRec > 0:
                    self.__wakeUpUT = __WakeUpUTRec
                    self.__wakeUpStrOffset = 0
                elif __WakeUpUTEpg > 0:
                    self.__wakeUpUT = __WakeUpUTEpg
                    self.__wakeUp = __WakeEPG
                    self.__wakeUpStrOffset = 1
            elif __WakeUpUTRec > __WakeUpUTEpg:
                if __WakeUpUTEpg > 0:
                    self.__wakeUpUT = __WakeUpUTEpg
                    self.__wakeUp = __WakeEPG
                    self.__wakeUpStrOffset = 1
                elif __WakeUpUTRec > 0:
                    self.__wakeUpUT = __WakeUpUTRec
                    self.__wakeUpStrOffset = 0
            self.__wakeUpMessage = '\n%s %s' % (
                __LS__(30024), __LS__(30018 + self.__wakeUpStrOffset) % (self.__wakeUp.strftime('%d.%m.%Y %H:%M')))
            return True
        else:
            return False

    def countDown(self, counter):

        # deactivate screensaver (if running), check screenmode, set progressbar and notify

        __bar = 0
        __percent = 0
        __counter = counter
        __idleTime = xbmc.getGlobalIdleTime()

        writeLog('Display countdown dialog for %s secs' % __counter)

        if self.__ScreensaverActive and self.__windowID: xbmc.executebuiltin('ActivateWindow(%s)' % (self.__windowID))
        if xbmc.getCondVisibility('VideoPlayer.isFullscreen'):
            writeLog('Countdown possibly invisible (fullscreen mode)')
            writeLog('Showing additional notification')
            self.notifyOSD(__LS__(30010), __LS__(30011) % __counter)
            xbmc.sleep(5000)

        pb = xbmcgui.DialogProgressBG()
        pb.create(__LS__(30010), __LS__(30011) % __counter)
        pb.update(__percent)

        # actualize progressbar
        while __bar <= __counter:
            __percent = int(__bar * 100 / __counter)
            pb.update(__percent, __LS__(30010), __LS__(30011) % (__counter - __bar))

            if __idleTime > xbmc.getGlobalIdleTime():
                writeLog('Countdown aborted by user', level=xbmc.LOGNOTICE)
                pb.close()
                return True

            xbmc.sleep(1000)
            __idleTime += 1
            __bar +=1
        pb.close()
        return False

    def setWakeup(self):

        if self.calcNextSched():
            __task = ['Recording', 'EPG-Update']
            writeLog('Wakeup for %s by %s at %s' % (__task[self.__wakeUpStrOffset], self.__wakeup,  self.__wakeUp.strftime('%d.%m.%y %H:%M')))
            if self.__nextsched: self.notifyOSD(__LS__(30017), __LS__(30018 + self.__wakeUpStrOffset) % (self.__wakeUp.strftime('%d.%m.%Y %H:%M')))
        elif self.__nextsched:
            self.notifyOSD(__LS__(30010), __LS__(30014))

        if xbmc.getCondVisibility('Player.Playing'):
            writeLog('Stopping Player')
            xbmc.Player().stop()

        _t = xbmc.getGlobalIdleTime()
        xbmc.sleep(5000)
        if xbmc.getGlobalIdleTime() - _t < 5:
            writeLog('Shutdown aborted by user')
            return False

        _sm = ['Kodi/XBMC', 'OS']
        writeLog('Instruct the system to shut down using %s method' % (_sm[self.__shutdown]))

        if self.__sudo:
            os.system('sudo %s %s %s %s' % (SHUTDOWN_CMD, self.__wakeup, self.__wakeUpUT, self.__shutdown))
        else:
            os.system('%s %s %s %s' % (SHUTDOWN_CMD, self.__wakeup, self.__wakeUpUT, self.__shutdown))
        if self.__shutdown == 0: xbmc.shutdown()

    ####################################### START MAIN SERVICE #####################################

    def start(self, mode=None):

        if mode is None:
            _bState = self.getSysState(Net=False)
            if not _bState:
                writeLog('Service with id %s finished' % (self.rndProcNum), level=xbmc.LOGNOTICE)
                return True

        elif mode == 'poweroff':
            writeLog('Poweroff command received', level=xbmc.LOGNOTICE)

            _bState = self.getSysState(Net=True)
            if (_bState & isREC):
                self.notifyOSD(__LS__(30015), __LS__(30020), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Recording in progress'
            elif (_bState & isEPG):
                self.notifyOSD(__LS__(30015), __LS__(30021), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'EPG-Update'
            elif (_bState & isPRG):
                self.notifyOSD(__LS__(30015), __LS__(30022), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Postprocessing'
            elif (_bState & isNET):
                self.notifyOSD(__LS__(30015), __LS__(30023), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Network active'
            else:
                return self.setWakeup()
        else: return False

        if (_bState & isEPG) and self.__epg_grab_ext and os.path.isfile(EXTGRABBER):
            writeLog('Starting script for grabbing external EPG')
            #
            # ToDo: implement startup of external script (epg grabbing)
            #
            _epgpath = self.__epg_path
            if self.__epg_store and _epgpath == '': _epgpath = '/dev/null'
            _start = datetime.datetime.now()
            try:
                _comm = subprocess.Popen('%s %s %s' % (EXTGRABBER, _epgpath, self.__epg_socket),
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
                while _comm.poll() is None:
                    writeLog(_comm.stdout.readline().decode('utf-8', 'ignore').strip())

                writeLog('external EPG grabber script tooks %s seconds' % ((datetime.datetime.now() - _start).seconds))
            except Exception:
                writeLog('Could not start external EPG grabber script', xbmc.LOGERROR)

        idle = xbmc.getGlobalIdleTime()

        ### START MAIN LOOP ###

        mon = xbmc.Monitor()

        while (not mon.abortRequested() and _bState):

            if mon.waitForAbort(CYCLE): return True
            if idle > xbmc.getGlobalIdleTime():
                writeLog('User activty detected')
                writeLog('System was %s idle' % (time.strftime('%H:%M:%S', time.gmtime(idle))))
                return True
            idle = xbmc.getGlobalIdleTime()

            writeLog('Service polling Net/Post/Rec/EPG: {0:04b}'.format(_bState), level=xbmc.LOGNOTICE)

            # check outdated recordings
            nodedata = self.readXML('title')
            for item in nodedata:
                if not item in self.__recTitles:
                    self.__recTitles.append(item)
                    writeLog('Recording of "%s" is/becomes active' % (item))
            for item in self.__recTitles:
                if not item in nodedata:
                    self.__recTitles.remove(item)
                    writeLog('Recording of "%s" has finished' % (item))
                    if not self.__recTitles: self.calcNextSched()
                    if mode is None:
                        self.deliverMail(__LS__(30047) % (HOST, item) + self.__wakeUpMessage)
            _bState= self.getSysState()
            if not self.__ScreensaverActive: self.__windowID = xbmcgui.getCurrentWindowId()

        ### END MAIN LOOP ###

        if not _bState and mode == 'poweroff':
            if not self.countDown(counter=self.__counter): self.setWakeup()
        elif not _bState and mode is None:
            writeLog('Service was running without any user activity', level=xbmc.LOGNOTICE)
            return self.setWakeup()

        ##################################### END OF MAIN SERVICE #####################################


TVHMan = Manager()

try:
    if sys.argv[1].upper() == 'CHECKMAILSETTINGS':
        setup_ok = TVHMan.deliverMail(__LS__(30065) % (HOST))
        if setup_ok:
            TVHMan.dialogOK(__LS__(30066), __LS__(30068) % (__addon__.getSetting('smtp_to')))
        else:
            TVHMan.dialogOK(__LS__(30067), __LS__(30069) % (__addon__.getSetting('smtp_to')))
    elif sys.argv[1].upper() == 'POWEROFF':
        TVHMan.start(mode='poweroff')

# Start without arguments (i.e. login|startup|restart)

except IndexError:
    TVHMan.start()

except Exception, e:
    writeLog('An unhandled exception has occured. Please inform the maintainer of this addon', xbmc.LOGERROR)

__p = platform.uname()
writeLog('Service with id %s (V.%s on %s) kicks off' % (TVHMan.rndProcNum, __version__,  __p[1]), level=xbmc.LOGNOTICE)

del TVHMan

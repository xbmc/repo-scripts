# -*- coding: utf-8 -*-
import sys, os, stat, subprocess
import xbmc, xbmcaddon, xbmcgui
import time, datetime, random
import requests
from xml.dom import minidom
import smtplib
from email.message import Message
import resources.lib.tools as tools

release = tools.release()

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo('version')
__path__ = __addon__.getAddonInfo('path')
__LS__ = __addon__.getLocalizedString

SHUTDOWN_CMD = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'shutdown.sh'))
EXTGRABBER = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'epggrab_ext.sh'))

# set permissions for these files, this is required after installation or update

_sts = os.stat(SHUTDOWN_CMD)
_stg = os.stat(EXTGRABBER)
if not (_sts.st_mode & stat.S_IEXEC): os.chmod(SHUTDOWN_CMD, _sts.st_mode | stat.S_IEXEC)
if not (_stg.st_mode & stat.S_IEXEC): os.chmod(EXTGRABBER, _stg.st_mode | stat.S_IEXEC)

CYCLE = 15  # polling cycle

tools.writeLog('OS ID is %s' % (release.osid))

if ('libreelec' or 'openelec') in release.osid and tools.getAddonSetting('sudo', sType=tools.BOOL):
    __addon__.setSetting('sudo', 'false')
    tools.writeLog('OS is LibreELEC or OpenELEC, reset wrong setting \'sudo\' in options')

# binary Flags

isRES = 0b10000     # TVH PM has started by Resume on record/EPG
isNET = 0b01000     # Network is active
isPRG = 0b00100     # Programs/Processes are active
isREC = 0b00010     # Recording is or becomes active
isEPG = 0b00001     # EPG grabbing is active
isUSR = 0b00000     # User is active

class Manager(object):

    def __init__(self):

        self.__xml = None
        self.__recTitles = []
        self.__wakeUp = None
        self.__wakeUpUT = None
        self.__monitored_ports = ''
        self.rndProcNum = random.randint(1, 1024)
        self.hasPVR = None

        ### read addon settings

        self.__prerun = tools.getAddonSetting('margin_start', sType=tools.NUM)
        self.__postrun = tools.getAddonSetting('margin_stop', sType=tools.NUM)
        self.__shutdown = tools.getAddonSetting('shutdown_method', sType=tools.NUM)
        self.__sudo = 'sudo ' if tools.getAddonSetting('sudo', sType=tools.BOOL) else ''
        self.__counter = tools.getAddonSetting('notification_counter', sType=tools.NUM)
        self.__nextsched = tools.getAddonSetting('next_schedule', sType=tools.BOOL)

        # TVHeadend server
        self.__maxattempts = tools.getAddonSetting('conn_attempts', sType=tools.NUM)

        self.hasPVR = True
        try:
            __addonTVH__ = xbmcaddon.Addon('pvr.hts')
            self.__server = 'http://' + __addonTVH__.getSetting('host')
            self.__port = __addonTVH__.getSetting('http_port')
            self.__user = __addonTVH__.getSetting('user')
            self.__pass = __addonTVH__.getSetting('pass')
        except RuntimeError:
            tools.writeLog('Addon \'pvr.hts\' not installed or inactive', level=xbmc.LOGERROR)
            self.hasPVR = False

        # check if network activity has to observed
        self.__network = tools.getAddonSetting('network', sType=tools.BOOL)
        self.__monitored_ports = self.createwellformedlist('monitored_ports')

        # check if processes has to observed
        self.__pp_enabled = tools.getAddonSetting('postprocessor_enable', sType=tools.BOOL)
        self.__pp_list = self.createwellformedlist('processor_list')

        # mail settings
        self.__notification = tools.getAddonSetting('smtp_sendmail', sType=tools.BOOL)
        self.__smtpserver = tools.getAddonSetting('smtp_server')
        self.__smtpuser = tools.getAddonSetting('smtp_user')
        self.__smtppass = self.crypt('smtp_passwd', 'smtp_key', 'smtp_token')
        self.__smtpenc = tools.getAddonSetting('smtp_encryption')
        self.__smtpfrom = tools.getAddonSetting('smtp_from')
        self.__smtpto = tools.getAddonSetting('smtp_to')
        self.__charset = tools.getAddonSetting('charset')

        # EPG-Wakeup settings
        self.__epg_interval = tools.getAddonSetting('epgtimer_interval', sType=tools.NUM)
        self.__epg_time = tools.getAddonSetting('epgtimer_time', sType=tools.NUM)
        self.__epg_duration = tools.getAddonSetting('epgtimer_duration', sType=tools.NUM)
        self.__epg_grab_ext = tools.getAddonSetting('epg_grab_ext', sType=tools.BOOL)
        self.__epg_socket = xbmc.translatePath(tools.getAddonSetting('epg_socket_path'))
        self.__epg_store = tools.getAddonSetting('store_epg', sType=tools.BOOL)
        self.__epg_path = xbmc.translatePath(os.path.join(tools.getAddonSetting('epg_path'), 'epg.xml'))

        tools.writeLog('Settings loaded')

    @classmethod
    def createwellformedlist(cls, setting):

        ''' transform possible ugly userinput (e.g. 'p1, p2,,   p3 p4  ') to a shapely list '''
        return ' '.join(tools.getAddonSetting(setting).replace(',', ' ').split()).split()

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

        # send email to user to inform about a successful completition

    def deliverMail(self, message):
        if self.__notification:
            try:
                __port = {'None': 25, 'SSL/TLS': 465, 'STARTTLS': 587}
                __s_msg = Message()
                __s_msg.set_charset(self.__charset)
                __s_msg.set_payload(message, charset=self.__charset)
                __s_msg["Subject"] = __LS__(30046) % (release.hostname)
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
                tools.writeLog('Mail delivered to %s.' % (self.__smtpto), level=xbmc.LOGNOTICE)
                return True
            except Exception, e:
                tools.writeLog('Mail could not be delivered. Check your settings.', xbmc.LOGERROR)
                tools.writeLog(e)
                return False
        else:
            tools.writeLog('"%s" completed, no Mail delivered.' % (message))
            return True

    # Connect to TVHeadend and establish connection (log in))

    def getPvrStatusXML(self):

        _attempts = self.__maxattempts

        if not self.hasPVR:
            tools.writeLog('No HTS PVR client installed or inactive', level=xbmc.LOGERROR)
            tools.Notify().notify(__LS__(30030), __LS__(30032), icon=xbmcgui.NOTIFICATION_ERROR)
            return None
        else:
            while self.hasPVR and _attempts > 0:
                # try DigestAuth as first, as this is the default auth on TVH > 3.9
                try:
                    conn = requests.get('%s:%s/status.xml' % (self.__server, self.__port), auth=requests.auth.HTTPDigestAuth(self.__user, self.__pass))
                    conn.close()
                    if conn.status_code == 200:
                        tools.writeLog('Getting status.xml (Digest Auth)')
                        return conn.content
                    else:
                        # try BasicAuth as older method
                        conn = requests.get('%s:%s/status.xml' % (self.__server, self.__port), auth=requests.auth.HTTPBasicAuth(self.__user, self.__pass))
                        conn.close()
                        if conn.status_code == 200:
                            tools.writeLog('Getting status.xml (Basic Auth)')
                            return conn.content

                    if conn.status_code == 401:
                        tools.writeLog('Unauthorized access (401)')
                        break
                except requests.ConnectionError:
                    _attempts -= 1
                    tools.writeLog('%s unreachable, remaining attempts: %s' % (self.__server, _attempts))
                    xbmc.sleep(5000)
                    continue

        tools.Notify().notify(__LS__(30030), __LS__(30031), icon=xbmcgui.NOTIFICATION_ERROR)
        return None

    def readStatusXML(self, xmlnode):

        nodedata = []
        try:
            _xml = minidom.parseString(self.getPvrStatusXML())
            nodes = _xml.getElementsByTagName(xmlnode)
            for node in nodes:
                if node: nodedata.append(node.childNodes[0].data)
            return nodedata
        except TypeError:
            tools.writeLog("Could not read XML tree from %s" % self.__server, xbmc.LOGERROR)
        return nodedata

    def getSysState(self, Net=True, verbose=False):
        _flags = isUSR

        # Check for current recordings. If there a 'status' tag,
        # and content is "Recording" current recording is in progress
        nodedata = self.readStatusXML('status')
        if nodedata and 'Recording' in nodedata: _flags |= isREC

        # Check for future recordings. If there is a 'next' tag a future recording comes up
        nodedata = self.readStatusXML('next')
        if nodedata:
            if int(nodedata[0]) <= (self.__prerun + self.__postrun):
                # immediate
                _flags |= isREC
            else:
                # later
                _flags |= isRES

        # Check if system started up because of actualizing EPG-Data
        if self.__epg_interval > 0:
            __curTime = datetime.datetime.now()
            __dayDelta = self.__epg_interval
            if int(__curTime.strftime('%j')) % __dayDelta == 0: __dayDelta = 0
            __epgTime = (__curTime + datetime.timedelta(days=__dayDelta) -
                         datetime.timedelta(days=int(__curTime.strftime('%j')) % self.__epg_interval)).replace(hour=self.__epg_time, minute=0, second=0)
            if __epgTime <= __curTime <= __epgTime + datetime.timedelta(minutes=self.__epg_duration): _flags |= isEPG

        # Check if any watched process is running
        if self.__pp_enabled:
            for _proc in self.__pp_list:
                _pid = subprocess.Popen(['pidof', _proc], stdout=subprocess.PIPE)
                if _pid.stdout.read().strip(): _flags |= isPRG

        # Check for active network connection(s)
        if self.__network and Net:
            _port = ''
            for port in self.__monitored_ports:
                nwc = subprocess.Popen('netstat -an | grep -iE "(established|verbunden)" | grep -v "127.0.0.1" | grep ":%s "' % port, stdout=subprocess.PIPE, shell=True).communicate()
                nwc = nwc[0].strip()
                if nwc and len(nwc.split('\n')) > 0:
                    _flags |= isNET
                    _port += '%s, ' % (port)
            if _port: tools.writeLog('Network on port %s established and active' % (_port[:-2]))
        if verbose: tools.writeLog('Status flags: {0:05b} (RES/NET/PRG/REC/EPG)'.format(_flags))
        return _flags

    def calcNextSched(self):

        __WakeUpUTRec = 0
        __WakeUpUTEpg = 0
        __WakeEPG = 0
        __curTime = datetime.datetime.now()
        __msgid = 30018

        _flags = isUSR
        nodedata = self.readStatusXML('next')
        if nodedata:
            self.__wakeUp = (__curTime + datetime.timedelta(minutes=int(nodedata[0]) - self.__prerun)).replace(second=0)
            __WakeUpUTRec = int(time.mktime(self.__wakeUp.timetuple()))
            _flags |= isRES
        else:
            tools.writeLog('No recordings to schedule')

        if self.__epg_interval > 0:
            __dayDelta = self.__epg_interval
            if int(__curTime.strftime('%j')) % __dayDelta == 0: __dayDelta = 0
            __WakeEPG = (__curTime + datetime.timedelta(days=__dayDelta) -
                        datetime.timedelta(days=int(__curTime.strftime('%j')) % self.__epg_interval)).replace(hour=self.__epg_time, minute=0, second=0)
            if __curTime > __WakeEPG: __WakeEPG = __WakeEPG + datetime.timedelta(days=self.__epg_interval)
            __WakeUpUTEpg = int(time.mktime(__WakeEPG.timetuple()))
            _flags |= isRES
        else:
            tools.writeLog('No EPG to schedule')

        if _flags:
            if __WakeUpUTRec <= __WakeUpUTEpg:
                if __WakeUpUTRec > 0:
                    self.__wakeUpUT = __WakeUpUTRec
                elif __WakeUpUTEpg > 0:
                    self.__wakeUpUT = __WakeUpUTEpg
                    self.__wakeUp = __WakeEPG
                    __msgid = 30019
            else:
                if __WakeUpUTEpg > 0:
                    self.__wakeUpUT = __WakeUpUTEpg
                    self.__wakeUp = __WakeEPG
                    __msgid = 30019
                elif __WakeUpUTRec > 0:
                    self.__wakeUpUT = __WakeUpUTRec

            # show notifications

            if __msgid == 30018:
                tools.writeLog('Wakeup for recording at %s' % (self.__wakeUp.strftime('%d.%m.%y %H:%M')))
                _flags |= isREC
                if self.__nextsched: tools.Notify().notify(__LS__(30017), __LS__(__msgid) % (self.__wakeUp.strftime('%d.%m.%Y %H:%M')))
            elif __msgid == 30019:
                tools.writeLog('Wakeup for EPG update at %s' % (self.__wakeUp.strftime('%d.%m.%y %H:%M')))
                _flags |= isEPG
                if self.__nextsched: tools.Notify().notify(__LS__(30017), __LS__(__msgid) % (self.__wakeUp.strftime('%d.%m.%Y %H:%M')))
        else:
            if self.__nextsched: tools.Notify().notify(__LS__(30010), __LS__(30014))
        xbmc.sleep(6000)
        return _flags

    @classmethod
    def countDown(cls, counter=5):

        __bar = 0
        __percent = 0
        __counter = counter
        __idleTime = xbmc.getGlobalIdleTime()

        # deactivate screensaver (send key select)

        if xbmc.getCondVisibility('System.ScreenSaverActive'):
            query = {
                "method": "Input.Select"
            }
            tools.jsonrpc(query)

        if xbmc.getCondVisibility('VideoPlayer.isFullscreen'):
            tools.writeLog('Countdown possibly invisible (fullscreen mode)')
            tools.writeLog('Showing additional notification')
            tools.Notify().notify(__LS__(30010), __LS__(30011) % (__counter))

        # show countdown

        tools.writeLog('Display countdown dialog for %s secs' % __counter)
        pb = xbmcgui.DialogProgressBG()
        pb.create(__LS__(30010), __LS__(30011) % __counter)
        pb.update(__percent)

        # actualize progressbar

        while __bar <= __counter:
            __percent = int(__bar * 100 / __counter)
            pb.update(__percent, __LS__(30010), __LS__(30011) % (__counter - __bar))

            if __idleTime > xbmc.getGlobalIdleTime():
                tools.writeLog('Countdown aborted by user', level=xbmc.LOGNOTICE)
                pb.close()
                return True

            xbmc.sleep(1000)
            __idleTime += 1
            __bar +=1
        pb.close()
        return False

    def setWakeup(self):

        if xbmc.getCondVisibility('Player.Playing'):
            tools.writeLog('Stopping Player')
            xbmc.Player().stop()

        _flags = self.calcNextSched()
        tools.writeLog('Instruct the system to shut down using %s' % ('Application' if self.__shutdown == 0 else 'OS'), xbmc.LOGNOTICE)
        tools.writeLog('Wake-Up Unix Time: %s' % (self.__wakeUpUT), xbmc.LOGNOTICE)
        tools.writeLog('Flags on resume points will be later {0:05b}'.format(_flags))

        os.system('%s%s %s %s' % (self.__sudo, SHUTDOWN_CMD, self.__wakeUpUT, self.__shutdown))
        if self.__shutdown == 0: xbmc.shutdown()
        xbmc.sleep(1000)

        # If we suspend instead of poweroff the system, we need the flags to control the main loop of the service.
        # On suspend we have to resume the service on resume points instead of start on poweron/login.
        # additional we set the resume flag in calcNextSched if necessary

        return _flags

    ####################################### START MAIN SERVICE #####################################

    def start(self, mode=None):

        tools.writeLog('Starting service with id:%s@mode:%s' % (self.rndProcNum, mode))
        # reset RTC
        os.system('%s%s %s %s' % (self.__sudo, SHUTDOWN_CMD, 0, 0))
        tools.writeLog('Reset RTC')

        _flags = self.getSysState(verbose=True)
        if mode is None:

            if not (_flags & (isREC | isEPG | isPRG | isNET)):
                tools.writeLog('Service with id %s finished' % (self.rndProcNum), level=xbmc.LOGNOTICE)
                return

        elif mode == 'sendmail':
            if self.deliverMail(__LS__(30065) % (release.hostname)):
                tools.dialogOK(__LS__(30066), __LS__(30068) % (self.__smtpto))
            else:
                tools.dialogOK(__LS__(30067), __LS__(30069) % (self.__smtpto))
            return

        elif mode == 'poweroff':
            tools.writeLog('Poweroff command received', level=xbmc.LOGNOTICE)

            if (_flags & isREC):
                tools.Notify().notify(__LS__(30015), __LS__(30020), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Recording in progress'
            elif (_flags & isEPG):
                tools.Notify().notify(__LS__(30015), __LS__(30021), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'EPG-Update'
            elif (_flags & isPRG):
                tools.Notify().notify(__LS__(30015), __LS__(30022), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Postprocessing'
            elif (_flags & isNET):
                tools.Notify().notify(__LS__(30015), __LS__(30023), icon=xbmcgui.NOTIFICATION_WARNING)  # Notify 'Network active'
            else:
                if self.countDown(): return
                _flags = self.setWakeup()
        else: return

        # RESUME POINT #1

        if (_flags & isRES) and mode == 'poweroff':
            tools.writeLog('Resume point #1 passed', xbmc.LOGNOTICE)
            _flags = self.getSysState(verbose=True) & (isREC | isEPG | isPRG | isNET)
            if not _flags: return
            mode = None

        if (_flags & isEPG) and self.__epg_grab_ext and os.path.isfile(EXTGRABBER):
            tools.writeLog('Starting script for grabbing external EPG')
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
                    tools.writeLog(_comm.stdout.readline().decode('utf-8', 'ignore').strip())

                tools.writeLog('external EPG grabber script tooks %s seconds' % ((datetime.datetime.now() - _start).seconds))
            except Exception:
                tools.writeLog('Could not start external EPG grabber script', xbmc.LOGERROR)

        idle = xbmc.getGlobalIdleTime()

        ### START MAIN LOOP ###

        mon = xbmc.Monitor()

        while _flags:

            _flags = self.getSysState(verbose=True) & (isREC | isEPG | isPRG | isNET)

            if mon.waitForAbort(CYCLE):
                tools.writeLog('Abort request received', level=xbmc.LOGNOTICE)
                break
            if idle > xbmc.getGlobalIdleTime():
                tools.writeLog('User activty detected (was %s idle)' % (time.strftime('%H:%M:%S', time.gmtime(idle))))
                break

            idle = xbmc.getGlobalIdleTime()

            # check outdated recordings
            nodedata = self.readStatusXML('title')
            for item in nodedata:
                if not item in self.__recTitles:
                    self.__recTitles.append(item)
                    tools.writeLog('Recording of "%s" is active' % (item))
            for item in self.__recTitles:
                if not item in nodedata:
                    self.__recTitles.remove(item)
                    tools.writeLog('Recording of "%s" has finished' % (item))
                    if mode is None: self.deliverMail(__LS__(30047) % (release.hostname, item))

            if not _flags:
                if mode == 'poweroff':
                    if self.countDown(counter=self.__counter): break
                    _flags = self.setWakeup()
                else:
                    tools.writeLog('Service was running w/o user activity', level=xbmc.LOGNOTICE)
                    _flags = self.setWakeup()

                # RESUME POINT #2

                tools.writeLog('Resume point #2 passed', xbmc.LOGNOTICE)
                mode = None
                idle = 0
                _flags = self.getSysState(verbose=True) & (isREC | isEPG | isPRG | isNET)

        ### END MAIN LOOP ###

        ##################################### END OF MAIN SERVICE #####################################

# mode translations
modes = {'NONE': None, 'POWEROFF': 'poweroff', 'CHECKMAILSETTINGS': 'sendmail'}
try:
    mode = sys.argv[1].upper()
except IndexError:
    # Start without arguments (i.e. login|startup|restart)
    mode = 'NONE'
try:
    TVHMan = Manager()
    TVHMan.start(mode=modes[mode])
    tools.writeLog('Service with id %s (V.%s on %s) kicks off' % (TVHMan.rndProcNum, __version__,  release.hostname), level=xbmc.LOGNOTICE)
    del TVHMan
except Exception:
    # tools.writeLog('An unhandled exception has occured. Please inform the maintainer of this addon', xbmc.LOGERROR)
    pass

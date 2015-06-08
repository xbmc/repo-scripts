# -*- coding: utf-8 -*-
# *
# *      Copyright © 2013 Postmet Corp.
# *      http://www.postmet.com
# *      Created by: Jermakovich Alexander <team@postmet.com>
# *

#execute targeted script at startup.
import xbmc
import xbmcgui
import os, stat, sys
#from os import path
import xbmcaddon
#import pyinotify
import threading
import time
import re
import platform as pl

__scriptname__ = "mcuphone_pip"
__author__     = "Team PostMet"
__GUI__        = "Postmet Corp"
__scriptId__   = "script.mcuphone"
__license__    = 1
__settings__   = xbmcaddon.Addon(id=__scriptId__)
__language__   = __settings__.getLocalizedString
__version__    = __settings__.getAddonInfo("version")
__cwd__        = __settings__.getAddonInfo('path')

PHONE_CONFIG   = xbmc.translatePath( os.path.join( __cwd__,'resources', '.mcuphonerc'))
PHONE_LOG      = '/home/' + os.getenv("USER") + '/mcuphone.log'
addon = xbmcaddon.Addon(id='script.mcuphone')

PHONE_PATH     = xbmc.translatePath( os.path.join( __cwd__,'resources', 'bin', 'mcuphonecsh.' + pl.machine() + '.bin'))
ORIG_DAEMON_PATH    = xbmc.translatePath( os.path.join( __cwd__,'resources', 'bin', 'mcuphonec.' + pl.machine() + '.bin' ))
DAEMON_PATH    = xbmc.translatePath( os.path.join( __cwd__,'resources', 'bin', 'mcuphonec'))


last_log_pos   = 0
CALL_STATUS = ''
CALLER_NAME = ''
QUIT = 0
os.system('killall -9 mcuphonec')
last_call_time = 0
started = 0

#class EventHandler(pyinotify.ProcessEvent):
#    def process_IN_MODIFY(self, event):
#        checkLogFile(self, event)
#
#wm = pyinotify.WatchManager()
#mask = pyinotify.IN_MODIFY

# while (not xbmc.abortRequested):
    # msize = xbmcaddon.Addon('script.mcuphone').getSetting("multimedia_size")
    # xbmcgui.Dialog().ok('Msize', 'Msize: ' + msize)
#    xbmc.sleep(30000)

# Set GUI active flag (used from MCUphone gui)
def setGuiActive(is_active):
    # xbmcaddon.Addon('script.mcuphone_pip').setSetting("gui_active", is_active)
    if is_active:
        os.system("touch /home/" + os.getenv("USER") + "/mcu_gui")
    elif os.path.isfile("/home/" + os.getenv("USER") + "/mcu_gui"):
        try:
            os.remove("/home/" + SYSTEM_USER + "/mcu_gui")
        except:
            xlog('Cant delete mcu_gui')

# get GUI active flag (used from MCUphone gui)
def getGuiActive():
    # return xbmcaddon.Addon('script.mcuphone_pip').getSetting("gui_active")
    if os.path.isfile("/home/" + os.getenv("USER") + "/mcu_gui"):
        # xlog('sGui A')
        return 1
    else:
        # xlog('sGui .')
        return 0

# perform basic mcuphone init. (without visual adjustments)
def phoneInit():

    if not os.path.isfile(DAEMON_PATH):
	os.symlink(ORIG_DAEMON_PATH, DAEMON_PATH)

    array = ["sip_port", "sip_tcp_port", "sip_tls_port"]
    host =  __settings__.getSetting("asterisk_host")
    auto_register = __settings__.getSetting("asterisk_register")
    user = __settings__.getSetting("asterisk_user")
    password = __settings__.getSetting("asterisk_pass")
    auto_answer = __settings__.getSetting("auto_answer")
    sip_protocol = array[int(__settings__.getSetting("sip_protocol"))]
    sip_port = __settings__.getSetting("sip_port")
    video_port = __settings__.getSetting("video_port")
    audio_port = __settings__.getSetting("audio_port")
    direct_connection = __settings__.getSetting("direct_connection")
    behind_nat_one = __settings__.getSetting("behind_nat_one")
    behind_nat_ip = __settings__.getSetting("behind_nat_ip")
    behind_nat_two = __settings__.getSetting("behind_nat_two")
    behind_nat_stun = __settings__.getSetting("behind_nat_stun")
    debugging = __settings__.getSetting("debug")
    debug_level = __settings__.getSetting("debug_level")

    debug_level = int(debug_level) + 1
    auto_answer = '-a' if auto_answer == "true" else ''
    debug_level = debug_level if debugging == "true" else 2
    cmd = 'bash -c "' + PHONE_PATH + ' init -d %s %s -l %s -c %s"' % (debug_level, auto_answer, PHONE_LOG, PHONE_CONFIG)
    xlog(cmd)
    os.system(cmd)
    time.sleep(1)

    if auto_register == "true":
        phone("register sip:%s@%s sip:%s %s" % (str(user), host, host, str(password)))

    phone("ports sip " + str(sip_port))
    if sip_protocol == array[0]:
        phone("param %s 0" %(array[1]))
        phone("param %s 0" %(array[2]))
    if sip_protocol == array[1]:
        phone("param %s 0" %(array[0]))
        phone("param %s 0" %(array[2]))
    if sip_protocol == array[2]:
        phone("param %s 0" %(array[0]))
        phone("param %s 0" %(array[1]))
    phone("param %s %s" % (sip_protocol, str(sip_port)))
    phone("param rtp video_rtp_port " + str(video_port))
    phone("param rtp audio_rtp_port " + str(audio_port))
    if direct_connection == "true":
        phone("firewall none")
    if behind_nat_one == "true":
        phone("nat " + behind_nat_ip)
        phone("firewall nat")
    if behind_nat_two == "true":
        phone("stun " + behind_nat_stun)
        phone("firewall stun")
    phone("mute")

def xlog(msg):
    xbmc.log("##### [MCUP_pip] - Debug msg: %s" % (msg),level=xbmc.LOGDEBUG)

def phone(cmd):
    xlog(PHONE_PATH + " generic '%s'" % (cmd))
    return os.system(PHONE_PATH + " generic '%s'" % (cmd))

def checker():
    global QUIT
    file = open(PHONE_LOG,'r')
    while 1:
        if QUIT == 1:
            return
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(1)
            file.seek(where)
        else:
            checkLogFile(line)


def checkLogFile(logdata):
    global CALL_STATUS
    global CALLER_NAME
    global last_call_time
    global selected
    global started
    started = 0
    #logdata = logGetData(the_event.pathname)
    if getGuiActive():
        return
    ldss = logdata.split("\n")
    status_list = {
        'phoneCallOutgoingInit' : 'calling',
        'phoneCallIncomingReceived' : 'ringing',
        'phoneCallStreamsRunning' : 'active',
        'phoneCallConnected' : 'active',
        'phoneCallReleased' : 'end',
        'phoneCallEnd' : 'end',
        'phoneCallError' : 'error'
    }
    for lds in ldss:
        if 'moving from state' in lds:
            xlog("LDS: " + lds);
            fcall_ids = re.findall('Call 0x([0-9a-f]+): moving', lds)
            for fcall_id in fcall_ids:
                if fcall_id:
                    for sfull_name in status_list:
                        if sfull_name in lds:
                            CALL_STATUS = status_list[sfull_name]
        cont = ''
        if (CALL_STATUS == 'ringing' or CALL_STATUS == 'active') and 'From: "' in lds:
            cont = re.search('From: "([^\r\n]+)"' ,lds)
        elif (CALL_STATUS == 'ringing' or CALL_STATUS == 'active') and 'From: <' in lds:
            cont = re.search('From: <sip:([^\r\n]+)>' ,lds)
        if cont:
            CALLER_NAME = cont.group(1)

    if CALLER_NAME:
        # Need to add some delay to prevent false notifications
        last_call = (time.time() - last_call_time)
        if last_call > 2:
            xlog('!!! Dialog !!!')
            #xbmc.executebuiltin('AlarmClock(closedialog,Dialog.Close(all, true),00:00:15,silent)')
            # Send Esc to active widnow after 15 sec
            xbmc.executebuiltin('AlarmClock(closedialog,SendClick(10),00:00:15, silent)')
            # Show notificaton popup with caller name for 5 sec (right bottom corner)
            xbmc.executebuiltin('Notification(Incomming call, ' + CALLER_NAME + ', 5000)')
            __cwd__ = xbmcaddon.Addon('script.mcuphone_pip').getAddonInfo('path')
            # Display invisible modal window, which will catch OK/Enter/Esc press
            mydisplay = MyClass('pip.xml', __cwd__, "Default")
            mydisplay.doModal()
            #mydisplay.show()
            #time.sleep(20)
            del mydisplay
            #if xbmcgui.Dialog().ok('Incommign call', "Do you want to talk with " + CALLER_NAME + ' ?'):
            #    xbmc.executebuiltin('PlayerControl(Play)')
            #    time.sleep(1)
            #    xbmc.executebuiltin('RunScript(/home/' + os.getenv("USER") + '/.xbmc/addons/script.mcuphone/default.py)')
            #    time.sleep(1)
            #else:
            #    phone("terminate all")
            #    phone("window hide")
            #    time.sleep(1)
            last_call_time = time.time()
        CALLER_NAME = ''
        CALL_STATUS = ''

#def logGetData(log_file):
#    global last_log_pos
#    fh = open(log_file, 'r')
#    full_size = os.path.getsize(log_file)
#    if (last_log_pos == 0) or ((full_size - last_log_pos) < 10):
#        last_log_pos = full_size
#        return ''
#
#
#    fh.seek(last_log_pos)
#    log_data = fh.read(full_size - last_log_pos)
#    last_log_pos = full_size
#    return log_data

class MyClass(xbmcgui.WindowXMLDialog):
    def onClick(self, controlId):
        global started
        if started:
            started = 0
            return
        # Close button
        if controlId == 10:
            xbmc.executebuiltin('CancelAlarm(closedialog, true)')
            self.close()
            phone("terminate all")
            phone("window hide")
            time.sleep(1)
        # Button Answer
        if controlId == 901:
            xbmc.executebuiltin('CancelAlarm(closedialog, true)')
            self.close()
            xlog('onClick 901 - INIT')
	    #xbmc.executebuiltin('Action(select)')
	    xbmc.executebuiltin('PlayerControl(play)')
	    time.sleep(1)
            xbmc.executebuiltin('RunScript(/home/' + os.getenv("USER") + '/.kodi/addons/script.mcuphone/default.py)')
            time.sleep(1)
        started = 1

    def onAction(self, action):
        global started
        if started:
            started = 0
            return
        # Escape / timeout
        if action.getId() == 10:
            xbmc.executebuiltin('CancelAlarm(closedialog, true)')
            self.close()
            phone("terminate all")
            phone("window hide")
            time.sleep(1)
        # Enter / OK
#        if action.getId() == 7:
#            xbmc.executebuiltin('CancelAlarm(closedialog, true)')
#            self.close()
#            xlog('onAction 7 - INIT')
#            xbmc.executebuiltin('RunScript(/home/' + os.getenv("USER") + '/.xbmc/addons/script.mcuphone/default.py)')
#            time.sleep(1)
#        started = 1

def ensure_exec_perms(file_):
    st = os.stat(file_)
    os.chmod(file_, st.st_mode | stat.S_IEXEC)
    return file_

ensure_exec_perms(PHONE_PATH)
ensure_exec_perms(ORIG_DAEMON_PATH)
#notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
#notifier.start()
os.system('touch ' + PHONE_LOG)
#wm.add_watch(PHONE_LOG, mask)
w = threading.Thread(target=checker, name='checker')
w.start()
phoneInit()
xlog('INIT')
__settings__.setSetting("pip_active", '1')
setGuiActive(0)

monitor = xbmc.Monitor()
monitor.waitForAbort()
__settings__.setSetting("pip_active", '')
QUIT = 1
w.join()
os.system('killall -9 mcuphonec')


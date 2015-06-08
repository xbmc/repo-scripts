# -*- coding: utf-8 -*-
# *
# *      Copyright (C) 2012 Postmet corp
# *      http://www.postmet.com
# *      Created by: Perepelyatnik Peter, Jermakovich Alexander <team@postmet.com>
# *

import os, sys, ast
import xbmc
import xbmcgui
import time
import xbmcaddon
import ConfigParser
import re
import subprocess as sub
import GuiControl
#import pyinotify
import threading
import string

SYSTEM_USER = os.getenv("USER")
__scriptId__   = sys.modules[ "__main__" ].__scriptId__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__
__is_full_ver__ = sys.modules[ "__main__" ].__license__
__cwd__ = '/home/'+SYSTEM_USER+'/.kodi/addons/'+__scriptId__
__language__ = __settings__.getLocalizedString
_  = sys.modules[ "__main__" ].__language__

PHONE_CONFIG = sys.modules[ "__main__" ].PHONE_CONFIG
PHONE_LOG = sys.modules[ "__main__" ].PHONE_LOG
PHONE_TERMINATE = sys.modules[ "__main__" ].PHONE_TERMINATE
PHONE_PATH = sys.modules[ "__main__" ].PHONE_PATH
PHONE_BOOK = "/home/" + SYSTEM_USER + "/phone_book.pb"

RIGHT_SHIFT = 340
DOWN_SHIFT = 100

SIZE_KEYCODE = 58 # 0
SELFVIEW_KEYCODE = 59 # 1

WIDTH = int(xbmcgui.Window().getWidth())
HEIGHT = int(xbmcgui.Window().getHeight())
RIGHT_SHIFT = int(WIDTH * 350 / 1280)

# Default video size (2 - max. free size)
VIEW_SIZE = 2

proport = float(WIDTH) / HEIGHT

if proport < 1.2:
    min_width = 180 #176
    min_height = int(min_width / proport)
else:
    min_height = 150 #144
    min_width = int(min_height * proport)

step = int((WIDTH - RIGHT_SHIFT - min_width) / 2)
msize_x = int((WIDTH - RIGHT_SHIFT + min_width) / 2)
msize_y = int((int((WIDTH - RIGHT_SHIFT) / proport) + min_height) / 2)

VIEW_SIZES = [[], [], [], [], []]
VIEW_SIZES[0] = [min_width, min_height] # minimal size
#VIEW_SIZES[1] = [WIDTH - RIGHT_SHIFT - step, int((WIDTH - RIGHT_SHIFT - step)/ proport)]
VIEW_SIZES[1] = [msize_x, msize_y] # half of the working area
VIEW_SIZES[2] = [WIDTH - RIGHT_SHIFT, int((WIDTH - RIGHT_SHIFT) / proport)] # fit working area
VIEW_SIZES[3] = [WIDTH - RIGHT_SHIFT / 2, int((WIDTH - RIGHT_SHIFT / 2) / proport)] # partly overlap menu
VIEW_SIZES[4] = [WIDTH, HEIGHT] # Full screen

SELF_VIEWS = [-1, 0, 3, 1, 2] # disabled, right-bottom, left-bottom, left-top, right-top
SELF_VIEW_POS = 1 # 2-nd element from SELF_VIEWS. 1 = right-bottom
CALLIDS = {}

#wm = pyinotify.WatchManager()
#mask = pyinotify.IN_MODIFY

last_log_pos = 0 # last position in log file (used in notifier)
LP_WIN = '' # main window pointer

list_type = 'contacts' # default list type: contacts / recent
selected_list_item = 0

# counters to force quit on double Esc press
last_try_exit = 0
last_try_exit_cnt = 0

CALL_STATUS = 'end'
LAST_CALL_ID = ''

MAX_CALLS = 10 # maximum allowed active calls
NEED2CALL = '' # user clicked on contact in contacts/recent list
checker = '' # Log notifier pointer
IS_CALLING = 0 # does we have any call in Calling/Ringing status
pip_activated = 0 # 2: activated by PIP

QUIT = 0

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


##--------------------Main Window-----------------##
class GUI( xbmcgui.WindowXML ):
    def __init__( self, *args, **kwargs ):
        self.controlId = 0
    def onInit(self):
        global checker
        #global wm
        #global mask
        global LP_WIN
        global list_type
        global last_log_pos
        global pip_activated
        global CALLIDS
        LP_WIN = self

        list_top_pos = int(HEIGHT / 720) + 90
        # initialize all controllers ids
        GuiControl.defineControl(LP_WIN, list_top_pos)

        # start watching mcu log file
        #notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
        #notifier.start()
        os.system("touch " + PHONE_LOG)
        #wm.add_watch(PHONE_LOG, mask)
	checker = threading.Thread(target=checker, name='checker')
	checker.start()

        # assign label and fill list with contacts
        self.btn_settings.setLabel(__language__(30501))
        if list_type == 'contacts':
            for row in pb:
                self.list_contacts.addItem(row[0])
        else:
            self.list_contacts.addItems(last_calls)

        # parse MCUphone config to get last self_view position
        config = ConfigParser.ConfigParser()
        config.read(PHONE_CONFIG)
        try:
            SELF_VIEW_POS = config.get("video", "self_view")
        except:
            SELF_VIEW_POS = 1
        if not SELF_VIEW_POS:
            SELF_VIEW_POS = 1

        GuiControl.fixUpDown(False, False, 'end', canCall(''))
        self.setFocus(self.btn_contacts)

        setGuiActive(1)
        # if we have PIP service running:
        if __settings__.getSetting("pip_active"):
            #perform short init (only visual adjustments, without auth and net settings)
            phoneInitShort()
            xlog('PIP!!!')
            # Analize new log data (added after last execution of gui)
            old_log_pos = getLastLogPos()
            cur_log_size = os.path.getsize(PHONE_LOG)
            if old_log_pos < cur_log_size:
                last_log_pos = old_log_pos
            else:
                last_log_pos = 100
            logdata = logGetData(PHONE_LOG)
            ldss = logdata.split("\n")
            last_statuss = ''
            for lds in ldss:
                call_id = logSetCallId(lds)
                lname = logSetName(lds)
                # xlog('IS: %s %s' % (call_id, lname))
                if call_id or lname:
                    cstat = updateStatus()
                    if cstat:
                        last_statuss = cstat
                    if lname:
                        pip_activated = 1
            # if there are finishid calls (unanswered) - this is not pip activation
            if last_statuss == 'end' or last_statuss == 'error' or last_statuss == '':
                pip_activated = 0
            else:
                if pip_activated == 1:
                    pip_activated = 2
                    xlog('PIP_ACTIVATED! %s' %last_statuss)
        else:
            xlog('STANDALONE!!!')
            os.system(PHONE_TERMINATE)
            phoneInit()

        phoneLimitCodecs()
        if sys.modules[ "__main__" ].FIRST_RUN:
            phone("quit")
            #settings = xbmcaddon.Addon(__scriptId__)
            #settings.openSettings()
            #del settings
	    __settings__.openSettings()
            phoneInit()
            phoneLimitCodecs()

    def onClick( self, controlId ):
        global pb
        global CALL_STATUS
        global list_type
        global selected_list_item
        global NEED2CALL
        xlog("(onClick)CONTROL ID =  "+str(controlId))

        # change SELF VIEW pos
        if controlId == self.control_btn_self_view_id:
            if xbmc.getCondVisibility("[Control.IsVisible(%s)]" % self.control_btn_self_view_id):
                self.changeSelfViewPos()

        # change video size
        if controlId == self.control_btn_scaler_id:
            self.changeViewSize()

        # Click on contact (Call to contact from list)
        if controlId == self.control_list_contacts_id:
            self.item = self.list_contacts.getSelectedItem()
            target = ''
            if list_type == 'contacts':
                for row in pb:
                    if row[0] == self.item.getLabel():
                        target = row[1]
            else:
                target = self.item.getLabel()

            if target and canCall(target):
                # LP_WIN.label_status.setLabel("Status: Dialing...")
                phoneCall(target)

        # switch to recent call list
        if controlId == self.control_btn_recent_id:
            if list_type != 'recent':
                self.list_contacts.reset()
                self.list_contacts.addItems(last_calls)
                list_type = 'recent'
                self.btn_recent.setLabel('   Recent', 'font14', '0xFFFFFFFF')
                self.btn_contacts.setLabel('  Contacts', 'font12', '0xFFAAAAAA')

        # switch to contacts call list
        if controlId == self.control_btn_contacts_id:
            if list_type != 'contacts':
                self.list_contacts.reset()
                for row in pb:
                    self.list_contacts.addItem(row[0])
                list_type = 'contacts'
                self.btn_recent.setLabel('   Recent', 'font12', '0xFFAAAAAA')
                self.btn_contacts.setLabel('  Contacts', 'font14', '0xFFFFFFFF')

        # close
        if controlId == self.control_btn_close_id:
            phoneTerminate()

        # Show Call To invite and perform call
        if controlId == self.control_btn_call_to_id:
            self.text = self.get_input("")
            if len(self.text) > 2:
                phoneCall(self.text)
            del(self.text)

        # Hang UP / Red button / Terminate
        if controlId == self.control_btn_hangup_id:
            phoneTerminate()

        # Answer incoming call / Green button
        if controlId == self.control_btn_answer_id:
            if CALL_STATUS == 'ringing':
                phone("answer")
            else:
                val = self.message_yesno("Redial", "Call to " + placed[0] + " ?")
                if val:
                    phoneCall(placed[0])

        # Open settings window
        if controlId == self.control_btn_settings_id:
            soundcards = phonePopen('soundcard list')
            phone("window hide")
            phone("quit")
            capture_list = ''
            playback_list = ''
            for i in soundcards:
                if i.find('layback device') > 0:
                    is_playback = 1
                    is_capture = 0
                elif i.find('apture device') > 0:
                    is_playback = 0
                    is_capture = 1
                elif is_playback == 1:
                    playback_list += i.strip()[2:] + '|'
                elif is_capture == 1:
                    capture_list += i.strip()[2:] + '|'

            playback_list = '    <setting id="playback_list" type="enum" label="30312" values="%s" default="0" />\n' % (playback_list)
            capture_list = '    <setting id="capture_list" type="enum" label="30311" values="%s" default="0" />\n' % (capture_list)

            f = open(__cwd__+'/resources'+'/settings.xml', 'r')
            settings = f.readlines()
            f.close()
            f = open(__cwd__+'/resources'+'/settings.xml', 'w')
            for i in settings:
                if i.find("capture_list") > 0:
                    f.write(capture_list)
                elif i.find("playback_list") > 0:
                    f.write(playback_list)
                else:
                    f.write(i)
            f.close()
            #settings = xbmcaddon.Addon(__scriptId__)
            #settings.openSettings()
            #del settings
            #__settings__ = xbmcaddon.Addon(id=__scriptId__)
	    __settings__.openSettings()
            phoneInit()
            phoneLimitCodecs()

        # Show add contact dialog
        if controlId == self.control_btn_add_contact_id:
            phone("pwindow hide")
            selected_list_item = 0
            contact_win = AddContact( "add_contact.xml" , __cwd__, "Default")
            contact_win.doModal()
            del contact_win
            phone("pwindow show")

        # Show context window (right click on contact)
        if controlId == self.control_btn_context_id:
            if canCall(''):
                if list_type == 'contacts':
                    selected_list_item = self.list_contacts.getSelectedItem().getLabel()
                    phone("pwindow hide")
                    contact_action = ContactAction( "action.xml" , __cwd__, "Default")
                    contact_action.doModal()
                    del contact_action
                    phone("pwindow show")
                self.setFocus(self.list_contacts)
                if NEED2CALL and canCall(NEED2CALL):
                    phoneCall(NEED2CALL)

        # increase brightness
        if controlId == self.control_btn_bright_plus_id:
            GuiControl.setBrightness(10, 0)

        # decrease brightness
        if controlId == self.control_btn_bright_minus_id:
            GuiControl.setBrightness(-10, 0)

    ##--------Virtual keyboard --------##
    def get_input(self, title):
        phone("pwindow hide")
        returned_text = ""
        keyboard = xbmc.Keyboard(title)
        keyboard.doModal()
        if keyboard.isConfirmed():
            returned_text = keyboard.getText()
        phone("pwindow show")
        return returned_text

    ##--------Dialog select ----------##
    def message_select(self, name, message):
        phone("pwindow hide")
        self.dialog = xbmcgui.Dialog()
        self.ret = self.dialog.select(name, message)
        phone("pwindow show")
        return self.ret

    ##--------Dialog Yes or No ----------##
    def message_yesno(self, name, message):
        phone("pwindow hide")
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno(name, message)
        phone("pwindow show")
        return ret

    def changeSelfViewPos(self):
        global SELF_VIEW_POS
        global SELF_VIEWS
        if SELF_VIEW_POS < 4:
            SELF_VIEW_POS += 1
        else:
            SELF_VIEW_POS = 0
        phone("selfview show %s" % (SELF_VIEWS[SELF_VIEW_POS]))

    def changeViewSize(self):
        global VIEW_SIZE
        global VIEW_SIZES
        if VIEW_SIZE < 4:
            VIEW_SIZE += 1
        else:
            VIEW_SIZE = 0
        phoneResize(VIEW_SIZES[VIEW_SIZE][0], VIEW_SIZES[VIEW_SIZE][1])
        phone("window hide")
        phone("window show")

    ##--------- Focus -----------##
    def onFocus( self, controlId ):
        pass

    ##--------- Button Actions ------##
    def onAction( self, action ):
        ##----------------ESC Button ---------------------##
        if action.getId() == 10:
            phoneTerminate()

        if action.getId() == SELFVIEW_KEYCODE and __is_full_ver__:
            self.changeSelfViewPos()

        if action.getId() == SIZE_KEYCODE and __is_full_ver__:
            self.changeViewSize()


#class EventHandler(pyinotify.ProcessEvent):
#    def process_IN_MODIFY(self, event):
#        checkLogFile(self, event)

class ContactAction(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.control_btn_close_id = 301
        self.control_btn_call_id = 303
        self.control_btn_edit_id = 304
        self.control_btn_delete_id = 305
        self.control_label_name_id = 311
        self.control_label_uri_id = 312
        xbmcgui.WindowXML.__init__(self)

    def onInit(self):
        global pb
        self.btn_close = self.getControl(self.control_btn_close_id)
        self.btn_edit = self.getControl(self.control_btn_edit_id)
        self.btn_delete = self.getControl(self.control_btn_delete_id)
        self.label_name = self.getControl(self.control_label_name_id)
        self.label_uri = self.getControl(self.control_label_uri_id)
        item = LP_WIN.list_contacts.getSelectedItem()
        self.label_name.setLabel(item.getLabel())
        for row in pb:
            if row[0] == item.getLabel():
                self.label_uri.setLabel(row[1])

    def onClick(self, controlId):
        global pb
        global selected_list_item
        global NEED2CALL
        if controlId == self.control_btn_close_id:
            selected_list_item = 0
            self.close()

        if controlId == self.control_btn_call_id:
            item = LP_WIN.list_contacts.getSelectedItem()
            if list_type == 'contacts':
                for row in pb:
                    if row[0] == item.getLabel():
                        NEED2CALL = row[1]
            self.close()

        if controlId == self.control_btn_edit_id:
            contact_win = AddContact("add_contact.xml" , __cwd__, "Default")
            contact_win.doModal()
            del contact_win
            self.close()

        if controlId == self.control_btn_delete_id:
            if list_type == 'contacts' and selected_list_item:
                pbb = []
                for row in pb:
                    if row[0] != selected_list_item:
                        pbb.append(row)
                pb = pbb
                phoneBookSet(pb)
                LP_WIN.list_contacts.reset()
                for row in pb:
                    LP_WIN.list_contacts.addItem(row[0])
            self.close()

    def onAction(self, action):
        if action.getId() == 10:
            self.close()

class AddContact(xbmcgui.WindowXMLDialog):

    def __init__( self, *args, **kwargs ):
        self.control_btn_close_id = 201
        self.control_win_label_id = 202
        self.control_btn_name_id = 206
        self.control_btn_uri_id = 208
        self.control_btn_save_id = 220
        self.control_btn_cancel_id = 221
        xbmcgui.WindowXML.__init__(self)

    def onInit(self):
        global selected_list_item
        global pb
        self.win_label = self.getControl(self.control_win_label_id)
        self.btn_close = self.getControl(self.control_btn_close_id)
        self.btn_name = self.getControl(self.control_btn_name_id)
        self.btn_uri = self.getControl(self.control_btn_uri_id)
        self.btn_save = self.getControl(self.control_btn_save_id)
        self.btn_cancel = self.getControl(self.control_btn_cancel_id)
        if selected_list_item:
            self.win_label.setLabel("Edit contact")
            self.btn_name.setLabel(selected_list_item)
            for row in pb:
                if row[0] == selected_list_item:
                    self.btn_uri.setLabel(row[1])

    def onClick(self, controlId):
        global pb
        global selected_list_item
        if controlId == self.control_btn_close_id or controlId == self.control_btn_cancel_id:
            selected_list_item = 0
            self.close()

        if controlId == self.control_btn_name_id:
            self.inputed_text = self.get_input('')
            if len(self.inputed_text) > 0:
                self.btn_name.setLabel(self.inputed_text)

        if controlId == self.control_btn_uri_id:
            self.inputed_text = self.get_input('')
            if len(self.inputed_text) > 0:
                self.btn_uri.setLabel(self.inputed_text)

        if controlId == self.control_btn_save_id:
            self.name = self.btn_name.getLabel()
            self.number = self.btn_uri.getLabel()
            if len(self.name) > 1  and len(self.number) > 3:
                if selected_list_item:
                    pbb = []
                    for row in pb:
                        if row[0] == selected_list_item:
                            pbb.append([self.name, self.number])
                        else:
                            pbb.append(row)
                    pb = pbb
                else:
                    pb.append([self.name, self.number])
                phoneBookSet(pb)

                if list_type == 'contacts':
                    LP_WIN.list_contacts.reset()
                    for row in pb:
                        LP_WIN.list_contacts.addItem(row[0])
            selected_list_item = 0
            self.close()

    def onFocus(self, controlId):
        if controlId == self.control_btn_name_id:
            self.inputed_text = self.get_input(self.btn_name.getLabel())
            if len(self.inputed_text) > 0:
                self.btn_name.setLabel(self.inputed_text)

        if controlId == self.control_btn_uri_id:
            self.inputed_text = self.get_input(self.btn_uri.getLabel())
            if len(self.inputed_text) > 0:
                self.btn_uri.setLabel(self.inputed_text)

    def onAction(self, action):
        if action.getId() == 10:
            self.close()

    def get_input(self, title):
        returned_text = ""
        keyboard = xbmc.Keyboard(title)
        keyboard.doModal()
        if keyboard.isConfirmed():
            returned_text = keyboard.getText()
        return returned_text

def phoneResize(w, h):
    return phone('pwindow size '+ str(w) + " " + str(h))

def phone(cmd):
    cmd = cmd.replace("pwindow", "window")
    xlog("Phone:" + cmd)
    return os.system(PHONE_PATH + " generic '%s'" % (cmd))

def phonePopen(cmd, raw = 0):
    std = sub.Popen(PHONE_PATH + " generic '" + cmd + "'", shell=True, stdout=sub.PIPE).stdout
    if raw:
        return std
    return std.readlines()

def phoneLimitCodecs():
    vcodec_priority = int(__settings__.getSetting("vcodec_priority"))
    if vcodec_priority == 1:
        vcodecs = ['VP8']
    elif vcodec_priority == 2:
        vcodecs = ['H264', 'VP8']
    else:
        vcodecs = ['H264']
    lines = phonePopen('vcodec list')
    cindex = 0
    for line in lines:
        dis = 1
        for vcodec in vcodecs:
            if line.find(vcodec) > 0:
                dis = 0
        if dis and line.find('enabled') > 0:
            phone("vcodec disable %s" % (cindex))
        elif not dis and line.find('disabled') > 0:
            phone("vcodec enable %s" % (cindex))
        cindex += 1

    acodecs = []
    if __settings__.getSetting("acodec_speex") == 'true':
        acodecs.append('speex (16')
    if __settings__.getSetting("acodec_pcma") == 'true':
        acodecs.append('PCMA')
    if __settings__.getSetting("acodec_pcmu") == 'true':
        acodecs.append('PCMU')
    if __settings__.getSetting("acodec_g722") == 'true':
        acodecs.append('G722')

    lines = phonePopen('codec list')
    cindex = 0
    for line in lines:
        dis = 1
        for acodec in acodecs:
            if line.find(acodec) > 0:
                dis = 0
        if dis and line.find('enabled') > 0:
            phone("codec disable %s" % (cindex))
        elif not dis and line.find('disabled') > 0:
            phone("codec enable %s" % (cindex))
        cindex += 1

def phoneCall(target):
    phone("call " + target)
    CALL_STATUS = 'calling'
    GuiControl.fixUpDown(False, True, 'calling', False)
    LP_WIN.setFocus(LP_WIN.btn_hangup)
    IS_CALLING = 1

def phoneTerminate():
    global placed
    global recieved
    global last_calls
    global last_try_exit
    global last_try_exit_cnt
    global checker
    global list_type
    global last_log_pos
    global pip_activated
    global QUIT
    IS_CALLING = 0
    tpass = (time.time() - last_try_exit)
    if tpass < 5:
        last_try_exit_cnt += 1
    else:
        last_try_exit_cnt = 0

    last_try_exit = time.time()

    xlog("Try to quit: %s, %s / %s / %s" % (CALL_STATUS, tpass, last_try_exit_cnt, last_try_exit))
    __settings__ = sys.modules[ "__main__" ].__settings__
    if last_try_exit_cnt < 2 and (CALL_STATUS == 'calling' or CALL_STATUS == 'ringing' or CALL_STATUS == 'active'):
        phone("terminate all")
        phone("window hide")
        QUIT = 1
        checker.join()
        if pip_activated == 2:
            xlog('!!PIP_DE-ACTIVATED!!!')

	    # may 20140410
	    #phoneResize(176, 144) #  % (VIEW_SIZES[0][0], VIEW_SIZES[0][1])
	    xbmc.executebuiltin('PlayerControl(play)')
	    #xbmc.executebuiltin('Action(select)')
	    time.sleep(1)

            #try:
            #    notifier.stop()
            #except OSError:
            #    xlog('Cant stop notifier')
		
            setLastLogPos(last_log_pos)
            setGuiActive(0)
            phone("mute")
            time.sleep(1)
            LP_WIN.close()
        else:
            # phoneResize(RIGHT_SHIFT, DOWN_SHIFT)
            xlog('NON PIP :(')
            phoneResize(VIEW_SIZES[2][0], VIEW_SIZES[2][1])
            phone("window show")
            GuiControl.fixUpDown(False, False, 'end', True)
            time.sleep(1)
            placed, recieved, last_calls = parsing(PHONE_CONFIG)
            if list_type == 'recent':
                LP_WIN.list_contacts.reset()
                LP_WIN.list_contacts.addItems(last_calls)
    else:
        phone("mute")
        if not __settings__.getSetting("pip_active"):
            phone("proxy remove 0")
            phone("quit")
        else:
            phoneResize(176, 144) #  % (VIEW_SIZES[0][0], VIEW_SIZES[0][1])
            # phone("terminate all")
            phone("window hide")
            setLastLogPos(last_log_pos)
            #QUIT = 1
            #checker.join()

#        if notifier:
#            try:
#                notifier.stop()
#            except:
#                xlog('Cant stop notifier')
        setGuiActive(0)
        time.sleep(1)
        if not __settings__.getSetting("pip_active"):
            os.system(PHONE_TERMINATE)
        if LP_WIN:
            LP_WIN.close()

def canCall(target):
    active_calls = 0
    for id in CALLIDS:
        status = CALLIDS[id]['status']
        # we have unanswered call
        if status == 'calling' or status == 'ringing':
            return False
        # we have active sesstion with target
        if target and CALLIDS[id]['number'] == target and status == 'active':
            return False
        if status == 'active':
            active_calls += 1
            # MAX CALLS limit reached
            if active_calls > MAX_CALLS:
                return False
    return True

def checkLogFile(logdata):
    #logdata = logGetData(the_event.pathname)
    ldss = logdata.split("\n")
    for lds in ldss:
        call_id = logSetCallId(lds)
        lname = logSetName(lds)
        if call_id or lname:
             updateStatus()

    return ''

    # out:
    # 1.phoneCallIdle,
    # 2.phoneCallOutgoingInit,
    # 3.phoneCallOutgoingProgress,
    # 4.phoneCallOutgoingRinging,
    # 5.phoneCallConnected,
    # 6.phoneCallStreamsRunning,
    # 7.phoneCallEnd,
    # 8.phoneCallReleased,
    # in:
    # 1.phoneCallIdle,
    # 2.phoneCallIncomingReceived,
    # 3.phoneCallConnected,
    # 4.phoneCallStreamsRunning,
    # 5.phoneCallEnd,
    # 6.phoneCallReleased,
    # Need to detect:
    # - calling (show window with Caller name + Answer / Hangup)
    # - connected (show contact name + Hangup button near cam win)
    # - disconnected (hide Hangup button)

def updateStatus():
    global CALL_STATUS
    global pip_activated
    remains_calls = MAX_CALLS
    b_answer = False
    b_hangup = False
    active = '';
    cur_status = 'active'
    can_call = True
    for id in CALLIDS:
        status = CALLIDS[id]['status']
        if status == 'ringing':
            b_answer = True
        if status == 'calling' or status == 'active' or status == 'ringing':
            remains_calls -= 1
            b_hangup = True
            if active:
                active += ",\n"
            active += CALLIDS[id]['name']
        if status == 'calling' or status == 'ringing':
            cur_status = status
            can_call = False

    if remains_calls < 1:
        can_call = False

    if not b_answer and not b_hangup:
        cur_status = 'end'
        phone("selfview hide")
    else:
        phone("selfview show %s" % (SELF_VIEWS[SELF_VIEW_POS]))

    showStatus(cur_status, active)
    GuiControl.fixUpDown(b_answer, b_hangup, cur_status, can_call)

    xlog('Changed status from %s to %s' % (CALL_STATUS, cur_status))
    CALL_STATUS = cur_status

    for call_id in CALLIDS:
        xlog("Cur: %s, status for %s: %s %s %s" % (CALL_STATUS, call_id, CALLIDS[call_id]['status'], CALLIDS[call_id]['name'], CALLIDS[call_id]['lstatus']))

    if pip_activated == 2 and not b_answer and not b_hangup:
        phoneTerminate()

    return cur_status

def logSetName(lds):
    global LAST_CALL_ID
    cont = ''
    cname = ''

    if not LAST_CALL_ID:
        return ''
    status = CALLIDS[LAST_CALL_ID]['status']
    if (status == 'calling' or (status == 'active'  and IS_CALLING)) and 'To: <' in lds:
        cont = re.search('To: <sip:([^\r\n]+)>' ,lds)
    elif (status == 'calling' or (status == 'active'  and IS_CALLING)) and 'To: "' in lds:
        cont = re.search('To: "([^\r\n]+)"' ,lds)
    elif (status == 'ringing' or (status == 'active' and not IS_CALLING)) and 'From: <' in lds:
        cont = re.search('From: <sip:([^\r\n]+)>' ,lds)
    elif (status == 'ringing' or (status == 'active' and not IS_CALLING)) and 'From: "' in lds:
        cont = re.search('From: "([^\r\n]+)"' ,lds)

    if cont:
        cname = cont.group(1)
        xlog("CALL_ID: %s, Name: %s" % (LAST_CALL_ID, cname))

    if cname and LAST_CALL_ID and not CALLIDS[LAST_CALL_ID]['name']:
        CALLIDS[LAST_CALL_ID]['name'] = cname
        CALLIDS[LAST_CALL_ID]['number'] = cname
        return cname

    return ''

def logSetCallId(lds):
    global LAST_CALL_ID
    global IS_CALLING
    call_status = ''
    call_id = ''
    lstatus = ''
    status_list = {
        'phoneCallOutgoingInit' : 'calling',
        'phoneCallIncomingReceived' : 'ringing',
        'phoneCallStreamsRunning' : 'active',
        'phoneCallConnected' : 'active',
        'phoneCallReleased' : 'end',
        'phoneCallEnd' : 'end',
        'phoneCallError' : 'error'
    }
    if 'moving from state' in lds:
        fcall_ids = re.findall('Call 0x([0-9a-f]+): moving', lds)
        for fcall_id in fcall_ids:
            if fcall_id:
                call_id = fcall_id
                for sfull_name in status_list:
                    if sfull_name in lds:
                        call_status = status_list[sfull_name]
                        lstatus = sfull_name
    if call_status == 'end' or call_status == 'error':
        IS_CALLING = 0
    if call_id and call_id not in CALLIDS:
        CALLIDS[call_id] = {'status' : '', 'name' : '', 'lstatus' : '', 'number' : ''}

    if call_status:
        CALLIDS[call_id]['status'] = call_status
        CALLIDS[call_id]['lstatus'] = lstatus
        xlog("CallID ID: %s  Status: %s (%s)" % (call_id, call_status, lstatus))

    if call_id:
        LAST_CALL_ID = call_id
        return call_id
    return 0

def logGetData(log_file):
    global last_log_pos
    fh = open(log_file, 'r')
    full_size = os.path.getsize(log_file)
    if (last_log_pos == 0) or ((full_size - last_log_pos) < 10):
        last_log_pos = full_size
        return ''

    fh.seek(last_log_pos)
    log_data = fh.read(full_size - last_log_pos)
    last_log_pos = full_size
    return log_data

def xlog(msg):
    xbmc.log("##### [%s] - Debug msg: %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

def showStatus(cstatus, contactn):
    vstats = {'error':'Unknown error', 'end':'', 'active':'Connected to', 'ringing':'Incoming call from', 'calling':'Calling to'}
    LP_WIN.sttus.setText("%s %s" % (vstats[cstatus], contactn))

def phoneInit():
    global MAX_CALLS
    ##------------------Initialisation Settings----------------------##
    array = ["sip_port", "sip_tcp_port"]
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
    multimedia_size = __settings__.getSetting("multimedia_size")
    multimedia_auto = __settings__.getSetting("multimedia_auto")
    capture_device = __settings__.getSetting("capture_list")
    playback_device = __settings__.getSetting("playback_list")
    echo_cancel = __settings__.getSetting("echo_cancel")

    xlog("Mmedia-size -1 %s" % (multimedia_size))
    if multimedia_auto == "true":
        multimedia_size = GuiControl.checkResolution(HEIGHT, WIDTH)
    else:
        multimedia_size = ["1080p", "720p", "svga", "4cif", "vga", "ios-medium", "cif", "qvga", "qcif"][int(multimedia_size)]
    xlog("Mmedia-size -2 %s" % (multimedia_size))
    debug_level = __settings__.getSetting("debug_level")
    debug_level = int(debug_level) + 1

    ##----------------STARTING PHONE------------------------##
    auto_answer = '-a' if auto_answer == "true" else ''

    if debugging == "true":
        cmd = 'bash -c "' + PHONE_PATH + ' init -d %s %s -l %s -c %s"' % (debug_level, auto_answer, PHONE_LOG, PHONE_CONFIG)
    else:
        # need to enable debugger anyway, because status watcher uses phone log.
        cmd = 'bash -c "' + PHONE_PATH + ' init -d %s %s -l %s -c %s"' % (2, auto_answer, PHONE_LOG, PHONE_CONFIG)
        # cmd = 'bash -c "' + PHONE_PATH + ' init -V %s -c \'%s\'"' % (auto_answer, PHONE_CONFIG)

    xlog("Init string: " + cmd)
    os.system(cmd)
    time.sleep(1)
    # phoneResize(RIGHT_SHIFT, DOWN_SHIFT)
    if auto_register == "true":
        phone("register sip:%s@%s sip:%s %s" % (str(user), host, host, str(password)))

    ##-----------------Params from settings to phonec------------------------##
    phone("soundcard capture " + capture_device)
    phone("soundcard playback " + playback_device)
    phoneResize(VIEW_SIZES[2][0], VIEW_SIZES[2][1])
    phone("ports sip " + str(sip_port))
    array = ["sip_port", "sip_tcp_port"]
    if sip_protocol == array[0]:
        phone("param %s 0" %(array[1]))
    if sip_protocol == array[1]:
        phone("param %s 0" %(array[0]))
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

    if echo_cancel == "true":
        phone("ec on")
    else:
        phone("ec off")
    phone("webcam use 0")
    phone("webcam size " + multimedia_size)
    phone("selfview hide")
    phone("unmute")
    m_c = phonePopen('maxcalls')
    m_c = m_c.pop(0)
    if len(m_c) < 4 and int(m_c) > 0:
       MAX_CALLS = int(m_c)
    xlog('MAX_CALLS: %s' %(MAX_CALLS))
    phone("window show")

    brightness = __settings__.getSetting("brightness")
    GuiControl.setBrightness(0, brightness)
    xlog("SIP_PROTOCOL = %s SIP_PORT = %s DIRECT_CONNECTION = %s" % (sip_protocol, sip_port, direct_connection))
    # status_register = phonePopen('status register', 1).readline()
    # self.sttus.setText(status_register)

def phoneInitShort():
    global MAX_CALLS
    phoneResize(VIEW_SIZES[2][0], VIEW_SIZES[2][1])
    phone("selfview show %s" % (SELF_VIEWS[SELF_VIEW_POS]))
    phone("unmute")
    m_c = phonePopen('maxcalls')
    m_c = m_c.pop(0)
    if len(m_c) < 4 and int(m_c) > 0:
       MAX_CALLS = int(m_c)
    xlog('MAX_CALLS: %s' %(MAX_CALLS))

    #capture_device = __settings__.getSetting("capture_list")
    #playback_device = __settings__.getSetting("playback_list")
    #echo_cancel = __settings__.getSetting("echo_cancel")
    #multimedia_size = __settings__.getSetting("multimedia_size")
    #multimedia_auto = __settings__.getSetting("multimedia_auto")
    #if multimedia_auto == "true":
    #    multimedia_size = GuiControl.checkResolution(HEIGHT, WIDTH)
    #else:
    #    multimedia_size = ["1080p", "720p", "svga", "4cif", "vga", "ios-medium", "cif", "qvga", "qcif"][int(multimedia_size)]
    #phone("soundcard capture " + capture_device)
    #phone("soundcard playback " + playback_device)
    #if echo_cancel == "true":
    #    phone("ec on")
    #else:
    #    phone("ec off")
    #phone("webcam use 0")
    #phone("webcam size " + multimedia_size)
    phone("window show")
    brightness = __settings__.getSetting("brightness")
    GuiControl.setBrightness(0, brightness)

def phoneBookGet():
    try:
        f = open(PHONE_BOOK, "r+")
    except IOError:
        os.system("touch " + PHONE_BOOK)
        f = open(PHONE_BOOK, "r+")
        f.write("[]")
        f.seek(0)

    str_pb = f.read()
    str_pb = str_pb.replace("\n", "")
    str_pb = eval(str_pb)
    f.close()
    return str_pb

def phoneBookSet(pb):
    f = open(PHONE_BOOK, "w")
    str_pb = repr(pb)
    str_pb = str_pb.replace("], [", "], \n[")
    str_pb = str_pb.replace("[u'", "['")
    str_pb = str_pb.replace("', u'", "', '")
    f.write(str_pb)
    f.close()

def parsing(filename):
    config = ConfigParser.ConfigParser()
    config.read(filename)
    i = 0
    outgoing = []
    incoming = []
    out_inc = []
    while 1:
        try:
            a = config.get("call_log_"+str(i), "dir")
            if a == "0":
                a = config.get("call_log_"+str(i), "to")
                res = re.search(r"<.*?:([^;>]*)", a)
                if res.group(1) not in outgoing:
                    outgoing += [res.group(1)]
                if res.group(1) not in out_inc:
                    out_inc += [res.group(1)]
            else:
                a = config.get("call_log_"+str(i), "from")
                res = re.search(r"<.*?:([^;>]*)", a)
                if res.group(1) not in incoming:
                    incoming +=  [res.group(1)]
                if res.group(1) not in out_inc:
                    out_inc += [res.group(1)]
            i += 1
        except:
            return outgoing, incoming, out_inc[-10:][::-1]

def setGuiActive(is_active):
    # xbmcaddon.Addon('script.mcuphone_pip').setSetting("gui_active", is_active)
    if is_active:
        os.system("touch /home/" + SYSTEM_USER + "/mcu_gui")
    else:
        try:
            os.remove("/home/" + SYSTEM_USER + "/mcu_gui")
        except:
            xlog('Cant delete mcu_gui')

def getGuiActive():
    # return xbmcaddon.Addon('script.mcuphone_pip').getSetting("gui_active")
    if os.path.isfile("/home/" + SYSTEM_USER + "/mcu_gui"):
        return 1
    else:
        return 0

def getLastLogPos():
    pos = 101
    if os.path.isfile("/tmp/mcu_log_pos"):
        f = open("/tmp/mcu_log_pos", "r")
        pos = int(f.read())
        f.close()
    return pos

def setLastLogPos(pos):
    f = open("/tmp/mcu_log_pos", "w")
    f.write(str(pos))
    f.close()

pb = phoneBookGet()
placed, recieved, last_calls = parsing(PHONE_CONFIG)
cmd = str()

# 1 Сделать echotest
#    Добавить контакт внутри сети
#    отредактировать контакт
#    позвонить контакту
#    Проследить правильность зеленой и красной кнопок, строки статуса звонка
#    Удалить контакт
#    добавить ещё один контакт
# 2 Сделать echotest
#    Сделать звонок через Call to ЗА НАТ
#    проверить изменение размеров окна (Num 0)
#    проверить смену позиций self view (Num 1)
#    проверить изменение яркости
#    рассоединить
#    перезвонить через Recent
# 3 Настройки
#    ? регистрация на астериске
#    автоответ
#    ? работа через НАТ
#    измен качество видео (Multimedia->Choose video quality)
# 4 Перезайти
#    проверить наличие контакта и набранного номера

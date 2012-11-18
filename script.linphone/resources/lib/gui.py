# -*- coding: utf-8 -*-
# *
# *      Copyright (C) 2012 Postmet corp
# *      http://www.postmet.com
# *      Created by: Perepelyatnik Peter, Jermakovich Alexander <team@postmet.com>
# *
# *
# * zip script.linphone.zip script.linphone/* -r

import os, sys, ast
import xbmc
import xbmcgui
import time
import xbmcaddon
import ConfigParser
import re
import subprocess as sub
import pyinotify

##-----------GLOBAL VARIABLES AND CONSTANTS------------##
is_full_ver = 0
SYSTEM_USER = os.getenv("USER")
__scriptId__   = "script.linphone"
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__version__ = sys.modules[ "__main__" ].__version__
__settings__ = sys.modules[ "__main__" ].__settings__
__cwd__ = '/home/'+SYSTEM_USER+'/.xbmc/addons/script.linphone'
__language__ = __settings__.getLocalizedString
_  = sys.modules[ "__main__" ].__language__
RIGHT_SHIFT = 340
DOWN_SHIFT = 100

SIZE_KEYCODE = 58
SELFVIEW_KEYCODE = 59

WIDTH = int(xbmcgui.Window().getWidth())
HEIGHT = int(xbmcgui.Window().getHeight())
RIGHT_SHIFT = int(WIDTH * 350 / 1280)

PERCENT1 = ((HEIGHT - RIGHT_SHIFT) * 100) / HEIGHT
PERCENT2 = ((WIDTH - DOWN_SHIFT) * 100) / WIDTH
PERCENT = int((PERCENT1 + PERCENT2) / 2)

VIEW_SIZE = 4
SELF_VIEW_POS = 1

proport = float(WIDTH) / HEIGHT

if proport < 1.6:
    min_width = 800
    min_height = int(800 / proport)
else:
    min_width = int(500 * proport)
    min_height = 500

step = int((WIDTH - RIGHT_SHIFT - min_width) / 2)

VIEW_SIZES = [[], [], [], [], []]
VIEW_SIZES[0] = [min_width, min_height]
#VIEW_SIZES[1] = [WIDTH - RIGHT_SHIFT - step * 2, int((WIDTH - RIGHT_SHIFT - step * 2)/ proport)]
VIEW_SIZES[1] = [WIDTH - RIGHT_SHIFT - step    , int((WIDTH - RIGHT_SHIFT - step    )/ proport)]
VIEW_SIZES[2] = [WIDTH - RIGHT_SHIFT, int((WIDTH - RIGHT_SHIFT) / proport)]
VIEW_SIZES[3] = [WIDTH - RIGHT_SHIFT / 2, int((WIDTH - RIGHT_SHIFT / 2) / proport)]
VIEW_SIZES[4] = [WIDTH, HEIGHT]

SELF_VIEWS = [-1, 0, 3, 1, 2]

wm = pyinotify.WatchManager()
mask = pyinotify.IN_MODIFY  # watched events
last_log_pos = 0
calling_to = ''
call_status = ''
LP_WIN = ''
list_type = 'contacts'
selected_list_item = 0
last_try_exit = 0
last_try_exit_cnt = 0

##--------------------Main Window-----------------##
class GUI( xbmcgui.WindowXML ):
    def __init__( self, *args, **kwargs ):
        self.controlId = 0
    def onInit(self):
        global notifier
        global wm
        global mask
        global LP_WIN
        global list_type

        self.define_controls()
        notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
        notifier.start()

        os.system("touch /home/" + SYSTEM_USER + '/linphone.log')
        wm.add_watch('/home/' + SYSTEM_USER + '/linphone.log', mask)

        LP_WIN = self
        #self.slider.setPercent(PERCENT)
        self.btn_settings.setLabel(__language__(30501))
        #self.btn_recieved.setLabel(__language__(30503))1
        if list_type == 'contacts':
            for row in pb:
                self.list_contacts.addItem(row[0])
        else:
            self.list_contacts.addItems(last_calls)

        LP_WIN.btn_hangup.setVisible(False)
        LP_WIN.btn_answer.setVisible(False)
        fixUpDown(False, False)
        self.setFocus(self.btn_contacts)
        status_register = initLinphone()
        self.sttus.setText(status_register)

    def define_controls(self):
        global is_full_ver
        #control ids
        self.control_btn_close_id = 10
        self.control_btn_call_to_id = 5001
        self.control_btn_answer_id = 5002
        self.control_btn_contacts_id = 5006
        self.control_btn_hangup_id = 5004
        self.control_btn_settings_id = 5005
        self.control_btn_recent_id = 5003
        #self.control_btn_recieved_id = 5007 #2px
        self.control_list_contacts_id = 5008
        #self.control_slider_id = 5009
        self.control_btn_scaler_id = 5010
        self.control_btn_add_contact_id = 5011
        self.control_btn_self_view_id = 5012
        self.control_label_status_id = 5051
        self.control_btn_context_id = 5019

        #controls
        self.btn_hangup = self.getControl(self.control_btn_hangup_id)
        self.btn_contacts = self.getControl(self.control_btn_contacts_id)
        #self.slider = self.getControl(self.control_slider_id)
        self.btn_scaler = self.getControl(self.control_btn_scaler_id)
        self.btn_self_view = self.getControl(self.control_btn_self_view_id)
        self.btn_close = self.getControl(self.control_btn_close_id)
        self.btn_call_to = self.getControl(self.control_btn_call_to_id)
        self.btn_answer = self.getControl(self.control_btn_answer_id)
        self.btn_settings = self.getControl(self.control_btn_settings_id)
        self.btn_recent = self.getControl(self.control_btn_recent_id)
        #self.btn_recieved = self.getControl(self.control_btn_recieved_id)
        #self.list_contacts = self.getControl(self.control_list_contacts_id)
        self.btn_add_contact = self.getControl(self.control_btn_add_contact_id)
        self.label_status = self.getControl(self.control_label_status_id)
        self.btn_context = self.getControl(self.control_btn_context_id)

        list_top_pos = int(HEIGHT / 720) + 90

        self.addControl(xbmcgui.ControlImage(970, list_top_pos - 3, 306, 306, __cwd__ + '/resources/skins/Default/media/list_bg.png'))
        self.list_contacts = xbmcgui.ControlList(973, list_top_pos, 300, 330, font = 'font12', selectedColor = "0xFF000000", textColor = '0xFFFFFFFF', buttonTexture = 'button-nofocus.png', buttonFocusTexture = 'button-focus.png', itemHeight = 25, space = 2)
        self.addControl(self.list_contacts)
        self.control_list_contacts_id = self.list_contacts.getId()

        self.list_contacts.controlUp(self.btn_contacts)
        self.list_contacts.controlDown(self.btn_call_to)
        self.list_contacts.controlLeft(self.btn_contacts)
        self.list_contacts.controlRight(self.btn_context)

        if is_full_ver > 0:
            self.btn_scaler.setVisible(True)
            self.btn_self_view.setVisible(True)
        else:
            self.btn_scaler.setVisible(False)
            self.btn_self_view.setVisible(False)
        self.btn_recent.controlDown(self.list_contacts)
        self.btn_contacts.controlDown(self.list_contacts)
        self.btn_call_to.controlUp(self.list_contacts)

        self.sttus = xbmcgui.ControlTextBox(973, 460, 300, 200, textColor='0xFF0DD00')
        self.addControl(self.sttus)
        self.sttus.setText("H:" + str(HEIGHT) + " W:" + str(WIDTH))

    ##--------- End Script -----------##
    def exit_script( self, action=None ):
        self.action = action
        self.close()

    def onClick( self, controlId ):
        global pb
        global PERCENT
        global calling_to
        global call_status
        global list_type
        global selected_list_item
        global current_name
        xlog("(onClick)CONTROL ID =  "+str(controlId))

        if controlId == self.control_btn_self_view_id:
            self.changeSelfViewPos()

        if controlId == self.control_btn_scaler_id:
            self.changeViewSize()

        #if controlId == self.control_slider_id:
        #    prev_percent = PERCENT
        #    PERCENT = int(self.slider.getPercent())
        #    height = int((PERCENT * HEIGHT) / 100.0)
        #    width = int((PERCENT * WIDTH) / 100.0)
        #    if width < 800 or height < 500:
        #        self.slider.setPercent(prev_percent)
        #    else:
        #        xlog("HEIGHT = %s, WIDTH = %s" % (height, width))
        #        linphoneGeneric("pwindow size %s %s" % (width, height) )
        #        linphoneGeneric("scale size %s %s" % (width, height) )

        if controlId == self.control_list_contacts_id:
            self.item = self.list_contacts.getSelectedItem()
            LP_WIN.label_status.setLabel("Status: Dialing...")
            if list_type == 'contacts':
                for row in pb:
                    if row[0] == self.item.getLabel():
                        linphoneCall(row[1])
            else:
                linphoneCall(self.item.getLabel())

        if controlId == self.control_btn_recent_id:
            if list_type != 'recent':
                self.list_contacts.reset()
                self.list_contacts.addItems(last_calls)
                list_type = 'recent'
                self.btn_recent.setLabel('   Recent', 'font14', '0xFFFFFFFF')
                self.btn_contacts.setLabel('  Contacts', 'font12', '0xFFAAAAAA')

        if controlId == self.control_btn_contacts_id:
            if list_type != 'contacts':
                self.list_contacts.reset()
                for row in pb:
                    self.list_contacts.addItem(row[0])
                list_type = 'contacts'
                self.btn_recent.setLabel('   Recent', 'font12', '0xFFAAAAAA')
                self.btn_contacts.setLabel('  Contacts', 'font14', '0xFFFFFFFF')

        if controlId == self.control_btn_close_id:
            linphoneTerminate()

        if controlId == self.control_btn_call_to_id:
            self.text = self.get_input("")
            if len(self.text) > 2:
                linphoneCall(self.text)
            del(self.text)

        if controlId == self.control_btn_hangup_id:
            linphoneTerminate()

        if controlId == self.control_btn_answer_id:
            if call_status == 'ringing':
                linphoneGeneric("answer")
            else:
                val = self.message_yesno("Redial", "Call to " + placed[0] + " ?")
                if val:
                    linphoneCall(placed[0])

        if controlId == self.control_btn_settings_id:
            linphoneGeneric("pwindow hide")
            settings = xbmcaddon.Addon(__scriptId__)
            settings.openSettings()
            del settings
            #os.system("cp /home/"+SYSTEM_USER+"/.linphonerc /home/"+SYSTEM_USER+"/.linphonerc2")
            linphoneGeneric("quit")
            multimedia_size = __settings__.getSetting("multimedia_size")
            multimedia_size = ["1080p", "720p", "svga", "4cif", "vga", "ios-medium", "cif", "qvga", "qcif"][int(multimedia_size)]
            xlog("M-media Size = %s" % multimedia_size)
            #linphoneGeneric("vsize " + multimedia_size)
            initLinphone()
        if controlId == self.control_btn_add_contact_id:
            linphoneGeneric("pwindow hide")
            current_name = ''
            selected_list_item = 0
            contact_win = AddContact( "add_contact.xml" , __cwd__, "Default")
            contact_win.doModal()
            del contact_win
            linphoneGeneric("pwindow show")

        if controlId == self.control_btn_context_id:
            if list_type == 'contacts':
                selected_list_item = self.list_contacts.getSelectedItem().getLabel()
                linphoneGeneric("pwindow hide")
                contact_action = ContactAction( "action.xml" , __cwd__, "Default")
                contact_action.doModal()
                del contact_action
                linphoneGeneric("pwindow show")
            self.setFocus(self.list_contacts)

    ##--------Virtual keyboard --------##
    def get_input(self, title):
        linphoneGeneric("pwindow hide")
        returned_text = ""
        keyboard = xbmc.Keyboard(title)
        keyboard.doModal()
        if keyboard.isConfirmed():
            returned_text = keyboard.getText()
        linphoneGeneric("pwindow show")
        return returned_text

    ##--------Dialog select ----------##
    def message_select(self, name, message):
        linphoneGeneric("pwindow hide")
        self.dialog = xbmcgui.Dialog()
        self.ret = self.dialog.select(name, message)
        linphoneGeneric("pwindow show")
        return self.ret

    ##--------Dialog Yes or No ----------##
    def message_yesno(self, name, message):
        linphoneGeneric("pwindow hide")
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno(name, message)
        linphoneGeneric("pwindow show")
        return ret

    def changeSelfViewPos(self):
        global SELF_VIEW_POS
        global SELF_VIEWS
        if SELF_VIEW_POS < 4:
            SELF_VIEW_POS = SELF_VIEW_POS + 1;
        else:
            SELF_VIEW_POS = 0
        linphoneGeneric("pwindow selfview %s" % (SELF_VIEWS[SELF_VIEW_POS]))

    def changeViewSize(self):
        global VIEW_SIZE
        global VIEW_SIZES
        if VIEW_SIZE < 4:
            VIEW_SIZE = VIEW_SIZE + 1
        else:
            VIEW_SIZE = 0
        width = VIEW_SIZES[VIEW_SIZE][0]
        height = VIEW_SIZES[VIEW_SIZE][1]
        xlog("SCALER %s, WIDTH = %s, HEIGHT = %s" % (VIEW_SIZE, width, height))
        linphoneGeneric("pwindow size %s %s" % (width, height) )
        linphoneGeneric("scale size %s %s" % (width, height) )

    ##--------- Focus -----------##
    def onFocus( self, controlId ):
        pass

    ##--------- Button Actions ------##
    def onAction( self, action ):
        ##----------------ESC Button ---------------------##
        if action.getId() == 10:
            linphoneTerminate()

        if action.getId() == SELFVIEW_KEYCODE and is_full_ver:
            self.changeSelfViewPos()

        if action.getId() == SIZE_KEYCODE and is_full_ver:
            self.changeViewSize()


class EventHandler(pyinotify.ProcessEvent):
    def process_IN_MODIFY(self, event):
        global LP_WIN
        global notifiers
        global calling_to
        global call_status
        statuss = checkLogFile(self, event)
        if (len(statuss) > 2):
            call_status = statuss
            if statuss == 'calling':
                statuss = statuss + ' ' + calling_to
            LP_WIN.label_status.setLabel("Status: " + statuss + ".")

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
        global current_name
        global selected_list_item
        if controlId == self.control_btn_close_id:
            selected_list_item = 0
            current_name = ''
            self.close()

        if controlId == self.control_btn_call_id:
            item = LP_WIN.list_contacts.getSelectedItem()
            if list_type == 'contacts':
                for row in pb:
                    if row[0] == item.getLabel():
                        self.label_uri.setLabel(row[1])
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
                set_phone_book(pb)
                LP_WIN.list_contacts.reset()
                for row in pb:
                    LP_WIN.list_contacts.addItem(row[0])
            self.close()

    def onAction(self, action):
        if action.getId() == 10:
            self.close()

class AddContact(xbmcgui.WindowXMLDialog):
    global current_name

    def __init__( self, *args, **kwargs ):
        self.control_btn_close_id = 201
        self.control_win_label_id = 202
        self.control_btn_name_id = 206
        self.control_btn_uri_id = 208
        self.control_btn_save_id = 220
        self.control_btn_cancel_id = 221
        xbmcgui.WindowXML.__init__(self)

    def onInit(self):
        global current_name
        global selected_list_item
        self.win_label = self.getControl(self.control_win_label_id)
        self.btn_close = self.getControl(self.control_btn_close_id)
        self.btn_name = self.getControl(self.control_btn_name_id)
        self.btn_uri = self.getControl(self.control_btn_uri_id)
        self.btn_save = self.getControl(self.control_btn_save_id)
        self.btn_cancel = self.getControl(self.control_btn_cancel_id)
        if selected_list_item:
            self.win_label.setLabel("Edit contact")
            self.btn_name.setLabel(selected_list_item)
            current_name = selected_list_item
            for row in pb:
                if row[0] == selected_list_item:
                    self.btn_uri.setLabel(row[1])

    def onClick(self, controlId):
        global pb
        global current_name
        global selected_list_item
        if controlId == self.control_btn_close_id or controlId == self.control_btn_cancel_id:
            selected_list_item = 0
            current_name = ''
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
                if selected_list_item and current_name != self.name:
                    pbb = []
                    for row in pb:
                        if row[0] != current_name:
                            pbb.append(row)
                    pb = pbb
                pb.append([self.name, self.number])
                set_phone_book(pb)
                if list_type == 'contacts':
                    LP_WIN.list_contacts.reset()
                    for row in pb:
                        LP_WIN.list_contacts.addItem(row[0])
            selected_list_item = 0
            current_name = ''
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

def linphoneResize(w, h):
    return linphoneGeneric('pwindow size '+ str(WIDTH - w) + " " + str(HEIGHT - h))

def linphoneGeneric(cmd):
    return linphonecsh("generic '%s'" % (cmd))

def linphonecsh(cmd):
    xlog(cmd)
    return os.system("/usr/local/bin/linphonecsh " + cmd)

def limitLinphonecCodecs():
    lines = sub.Popen("linphonecsh generic 'vcodec list'", shell=True, stdout=sub.PIPE).stdout.readlines()
    cindex = 0
    for line in lines:
        if 'H264' not in line and 'enabled' in line:
            linphoneGeneric("vcodec disable %s" % (cindex))
        cindex = cindex + 1

    lines = sub.Popen("linphonecsh generic 'codec list'", shell=True, stdout=sub.PIPE).stdout.readlines()
    cindex = 0
    for line in lines:
        if 'PCMU' not in line and 'PCMA' not in line and 'enabled' in line:
            linphoneGeneric("codec disable %s" % (cindex))
        cindex = cindex + 1

def linphoneCall(target):
    global calling_to
    global call_status
    global LP_WIN
    calling_to = target
    linphonecsh("dial " + calling_to)
    call_status = 'calling'
    LP_WIN.btn_hangup.setVisible(True)
    LP_WIN.setFocus(LP_WIN.btn_hangup)
    fixUpDown(False, True)

def linphoneTerminate():
    global call_status
    global LP_WIN
    global placed
    global recieved
    global last_calls
    global last_try_exit
    global last_try_exit_cnt
    global notifier
    xbmc.log("##### [%s] - Debug msg: %s" % (__scriptname__, call_status),level=xbmc.LOGDEBUG )

    tpass = (time.time() - last_try_exit)
    if tpass < 5:
        last_try_exit_cnt += 1
    else:
        last_try_exit_cnt = 0

    last_try_exit = time.time()

    xbmc.log("##### [%s] - Try to quit: %s / %s / %s" % (__scriptname__, tpass, last_try_exit_cnt, last_try_exit),level=xbmc.LOGDEBUG )

    if last_try_exit_cnt < 2 and (call_status == 'calling' or call_status == 'ringing' or call_status == 'active'):
        # is_started = os.system("ps aux | grep linphonec")
        # if len(is_started) > 200:
        #    self.sttus.setText('EXITED')
        linphoneGeneric("terminate")
        linphoneResize(RIGHT_SHIFT, DOWN_SHIFT)
        LP_WIN.btn_hangup.setVisible(False)
        #LP_WIN.setFocus(LP_WIN.btn_hangup)
        fixUpDown(False, False)
        time.sleep(1)
        placed, recieved, last_calls = parsing('/home/%s/.linphonerc' % (SYSTEM_USER))
        #else:
        #    LP_WIN.btn_hangup.setVisible(False)
        #    LP_WIN.btn_answer.setVisible(False)
        #    self.sttus.setText('FORCED')
    else:
        linphoneGeneric("proxy remove 0")
        linphoneGeneric("quit")
        notifier.stop()
        time.sleep(1)
        # LP_WIN.exit_script()
        LP_WIN.close()
        #os.system('killall -9 xbmc.bin')


def checkLogFile(self, the_event):
    global last_log_pos
    log_file = the_event.pathname
    fh = open(log_file, 'r')
    full_size = os.path.getsize(log_file)
    if (last_log_pos == 0) or ((full_size - last_log_pos) < 10):
        last_log_pos = full_size
        return ''

    fh.seek(last_log_pos)
    logdata = fh.read(full_size - last_log_pos)
    call_status = ""
    last_log_pos = full_size
    if 'LinphoneCallOutgoingInit' in logdata:
        call_status = 'calling'
        LP_WIN.btn_answer.setVisible(False)
        LP_WIN.btn_hangup.setVisible(True)
        fixUpDown(False, True)
    if 'LinphoneCallConnected' in logdata:
        call_status = 'active'
        LP_WIN.btn_answer.setVisible(False)
        LP_WIN.btn_hangup.setVisible(True)
        fixUpDown(False, True)
    if 'LinphoneCallIncomingReceived' in logdata or '-CALL_NEW' in logdata:
        call_status = 'ringing'
        LP_WIN.btn_answer.setVisible(True)
        LP_WIN.btn_hangup.setVisible(True)
        fixUpDown(True, True)
    if 'LinphoneCallEnd' in logdata or '-CALL_CLOSED' in logdata:
        call_status = 'end'
        LP_WIN.btn_hangup.setVisible(False)
        LP_WIN.btn_answer.setVisible(False)
        fixUpDown(False, False)
    if 'LinphoneCallError' in logdata:
        call_status = 'error'
        LP_WIN.btn_hangup.setVisible(False)
        LP_WIN.btn_answer.setVisible(False)
        fixUpDown(False, False)

    return call_status
    # out:
    # 1.LinphoneCallIdle,
    # 2.LinphoneCallOutgoingInit,
    # 3.LinphoneCallOutgoingProgress,
    # 4.LinphoneCallOutgoingRinging,
    # 5.LinphoneCallConnected,
    # 6.LinphoneCallStreamsRunning,
    # 7.LinphoneCallEnd,
    # 8.LinphoneCallReleased,
    # in:
    # 1.LinphoneCallIdle,
    # 2.LinphoneCallIncomingReceived,
    # 3.LinphoneCallConnected,
    # 4.LinphoneCallStreamsRunning,
    # 5.LinphoneCallEnd,
    # 6.LinphoneCallReleased,
    # Need to detect:
    # - calling (show window with Caller name + Answer / Hangup)
    # - connected (show contact name + Hangup button near cam win)
    # - disconnected (hide Hangup button)

def xlog(msg):
    xbmc.log("##### [%s] - Debug msg: %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

def fixUpDown(answer, hangup):
    # 5001 - Call to, 5002 - Dial, 5004 - Hangup, 5005 - Settings, 5010 - Size, 5011 - Add contact, 5012 - SelfView

    #5001Down, 5011Down - answer:5002 / hangup:5004 / full:5010 / 5005
    if answer:
        b5001Down = 5002
    elif hangup:
        b5001Down = 5004
    elif is_full_ver:
        b5001Down = 5010
    else:
        b5001Down = 5005
    LP_WIN.getControl(5001).controlDown(LP_WIN.getControl(b5001Down))
    LP_WIN.getControl(5011).controlDown(LP_WIN.getControl(b5001Down))

    #5002Right, 5002Left - hangup:5004 / 5002
    #5004Right, 5004Left - answer:5002 / 5004
    if answer and hangup:
        LP_WIN.getControl(5002).controlRight(LP_WIN.getControl(5004)) # from Dial to Hangup
        LP_WIN.getControl(5004).controlLeft(LP_WIN.getControl(5002))
    elif answer:
        LP_WIN.getControl(5002).controlRight(LP_WIN.getControl(5002))
    elif hangup:
        LP_WIN.getControl(5004).controlLeft(LP_WIN.getControl(5004))

    #5002Down, 5004Down - full:5010 / 5005
    b500xDown = 5010 if is_full_ver else 5005
    if answer:
        LP_WIN.getControl(5002).controlDown(LP_WIN.getControl(b500xDown))
    if hangup:
        LP_WIN.getControl(5004).controlDown(LP_WIN.getControl(b500xDown))

    #5010Up - answer:5002 / hangup:5004 / 5001
    #5012Up - answer:5002 / hangup:5004 / 5001
    if answer:
        b500xUp = 5002
    elif hangup:
        b500xUp = 5004
    else:
        b500xUp = 5001
    LP_WIN.getControl(5010).controlUp(LP_WIN.getControl(b500xUp))
    LP_WIN.getControl(5012).controlUp(LP_WIN.getControl(b500xUp))

    #5005Up - full:5010 / answer:5002 / hangup:5004 / 5001
    b5005Up = 5010 if is_full_ver else b500xUp
    LP_WIN.getControl(5005).controlUp(LP_WIN.getControl(b5005Up))

    #if answer:
    #    ctrl_down = 5002
    #    ctrl_up = 5002
    #elif hangup:
    #    ctrl_down = 5004
    #    ctrl_up = 5004
    #else:
    #    ctrl_down = 5010
    #    ctrl_up = 5011
    #LP_WIN.getControl(5011).controlDown(LP_WIN.getControl(ctrl_down))
    #LP_WIN.getControl(5010).controlUp(LP_WIN.getControl(ctrl_up))
    #if answer and hangup:
    #    LP_WIN.getControl(5002).controlRight(LP_WIN.getControl(5004)) # from Dial to Hangup
    #    LP_WIN.getControl(5004).controlLeft(LP_WIN.getControl(5002))
    #elif answer:
    #    LP_WIN.getControl(5004).controlLeft(LP_WIN.getControl(5004))
    #elif hangup:
    #    LP_WIN.getControl(5002).controlLeft(LP_WIN.getControl(5002))

def initLinphone():
    ##------------------Initialisation Settings----------------------##
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
    multimedia_size = __settings__.getSetting("multimedia_size")
    multimedia_auto = __settings__.getSetting("multimedia_auto")
    capture_device = __settings__.getSetting("capture_list")
    playback_device = __settings__.getSetting("playback_list")
    echo_cancel = __settings__.getSetting("echo_cancel")

    xlog("Mmedia-size -1 %s" % (multimedia_size))
    if multimedia_auto == "true":
        multimedia_size = check_resolution(HEIGHT, WIDTH)
    else:
        multimedia_size = ["1080p", "720p", "svga", "4cif", "vga", "ios-medium", "cif", "qvga", "qcif"][int(multimedia_size)]
    xlog("Mmedia-size -2 %s" % (multimedia_size))
    debug_level = __settings__.getSetting("debug_level")
    debug_level = int(debug_level) +1

    ##----------------STARTING LINPHONE------------------------##

    if auto_answer == "true":
        auto_answer = '-a'
    else:
        auto_answer = ''

    os.system('killall -9 linphonec')
    if debugging == "true":
        cmd = 'bash -c "/usr/local/bin/linphonecsh init -V -d %s %s -l \'/home/%s/linphone.log\' -c \'/home/%s/.linphonerc\'"' % (debug_level, auto_answer, SYSTEM_USER, SYSTEM_USER)
    else:
        # need to enable debugger anyway, because status watcher uses linphone log.
        cmd = 'bash -c "/usr/local/bin/linphonecsh init -V -d %s %s -l \'/home/%s/linphone.log\' -c \'/home/%s/.linphonerc\'"' % (2, auto_answer, SYSTEM_USER, SYSTEM_USER)
        # cmd = 'bash -c "/usr/local/bin/linphonecsh init -V %s -c \'/home/%s/.linphonerc\'"' % (auto_answer, SYSTEM_USER)

    xlog("Init string: " +cmd)
    os.system(cmd)
    time.sleep(1)
    linphoneResize(RIGHT_SHIFT, DOWN_SHIFT)
    linphoneGeneric("pwindow pos 0 0")
    if auto_register == "true":
        linphonecsh("register --host '%s' --username '%s' --password '%s'" % (host, str(user), str(password)))
        xlog("HOST = %s USER = %s" % (host, str(user)))

    ##-----------------Params from settings to Linphonec------------------------##
    linphoneGeneric("soundcard capture " + capture_device)
    linphoneGeneric("soundcard playback " + playback_device)
    linphoneGeneric("param video size " + multimedia_size)
    linphoneGeneric("scale size %s %s" % (WIDTH - 350, HEIGHT))

    linphoneGeneric("ports sip " + str(sip_port))
    array = ["sip_port", "sip_tcp_port", "sip_tls_port"]
    if sip_protocol == array[0]:
        linphoneGeneric("param %s 0" %(array[1]))
        linphoneGeneric("param %s 0" %(array[2]))
    if sip_protocol == array[1]:
        linphoneGeneric("param %s 0" %(array[0]))
        linphoneGeneric("param %s 0" %(array[2]))
    if sip_protocol == array[2]:
        linphoneGeneric("param %s 0" %(array[0]))
        linphoneGeneric("param %s 0" %(array[1]))
    linphoneGeneric("param %s %s" % (sip_protocol, str(sip_port)))
    linphoneGeneric("param rtp video_rtp_port " + str(video_port))
    linphoneGeneric("param rtp audio_rtp_port " + str(audio_port))
    if direct_connection == "true":
        linphoneGeneric("firewall none")
    if behind_nat_one == "true":
        linphoneGeneric("nat " + behind_nat_ip)
        linphoneGeneric("firewall nat")
    if behind_nat_two == "true":
        linphoneGeneric("stun " + behind_nat_stun)
        linphoneGeneric("firewall stun")

    if echo_cancel == "true":
        linphoneGeneric("ec on")
    else:
        linphoneGeneric("ec off")

    time.sleep(1)
    xlog("SIP_PROTOCOL = %s SIP_PORT = %s DIRECT_CONNECTION = %s" % (sip_protocol, sip_port, direct_connection))

    status_register = sub.Popen("linphonecsh status register", shell=True, stdout=sub.PIPE).stdout.readline()
    linphone_friend_list = sub.Popen("linphonecsh generic 'friend list'", shell=True, stdout=sub.PIPE).stdout.read()
    soundcard_list = sub.Popen("linphonecsh generic 'soundcard list'", shell=True, stdout=sub.PIPE).stdout.readlines()
    sound_card_list_creating(soundcard_list)
    xlog("Status register: %s Friend list: %s" % (status_register, linphone_friend_list))
    return status_register

def check_resolution(h,w):
    my_paramethr = "qcif"
    if h > 1080 and w > 1920:
        my_paramethr = "720p"
    if (1080 > h > 720) and (1920 > w > 1080):
        my_paramethr = "svga"
    if (720 > h > 600) and (1280 > w >  800):
        my_paramethr = "4cif"
    if (600 > h > 576) and (800 > w > 704):
        my_paramethr = "vga"
    if (576 > h > 480) and (704 > w > 640):
        my_paramethr = "ios-medium"
    if (480 > h > 360) and (640 > w > 480):
        my_paramethr = "cif"
    if (360 > h > 288) and (480 > w > 352):
        my_paramethr = "qcif"

    if h == 1080 and w == 1920:
        my_paramethr = "720p"
    if h == 720 and w == 1280:
        my_paramethr = "svga"
    if h == 600 and w == 800:
        my_paramethr = "4cif"
    if h == 576 and w == 704:
        my_paramethr = "vga"
    if h == 480 and w == 640:
        my_paramethr = "ios-medium"
    if h == 360 and w == 480:
        my_paramethr = "cif"
    if h == 288 and w == 352:
        my_paramethr = "qvga"
    if h == 240 and w == 320:
        my_paramethr = "qcif"
    return my_paramethr

def get_phone_book():
    try:
        f = open(__cwd__ + "/phone_book.pb", "r+")
    except IOError:
        os.system("touch " + __cwd__ + "/phone_book.pb")
        f = open(__cwd__ + "/phone_book.pb", "r+")
        f.write("[]")
        f.seek(0)

    str_pb = f.read()
    str_pb = str_pb.replace("\n", "")
    str_pb = eval(str_pb)
    f.close()
    return str_pb

def set_phone_book(pb):
    f = open(__cwd__ + "/phone_book.pb", "w")
    str_pb = repr(pb)
    str_pb = str_pb.replace("], [", "], \n[")
    str_pb = str_pb.replace("[u'", "['")
    str_pb = str_pb.replace("', u'", "', '")
    f.write(str_pb)
    f.close()

def sound_card_list_creating(soundcard_list):
    try:
        f = open(__cwd__ + '/soundcards', 'w')
    except:
        limitLinphonecCodecs()
        os.system("touch %s" % __cwd__ + '/soundcards')
        f = open(__cwd__ + '/soundcards', 'w')
    for i in soundcard_list:
        f.write(i)
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
#            res = re.search(r"<.*?:([^:;>]*)", a)
            if a == "0":
                a = config.get("call_log_"+str(i), "to")
                res = re.search(r"<.*?:([^:;>]*)", a)
                if res.group(1) not in outgoing:
                    outgoing += [res.group(1)]
                if res.group(1) not in out_inc:
                    out_inc += [res.group(1)]
            else:
                a = config.get("call_log_"+str(i), "from")
                res = re.search(r"<.*?:([^:;>]*)", a)
                if res.group(1) not in incoming:
                    incoming +=  [res.group(1)]
                if res.group(1) not in out_inc:
                    out_inc += [res.group(1)]
            i += 1
        except:
            return outgoing, incoming, out_inc[-10:][::-1]

pb = get_phone_book()
placed, recieved, last_calls = parsing('/home/' + SYSTEM_USER + '/.linphonerc')
cmd = str()

# 91.189.95.83
# register_only_when_network_is_up
# reg_sendregister=0
#dpkg -i .deb
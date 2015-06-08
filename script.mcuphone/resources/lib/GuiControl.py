import xbmcgui
import os, sys
import subprocess as sub

__is_full_ver__ = sys.modules[ "__main__" ].__license__
__settings__ = sys.modules[ "__main__" ].__settings__

def defineControl(lp_win, list_top_pos):
    global ALL_BUTTONS
    global SW_LISTS
    global LP_WIN
    LP_WIN = lp_win
    #control ids
    LP_WIN.control_btn_close_id = 10
    LP_WIN.control_btn_call_to_id = 5001
    LP_WIN.control_btn_answer_id = 5002
    LP_WIN.control_btn_contacts_id = 5006
    LP_WIN.control_btn_hangup_id = 5004
    LP_WIN.control_btn_settings_id = 5005
    LP_WIN.control_btn_recent_id = 5003
    LP_WIN.control_list_contacts_id = 5008
    LP_WIN.control_btn_scaler_id = 5010
    LP_WIN.control_btn_add_contact_id = 5011
    LP_WIN.control_btn_self_view_id = 5012
    LP_WIN.control_label_status_id = 5051
    LP_WIN.control_btn_context_id = 5019
    LP_WIN.control_btn_bright_plus_id = 5031
    LP_WIN.control_btn_bright_minus_id = 5032
    #controls
    LP_WIN.btn_hangup = LP_WIN.getControl(LP_WIN.control_btn_hangup_id)
    LP_WIN.btn_contacts = LP_WIN.getControl(LP_WIN.control_btn_contacts_id)
    LP_WIN.btn_scaler = LP_WIN.getControl(LP_WIN.control_btn_scaler_id)
    LP_WIN.btn_self_view = LP_WIN.getControl(LP_WIN.control_btn_self_view_id)
    LP_WIN.btn_close = LP_WIN.getControl(LP_WIN.control_btn_close_id)
    LP_WIN.btn_call_to = LP_WIN.getControl(LP_WIN.control_btn_call_to_id)
    LP_WIN.btn_answer = LP_WIN.getControl(LP_WIN.control_btn_answer_id)
    LP_WIN.btn_settings = LP_WIN.getControl(LP_WIN.control_btn_settings_id)
    LP_WIN.btn_recent = LP_WIN.getControl(LP_WIN.control_btn_recent_id)
    #LP_WIN.list_contacts = LP_WIN.getControl(LP_WIN.control_list_contacts_id)
    LP_WIN.btn_add_contact = LP_WIN.getControl(LP_WIN.control_btn_add_contact_id)
    # LP_WIN.label_status = LP_WIN.getControl(LP_WIN.control_label_status_id)
    LP_WIN.btn_context = LP_WIN.getControl(LP_WIN.control_btn_context_id)
    LP_WIN.btn_bright_plus = LP_WIN.getControl(LP_WIN.control_btn_bright_plus_id)
    LP_WIN.btn_bright_minus = LP_WIN.getControl(LP_WIN.control_btn_bright_minus_id)

    LP_WIN.addControl(xbmcgui.ControlImage(970, list_top_pos - 3, 306, 306, 'list_bg.png'))
    LP_WIN.list_contacts = xbmcgui.ControlList(973, list_top_pos, 300, 330, 'font12', '0xFFFFFFFF', 'button-nofocus.png', 'button-focus.png', "0xFF000000", 0, 0, 0, 0, 25, 2)
    LP_WIN.addControl(LP_WIN.list_contacts)
    LP_WIN.control_list_contacts_id = LP_WIN.list_contacts.getId()
    LP_WIN.list_contacts.controlUp(LP_WIN.btn_contacts)
    LP_WIN.list_contacts.controlDown(LP_WIN.btn_call_to)
    LP_WIN.list_contacts.controlLeft(LP_WIN.btn_contacts)
    LP_WIN.list_contacts.controlRight(LP_WIN.btn_context)
    if __is_full_ver__ > 0:
        LP_WIN.btn_scaler.setVisible(True)
        LP_WIN.btn_self_view.setVisible(True)
    else:
        LP_WIN.btn_scaler.setVisible(False)
        LP_WIN.btn_self_view.setVisible(False)
    LP_WIN.btn_recent.controlDown(LP_WIN.list_contacts)
    LP_WIN.btn_contacts.controlDown(LP_WIN.list_contacts)
    LP_WIN.btn_call_to.controlUp(LP_WIN.list_contacts)
    LP_WIN.sttus = xbmcgui.ControlTextBox(973, 460, 300, 200, textColor='0xFFFFFFFF')
    LP_WIN.addControl(LP_WIN.sttus)


    #LP_WIN.sttus.setText("H:" + str(HEIGHT) + " W:" + str(WIDTH))
    if os.path.exists('/usr/bin/v4l2-ctl'):
        LP_WIN.btn_bright_plus.setVisible(True)
        LP_WIN.btn_bright_minus.setVisible(True)
        set_r = LP_WIN.control_btn_bright_plus_id
    else:
        LP_WIN.btn_bright_plus.setVisible(False)
        LP_WIN.btn_bright_minus.setVisible(False)
        set_r = LP_WIN.control_btn_settings_id
    b_list = LP_WIN.control_list_contacts_id
    b_callto = LP_WIN.control_btn_call_to_id
    b_addcont = LP_WIN.control_btn_add_contact_id
    b_up = LP_WIN.control_btn_answer_id
    b_down = LP_WIN.control_btn_hangup_id
    b_size = LP_WIN.control_btn_scaler_id
    b_self = LP_WIN.control_btn_self_view_id
    b_sett = LP_WIN.control_btn_settings_id
    b_close = LP_WIN.control_btn_close_id
    # b_bplus = LP_WIN.control_btn_bright_plus_id
    # b_list, b_callto, b_addcont, b_up, b_down, b_size, b_self, b_sett, b_close
    ALL_BUTTONS = {'b_list' : b_list, 'b_callto' : b_callto, 'b_addcont' : b_addcont, 'b_up' : b_up, 'b_down' : b_down,
                'b_size' : b_size, 'b_self' : b_self, 'b_sett' : b_sett, 'b_close' : b_close}
    #                                  UP        RIGHT      DOWN      LEFT
    b_lite = {'end':    {'b_list'   : [0,        0,         b_callto, 0],
                         'b_callto' : [b_list,   b_addcont, b_sett,   b_addcont],
                         'b_addcont': [b_list,   b_callto,  b_sett,   b_callto],
                         'b_sett'   : [b_callto, set_r,     b_close,  b_sett],
                         'b_close'  : [b_sett,   0,         0,        0]},
              'ringing':{'b_list'   : [0,        0,         b_up,     0],
                         'b_up'     : [b_list,   b_down,    b_close,  b_down],
                         'b_down'   : [b_list,   b_up,      b_close,  b_up],
                         'b_close'  : [b_up,     0,         0,        0]},
              'calling':{'b_list'   : [0,        0,         b_down,   0],
                         'b_down'   : [b_list,   b_down,    b_close,  b_down],
                         'b_close'  : [b_down,   0,         0,        0]},
              'active': {'b_list'   : [0,        0,         b_down,   0],
                         'b_down'   : [b_list,   b_down,    b_close,  b_down],
                         'b_close'  : [b_down,   0,         0,        0]},
             }
    b_full = {'end':    {'b_list'   : [0,        0,         b_callto, 0],
                         'b_callto' : [b_list,   b_addcont, b_size,   b_addcont],
                         'b_addcont': [b_list,   b_callto,  b_size,   b_callto],
                         'b_size'   : [b_addcont,b_size,    b_sett,   b_size],
                         'b_sett'   : [b_size,   set_r,     b_close,  b_sett],
                         'b_close'  : [b_sett,   0,         0,        0]},
              'ringing':{'b_list'   : [0,        0,         b_up,     0],
                         'b_up'     : [b_list,   b_down,    b_close,  b_down],
                         'b_down'   : [b_list,   b_up,      b_close,  b_up],
                         'b_close'  : [b_up,     0,         0,        0]},
              'calling':{'b_list'   : [0,        0,         b_down,   0],
                         'b_down'   : [b_list,   b_down,    b_close,  b_down],
                         'b_close'  : [b_down,   0,         0,        0]},
              'active': {'b_list'   : [0,        0,         b_down,   0],
                         'b_down'   : [b_list,   b_down,    b_size,   b_down],
                         'b_size'   : [b_down,   b_self,    b_close,  b_self],
                         'b_self'   : [b_down,   b_size,    b_close,  b_size],
                         'b_close'  : [b_size,   0,         0,        0]},
              'conf':   {'b_list'   : [0,        0,         b_callto, 0],
                         'b_callto' : [b_list,   b_callto,  b_down,   b_callto],
                         'b_down'   : [b_callto, b_down,    b_size,   b_down],
                         'b_size'   : [b_down,   b_self,    b_close,  b_self],
                         'b_self'   : [b_down,   b_size,    b_close,  b_size],
                         'b_close'  : [b_size,   0,         0,        0]},
              }
    SW_LISTS = b_full if __is_full_ver__ else b_lite

def fixUpDown(answer, hangup, callstatus, can_call):
    global ALL_BUTTONS
    global SW_LISTS

    if callstatus == 'error':
        callstatus = 'end'
    # 'end', 'ringing', 'calling', 'active'
    # 5001 - Call to, 5002 - Dial, 5004 - Hangup, 5005 - Settings, 5010 - Size, 5011 - Add contact, 5012 - SelfView
    # list_contacts / control_list_contacts_id

    if callstatus == 'active' and can_call:
        callstatus = 'conf'
    sw_list = SW_LISTS[callstatus]
    for abtn in ALL_BUTTONS:
        if abtn not in sw_list:
            LP_WIN.getControl(ALL_BUTTONS[abtn]).setVisible(False)
    for button in sw_list:
        LP_WIN.getControl(ALL_BUTTONS[button]).setVisible(True)
        if sw_list[button][0]: # UP
            LP_WIN.getControl(ALL_BUTTONS[button]).controlUp(LP_WIN.getControl(sw_list[button][0]))
        if sw_list[button][1]: # RIGHT
            LP_WIN.getControl(ALL_BUTTONS[button]).controlRight(LP_WIN.getControl(sw_list[button][1]))
        if sw_list[button][2]: # DOWN
            LP_WIN.getControl(ALL_BUTTONS[button]).controlDown(LP_WIN.getControl(sw_list[button][2]))
        if sw_list[button][3]: # LEFT
            LP_WIN.getControl(ALL_BUTTONS[button]).controlLeft(LP_WIN.getControl(sw_list[button][3]))

def checkResolution(h, w):
    res = "qcif"
    if h > 1080 and w > 1920:
        res = "720p"
    if (1080 > h > 720) and (1920 > w > 1080):
        res = "svga"
    if (720 > h > 600) and (1280 > w >  800):
        res = "4cif"
    if (600 > h > 576) and (800 > w > 704):
        res = "vga"
    if (576 > h > 480) and (704 > w > 640):
        res = "ios-medium"
    if (480 > h > 360) and (640 > w > 480):
        res = "cif"
    if (360 > h > 288) and (480 > w > 352):
        res = "qcif"

    if h == 1080 and w == 1920:
        res = "720p"
    if h == 720 and w == 1280:
        res = "svga"
    if h == 600 and w == 800:
        res = "4cif"
    if h == 576 and w == 704:
        res = "vga"
    if h == 480 and w == 640:
        res = "ios-medium"
    if h == 360 and w == 480:
        res = "cif"
    if h == 288 and w == 352:
        res = "qvga"
    if h == 240 and w == 320:
        res = "qcif"
    return res

def setBrightness(delta, exact):
    cmd = '/usr/bin/v4l2-ctl'
    if os.path.exists(cmd):
        if exact:
            os.system(cmd + ' -c brightness=' + str(exact))
        else:
            cur_bright = sub.Popen(cmd + ' -C brightness', shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
            err = cur_bright.stderr.readline()
            if err and err.find("to open /dev") > 0:
                cmd = cmd + ' -d /dev/video1'
                cur_bright = sub.Popen(cmd + ' -C brightness', shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
            cb = cur_bright.stdout.readline()
            if cb.find("rightness") > 0:
                cur_bright = cb
                cur_bright = int(cur_bright.replace("brightness: ",""))
                new_bright = cur_bright + delta
                if new_bright >= 0 and new_bright <= 255:
                    os.system(cmd + ' -c brightness=' + str(new_bright))
                    __settings__.setSetting(id="brightness", value=str(new_bright))
            else:
                xlog("_CTL_ Wrong cur_bright:" + cur_bright + ' / ' + cur_bright.stderr.readline())
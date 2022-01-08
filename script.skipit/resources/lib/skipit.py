import xbmc
import xbmcgui
import xbmcaddon
import threading

# create a class for your addon, we need this to get info about your addon
ADDON = xbmcaddon.Addon()
# get the full path to your addon, decode it to unicode to handle special (non-ascii) characters in the path
CWD = ADDON.getAddonInfo('path')
 
skip_secs = 180 
min_skip_secs = 3 
slippage = 1
timeout = 5.0
going_forward = False
going_backward = False

class SkipItWindow(xbmcgui.WindowXMLDialog):

    # until now we have a blank window, the onInit function will parse the xml file
    def onInit(self):
        
        global my_timer
        global skip_secs
        global min_skip_secs
        global slippage
        global timeout

        self.setFocusId(self.getCurrentContainerId())
        
        skip_secs = ADDON.getSettingInt('skipsecs')
        min_skip_secs = ADDON.getSettingInt('minskipsecs')
        slippage = ADDON.getSettingInt('slippage')
        timeout = ADDON.getSettingNumber('timeout')
        
        skip_forward()

    def onAction(self, action):

        xbmc.log('actionid received: ' + str(action.getId()), xbmc.LOGDEBUG)

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU:
          xbmc.log('action received: previous', xbmc.LOGDEBUG)
          close_me()
        if action.getId() == xbmcgui.ACTION_NAV_BACK:
          xbmc.log('action received: back', xbmc.LOGDEBUG)
          close_me()
        if action.getId() == xbmcgui.ACTION_SELECT_ITEM:
          xbmc.log('action received: enter', xbmc.LOGDEBUG)
          close_me()

        if action.getId() == xbmcgui.ACTION_MOVE_RIGHT:
          xbmc.log('action received: move right', xbmc.LOGDEBUG)
          skip_forward()

        if action.getId() == xbmcgui.ACTION_MOVE_LEFT:
          xbmc.log('action received: move left', xbmc.LOGDEBUG)
          skip_backward()

        if action.getId() == xbmcgui.ACTION_MOVE_UP:
          xbmc.log('action received: move up', xbmc.LOGDEBUG)
          reset()
          skip_forward()

        if action.getId() == xbmcgui.ACTION_MOVE_DOWN:
          xbmc.log('action received: move down', xbmc.LOGDEBUG)
          reset()
          skip_backward()

def skip_forward():
    # 
    # Skip forward the required amount
    global skip_secs
    global going_forward
    going_forward = True

    reset_timer()
    halve()
    set_label(skip_secs, True)
    command = build_command(skip_secs - slippage, True)
    xbmc.executebuiltin(command)
    return 

def skip_backward():
    # 
    # Skip forward the required amount
    global skip_secs
    global going_backward
    going_backward = True
    
    reset_timer()
    halve()
    set_label(skip_secs, False)
    # Add a couple of extra seconds as the video is still playing forwards
    command = build_command(skip_secs + slippage, False)
    xbmc.executebuiltin(command)
    return 

def set_label(seconds, forward):
    global ui
    if forward:
        arrow = '>>'
    else:
        arrow = '<<'
        
    text = ADDON.getLocalizedString(32110)
    text = text.format(arrow, seconds) 
    label = ui.getControl(1)
    label.setLabel(text)
    return 

def reset():
    global skip_secs
    global going_forward
    global going_backward
    
    going_forward = False
    going_backward = False
    skip_secs = ADDON.getSettingInt('skipsecs')
    return
        
def halve():
    global going_forward
    global going_backward
    global skip_secs
    global min_skip_secs
    if going_forward & going_backward:
        skip_secs = round(skip_secs / 2);
    if skip_secs < min_skip_secs:
        skip_secs = min_skip_secs
    return
        
def build_command(seconds, forward):
    #
    # Build the skip command
    if not(forward):
        seconds = -seconds
    
    command = 'Seek({})'
    command = command.format(seconds) 
    xbmc.log('SkipIt seeking command - {}'.format(command), xbmc.LOGDEBUG)
    return command

def close_me():
    global my_timer
    global ui
    if my_timer:
        my_timer.cancel()
    ui.close()

def reset_timer():
    global my_timer
    global timeout
    if my_timer:
        my_timer.cancel()
    my_timer = threading.Timer(timeout, close_me)
    my_timer.start()
    
    
my_timer = threading.Timer(timeout, close_me)

addon       = xbmcaddon.Addon()
addonname   = addon.getAddonInfo('name')

ui = SkipItWindow('script-skipitwindow.xml', CWD, 'default', '1080i')
# now open your window. the window will be shown until you close your addon
ui.doModal()
# window closed, now cleanup a bit: delete your window before the script fully exits
del ui

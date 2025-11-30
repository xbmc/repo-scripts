import xbmc
import xbmcgui
import xbmcaddon
import threading

# create a class for your addon, we need this to get info about your addon
ADDON = xbmcaddon.Addon()
# get the full path to your addon, decode it to unicode to handle special (non-ascii) characters in the path
CWD = ADDON.getAddonInfo('path')
 
going_forward = False
going_backward = False
went_forward = False
went_backward = False
overshot = False
lock = threading.Lock()
min_skip_secs = 3 
skip_secs = 180 
slippage = 1
timeout = 5.0


class SkipItWindow(xbmcgui.WindowXMLDialog):

    # until now we have a blank window, the onInit function will parse the xml file
    def onInit(self):
        
        global my_timer
        global skip_secs
        global min_skip_secs
        global max_skip_secs
        global slippage
        global timeout
        global going_forward

        self.setFocusId(self.getCurrentContainerId())
        
        max_skip_secs = ADDON.getSettingInt('skipsecs')
        min_skip_secs = ADDON.getSettingInt('minskipsecs')
        slippage = ADDON.getSettingInt('slippage')
        timeout = ADDON.getSettingNumber('timeout')
        skip_secs = max_skip_secs
        going_forward = True
        
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


def do_skip(skip_secs):
    # We need to track the actual skip, in case we run past the end
    player = xbmc.Player()
    totalTime = player.getTotalTime()
    preSeekTime = player.getTime()

    seek_to = preSeekTime + skip_secs;
    if seek_to < 1:
        seek_to = 1;
    if seek_to > (totalTime - 1):
        seek_to = totalTime - 1;
    player.seekTime(seek_to)
    # Now work out how far we went (might have run to the end or start
    xbmc.log('Skipping : Req {0}, pre {1}, post {2}, tot {3}'.format(skip_secs, preSeekTime, seek_to, totalTime), xbmc.LOGDEBUG)
    
    return round(seek_to - preSeekTime)


def skip_forward():

    with lock:
        if not(xbmc.Player().isPlaying()):
            close_me()
            return
        # 
        # Skip forward the required amount
        global addonname
        global skip_secs
        global went_forward
        global going_forward
        global went_backward
        went_forward = True
    
        reset_timer()

        calc_overshot(True)
        calc_next_skip_size()
        set_label(skip_secs, True)
        requested_skip = skip_secs - slippage
        actual_skip = do_skip(requested_skip)
        if actual_skip != requested_skip:
            skip_secs = abs(actual_skip)
            xbmcgui.Dialog().notification(addonname, ADDON.getLocalizedString(32135))

        going_forward = True
    return 


def skip_backward():
    
    with lock:
    
        if not(xbmc.Player().isPlaying()):
            close_me()
            return
        # 
        # Skip forward the required amount
        global addonname
        global skip_secs
        global went_backward
        global going_forward

        went_backward = True
    
        reset_timer()
        calc_overshot(False)
        calc_next_skip_size()
        set_label(skip_secs, False)
        # Add a couple of extra seconds as the video is still playing forwards
        requested_skip = -(skip_secs + slippage)
        actual_skip = do_skip(requested_skip);
        if actual_skip != requested_skip:
            skip_secs = abs(actual_skip)
            xbmcgui.Dialog().notification(addonname, ADDON.getLocalizedString(32130))
            
        going_forward = False
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
    global went_forward
    global went_backward
    global overshot
    global max_skip_secs
    
    with lock:
        went_forward = False
        went_backward = False
        overshot = False
        skip_secs = max_skip_secs
    return

        
def calc_next_skip_size():
    global went_forward
    global went_backward
    global skip_secs
    global min_skip_secs
    global overshot

    if went_forward & went_backward:
        if overshot:
            skip_secs = skip_secs * 2
        else:
            skip_secs = round(skip_secs / 2)
    if skip_secs < min_skip_secs:
        skip_secs = min_skip_secs
    if skip_secs > max_skip_secs:
        skip_secs = max_skip_secs
    return

        
def calc_overshot(forward):
    global going_forward
    global skip_secs
    global min_skip_secs
    global overshot

    # If going in the same direction and are at the minimum skip we have overshot
    if going_forward == forward:
        if skip_secs <= min_skip_secs:
            overshot = True
    # Change of direction turns overshoot off
    else:
        overshot = False    
    return

        
def close_me():
    global my_timer
    global ui
    if my_timer:
        my_timer.cancel()
    label = ui.getControl(1)
    label.setLabel('')
    ui.close()


def reset_timer():
    global my_timer
    global timeout
    if my_timer:
        my_timer.cancel()
    my_timer = threading.Timer(timeout, close_me)
    my_timer.start()
    
    
my_timer = threading.Timer(timeout, close_me)

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')

ui = SkipItWindow('script-skipitwindow.xml', CWD, 'default', '1080i')
# now open your window. the window will be shown until you close your addon
ui.doModal()
# window closed, now cleanup a bit: delete your window before the script fully exits
del ui

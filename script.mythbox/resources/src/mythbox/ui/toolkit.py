#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import logging
import xbmc
import xbmcgui
import time

from decorator import decorator
from mythbox.util import safe_str

log = logging.getLogger('mythbox.ui')
elog = logging.getLogger('mythbox.event')


class AspectRatio(object):
    STRETCH = 0       
    SCALE_UP = 1     # crops
    SCALE_DOWN = 2   # black bars
    

class Action(object):
    LEFT                    = 1
    RIGHT                   = 2
    UP                      = 3
    DOWN                    = 4
    PAGE_UP                 = 5  # Channel Up on MCE remote
    PAGE_DOWN               = 6  # Channel Down on MCE remote
    SELECT_ITEM             = 7
    ACTION_HIGHLIGHT_ITEM   = 8
    PARENT_DIR              = 9
    PREVIOUS_MENU           = 10
    ACTION_SHOW_INFO        = 11
    PAUSE                   = 12
    STOP                    = 13
    ACTION_NEXT_ITEM        = 14  # Remote: >>|
    ACTION_PREV_ITEM        = 15  # Remote: <<|
    FORWARD                 = 77  # Remote: >>
    REWIND                  = 78  # Remote: <<
    NAV_BACK                = 92  # introduced in eden
    ACTION_SCROLL_UP        = 111
    ACTION_SCROLL_DOWN      = 112
    CONTEXT_MENU            = 117  # TV Guide on MCE remote
    HOME                    = 159  # kbd only
    END                     = 160  # kbd only
    
    GO_BACK = (PARENT_DIR, PREVIOUS_MENU, NAV_BACK,)
    

class Align(object):
    # from xbmc/guilib/common/xbfont.h
    LEFT      = 0
    RIGHT     = 1
    CENTER_X  = 2
    CENTER_Y  = 4
    TRUNCATED = 8


def toString(action):
    """
    @type action: xbmcgui.Action
    """ 
    return "Action(id = %s, amount1=%s, amount2=%s, buttonCode=%s" % (
        action.getId(), action.getAmount1(), action.getAmount2(), action.getButtonCode())
         

def showPopup(title, text, millis=10000):
    # filter all commas out of text since they delimit args
    title = title.replace(',', ';')
    text = text.replace(',', ';')
    s = u'XBMC.Notification(%s,%s,%s)'  % (title, text, millis)
    log.debug('showPopup: %s' % safe_str(s))
    xbmc.executebuiltin(s)


def enterText(control, validator=None, updater=None, heading=None, current=None):
    """
    Prompt user to enter a text string via xbmc's keyboard control and populate
    the associated text control.
    
    @param control: control to edit
    @param validator: method with a single param to validate text. should raise Exception on invald text
    @param updater: method with a single param to update the text in a domain object
    @param heading: Dialog title as str
    @param current: current value as str
    @return: tuple(ok=bool, value=str)
    """
    ok = False
    txt = None
    
    if heading is None:
        if True: # type(control) == xbmcgui.ControlButton:
            heading = control.getLabel()
        
    if current is None:
        if True: # type(control) == xbmcgui.ControlButton:
            current = control.getLabel2()
            
    log.debug('current=%s heading=%s' % (current, heading))
    
    kbd = xbmc.Keyboard(current, heading)
    kbd.doModal()
    if kbd.isConfirmed():
        txt = kbd.getText()
        
        valid = True
        if validator:
            try:
                log.debug('validating %s' % txt)
                validator(txt)
            except Exception, e:
                valid = False
                errMsg = str(e)  # TODO: Extract proper error message
                log.exception('validator')

        if valid:
            if True: #type(control) == xbmcgui.ControlButton:
                control.setLabel(label=heading, label2=txt)
                ok = True
                if updater: 
                    updater(txt)
        else:
            xbmcgui.Dialog().ok("Error", errMsg)
            
    return ok, txt
            

def enterNumeric(control, min=None, max=None, validator=None, updater=None, heading=None, current=None):
    """
    Prompt user to enter a number and update the associated control and/or domain object.
    
    @param heading: Dialog title as string
    @param current: current value as int
    """
    ok = False
    value = None
    
    if heading is None:
        if True: # type(control) == xbmcgui.ControlButton:
            heading = control.getLabel()
        
    if current is None:
        if True: #type(control) == xbmcgui.ControlButton:
            current = control.getLabel2()
    
    value = xbmcgui.Dialog().numeric(0, heading, current)
    result = int(value)
    valid = True
        
    if min is not None and result < min:
        valid = False
        errMsg = 'Value must be between %d and %d' % (min, max)
        
    if max is not None and result > max:
        valid = False
        errMsg = 'Value must be between %d and %d' % (min, max)
    
    if validator:
        try:
            log.debug('validating %s' % result)
            validator(str(result))
        except Exception, e:
            valid = False
            errMsg = str(e)  # TODO: Extract proper error message
            log.exception('validator')

    if valid:
        if True: #type(control) == xbmcgui.ControlButton:
            control.setLabel(label=heading, label2=str(result))
            ok = True
            if updater: 
                updater(result)
    else:
        xbmcgui.Dialog().ok("Error", errMsg)
        
    return ok, value


@decorator
def window_busy(func, *args, **kwargs):
    window = args[0]
    try:
        window.setBusy(True)
        result = func(*args, **kwargs)
    finally:
        window.setBusy(False)
    return result


def setIconImage(playlistItem, imagePath):
    if imagePath is None:
        log.warn('playlist.setIconImage(None) called')
    else:
        playlistItem.setIconImage(imagePath)


def setThumbnailImage(playlistItem, imagePath):
    if imagePath is None:
        log.warn('playlist.setThumbnailImage(None) called')
    else:
        playlistItem.setThumbnailImage(imagePath)


class WindowMixin(object):
    
    def getListItemProperty(self, listItem, name):
        '''Workaround for default impl always returning a string even though value set was unicode.'''
        p = listItem.getProperty(name)
        if p is not None:
            return p.decode('utf-8')
        
    def setListItemProperty(self, listItem, name, value):
        """
        Convenience method to make sure None values don't get set on a listItem
        """
        if listItem and name and not value is None:
            listItem.setProperty(name, value)
        else:
            log.debug('Setting listitem with a None: listItem=%s name=%s value=%s' % (listItem, name, value))

    def updateListItemProperty(self, listItem, name, value):
        self.setListItemProperty(listItem, name, value)
        # HACK: to force listitem update
        listItem.setThumbnailImage('%s' + str(time.clock()))   

    def setWindowProperty(self, name, value):
        """
        Convenience method to make sure None values don't get set on a Window
        """
        if self.win and name and not value is None:
            self.win.setProperty(name, value)
        else:
            log.debug('Setting window property with a None: win=%s name=%s value=%s' % (self.win, name, value))

    def selectListItemAtIndex(self, listbox, index):
        ''''
        ControlList.selectItem(index) is async. A subsequent call to ControlList.getSelectedPosition() 
        does not guarantee that the index set in selectItem(...) will be returned. This here is a
        little hack to wait until the the async msg is completed otherwise weird things happen :-)
        '''
        # TODO: guard against index > num list items
        if index < 0: 
            index = 0
        listbox.selectItem(index)
        maxtries = 100
        cnt = 0
        while listbox.getSelectedPosition() != index and cnt < maxtries:
            cnt += 1
            log.debug("waiting for item select to happen...%d" % cnt)
            time.sleep(0.1)
        if cnt == maxtries:
            log.warn("timeout waiting for item select to happen")


class BaseWindow(xbmcgui.WindowXML, WindowMixin):
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.win = None        
        self.closed = False
        
    def setBusy(self, busy):
        self.win.setProperty('busy', ('false', 'true')[busy])
        
    def isBusy(self):
        busy = self.win.getProperty('busy')
        return busy and busy == 'true'


class BaseDialog(xbmcgui.WindowXMLDialog, WindowMixin):
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.win = None        

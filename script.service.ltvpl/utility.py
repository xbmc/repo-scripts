#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
from threading import Thread, Event as Signal
import xbmc
import xbmcgui
from resources.lib.Utilities.DebugPrint import DEBUGMODE

__Version__ = "1.0.0"

try:
    from util import LTVPL_HEADER
except: pass

from resources.lib.Utilities.VirtualEvents import TS_decorator

def myLog(*args):
    if DEBUGMODE:
        xbmc.log(*args,level=xbmc.LOGINFO)


myWindowActivated = False


@TS_decorator
def BusyDialog(msg):
    global myWindowActivated
    myWindowActivated = False
    count = 0
    percent = 0
    dialog = xbmcgui.DialogProgress()
    dialog.create(LTVPL_HEADER, msg)

    while not myWindowActivated and count < 20:
        dialog.update(percent)
        percent = (percent + 5) % 100
        count += 1
        xbmc.sleep(1000)

    dialog.close()


def translateResolution(resNo):
    """
    Translates a resolution number into a resolution tuple
    :param resNo: int
    :return: tuple
    """
    xbmc.log("trasnlateResolution resNo: {}".format(resNo))
    resTable = [
        (1920, 1080),
        (1280, 720),
        (720, 480),
        (720, 480),
        (720, 480),
        (720, 480),
        (720, 576),
        (720, 576),
        (720, 480),
        (720, 480)
    ]
    return resTable[resNo]


def setDialogActive(name):
    xbmcgui.Window(10000).setProperty(name, 'true')

def clearDialogActive(name):
    xbmcgui.Window(10000).setProperty(name, 'false')

def deleteDialogActiveProperty(name):
    xbmcgui.Window(10000).clearProperty(name)

def isDialogActive(name):
    try:
        return xbmcgui.Window(10000).getProperty(name) == 'true'
    except:
        return False


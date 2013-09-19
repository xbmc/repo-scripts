#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
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
#
import sys
import traceback as tb
import random

import xbmcaddon
import xbmcplugin

import buggalo_client as client
import buggalo_gui as gui
import buggalo_userflow as userflow

# You must provide either the SUBMIT_URL or GMAIL_RECIPIENT
# via buggalo.SUBMIT_URL = '' or buggalo.GMAIL_RECIPIENT = ''

# The full URL to where the gathered data should be posted.
SUBMIT_URL = None
# The email address where the gathered data should be sent.
GMAIL_RECIPIENT = None

EXTRA_DATA = dict()

SCRIPT_ADDON = len(sys.argv) == 1

if not SCRIPT_ADDON:
    # Automatically track userflow for plugin type addons
    userflow.trackUserFlow('%s%s' % (sys.argv[0], sys.argv[2]))


def addExtraData(key, value):
    EXTRA_DATA[key] = value


def trackUserFlow(value):
    """
    Registers an entry in the user's flow through the addon.
    The values is stored in a dict with the current time as key and the provided value as the value.

    For plugin-type addons the user flow is automatically registered for each page the user loads.
    The value can be any string, so it's also useful in script-type addons.

    @param value: the value indicating the user's flow.
    @type value: str
    """
    userflow.trackUserFlow(value)


def getRandomHeading():
    """
    Get a random heading for use in dialogs, etc.
    The heading contains a random movie quote from the English strings.xml
    """
    return getLocalizedString(random.randint(90000, 90011))


def getLocalizedString(id):
    """
    Same as Addon.getLocalizedString() but retrieves data from this module's strings.xml
    """
    buggaloAddon = xbmcaddon.Addon(id='script.module.buggalo')
    return buggaloAddon.getLocalizedString(id)


def buggalo_try_except(extraData = None):
    """
    @buggalo_try_except function decorator wraps a function in a try..except clause and invokes onExceptionRaised()
    in case an exception is raised. Provide extraData to specific function specific extraData.

    @param extraData: str or dict
    """
    def decorator(fn):
        def wrap_in_try_except(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                onExceptionRaised(extraData)
        return wrap_in_try_except
    return decorator


def onExceptionRaised(extraData=None):
    """
    Invoke this method in an except clause to allow the user to submit
    a bug report with stacktrace, system information, etc.

    This also avoids the 'Script error' popup in XBMC, unless of course
    an exception is thrown in this code :-)

    @param extraData: str or dict
    """
    # start by logging the usual info to stderr
    (etype, value, traceback) = sys.exc_info()
    tb.print_exception(etype, value, traceback)

    if not SCRIPT_ADDON:
        try:
            # signal error to XBMC to hide progress dialog
            HANDLE = int(sys.argv[1])
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        except Exception:
            pass

    heading = getRandomHeading()
    data = client.gatherData(etype, value, traceback, extraData, EXTRA_DATA)

    d = gui.BuggaloDialog(SUBMIT_URL, GMAIL_RECIPIENT, heading, data)
    d.doModal()
    del d

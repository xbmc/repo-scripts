#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import sys
import traceback
from resources.lib.taskABC import AbstractTask, KodiLogger, notify
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString
__ = kodipo.getLocalizedStringId

class TaskCustom(AbstractTask):
    """
    Your task MUST subclass AbstractTask. If it doesn't, it will not be accessible.
    The following two parameters are REQUIRED with the same structure as shown.
    'Varaibles' will be prompted for from the Settings screen.
    If you have no variables, then you probably do not need to be writing a custom task.
    Shorten or extend the list as needed for more or less variables.
    This allows for the task to be properly 'discovered' and also will allow users to imput required information.
    See http://kodi.wiki/view/Add-on_settings for details about the settings variables.
    """
    tasktype = 'mycustomtasktype'
    variables = [
        {
            'id':'mycustomvariable1',
            'settings':{
                'default':'',
                'label':__('My Custom Task Variable 1', update=True),  # Surround label for settings with localization function
                'type':'text'
            }
        },
        {
            'id':'mycustomvariable2',
            'settings':{
                'default':'false',
                'label':__('My Custom Task Variable 2', update=True), # Surround label for settings with localization function
                'type':'bool'
            }
        },
    ]

    def __init__(self):
        """Do not request any other variables via __init__. Nothing else will be provided and an exception will be raised.
        The following super call is REQUIRED."""
        super(TaskCustom, self).__init__()
        # Put anything else here you may need, but note that validate is a staticmethod and cannot access 'self'.

    @staticmethod
    def validate(taskKwargs, xlog=KodiLogger.log):
        """
        :param taskKwargs:
        :param xlog: class or method that accepts msg=str and loglevel=int see below
        :type:
        :return: whether validate
        :rtype: bool
        Place any code here to validate the users input from the settings page.
        Referring to the above taskKwargs will be a dictionary objected keyed for your variable ids.
        For example: {'mycustomvariable1':'userinput', 'mycustomvariable2':False}
        The appropraite logger will be passed in. During testing, log output is captured and then displayed
        on the screen. Usage:
        xlog(msg='My message')
        Return True if validating passed. False if it didn't. If there is nothing to validate, just return True.

        ** If you generate any log messages here, surround them with the _(  , update=True) localization function.
        This will cause the po file to be updated with your strings.
        See below. During direct testing from the settings page, these log messages will be displayed on the screen
        """
        xlog(msg=_('My Custom Task passed validation', update=True))

        return True

    def run(self):
        """
        The following templated code is recommended. As above, self.taskKwargs contains your user input variables.
        There are a few other things added to taskKwargs (such as 'notify' seen below). If you have access to a debugger,
        stop the code here and look at that variable. Or try logging it as a string, if interested.
        self.runtimeargs contains the variable substituted event string.
        Information is passed out via the err and msg variables.

        ** If you generate any log messages here, surround them with the _(  , update=True) localization function.
        This will cause the po file to be updated with your strings.
        See below. During direct testing from the settings page, these log messages will be displayed on the screen
        """
        if self.taskKwargs['notify'] is True:
            notify(_('Task %s launching for event: %s') % (self.taskId, str(self.topic)))
        err = False  # Change this to True if an error is encountered
        msg = '' # Accumulate error or non-error information that needs to be returned in this string
        args = self.runtimeargs  # This contains a list derived from the variable subsituted event string
            # This list format is needed for using python's subprocess and Popen calls so that's why it is formatted
            # in this fashion.
            # If you need the args in a different format consider rejoining it into a string such as ' '.join(args) or
            # ', '.join(args). If you need something very different, you will need to override self.processUserargs()
            # See taskABC for the default processing and taskHttp for an example of overriding.
        assert isinstance(args, list)
        try:
            pass
            # Put your task implementation code here. Consider an inner try/except block accumulating specific error info
            # by setting err=True and appending to the message.
        except Exception:
            # Non-specific error catching and processing.
            e = sys.exc_info()[0]
            err = True
            if hasattr(e, 'message'):
                msg = str(e.message)
            msg = msg + '\n' + traceback.format_exc()
        # The following needs to be the last call. Since this code is running in its own thread, to pass information
        # backout, the following is formatted and placed in an output Queue where the parent thread is waiting.
        # If you do not pass anything out, a memory leak will accumulate with 'TaskManagers' accumulating over time.
        self.threadReturn(err, msg)

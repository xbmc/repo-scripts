#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
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

import xbmcaddon
import xbmcgui


def selectordialog(args):
    """
    Emulates a selector control that is lvalues compatible for subsequent conditionals in Kodi settings
    args is a list of strings that is kwarg 'like'.
    'id=myid': (Required) where myid is the settings.xml id that will be updated
        The plain id will contain the actual index value and is expected to be a hidden text element.
        This is the value to be tested against in subsequent conitionals.
        The string passed will be appended with '-v' i.e. myid-v. It is expected that this refers to a
        disabled selector element with the same lvalues as passed to the script.
        NOTE: There is an undocumented feature of type="select" controls to set the default based on an lvalue:
        ldefault="lvalue" where lvalue is a po string id.
    'useindex=bool': (Optional)If True, the zero based index of the subsequent lvalues will be stored in the hidden test
        element.
        If False or not provided, will store the actual lvalue in the hidden field.
    'heading=lvalue': (Optional) String id for heading of dialog box.
    'lvalues=int|int|int|...': (Required) The list of lvalues to display as choices.

    Usage example for settings.xml:

    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <settings>
      <category label="lvalues example">
          <setting label="The selector below calls a script that sets a setting" type="lsep" />
          <setting label="32001" type="action" action="RunScript(script.lvalues_example, lselector, id=choice, heading=32007, lvalues=32006|32003|32004|32005)" />
          <setting ldefault="32006" label="32002" type="select" id="choice-v" enable="false" lvalues="32006|32003|32004|32005" />
          <setting label="" type="text" id="choice" visible="false" default="" />
          <setting label="The line below uses visible='eq(-2,32003)' matching the hidden value" type="lsep" />
          <setting label="You can see me if you choose Task 1" type="lsep" visible="eq(-2,32003)" />
      </category>
    </settings>

    <!--32001 = 'Choose:', 32002 = 'Choice', 32003 = 'Task1', 32004 = 'Task2', 32005 = 'Task3'-->
    <!--32006 = 'None', 32007 = 'Choose wisely'-->

    :param args: List of string args
    :type args: list
    :return: True is selected, False if cancelled
    :rtype: bool
    """

    settingid = None
    useindex = False
    lvalues_str = None
    heading = ''
    for arg in args:
        splitarg = arg.split('=')
        kw = splitarg[0].strip()
        value = splitarg[1].strip()
        if kw == 'id':
            settingid = value
        elif kw == 'useindex':
            useindex = value.lower() == 'true'
        elif kw == 'lvalues':
            lvalues_str = value.split('|')
        elif kw == 'heading':
            heading = value
    if lvalues_str is None or settingid is None:
        raise SyntaxError('Selector Dialog: Missing elements from args')
    lvalues = []
    choices = []
    for lvalue in lvalues_str:
        try:
            lvalues.append(int(lvalue))
        except TypeError:
            raise TypeError('Selector Dialog: lvalue not int')
        else:
            choices.append(xbmcaddon.Addon().getLocalizedString(int(lvalue)))
    if heading != '':
        try:
            lheading = int(heading)
        except TypeError:
            raise TypeError('Selector Dialog: heading lvalue not int')
    else:
        lheading = ''
    result = xbmcgui.Dialog().select(heading=xbmcaddon.Addon().getLocalizedString(lheading), list=choices)
    if result != -1:
        if useindex:
            xbmcaddon.Addon().setSetting(settingid, str(result))
        else:
            xbmcaddon.Addon().setSetting(settingid, str(lvalues[result]))
        xbmcaddon.Addon().setSetting('%s-v' % settingid, str(result))
        return True
    else:
        return False

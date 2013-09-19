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
import traceback

import buggalo_client as client

import xbmc
import xbmcaddon
import xbmcgui

buggaloAddon = xbmcaddon.Addon(id='script.module.buggalo')

ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10


class BuggaloDialog(xbmcgui.WindowXMLDialog):
    THANK_YOU_VISIBLE_LABEL = 98
    DETAILS_VISIBLE_LABEL = 99
    CLOSE_BUTTON = 100
    SUBMIT_BUTTON = 101
    DETAILS_BUTTON = 102
    DETAILS_LIST = 103
    HEADING_LABEL = 110
    DETAILS_LINE1_LABEL = 111

    ERROR_MESSAGE_GROUP = 200
    DETAILS_GROUP = 201
    THANK_YOU_GROUP = 202
    THANK_YOU_LABEL = 203

    def __new__(cls, serviceUrl, gmailRecipient, heading, data):
        return super(BuggaloDialog, cls).__new__(cls, 'buggalo-dialog.xml', buggaloAddon.getAddonInfo('path'))

    def __init__(self, serviceUrl, gmailRecipient, heading, data):
        super(BuggaloDialog, self).__init__()
        self.serviceUrl = serviceUrl
        self.gmailRecipient = gmailRecipient
        self.heading = heading
        self.data = data
        self.detailsVisible = False

    def onInit(self):
        self.getControl(self.HEADING_LABEL).setLabel(self.heading)
        self.getControl(self.DETAILS_VISIBLE_LABEL).setVisible(not self.detailsVisible)
        self.getControl(self.THANK_YOU_VISIBLE_LABEL).setVisible(True)
        self.getControl(self.DETAILS_LINE1_LABEL).setLabel(buggaloAddon.getLocalizedString(91000) % self.data['addon']['name'].decode('utf-8', 'replace'))
        listControl = self.getControl(self.DETAILS_LIST)

        try:
            for group in sorted(self.data.keys()):
                values = self.data[group]
                if type(values) == dict:
                    item = xbmcgui.ListItem(label = '[B]%s[/B]' % group)
                    listControl.addItem(item)
                    keys = values.keys()
                    if group == 'userflow':
                        keys = sorted(keys)

                    for key in keys:
                            item = xbmcgui.ListItem(label='    %s' % key, label2=str(values[key]))
                            listControl.addItem(item)

                else:
                    item = xbmcgui.ListItem(label='[B]%s[/B]' % group, label2=str(values))
                    listControl.addItem(item)
        except Exception:
            item = xbmcgui.ListItem(label2=buggaloAddon.getLocalizedString(91008))
            listControl.addItem(item)

    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU]:
            self.close()

    def onClick(self, controlId):
        if controlId == self.CLOSE_BUTTON:
            self.close()

        elif controlId == self.SUBMIT_BUTTON:
            self.getControl(self.DETAILS_VISIBLE_LABEL).setVisible(True)
            self.getControl(self.THANK_YOU_VISIBLE_LABEL).setVisible(False)

            try:
                if self.serviceUrl is not None:
                    client.submitData(self.serviceUrl, self.data)
                elif self.gmailRecipient is not None:
                    client.emailData(self.gmailRecipient, self.data)
            except Exception:
                self.getControl(self.THANK_YOU_LABEL).setLabel(buggaloAddon.getLocalizedString(91009))
                (etype, value, tb) = sys.exc_info()
                traceback.print_exception(etype, value, tb)

            xbmc.sleep(2000)
            self.close()

        elif controlId == self.DETAILS_BUTTON:
            self.detailsVisible = not self.detailsVisible
            self.getControl(self.DETAILS_VISIBLE_LABEL).setVisible(not self.detailsVisible)
            if self.detailsVisible:
                self.getControl(self.DETAILS_BUTTON).setLabel(buggaloAddon.getLocalizedString(91007))
            else:
                self.getControl(self.DETAILS_BUTTON).setLabel(buggaloAddon.getLocalizedString(91006))

    def onFocus(self, control):
        pass
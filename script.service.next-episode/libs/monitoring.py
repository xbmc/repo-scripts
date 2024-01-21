# (c) Roman Miroshnychenko, 2023
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import logging

import xbmc
from xbmcgui import Dialog

from libs.addon import ADDON
from libs.gui import ui_string
from libs.medialibrary import get_item_details
from libs.utils import sync_library, sync_new_items, login, update_single_item

# Here ``addon`` is imported from another module to prevent a bug
# when username and hash are not stored in the addon settings.

__all__ = ['UpdateMonitor', 'initial_prompt']

DIALOG = Dialog()


class UpdateMonitor(xbmc.Monitor):
    """
    Monitors updating Kodi library
    """

    def onScanFinished(self, library):
        if library == 'video':
            sync_new_items()
            logging.debug('New items updated')

    def onNotification(self, sender, method, data):
        """
        Example data::

            16:05:29 T:8216  NOTICE: Sender: xbmc
            16:05:29 T:8216  NOTICE: Method: VideoLibrary.OnUpdate
            16:05:29 T:8216  NOTICE: Data: {"item":{"id":3,"type":"movie"},"playcount":1}

            16:10:14 T:8216  NOTICE: Sender: xbmc
            16:10:14 T:8216  NOTICE: Method: VideoLibrary.OnUpdate
            16:10:14 T:8216  NOTICE: Data: {"item":{"id":10,"type":"episode"},"playcount":1}
        """
        if method == 'VideoLibrary.OnUpdate' and 'playcount' in data:
            item = json.loads(data)['item']
            item.update(get_item_details(item['id'], item['type']))
            update_single_item(item)


def initial_prompt():
    """
    Show login prompt at first start
    """
    if (ADDON.getSetting('prompt_shown') != 'true' and
            not ADDON.getSetting('username') and
            DIALOG.yesno(ui_string(32012),
                         '[CR]'.join(
                             (ui_string(32013),
                              ui_string(32014),
                              ui_string(32015)
                             )))):
        if login() and DIALOG.yesno(ui_string(32016),
                                    '[CR]'.join((
                                        ui_string(32017),
                                        ui_string(32018)
                                    ))):
            sync_library()
        ADDON.setSetting('prompt_shown', 'true')

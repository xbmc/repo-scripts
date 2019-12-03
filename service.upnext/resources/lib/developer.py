# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
import xbmc
from . import pages
from . import utils


class Developer:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state

    @staticmethod
    def developer_play_back():
        episode = utils.load_test_data()
        next_up_page, next_up_page_simple, still_watching_page, still_watching_page_simple = (
            pages.set_up_developer_pages(episode))
        if utils.settings('windowMode') == '0':
            next_up_page.show()
        elif utils.settings('windowMode') == '1':
            next_up_page_simple.show()
        elif utils.settings('windowMode') == '2':
            still_watching_page.show()
        elif utils.settings('windowMode') == '3':
            still_watching_page_simple.show()
        utils.window('service.upnext.dialog', 'true')

        player = xbmc.Player()
        while (player.isPlaying() and not next_up_page.is_cancel()
               and not next_up_page.is_watch_now() and not still_watching_page.is_still_watching()
               and not still_watching_page.is_cancel()):
            xbmc.sleep(100)
            next_up_page.update_progress_control()
            next_up_page_simple.update_progress_control()
            still_watching_page.update_progress_control()
            still_watching_page_simple.update_progress_control()

        if utils.settings('windowMode') == '0':
            next_up_page.close()
        elif utils.settings('windowMode') == '1':
            next_up_page_simple.close()
        elif utils.settings('windowMode') == '2':
            still_watching_page.close()
        elif utils.settings('windowMode') == '3':
            still_watching_page_simple.close()
        utils.window('service.upnext.dialog', clear=True)

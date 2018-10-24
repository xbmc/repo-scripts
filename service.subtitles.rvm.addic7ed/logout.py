# coding: utf-8

from __future__ import unicode_literals
import os
from kodi_six.xbmcgui import Dialog
from addic7ed import addon
from addic7ed.utils import logger


cookies = os.path.join(addon.profile, 'cookies.pickle')
dialog = Dialog()


def do_logout():
    """
    Clean cookie file to logout from the site
    """
    if dialog.yesno(addon.get_ui_string(32013), addon.get_ui_string(32014),
                    addon.get_ui_string(32015)):
        if os.path.exists(cookies):
            try:
                os.remove(cookies)
            except OSError:
                pass
            else:
                if not os.path.exists(cookies):
                    dialog.notification(addon.ADDON_ID,
                                        addon.get_ui_string(32016),
                                        icon=addon.icon
                                        )
                    logger.debug('Cookies removed successfully.')
                    return
        dialog.notification(addon.ADDON_ID, addon.get_ui_string(32017),
                            icon='error')
        logger.error('Unable to remove cookies!')


if __name__ == '__main__':
    do_logout()

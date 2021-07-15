# -*- coding: utf-8 -*-
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from __future__ import unicode_literals

import xbmcgui

from .webclient import WebClientError

__all__ = ['Dialogs']


class Dialogs(object):

    def notify_error(self, error, show_dialog=False):
        heading = ''
        message = '{0}'.format(error)
        if isinstance(error, WebClientError):
            _ = self.initialize_gettext()
            heading = _('Connection error')
        else:
            self.log_error(message)

        if show_dialog:
            self.dialog_ok(message)
        else:
            self.dialog_notification_error(heading, message)

    def dialog_notification_error(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_ERROR, time, sound)

    def dialog_notification_info(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_INFO, time, sound)

    def dialog_notification_warning(self, heading, message="", time=0, sound=True):
        self.dialog_notification(heading, message, xbmcgui.NOTIFICATION_WARNING, time, sound)

    def dialog_notification(self, heading, message="", icon="", time=0, sound=True):

        _message = message if message else heading

        if heading \
                and heading != _message:
            _heading = '{0}: {1}'.format(self.name, heading)
        else:
            _heading = self.name

        xbmcgui.Dialog().notification(_heading, _message, icon, time, sound)

    def dialog_ok(self, line1, line2="", line3=""):

        if self.kodi_major_version() >= '19':
            xbmcgui.Dialog().ok(self.name, self._join_strings(line1, line2, line3))
        else:
            xbmcgui.Dialog().ok(self.name, line1, line2, line3)

    def dialog_progress_create(self, heading, line1="", line2="", line3=""):
        progress = xbmcgui.DialogProgress()

        if self.kodi_major_version() >= '19':
            progress.create(heading, self._join_strings(line1, line2, line3))
        else:
            progress.create(heading, line1, line2, line3)

        return progress

    def dialog_progress_update(self, progress, percent, line1="", line2="", line3=""):

        if self.kodi_major_version() >= '19':
            progress.update(percent, self._join_strings(line1, line2, line3))
        else:
            progress.update(percent, line1, line2, line3)

        return progress

    @staticmethod
    def dialog_select(heading, _list, **kwargs):
        return xbmcgui.Dialog().select(heading, _list, **kwargs)

    @staticmethod
    def _join_strings(line1, line2="", line3=""):

        lines = [line1]
        if line2:
            lines.append(line2)
        if line3:
            lines.append(line3)

        return '[CR]'.join(lines)

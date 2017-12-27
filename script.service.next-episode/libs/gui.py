# coding: utf-8
# Created on: 15.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from xbmc import executebuiltin
from xbmcaddon import Addon
from xbmcgui import ACTION_NAV_BACK
import pyxbmct

addon = Addon('script.service.next-episode')


def ui_string(id_):
    """
    Get localized UI string

    :param id_: string ID
    :type id_: int
    :return: localized string
    :rtype: str
    """
    return addon.getLocalizedString(id_).encode('utf-8')


@contextmanager
def busy_spinner():
    """
    Show busy spinner for long operations

    This context manager guarantees that a busy spinner will be closed
    even in the event of an unhandled exception.
    """
    executebuiltin('ActivateWindow(10138)')  # Busy spinner on
    try:
        yield
    finally:
        executebuiltin('Dialog.Close(10138)')  # Busy spinner off


class NextEpDialog(pyxbmct.AddonDialogWindow):
    """
    Base class for addon dialogs
    """
    __metaclass__ = ABCMeta

    def __init__(self, width, height, rows, columns, title=''):
        super(NextEpDialog, self).__init__(title)
        self.setGeometry(width, height, rows, columns)
        self._set_controls()
        self._set_connections()
        self._set_navigation()

    @abstractmethod
    def _set_controls(self):
        pass

    @abstractmethod
    def _set_connections(self):
        self.connect(ACTION_NAV_BACK, self.close)

    @abstractmethod
    def _set_navigation(self):
        pass

    def setAnimation(self, control):
        control.setAnimations(
            [('WindowOpen', 'effect=fade start=0 end=100 time=250'),
             ('WindowClose', 'effect=fade start=100 end=0 time=250')]
        )

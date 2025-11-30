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

from abc import ABC, abstractmethod
from contextlib import contextmanager

import pyxbmct

from xbmc import executebuiltin
from xbmcgui import ACTION_NAV_BACK

from .addon import ADDON

__all__ = ['NextEpDialog', 'ui_string', 'busy_spinner']


def ui_string(id_):
    """
    Get localized UI string

    :param id_: string ID
    :type id_: int
    :return: localized string
    :rtype: str
    """
    return ADDON.getLocalizedString(id_)


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


class NextEpDialog(ABC, pyxbmct.AddonDialogWindow):
    """
    Base class for addon dialogs
    """
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

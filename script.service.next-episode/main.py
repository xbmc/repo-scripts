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

import logging
import sys

import pyxbmct

from libs.exception_logger import catch_exception
from libs.gui import NextEpDialog, ui_string
from libs.logger import initialize_logging
from libs.utils import sync_library, login


class MainDialog(NextEpDialog):
    """
    Main UI dialog
    """
    def _set_controls(self):
        self._sync_library_btn = pyxbmct.Button(ui_string(32002))
        self.placeControl(self._sync_library_btn, 0, 0)
        self._enter_login_btn = pyxbmct.Button(ui_string(32001))
        self.placeControl(self._enter_login_btn, 1, 0)

    def _set_connections(self):
        super(MainDialog, self)._set_connections()
        self.connect(self._sync_library_btn, sync_library)
        self.connect(self._enter_login_btn, self._enter_login)

    def _set_navigation(self):
        self._sync_library_btn.controlUp(self._enter_login_btn)
        self._sync_library_btn.controlDown(self._enter_login_btn)
        self._enter_login_btn.controlUp(self._sync_library_btn)
        self._enter_login_btn.controlDown(self._sync_library_btn)
        self.setFocus(self._sync_library_btn)

    def _enter_login(self):
        self.close()
        login()
        self.doModal()


if __name__ == '__main__':
    initialize_logging()
    with catch_exception(logging.error):
        if 'sync_library' in sys.argv:
            sync_library()
        elif 'login' in sys.argv:
            login()
        else:
            main_dialog = MainDialog(520, 160, 2, 1, 'next-episode.net')
            main_dialog.doModal()
            del main_dialog

# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: romanvm@yandex.ua
# License: GPL v. 3 <http://www.gnu.org/licenses/gpl-3.0.en.html>

import pyxbmct
from libs.gui import NextEpDialog, ui_string
from libs.commands import sync_library, login


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
    main_dialog = MainDialog(520, 160, 2, 1, 'next-episode.net')
    main_dialog.doModal()
    del main_dialog

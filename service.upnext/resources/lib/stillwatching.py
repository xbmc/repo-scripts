# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from popup import Popup


class StillWatching(Popup):
    stillwatching = False

    def set_still_watching(self, stillwatching):
        self.stillwatching = stillwatching

    def is_still_watching(self):
        return self.stillwatching

    def confirm(self):
        self.set_still_watching(True)

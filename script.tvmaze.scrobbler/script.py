# coding: utf-8
# (c) Roman Miroshnychenko <roman1972@gmail.com> 2020
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

"""Script entry point"""

from __future__ import absolute_import, unicode_literals

from libs.gui import DIALOG
from libs.kodi_service import debug_exception, GETTEXT
from libs.scrobbling_service import get_menu_actions

_ = GETTEXT


def main():
    """Main scrobbler menu"""
    actions = get_menu_actions()
    menu = [action[0] for action in actions]
    result = DIALOG.select(_('TVmaze Scrobbler Menu'), menu)
    if result >= 0:
        action = actions[result][1]
        action()


if __name__ == '__main__':
    with debug_exception():
        main()

"""
PyXBMCt framework package

PyXBMCt is a mini-framework for creating Kodi (XBMC) Python addons
with arbitrary UI made of Controls - decendants of xbmcgui.Control class.
The framework uses image textures from Kodi Confluence skin.

Licence: GPL v.3 http://www.gnu.org/licenses/gpl.html
"""

from addonwindow import *
from addonskin import BaseSkin

__all__ = [
    'ALIGN_LEFT',
    'ALIGN_RIGHT',
    'ALIGN_CENTER_X',
    'ALIGN_CENTER_Y',
    'ALIGN_CENTER',
    'ALIGN_TRUNCATED',
    'ALIGN_JUSTIFY',
    'ACTION_PREVIOUS_MENU',
    'ACTION_NAV_BACK',
    'ACTION_MOVE_LEFT',
    'ACTION_MOVE_RIGHT',
    'ACTION_MOVE_UP',
    'ACTION_MOVE_DOWN',
    'ACTION_MOUSE_WHEEL_UP',
    'ACTION_MOUSE_WHEEL_DOWN',
    'ACTION_MOUSE_DRAG',
    'ACTION_MOUSE_MOVE',
    'ACTION_MOUSE_LEFT_CLICK',
    'AddonWindowError',
    'Label',
    'FadeLabel',
    'TextBox',
    'Image',
    'Button',
    'RadioButton',
    'Edit',
    'List',
    'Slider',
    'BlankFullWindow',
    'BlankDialogWindow',
    'AddonDialogWindow',
    'AddonFullWindow',
    'Skin',
    'skin',
    'BaseSkin'
]

# coding: utf-8
# Module: skin
# Created on: 04.03.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# Licence: GPL v.3 <http://www.gnu.org/licenses/gpl.html>
"""Classes for defining the appearance of PyXBMCt Windows and Controls"""

from __future__ import unicode_literals
import os
from abc import ABCMeta, abstractmethod
from six import with_metaclass
import xbmc
from xbmcaddon import Addon


class BaseSkin(with_metaclass(ABCMeta, object)):
    """
    Abstract class for creating fully customized skins

    .. warning:: This class is meant for subclassing and cannot be instantiated directly!
        A sublcass must implement all the following properties.
    """
    @abstractmethod
    def images(self):
        """
        Get the base directory for image files

        :rtype: str
        """
        return

    @abstractmethod
    def x_margin(self):
        """
        Get horizontal adjustment for the header background
        if the main background has transparent edges.

        :rtype: int
        """
        return

    @abstractmethod
    def y_margin(self):
        """
        Get vertical adjustment for the header background
        if the main background has transparent edges.

        :rtype: int
        """
        return

    @abstractmethod
    def title_bar_x_shift(self):
        """
        Get horizontal adjustment for title bar texture

        :rtype: int
        """
        return

    @abstractmethod
    def title_bar_y_shift(self):
        """
        Get vertical adjustment for title bar texture

        :rtype: int
        """
        return

    @abstractmethod
    def title_back_y_shift(self):
        """
        Get header position adjustment
        if the main background has visible borders.

        :rtype: int
        """
        return

    @abstractmethod
    def header_height(self):
        """
        Get the height of a window header
        (for the title background and the title label).

        :rtype: int
        """
        return

    @abstractmethod
    def close_btn_width(self):
        """
        Get the width of the top-right close button

        :rtype: int
        """
        return

    @abstractmethod
    def close_btn_height(self):
        """
        Get the height of the top-right close button

        :rtype: int
        """
        return

    @abstractmethod
    def close_btn_x_offset(self):
        """
        Get close button horizontal adjustment

        :rtype: int
        """
        return

    @abstractmethod
    def close_btn_y_offset(self):
        """
        Get close button vertical adjustment

        :rtype: int
        """
        return

    @abstractmethod
    def header_align(self):
        """
        Get a numeric value for header text alignment

        For example:

        - ``0``: left
        - ``6``: center

        :rtype: int
        """
        return

    @abstractmethod
    def header_text_color(self):
        """
        Get the color of the header text

        :rtype: str
        """
        return

    @abstractmethod
    def background_img(self):
        """
        Get dialog background texture

        :rtype: str
        """
        return

    @abstractmethod
    def title_background_img(self):
        """
        Get title bar background texture

        :rtype: str
        """
        return

    @abstractmethod
    def close_button_focus(self):
        """
        Get close button focused texture

        :rtype: str
        """
        return

    @abstractmethod
    def close_button_no_focus(self):
        """
        Get close button unfocused texture

        :rtype: str
        """
        return

    @abstractmethod
    def main_bg_img(self):
        """
        Get fullscreen background for
        :class:`AddonFullWindow<pyxbmct.addonwindow.AddonFullWindow>` class

        :rtype: str
        """
        return


class Skin(BaseSkin):
    """
    Skin class

    Defines parameters that control
    the appearance of PyXBMCt windows and controls.
    """
    def __init__(self):
        kodi_version = xbmc.getInfoLabel('System.BuildVersion')[:2]
        # Kodistubs return an empty string
        if kodi_version and kodi_version >= '17':
            self._estuary = True
        else:
            self._estuary = False
        self._texture_dir = os.path.join(Addon('script.module.pyxbmct').getAddonInfo('path'),
                                         'lib', 'pyxbmct', 'textures')

    @property
    def estuary(self):
        """
        Get or set a boolean property that defines the look of PyXBMCt elements:

        - ``True`` -- use Estuary skin appearance
        - ``False`` -- use Confluence skin appearance.

        :rtype: bool
        """
        return self._estuary

    @estuary.setter
    def estuary(self, value):
        if not isinstance(value, bool):
            raise TypeError('estuary property value must be bool!')
        self._estuary = value

    @property
    def images(self):
        if self.estuary:
            return os.path.join(self._texture_dir, 'estuary')
        else:
            return os.path.join(self._texture_dir, 'confluence')

    @property
    def x_margin(self):
        if self.estuary:
            return 0
        else:
            return 5

    @property
    def y_margin(self):
        if self.estuary:
            return 0
        else:
            return 5

    @property
    def title_bar_x_shift(self):
        if self.estuary:
            return 20
        else:
            return 0

    @property
    def title_bar_y_shift(self):
        if self.estuary:
            return 8
        else:
            return 4

    @property
    def title_back_y_shift(self):
        if self.estuary:
            return 0
        else:
            return 4

    @property
    def header_height(self):
        if self.estuary:
            return 45
        else:
            return 35

    @property
    def close_btn_width(self):
        if self.estuary:
            return 35
        else:
            return 60

    @property
    def close_btn_height(self):
        if self.estuary:
            return 30
        else:
            return 30

    @property
    def close_btn_x_offset(self):
        if self.estuary:
            return 50
        else:
            return 70

    @property
    def close_btn_y_offset(self):
        if self.estuary:
            return 7
        else:
            return 4

    @property
    def header_align(self):
        if self.estuary:
            return 0
        else:
            return 6

    @property
    def header_text_color(self):
        if self.estuary:
            return ''
        else:
            return '0xFFFFA500'

    @property
    def background_img(self):
        return os.path.join(self.images, 'AddonWindow', 'ContentPanel.png')

    @property
    def title_background_img(self):
        return os.path.join(self.images, 'AddonWindow', 'dialogheader.png')

    @property
    def close_button_focus(self):
        return os.path.join(self.images, 'AddonWindow', 'DialogCloseButton-focus.png')

    @property
    def close_button_no_focus(self):
        return os.path.join(self.images, 'AddonWindow', 'DialogCloseButton.png')

    @property
    def main_bg_img(self):
        return os.path.join(self.images, 'AddonWindow', 'SKINDEFAULT.jpg')

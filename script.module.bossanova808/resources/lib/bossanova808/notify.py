# -*- coding: utf-8 -*-

import xbmcgui
from .constants import *


class Notify:

    @staticmethod
    def kodi_notification(message, duration=5000, icon=xbmcgui.NOTIFICATION_INFO):
        """
        Send a custom notification to the user via the Kodi GUI

        :param message: the message to send
        :param duration: time to display notification in milliseconds, default 5000
        :param icon: xbmcgui.NOTIFICATION_INFO (default), xbmcgui.NOTIFICATION_WARNING, or xbmcgui.NOTIFICATION_ERROR (or custom icon)
        :return: None
        """
        dialog = xbmcgui.Dialog()

        dialog.notification(heading=ADDON_NAME,
                            message=message,
                            icon=icon,
                            time=duration)

    @staticmethod
    def info(message, duration=5000):
        """
        Send an info level notification to the user via the Kodi GUI

        :param message: the message to display
        :param duration: the duration to show the message, default 5000ms
        :return:
        """
        Notify.kodi_notification(message, duration, xbmcgui.NOTIFICATION_INFO)

    @staticmethod
    def warning(message, duration=5000):
        """
        Send a warning notification to the user via the Kodi GUI

        :param message: the message to display
        :param duration: the duration to show the message, default 5000ms
        :return:
        """
        Notify.kodi_notification(message, duration, xbmcgui.NOTIFICATION_WARNING)

    @staticmethod
    def error(message, duration=5000):
        """
        Send an error level notification to the user via the Kodi GUI

        :param message: the message to display
        :param duration: the duration to show the message, default 5000ms
        :return:
        """
        Notify.kodi_notification(message, duration, xbmcgui.NOTIFICATION_ERROR)
# noinspection PyUnresolvedReferences
import xbmcgui
# noinspection PyPackages
from .constants import ADDON_NAME


class Notify:

    @staticmethod
    def kodi_notification(message: str, duration: int = 5000, icon: str = xbmcgui.NOTIFICATION_INFO) -> None:
        """
        Send a custom notification to the user via the Kodi GUI

        :param message: the message to send
        :param duration: time to display notification in milliseconds, default 5000
        :param icon: xbmcgui.NOTIFICATION_INFO (default), xbmcgui.NOTIFICATION_WARNING, or xbmcgui.NOTIFICATION_ERROR, or custom icon
        """
        dialog = xbmcgui.Dialog()
        dialog.notification(heading=ADDON_NAME,
                            message=message,
                            icon=icon,
                            time=duration)

    @staticmethod
    def info(message: str, duration: int = 5000) -> None:
        """
        Send an info level notification to the user via the Kodi GUI

        :param message: the message to display
        :param duration: the duration to show the message, default 5000 ms
        """
        Notify.kodi_notification(message, duration, xbmcgui.NOTIFICATION_INFO)

    @staticmethod
    def warning(message: str, duration: int = 5000) -> None:
        """
        Send a warning notification to the user via the Kodi GUI

        :param message: the message to display
        :param duration: the duration to show the message, default 5000 ms
        """
        Notify.kodi_notification(message, duration, xbmcgui.NOTIFICATION_WARNING)

    @staticmethod
    def error(message: str, duration: int = 5000) -> None:
        """
        Send an error level notification to the user via the Kodi GUI

        :param message: the message to display
        :param duration: the duration to show the message, default 5000 ms
        """
        Notify.kodi_notification(message, duration, xbmcgui.NOTIFICATION_ERROR)

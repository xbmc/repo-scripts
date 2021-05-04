import xbmc
from xbmcgui import Dialog

# Prevents circular import problems
import util.settings
from util.addon_info import ADDON, ADDON_NAME, ADDON_ICON


def translate(msg_id):
    """
    Retrieve a localized string by id.

    :type msg_id: int
    :param msg_id: The id of the localized string.
    :rtype: unicode
    :return: The localized string. Empty if msg_id is not an integer.
    """
    return ADDON.getLocalizedString(msg_id) if isinstance(msg_id, int) else ""


def notify(message, duration=5000, image=ADDON_ICON, level=xbmc.LOGDEBUG, sound=True):
    """
    Display a Kodi notification and log the message.

    :type message: unicode
    :param message: the message to be displayed (and logged).
    :type duration: int
    :param duration: the duration the notification is displayed in milliseconds (defaults to 5000)
    :type image: unicode
    :param image: the path to the image to be displayed on the notification (defaults to ``icon.png``)
    :type level: int
    :param level: (Optional) the log level (supported values are found at xbmc.LOG...)
    :type sound: bool
    :param sound: (Optional) Whether or not to play a sound with the notification. (defaults to ``True``)
    """
    if message:
        debug(message, level)
        if (util.settings.get_value(util.settings.notifications_enabled) and not
                (util.settings.get_value(util.settings.notify_when_idle) and xbmc.Player().isPlaying())):
            Dialog().notification(ADDON_NAME.encode(), message.encode(), image.encode(), duration, sound)


def debug(message, level=xbmc.LOGDEBUG):
    """
    Write a debug message to xbmc.log

    :type message: unicode
    :param message: the message to log
    :type level: int
    :param level: (Optional) the log level (supported values are found at xbmc.LOG...)
    """
    if util.settings.get_value(util.settings.debugging_enabled):
        for line in message.splitlines():
            xbmc.log(msg=f"{ADDON_NAME}: {line}", level=level)

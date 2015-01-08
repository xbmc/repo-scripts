import xbmcgui
from resources.lib.helper import settings
from resources.lib import helper
from resources import config


def create():
    return xbmcgui.Dialog()


def create_ok(*msg):
    return create().ok(config.__NAME__, *msg)


def create_yes_no(*lines):
    return create().yesno(config.__NAME__, *lines)


def create_notification(message):
    dialog = create()
    dialog.notification(config.__NAME__, message,  settings.getAddonInfo("icon"), 5000)


def create_error_notification(message):
    create_notification(helper.language(32018) + ": " + message)


def create_select(options):
    """
    Create a select dialog from options
    Returns the position of the highlighted item as an integer.
    :param options:list
    :return:integer
    """
    return create().select(config.__NAME__, options)

import xbmcaddon

NO_DESCRIPTION = 30000

NO_STREAM_AVAILABLE_TITLE = 30100
NO_STREAM_AVAILABLE_LINE1 = 30101
NO_STREAM_AVAILABLE_LINE2 = 30102

CLEAR_CACHE = 30104
CLEAR_NOTIFICATIONS = 30108
DONE = 30105

LOAD_ERROR_TITLE = 30150
LOAD_ERROR_LINE1 = 30151
LOAD_ERROR_LINE2 = 30152

NOTIFICATION_TEMPLATE = 30200

WATCH_CHANNEL = 30300
REMIND_PROGRAM = 30301
DONT_REMIND_PROGRAM = 30302

def strings(id, replacements = None):
    string = xbmcaddon.Addon(id = 'script.tvguide').getLocalizedString(id)
    if replacements is not None:
        return string % replacements
    else:
        return string
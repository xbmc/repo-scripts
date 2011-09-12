import xbmcaddon

NO_DESCRIPTION = 30000

NO_STREAM_AVAILABLE_TITLE = 30100
NO_STREAM_AVAILABLE_LINE1 = 30101
NO_STREAM_AVAILABLE_LINE2 = 30102

CLEAR_CACHE = 30104
CLEAR_CACHE_DONE = 30105

LOAD_ERROR_TITLE = 30110
LOAD_ERROR_LINE1 = 30111
LOAD_ERROR_LINE2 = 30112

def strings(id, replacements = None):
    string = xbmcaddon.Addon(id = 'script.tvguide').getLocalizedString(id)
    if replacements is not None:
        return string % replacements
    else:
        return string
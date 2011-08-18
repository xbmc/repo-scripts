import xbmcaddon

NO_DESCRIPTION = 30000

NO_STREAM_AVAILABLE_TITLE = 30100
NO_STREAM_AVAILABLE_LINE1 = 30101
NO_STREAM_AVAILABLE_LINE2 = 30102

def strings(id, replacements = None):
    string = xbmcaddon.Addon(id = 'script.tvguide').getLocalizedString(id)
    if replacements is not None:
        return string % replacements
    else:
        return string
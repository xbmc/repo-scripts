import xbmc
import xbmcaddon
import xbmcgui

_name = "EpisodeHunter"


def Debug(msg):
    settings = xbmcaddon.Addon("script.episodeHunter")
    debug = settings.getSetting("debug")
    if debug:
        try:
            print _name + ": " + msg
        except Exception:
            try:
                print _name + ": You are trying to print some bad string, " + msg.encode("utf-8", "ignore")
            except Exception:
                print _name + ": You are trying to print a bad string, I can not even print it"



def notification(header, message, level=0):
    settings = xbmcaddon.Addon("script.episodeHunter")
    debug = settings.getSetting("debug")
    if debug or level == 0:
        xbmc.executebuiltin("XBMC.Notification(%s,%s,%i,%s)" % (header, message, 5000, settings.getAddonInfo("icon")))


# Do we have username and api key?
def isSettingsOkey(daemon=False, silent=False):
    settings = xbmcaddon.Addon("script.episodeHunter")
    language = settings.getLocalizedString

    if settings.getSetting("username") == "" and settings.getSetting("api_key") == "":
        if silent:
            return False
        elif daemon:
            notification(_name, language(32014))
        else:
            xbmcgui.Dialog().ok(_name, language(32014))
        return False

    elif settings.getSetting("username") == "":
        if silent:
            return False
        if daemon:
            notification(_name, language(32012))
        else:
            xbmcgui.Dialog().ok(_name, language(32012))
        return False

    elif settings.getSetting("api_key") == "":
        if silent:
            return False
        if daemon:
            notification(_name, language(32013))
        else:
            xbmcgui.Dialog().ok(_name, language(32013))
        return False

    return True


def notSeenMovie(imdb, array):
    for x in array:
        if imdb == x['imdb_id']:
            return False
    return True


def seenEpisode(e, array):
    for i in range(0, len(array)):
        if e == array[i]:
            return True
    return False


def isnotin(test, array):
    for x in array:
        if test in x:
            return False
    return True


def to_seconds(timestr):
    seconds = 0
    for part in timestr.split(':'):
        seconds = seconds * 60 + int(part)
    return seconds

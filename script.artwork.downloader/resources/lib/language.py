#import modules
import xbmc
import xbmcaddon
def get_abbrev():
    language = xbmcaddon.Addon().getSetting("limit_language").upper()
    translates = {
        'CHINESE'       : 'zh',
        'DUTCH'         : 'nl',
        'ENGLISH'       : 'en',
        'FINNISH'       : 'fi',
        'FRENCH'        : 'fr',
        'GERMAN'        : 'de',
        'HUNGARIAN'     : 'hu',
        'ITALIAN'       : 'it',
        'JAPANESE'      : 'ja',
        'POLISH'        : 'pl',
        'PORTUGUESE'    : 'pt',
        'RUSSIAN'       : 'ru',
        'SPANISH'       : 'es',
        'SWEDISH'       : 'sv'
    }
    if language in translates:
        return translates[language]
    else:
        ### Default to English
        return 'en'
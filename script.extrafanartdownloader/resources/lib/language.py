import xbmc

def get_abbrev():
    language = xbmc.getLanguage().upper()
    translates = {
        'ENGLISH':'en',
        'GERMAN': 'de'
    }
    if language in translates:
        return translates[language]
    else:
        ### Default to English
        return 'en'
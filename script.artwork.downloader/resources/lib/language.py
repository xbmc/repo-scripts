#import modules
import xbmc
import xbmcaddon

LANGUAGES = {'Albanian' : 'sq',
            'Arabic'    : 'ar',
            'Belarusian': 'hy',
            'Bosnian'   : 'bs',
            'Bulgarian' : 'bg',
            'Catalan'   : 'ca',
            'Chinese'   : 'zh',
            'Croatian'  : 'hr',
            'Czech'     : 'cs',
            'Danish'    : 'da',
            'Dutch'     : 'nl',
            'English'   : 'en',
            'Estonian'  : 'et',
            'Persian'   : 'fa',
            'Finnish'   : 'fi',
            'French'    : 'fr',
            'German'    : 'de',
            'Greek'     : 'el',
            'Hebrew'    : 'he',
            'Hindi'     : 'hi',
            'Hungarian' : 'hu',
            'Icelandic' : 'is',
            'Indonesian': 'id',
            'Italian'   : 'it',
            'Japanese'  : 'ja',
            'Korean'    : 'ko',
            'Latvian'   : 'lv',
            'Lithuanian': 'lt',
            'Macedonian': 'mk',
            'Norwegian' : 'no',
            'Polish'    : 'pl',
            'Portuguese': 'pt',
            'Portuguese (Brazil)': 'pb',
            'Romanian'  : 'ro',
            'Russian'   : 'ru',
            'Serbian'   : 'sr',
            'Slovak'    : 'sk',
            'Slovenian' : 'sl',
            'Spanish'   : 'es',
            'Swedish'   : 'sv',
            'Thai'      : 'th',
            'Turkish'   : 'tr',
            'Ukrainian' : 'uk',
            'Vietnamese': 'vi',
            'BosnianLatin': 'bs',
            'Farsi'     : 'fa',
            'Serbian (Cyrillic)': 'sr',
            'Chinese (Traditional)' : 'zh',
            'Chinese (Simplified)'  : 'zh'}

def get_abbrev():
    language = xbmcaddon.Addon().getSetting('limit_preferred_language')
    if language in LANGUAGES:
        return LANGUAGES[language]
    else:
        ### Default to English
        return 'en'
        
def get_language(abbrev):
    try:
        lang_string = (key for key,value in LANGUAGES.items() if value == abbrev).next()
    except StopIteration:
        lang_string = 'n/a'
    return lang_string
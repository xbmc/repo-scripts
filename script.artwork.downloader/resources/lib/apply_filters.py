#import modules
import xbmc
import xbmcaddon

### import libraries
from resources.lib.fileops import fileops
from resources.lib.settings import settings
pref_language = xbmcaddon.Addon().getSetting("limit_preferred_language")

class apply_filters:

    def __init__(self):
        self.settings = settings()
        self.settings._get_limit()

    def do_filter(self, art_type, mediatype, artwork, downloaded_artwork, language, disctype = ''):
        if art_type   == 'fanart':
            return self.fanart(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'extrafanart':
            return self.extrafanart(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'extrathumbs':
            return self.extrathumbs(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'poster':
            return self.poster(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'seasonposter':
            return self.seasonposter(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'banner':
            return self.banner(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'seasonbanner':
            return self.seasonbanner(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'clearlogo':
            return self.clearlogo(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'clearart':
            return self.clearart(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'characterart':
            return self.characterart(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'landscape':
            return self.landscape(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'seasonlandscape':
            return self.seasonlandscape(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'defaultthumb':
            return self.defaultthumb(mediatype, artwork, downloaded_artwork, language)

        elif art_type == 'discart':
            return self.discart(mediatype, artwork, downloaded_artwork, language, disctype)
        else:
            return [False, 'Unrecognised art_type']

    def fanart(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number fanart reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Minimal size
        elif self.settings.limit_artwork and 'height' in artwork and (mediatype == 'movie' and artwork['height'] < self.settings.limit_size_moviefanart) or (mediatype == 'tvshow' and artwork['height'] < self.settings.limit_size_tvshowfanart):
            reason = 'Size was to small: %s' % artwork['height'] 
            limited = True
        # Minimal rating
        elif self.settings.limit_artwork and artwork['rating'] < self.settings.limit_extrafanart_rating:
            reason = 'Rating too low: %s' % artwork['rating']
            limited = True
        # Has text       
        elif self.settings.limit_artwork and 'series_name' in artwork and self.settings.limit_notext and artwork['series_name']:
            reason = 'Has text'
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [language, 'n/a']:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
        
    def extrafanart(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if self.settings.limit_artwork and downloaded_artwork >= self.settings.limit_extrafanart_max:
            reason = 'Max number extrafanart reached: %s' % self.settings.limit_extrafanart_max
            limited = True
        # Minimal size
        elif self.settings.limit_artwork and 'height' in artwork and (mediatype == 'movie' and artwork['height'] < self.settings.limit_size_moviefanart) or (mediatype == 'tvshow' and artwork['height'] < self.settings.limit_size_tvshowfanart):
            reason = 'Size was to small: %s' % artwork['height'] 
            limited = True
        # Minimal rating
        elif self.settings.limit_artwork and artwork['rating'] < self.settings.limit_extrafanart_rating:
            reason = 'Rating too low: %s' % artwork['rating']
            limited = True
        # Has text
        elif self.settings.limit_artwork and 'series_name' in artwork and self.settings.limit_notext and artwork['series_name']:
            reason = 'Has text'
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
        return [limited, reason]

    def extrathumbs(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_extrathumbs_max:
            reason = 'Max number extrathumbs reached: %s' % self.settings.limit_extrathumbs_max
            limited = True
        # Minimal size
        elif self.settings.limit_extrathumbs and 'height' in artwork and artwork['height'] < int('169'):
            reason = 'Size was to small: %s' % artwork['height']
            limited = True
        return [limited, reason]
        
    def poster(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number poster reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Minimal size
        elif self.settings.limit_extrathumbs and 'height' in artwork and artwork['height'] < int('169'):
            reason = 'Size was to small: %s' % artwork['height']
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]

    def seasonposter(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number seasonposter reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Minimal size
        elif self.settings.limit_extrathumbs and 'height' in artwork and artwork['height'] < int('169'):
            reason = 'Size was to small: %s' % artwork['height']
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]

    def banner(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number banner reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
        
    def seasonbanner(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number seasonbanner reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Has season
        if not 'season' in artwork:
            reason = 'No season'
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
        
    def clearlogo(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number logos reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
        
    def clearart(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number clearart reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]

    def characterart(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number characterart reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
        
    def landscape(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number landscape reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
        
    def seasonlandscape(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number seasonthumb reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]

    def defaultthumb(self, mediatype, artwork, downloaded_artwork, language):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number defaultthumb reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]        

    def discart(self, mediatype, artwork, downloaded_artwork, language, disctype):
        limited = False
        reason = ''
        # Maximum number
        if downloaded_artwork >= self.settings.limit_artwork_max:
            reason = 'Max number discart reached: %s' % self.settings.limit_artwork_max
            limited = True
        # Correct discnumber
        elif not artwork['discnumber'] == '1':
            reason = "Doesn't match preferred discnumber: 1"
            limited = True
        # Correct discnumber
        elif not artwork['disctype'] == disctype:
            reason = "Doesn't match preferred disctype: %s" %disctype
            limited = True
        # Correct language
        elif self.settings.limit_artwork and not artwork['language'] in [ language, 'n/a' ]:
            reason = "Doesn't match preferred language: %s" % pref_language
            limited = True
        return [limited, reason]
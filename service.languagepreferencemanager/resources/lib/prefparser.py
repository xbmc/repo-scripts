import re
import xbmc, xbmcaddon
from langcodes import *
from logger import log, LOG_NONE, LOG_INFO, LOG_DEBUG, LOG_ERROR


class PrefParser:
    
    def __init__( self ):
        addon = xbmcaddon.Addon()
        self.logLevel = addon.getSetting('log_level')
        if self.logLevel and len(self.logLevel) > 0:
            self.logLevel = int(self.logLevel)
        else:
            self.logLevel = LOG_INFO
        self.custom_prefs_delim = r'>'
        self.custom_genre_prefs_delim = r'|'
        self.custom_g_t_pref_delim = r'#'
        self.custom_g_t_delim = r','
        self.custom_condSub_delim = r':'
        
    def parsePrefString(self, pref_string):
        preferences = []
        if not pref_string:
            return preferences
        
        if (pref_string.find(self.custom_genre_prefs_delim) > 0):
            c_prefs = pref_string.split(self.custom_genre_prefs_delim)
        else:
            c_prefs = [pref_string]
            
        for s_pref in c_prefs:
            pref = self.parseSinglePref(s_pref)
            if (pref):
                preferences.append(pref)
                
        if (len(preferences) == 1
            and isinstance(preferences[0], list)):
            preferences = preferences[0]

        return preferences
    
    def parseSinglePref(self, s_pref):
        if (s_pref.find(self.custom_g_t_pref_delim) > 0):
            g_pref = s_pref.split(self.custom_g_t_pref_delim)
            if len(g_pref ) != 2:
                log(LOG_INFO, 'Parse error: {0}'.format(g_pref))
                return []
            else:
                return (set(map(lambda x:x.lower(), g_pref[0].split(self.custom_g_t_delim))),
                        self.parsePref(g_pref[1]))
        else:
            return (set(), self.parsePref(s_pref))
            
    def parsePref(self, prefs):
        lang_prefs = []
        if (prefs.find(self.custom_prefs_delim) > 0):
            s_prefs = prefs.split(self.custom_prefs_delim)
        else:
            s_prefs = [prefs]
        for pref in s_prefs:
            # custom cond sub pref
            if (pref.find(self.custom_condSub_delim) > 0):
                pref = pref.split(self.custom_condSub_delim)
                if len(pref) != 2:
                            log(LOG_INFO, 'Custom cond subs prefs parse error: {0}'.format(pref))
                else:
                    temp_a = (languageTranslate(pref[0], 3, 0), pref[0])
                     # Searching if a sub tag is present (like Eng:Jpn-ff to prioritize Forced tracks of another language)
                    if pref[1].endswith('-ff'):
                        ff_tag = True
                        pref[1] = pref[1].rstrip('-ff')
                    else:
                        ff_tag = False
                    # Searching if a sub tag is present (like Eng:Eng-ss to prioritize Signs&Songs tracks)
                    if pref[1].endswith('-ss'):
                        ss_tag = 'true'
                        pref[1] = pref[1].rstrip('-ss')
                    else:
                        ss_tag = 'false'
                    temp_s = (languageTranslate(pref[1], 3, 0), pref[1])
                    if (temp_a[0] and temp_a[1] and temp_s[0] and temp_s[1]):
                        if (temp_s[1] == 'non' or ff_tag):
                            forced_tag = 'true'
                        else:
                            forced_tag = 'false'
                        lang_prefs.append((temp_a[0], temp_a[1], temp_s[0], temp_s[1], forced_tag, ss_tag))
                    else:
                        log(LOG_INFO, 'Custom cond sub prefs: lang code not found in db!'\
                                 ' Please report this: {0}:{1}'.format(temp_a, temp_s))
            # custom audio or subtitle pref                            
            else:
                temp_pref = (languageTranslate(pref, 3, 0), pref)
                if temp_pref[0]:
                    lang_prefs.append(temp_pref)
                else:
                    log(LOG_INFO, 'Custom audio prefs: lang code {0} not found in db!'\
                             ' Please report this'.format(pref))
        return lang_prefs

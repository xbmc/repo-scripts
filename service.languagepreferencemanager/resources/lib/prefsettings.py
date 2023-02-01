import xbmc, xbmcaddon
import re
from langcodes import *
from prefparser import PrefParser

LOG_NONE = 0
LOG_ERROR = 1
LOG_INFO = 2
LOG_DEBUG = 3
    


class settings():

    def log(self, level, msg):
        if level <= self.logLevel:
            if level == LOG_ERROR:
                l = xbmc.LOGERROR
            elif level == LOG_INFO:
                l = xbmc.LOGINFO
            elif level == LOG_DEBUG:
                l = xbmc.LOGDEBUG
            xbmc.log("[Language Preference Manager]: " + str(msg), l)

    def init(self):
        addon = xbmcaddon.Addon()
        self.logLevel = addon.getSetting('log_level')
        if self.logLevel and len(self.logLevel) > 0:
            self.logLevel = int(self.logLevel)
        else:
            self.logLevel = LOG_INFO
            
        self.custom_audio = []
        self.custom_subs = []
        self.custom_condsub = []

        self.service_enabled = addon.getSetting('enabled') == 'true'
    
    def __init__( self ):
        self.init()
        
    def readSettings(self):
        self.readPrefs()
        self.readCustomPrefs()
        self.log(LOG_DEBUG,
                 '\n##### LPM Settings #####\n' \
                 'delay: {0}ms\n' \
                 'audio on: {1}\n' \
                 'subs on: {2}\n' \
                 'cond subs on: {3}\n' \
                 'turn subs on: {4}, turn subs off: {5}\n' \
                 'signs: {15}\n' \
                 'blacklisted keywords: {16}\n' \
                 'use file name: {6}, file name regex: {7}\n' \
                 'at least one pref on: {8}\n'\
                 'audio prefs: {9}\n' \
                 'sub prefs: {10}\n' \
                 'cond sub prefs: {11}\n' \
                 'custom audio prefs: {12}\n' \
                 'custom subs prefs: {13}\n'
                 'custom cond subs prefs: {14}\n'
                 '##### LPM Settings #####\n'
                 .format(self.delay, self.audio_prefs_on, self.sub_prefs_on,
                         self.condsub_prefs_on, self.turn_subs_on, self.turn_subs_off,
                         self.useFilename, self.filenameRegex, self.at_least_one_pref_on,
                         self.AudioPrefs, self.SubtitlePrefs, self.CondSubtitlePrefs,
                         self.custom_audio, self.custom_subs, self.custom_condsub, self.ignore_signs_on,
                         ','.join(self.keyword_blacklist))
                 )
      
    def readPrefs(self):
      addon = xbmcaddon.Addon()    

      self.service_enabled = addon.getSetting('enabled') == 'true'
      self.delay = int(addon.getSetting('delay'))
      self.audio_prefs_on = addon.getSetting('enableAudio') == 'true'
      self.sub_prefs_on = addon.getSetting('enableSub') == 'true'
      self.condsub_prefs_on = addon.getSetting('enableCondSub') == 'true'
      self.turn_subs_on = addon.getSetting('turnSubsOn') == 'true'
      self.turn_subs_off = addon.getSetting('turnSubsOff') == 'true'
      self.ignore_signs_on = addon.getSetting('signs') == 'true'
      self.keyword_blacklist_enabled = addon.getSetting('enableKeywordBlacklist') == 'true'
      self.keyword_blacklist = addon.getSetting('KeywordBlacklist')
      if self.keyword_blacklist and self.keyword_blacklist_enabled:
          self.keyword_blacklist = self.keyword_blacklist.lower().split(',')
      else:
          self.keyword_blacklist = []
      self.useFilename = addon.getSetting('useFilename') == 'true'
      self.filenameRegex = addon.getSetting('filenameRegex')
      if self.useFilename:
          self.reg = re.compile(self.filenameRegex, re.IGNORECASE)
          self.split = re.compile(r'[_|.|-]*', re.IGNORECASE)

      self.at_least_one_pref_on = (self.audio_prefs_on
                                  or self.sub_prefs_on
                                  or self.condsub_prefs_on
                                  or self.useFilename)
      
      self.AudioPrefs = [(set(), [
          (languageTranslate(addon.getSetting('AudioLang01'), 4, 0) ,
           languageTranslate(addon.getSetting('AudioLang01'), 4, 3)),
          (languageTranslate(addon.getSetting('AudioLang02'), 4, 0) ,
           languageTranslate(addon.getSetting('AudioLang02'), 4, 3)),
          (languageTranslate(addon.getSetting('AudioLang03'), 4, 0) ,
           languageTranslate(addon.getSetting('AudioLang03'), 4, 3))]
      )]
      self.SubtitlePrefs = [(set(), [
          (languageTranslate(addon.getSetting('SubLang01'), 4, 0) ,
           languageTranslate(addon.getSetting('SubLang01'), 4, 3),
           addon.getSetting('SubForced01')),
          (languageTranslate(addon.getSetting('SubLang02'), 4, 0) ,
           languageTranslate(addon.getSetting('SubLang02'), 4, 3),
           addon.getSetting('SubForced02')),
          (languageTranslate(addon.getSetting('SubLang03'), 4, 0) ,
           languageTranslate(addon.getSetting('SubLang03'), 4, 3),
           addon.getSetting('SubForced03'))]
      )]
      self.CondSubtitlePrefs = [(set(), [
          (
              languageTranslate(addon.getSetting('CondAudioLang01'), 4, 0),
              languageTranslate(addon.getSetting('CondAudioLang01'), 4, 3),
              languageTranslate(addon.getSetting('CondSubLang01'), 4, 0),
              languageTranslate(addon.getSetting('CondSubLang01'), 4, 3),
              addon.getSetting('CondSubForced01')
          ),
          (
              languageTranslate(addon.getSetting('CondAudioLang02'), 4, 0),
              languageTranslate(addon.getSetting('CondAudioLang02'), 4, 3),
              languageTranslate(addon.getSetting('CondSubLang02'), 4, 0),
              languageTranslate(addon.getSetting('CondSubLang02'), 4, 3),
              addon.getSetting('CondSubForced02')
          ),
          (
              languageTranslate(addon.getSetting('CondAudioLang03'), 4, 0),
              languageTranslate(addon.getSetting('CondAudioLang03'), 4, 3),
              languageTranslate(addon.getSetting('CondSubLang03'), 4, 0),
              languageTranslate(addon.getSetting('CondSubLang03'), 4, 3),
              addon.getSetting('CondSubForced03')
          )]
      )]

    def readCustomPrefs(self):
        addon = xbmcaddon.Addon()
        self.custom_audio = []
        self.custom_audio_prefs_on = False
        self.custom_subs = []
        self.custom_sub_prefs_on = False
        self.custom_condsub = []
        self.custom_condsub_prefs_on = False

        prefParser = PrefParser()
        self.custom_audio = prefParser.parsePrefString(
            addon.getSetting('CustomAudio'))
        self.custom_subs = prefParser.parsePrefString(
            addon.getSetting('CustomSub'))
        self.custom_condsub = prefParser.parsePrefString(
            addon.getSetting('CustomCondSub'))

        if len(self.custom_audio) > 0:
            self.custom_audio_prefs_on = True     
        if len(self.custom_subs) > 0:
            self.custom_sub_prefs_on = True
        if len(self.custom_condsub) >0:
            self.custom_condsub_prefs_on = True

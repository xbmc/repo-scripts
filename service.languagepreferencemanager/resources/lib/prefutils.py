import os, sys, re
import xbmc, xbmcaddon, xbmcvfs

import json as simplejson

from langcodes import *
from prefsettings import settings

settings = settings()

LOG_NONE = 0
LOG_ERROR = 1
LOG_INFO = 2
LOG_DEBUG = 3

def log(level, msg):
    if level <= settings.logLevel:
        if level == LOG_ERROR:
            l = xbmc.LOGERROR
        elif level == LOG_INFO:
            l = xbmc.LOGINFO
        elif level == LOG_DEBUG:
            l = xbmc.LOGDEBUG
        xbmc.log("[Language Preference Manager]: " + str(msg), l)

class LangPref_Monitor( xbmc.Monitor ):
  
  def __init__( self ):
      xbmc.Monitor.__init__( self )
        
  def onSettingsChanged( self ):
      settings.init()
      settings.readSettings()

class LangPrefMan_Player(xbmc.Player) :
    
    def __init__ (self):
        self.LPM_initial_run_done = False
        settings.readSettings()
        xbmc.Player.__init__(self)

    def onPlayBackStarted(self):
        if settings.service_enabled and settings.at_least_one_pref_on:
            log(LOG_DEBUG, 'New AV Playback initiated - Resetting LPM Initial Flag')
            self.LPM_initial_run_done = False
    
    def onAVStarted(self):
        if settings.service_enabled and settings.at_least_one_pref_on and self.isPlayingVideo():
            log(LOG_DEBUG, 'Playback started')
            self.audio_changed = False
            # switching an audio track to early leads to a reopen -> start at the beginning
            if settings.delay > 0:
                log(LOG_DEBUG, "Delaying preferences evaluation by {0} ms".format(settings.delay))
                xbmc.sleep(settings.delay)
            log(LOG_DEBUG, 'Getting video properties')
            self.getDetails()
            self.evalPrefs()
            self.LPM_initial_run_done = True

    def onAVChange(self):
        if self.LPM_initial_run_done and settings.service_enabled and settings.at_least_one_pref_on and self.isPlayingVideo():
            log(LOG_DEBUG, 'AVChange detected - Checking possible change of audio track...')
            self.audio_changed = False
            if settings.delay > 0:
                log(LOG_DEBUG, "Delaying preferences evaluation by {0} ms".format(settings.delay))
                xbmc.sleep(settings.delay)
            previous_audio_index = self.selected_audio_stream['index']
            previous_audio_language = self.selected_audio_stream['language']
            log(LOG_DEBUG, 'Getting video properties')
            self.getDetails()
            if (self.selected_audio_stream['index'] != previous_audio_index):
                log(LOG_INFO, 'Audio track changed from {0} to {1}. Reviewing Conditional Subtitles rules...'.format(previous_audio_language, self.selected_audio_stream['language']))
                self.evalPrefs()
    
    def evalPrefs(self):
        # recognized filename audio or filename subtitle
        fa = False
        fs = False
        if settings.useFilename and not self.LPM_initial_run_done:
            audio, sub = self.evalFilenamePrefs()
            if (audio >= 0) and audio < len(self.audiostreams):
                log(LOG_INFO, 'Filename preference: Match, selecting audio track {0}'.format(audio))
                self.setAudioStream(audio)
                self.audio_changed = True
                fa = True
            else:
                log(LOG_INFO, 'Filename preference: No match found for audio track ({0})'.format(self.getPlayingFile()))
                
            if (sub >= 0) and sub < len(self.subtitles):
                self.setSubtitleStream(sub)
                fs = True
                log(LOG_INFO, 'Filename preference: Match, selecting subtitle track {0}'.format(sub))
                if settings.turn_subs_on:
                    log(LOG_DEBUG, 'Subtitle: enabling subs' )
                    self.showSubtitles(True)
            else:
                log(LOG_INFO, 'Filename preference: No match found for subtitle track ({0})'.format(self.getPlayingFile()))
                if settings.turn_subs_off:
                    log(LOG_INFO, 'Subtitle: disabling subs' )
                    self.showSubtitles(False)
                    
        if settings.audio_prefs_on and not fa and not self.LPM_initial_run_done:
            if settings.custom_audio_prefs_on:
                trackIndex = self.evalAudioPrefs(settings.custom_audio)
            else:
                trackIndex = self.evalAudioPrefs(settings.AudioPrefs)
                
            if trackIndex == -2:
                log(LOG_INFO, 'Audio: None of the preferred languages is available' )
            elif trackIndex >= 0:
                self.setAudioStream(trackIndex)
                self.audio_changed = True
            
        if settings.sub_prefs_on and not fs and not self.LPM_initial_run_done:
            if settings.custom_sub_prefs_on:
                trackIndex = self.evalSubPrefs(settings.custom_subs)
            else:
                trackIndex = self.evalSubPrefs(settings.SubtitlePrefs)
                
            if trackIndex == -2:
                log(LOG_INFO, 'Subtitle: None of the preferred languages is available' )
                if settings.turn_subs_off:
                    log(LOG_INFO, 'Subtitle: disabling subs' )
                    self.showSubtitles(False)
            if trackIndex == -1:
                log(LOG_INFO, 'Subtitle: Preferred subtitle is selected but might not be enabled' )
                if settings.turn_subs_on and not self.selected_sub_enabled:
                    log(LOG_INFO, 'Subtitle: enabling subs because selected sub is not enabled' )
                    self.showSubtitles(True)
            elif trackIndex >= 0:
                self.setSubtitleStream(trackIndex)
                if settings.turn_subs_on:
                    log(LOG_INFO, 'Subtitle: enabling subs' )
                    self.showSubtitles(True)
                
        if settings.condsub_prefs_on and not fs:
            if settings.custom_condsub_prefs_on:
                trackIndex = self.evalCondSubPrefs(settings.custom_condsub)
            else:
                trackIndex = self.evalCondSubPrefs(settings.CondSubtitlePrefs)

            if trackIndex == -1:
                log(LOG_INFO, 'Conditional subtitle: disabling subs' )
                self.showSubtitles(False)
            if trackIndex == -2:
                log(LOG_INFO, 'Conditional subtitle: No matching preferences found for current audio stream. Doing nothing.')
            elif trackIndex >= 0:
                self.setSubtitleStream(trackIndex)
                if settings.turn_subs_on:
                    log(LOG_DEBUG, 'Subtitle: enabling subs' )
                    self.showSubtitles(True)

        # Workaround to an old Kodi bug creating 10-15 sec latency when activating a subtitle track.
        # Force a short rewind to avoid 10-15sec delay and first few subtitles lines potentially lost
        #       but if we are very close to beginning, then restart from time 0
        # Ignore this workaround if fast_subs_display option is disabled (default = 0)
        current_time = self.getTime()
        if (settings.fast_subs_display == 0):
            # Default is no seek back, which sometimes generate restart or freeze on slower systems
            log(LOG_DEBUG, 'Fast Subs Display disabled - Subs display will be slightly delayed 8-10sec.')
        elif (current_time <= 10 and settings.fast_subs_display >= 1):
            # This is an initial start, seek back to 0 is securing subs are displayed immediately
            log(LOG_DEBUG, 'Fast Subs Display on Start - Position time is {0} sec. Restart from 0.'.format(current_time))
            self.seekTime(0)
        elif (not self.LPM_initial_run_done and settings.fast_subs_display == 2):
            # This is a resume, seek back 10sec to secure the 8sec normal Aud/Vid buffers are flushed
            # Seek back less while resuming (ex. 1sec) create too many Large Audio Sync errors, with some unwanted restart from 0, or even possible bug freeze
            log(LOG_DEBUG, 'Fast Subs Display on Resume - Position time is {0} sec. Resume with 10 sec rewind.'.format(current_time))
            self.seekTime(current_time - 10) 
        else:
            # This is an Audio Track change on-the-fly or a Resume with fast_sub_display on 'Start Only', accept the subs latency to keep snappyness. No seek back at all.
            log(LOG_DEBUG, 'Position time was {0} sec. Subs display slightly delayed.'.format(current_time))

    def evalFilenamePrefs(self):
        log(LOG_DEBUG, 'Evaluating filename preferences' )
        audio = -1
        sub = -1
        filename = self.getPlayingFile()
        matches = settings.reg.findall(filename)
        fileprefs = []
        for m in matches:
            sp = settings.split.split(m)
            fileprefs.append(sp)

        for pref in fileprefs:
            if len(pref) == 2:
                if (pref[0].lower() == 'audiostream'):
                    audio = int(pref[1])
                    log(LOG_INFO, 'audio track extracted from filename: {0}'.format(audio))
                elif(pref[0].lower() == 'subtitle'):
                    sub = int(pref[1])
                    log(LOG_INFO, 'subtitle track extracted from filename: {0}'.format(sub))
        log(LOG_DEBUG, 'filename: audio: {0}, sub: {1} ({2})'.format(audio, sub, filename))
        return audio, sub
    
    def evalAudioPrefs(self, audio_prefs):
        log(LOG_DEBUG, 'Evaluating audio preferences' )
        log(LOG_DEBUG, 'Audio names containing the following keywords are blacklisted: {0}'.format(','.join(settings.audio_keyword_blacklist)))
        i = 0
        for pref in audio_prefs:
            i += 1
            g_t, preferences = pref
            # genre or tags are given (g_t not empty) but none of them matches the video's tags/genres
            if g_t and (not (self.genres_and_tags & g_t)):
                continue

            log(LOG_INFO,'Audio: genre/tag preference {0} met with intersection {1}'.format(g_t, (self.genres_and_tags & g_t)))
            for pref in preferences:
                name, codes = pref
                codes = codes.split(r',')
                for code in codes:
                    if (code is None):
                        log(LOG_DEBUG,'continue')
                        continue                
                    if (self.selected_audio_stream and
                        'language' in self.selected_audio_stream and
                        # filter out audio tracks matching Keyword Blacklist
                        not self.isInBlacklist(self.selected_audio_stream['name'],'Audio') and
                        (code == self.selected_audio_stream['language'] or name == self.selected_audio_stream['language'])):
                            log(LOG_INFO, 'Selected audio language matches preference {0} ({1})'.format(i, name) )
                            return -1
                    else:
                        for stream in self.audiostreams:
                            # filter out audio tracks matching Keyword Blacklist
                            if (self.isInBlacklist(stream['name'],'Audio')):
                                log(LOG_INFO,'Audio: one audio track is found matching Keyword Blacklist : {0}. Skipping it.'.format(','.join(settings.audio_keyword_blacklist)))
                                continue
                            if ((code == stream['language']) or (name == stream['language'])):
                                log(LOG_INFO, 'Language of Audio track {0} matches preference {1} ({2})'.format((stream['index']+1), i, name) )
                                return stream['index']
                        log(LOG_INFO, 'Audio: preference {0} ({1}:{2}) not available'.format(i, name, code) )
                i += 1
        return -2
                
    def evalSubPrefs(self, sub_prefs):
        log(LOG_DEBUG, 'Evaluating subtitle preferences' )
        log(LOG_DEBUG, 'Subtitle names containing the following keywords are blacklisted: {0}'.format(','.join(settings.subtitle_keyword_blacklist)))
        i = 0
        for pref in sub_prefs:
            i += 1
            g_t, preferences = pref
            # genre or tags are given (g_t not empty) but none of them matches the video's tags/genres
            if g_t and (not (self.genres_and_tags & g_t)):
                continue

            log(LOG_INFO,'Subtitle: genre/tag preference {0} met with intersection {1}'.format(g_t, (self.genres_and_tags & g_t)))
            for pref in preferences:
                if len(pref) == 2:
                    name, codes = pref
                    forced = 'false'
                else:
                    name, codes, forced = pref
                codes = codes.split(r',')
                for code in codes:
                    if (code is None):
                        log(LOG_DEBUG,'continue')
                        continue 
                    if (self.selected_sub and
                        'language' in self.selected_sub and
                        # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                        not self.isInBlacklist(self.selected_sub['name'],'Subtitle') and
                        not (settings.ignore_signs_on and self.isSignsSub(self.selected_sub['name'])) and
                        ((code == self.selected_sub['language'] or name == self.selected_sub['language']) and self.testForcedFlag(forced, self.selected_sub['name'], self.selected_sub['isforced']))):
                            log(LOG_INFO, 'Selected subtitle language matches preference {0} ({1})'.format(i, name) )
                            return -1
                    else:
                        for sub in self.subtitles:
                            # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                            if self.isInBlacklist(sub['name'], 'Subtitle'):
                                log(LOG_INFO,'SubPrefs : one subtitle track is found matching Keyword Blacklist : {0}. Skipping it.'.format(','.join(settings.subtitle_keyword_blacklist)))
                                continue
                            if (settings.ignore_signs_on and self.isSignsSub(sub['name'])):
                                log(LOG_INFO,'SubPrefs : ignore_signs toggle is on and one such subtitle track is found. Skipping it.')
                                continue
                            if ((code == sub['language'] or name == sub['language']) and self.testForcedFlag(forced, sub['name'], sub['isforced'])):
                                log(LOG_INFO, 'Subtitle language of subtitle {0} matches preference {1} ({2})'.format((sub['index']+1), i, name) )
                                return sub['index']
                        log(LOG_INFO, 'Subtitle: preference {0} ({1}:{2}) not available'.format(i, name, code) )
                i += 1
        return -2

    def evalCondSubPrefs(self, condsub_prefs):
        log(LOG_DEBUG, 'Evaluating conditional subtitle preferences' )
        log(LOG_DEBUG, 'Subtitle names containing the following keywords are blacklisted: {0}'.format(','.join(settings.subtitle_keyword_blacklist)))
        # if the audio track has been changed wait some time
        if (self.audio_changed and settings.delay > 0):
            log(LOG_DEBUG, "Delaying preferences evaluation by {0} ms".format(4*settings.delay))
            xbmc.sleep(4*settings.delay)
        log(LOG_DEBUG, 'Getting video properties')
        self.getDetails()
        i = 0
        for pref in condsub_prefs:
            i += 1
            g_t, preferences = pref
            # genre or tags are given (g_t not empty) but none of them matches the video's tags/genres
            if g_t and (not (self.genres_and_tags & g_t)):
                continue

            log(LOG_INFO,'Cond Sub: genre/tag preference {0} met with intersection {1}'.format(g_t, (self.genres_and_tags & g_t)))
            for pref in preferences:
                audio_name, audio_codes, sub_name, sub_codes, forced, ss_tag = pref
                # manage multiple audio and/or subtitle 3-letters codes if present (ex. German = ger,deu)
                audio_codes = audio_codes.split(r',')
                sub_codes = sub_codes.split(r',')
                nbr_sub_codes = len(sub_codes)

                for audio_code in audio_codes:
                    if (audio_code is None):
                        log(LOG_DEBUG,'continue')
                        continue 

                    if (self.selected_audio_stream and
                        'language' in self.selected_audio_stream and
                        (audio_code == self.selected_audio_stream['language'] or audio_name == self.selected_audio_stream['language'] or audio_code == "any")):
                            log(LOG_INFO, 'Selected audio language matches conditional preference {0} ({1}:{2}), force tag is {3}'.format(i, audio_name, sub_name, forced) )
                            for sub_code in sub_codes:
                                if (sub_code == "non"):
                                    if (forced == 'true'):
                                        log(LOG_INFO, 'Subtitle condition is None but forced is true, searching a forced subtitle matching selected audio...')
                                        for sub in self.subtitles:
                                            log(LOG_DEBUG, 'Looping subtitles...')
                                            # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                                            if self.isInBlacklist(sub['name'], 'Subtitle'):
                                                log(LOG_INFO,'CondSubs : one subtitle track is found matching Keyword Blacklist : {0}. Skipping it.'.format(','.join(settings.subtitle_keyword_blacklist)))
                                                continue
                                            if (settings.ignore_signs_on and self.isSignsSub(sub['name'])):
                                                log(LOG_INFO,'CondSubs : ignore_signs toggle is on and one such subtitle track is found. Skipping it.')
                                                continue
                                            if ((audio_code == sub['language']) or (audio_name == sub['language'])):
                                                log(LOG_DEBUG, 'One potential match found...')
                                                if (self.testForcedFlag(forced, sub['name'], sub['isforced'])):
                                                    log(LOG_DEBUG, 'One forced match found...')
                                                    log(LOG_INFO, 'Language of subtitle {0} matches audio preference {1} ({2}:{3}) with forced overriding rule {4}'.format((sub['index']+1), i, audio_name, sub_name, forced) )
                                                    return sub['index']
                                        log(LOG_INFO, 'Conditional subtitle: no match found for preference {0} ({1}:{2}) with forced overriding rule {3}'.format(i, audio_name, sub_name, forced))
                                    return -1
                                else:
                                    for sub in self.subtitles:
                                        # take into account -ss tag to prioritize specific Signs&Songs subtitles track
                                        if ((sub_code == sub['language']) or (sub_name == sub['language'])):
                                            if (ss_tag == 'true' and self.isSignsSub(sub['name'])):
                                                log(LOG_INFO, 'Language of subtitle {0} matches conditional preference {1} ({2}:{3}) SubTag {4}'.format((sub['index']+1), i, audio_name, sub_name, ss_tag) )
                                                return sub['index']
                                        # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                                        if self.isInBlacklist(sub['name'], 'Subtitle'):
                                            log(LOG_INFO,'CondSubs : one subtitle track is found matching Keyword Blacklist : {0}. Skipping it.'.format(','.join(settings.subtitle_keyword_blacklist)))
                                            continue
                                        if (settings.ignore_signs_on and self.isSignsSub(sub['name'])):
                                            log(LOG_INFO,'CondSubs : ignore_signs toggle is on and one such subtitle track is found. Skipping it.')
                                            continue
                                        if ((sub_code == sub['language']) or (sub_name == sub['language'])):
                                            if (ss_tag == 'false' and self.testForcedFlag(forced, sub['name'], sub['isforced'])):
                                                log(LOG_INFO, 'Language of subtitle {0} matches conditional preference {1} ({2}:{3}) forced {4}'.format((sub['index']+1), i, audio_name, sub_name, forced) )
                                                return sub['index']
                                    nbr_sub_codes -= 1
                                    if nbr_sub_codes == 0:
                                        log(LOG_INFO, 'Conditional subtitle: no match found for preference {0} ({1}:{2})'.format(i, audio_name, sub_name) )
                i += 1
        return -2

    def isInBlacklist(self, TrackName, TrackType):
        found = False
        test = TrackName.lower()
        if (TrackType == 'Subtitle' and settings.subtitle_keyword_blacklist_enabled and any(keyword in test for keyword in settings.subtitle_keyword_blacklist)):
            found = True
        elif (TrackType == 'Audio' and settings.audio_keyword_blacklist_enabled and any(keyword in test for keyword in settings.audio_keyword_blacklist)):
            found = True
        return found

    def isSignsSub(self, subName):
        test = subName.lower()
        matches = ['signs']
        return any(x in test for x in matches)
    
    def testForcedFlag(self, forced, subName, subForcedTag):
        test = subName.lower()
        matches = ['forced', 'forcés']
        found = any(x in test for x in matches)
        # Only when looking for forced subs :
        #   in case the sub name is plain empty or not well documented, 
        #   check also the sub isforced tag and consider it a match if set
        if (forced and not found and subForcedTag):
            found = True
        return ((forced == 'false') and not found) or ((forced == 'true') and found)

    def isExternalSub(self, subName):
        test = subName.lower()
        matches = ['ext']
        return any(x in test for x in matches)
    
    def getDetails(self):
        activePlayers ='{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
        json_query = xbmc.executeJSONRPC(activePlayers)
        #json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        activePlayerID = json_response['result'][0]['playerid']
        details_query_dict = {  "jsonrpc": "2.0",
                                "method": "Player.GetProperties",
                                "params": { "properties": 
                                            ["currentaudiostream", "audiostreams", "subtitleenabled",
                                             "currentsubtitle", "subtitles" ],
                                            "playerid": activePlayerID },
                                "id": 1}
        details_query_string = simplejson.dumps(details_query_dict)
        json_query = xbmc.executeJSONRPC(details_query_string)
        #json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        
        if 'result' in json_response and json_response['result'] != None:
            self.selected_audio_stream = json_response['result']['currentaudiostream']
            self.selected_sub = json_response['result']['currentsubtitle']
            self.selected_sub_enabled = json_response['result']['subtitleenabled']
            self.audiostreams = json_response['result']['audiostreams']
            self.subtitles = json_response['result']['subtitles']
        log(LOG_DEBUG, json_response )
        
        if (not settings.custom_condsub_prefs_on and not settings.custom_audio_prefs_on and not settings.custom_sub_prefs_on):
            log(LOG_DEBUG, 'No custom prefs used at all, skipping extra Video tags/genres JSON query.')
            self.genres_and_tags = set()
            return        
        
        genre_tags_query_dict = {"jsonrpc": "2.0",
                                 "method": "Player.GetItem",
                                 "params": { "properties":
                                            ["genre", "tag"],
                                            "playerid": activePlayerID },
                                 "id": 1}
        genre_tags_query_string = simplejson.dumps(genre_tags_query_dict)
        json_query = xbmc.executeJSONRPC(genre_tags_query_string)
        #json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if 'result' in json_response and json_response['result'] != None:
            gt = []
            if 'genre' in json_response['result']['item']:
                gt = json_response['result']['item']['genre']
            if 'tag' in json_response['result']['item']:
                gt.extend(json_response['result']['item']['tag'])
            self.genres_and_tags = set(map(lambda x:x.lower(), gt))
        log(LOG_DEBUG, 'Video tags/genres: {0}'.format(self.genres_and_tags))
        log(LOG_DEBUG, json_response )


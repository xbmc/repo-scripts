import os, sys, re
import threading
import time

import xbmc, xbmcaddon, xbmcvfs

from custom_media_preference import media_preference_manager, CustomMediaPreference
from logger import log, LOG_NONE, LOG_INFO, LOG_DEBUG, LOG_ERROR

import json as simplejson

from langcodes import *
from prefsettings import settings

settings = settings()


class LangPref_Monitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        settings.init()
        settings.readSettings()


class LangPrefWatcher(threading.Thread):
    """
    A thread that periodically checks for subtitle changes.
    """

    def __init__(self, player, check_interval=10):
        super().__init__()
        self.player = player
        self.check_interval = check_interval

        # Event to stop the thread gracefully
        self._stop_event = threading.Event()

        # Ensures the thread exits when the program ends
        self.daemon = True

        self.WatcherMonitor = xbmc.Monitor()

    def run(self):
        """
        This method runs in the background and periodically checks for subtitle changes.
        Possibly in the future, this method will also check for other stuff.
        """
        while not self._stop_event.is_set() and not self.WatcherMonitor.abortRequested():
            if self.player.isPlayingVideo():
                self.player.detect_subtitle_change()
            self.WatcherMonitor.waitForAbort(self.check_interval)
        if self.WatcherMonitor.abortRequested():
            log(LOG_DEBUG, 'Aborting Watcher Thread due to Kodi request')

    def stop(self):
        """ Method to stop the thread gracefully """
        self._stop_event.set()
        log(LOG_DEBUG, 'Watcher Thread gracefully stopping')
        self.join()


class LangPrefMan_Player(xbmc.Player):

    def __init__(self):
        self.LPM_initial_run_done = False
        self.selected_sub_enabled = False

        self.ignore_audio_change_index_list = []

        settings.readSettings()
        xbmc.Player.__init__(self)

        if settings.storeCustomMediaPreferences:
            # Start the LangPrefWatcher thread. This thread will periodically check for subtitle changes.
            # This is because onAVChange does not get called when the subtitle stream changes.
            self.lang_pref_watcher = LangPrefWatcher(self, check_interval=10)
            self.lang_pref_watcher.start()

    def add_ignore_audio_change_index(self, index):
        """
        Adds an audio stream index to the ignore list.
        This means that the audio stream will be ignored for changes and preference re-evaluation will not be done.
        After one matching change based on index, the audio stream will be considered again.
        :param index: The index of the audio stream to ignore.
        """
        if index not in self.ignore_audio_change_index_list:
            self.ignore_audio_change_index_list.append(index)
            log(LOG_DEBUG, f"Audio stream index {index} added to ignore list.")

    def remove_ignore_audio_change_index(self, index):
        """
        Removes an audio stream index from the ignore list.
        This means that the audio stream will be considered for changes again and preference re-evaluation will be done.
        :param index: The index of the audio stream to remove from the ignore list.
        """
        if index in self.ignore_audio_change_index_list:
            self.ignore_audio_change_index_list.remove(index)
            log(LOG_DEBUG, f"Audio stream index {index} removed from ignore list.")

    def is_ignore_audio_change_index(self, index):
        """
        Checks if an audio stream index is in the ignore list.
        This means that the audio stream will be ignored for changes and preference re-evaluation will not be done.
        :param index: The index of the audio stream to check.
        :return: True if the index is in the ignore list, False otherwise.
        """
        return index in self.ignore_audio_change_index_list

    def onPlayBackPaused(self):
        """ Will be called when [user] stops Kodi playing a file """
        log(LOG_DEBUG, 'Player: [onPlayBackPaused] called')
        self.detect_subtitle_change()

    def onPlayBackResumed(self):
        """ Will be called when [user] stops Kodi playing a file """
        log(LOG_DEBUG, 'Player: [onPlayBackResumed] called')
        self.detect_subtitle_change()

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

            # If the user has enabled to store preferences (that is manually overriden preferences) for the player, we willl check for that here
            if settings.is_store_user_preference_for_player(self):
                log(LOG_DEBUG, 'Media preference storage enabled for current media. Checking for custom preferences...')
                custom_preference = media_preference_manager.get_preference(self)

                if custom_preference is not None:
                    log(LOG_INFO, 'Custom media preferences found for current media - Applying them...')
                    log(LOG_INFO, '       ... Audio {0} Subtitles {1} Enabled {2} .'.format(custom_preference.audio_language,
                                                                                        custom_preference.subtitle_language,
                                                                                        custom_preference.enable_subtitles))
                    if not custom_preference.apply_to_player(self):
                        log(LOG_INFO,
                            'Failed to apply custom media preferences for current media. Falling back to default preferences...')
                        self.evalPrefs()
                else:
                    self.evalPrefs()
            else:
                self.evalPrefs()

            self.LPM_initial_run_done = True

    def onAVChange(self):
        """
        This method is called when the audio or video stream changes. It is not called when the subtitle stream changes.
        :return: None
        """
        log(LOG_DEBUG, 'onAVChange detected')
        if self.LPM_initial_run_done and settings.service_enabled and settings.at_least_one_pref_on and self.isPlayingVideo():
            log(LOG_DEBUG, 'AVChange detected - Checking possible change of audio track...')
            self.audio_changed = False

            if settings.delay > 0:
                log(LOG_DEBUG, "Delaying preferences evaluation by {0} ms".format(settings.delay))
                xbmc.sleep(settings.delay)

            previous_audio_index = self.getSelectedAudioIndex()
            previous_audio_language = self.getSelectedAudioLanguage()
            if previous_audio_index == -1:
                log(LOG_INFO, "No Current Audio Stream activated so far for this video. Bizarre...")

            log(LOG_DEBUG, 'Getting video properties')
            self.getDetails()

            log(LOG_DEBUG, 'Subtitle enabled: {0}'.format(self.selected_sub_enabled))

            new_audio_index = self.getSelectedAudioIndex()

            if self.is_ignore_audio_change_index(new_audio_index):
                log(LOG_DEBUG, 'Audio track index {0} is in the ignore list. Skipping preference evaluation.'.format(new_audio_index))
                self.remove_ignore_audio_change_index(new_audio_index)
                return

            if new_audio_index != previous_audio_index:
                log(LOG_INFO, 'Audio track changed from {0} to {1}. Reviewing Conditional Subtitles rules...'.format(
                    previous_audio_language, self.selected_audio_stream['language']))

                if settings.is_store_user_preference_for_player(self):
                    custom_preference = CustomMediaPreference.from_player(self)
                    media_preference_manager.add_preference(custom_preference)
                    media_preference_manager.save_preferences()

                self.evalPrefs()

    def detect_subtitle_change(self):
        """
        This method detects if the subtitle track has changed and stores the new preference if it has.
        :return: None
        """
        if self.LPM_initial_run_done and settings.service_enabled and settings.at_least_one_pref_on and self.isPlayingVideo():
            log(LOG_DEBUG, 'Running subtitle change detect')
            previous_sub_index = self.getSelectedSubtitleIndex()

            previous_sub_language = self.getSelectedSubtitleLanguage()
            previous_enabled_sub = self.selected_sub_enabled

            self.getDetails()

            if self.getSelectedSubtitleIndex() != previous_sub_index or self.selected_sub_enabled != previous_enabled_sub:
                log(LOG_DEBUG, 'Subtitle track changed from {0} to {1}'.format(previous_sub_language,
                                                                               self.getSelectedSubtitleLanguage()))

                if settings.is_store_user_preference_for_player(self):
                    custom_preference = CustomMediaPreference.from_player(self)
                    media_preference_manager.add_preference(custom_preference)
                    media_preference_manager.save_preferences()

    def evalPrefs(self):
        # recognized filename audio or filename subtitle
        use_filename_audio = False
        use_filename_subs = False

        if settings.useFilename and not self.LPM_initial_run_done:
            audio, sub = self.evalFilenamePrefs()
            if (audio >= 0) and audio < len(self.audiostreams):
                log(LOG_INFO, 'Filename preference: Match, selecting audio track {0}'.format(audio))
                self.setAudioStream(audio)
                self.audio_changed = True
                use_filename_audio = True
            else:
                log(LOG_INFO, 'Filename preference: No match found for audio track ({0})'.format(self.getPlayingFile()))

            if (sub >= 0) and sub < len(self.subtitles):
                self.setSubtitleStream(sub)
                use_filename_subs = True
                log(LOG_INFO, 'Filename preference: Match, selecting subtitle track {0}'.format(sub))
                if settings.turn_subs_on:
                    log(LOG_DEBUG, 'Subtitle: enabling subs')
                    self.showSubtitles(True)
            else:
                log(LOG_INFO,
                    'Filename preference: No match found for subtitle track ({0})'.format(self.getPlayingFile()))
                if settings.turn_subs_off:
                    log(LOG_INFO, 'Subtitle: disabling subs')
                    self.showSubtitles(False)

        if settings.audio_prefs_on and not use_filename_audio and not self.LPM_initial_run_done:
            if settings.custom_audio_prefs_on:
                trackIndex = self.evalAudioPrefs(settings.custom_audio)
            else:
                trackIndex = self.evalAudioPrefs(settings.AudioPrefs)

            if trackIndex == -2:
                log(LOG_INFO, 'Audio: None of the preferred languages is available')
            elif trackIndex >= 0:
                self.setAudioStream(trackIndex)
                self.audio_changed = True

        if settings.sub_prefs_on and not use_filename_subs and not self.LPM_initial_run_done:
            if settings.custom_sub_prefs_on:
                trackIndex = self.evalSubPrefs(settings.custom_subs)
            else:
                trackIndex = self.evalSubPrefs(settings.SubtitlePrefs)

            if trackIndex == -2:
                log(LOG_INFO, 'Subtitle: None of the preferred languages is available')
                if settings.turn_subs_off:
                    log(LOG_INFO, 'Subtitle: disabling subs')
                    self.showSubtitles(False)
            if trackIndex == -1:
                log(LOG_INFO, 'Subtitle: Preferred subtitle is selected but might not be enabled')
                if settings.turn_subs_on and not self.selected_sub_enabled:
                    log(LOG_INFO, 'Subtitle: enabling subs because selected sub is not enabled')
                    self.showSubtitles(True)
            elif trackIndex >= 0:
                self.setSubtitleStream(trackIndex)
                if settings.turn_subs_on:
                    log(LOG_INFO, 'Subtitle: enabling subs')
                    self.showSubtitles(True)

        if settings.condsub_prefs_on and not use_filename_subs:
            if settings.custom_condsub_prefs_on:
                trackIndex = self.evalCondSubPrefs(settings.custom_condsub)
            else:
                trackIndex = self.evalCondSubPrefs(settings.CondSubtitlePrefs)

            if trackIndex == -1:
                log(LOG_INFO, 'Conditional subtitle: disabling subs')
                self.showSubtitles(False)
            if trackIndex == -2:
                log(LOG_INFO,
                    'Conditional subtitle: No matching preferences found for current audio stream.')
                if settings.turn_subs_off:
                    log(LOG_INFO,
                        'Conditional subtitle: Disabling subs.')
                    self.showSubtitles(False)
                else:
                    log(LOG_INFO,
                        'Conditional subtitle: Doing nothing.')
            elif trackIndex >= 0:
                self.setSubtitleStream(trackIndex)
                if settings.turn_subs_on:
                    log(LOG_DEBUG, 'Subtitle: enabling subs')
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
            log(LOG_DEBUG,
                'Fast Subs Display on Start - Position time is {0} sec. Restart from 0.'.format(current_time))
            self.seekTime(0)
        elif (not self.LPM_initial_run_done and settings.fast_subs_display == 2):
            # This is a resume, seek back 10sec to secure the 8sec normal Aud/Vid buffers are flushed
            # Seek back less while resuming (ex. 1sec) create too many Large Audio Sync errors, with some unwanted restart from 0, or even possible bug freeze
            log(LOG_DEBUG, 'Fast Subs Display on Resume - Position time is {0} sec. Resume with 10 sec rewind.'.format(
                current_time))
            self.seekTime(current_time - 10)
        else:
            # This is an Audio Track change on-the-fly or a Resume with fast_sub_display on 'Start Only', accept the subs latency to keep snappyness. No seek back at all.
            log(LOG_DEBUG, 'Position time was {0} sec. Subs display slightly delayed.'.format(current_time))

    def getSelectedAudioLanguage(self):
        if self.selected_audio_stream and 'language' in self.selected_audio_stream:
            return self.selected_audio_stream['language']

        return ""

    def getSelectedAudioIndex(self):
        if self.selected_audio_stream and 'index' in self.selected_audio_stream:
            return self.selected_audio_stream['index']

        return -1

    def getSelectedSubtitleLanguage(self):
        if self.selected_sub and 'language' in self.selected_sub:
            return self.selected_sub['language']

        return ""

    def getSelectedSubtitleIndex(self):
        if self.selected_sub and 'index' in self.selected_sub:
            return self.selected_sub['index']

        return -1

    def evalFilenamePrefs(self):
        log(LOG_DEBUG, 'Evaluating filename preferences')
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
                elif (pref[0].lower() == 'subtitle'):
                    sub = int(pref[1])
                    log(LOG_INFO, 'subtitle track extracted from filename: {0}'.format(sub))
        log(LOG_DEBUG, 'filename: audio: {0}, sub: {1} ({2})'.format(audio, sub, filename))
        return audio, sub

    def evalAudioPrefs(self, audio_prefs):
        log(LOG_DEBUG, 'Evaluating audio preferences')
        log(LOG_DEBUG, 'Audio names containing the following keywords are blacklisted: {0}'.format(
            ','.join(settings.audio_keyword_blacklist)))
        
        log(LOG_DEBUG, 'Original Audio tracks to be preferred if present: {0}'.format(
            ','.join(settings.audio_original_preflist)))
        
        if settings.audio_original_preflist_enabled and settings.audio_original_preflist:
            AudioOriginalTrackIndex = self.get_original_audio_track_index()
            # Audio Original tracks are preferred. If one is found we choose it and skip remaining preference evaluation.
            if AudioOriginalTrackIndex is not None:
                return AudioOriginalTrackIndex
            
        i = 0
        for pref in audio_prefs:
            i += 1
            g_t, preferences = pref
            # genre or tags are given (g_t not empty) but none of them matches the video's tags/genres
            if g_t and (not (self.genres_and_tags & g_t)):
                continue

            if g_t:
                log(LOG_INFO, 'Audio: genre/tag preference {0} met with intersection {1}'.format(g_t, (
                            self.genres_and_tags & g_t)))
            for pref in preferences:
                name, codes = pref
                codes = codes.split(r',')
                for code in codes:
                    if (code is None):
                        log(LOG_DEBUG, 'continue')
                        continue
                    if (self.selected_audio_stream and
                            'language' in self.selected_audio_stream and
                            # filter out audio tracks matching Keyword Blacklist
                            not self.isInBlacklist(self.selected_audio_stream['name'], 'Audio') and
                            (code == self.selected_audio_stream['language'] or name == self.selected_audio_stream[
                                'language'])):
                        log(LOG_INFO, 'Selected audio language matches preference {0} ({1})'.format(i, name))
                        return -1
                    else:
                        for stream in self.audiostreams:
                            # filter out audio tracks matching Keyword Blacklist
                            if (self.isInBlacklist(stream['name'], 'Audio')):
                                log(LOG_INFO,
                                    'Audio: one audio track is found matching Keyword Blacklist : {0}. Skipping it.'.format(
                                        ','.join(settings.audio_keyword_blacklist)))
                                continue
                            if ((code == stream['language']) or (name == stream['language'])):
                                log(LOG_INFO, 'Language of Audio track {0} matches preference {1} ({2})'.format(
                                    (stream['index'] + 1), i, name))
                                return stream['index']
                        log(LOG_INFO, 'Audio: preference {0} ({1}:{2}) not available'.format(i, name, code))
                i += 1
        return -2

    def evalSubPrefs(self, sub_prefs):
        log(LOG_DEBUG, 'Evaluating subtitle preferences')
        log(LOG_DEBUG, 'Subtitle names containing the following keywords are blacklisted: {0}'.format(
            ','.join(settings.subtitle_keyword_blacklist)))
        i = 0
        for pref in sub_prefs:
            i += 1
            g_t, preferences = pref
            # genre or tags are given (g_t not empty) but none of them matches the video's tags/genres
            if g_t and (not (self.genres_and_tags & g_t)):
                continue

            if g_t:
                log(LOG_INFO, 'SubPrefs : genre/tag preference {0} met with intersection {1}'.format(g_t, (
                            self.genres_and_tags & g_t)))
            for pref in preferences:
                if len(pref) == 2:
                    name, codes = pref
                    forced = 'false'
                else:
                    name, codes, forced = pref
                codes = codes.split(r',')
                for code in codes:
                    if (code is None):
                        log(LOG_DEBUG, 'continue')
                        continue
                    if (self.selected_sub and
                            'language' in self.selected_sub and
                            # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                            not self.isInBlacklist(self.selected_sub['name'], 'Subtitle') and
                            not (settings.ignore_signs_on and self.isSignsSub(self.selected_sub['name'])) and
                            ((code == self.selected_sub['language'] or name == self.selected_sub[
                                'language']) and self.testForcedFlag(forced, self.selected_sub['name'],
                                                                     self.selected_sub['isforced']))):
                        log(LOG_INFO, 'SubPrefs : Selected subtitle language matches preference {0} ({1})'.format(i, name))
                        return -1
                    else:
                        to_chose_subtitle_indexes = []

                        for sub in self.subtitles:
                            # Consider empty subtitle language code as und/Undefined so it can still be prioritized in rules, not just ignored
                            if sub['language'] == "":
                                sub['language'] = "und"
                            # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                            if self.isInBlacklist(sub['name'], 'Subtitle'):
                                log(LOG_INFO,
                                    'SubPrefs : one subtitle track is found matching Keyword Blacklist : {0}. Skipping it.'.format(
                                        ','.join(settings.subtitle_keyword_blacklist)))
                                continue
                            if (settings.ignore_signs_on and self.isSignsSub(sub['name'])):
                                log(LOG_INFO,
                                    'SubPrefs : ignore_signs toggle is on and one such subtitle track is found. Skipping it.')
                                continue
                            if (code == sub['language'] or name == sub['language']) and self.testForcedFlag(forced, sub['name'], sub['isforced']):
                                log(LOG_INFO, 'Subtitle language of subtitle {0} matches preference {1} ({2})'.format(
                                    (sub['index'] + 1), i, name))
                                to_chose_subtitle_indexes.append(sub['index'])

                        current_subtitle_index = self.getSelectedSubtitleIndex()

                        # If our current subtitle is eligible for the condition, we will not change it
                        if current_subtitle_index in to_chose_subtitle_indexes:
                            log(LOG_INFO,
                                'SubPrefs : already selected subtitle {0} matches preference {1} ({2})'.format(
                                    (current_subtitle_index + 1), i, name))
                            return current_subtitle_index

                        if len(to_chose_subtitle_indexes) > 0:
                            # if we have more than one subtitles, we will take the first one
                            to_chose_subtitle_index = to_chose_subtitle_indexes[0]
                            log(LOG_INFO, 'SubPrefs : Found {0} matching subtitles, using first at index {1}'.format(
                                len(to_chose_subtitle_indexes), to_chose_subtitle_index))

                            return to_chose_subtitle_index

                        log(LOG_INFO, 'SubPrefs : preference {0} ({1}:{2}) not available'.format(i, name, code))
                i += 1
        return -2

    def evalCondSubPrefs(self, condsub_prefs):
        log(LOG_DEBUG, 'Evaluating conditional subtitle preferences')
        log(LOG_DEBUG, 'Subtitle names containing the following keywords are blacklisted: {0}'.format(
            ','.join(settings.subtitle_keyword_blacklist)))
        # if the audio track has been changed wait some time
        if (self.audio_changed and settings.delay > 0):
            log(LOG_DEBUG, "Delaying preferences evaluation by {0} ms".format(4 * settings.delay))
            xbmc.sleep(4 * settings.delay)
        log(LOG_DEBUG, 'Getting video properties')
        self.getDetails()
        i = 0
        for pref in condsub_prefs:
            i += 1
            g_t, preferences = pref
            # genre or tags are given (g_t not empty) but none of them matches the video's tags/genres
            if g_t and (not (self.genres_and_tags & g_t)):
                continue

            if g_t:
                log(LOG_INFO, 'CondSubs : genre/tag preference {0} met with intersection {1}'.format(g_t, (
                            self.genres_and_tags & g_t)))
            for pref in preferences:
                audio_name, audio_codes, sub_name, sub_codes, forced, ss_tag = pref
                # manage multiple audio and/or subtitle 3-letters codes if present (ex. German = ger,deu)
                audio_codes = audio_codes.split(r',')
                sub_codes = sub_codes.split(r',')
                nbr_sub_codes = len(sub_codes)

                for audio_code in audio_codes:
                    if audio_code is None:
                        log(LOG_DEBUG, 'continue')
                        continue

                    if (self.selected_audio_stream and
                            'language' in self.selected_audio_stream and
                            (audio_code == self.selected_audio_stream['language'] or audio_name ==
                             self.selected_audio_stream['language'] or audio_code == "any")):
                        log(LOG_INFO,
                            'CondSubs : Selected audio language matches conditional preference {0} ({1}:{2}), force tag is {3}'.format(
                                i, audio_name, sub_name, forced))
                        for sub_code in sub_codes:
                            if sub_code == "non":
                                if forced == 'true':
                                    log(LOG_INFO,
                                        'CondSubs : Subtitle condition is None but forced is true, searching a forced subtitle matching selected audio...')
                                    for sub in self.subtitles:
                                        log(LOG_DEBUG, 'Looping subtitles...')
                                        # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                                        if self.isInBlacklist(sub['name'], 'Subtitle'):
                                            log(LOG_INFO,
                                                'CondSubs : one subtitle track is found matching Keyword Blacklist : {0}. Skipping it.'.format(
                                                    ','.join(settings.subtitle_keyword_blacklist)))
                                            continue
                                        if settings.ignore_signs_on and self.isSignsSub(sub['name']):
                                            log(LOG_INFO,
                                                'CondSubs : ignore_signs toggle is on and one such subtitle track is found. Skipping it.')
                                            continue
                                        if (audio_code == sub['language']) or (audio_name == sub['language']):
                                            log(LOG_DEBUG, 'One potential match found...')
                                            if self.testForcedFlag(forced, sub['name'], sub['isforced']):
                                                log(LOG_DEBUG, 'One forced match found...')
                                                log(LOG_INFO,
                                                    'CondSubs : Language of subtitle {0} matches audio preference {1} ({2}:{3}) with forced overriding rule {4}'.format(
                                                        (sub['index'] + 1), i, audio_name, sub_name, forced))
                                                return sub['index']
                                    log(LOG_INFO,
                                        'CondSubs : no match found for preference {0} ({1}:{2}) with forced overriding rule {3}'.format(
                                            i, audio_name, sub_name, forced))
                                return -1
                            else:
                                to_chose_subtitle_indexes = []

                                for sub in self.subtitles:
                                    # Consider empty subtitle language code as und/Undefined so it can still be prioritized in rules, not just ignored
                                    if sub['language'] == "":
                                        sub['language'] = "und"
                                    # take into account -ss tag to prioritize specific Signs&Songs subtitles track
                                    if (sub_code == sub['language']) or (sub_name == sub['language']):
                                        if ss_tag == 'true' and self.isSignsSub(sub['name']):
                                            log(LOG_INFO,
                                                'CondSubs : Language of subtitle {0} matches conditional preference {1} ({2}:{3}) SubTag {4}'.format(
                                                    (sub['index'] + 1), i, audio_name, sub_name, ss_tag))
                                            to_chose_subtitle_indexes.append(sub['index'])
                                            # return sub['index']
                                    # filter out subtitles to be ignored via Signs&Songs Toggle or matching Keywords Blacklist
                                    if self.isInBlacklist(sub['name'], 'Subtitle'):
                                        log(LOG_INFO,
                                            'CondSubs : one subtitle track is found matching Keyword Blacklist : {0}. Skipping it.'.format(
                                                ','.join(settings.subtitle_keyword_blacklist)))
                                        continue
                                    if settings.ignore_signs_on and self.isSignsSub(sub['name']):
                                        log(LOG_INFO,
                                            'CondSubs : ignore_signs toggle is on and one such subtitle track is found. Skipping it.')
                                        continue
                                    if (sub_code == sub['language']) or (sub_name == sub['language']):
                                        if (ss_tag == 'false' and self.testForcedFlag(forced, sub['name'],
                                                                                      sub['isforced'])):
                                            log(LOG_INFO,
                                                'CondSubs : Language of subtitle {0} matches conditional preference {1} ({2}:{3}) forced {4}'.format(
                                                    (sub['index'] + 1), i, audio_name, sub_name, forced))
                                            to_chose_subtitle_indexes.append(sub['index'])

                                current_subtitle_index = self.getSelectedSubtitleIndex()

                                # If our current subtitle is eligible for the condition, we will not change it
                                if current_subtitle_index in to_chose_subtitle_indexes:
                                    log(LOG_INFO,
                                        'CondSubs : already selected subtitle matches preference {0} ({1}:{2}) with forced {3} & ss-tag {4}'.format(
                                            i, audio_name, sub_name, forced, ss_tag))
                                    return current_subtitle_index

                                if len(to_chose_subtitle_indexes) > 0:
                                    # if we have more than one subtitles, we will take the first one
                                    to_chose_subtitle_index = to_chose_subtitle_indexes[0]
                                    log(LOG_INFO,
                                        'CondSubs : Found {0} matching subtitles, using first at index {1}'.format(
                                        len(to_chose_subtitle_indexes), to_chose_subtitle_index))

                                    return to_chose_subtitle_index

                                nbr_sub_codes -= 1
                                if nbr_sub_codes == 0:
                                    log(LOG_INFO,
                                        'CondSubs : no match found for preference {0} ({1}:{2}) with forced {3} & ss-tag {4}'.format(
                                            i, audio_name, sub_name, forced, ss_tag))
                i += 1
        return -2

    def get_original_audio_track_index(self):
        """
        Get the audio track index that matches the original_preferred_list. If no audio track matches, return None.
        The audio track is searched by language, checking for the isoriginal tag. If multiple original found (weird...) the first one is returned.

        :return: The first audio track index tagged as isoriginal and that matches the original_preferred_list.
                -1 if the current selected audio track is already correct (to avoid unnecessary audio change)
                 None if no original audio track found or no match.       
        """

        # Find all 'isoriginal' audio tracks (index, language) that match one language code in the original preferred list
        found_original_audio_languages = [[stream['index'],stream['language']] for stream in self.audiostreams if
                                          ('index' in stream and 'language' in stream and 'isoriginal' in stream
                                            and stream['language'] in settings.audio_original_preflist
								            and stream['isoriginal'])]

        if found_original_audio_languages:
            if found_original_audio_languages[0][0] != self.selected_audio_stream['index']:
                log(LOG_INFO,
                    "Audio: Found at least one preferred original audio track among " + ",".join(settings.audio_original_preflist) +
                    " . Picking first: " + found_original_audio_languages[0][1])
                return found_original_audio_languages[0][0]
            else:
                # Found audio track is already the selected one - No need to change
                log(LOG_INFO,
                    "Audio: Selected audio track matches preferred original list " + ",".join(settings.audio_original_preflist) +
                    " . Keeping it   : " + found_original_audio_languages[0][1])
                return -1
        log(LOG_INFO,
            "Audio: No preferred original audio track found among " + ",".join(settings.audio_original_preflist) +
            " . Continue preferences evaluation...")
        return None

    def isInBlacklist(self, TrackName, TrackType):
        found = False
        test = TrackName.lower()
        if (TrackType == 'Subtitle' and settings.subtitle_keyword_blacklist_enabled and any(
                keyword in test for keyword in settings.subtitle_keyword_blacklist)):
            found = True
        elif (TrackType == 'Audio' and settings.audio_keyword_blacklist_enabled and any(
                keyword in test for keyword in settings.audio_keyword_blacklist)):
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
        activePlayers = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
        json_query = xbmc.executeJSONRPC(activePlayers)
        # json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        activePlayerID = json_response['result'][0]['playerid']
        details_query_dict = {"jsonrpc": "2.0",
                              "method": "Player.GetProperties",
                              "params": {"properties":
                                             ["currentaudiostream", "audiostreams", "subtitleenabled",
                                              "currentsubtitle", "subtitles"],
                                         "playerid": activePlayerID},
                              "id": 1}
        details_query_string = simplejson.dumps(details_query_dict)
        json_query = xbmc.executeJSONRPC(details_query_string)
        # json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)

        if 'result' in json_response and json_response['result'] != None:
            self.selected_audio_stream = json_response['result']['currentaudiostream']
            self.selected_sub = json_response['result']['currentsubtitle']
            self.selected_sub_enabled = json_response['result']['subtitleenabled']
            self.audiostreams = json_response['result']['audiostreams']
            self.subtitles = json_response['result']['subtitles']
        log(LOG_DEBUG, json_response)

        if (
                not settings.custom_condsub_prefs_on and not settings.custom_audio_prefs_on and not settings.custom_sub_prefs_on):
            log(LOG_DEBUG, 'No custom prefs used at all, skipping extra Video tags/genres JSON query.')
            self.genres_and_tags = set()
            return

        genre_tags_query_dict = {"jsonrpc": "2.0",
                                 "method": "Player.GetItem",
                                 "params": {"properties":
                                                ["genre", "tag"],
                                            "playerid": activePlayerID},
                                 "id": 1}
        genre_tags_query_string = simplejson.dumps(genre_tags_query_dict)
        json_query = xbmc.executeJSONRPC(genre_tags_query_string)
        # json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if 'result' in json_response and json_response['result'] != None:
            gt = []
            if 'genre' in json_response['result']['item']:
                gt = json_response['result']['item']['genre']
            if 'tag' in json_response['result']['item']:
                gt.extend(json_response['result']['item']['tag'])
            self.genres_and_tags = set(map(lambda x: x.lower(), gt))
        log(LOG_DEBUG, 'Video tags/genres: {0}'.format(self.genres_and_tags))
        log(LOG_DEBUG, json_response)

    def __del__(self):
        """ Ensure that the watcher thread is properly stopped when the object is deleted """
        if hasattr(self, 'lang_pref_watcher'):
            log(LOG_DEBUG, '__del__ function called : request Watcher Thread to gracefully stop')
            self.lang_pref_watcher.stop()

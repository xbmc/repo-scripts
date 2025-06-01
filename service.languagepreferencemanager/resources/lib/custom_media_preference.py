from logger import log, LOG_INFO, LOG_DEBUG, LOG_ERROR
import xbmcvfs
import json as simplejson

__user_data_path__ = xbmcvfs.translatePath("special://profile/addon_data/service.languagepreferencemanager/")

from resources.lib import kodi_utils


class MediaPreferenceManager:

    def __init__(self):
        self.preferences = []

    def add_preference(self, custom_media_preference):
        if not isinstance(custom_media_preference, CustomMediaPreference):
            log(LOG_ERROR, "Cannot add non-custom media preference")
            return

        if not custom_media_preference:
            log(LOG_ERROR, "Cannot add empty custom media preference")
            return

        matching_preference = self.get_matching_preference(custom_media_preference)
        if matching_preference is not None:
            self.remove_preference(matching_preference)

        self.preferences.append(custom_media_preference)

    def remove_preference(self, custom_media_preference):
        if self.has_preference(custom_media_preference):
            self.preferences.remove(custom_media_preference)

    def has_preference(self, custom_media_preference):
        """
        Check if the custom media preference is already in the list of preferences. That is, if the same media selector is already in the list.
        :param custom_media_preference: The custom media preference to check
        :return: True if the custom media preference is already in the list, False otherwise
        """
        return self.get_matching_preference(custom_media_preference) is not None

    def get_matching_preference(self, custom_media_preference):
        """
        Get the custom media preference that matches the media selector of the given custom media preference. If no preference matches, return None.
        :param custom_media_preference: The custom media preference to match
        :return: The custom media preference that matches the media selector of the given custom media preference, or None if no preference matches
        """
        for preference in self.preferences:
            if preference.selector.is_same_media(custom_media_preference.selector):
                return preference

        return None

    def get_preference(self, player):
        """
        Get the custom media preference that applies to the playing item with the highest priority. If no preference applies, return None.
        e.g. If two preferences apply to the playing item, the one with the highest priority will be returned.
        :param player: The player to get the custom media preference for
        :return:  The custom media preference that applies to the playing item with the highest priority, or None if no preference applies
        """

        applicable_preferences = []

        for preference in self.preferences:
            log(LOG_DEBUG, "Checking preference: " + preference.selector.to_string())
            if preference.selector.applies_to_player(player):
                applicable_preferences.append(preference)

        if len(applicable_preferences) == 0:
            return None

        return max(applicable_preferences, key=lambda preference: preference.priority_index)

    def save_preferences(self):
        file_name = __user_data_path__ + "customMediaPreferences.json"

        with open(file_name, 'w') as file:
            file.write(simplejson.dumps(self.to_json(), indent=4))

    @staticmethod
    def from_file():
        file_name = __user_data_path__ + "customMediaPreferences.json"
        if xbmcvfs.exists(file_name):
            log(LOG_DEBUG, "Attempting custom media preferences from file")

            with open(file_name, 'r') as file:
                # Check if file is empty
                if not file.read(1):
                    log(LOG_DEBUG, "No custom media preferences found (empty file?)")
                    return

                file.seek(0)

                try:
                    return MediaPreferenceManager.from_json(simplejson.loads(file.read()))
                except Exception as e:
                    log(LOG_ERROR, "Failed to load custom media preferences: " + str(e))

        return MediaPreferenceManager()

    def to_json(self):
        return [preference.to_json() for preference in self.preferences]

    @staticmethod
    def from_json(json):
        custom_media_preferences = MediaPreferenceManager()
        for preference_json in json:
            custom_media_preferences.add_preference(CustomMediaPreference.from_json(preference_json))

        log(LOG_DEBUG, "Loaded " + str(len(custom_media_preferences.preferences)) + " custom media preferences")

        return custom_media_preferences


class CustomMediaPreference:

    def __init__(self):
        self.selector = None
        self.priority_index = 0
        self.audio_language = ""
        self.audio_track_id = -1
        self.subtitle_language = ""
        self.subtitle_track_id = -1
        self.enable_subtitles = False

    def apply_to_player(self, player):
        """
        Apply the custom media preference to the player. This will set the audio and subtitle streams according to the preference.

        :param player: The player to apply the custom media preference to
        :return: True if the custom media preference was successfully applied, False otherwise. False can be returned if the audio or subtitle track is not found in the media.
        """
        if not player.isPlayingVideo():
            return False

        set_subtitles = self.subtitle_language or self.subtitle_track_id != -1

        if self.audio_language or self.audio_track_id != -1:
            audio_track_index = self.get_audio_track_index(player)
            if audio_track_index is not None:
                # Changing audio track causes an audio stream change call (delayed)
                # We need to ignore the change, otherwise this we might unnecessarily change the subtitles again
                if set_subtitles:
                    player.add_ignore_audio_change_index(audio_track_index)

                player.setAudioStream(audio_track_index)
            else:
                # If the audio track is not found, we failed to apply the preferences
                return False

        if set_subtitles:
            subtitle_track_index = self.get_subtitle_track_index(player)
            if subtitle_track_index is not None:
                if self.enable_subtitles:
                    player.setSubtitleStream(subtitle_track_index)
                player.showSubtitles(self.enable_subtitles)
            else:
                # If the subtitle track is not found, we failed to apply the preferences.
                # However, we can return success, if the subtitles are disabled and no subtitle track is found.
                return not self.enable_subtitles

        return True

    def get_audio_track_index(self, player):
        """
        Get the audio track index that matches the custom media preference. If no audio track matches, return None.
        First, the audio track is searched by language. If no audio track is found by language, the audio track is searched by raw index.

        :param player: The player to get the audio track index for
        :return: The audio track index that matches the custom media preference, or None if no audio track matches
        """

        # Find all audio tracks (index) that match the language code
        found_audio_languages = [stream['index'] for stream in player.audiostreams if
                                 stream['language'] == self.audio_language]

        if found_audio_languages:
            if len(found_audio_languages) == 1:
                log(LOG_DEBUG,
                    "Found audio track by language " + self.audio_language + " for file " + player.getPlayingFile())
                return found_audio_languages[0]
            elif len(found_audio_languages) > 1:
                log(LOG_DEBUG, "Multiple audio tracks found for language " + self.audio_language + " for file " + player.getPlayingFile())

        if self.audio_track_id != -1:
            log(LOG_DEBUG,
                "Failed to find audio track by language " + self.audio_language + " for file " + player.getPlayingFile() + ". Trying by index")
            if self.audio_track_id < len(player.audiostreams):
                log(LOG_DEBUG, "Found audio track by index " + str(self.audio_track_id) + " for file " + player.getPlayingFile())
                return self.audio_track_id
            else:
                log(LOG_ERROR, "Audio track id " + str(
                    self.audio_track_id) + " is out of range for file " + player.getPlayingFile())

        if found_audio_languages:
            log(LOG_DEBUG,
                "Multiple audio tracks found for language " + self.audio_language + " for file " + player.getPlayingFile() + " and no set index. Picking first.")
            return found_audio_languages

        return None

    def get_subtitle_track_index(self, player):
        """
        Get the subtitle track index that matches the custom media preference. If no subtitle track matches, return None.
        First, the subtitle track is searched by language. If no subtitle track is found by language, the subtitle track is searched by raw index.

        :param player: The player to get the subtitle track index for
        :return: The subtitle track index that matches the custom media preference, or None if no subtitle track matches
        """

        # Find all subtitle tracks (index) that match the language code
        found_language_subtitles = [subtitle['index'] for subtitle in player.subtitles if
                                    subtitle['language'] == self.subtitle_language]

        if found_language_subtitles:
            if len(found_language_subtitles) == 1:
                log(LOG_DEBUG,
                    f"Found subtitle track by language {self.subtitle_language} for file {player.getPlayingFile()}")
                return found_language_subtitles[0]
            else:
                log(LOG_DEBUG,
                    f"Multiple subtitle tracks found for language {self.subtitle_language} for file {player.getPlayingFile()}")

        if self.subtitle_track_id != -1:
            log(LOG_DEBUG,
                "Failed to find subtitle track by language " + self.subtitle_language + " for file " + player.getPlayingFile() + ". Trying by index")
            if self.subtitle_track_id < len(player.subtitles):
                log(LOG_DEBUG, "Found subtitle track by index " + str(self.subtitle_track_id) + " for file " + player.getPlayingFile())
                return self.subtitle_track_id
            else:
                log(LOG_ERROR, "Subtitle track id " + str(
                    self.subtitle_track_id) + " is out of range for file " + player.getPlayingFile())

        if found_language_subtitles:
            log(LOG_DEBUG,
                f"Multiple subtitle tracks found for language {self.subtitle_language} for file {player.getPlayingFile()} and no set index. Picking first.")
            return found_language_subtitles[0]

        return None

    def to_json(self):
        """
        Convert the custom media preference to a JSON object. The selector is converted to a string separately.
        Counterpart to from_json.
        :return: The custom media preference as a JSON object
        """
        selector_string = ""

        if self.selector:
            selector_string = self.selector.to_string()

        return {
            "selector": selector_string,
            "priority": self.priority_index,
            "audio_language": self.audio_language,
            "audio_track_id": self.audio_track_id,
            "subtitle_language": self.subtitle_language,
            "subtitle_track_id": self.subtitle_track_id,
            "enable_subtitles": self.enable_subtitles
        }

    @staticmethod
    def from_json(json):
        """
        Create a custom media preference from a JSON object. The selector is created from a string separately.
        Counterpart to to_json.
        :param json: The JSON object to create the custom media preference from
        :return: The custom media preference created from the JSON object
        """
        custom_media_preference = CustomMediaPreference()
        custom_media_preference.selector = MediaSelector.from_string(json["selector"])
        custom_media_preference.priority_index = json["priority"]
        custom_media_preference.audio_language = json["audio_language"]
        custom_media_preference.audio_track_id = json["audio_track_id"]
        custom_media_preference.subtitle_language = json["subtitle_language"]
        custom_media_preference.subtitle_track_id = json["subtitle_track_id"]
        custom_media_preference.enable_subtitles = json["enable_subtitles"]
        return custom_media_preference

    @staticmethod
    def from_player(player):
        """
        Create a custom media preference from the currently playing item of the player. The selector is created from the playing item.
        :param player: The player to create the custom media preference from
        :return: The custom media preference created from the player or None if the player is not playing a video
        """

        if not player.isPlayingVideo():
            return None

        custom_media_preference = CustomMediaPreference()
        custom_media_preference.selector = MediaSelector.from_playing_item(player)

        custom_media_preference.audio_language = player.getSelectedAudioLanguage()
        custom_media_preference.audio_track_id = player.getSelectedAudioIndex()
        custom_media_preference.subtitle_language = player.getSelectedSubtitleLanguage()
        custom_media_preference.subtitle_track_id = player.getSelectedSubtitleIndex()
        custom_media_preference.enable_subtitles = player.selected_sub_enabled

        return custom_media_preference


class MediaSelector:
    """
    A media selector is used to identify and store a specific media item. It can be created from a playing item or restored from a string.
    MediaSelector supports two types of media selection:
    - TV Show: The TV show name is used to identify the media item.
    - File: The file name is used to identify the media item.
    """

    def __init__(self):
        self.tv_show_name = ""
        self.file_name = ""

    def applies_to_player(self, player):
        """
        Check if the media selector applies to the player. That is, if the playing item of the player matches the media selector.
        :param player: The player to check the media selector against
        :return: True if the media selector applies to the player, False otherwise
        """
        if not player:
            return False

        if not player.isPlayingVideo():
            log(LOG_DEBUG, 'Player is not playing video, cannot apply media selector')
            return False

        playing_item = player.getPlayingItem()

        if not playing_item:
            log(LOG_DEBUG, 'No playing item found, cannot apply media selector')
            return

        video_info_tag = playing_item.getVideoInfoTag()

        if not video_info_tag:
            log(LOG_DEBUG, 'No video info tag found, cannot apply media selector')
            return

        is_tv_show = kodi_utils.is_tv_show(video_info_tag.getMediaType())
        log(LOG_DEBUG, 'Media Info: ' + video_info_tag.getMediaType() + " is_tv_show: " + str(is_tv_show))

        if is_tv_show and self.tv_show_name:
            log(LOG_DEBUG,
                'Checking TV Show name: ' + self.tv_show_name + ' against ' + video_info_tag.getTVShowTitle())
            return video_info_tag.getTVShowTitle() == self.tv_show_name
        elif self.file_name:
            log(LOG_DEBUG, 'Checking file name: ' + self.file_name + ' against ' + player.getPlayingFile())
            return player.getPlayingFile() == self.file_name
        else:
            return False

    def to_string(self):
        """
        Convert the media selector to a string. The string is used to serialize the media selector.
        Counterpart to from_string.
        :return: The media selector as a string
        """
        type_name = self.get_type_name()
        display_name = self.get_display_name()
        return type_name + ":" + display_name

    def get_display_name(self):
        """
        Get the display name of the media selector. The display name is used to identify the media selector in the UI.
        :return: The display name of the media selector
        """
        if self.tv_show_name:
            return self.tv_show_name
        elif self.file_name:
            return self.file_name
        else:
            return "Unknown Media Selector"

    def get_type_name(self):
        """
        Get the type name of the media selector. The type name is used to identify the media selector type.
        :return: The type name of the media selector
        """
        if self.tv_show_name:
            return "tv_show"
        elif self.file_name:
            return "file"
        else:
            return "unknown"

    def is_same_media(self, media_selector):
        """
        Check if the media selector is the same as the given media selector. That is, if the media selector serializes to the same string.
        :param media_selector: The media selector to compare to
        :return: True if the media selector is the same as the given media selector, False otherwise
        """
        return self.to_string() == media_selector.to_string()

    @staticmethod
    def from_string(s):
        """
        Create a media selector from a string.
        Counterpart to to_string.
        :param s: The string to create the media selector from
        :return: The media selector created from the string
        """
        if not s:
            return None

        media_info = MediaSelector()
        if s.startswith("tv_show:"):
            media_info.tv_show_name = s[8:]
        elif s.startswith("file:"):
            media_info.file_name = s[5:]
        return media_info

    @staticmethod
    def from_playing_item(player):
        """
        Create a media selector from the playing item of the player. The media selector is created based on the media type of the playing item.
        If the media type is a TV show, the TV show name is used. If the media type is a movie, the file name is used.
        :param player: The player to create the media selector from
        :return: The media selector created from the playing item or None if the player is not playing a video
        """
        media_selector = MediaSelector()
        playing_item = player.getPlayingItem()

        video_info_tag = playing_item.getVideoInfoTag()

        if not video_info_tag:
            log(LOG_ERROR, 'No video info tag found, cannot create media selector')
            return

        media_selector.tv_show_name = video_info_tag.getTVShowTitle()
        media_selector.file_name = player.getPlayingFile()

        return media_selector


media_preference_manager = MediaPreferenceManager.from_file()

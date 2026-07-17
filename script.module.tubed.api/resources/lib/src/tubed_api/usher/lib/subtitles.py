# -*- coding: utf-8 -*-
"""

    Copyright (C) 2017-2020 plugin.video.youtube
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit


class Subtitles:
    def __init__(self, video_id, captions):
        self.video_id = video_id

        self.caption_track = {}

        renderer = captions.get('playerCaptionsTracklistRenderer', {})

        self.caption_tracks = renderer.get('captionTracks', [])
        self.translation_languages = renderer.get('translationLanguages', [])

        default_audio = renderer.get('defaultAudioTrackIndex')
        if default_audio:
            audio_tracks = renderer.get('audioTracks', [])

            try:
                audio_track = audio_tracks[default_audio]
            except:  # pylint: disable=bare-except
                audio_track = None

            if audio_track:
                default_caption = audio_track.get('defaultCaptionTrackIndex')

                if not default_caption:
                    default_caption = audio_track.get('captionTrackIndices')
                    if default_caption and isinstance(default_caption, list):
                        default_caption = default_caption[0]

                if default_caption and default_caption in self.caption_tracks:
                    self.caption_track = self.caption_tracks[default_caption]

    def retrieve(self):
        list_of_subs = []

        all_captions = self.translation_languages + self.caption_tracks
        for language in all_captions:
            subtitle = self._get(language=language.get('languageCode'))
            if subtitle:
                list_of_subs.append(subtitle)

        return list(set(list_of_subs))

    def _get(self, language='en'):
        caption = None

        for track in self.caption_tracks:
            if language == track.get('languageCode'):
                if track.get('kind') == 'asr':
                    if not caption:
                        caption = track
                    continue

                caption = track
                break

        has_translation = any(lang for lang in self.translation_languages
                              if lang.get('languageCode') == language)

        if not has_translation and not caption:
            return None

        subtitle_url = None
        if not caption and has_translation:
            base_url = self.caption_track.get('baseUrl')
            if base_url:
                subtitle_url = self.set_query_param(base_url, 'tlang', language)

        elif caption:
            base_url = caption.get('baseUrl')
            if base_url:
                subtitle_url = base_url

        if subtitle_url:
            subtitle_url = self.set_query_param(subtitle_url, 'type', 'track')
            subtitle_url = self.set_query_param(subtitle_url, 'fmt', 'vtt')
            return (caption.get('languageCode'),
                    self._get_language_name(caption),
                    caption.get('kind'),
                    subtitle_url)

        return None

    @staticmethod
    def _get_language_name(track):
        key = 'languageName' if 'languageName' in track else 'name'

        lang_name = track.get(key, {}).get('simpleText')
        if lang_name:
            return lang_name

        if not lang_name:
            track_name = track.get(key, {}).get('runs', [{}])

            if isinstance(track_name, list) and len(track_name) >= 1:
                return track_name[0].get('text')

        return ''

    @staticmethod
    def set_query_param(url, name, value):
        scheme, netloc, path, query_string, fragment = urlsplit(url)
        query_params = parse_qs(query_string)

        query_params[name] = [value]
        new_query_string = urlencode(query_params, doseq=True)
        if isinstance(scheme, bytes):
            new_query_string = new_query_string.encode('utf-8')

        return urlunsplit((scheme, netloc, path, new_query_string, fragment))

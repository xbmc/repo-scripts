import xbmc

from resources.lib.utils import (
    get_setting_bool, get_setting_int, get_show_uniqueids,
    log, log_error, notify
)


class BingebasePlayer(xbmc.Player):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._playing = False
        self._media_info = None
        self._total_time = 0
        self._last_time = 0

    def onAVStarted(self):
        if not get_setting_bool('scrobble_enabled'):
            return

        try:
            info_tag = self.getVideoInfoTag()
            media_type = info_tag.getMediaType()

            if media_type not in ('movie', 'episode'):
                return

            if media_type == 'movie' and not get_setting_bool('scrobble_movies'):
                return
            if media_type == 'episode' and not get_setting_bool('scrobble_episodes'):
                return

            self._total_time = self.getTotalTime()
            self._last_time = 0
            self._media_info = self._build_media_info(info_tag, media_type)
            self._playing = True
        except RuntimeError:
            log_error('Failed to get video info on playback start')
            self._playing = False

    def onPlayBackStopped(self):
        if not self._playing or self._media_info is None:
            return

        self._handle_scrobble('stop', self._last_time)
        self._reset()

    def onPlayBackEnded(self):
        if not self._playing or self._media_info is None:
            return

        self._handle_scrobble('end', self._total_time)
        self._reset()

    def onPlayBackPaused(self):
        self._update_time()

    def onPlayBackResumed(self):
        pass

    def update_time(self):
        """Call periodically from service loop to track playback position."""
        if self._playing:
            self._update_time()

    def _update_time(self):
        try:
            self._last_time = self.getTime()
        except RuntimeError:
            pass

    def _handle_scrobble(self, event, current_time):
        if self._total_time <= 0:
            return

        percent = (current_time / self._total_time) * 100
        threshold = get_setting_int('scrobble_threshold')

        if event == 'stop' and percent < threshold:
            return

        payload = dict(self._media_info)
        payload['event'] = event
        payload['duration'] = int(self._total_time)
        payload['progress'] = {
            'time': int(current_time),
            'percent': round(percent, 1),
        }

        try:
            self.api.scrobble(payload)
            title = self._media_info.get('title', 'Unknown')
            log('Scrobbled: {}'.format(title))

            if get_setting_bool('scrobble_notify'):
                notify('Scrobbled: {}'.format(title))
        except Exception:
            log_error('Failed to scrobble')

    def _build_media_info(self, info_tag, media_type):
        info = {
            'mediaType': media_type,
            'title': info_tag.getTitle(),
            'year': info_tag.getYear(),
            'uniqueIds': {
                'tmdb': info_tag.getUniqueID('tmdb'),
                'tvdb': info_tag.getUniqueID('tvdb'),
                'imdb': info_tag.getUniqueID('imdb'),
            },
        }

        if media_type == 'episode':
            info['tvShowTitle'] = info_tag.getTVShowTitle()
            info['season'] = info_tag.getSeason()
            info['episode'] = info_tag.getEpisode()

            # Get show-level IDs from parent TV show
            show_uids = get_show_uniqueids(info_tag.getDbId())
            info['showUniqueIds'] = {
                'tmdb': show_uids.get('tmdb', ''),
                'tvdb': show_uids.get('tvdb', ''),
                'imdb': show_uids.get('imdb', ''),
            }

        return info

    def _reset(self):
        self._playing = False
        self._media_info = None
        self._total_time = 0
        self._last_time = 0

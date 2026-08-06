import os
import re
import json
from dataclasses import dataclass, asdict, fields
from typing import Optional

import xbmc
import xbmcgui

# noinspection PyPackages
from .utilities import clean_art_url, send_kodi_json
# noinspection PyPackages
from .logger import Logger


@dataclass
class Playback:
    """
    Stores whatever data can be determined about the currently playing (video) item in Kodi -
    what it is, where it's from (library/PVR/addon/file), and enough metadata to identify and
    resume it later. Video only - no audio/song support.
    """
    file: Optional[str] = None
    path: Optional[str] = None
    type: Optional[str] = None  # episode, movie, musicvideo, video (per Kodi types)
    source: Optional[str] = None  # kodi_library, pvr_live, pvr_recording, addon, file
    dbid: Optional[int] = None
    tvshowdbid: Optional[int] = None
    totalseasons: Optional[int] = None
    title: Optional[str] = None
    label: Optional[str] = None
    label2: Optional[str] = None
    thumbnail: Optional[str] = None
    fanart: Optional[str] = None
    poster: Optional[str] = None
    icon: Optional[str] = None
    banner: Optional[str] = None
    clearlogo: Optional[str] = None
    clearart: Optional[str] = None
    landscape: Optional[str] = None
    year: Optional[int] = None
    showtitle: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    resumetime: Optional[int] = None
    totaltime: Optional[int] = None
    duration: Optional[int] = None
    channelname: Optional[str] = None
    channelnumberlabel: Optional[str] = None
    channelgroup: Optional[str] = None
    # Extended metadata - best effort, gathered from VideoPlayer.* InfoLabels during playback
    originaltitle: Optional[str] = None
    plot: Optional[str] = None
    plotoutline: Optional[str] = None
    tagline: Optional[str] = None
    genre: Optional[str] = None  # multi-value fields are stored as Kodi's own " / " joined display string
    director: Optional[str] = None
    writer: Optional[str] = None
    studio: Optional[str] = None
    country: Optional[str] = None
    mpaa: Optional[str] = None
    premiered: Optional[str] = None
    imdbnumber: Optional[str] = None
    trailer: Optional[str] = None
    rating: Optional[float] = None
    votes: Optional[str] = None  # kept as Kodi's own formatted string (e.g. "1,234") rather than parsed
    top250: Optional[int] = None
    playcount: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Playback":
        """
        Construct a Playback from a stored (JSON) dict, tolerant of it having been written by an
        older or newer version of this class - unknown keys (e.g. a field since removed/renamed)
        are dropped rather than raising, and missing keys (e.g. a field added since the dict was
        written) simply fall back to the dataclass defaults.

        :param data: a dict of Playback field values, as previously produced by asdict()/toJson()
        :return: a Playback instance
        """
        if not isinstance(data, dict):
            raise TypeError(f"Playback.from_dict: expected a dict, got {type(data).__name__}")
        known_fields = {f.name for f in fields(cls)}
        unknown_keys = data.keys() - known_fields
        if unknown_keys:
            Logger.debug(f"Playback.from_dict: ignoring unknown stored keys: {sorted(unknown_keys)}")
        return cls(**{key: value for key, value in data.items() if key in known_fields})

    @property
    def pluginlabel(self) -> str:
        """
        Create a more full label, e.g. Showname (2x03) - Episode title

        :return: A human-readable label for this playback
        """
        label = self.title or self.label or self.channelname or (os.path.basename(self.path) if self.path else None) or "Unknown"
        if self.showtitle:
            if (self.season is not None and self.season >= 0) and (self.episode is not None and self.episode >= 0):
                label = f"{self.showtitle} ({self.season}x{self.episode:02d}) - {self.title or label}"
            elif self.season is not None and self.season >= 0:
                label = f"{self.showtitle} ({self.season}x?) - {self.title or label}"
            else:
                label = f"{self.showtitle} - {self.title or label}"
        elif self.channelname:
            if self.source == "pvr_live":
                label = f"{self.channelname} (PVR Live)"
            else:
                label = f"{label} (PVR Recording {self.channelname})"

        if self.source == "addon":
            label = f"{label} (* Add-on)"
        return label

    @property
    def pluginlabel_short(self) -> str:
        """
        Create a shorter label, e.g. Showname (2x03)
        """
        label = self.title or self.label or self.channelname or (os.path.basename(self.path) if self.path else None) or "Unknown"
        if self.showtitle:
            if (self.season is not None and self.season >= 0) and (self.episode is not None and self.episode >= 0):
                label = f"{self.showtitle} ({self.season}x{self.episode:02d})"
            elif self.season is not None and self.season >= 0:
                label = f"{self.showtitle} ({self.season}x?)"
            else:
                label = f"{self.showtitle}"

        return label

    @property
    def resume_timestamp(self) -> str:
        """
        A human-readable "M:SS" rendering of resumetime, or an empty string if there's no
        meaningful (non-zero) resumetime set - handy for notifications/logging, e.g.
        f"Resuming: {label}{f' at {playback.resume_timestamp}' if playback.resume_timestamp else ''}"
        """
        if not self.resumetime:
            return ""
        mins, secs = divmod(int(self.resumetime), 60)
        return f"{mins}:{secs:02d}"

    def _is_addon_playback(self) -> bool:
        """
        Determine if playback originates from an addon

        :return: True if playback is from an addon, False otherwise
        """
        path_lower = (self.path or '').lower()

        # Method 1: Check for plugin:// URLs (most reliable)
        if path_lower.startswith('plugin://'):
            return True

        # Method 2: Check ListItem.Path infolabel for plugin URLs
        listitem_path_lower = xbmc.getInfoLabel('ListItem.Path').lower()
        if listitem_path_lower.startswith('plugin://'):
            return True

        # Method 3: Check if an addon ID is associated with the current item
        addon_id = xbmc.getInfoLabel('ListItem.Property(Addon.ID)')
        if addon_id:
            return True

        # Method 4: Check container path (for addon-generated content)
        container_path_lower = xbmc.getInfoLabel('Container.FolderPath').lower()
        if container_path_lower.startswith('plugin://'):
            return True

        # Method 5: Conservative HTTP fallback for local addon proxies only
        if path_lower.startswith(('http://', 'https://')):
            # Exclude known WebDAV/cloud storage patterns
            webdav_patterns = [
                    '/dav/', 'webdav', '.nextcloud.', 'owncloud', '/remote.php/', 'dropbox', 'googledrive', 'onedrive',
            ]

            if not any(pattern in path_lower for pattern in webdav_patterns):
                # Additional check: look for typical addon URL structures
                if any(indicator in path_lower for indicator in ('plugin', 'addon')):
                    Logger.debug("Classified as addon via HTTP fallback heuristic", path_lower)
                    return True
            # If we still have an Addon.ID or container is a plugin, treat as addon
            addon_id_http = xbmc.getInfoLabel('ListItem.Property(Addon.ID)')
            container_path_lower_http = xbmc.getInfoLabel('Container.FolderPath').lower()
            if addon_id_http or container_path_lower_http.startswith('plugin://'):
                return True
            # Accept loopback hosts commonly used by addon proxy/resolvers
            if any(host in path_lower for host in ('127.0.0.1', 'localhost', '[::1]')):
                Logger.debug("Classified as addon via localhost HTTP fallback", path_lower)
                return True

        return False

    def update(self, new_details: dict) -> None:
        """
        Update a Playback object with new details

        :param new_details: a dictionary (need not be complete) of the Playback object's new details
        """
        for key, value in new_details.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                Logger.error(f"Playback.update: Unknown key [{key}]")

    def toJson(self) -> str:
        """
        Return the Playback object as JSON

        :return: the Playback object as JSON
        """
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def update_playback_details(self, file: str, item: xbmcgui.ListItem) -> None:
        """
        Update the Playback object with details from a playing Kodi ListItem object and InfoLabels

        :param file: the current file Kodi is playing (from xbmc.Player().getPlayingFile())
        :param item: the current Kodi playing item (from xbmc.Player().getPlayingItem())
        """

        self.path = item.getPath()
        self.file = file
        self.label = item.getLabel()
        self.label2 = item.getLabel2()

        # Callers may update resumetime/totaltime themselves as playback progresses, but initialise
        # here in case of early exits etc.
        if self.source != "pvr_live":
            # Getting from the player directly is more reliable than using item.getVideoInfoTag() etc
            self.totaltime = self.duration = int(xbmc.Player().getTotalTime())
            self.resumetime = int(xbmc.Player().getTime())

        # Determine the Playback source - Kodi Library (...get DBID), PVR, Addon, or Non-Library file?
        dbid_label = xbmc.getInfoLabel('VideoPlayer.DBID')
        try:
            self.dbid = int(dbid_label) if dbid_label else None
        except ValueError:
            self.dbid = None

        if self.dbid:
            self.source = "kodi_library"
        elif xbmc.getCondVisibility('PVR.IsPlayingTV') or xbmc.getCondVisibility('PVR.IsPlayingRadio'):
            self.source = "pvr_live"
        elif (self.path or '').lower().startswith('pvr://recordings/'):
            self.source = "pvr_recording"
        elif self._is_addon_playback():
            self.source = "addon"
        else:
            Logger.debug("Not from Kodi library, PVR, or addon - treating as a non-library media file")
            self.source = "file"

        # TITLE
        if self.source != "pvr_live":
            self.title = xbmc.getInfoLabel('VideoPlayer.Title')
        else:
            self.title = xbmc.getInfoLabel('VideoPlayer.ChannelName')

        # MEDIA TYPE (see also source above, e.g. to distinguish PVR from non library video)
        if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):
            self.type = "episode"
            tvshowdbid_label = xbmc.getInfoLabel('VideoPlayer.TvShowDBID')
            try:
                self.tvshowdbid = int(tvshowdbid_label) if tvshowdbid_label else None
            except ValueError:
                self.tvshowdbid = None

        elif self.dbid:
            # A dbid alone doesn't distinguish movie from musicvideo - both live in the video
            # library with a dbid. Musicvideos carry artist metadata that movies don't.
            self.type = "musicvideo" if xbmc.getInfoLabel('VideoPlayer.Artist') else "movie"
        elif xbmc.getInfoLabel('VideoPlayer.ChannelName'):
            self.type = "video"  # use standard mediatype; PVR tracked via self.source
        else:
            self.type = "video"

        # ARTWORK - POSTER, FANART, THUMBNAIL, ICON, and a few extras
        self.poster = clean_art_url(xbmc.getInfoLabel('Player.Art(tvshow.poster)') or xbmc.getInfoLabel('Player.Art(poster)') or xbmc.getInfoLabel('Player.Art(thumb)'))
        self.fanart = clean_art_url(xbmc.getInfoLabel('Player.Art(fanart)'))
        thumbnail = xbmc.getInfoLabel('Player.Art(thumb)') or (item.getArt('thumb') or '')
        self.thumbnail = clean_art_url(thumbnail)
        icon = xbmc.getInfoLabel('Player.Art(icon)') or (item.getArt('icon') or '')
        self.icon = clean_art_url(icon)
        self.banner = clean_art_url(xbmc.getInfoLabel('Player.Art(banner)'))
        self.clearlogo = clean_art_url(xbmc.getInfoLabel('Player.Art(clearlogo)'))
        self.clearart = clean_art_url(xbmc.getInfoLabel('Player.Art(clearart)'))
        self.landscape = clean_art_url(xbmc.getInfoLabel('Player.Art(landscape)'))

        # OTHER DETAILS
        # PVR Live/Recordings
        self.channelname = xbmc.getInfoLabel('VideoPlayer.ChannelName')
        self.channelnumberlabel = xbmc.getInfoLabel('VideoPlayer.ChannelNumberLabel')
        self.channelgroup = xbmc.getInfoLabel('VideoPlayer.ChannelGroup')
        # Episodes & Movies
        year_label = xbmc.getInfoLabel('VideoPlayer.Year')
        try:
            self.year = int(year_label) if year_label else None
        except ValueError:
            self.year = None
        # Episodes
        self.showtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
        season_label = xbmc.getInfoLabel('VideoPlayer.Season')
        episode_label = xbmc.getInfoLabel('VideoPlayer.Episode')
        try:
            self.season = int(season_label) if season_label else None
        except ValueError:
            self.season = None
        try:
            self.episode = int(episode_label) if episode_label else None
        except ValueError:
            self.episode = None

        # EXTENDED METADATA - best effort, for as rich a resumed/switched-back ListItem as possible
        self.originaltitle = xbmc.getInfoLabel('VideoPlayer.OriginalTitle') or None
        self.plot = xbmc.getInfoLabel('VideoPlayer.Plot') or None
        self.plotoutline = xbmc.getInfoLabel('VideoPlayer.PlotOutline') or None
        self.tagline = xbmc.getInfoLabel('VideoPlayer.TagLine') or None
        self.genre = xbmc.getInfoLabel('VideoPlayer.Genre') or None
        self.director = xbmc.getInfoLabel('VideoPlayer.Director') or None
        self.writer = xbmc.getInfoLabel('VideoPlayer.Writer') or None
        self.studio = xbmc.getInfoLabel('VideoPlayer.Studio') or None
        self.country = xbmc.getInfoLabel('VideoPlayer.Country') or None
        self.mpaa = xbmc.getInfoLabel('VideoPlayer.mpaa') or None
        self.premiered = xbmc.getInfoLabel('VideoPlayer.Premiered') or None
        self.imdbnumber = xbmc.getInfoLabel('VideoPlayer.IMDBNumber') or None
        self.trailer = xbmc.getInfoLabel('VideoPlayer.Trailer') or None
        self.votes = xbmc.getInfoLabel('VideoPlayer.Votes') or None

        rating_label = xbmc.getInfoLabel('VideoPlayer.Rating')
        try:
            self.rating = float(rating_label) if rating_label else None
        except ValueError:
            self.rating = None

        top250_label = xbmc.getInfoLabel('VideoPlayer.Top250')
        try:
            self.top250 = int(top250_label) if top250_label else None
        except ValueError:
            self.top250 = None

        playcount_label = xbmc.getInfoLabel('VideoPlayer.PlayCount')
        try:
            self.playcount = int(playcount_label) if playcount_label else None
        except ValueError:
            self.playcount = None

        # Episodes -> we also want the number of seasons so callers can force-browse to the
        # appropriate spot after a resumed playback
        if self.tvshowdbid:
            json_dict = {
                    "jsonrpc":"2.0",
                    "id":"VideoLibrary.GetSeasons",
                    "method":"VideoLibrary.GetSeasons",
                    "params":{
                            "tvshowid":self.tvshowdbid,
                    },
            }

            properties_json = send_kodi_json(f'Get seasons details for tv show {self.showtitle}', json_dict)
            if not properties_json or 'result' not in properties_json:
                Logger.error("VideoLibrary.GetSeasons returned no result")
                self.totalseasons = None
                # Continue without seasons info
                return

            if 'error' in properties_json:
                Logger.error("VideoLibrary.GetSeasons returned error:", properties_json['error'])
                self.totalseasons = None
                return
            properties = properties_json['result']

            # {'limits': {'end': 2, 'start': 0, 'total': 2}, 'seasons': [...]}
            total_limit = properties.get('limits', {}).get('total')
            self.totalseasons = total_limit if isinstance(total_limit, int) else None
            if self.totalseasons is None and 'seasons' in properties:
                self.totalseasons = len(properties['seasons'])

    @staticmethod
    def _split_multi(value: Optional[str]) -> list:
        """
        Split one of Kodi's own joined multi-value display strings (genre, director, writer,
        studio, country - Kodi joins these with " / " by default, though a comma is also seen)
        back into a list, for the setters that want one.

        :param value: a Kodi-style joined string, e.g. "Action / Adventure"
        :return: a list of the individual values, e.g. ["Action", "Adventure"]
        """
        if not value:
            return []
        return [v.strip() for v in re.split(r'\s*/\s*|\s*,\s*', value) if v.strip()]

    def _apply_modern_video_tag(self, tag, duration_seconds: Optional[int]) -> None:
        """
        Populate a ListItem's InfoTagVideo using its modern, settable API (Kodi 20/Nexus+). Every
        setter is called defensively (only if present, and only for values we actually have) so
        that gaps in either the stored metadata or the Kodi version's API surface just mean less
        gets set, rather than an error.

        :param tag: the InfoTagVideo object, from ListItem.getVideoInfoTag()
        :param duration_seconds: playback duration in seconds, if known
        """
        def set_if(method_name: str, *args) -> None:
            method = getattr(tag, method_name, None)
            if method:
                method(*args)

        if self.type:
            set_if('setMediaType', self.type)
        if self.dbid:
            set_if('setDbId', self.dbid)
        if self.title:
            set_if('setTitle', self.title)
        if self.originaltitle:
            set_if('setOriginalTitle', self.originaltitle)
        if self.plot:
            set_if('setPlot', self.plot)
        if self.plotoutline:
            set_if('setPlotOutline', self.plotoutline)
        if self.tagline:
            set_if('setTagLine', self.tagline)
        genres = self._split_multi(self.genre)
        if genres:
            set_if('setGenres', genres)
        directors = self._split_multi(self.director)
        if directors:
            set_if('setDirectors', directors)
        writers = self._split_multi(self.writer)
        if writers:
            set_if('setWriters', writers)
        studios = self._split_multi(self.studio)
        if studios:
            set_if('setStudios', studios)
        countries = self._split_multi(self.country)
        if countries:
            set_if('setCountries', countries)
        if self.mpaa:
            set_if('setMpaa', self.mpaa)
        if self.premiered:
            set_if('setPremiered', self.premiered)
        if self.year:
            set_if('setYear', self.year)
        if self.imdbnumber:
            set_if('setIMDBNumber', self.imdbnumber)
        if self.top250:
            set_if('setTop250', self.top250)
        if self.trailer:
            set_if('setTrailer', self.trailer)
        if self.playcount is not None:
            set_if('setPlaycount', self.playcount)
        if self.rating is not None:
            votes = 0
            if self.votes:
                try:
                    votes = int(str(self.votes).replace(',', ''))
                except ValueError:
                    votes = 0
            set_if('setRating', self.rating, votes)
        if self.showtitle:
            set_if('setTvShowTitle', self.showtitle)
        if self.season is not None:
            set_if('setSeason', self.season)
        if self.episode is not None:
            set_if('setEpisode', self.episode)
        if duration_seconds is not None:
            set_if('setDuration', int(duration_seconds))
        if self.path:
            set_if('setFilenameAndPath', self.path)
        # Required, otherwise immediate resumed playback won't resume properly
        set_if('setResumePoint', float(self.resumetime or 0.0), float(self.totaltime or 0.0))

    def _apply_legacy_video_info(self, list_item: xbmcgui.ListItem, duration_seconds: Optional[int]) -> None:
        """
        Populate a ListItem's video info using the older, universally-supported setInfo()/
        setProperty() APIs - the only option on Kodi versions (e.g. Matrix) that predate the
        settable InfoTagVideo. Deprecated on newer Kodi (logs a warning), but still fully
        functional, and this path is only used as a fallback when the modern API isn't available.

        :param list_item: the ListItem to populate
        :param duration_seconds: playback duration in seconds, if known
        """
        info = {
                'mediatype':self.type,
                'title':self.title,
                'originaltitle':self.originaltitle,
                'plot':self.plot,
                'plotoutline':self.plotoutline,
                'tagline':self.tagline,
                'genre':self._split_multi(self.genre),
                'director':self._split_multi(self.director),
                'writer':self._split_multi(self.writer),
                'studio':self._split_multi(self.studio),
                'country':self._split_multi(self.country),
                'mpaa':self.mpaa,
                'premiered':self.premiered,
                'year':self.year,
                'imdbnumber':self.imdbnumber,
                'top250':self.top250,
                'trailer':self.trailer,
                'playcount':self.playcount,
                'dbid':self.dbid,
                'path':self.path,
                'tvshowtitle':self.showtitle,
                'episode':self.episode,
                'season':self.season,
                'duration':duration_seconds,
                'rating':self.rating,
        }
        info = {key:value for key, value in info.items() if value not in (None, '', [])}
        list_item.setInfo('video', info)
        # Required, otherwise immediate resumed playback won't resume properly
        list_item.setProperty('ResumeTime', str(self.resumetime or 0))
        list_item.setProperty('TotalTime', str(self.totaltime or 0))

    def create_list_item_from_playback(self) -> xbmcgui.ListItem:
        """
        Create a Kodi ListItem object from a Playback object, with as much metadata attached as
        possible (title, artwork, cast/crew/plot, episode/season, resume point etc) so Kodi's UI
        has something meaningful to display, rather than e.g. a bare "stream" label. Uses the
        modern, settable InfoTagVideo API (Kodi 20/Nexus+) when available, since that avoids the
        deprecation warnings the older setInfo() API now logs - and falls back to setInfo()/
        setProperty() on older Kodi (e.g. Matrix), where the modern API doesn't exist.

        :return: ListItem: a Kodi ListItem object constructed from the Playback object
        """

        Logger.debug("Creating list item from playback:", self)

        list_item = xbmcgui.ListItem(label=self.pluginlabel, path=self.file if self.source not in ["addon", "pvr_live"] else self.path)
        art = {key:value for key, value in {"thumb":self.thumbnail, "poster":self.poster, "fanart":self.fanart, "icon":self.icon,
                                             "banner":self.banner, "clearlogo":self.clearlogo, "clearart":self.clearart, "landscape":self.landscape}.items() if value}
        if art:
            list_item.setArt(art)
        list_item.setProperty('IsPlayable', 'true')

        # PVR channels are not really videos! See: https://forum.kodi.tv/showthread.php?tid=381623&pid=3232826#pid3232826
        # So that's all we need to do for PVR playbacks
        if self.source == "pvr_live":
            return list_item

        duration_seconds = self.duration if self.duration is not None else self.totaltime

        try:
            tag = list_item.getVideoInfoTag()
            if hasattr(tag, 'setResumePoint'):
                self._apply_modern_video_tag(tag, duration_seconds)
            else:
                self._apply_legacy_video_info(list_item, duration_seconds)
        except Exception as e:
            Logger.error(f"create_list_item_from_playback: error setting video info via modern API, falling back to legacy: {e}")
            try:
                self._apply_legacy_video_info(list_item, duration_seconds)
            except Exception as e2:
                Logger.error(f"create_list_item_from_playback: legacy fallback also failed, list item will have minimal metadata: {e2}")

        if self.tvshowdbid:
            list_item.setProperty('tvshowdbid', str(self.tvshowdbid))

        return list_item

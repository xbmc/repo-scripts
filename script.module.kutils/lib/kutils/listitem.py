# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
import xbmc
from kutils import utils


class ListItem:
    ICON_OVERLAY_NONE = 0       # No overlay icon
    ICON_OVERLAY_RAR = 1        # Compressed *.rar files
    ICON_OVERLAY_ZIP = 2        # Compressed *.zip files
    ICON_OVERLAY_LOCKED = 3     # Locked files
    ICON_OVERLAY_UNWATCHED = 4  # For not watched files
    ICON_OVERLAY_WATCHED = 5    # For seen files
    ICON_OVERLAY_HD = 6         # Is on hard disk stored

    def __init__(self, label="", label2="", path="", infos=None, properties=None, size="", artwork=None, ratings=None, ids=None):
        """
        Kodi listitem, based on built-in datatypes
        """
        #
        # Define all instance variables
        #
        self.size = ""
        self.videoinfo = []
        self.audioinfo = []
        self.subinfo = []
        self.cast = []
        self.specials = {}
        self._is_folder = False
        self.type: str = ""
        self.label: str = ""
        self.label2 = ""

        self.set_label(label)
        self.set_label2(label2)
        self.path = path
        self._properties = properties if properties else {}
        self._artwork = artwork if artwork else {}
        self._ratings: Dict[str, str] = ratings if ratings else []
        self._ids = ids if ids else {}
        self._infos = infos if infos else {}

    def __setitem__(self, key, value):
        self._properties[key] = value

    def __getitem__(self, key):
        if key in self._properties:
            return self._properties[key]
        elif key in self._artwork:
            return self._artwork[key]
        elif key in self._infos:
            return self._infos[key]
        elif key == "properties":
            return self._properties
        elif key == "infos":
            return self._infos
        elif key == "artwork":
            return self._artwork
        elif key == "label":
            return self.label
        elif key == "label2":
            return self.label2
        elif key == "path":
            return self.path
        else:
            raise KeyError(str(key))

    def __repr__(self):
        return "\n".join(["Label:", self.label,
                          "Label2:", self.label2,
                          "InfoLabels:", utils.dump_dict(self._infos),
                          "Properties:", utils.dump_dict(self._properties),
                          "Artwork:", utils.dump_dict(self._artwork),
                          "Specials:", utils.dump_dict(self.specials),
                          "", ""])

    def __contains__(self, key):
        if key in self._properties:
            return True
        elif key in self._artwork:
            return True
        elif key in self._infos:
            return True
        elif key in ["properties", "infos", "artwork", "label", "label2", "path"]:
            return True

    def __delitem__(self, key):
        if key in self._properties:
            del self._properties[key]

    def get(self, key, fallback=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return fallback

    def update_from_listitem(self, listitem):
        if not listitem:
            return None
        self.set_label(listitem.label)
        self.set_label2(listitem.label2)
        self.set_size(listitem.size)
        self.update_properties(listitem.get_properties())
        self.update_artwork(listitem.get_artwork())
        self.update_infos(listitem.get_infos())

    def set_label(self, label):
        self.label = label

    def set_label2(self, label):
        self.label2 = label

    def set_mimetype(self, mimetype):
        self.specials["mimetype"] = mimetype

    def fix_at_top(self):
        self.specials["specialsort"] = "top"

    def fix_at_bottom(self):
        self.specials["specialsort"] = "bottom"

    def set_startoffset(self, value):
        self.specials["startoffset"] = value

    def set_totaltime(self, value):
        self.specials["totaltime"] = value

    def set_resumetime(self, value):
        self.specials["resumetime"] = value

    def set_playable(self, value):
        self.specials["isPlayable"] = value

    def is_playable(self):
        return bool(self.specials.get("isPlayable"))

    def set_folder(self, value):
        self._is_folder = value

    def is_folder(self):
        return bool(self._is_folder)

# playlist_starting_track isspecial item_start isplayable

    def set_size(self, size):
        self.size = size

    def set_visible(self, condition):
        self.specials["node.visible"] = condition

    def set_target(self, target):
        self.specials["node.target"] = target

    def set_infos(self, infos):
        self._infos = infos

    def set_artwork(self, artwork):
        self._artwork = artwork

    def set_properties(self, properties):
        self._properties = properties

    def update_properties(self, properties):
        self._properties.update({k: v for k, v in properties.items() if v})

    def update_artwork(self, artwork):
        self._artwork.update({k: v for k, v in artwork.items() if v})

    def update_infos(self, infos):
        self._infos.update({k: v for k, v in infos.items() if v})

    def set_art(self, key, value):
        self._artwork[key] = value

    def set_property(self, key, value):
        self._properties[key] = value

    def set_info(self, key, value):
        self._infos[key] = value

    def get_path(self):
        return self.path

    def get_art(self, key):
        value = self._artwork.get(key)
        return value if value else ""

    def get_info(self, key):
        value = self._infos.get(key)
        return value if value else ""

    def get_property(self, key):
        value = self._properties.get(key)
        return value if value else ""

    def get_artwork(self):
        return {k: v for k, v in self._artwork.items() if v}

    def get_infos(self):
        return {k: v for k, v in self._infos.items() if v}

    def get_properties(self):
        return {k: v for k, v in self._properties.items() if v}

    def get_listitem(self) -> xbmcgui.ListItem:
        listitem: xbmcgui.ListItem
        listitem = xbmcgui.ListItem(label=str(self.label) if self.label else "",
                                    label2=str(self.label2) if self.label2 else "",
                                    path=self.path)
        props = {k: str(v) for k, v in self._properties.items() if v}
        infos = {k.lower(): v for k, v in self._infos.items() if v}
        infos["path"] = self.path
        if "duration" in infos:
            props['duration(h)'] = utils.format_time(infos["duration"], "h")
            props['duration(m)'] = utils.format_time(infos["duration"], "m")
        for key, value in props.items():
            listitem.setProperty(key, str(value))
        for key, value in self.specials.items():
            listitem.setProperty(key, str(value))
        artwork = {k: v for k, v in self._artwork.items() if v}
        if artwork:
            listitem.setArt(artwork)
        if infos:
            listitem.setInfo(self.type, infos)
        return listitem

    def to_windowprops(self, prefix="", window_id=10000):
        window = xbmcgui.Window(window_id)
        window.setProperty('%slabel' % (prefix), self.label)
        window.setProperty('%slabel2' % (prefix), self.label2)
        window.setProperty('%spath' % (prefix), self.path)
        dct = utils.merge_dicts(self.get_properties(),
                                self.get_artwork(),
                                self.get_infos())
        for k, v in dct.items():
            window.setProperty('%s%s' % (prefix, k), str(v))


class AudioItem(ListItem):
    """
    Kodi audio listitem, based on built-in datatypes
    """
    props = ["id",
             "artist_instrument",
             "artist_style",
             "artist_mood",
             "artist_born",
             "artist_formed",
             "artist_description",
             "artist_genre",
             "artist_died",
             "artist_disbanded",
             "artist_yearsactive",
             "artist_born",
             "artist_died",
             "album_description",
             "album_theme",
             "album_mood",
             "album_style",
             "album_type",
             "album_label",
             "album_artist",
             "album_genre",
             "album_title",
             "album_rating",
             "album_userrating",
             "album_votes",
             "album_releasetype"]

    def __init__(self, *args, **kwargs):
        self.type = "music"
        super().__init__(*args, **kwargs)

    def from_listitem(self, listitem):
        info = listitem.getAudioInfoTag()
        self.label = listitem.getLabel()
        self.path = info.getPath()
        self._infos = {"dbid": info.GetDatabaseId(),
                       "mediatype": info.GetMediaType(),
                       "title": info.GetTitle(),
                       "votes": info.GetVotes(),
                       "rating": info.GetRating(),
                       "userrating": info.GetUserRating(),
                       "file": info.GetFile(),
                       "comment": info.getComment(),
                       "lyrics": info.getLyrics(),
                       "genre": info.getGenre(),
                       "lastplayed": info.getLastPlayed(),
                       "listeners": info.getListeners(),
                       "playcount": info.getPlayCount(),
                       "year": info.getReleaseDate()}
        self._properties = {key: listitem.getProperty(key) for key in self.props}

    def from_infolabels(self):
        self.label = xbmc.getInfoLabel("ListItem.Label")
        self.path = xbmc.getInfoLabel("ListItem.Path")
        self._infos = {"dbid": xbmc.getInfoLabel("ListItem.Label"),
                       "mediatype": xbmc.getInfoLabel("ListItem.DBType"),
                       "title": xbmc.getInfoLabel("ListItem.Title"),
                       "votes": xbmc.getInfoLabel("ListItem.Votes"),
                       "rating": xbmc.getInfoLabel("ListItem.Rating"),
                       "userrating": xbmc.getInfoLabel("ListItem.UserRating"),
                       "file": xbmc.getInfoLabel("ListItem.FileNameAndPath"),
                       "comment": xbmc.getInfoLabel("ListItem.Comment"),
                       "lyrics": xbmc.getInfoLabel("ListItem.Lyrics"),
                       "genre": xbmc.getInfoLabel("ListItem.Genre"),
                       "lastplayed": xbmc.getInfoLabel("ListItem.Label"),
                       "listeners": xbmc.getInfoLabel("ListItem.Listeners"),
                       "playcount": xbmc.getInfoLabel("ListItem.Playcount"),
                       "year": xbmc.getInfoLabel("ListItem.Year")}
        self._properties = {key: xbmc.getInfoLabel("ListItem.Property({}".format(key)) for key in self.props}


class VideoItem(ListItem):
    """
    Kodi video listitem, based on built-in datatypes
    """

    def __init__(self, *args, **kwargs):
        self.type = "video"
        super().__init__(*args, **kwargs)

    def __repr__(self):
        baseinfo = super().__repr__()
        return "\n".join([baseinfo,
                          "Cast:", utils.dump_dict(self.cast),
                          "VideoStreams:", utils.dump_dict(self.videoinfo),
                          "AudioStreams:", utils.dump_dict(self.audioinfo),
                          "Ratings:", utils.dump_dict(self._ratings),
                          "Ids:", utils.dump_dict(self._ids),
                          "Subs:", utils.dump_dict(self.subinfo),
                          "", ""])

    def from_listitem(self, listitem: xbmcgui.ListItem):
        """
        xbmcgui listitem -> kodi65 listitem
        """
        info = listitem.getVideoInfoTag()
        self.label = listitem.getLabel()
        self.path = info.getPath()
        for provider in {"tmdb", "imdb", "trakt"}:
            self._ratings[provider] = listitem.getRating(provider)
        self._infos = {"dbid": info.getDbId(),
                       "mediatype": info.getMediaType(),
                       "plot": info.getPlot(),
                       "plotoutline": info.getPlotOutline(),
                       "tvshowtitle": info.getTVShowTitle(),
                       "title": info.getTitle(),
                       "votes": info.getVotes(),
                       "season": info.getSeason(),
                       "episode": info.getEpisode(),
                       "rating": info.getRating(),
                       "userrating": info.getUserRating(),
                       "pictureurl": info.getPictureURL(),
                       "cast": info.getCast(),
                       "file": info.getFile(),
                       "trailer": info.getTrailer(),
                       "originaltitle": info.getOriginalTitle(),
                       "tagline": info.getTagLine(),
                       "genre": info.getGenre(),
                       "director": info.getDirector(),
                       "writer": info.getWritingCredits(),
                       "lastplayed": info.getLastPlayed(),
                       "premiered": info.getPremiered(),
                       "firstaired": info.getFirstAired(),
                       "playcount": info.getPlayCount(),
                       "imdbnumber": info.getIMDBNumber(),
                       "year": info.getYear()}

    def update_from_listitem(self, listitem: ListItem):
        if not listitem:
            return None
        super().update_from_listitem(listitem)
        self.set_videoinfos(listitem.videoinfo)
        self.set_audioinfos(listitem.audioinfo)
        self.set_subinfos(listitem.subinfo)
        self.set_cast(listitem.cast)

    def get_listitem(self) -> xbmcgui.ListItem:
        listitem = super().get_listitem()
        for item in self.videoinfo:
            listitem.addStreamInfo("video", item)
        for item in self.audioinfo:
            listitem.addStreamInfo("audio", item)
        for item in self.subinfo:
            listitem.addStreamInfo("subtitle", item)
        for item in self._ratings:
            listitem.setRating(item["type"], item["rating"], item["votes"], item["default"])
        listitem.setUniqueIDs(self._ids)
        listitem.setCast(self.cast)
        return listitem

    def add_videoinfo(self, info):
        self.videoinfo.append(info)

    def add_audioinfo(self, info):
        self.audioinfo.append(info)

    def add_subinfo(self, info):
        self.subinfo.append(info)

    def add_cast(self, value):
        self.cast.append(value)

    def set_cast(self, value):
        self.cast = value

    def set_videoinfos(self, infos):
        self.videoinfo = infos

    def set_audioinfos(self, infos):
        self.audioinfo = infos

    def set_subinfos(self, infos):
        self.subinfo = infos

    def get_rating(self, provider):
        for item in self._ratings:
            if item["provider"] == provider.lower():
                return item
        return None

    def get_ratings(self):
        return self._ratings

    def add_rating(self, provider, rating, votes=None, default=None):
        self._ratings.append({"provider": provider.lower(),
                              "rating": rating,
                              "votes": int(votes),
                              "default": bool(default)})

    def set_id(self, provider, uid):
        self._ids[provider] = uid

    def get_id(self):
        return self._ids

    def movie_from_dbid(self, dbid):
        from kutils.localdb import LocalDB
        if not dbid:
            return None
        self.update_from_listitem(LocalDB.get_movie(dbid))


class GameItem(ListItem):
    """
    Kodi game listitem, based on built-in datatypes
    """

    def __init__(self, *args, **kwargs):
        self.type = "game"
        super().__init__(*args, **kwargs)


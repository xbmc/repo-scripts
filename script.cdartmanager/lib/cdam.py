import os
import xbmc
import xbmcaddon


class CDAMAddon:

    # this is shared between all instances
    """:rtype : xbmcaddon.Addon"""
    _addon = None

    def __init__(self):
        if self._addon is None:
            self.reload()

    @classmethod
    def reload(cls):
        cls._addon = xbmcaddon.Addon(id=Def.SCRIPT_ID)


class CDAM(CDAMAddon):

    def getAddon(self):
        """:rtype : xbmcaddon.Addon"""
        return self._addon

    # info

    def __getAddonInfo__(self, info):
        return self.getAddon().getAddonInfo(info)

    def getLocalizedString(self, string):
        return self.getAddon().getLocalizedString(string)

    def name(self):
        return self.__getAddonInfo__('name')

    def id(self):
        return self.__getAddonInfo__('id')

    def author(self):
        return self.__getAddonInfo__('author')

    def version(self):
        return self.__getAddonInfo__('version')

    def path(self):
        return self.__getAddonInfo__('path')

    def icon(self):
        return self.__getAddonInfo__('icon')

    def fanart(self):
        return self.__getAddonInfo__('fanart')

    def profile(self):
        return self.__getAddonInfo__('profile')

    # strings

    def credits(self):
        return [
            self.name(),
            "%s by %s - Branch NG / v%s" % (self.id(), self.author(), self.version()),
            "This addon is yet another fork of the original",
            "cdART Manager by giftie, thanks to all contributors!"
        ]

    def user_agent(self):
        return "%s\\%s (%s)" % (self.name(), self.version(), Def.USERAGENT_BASE)

    # files and folders

    @staticmethod
    def __aspath__(path, *subpath):
        p = os.path.join(path, *subpath)
        return xbmc.translatePath(p).decode('utf-8') or p.decode('utf-8')

    def file_icon(self):
        return self.__aspath__(self.icon())

    def path_resources_images(self):
        return self.__aspath__(self.path(), "resources", "skins", "Default", "media")

    def file_missing_cdart(self):
        return self.__aspath__(self.path_resources_images(), "missing_cdart.png")

    def file_missing_cover(self):
        return self.__aspath__(self.path_resources_images(), "missing_cover.png")

    def file_blank_artwork(self):
        return self.__aspath__(self.path_resources_images(), "blank_artwork.png")

    def path_profile(self, folder=None):
        if folder:
            return self.__aspath__(os.path.join(self.profile(), folder))
        else:
            return self.__aspath__(self.profile())

    def path_temp(self):
        return self.path_profile("temp")

    def path_temp_xml(self):
        return self.path_profile("tempxml")

    def path_temp_gfx(self):
        return self.path_profile("tempgfx")

    def file_addon_db(self):
        return self.path_profile("l_cdart.db")

    def file_addon_db_crash(self):
        return self.path_profile("l_cdart.db-journal")

    def file_settings_xml(self):
        return self.path_profile("settings.xml")

    # more

    def log(self, text, severity=xbmc.LOGDEBUG):
        if type(text).__name__ == 'unicode':
            text = text.encode('utf-8')
        message = ('[%s] - %s' % (self.name(), text.__str__()))
        xbmc.log(msg=message, level=severity)


class Settings(CDAMAddon):

    def getAddon(self):
        """:rtype : xbmcaddon.Addon"""
        return self._addon

    def open(self):
        self.getAddon().openSettings()
        self.reload()

    def __getSetting__(self, setting):
        return self.getAddon().getSetting(setting)

    def __getSettingString__(self, setting):
        return self.__getSetting__(setting).decode("utf-8")

    def __getSettingBool__(self, setting):
        return self.__getSetting__(setting) == "true"

    def __getSettingList__(self, setting):
        return list(self.__getSetting__(setting))

    def __getSettingInt__(self, setting):
        try:
            return int(float(self.__getSetting__(setting)))
        except ValueError:
            return -1

    def __getSettingPath__(self, setting):
        p = self.__getSettingString__(setting)
        return xbmc.translatePath(p).decode('utf-8') or p.decode('utf-8')

    def mbid_match_number(self):
        return self.__getSettingInt__("mbid_match_number")

    def use_musicbrainz(self):
        return self.__getSettingBool__("use_musicbrainz")

    def musicbrainz_server(self):
        return self.__getSettingString__("musicbrainz_server")

    def mb_delay(self):
        return self.__getSettingInt__("mb_delay")

    def illegal_characters(self):
        return self.__getSettingList__("illegal_characters")

    def replace_character(self):
        return self.__getSetting__("replace_character")

    def enable_replace_illegal(self):
        return self.__getSettingBool__("enable_replace_illegal")

    def change_period_atend(self):
        return self.__getSettingBool__("change_period_atend")

    def folder(self):
        return self.__getSettingInt__("folder")

    def update_musicbrainz(self):
        return self.__getSettingBool__("update_musicbrainz")

    def check_mbid(self):
        return self.__getSettingBool__("check_mbid")

    def enable_all_artists(self):
        return self.__getSettingBool__("enable_all_artists")

    def notify_in_background(self):
        return self.__getSettingBool__("notify_in_background")

    def backup_during_update(self):
        return self.__getSettingBool__("backup_during_update")

    def enable_missing(self):
        return self.__getSettingBool__("enable_missing")

    def enable_fanart_limit(self):
        return self.__getSettingBool__("enable_fanart_limit")

    def fanart_limit(self):
        return self.__getSettingInt__("fanart_limit")

    def client_key(self):
        return self.__getSettingString__("client_key")

    # paths

    def path_music_path(self):
        return self.__getSettingPath__("music_path")

    def path_backup_path(self):
        return self.__getSettingPath__("backup_path")

    def path_missing_path(self):
        return self.__getSettingPath__("missing_path")

    def path_unique_path(self):
        return self.__getSettingPath__("unique_path")


class Def:
    def __init__(self):
        pass

    SCRIPT_ID = "script.cdartmanager"
    DB_VERSION = "3.0.3"
    USERAGENT_BASE = "https://github.com/stefansielaff/script.cdartmanager"
    FANARTTV_API_KEY = "65169f993d552483391ca10c1ae7fb03"


class MediaType:
    def __init__(self):
        pass

    ARTIST = "artist"
    ALBUM = "album"


class ArtType:
    def __init__(self):
        pass

    CDART = 'cdart'
    COVER = 'cover'
    CLEARLOGO = 'clearlogo'
    HDLOGO = 'hdlogo'
    THUMB = 'artistthumb'
    BANNER = 'musicbanner'
    FANART = 'fanart'


class Color:
    def __init__(self):
        pass

    GREEN = "FF00FF00"
    BLUE = "FF0000FF"
    RED = "FFFF0000"
    YELLOW = "FFFFFF00"
    WHITE = "FFFFFFFF"
    CYAN = "FF00FFFF"
    VIOLET = "FFEE82EE"
    PINK = "FFFF1493"
    ORANGE = "FFFF4500"


class FileName:
    def __init__(self):
        pass

    CDART = "cdart.png"
    CDART_DISC = "disc.png"
    FOLDER = "folder.jpg"
    LOGO = "logo.png"
    BANNER = "banner.jpg"
    FANART = "fanart.jpg"

# encoding: utf-8
import os
import locale
import time
import re
import json
from ctypes import *
import xbmc
import xbmcaddon
import xbmcvfs

# Addon info
__title__ = "XBMC File Cleaner"
__author__ = "Anthirian"
__addonID__ = "script.filecleaner"
__icon__ = "special://home/addons/" + __addonID__ + "/icon.png"
__settings__ = xbmcaddon.Addon(__addonID__)


class Cleaner:

    """
    The Cleaner class is used in XBMC to identify and delete videos that have been watched by the user. It starts with
    XBMC and runs until XBMC shuts down. Identification of watched videos can be enhanced with additional criteria,
    such as recently watched, low rated and based on free disk space. Deleting of videos can be enabled for movies,
    music videos or tv shows, or any combination of these. Almost all of the methods in this class will be called
    through the cleanup method.
    """

    # Constants to ensure correct JSON-RPC requests for XBMC
    MOVIES = "movies"
    MUSIC_VIDEOS = "musicvideos"
    TVSHOWS = "episodes"

    movie_filter_fields = ["title", "plot", "plotoutline", "tagline", "votes", "rating", "time", "writers",
                           "playcount", "lastplayed", "inprogress", "genre", "country", "year", "director",
                           "actor", "mpaarating", "top250", "studio", "hastrailer", "filename", "path", "set",
                           "tag", "dateadded", "videoresolution", "audiochannels", "videocodec", "audiocodec",
                           "audiolanguage", "subtitlelanguage", "videoaspect", "playlist"]
    episode_filter_fields = ["title", "tvshow", "plot", "votes", "rating", "time", "writers", "airdate",
                             "playcount", "lastplayed", "inprogress", "genre", "year", "director", "actor",
                             "episode", "season", "filename", "path", "studio", "mpaarating", "dateadded",
                             "videoresolution", "audiochannels", "videocodec", "audiocodec", "audiolanguage",
                             "subtitlelanguage", "videoaspect", "playlist"]
    musicvideo_filter_fields = ["title", "genre", "album", "year", "artist", "filename", "path", "playcount",
                                "lastplayed", "time", "director", "studio", "plot", "dateadded", "videoresolution",
                                "audiochannels", "videocodec", "audiocodec", "audiolanguage", "subtitlelanguage",
                                "videoaspect", "playlist"]

    supported_filter_fields = {
        TVSHOWS: episode_filter_fields,
        MOVIES: movie_filter_fields,
        MUSIC_VIDEOS: musicvideo_filter_fields
    }
    methods = {
        TVSHOWS: "VideoLibrary.GetEpisodes",
        MOVIES: "VideoLibrary.GetMovies",
        MUSIC_VIDEOS: "VideoLibrary.GetMusicVideos"
    }
    properties = {
        TVSHOWS: ["file", "showtitle", "season"],
        MOVIES: ["file", "title", "year"],
        MUSIC_VIDEOS: ["file", "artist"]
    }

    def __init__(self):
        """Create a Cleaner object that performs regular cleaning of watched videos."""
        self.reload_settings()

        try:
            locale.setlocale(locale.LC_ALL, "English_United Kingdom")
        except locale.Error, le:
            self.debug("Could not change locale: %s" % le, xbmc.LOGWARNING)

        service_sleep = 10
        ticker = 0
        delayed_completed = False

        while not xbmc.abortRequested:
            self.reload_settings()

            scanInterval_ticker = self.scan_interval * 60 / service_sleep
            delayedStart_ticker = self.delayed_start * 60 / service_sleep

            if not self.cleaner_enabled:
                continue
            else:
                if delayed_completed and ticker >= scanInterval_ticker:
                    self.cleanup()
                    ticker = 0
                elif not delayed_completed and ticker >= delayedStart_ticker:
                    delayed_completed = True
                    self.cleanup()
                    ticker = 0

                time.sleep(service_sleep)
                ticker += 1

        self.debug("Abort requested. Terminating.")

    def cleanup(self):
        """Delete any watched videos from the XBMC video database. The videos to be deleted are subject to a number of
        criteria as can be specified in the addon's settings.
        :rtype : None
        """
        self.debug("Starting cleaning routine")

        if self.delete_when_idle and xbmc.Player().isPlayingVideo():
            self.debug("A video is currently playing. No cleaning will be performed this interval.", xbmc.LOGWARNING)
            return

        if not self.delete_when_low_disk_space or (self.delete_when_low_disk_space and self.disk_space_low()):
            # create stub to summarize cleaning results
            summary = "Deleted" if self.delete_files else "Moved"
            cleaning_required = False
            if self.delete_movies:
                movies = self.get_expired_videos(self.MOVIES)
                if movies:
                    count = 0
                    for abs_path, title, year in movies:
                        if xbmcvfs.exists(abs_path):
                            cleaning_required = True
                            if not self.delete_files:
                                if self.create_subdirs:
                                    new_path = os.path.join(self.holding_folder, "%s (%d)" % (title, year))
                                else:
                                    new_path = self.holding_folder
                                if self.move_file(abs_path, new_path):
                                    count += 1
                                    self.delete_empty_folders(os.path.dirname(abs_path))
                            else:
                                if self.delete_file(abs_path):
                                    count += 1
                                    self.delete_empty_folders(os.path.dirname(abs_path))
                        else:
                            self.debug("XBMC could not find the file at %s" % abs_path, xbmc.LOGWARNING)
                    if count > 0:
                        summary += " %d %s" % (count, self.MOVIES)

            if self.delete_tv_shows:
                episodes = self.get_expired_videos(self.TVSHOWS)
                if episodes:
                    count = 0
                    for abs_path, show_name, season_number in episodes:
                        if xbmcvfs.exists(abs_path):
                            if not self.delete_files:
                                if self.create_subdirs:
                                    new_path = os.path.join(self.holding_folder, show_name, "Season %d" % season_number)
                                else:
                                    new_path = self.holding_folder
                                if self.move_file(abs_path, new_path):
                                    cleaning_required = True
                                    count += 1
                                    self.delete_empty_folders(os.path.dirname(abs_path))
                            else:
                                if self.delete_file(abs_path):
                                    cleaning_required = True
                                    count += 1
                                    self.delete_empty_folders(os.path.dirname(abs_path))
                        else:
                            self.debug("XBMC could not find the file at %s" % abs_path, xbmc.LOGWARNING)
                    if count > 0:
                        summary += " %d %s" % (count, self.TVSHOWS)

            if self.delete_music_videos:
                musicvideos = self.get_expired_videos(self.MUSIC_VIDEOS)
                if musicvideos:
                    count = 0
                    for abs_path, artists in musicvideos:
                        if xbmcvfs.exists(abs_path):
                            cleaning_required = True
                            if not self.delete_files:
                                if self.create_subdirs:
                                    artist = ", ".join(str(a) for a in artists)
                                    new_path = os.path.join(self.holding_folder, artist)
                                else:
                                    new_path = self.holding_folder
                                if self.move_file(abs_path, new_path):
                                    count += 1
                                    self.delete_empty_folders(os.path.dirname(abs_path))
                            else:
                                if self.delete_file(abs_path):
                                    count += 1
                                    self.delete_empty_folders(os.path.dirname(abs_path))
                        else:
                            self.debug("XBMC could not find the file at %s" % abs_path, xbmc.LOGWARNING)
                    if count > 0:
                        summary += " %d %s" % (count, self.MUSIC_VIDEOS)

            # Give a status report if any deletes occurred
            if not summary.endswith("ed"):
                self.notify(summary)

            # Finally clean the library to account for any deleted videos.
            if self.clean_xbmc_library and cleaning_required:
                # Wait 10 seconds for deletions to finish before cleaning.
                time.sleep(10)

                # Check if the library is being updated before cleaning up
                if xbmc.getCondVisibility("Library.IsScanningVideo"):
                    self.debug("The video library is being updated. Skipping library cleanup.", xbmc.LOGWARNING)
                else:
                    xbmc.executebuiltin("XBMC.CleanLibrary(video)")

    def get_expired_videos(self, option):
        """Find videos in the XBMC library that have been watched and satisfy any other conditions as enabled in the
        addon's settings.

        :type option: str
        :param option: The type of videos to find (one of the globals MOVIES, MUSIC_VIDEOS or TVSHOWS)
        :rtype : list
        """
        # This currently does not do anything and may have to be removed
        operators = ["contains", "doesnotcontain", "is", "isnot", "startswith", "endswith", "greaterthan", "lessthan",
                     "after", "before", "inthelast", "notinthelast", "true", "false", "between"]

        # A non-exhaustive list of pre-defined filters to use during JSON-RPC requests
        # These are possible conditions that must be met before a video can be deleted
        by_playcount = {"field": "playcount", "operator": "greaterthan", "value": "0"}
        by_date_played = {"field": "lastplayed", "operator": "notinthelast", "value": "%d" % self.expire_after}
        # TODO add GUI setting for date_added
        by_date_added = {"field": "dateadded", "operator": "notinthelast", "value": "7"}
        by_minimum_rating = {"field": "rating", "operator": "lessthan", "value": "%d" % self.minimum_rating}
        by_no_rating = {"field": "rating", "operator": "isnot", "value": "0"}
        by_artist = {"field": "artist", "operator": "contains", "value": "Muse"}
        by_progress = {"field": "inprogress", "operator": "false", "value": ""}

        # link settings and filters together
        settings_and_filters = [
            (self.enable_expiration, by_date_played),
            (self.delete_when_low_rated, by_minimum_rating),
            (self.not_in_progress, by_progress)
        ]

        # Only check not rated videos if checking for video ratings at all
        if self.delete_when_low_rated:
            settings_and_filters.append((self.ignore_no_rating, by_no_rating))

        enabled_filters = [by_playcount]
        for s, f in settings_and_filters:
            if s and f["field"] in self.supported_filter_fields[option]:
                enabled_filters.append(f)

        self.debug("[%s] Filters enabled: %s" % (self.methods[option], enabled_filters))

        filters = {"and": enabled_filters}

        request = {
            "jsonrpc": "2.0",
            "method": self.methods[option],
            "params": {
                "properties": self.properties[option],
                "filter": filters
            },
            "id": 1
        }

        rpc_cmd = json.dumps(request)
        response = xbmc.executeJSONRPC(rpc_cmd)
        self.debug("[%s] Response: %s" % (self.methods[option], response))
        result = json.loads(response)

        try:
            error = result["error"]
            return self.handle_json_error(error)
        except KeyError, ke:
            if "error" in ke:
                pass  # no error
            else:
                raise

        self.debug("Building list of expired videos")
        expired_videos = []
        response = result["result"]
        try:
            self.debug("Found %d watched %s matching your conditions" % (response["limits"]["total"], option))
            self.debug("JSON Response: " + str(response))
            for video in response[option]:
                # Gather all properties and add it to this video's information
                temp = []
                for p in self.properties[option]:
                    temp.append(video[p])
                expired_videos.append(temp)
        except KeyError, ke:
            if option in ke:
                pass  # no expired videos found
            else:
                self.debug("KeyError: %s not found" % ke, xbmc.LOGWARNING)
                self.handle_json_error(response)
                raise
        finally:
            self.debug("Expired videos: " + str(expired_videos))
            return expired_videos

    def handle_json_error(self, error):
        """If a JSON-RPC request results in an error, this function will handle it.
        This function currently only logs the error that occurred, and will not act on it.

        :type error: dict
        :param error: the error to handle
        :rtype : None
        """
        error_format = {
            "code": {
                "type": "integer",
                "required": True
            },
            "message": {
                "type": "string",
                "required": True
            },
            "data": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "required": True
                    },
                    "stack": {
                        "type": "object",
                        "id": "Error.Stack",
                        "properties": {
                            "name": {
                                "type": "string",
                                "required": True
                            },
                            "type": {
                                "type": "string",
                                "required": True
                            },
                            "message": {
                                "type": "string",
                                "required": True
                            },
                            "property": {
                                "$ref": "Error.Stack"
                            }
                        }
                    }
                }
            }
        }

        code = error["code"]
        msg = error["message"]
        details = error["data"] if "data" in error else "No further details"

        # If we cannot do anything about this error, just log it and stop
        self.debug("JSON error occurred.\nCode: %d\nMessage: %s\nDetails: %s" % (code, msg, details), xbmc.LOGERROR)
        return None

    def reload_settings(self):
        """Retrieve new values for all settings, in order to account for any recent changes.

        :rtype : None
        """
        self.cleaner_enabled = bool(__settings__.getSetting("cleaner_enabled") == "true")
        self.delete_folders = bool(__settings__.getSetting("delete_folders") == "true")
        self.ignore_extensions = str(__settings__.getSetting("ignore_extensions"))
        self.delayed_start = float(__settings__.getSetting("delayed_start"))
        self.scan_interval = float(__settings__.getSetting("scan_interval"))

        self.notifications_enabled = bool(__settings__.getSetting("notifications_enabled") == "true")
        self.notify_when_idle = bool(__settings__.getSetting("notify_when_idle") == "true")
        self.debugging_enabled = bool(xbmc.translatePath(__settings__.getSetting("debugging_enabled")) == "true")

        self.clean_xbmc_library = bool(__settings__.getSetting("clean_xbmc_library") == "true")
        self.delete_movies = bool(__settings__.getSetting("delete_movies") == "true")
        self.delete_tv_shows = bool(__settings__.getSetting("delete_tv_shows") == "true")
        self.delete_music_videos = bool(__settings__.getSetting("delete_music_videos") == "true")
        self.delete_when_idle = bool(xbmc.translatePath(__settings__.getSetting("delete_when_idle")) == "true")

        self.enable_expiration = bool(__settings__.getSetting("enable_expiration") == "true")
        self.expire_after = float(__settings__.getSetting("expire_after"))

        self.delete_when_low_rated = bool(__settings__.getSetting("delete_when_low_rated") == "true")
        self.minimum_rating = float(__settings__.getSetting("minimum_rating"))
        self.ignore_no_rating = bool(__settings__.getSetting("ignore_no_rating") == "true")

        self.delete_when_low_disk_space = bool(__settings__.getSetting("delete_when_low_disk_space") == "true")
        self.disk_space_threshold = float(__settings__.getSetting("disk_space_threshold"))
        self.disk_space_check_path = xbmc.translatePath(__settings__.getSetting("disk_space_check_path"))

        self.delete_files = bool(__settings__.getSetting("delete_files") == "true")
        self.holding_folder = xbmc.translatePath(__settings__.getSetting("holding_folder"))
        self.create_subdirs = bool(xbmc.translatePath(__settings__.getSetting("create_subdirs")) == "true")

        self.not_in_progress = bool(__settings__.getSetting("not_in_progress") == "true")

        self.exclusion_enabled = bool(__settings__.getSetting("exclusion_enabled") == "true")
        self.exclusion1 = xbmc.translatePath(__settings__.getSetting("exclusion1"))
        self.exclusion2 = xbmc.translatePath(__settings__.getSetting("exclusion2"))
        self.exclusion3 = xbmc.translatePath(__settings__.getSetting("exclusion3"))

    def is_excluded(self, full_path):
        """Check if the file path is part of the excluded sources. Returns True if the file is part of the excluded
        sources, False otherwise. Also returns False when an error occurs to prevent data loss.

        :type full_path: str
        :param full_path: the path to the file that should be checked for exclusion
        :rtype: bool
        """
        if not self.exclusion_enabled:
            self.debug("Path exclusion is disabled.")
            return False

        if not full_path:
            self.debug("File path is empty and cannot be checked for exclusions")
            return False

        exclusions = [self.exclusion1, self.exclusion2, self.exclusion3]

        if r"://" in full_path:
            self.debug("Detected a network path")
            pattern = re.compile("(?:smb|afp|nfs)://(?:(?:.+):(?:.+)@)?(?P<tail>.*)$", flags=re.U | re.I)

            self.debug("Converting excluded network paths for easier comparison")
            normalized_exclusions = []
            for ex in exclusions:
                # Strip everything but the folder structure
                try:
                    if ex and r"://" in ex:
                        # Only normalize non-empty excluded paths
                        normalized_exclusions.append(pattern.match(ex).group("tail").lower())
                except (AttributeError, IndexError, KeyError):
                    self.debug("Could not parse the excluded network path '%s'" % ex, xbmc.LOGWARNING)
                    return True

            self.debug("Conversion result: %s" % normalized_exclusions)

            self.debug("Proceeding to match a file with the exclusion paths")
            self.debug("The file to match is '%s'" % full_path)
            result = pattern.match(full_path)

            try:
                self.debug("Converting file path for easier comparison.")
                converted_path = result.group("tail").lower()
                self.debug("Result: '%s'" % converted_path)
                for ex in normalized_exclusions:
                    self.debug("Checking against exclusion '%s'" % ex)
                    if converted_path.startswith(ex):
                        self.debug("File '%s' matches excluded path '%s'." % (converted_path, ex))
                        return True

                self.debug("No match was found with an excluded path.")
                return False

            except (AttributeError, IndexError, KeyError):
                self.debug("Error converting '%s'. No files will be deleted" % full_path, xbmc.LOGWARNING)
                return True
        else:
            self.debug("Detected a local path")
            for ex in exclusions:
                if ex and full_path.startswith(ex):
                    self.debug("File '%s' matches excluded path '%s'." % (full_path, ex))
                    return True

            self.debug("No match was found with an excluded path.")
            return False

    def get_free_disk_space(self, path):
        """Determine the percentage of free disk space.

        :type path: str
        :param path: the path to the drive to check (this can be any path of any depth on the desired drive). If the
        path doesn't exist, this function returns 100, in order to prevent files from being deleted accidentally
        :rtype : float
        """
        percentage = float(100)
        self.debug("Checking for disk space on path: %s" % path)
        dirs, files = xbmcvfs.listdir(path)
        if dirs or files:  # Workaround for xbmcvfs.exists("C:\")
            #if platform.system() == "Windows":
            if xbmc.getCondVisibility("System.Platform.Windows"):
                self.debug("We are checking disk space from a Windows file system")
                self.debug("The path to check is %s" % path)

                if r"://" in path:
                    self.debug("We are dealing with network paths")
                    self.debug("Extracting information from share %s" % path)

                    regex = "(?P<type>smb|nfs|afp)://(?P<user>\w+):(?P<pass>.+)@(?P<host>.+?)/(?P<share>.+?)/"
                    pattern = re.compile(regex, flags=re.I | re.U)
                    match = pattern.match(path)
                    try:
                        share = match.groupdict()
                        self.debug("Protocol: %s, User: %s, Password: %s, Host: %s, Share: %s" %
                                   (share["type"], share["user"], share["pass"], share["host"], share["share"]))
                    except AttributeError, ae:
                        self.debug("%s\nCould not extract required data from %s" % (ae, path), xbmc.LOGERROR)
                        return percentage

                    self.debug("Creating UNC paths so Windows understands the shares")
                    path = os.path.normcase(r"\\" + share["host"] + os.sep + share["share"])
                    self.debug("UNC path: %s" % path)
                    self.debug("If checks fail because you need credentials, please mount the drive first")
                else:
                    self.debug("We are dealing with local paths")

                if not isinstance(path, unicode):
                    self.debug("Converting path to unicode for disk space checks")
                    path = path.decode("mbcs")
                    self.debug("New path: %s" % path)

                bytesTotal = c_ulonglong(0)
                bytesFree = c_ulonglong(0)
                windll.kernel32.GetDiskFreeSpaceExW(c_wchar_p(path), byref(bytesFree), byref(bytesTotal), None)

                try:
                    percentage = float(bytesFree.value) / float(bytesTotal.value) * 100
                    self.debug("Hard disk check results:")
                    self.debug("Bytes free: %s" % locale.format("%d", bytesFree.value, grouping=True))
                    self.debug("Bytes total: %s" % locale.format("%d", bytesTotal.value, grouping=True))
                except ZeroDivisionError:
                    self.notify(self.translate(32511), 15000, level=xbmc.LOGERROR)
            else:
                self.debug("We are checking disk space from a non-Windows file system")
                self.debug("Stripping " + path + " of all redundant stuff.")
                path = os.path.normpath(path)
                self.debug("The path now is " + path)

                try:
                    diskstats = os.statvfs(path)
                    percentage = float(diskstats.f_bfree) / float(diskstats.f_blocks) * 100
                    self.debug("Hard disk check results:")
                    self.debug("Bytes free: %s" % locale.format("%d", diskstats.f_bfree, grouping=True))
                    self.debug("Bytes total: %s" % locale.format("%d", diskstats.f_blocks, grouping=True))
                except OSError:
                    self.notify(self.translate(32512), 15000, level=xbmc.LOGERROR)
                except ZeroDivisionError:
                    self.notify(self.translate(32511), 15000, level=xbmc.LOGERROR)
        else:
            self.notify(self.translate(32513), 15000, level=xbmc.LOGERROR)

        self.debug("Free space: %0.2f%%" % percentage)
        return percentage

    def disk_space_low(self):
        """Check if the disk is running low on free space.
        Returns true if the free space is less than the threshold specified in the addon's settings.

        :rtype : Boolean
        """
        return self.get_free_disk_space(self.disk_space_check_path) <= self.disk_space_threshold

    def delete_file(self, location):
        """Delete a file from the file system.

        Example:
            success = delete_file(location)

        :type location: str
        :param location: the path to the file you wish to delete
        :rtype : bool
        """
        self.debug("Deleting file at %s" % location)
        if self.is_excluded(location):
            self.debug("This file is found on an excluded path and will not be deleted.")
            return False

        if xbmcvfs.exists(location):
            return xbmcvfs.delete(location)
        else:
            self.debug("XBMC could not find the file at %s" % location, xbmc.LOGERROR)
            return False

    def delete_empty_folders(self, folder):
        """
        Delete the folder if it is empty. Presence of custom file extensions can be ignored while scanning.
        To achieve this, edit the ignored file types setting in the addon settings.

        Example:
            success = delete_empty_folders(path)

        :type folder: str
        :param folder: The folder to be deleted
        :rtype : bool
        """
        if not self.delete_folders:
            self.debug("Deleting of folders is disabled.")
            return False

        self.debug("Checking if %s is empty" % folder)

        ignored_file_types = [file_ext.strip() for file_ext in self.ignore_extensions.split(",")]

        self.debug("Ignoring file types %s" % ignored_file_types)

        subfolders, files = xbmcvfs.listdir(folder)

        self.debug("Contents of %s:\nSubfolders: %s\nFiles: %s" % (folder, subfolders, files))

        empty = True
        try:
            for f in files:
                _, ext = os.path.splitext(f)
                self.debug("File extension: " + ext)
                if ext not in ignored_file_types:
                    self.debug("Found non-ignored file type %s" % ext)
                    empty = False
                    break
        except OSError, oe:
            self.debug("Error deriving file extension. Errno " + str(oe.errno), xbmc.LOGERROR)
            empty = False

        # Only delete directories if we found them to be empty (containing no files or filetypes we ignored)
        if empty:
            self.debug("Directory is empty and will be removed")
            try:
                # Recursively delete any subfolders
                for f in subfolders:
                    self.debug("Deleting file at " + str(os.path.join(folder, f)))
                    self.delete_empty_folders(os.path.join(folder, f))

                # Delete any files in the current folder
                for f in files:
                    self.debug("Deleting file at " + str(os.path.join(folder, f)))
                    xbmcvfs.delete(os.path.join(folder, f))

                # Finally delete the current folder
                return xbmcvfs.rmdir(folder)
            except OSError, oe:
                self.debug("An exception occurred while deleting folders. Errno " + str(oe.errno), xbmc.LOGERROR)
                return False
        else:
            self.debug("Directory is not empty and will not be removed")
            return False

    def move_file(self, source, dest_folder):
        """Move a file to a new destination. Returns True if the move succeeded, False otherwise.
        Will create destination if it does not exist.

        Example:
            success = move_file(a, b)

        :type source: basestring
        :param source: the source path (absolute)
        :type dest_folder: str
        :param dest_folder: the destination path (absolute)
        :rtype : bool
        """
        if self.is_excluded(source):
            self.debug("This file is found on an excluded path and will not be moved.")
            return False
        if isinstance(source, unicode):
            source = source.encode("utf-8")
        dest_folder = xbmc.makeLegalFilename(dest_folder)
        self.debug("Moving %s to %s" % (os.path.basename(source), dest_folder))
        if xbmcvfs.exists(source):
            if not xbmcvfs.exists(dest_folder):
                self.debug("XBMC could not find destination %s" % dest_folder)
                self.debug("Creating destination %s" % dest_folder)
                if xbmcvfs.mkdirs(dest_folder):
                    self.debug("Successfully created %s" % dest_folder)
                else:
                    self.debug("XBMC could not create destination %s" % dest_folder, xbmc.LOGERROR)
                    return False

            new_path = os.path.join(dest_folder, os.path.basename(source))

            if xbmcvfs.exists(new_path):
                self.debug("A file with the same name already exists in the holding folder. Checking file sizes.")
                existing_file = xbmcvfs.File(new_path)
                file_to_move = xbmcvfs.File(source)
                if file_to_move.size() > existing_file.size():
                    self.debug("This file is larger than the existing file. Replacing the existing file with this one.")
                    existing_file.close()
                    file_to_move.close()
                    return xbmcvfs.delete(new_path) and xbmcvfs.rename(source, new_path)
                else:
                    self.debug("This file is smaller than the existing file. Deleting this file instead of moving.")
                    existing_file.close()
                    file_to_move.close()
                    return self.delete_file(source)
            else:
                self.debug("Moving %s\nto %s\nNew path: %s" % (source, dest_folder, new_path))
                return xbmcvfs.rename(source, new_path)
        else:
            self.debug("XBMC could not find the file at %s" % source, xbmc.LOGWARNING)
            return False

    def translate(self, msg_id):
        """
        Retrieve a localized string by id. Returns the empty string if id is not an int.

        :type msg_id: int
        :param msg_id: the id of the localized string
        :rtype : str
        """
        if isinstance(msg_id, int):
            return __settings__.getLocalizedString(msg_id)
        else:
            return ""

    def notify(self, message, duration=5000, image=__icon__, level=xbmc.LOGNOTICE):
        """Display an XBMC notification and log the message.

        :type message: str
        :param message: the message to be displayed (and logged). You may also use the id (int) for localization.
        :type duration: int
        :param duration: the duration the notification is displayed in milliseconds (default 5000)
        :type image: str
        :param image: the path to the image to be displayed on the notification (default "icon.png")
        :type level: int
        :param level: (Optional) the log level (supported values are found at xbmc.LOG...)
        :rtype : None
        """
        self.debug(message, level)
        if self.notifications_enabled and not (self.notify_when_idle and xbmc.Player().isPlayingVideo()):
            xbmc.executebuiltin("XBMC.Notification(%s, %s, %s, %s)" % (__title__, message, duration, image))

    def debug(self, message, level=xbmc.LOGNOTICE):
        """Write a debug message to xbmc.log

        :type message: basestring
        :param message: the message to log
        :type level: int
        :param level: (Optional) the log level (supported values are found at xbmc.LOG...)
        :rtype : None
        """
        if self.debugging_enabled:
            if isinstance(message, unicode):
                message = message.encode("utf-8")
            for line in message.splitlines():
                xbmc.log(msg=__title__ + ": " + line, level=level)

run = Cleaner()

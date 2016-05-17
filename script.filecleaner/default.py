#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

import xbmcvfs
from utils import *


# Addon info
ADDON_ID = "script.filecleaner"
ADDON = Addon(ADDON_ID)
ADDON_NAME = xbmc.translatePath(ADDON.getAddonInfo("name")).decode("utf-8")
ADDON_AUTHOR = "Anthirian, drewzh"
ADDON_ICON = xbmc.translatePath(ADDON.getAddonInfo("icon")).decode("utf-8")


class Cleaner(object):
    """
    The Cleaner class allows users to clean up their movie, TV show and music video collection by removing watched
    items. The user can apply a number of conditions to cleaning, such as limiting cleaning to files with a given
    rating, excluding a particular folder or only cleaning when a particular disk is low on disk space.

    The main method to call is the ``clean_all()`` method. This method will invoke the subsequent checks and (re)move
    your videos. Upon completion, you will receive a short summary of the cleaning results.

    *Example*
      ``summary = Cleaner().clean_all()``
    """

    # Constants to ensure correct (Gotham-compatible) JSON-RPC requests for Kodi
    MOVIES = "movies"
    MUSIC_VIDEOS = "musicvideos"
    TVSHOWS = "episodes"
    CLEANING_TYPE_MOVE = "0"
    CLEANING_TYPE_DELETE = "1"
    DEFAULT_ACTION_CLEAN = "0"
    DEFAULT_ACTION_LOG = "1"

    STATUS_SUCCESS = 1
    STATUS_FAILURE = 2
    STATUS_ABORTED = 3

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
        TVSHOWS: ["file", "showtitle"],
        MOVIES: ["file", "title"],
        MUSIC_VIDEOS: ["file", "artist"]
    }
    stacking_indicators = ["part", "pt", "cd", "dvd", "disk", "disc"]

    progress = xbmcgui.DialogProgress()
    silent = True
    exit_status = STATUS_SUCCESS

    def __init__(self):
        debug("{0!s} version {1!s} loaded.".format(ADDON.getAddonInfo("name").decode("utf-8"),
                                                   ADDON.getAddonInfo("version").decode("utf-8")))

    def __is_canceled(self):
        """
        Test if the progress dialog has been canceled by the user. If the cleaner was started as a service this will
        always return False
        :rtype: bool
        :return: True if the user cancelled cleaning, False otherwise.
        """
        if self.silent:
            return False
        elif self.progress.iscanceled():
            debug("User canceled.", xbmc.LOGWARNING)
            self.exit_status = self.STATUS_ABORTED
            return True

    def show_progress(self):
        """
        Toggle the progress dialog on. Use before calling the cleaning method.
        """
        self.silent = False

    def hide_progress(self):
        """
        Toggle the progress dialog off. Use before calling the cleaning method.
        """
        self.silent = True

    def clean(self, video_type):
        """
        Clean all watched videos of the provided type.

        :type video_type: str
        :param video_type: The type of videos to clean (one of TVSHOWS, MOVIES, MUSIC_VIDEOS).
        :rtype: (list, int, int)
        :return: A list of the filenames that were cleaned, as well as the number of files cleaned and the return status.
        """
        cleaned_files = []
        count = 0
        type_translation = {self.MOVIES: translate(32626), self.MUSIC_VIDEOS: translate(32627), self.TVSHOWS: translate(32628)}

        if not self.silent:
            # Cleaning <video type>
            self.progress.update(0, translate(32629).format(type=type_translation[video_type]), *map(translate, (32615, 32615)))
            monitor.waitForAbort(1)

        if video_type == self.TVSHOWS:
            clean_this_video_type = get_setting(clean_tv_shows)
        elif video_type == self.MOVIES:
            clean_this_video_type = get_setting(clean_movies)
        elif video_type == self.MUSIC_VIDEOS:
            clean_this_video_type = get_setting(clean_music_videos)
        else:
            debug("Incorrect video type specified: {0!r}".format(video_type), xbmc.LOGERROR)
            return [], 0, self.STATUS_FAILURE

        progress_percent = 0

        if clean_this_video_type:
            expired_videos = self.get_expired_videos(video_type)
            if not self.silent:
                amount = len(expired_videos)
                debug("Found {0} videos that may need cleaning.".format(amount))
                try:
                    increment = 1.0 / amount
                except ZeroDivisionError:
                    self.progress.update(0, *map(translate, (32621, 32622, 32623)))  # No watched videos found
                    if monitor.waitForAbort(2.5):
                        pass

            for filename, title in expired_videos:
                if not self.__is_canceled():
                    unstacked_path = self.unstack(filename)
                    if xbmcvfs.exists(unstacked_path[0]):
                        if get_setting(cleaning_type) == self.CLEANING_TYPE_MOVE:
                            # No destination set, prompt user to set one now
                            if get_setting(holding_folder) == "":
                                if xbmcgui.Dialog().yesno(ADDON_NAME, *map(translate, (32521, 32522, 32523))):
                                    xbmc.executebuiltin("Addon.OpenSettings({0!s})".format(ADDON_ID))
                                self.exit_status = self.STATUS_ABORTED
                                break
                            if get_setting(create_subdirs):
                                if isinstance(title, unicode):
                                    title = title.encode("utf-8")
                                new_path = os.path.join(get_setting(holding_folder), str(title))
                            else:
                                new_path = get_setting(holding_folder)
                            move_result = self.move_file(filename, new_path)
                            if move_result == 1:
                                debug("File(s) moved successfully.")
                                count += 1
                                if len(unstacked_path) > 1:
                                    cleaned_files.extend(unstacked_path)
                                else:
                                    cleaned_files.append(filename)
                                self.clean_related_files(filename, new_path)
                                self.delete_empty_folders(os.path.dirname(filename))
                            elif move_result == -1:
                                debug("Moving errors occurred. Skipping related files and directories.", xbmc.LOGWARNING)
                                xbmcgui.Dialog().ok(*map(translate, (32611, 32612, 32613, 32614)))
                        elif get_setting(cleaning_type) == self.CLEANING_TYPE_DELETE:
                            if self.delete_file(filename):
                                debug("File(s) deleted successfully.")
                                count += 1
                                if len(unstacked_path) > 1:
                                    cleaned_files.extend(unstacked_path)
                                else:
                                    cleaned_files.append(filename)
                                self.clean_related_files(filename)
                                self.delete_empty_folders(os.path.dirname(filename))
                    else:
                        debug("{0!r} was already deleted. Skipping.".format(filename), xbmc.LOGWARNING)

                    if not self.silent:
                        progress_percent += increment * 100
                        debug("Progress percent is {percent}, amount is {amount} and increment is {increment}".format(percent=progress_percent, amount=amount, increment=increment))
                        self.progress.update(int(progress_percent), translate(32616).format(amount=amount, type=type_translation[video_type]), translate(32617), "[I]{0!s}[/I]".format(title))
                        monitor.waitForAbort(2)
                else:
                    debug("We had {amt!s} {type!s} left to clean.".format(amt=(amount - count), type=type_translation[video_type]))
        else:
            debug("Cleaning of {0!r} is disabled. Skipping.".format(video_type))
            if not self.silent:
                self.progress.update(0, translate(32624).format(type=type_translation[video_type]), *map(translate, (32625, 32615)))
                monitor.waitForAbort(2)

        return cleaned_files, count, self.exit_status

    def clean_all(self):
        """
        Clean up any watched videos in the Kodi library, satisfying any conditions set via the addon settings.

        :rtype: (str, int)
        :return: A single-line (localized) summary of the cleaning results to be used for a notification, plus a status.
        """
        debug("Starting cleaning routine.")

        if get_setting(clean_when_idle) and xbmc.Player().isPlaying():
            debug("Kodi is currently playing a file. Skipping cleaning.", xbmc.LOGWARNING)
            return None, self.exit_status

        results = {}
        cleaning_results, cleaned_files = [], []
        if not get_setting(clean_when_low_disk_space) or (get_setting(clean_when_low_disk_space) and
                                                          utils.disk_space_low()):
            if not self.silent:
                self.progress.create(ADDON_NAME, *map(translate, (32619, 32615, 32615)))
                self.progress.update(0)
                monitor.waitForAbort(2)
            for video_type in [self.MOVIES, self.MUSIC_VIDEOS, self.TVSHOWS]:
                if not self.__is_canceled():
                    cleaned_files, count, status = self.clean(video_type)
                    if count > 0:
                        cleaning_results.extend(cleaned_files)
                        results[video_type] = count
            if not self.silent:
                self.progress.close()

        # Check if we need to perform any post-cleaning operations
        if cleaning_results:
            # Write cleaned file names to the log
            Log().prepend(cleaning_results)

            # Finally clean the library to account for any deleted videos.
            if get_setting(clean_kodi_library):
                monitor.waitForAbort(2)  # Sleep 2 seconds to make sure file I/O is done.

                if xbmc.getCondVisibility("Library.IsScanningVideo"):
                    debug("The video library is being updated. Skipping library cleanup.", xbmc.LOGWARNING)
                else:
                    xbmc.executebuiltin("XBMC.CleanLibrary(video, false)")

        return self.summarize(results), self.exit_status

    def summarize(self, details):
        """
        Create a summary from the cleaning results.

        :type details: dict
        :rtype: str
        :return: A comma separated summary of the cleaning results.
        """
        summary = ""

        # Localize video types
        for vid_type, amount in details.items():
            if vid_type is self.MOVIES:
                video_type = utils.translate(32515)
            elif vid_type is self.TVSHOWS:
                video_type = utils.translate(32516)
            elif vid_type is self.MUSIC_VIDEOS:
                video_type = utils.translate(32517)
            else:
                video_type = ""

            summary += "{0:d} {1}, ".format(amount, video_type)

        # strip the comma and space from the last iteration and add the localized suffix
        return "{0}{1}".format(summary.rstrip(", "), utils.translate(32518)) if summary else ""

    def get_expired_videos(self, option):
        """
        Find videos in the Kodi library that have been watched.

        Respects any other conditions user enables in the addon's settings.

        :type option: str
        :param option: The type of videos to find (one of the globals MOVIES, MUSIC_VIDEOS or TVSHOWS).
        :rtype: list
        :return: A list of expired videos, along with a number of extra attributes specific to the video type.
        """

        # A non-exhaustive list of pre-defined filters to use during JSON-RPC requests
        # These are possible conditions that must be met before a video can be deleted
        by_playcount = {"field": "playcount", "operator": "greaterthan", "value": "0"}
        by_date_played = {"field": "lastplayed", "operator": "notinthelast", "value": "{0:f}".format(get_setting(expire_after))}
        by_minimum_rating = {"field": "rating", "operator": "lessthan", "value": "{0:f}".format(get_setting(minimum_rating))}
        by_no_rating = {"field": "rating", "operator": "isnot", "value": "0"}
        by_progress = {"field": "inprogress", "operator": "false", "value": ""}

        # link settings and filters together
        settings_and_filters = [
            (get_setting(enable_expiration), by_date_played),
            (get_setting(clean_when_low_rated), by_minimum_rating),
            (get_setting(not_in_progress), by_progress)
        ]

        # Only check not rated videos if checking for video ratings at all
        if get_setting(clean_when_low_rated):
            settings_and_filters.append((get_setting(ignore_no_rating), by_no_rating))

        enabled_filters = [by_playcount]
        for s, f in settings_and_filters:
            if s and f["field"] in self.supported_filter_fields[option]:
                enabled_filters.append(f)

        debug("[{0}] Filters enabled: {1!r}".format(self.methods[option], enabled_filters))

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
        debug("[{0}] Response: {1!r}".format(self.methods[option], response))
        result = json.loads(response)

        # Check the results for errors
        try:
            error = result["error"]
            debug("An error occurred. {0!r}".format(error))
            return None
        except KeyError as ke:
            if "error" in ke:
                pass  # no error
            else:
                raise

        debug("Building list of expired videos")
        expired_videos = []
        response = result["result"]
        try:
            debug("Found {0:d} watched {1} matching your conditions".format(response["limits"]["total"], option))
            debug("JSON Response: " + str(response))
            for video in response[option]:
                # Test for file exclusions
                if self.is_excluded(video["file"]):
                    debug("{0!r} matches an exclusion, not including it in the list of expired videos".format(video))
                    continue

                # Gather all properties and add it to this video's information
                temp = []
                for p in self.properties[option]:
                    temp.append(video[p])
                expired_videos.append(temp)
        except KeyError as ke:
            if option in ke:
                pass  # no expired videos found
            else:
                debug("KeyError: {0!r} not found".format(ke), xbmc.LOGWARNING)
                debug("{0!r}".format(response), xbmc.LOGWARNING)
                raise
        finally:
            debug("Expired videos: {0}".format(expired_videos))
            return expired_videos

    def is_excluded(self, full_path):
        """Check if the file path is part of the excluded sources.

        :type full_path: str
        :param full_path: the path to the file that should be checked for exclusion
        :rtype: bool
        :return: True if the path matches a user-set excluded path, False otherwise.
        """
        if not get_setting(exclusion_enabled):
            debug("Path exclusion is disabled.")
            return False
        elif not full_path:
            debug("File path is empty and cannot be checked for exclusions")
            return False

        exclusions = map(get_setting, [exclusion1, exclusion2, exclusion3])

        if r"://" in full_path:
            debug("Detected a network path")
            pattern = re.compile("(?:smb|nfs)://(?:(?:.+):(?:.+)@)?(?P<tail>.*)$", flags=re.U | re.I)

            debug("Converting excluded network paths for easier comparison")
            normalized_exclusions = []
            for ex in exclusions:
                # Strip everything but the folder structure
                try:
                    if ex and r"://" in ex:
                        # Only normalize non-empty excluded paths
                        normalized_exclusions.append(pattern.match(ex).group("tail").lower())
                except (AttributeError, IndexError, KeyError) as err:
                    debug("Could not parse the excluded network path {0!r}\n{1}".format(ex, err), xbmc.LOGWARNING)
                    return True

            debug("Conversion result: {0!r}".format(normalized_exclusions))

            debug("Proceeding to match a file with the exclusion paths")
            debug("The file to match is {0!r}".format(full_path))
            result = pattern.match(full_path)

            try:
                debug("Converting file path for easier comparison.")
                converted_path = result.group("tail").lower()
                debug("Result: {0!r}".format(converted_path))
                for ex in normalized_exclusions:
                    debug("Checking against exclusion {0!r}.".format(ex))
                    if converted_path.startswith(ex):
                        debug("File {0!r} matches excluded path {1!r}.".format(converted_path, ex))
                        return True

            except (AttributeError, IndexError, KeyError) as err:
                debug("Error converting {0!r}. No files will be deleted.\n{1}".format(full_path, err), xbmc.LOGWARNING)
                return True
        else:
            debug("Detected a local path")
            for ex in exclusions:
                if ex and full_path.startswith(ex):
                    debug("File {0!r} matches excluded path {1!r}.".format(full_path, ex))
                    return True

        debug("No match was found with an excluded path.")
        return False

    def unstack(self, path):
        """Unstack path if it is a stacked movie. See http://kodi.wiki/view/File_stacking for more info.

        :type path: str
        :param path: The path that should be unstacked.
        :rtype: list
        :return: A list of paths that are part of the stack. If it is no stacked movie, a one-element list is returned.
        """
        if isinstance(path, unicode):
            path = path.encode("utf-8")
        if path.startswith("stack://"):
            debug("Unstacking {0!r}.".format(path))
            return path.replace("stack://", "").split(" , ")
        else:
            debug("Unstacking {0!r} is not needed.".format(path))
            return [path]

    def get_stack_bare_title(self, filenames):
        """Find the common title of files part of a stack, minus the volume and file extension.

        Example:
            ["Movie_Title_part1.ext", "Movie_Title_part2.ext"] yields "Movie_Title"

        :type filenames: list
        :param filenames: a list of file names that are part of a stack. Use unstack() to find these file names.
        :rtype: str
        :return: common title of file names part of a stack
        """
        title = os.path.basename(os.path.commonprefix(filenames))
        for e in self.stacking_indicators:
            if title.endswith(e):
                title = title[:-len(e)].rstrip("._-")
                break
        return title

    def delete_file(self, location):
        """
        Delete a file from the file system. Also supports stacked movie files.

        Example:
            success = delete_file(location)

        :type location: str
        :param location: the path to the file you wish to delete.
        :rtype: bool
        :return: True if (at least one) file was deleted successfully, False otherwise.
        """
        debug("Attempting to delete {0!r}".format(location))

        paths = self.unstack(location)
        success = []

        if self.is_excluded(paths[0]):
            debug("Detected a file on an excluded path. Aborting.")
            return False

        for p in paths:
            if xbmcvfs.exists(p):
                success.append(bool(xbmcvfs.delete(p)))
            else:
                debug("File {0!r} no longer exists.".format(p), xbmc.LOGERROR)
                success.append(False)

        return any(success)

    def delete_empty_folders(self, location):
        """
        Delete the folder if it is empty. Presence of custom file extensions can be ignored while scanning.

        To achieve this, edit the ignored file types setting in the addon settings.

        Example:
            success = delete_empty_folders(path)

        :type location: str
        :param location: The path to the folder to be deleted.
        :rtype: bool
        :return: True if the folder was deleted successfully, False otherwise.
        """
        if not get_setting(delete_folders):
            debug("Deleting of empty folders is disabled.")
            return False

        folder = self.unstack(location)[0]  # Stacked paths should have the same parent, use any
        debug("Checking if {0!r} is empty".format(folder))
        ignored_file_types = [file_ext.strip() for file_ext in get_setting(ignore_extensions).split(",")]
        debug("Ignoring file types {0!r}".format(ignored_file_types))

        subfolders, files = xbmcvfs.listdir(folder)
        debug("Contents of {0!r}:\nSubfolders: {1!r}\nFiles: {2!r}".format(folder, subfolders, files))

        empty = True
        try:
            for f in files:
                _, ext = os.path.splitext(f)
                if ext and ext not in ignored_file_types:  # ensure f is not a folder and its extension is not ignored
                    debug("Found non-ignored file type {0!r}".format(ext))
                    empty = False
                    break
        except OSError as oe:
            debug("Error deriving file extension. Errno {0}".format(oe.errno), xbmc.LOGERROR)
            empty = False

        # Only delete directories if we found them to be empty (containing no files or filetypes we ignored)
        if empty:
            debug("Directory is empty and will be removed")
            try:
                # Recursively delete any subfolders
                for f in subfolders:
                    debug("Deleting file at " + str(os.path.join(folder, f)))
                    self.delete_empty_folders(os.path.join(folder, f))

                # Delete any files in the current folder
                for f in files:
                    debug("Deleting file at " + str(os.path.join(folder, f)))
                    xbmcvfs.delete(os.path.join(folder, f))

                # Finally delete the current folder
                return xbmcvfs.rmdir(folder)
            except OSError as oe:
                debug("An exception occurred while deleting folders. Errno " + str(oe.errno), xbmc.LOGERROR)
                return False
        else:
            debug("Directory is not empty and will not be removed")
            return False

    def clean_related_files(self, source, dest_folder=None):
        """Clean files related to another file based on the user's preferences.

        Related files are files that only differ by extension, or that share a prefix in case of stacked movies.

        Examples of related files include NFO files, thumbnails, subtitles, fanart, etc.

        :type source: str
        :param source: Location of the file whose related files should be cleaned.
        :type dest_folder: str
        :param dest_folder: (Optional) The folder where related files should be moved to. Not needed when deleting.
        """
        if get_setting(clean_related):
            debug("Cleaning related files.")

            path_list = self.unstack(source)
            path, name = os.path.split(path_list[0])  # Because stacked movies are in the same folder, only check one
            if source.startswith("stack://"):
                name = self.get_stack_bare_title(path_list)
            else:
                name, ext = os.path.splitext(name)

            debug("Attempting to match related files in {0!r} with prefix {1!r}".format(path, name))
            for extra_file in xbmcvfs.listdir(path)[1]:
                if isinstance(path, unicode):
                    path = path.encode("utf-8")
                if isinstance(extra_file, unicode):
                    extra_file = extra_file.encode("utf-8")
                if isinstance(name, unicode):
                    name = name.encode("utf-8")

                if extra_file.startswith(name):
                    debug("{0!r} starts with {1!r}.".format(extra_file, name))
                    extra_file_path = os.path.join(path, extra_file)
                    if get_setting(cleaning_type) == self.CLEANING_TYPE_DELETE:
                        if extra_file_path not in path_list:
                            debug("Deleting {0!r}.".format(extra_file_path))
                            xbmcvfs.delete(extra_file_path)
                    elif get_setting(cleaning_type) == self.CLEANING_TYPE_MOVE:
                        new_extra_path = os.path.join(dest_folder, os.path.basename(extra_file))
                        if new_extra_path not in path_list:
                            debug("Moving {0!r} to {1!r}.".format(extra_file_path, new_extra_path))
                            xbmcvfs.rename(extra_file_path, new_extra_path)
            debug("Finished searching for related files.")
        else:
            debug("Cleaning of related files is disabled.")

    def move_file(self, source, dest_folder):
        """Move a file to a new destination. Will create destination if it does not exist.

        Example:
            result = move_file(a, b)

        :type source: str
        :param source: the source path (absolute)
        :type dest_folder: str
        :param dest_folder: the destination path (absolute)
        :rtype: int
        :return: 1 if (all stacked) files were moved, 0 if not, -1 if errors occurred
        """
        if isinstance(source, unicode):
            source = source.encode("utf-8")

        paths = self.unstack(source)
        success = []
        files_moved_successfully = 0
        dest_folder = xbmc.makeLegalFilename(dest_folder)

        if self.is_excluded(paths[0]):
            debug("Detected a file on an excluded path. Aborting.")
            return 0

        for p in paths:
            debug("Attempting to move {0!r} to {1!r}.".format(p, dest_folder))
            if xbmcvfs.exists(p):
                if not xbmcvfs.exists(dest_folder):
                    if xbmcvfs.mkdirs(dest_folder):
                        debug("Created destination {0!r}.".format(dest_folder))
                    else:
                        debug("Destination {0!r} could not be created.".format(dest_folder), xbmc.LOGERROR)
                        return -1

                new_path = os.path.join(dest_folder, os.path.basename(p))

                if xbmcvfs.exists(new_path):
                    debug("A file with the same name already exists in the holding folder. Checking file sizes.")
                    existing_file = xbmcvfs.File(new_path)
                    file_to_move = xbmcvfs.File(p)
                    if file_to_move.size() > existing_file.size():
                        debug("This file is larger than the existing file. Replacing it with this one.")
                        existing_file.close()
                        file_to_move.close()
                        if bool(xbmcvfs.delete(new_path) and bool(xbmcvfs.rename(p, new_path))):
                            files_moved_successfully += 1
                        else:
                            return -1
                    else:
                        debug("This file isn't larger than the existing file. Deleting it instead of moving.")
                        existing_file.close()
                        file_to_move.close()
                        if bool(xbmcvfs.delete(p)):
                            files_moved_successfully += 1
                        else:
                            return -1
                else:
                    debug("Moving {0!r} to {1!r}.".format(p, new_path))
                    move_success = bool(xbmcvfs.rename(p, new_path))
                    copy_success, delete_success = False, False
                    if not move_success:
                        debug("Move failed, falling back to copy and delete.", xbmc.LOGWARNING)
                        copy_success = bool(xbmcvfs.copy(p, new_path))
                        if copy_success:
                            debug("Copied successfully, attempting delete of source file.")
                            delete_success = bool(xbmcvfs.delete(p))
                            if not delete_success:
                                debug("Could not remove source file. Please remove the file manually.", xbmc.LOGWARNING)
                        else:
                            debug("Copying failed, please make sure you have appropriate permissions.", xbmc.LOGFATAL)
                            return -1

                    if move_success or (copy_success and delete_success):
                        files_moved_successfully += 1

            else:
                debug("File {0!r} is no longer available.".format(p), xbmc.LOGWARNING)

        return 1 if len(paths) == files_moved_successfully else -1

if __name__ == "__main__":
    cleaner = Cleaner()
    monitor = xbmc.Monitor()
    if get_setting(default_action) == cleaner.DEFAULT_ACTION_LOG:
        xbmc.executescript("special://home/addons/script.filecleaner/viewer.py")
    else:
        cleaner.show_progress()
        results, return_status = cleaner.clean_all()
        if results:
            # Videos were cleaned. Ask the user to view the log file.
            # TODO: Listen to OnCleanFinished notifications and wait before asking to view the log
            if xbmcgui.Dialog().yesno(utils.translate(32514), results, utils.translate(32519)):
                xbmc.executescript("special://home/addons/script.filecleaner/viewer.py")
        elif return_status == cleaner.STATUS_ABORTED:
            # Do not show cleaning results in case user aborted, e.g. to set holding folder
            pass
        else:
            xbmcgui.Dialog().ok(ADDON_NAME, utils.translate(32520))

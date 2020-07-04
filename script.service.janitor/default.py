#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import sys
import re

from reset_exclusions import *
from utils import *
from viewer import *


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
    MOVIES = u"movies"
    MUSIC_VIDEOS = u"musicvideos"
    TVSHOWS = u"episodes"
    CLEANING_TYPE_MOVE = u"0"
    CLEANING_TYPE_DELETE = u"1"
    DEFAULT_ACTION_CLEAN = u"0"
    DEFAULT_ACTION_LOG = u"1"

    STATUS_SUCCESS = 1
    STATUS_FAILURE = 2
    STATUS_ABORTED = 3

    movie_filter_fields = [u"title", u"plot", u"plotoutline", u"tagline", u"votes", u"rating", u"time", u"writers",
                           u"playcount", u"lastplayed", u"inprogress", u"genre", u"country", u"year", u"director",
                           u"actor", u"mpaarating", u"top250", u"studio", u"hastrailer", u"filename", u"path", u"set",
                           u"tag", u"dateadded", u"videoresolution", u"audiochannels", u"videocodec", u"audiocodec",
                           u"audiolanguage", u"subtitlelanguage", u"videoaspect", u"playlist"]
    episode_filter_fields = [u"title", u"tvshow", u"plot", u"votes", u"rating", u"time", u"writers", u"airdate",
                             u"playcount", u"lastplayed", u"inprogress", u"genre", u"year", u"director", u"actor",
                             u"episode", u"season", u"filename", u"path", u"studio", u"mpaarating", u"dateadded",
                             u"videoresolution", u"audiochannels", u"videocodec", u"audiocodec", u"audiolanguage",
                             u"subtitlelanguage", u"videoaspect", u"playlist"]
    musicvideo_filter_fields = [u"title", u"genre", u"album", u"year", u"artist", u"filename", u"path", u"playcount",
                                u"lastplayed", u"time", u"director", u"studio", u"plot", u"dateadded",
                                u"videoresolution", u"audiochannels", u"videocodec", u"audiocodec", u"audiolanguage",
                                u"subtitlelanguage", u"videoaspect", u"playlist"]

    supported_filter_fields = {
        TVSHOWS: episode_filter_fields,
        MOVIES: movie_filter_fields,
        MUSIC_VIDEOS: musicvideo_filter_fields
    }
    methods = {
        TVSHOWS: u"VideoLibrary.GetEpisodes",
        MOVIES: u"VideoLibrary.GetMovies",
        MUSIC_VIDEOS: u"VideoLibrary.GetMusicVideos"
    }
    properties = {
        TVSHOWS: [u"file", u"showtitle"],
        MOVIES: [u"file", u"title"],
        MUSIC_VIDEOS: [u"file", u"artist"]
    }
    stacking_indicators = [u"part", u"pt", u"cd", u"dvd", u"disk", u"disc"]

    progress = xbmcgui.DialogProgress()
    monitor = xbmc.Monitor()
    silent = True
    exit_status = STATUS_SUCCESS

    def __init__(self):
        debug(u"{0} version {1} loaded.".format(ADDON.getAddonInfo(u"name").decode("utf-8"),
                                                ADDON.getAddonInfo(u"version").decode("utf-8")))

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
            debug(u"User canceled.", xbmc.LOGWARNING)
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

        :type video_type: unicode
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
            self.monitor.waitForAbort(1)

        if video_type == self.TVSHOWS:
            clean_this_video_type = get_setting(clean_tv_shows)
        elif video_type == self.MOVIES:
            clean_this_video_type = get_setting(clean_movies)
        elif video_type == self.MUSIC_VIDEOS:
            clean_this_video_type = get_setting(clean_music_videos)
        else:
            debug(u"Incorrect video type specified: {0}".format(video_type), xbmc.LOGERROR)
            return [], 0, self.STATUS_FAILURE

        progress_percent = 0

        if clean_this_video_type:
            expired_videos = self.get_expired_videos(video_type)
            if not self.silent:
                amount = len(expired_videos)
                debug(u"Found {0} videos that may need cleaning.".format(amount))
                try:
                    increment = 1.0 / amount
                except ZeroDivisionError:
                    self.progress.update(0, *map(translate, (32621, 32622, 32623)))  # No watched videos found
                    if self.monitor.waitForAbort(2.5):
                        pass

            for filename, title in expired_videos:
                if not self.__is_canceled():
                    unstacked_path = self.unstack(filename)
                    if xbmcvfs.exists(unstacked_path[0]) and self.has_no_hard_links(filename):
                        if get_setting(cleaning_type) == self.CLEANING_TYPE_MOVE:
                            # No destination set, prompt user to set one now
                            if get_setting(holding_folder) == "":
                                if xbmcgui.Dialog().yesno(ADDON_NAME, *map(translate, (32521, 32522, 32523))):
                                    xbmc.executebuiltin(u"Addon.OpenSettings({0})".format(ADDON_ID))
                                self.exit_status = self.STATUS_ABORTED
                                break
                            if get_setting(create_subdirs):
                                title = re.sub(r"[\\/:*?\"<>|]+","_", title)
                                new_path = os.path.join(get_setting(holding_folder).encode("utf-8"),
                                                        title.encode("utf-8"))
                            else:
                                new_path = get_setting(holding_folder)
                            move_result = self.move_file(filename, new_path)
                            if move_result == 1:
                                debug(u"File(s) moved successfully.")
                                count += 1
                                if len(unstacked_path) > 1:
                                    cleaned_files.extend(unstacked_path)
                                else:
                                    cleaned_files.append(filename)
                                self.clean_related_files(filename, new_path)
                                self.delete_empty_folders(os.path.dirname(filename))
                            elif move_result == -1:
                                debug(u"Moving errors occurred. Skipping related files and directories.", xbmc.LOGWARNING)
                                xbmcgui.Dialog().ok(*map(translate, (32611, 32612, 32613, 32614)))
                        elif get_setting(cleaning_type) == self.CLEANING_TYPE_DELETE:
                            if self.delete_file(filename):
                                debug(u"File(s) deleted successfully.")
                                count += 1
                                if len(unstacked_path) > 1:
                                    cleaned_files.extend(unstacked_path)
                                else:
                                    cleaned_files.append(filename)
                                self.clean_related_files(filename)
                                self.delete_empty_folders(os.path.dirname(filename))
                    else:
                        debug(u"Not cleaning {0}.".format(filename), xbmc.LOGNOTICE)

                    if not self.silent:
                        progress_percent += increment * 100
                        debug(u"Progress percent is {percent}, amount is {amount} and increment is {increment}".format(percent=progress_percent, amount=amount, increment=increment))
                        self.progress.update(int(progress_percent), translate(32616).format(amount=amount, type=type_translation[video_type]), translate(32617), u"[I]{0}[/I]".format(title))
                        self.monitor.waitForAbort(2)
                else:
                    debug(u"We had {amt} {type} left to clean.".format(amt=(amount - count), type=type_translation[video_type]))
        else:
            debug(u"Cleaning of {0} is disabled. Skipping.".format(video_type))
            if not self.silent:
                self.progress.update(0, translate(32624).format(type=type_translation[video_type]), *map(translate, (32625, 32615)))
                self.monitor.waitForAbort(2)

        return cleaned_files, count, self.exit_status

    def clean_all(self):
        """
        Clean up any watched videos in the Kodi library, satisfying any conditions set via the addon settings.

        :rtype: (unicode, int)
        :return: A single-line (localized) summary of the cleaning results to be used for a notification, plus a status.
        """
        debug(u"Starting cleaning routine.")

        if get_setting(clean_when_idle) and xbmc.Player().isPlaying():
            debug(u"Kodi is currently playing a file. Skipping cleaning.", xbmc.LOGWARNING)
            return None, self.exit_status

        results = {}
        cleaning_results, cleaned_files = [], []
        if not get_setting(clean_when_low_disk_space) or (get_setting(clean_when_low_disk_space) and disk_space_low()):
            if not self.silent:
                self.progress.create(ADDON_NAME, *map(translate, (32619, 32615, 32615)))
                self.progress.update(0)
                self.monitor.waitForAbort(2)
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
                self.monitor.waitForAbort(2)  # Sleep 2 seconds to make sure file I/O is done.

                if xbmc.getCondVisibility(u"Library.IsScanningVideo"):
                    debug(u"The video library is being updated. Skipping library cleanup.", xbmc.LOGWARNING)
                else:
                    xbmc.executebuiltin(u"XBMC.CleanLibrary(video, false)")

        return self.summarize(results), self.exit_status

    def summarize(self, details):
        """
        Create a summary from the cleaning results.

        :type details: dict
        :rtype: unicode
        :return: A comma separated summary of the cleaning results.
        """
        summary = u""

        # Localize video types
        for vid_type, amount in details.items():
            if vid_type is self.MOVIES:
                video_type = translate(32515)
            elif vid_type is self.TVSHOWS:
                video_type = translate(32516)
            elif vid_type is self.MUSIC_VIDEOS:
                video_type = translate(32517)
            else:
                video_type = ""

            summary += u"{0:d} {1}, ".format(amount, video_type)

        # strip the comma and space from the last iteration and add the localized suffix
        return u"{0}{1}".format(summary.rstrip(u", "), translate(32518)) if summary else u""

    def get_expired_videos(self, option):
        """
        Find videos in the Kodi library that have been watched.

        Respects any other conditions user enables in the addon's settings.

        :type option: unicode
        :param option: The type of videos to find (one of the globals MOVIES, MUSIC_VIDEOS or TVSHOWS).
        :rtype: list
        :return: A list of expired videos, along with a number of extra attributes specific to the video type.
        """

        # A non-exhaustive list of pre-defined filters to use during JSON-RPC requests
        # These are possible conditions that must be met before a video can be deleted
        by_playcount = {u"field": u"playcount", u"operator": u"greaterthan", u"value": u"0"}
        by_date_played = {u"field": u"lastplayed", u"operator": u"notinthelast", u"value": u"{0:f}".format(get_setting(expire_after))}
        by_minimum_rating = {u"field": u"rating", u"operator": u"lessthan", u"value": u"{0:f}".format(get_setting(minimum_rating))}
        by_no_rating = {u"field": u"rating", u"operator": u"isnot", u"value": u"0"}
        by_progress = {u"field": u"inprogress", u"operator": u"false", u"value": u""}
        by_exclusion1 = {u"field": u"path", u"operator": u"doesnotcontain", u"value": get_setting(exclusion1)}
        by_exclusion2 = {u"field": u"path", u"operator": u"doesnotcontain", u"value": get_setting(exclusion2)}
        by_exclusion3 = {u"field": u"path", u"operator": u"doesnotcontain", u"value": get_setting(exclusion3)}
        by_exclusion4 = {u"field": u"path", u"operator": u"doesnotcontain", u"value": get_setting(exclusion4)}
        by_exclusion5 = {u"field": u"path", u"operator": u"doesnotcontain", u"value": get_setting(exclusion5)}

        # link settings and filters together
        settings_and_filters = [
            (get_setting(enable_expiration), by_date_played),
            (get_setting(clean_when_low_rated), by_minimum_rating),
            (get_setting(not_in_progress), by_progress),
            (get_setting(exclusion_enabled) and get_setting(exclusion1) is not u"", by_exclusion1),
            (get_setting(exclusion_enabled) and get_setting(exclusion2) is not u"", by_exclusion2),
            (get_setting(exclusion_enabled) and get_setting(exclusion3) is not u"", by_exclusion3),
            (get_setting(exclusion_enabled) and get_setting(exclusion4) is not u"", by_exclusion4),
            (get_setting(exclusion_enabled) and get_setting(exclusion5) is not u"", by_exclusion5)
        ]

        # Only check not rated videos if checking for video ratings at all
        if get_setting(clean_when_low_rated):
            settings_and_filters.append((get_setting(ignore_no_rating), by_no_rating))

        enabled_filters = [by_playcount]
        for s, f in settings_and_filters:
            if s and f[u"field"] in self.supported_filter_fields[option]:
                enabled_filters.append(f)

        debug(u"[{0}] Filters enabled: {1}".format(self.methods[option], enabled_filters))

        filters = {u"and": enabled_filters}

        request = {
            u"jsonrpc": u"2.0",
            u"method": self.methods[option],
            u"params": {
                u"properties": self.properties[option],
                u"filter": filters
            },
            u"id": 1
        }

        rpc_cmd = json.dumps(request)
        response = xbmc.executeJSONRPC(rpc_cmd)
        debug(u"[{0}] Response: {1}".format(self.methods[option], response.decode("utf-8")))
        result = json.loads(response)

        # Check the results for errors
        try:
            error = result[u"error"]
            debug(u"An error occurred. {0}".format(error))
            return None
        except KeyError as ke:
            if u"error" in ke:
                pass  # no error
            else:
                raise

        debug(u"Building list of expired videos")
        expired_videos = []
        response = result[u"result"]
        try:
            debug(u"Found {0:d} watched {1} matching your conditions".format(response[u"limits"][u"total"], option))
            debug(u"JSON Response: {0}".format(response))
            for video in response[option]:
                # Gather all properties and add it to this video's information
                temp = []
                for p in self.properties[option]:
                    temp.append(video[p])
                expired_videos.append(temp)
        except KeyError as ke:
            if option in ke:
                pass  # no expired videos found
            else:
                debug(u"KeyError: {0} not found".format(ke), xbmc.LOGWARNING)
                debug(u"{0}".format(response), xbmc.LOGWARNING)
                raise
        finally:
            debug(u"Expired videos: {0}".format(expired_videos))
            return expired_videos

    def unstack(self, path):
        """Unstack path if it is a stacked movie. See http://kodi.wiki/view/File_stacking for more info.

        :type path: unicode
        :param path: The path that should be unstacked.
        :rtype: list
        :return: A list of paths that are part of the stack. If it is no stacked movie, a one-element list is returned.
        """
        if path.startswith(u"stack://"):
            debug(u"Unstacking {0}.".format(path))
            return path.replace(u"stack://", u"").split(u" , ")
        else:
            debug(u"Unstacking {0} is not needed.".format(path))
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
        title = os.path.basename(os.path.commonprefix([f.encode("utf-8") for f in filenames])).decode("utf-8")
        for e in self.stacking_indicators:
            if title.endswith(e):
                title = title[:-len(e)].rstrip(u"._-")
                break
        return title

    def delete_file(self, location):
        """
        Delete a file from the file system. Also supports stacked movie files.

        Example:
            success = delete_file(location)

        :type location: unicode
        :param location: the path to the file you wish to delete.
        :rtype: bool
        :return: True if (at least one) file was deleted successfully, False otherwise.
        """
        debug(u"Attempting to delete {0}".format(location))

        paths = self.unstack(location)
        success = []

        for p in paths:
            if xbmcvfs.exists(p):
                success.append(bool(xbmcvfs.delete(p)))
            else:
                debug(u"File {0} no longer exists.".format(p), xbmc.LOGERROR)
                success.append(False)

        return any(success)

    def delete_empty_folders(self, location):
        """
        Delete the folder if it is empty. Presence of custom file extensions can be ignored while scanning.

        To achieve this, edit the ignored file types setting in the addon settings.

        Example:
            success = delete_empty_folders(path)

        :type location: unicode
        :param location: The path to the folder to be deleted.
        :rtype: bool
        :return: True if the folder was deleted successfully, False otherwise.
        """
        if not get_setting(delete_folders):
            debug(u"Deleting of empty folders is disabled.")
            return False

        folder = self.unstack(location)[0]  # Stacked paths should have the same parent, use any
        debug(u"Checking if {0} is empty".format(folder))
        ignored_file_types = [file_ext.strip() for file_ext in get_setting(ignore_extensions).split(u",")]
        debug(u"Ignoring file types {0}".format(ignored_file_types))

        subfolders, files = xbmcvfs.listdir(folder)
        debug(u"Contents of {dir}:\nSubfolders: {sub}\nFiles: {files}".format(dir=folder, sub=subfolders, files=files))

        empty = True
        try:
            for f in files:
                _, ext = os.path.splitext(f)
                if ext and ext not in ignored_file_types:  # ensure f is not a folder and its extension is not ignored
                    debug(u"Found non-ignored file type {0}".format(ext))
                    empty = False
                    break
        except OSError as oe:
            debug(u"Error deriving file extension. Errno {0}".format(oe.errno), xbmc.LOGERROR)
            empty = False

        # Only delete directories if we found them to be empty (containing no files or filetypes we ignored)
        if empty:
            debug(u"Directory is empty and will be removed")
            try:
                # Recursively delete any subfolders
                for f in subfolders:
                    debug(u"Deleting file at {0}".format(os.path.join(folder, f)))
                    self.delete_empty_folders(os.path.join(folder, f))

                # Delete any files in the current folder
                for f in files:
                    debug(u"Deleting file at {0}".format(os.path.join(folder, f)))
                    xbmcvfs.delete(os.path.join(folder, f))

                # Finally delete the current folder
                return xbmcvfs.rmdir(folder)
            except OSError as oe:
                debug(u"An exception occurred while deleting folders. Errno {0}".format(oe.errno), xbmc.LOGERROR)
                return False
        else:
            debug(u"Directory is not empty and will not be removed")
            return False

    def clean_related_files(self, source, dest_folder=None):
        """Clean files related to another file based on the user's preferences.

        Related files are files that only differ by extension, or that share a prefix in case of stacked movies.

        Examples of related files include NFO files, thumbnails, subtitles, fanart, etc.

        :type source: unicode
        :param source: Location of the file whose related files should be cleaned.
        :type dest_folder: unicode
        :param dest_folder: (Optional) The folder where related files should be moved to. Not needed when deleting.
        """
        if get_setting(clean_related):
            debug(u"Cleaning related files.")

            path_list = self.unstack(source)
            path, name = os.path.split(path_list[0])  # Because stacked movies are in the same folder, only check one
            if source.startswith(u"stack://"):
                name = self.get_stack_bare_title(path_list)
            else:
                name, ext = os.path.splitext(name)

            debug(u"Attempting to match related files in {0} with prefix {1}".format(path, name))
            for extra_file in xbmcvfs.listdir(path)[1]:
                extra_file = unicode(extra_file, encoding="utf-8")

                if extra_file.startswith(name):
                    debug(u"{0} starts with {1}.".format(extra_file, name))
                    extra_file_path = os.path.join(path, extra_file)
                    if get_setting(cleaning_type) == self.CLEANING_TYPE_DELETE:
                        if extra_file_path not in path_list:
                            debug(u"Deleting {0}.".format(extra_file_path))
                            xbmcvfs.delete(extra_file_path)
                    elif get_setting(cleaning_type) == self.CLEANING_TYPE_MOVE:
                        new_extra_path = os.path.join(dest_folder, os.path.basename(extra_file))
                        if new_extra_path not in path_list:
                            debug(u"Moving {0} to {1}.".format(extra_file_path, new_extra_path))
                            xbmcvfs.rename(extra_file_path, new_extra_path)
            debug(u"Finished searching for related files.")
        else:
            debug(u"Cleaning of related files is disabled.")

    def move_file(self, source, dest_folder):
        """Move a file to a new destination. Will create destination if it does not exist.

        Example:
            result = move_file(a, b)

        :type source: unicode
        :param source: the source path (absolute)
        :type dest_folder: unicode
        :param dest_folder: the destination path (absolute)
        :rtype: int
        :return: 1 if (all stacked) files were moved, 0 if not, -1 if errors occurred
        """
        paths = self.unstack(source)
        files_moved_successfully = 0
        dest_folder = unicode(xbmc.makeLegalFilename(dest_folder), encoding="utf-8")

        for p in paths:
            debug(u"Attempting to move {0} to {1}.".format(p, dest_folder))
            if xbmcvfs.exists(p):
                if not xbmcvfs.exists(dest_folder):
                    if xbmcvfs.mkdirs(dest_folder):
                        debug(u"Created destination {0}.".format(dest_folder))
                    else:
                        debug(u"Destination {0} could not be created.".format(dest_folder), xbmc.LOGERROR)
                        return -1

                new_path = os.path.join(dest_folder, os.path.basename(p))

                if xbmcvfs.exists(new_path):
                    debug(u"A file with the same name already exists in the holding folder. Checking file sizes.")
                    existing_file = xbmcvfs.File(new_path)
                    file_to_move = xbmcvfs.File(p)
                    if file_to_move.size() > existing_file.size():
                        debug(u"This file is larger than the existing file. Replacing it with this one.")
                        existing_file.close()
                        file_to_move.close()
                        if bool(xbmcvfs.delete(new_path) and bool(xbmcvfs.rename(p, new_path))):
                            files_moved_successfully += 1
                        else:
                            return -1
                    else:
                        debug(u"This file isn't larger than the existing file. Deleting it instead of moving.")
                        existing_file.close()
                        file_to_move.close()
                        if bool(xbmcvfs.delete(p)):
                            files_moved_successfully += 1
                        else:
                            return -1
                else:
                    debug(u"Moving {0} to {1}.".format(p, new_path))
                    move_success = bool(xbmcvfs.rename(p, new_path))
                    copy_success, delete_success = False, False
                    if not move_success:
                        debug(u"Move failed, falling back to copy and delete.", xbmc.LOGWARNING)
                        copy_success = bool(xbmcvfs.copy(p, new_path))
                        if copy_success:
                            debug(u"Copied successfully, attempting delete of source file.")
                            delete_success = bool(xbmcvfs.delete(p))
                            if not delete_success:
                                debug(u"Could not remove source file. Please remove the file manually.", xbmc.LOGWARNING)
                        else:
                            debug(u"Copying failed, please make sure you have appropriate permissions.", xbmc.LOGFATAL)
                            return -1

                    if move_success or (copy_success and delete_success):
                        files_moved_successfully += 1

            else:
                debug(u"File {0} is no longer available.".format(p), xbmc.LOGWARNING)

        return 1 if len(paths) == files_moved_successfully else -1

    def has_no_hard_links(self, filename):
        """
        Tests the provided filename for hard links and only returns True if the number of hard links is exactly 1.

        :param filename: The filename to check for hard links
        :type filename: str
        :return: True if the number of hard links equals 1, False otherwise.
        :rtype: bool
        """
        if get_setting(keep_hard_linked):
            debug(u"Making sure the number of hard links is exactly one.")
            is_hard_linked = all(i == 1 for i in map(xbmcvfs.Stat.st_nlink, map(xbmcvfs.Stat, self.unstack(filename))))
            debug(u"No hard links detected." if is_hard_linked else u"Hard links detected. Skipping.")
        else:
            debug(u"Not checking for hard links.")
            return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == u"log":
        win = LogViewerDialog("JanitorLogViewer.xml", ADDON.getAddonInfo(u"path"))
        win.doModal()
        del win
    elif len(sys.argv) > 1 and sys.argv[1] == u"reset":
        reset_exclusions()
    else:
        cleaner = Cleaner()
        if get_setting(default_action) == cleaner.DEFAULT_ACTION_LOG:
            xbmc.executebuiltin(u"RunScript({0}, log)".format(ADDON_ID))
        else:
            cleaner.show_progress()
            results, return_status = cleaner.clean_all()
            if results:
                # Videos were cleaned. Ask the user to view the log file.
                # TODO: Listen to OnCleanFinished notifications and wait before asking to view the log
                if xbmcgui.Dialog().yesno(translate(32514), results, translate(32519)):
                    xbmc.executebuiltin(u"RunScript({0}, log)".format(ADDON_ID))
            elif return_status == cleaner.STATUS_ABORTED:
                # Do not show cleaning results in case user aborted, e.g. to set holding folder
                pass
            else:
                xbmcgui.Dialog().ok(ADDON_NAME.decode("utf-8"), translate(32520))

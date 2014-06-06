#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

import xbmcvfs
from utils import *


# Addon info
__addonID__ = "script.filecleaner"
__addon__ = Addon(__addonID__)
__title__ = xbmc.translatePath(__addon__.getAddonInfo("name")).decode("utf-8")
__author__ = "Anthirian, drewzh"
__icon__ = xbmc.translatePath(__addon__.getAddonInfo("icon")).decode("utf-8")


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

    # Constants to ensure correct (Gotham-compatible) JSON-RPC requests for XBMC
    MOVIES = "movies"
    MUSIC_VIDEOS = "musicvideos"
    TVSHOWS = "episodes"
    CLEANING_TYPE_MOVE = "0"
    CLEANING_TYPE_DELETE = "1"
    DEFAULT_ACTION_CLEAN = "0"
    DEFAULT_ACTION_LOG = "1"

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

    def __init__(self):
        debug("%s version %s loaded." % (__addon__.getAddonInfo("name").decode("utf-8"),
                                         __addon__.getAddonInfo("version").decode("utf-8")))

    def clean(self, video_type):
        """
        Clean all watched videos of the provided type.

        :type video_type: str
        :param video_type: The type of videos to clean (one of TVSHOWS, MOVIES, MUSIC_VIDEOS).
        :rtype: (list, int)
        :return: A list of the filenames that were cleaned, as well as the number of files cleaned.
        """
        cleaned_files = []
        count = 0
        clean_this_video_type = False
        if video_type == self.TVSHOWS:
            clean_this_video_type = get_setting(clean_tv_shows)
        elif video_type == self.MOVIES:
            clean_this_video_type = get_setting(clean_movies)
        elif video_type == self.MUSIC_VIDEOS:
            clean_this_video_type = get_setting(clean_music_videos)

        if clean_this_video_type:
            for filename, title in self.get_expired_videos(video_type):
                unstacked_path = self.unstack(filename)
                if xbmcvfs.exists(unstacked_path[0]):
                    if get_setting(cleaning_type) == self.CLEANING_TYPE_MOVE:
                        if get_setting(holding_folder) == "":
                            # No destination set, prompt user to set one now
                            if xbmcgui.Dialog().yesno(__title__, translate(32521), translate(32522),
                                                      translate(32523)):
                                xbmc.executebuiltin("Addon.OpenSettings(%s)" % __addonID__)
                            break
                        if get_setting(create_subdirs):
                            if isinstance(title, unicode):
                                title = title.encode("utf-8")
                            new_path = os.path.join(get_setting(holding_folder), str(title))
                        else:
                            new_path = get_setting(holding_folder)
                        if self.move_file(filename, new_path):
                            debug("File(s) moved successfully.")
                            count += 1
                            if len(unstacked_path) > 1:
                                cleaned_files.extend(unstacked_path)
                            else:
                                cleaned_files.append(filename)
                            self.clean_related_files(filename, new_path)
                            self.delete_empty_folders(os.path.dirname(filename))
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
                    debug("%r was already deleted. Skipping." % filename, xbmc.LOGWARNING)
        else:
            debug("Cleaning of %s is disabled. Skipping." % video_type)

        return cleaned_files, count

    def clean_all(self):
        """
        Clean up any watched videos in the XBMC library, satisfying any conditions set via the addon settings.

        :rtype: str
        :return: A single-line (localized) summary of the cleaning results to be used for a notification.
        """
        debug("Starting cleaning routine.")

        if get_setting(clean_when_idle) and xbmc.Player().isPlaying():
            debug("XBMC is currently playing a file. Skipping cleaning.", xbmc.LOGWARNING)
            return None

        summary = {}
        cleaning_results, cleaned_files = [], []
        if not get_setting(clean_when_low_disk_space) or (get_setting(clean_when_low_disk_space)
                                                          and utils.disk_space_low()):
            for video_type in [self.MOVIES, self. MUSIC_VIDEOS, self.TVSHOWS]:
                cleaned_files, count = self.clean(video_type)
                if count > 0:
                    cleaning_results.extend(cleaned_files)
                    summary[video_type] = count

        # Check if we need to perform any post-cleaning operations
        if cleaning_results:
            # Write cleaned file names to the log
            Log().prepend(cleaning_results)

            # Finally clean the library to account for any deleted videos.
            if get_setting(clean_xbmc_library):
                xbmc.sleep(2000)  # Sleep 2 seconds to make sure file I/O is done.

                if xbmc.getCondVisibility("Library.IsScanningVideo"):
                    debug("The video library is being updated. Skipping library cleanup.", xbmc.LOGWARNING)
                else:
                    xbmc.executebuiltin("XBMC.CleanLibrary(video)")

        return self.summarize(summary)

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

            summary += "%d %s, " % (amount, video_type)

        # strip the comma and space from the last iteration and add the localized suffix
        if summary:
            return "%s%s" % (summary.rstrip(", "), utils.translate(32518))
        else:
            return ""

    def get_expired_videos(self, option):
        """
        Find videos in the XBMC library that have been watched.

        Respects any other conditions user enables in the addon's settings.

        :type option: str
        :param option: The type of videos to find (one of the globals MOVIES, MUSIC_VIDEOS or TVSHOWS).
        :rtype: list
        :return: A list of expired videos, along with a number of extra attributes specific to the video type.
        """

        # A non-exhaustive list of pre-defined filters to use during JSON-RPC requests
        # These are possible conditions that must be met before a video can be deleted
        by_playcount = {"field": "playcount", "operator": "greaterthan", "value": "0"}
        by_date_played = {"field": "lastplayed", "operator": "notinthelast", "value": "%d" % get_setting(expire_after)}
        by_minimum_rating = {"field": "rating", "operator": "lessthan", "value": "%d" % get_setting(minimum_rating)}
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

        debug("[%s] Filters enabled: %r" % (self.methods[option], enabled_filters))

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
        debug("[%s] Response: %r" % (self.methods[option], response))
        result = json.loads(response)

        try:
            error = result["error"]
            debug("An error occurred. %r" % error)
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
            debug("Found %d watched %s matching your conditions" % (response["limits"]["total"], option))
            debug("JSON Response: " + str(response))
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
                debug("KeyError: %r not found" % ke, xbmc.LOGWARNING)
                debug("%r" % response, xbmc.LOGWARNING)
                raise
        finally:
            debug("Expired videos: " + str(expired_videos))
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

        if not full_path:
            debug("File path is empty and cannot be checked for exclusions")
            return False

        exclusions = [get_setting(exclusion1), get_setting(exclusion2), get_setting(exclusion3)]

        if r"://" in full_path:
            debug("Detected a network path")
            pattern = re.compile("(?:smb|afp|nfs)://(?:(?:.+):(?:.+)@)?(?P<tail>.*)$", flags=re.U | re.I)

            debug("Converting excluded network paths for easier comparison")
            normalized_exclusions = []
            for ex in exclusions:
                # Strip everything but the folder structure
                try:
                    if ex and r"://" in ex:
                        # Only normalize non-empty excluded paths
                        normalized_exclusions.append(pattern.match(ex).group("tail").lower())
                except (AttributeError, IndexError, KeyError) as err:
                    debug("Could not parse the excluded network path %r\n%s" % (ex, err), xbmc.LOGWARNING)
                    return True

            debug("Conversion result: %r" % normalized_exclusions)

            debug("Proceeding to match a file with the exclusion paths")
            debug("The file to match is %r" % full_path)
            result = pattern.match(full_path)

            try:
                debug("Converting file path for easier comparison.")
                converted_path = result.group("tail").lower()
                debug("Result: %r" % converted_path)
                for ex in normalized_exclusions:
                    debug("Checking against exclusion %r." % ex)
                    if converted_path.startswith(ex):
                        debug("File %r matches excluded path %r." % (converted_path, ex))
                        return True

                debug("No match was found with an excluded path.")
                return False

            except (AttributeError, IndexError, KeyError) as err:
                debug("Error converting %r. No files will be deleted.\n%s" % (full_path, err), xbmc.LOGWARNING)
                return True
        else:
            debug("Detected a local path")
            for ex in exclusions:
                if ex and full_path.startswith(ex):
                    debug("File %r matches excluded path %r." % (full_path, ex))
                    return True

            debug("No match was found with an excluded path.")
            return False

    def unstack(self, path):
        """Unstack path if it is a stacked movie. See http://wiki.xbmc.org/index.php?title=File_stacking for more info.

        :type path: str
        :param path: The path that should be unstacked.
        :rtype: list
        :return: A list of paths that are part of the stack. If it is no stacked movie, a one-element list is returned.
        """
        if isinstance(path, unicode):
            path = path.encode("utf-8")
        if path.startswith("stack://"):
            debug("Unstacking %r." % path)
            return path.replace("stack://", "").split(" , ")
        else:
            debug("Unstacking %r is not needed." % path)
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
        debug("Attempting to delete %r" % location)

        paths = self.unstack(location)
        success = []

        if self.is_excluded(paths[0]):
            debug("Detected a file on an excluded path. Aborting.")
            return False

        for p in paths:
            if xbmcvfs.exists(p):
                success.append(bool(xbmcvfs.delete(p)))
            else:
                debug("File %r no longer exists." % p, xbmc.LOGERROR)
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
        debug("Checking if %r is empty" % folder)
        ignored_file_types = [file_ext.strip() for file_ext in get_setting(ignore_extensions).split(",")]
        debug("Ignoring file types %r" % ignored_file_types)

        subfolders, files = xbmcvfs.listdir(folder)
        debug("Contents of %r:\nSubfolders: %r\nFiles: %r" % (folder, subfolders, files))

        empty = True
        try:
            for f in files:
                _, ext = os.path.splitext(f)
                if ext and not ext in ignored_file_types:  # ensure f is not a folder and its extension is not ignored
                    debug("Found non-ignored file type %r" % ext)
                    empty = False
                    break
        except OSError as oe:
            debug("Error deriving file extension. Errno " + str(oe.errno), xbmc.LOGERROR)
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

            debug("Attempting to match related files in %r with prefix %r" % (path, name))
            for extra_file in xbmcvfs.listdir(path)[1]:
                if isinstance(path, unicode):
                    path = path.encode("utf-8")
                if isinstance(extra_file, unicode):
                    extra_file = extra_file.encode("utf-8")
                if isinstance(name, unicode):
                    name = name.encode("utf-8")

                if extra_file.startswith(name):
                    debug("%r starts with %r." % (extra_file, name))
                    extra_file_path = os.path.join(path, extra_file)
                    if get_setting(cleaning_type) == self.CLEANING_TYPE_DELETE:
                        if extra_file_path not in path_list:
                            debug("Deleting %r." % extra_file_path)
                            xbmcvfs.delete(extra_file_path)
                    elif get_setting(cleaning_type) == self.CLEANING_TYPE_MOVE:
                        new_extra_path = os.path.join(dest_folder, os.path.basename(extra_file))
                        if new_extra_path not in path_list:
                            debug("Moving %r to %r." % (extra_file_path, new_extra_path))
                            xbmcvfs.rename(extra_file_path, new_extra_path)
            debug("Finished searching for related files.")
        else:
            debug("Cleaning of related files is disabled.")

    def move_file(self, source, dest_folder):
        """Move a file to a new destination. Will create destination if it does not exist.

        Example:
            success = move_file(a, b)

        :type source: str
        :param source: the source path (absolute)
        :type dest_folder: str
        :param dest_folder: the destination path (absolute)
        :rtype: bool
        :return: True if (at least one) file was moved successfully, False otherwise.
        """
        if isinstance(source, unicode):
            source = source.encode("utf-8")

        paths = self.unstack(source)
        success = []
        dest_folder = xbmc.makeLegalFilename(dest_folder)

        if self.is_excluded(paths[0]):
            debug("Detected a file on an excluded path. Aborting.")
            return False

        for p in paths:
            debug("Attempting to move %r to %r." % (p, dest_folder))
            if xbmcvfs.exists(p):
                if not xbmcvfs.exists(dest_folder):
                    if xbmcvfs.mkdirs(dest_folder):
                        debug("Created destination %r." % dest_folder)
                    else:
                        debug("Destination %r could not be created." % dest_folder, xbmc.LOGERROR)
                        return False

                new_path = os.path.join(dest_folder, os.path.basename(p))

                if xbmcvfs.exists(new_path):
                    debug("A file with the same name already exists in the holding folder. Checking file sizes.")
                    existing_file = xbmcvfs.File(new_path)
                    file_to_move = xbmcvfs.File(p)
                    if file_to_move.size() > existing_file.size():
                        debug("This file is larger than the existing file. Replacing it with this one.")
                        existing_file.close()
                        file_to_move.close()
                        success.append(bool(xbmcvfs.delete(new_path) and xbmcvfs.rename(p, new_path)))
                    else:
                        debug("This file isn't larger than the existing file. Deleting it instead of moving.")
                        existing_file.close()
                        file_to_move.close()
                        success.append(bool(xbmcvfs.delete(p)))
                else:
                    debug("Moving %r to %r." % (p, new_path))
                    success.append(bool(xbmcvfs.rename(p, new_path)))
            else:
                debug("File %r no longer exists." % p, xbmc.LOGWARNING)
                success.append(False)

        return any(success)

if __name__ == "__main__":
    cleaner = Cleaner()
    if get_setting(default_action) == cleaner.DEFAULT_ACTION_LOG:
        xbmc.executescript("special://home/addons/script.filecleaner/viewer.py")
    else:
        results = cleaner.clean_all()
        if results:
            # Videos were cleaned. Ask the user to view the log file.
            # TODO: Listen to OnCleanFinished notifications and wait before asking to view the log
            if xbmcgui.Dialog().yesno(utils.translate(32514), results, utils.translate(32519)):
                xbmc.executescript("special://home/addons/script.filecleaner/viewer.py")
        else:
            notify(utils.translate(32520))

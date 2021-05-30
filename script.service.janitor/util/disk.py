#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from ctypes import *

import xbmc
import xbmcvfs

from util.logging.kodi import debug, notify, translate
from util.settings import *


def get_free_disk_space(path):
    """Determine the percentage of free disk space.

    :type path: unicode
    :param path: The path to the drive to check. This can be any path of any depth on the desired drive.
    :rtype: float
    :return: The percentage of free space on the disk; 100% if errors occur.
    """
    percentage = float(100)
    debug(f"Checking for disk space on path: {path}")
    if xbmcvfs.exists(path.encode()):
        if xbmc.getCondVisibility("System.Platform.Windows"):
            debug("We are checking disk space from a Windows file system")
            debug(f"The path to check is {path}")

            if "://" in path:
                debug("We are dealing with network paths")
                debug(f"Extracting information from share {path}")

                regex = "(?P<type>smb|nfs|afp)://(?:(?P<user>.+):(?P<pass>.+)@)?(?P<host>.+?)/(?P<share>[^\/]+).*$"
                pattern = re.compile(regex, flags=re.I | re.U)
                match = pattern.match(path)
                try:
                    share = match.groupdict()
                    debug(f"Protocol: {share['type']}, User: {share['user']}, Password: {share['pass']}, Host: {share['host']}, Share: {share['share']}")
                except KeyError as ke:
                    debug(f"Could not parse {ke} from {path}.", xbmc.LOGERROR)
                    return percentage

                debug("Creating UNC paths so Windows understands the shares")
                path = os.path.normcase(os.sep + os.sep + share["host"] + os.sep + share["share"])
                debug(f"UNC path: {path}")
                debug("If checks fail because you need credentials, please mount the share first")
            else:
                debug("We are dealing with local paths")

            bytes_total = c_ulonglong(0)
            bytes_free = c_ulonglong(0)
            windll.kernel32.GetDiskFreeSpaceExW(c_wchar_p(path), byref(bytes_free), byref(bytes_total), None)

            try:
                percentage = float(bytes_free.value) / float(bytes_total.value) * 100
                debug("Hard disk check results:")
                debug(f"Bytes free: {bytes_free.value}")
                debug(f"Bytes total: {bytes_total.value}")
            except ZeroDivisionError:
                notify(translate(32511), 15000, level=xbmc.LOGERROR)
        else:
            debug("We are checking disk space from a non-Windows file system")
            debug(f"Stripping {path} of all redundant stuff.")
            path = os.path.normpath(path)
            debug(f"The path now is {path}")

            try:
                diskstats = os.statvfs(path)
                percentage = float(diskstats.f_bfree) / float(diskstats.f_blocks) * 100
                debug("Hard disk check results:")
                debug(f"Bytes free: {diskstats.f_bfree}")
                debug(f"Bytes total: {diskstats.f_blocks}")
            except OSError as ose:
                # TODO: Linux cannot check remote share disk space yet
                # notify(translate(32512), 15000, level=xbmc.LOGERROR)
                notify(translate(32524), 15000, level=xbmc.LOGERROR)
                debug(f"Error accessing {path}: {ose}")
            except ZeroDivisionError:
                notify(translate(32511), 15000, level=xbmc.LOGERROR)
    else:
        notify(translate(32513), 15000, level=xbmc.LOGERROR)

    debug(f"Free space: {percentage:.2f}%")
    return percentage


def disk_space_low():
    """Check whether the disk is running low on free space.

    :rtype: bool
    :return: True if disk space is below threshold (set through addon settings), False otherwise.
    """
    return get_free_disk_space(get_value(disk_space_check_path)) <= get_value(disk_space_threshold)


def split_stack(stacked_path):
    """Split stack path if it is a stacked movie. See http://kodi.wiki/view/File_stacking for more info.

    :type stacked_path: unicode
    :param stacked_path: The stacked path that should be split.
    :rtype: list
    :return: A list of paths that are part of the stack. If it is non-stacked movie, a one-element list is returned.
    """
    return [element.replace("stack://", "") for element in stacked_path.split(" , ")]


def is_hardlinked(filename):
    """
    Tests the provided filename for hard links and only returns True if the number of hard links is exactly 1.

    :param filename: The filename to check for hard links
    :type filename: str
    :return: True if the number of hard links equals 1, False otherwise.
    :rtype: bool
    """
    if get_value(keep_hard_linked):
        debug("Hard link checks are enabled.")
        return not all(i == 1 for i in map(xbmcvfs.Stat.st_nlink, map(xbmcvfs.Stat, split_stack(filename))))
    else:
        debug("Hard link checks are disabled.")
        return False


def delete(location):
    """
    Delete a file from the file system. Also supports stacked movie files.

    Example:
        success = delete(location)

    :type location: unicode
    :param location: the path to the file you wish to delete.
    :rtype: bool
    :return: True if (at least one) file was deleted successfully, False otherwise.
    """
    debug("Attempting to delete {0}".format(location))

    paths = split_stack(location)
    success = []

    for p in paths:
        if xbmcvfs.exists(p):
            success.append(bool(xbmcvfs.delete(p)))
        else:
            debug(f"File {p} no longer exists.", xbmc.LOGERROR)
            success.append(False)

    return any(success)


def recycle(source, dest_folder):
    """Move a file to a new destination. Will create destination if it does not exist.

    Example:
        result = recycle(a, b)

    :type source: unicode
    :param source: the source path (absolute)
    :type dest_folder: unicode
    :param dest_folder: the destination path (absolute)
    :rtype: bool
    :return: True if (all stacked) files were moved, False otherwise
    """
    paths = split_stack(source)
    files_moved_successfully = 0
    dest_folder = xbmcvfs.makeLegalFilename(dest_folder)

    for p in paths:
        debug(f"Attempting to move {p} to {dest_folder}.")
        if xbmcvfs.exists(p):
            if not xbmcvfs.exists(dest_folder):
                if xbmcvfs.mkdirs(dest_folder):
                    debug(f"Created destination {dest_folder}.")
                else:
                    debug(f"Destination {dest_folder} could not be created.", xbmc.LOGERROR)
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
                    if bool(xbmcvfs.delete(new_path) and bool(xbmcvfs.rename(p, new_path))):
                        files_moved_successfully += 1
                    else:
                        return False
                else:
                    debug("This file isn't larger than the existing file. Deleting it instead of moving.")
                    existing_file.close()
                    file_to_move.close()
                    if bool(xbmcvfs.delete(p)):
                        files_moved_successfully += 1
                    else:
                        return False
            else:
                debug(f"Moving {p} to {new_path}.")
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
                        return False

                if move_success or (copy_success and delete_success):
                    files_moved_successfully += 1

        else:
            debug(f"File {p} is no longer available.", xbmc.LOGWARNING)

    return len(paths) == files_moved_successfully


def delete_empty_folders(location):
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
    if not get_value(delete_folders):
        debug("Deleting of empty folders is disabled.")
        return False

    folder = split_stack(location)[0]  # Stacked paths should have the same parent, use any
    debug(f"Checking if {folder} is empty")
    ignored_file_types = [file_ext.strip() for file_ext in get_value(ignore_extensions).split(",")]
    debug(f"Ignoring file types {ignored_file_types}")

    subfolders, files = xbmcvfs.listdir(folder)

    empty = True
    try:
        for f in files:
            _, ext = os.path.splitext(f)
            if ext and ext not in ignored_file_types:  # ensure f is not a folder and its extension is not ignored
                debug(f"Found non-ignored file type {ext}")
                empty = False
                break
    except OSError as oe:
        debug(f"Error deriving file extension. Errno {oe.errno}", xbmc.LOGERROR)
        empty = False

    # Only delete directories if we found them to be empty (containing no files or filetypes we ignored)
    if empty:
        debug("Directory is empty and will be removed")
        try:
            # Recursively delete any subfolders
            for f in subfolders:
                debug(f"Deleting file at {os.path.join(folder, f)}")
                delete_empty_folders(os.path.join(folder, f))

            # Delete any files in the current folder
            for f in files:
                debug(f"Deleting file at {os.path.join(folder, f)}")
                xbmcvfs.delete(os.path.join(folder, f))

            # Finally delete the current folder
            return xbmcvfs.rmdir(folder)
        except OSError as oe:
            debug(f"An exception occurred while deleting folders. Errno {oe.errno}", xbmc.LOGERROR)
            return False
    else:
        debug("Directory is not empty and will not be removed")
        return False


def get_common_prefix(filenames):
    """Find the common title of files part of a stack, minus the volume and file extension.

    Example:
        ["Movie_Title_part1.ext", "Movie_Title_part2.ext"] yields "Movie_Title"

    :type filenames: list
    :param filenames: a list of file names that are part of a stack. Use unstack() to find these file names.
    :rtype: str
    :return: common prefix for all stacked movie parts
    """
    prefix = os.path.basename(os.path.commonprefix([f for f in filenames]))
    for suffix in ["part", "pt", "cd", "dvd", "disk", "disc"]:
        if prefix.endswith(suffix):
            # Strip stacking indicator and separator
            prefix = prefix[:-len(suffix)].rstrip("._-")
            break
    return prefix


def is_stacked_file(location):
    """Test if this file is a stacked video file

    :param location: The path from the Kodi database to test
    :type location: str
    :return: True if this is a stacked video file, False otherwise
    :rtype: bool
    """
    return "stack://" in location


def file_exists(location):
    """Test if this file exists on disk

    :param location: The file to test
    :type location: str
    :return: True if (all elements in the stack of) this file exist(s), False otherwise
    :rtype: bool
    """
    if is_stacked_file(location):
        # Recursively test for file existence across all stacked files
        return all(map(file_exists, split_stack(location)))
    else:
        return xbmcvfs.exists(location)

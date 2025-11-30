# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of script.module.srgssr.
#
# script.module.srgssr is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# script.module.srgssr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.srgssr.
# If not, see <http://www.gnu.org/licenses/>.

import os
import json
import xbmcvfs


class StorageManager:
    """Manages file I/O operations for the SRGSSR plugin."""

    def __init__(self, srgssr_instance):
        self.srgssr = srgssr_instance
        self.profile_path = xbmcvfs.translatePath(
            self.srgssr.real_settings.getAddonInfo("profile")
        )

    def read_favourite_show_ids(self):
        """
        Reads the show ids from the file defined by the global
        variable FAVOURITE_SHOWS_FILENAMES and returns a list
        containing these ids.
        An empty list will be returned in case of failure.
        """
        path = xbmcvfs.translatePath(self.profile_path)
        file_path = os.path.join(path, self.srgssr.fname_favourite_shows)
        try:
            with open(file_path, "r") as f:
                json_file = json.load(f)
                try:
                    return [entry["id"] for entry in json_file]
                except KeyError:
                    self.srgssr.log(
                        "Unexpected file structure "
                        f"for {self.srgssr.fname_favourite_shows}."
                    )
                    return []
        except (IOError, TypeError):
            return []

    def write_favourite_show_ids(self, show_ids):
        """
        Writes a list of show ids to the file defined by the global
        variable FAVOURITE_SHOWS_FILENAME.

        Keyword arguments:
        show_ids -- a list of show ids (as strings)
        """
        show_ids_dict_list = [{"id": show_id} for show_id in show_ids]
        file_path = os.path.join(self.profile_path, self.srgssr.fname_favourite_shows)
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)
        with open(file_path, "w") as f:
            json.dump(show_ids_dict_list, f)

    def read_searches(self, filename):
        file_path = os.path.join(self.profile_path, filename)
        try:
            with open(file_path, "r") as f:
                json_file = json.load(f)
            try:
                return [entry["search"] for entry in json_file]
            except KeyError:
                self.srgssr.log(f"Unexpected file structure for {filename}.")
                return []
        except (IOError, TypeError):
            return []

    def write_search(self, filename, name, max_entries=10):
        searches = self.read_searches(filename)
        try:
            searches.remove(name)
        except ValueError:
            pass
        if len(searches) >= max_entries:
            searches.pop()
        searches.insert(0, name)
        write_dict_list = [{"search": entry} for entry in searches]
        file_path = os.path.join(self.profile_path, filename)
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)
        with open(file_path, "w") as f:
            json.dump(write_dict_list, f)

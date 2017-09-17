import datetime
import time
import calendar
import os
import json
import shutil

from sync.sync_base import SyncError
from logger import Logger


# noinspection PyMethodMayBeStatic
class SyncClient:
    def __init__(self, root_folder, file_map_path, sync_client, sync_group, selective_sync, abort_requested,
                 dry_run=False):
        self.rootFolder = root_folder
        self.syncGroup = sync_group
        self.selectiveSync = selective_sync
        self.fileMapPath = file_map_path
        self.dryRun = dry_run
        if dry_run:
            Logger.warning("Dry-run exercising only!")

        # Abort callback
        self.__abortRequested = abort_requested

        # Actual sync client for a platform
        self.__destination = sync_client

        # mask the e-mail
        email = self.__destination.users_get_current_account().email
        user, domain = email.split("@")
        domain, ext = domain.rsplit(".")
        user = user if len(user) == 2 else "%s%s%s" % (user[0], "*" * (len(user) - 2), user[-1])
        domain = domain if len(domain) == 2 else "%s%s%s" % (domain[0], "*" * (len(domain) - 2), domain[-1])
        self.eMail = "%s@%s.%s" % (user, domain, ext)

        Logger.info("Created %s", self)
        return

    def close(self):
        Logger.info("Stopping %s.", self)
        # if self.__session:
        #     self.__session.close()
        #     del self.__session
        # del self.__dbx

    def sync(self):
        Logger.info("Syncing %s.", self)

        # get the data from the previous sync
        prev_file_map = self.__load_file_map(self.fileMapPath)
        last_sync_dt = prev_file_map["timeStamp"]
        prev_local_files = prev_file_map["local"]["files"]
        prev_local_folders = prev_file_map["local"]["folders"]
        prev_remote_files = prev_file_map["remote"]["files"]
        prev_remote_folders = prev_file_map["remote"]["folders"]

        first_run = prev_local_files == [] and prev_remote_files == [] \
            and prev_local_folders == [] and prev_remote_folders == []

        if first_run:
            Logger.warning("First time sync, keeping remote files")

        completed = self.__sync_dir(self.rootFolder, prev_file_map["timeStamp"], prev_local_files,
                                    prev_local_folders, prev_remote_files, prev_remote_folders, keep_remote=first_run)

        # Now we need to fetch the most recent remote and local version again and store them
        if completed:
            new_file_map = self.__save_file_map()
            last_sync_dt = new_file_map["timeStamp"]

        if completed:
            Logger.info("Syncing completed at %s (UTC).", last_sync_dt.isoformat(sep=" "))
        else:
            Logger.warning("Syncing was stopped.")
        Logger.get_instance().flush()
        return last_sync_dt

    def get_addon_list(self):
        remote_add_on_list = self.__destination.convert_to_remote_path(os.path.join(self.rootFolder, "addonlist.json"))
        folder = os.path.split(self.fileMapPath)[0]
        local_add_on_list = os.path.join(folder, "addonlist.json")
        try:
            self.__download_file(local_add_on_list, remote_add_on_list, ignore_dry_run=True)
            with open(local_add_on_list) as fp:
                add_ons = json.load(fp)
        except SyncError:
            Logger.warning("Missing %s. Creating a new add-on list", remote_add_on_list)
            add_ons = []
        except:
            Logger.critical("Error getting add-on sync list", exc_info=True)
            add_ons = []

        if os.path.isfile(local_add_on_list):
            os.remove(local_add_on_list)

        Logger.info("Found add-ons to sync:\n%s", "\n".join(add_ons))
        return add_ons

    def store_addon_list(self, add_on_list):
        Logger.info("Storing add-ons to sync:\n%s", "\n".join(add_on_list))

        remote_add_on_list = self.__destination.convert_to_remote_path(os.path.join(self.rootFolder, "addonlist.json"))
        folder = os.path.split(self.fileMapPath)[0]
        local_add_on_list = os.path.join(folder, "addonlist.json")
        try:
            with open(local_add_on_list, mode='w') as fp:
                json.dump(add_on_list, fp, indent=2)
            self.__upload_file(local_add_on_list, remote_add_on_list, datetime.datetime.utcnow())
        except:
            Logger.critical("Error uploading the updated add-on list", exc_info=True)

        if os.path.isfile(local_add_on_list):
            os.remove(local_add_on_list)
        return

    def upload_file(self, local_fullname):
        file_name = os.path.split(local_fullname)[1]
        local_modified_time_dt = datetime.datetime(*time.gmtime(os.path.getmtime(local_fullname))[:6])
        remote_fullname = self.__destination.convert_to_remote_path(os.path.join(self.rootFolder, file_name))
        self.__upload_file(local_fullname, remote_fullname, local_modified_time_dt)
        return

    def __sync_dir(self, root_folder,
                   last_sync, prev_local_files, prev_local_folders,
                   prev_remote_files, prev_remote_folders, keep_remote=False):
        Logger.info("Syncing path: %s", root_folder)

        for root_path, local_folders, local_files in os.walk(root_folder):
            is_root_folder = root_path == root_folder

            # get remote files and compare with local
            remote_folder = self.__destination.convert_to_remote_path(root_path)
            remote_files, remote_folders = \
                self.__destination.list_folder(remote_folder, recurse=False)

            if self.__abortRequested():
                return False

            # Compare remote and local files
            if not is_root_folder:
                # No syncing of files for root folder
                local_files = filter(lambda f: not self.__exclude_file(f, root_path), local_files)
                if not self.__sync_files(last_sync, root_path, local_files, prev_local_files,
                                         remote_files, prev_remote_files, keep_remote):
                    return False
            else:
                Logger.debug("Skipping file syncing for root folder")

            # Compare remote and local folders
            if is_root_folder and self.selectiveSync:
                Logger.info("Selective-Sync is enabled. Using Add-on list for syncing.")

                # what add-ons to include according to the list.
                add_ons_to_sync = self.get_addon_list()
                if len(add_ons_to_sync) == 0:
                    Logger.warning("Not syncing any add-ons. Use the Kodi Add-on Manager "
                                   "to select add-ons for syncing.")
                local_folders[:] = filter(lambda f: f in add_ons_to_sync, local_folders)
                for remote_folder in remote_folders.keys():
                    if remote_folder not in add_ons_to_sync:
                        remote_folders.pop(remote_folder)

                Logger.debug("Limited add-ons to:\n"
                             "Local:\n- %s\n"
                             "Remote:\n- %s", "\n- ".join(local_folders), "\n- ".join(remote_folders.keys()))

            if not self.__sync_folders(root_path, local_folders, prev_local_folders,
                                       remote_folders, prev_remote_folders):
                return False

        return True

    def __sync_files(self, last_sync, root_path,
                     local_files, prev_local_files,
                     remote_files, prev_remote_files, keep_remote):

        both = filter(lambda f: f in remote_files.keys(), local_files)
        local_only = filter(lambda f: f not in remote_files.keys(), local_files)
        remote_only = filter(lambda f: f not in local_files, remote_files.keys())

        Logger.trace("File Results: \n"
                     "Both:        %s\n"
                     "Remote Only: %s\n"
                     "Local Only:  %s", both, remote_only, local_only)

        # first the simple ones:
        for local_file in both:
            if self.__abortRequested():
                return False

            local_fullname = os.path.join(root_path, local_file)
            # Get the UTC modified time using time.gmtime
            local_modified_time_dt = datetime.datetime(*time.gmtime(os.path.getmtime(local_fullname))[:6])

            remote_file = remote_files[local_file]
            remote_fullname = remote_file.path_display
            remote_modified_time_dt = remote_file.client_modified
            if remote_modified_time_dt == local_modified_time_dt:
                Logger.debug("Found unchanged file: %s (%s).", local_fullname, local_modified_time_dt)
            elif keep_remote:
                Logger.info("First run: Found a file both remote and locally, downloading: %s", remote_fullname)
                self.__download_file(local_fullname, remote_fullname)
            elif remote_modified_time_dt < local_modified_time_dt:
                Logger.debug("Found newer local file: %s (%s vs %s).", local_fullname,
                             local_modified_time_dt, remote_modified_time_dt)
                self.__upload_file(local_fullname, remote_fullname, local_modified_time_dt)
            else:
                Logger.debug("Found newer remote file: %s (%s vs %s).", remote_fullname,
                             local_modified_time_dt, remote_modified_time_dt)
                self.__download_file(local_fullname, remote_fullname)

        for local_file in local_only:
            if self.__abortRequested():
                return False

            local_fullname = os.path.join(root_path, local_file)
            local_modified_time_dt = datetime.datetime(*time.gmtime(os.path.getmtime(local_fullname))[:6])
            remote_fullname = self.__destination.convert_to_remote_path(local_fullname)

            # it was either added locally (it was not here locally the previous sync)
            if local_fullname not in prev_local_files:
                Logger.debug("Found locally added file: %s", local_fullname)
                self.__upload_file(local_fullname, remote_fullname, local_modified_time_dt)

            # or removed remotely (it was there remotely the previous sync)
            elif remote_fullname in prev_remote_files:
                Logger.debug("Found remotely removed file: %s", remote_fullname)
                # was it updated since the last sync time?
                if local_modified_time_dt > last_sync:
                    Logger.debug("Local file updated after last sync. Uploading %s", local_fullname)
                    self.__upload_file(local_fullname, remote_fullname, local_modified_time_dt)
                else:
                    Logger.debug("Removing local file: %s", local_fullname)
                    self.__delete_local_file(local_fullname)

            # it is here now and was here the previous run and it was not deleted remotely, so it should have
            # already been uploaded a while ago
            elif local_fullname in prev_local_files:
                Logger.debug("Found local file that should have already been synced: %s", local_fullname)
                self.__upload_file(local_fullname, remote_fullname, local_modified_time_dt)

            else:
                raise StandardError("Cannot determine action for local only file: %s" % (local_fullname,))

        for remote_filename in remote_only:
            if self.__abortRequested():
                return False

            remote_file = remote_files[remote_filename]
            remote_fullname = remote_file.path_display
            remote_modified_time_dt = remote_file.client_modified
            local_fullname = self.__get_local_path(remote_fullname)

            # it was either added remotely (it was not there remotely the previous sync)
            if self.__exclude_file(full_path=local_fullname):
                Logger.warning("Found remote excluded file '%s': Deleting.", remote_fullname)
                self.__delete_remote_file(remote_fullname)

            elif remote_fullname not in prev_remote_files:
                Logger.debug("Found remotely added file: %s", remote_fullname)
                self.__download_file(local_fullname, remote_fullname)

            # or removed locally (it was here locally the previous sync)
            elif local_fullname in prev_local_files:
                Logger.debug("Found locally removed file: %s", local_fullname)
                # when was it last updated remotely?
                if remote_modified_time_dt > last_sync:
                    Logger.debug("Remote file was updated after last sync. Downloading %s", remote_fullname)
                    self.__download_file(local_fullname, remote_fullname)
                else:
                    self.__delete_remote_file(remote_fullname)

            # it is there now and was there the previous run and it was not deleted locally, so it should have
            # already been downloaded a while ago
            elif remote_fullname in prev_remote_files:
                Logger.debug("Found remote file that should have already been synced: %s", local_fullname)
                self.__download_file(local_fullname, remote_fullname)

            else:
                raise StandardError("Cannot determine action for remote only file: %s" % (local_fullname,))

        return True

    def __sync_folders(self, root_path,
                       local_folders, prev_local_folders,
                       remote_folders, prev_remote_folders):

        both = filter(lambda f: f in remote_folders.keys(), local_folders)
        local_only = filter(lambda f: f not in remote_folders.keys(), local_folders)
        remote_only = filter(lambda f: f not in local_folders, remote_folders.keys())
        Logger.trace("Folder Results: \n"
                     "Both:        %s\n"
                     "Remote Only: %s\n"
                     "Local Only:  %s", both, remote_only, local_only)

        for local_folder in both:
            Logger.debug("No work for %s, as it exists both locally and remotely. Syncing files later.",
                         local_folder)

        for local_folder in local_only:
            if self.__abortRequested():
                return False

            local_fullname = os.path.join(root_path, local_folder)
            remote_fullname = self.__destination.convert_to_remote_path(local_fullname)

            # it was either added locally (it was not here locally the previous sync)
            if local_fullname not in prev_local_folders:
                Logger.debug("No work for %s, as it exists locally. Syncing files later.",
                             local_folder)
                self.__create_remote_folder(remote_fullname)

            # or removed remotely (it was there remotely the previous sync)
            elif remote_fullname in prev_remote_folders:
                Logger.debug("Removing local file: %s", local_fullname)
                self.__delete_local_folder(local_fullname)
                # no reason to travers it locally, so we remove it from the list.
                local_folders.remove(local_folder)

            # it is here now and was here the previous run and it was not deleted remotely, so it should have
            # already been uploaded a while ago
            elif local_fullname in prev_local_folders:
                Logger.debug("Found local folder that should have already been synced: %s. Syncing files later.",
                             local_fullname)
                self.__create_remote_folder(remote_fullname)
            else:
                raise StandardError("Cannot determine action for local only folder: %s" % (local_fullname,))

        for remote_folder_name in remote_only:
            if self.__abortRequested():
                return False

            remote_folder = remote_folders[remote_folder_name]
            remote_fullname = remote_folder.path_display
            local_fullname = self.__get_local_path(remote_fullname)

            # it was either added remotely (it was not there remotely the previous sync)
            if remote_fullname not in prev_remote_folders:
                Logger.debug("Found remotely added folder: %s", remote_fullname)
                self.__download_folder(local_fullname, remote_fullname)

            # or removed locally (it was here locally the previous sync)
            elif local_fullname in prev_local_folders:
                Logger.debug("Found locally removed folder: %s", local_fullname)
                self.__delete_remote_folder(remote_fullname)

            # it is there now and was there the previous run and it was not deleted locally, so it should have
            # already been downloaded a while ago
            elif remote_fullname in prev_remote_folders:
                Logger.debug("Found remote folder that should have already been synced: %s", local_fullname)
                self.__download_folder(local_fullname, remote_fullname)

            else:
                raise StandardError("Cannot determine action for remote only file: %s" % (local_fullname,))
        return True

    def __delete_remote_file(self, remote_fullname):
        Logger.info("Deleting remote file %s", remote_fullname)
        self.__destination.delete_file(remote_fullname)

    def __delete_remote_folder(self, remote_fullname):
        Logger.info("Deleting remote folder %s", remote_fullname)
        self.__destination.delete_folder(remote_fullname)

    def __delete_local_file(self, local_fullname):
        Logger.info("Deleting local file %s", local_fullname)
        if self.dryRun:
            return

        os.remove(local_fullname)
        return

    def __delete_local_folder(self, local_fullname):
        Logger.info("Deleting local folder %s", local_fullname)
        if self.dryRun:
            return

        shutil.rmtree(local_fullname)
        return

    def __download_file(self, local_fullname, remote_fullname, ignore_dry_run=False):
        Logger.info("Downloading file %s to %s", remote_fullname, local_fullname)
        self.__destination.get_file(local_fullname, remote_fullname, ignore_dry_run)

    def __download_folder(self, local_fullname, remote_fullname):
        Logger.info("Downloading folder %s to %s", remote_fullname, local_fullname)

        if not os.path.isdir(local_fullname) and not self.dryRun:
            os.mkdir(local_fullname)

        remote_files, remote_folders = self.__destination.list_folder(remote_fullname, recurse=True)
        for remote_file in remote_files:
            remote_file_fullname = remote_files[remote_file].path_display
            local_file_fullname = self.__get_local_path(remote_file_fullname)
            self.__download_file(local_file_fullname, remote_file_fullname)

        for remote_folder in remote_folders:
            if remote_folder == remote_fullname:
                # in some occasions (empty folders) the folder it self might appear!
                continue
            remote_folder_fullname = remote_folders[remote_folder].path_display
            local_folder_fullname = self.__get_local_path(remote_folder_fullname)
            self.__download_folder(local_folder_fullname, remote_folder_fullname)
        return

    def __upload_file(self, local_fullname, remote_fullname, local_modified_time_dt):
        Logger.info("Uploading file %s to %s (%s)", local_fullname, remote_fullname, local_modified_time_dt)
        self.__destination.put_file(local_fullname, remote_fullname, local_modified_time_dt)

        # TODO: We should validate if the client_modified was actually updated? If the time stamp is only modified,
        # but not the content. Dropbox won't set the client_modified to the new value.
        return

    def __create_remote_folder(self, remote_fullname):
        Logger.info("Creating remote folder: %s", remote_fullname)
        self.__destination.put_folder(remote_fullname)

    def __exclude_file(self, file_name=None, folder_path=None, full_path=None):
        if full_path and file_name is None and folder_path is None:
            folder_path, file_name = os.path.split(full_path)

        exclude = False

        # file excludes
        if file_name.startswith("."):
            exclude = True
        elif file_name == "addonlist.json":
            exclude = True
        elif os.path.splitext(file_name)[-1] in (".png", ".jpg", ".bmp", ".log"):
            exclude = True

        # folder excludes
        elif folder_path.endswith("%sservice.addondata.sync" % (os.sep,)):
            exclude = True

        if exclude:
            Logger.trace("Excluding: %s", os.path.join(folder_path, file_name))
        return exclude

    def __get_local_path(self, remote_fullname):
        remote_fullname = remote_fullname.strip("/").split("/", 1)[1]
        remote_fullname = remote_fullname.replace("/", os.sep)
        return os.path.join(self.rootFolder, remote_fullname)

    def __load_file_map(self, file_map_path):
        if not os.path.exists(file_map_path):
            # Create new map
            return self.__save_file_map(empty=True)

        with open(file_map_path) as fp:
            result = json.load(fp)
            result["timeStamp"] = datetime.datetime.utcfromtimestamp(result["timeStamp"])

        if result.get("sync_group", "") != self.syncGroup:
            Logger.warning("Sync group changed from '%s' to '%s', resetting file map",
                           result.get("sync_group", ""), self.syncGroup)
            result = self.__save_file_map(empty=True)

        return result

    def __save_file_map(self, empty=False):
        if empty:
            current_local_files = []
            current_local_folders = []
            current_remote_files = []
            current_remote_folders = []
        else:
            # generate the current remote file map
            remote_folder = self.__destination.convert_to_remote_path(self.rootFolder)
            remote_files, remote_folders = \
                self.__destination.list_folder(remote_folder, recurse=True)
            current_remote_files = map(lambda e: e.path_display, remote_files.values())
            current_remote_folders = map(lambda e: e.path_display, remote_folders.values())

            # generate the current local file map
            current_local_files = []
            current_local_folders = []
            for root_path, dirs, files in os.walk(self.rootFolder):
                for file_name in files:
                    if self.__exclude_file(file_name, root_path):
                        continue
                    current_local_files.append(os.path.join(root_path, file_name))
                for dir_name in dirs:
                    current_local_folders.append(os.path.join(root_path, dir_name))

        Logger.info("Storing new file map for sync group '%s' with: \n"
                    "Local files   : %d\n"
                    "Local folders : %d\n"
                    "Remote files  : %d\n"
                    "Remote folders: %d", self.syncGroup,
                    len(current_local_files), len(current_local_folders),
                    len(current_remote_files), len(current_remote_folders) - 1)
        # Remote folders include the root one!

        file_map_dir = os.path.split(self.fileMapPath)[0]
        if not os.path.isdir(file_map_dir):
            Logger.info("Creating folder: %s", file_map_dir)
            os.mkdir(file_map_dir)

        now_utc = datetime.datetime.utcnow()
        now_utc_tuple = now_utc.timetuple()
        file_map = {
            "timeStamp": 0 if empty else calendar.timegm(now_utc_tuple),
            "timeStampStr": "Never" if empty else str(now_utc),
            "local": {
                "folders": current_local_folders,
                "files": current_local_files
            },
            "remote": {
                "folders": current_remote_folders,
                "files": current_remote_files
            },
            "sync_group": self.syncGroup
        }

        if not self.dryRun:
            with open(self.fileMapPath, mode='w') as fp:
                json.dump(file_map, fp, indent=2)
            Logger.info("File map saved to '%s'", self.fileMapPath)

        file_map["timeStamp"] = datetime.datetime.utcfromtimestamp(file_map["timeStamp"])
        return file_map

    def __str__(self):
        if self.eMail and self.dryRun:
            return "%s for %s and group '%s' (Dry-run)" % (self.__destination, self.eMail, self.syncGroup)
        elif self.eMail:
            return "%s for %s and group '%s'" % (self.__destination, self.eMail, self.syncGroup)
        elif self.dryRun:
            return "%s without e-mail (Dry-run) for group '%s'" % (self.__destination, self.syncGroup,)

        return "%s without e-mail for group '%s'" % (self.__destination, self.syncGroup,)

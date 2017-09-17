import os
import calendar

from .. dropbox.exceptions import ApiError
from .. dropbox.files import FolderMetadata
from .. dropbox.files import WriteMode
from .. dropbox import dropbox

from .. logger import Logger

from sync_base import UserData
from sync_base import SyncBase
from sync_base import SyncError
from sync_base import RemoteFile
from sync_base import RemoteFolder


class DropBoxSync(SyncBase):
    def __init__(self, authentication_key, sync_group, root_folder):
        SyncBase.__init__(self, sync_group, root_folder)

        # Setup the Connection to Dropbox
        # proxies = {
        #   'http': 'http://127.0.0.1:8888',
        #   'https': 'http://127.0.0.1:8888',
        # }
        # self.__session = dropbox_api.create_session(proxies=proxies)
        # self.__dbx = dropbox.Dropbox(authentication_key, session=self.__session)
        self.__dbx = dropbox.Dropbox(authentication_key)

    def users_get_current_account(self):
        return UserData(email=self.__dbx.users_get_current_account().email)

    def convert_to_remote_path(self, local_path):
        relative_path = os.path.relpath(local_path, self.rootFolder).replace("\\", "/")
        if relative_path == ".":
            relative_path = ""
        return "/".join(["", self.syncGroup, relative_path]).rstrip("/")

    def get_file(self, local_path, remote_path, ignore_dry_run=False):
        try:
            res = self.__dbx.files_download_to_file(local_path, remote_path)
            Logger.info("Downloaded: %s", res.path_display)
        except ApiError, ex:
            raise SyncError(ex.message)

        # make sure we set the correct local modified time
        self.__set_local_modified_time(local_path, res.client_modified)

    def list_folder(self, remote_full_path, include_deleted=False, recurse=True):
        """ Lists a remote folder and returns a tuple of files and folders. The values keys of the resulting
        dictionaries depend on the value of the parameter <recurse>.

        :param remote_full_path: base folder to list
        :param include_deleted:  should we list deleted entries?
        :param recurse:          recurse into sub-directories? If so, the resulting dictionary keys will contain the
                                 full paths rather than the file names only.

        :return: a tuple with 2 dictionaries for files and folders. The dictionaries have the file name as keys for
        non-recursive listings, or the full file path for recursive listings.

        """

        Logger.debug("Listing remote folder: %s", remote_full_path)
        remote_files = {}
        remote_folders = {}

        try:
            res = self.__dbx.files_list_folder(remote_full_path, include_deleted=include_deleted, recursive=recurse)
            for entry in res.entries:
                if isinstance(entry, FolderMetadata):
                    remote_folders[entry.name if not recurse else entry.path_lower] = \
                        RemoteFolder(path_display=entry.path_display)
                else:
                    remote_files[entry.name if not recurse else entry.path_lower] = \
                        RemoteFile(path_display=entry.path_display, client_modified=entry.client_modified)

            page = 2
            while res.has_more:
                Logger.debug("Listing remote folder page %d: %s", page, remote_full_path)
                res = self.__dbx.files_list_folder_continue(res.cursor)
                for entry in res.entries:
                    if isinstance(entry, FolderMetadata):
                        remote_folders[entry.name if not recurse else entry.path_lower] = \
                            RemoteFolder(path_display=entry.path_display)
                    else:
                        remote_files[entry.name if not recurse else entry.path_lower] = \
                            RemoteFile(path_display=entry.path_display, client_modified=entry.client_modified)
                page += 1

        except ApiError:
            Logger.warning("Folder listing failed for '%s'. Empty?", remote_full_path)

        return remote_files, remote_folders

    def put_file(self, local_fullname, remote_fullname, local_modified_time_dt):
        with open(local_fullname, 'rb') as f:
            data = f.read()

        mode = WriteMode.overwrite
        res = self.__dbx.files_upload(data, remote_fullname, mode, client_modified=local_modified_time_dt, mute=True)
        Logger.info("Uploaded: %s", res.path_display)

        # As Dropbox does not set modified times if the content was not changed, we need to update the local modified
        # date based on the dropbox modified time.
        self.__set_local_modified_time(local_fullname, res.client_modified)
        return

    def put_folder(self, remote_folder_path):
        self.__dbx.files_create_folder(remote_folder_path)
        Logger.info("Created remote folder: %s", remote_folder_path)

    def delete_file(self, remote_file_path):
        self.__dbx.files_delete(remote_file_path)
        Logger.info("Deleted remote file: %s", remote_file_path)

    def delete_folder(self, remote_folder_path):
        self.__dbx.files_delete(remote_folder_path)
        Logger.info("Deleted remote folder: %s", remote_folder_path)

    def __str__(self):
        return "Dropbox Client"

    @staticmethod
    def __set_local_modified_time(local_fullname, modified_dt):
        # UTC time tuple to seconds since epoch
        Logger.trace("Setting modified time for %s to %s", local_fullname, modified_dt)
        modified_time = calendar.timegm(modified_dt.timetuple())
        os.utime(local_fullname, (modified_time, modified_time))

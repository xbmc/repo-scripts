from collections import namedtuple

# custom quick classes
UserData = namedtuple('UserData', ['email'])
RemoteFile = namedtuple('RemoteFile', ['path_display', 'client_modified'])
RemoteFolder = namedtuple('RemoteFolder', ['path_display'])


class SyncError(Exception):
    pass


class SyncBase:
    def __init__(self, sync_group, root_folder):
        self.rootFolder = root_folder
        self.syncGroup = sync_group

    def users_get_current_account(self):
        raise NotImplementedError()

    def convert_to_remote_path(self, local_path):
        raise NotImplementedError()

    def delete_file(self, file_path):
        raise NotImplementedError()

    def delete_folder(self, folder_path):
        raise NotImplementedError()

    def get_file(self, local_path, remote_path, ignore_dry_run=False):
        raise NotImplementedError()

    def list_folder(self, remote_full_path, include_deleted=False, recurse=True):
        raise NotImplementedError()

    def put_file(self, local_fullname, remote_fullname, local_modified_time_dt):
        raise NotImplementedError()

    def put_folder(self, remote_folder_path):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

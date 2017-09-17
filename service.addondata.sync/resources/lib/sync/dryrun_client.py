from sync_base import SyncBase


class DryRunClient(SyncBase):
    def __init__(self, base_client, sync_group, root_folder):
        # type: (SyncBase, str, str) -> DryRunClient

        SyncBase.__init__(self, sync_group, root_folder)

        # we only call base_client for the none permanent stuff
        self.__baseClient = base_client

    def users_get_current_account(self):
        return self.__baseClient.users_get_current_account()

    def convert_to_remote_path(self, local_path):
        return self.__baseClient.convert_to_remote_path(local_path)

    def put_folder(self, remote_folder_path):
        return

    def delete_file(self, file_path):
        return

    def delete_folder(self, folder_path):
        return

    def list_folder(self, remote_full_path, include_deleted=False, recurse=True):
        return self.__baseClient.list_folder(remote_full_path, include_deleted, recurse)

    def get_file(self, local_path, remote_path, ignore_dry_run=False):
        if ignore_dry_run:
            return self.__baseClient.get_file(local_path, remote_path, ignore_dry_run)
        return

    def put_file(self, local_fullname, remote_fullname, local_modified_time_dt):
        return

    def __str__(self):
        return "Dry-Run Client"

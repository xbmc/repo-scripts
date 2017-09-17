import sys
import os
import requests

import xbmc
import xbmcaddon

from kodi import dialog
from kodi import settings
from kodi.locker import LockWithDialog
from logger import Logger
from remote.remote import Remote
from sync_client import SyncClient
from sync import dropbox_client
from sync import dryrun_client


@LockWithDialog()
def menu_action(action, add_on_id=None):
    if add_on_id:
        add_on = xbmcaddon.Addon(add_on_id)
    else:
        add_on = xbmcaddon.Addon()

    if action == "settings":
        add_on.openSettings()
        return

    add_on_id = add_on.getAddonInfo('id')
    add_on_data = xbmc.translatePath("special://profile/addon_data/").decode('utf-8')
    this_add_on_data = os.path.join(add_on_data, add_on_id)
    add_on_name = add_on.getAddonInfo("name")

    # Retrieve the add-ons settings
    add_on_settings = settings.get_add_on_settings(add_on)

    # noinspection SpellCheckingInspection
    log_path = os.path.join(this_add_on_data, "add_on_data_sync_menu.log")
    Logger.create_logger(log_path, add_on_name, add_on_settings.log_level)

    if not add_on_settings.dropbox_api_key or not add_on_settings.sync_group:
        raise ValueError("Missing configuration elements. Please configure the add-on.")

    client = None
    try:
        if action == "sync":
            url = "http://%s:%s/trigger/sync" % (Remote.HostName, Remote.Port)
            Logger.info("Forcing sync on %s", url)
            result = requests.get(url)
            if result.ok:
                Logger.info("Response: %s", result.text)
            else:
                Logger.error("Response: %s", result.text)
            message = add_on.getLocalizedString(30022)
            dialog.show_notification(add_on_name, message)
            return

        # noinspection SpellCheckingInspection
        file_map = os.path.join(this_add_on_data, "filemap.json")

        dbx = dropbox_client.DropBoxSync(add_on_settings.dropbox_api_key, add_on_settings.sync_group, add_on_data)
        if add_on_settings.dry_run:
            dbx = dryrun_client.DryRunClient(dbx, add_on_settings.sync_group, add_on_data)
        client = SyncClient(add_on_data, file_map,
                            sync_client=dbx,
                            sync_group=add_on_settings.sync_group,
                            selective_sync=add_on_settings.selective_sync,
                            abort_requested=None,
                            dry_run=add_on_settings.dry_run)

        add_ons_to_sync = client.get_addon_list()
        previous_add_ons_to_sync = map(lambda a: a, add_ons_to_sync)

        if action == "add":
            if not add_on_settings.selective_sync:
                __show_selective_sync_disabled_message(add_on, add_on_name)
                return

            selected_add_on_id, selected_add_on_name = __get_selected_add_on()
            if selected_add_on_id == add_on_id:
                message = add_on.getLocalizedString(30020) % (selected_add_on_name,)
                Logger.error("Cannot add %s (%s) to add-on sync list", selected_add_on_name, selected_add_on_id)
                dialog.show_notification(add_on_name, message, 2)
                return

            Logger.info("Adding add-on '%s' to the sync list.", selected_add_on_id)
            if selected_add_on_id not in add_ons_to_sync:
                add_ons_to_sync.append(selected_add_on_id)
            client.store_addon_list(add_ons_to_sync)

            # Show Dialog
            message = add_on.getLocalizedString(30013)
            dialog.show_notification(add_on_name, message % (selected_add_on_name, selected_add_on_id))

        elif action == "remove":
            if not add_on_settings.selective_sync:
                __show_selective_sync_disabled_message(add_on, add_on_name)
                return

            selected_add_on_id, selected_add_on_name = __get_selected_add_on()
            Logger.info("Removing add-on '%s' from the sync list.", selected_add_on_id)
            if selected_add_on_id in add_ons_to_sync:
                add_ons_to_sync.remove(selected_add_on_id)
            client.store_addon_list(add_ons_to_sync)

            # Show Dialog
            message = add_on.getLocalizedString(30014)
            dialog.show_notification(add_on_name, message % (selected_add_on_name, selected_add_on_id))

        elif action == "list":
            if not add_on_settings.selective_sync:
                __show_selective_sync_disabled_message(add_on, add_on_name)
                return

            message = add_on.getLocalizedString(30018)
            to_remove = dialog.multi_select(heading=message, options=add_ons_to_sync)
            if to_remove:
                to_remove.sort(reverse=True)
                Logger.debug("Removing: %s", to_remove)
                for index in to_remove:
                    add_on_id_to_remove = add_ons_to_sync[index]
                    Logger.info("Removing %s", add_on_id_to_remove)
                    add_ons_to_sync.remove(add_on_id_to_remove)
            else:
                Logger.debug("List was aborted")

            if set(add_ons_to_sync) != set(previous_add_ons_to_sync):
                Logger.info("Add-on list changed. Storing the new list.")
                client.store_addon_list(add_ons_to_sync)

                # Show Dialog
                message = add_on.getLocalizedString(30019)
                dialog.show_notification(add_on_name, message)

        elif action == "send_logs":
            file_count = 0
            for file_name in os.listdir(this_add_on_data):
                if not file_name.endswith(".log"):
                    continue
                log_file = os.path.join(this_add_on_data, file_name)
                client.upload_file(log_file)
                file_count += 1

            message = add_on.getLocalizedString(30009) % (file_count, )
            dialog.show_notification(add_on_name, message)
        else:
            raise ValueError("Invalid action: %s" % (action, ))

    except:
        Logger.error("Error performing menu action: %s", menu_action, exc_info=True)
        raise
    finally:
        if client is not None:
            del client
        Logger.get_instance().close_log()


def __get_selected_add_on():
    # noinspection PyUnresolvedReferences
    selected_add_on_id = sys.listitem.getProperty('Addon.ID')
    # noinspection PyUnresolvedReferences
    selected_add_on_name = sys.listitem.getLabel()
    return selected_add_on_id, selected_add_on_name


def __show_selective_sync_disabled_message(add_on, add_on_name):
    msg = add_on.getLocalizedString(30025)
    dialog.show_notification(add_on_name, msg, severity=2)

from collections import namedtuple

from ..logger import Logger

# Custom objects
AddonSettings = namedtuple('AddonSettings', ['dropbox_api_key', 'log_level', 'sync_group',
                                             'selective_sync', 'dry_run', 'sync_interval'])


def get_add_on_settings(add_on):
    """ Generic method that fetches all add-on settings

    :param add_on: the Kodi add-on object
    :return:       an AddonSettings namedtuple

    """

    # Map the settings index to the actual log level
    config_levels = [Logger.TRACE, Logger.DEBUG, Logger.INFO]

    log_level = config_levels[int(add_on.getSetting("log_level"))]
    dropbox_api_key = add_on.getSetting('dropbox_api_key')
    sync_group = add_on.getSetting('sync_group')
    dry_run = add_on.getSetting("dry_run") == "true"
    sync_interval = int(add_on.getSetting("sync_interval") or "5")

    sync_mode = add_on.getSetting('sync_mode')
    selective_sync = sync_mode == "1"

    return AddonSettings(dropbox_api_key=dropbox_api_key,
                         log_level=log_level,
                         sync_group=sync_group,
                         selective_sync=selective_sync,
                         dry_run=dry_run,
                         sync_interval=sync_interval)

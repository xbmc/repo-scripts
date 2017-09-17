import os
import time
import datetime
import calendar

import xbmc
import xbmcaddon

from resources.lib.logger import Logger
from resources.lib.sync_client import SyncClient
from resources.lib.remote.remote import Remote
from resources.lib.kodi import dialog
from resources.lib.kodi import settings
from resources.lib.version import Version
from resources.lib.dnsquery import DnsQuery
from resources.lib.sync import dropbox_client
from resources.lib.sync import dryrun_client


def is_version_blocked(version):
    dns = DnsQuery("8.8.8.8")
    results = dns.resolve_dns('addon_sync_version.rieter.net', dns_types=(DnsQuery.TypeTXT, ))
    if not results:
        return False

    blocked_version = Version(results[0][1])
    Logger.trace("Found kill-switch: %s", blocked_version)
    return blocked_version >= version


try:
    monitor = xbmc.Monitor()

    # Path detection
    add_on = xbmcaddon.Addon()
    add_on_id = add_on.getAddonInfo('id')
    add_on.getAddonInfo('name')
    add_on_data = xbmc.translatePath("special://profile/addon_data/").decode('utf-8')
    this_add_on_data = os.path.join(add_on_data, add_on_id)
    add_on_name = add_on.getAddonInfo("name")
    add_on_version = Version(add_on.getAddonInfo('version'))
    # noinspection SpellCheckingInspection
    file_map = os.path.join(this_add_on_data, "filemap.json")

    # Retrieve the add-ons settings
    add_on_settings = settings.get_add_on_settings(add_on)

    # noinspection SpellCheckingInspection
    log_path = os.path.join(this_add_on_data, "add_on_data_sync.log")
    Logger.create_logger(log_path, add_on_name, add_on_settings.log_level)
    Logger.info("Add-on version installed: %s-%s", add_on_id, add_on_version)
    if is_version_blocked(add_on_version):
        raise RuntimeError("Version: %s is blocked by the DNS kill-switch" % (add_on_version, ))

    if not add_on_settings.dropbox_api_key or not add_on_settings.sync_group:
        raise ValueError("Missing configuration elements. Please configure the add-on.")

    # create a http handler
    remote_control = Remote(Logger.get_instance())
    remote_control.onEventReceived += \
        lambda remote_address, port, path: Logger.debug("Call from %s:%d to %s", remote_address, port, path)

    remote_sync_triggered = [False]
    remote_control.onSyncTriggered += lambda: remote_sync_triggered.__setitem__(0, True)
    remote_control.start()

    sync_client = dropbox_client.DropBoxSync(add_on_settings.dropbox_api_key, add_on_settings.sync_group, add_on_data)
    if add_on_settings.dry_run:
        sync_client = dryrun_client.DryRunClient(sync_client, add_on_settings.sync_group, add_on_data)
    client = SyncClient(add_on_data, file_map,
                        sync_client=sync_client,
                        sync_group=add_on_settings.sync_group,
                        selective_sync=add_on_settings.selective_sync,
                        abort_requested=monitor.abortRequested,
                        dry_run=add_on_settings.dry_run)
except Exception, ex:
    if Logger.get_instance():
        Logger.critical("Error starting Add-on Data Sync client", exc_info=True)
        Logger.get_instance().close_log()
    raise

while not monitor.abortRequested():
    try:
        # Check if settings where changed (we need to reload the settings as some time might have passed)
        add_on = xbmcaddon.Addon()
        add_on_settings = settings.get_add_on_settings(add_on)
        client.syncGroup = add_on_settings.sync_group
        client.selectiveSync = add_on_settings.selective_sync
        Logger.get_instance().set_log_level(add_on_settings.log_level)

        # new kill-switch?
        if is_version_blocked(add_on_version):
            Logger.critical("Version: %s is blocked by the DNS kill-switch", add_on_version)
            break

        last_sync_dt = client.sync()
        Logger.get_instance().flush()
        if monitor.abortRequested():
            Logger.warning("Stopping Service Loop due to Abort Request")
            break

        last_sync_tpl = last_sync_dt.utctimetuple()
        last_sync = calendar.timegm(last_sync_tpl)
        last_sync_dt = datetime.datetime.fromtimestamp(last_sync)
        add_on.setSetting("last_sync", last_sync_dt.isoformat(sep=" "))

        # Reset any previous forced syncs
        remote_sync_triggered[0] = False

        # Reload the add-on settings to get the most recent sync interval
        add_on = xbmcaddon.Addon()
        add_on_settings = settings.get_add_on_settings(add_on)
        next_sync = datetime.datetime.utcnow() + datetime.timedelta(minutes=add_on_settings.sync_interval)
        Logger.info("Sleeping for %d minutes (%s UTC) (or until stopped)", add_on_settings.sync_interval, next_sync)
        Logger.get_instance().flush()

        while datetime.datetime.utcnow() < next_sync:
            # Did Kodi break (break inner loop)?
            if monitor.abortRequested():
                Logger.warning("Stopping Service Loop due to Abort Request")
                break

            # Did we break?
            if remote_sync_triggered[0]:
                Logger.warning("Sync triggered using remote API call.")
                dialog.show_notification(add_on_name, "Sync started")
                break

            # Sleep 500 ms
            time.sleep(1)

        # Did Kodi break (break outer loop)?
        if monitor.abortRequested():
            break

    except:
        Logger.error("Error in working loop. Waiting 60 seconds before continuing", exc_info=True)
        # Sleep/wait for abort for xx seconds
        if monitor.waitForAbort(1 * 60):
            # Abort was requested while waiting. We should exit
            break

Logger.debug("Deleting Sync Client")
client.close()
del client
remote_control.stop()
del remote_control
Logger.get_instance().close_log()

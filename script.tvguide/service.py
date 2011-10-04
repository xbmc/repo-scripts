import addon
import notification
import xbmc

if addon.SETTINGS['cache.data.on.xbmc.startup'] == 'true':
    addon.SOURCE.updateChannelAndProgramListCaches()

if addon.SETTINGS['notifications.enabled'] == 'true':
    n = notification.Notification(addon.SOURCE, addon.ADDON.getAddonInfo('path'),
        xbmc.translatePath(addon.ADDON.getAddonInfo('profile')))
    n.scheduleNotifications()
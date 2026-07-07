"""
Webhook Runner background service.

Listens for Kodi playback / system events and fires the webhook mapped
to each event in events.json. Mappings are configured from the main UI
in default.py.
"""
import json
import os
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcvfs


ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
WEBHOOKS_FILE = os.path.join(ADDON_DATA, 'webhooks.json')
EVENTS_FILE = os.path.join(ADDON_DATA, 'events.json')


SUPPORTED_EVENTS = [
    'kodi_start',
    'kodi_stop',
    'playback_start',
    'playback_stop',
    'playback_pause',
    'playback_resume',
    'screensaver_on',
    'screensaver_off',
]


def _log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[Webhook Runner Service] {msg}", level)


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception as e:
        _log(f"Failed to read {path}: {e}", xbmc.LOGERROR)
        return {}


def _fire(event_name):
    if not ADDON.getSettingBool('enable_event_triggers'):
        return
    events = _load_json(EVENTS_FILE)
    webhook_id = events.get(event_name)
    if not webhook_id:
        return
    webhooks = _load_json(WEBHOOKS_FILE)
    webhook = webhooks.get(str(webhook_id))
    if not webhook or not webhook.get('enabled', True) or not webhook.get('url'):
        return
    try:
        _log(f"event={event_name} -> webhook {webhook_id} ({webhook.get('name', '')})")
        data = urllib.parse.urlencode({}).encode()
        req = urllib.request.Request(webhook['url'], data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        _log(f"webhook for {event_name} failed: {e}", xbmc.LOGERROR)


class _Player(xbmc.Player):
    def onAVStarted(self):
        _fire('playback_start')

    def onPlayBackStopped(self):
        _fire('playback_stop')

    def onPlayBackEnded(self):
        _fire('playback_stop')

    def onPlayBackPaused(self):
        _fire('playback_pause')

    def onPlayBackResumed(self):
        _fire('playback_resume')


class _Monitor(xbmc.Monitor):
    def onScreensaverActivated(self):
        _fire('screensaver_on')

    def onScreensaverDeactivated(self):
        _fire('screensaver_off')


def main():
    _log("starting")
    monitor = _Monitor()
    player = _Player()  # noqa: F841 — must stay referenced for callbacks
    _fire('kodi_start')
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
    _fire('kodi_stop')
    _log("stopped")


if __name__ == '__main__':
    main()

"""Connect or disconnect the Refract account, from the add-on settings."""
import sys
import time

import xbmcgui

from resources.lib import api, kodi


def connect():
    try:
        started = api.start_device_login()
    except Exception as error:
        kodi.log("device code refused: {0}".format(error))
        xbmcgui.Dialog().ok(kodi.string(32020), kodi.string(32024))
        return
    url = started.get("verification_uri", "https://getrefract.app/device").replace("https://", "")
    code = started.get("user_code", "")
    interval = int(started.get("interval") or 5)
    deadline = time.time() + int(started.get("expires_in") or 600)
    dialog = xbmcgui.DialogProgress()
    dialog.create(kodi.string(32020), "{0}\n[B][COLOR white]{1}[/COLOR][/B]\n{2}".format(kodi.string(32021, url), code, kodi.string(32022)))
    try:
        while time.time() < deadline:
            remaining = max(0, deadline - time.time())
            dialog.update(int(100 * remaining / max(1, int(started.get("expires_in") or 600))))
            for _ in range(interval * 4):
                if dialog.iscanceled():
                    return
                time.sleep(0.25)
            try:
                tokens = api.poll_device_login(started["device_code"])
            except api.ApiError as error:
                kodi.log("device login failed: {0}".format(error))
                if error.body.get("error") == "slow_down":
                    interval += 5
                    continue
                xbmcgui.Dialog().ok(kodi.string(32020), kodi.string(32024))
                return
            if tokens:
                break
        else:
            xbmcgui.Dialog().ok(kodi.string(32020), kodi.string(32025))
            return
    finally:
        dialog.close()
    try:
        member = api.me()
        name = member.get("username") or member.get("display_name") or ""
    except Exception:
        name = ""
    kodi.set_setting("account_name", name)
    kodi.notify(kodi.string(32023, name))


def disconnect():
    api.revoke()
    kodi.set_setting("account_name", "")
    kodi.notify(kodi.string(32026))


def main(args):
    action = args[0] if args else ""
    if action == "connect":
        connect()
    elif action == "disconnect":
        disconnect()
    else:
        kodi.ADDON.openSettings()

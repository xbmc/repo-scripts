import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import xbmc
import xbmcgui

from resources.lib.utils import get_setting, set_setting, log, log_error, notify, BASE_URL

DEVICE_CODE_URL = '{}/api/v1/kodi/device/code'.format(BASE_URL)
DEVICE_TOKEN_URL = '{}/api/v1/kodi/device/token'.format(BASE_URL)


def is_connected():
    return bool(get_setting('access_token'))


def start_authorization():
    log('Starting device authorization')

    try:
        req = Request(DEVICE_CODE_URL, data=b'', headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Kodi/script.bingebase',
        })
        response = urlopen(req, timeout=15)
        data = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, ValueError) as e:
        log_error('Failed to request device code')
        notify('Failed to connect to Bingebase', icon=xbmcgui.NOTIFICATION_ERROR)
        return False

    device_code = data['device_code']
    user_code = data['user_code']
    expires_in = data.get('expires_in', 600)
    interval = data.get('interval', 5)

    return _poll_for_authorization(device_code, user_code, expires_in, interval)


def _poll_for_authorization(device_code, user_code, expires_in, interval):
    dialog = xbmcgui.DialogProgress()
    dialog.create(
        'Bingebase',
        'Go to [B]bingebase.com/activate[/B]\n\n'
        'Enter code: [B]{}[/B]\n\n'
        'Waiting for authorization...'.format(user_code)
    )

    start_time = time.time()

    while not dialog.iscanceled():
        elapsed = time.time() - start_time

        if elapsed >= expires_in:
            dialog.close()
            notify('Authorization expired. Please try again.', icon=xbmcgui.NOTIFICATION_ERROR)
            return False

        percent = int((elapsed / expires_in) * 100)
        dialog.update(percent)

        result = _poll_for_token(device_code)

        if result == 'EXPIRED':
            dialog.close()
            notify('Authorization expired. Please try again.', icon=xbmcgui.NOTIFICATION_ERROR)
            return False

        if result:
            dialog.close()
            _save_token(result)
            notify('Successfully connected to Bingebase!')
            log('Device authorization successful')
            return True

        xbmc.sleep(interval * 1000)

    dialog.close()
    log('Device authorization cancelled by user')
    return False


def _poll_for_token(device_code):
    try:
        body = json.dumps({'device_code': device_code}).encode('utf-8')
        req = Request(DEVICE_TOKEN_URL, data=body, headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Kodi/script.bingebase',
        })
        response = urlopen(req, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        return data.get('access_token')
    except HTTPError as e:
        if e.code == 400:
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                if error_data.get('error') == 'expired_token':
                    return 'EXPIRED'
            except (ValueError, KeyError):
                pass
        return None
    except (URLError, ValueError):
        return None


def _save_token(token):
    set_setting('access_token', token)
    webhook_url = '{}/webhooks/kodi/{}'.format(BASE_URL, token)
    set_setting('webhook_url', webhook_url)
    # Clear last sync so first sync pulls full history
    set_setting('last_sync_timestamp', '')


def disconnect():
    dialog = xbmcgui.Dialog()
    if dialog.yesno('Bingebase', 'Disconnect from Bingebase?'):
        set_setting('access_token', '')
        set_setting('webhook_url', '')
        notify('Disconnected')
        log('Disconnected from Bingebase')

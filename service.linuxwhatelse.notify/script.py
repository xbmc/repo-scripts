import os

import pyqrcode
import xbmc
import xbmcaddon
from addon import CACHE_DIR, utils

if __name__ == '__main__':
    addon = xbmcaddon.Addon()

    host = xbmc.getIPAddress()
    port = addon.getSetting('server.port')

    is_auth_enabled = addon.getSetting('server.auth_enabled')
    username = addon.getSetting('server.username')
    password = addon.getSetting('server.password')

    tmp_file = os.path.join(CACHE_DIR, 'qr-code.png')

    qr_string = host + ':' + port

    if is_auth_enabled and username and password:
        qr_string = username + ':' + password + '@' + qr_string

    qr = pyqrcode.create(qr_string)
    qr.png(tmp_file, scale=30)

    utils.execute_jsonrpc('Player.Open', {'item': {'file': tmp_file}})

import os
import socket

import xbmc

import pyqrcode

from addon import cache_dir
from addon import addon
from addon import utils

if __name__ == '__main__':
    host = xbmc.getIPAddress()
    port = addon.getSetting('server.port')

    is_auth_enabled = addon.getSetting('server.auth_enabled')
    username = addon.getSetting('server.username')
    password = addon.getSetting('server.password')

    tmp_file = os.path.join(cache_dir, 'qr-code.png')

    qr_string = host + ':' + port

    if is_auth_enabled and username and password:
        qr_string = username + ':' + password + '@' + qr_string

    qr = pyqrcode.create(qr_string)
    qr.png(tmp_file, scale=30)

    utils.execute_jsonrpc('Player.Open', {'item' : {'file' : tmp_file}})

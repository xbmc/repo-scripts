# -*- coding: utf-8 -*-
# Copyright (c) 2013 Artem Glebov

import sys
import transmissionrpc

__settings__ = sys.modules[ "__main__" ].__settings__

def get_settings():
    params = {
        'address': __settings__.getSetting('rpc_host'),
        'port': __settings__.getSetting('rpc_port'),
        'user': __settings__.getSetting('rpc_user'),
        'password': __settings__.getSetting('rpc_password'),
        'stop_all_on_playback': __settings__.getSetting('stop_all_on_playback')
    }
    return params

def get_params():
    params = {
        'address': __settings__.getSetting('rpc_host'),
        'port': __settings__.getSetting('rpc_port'),
        'user': __settings__.getSetting('rpc_user'),
        'password': __settings__.getSetting('rpc_password'),
    }
    return params

def get_rpc_client():
    params = get_params()
    return transmissionrpc.Client(**params)

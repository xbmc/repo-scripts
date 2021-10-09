# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import json

import xbmc

from .common import log


def rpc_request(request):
    payload = xbmc.executeJSONRPC(json.dumps(request))
    response = json.loads(payload)
    log('JSONRPC: Requested |%s| received |%s|' % (request, str(response)))
    return response


def validate_rpc_response(response, request=None, required_attrib=None):
    if 'result' in response:
        if not required_attrib:
            return True
        if required_attrib in response['result'] and response['result'][required_attrib]:
            return True

    if 'error' in response:
        message = response['error']['message']
        code = response['error']['code']
        if request:
            error = 'JSONRPC: Requested |%s| received error |%s| and code: |%s|' % \
                    (request, message, code)
        else:
            error = 'JSONRPC: Received error |%s| and code: |%s|' % (message, code)
    else:
        if request:
            error = 'JSONRPC: Requested |%s| received error |%s|' % (request, str(response))
        else:
            error = 'JSONRPC: Received error |%s|' % str(response)

    log(error)
    return False


def files_get_directory(directory, properties=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Files.GetDirectory",
        "params": {
            "directory": "%s" % directory,
            "media": "files"
        }
    }
    if properties:
        payload["params"]["properties"] = properties

    response = rpc_request(payload)
    if not validate_rpc_response(response, payload, 'files'):
        return None
    return response


def files_get_sources(media):
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Files.GetSources",
        "params": {
            "media": "%s" % media
        }
    }

    response = rpc_request(payload)
    if not validate_rpc_response(response, payload, 'sources'):
        return None
    return response


def addons_get_addons(content, properties=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Addons.Getaddons",
        "params": {
            "content": "%s" % content
        }
    }
    if properties:
        payload["params"]["properties"] = properties

    response = rpc_request(payload)
    if not validate_rpc_response(response, payload, 'addons'):
        return None
    return response


def pvr_get_channels(group_id, properties=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "PVR.GetChannels",
        "params": {
            "channelgroupid": "%s" % group_id
        }
    }
    if properties:
        payload["params"]["properties"] = properties

    response = rpc_request(payload)
    if not validate_rpc_response(response, payload, 'channels'):
        return None
    return response


def player_open(channel_id):
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Player.Open",
        "params": {
            "item": {
                "channelid": "%s" % channel_id
            }
        }
    }
    response = rpc_request(payload)
    validate_rpc_response(response, payload)


def get_settings():
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Settings.getSettings"
    }

    response = rpc_request(payload)
    if not validate_rpc_response(response, payload, 'settings'):
        return None
    return response


def debug_show_log_info(value):
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "Settings.setSettingValue",
        "params": {
            "setting": "debug.showloginfo",
            "value": value
        }
    }

    response = rpc_request(payload)
    if not validate_rpc_response(response, payload):
        return None
    return response

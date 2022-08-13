import json
import time

import xbmc


def json_rpc(jsonmethod: str, params=None) -> dict:

    kodi_json = {}

    kodi_json["jsonrpc"] = "2.0"
    kodi_json["method"] = jsonmethod

    if not params:
        params = {}

    kodi_json["params"] = params
    kodi_json["id"] = int(time.time() * 1000)

    json_response = xbmc.executeJSONRPC(json.dumps(kodi_json))
    json_object = json.loads(json_response)
    return json_object["result"] if "result" in json_object else None

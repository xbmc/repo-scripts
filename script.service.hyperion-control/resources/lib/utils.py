"""Stereoscopic mode detection."""
import json

import xbmc

from resources.lib.interfaces import Logger


def get_stereoscopic_mode(logger: Logger) -> str:
    """Returns the currently active stereoscopic mode."""
    msg = {
        "jsonrpc": "2.0",
        "method": "GUI.GetProperties",
        "params": {"properties": ["stereoscopicmode"]},
        "id": 669,
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(msg)))
        mode = response["result"]["stereoscopicmode"]["mode"]
    except Exception:
        logger.error("Error executing JSONRPC call")
        return "2D"
    if mode == "split_vertical":
        return "3DSBS"
    return "3DTAB" if mode == "split_horizontal" else "2D"

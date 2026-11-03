"""Skinner-facing JSON-RPC calls, shown in a text viewer or bound to window properties."""
from __future__ import annotations

import json
from typing import Any, Dict, Final

import xbmc
import xbmcgui

from lib.kodi.client import log
from lib.kodi.utilities import set_window_prop


_DEFAULT_MODE: Final = 'textviewer'


def execute(
    method: str,
    params_str: str = '',
    mode: str = _DEFAULT_MODE,
    prop_prefix: str = '',
) -> None:
    """Run one JSON-RPC call, shown in a text viewer or bound to properties."""
    if not method:
        log("JSON", "execute called without a method", xbmc.LOGWARNING)
        return

    params = _parse_params(params_str)
    response = _call(method, params)

    if mode == 'property':
        _bind_properties(method, response, prop_prefix)
    else:
        _show_textviewer(method, params, response)


def _call(method: str, params: Dict[str, Any]) -> dict:
    """Issue the JSON-RPC call and return the parsed body, JSON-RPC errors included."""
    payload = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
        separators=(',', ':'),
    )
    try:
        raw = xbmc.executeJSONRPC(payload)
        parsed = json.loads(raw)
        return (
            parsed if isinstance(parsed, dict)
            else {"error": {"message": "non-dict response", "raw": raw}}
        )
    except Exception as e:
        return {"error": {"message": f"executeJSONRPC failed: {e}"}}


def _show_textviewer(method: str, params: Dict[str, Any], response: dict) -> None:
    """Show the request and response as formatted JSON."""
    body = {"method": method, "params": params, "response": response}
    xbmcgui.Dialog().textviewer(
        f"JSON-RPC: {method}",
        json.dumps(body, indent=2, sort_keys=True),
    )


def _bind_properties(method: str, response: dict, prop_prefix: str) -> None:
    """Flatten a JSON-RPC dict result into SkinInfo window properties, one level deep."""
    if not prop_prefix:
        log("JSON", f"property mode requires prop_prefix (method={method})", xbmc.LOGWARNING)
        return

    error = response.get('error')
    if error:
        log("JSON", f"JSON-RPC error for {method}: {error}", xbmc.LOGWARNING)
        return

    result = response.get('result')
    if not isinstance(result, dict):
        log(
            "JSON",
            f"property mode needs dict result for {method} (got {type(result).__name__})",
            xbmc.LOGWARNING,
        )
        return

    for key, value in result.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                _set_prop(f"SkinInfo.{prop_prefix}.{key}.{sub_key}", sub_value)
        else:
            _set_prop(f"SkinInfo.{prop_prefix}.{key}", value)


def _set_prop(name: str, value: Any) -> None:
    """Set one Home window property."""
    set_window_prop(name, value, 'home')


def _parse_params(raw: str) -> Dict[str, Any]:
    """Parse `key:value|key:a;b` pairs or raw JSON into the JSON-RPC params dict."""
    if not raw:
        return {}

    stripped = raw.strip()
    if stripped.startswith('{') or stripped.startswith('['):
        try:
            decoded = json.loads(stripped)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError as e:
            log("JSON", f"Failed to parse JSON params: {e}", xbmc.LOGWARNING)
            return {}

    out: Dict[str, Any] = {}
    for pair in raw.split('|'):
        if ':' not in pair:
            continue
        key, _, value = pair.partition(':')
        key = key.strip()
        if not key:
            continue
        if ';' in value:
            out[key] = [_coerce(token) for token in value.split(';') if token]
        else:
            out[key] = _coerce(value)
    return out


def _coerce(token: str) -> Any:
    """Coerce a string token to bool/None/int/float, falling back to string."""
    token = token.strip()
    if token == 'true':
        return True
    if token == 'false':
        return False
    if token == 'null':
        return None
    try:
        if '.' in token:
            return float(token)
        return int(token)
    except ValueError:
        return token


def execute_from_args(args: dict) -> None:
    """Execute a JSON-RPC call from the script action's arguments."""
    execute(
        method=args.get('method', ''),
        params_str=args.get('params', ''),
        mode=args.get('mode', _DEFAULT_MODE),
        prop_prefix=args.get('prop_prefix', ''),
    )

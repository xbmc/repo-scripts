"""Kodi JSON-RPC gateway: every method is a single RPC round-trip.

Single-shot by design: each call performs exactly one JSON-RPC round-trip
(or one InfoLabel / window-property read) and returns, with no retry loops,
sleeps, or jitter. Patience lives up in the app-layer scheduler, where a
retry is a cancelable scheduled event rather than a blocking loop that
stalls the dispatcher thread.

The only ``aome`` layer permitted to import ``xbmc``/``xbmcgui``.
"""

import json

import xbmc
import xbmcgui

# Kodi's home window. Its window properties are the inter-addon signaling
# channel (e.g. PM4K/Plexmod seek coordination).
_HOME_WINDOW_ID = 10000


class KodiGateway:
    """Single-shot wrapper over Kodi's JSON-RPC, InfoLabels, and window props."""

    def __init__(self, *, log):
        """``log`` is a required ``(message, level)`` sink (production
        injects the ``KodiLogger`` callable), so one instance per process
        carries the addon-wide LOGDEBUG->LOGINFO escalation.
        """
        self._log = log
        # Home-window handle, created LAZILY on first window-property use:
        # constructing a gateway must perform no Kodi GUI I/O.
        self._home_window = None

    def _execute_rpc(self, request):
        """Execute one JSON-RPC request and return the decoded response."""
        return json.loads(xbmc.executeJSONRPC(json.dumps(request)))

    def active_player_id(self):
        """Return the active player id, or -1 when there is none.

        Single ``Player.GetActivePlayers`` call. Returns the first player's
        ``playerid`` when present, else -1. No retry loop — the caller owns any
        patience for a player that is not ready yet.
        """
        try:
            response = self._execute_rpc({
                "jsonrpc": "2.0",
                "method": "Player.GetActivePlayers",
                "id": 1
            })

            if "result" in response and len(response["result"]) > 0:
                return response["result"][0].get("playerid", -1)

            return -1
        except Exception as e:
            self._log(f"AOMe_Gateway: Error getting player ID: {str(e)}", xbmc.LOGERROR)
            return -1

    def audio_info(self, player_id):
        """Return ``(codec, channels)`` for the current audio stream.

        Single ``Player.GetProperties`` call. A codec of ``'none'`` (audio
        not yet negotiated) is returned AS-IS: retry patience belongs to
        the caller, so this gateway reports whatever the player currently
        says.

        A missing ``currentaudiostream`` (LOGDEBUG) or any exception (LOGERROR)
        yields ``("unknown", "unknown")``.
        """
        try:
            response = self._execute_rpc({
                "jsonrpc": "2.0",
                "method": "Player.GetProperties",
                "params": {
                    "playerid": player_id,
                    "properties": ["currentaudiostream"]
                },
                "id": 1
            })

            if "result" in response and "currentaudiostream" in response["result"]:
                audio_stream = response["result"]["currentaudiostream"]
                return (audio_stream.get("codec", "unknown").replace('pt-', ''),
                        audio_stream.get("channels", "unknown"))

            self._log("AOMe_Gateway: No currentaudiostream in response", xbmc.LOGDEBUG)
            return "unknown", "unknown"
        except Exception as e:
            self._log(f"AOMe_Gateway: Error getting audio info: {str(e)}", xbmc.LOGERROR)
            return "unknown", "unknown"

    def infolabel(self, label):
        """Return ``xbmc.getInfoLabel(label)``, or '' if the read raises.

        The gateway does not interpret the value; callers apply the echo guard
        (dropping a label that just repeats the query) themselves. The
        exception guard matches the sibling methods: a transient read failure
        must yield the "unresolved" sentinel, not unwind the caller's
        probe/verify chain before its next attempt is scheduled.
        """
        try:
            return xbmc.getInfoLabel(label)
        except Exception as e:
            self._log(f"AOMe_Gateway: Error reading infolabel {label}: {str(e)}",
                      xbmc.LOGERROR)
            return ''

    def set_audio_delay(self, player_id, delay_seconds):
        """Set the audio delay via ``Player.SetAudioDelay``; return success.

        An ``error``
        key in the response logs LOGWARNING and returns False; success logs
        LOGDEBUG and returns True; an exception logs LOGERROR and returns False.
        """
        try:
            response = self._execute_rpc({
                "jsonrpc": "2.0",
                "method": "Player.SetAudioDelay",
                "params": {
                    "playerid": player_id,
                    "offset": delay_seconds
                },
                "id": 1
            })

            if "error" in response:
                self._log(f"AOMe_Gateway: Failed to set audio offset: {response['error']}",
                          xbmc.LOGWARNING)
                return False

            self._log(f"AOMe_Gateway: Audio offset set to {delay_seconds} seconds",
                      xbmc.LOGDEBUG)
            return True
        except Exception as e:
            self._log(f"AOMe_Gateway: Error setting audio delay: {str(e)}", xbmc.LOGERROR)
            return False

    def seek_back(self, seconds, player_id=None):
        """Seek backward by ``seconds`` via ``Player.Seek``; return success.

        A ``player_id`` of ``None`` falls back to player id ``1``.
        Error/exception handling mirrors
        :meth:`set_audio_delay`.
        """
        # No explicit player id -> assume player 1.
        target_player_id = player_id if player_id is not None else 1
        request = {
            "jsonrpc": "2.0",
            "method": "Player.Seek",
            "params": {
                "playerid": target_player_id,
                "value": {"seconds": -seconds}
            },
            "id": 1
        }

        try:
            self._log(f"AOMe_Gateway: Attempting to seek back {seconds} seconds",
                      xbmc.LOGDEBUG)
            response = self._execute_rpc(request)

            if "error" in response:
                self._log(f"AOMe_Gateway: Failed to perform seek back: {response['error']}",
                          xbmc.LOGWARNING)
                return False

            self._log(f"AOMe_Gateway: Successfully seeked back by {seconds} seconds",
                      xbmc.LOGDEBUG)
            return True
        except Exception as e:
            self._log(f"AOMe_Gateway: Error executing seek command: {str(e)}", xbmc.LOGERROR)
            return False

    def addon_enabled(self, addon_id):
        """True when ``addon_id`` is installed and enabled; False otherwise.

        Single ``Addons.GetAddonDetails`` call (the coexistence probe). A
        missing addon is a JSON-RPC error response; that and any exception
        answer False, the safe reading of every failure (the once-flag is
        only set after a warning shows, so a transient error just retries
        next start).
        """
        try:
            response = self._execute_rpc({
                "jsonrpc": "2.0",
                "method": "Addons.GetAddonDetails",
                "params": {
                    "addonid": addon_id,
                    "properties": ["enabled"]
                },
                "id": 1
            })

            if "error" in response:
                self._log(f"AOMe_Gateway: {addon_id} not installed",
                          xbmc.LOGDEBUG)
                return False

            addon = response.get("result", {}).get("addon", {})
            return bool(addon.get("enabled", False))
        except Exception as e:
            self._log(f"AOMe_Gateway: Error probing addon {addon_id}: "
                      f"{str(e)}", xbmc.LOGERROR)
            return False

    def notify_all(self, sender, message, data):
        """Broadcast a ``JSONRPC.NotifyAll`` message; return success.

        The store mutation channel's reply path (the service acks script-
        process requests through this). Single-shot like every sibling:
        an ``error`` response logs LOGWARNING and returns False, an
        exception logs LOGERROR and returns False.
        """
        try:
            response = self._execute_rpc({
                "jsonrpc": "2.0",
                "method": "JSONRPC.NotifyAll",
                "params": {
                    "sender": sender,
                    "message": message,
                    "data": data
                },
                "id": 1
            })

            if "error" in response:
                self._log(f"AOMe_Gateway: Failed to broadcast {message}: "
                          f"{response['error']}", xbmc.LOGWARNING)
                return False

            self._log(f"AOMe_Gateway: Broadcast {message}", xbmc.LOGDEBUG)
            return True
        except Exception as e:
            self._log(f"AOMe_Gateway: Error broadcasting {message}: {str(e)}",
                      xbmc.LOGERROR)
            return False

    # Kodi's WINDOW_DIALOG_ADDON_SETTINGS. While it is open, its working copy
    # of our settings is saved back on close, clobbering programmatic writes
    # made underneath it, so writers defer past it.
    _SETTINGS_DIALOG_ID = 10140

    def settings_dialog_open(self):
        """True while an addon-settings dialog is the active dialog.

        The window-id knowledge lives here (the Kodi layer) so callers only
        ask the question. ``getCurrentWindowDialogId()`` reports 9999 when no
        dialog is open; the error fallback answers False, since a transient
        read failure must not wedge a write forever.
        """
        try:
            return xbmcgui.getCurrentWindowDialogId() == self._SETTINGS_DIALOG_ID
        except Exception as e:
            self._log(f"AOMe_Gateway: Error reading current dialog id: {str(e)}",
                      xbmc.LOGERROR)
            return False

    def _window(self):
        """The cached home-window handle, created on first use."""
        if self._home_window is None:
            self._home_window = xbmcgui.Window(_HOME_WINDOW_ID)
        return self._home_window

    # The window-property methods carry the same exception guards as the RPC
    # methods: a transient GUI-layer failure must degrade to the unset
    # sentinel / a no-op, never unwind a caller mid-handler.

    def window_property(self, name):
        """Return the home-window property ``name`` (empty string if unset)."""
        try:
            return self._window().getProperty(name)
        except Exception as e:
            self._log(f"AOMe_Gateway: Error reading window property {name}: "
                      f"{str(e)}", xbmc.LOGERROR)
            return ''

    def set_window_property(self, name, value):
        """Set the home-window property ``name`` to ``value``."""
        try:
            self._window().setProperty(name, value)
        except Exception as e:
            self._log(f"AOMe_Gateway: Error setting window property {name}: "
                      f"{str(e)}", xbmc.LOGERROR)

    def clear_window_property(self, name):
        """Clear the home-window property ``name``."""
        try:
            self._window().clearProperty(name)
        except Exception as e:
            self._log(f"AOMe_Gateway: Error clearing window property {name}: "
                      f"{str(e)}", xbmc.LOGERROR)

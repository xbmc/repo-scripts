"""The scoreboard window, behind the ``xbmc.python.script`` extension point.

Shows the matches in play with their set scores, the current game's points, a
``*`` against the player serving and ``BP`` on a break point.

It uses Kodi's built-in text viewer -- ``xbmcgui.Dialog().textviewer(heading,
text, usemono)``, present since Kodi 16 with ``usemono`` since Kodi 18 -- rather
than a ``WindowXMLDialog``. That keeps the add-on free of skin XML, and the
monospace font is what lets the score columns line up. The call is modal and
returns when the viewer is closed.

Requests: the service caches each poll, so opening this window normally costs
nothing. Only a cache older than the polling cadence triggers a live read,
which matters on a plan capped at 100 requests a day.
"""

import xbmcgui

from . import api, cache, scoring, strings
from .settings import Settings, log

_LEGEND_RULE = "-" * 46


def _resolve(settings, string_id):
    return settings.localized(string_id, strings.FALLBACKS.get(string_id, ""))


def _error_string_for(status):
    """The user-facing string id for a failed read.

    A rejected key, a spent quota and a plan limit each get their own line,
    because each needs a different thing done about it. A server-side failure
    is told apart from an unreachable network: blaming the viewer's connection
    for our HTTP 500 sends them looking in the wrong place.
    """
    return {
        api.UNAUTHORIZED: strings.ERROR_UNAUTHORIZED,
        api.RATE_LIMITED: strings.ERROR_RATE_LIMITED,
        api.UPGRADE_REQUIRED: strings.ERROR_UPGRADE_REQUIRED,
        api.HTTP_ERROR: strings.ERROR_SERVICE,
        api.BAD_RESPONSE: strings.ERROR_SERVICE,
        api.NOT_FOUND: strings.ERROR_SERVICE,
    }.get(status, strings.ERROR_OFFLINE)


def _load_matches(settings):
    """Live matches for display.

    :returns: ``(matches, age_seconds, error_string_id)``. ``age_seconds`` is
        None for a list just fetched, and a number when it came from the
        service's cache. ``matches`` is None when the read failed.
    """
    # The service's last poll, if it is still within one cadence.
    cached, age = cache.read(settings.poll_seconds)
    if cached is not None:
        return cached, age, None

    result = api.Client(settings.api_key, log=log).live_matches()
    if not result:
        return None, None, _error_string_for(result.status)
    return scoring.parse_matches(result.payload), None, None


def build_text(settings, matches, age_seconds=None, error_string_id=None):
    """The viewer body. Pure enough to check without opening a window."""
    if error_string_id is not None:
        return _resolve(settings, error_string_id)
    if not matches:
        return _resolve(settings, strings.BOARD_EMPTY)

    footer = [_resolve(settings, strings.BOARD_LEGEND)]
    # Say how old the scores are whenever they did not come off the wire just
    # now. Without this a break point that resolved twenty minutes ago reads
    # as one happening this second.
    if age_seconds is not None and age_seconds >= 60:
        footer.append(_resolve(settings, strings.BOARD_AS_OF).format(
            minutes=int(age_seconds // 60)))

    blocks = scoring.board_lines(matches)
    return "\n\n".join(blocks) + f"\n\n{_LEGEND_RULE}\n" + "\n".join(footer)


def show(settings=None, dialog=None):
    """Open the scoreboard. Never raises, never logs a traceback."""
    settings = settings or Settings()
    dialog = dialog or xbmcgui.Dialog()
    heading = _resolve(settings, strings.BOARD_HEADING)

    try:
        if not settings.has_api_key:
            # No key: say what to do about it, and make no request.
            dialog.textviewer(heading, _resolve(settings, strings.BOARD_NO_KEY), True)
            return

        matches, age, error_string_id = _load_matches(settings)
        dialog.textviewer(
            heading, build_text(settings, matches, age, error_string_id), True)
    except Exception as error:  # noqa: BLE001
        log(f"scoreboard failed: {type(error).__name__}: {error}")
        try:
            dialog.textviewer(heading, _resolve(settings, strings.ERROR_OFFLINE), True)
        except Exception:  # noqa: BLE001
            pass

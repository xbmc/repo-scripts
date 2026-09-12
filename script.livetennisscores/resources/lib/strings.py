"""String ids from ``resources/language/resource.language.en_gb/strings.po``.

Kept in one place so the Python and the .po file cannot drift apart, and so
nothing user-facing is spelled out inline in the logic.

``FALLBACKS`` holds the English text for each id. It is used only if
``getLocalizedString`` comes back empty, which happens when a translation is
missing -- an empty notification is worse than an untranslated one.
"""

HEADING_ADDON = 30000
HEADING_MATCH_LIVE = 30040
HEADING_SET_DONE = 30041
HEADING_MATCH_DONE = 30042
HEADING_BREAK_POINT = 30043

BOARD_HEADING = 30050
BOARD_EMPTY = 30051
BOARD_NO_KEY = 30052
BOARD_LEGEND = 30057
BOARD_AS_OF = 30058

MORE_CHANGES = 30044

ERROR_OFFLINE = 30053
ERROR_UNAUTHORIZED = 30054
ERROR_RATE_LIMITED = 30055
ERROR_UPGRADE_REQUIRED = 30056
ERROR_SERVICE = 30059

FALLBACKS = {
    HEADING_ADDON: "Live Tennis Scores",
    HEADING_MATCH_LIVE: "Now on court",
    HEADING_SET_DONE: "Set complete",
    HEADING_MATCH_DONE: "Match finished",
    HEADING_BREAK_POINT: "Break point",
    MORE_CHANGES: "and {count} more changes",
    BOARD_HEADING: "Matches in play",
    BOARD_EMPTY: "No matches are in play right now.",
    BOARD_NO_KEY: "Set an API key in this add-on's settings to see live scores.",
    BOARD_LEGEND: "* serving    BP break point",
    BOARD_AS_OF: "Scores as at {minutes} min ago.",
    ERROR_OFFLINE: "Could not reach the Live Tennis API. Check the connection and try again.",
    ERROR_UNAUTHORIZED: "The API key was not accepted. Check it in this add-on's settings.",
    ERROR_RATE_LIMITED: "Daily request limit reached. Scores return when the limit resets.",
    ERROR_UPGRADE_REQUIRED: "This key's plan does not include the live match list.",
    ERROR_SERVICE: "The Live Tennis API could not answer just now. Try again shortly.",
}

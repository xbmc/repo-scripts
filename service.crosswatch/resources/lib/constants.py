# SPDX-License-Identifier: GPL-2.0-only
"""Addon-wide constants. No behaviour lives here."""

ADDON_ID = "service.crosswatch"
LOG_NAME = "crosswatch"

# Progress cadence is wall clock, not percentage: the contract asks for an event every
# 60 seconds and after a seek, and CrossWatch does its own throttling on top.
DEFAULT_PROGRESS_INTERVAL_SECONDS = 60

# A held skip button delivers seeks faster than the tick, and Kodi's own debounce is
# user-configurable down to zero, so seek-driven progress needs its own floor.
SEEK_MIN_GAP_SECONDS = 5.0

# The heartbeat that tells CrossWatch to stop polling this Kodi. It falls back to polling
# after 15 minutes of silence, so 5 minutes leaves room for two lost pings.
PING_INTERVAL_SECONDS = 300


DEFAULT_INDEX_TTL_SECONDS = 3600

# How far past its TTL an index may still be served when it cannot be rebuilt, expressed as
# a multiple of the TTL so there is one number to reason about rather than two. Smart
# playlists are dynamic, so an index does not merely go stale, it goes wrong: a show leaves
# Continue Watching the moment it is watched, and a kept snapshot then attributes it to
# whoever held it before. Past this, the addon stops claiming to know.
INDEX_MAX_AGE_MULTIPLIER = 2
# The contract's request timeout, and the budget a failed delivery may consume. The budget
# is far larger than Kodi's 5000ms shutdown window, which is why the backoff waits on an
# abort event rather than sleeping blind.
HTTP_TIMEOUT_SECONDS = 10.0
RETRY_BUDGET_SECONDS = 120.0
RETRY_BACKOFF_SECONDS = (1.0, 2.0, 5.0, 10.0, 20.0, 30.0)

# Kodi allows a service script 5000ms after abort before injecting SystemExit
# (xbmc/interfaces/python/PythonInvoker.cpp:62), so the shutdown path must finish well inside it.
SHUTDOWN_HTTP_TIMEOUT_SECONDS = 1.0
SHUTDOWN_DRAIN_SECONDS = 2.5

DEFAULT_QUEUE_SIZE = 100

# Completed watches kept through an outage and a restart. Bounded so a box whose CrossWatch
# is gone for good does not carry a growing file for ever.
OUTBOX_MAX_ENTRIES = 200
OUTBOX_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
PROMPT_AUTOCLOSE_SECONDS = 120
# Shorter than who-watched: at the end of a binge several follow each other, and Skip is the
# answer an empty room gives.
RATING_AUTOCLOSE_SECONDS = 60
# A Link arrives from CrossWatch, maybe while nobody is watching the TV; unanswered is No.
LINK_AUTOCLOSE_SECONDS = 60
PAIR_TIMEOUT_SECONDS = 10.0

# A permanently unexpandable playlist must not pin the addon into a continuous rebuild loop.
FAILURE_BACKOFF_SECONDS = 60
MAX_FAILURE_BACKOFF_SECONDS = 1800

# strings.po ids for what the addon shows the household directly.
NOTIFY_HEADING = 30030
NOTIFY_UNREADABLE = 30031
PROMPT_EVERYONE = 30034
WHO_WATCHED_QUESTION = 30081
WHO_WATCHED_DONE = 30082
WHO_WATCHED_SKIP = 30083
WHO_WATCHED_EPISODE = 30084
WINDOW_CLOSES_IN = 30085
WHO_WATCHED_NO_POSTER = 30101
VIEWER_PLAYLISTS = 30107
VIEWER_PROFILES = 30108
VIEWER_RENAME = 30109
VIEWER_REMOVE = 30110
WINDOW_SEARCH = 30086
WINDOW_VIEWER = 30087
WINDOW_ALL = 30088
WINDOW_NOTHING_MATCHES = 30089
WINDOW_COUNT_ALL = 30090
WINDOW_COUNT_SOME = 30091
WINDOW_FORGET_ALL = 30092
WINDOW_FORGET_SHOWN = 30093
WINDOW_YES = 30094
WINDOW_NO = 30095
WINDOW_CLOSE = 30096
WINDOW_COUNT_ONE = 30097
WINDOW_CANCEL = 30099
REMEMBERED_HEADING = 30035
REMEMBERED_FORGET = 30039
REMEMBERED_WILL_ASK = 30041
REMEMBERED_NOT_IN_LIBRARY_HEAD = 30042
REMEMBERED_LIBRARY_ID = 30043
REMEMBERED_CONFIRM_FORGET_ALL = 30044
REMEMBERED_NONE_YET = 30045
REMEMBERED_NOT_STABLE_HEAD = 30046
REMEMBERED_CONFIRM_FORGET_ONE = 30047
# The settings category title doubles as the viewer list's heading.
VIEWERS_HEADING = 30010
VIEWERS_ADD = 30048
VIEWERS_PLAYLISTS_FOR = 30052
VIEWERS_PROFILES_FOR = 30114
VIEWERS_NAME_PROMPT = 30054
VIEWERS_NAME_CLASH = 30153
VIEWERS_ADD_PEOPLE = 30154
VIEWERS_TYPE_NAME = 30155
VIEWERS_ONE_PERSON = 30156
VIEWERS_PEOPLE = 30157
VIEWER_FROM_CROSSWATCH = 30158
VIEWER_RENAMED_HEADING = 30159
VIEWERS_PICK_CLASH = 30160
VIEWERS_REMOVE_CONFIRM = 30055
VIEWERS_PLAYLISTS = 30056
VIEWERS_MISSING = 30058
VIEWERS_ONE_PLAYLIST = 30059
VIEWERS_ALSO = 30098
VIEWERS_NO_PLAYLISTS = 30100
VIEWERS_ONE_VIEWER = 30102
VIEWERS_COUNT = 30103
VIEWERS_ONE_PROFILE = 30105
VIEWERS_PROFILES = 30106
VIEWER_NONE = 30113
VIEWERS_REMOVE_MESSAGE = 30115
VIEWERS_PROFILES_FAILED = 30116
VIEWERS_EMPTY = 30118
VIEWER_ROUTE_OK = 30119
VIEWER_ROUTE_MISSING = 30120
VIEWER_MORE = 30121
VIEWER_UNUSABLE = 30122
REMEMBERED_ANSWER = 30123
REMEMBERED_PLAYLIST_OF = 30124
REMEMBERED_GONE = 30125
REMEMBERED_POINTS_AT = 30126
REMEMBERED_NO_TITLE = 30127
REMEMBERED_CHANGE = 30128
PAIR_ADDRESS = 30063
PAIR_CODE = 30064
PAIR_DONE = 30065
PAIR_INVALID_CODE = 30066
PAIR_RATE_LIMITED = 30067
PAIR_UNREACHABLE = 30068
PAIR_FAILED = 30069
PAIR_BAD_ADDRESS = 30070
LINK_CONFIRM = 30071
STATUS_PAIRED = 30072
STATUS_NOT_PAIRED = 30074
UNPAIR_CONFIRM = 30075
REMEMBERED_COVERED_BY = 30077
PAIR_CERTIFICATE = 30078

LOG_MAX_BYTES = 500 * 1024
LOG_BACKUP_COUNT = 3
RATING_QUESTION_NAMED = 30139
RATING_QUESTION_HOUSEHOLD = 30140
RATING_REMOVE = 30141
# Score 1 first; the window shows the word of the score that has focus.
RATING_WORDS = (30143, 30144, 30145, 30146, 30147, 30148, 30149, 30150, 30151, 30152)

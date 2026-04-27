"""
Centralized constants for EasyMovie.

All magic numbers, string literals, property names, setting IDs,
and configuration values live here. Import from this module rather
than hardcoding values elsewhere.
"""

# Addon identity
ADDON_ID = "script.easymovie"
ADDON_NAME = "EasyMovie"

# Icon persistence
CUSTOM_ICON_BACKUP = "custom_icon.png"

# Log file configuration
LOG_DIR = "logs"
LOG_FILENAME = "easymovie.log"
LOG_MAX_BYTES = 500 * 1024  # 500KB
LOG_BACKUP_COUNT = 3
LOG_MAX_VALUE_LENGTH = 200
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
LOG_TIMESTAMP_TRIM = 23  # Trim microseconds to milliseconds

# Primary function modes
MODE_BROWSE = 0
MODE_PLAYLIST = 1
MODE_ASK = 2

# Filter modes (for settings: Ask / Pre-set / Skip)
FILTER_ASK = 0
FILTER_PRESET = 1
FILTER_SKIP = 2

# Watched status values
WATCHED_UNWATCHED = 0
WATCHED_WATCHED = 1
WATCHED_BOTH = 2

# Year filter types
YEAR_FILTER_AFTER = 0
YEAR_FILTER_RECENCY = 3

# Sort options
SORT_RANDOM = 0
SORT_TITLE = 1
SORT_YEAR = 2
SORT_RATING = 3
SORT_RUNTIME = 4
SORT_DATE_ADDED = 5

# Sort directions
SORT_ASC = 0
SORT_DESC = 1

# View styles
VIEW_SHOWCASE = 0  # Horizontal filmstrip carousel
VIEW_CARD_LIST = 1
VIEW_POSTERS = 2
VIEW_BIG_SCREEN = 3
VIEW_SPLIT_VIEW = 4

# Theme IDs (shared with EasyTV)
THEME_GOLDEN_HOUR = 0
THEME_ULTRAVIOLET = 1
THEME_EMBER = 2
THEME_NIGHTFALL = 3

# Theme color definitions (AARRGGBB format)
# Same values as EasyTV for visual consistency
THEME_COLORS = {
    THEME_GOLDEN_HOUR: {
        'EasyMovie.Accent': 'FFF5A623',
        'EasyMovie.AccentGlow': 'FFF5C564',
        'EasyMovie.AccentBG': '59B4781E',
        'EasyMovie.ButtonTextFocused': 'FF0D1117',
        'EasyMovie.ButtonFocus': 'FFD4912A',
    },
    THEME_ULTRAVIOLET: {
        'EasyMovie.Accent': 'FFA78BFA',
        'EasyMovie.AccentGlow': 'FFC4B5FD',
        'EasyMovie.AccentBG': '596432B4',
        'EasyMovie.ButtonTextFocused': 'FFFFFFFF',
        'EasyMovie.ButtonFocus': 'FF7C3AED',
    },
    THEME_EMBER: {
        'EasyMovie.Accent': 'FFF87171',
        'EasyMovie.AccentGlow': 'FFFCA5A5',
        'EasyMovie.AccentBG': '59B43232',
        'EasyMovie.ButtonTextFocused': 'FFFFFFFF',
        'EasyMovie.ButtonFocus': 'FFEF4444',
    },
    THEME_NIGHTFALL: {
        'EasyMovie.Accent': 'FF60A5FA',
        'EasyMovie.AccentGlow': 'FF93C5FD',
        'EasyMovie.AccentBG': '59286AB4',
        'EasyMovie.ButtonTextFocused': 'FFFFFFFF',
        'EasyMovie.ButtonFocus': 'FF3B82F6',
    },
}

# Re-suggestion window options (hours)
RESURFACE_WINDOWS = {
    0: 4,
    1: 8,
    2: 12,
    3: 24,
    4: 48,
    5: 72,
}

# Runtime filter ranges for wizard (in minutes)
RUNTIME_RANGES = [
    (0, 90, "Under 90 minutes"),
    (90, 120, "90 – 120 minutes"),
    (120, 150, "120 – 150 minutes"),
    (150, 0, "Over 150 minutes"),  # 0 = no upper limit
    (0, 0, "Any runtime"),  # both 0 = no filter
]

# Recency ranges for year filter wizard (years_ago, lang_id)
RECENCY_RANGES = [
    (1, 32210),   # "Last year"
    (2, 32211),   # "Last 2 years"
    (5, 32212),   # "Last 5 years"
    (10, 32213),  # "Last 10 years"
    (20, 32214),  # "Last 20 years"
]

# Score filter ranges for wizard
SCORE_RANGES = [
    (80, "8.0+ (Excellent)"),
    (70, "7.0+ (Good)"),
    (60, "6.0+ (Above Average)"),
    (50, "5.0+ (Average)"),
    (0, "Any score"),
]

# Timing constants (milliseconds)
NOTIFICATION_DURATION_MS = 5000
PLAYLIST_ADD_DELAY_MS = 50

# Continuation prompt
CONTINUATION_DEFAULT_CONTINUE_SET = 0

# Window properties for service coordination
PROP_PLAYLIST_RUNNING = "EasyMovie.PlaylistRunning"

# Playback monitor timing (milliseconds)
PLAYER_STOP_DELAY_MS = 500

# Seconds to rewind from a saved resume point so the user catches context.
RESUME_REWIND_SECONDS = 10

# Kodi GUI action IDs
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117
ACTION_TELETEXT_BLUE = 218

# Theme names (for UI display, e.g. preview mode cycling)
THEME_NAMES = ["Golden Hour", "Ultraviolet", "Ember", "Nightfall"]

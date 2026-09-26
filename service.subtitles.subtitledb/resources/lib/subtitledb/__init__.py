"""SubtitleDB client shared by the Bazarr provider and the Kodi addon.

Standard library only, so it can be vendored into a Kodi addon zip and dropped into
a Bazarr install without touching either one's dependency tree.

    from subtitledb import Client, Hint, Options, find

    client = Client(client="kodi")
    result = find(client, Hint(imdb_id="tt17009710", release="Anatomy.of.a.Fall.2023.1080p"),
                  Options(languages=["en", "fr"], formats=["srt"]))
    for c in result.candidates:
        print(candidate_label(c), c.subtitle["download_url"])
"""

from .client import DEFAULT_API_BASE, Client, SubtitleDbError
from .find import (
    PER_LANGUAGE,
    TIER_IMDB,
    TIER_NONE,
    TIER_SERIES_IMDB,
    TIER_TITLE,
    TIER_TMDB,
    Result,
    find,
    per_language,
)
from .languages import language_name, to_code, to_codes
from .match import (
    Candidate,
    Hint,
    Options,
    Ranked,
    candidate_label,
    rank,
    score_subtitle,
    similarity,
)

__version__ = "0.3.1"

__all__ = [
    "DEFAULT_API_BASE",
    "PER_LANGUAGE",
    "TIER_IMDB",
    "TIER_NONE",
    "TIER_SERIES_IMDB",
    "TIER_TITLE",
    "TIER_TMDB",
    "Candidate",
    "Client",
    "Hint",
    "Options",
    "Ranked",
    "Result",
    "SubtitleDbError",
    "__version__",
    "candidate_label",
    "find",
    "language_name",
    "per_language",
    "rank",
    "score_subtitle",
    "similarity",
    "to_code",
    "to_codes",
]

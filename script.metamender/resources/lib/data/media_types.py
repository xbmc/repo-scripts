"""Media type definitions for MetaMender."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaType:
    name: str
    label: str
    kodi_list_method: str
    kodi_set_method: str
    kodi_get_method: str
    kodi_id_field: str
    kodi_result_key: str
    kodi_detail_key: str
    backfill_fields: frozenset[str]
    date_field: str


MOVIE = MediaType(
    name="movie",
    label="Movies",
    kodi_list_method="VideoLibrary.GetMovies",
    kodi_set_method="VideoLibrary.SetMovieDetails",
    kodi_get_method="VideoLibrary.GetMovieDetails",
    kodi_id_field="movieid",
    kodi_result_key="movies",
    kodi_detail_key="moviedetails",
    backfill_fields=frozenset({
        "rating", "votes", "plot", "tagline", "director", "writer",
        "genre", "studio", "country", "trailer", "runtime", "mpaa", "title",
        "poster", "fanart", "clearlogo", "keyart", "landscape", "banner",
        "discart", "clearart",
    }),
    date_field="premiered",
)

TVSHOW = MediaType(
    name="tvshow",
    label="TV Shows",
    kodi_list_method="VideoLibrary.GetTVShows",
    kodi_set_method="VideoLibrary.SetTVShowDetails",
    kodi_get_method="VideoLibrary.GetTVShowDetails",
    kodi_id_field="tvshowid",
    kodi_result_key="tvshows",
    kodi_detail_key="tvshowdetails",
    backfill_fields=frozenset({
        "rating", "votes", "plot", "genre", "mpaa", "title", "poster",
        "fanart", "clearlogo", "keyart", "landscape", "banner", "clearart",
        "characterart",
    }),
    date_field="premiered",
)

EPISODE = MediaType(
    name="episode",
    label="Episodes",
    kodi_list_method="VideoLibrary.GetEpisodes",
    kodi_set_method="VideoLibrary.SetEpisodeDetails",
    kodi_get_method="VideoLibrary.GetEpisodeDetails",
    kodi_id_field="episodeid",
    kodi_result_key="episodes",
    kodi_detail_key="episodedetails",
    backfill_fields=frozenset({
        "rating", "votes", "plot", "title", "director", "writer",
        "firstaired", "runtime", "thumb",
    }),
    date_field="firstaired",
)

# date_field is a synthetic key the scan sets; Kodi has no date on a season.
SEASON = MediaType(
    name="season",
    label="Seasons",
    kodi_list_method="VideoLibrary.GetSeasons",
    kodi_set_method="VideoLibrary.SetSeasonDetails",
    kodi_get_method="VideoLibrary.GetSeasonDetails",
    kodi_id_field="seasonid",
    kodi_result_key="seasons",
    kodi_detail_key="seasondetails",
    backfill_fields=frozenset({"poster"}),
    date_field="firstaired",
)

# A Kodi movie set. Its identity is the TMDB collection its members belong
# to (engine/sets.py); date_field is the newest member's premiered date,
# which the set pass puts on the item.
SET = MediaType(
    name="set",
    label="Movie sets",
    kodi_list_method="VideoLibrary.GetMovieSets",
    kodi_set_method="VideoLibrary.SetMovieSetDetails",
    kodi_get_method="VideoLibrary.GetMovieSetDetails",
    kodi_id_field="setid",
    kodi_result_key="sets",
    kodi_detail_key="setdetails",
    backfill_fields=frozenset({
        "title", "plot", "poster", "fanart", "clearlogo", "keyart", "landscape",
        "banner", "discart", "clearart",
    }),
    date_field="premiered",
)

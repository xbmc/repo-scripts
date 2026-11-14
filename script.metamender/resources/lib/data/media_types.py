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
        "rating", "votes", "plot", "genre", "mpaa", "title",
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
        "firstaired", "runtime",
    }),
    date_field="firstaired",
)

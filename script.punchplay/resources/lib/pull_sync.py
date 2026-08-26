"""
pull_sync.py — apply PunchPlay history back to the Kodi library.

Fetches the authenticated user's watched history and in-progress items from
/api/scrobble/sync and applies them to Kodi via JSON-RPC:

  • Watched movies/episodes → playcount + lastplayed (never *un*-watches).
  • In-progress items       → resume points (with staleness guards).

Matching is by TMDB uniqueid first, then IMDb.  Items that are not in the
Kodi library are counted as unmatched and skipped.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import xbmc

from constants import (
    PULL_SYNC_TIMEOUT_SECS,
    SCROBBLE_SYNC_ENDPOINT,
    iso_to_epoch,
    iso_to_kodi_datetime,
    kodi_datetime_to_epoch,
)

# Resume points below this position are noise (credits skip, sampling).
RESUME_MIN_POSITION_SECS = 60
# Don't set a resume point that is basically "finished".
RESUME_END_GUARD_SECS = 120
# Skip when Kodi's resume point is already within this distance.
RESUME_MIN_DELTA_SECS = 60


def _rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
    raw = xbmc.executeJSONRPC(
        json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1})
    )
    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"JSON-RPC {method} failed: {data['error']}")
    return data.get("result", {}) or {}


def _get_kodi_movies() -> list[dict[str, Any]]:
    result = _rpc(
        "VideoLibrary.GetMovies",
        {"properties": ["uniqueid", "playcount", "lastplayed", "resume"]},
    )
    return result.get("movies", []) or []


def _get_kodi_shows() -> list[dict[str, Any]]:
    result = _rpc("VideoLibrary.GetTVShows", {"properties": ["uniqueid"]})
    return result.get("tvshows", []) or []


def _get_kodi_episodes() -> list[dict[str, Any]]:
    result = _rpc(
        "VideoLibrary.GetEpisodes",
        {
            "properties": [
                "tvshowid", "season", "episode",
                "playcount", "lastplayed", "resume",
            ]
        },
    )
    return result.get("episodes", []) or []


def _index_by_unique_ids(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index library items by "tmdb:<id>" and "imdb:<id>" uniqueid keys."""
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        unique_ids = item.get("uniqueid") or {}
        tmdb = str(unique_ids.get("tmdb") or "").strip()
        imdb = str(unique_ids.get("imdb") or "").strip()
        if tmdb:
            index.setdefault(f"tmdb:{tmdb}", item)
        if imdb:
            index.setdefault(f"imdb:{imdb}", item)
    return index


def _find_in_index(
    index: dict[str, dict[str, Any]],
    tmdb_id: Any,
    imdb_id: Any,
) -> dict[str, Any] | None:
    if tmdb_id is not None:
        found = index.get(f"tmdb:{tmdb_id}")
        if found:
            return found
    if imdb_id:
        found = index.get(f"imdb:{imdb_id}")
        if found:
            return found
    return None


class KodiLibraryIndex:
    """Snapshot of the Kodi video library keyed for PunchPlay matching."""

    def __init__(self) -> None:
        self.movies = _index_by_unique_ids(_get_kodi_movies())
        self.shows = _index_by_unique_ids(_get_kodi_shows())
        episodes = _get_kodi_episodes()
        self.episodes: dict[tuple[int, int, int], dict[str, Any]] = {}
        for ep in episodes:
            try:
                key = (int(ep["tvshowid"]), int(ep["season"]), int(ep["episode"]))
            except (KeyError, TypeError, ValueError):
                continue
            self.episodes.setdefault(key, ep)

    def find_movie(self, remote: dict[str, Any]) -> dict[str, Any] | None:
        return _find_in_index(self.movies, remote.get("tmdb_id"), remote.get("imdb_id"))

    def find_episode(self, remote: dict[str, Any]) -> dict[str, Any] | None:
        show = _find_in_index(
            self.shows, remote.get("show_tmdb_id"), remote.get("show_imdb_id")
        )
        if not show:
            return None
        season = remote.get("season")
        episode = remote.get("episode")
        if season is None or episode is None:
            return None
        try:
            key = (int(show["tvshowid"]), int(season), int(episode))
        except (KeyError, TypeError, ValueError):
            return None
        return self.episodes.get(key)


def should_apply_resume(
    remote: dict[str, Any],
    kodi_item: dict[str, Any],
) -> bool:
    """
    Decide whether a remote in-progress position should overwrite the Kodi
    resume point.  Pure function — unit-tested.
    """
    position = remote.get("position_seconds") or 0
    duration = remote.get("duration_seconds") or 0
    if position < RESUME_MIN_POSITION_SECS:
        return False
    if duration > 0 and duration - position < RESUME_END_GUARD_SECS:
        return False

    resume = kodi_item.get("resume") or {}
    kodi_position = float(resume.get("position") or 0)
    if abs(kodi_position - position) < RESUME_MIN_DELTA_SECS:
        return False

    # Only overwrite when the remote progress is newer. `lastplayed` updates
    # whenever Kodi stops playback — including finishing an item, which
    # clears its resume position to 0 — so it's a usable proxy for the local
    # state's age regardless of the current resume position. Gating this on
    # kodi_position > 0 would let a stale remote in-progress position
    # resurrect a resume marker on an item already completed locally.
    kodi_epoch = kodi_datetime_to_epoch(kodi_item.get("lastplayed"))
    remote_epoch = iso_to_epoch(remote.get("updated_at"))
    if kodi_epoch is not None and remote_epoch is not None and kodi_epoch >= remote_epoch:
        return False
    return True


def _set_movie_watched(movie: dict[str, Any], remote: dict[str, Any]) -> None:
    params: dict[str, Any] = {
        "movieid": int(movie["movieid"]),
        "playcount": max(1, int(remote.get("playcount") or 1)),
    }
    lastplayed = iso_to_kodi_datetime(remote.get("watched_at"))
    if lastplayed:
        params["lastplayed"] = lastplayed
    _rpc("VideoLibrary.SetMovieDetails", params)


def _set_episode_watched(episode: dict[str, Any], remote: dict[str, Any]) -> None:
    params: dict[str, Any] = {
        "episodeid": int(episode["episodeid"]),
        "playcount": max(1, int(remote.get("playcount") or 1)),
    }
    lastplayed = iso_to_kodi_datetime(remote.get("watched_at"))
    if lastplayed:
        params["lastplayed"] = lastplayed
    _rpc("VideoLibrary.SetEpisodeDetails", params)


def _set_resume(kodi_item: dict[str, Any], remote: dict[str, Any]) -> None:
    position = int(remote.get("position_seconds") or 0)
    duration = int(remote.get("duration_seconds") or 0)
    resume: dict[str, Any] = {"position": position}
    if duration > 0:
        resume["total"] = duration
    if "movieid" in kodi_item:
        _rpc(
            "VideoLibrary.SetMovieDetails",
            {"movieid": int(kodi_item["movieid"]), "resume": resume},
        )
    else:
        _rpc(
            "VideoLibrary.SetEpisodeDetails",
            {"episodeid": int(kodi_item["episodeid"]), "resume": resume},
        )


def _record_failed_item(
    failed_out: set[str] | None,
    operation: str,
    remote: dict[str, Any],
) -> None:
    """Add a stable, non-sensitive identity for a failed library write.

    The service persists consecutive retry counts per identity, so a new
    failure cannot inherit an unrelated item's exhausted retry allowance.
    """
    if failed_out is None:
        return
    identity_fields = (
        "media_type",
        "punchplay_id",
        "tmdb_id",
        "imdb_id",
        "show_tmdb_id",
        "show_imdb_id",
        "season",
        "episode",
        "title",
        "year",
    )
    identity = {
        key: remote.get(key)
        for key in identity_fields
        if remote.get(key) is not None
    }
    if not identity:
        identity = {"unidentified": True}
    raw = json.dumps(
        {"operation": operation, "identity": identity},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    failed_out.add(hashlib.sha256(raw).hexdigest())


def run_pull_sync(
    api,
    *,
    apply_watched: bool,
    apply_resume: bool,
    since_ms: int | None = None,
    progress_callback=None,
    applied_out: set | None = None,
    applied_callback=None,
    failed_out: set[str] | None = None,
) -> dict[str, int]:
    """
    Fetch PunchPlay state and apply it to the Kodi library.

    Returns a summary dict:
      movies_marked / episodes_marked / resume_set / unmatched /
      already_synced / cancelled / apply_failed
    When `applied_out` is given, ("movie"|"episode", library_id) tuples are
    added for every watched state we set — live watched sync uses these to
    suppress the resulting OnUpdate echoes.
    `applied_callback`, when provided, is invoked with each tuple immediately
    after the write so echo matching uses the write time rather than the end
    of a potentially long library sync.
    When `failed_out` is given, stable hashed identities are added for every
    library write that failed so checkpoint retry counts can be scoped per
    item without persisting media metadata.
    Raises on fetch failure (callers surface the error).
    """
    path = SCROBBLE_SYNC_ENDPOINT
    if since_ms:
        path = f"{path}?since={int(since_ms)}"
    remote = api.get(path, timeout=PULL_SYNC_TIMEOUT_SECS)

    movies = remote.get("movies") or []
    episodes = remote.get("episodes") or []
    in_progress = remote.get("in_progress") or []

    summary = {
        "movies_marked": 0,
        "episodes_marked": 0,
        "resume_set": 0,
        "unmatched": 0,
        "already_synced": 0,
        "cancelled": 0,
        "apply_failed": 0,
    }
    total = (
        (len(movies) + len(episodes) if apply_watched else 0)
        + (len(in_progress) if apply_resume else 0)
    )
    if total == 0:
        return summary

    index = KodiLibraryIndex()
    done = 0

    def _tick() -> bool:
        nonlocal done
        done += 1
        if progress_callback is not None and not progress_callback(done, total):
            summary["cancelled"] = 1
            return False
        return True

    if apply_watched:
        for remote_movie in movies:
            if not _tick():
                return summary
            movie = index.find_movie(remote_movie)
            if movie is None:
                summary["unmatched"] += 1
                continue
            if int(movie.get("playcount") or 0) > 0:
                summary["already_synced"] += 1
                continue
            try:
                _set_movie_watched(movie, remote_movie)
                summary["movies_marked"] += 1
                applied_item = ("movie", int(movie["movieid"]))
                if applied_out is not None:
                    applied_out.add(applied_item)
                if applied_callback is not None:
                    applied_callback(applied_item)
            except (RuntimeError, KeyError, TypeError, ValueError) as exc:
                summary["apply_failed"] += 1
                _record_failed_item(failed_out, "movie_watched", remote_movie)
                xbmc.log(f"[PunchPlay] Pull sync movie error: {exc}", xbmc.LOGWARNING)

        for remote_episode in episodes:
            if not _tick():
                return summary
            episode = index.find_episode(remote_episode)
            if episode is None:
                summary["unmatched"] += 1
                continue
            if int(episode.get("playcount") or 0) > 0:
                summary["already_synced"] += 1
                continue
            try:
                _set_episode_watched(episode, remote_episode)
                summary["episodes_marked"] += 1
                applied_item = ("episode", int(episode["episodeid"]))
                if applied_out is not None:
                    applied_out.add(applied_item)
                if applied_callback is not None:
                    applied_callback(applied_item)
            except (RuntimeError, KeyError, TypeError, ValueError) as exc:
                summary["apply_failed"] += 1
                _record_failed_item(failed_out, "episode_watched", remote_episode)
                xbmc.log(f"[PunchPlay] Pull sync episode error: {exc}", xbmc.LOGWARNING)

    if apply_resume:
        for remote_item in in_progress:
            if not _tick():
                return summary
            if remote_item.get("media_type") == "episode":
                kodi_item = index.find_episode(remote_item)
            else:
                kodi_item = index.find_movie(remote_item)
            if kodi_item is None:
                summary["unmatched"] += 1
                continue
            if not should_apply_resume(remote_item, kodi_item):
                summary["already_synced"] += 1
                continue
            try:
                _set_resume(kodi_item, remote_item)
                summary["resume_set"] += 1
                # Resume writes never touch playcount, so they must not enter
                # the echo-suppression set — doing so would silently drop a
                # genuine manual watched-toggle made shortly afterward.
            except (RuntimeError, KeyError, TypeError, ValueError) as exc:
                summary["apply_failed"] += 1
                _record_failed_item(failed_out, "resume", remote_item)
                xbmc.log(f"[PunchPlay] Pull sync resume error: {exc}", xbmc.LOGWARNING)

    return summary

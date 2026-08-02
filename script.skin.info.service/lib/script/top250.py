"""Update IMDb Top 250 rankings in Kodi library via Trakt's official list."""
from __future__ import annotations

from typing import Dict, List, Tuple
import xbmc

from lib.kodi.client import (
    request,
    batch_request,
    ADDON,
    log,
    KODI_SET_DETAILS_METHODS,
    extract_result,
)
from lib.infrastructure.dialogs import show_ok, show_yesno, DialogProgress


def run_top250_update() -> None:
    """Update IMDb Top 250 rankings from Trakt's official list."""
    from lib.data.api.trakt import fetch_top250_list

    progress = DialogProgress()
    progress.create(ADDON.getLocalizedString(32600))
    cancelled = False

    try:
        progress.update(0, ADDON.getLocalizedString(32601))
        trakt_list = fetch_top250_list()

        if not trakt_list:
            progress.close()
            show_ok(ADDON.getLocalizedString(32600), ADDON.getLocalizedString(32607))
            return

        if progress.iscanceled():
            return

        imdb_to_rank: Dict[str, int] = {}
        tmdb_to_rank: Dict[str, int] = {}
        for item in trakt_list:
            rank = item["rank"]
            ids = item["movie"]["ids"]
            if ids.get("imdb"):
                imdb_to_rank[ids["imdb"]] = rank
            if ids.get("tmdb"):
                tmdb_to_rank[str(ids["tmdb"])] = rank

        log("General", f"Top 250: fetched {len(trakt_list)} items from Trakt", xbmc.LOGINFO)

        progress.update(25, ADDON.getLocalizedString(32602))
        resp = request("VideoLibrary.GetMovies", {
            "properties": ["title", "uniqueid", "top250"]
        })
        movies = extract_result(resp, "movies", [])

        if not movies:
            progress.close()
            show_ok(ADDON.getLocalizedString(32600), ADDON.getLocalizedString(32608))
            return

        if progress.iscanceled():
            return

        progress.update(50, ADDON.getLocalizedString(32603))
        updates: List[Tuple[int, int, str]] = []
        already_correct = 0

        for movie in movies:
            uniqueid = movie.get("uniqueid", {})
            current = movie.get("top250", 0)
            movieid = movie.get("movieid")
            title = movie.get("title", "")

            new_rank = None
            imdb_id = uniqueid.get("imdb")
            tmdb_id = uniqueid.get("tmdb")
            if imdb_id:
                new_rank = imdb_to_rank.get(imdb_id)
            if new_rank is None and tmdb_id:
                new_rank = tmdb_to_rank.get(str(tmdb_id))

            if new_rank is not None:
                if current != new_rank:
                    updates.append((movieid, new_rank, title))
                else:
                    already_correct += 1
            elif current > 0:
                updates.append((movieid, 0, title))

        progress.close()

        if not updates:
            show_ok(
                ADDON.getLocalizedString(32605),
                ADDON.getLocalizedString(32606).format(0, 0, already_correct)
            )
            return

        set_count = sum(1 for _, r, _ in updates if r > 0)
        clear_count = sum(1 for _, r, _ in updates if r == 0)

        if not show_yesno(
            ADDON.getLocalizedString(32609),
            ADDON.getLocalizedString(32610).format(set_count, clear_count, already_correct)
        ):
            return

        progress.create(ADDON.getLocalizedString(32600))
        set_method, set_id_key = KODI_SET_DETAILS_METHODS["movie"]
        updated = 0
        cleared = 0
        failed = 0
        batch_size = 50

        for batch_start in range(0, len(updates), batch_size):
            if progress.iscanceled():
                cancelled = True
                break

            batch = updates[batch_start:batch_start + batch_size]
            calls = [{
                "method": set_method,
                "params": {set_id_key: movieid, "top250": rank}
            } for movieid, rank, _ in batch]

            responses = batch_request(calls)

            for i, r in enumerate(responses):
                _, rank, title = batch[i]
                if r is not None and "error" not in r:
                    if rank > 0:
                        updated += 1
                        log("General", f"Top 250: #{rank} {title}", xbmc.LOGDEBUG)
                    else:
                        cleared += 1
                        log("General", f"Top 250: cleared {title}", xbmc.LOGDEBUG)
                else:
                    failed += 1
                    log("General", f"Top 250: failed to update {title}", xbmc.LOGWARNING)

            current = min(batch_start + batch_size, len(updates))
            percent = int(current * 100 / len(updates))
            progress.update(
                percent,
                ADDON.getLocalizedString(32604).format(current, len(updates))
            )

        progress.close()

        status = "cancelled" if cancelled else "complete"
        log(
            "General",
            f"Top 250 update {status}: {updated} set, {cleared} cleared, "
            f"{failed} failed, {already_correct} unchanged",
            xbmc.LOGINFO,
        )

        if cancelled:
            show_ok(
                ADDON.getLocalizedString(32600),
                ADDON.getLocalizedString(32611).format(updated, cleared)
            )
        else:
            show_ok(
                ADDON.getLocalizedString(32605),
                ADDON.getLocalizedString(32606).format(updated, cleared, already_correct)
            )

    except Exception as e:
        log("General", f"Top 250 update error: {e}", xbmc.LOGERROR)
        show_ok(ADDON.getLocalizedString(32600), str(e))
    finally:
        try:
            progress.close()
        except Exception:
            pass

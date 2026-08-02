"""Actor image download logic using Kodi JSON-RPC and TMDB cache."""
from __future__ import annotations

import xbmc
import xbmcvfs
from typing import Dict, List, Optional, Tuple

from lib.kodi.client import log, request, extract_result, decode_image_url, get_item_details, ADDON
from lib.kodi.utilities import extract_media_ids
from lib.data.api.utilities import tmdb_image_url
from lib.download.artwork import DownloadArtwork
from lib.actor.config import sanitize_actor_filename
from lib.infrastructure.paths import vfs_join, vfs_ensure_dir_slash, build_actors_folder_path


def get_cast_with_ids(media_type: str, dbid: int) -> Tuple[List[Dict], Dict[str, Optional[str]]]:
    """Get cast list and media IDs for a movie or tvshow from Kodi JSON-RPC."""
    if media_type not in ("movie", "tvshow"):
        return [], {}

    details = get_item_details(media_type, dbid, ["cast", "uniqueid"])
    if not isinstance(details, dict):
        return [], {}

    return details.get("cast", []), extract_media_ids(details)


def get_episode_guest_stars(tvshowid: int) -> List[Dict]:
    """Get guest stars from every episode of a TV show (may contain duplicates across episodes)."""
    response = request("VideoLibrary.GetEpisodes", {
        "tvshowid": tvshowid,
        "properties": ["cast"]
    })
    episodes = extract_result(response, "episodes")

    if not episodes:
        return []

    guest_stars: List[Dict] = []
    for episode in episodes:
        cast = episode.get("cast", [])
        guest_stars.extend(cast)

    return guest_stars


def _get_tmdb_credits(media_type: str, tmdb_id: str) -> List[Dict]:
    """Get TMDB cast list from cache or API."""
    from lib.data.api.tmdb import ApiTmdb

    api = ApiTmdb()
    data = api.get_complete_data(media_type, int(tmdb_id))

    if not data:
        return []

    credits = data.get("credits", {})
    return credits.get("cast", [])


def _match_actor_to_profile(
    actor_name: str,
    actor_role: str,
    tmdb_credits: List[Dict]
) -> Optional[str]:
    """Match Kodi actor to TMDB cast member via 4-stage matching."""
    from lib.data.api.person import (
        exact_match,
        fuzzy_role_match,
        name_only_match,
        fuzzy_name_match
    )

    match = exact_match(tmdb_credits, actor_name, actor_role)
    if match and match.get("profile_path"):
        return match["profile_path"]

    match = fuzzy_role_match(tmdb_credits, actor_name, actor_role)
    if match and match.get("profile_path"):
        return match["profile_path"]

    match = name_only_match(tmdb_credits, actor_name)
    if match and match.get("profile_path"):
        return match["profile_path"]

    match = fuzzy_name_match(tmdb_credits, actor_name)
    if match and match.get("profile_path"):
        return match["profile_path"]

    return None


def download_actor_images(
    media_type: str,
    dbid: int,
    file_path: str,
    show_path: Optional[str] = None,
    existing_file_mode: str = "skip",
    abort_flag=None
) -> Tuple[int, int, int]:
    """Download actor images for a single media item.

    Falls back to Kodi thumbnail URLs when TMDB match fails.
    Returns (downloaded, skipped, failed) counts.
    """
    downloaded = 0
    skipped = 0
    failed = 0
    monitor = xbmc.Monitor()

    cast, media_ids = get_cast_with_ids(media_type, dbid)

    if media_type == "tvshow" and ADDON.getSettingBool("download.include_guest_stars"):
        guest_stars = get_episode_guest_stars(dbid)
        if guest_stars:
            log(
                "Artwork",
                f"Got {len(guest_stars)} guest star entries from episodes",
                xbmc.LOGDEBUG,
            )
            cast = cast + guest_stars

    if not cast:
        log("Artwork", f"No cast found for {media_type} {dbid}", xbmc.LOGDEBUG)
        return downloaded, skipped, failed

    actors_folder = build_actors_folder_path(media_type, file_path, show_path)
    if not actors_folder:
        log(
            "Artwork",
            f"Could not determine .actors folder for {media_type} {dbid}",
            xbmc.LOGWARNING,
        )
        return downloaded, skipped, failed

    actors_folder_check = vfs_ensure_dir_slash(actors_folder)
    if not xbmcvfs.exists(actors_folder_check):
        xbmcvfs.mkdirs(actors_folder)
        if not xbmcvfs.exists(actors_folder_check):
            log("Artwork", f"Failed to create .actors folder: {actors_folder}", xbmc.LOGWARNING)
            return downloaded, skipped, failed
        log("Artwork", f"Created .actors folder: {actors_folder}", xbmc.LOGDEBUG)

    tmdb_credits: List[Dict] = []
    tmdb_id = media_ids.get("tmdb")
    if tmdb_id:
        tmdb_credits = _get_tmdb_credits(media_type, tmdb_id)
        if tmdb_credits:
            log("Artwork", f"Got {len(tmdb_credits)} cast members from TMDB", xbmc.LOGDEBUG)

    downloader = DownloadArtwork()
    seen_filenames: set = set()

    for actor in cast:
        if monitor.abortRequested():
            break
        if abort_flag and abort_flag.is_requested():
            break

        name = actor.get("name", "").strip()
        if not name:
            continue

        role = actor.get("role", "").strip()

        filename = sanitize_actor_filename(name, "")
        if filename in seen_filenames:
            log("Artwork", f"Duplicate actor filename '{filename}', skipping", xbmc.LOGDEBUG)
            skipped += 1
            continue
        seen_filenames.add(filename)

        local_path = vfs_join(actors_folder, filename)

        profile_path = _match_actor_to_profile(name, role, tmdb_credits) if tmdb_credits else None
        if profile_path:
            url = tmdb_image_url(profile_path)
            success, error, _, _ = downloader.download_artwork(
                url=url,
                local_path=local_path,
                existing_file_mode=existing_file_mode,
            )
            if success:
                downloaded += 1
                log("Artwork", f"Downloaded actor image from TMDB: {name}", xbmc.LOGDEBUG)
                continue
            elif error is None:
                skipped += 1
                continue

        thumbnail = actor.get("thumbnail", "").strip()
        if thumbnail:
            decoded_url = decode_image_url(thumbnail)
            if decoded_url.startswith("http"):
                success, error, _, _ = downloader.download_artwork(
                    url=decoded_url,
                    local_path=local_path,
                    existing_file_mode=existing_file_mode,
                )
                if success:
                    downloaded += 1
                    log("Artwork", f"Downloaded actor image from Kodi URL: {name}", xbmc.LOGDEBUG)
                    continue
                elif error is None:
                    skipped += 1
                    continue
                else:
                    failed += 1
                    log(
                        "Artwork",
                        f"Failed to download actor image for '{name}': {error}",
                        xbmc.LOGWARNING,
                    )
                    continue

        log("Artwork", f"No image source for actor '{name}'", xbmc.LOGDEBUG)
        skipped += 1

    return downloaded, skipped, failed

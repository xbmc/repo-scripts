"""Actor image download logic using Kodi JSON-RPC and TMDB cache."""
from __future__ import annotations

import xbmc
import xbmcvfs
from typing import Dict, List, Optional, Tuple

from lib.kodi.client import log, request, extract_result, decode_image_url, get_item_details, ADDON
from lib.kodi.utilities import extract_media_ids
from lib.data.api.utilities import tmdb_image_url
from lib.data.api.person import match_credit
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
    """Get the cast from the item's complete TMDB record."""
    from lib.data.api.person import tmdb_cast
    from lib.data.api.tmdb import ApiTmdb

    return tmdb_cast(ApiTmdb().get_complete_data(media_type, int(tmdb_id)), media_type)


def download_actor_images(media_type: str, dbid: int, file_path: str,
                          existing_file_mode: str = "skip",
                          downloader: Optional[DownloadArtwork] = None) -> int:
    """Download actor images, Kodi's thumbnail on a TMDB miss; returns how many were written."""
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
        return 0

    actors_folder = build_actors_folder_path(media_type, file_path)
    if not actors_folder:
        log(
            "Artwork",
            f"Could not determine .actors folder for {media_type} {dbid}",
            xbmc.LOGWARNING,
        )
        return 0

    actors_folder_check = vfs_ensure_dir_slash(actors_folder)
    if not xbmcvfs.exists(actors_folder_check):
        xbmcvfs.mkdirs(actors_folder)
        if not xbmcvfs.exists(actors_folder_check):
            log("Artwork", f"Failed to create .actors folder: {actors_folder}", xbmc.LOGWARNING)
            return 0
        log("Artwork", f"Created .actors folder: {actors_folder}", xbmc.LOGDEBUG)

    tmdb_credits: List[Dict] = []
    tmdb_id = media_ids.get("tmdb")
    if tmdb_id:
        tmdb_credits = _get_tmdb_credits(media_type, tmdb_id)
        if tmdb_credits:
            log("Artwork", f"Got {len(tmdb_credits)} cast members from TMDB", xbmc.LOGDEBUG)

    own_downloader = downloader is None
    active = downloader or DownloadArtwork()
    seen_filenames: set = set()
    downloaded = 0

    try:
        for actor in cast:
            if monitor.abortRequested():
                break

            name = actor.get("name", "").strip()
            if not name:
                continue

            filename = sanitize_actor_filename(name, "")
            if filename in seen_filenames:
                continue
            seen_filenames.add(filename)

            local_path = vfs_join(actors_folder, filename)
            sources = []
            match = match_credit(tmdb_credits, name, actor.get("role", "").strip(),
                                 lambda credit: bool(credit.get("profile_path")))
            if match:
                sources.append(("TMDB", tmdb_image_url(match["profile_path"])))
            thumbnail = decode_image_url(actor.get("thumbnail", "").strip())
            if thumbnail.startswith("http"):
                sources.append(("Kodi URL", thumbnail))
            if not sources:
                log("Artwork", f"No image source for actor '{name}'", xbmc.LOGDEBUG)
                continue

            for source, url in sources:
                success, error, _, _ = active.download_artwork(
                    url=url,
                    local_path=local_path,
                    existing_file_mode=existing_file_mode,
                )
                if success:
                    downloaded += 1
                    log("Artwork", f"Downloaded actor image from {source}: {name}",
                        xbmc.LOGDEBUG)
                if success or error is None:
                    break
                log("Artwork", f"Failed to download actor image for '{name}' from {source}: "
                    f"{error}", xbmc.LOGWARNING)
    finally:
        if own_downloader:
            active.close()

    return downloaded

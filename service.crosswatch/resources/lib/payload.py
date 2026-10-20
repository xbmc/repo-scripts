# SPDX-License-Identifier: GPL-2.0-only
"""Domain event to wire format.

The only file that knows the payload shape. It implements docs/contract.md on
crosswatch-app/kodi-addon; a spelling change there lands here and nowhere else. It is not a
firewall against every contract change: a change to what the addon must resolve, such as one
event per viewer, reaches the event model too.

Two shapes share one entry point. A playback event carries media and a session; a ping
carries neither, and is a separate type precisely so that nothing handling playback has to
reason about a media that is absent.

Episodes are keyed on show ids plus season and episode number, because most episodes carry
no usable episode id.

A rate carries the stop's media block without the playback fields (contract, Ratings): its
score is about the item, not about where playback was.
"""

from __future__ import annotations

from typing import Any

from resources.lib.models import Device, MediaItem, PingEvent, PlaybackEvent

PAYLOAD_VERSION = 1

# The contract's episode spelling: the show's ids are suffixed, the episode's are bare.
_SHOW_SUFFIX = "_show"


def build_payload(event: PlaybackEvent | PingEvent, device: Device) -> dict[str, Any]:
    body: dict[str, Any] = {
        "version": PAYLOAD_VERSION,
        "event_id": event.event_id,
        "sent_at": event.sent_at,
        "device": {"id": device.id, "name": device.name},
        "viewers": list(event.viewers),
    }
    if device.addon_version:
        body["addon_version"] = device.addon_version

    if isinstance(event, PingEvent):
        body["event"] = "ping"
        if event.pkc_skipped:
            body["pkc_skipped"] = event.pkc_skipped
        return body

    body["event"] = event.kind
    body["session_id"] = event.session_id
    body["media"] = _media(event)
    if event.kind == "rate":
        body["rating"] = event.rating
    elif event.viewers_source:
        body["viewers_source"] = event.viewers_source
    return body


def _ids(media: MediaItem) -> dict[str, str]:
    """One flat map. Show ids are suffixed so an episode can carry both sets at once."""
    if media.media_type != "episode":
        return dict(media.show_ids)
    out = {f"{name}{_SHOW_SUFFIX}": value for name, value in media.show_ids.items()}
    out.update(media.episode_ids)
    return out


def _media(event: PlaybackEvent) -> dict[str, Any]:
    media = event.media
    out: dict[str, Any] = {
        "source": media.source,
        "type": media.media_type,
        "title": media.title,
        "year": media.year,
    }
    if media.media_type == "episode":
        out["season"] = media.season
        out["episode"] = media.episode
        if media.episode_title:
            out["episode_title"] = media.episode_title
    ids = _ids(media)
    if ids:
        out["ids"] = ids
    if event.kind == "rate":
        if media.plex_rating_key:
            out["plex_rating_key"] = media.plex_rating_key
        return out

    # Omitted rather than zeroed when the duration was never known. Kodi reports a duration
    # of zero for a stream of unknown length, and a percent of 0.0 is indistinguishable from
    # having watched nothing, which the receiver discards and which overwrites a real resume
    # point downstream. The contract requires percent only when the duration is known.
    if event.percent is not None:
        out["percent"] = event.percent
    if event.position_ms is not None:
        out["position_ms"] = event.position_ms
    if event.duration_ms is not None:
        out["duration_ms"] = event.duration_ms
    if event.completed:
        out["completed"] = True

    if media.file:
        out["file"] = media.file
    if media.plex_rating_key:
        out["plex_rating_key"] = media.plex_rating_key
    return out

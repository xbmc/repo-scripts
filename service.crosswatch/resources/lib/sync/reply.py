# SPDX-License-Identifier: GPL-2.0-only
"""CrossWatch's library_sync block in a ping reply, and the ticket a ping carries.

A leaf module: models.PingEvent carries a PingTicket, so nothing here may import from the
rest of the add-on.

The reply is the only place the add-on learns whether sync is on for this device, which
viewers CrossWatch has mapped, and the last upload number CrossWatch saw per viewer. A
missing block or an unsupported version means sync is off (contract, Ping).

Log events: none.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

SUPPORTED_VERSION = 1


def connection_id(base_url: str) -> str:
    """The paired address as scheme, host and path, without query or credentials.

    Used only to tell whether Start was run for the current pairing; the sync record is keyed
    by viewer, because CrossWatch counts uploads per device and viewer, not per address.
    """
    parts = urlsplit((base_url or "").strip())
    scheme = parts.scheme.lower()
    host = parts.netloc.rsplit("@", 1)[-1].lower()
    # The same server spelled with or without its default port is the same pairing.
    default = {"http": ":80", "https": ":443"}.get(scheme)
    if default and host.endswith(default):
        host = host[: -len(default)]
    return f"{scheme}://{host}{parts.path.rstrip('/')}"


@dataclass(frozen=True)
class ReplyViewer:
    instance: str
    upload_seq: int
    # The seq CrossWatch gives this viewer's next queued change.
    next_change: int = 0
    # True from a completed full upload until the pair run it started has finished; steps that
    # depend on the services' data (sending existing ratings) wait for it to turn false.
    run_pending: bool = False


@dataclass(frozen=True)
class SyncReply:
    enabled: bool
    reason: str | None
    viewers: dict[str, ReplyViewer]
    queue_pending: int


@dataclass(frozen=True)
class PingTicket:
    """What a ping knew when it went out: per viewer, the upload epoch then current.

    A reply is judged against uploads only when no upload started or ended since its ping
    was built, so a reply that crossed one is not read as CrossWatch losing state.
    """

    sent_at: float
    epochs: dict[str, int] = field(default_factory=dict)
    # The connection_id the block was built for. The reporter queue sends what it holds to
    # whatever server is paired when an event is taken, so a ping built for one pairing can
    # reach the next one; the reporter drops the block there.
    connection: str = ""
    # Whether the block asked for sync (its "enabled"), so the reply can be judged against
    # what this device said.
    enabled: bool = False


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def parse_reply(block: Mapping[str, Any] | None) -> SyncReply | None:
    if not isinstance(block, Mapping) or _int(block.get("version")) != SUPPORTED_VERSION:
        return None
    viewers: dict[str, ReplyViewer] = {}
    rows = block.get("viewers")
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        viewer_id = row.get("viewer_id")
        instance = row.get("instance")
        if not isinstance(viewer_id, str) or not viewer_id or not isinstance(instance, str) or not instance:
            continue
        viewers[viewer_id] = ReplyViewer(
            instance=instance,
            upload_seq=max(_int(row.get("upload_seq")) or 0, 0),
            next_change=max(_int(row.get("next_change")) or 0, 0),
            run_pending=row.get("run_pending") is True,
        )
    reason = block.get("reason")
    return SyncReply(
        enabled=block.get("enabled") is True,
        reason=reason if isinstance(reason, str) and reason else None,
        viewers=viewers,
        queue_pending=max(_int(block.get("queue_pending")) or 0, 0),
    )

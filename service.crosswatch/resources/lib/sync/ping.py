# SPDX-License-Identifier: GPL-2.0-only
"""The library_sync block the add-on's ping carries, and what a ping reply means for pausing.

The ping is how CrossWatch learns which device syncs a library and which viewers it has, and
the only way to release this device as the sync device: CrossWatch releases it on a block
with enabled false and on nothing else (contract, Setup). So the block is sent on every ping
once Start ran for the current pairing, enabled or not, and never before.

The block's JSON-RPC lookups run only after Start: a household that never set up library
sync sends the ping it always sent.

Log events: none.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal

from resources.lib.config import Settings
from resources.lib.kodi import KodiApi
from resources.lib.models import Viewer
from resources.lib.storage import ViewerStore
from resources.lib.sync.files import StartedFile, read_started
from resources.lib.sync.library_id import kodi_version, library_id
from resources.lib.sync.reply import SUPPORTED_VERSION, PingTicket, SyncReply, connection_id

BlockState = Literal["absent", "enabled", "disabled"]
# Why the worker pauses this device: another device is the sync device, or this one sent
# enabled false after its household turned sync off.
PauseReason = Literal["not_sync_device", "turned_off"]


def block_state(started: StartedFile | None, current_connection: str, sync_enabled: bool, device_id: str) -> BlockState:
    """Whether the ping carries a block, and whether it asks for sync.

    A paired address Start was not run for gets no block: its viewers are new to that
    CrossWatch, and the household confirms them through Start first.

    An id other than the one CrossWatch bound asks for nothing until Start runs again (it
    clears bound_device): the id setting was edited, or this install's files were copied to
    another box, and either could otherwise take the library whenever no device holds it.
    """
    if started is None or started.connection != current_connection:
        return "absent"
    if started.paused or (started.bound_device and started.bound_device != device_id):
        return "disabled"
    return "enabled" if sync_enabled else "disabled"


def library_sync_block(
    enabled: bool, viewers: list[Viewer], library_id: str, kodi_version: str, jsonrpc_version: str
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "version": SUPPORTED_VERSION,
        "enabled": enabled,
        # A viewer gets its sync id before Start; one without it has nothing to sync yet.
        "viewers": [{"viewer_id": v.sync_id, "name": v.name} for v in viewers if v.sync_id],
        "kodi_version": kodi_version,
        "jsonrpc_version": jsonrpc_version,
    }
    # Left out rather than sent empty when the lookup failed: CrossWatch keeps its last value
    # for a missing key, while a changed one makes every viewer wait for a new full upload.
    if library_id:
        block["library_id"] = library_id
    return block


def jsonrpc_version(kodi: KodiApi) -> str:
    """JSON-RPC's version as major.minor.patch, or "" when Kodi doesn't answer."""
    try:
        version = kodi.jsonrpc("JSONRPC.Version").get("version")
    except Exception:
        return ""
    if not isinstance(version, Mapping):
        return ""
    parts = [version.get(key) for key in ("major", "minor", "patch")]
    if not all(isinstance(p, int) and not isinstance(p, bool) for p in parts):
        return ""
    return ".".join(str(p) for p in parts)


def pause_reason(block: Mapping[str, Any] | None, reply: SyncReply | None, *, turned_off: bool) -> PauseReason | None:
    """Whether a judged ping should pause this device until its household runs Start again.

    turned_off is true only when the worker saw sync_enabled go from true to false. Start
    turns the setting on before it writes the started file, and the service reloads settings
    on its own schedule, so a ping can carry enabled false between the two; pausing on that
    would undo the Start that was just run.

    A paused device keeps sending enabled false, so it never takes a library over from
    another device by itself. A 403 from a sync request never pauses: CrossWatch answers an
    unbound device the same way.
    """
    if block is None or reply is None:
        return None
    if reply.reason == "not_sync_device":
        return "not_sync_device"
    if block.get("enabled") is False and turned_off:
        return "turned_off"
    return None


def device_id_changed(reply: SyncReply | None, device_id: str, started: StartedFile | None) -> bool:
    """Whether CrossWatch still has this install's old device id as the sync device.

    Judged from CrossWatch's answer rather than a local comparison: a different id alone
    doesn't say whether the old one is still bound, or whether it ever was. Nothing is
    released automatically either way, because a copy of this install's data on another
    device would release the real sync device under the shared id.
    """
    return (
        reply is not None
        and reply.reason == "not_sync_device"
        and started is not None
        and bool(started.bound_device)
        and started.bound_device != device_id
    )


class PingBlocks:
    """Builds each ping's block and ticket, for the controller.

    epochs is the engine's published upload epochs, read through a late-bound callable so a
    ping built before the engine exists carries a ticket with none. device_id is the id the
    reporter sends under, which a settings change can replace.
    """

    def __init__(
        self,
        kodi: KodiApi,
        viewer_store: ViewerStore,
        started_path: str,
        clock: Callable[[], float],
        device_id: Callable[[], str],
        epochs: Callable[[], Mapping[str, int]] = dict,
    ) -> None:
        self._kodi = kodi
        self._viewers = viewer_store
        self._started_path = started_path
        self._clock = clock
        self._device_id = device_id
        self._epochs = epochs

    def __call__(self, settings: Settings) -> tuple[dict[str, Any], PingTicket] | None:
        started = read_started(self._started_path)
        connection = connection_id(settings.webhook_base_url)
        state = block_state(started, connection, settings.sync_enabled, self._device_id())
        if state == "absent":
            return None
        block = library_sync_block(
            enabled=state == "enabled",
            viewers=self._viewers.viewers(),
            library_id=library_id(self._kodi),
            kodi_version=kodi_version(self._kodi),
            jsonrpc_version=jsonrpc_version(self._kodi),
        )
        ticket = PingTicket(
            sent_at=self._clock(), epochs=dict(self._epochs()), connection=connection, enabled=state == "enabled"
        )
        return block, ticket

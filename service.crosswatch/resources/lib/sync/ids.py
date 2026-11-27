# SPDX-License-Identifier: GPL-2.0-only
"""The sync id each viewer is known by in library sync.

CrossWatch keys a viewer's sync state (its upload numbers, its queue, what it already
applied) on the viewer_id the add-on sends. A new id is a stranger to it, so an id is given
once and never changed: not on a rename, not on Start, and a viewer removed and added back
under the same name gets its old id from the store's retired list. The contract allows
[a-z0-9-] ids; the "kv-" prefix only makes them recognisable in CrossWatch's logs.

Log events: sync.ids.assigned (count).
"""
from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from dataclasses import replace

from resources.lib.log import get_logger
from resources.lib.models import Viewer
from resources.lib.storage import JsonViewerStore

_log = get_logger("sync")

SYNC_ID_PATTERN = re.compile(r"^[a-z0-9-]{8,40}$")


def new_sync_id() -> str:
    return "kv-" + secrets.token_hex(6)


def ensure_sync_ids(store: JsonViewerStore, make_id: Callable[[], str] = new_sync_id) -> list[Viewer]:
    """Every viewer with a sync id, saved; the list as it now stands.

    Under the store's lock, because the Viewers screen in another interpreter saves the same
    file: an id given here must not be lost to a save of a list read before it.
    """
    with store.locked():
        viewers = store.viewers()
        used = {v.sync_id for v in viewers if v.sync_id}
        # A second viewer carrying the same id (a hand-edited file) gets a new one.
        kept: set[str] = set()
        out: list[Viewer] = []
        assigned = 0
        for viewer in viewers:
            if viewer.sync_id and SYNC_ID_PATTERN.fullmatch(viewer.sync_id) and viewer.sync_id not in kept:
                kept.add(viewer.sync_id)
                out.append(viewer)
                continue
            sync_id = store.retired_id(viewer.name)
            if not sync_id or sync_id in used or not SYNC_ID_PATTERN.fullmatch(sync_id):
                sync_id = make_id()
                while sync_id in used:
                    sync_id = make_id()
            used.add(sync_id)
            out.append(replace(viewer, sync_id=sync_id))
            assigned += 1
        if assigned:
            store.save(out)
            _log.info("sync.ids.assigned", count=assigned)
            # What is on disk, not what was meant to be: an id that failed to save must not
            # be uploaded under and then lost.
            return store.viewers()
        return out

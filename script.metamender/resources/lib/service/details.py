"""Service side of the item details window: open it for a library item,
and restore or unlock a field from it.

Logging:
    Logger: 'details'
    Key events:
        - details.open_invalid (WARNING): Details asked for an unsupported
          type or a bad id
        - details.open_notfound (WARNING): The item is not in the library
        - details.locked (INFO): Restore or Unlock skipped, a scan is running
        - details.restored / details.restore_changed / details.restore_failed
          (cause=lock: the lock could not be saved; cause=kodi: Kodi refused)
        - details.rekey_failed (WARNING): A show title was restored but its
          episode rows could not be re-keyed to it
        - details.unlocked (INFO): only once the unlock is committed
        - details.error (ERROR): Reading the item or a window action raised
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from resources.lib.data import kodi
from resources.lib.data.identity import compute_identity
from resources.lib.data.media_types import EPISODE, MOVIE, TVSHOW, MediaType
from resources.lib.data.presets import load_preset
from resources.lib.data.sources import (
    kodi_ui_language,
    load_source_config,
    match_source,
)
from resources.lib.data.tracker import REASON_LOCKED, TrackerDB
from resources.lib.engine.scan import candidate_fields, item_fields
from resources.lib.engine.scanctx import holds_written_value
from resources.lib.service import actions
from resources.lib.service.actions import _init_logging
from resources.lib.service.daemon import (
    _get_db_path,
    _get_sources_config_path,
    _load_settings,
)
from resources.lib.service.lock import acquire_scan_lock, release_scan_lock
from resources.lib.ui.setup_window import language_name
from resources.lib.utils import get_logger, lang, notify

if TYPE_CHECKING:
    from resources.lib.ui.details_model import DetailRow

log = get_logger('details')

_DBTYPE_TO_MEDIA_TYPE = {"movie": MOVIE, "episode": EPISODE, "tvshow": TVSHOW}
# Certifications are scanned for movies and shows only (scan._cert_config).
_CERT_TYPES = frozenset({"movie", "tvshow"})

# The rating slots are rebuilt from several providers on every scan, so a
# single kept value is neither meaningful to restore nor stable to lock.
RESTORABLE_EXCLUDED = frozenset({"rating", "votes", "ratings"})

RESTORED = "restored"
KEPT = "kept"
CHANGED = "changed"
NOT_RESTORABLE = "not_restorable"
LOCK_FAILED = "lock_failed"
FAILED = "failed"
EPISODES_NOT_MOVED = "episodes_not_moved"


def can_restore(
    field: str, current: Any, fs: dict[str, Any], keep: dict[str, Any]
) -> bool:
    """An original is kept and Kodi still holds MetaMender's own value.

    ``keep`` is the item's get_keep() map; scanctx.holds_written_value
    decides whether the value is MetaMender's own.
    """
    if field in RESTORABLE_EXCLUDED:
        return False
    entry = keep.get(field) or {}
    if not entry.get("has_original"):
        return False
    return holds_written_value(field, current, fs, entry)


def restore_field(
    tracker: TrackerDB, media_type: MediaType, kodi_id: int, identity: str, field: str
) -> str:
    """Lock the field, then write the kept original back to Kodi.

    Kodi is re-read first: the window may have been open while the user or a
    scraper changed the value, and overwriting that would lose it. The lock
    is committed before Kodi is written, so a value Kodi now holds is never
    unprotected; a lock that cannot be saved writes nothing. Returns
    RESTORED, NOT_RESTORABLE (a rating field, nothing written), CHANGED
    (nothing written), LOCK_FAILED (nothing written), FAILED (Kodi refused
    the write; the lock is put back as it was) or EPISODES_NOT_MOVED (a show
    title was restored, but its episode rows keep the old key and start
    over at the next scan). Provenance is left alone: the field now holds
    the original, not a value MetaMender wrote.
    """
    if field in RESTORABLE_EXCLUDED:
        return NOT_RESTORABLE
    keep = tracker.get_keep(media_type.name, identity)
    fs = tracker.get_field_status_map(media_type.name, identity).get(field, {})
    item = kodi.get_item_by_id(media_type, kodi_id) or {}
    if not can_restore(field, item.get(field), fs, keep):
        log.info(
            "Restore refused, value is no longer MetaMender's",
            event="details.restore_changed", identity=identity,
            media_type=media_type.name, field=field,
        )
        return CHANGED
    was_locked = bool(keep[field].get("locked"))
    if not _save_lock(tracker, media_type, identity, field, True):
        log.warning(
            "The lock could not be saved, nothing restored",
            event="details.restore_failed", identity=identity,
            media_type=media_type.name, field=field, cause="lock",
        )
        return LOCK_FAILED
    original = keep[field]["original"]
    current_title = str(item.get("title") or "")
    if not kodi.update_item(kodi_id, media_type, current_title, **{field: original}):
        log.warning(
            "Kodi refused the restore",
            event="details.restore_failed", identity=identity,
            media_type=media_type.name, field=field, cause="kodi",
        )
        if not was_locked:
            _save_lock(tracker, media_type, identity, field, False)
        return FAILED
    tracker.record_field_reason(media_type.name, identity, field, REASON_LOCKED)
    if media_type.name == "tvshow" and field == "title" and current_title and original:
        # Episodes are keyed on their show's title, as after a scan's title
        # write; without the re-key they lose their rows and locks. It
        # commits the reason with it.
        if tracker.rename_show_episodes(current_title, str(original)) is None:
            # The tracker undid the partial re-key; the reason is still
            # pending, and losing it costs only the displayed reason.
            _commit_reason(tracker, media_type, identity, field)
            log.warning(
                "Original restored, but the episode rows kept the old show title",
                event="details.rekey_failed", identity=identity,
                media_type=media_type.name, field=field,
            )
            return EPISODES_NOT_MOVED
    else:
        _commit_reason(tracker, media_type, identity, field)
    log.info(
        "Original restored and field locked",
        event="details.restored", identity=identity,
        media_type=media_type.name, field=field,
    )
    return RESTORED


def _commit_reason(
    tracker: TrackerDB, media_type: MediaType, identity: str, field: str
) -> None:
    """Commit the "locked" reason after a restore. A failure is logged and
    swallowed: the lock is saved and Kodi holds the original, so the user is
    told what happened to those, not a database error."""
    try:
        tracker.commit()
    except sqlite3.Error:
        log.exception("Failed to record the locked reason", event="details.error",
                      identity=identity, media_type=media_type.name, field=field)


def _save_lock(
    tracker: TrackerDB, media_type: MediaType, identity: str, field: str, locked: bool
) -> bool:
    """Set the lock flag and commit it; False, with nothing kept, when either
    failed."""
    try:
        if tracker.set_locked(media_type.name, identity, field, locked):
            tracker.commit()
            return True
    except sqlite3.Error:
        log.exception("Failed to save the lock", event="details.error",
                      identity=identity, media_type=media_type.name, field=field)
    tracker.rollback()
    return False


def keep_field(
    tracker: TrackerDB, media_type: MediaType, identity: str, field: str
) -> str:
    """Lock the field as Kodi holds it now, so MetaMender leaves it alone
    (Keep this value): the way to keep a hand edit, which has no original to
    restore. Kodi is not written. Returns KEPT, NOT_RESTORABLE (a rating
    field, nothing saved) or LOCK_FAILED (nothing saved). The "locked"
    reason is recorded with the lock, so an unlock later shows the field as
    due again."""
    if field in RESTORABLE_EXCLUDED:
        return NOT_RESTORABLE
    try:
        saved = tracker.set_locked(media_type.name, identity, field, True)
        if saved:
            # A reason that cannot be recorded (the tracker logs it) costs
            # only the displayed reason; the lock is what matters.
            tracker.record_field_reason(media_type.name, identity, field, REASON_LOCKED)
            tracker.commit()
    except sqlite3.Error:
        log.exception("Failed to save the lock", event="details.error",
                      identity=identity, media_type=media_type.name, field=field)
        saved = False
    if not saved:
        tracker.rollback()
        log.warning(
            "The lock could not be saved, field not kept",
            event="details.keep_failed", identity=identity,
            media_type=media_type.name, field=field,
        )
        return LOCK_FAILED
    log.info(
        "Field kept as it is and locked",
        event="details.kept", identity=identity,
        media_type=media_type.name, field=field,
    )
    return KEPT


def unlock_field(
    tracker: TrackerDB, media_type: MediaType, identity: str, field: str
) -> bool:
    """Let MetaMender update the field again from the next scan on; the kept
    original stays. The field may be settled, and a lock flag alone would
    leave it settled forever, so it is made due at the next scan. False when
    the tracker could not save it; the field then stays locked."""
    try:
        saved = (tracker.set_locked(media_type.name, identity, field, False)
                 and tracker.forget_field_fingerprint(media_type.name, identity, field))
        if saved:
            tracker.commit()
    except sqlite3.Error:
        log.exception("Failed to save the unlock", event="details.error",
                      identity=identity, media_type=media_type.name, field=field)
        saved = False
    if not saved:
        tracker.rollback()
        return False
    log.info(
        "Field unlocked",
        event="details.unlocked", identity=identity,
        media_type=media_type.name, field=field,
    )
    return True


@dataclass
class DetailsView:
    """What the window shows: the item, the header's short line, the rows."""

    heading: str
    sub: str
    rows: list[DetailRow]


def _read_identity(
    tracker: TrackerDB, media_type: MediaType, item: dict[str, Any], kodi_id: int
) -> tuple[str, str]:
    """(the key the item's rows are under now, the key the scan uses), found
    the way scan._tracker_identity finds it but without its writes: opening
    the window must change nothing, so a row the next scan would adopt is
    read under its current identity. The two differ only for such a row."""
    identity = compute_identity(item, media_type)
    own = "{}|{}".format(identity, item.get("file", ""))
    if tracker.get_item(media_type.name, own) is not None:
        return own, own
    # An id written back to Kodi changes the identity the item computes; the
    # row stays under the old one until the next scan adopts it. Restore and
    # Unlock on the old identity are carried along by that adoption.
    adoptable = tracker.adoptable_identity(media_type.name, identity, kodi_id)
    if adoptable is not None:
        return adoptable, identity
    row = tracker.get_item(media_type.name, identity)
    holder = row.get("kodi_id") if row else None
    if holder is None or holder == kodi_id:
        return identity, identity
    other = kodi.get_item_by_id(media_type, holder)
    if other and compute_identity(other, media_type) == identity:
        return own, own
    return identity, identity


def certifications_on(media_type: MediaType, enabled_fields: frozenset[str]) -> bool:
    """Certifications are switched on for this media type."""
    return "mpaa" in enabled_fields and media_type.name in _CERT_TYPES


def cert_country_usable(cert_country: str | None) -> bool:
    """The configured country has a usable preset, as scan._cert_config
    requires. Not logged: the scan reports an unusable preset, and the
    window asks on every view."""
    return bool(cert_country) and load_preset(str(cert_country), report=False) is not None


def managed_fields(
    media_type: MediaType, enabled_fields: frozenset[str], cert_usable: bool,
    identity: str,
) -> list[str]:
    """The fields a scan manages for this item under the current settings.
    ``identity`` is the key the scan uses (after adopting a row);
    ``cert_usable`` is cert_country_usable() for the configured country."""
    fields = candidate_fields(media_type, enabled_fields)
    if certifications_on(media_type, enabled_fields) and cert_usable:
        fields = sorted(set(fields) | {"mpaa"})
    return item_fields(fields, media_type, identity)


def _shown_fields(
    media_type: MediaType, managed: list[str], fs_map: dict[str, dict[str, Any]],
    keep: dict[str, dict[str, Any]],
) -> list[str]:
    """The managed fields, and a field the user locked or just unlocked
    though the scan no longer manages it, so its lock stays in reach."""
    known = media_type.backfill_fields | ({"mpaa"} if media_type.name in _CERT_TYPES
                                          else set())
    held = {f for f, e in keep.items() if e.get("locked")}
    held |= {f for f, fs in fs_map.items() if fs.get("last_reason") == REASON_LOCKED}
    return sorted(set(managed) | ((held & known) - RESTORABLE_EXCLUDED))


def _heading(media_type: MediaType, item: dict[str, Any]) -> str:
    if media_type.name == "episode":
        return lang(32585).format(
            item.get("showtitle", ""), item.get("season", 0), item.get("episode", 0)
        )
    return str(item.get("title") or "")


class DetailsSession:
    """One item in the details window: reads it for each view and runs the
    window's buttons. ``identity`` is the tracker key of the last load."""

    def __init__(self, dbtype: str, media_type: MediaType, kodi_id: int) -> None:
        self.dbtype = dbtype
        self.media_type = media_type
        self.kodi_id = kodi_id
        self.identity = ""

    def load(self) -> DetailsView | None:
        """Read the item from Kodi and the tracker; None when it is gone.
        Reads only."""
        # details_model imports this module (can_restore), so it is imported
        # here rather than at the top.
        from resources.lib.ui.details_model import build_rows, header_line

        item = kodi.get_item_by_id(self.media_type, self.kodi_id)
        if not item:
            return None
        settings = _load_settings()
        config = load_source_config(_get_sources_config_path())
        source = match_source(item.get("file", ""), config.get("sources", []))
        # The scan's language for the folder (scan.run_scan): the folder's
        # own, else the configured default; with neither, the folder has no
        # language and text is filled in Kodi's interface language.
        code = source.get("language") or config.get("default_language") or ""
        folder = language_name(code) if code else ""
        text_language = folder or language_name(kodi_ui_language())
        tracker = TrackerDB(_get_db_path())
        try:
            identity, scan_identity = _read_identity(
                tracker, self.media_type, item, self.kodi_id)
            item_row = tracker.get_item(self.media_type.name, identity)
            fs_map = tracker.get_field_status_map(self.media_type.name, identity)
            keep = tracker.get_keep(self.media_type.name, identity)
        finally:
            tracker.close()
        self.identity = identity
        enabled = settings["enabled_fields"]
        cert_usable = cert_country_usable(settings.get("cert_country"))
        managed = managed_fields(self.media_type, enabled, cert_usable, scan_identity)
        rows = build_rows(
            self.media_type, item, item_row, fs_map, keep, date.today().isoformat(),
            language=text_language,
            fields=_shown_fields(self.media_type, managed, fs_map, keep),
            managed=managed,
            cert_country_missing=certifications_on(self.media_type, enabled) and not cert_usable,
            threshold_days=settings["stale_threshold_days"],
        )
        return DetailsView(
            _heading(self.media_type, item), header_line(item_row, fs_map, folder), rows
        )

    def reload(self) -> DetailsView | None:
        """load(), with a missing item or a failed read told to the user and
        logged here; None then, and the window has nothing to show."""
        try:
            view = self.load()
        except Exception:
            log.exception("Reading the item's details failed", event="details.error",
                          media_type=self.media_type.name, item_id=self.kodi_id)
            notify(lang(32592))  # Could not read this item's details
            return None
        if view is None:
            log.warning("Details could not find the item", event="details.open_notfound",
                        media_type=self.media_type.name, item_id=self.kodi_id)
            notify(lang(32345))  # Item not found
        return view

    def update_now(self) -> None:
        """The context menu's Update now: one movie or episode, or a show's
        refresh with its own progress window. It takes the scan lock and
        reports the result itself."""
        actions.update_now(self.dbtype, str(self.kodi_id))

    def run_action(self, row: DetailRow) -> None:
        """The row's button: restore the original, keep the value as it is,
        or unlock the field, each under the scan lock. A running scan writes the tracker for long
        stretches, so the press says so at once rather than waiting on the
        database."""
        from resources.lib.ui.details_model import (
            ACTION_KEEP,
            ACTION_RESTORE,
            ACTION_UNLOCK,
        )

        if row.action not in (ACTION_RESTORE, ACTION_UNLOCK, ACTION_KEEP):
            return
        if not acquire_scan_lock():
            log.info("A scan is already running, skipping the action",
                     event="details.locked", action=row.action, field=row.key)
            notify(lang(32344))  # A scan is already running
            return
        if row.action == ACTION_KEEP:
            tracker = None
            kept = LOCK_FAILED
            try:
                tracker = TrackerDB(_get_db_path())
                kept = keep_field(tracker, self.media_type, self.identity, row.key)
            except Exception:
                log.exception("Keep failed", event="details.error", field=row.key)
            finally:
                release_scan_lock()
                if tracker is not None:
                    tracker.close()
            if kept != KEPT:
                notify(lang(32627))  # Could not save the lock
            return
        if row.action == ACTION_UNLOCK:
            tracker = None
            unlocked = False
            try:
                tracker = TrackerDB(_get_db_path())
                unlocked = unlock_field(tracker, self.media_type, self.identity, row.key)
            except Exception:
                log.exception("Unlock failed", event="details.error", field=row.key)
            finally:
                release_scan_lock()
                if tracker is not None:
                    tracker.close()
            if not unlocked:
                notify(lang(32596))  # Could not unlock this field
            return
        tracker = None
        result = FAILED
        try:
            tracker = TrackerDB(_get_db_path())
            result = restore_field(
                tracker, self.media_type, self.kodi_id, self.identity, row.key
            )
        except Exception:
            log.exception("Restore failed", event="details.error", field=row.key)
        finally:
            release_scan_lock()
            if tracker is not None:
                tracker.close()
        if result == CHANGED:
            # Also what a stale identity gives (a scan adopted the row while
            # the window was open); the reload that follows finds it again.
            notify(lang(32590))  # Nothing was restored: the item changed
        elif result == NOT_RESTORABLE:
            notify(lang(32606))  # This field has no original to restore
        elif result == EPISODES_NOT_MOVED:
            notify(lang(32605))  # The episodes' records could not follow
        elif result == LOCK_FAILED:
            notify(lang(32595))  # Could not lock the field, nothing restored
        elif result == FAILED:
            notify(lang(32591))  # Kodi did not accept the restore


def open_details(dbtype: str, dbid: str) -> None:
    """Open the details window for a library item (context menu "MetaMender:
    Details"). Opening writes nothing; only the window's buttons do.

    Args:
        dbtype: Kodi ListItem.DBTYPE ("movie", "tvshow" or "episode").
        dbid: Kodi database ID as a string (from $INFO[ListItem.DBID]).
    """
    from resources.lib.ui.details_window import show_details_window

    _init_logging()
    media_type = _DBTYPE_TO_MEDIA_TYPE.get(dbtype)
    if media_type is None:
        log.warning("Details asked for an unsupported type",
                    event="details.open_invalid", dbtype=dbtype)
        notify(lang(32342))  # Cannot update this item type
        return
    try:
        kodi_id = int(dbid)
    except (TypeError, ValueError):
        log.warning("Details asked with an invalid id",
                    event="details.open_invalid", dbid=str(dbid))
        notify(lang(32343))  # Invalid item
        return
    session = DetailsSession(dbtype, media_type, kodi_id)
    view = session.reload()
    if view is None:
        return
    show_details_window(session, view)

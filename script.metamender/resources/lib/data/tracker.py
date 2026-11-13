"""
SQLite tracker for backfill state.

Tracks which items have been processed, which fields were filled,
retry scheduling, and scan cycle state.

Logging:
    Logger: 'tracker'
    Key events:
        - tracker.upsert (DEBUG): Item created or updated
        - tracker.attempt (DEBUG): Retry attempt recorded
        - tracker.exhausted (INFO): Item marked as exhausted
        - tracker.field_update (DEBUG): Field status changed
        - tracker.rekey_commit_deferred (WARNING): An episode re-key is
          complete but its commit failed; the caller's next commit writes it
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from datetime import date
from typing import Any

from resources.lib.constants import SCHEMA_VERSION
from resources.lib.utils import get_logger

log = get_logger('tracker')

# scan_state key holding "0" while a cycle is open and "1" once it finished.
# A missing value means no cycle has ever been opened, which begin_cycle treats
# as "not interrupted" so the first run starts fresh.
_CYCLE_COMPLETE_KEY = "cycle_complete"

# The part of an episode identity after its show title (see compute_identity
# and the scan's duplicate key "<identity>|<file>").
_EPISODE_SUFFIX = re.compile(r"S\d{2,}E\d{2,}(\|.*)?$")

# Why a field last ended up as it did, stored in field_status.last_reason and
# shown in the item details window.
REASON_UPDATED = "updated"      # a provider value replaced Kodi's
REASON_UNCHANGED = "unchanged"  # checked, Kodi already held the provider value
REASON_NFO = "nfo"              # Kodi's value came from an NFO and was kept
REASON_FILL_ONLY = "fill_only"  # Kodi had a value and the field only fills gaps
REASON_NOTHING = "nothing"      # the provider had nothing to offer
REASON_UNCHECKED = "unchecked"  # not answered yet (transient failure, never reached)
REASON_LOCKED = "locked"        # the user locked the field

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type TEXT NOT NULL,
    identity TEXT NOT NULL,
    title TEXT NOT NULL,
    kodi_id INTEGER,
    tmdb_id TEXT,
    imdb_id TEXT,
    tvdb_id TEXT,
    source_path TEXT,
    premiered TEXT,
    date_added TEXT,
    last_scanned TEXT,
    last_seen TEXT,
    next_retry TEXT,
    attempt_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    cycle_processed INTEGER DEFAULT 0,
    ids_checked TEXT,
    -- TMDB season of an episode whose TMDB id came from /find; TMDB can
    -- number seasons differently from Kodi.
    tmdb_season INTEGER,
    -- An episode without a usable id of its own, matched by season and
    -- episode number: the title and date it had when first seen unmatched
    -- (the scraper's, which a match is always checked against), and whether
    -- its ids came from such a match. See engine/numbermatch.py.
    orig_title TEXT,
    orig_aired TEXT,
    number_matched INTEGER DEFAULT 0,
    -- JSON describing how an episode was matched by number (engine/numbermatch.py).
    match_note TEXT,
    UNIQUE(media_type, identity)
);

CREATE TABLE IF NOT EXISTS field_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(id),
    field TEXT NOT NULL,
    source TEXT,
    vote_count INTEGER,
    fetch_count INTEGER DEFAULT 0,
    next_retry TEXT,
    fetched_at TEXT,
    written_value TEXT,
    from_fallback INTEGER DEFAULT 0,
    fallback_checks INTEGER DEFAULT 0,
    settings_fp TEXT,
    -- One of the REASON_* values; never read by the maturity clock.
    last_reason TEXT,
    UNIQUE(item_id, field)
);

-- Keyed on the item's identity rather than its items row: the user's locks
-- and the values MetaMender replaced outlive the Reset tracker action, which
-- empties field_status. original is json.dumps of the Kodi value.
CREATE TABLE IF NOT EXISTS field_keep (
    media_type TEXT NOT NULL,
    identity TEXT NOT NULL,
    field TEXT NOT NULL,
    original TEXT,
    has_original INTEGER DEFAULT 0,
    locked INTEGER DEFAULT 0,
    -- Fingerprint of the value metamender last wrote, as field_status's
    -- written_value, but surviving clear_field_status: it tells whether
    -- Kodi still holds metamender's own value after a tracker reset.
    written_fp TEXT,
    PRIMARY KEY (media_type, identity, field)
);

CREATE TABLE IF NOT EXISTS scan_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_next_retry ON items(next_retry);
CREATE INDEX IF NOT EXISTS idx_items_cycle ON items(cycle_processed);
CREATE INDEX IF NOT EXISTS idx_items_last_seen ON items(last_seen);
CREATE INDEX IF NOT EXISTS idx_field_status ON field_status(item_id, field);
"""

# Columns that callers can set via upsert_item kwargs
_UPSERT_KWARGS = frozenset((
    "kodi_id", "tmdb_id", "imdb_id", "tvdb_id",
    "source_path", "premiered", "date_added", "ids_checked",
    "tmdb_season", "orig_title", "orig_aired", "number_matched", "match_note",
))

_ID_KWARGS = frozenset(("tmdb_id", "imdb_id", "tvdb_id"))


class TrackerDB:
    """SQLite-backed tracker for backfill item state."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables/indexes if missing and reconcile the schema version.

        Fresh database: create everything and stamp SCHEMA_VERSION. Existing
        database with an OLDER schema: drop and recreate every table (the
        tracker only caches per-field progress, so it is rebuilt by the next
        scan) and re-stamp. A database from a NEWER
        addon (stored > SCHEMA_VERSION) is left as-is with a warning rather than
        silently re-stamped, so a forward-incompatible open is at least visible.
        """
        # CREATE TABLE IF NOT EXISTS is safe on fresh and existing DBs, and
        # guarantees scan_state exists so the version marker can be read.
        self._conn.executescript(_SCHEMA_SQL)

        row = self._conn.execute(
            "SELECT value FROM scan_state WHERE key='schema_version'"
        ).fetchone()
        stored = int(row["value"]) if row and str(row["value"]).isdigit() else None

        if stored is not None and stored > SCHEMA_VERSION:
            log.warning(
                "Tracker database is from a newer addon version; "
                "operating without migrating",
                event="tracker.schema_newer",
                stored=stored,
                supported=SCHEMA_VERSION,
            )
            return

        if stored is not None and stored < SCHEMA_VERSION:
            # CREATE TABLE IF NOT EXISTS cannot add columns to the old tables,
            # so they are dropped and rebuilt rather than altered.
            log.warning(
                "Tracker schema is older than supported; recreating tables",
                event="tracker.schema_reset",
                from_version=stored,
                to_version=SCHEMA_VERSION,
            )
            self._conn.executescript(
                "DROP TABLE IF EXISTS field_status;"
                "DROP TABLE IF EXISTS items;"
                "DROP TABLE IF EXISTS scan_state;"
            )
            self._conn.executescript(_SCHEMA_SQL)

        # A current stamp is not rewritten: the write would wait for the lock
        # a running scan holds across its provider calls, and opening the
        # details window must not write at all.
        if stored == SCHEMA_VERSION:
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO scan_state (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Item CRUD
    # ------------------------------------------------------------------

    def upsert_item(
        self, media_type: str, identity: str, title: str | None = None, **kwargs: Any
    ) -> int:
        """Insert or update an item keyed on (media_type, identity).

        `title` is display-only. When omitted it defaults to `identity` on
        insert and is left unchanged on update. Other supplied kwargs update
        their columns; unmentioned columns keep their existing values.

        Returns the row id of the inserted or updated item.
        """
        # A missing ID is "not known here", never "clear it": discovered IDs
        # (resolved by search or enrichment) must survive a later scan whose
        # Kodi uniqueid lacks them.
        cols = {
            k: v for k, v in kwargs.items()
            if k in _UPSERT_KWARGS and not (k in _ID_KWARGS and v is None)
        }

        set_parts = []
        for col in _UPSERT_KWARGS:
            if col in cols:
                set_parts.append("{col} = excluded.{col}".format(col=col))
            else:
                set_parts.append("{col} = items.{col}".format(col=col))
        # title: update only when explicitly provided, else keep existing
        if title is not None:
            set_parts.append("title = excluded.title")
        else:
            set_parts.append("title = items.title")

        insert_cols = ["media_type", "identity", "title"] + list(cols.keys())
        placeholders = ", ".join(["?"] * len(insert_cols))
        values = [media_type, identity, title if title is not None else identity] + list(cols.values())

        sql = (
            "INSERT INTO items ({cols}) VALUES ({placeholders}) "
            "ON CONFLICT(media_type, identity) DO UPDATE SET {sets}"
        ).format(
            cols=", ".join(insert_cols),
            placeholders=placeholders,
            sets=", ".join(set_parts),
        )

        try:
            cursor = self._conn.execute(sql, values)
        except sqlite3.Error:
            log.exception(
                "Failed to upsert item",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
            )
            return -1

        log.debug("Item upserted", event="tracker.upsert", media_type=media_type, identity=identity)
        return cursor.lastrowid  # type: ignore[return-value]

    def get_item(self, media_type: str, identity: str) -> dict[str, Any] | None:
        """Get an item by (media_type, identity), or None if not found."""
        cursor = self._conn.execute(
            "SELECT * FROM items WHERE media_type = ? AND identity = ?",
            (media_type, identity),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def adoptable_identity(
        self, media_type: str, identity: str, kodi_id: Any
    ) -> str | None:
        """The identity of the row adopt_identity would rename to
        ``identity``, without renaming it; None when it would rename none."""
        prefix, _, ext_id = identity.partition(":")
        column = {"tmdb": "tmdb_id", "imdb": "imdb_id"}.get(prefix)
        if column is None or not ext_id or kodi_id is None:
            return None
        if self._get_item_id(media_type, identity) is not None:
            return None
        rows = self._conn.execute(
            "SELECT identity FROM items WHERE media_type = ? AND kodi_id = ? "
            "AND {} = ?".format(column),
            (media_type, kodi_id, ext_id),
        ).fetchall()
        if len(rows) != 1:
            return None
        return str(rows[0]["identity"])

    def adopt_identity(
        self, media_type: str, identity: str, kodi_id: Any
    ) -> str | None:
        """Rename this Kodi item's row to ``identity`` when that identity is
        new because the item gained the external id it names.

        An item keyed on "title (year)" or "imdb:<id>" becomes "imdb:<id>" or
        "tmdb:<id>" once that id is in Kodi's uniqueid, for instance after
        metamender wrote back an IMDb id it found. Without the rename the next
        scan starts a fresh row and the old one, with its fetch clocks and
        provenance, is orphaned. The row is adopted only when it belongs to
        the same Kodi item and already carries the id, so another item that
        resolved to the same id keeps its own row. Returns the old identity,
        or None when nothing was renamed.
        """
        old = self.adoptable_identity(media_type, identity, kodi_id)
        if old is None:
            return None
        try:
            self._conn.execute(
                "UPDATE items SET identity = ? WHERE media_type = ? AND identity = ?",
                (identity, media_type, old),
            )
            self._move_keep(media_type, old, identity)
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to adopt identity", event="tracker.error",
                media_type=media_type, identity=identity, old_identity=old,
            )
            return None
        log.info(
            "Item identity adopted", event="tracker.identity_adopted",
            media_type=media_type, identity=identity, old_identity=old,
        )
        return old

    def rename_show_episodes(self, old_title: str, new_title: str) -> int | None:
        """Re-key a show's episode rows after the show's title changed (a
        scan wrote a new one, or the details window restored the original).

        An episode is keyed "<show title> SxxEyy" (with "|<file>" for a
        duplicate), so a new show title would otherwise orphan every episode
        row and restart its clocks. A row whose new key is already taken keeps
        its old one. Returns the number of rows renamed, or None when the
        re-key failed, so the caller can tell the user that the episodes
        lost their rows. A failed re-key is undone (see _undo_rekey), so
        none of it is committed later. A failure of only the final commit
        is not a failed re-key: the complete renames stay pending with the
        caller's transaction, which its next commit writes.
        """
        prefix = old_title + " "
        rows = self._conn.execute(
            "SELECT id, identity FROM items WHERE media_type = 'episode' "
            "AND substr(identity, 1, ?) = ?",
            (len(prefix), prefix),
        ).fetchall()
        renamed = 0
        try:
            # A savepoint opens a transaction when none is pending, so the
            # renames and the commit below stay one unit either way.
            self._conn.execute("SAVEPOINT rekey")
            for row in rows:
                rest = row["identity"][len(prefix):]
                if not _EPISODE_SUFFIX.match(rest):
                    continue
                new_identity = new_title + " " + rest
                if self._get_item_id("episode", new_identity) is not None:
                    continue
                self._conn.execute(
                    "UPDATE items SET identity = ? WHERE id = ?", (new_identity, row["id"]),
                )
                self._move_keep("episode", row["identity"], new_identity)
                renamed += 1
            self._conn.execute("RELEASE rekey")
        except sqlite3.Error:
            log.exception(
                "Failed to re-key episode rows", event="tracker.error",
                old_title=old_title, new_title=new_title,
            )
            self._undo_rekey()
            return None
        try:
            self._conn.commit()
        except sqlite3.Error:
            log.warning(
                "Episode re-key not committed yet, left for the next commit",
                event="tracker.rekey_commit_deferred", old_title=old_title,
                new_title=new_title, renamed=renamed,
            )
        log.info(
            "Episode rows re-keyed after a show title change",
            event="tracker.episodes_renamed", old_title=old_title,
            new_title=new_title, renamed=renamed,
        )
        return renamed

    def _undo_rekey(self) -> None:
        """Drop a failed re-key's renames by rolling back to its savepoint,
        which keeps the caller's pending writes. When that fails, the whole
        transaction is rolled back, those writes included, so a later commit
        cannot write half a re-key. Should even that fail, it is logged and
        the connection's state is unknown."""
        try:
            self._conn.execute("ROLLBACK TO rekey")
            self._conn.execute("RELEASE rekey")
            return
        except sqlite3.Error:
            log.exception("Failed to undo a partial episode re-key, rolling back "
                          "the whole transaction", event="tracker.error")
        try:
            self._conn.rollback()
        except sqlite3.Error:
            log.exception("Failed to roll back a partial episode re-key",
                          event="tracker.error")

    def known_kodi_ids(self, media_type: str) -> set[int]:
        """Kodi ids of the tracked items of this type, as last scanned."""
        rows = self._conn.execute(
            "SELECT kodi_id FROM items WHERE media_type = ? AND kodi_id IS NOT NULL",
            (media_type,),
        )
        return {int(r["kodi_id"]) for r in rows}

    def update_item_status(
        self, media_type: str, identity: str, status: str
    ) -> None:
        """Update the status column for an item."""
        try:
            self._conn.execute(
                "UPDATE items SET status = ? WHERE media_type = ? AND identity = ?",
                (status, media_type, identity),
            )
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to update item status",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
                status=status,
            )
            return

        log.debug(
            "Item status updated",
            media_type=media_type,
            identity=identity,
            status=status,
        )

    def update_last_seen(self, media_type: str, identity: str, today: str) -> None:
        """Record that this item was present in the Kodi library on `today`."""
        try:
            self._conn.execute(
                "UPDATE items SET last_seen = ? WHERE media_type = ? AND identity = ?",
                (today, media_type, identity),
            )
        except sqlite3.Error:
            log.exception(
                "Failed to update last_seen",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
            )

    def prune_orphans(self, media_type: str, cutoff: str) -> int:
        """Delete items of this type whose last_seen is older than `cutoff`.

        Items with a NULL last_seen are kept (never confirmed present yet).
        Associated field_status and field_keep rows are deleted too.
        `cutoff` is an ISO date string (callers pass today minus the
        retention window). Returns the number of items removed.
        """
        try:
            doomed = self._conn.execute(
                "SELECT id, identity FROM items WHERE media_type = ? "
                "AND last_seen IS NOT NULL AND last_seen < ?",
                (media_type, cutoff),
            ).fetchall()
            ids = [r["id"] for r in doomed]
            if not ids:
                return 0
            self._conn.executemany(
                "DELETE FROM field_keep WHERE media_type = ? AND identity = ?",
                [(media_type, r["identity"]) for r in doomed],
            )
            placeholders = ", ".join(["?"] * len(ids))
            self._conn.execute(
                "DELETE FROM field_status WHERE item_id IN ({})".format(placeholders), ids
            )
            self._conn.execute(
                "DELETE FROM items WHERE id IN ({})".format(placeholders), ids
            )
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to prune orphans", event="tracker.error", media_type=media_type
            )
            return 0

        log.info(
            "Pruned orphaned items", event="tracker.prune",
            media_type=media_type, removed=len(ids),
        )
        return len(ids)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _move_keep(self, media_type: str, old: str, new: str) -> None:
        """Re-key an item's field_keep rows with its items row (no commit)."""
        # A row already at ``new`` is a stray of an item that left; the
        # moved rows belong to the item now at that identity, so they win.
        self._conn.execute(
            "UPDATE OR REPLACE field_keep SET identity = ? "
            "WHERE media_type = ? AND identity = ?",
            (new, media_type, old),
        )

    def _get_item_id(self, media_type: str, identity: str) -> int | None:
        """Look up the row id for an item by (media_type, identity)."""
        cursor = self._conn.execute(
            "SELECT id FROM items WHERE media_type = ? AND identity = ?",
            (media_type, identity),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row["id"]  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Field status (Task 2.3)
    # ------------------------------------------------------------------

    def get_field_status(
        self, media_type: str, identity: str, field: str
    ) -> dict[str, Any] | None:
        """Get a single field_status row, or None if not found."""
        item_id = self._get_item_id(media_type, identity)
        if item_id is None:
            log.debug(
                "Item not found for field status query",
                media_type=media_type,
                identity=identity,
                field=field,
            )
            return None

        cursor = self._conn.execute(
            "SELECT * FROM field_status WHERE item_id = ? AND field = ?",
            (item_id, field),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_field_status_map(
        self, media_type: str, identity: str
    ) -> dict[str, dict[str, Any]]:
        """Return {field: row_dict} for all field_status rows of an item."""
        item_id = self._get_item_id(media_type, identity)
        if item_id is None:
            return {}
        cursor = self._conn.execute(
            "SELECT * FROM field_status WHERE item_id = ?", (item_id,)
        )
        return {row["field"]: dict(row) for row in cursor.fetchall()}

    def record_field_fetch(
        self,
        media_type: str,
        identity: str,
        field: str,
        next_retry: str | None,
        source: str | None = None,
        vote_count: int | None = None,
        written_value: str | None = None,
        from_fallback: bool | None = None,
        settings_fp: str | None = None,
        fallback_recheck: bool = False,
        reason: str | None = None,
    ) -> None:
        """Record a successful sample: bump fetch_count, stamp fetched_at, set the
        next due date and (optionally) provenance.

        COALESCE keeps the prior source, vote_count, written_value and
        from_fallback when the new call passes None. settings_fp is always
        overwritten so it names the settings the latest answer was fetched
        under. fallback_checks counts the monthly rechecks of a
        fallback-sourced value: a sample with ``fallback_recheck`` (one that
        replaced a FINAL verdict) of a row still flagged from_fallback adds
        one; any other sample, such as young content on its refetch schedule,
        leaves the count, so a dense schedule cannot spend the rechecks early.
        The first fallback write starts at 0, and from_fallback=False clears
        both the flag and the counter.
        """
        item_id = self._get_item_id(media_type, identity)
        if item_id is None:
            return
        today = date.today().isoformat()
        fallback = None if from_fallback is None else int(from_fallback)
        try:
            self._conn.execute(
                "INSERT INTO field_status "
                "(item_id, field, fetch_count, fetched_at, next_retry, source, "
                "vote_count, written_value, from_fallback, fallback_checks, settings_fp, "
                "last_reason) "
                "VALUES (:item_id, :field, 1, :today, :next_retry, :source, "
                ":vote_count, :written_value, COALESCE(:fallback, 0), 0, :settings_fp, "
                ":reason) "
                "ON CONFLICT(item_id, field) DO UPDATE SET "
                "fetch_count = field_status.fetch_count + 1, "
                "fetched_at = excluded.fetched_at, "
                "next_retry = excluded.next_retry, "
                "source = COALESCE(excluded.source, field_status.source), "
                "vote_count = COALESCE(excluded.vote_count, field_status.vote_count), "
                "written_value = COALESCE(excluded.written_value, field_status.written_value), "
                "fallback_checks = CASE "
                "WHEN :fallback = 0 THEN 0 "
                "WHEN field_status.from_fallback = 1 AND :recheck = 1 "
                "THEN field_status.fallback_checks + 1 "
                "WHEN field_status.from_fallback = 1 THEN field_status.fallback_checks "
                "ELSE 0 END, "
                "from_fallback = COALESCE(:fallback, field_status.from_fallback), "
                "settings_fp = excluded.settings_fp, "
                "last_reason = COALESCE(excluded.last_reason, field_status.last_reason)",
                {
                    "item_id": item_id, "field": field, "today": today,
                    "next_retry": next_retry, "source": source,
                    "vote_count": vote_count, "written_value": written_value,
                    "fallback": fallback, "settings_fp": settings_fp,
                    "recheck": int(fallback_recheck), "reason": reason,
                },
            )
        except sqlite3.Error:
            log.exception(
                "Failed to record field fetch",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
                field=field,
            )

    def record_manual_check(
        self,
        media_type: str,
        identity: str,
        field: str,
        settings_fp: str | None,
        written_value: str | None = None,
        source: str | None = None,
        vote_count: int | None = None,
        from_fallback: bool | None = None,
        reason: str | None = None,
    ) -> None:
        """Record what an Update now check left in Kodi without touching the
        field's schedule: fetch_count, next_retry and fetched_at stay as they
        were, since a manual refresh is not a sample of the item's ageing.
        None keeps the stored value, as in record_field_fetch; settings_fp is
        always overwritten. A value newly from the fallback language starts
        its recheck count at 0, as a first fallback write does."""
        item_id = self._get_item_id(media_type, identity)
        if item_id is None:
            return
        fallback = None if from_fallback is None else int(from_fallback)
        try:
            self._conn.execute(
                "UPDATE field_status SET "
                "source = COALESCE(:source, source), "
                "vote_count = COALESCE(:vote_count, vote_count), "
                "written_value = COALESCE(:written_value, written_value), "
                "fallback_checks = CASE "
                "WHEN :fallback = 0 THEN 0 "
                "WHEN :fallback = 1 AND from_fallback = 0 THEN 0 "
                "ELSE fallback_checks END, "
                "from_fallback = COALESCE(:fallback, from_fallback), "
                "settings_fp = :settings_fp, "
                "last_reason = COALESCE(:reason, last_reason) "
                "WHERE item_id = :item_id AND field = :field",
                {
                    "item_id": item_id, "field": field, "source": source,
                    "vote_count": vote_count, "written_value": written_value,
                    "fallback": fallback, "settings_fp": settings_fp,
                    "reason": reason,
                },
            )
        except sqlite3.Error:
            log.exception(
                "Failed to record manual check",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
                field=field,
            )

    def reset_field_clock(
        self,
        media_type: str,
        identity: str,
        field: str,
        next_retry: str | None,
        settings_fp: str | None = None,
        written_value: str | None = None,
        source: str | None = None,
        vote_count: int | None = None,
        from_fallback: bool | None = None,
        reason: str | None = None,
    ) -> None:
        """Re-baseline a field to its first sample ('Update now', or a change
        in the settings the field depends on).

        Stores the supplied next_retry date so young content is re-sampled on
        the normal schedule after a manual update, rather than being skipped
        forever because NULL next_retry is treated as "not due" by decide_field.
        settings_fp is stored as given so the re-baselined row matches the
        settings in force. fallback_checks restarts at 0: a fallback value gets
        its full run of re-checks again. source, vote_count, written_value and
        from_fallback describe what the sample left in Kodi; None keeps the
        stored value, as in record_field_fetch.
        """
        item_id = self._get_item_id(media_type, identity)
        if item_id is None:
            return
        today = date.today().isoformat()
        fallback = None if from_fallback is None else int(from_fallback)
        try:
            self._conn.execute(
                "INSERT INTO field_status "
                "(item_id, field, fetch_count, fetched_at, next_retry, settings_fp, "
                "written_value, source, vote_count, from_fallback, fallback_checks, "
                "last_reason) "
                "VALUES (:item_id, :field, 1, :today, :next_retry, :settings_fp, "
                ":written_value, :source, :vote_count, COALESCE(:fallback, 0), 0, "
                ":reason) "
                "ON CONFLICT(item_id, field) DO UPDATE SET "
                "fetch_count = 1, fetched_at = excluded.fetched_at, "
                "next_retry = excluded.next_retry, settings_fp = excluded.settings_fp, "
                "written_value = COALESCE(excluded.written_value, field_status.written_value), "
                "source = COALESCE(excluded.source, field_status.source), "
                "vote_count = COALESCE(excluded.vote_count, field_status.vote_count), "
                "from_fallback = COALESCE(:fallback, field_status.from_fallback), "
                "fallback_checks = 0, "
                "last_reason = COALESCE(excluded.last_reason, field_status.last_reason)",
                {
                    "item_id": item_id, "field": field, "today": today,
                    "next_retry": next_retry, "settings_fp": settings_fp,
                    "written_value": written_value, "source": source,
                    "vote_count": vote_count, "fallback": fallback,
                    "reason": reason,
                },
            )
        except sqlite3.Error:
            log.exception(
                "Failed to reset field clock",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
                field=field,
            )

    def record_field_reason(
        self, media_type: str, identity: str, field: str, reason: str
    ) -> None:
        """Record only why a field is as it is, for a field that was not
        sampled (a transient failure, a locked field). The row is created
        with fetch_count 0 when missing; no clock, date or provenance changes,
        so the maturity model sees no fetch that did not happen."""
        item_id = self._get_item_id(media_type, identity)
        if item_id is None:
            return
        try:
            self._conn.execute(
                "INSERT INTO field_status (item_id, field, fetch_count, last_reason) "
                "VALUES (?, ?, 0, ?) "
                "ON CONFLICT(item_id, field) DO UPDATE SET last_reason = excluded.last_reason",
                (item_id, field, reason),
            )
        except sqlite3.Error:
            log.exception(
                "Failed to record field reason", event="tracker.error",
                media_type=media_type, identity=identity, field=field,
            )

    # ------------------------------------------------------------------
    # Kept originals and locks (survive clear_field_status)
    # ------------------------------------------------------------------

    def keep_original(
        self, media_type: str, identity: str, field: str, value: Any
    ) -> None:
        """Remember the Kodi value MetaMender is about to replace. The value
        is stored as JSON so a list stays a list and "" stays "". A lock on
        the field is kept."""
        try:
            self._conn.execute(
                "INSERT INTO field_keep (media_type, identity, field, original, "
                "has_original) VALUES (?, ?, ?, ?, 1) "
                "ON CONFLICT(media_type, identity, field) DO UPDATE SET "
                "original = excluded.original, has_original = 1",
                (media_type, identity, field, json.dumps(value)),
            )
        except sqlite3.Error:
            log.exception(
                "Failed to keep original", event="tracker.error",
                media_type=media_type, identity=identity, field=field,
            )

    def set_locked(
        self, media_type: str, identity: str, field: str, locked: bool
    ) -> bool:
        """Lock or unlock a field (no commit); a kept original is left alone.
        False when the write failed: a lock the caller believes is set but
        is not lets the next scan overwrite the field."""
        try:
            self._conn.execute(
                "INSERT INTO field_keep (media_type, identity, field, locked) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(media_type, identity, field) DO UPDATE SET "
                "locked = excluded.locked",
                (media_type, identity, field, int(locked)),
            )
        except sqlite3.Error:
            log.exception(
                "Failed to set lock", event="tracker.error",
                media_type=media_type, identity=identity, field=field,
            )
            return False
        return True

    def set_written_fp(
        self, media_type: str, identity: str, field: str, written_fp: str
    ) -> None:
        """Record the fingerprint of the value metamender wrote; a kept
        original and a lock are left alone."""
        try:
            self._conn.execute(
                "INSERT INTO field_keep (media_type, identity, field, written_fp) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(media_type, identity, field) DO UPDATE SET "
                "written_fp = excluded.written_fp",
                (media_type, identity, field, written_fp),
            )
        except sqlite3.Error:
            log.exception(
                "Failed to record written fingerprint", event="tracker.error",
                media_type=media_type, identity=identity, field=field,
            )

    def get_keep(self, media_type: str, identity: str) -> dict[str, dict[str, Any]]:
        """field -> {"original": decoded value, "has_original", "locked",
        "written_fp"}."""
        rows = self._conn.execute(
            "SELECT field, original, has_original, locked, written_fp FROM field_keep "
            "WHERE media_type = ? AND identity = ?",
            (media_type, identity),
        ).fetchall()
        return {
            r["field"]: {
                "original": (
                    json.loads(r["original"]) if r["has_original"] else None
                ),
                "has_original": bool(r["has_original"]),
                "locked": bool(r["locked"]),
                "written_fp": r["written_fp"],
            }
            for r in rows
        }

    def locked_fields(self, media_type: str, identity: str) -> frozenset[str]:
        """The fields the user locked on this item."""
        return frozenset(
            r["field"] for r in self._conn.execute(
                "SELECT field FROM field_keep "
                "WHERE media_type = ? AND identity = ? AND locked = 1",
                (media_type, identity),
            )
        )

    def clear_field_status(self) -> int:
        """Delete all field_status rows (the Reset-tracker action). Returns count.

        field_keep is left alone: locks and kept originals are the user's."""
        try:
            cur = self._conn.execute("DELETE FROM field_status")
            self._conn.commit()
            return cur.rowcount
        except sqlite3.Error:
            log.exception("Failed to clear field status", event="tracker.error")
            return 0

    def forget_field_fingerprint(self, media_type: str, identity: str, field: str) -> bool:
        """Clear one field's settings fingerprint (no commit), so the next
        scan checks it again whatever its clock says, keeping its provenance,
        as forget_disabled_fields does for a re-enabled field. False when the
        write failed."""
        try:
            self._conn.execute(
                "UPDATE field_status SET settings_fp = NULL WHERE field = ? AND item_id IN "
                "(SELECT id FROM items WHERE media_type = ? AND identity = ?)",
                (field, media_type, identity),
            )
        except sqlite3.Error:
            log.exception("Failed to forget field fingerprint", event="tracker.error",
                          media_type=media_type, identity=identity, field=field)
            return False
        return True

    def forget_disabled_fields(self, media_type: str, enabled: Iterable[str]) -> int:
        """Clear the settings fingerprint of every field of ``media_type`` not
        in ``enabled``. A field switched off and on again then no longer
        matches its fingerprint, so the scan checks it once more, keeping
        its provenance. Returns the number of rows cleared."""
        keep = sorted(set(enabled))
        marks = ",".join("?" * len(keep))
        not_kept = "AND field NOT IN ({})".format(marks) if keep else ""
        try:
            cur = self._conn.execute(
                "UPDATE field_status SET settings_fp = NULL "
                "WHERE settings_fp IS NOT NULL {} AND item_id IN "
                "(SELECT id FROM items WHERE media_type = ?)".format(not_kept),
                (*keep, media_type),
            )
            self._conn.commit()
            return cur.rowcount
        except sqlite3.Error:
            log.exception("Failed to forget disabled fields", event="tracker.error",
                          media_type=media_type)
            return 0

    def commit(self) -> None:
        """Commit the current transaction (callers batch one item's writes)."""
        self._conn.commit()

    def rollback(self) -> None:
        """Drop the current transaction's uncommitted writes."""
        self._conn.rollback()

    def get_show_id_map(self) -> dict[int, str]:
        """Map a TV show's Kodi id to its show-level TMDB ID.

        Built from the tvshow items recorded during the show scan so the
        episode scan can resolve the correct show TMDB ID for season lookups.
        Keyed by Kodi id (an episode's ``tvshowid``), not title, because
        distinct shows can share a title.
        """
        show_map: dict[int, str] = {}
        cursor = self._conn.execute(
            "SELECT kodi_id, tmdb_id FROM items "
            "WHERE media_type = 'tvshow' AND tmdb_id IS NOT NULL "
            "AND kodi_id IS NOT NULL"
        )
        for row in cursor.fetchall():
            show_map[row["kodi_id"]] = row["tmdb_id"]
        return show_map

    def get_show_tvdb_map(self) -> dict[int, str]:
        """Map a TV show's Kodi id to its TVDB series ID.

        The episode scan needs the series ID to fetch a show's episode list
        from TVDB; Kodi stores it only on the show, not on its episodes.
        """
        cursor = self._conn.execute(
            "SELECT kodi_id, tvdb_id FROM items "
            "WHERE media_type = 'tvshow' AND tvdb_id IS NOT NULL "
            "AND kodi_id IS NOT NULL"
        )
        return {row["kodi_id"]: row["tvdb_id"] for row in cursor.fetchall()}

    def get_tracked_show_ids(self) -> frozenset[int]:
        """Kodi ids of every TV show the tracker knows."""
        cursor = self._conn.execute(
            "SELECT kodi_id FROM items WHERE media_type = 'tvshow' AND kodi_id IS NOT NULL"
        )
        return frozenset(row["kodi_id"] for row in cursor.fetchall())

    def get_checked_show_ids(self) -> frozenset[int]:
        """Kodi ids of the TV shows whose id cross-reference lookups have
        answered at least once.

        For a show in this set a missing TMDB or TVDB id is an answer (the
        provider has no such show); for any other show it is not known yet.
        """
        cursor = self._conn.execute(
            "SELECT kodi_id FROM items "
            "WHERE media_type = 'tvshow' AND ids_checked IS NOT NULL "
            "AND kodi_id IS NOT NULL"
        )
        return frozenset(row["kodi_id"] for row in cursor.fetchall())

    # ------------------------------------------------------------------
    # Cycle tracking and scan state (Task 2.4)
    # ------------------------------------------------------------------

    def start_new_cycle(self) -> None:
        """Reset cycle_processed to 0 for all items."""
        try:
            cursor = self._conn.execute("UPDATE items SET cycle_processed = 0")
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to start new cycle",
                event="tracker.error",
            )
            return

        log.info(
            "New scan cycle started",
            event="tracker.cycle_start",
            items_reset=cursor.rowcount,
        )

    def begin_cycle(self, resume_interrupted: bool) -> bool:
        """Open a scan cycle. Returns True if a fresh cycle was started.

        A cycle is resumed only when the previous one was interrupted AND the
        user asked to resume. A cycle that ran to completion always starts
        fresh: `cycle_processed` would otherwise stay 1 for every item, the
        whole library would be skipped from the second cycle on, and the
        per-field refetch schedule would never come around again.
        """
        interrupted = self.get_scan_state(_CYCLE_COMPLETE_KEY) == "0"
        started_fresh = not (interrupted and resume_interrupted)
        if started_fresh:
            self.start_new_cycle()
        else:
            log.info(
                "Resuming interrupted scan cycle",
                event="tracker.cycle_resume",
            )
        self.set_scan_state(_CYCLE_COMPLETE_KEY, "0")
        return started_fresh

    def mark_cycle_complete(self) -> None:
        """Record that the current cycle reached the end of the library.

        Only a cycle that was not cut short (shutdown, providers down) may be
        marked complete, or the next run resumes from a watermark that never
        covered the whole library.
        """
        self.set_scan_state(_CYCLE_COMPLETE_KEY, "1")

    def clear_number_match(self, media_type: str, identity: str) -> None:
        """Drop the ids a number match gave an episode (upsert_item never
        clears an id); the kept original title and date stay."""
        try:
            self._conn.execute(
                "UPDATE items SET tmdb_id = NULL, tvdb_id = NULL, imdb_id = NULL, "
                "tmdb_season = NULL, number_matched = 0 "
                "WHERE media_type = ? AND identity = ?",
                (media_type, identity),
            )
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to clear number match",
                event="tracker.error", media_type=media_type, identity=identity,
            )

    def mark_cycle_processed(self, media_type: str, identity: str) -> None:
        """Mark an item as processed in the current cycle."""
        try:
            self._conn.execute(
                "UPDATE items SET cycle_processed = 1 "
                "WHERE media_type = ? AND identity = ?",
                (media_type, identity),
            )
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to mark cycle processed",
                event="tracker.error",
                media_type=media_type,
                identity=identity,
            )

    def set_scan_state(self, key: str, value: str) -> None:
        """Insert or replace a key-value pair in the scan_state table."""
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO scan_state (key, value) VALUES (?, ?)",
                (key, value),
            )
            self._conn.commit()
        except sqlite3.Error:
            log.exception(
                "Failed to set scan state",
                event="tracker.error",
                key=key,
            )

    def get_scan_state(self, key: str) -> str | None:
        """Get a value from the scan_state table, or None if not found."""
        cursor = self._conn.execute(
            "SELECT value FROM scan_state WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row["value"]  # type: ignore[no-any-return]

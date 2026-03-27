#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Shared database module for multi-instance sync.

Provides connection management and CRUD operations for the shared MySQL/MariaDB
database used to synchronize ondeck state across multiple Kodi instances.

Architecture:
    - Primary: Creates namespaced database `easytv_{kodi_base_name}`
    - Fallback: Uses prefixed tables in Kodi's video database if CREATE DATABASE denied

Key Features:
    - Atomic writes using LAST_INSERT_ID pattern
    - Consistent reads using CROSS JOIN
    - Connection pooling with ping/reconnect
    - Backoff after connection failures (30s)
    - TTL-based migration lock for crash recovery
    - Batch write mode with deferred commit for O(1) fsync overhead

Logging:
    Logger name: 'shareddb'
    Key events:
        - shareddb.connect: Connection established
        - shareddb.reconnect: Connection recovered
        - shareddb.backoff: Connection failed, entering backoff
        - shareddb.init_separate: Using separate easytv database
        - shareddb.init_prefixed: Using prefixed tables in Kodi DB
        - shareddb.write: Show tracking data saved (non-batch mode)
        - shareddb.write_slow: Slow write detected during batch (≥50ms)
        - shareddb.write_error: Write operation failed
        - shareddb.reselect_error: Failed to re-select database after reconnect
        - shareddb.batch_complete: Batch write summary with stats
        - shareddb.batch_finalize_error: Failed to commit batch transaction
        - shareddb.migration_claimed: Migration lock acquired
        - shareddb.migration_stolen: Stale migration lock stolen
        - shareddb.schema_migrate: Schema migration applied
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import socket
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, Generator, List, Optional, Tuple, TYPE_CHECKING

import xbmcgui
import xbmcvfs

from resources.lib.constants import (
    EASYTV_DB_BACKOFF_SECONDS,
    EASYTV_DB_PREFIX,
    EASYTV_MIGRATION_LOCK_TTL_MINUTES,
    EASYTV_SCHEMA_VERSION,
    EASYTV_TABLE_PREFIX,
    KODI_DEFAULT_VIDEO_DB_NAME,
    KODI_HOME_WINDOW_ID,
)
from resources.lib.utils import get_logger, log_timing

if TYPE_CHECKING:
    from pymysql import Connection

log = get_logger('shareddb')

# Window for storing sync revision
WINDOW = xbmcgui.Window(KODI_HOME_WINDOW_ID)

# Threshold for logging slow writes during batch operations (milliseconds)
SLOW_WRITE_THRESHOLD_MS = 50


class SharedDatabase:
    """
    Manages connection to shared MySQL/MariaDB database for multi-instance sync.
    
    The database stores ondeck/offdeck state for TV shows, allowing multiple
    Kodi instances to stay synchronized. Uses a global revision counter for
    O(1) staleness detection.
    
    Connection Strategy:
        - Persistent connection with ping/reconnect
        - 30-second backoff after connection failure
        - One-time notification per backoff cycle
        - sync_rev cleared on failure to force refresh when DB returns
    
    Schema Strategy:
        1. Try to create namespaced database `easytv_{kodi_base_name}`
        2. If permission denied, fall back to prefixed tables in Kodi video DB
    
    Example:
        db = SharedDatabase()
        if db.is_available():
            new_rev = db.set_show_tracking(123, {...})
            data, rev = db.get_show_tracking_bulk_with_rev([123, 456])
    """
    
    # Class-level backoff state (shared across instances for consistent behavior)
    _last_failure_time: float = 0
    _backoff_notified: bool = False
    
    # advancedsettings.xml paths to check (in order of preference)
    ADVANCEDSETTINGS_PATHS = [
        'special://userdata/advancedsettings.xml',     # Most common
        'special://profile/advancedsettings.xml',      # Profile-specific
        'special://masterprofile/advancedsettings.xml'  # Master profile
    ]
    
    # Class-level instance counter for debugging
    _instance_count: int = 0
    
    def __init__(self) -> None:
        """Initialize the shared database manager."""
        SharedDatabase._instance_count += 1
        self._instance_id = SharedDatabase._instance_count
        log.debug("SharedDatabase instance created",
                 event="shareddb.instance_created",
                 instance_id=self._instance_id)
        
        self._conn: Optional[Connection] = None
        self._config: Optional[Dict[str, Any]] = None
        self._use_separate_db: bool = True
        self._table_prefix: str = ""
        self._easytv_db_name: str = ""
        self._schema_initialized: bool = False
        # Batch write state
        self._batch_active: bool = False
        self._batch_stats: Dict[str, Any] = self._reset_batch_stats()
        self._batch_preload: Optional[Dict[int, Dict[str, Any]]] = None
        self._batch_current_rev: int = 0
        self._batch_write_count: int = 0
        self._batch_final_rev: Optional[int] = None
    
    def is_available(self) -> bool:
        """
        Check if database is available, respecting backoff period.
        
        Returns:
            True if database is available and connected, False otherwise.
        """
        # Check backoff
        elapsed = time.time() - SharedDatabase._last_failure_time
        if elapsed < EASYTV_DB_BACKOFF_SECONDS:
            # In backoff period - notify once per cycle
            if not SharedDatabase._backoff_notified:
                remaining = int(EASYTV_DB_BACKOFF_SECONDS - elapsed)
                log.warning("Database unavailable, using local cache",
                           event="shareddb.backoff_active",
                           remaining_seconds=remaining)
                SharedDatabase._backoff_notified = True
            return False
        
        try:
            self._get_connection()
            SharedDatabase._backoff_notified = False  # Reset for next failure
            log.debug("is_available check passed", event="shareddb.available_check")
            return True
        except Exception as e:
            SharedDatabase._last_failure_time = time.time()
            # Clear sync_rev so we force refresh when DB returns
            WINDOW.clearProperty("EasyTV.sync_rev")
            log.warning("Database unavailable, backing off",
                       event="shareddb.backoff",
                       backoff_seconds=EASYTV_DB_BACKOFF_SECONDS,
                       error=str(e),
                       error_type=type(e).__name__)
            return False
    
    def _reset_batch_stats(self) -> Dict[str, Any]:
        """
        Reset and return batch statistics dictionary.
        
        Returns:
            Fresh statistics dictionary with zeroed counters.
        """
        return {
            'count': 0,
            'skipped': 0,
            'slow_count': 0,
            'total_ms': 0.0,
            'max_ms': 0.0,
        }
    
    @property
    def batch_final_rev(self) -> Optional[int]:
        """
        The final global revision after a batch completes.
        
        Set by _batch_finalize() when at least one write occurred.
        None if the batch had zero actual writes (all skipped or empty).
        Only valid immediately after a batch_write() context exits.
        """
        return self._batch_final_rev
    
    @contextlib.contextmanager
    def batch_write(
        self,
        preload: Optional[Dict[int, Dict[str, Any]]] = None,
        current_rev: int = 0
    ) -> Generator[None, None, None]:
        """
        Context manager for batch write operations with deferred commit.
        
        All writes within the batch share a single database transaction.
        Individual set_show_tracking() calls execute their UPSERT SQL but
        skip the per-write revision UPDATE and commit. On exit,
        _batch_finalize() performs a single revision bump and commit for
        all writes, reducing fsync overhead from O(N) to O(1).
        
        Individual DEBUG logs are suppressed unless the operation is slow
        (≥50ms) or errors.
        
        When preload is provided, writes are skipped if ondeck_episode_id
        matches the existing value (no actual change).
        
        After the context exits, batch_final_rev contains the new global
        revision (or None if no writes occurred).
        
        Args:
            preload: Optional dict of {show_id: existing_data} from bulk read.
                    When provided, unchanged writes are skipped.
            current_rev: The current global revision (from bulk read).
                        Returned for skipped writes to avoid extra queries.
        
        Example:
            # Without preload (migration): all writes proceed
            with db.batch_write():
                for show_id, data in shows.items():
                    db.set_show_tracking(show_id, data)
            final_rev = db.batch_final_rev  # New revision or None
            
            # With preload (startup): unchanged writes skipped
            existing, rev = db.get_show_tracking_bulk_with_rev(show_ids)
            with db.batch_write(preload=existing, current_rev=rev):
                for show_id, data in shows.items():
                    db.set_show_tracking(show_id, data)
        """
        self._batch_active = True
        self._batch_stats = self._reset_batch_stats()
        self._batch_preload = preload
        self._batch_current_rev = current_rev
        self._batch_write_count = 0
        self._batch_final_rev = None
        
        try:
            yield
        except Exception:
            # Error during batch — previous writes were rolled back by
            # set_show_tracking's except handler. Reset write count so
            # _batch_finalize skips the revision bump (no data to commit).
            self._batch_write_count = 0
            raise
        finally:
            self._batch_finalize()
            self._batch_active = False
            self._batch_preload = None
            self._batch_current_rev = 0
            self._batch_write_count = 0
    
    def _batch_finalize(self) -> None:
        """
        Finalize a batch by committing all deferred writes in one transaction.
        
        If any writes occurred (_batch_write_count > 0), performs a single
        revision bump by the total write count, commits once, and stores
        the final revision in _batch_final_rev.
        
        If no writes occurred (all skipped or empty batch), no database
        operations are performed and _batch_final_rev remains None.
        
        Also logs the batch summary statistics.
        """
        stats = self._batch_stats
        
        if self._batch_write_count > 0:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                try:
                    # Single revision bump for all writes
                    cursor.execute(f"""
                        UPDATE {self._table('sync_metadata')}
                        SET int_value = LAST_INSERT_ID(int_value + %s)
                        WHERE key_name = 'global_rev'
                    """, (self._batch_write_count,))
                    
                    conn.commit()
                    
                    cursor.execute("SELECT LAST_INSERT_ID()")
                    row = cursor.fetchone()
                    assert row is not None
                    self._batch_final_rev = row[0]
                finally:
                    cursor.close()
            except Exception:
                log.exception(
                    "Batch finalize failed",
                    event="shareddb.batch_finalize_error",
                    write_count=self._batch_write_count
                )
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
        
        # Log batch summary
        if stats['count'] > 0 or stats['skipped'] > 0:
            avg_ms = stats['total_ms'] / stats['count'] if stats['count'] > 0 else 0
            log.debug(
                "Batch write complete",
                event="shareddb.batch_complete",
                writes=stats['count'],
                skipped=stats['skipped'],
                slow_writes=stats['slow_count'],
                threshold_ms=SLOW_WRITE_THRESHOLD_MS,
                avg_ms=round(avg_ms, 1),
                max_ms=round(stats['max_ms'], 1),
                total_ms=round(stats['total_ms'], 1),
                final_rev=self._batch_final_rev
            )
    
    def _get_connection(self) -> "Connection":
        """
        Get or create database connection with reconnect support.
        
        After a reconnect (either via ping or fresh _connect), the
        database session state is lost. Re-selects the EasyTV database
        when schema was previously initialized.
        
        Returns:
            Active database connection.
        
        Raises:
            Exception: If connection cannot be established.
        """
        if self._conn is None:
            self._connect()
        else:
            try:
                self._conn.ping(reconnect=True)
            except Exception:
                log.info("Reconnecting to database", event="shareddb.reconnect")
                self._connect()
            # After ping(reconnect=True) or _connect() on an already-initialized
            # instance, the new TCP session has no database selected. Re-select it.
            self._ensure_db_selected()
        assert self._conn is not None
        return self._conn
    
    def _ensure_db_selected(self) -> None:
        """
        Re-select the EasyTV database after a connection reconnect.
        
        ping(reconnect=True) silently re-establishes the TCP connection
        and re-authenticates, but the new session has no database selected.
        Similarly, _connect() skips _initialize_schema() when
        _schema_initialized is already True. In both cases, queries using
        unqualified table names fail with error 1046 ("No database selected").
        
        This method restores the session-level database selection. It is a
        no-op before initial schema setup (when _easytv_db_name is empty).
        """
        if self._schema_initialized and self._easytv_db_name and self._conn:
            try:
                self._conn.select_db(self._easytv_db_name)
            except Exception as e:
                log.warning(
                    "Failed to re-select database after reconnect",
                    event="shareddb.reselect_error",
                    database=self._easytv_db_name,
                    error=str(e)
                )
    
    def _connect(self) -> None:
        """
        Establish connection to the database.
        
        Parses advancedsettings.xml to get connection parameters,
        connects to MySQL/MariaDB, and initializes schema if needed.
        
        Raises:
            ImportError: If pymysql is not available.
            RuntimeError: If no MySQL configuration found in advancedsettings.xml.
            Exception: If connection fails.
        """
        try:
            import pymysql
        except ImportError:
            raise ImportError("pymysql not available")
        
        if self._config is None:
            self._config = self._parse_advancedsettings()
            if self._config is None:
                raise RuntimeError(
                    "No MySQL video database configuration found in advancedsettings.xml"
                )
        
        self._conn = pymysql.connect(
            host=self._config['host'],
            port=self._config['port'],
            user=self._config['user'],
            password=self._config['password'],
            charset='utf8mb4',
            autocommit=False
        )
        
        log.info("Connected to database",
                event="shareddb.connect",
                host=self._config['host'],
                port=self._config['port'])
        
        # Initialize schema on first connection
        if not self._schema_initialized:
            self._initialize_schema()
            self._schema_initialized = True
            log.debug("Schema initialization complete, returning connection",
                     event="shareddb.connect_complete",
                     use_separate_db=self._use_separate_db,
                     table_prefix=self._table_prefix,
                     db_name=self._easytv_db_name)
    
    def _parse_advancedsettings(self) -> Optional[Dict[str, Any]]:
        """
        Parse MySQL config from advancedsettings.xml.
        
        Checks multiple paths in order of preference to find Kodi's
        video database configuration.
        
        Returns:
            Dictionary with host, port, user, password, name keys,
            or None if no configuration found.
        """
        for path in self.ADVANCEDSETTINGS_PATHS:
            real_path = xbmcvfs.translatePath(path)
            if xbmcvfs.exists(real_path):
                try:
                    tree = ET.parse(real_path)
                    root = tree.getroot()
                    video_db = root.find('.//videodatabase')
                    if video_db is not None:
                        # Extract type - only proceed for mysql
                        db_type = video_db.findtext('type', '').lower()
                        if db_type != 'mysql':
                            continue
                        
                        config = {
                            'host': video_db.findtext('host', 'localhost'),
                            'port': int(video_db.findtext('port', '3306')),
                            'user': video_db.findtext('user', 'kodi'),
                            'password': video_db.findtext('pass', ''),
                            'name': video_db.findtext('name', KODI_DEFAULT_VIDEO_DB_NAME),
                        }
                        log.debug("Found advancedsettings.xml",
                                 event="shareddb.config_found",
                                 path=path,
                                 host=config['host'],
                                 name=config['name'])
                        return config
                except Exception as e:
                    log.warning("Failed to parse advancedsettings.xml",
                               event="shareddb.config_error",
                               path=path, error=str(e))
        
        return None
    
    def _find_kodi_video_database(self, base_name: Optional[str] = None) -> Optional[str]:
        """
        Find the actual Kodi video database name.
        
        Kodi creates databases as {base_name}{version}, e.g.:
        - Default: MyVideos131 (Kodi 21 Omega)
        - Custom <name>mastervideo</name>: mastervideo131
        
        Uses numeric sorting to find the highest version (e.g., 131 > 99).
        
        Args:
            base_name: The database base name from advancedsettings.xml,
                      or None for default (MyVideos).
        
        Returns:
            The actual database name (highest version found), or None if not found.
        """
        if not base_name:
            base_name = KODI_DEFAULT_VIDEO_DB_NAME
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Query for databases matching the base name pattern
            cursor.execute("SHOW DATABASES LIKE %s", (f"{base_name}%",))
            databases = [row[0] for row in cursor.fetchall()]
            
            if not databases:
                log.warning("No Kodi video database found",
                           event="shareddb.no_video_db",
                           base_name=base_name)
                return None
            
            def extract_version(db_name: str) -> int:
                """Extract trailing numeric version from database name."""
                match = re.search(r'(\d+)$', db_name)
                return int(match.group(1)) if match else 0
            
            # Use max() with key function for correct numeric comparison
            best_db = max(databases, key=extract_version)
            best_version = extract_version(best_db)
            
            log.debug("Found Kodi video database",
                     event="shareddb.found_video_db",
                     database=best_db,
                     version=best_version,
                     candidates_count=len(databases))
            
            return best_db
            
        finally:
            cursor.close()
    
    def _initialize_schema(self) -> None:
        """
        Create EasyTV tables, with fallback to Kodi video database.
        
        Strategy:
            1. Try to create namespaced 'easytv_{kodi_base_name}' database
            2. If ANY step fails (CREATE DATABASE, CREATE TABLE, INSERT), 
               fall back to tables in Kodi's video database
        """
        with log_timing(log, "shareddb.schema_init"):
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get Kodi DB base name for namespacing
            assert self._config is not None
            kodi_base_name = self._config.get('name', KODI_DEFAULT_VIDEO_DB_NAME).lower()
            easytv_db_name = f"{EASYTV_DB_PREFIX}{kodi_base_name}"
            
            try:
                # Try to create our namespaced database AND initialize tables
                log.debug("Attempting to create/select easytv database",
                         event="shareddb.init_step", step="create_db")
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{easytv_db_name}`")
                conn.select_db(easytv_db_name)
                self._use_separate_db = True
                self._table_prefix = ""
                self._easytv_db_name = easytv_db_name
                
                # Create tables and initial data - if this fails, we fall back
                log.debug("Creating tables",
                         event="shareddb.init_step", step="create_tables")
                self._create_tables(cursor)
                
                # Probe write: verify we actually have INSERT/UPDATE access
                # This catches the case where DB exists but user lacks privileges
                # Use INSERT...ON DUPLICATE KEY which requires INSERT privilege
                log.debug("Probing write access",
                         event="shareddb.init_step", step="probe_write")
                cursor.execute(f"""
                    INSERT INTO {self._table('sync_metadata')} 
                    (key_name, int_value) VALUES ('_probe', 0)
                    ON DUPLICATE KEY UPDATE int_value = 0
                """)
                # Clean up probe row
                cursor.execute(f"""
                    DELETE FROM {self._table('sync_metadata')} 
                    WHERE key_name = '_probe'
                """)
                
                log.debug("Committing transaction",
                         event="shareddb.init_step", step="commit")
                conn.commit()
                
                # Run schema migrations - also inside try to catch permission errors
                log.debug("Running schema migrations",
                         event="shareddb.init_step", step="migrate")
                self._migrate_schema()
                
                log.debug("Schema init try block completed successfully",
                         event="shareddb.init_step", step="try_complete")
                
                log.info("Using separate easytv database",
                        event="shareddb.init_separate",
                        database=easytv_db_name)
                
            except Exception as e:
                # Permission denied at some step - fall back to Kodi video database
                log.info("Cannot use separate easytv database, falling back to Kodi video DB",
                        event="shareddb.init_fallback",
                        error=str(e))
                
                # Rollback any partial work
                try:
                    conn.rollback()
                except Exception:
                    pass
                
                # Reset state for fallback
                self._use_separate_db = False
                self._table_prefix = EASYTV_TABLE_PREFIX
                
                # Find the actual Kodi video database using the base name
                assert self._config is not None
                kodi_video_db = self._find_kodi_video_database(self._config.get('name'))
                if not kodi_video_db:
                    cursor.close()
                    raise RuntimeError(
                        f"Could not find Kodi video database with base name "
                        f"'{self._config.get('name', KODI_DEFAULT_VIDEO_DB_NAME)}'"
                    )
                
                # Use select_db() instead of f-string SQL to avoid injection risks
                conn.select_db(kodi_video_db)
                self._easytv_db_name = kodi_video_db
                
                # Create tables in Kodi video database with prefix
                self._create_tables(cursor)
                conn.commit()
                
                # Run migrations for fallback DB too
                self._migrate_schema()
                
                log.info("Using Kodi video database with prefix",
                        event="shareddb.init_prefixed",
                        database=kodi_video_db,
                        prefix=self._table_prefix)
            
            cursor.close()
    
    def _create_tables(self, cursor: Any) -> None:
        """
        Create the required tables for sync.
        
        Args:
            cursor: Database cursor to use for execution.
        """
        # Create show_tracking table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table('show_tracking')} (
                show_id           INT PRIMARY KEY,
                show_title        VARCHAR(255) NOT NULL,
                show_year         INT,
                ondeck_episode_id INT NOT NULL,
                ondeck_list       JSON,
                offdeck_list      JSON,
                watched_count     INT DEFAULT 0,
                unwatched_count   INT DEFAULT 0,
                updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_title_year (show_title, show_year),
                INDEX idx_updated (updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Create sync_metadata table with BIGINT UNSIGNED for revision
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table('sync_metadata')} (
                key_name   VARCHAR(50) PRIMARY KEY,
                int_value  BIGINT UNSIGNED DEFAULT 0,
                str_value  VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Initialize global_rev if not exists
        cursor.execute(f"""
            INSERT IGNORE INTO {self._table('sync_metadata')} 
            (key_name, int_value) VALUES ('global_rev', 0)
        """)
        
        # Initialize schema_version if not exists
        cursor.execute(f"""
            INSERT IGNORE INTO {self._table('sync_metadata')} 
            (key_name, int_value) VALUES ('schema_version', %s)
        """, (EASYTV_SCHEMA_VERSION,))
    
    def _table(self, name: str) -> str:
        """
        Get the full table name with optional prefix.
        
        Args:
            name: Base table name (e.g., 'show_tracking').
        
        Returns:
            Full table name with prefix if using fallback mode.
        """
        return f"{self._table_prefix}{name}"
    
    def _migrate_schema(self) -> None:
        """
        Apply schema migrations if needed.
        
        Checks current schema version and applies any pending migrations.
        Currently a placeholder for future schema changes.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT int_value FROM {self._table('sync_metadata')}
                WHERE key_name = 'schema_version'
            """)
            row = cursor.fetchone()
            current_version = int(row[0]) if row else 0
            
            if current_version >= EASYTV_SCHEMA_VERSION:
                return
            
            log.info("Migrating schema",
                    event="shareddb.schema_migrate",
                    from_version=current_version,
                    to_version=EASYTV_SCHEMA_VERSION)
            
            # Future migrations go here:
            # if current_version < 2:
            #     self._migrate_v1_to_v2(cursor)
            #     current_version = 2
            
            # Update version marker
            cursor.execute(f"""
                INSERT INTO {self._table('sync_metadata')} (key_name, int_value)
                VALUES ('schema_version', %s)
                ON DUPLICATE KEY UPDATE int_value = VALUES(int_value)
            """, (EASYTV_SCHEMA_VERSION,))
            
            conn.commit()
            
        finally:
            cursor.close()
    
    # =========================================================================
    # Read Operations
    # =========================================================================
    
    def get_global_rev(self) -> int:
        """
        Get current global revision. Fast scalar query (~0.5ms).
        
        Commits any pending transaction first to ensure we see the latest
        data written by other instances (required due to autocommit=False
        and MariaDB's REPEATABLE READ isolation level).
        
        Returns:
            The current global revision number, or 0 if not set.
        """
        conn = self._get_connection()
        # End any implicit transaction to get a fresh snapshot
        # Without this, we'd see stale data from when the connection
        # first started reading (REPEATABLE READ isolation)
        conn.commit()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                SELECT int_value FROM {self._table('sync_metadata')} 
                WHERE key_name = 'global_rev'
            """)
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            cursor.close()
    
    def get_show_tracking(self, show_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tracking data for a single show.
        
        Commits any pending transaction first to ensure we see the latest
        data written by other instances.
        
        Args:
            show_id: The Kodi TV show ID.
        
        Returns:
            Dictionary with show data, or None if not found.
        """
        conn = self._get_connection()
        # End any implicit transaction to get a fresh snapshot
        conn.commit()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT show_title, show_year, ondeck_episode_id,
                       ondeck_list, offdeck_list, watched_count, unwatched_count
                FROM {self._table('show_tracking')}
                WHERE show_id = %s
            """, (show_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'show_title': row[0],
                'show_year': row[1],
                'ondeck_episode_id': row[2],
                'ondeck_list': json.loads(row[3] or '[]'),
                'offdeck_list': json.loads(row[4] or '[]'),
                'watched_count': row[5],
                'unwatched_count': row[6],
            }
            
        finally:
            cursor.close()
    
    def get_show_tracking_bulk_with_rev(
        self,
        show_ids: List[int]
    ) -> Tuple[Dict[int, Dict[str, Any]], int]:
        """
        Bulk fetch show tracking data with consistent revision snapshot.
        
        Uses CROSS JOIN to get revision and data in a single query,
        ensuring consistency even if a write happens during the read.
        
        Commits any pending transaction first to ensure we see the latest
        data written by other instances.
        
        Args:
            show_ids: List of Kodi TV show IDs to fetch.
        
        Returns:
            Tuple of (data_dict, revision_at_time_of_read) where:
                - data_dict: {show_id: {show data}}
                - revision: The global_rev at time of read
        """
        if not show_ids:
            return {}, self.get_global_rev()
        
        with log_timing(log, "shareddb.bulk_read", show_count=len(show_ids)):
            try:
                import pymysql.cursors
            except ImportError:
                log.warning("pymysql.cursors not available for bulk read",
                            event="shareddb.import_error")
                return {}, 0
            
            conn = self._get_connection()
            # End any implicit transaction to get a fresh snapshot
            # Without this, we'd see stale data from when the connection
            # first started reading (REPEATABLE READ isolation)
            conn.commit()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            try:
                placeholders = ",".join(["%s"] * len(show_ids))
                
                # Single query with CROSS JOIN for consistent snapshot
                cursor.execute(f"""
                    SELECT st.*, m.int_value AS current_rev
                    FROM {self._table('show_tracking')} st
                    CROSS JOIN (
                        SELECT int_value FROM {self._table('sync_metadata')} 
                        WHERE key_name = 'global_rev'
                    ) m
                    WHERE st.show_id IN ({placeholders})
                """, show_ids)
                
                rows = cursor.fetchall()
                
                # Extract revision from first row, or query separately if no results
                if rows:
                    revision = rows[0]['current_rev']
                else:
                    revision = self.get_global_rev()
                
                # Build result dict
                result = {}
                for row in rows:
                    show_id = row['show_id']
                    result[show_id] = {
                        'show_title': row['show_title'],
                        'show_year': row['show_year'],
                        'ondeck_episode_id': row['ondeck_episode_id'],
                        'ondeck_list': json.loads(row['ondeck_list'] or '[]'),
                        'offdeck_list': json.loads(row['offdeck_list'] or '[]'),
                        'watched_count': row['watched_count'],
                        'unwatched_count': row['unwatched_count'],
                    }
                
                return result, revision
                
            finally:
                cursor.close()
    
    def get_all_stored_shows(self) -> Dict[int, Tuple[str, Optional[int]]]:
        """
        Get all stored shows with their title and year.
        
        Used for ID validation/migration when library is rebuilt.
        Commits any pending transaction first to ensure we see the latest data.
        
        Returns:
            Dictionary mapping show_id to (title, year) tuple.
        """
        conn = self._get_connection()
        conn.commit()  # Fresh snapshot
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT show_id, show_title, show_year
                FROM {self._table('show_tracking')}
            """)
            
            return {
                row[0]: (row[1], row[2])
                for row in cursor.fetchall()
            }
            
        finally:
            cursor.close()
    
    def is_empty(self) -> bool:
        """
        Check if database has no show tracking data.
        
        Returns:
            True if no shows are stored, False otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {self._table('show_tracking')}")
            row = cursor.fetchone()
            assert row is not None
            return row[0] == 0
        finally:
            cursor.close()
    
    # =========================================================================
    # Write Operations
    # =========================================================================
    
    def set_show_tracking(self, show_id: int, data: Dict[str, Any]) -> int:
        """
        Store show tracking data with atomic revision increment.
        
        Uses LAST_INSERT_ID(expr) pattern to atomically increment revision
        and capture the new value without an extra query.
        
        In batch mode (within a batch_write() context):
        - Executes the UPSERT SQL but defers the revision UPDATE and commit
          to _batch_finalize(), which performs a single commit for all writes
        - Returns _batch_current_rev as a sentinel value
        - Individual DEBUG logs are suppressed unless slow (≥50ms)
        
        Outside batch mode:
        - Executes UPSERT + revision UPDATE + commit immediately
        - Returns the new global revision
        
        Args:
            show_id: The Kodi TV show ID.
            data: Dictionary containing:
                - show_title: str
                - show_year: int (optional)
                - ondeck_episode_id: int
                - ondeck_list: List[int] (optional)
                - offdeck_list: List[int] (optional)
                - watched_count: int (optional)
                - unwatched_count: int (optional)
        
        Returns:
            The new global revision after this write, or _batch_current_rev
            in batch mode (sentinel — real revision set by _batch_finalize).
        
        Raises:
            Exception: If write fails (connection rolls back).
        """
        # Skip unchanged writes in batch mode with preload
        if self._batch_active and self._batch_preload is not None:
            existing = self._batch_preload.get(show_id)
            if existing and existing['ondeck_episode_id'] == data['ondeck_episode_id']:
                self._batch_stats['skipped'] += 1
                return self._batch_current_rev
        
        if 'ondeck_episode_id' not in data:
            raise ValueError("set_show_tracking: missing required field 'ondeck_episode_id'")

        start_time = time.time()
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Upsert show data
            sql = f"""
                INSERT INTO {self._table('show_tracking')}
                    (show_id, show_title, show_year, ondeck_episode_id, 
                     ondeck_list, offdeck_list, watched_count, unwatched_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    show_title = VALUES(show_title),
                    show_year = VALUES(show_year),
                    ondeck_episode_id = VALUES(ondeck_episode_id),
                    ondeck_list = VALUES(ondeck_list),
                    offdeck_list = VALUES(offdeck_list),
                    watched_count = VALUES(watched_count),
                    unwatched_count = VALUES(unwatched_count)
            """
            cursor.execute(sql, (
                show_id,
                data.get('show_title', ''),
                data.get('show_year'),
                data['ondeck_episode_id'],
                json.dumps(data.get('ondeck_list', [])),
                json.dumps(data.get('offdeck_list', [])),
                data.get('watched_count', 0),
                data.get('unwatched_count', 0)
            ))
            
            # Calculate elapsed time
            elapsed_ms = (time.time() - start_time) * 1000
            is_slow = elapsed_ms >= SLOW_WRITE_THRESHOLD_MS
            
            if self._batch_active:
                # Batch mode: defer revision bump and commit to _batch_finalize
                self._batch_write_count += 1
                self._batch_stats['count'] += 1
                self._batch_stats['total_ms'] += elapsed_ms
                self._batch_stats['max_ms'] = max(
                    self._batch_stats['max_ms'], elapsed_ms
                )
                if is_slow:
                    self._batch_stats['slow_count'] += 1
                    log.debug("Slow write detected",
                             event="shareddb.write_slow",
                             show_id=show_id,
                             elapsed_ms=round(elapsed_ms, 1),
                             threshold_ms=SLOW_WRITE_THRESHOLD_MS)
                return self._batch_current_rev
            
            # Non-batch: immediate revision bump and commit
            cursor.execute(f"""
                UPDATE {self._table('sync_metadata')} 
                SET int_value = LAST_INSERT_ID(int_value + 1) 
                WHERE key_name = 'global_rev'
            """)
            
            conn.commit()
            
            cursor.execute("SELECT LAST_INSERT_ID()")
            row = cursor.fetchone()
            assert row is not None
            new_rev = row[0]
            
            log.debug("Show tracking saved",
                     event="shareddb.write",
                     show_id=show_id,
                     new_revision=new_rev,
                     elapsed_ms=round(elapsed_ms, 1))
            
            return new_rev
                     
        except Exception as e:
            conn.rollback()
            SharedDatabase._last_failure_time = time.time()
            # Always log errors, regardless of batch mode
            log.warning("Failed to save show tracking",
                       event="shareddb.write_error",
                       show_id=show_id,
                       error=str(e))
            raise
        finally:
            cursor.close()
    
    def delete_show_tracking(self, show_ids: List[int]) -> int:
        """
        Delete tracking data for specified shows.
        
        Args:
            show_ids: List of show IDs to delete.
        
        Returns:
            Number of rows deleted.
        """
        if not show_ids:
            return 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            placeholders = ",".join(["%s"] * len(show_ids))
            cursor.execute(f"""
                DELETE FROM {self._table('show_tracking')}
                WHERE show_id IN ({placeholders})
            """, show_ids)
            
            deleted = cursor.rowcount
            conn.commit()
            
            log.debug("Deleted show tracking",
                     deleted_count=deleted,
                     show_ids=show_ids[:5])  # Log first 5 for brevity
            
            return deleted
            
        finally:
            cursor.close()
    
    def migrate_show_id(
        self,
        old_id: int,
        new_id: int,
        clear_episode_lists: bool = True
    ) -> bool:
        """
        Migrate a show's tracking data to a new ID.
        
        Used when library rebuild causes show IDs to shift.
        Optionally clears episode lists since episode IDs also shift.
        
        Args:
            old_id: The previous show ID.
            new_id: The new show ID.
            clear_episode_lists: If True, clear ondeck_list and offdeck_list
                                (episode IDs are also invalid after rebuild).
        
        Returns:
            True if migration succeeded, False if old_id not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if clear_episode_lists:
                # Update ID and clear episode lists
                cursor.execute(f"""
                    UPDATE {self._table('show_tracking')}
                    SET show_id = %s, ondeck_list = '[]', offdeck_list = '[]'
                    WHERE show_id = %s
                """, (new_id, old_id))
            else:
                # Just update ID
                cursor.execute(f"""
                    UPDATE {self._table('show_tracking')}
                    SET show_id = %s
                    WHERE show_id = %s
                """, (new_id, old_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                log.info("Migrated show ID",
                        event="shareddb.id_migrated",
                        old_id=old_id,
                        new_id=new_id,
                        cleared_episodes=clear_episode_lists)
            
            return success
            
        finally:
            cursor.close()
    
    def validate_and_migrate_ids(
        self,
        current_shows: Dict[int, Tuple[str, Optional[int]]]
    ) -> Tuple[int, int, int]:
        """
        Validate stored show IDs against current Kodi library.
        
        Handles library rebuilds where show IDs may have shifted:
        - Shows with matching ID + title + year are considered valid
        - Shows with mismatched ID but matching title + year are migrated
        - Shows with no match in current library are orphaned and deleted
        
        For migrated shows, episode lists are cleared since episode IDs
        also shift during library rebuilds. The caller should trigger
        recomputation for these shows.
        
        Args:
            current_shows: Dictionary mapping current show IDs to (title, year).
                          This should come from the Kodi library query.
        
        Returns:
            Tuple of (migrated_count, orphaned_count, valid_count).
        """
        with log_timing(log, "shareddb.validate_ids", 
                       current_show_count=len(current_shows)):
            # Get all stored shows from database
            stored_shows = self.get_all_stored_shows()
            
            if not stored_shows:
                return 0, 0, 0
            
            # Build reverse lookup: (title_lower, year) -> new_id
            # Use lowercase title for case-insensitive matching
            title_year_to_new_id: Dict[Tuple[str, Optional[int]], int] = {
                (title.lower() if title else '', year): show_id
                for show_id, (title, year) in current_shows.items()
            }
            
            valid_count = 0
            migrated_count = 0
            orphaned_ids: List[int] = []
            
            for stored_id, (stored_title, stored_year) in stored_shows.items():
                # Check if stored ID still exists with same title+year
                if stored_id in current_shows:
                    current_title, current_year = current_shows[stored_id]
                    # Verify title matches (case-insensitive)
                    if (current_title and stored_title and 
                        current_title.lower() == stored_title.lower()):
                        # Valid: same ID, same title
                        valid_count += 1
                        continue
                
                # ID doesn't match - try to find by title+year
                lookup_key = (
                    stored_title.lower() if stored_title else '',
                    stored_year
                )
                new_id = title_year_to_new_id.get(lookup_key)
                
                if new_id is not None and new_id != stored_id:
                    # Found match with different ID - migrate
                    if self.migrate_show_id(stored_id, new_id, clear_episode_lists=True):
                        migrated_count += 1
                        log.info("Show ID migrated via title+year",
                                event="shareddb.id_recovered",
                                old_id=stored_id,
                                new_id=new_id,
                                title=stored_title,
                                year=stored_year)
                    else:
                        # Migration failed (shouldn't happen, but handle it)
                        orphaned_ids.append(stored_id)
                else:
                    # No match found - show was deleted from library
                    orphaned_ids.append(stored_id)
            
            # Delete orphaned shows
            if orphaned_ids:
                deleted = self.delete_show_tracking(orphaned_ids)
                log.info("Orphaned shows cleaned up",
                        event="shareddb.orphans_deleted",
                        orphaned_count=deleted,
                        orphaned_ids=orphaned_ids[:10])  # Log first 10
            
            orphaned_count = len(orphaned_ids)
            
            log.info("ID validation complete",
                    event="shareddb.validate_complete",
                    valid=valid_count,
                    migrated=migrated_count,
                    orphaned=orphaned_count)
            
            return migrated_count, orphaned_count, valid_count
    
    def clear_all_data(self) -> None:
        """
        Clear all EasyTV sync data from the database.
        
        Used for troubleshooting or when user wants to fully reset.
        Resets global_rev to 0 and removes all show tracking.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"DELETE FROM {self._table('show_tracking')}")
            cursor.execute(f"""
                UPDATE {self._table('sync_metadata')} 
                SET int_value = 0 
                WHERE key_name = 'global_rev'
            """)
            conn.commit()
            log.info("All sync data cleared", event="shareddb.clear")
        except Exception:
            conn.rollback()
            log.exception("Failed to clear sync data", event="shareddb.clear_error")
            raise
        finally:
            cursor.close()
    
    # =========================================================================
    # Migration Lock Operations
    # =========================================================================
    
    def try_claim_migration(self, instance_id: Optional[str] = None) -> bool:
        """
        Attempt to claim migration rights atomically.
        
        Uses conditional UPDATE + INSERT IGNORE with rowcount checks
        to ensure exactly one winner. Server-side time calculation
        avoids clock skew issues between clients.
        
        Args:
            instance_id: Unique identifier for this instance.
                        Defaults to hostname-pid.
        
        Returns:
            True if this instance should perform migration.
        """
        if instance_id is None:
            instance_id = f"{socket.gethostname()}-{os.getpid()}"
        
        with log_timing(log, "shareddb.migration_claim", instance_id=instance_id):
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Step 1: Try to steal a stale lock (atomic, server-side time)
                cursor.execute(f"""
                    UPDATE {self._table('sync_metadata')}
                    SET str_value = %s, updated_at = NOW()
                    WHERE key_name = 'migration_lock'
                      AND updated_at < NOW() - INTERVAL %s MINUTE
                """, (instance_id, EASYTV_MIGRATION_LOCK_TTL_MINUTES))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    log.warning("Stole stale migration lock",
                               event="shareddb.migration_lock_stolen",
                               instance_id=instance_id,
                               ttl_minutes=EASYTV_MIGRATION_LOCK_TTL_MINUTES)
                    return True
                
                # Step 2: Try to create new lock (only succeeds if no row exists)
                cursor.execute(f"""
                    INSERT IGNORE INTO {self._table('sync_metadata')} 
                    (key_name, str_value, updated_at)
                    VALUES ('migration_lock', %s, NOW())
                """, (instance_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    log.info("Claimed migration lock",
                            event="shareddb.migration_claimed",
                            instance_id=instance_id)
                    return True
                
                # Lock exists and is fresh - someone else has it
                conn.rollback()  # Release any implicit locks
                log.info("Migration in progress by another instance",
                        event="shareddb.migration_skipped")
                return False
                
            finally:
                cursor.close()
    
    def release_migration_lock(self) -> None:
        """Release migration lock after completion."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                DELETE FROM {self._table('sync_metadata')}
                WHERE key_name = 'migration_lock'
            """)
            conn.commit()
            log.info("Released migration lock", event="shareddb.migration_complete")
        finally:
            cursor.close()
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            log.debug("Database connection closed")
    
    @property
    def easytv_db_name(self) -> str:
        """Get the name of the EasyTV database being used."""
        return self._easytv_db_name
    
    @property
    def is_using_separate_db(self) -> bool:
        """Check if using separate easytv database vs prefixed tables."""
        return self._use_separate_db

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
Clear sync data script for EasyTV.

Invoked from settings action button to clear all EasyTV sync data
from the shared database. Shows confirmation dialog before clearing
and displays success/failure notification.

Logging:
    Module: clear_sync
    Events:
        - sync.clear_requested (INFO): User initiated clear
        - sync.clear_success (INFO): Data cleared successfully
        - sync.clear_failed (WARNING): Clear operation failed
        - sync.clear_cancelled (INFO): User cancelled operation
"""
from __future__ import annotations

import xbmcgui

from resources.lib.utils import get_logger, lang

log = get_logger('clear_sync')


def main() -> None:
    """
    Main entry point for clearing sync data.
    
    Shows confirmation dialog, then clears all EasyTV data from the
    shared database if confirmed. Shows notification with result.
    """
    dialog = xbmcgui.Dialog()
    
    log.info("Clear sync data requested", event="sync.clear_requested")
    
    # Confirmation dialog
    # 32705 = "Clear sync data?"
    # 32706 = "This will remove all EasyTV tracking data..."
    if not dialog.yesno(lang(32705), lang(32706)):
        log.info("Clear sync data cancelled by user", event="sync.clear_cancelled")
        return
    
    try:
        # Import here to avoid loading database modules unless needed
        from resources.lib.data.shared_db import SharedDatabase
        
        db = SharedDatabase()
        
        if not db.is_available():
            # 32709 = "Database is not available..."
            dialog.notification("EasyTV", lang(32709), xbmcgui.NOTIFICATION_WARNING)
            log.warning("Database unavailable for clear operation",
                       event="sync.clear_failed",
                       reason="database_unavailable")
            return
        
        # Clear all data
        db.clear_all_data()
        
        # Also clear local revision to force refresh
        window = xbmcgui.Window(10000)
        window.clearProperty("EasyTV.sync_rev")
        
        # Close database connection
        db.close()
        
        # Success notification
        # 32707 = "Sync data cleared"
        dialog.notification("EasyTV", lang(32707), xbmcgui.NOTIFICATION_INFO)
        log.info("Sync data cleared successfully", event="sync.clear_success")
        
    except ImportError:
        # pymysql not available
        # 32708 = "Failed to clear sync data"
        dialog.notification("EasyTV", lang(32708), xbmcgui.NOTIFICATION_ERROR)
        log.warning("Clear sync data failed - pymysql not available",
                   event="sync.clear_failed",
                   reason="pymysql_missing")
        
    except Exception as e:
        # 32708 = "Failed to clear sync data"
        dialog.notification("EasyTV", lang(32708), xbmcgui.NOTIFICATION_ERROR)
        log.exception("Clear sync data failed",
                     event="sync.clear_failed",
                     error=str(e))


if __name__ == "__main__":
    main()

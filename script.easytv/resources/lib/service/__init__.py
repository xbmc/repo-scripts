#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Background Service Components.

This package provides the background service functionality:
- daemon.py: Main service loop and initialization
- playback_monitor.py: PlaybackMonitor class (tracks playback state)
- library_monitor.py: LibraryMonitor class (responds to library/settings changes)
- episode_tracker.py: Episode state machine (next episode caching)
- settings.py: Settings management and persistence
"""

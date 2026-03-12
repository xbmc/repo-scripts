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
EasyTV Playback Generation Components.

This package provides playlist building functionality:
- random_player.py: Random playlist builder (channel surfing mode)
- browse_mode.py: Browse mode orchestrator (episode list display + playback)
- browse_player.py: BrowseModePlayer class (playback from browse window)
- playlist_session.py: Lazy queue state management for Both mode playlists
"""

from resources.lib.playback.playlist_session import PlaylistSession

__all__ = ['PlaylistSession']

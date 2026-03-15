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
EasyTV Background Service Entry Point.

Monitors playback, updates episode tracking, and provides next episode prompts.
Modernized for Kodi 21+ (Nexus/Omega).

Logging:
    Module: service
    Events:
        - service.start (INFO): Service has started
        - service.stop (INFO): Service has stopped
"""

import xbmc
import xbmcaddon
from resources.lib.utils import get_logger, parse_version, StructuredLogger
from resources.lib.service.daemon import ServiceDaemon


def _get_device_name() -> str:
    """Get device identifier for logging. Prefers friendly name, falls back to hostname."""
    friendly = xbmc.getInfoLabel('System.FriendlyName')
    if friendly:
        return friendly
    # Fallback to hostname if friendly name not set
    import socket
    try:
        return socket.gethostname()
    except Exception:
        return 'unknown'


def _get_kodi_version() -> str:
    """Get Kodi version string (e.g., '21.1')."""
    # BuildVersion format: "21.1 (21.1.0) Git:..." - extract first part
    build = xbmc.getInfoLabel('System.BuildVersion')
    if build:
        return build.split()[0]
    return 'unknown'


if __name__ == "__main__":
    addon = xbmcaddon.Addon()
    version_str = addon.getAddonInfo('version')
    version = parse_version(version_str)
    log = get_logger('service')

    # Startup banner with device identification for multi-instance debugging
    log.info(
        "Service started",
        event="service.start",
        version=version_str,
        device=_get_device_name(),
        kodi=_get_kodi_version()
    )

    daemon = ServiceDaemon(addon=addon, logger=log)
    daemon.load_initial_settings()
    daemon.initialize()
    daemon.run()

    log.info(
        "Service stopped",
        event="service.stop",
        version=version_str,
        device=_get_device_name()
    )
    StructuredLogger.shutdown()

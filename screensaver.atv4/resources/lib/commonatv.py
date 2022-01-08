"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo("path")
addon_icon = addon.getAddonInfo("icon")
dialog = xbmcgui.Dialog()


def translate(text):
    return addon.getLocalizedString(text)


def notification(header, message, time=2000, icon=addon_icon,
                 sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


# Given a block and a set of keys to check, return the first one we find a nonempty value for
def find_ranked_key_in_dict(dict, key_list):
    for key in key_list:
        if key in dict:
            return dict[key]
    # Explicitly return None if no value exists
    return None


# Compute the struct where we'll keep the preferred URL key ordering. The earlier we append, the higher the priority
def compute_block_key_list(enable_4k, enable_hdr, enable_hevc):
    block_key_list = []
    # Possible URL keys are "url-1080-H264","url-1080-SDR","url-1080-HDR","url-4K-SDR","url-4K-HDR"
    if enable_hevc:
        if enable_hdr and enable_4k:
            # We have all features. Get 4K HDR/SDR first, then 1080 HDR/SDR, then H264
            block_key_list.append("url-4K-HDR")
            block_key_list.append("url-4K-SDR")
            block_key_list.append("url-1080-HDR")
        if enable_hdr and not enable_4k:
            # We have all HDR but not 4K. Get 1080 HDR/SDR, then H264
            block_key_list.append("url-1080-HDR")
        if enable_4k and not enable_hdr:
            # We have all 4K but not HDR. Get 4K SDR, then 1080 SDR, then H264
            block_key_list.append("url-4K-SDR")
        # We don't have 4K or HDR. Get 1080 SDR, then H264
        block_key_list.append("url-1080-SDR")

    # Always check H264 as the default option
    block_key_list.append("url-1080-H264")
    return block_key_list

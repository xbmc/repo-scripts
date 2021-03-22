"""
   Copyright (C) 2015- enen92
   This file is part of screensaver.atv4 - https://github.com/enen92/screensaver.atv4

   SPDX-License-Identifier: GPL-2.0-only
   See LICENSE for more information.
"""

import xbmc
import xbmcvfs

from .commonatv import dialog, addon, translate, find_ranked_key_in_dict, compute_block_key_list
from .downloader import Downloader
from .playlist import AtvPlaylist

# Array of "All" plus each unique "accessibilityLabel" in entries.json
# Used in a popup to allow the user to choose what to download
# Sort the locations list alphabetically and in place
locations = sorted(["All", "Italy to Asia", "Iran and Afghanistan", "Dubai", "Africa and the Middle East",
                    "California to Vegas", "Southern California to Baja", "China", "Antarctica", "Liwa",
                    "Sahara and Italy",
                    "Los Angeles", "San Francisco", "London", "Ireland to Asia", "New York", "West Africa to the Alps",
                    "New Zealand", "Caribbean Day", "Hawaii", "Caribbean", "Africa Night", "North America Aurora",
                    "New York Night", "Greenland", "Hong Kong", "Korean and Japan Night"])


# Parse the JSON to get a list of URLs and download the files to the download folder
def offline():
    # NOTE: the download folder must be saved by pushing OK in the settings dialog before this will succeed
    if addon.getSetting("download-folder") and xbmcvfs.exists(addon.getSetting("download-folder")):
        # Present a popup to the user and allow them to select a single location to download, or all
        locations_chosen_index = dialog.select(translate(32014), locations)
        if locations_chosen_index > -1:
            # Initialize the Playlist class, and get the JSON containing URLs
            top_level_json = AtvPlaylist().get_playlist_json()
            download_list = []
            if top_level_json:

                # Parse the H264, HDR, and 4K settings to determine URL preference.
                block_key_list = compute_block_key_list(addon.getSettingBool("enable-4k"),
                                                        addon.getSettingBool("enable-hdr"),
                                                        addon.getSettingBool("enable-hevc"))

                # Top-level JSON has assets array, initialAssetCount, version. Inspect each block in assets
                for block in top_level_json["assets"]:

                    # If the chosen location was a specific place and not All
                    if not locations[locations_chosen_index] == "All":
                        # Each block contains a location whose name is stored in accessibilityLabel. These may recur
                        # Get the location from the current block
                        location = block["accessibilityLabel"]
                        # Exit block processing early if the location didn't match our preference.
                        # This prevents the location from being added to the download list
                        if not locations[locations_chosen_index] == location:
                            xbmc.log("Current location {} is not chosen location, skipping download".format(location),
                                     level=xbmc.LOGDEBUG)
                            continue

                    # Get the URL to download
                    url = find_ranked_key_in_dict(block, block_key_list)

                    # If the URL contains HTTPS, we need revert to HTTP to avoid bad SSL cert
                    # NOTE: Old Apple URLs were HTTP, new URLs are HTTPS with a bad cert
                    if "https" in url:
                        url = url.replace("https://", "http://")
                    download_list.append(url)

            # call downloader if the download_list has been populated
            if download_list:
                Downloader().download_videos_from_urls(download_list)
            else:
                dialog.ok(translate(32000), translate(32012))
    else:
        dialog.ok(translate(32000), translate(32013))

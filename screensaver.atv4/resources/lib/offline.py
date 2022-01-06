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
locations = ["All"] + sorted(["Africa and the Middle East", "Africa Night", "Alaskan Jellies", "Antarctica",
                              "Atlantic Ocean to Spain and France", "Australia", "Barracuda", "Bumpheads",
                              "California Dolphins", "California Kelp Forest", "California to Vegas", "Caribbean Day",
                              "Caribbean", "China", "Costa Rica Dolphins", "Cownose Rays", "Dubai", "Grand Canyon",
                              "Gray Reef Sharks", "Greenland", "Hawaii", "Hong Kong", "Humpback Whale", "Iceland",
                              "Iran and Afghanistan", "Ireland to Asia", "Italy to Asia", "Jacks", "Kelp",
                              "Korea and Japan Night", "Liwa", "London", "Los Angeles", "New York Night", "New York",
                              "New Zealand", "Nile Delta", "North America Aurora", "Palau Coral", "Palau Jellies",
                              "Patagonia", "Red Sea Coral", "Sahara and Italy", "San Francisco", "Scotland",
                              "Sea Stars", "Seals", "South Africa to North Asia", "Southern California to Baja",
                              "Tahiti Waves", "West Africa to the Alps", "Yosemite"])


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

                # Top-level JSON has assets array, initialAssetCount, categories, version.
                # Inspect each block in assets, the other sections are irrelevant to us
                for block in top_level_json["assets"]:
                    # Each block contains a location whose name is stored in accessibilityLabel. These may recur
                    # Get the location from the current block
                    location = block["accessibilityLabel"]

                    # If the chosen location was a specific place and not All, inspect each block
                    if not locations[locations_chosen_index] == "All":
                        # Exit block processing early if the location didn't match our preference.
                        # This prevents the location from being added to the download list
                        if not locations[locations_chosen_index] == location:
                            xbmc.log("Current location {} is not chosen location, skipping download".format(location),
                                     level=xbmc.LOGDEBUG)
                            continue

                    # Get the URL from the current block to download
                    url = find_ranked_key_in_dict(block, block_key_list)

                    # URL could be empty if the JSON didn't have a matching quality, so skip adding it in that case
                    if url:
                        # If the URL contains HTTPS, we need revert to HTTP to avoid bad SSL cert
                        # NOTE: Old Apple URLs were HTTP, new URLs are HTTPS with a bad cert
                        if "https" in url:
                            url = url.replace("https://", "http://")
                        download_list.append(url)
                    else:
                        xbmc.log("The needed quality does not exist for current location {}, skipping".format(location),
                                 level=xbmc.LOGDEBUG)

            # call downloader if the download_list has been populated
            if download_list:
                Downloader().download_videos_from_urls(download_list)
            else:
                dialog.ok(translate(32000), translate(32012))
    else:
        dialog.ok(translate(32000), translate(32013))

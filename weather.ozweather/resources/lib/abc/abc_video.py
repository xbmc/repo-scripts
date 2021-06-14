# -*- coding: utf-8 -*-
import requests
import re
import sys
import xbmc

# Small hack to allow for unit testing - see common.py for explanation
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')

from resources.lib.store import Store
from resources.lib.common import *


def get_abc_weather_video_link(quality):

    # Seems like the best/trw option has been removed, so just map these to 1000k
    if quality == "Best" or quality == "trw":
        quality = "1000k"

    try:
        r = requests.get(Store.ABC_URL)
        video = re.findall(Store.ABC_WEATHER_VIDEO_PATTERN, r.text)
        try:
            url = f'{Store.ABC_STUB}{video[0][0]}/WIN{video[0][1]}_{quality}.mp4'
            return url
        except Exception as inst:
            log("Couldn't get ABC video URL from scraped page: " + str(inst))
            return ""

    except Exception as inst:
        log("********** Couldn't get ABC video page at all: " + str(inst))
        return ""


# UNIT TESTING
if __name__ == "__main__":
    log("\nTesting scraping of ABC Weather Video - here's the 'Best' link:\n")
    log(get_abc_weather_video_link("Best") + "\n")


# ABC VIDEO URL NOTES
# note date and quality level variables...
# view source on https://www.abc.net.au/news/newschannel/weather-in-90-seconds/ and find mp4 to see this list, 
# the end of the URL can change regularly

# {'url': 'https://abcmedia.akamaized.net/news/news24/wins/201403/WINs_Weather1_0703_1000k.mp4', 'contentType': 'video/mp4', 'codec': 'AVC', 'bitrate': '928', 'width': '1024', 'height': '576', 'filesize': '11657344'}
# {'url': 'https://abcmedia.akamaized.net/news/news24/wins/201403/WINs_Weather1_0703_256k.mp4', 'contentType': 'video/mp4', 'codec': 'AVC', 'bitrate': '170', 'width': '320', 'height': '180', 'filesize': '2472086'}
# {'url': 'https://abcmedia.akamaized.net/news/news24/wins/201403/WINs_Weather1_0703_512k.mp4', 'contentType': 'video/mp4', 'codec': 'AVC', 'bitrate': '400', 'width': '512', 'height': '288', 'filesize': '5328218'}
# {'url': 'https://abcmedia.akamaized.net/news/news24/wins/201403/WINs_Weather1_0703_trw.mp4', 'contentType': 'video/mp4', 'codec': 'AVC', 'bitrate': '1780', 'width': '1280', 'height': '720', 'filesize': '21599356'}
# Other URLs - should match any of these
# https://abcmedia.akamaized.net/news/news24/wins/201409/WINm_Update1_0909_VSB03WF2_512k.mp4&
# https://abcmedia.akamaized.net/news/news24/wins/201409/WINs_Weather2_0209_trw.mp4


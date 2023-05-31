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


def scrape_and_play_abc_weather_video():
    """
    On-demand scrape the current ABC video URL and then play it back, with appropriate metadata/art etc.
    """
    url = get_abc_weather_video_link()
    # Construct an offscreen list item with metadata...
    item = xbmcgui.ListItem(path=url)
    item.setProperty('mimetype', 'video/mpeg')
    item.setInfo('Video', {	'title' : 'ABC Weather In 90 Seconds'})
    item.setArt({'thumb': f'{CWD}/resources/ABC.png'})
    # ...and then play it, fullscreen
    xbmc.Player().play(url, item, False)
    pass


# See bottom of this file for notes on matching the video links (& Store.py for the regex)
def get_abc_weather_video_link():

    try:
        r = requests.get(Store.ABC_URL)
        videos = re.findall(Store.ABC_WEATHER_VIDEO_PATTERN, r.text)

        # for video in videos:
        #     log(video)

        try:
            url = f'{Store.ABC_STUB}/{videos[1][0]}/{videos[1][1]}/{videos[1][2]}/{videos[1][3]}.mp4'
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
    log(get_abc_weather_video_link())


# > 2023_05 - CURRENT ABC VIDEO URL NOTES
# view the source on: https://www.abc.net.au/news/weather
# search for 'mp4'
# Regex in Store.py used to match the URL format
# Multiple matches will be found - first is a definition/download link (.mpg)
# 2nd is the highest quality stream (720p) - the one we want.
# https://mediacore-live-production.akamaized.net/video/01/im/Z/0m.mp4

# < 2023_05 - LEGACY INFO
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

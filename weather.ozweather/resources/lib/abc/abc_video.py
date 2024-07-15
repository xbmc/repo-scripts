# -*- coding: utf-8 -*-
import requests
import re
import sys
import xbmc
import json
from bs4 import BeautifulSoup

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
    item.setArt({'thumb': f'{CWD}/resources/weather-in-90-seconds.png'})
    # ...and then play it, fullscreen
    xbmc.Player().play(url, item, False)
    pass


# See bottom of this file for notes on matching the video links (& Store.py for the regex)
def get_abc_weather_video_link():

    try:
        r = requests.get(Store.ABC_URL)

        bs = BeautifulSoup(r.text, "html.parser")
        json_string = bs.find("script", {'type': 'application/json',"id": "__NEXT_DATA__"})

        json_object = json.loads(json_string.string)

        # log(json_object)
        # Put the json blob into: https://jsonhero.io/j/JU0I9LB4AlLU
        # Gives a path to the needed video as:
        # $.props.pageProps.channelpage.components.0.component.props.list.3.player.config.sources.1.file
        # Rather than grab the URL directly (as place in array might change), grab all the available URLs and get the best quality from it
        # See: https://github.com/bossanova808/weather.ozweather/commit/e6158d704fc160808bf66220da711805860d85c7
        data = json_object['props']['pageProps']['channelpage']['components'][0]['component']['props']['list'][3]
        urls = [x for x in data['player']['config']['sources'] if x['type'] == 'video/mp4']
        return sorted(urls, key=lambda x: x['bitrate'], reverse=True)[0]['file']

    except Exception as inst:
        log("Couldn't get ABC video URL from scraped page: " + str(inst))
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

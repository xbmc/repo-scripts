# -*- coding: utf-8 -*-

import requests
import re

# This little bit of code is only for unit testing.
# When this module is run within Kodi, it will use the Kodi log function as usual
# However, when unit testing from the command line, the xbmc* modules will not be importable
# So the exception will be raised and in response we define a local log function that simply
# prints stuff to the command line.
try:
    from .common import log as log
except ImportError:
    print("\nKodi is not available -> probably unit testing")

    def log(message):
        print(message)

ABC_URL = "https://www.abc.net.au/news/newschannel/weather-in-90-seconds/"
VIDEO_PATTERN = "//abcmedia.akamaized.net/news/news24/wins/(.+?)/WIN(.*?)_512k.mp4"
ABC_STUB = "https://abcmedia.akamaized.net/news/news24/wins/"


def getABCWeatherVideoLink(quality):
    if quality == "Best":
        quality = "trw"

    try:
        r = requests.get(ABC_URL)
        video = re.findall(VIDEO_PATTERN, r.text)
        try:
            url = ABC_STUB + video[0][0] + "/WIN" + video[0][1] + "_" + quality + ".mp4"
            return url
        except Exception as inst:
            log("Couldn't get ABC video URL from page" + str(inst))
            return ""

    except Exception as inst:
        log("********** Couldn't get ABC video page" + str(inst))
        return ""


# UNIT TESTING
if __name__ == "__main__":
    log("\nTesting scraping of ABC Weather Video - here's the 'Best' link:\n")
    log(getABCWeatherVideoLink("Best") + "\n")

# ABC VIDEO URL
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

# Thus
# //mpegmedia.abc.net.au/news/news24/wins/(.+?)/WIN(.*?)_512k.mp4

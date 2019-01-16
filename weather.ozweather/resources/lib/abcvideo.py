# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with KODI; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *

import requests
import re

try:
    from xbmc import log as log
except ImportError:
    print("\nXBMC is not available -> probably unit testing")
    def log(str):
        print(str)

ABC_URL = "https://www.abc.net.au/news/newschannel/weather-in-90-seconds/"
VIDEO_PATTERN = "//abcmedia.akamaized.net/news/news24/wins/(.+?)/WIN(.*?)_512k.mp4"

def getABCWeatherVideoLink(quality):

    if quality=="Best":
        quality="trw"

    try:
        r = requests.get(ABC_URL)
        video = re.findall( VIDEO_PATTERN, r.text )
        try:
            url = "https://abcmedia.akamaized.net/news/news24/wins/"+ video[0][0] + "/WIN" + video[0][1] + "_" + quality + ".mp4"
            return url
        except Exception as inst:
            log("Couldn't get ABC video URL from page", inst)
            return ""

    except Exception as inst:
        log("********** Couldn't get ABC video page", inst)
        return ""
    

if __name__ == "__main__":
    log("\nTesting scraping of ABC Weather Video\n")

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
# -*- coding: utf-8 -*-
import requests
import sys
import xbmc
from bs4 import BeautifulSoup

# Allow for unit testing this file
# This brings this addon's resources, and bossanova808 module stuff into scope
# (when running this module outside Kodi)
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')
    sys.path.insert(0, '../../../../script.module.bossanova808/resources/lib')

from resources.lib.store import Store
from bossanova808.utilities import *


def scrape_and_play_abc_weather_video():
    """
    On-demand scrape the current ABC video URL and then play it back, with appropriate metadata/art etc.
    """
    url = get_abc_weather_video_link()
    # Construct an offscreen list item with metadata...
    item = xbmcgui.ListItem(path=url)
    item.setProperty('mimetype', 'video/mpeg')
    item.setInfo('Video', {'title': 'ABC Weather In 90 Seconds'})
    item.setArt({'thumb': f'{CWD}/resources/weather-in-90-seconds.png'})
    # ...and then play it, fullscreen
    xbmc.Player().play(url, item, False)
    pass


# See bottom of this file for notes on matching the video links (& Store.py for the regex)
def get_abc_weather_video_link():
    try:
        r = requests.get(Store.ABC_URL)
        bs = BeautifulSoup(r.text, "html.parser")
        json_string = bs.find("script", {'type': 'application/json', "id": "__NEXT_DATA__"})
        json_object = json.loads(json_string.string)
        # Logger.debug(json_object)
        # Put the json blob into: https://jsonhero.io/j/JU0I9LB4AlLU
        # Gives a path to the needed video as:
        # $.props.pageProps.channelpage.components.0.component.props.list.3.player.config.sources.1.file
        # Rather than grab the URL directly (as place in array might change), grab all the available URLs and get the best quality from it
        # See: https://github.com/bossanova808/weather.ozweather/commit/e6158d704fc160808bf66220da711805860d85c7
        data = json_object['props']['pageProps']['channelpage']['components'][0]['component']['props']['list'][3]
        urls = [x for x in data['player']['config']['sources'] if x['type'] == 'video/mp4']
        return sorted(urls, key=lambda x: x['bitrate'], reverse=True)[0]['file']

    except Exception as inst:
        Logger.error("Couldn't get ABC video URL from scraped page: " + str(inst))
        return ""


# UNIT TESTING
if __name__ == "__main__":
    Logger.info("\nTesting scraping of ABC Weather Video - here's the 'Best' link:\n")
    Logger.info(get_abc_weather_video_link())

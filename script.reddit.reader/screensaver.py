#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import urllib

addon = xbmcaddon.Addon()
screensaver_subreddit = addon.getSetting("screensaver_subreddit")

from resources.lib.reddit import assemble_reddit_filter_string

if __name__ == '__main__':
    xbmc.log('starting reddit_reader screensaver',xbmc.LOGDEBUG)
    reddit_url=assemble_reddit_filter_string(search_string='',subreddit=screensaver_subreddit )

    xbmc.executebuiltin("RunAddon(script.reddit.reader,mode=autoSlideshow&url=%s&name=&type=%s)" %(urllib.quote_plus(reddit_url), 'screensaver') )

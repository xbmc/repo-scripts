#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Feedreader screensaver by Aslak Grinsted
#
#The MIT License (MIT)
#
#Copyright (c) 2014 Aslak Grinsted
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.
#

import xbmcaddon
import xbmcgui
import xbmc

import random
import feedparser
import re
#from threading import Timer
import urllib
import HTMLParser #alternative: http://fredericiana.com/2010/10/08/decoding-html-entities-to-text-in-python/
import time
import datetime
import requests
import urlparse
import traceback

addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path')


CONTROL_BACKGROUND = 30001
CONTROL_HEADLINE = 30002
CONTROL_MAINSTORY = 30003
CONTROL_DATE = 30004
CONTROL_DEBUG = 30005
CONTROL_IMAGE = 30006
CONTROL_CLOCK = 30007


class Screensaver(xbmcgui.WindowXMLDialog):


    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.handle_settings()

    def reportError(self):
        if addon.getSetting('DebugModeß') == 'true':
            #self.getControl(CONTROL_DEBUG).setText(traceback.format_exception(sys.exc_info()[2]))
            self.getControl(CONTROL_DEBUG).setText(repr(traceback.format_exc()))


    def displayNext(self):
        try:
            self.lastDisplayTime = datetime.datetime.now() 
            self.curitem=(self.curitem + 1) % len(self.entries);
            item = self.entries[self.curitem]
            self.getControl(CONTROL_HEADLINE).setLabel(item.title)
            desc = 'n/a'
            if 'description' in item:
                desc = item.description 
            if 'content' in item:
                desc = item.content[0].value
               
            cimg=''
            imgsrc = re.search('img[^<>\\n]+src=[\'"]([^"\']+)[\'"]',desc)
            if imgsrc:
                cimg=imgsrc.group(1)
            #convert news text into plain text
            desc = re.sub('<p[^>\\n]*>','\n\n',desc)
            desc = re.sub('<br[^>\\n]*>','\n',desc)
            desc = re.sub('<[^>\\n]+>','',desc)
            desc = re.sub('\\n\\n+','\n\n',desc)
            desc = re.sub('(\\w+,?) *\\n(\\w+)','\\1 \\2',desc)  
            desc = HTMLParser.HTMLParser().unescape(desc) 
            self.getControl(CONTROL_MAINSTORY).setText(desc.strip() + '\n')
            if 'published_parsed' in item:
                sdate=time.strftime('%d %b %H:%M',item.published_parsed)
            else: sdate=''
            self.getControl(CONTROL_DATE).setText('%s\n%s' % (item.feedtitle,sdate))
            try:
                maxwidth=0
                if 'media_thumbnail' in item:
                    for img in item.media_thumbnail:
                        w=1
                        if 'width' in img: w=img['width']
                        if w>maxwidth:
                            cimg=img['url']
                            maxwidth=w
                if 'enclosures' in item:
                    for img in item.enclosures:
                        if re.search('\.(png|jpg|jpeg|gif)',img.href.lower()):
                            cimg = img.href
                        elif 'type' in img:
                            if img.type.lower().find('image') >= 0:
                                cimg = img.href
            except:
                pass
            if cimg:
                cimg = cimg.replace('&amp;','&') #workaround for bug in feedparser
                ##bing-news rss urlparser
                #if cimg.find('imagenewsfetcher.aspx') >= 0:
                #    imgparsed = urlparse.urlparse(cimg)
                #    imgparsed = urlparse.parse_qs(imgparsed.query)
                #    if 'q' in imgparsed: cimg = imgparsed['q']
                self.getControl(CONTROL_BACKGROUND).setImage(cimg)
                self.getControl(CONTROL_IMAGE).setImage(cimg)
                #self.getControl(CONTROL_DEBUG).setText('test: %s' % cimg)
        except:
            self.reportError()
        #self.getControl(CONTROL_DEBUG).setText('%d' % len(desc))
        #self.itemtimer = Timer(float(addon.getSetting('Time')), self.displayNext)
        #self.itemtimer.start()

    def processEvents(self):
        self.clockblink = not self.clockblink
        try:
            if self.clockblink:
                self.getControl(CONTROL_CLOCK).setText(time.strftime('%d %b %H:%M'))
            else:
                self.getControl(CONTROL_CLOCK).setText(time.strftime('%d %b %H %M'))
            if self.abort_requested: return
            #if abs(time.time()-self.lastDisplayTime) >= self.delayTime:
            if datetime.datetime.now() >= self.lastDisplayTime + datetime.timedelta(seconds=self.delayTime):
                self.displayNext()
        except:
            self.reportError()

    def addFeed(self,url):
        try:
            if url:
                if url.find('//')<0: #if there is no urlscheme, then make a news search
                    url = 'https://news.google.com/news/feeds?pz=1&cf=all&q=%s&hl=en&output=rss' % urllib.quote_plus(url)
                    #url = "https://www.bing.com/news/search?q=%s&format=RSS" % urllib.quote_plus(url) 
                    #url = requests.get(url, headers={'Accept-Language': 'en-US,en'});
                    #url = url.content.replace('<News:Image>','<media:thumbnail>')
                    #url = url.replace('</News:Image>','&amp;sz=1920x720</media:thumbnail>')
                feed = feedparser.parse(url)
                if not 'entries' in feed:
                    return
                self.feedcounter+=1.
                for ii, item in enumerate(feed.entries):
                    item.update({'feedtitle': feed.feed.title, 'itemno': ii, 'feedno': self.feedcounter, 'globalitemno': 0.})

                if hasattr(self,'entries'):
                    self.entries = self.entries + feed.entries
                    for ii, item in enumerate(self.entries):
                        item.globalitemno = ii #re-label them all for sorting (used in interleave mode)
                        if not 'published_parsed' in item:
                            item.published_parsed = (datetime.datetime.now() - datetime.timedelta(hours=item.itemno*2)).timetuple()
                    sorting = addon.getSetting('Sorting')
                    if sorting=='Time':
                        self.entries.sort(key=lambda item: (item.globalitemno>self.curitem, -time.mktime(item.published_parsed)))
                    if sorting=='Interleave':
                        self.entries.sort(key=lambda item: (item.globalitemno>self.curitem, item.itemno, item.feedno))
                else:
                    self.entries = feed.entries
                    self.displayNext()
        except:
            self.reportError()


    def handle_settings(self):
        self.lastDisplayTime = datetime.datetime.now() - datetime.timedelta(hours=24)
        self.clockblink = True
        self.abort_requested = False
        self.curitem = -1
        self.feedcounter = -1.
        self.getControl(CONTROL_MAINSTORY).setText('')
        self.delayTime=float(addon.getSetting('Time'));
        for x in range(1, 7):
            if not self.abort_requested:
                self.addFeed(addon.getSetting('Feed%d' % x))
                xbmc.sleep(100)
                self.processEvents()
        while not self.abort_requested:
            xbmc.sleep(1000)
            self.processEvents()



    def exit(self):
        #self.itemtimer.stop()
        self.abort_requested = True
        self.exit_monitor = None
        self.log('exit')
        self.close()

    def log(self, msg):
        xbmc.log(u'Feedreader screensaver: %s' % msg)


if __name__ == '__main__':

    screensaver = Screensaver(
        'script-%s-Main.xml' % addon_name,
        addon_path,
        'default',
    )
    screensaver.doModal()
    del screensaver
    sys.modules.clear()

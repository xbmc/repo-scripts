# -*- coding: utf-8 -*-
# Copyright (c) 2010 Andre LeBlanc

from PIL import Image
import re
import time
import os
import sys
import base64
import xbmc
import xbmcgui
from datetime import datetime, timedelta
import urllib
from onmytv import OnMyTV

print "PYTHON VERSION: %s" % (sys.version,)
from elementtree import ElementTree

_ = sys.modules[ "__main__" ].__language__
__settings__ = sys.modules[ "__main__" ].__settings__

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

EXIT_SCRIPT = ( 6, 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )

UID = __settings__.getSetting('onmytv_uid')


def utcs_to_localdt(utc_string):
    utc_dt = datetime(*map(int,re.split(r"[-:\s]",utc_string)))
    return TZ.fromutc(utc_dt)


class TVListingGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.list = {}
        cachepath = xbmc.translatePath("special://profile/addon_data/script.onmytv/")
        if not os.path.exists(cachepath):
            os.mkdir(cachepath)
        self.OTV = OnMyTV(UID, cachepath, max_cache_age=__settings__.getSetting("max_cache_age"))

    def loadListing(self, full=True):
        self.checkmark = self.getControl(96)
        print 'checked?', self.checkmark.isSelected()
        full = self.checkmark.isSelected()
        if ((full and not self.OTV.check_cache(self.OTV.full_cache_file())) or 
           ((not full) and not self.OTV.check_cache(self.OTV.user_cache_file()))):
            print "Showing Progress Dialog"
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create("On-My.TV", "Refreshing Listings")
            def updater(count, bsize, tsize):
                dsize = count * bsize
                if dsize > tsize: dsize = tsize
                progress_dialog.update(int((dsize/float(tsize))*100))
            self.OTV.load_listings(full=full, report_hook=updater)
            progress_dialog.close()
        else: 
            self.OTV.load_listings(full=full)
        self.dates = {}
        self.episodes = {}
        
        if full:
            listings = self.OTV.full_listing
        else:
            listings = self.OTV.user_listing
            
        for entry in listings:
            if entry['ep_date_local'].date() not in self.dates:
                self.dates[entry['ep_date_local'].date()] = []

            self.dates[entry['ep_date_local'].date()].append(entry)            
            self.episodes[entry['ep_tvrage_id']] = entry
            

    def onInit(self):
        self.loadListing(True)
        
        p = None
        self.quit_btn = quit_btn = self.getControl(15)
        self.tgl_btn = tgl_btn = self.getControl(96)
        self.button_to_date = {}
        for i,d in enumerate(sorted(self.dates)):
            btn = xbmcgui.ControlButton(0,30+(i*38),225,30,d.strftime("%A, %b %d"),font='font11',textColor='0xFF000000')
            if i == 0:
                self.today_button = btn
            self.addControl(btn)
            btn.controlLeft(self.getControl(20))
            btn.controlRight(self.getControl(20))
            self.button_to_date[btn.getId()] = d
            if p is not None:
                p.controlDown(btn)
                btn.controlUp(p)
            else:
                btn.controlUp(quit_btn)
                quit_btn.controlDown(btn)
            p = btn
            print 'added button'
        btn.controlDown(tgl_btn)
        tgl_btn.controlUp(btn)
        self.setFocus(self.today_button)

    def shutDown(self):
        print "terminating"
        self.close()
        
    def updateListings(self,date):
        date_header = self.getControl(25)
        date_header.setLabel(date.strftime("%A %B %d"))
        list = self.getControl(20)
        print 'date: [%s]' % (date,)
        listings = self.dates[date]        
        list.reset()
        listings.sort(key=lambda e: e['ep_date_local'])
        for event in listings:
            start_time_string = event['ep_date_local'].strftime("%I:%M %p")
            if start_time_string.startswith('0'):
                start_time_string = start_time_string[1:]
            l = xbmcgui.ListItem(label="%s: %s %dx%02d %s" % (start_time_string, event['show_name'], event['season'], event['episode'], event['name']),
                                  label2="%s" % (unicode(event['episode_summary']),))
            l.setProperty('episode_id',str(event['ep_tvrage_id']))
            list.addItem(l)
                
   
    def exit_script( self, restart=False ):
        self.shutDown()
        #self.close()
        
    def onClick(self, controlID):
        list = self.getControl(20)
        if (controlID == 96):            
            self.loadListing(self.checkmark.isSelected())
            
        if (controlID == 15):
            self.shutDown()
        if (controlID == 20):
            # A torrent was chosen, show details
            item = list.getSelectedItem()
            w = EpisodeInfoGUI("script-tvlisting-details.xml",os.getcwd() ,"Default")
            epid = item.getProperty('episode_id')
            episode = self.episodes[int(epid)]
            w.setEpisode(episode)
            w.doModal()
            del w
        return False
    def onFocus(self, controlID):
        if hasattr(self, 'button_to_date'):
            btn = self.getControl(controlID)
            if controlID in self.button_to_date:
                self.updateListings(self.button_to_date[controlID])
            elif controlID in (self.quit_btn.getId(), self.tgl_btn.getId()):
                self.getControl(20).reset()
                self.getControl(25).setLabel("")
            ls = self.getControl(20)
            if btn != ls:
                ls.controlLeft(btn)
                ls.controlRight(btn)

    def onAction( self, action ):
        if ( action.getButtonCode() in CANCEL_DIALOG ):
            print str(action.getButtonCode())
            self.exit_script() 

        
class EpisodeInfoGUI(xbmcgui.WindowXMLDialog):
    def onInit(self):
        pass
    def setEpisode(self, episodeDict):
        self.episode = episodeDict
        self.episode_set = False
        
    def onFocus(self, controlID):
        left_margin = 50
        top = 50
        if not self.episode_set:
            self.getControl(1).setLabel("%s - %sx%02d - %s" % (self.episode['show_name'], self.episode['season'], int(self.episode['episode']), self.episode['name']))
            if self.episode['screen_cap']:
                progress_dialog = xbmcgui.DialogProgress()
                progress_dialog.create("Downloading Screenshot","")
                progress_dialog.update(0)
                def updater(count, bsize, tsize):
                    dsize = count * bsize
                    if dsize > tsize: dsize = tsize
                    completion = int((dsize/float(tsize))*100)
                    print "%s%%" % (completion,)
                    progress_dialog.update(completion)
                    time.sleep(0.01)
                try:
                    filename,garb = urllib.urlretrieve(self.episode['screen_cap'], reporthook=updater)
                    image = Image.open(filename)
                    max_size = 320
                    imctl = xbmcgui.ControlImage(50,40,image.size[0]*(240/float(image.size[1])),240,filename)
                    self.addControl(imctl)
                    top = 50 + image.size[1]
                except:
                    pass
                progress_dialog.close()
            else:
                self.getControl(99).setPosition(50,top)
                self.getControl(99).setHeight(480)
            
            self.getControl(99).setText(self.episode['episode_summary'])
            self.episode_set = True
#            print "SIZE: %sx%s" % im.size
            
            
            
    def onClick(self, controlID):
        if controlID == 100:
            self.close()
    
    def onAction(self, action):
        if (action.getButtonCode() in CANCEL_DIALOG):
            self.close()
            
        
        
       

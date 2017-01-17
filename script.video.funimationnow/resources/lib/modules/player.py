# -*- coding: utf-8 -*-

'''
    Funimation|Now Add-on
    Copyright (C) 2016 Funimation|Now

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''



import xbmc;
import logging;

from resources.lib.modules import funimationnow;
from resources.lib.modules import utils;


logger = logging.getLogger('funimationnow');



class player(xbmc.Player):
    def __init__ (self, *args):
        xbmc.Player.__init__(self);


    def run(self, videourl, listitem):
        
        try:
            
            xbmc.sleep(200);

            self.totalTime = 0; 
            self.currentTime = 0;
            self.offset = '0';
            self.item = listitem;
            self.startPosition = self.item.getProperty('startPosition');
            self.usecurrentprogress = 1;


            if self.startPosition:

                try:
                    
                    self.startPosition = int(self.startPosition);

                    if self.startPosition > 0:

                        self.usecurrentprogress = utils.requestContinueProgress(self.startPosition);
                        
                        if self.usecurrentprogress != 0:
                            self.startPosition = 0;


                except:
                    self.startPosition = 0;

            else:
                self.startPosition = 0;


            if self.usecurrentprogress >= 0:

                videourl = utils.resolutionPicker(videourl);

                if videourl:
                    
                    self.play(videourl, listitem, False);
                    self.keepPlaybackAlive();


        except Exception as inst:
            logger.error(inst);
            
            return;


    def keepPlaybackAlive(self):

        cycle = 0;

        for i in range(0, 240):

            if self.isPlayingVideo() or self.isPlaying(): 
                break;

            xbmc.sleep(1000);

        while(self.isPlayingVideo() or self.isPlaying()):
            
            xbmc.sleep(2000);
            cycle += 2;

            if cycle >= 10:

                cycle = 0;

                self.updateProgress();


    def idleForPlayback(self):

        for i in range(0, 200):

            if utils.condVisibility('Window.IsActive(busydialog)') == 1: 
                utils.idle(); 

            else: 
                break;

            utils.sleep(100);


    def onPlayBackStarted(self):

        if not self.startPosition == 0: 
            self.seekTime(float(self.startPosition));

        self.idleForPlayback();


    #def onPlayBackResumed(self):


    def onPlayBackPaused(self):
        
        self.updateProgress();


    def onPlayBackStopped(self):
        
        self.updateProgress();


    def onPlayBackEnded(self):

        self.onPlayBackStopped();


    def updateProgress(self):

        try:

            self.currentTime = self.getTime();
            self.totalTime = self.getTotalTime();

            funimationnow.updateProgess(self.item, self.currentTime, self.totalTime);

        except:
            pass;

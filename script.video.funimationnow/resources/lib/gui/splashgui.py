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
import xbmcgui;
import os;

from resources.lib.modules import utils;


class introPlayer(xbmc.Player):
 
    def __init__ (self):
 
        xbmc.Player.__init__(self);

        self.gui = None;

 
    def run(self, murl, gui):

        self.gui = gui;

        self.play(item=murl, windowed=True);
        

    def onPlayBackEnded(self):

        self.gui.deleteControl();


class SplashScreenUI(xbmcgui.WindowXMLDialog):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.player = introPlayer();


    def onInit(self):

        self.playIntro();

        pass;


    def playIntro(self):

        try:

            playercontrol = self.getControl(100);

            if playercontrol:

                self.player.run(os.path.join(utils.getAddonInfo('path'), 'resources/skins/default/media/FunimationNowExtended.mp4'), self);

        except:
            pass;


    def deleteControl(self):

        try:

            playercontrol = self.getControl(100);

            if playercontrol:
                self.removeControl(playercontrol);

        except:
            pass;


        #self.player = None;
        #from resources.lib.gui.maingui import main;
        #main(self);
        self.close();


def splashscreen():
    
    splashgui = SplashScreenUI("funimation-splash.xml", utils.getAddonInfo('path'), 'default', "720p");
    
    splashgui.doModal();

    del splashgui;

    


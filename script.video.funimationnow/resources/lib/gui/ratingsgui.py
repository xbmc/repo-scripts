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
import sys;
import re;
import logging;
import json;

from resources.lib.modules import utils;


RATING_BUTTONS = list([2000, 2001, 2002, 2003, 2004, 2005]);
CANCEL_BUTTON = 100;

PREVIOUS_WINDOW = (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK);

#https://github.com/phil65/script.module.actionhandler/blob/master/lib/ActionHandler.py
#https://github.com/romanvm/Kodistubs/blob/master/xbmcgui.py

class RatingViewUI(xbmcgui.WindowXMLDialog):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.dialog_content = None;
        self.initialRating = 0;
        self.userRating = 0;
        self.logger = utils.getLogger();


    def setInitialRating(self, rating):
        
        self.initialRating = int('200%s' % rating);

        self.runDirectoryChecks();
        self.createDialofTextImgs();

        #if self.initialRating in RATING_BUTTONS:
            #RATING_BUTTONS.remove(self.initialRating);

        pass;


    def createDialofTextImgs(self):

        try:

            #lang = utils.addon.getLocalizedString;

            dialogTitle = utils.lang(30900).encode('utf-8');
            tempImg = os.path.join(self.dialog_content, 'title_rating.png');

            utils.text2Display(dialogTitle, 'RGB', (255, 255, 255), (0, 0, 0), 36, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

            dialogBtn = utils.lang(30901).encode('utf-8');
            tempImgFocus = os.path.join(self.dialog_content, 'focus_rating.png');
            tempImgNoFocus = os.path.join(self.dialog_content, 'nofocus_rating.png');

            utils.text2Display(dialogBtn, 'RGB', None, (255, 255, 255), 36, 'Bold', tempImgFocus, multiplier=1, sharpen=False, bgimage='rating_cancel_focus.png');
            utils.text2Display(dialogBtn, 'RGB', None, (150, 39, 171), 36, 'Bold', tempImgNoFocus, multiplier=1, sharpen=False, bgimage='rating_cancel_no_focus.png');

        except:
            pass;


        pass;


    def runDirectoryChecks(self):

        #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', utils.getAddonInfo('id')));
        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.dialog_content = os.path.join(dsPath, 'media/dialog');

        utils.checkDirectory(self.dialog_content);

        pass;
                   

    def onInit(self):

        try:

            self.setFocus(self.getControl(self.initialRating));

        except Exception as inst:
            self.logger.error(inst);

            pass;


        pass;


    def onAction(self, action):

        if action.getId() in PREVIOUS_WINDOW:
            self.userRating = 0;
            self.close();

        
        pass;


    def onClick(self, controlID):

        if controlID in RATING_BUTTONS:

            self.userRating = RATING_BUTTONS.index(controlID);
            self.close();

        else:
            self.userRating = 0;
            self.close();

        pass;


    def onFocus(self, controlID):

        pass;


    def getUserRating(self):

        return self.userRating;



def rating(rating):

    
    ratingui = RatingViewUI("funimation-rating.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    ratingui.setInitialRating(rating);
    ratingui.doModal();
    
    userRating = ratingui.getUserRating();

    del ratingui;
    

    return userRating;

    


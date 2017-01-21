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
import xbmcaddon;
import xbmcplugin;
import os;
import re;
import sys;
import logging;
import json;

from resources.lib.modules import utils;
from resources.lib.modules import funimationnow;
from resources.lib.modules import workers;



EXIT_CODE = 2;
SUCCESS_CODE = 3;
EXPIRE_CODE = 4;
HOME_SCREEN_CODE = 5;
BACK_CODE = 6;

EXIT_CODE = 2;
SUCCESS_CODE = 3;
EXPIRE_CODE = 4;
HOME_SCREEN_CODE = 5;
BACK_CODE = 6;
LOGOUT_CODE = 7;
REST_CODE = 8;

SEARCH_WINDOW = 100100;
HOME_WINDOW = 110101;
QUEUE_WINDOW = 110102;
ALL_WINDOW = 110103;
SIMALCAST_WINDOW = 110104;
GENRE_WINDOW = 110105;
SETTINGS_WINDOW = 110106;
HELP_WINDOW = 110107;
LOGOUT_WINDOW = 110108;

CURRENT_WINDOW = GENRE_WINDOW;

SIDE_MENU = (
    SEARCH_WINDOW,
    HOME_WINDOW,
    QUEUE_WINDOW,
    ALL_WINDOW,
    SIMALCAST_WINDOW,
    GENRE_WINDOW,
    SETTINGS_WINDOW,
    HELP_WINDOW,
    LOGOUT_WINDOW
);

LOADING_SCREEN = 90000;
MENU_BTN = 110100;

PANEL_LIST = 80001;

FILTER_GROUP = 100;
GENRE_SELECT_IMG = 1000;
GENRE_SELECT_LIST = 1001;
SORT_SELECT_IMG = 1002;
SORT_SELECT_LIST = 1003;
SUB_SELECT_IMG = 1004;
SUB_SELECT_LIST = 1005;
SORT_DIRECTION_BTN = 1006;  #Sort Direction does not work for anything but recent so removing it.

NAV_SELECT_LISTS = (
    GENRE_SELECT_LIST,
    SORT_SELECT_LIST,
    SUB_SELECT_LIST
);

NAV_SELECT_IMGS = (
    GENRE_SELECT_IMG,
    SORT_SELECT_IMG,
    SUB_SELECT_IMG
);


class GenreShowsUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();

        self.navigation = None;
        self.landing_page = None;
        self.currentposition = 0;


    def onInit(self):

        if self.landing_page and self.landing_page.result_code in (HOME_SCREEN_CODE, EXIT_CODE, LOGOUT_CODE):
            self.close();

        else:

            self.runDirectoryChecks();
            self.getGenres();

            try:
                xbmc.executebuiltin('Control.SetFocus(%s, %s)' % (PANEL_LIST, self.currentposition));

            except:
                pass;

            utils.unlock();


    def setInitialItem(self, landing_page, navSet):
        self.navigation = navSet;
        self.landing_page = landing_page;


    def onClick(self, controlID):

        #need to add a loading check and return None if loading

        if controlID == MENU_BTN:
            self.close();

        elif controlID == PANEL_LIST:

            listitem = self.getControl(PANEL_LIST).getSelectedItem();

            self.currentposition = self.getControl(PANEL_LIST).getSelectedPosition();

            try:

                from resources.lib.gui.genreselectgui import genreselect;

                xrfTitle = listitem.getProperty('title');
                xrfPath = listitem.getProperty('path');
                xrfParam = listitem.getProperty('params');
                xrfTarget = listitem.getProperty('target');

                mnavset = dict({
                    'width': 140,
                    'title': xrfTitle,
                    #'params': 'id=shows&title=All Shows&territory=US&showGenres=true',
                    'params': xrfParam,
                    'target': xrfTarget,
                    'path': xrfPath,
                    'offset': 0,
                    'limit': 144
                });

                genreselect(self.landing_page, mnavset);


            except Exception as inst:
                self.logger.error(inst);


        elif controlID in SIDE_MENU:
            self.menuNavigation(controlID);


    def getGenres(self):

        try:

            longList = funimationnow.getLongList(self.navigation['path'], self.navigation['params']);

            self.logger.debug(json.dumps(longList));

            if longList:
                self.setGenreDisplay(longList);
            
        except Exception as inst:
            self.logger.error(inst);


        self.setVisible(LOADING_SCREEN, False);


    def setGenreDisplay(self, longList):

        gControl = self.getControl(PANEL_LIST);

        gControl.reset();

        items = utils.parseValue(longList, ['items', 'item'], False);

        if items:
            
            if not isinstance(items, list):
                items = list([items]);


            for item in items:

                try:

                    gTitle = utils.parseValue(item, ['analytics', 'click', 'label']);
                    gThumbnail = utils.parseValue(item, ['thumbnail', '#text']);
                    gThumbnail = funimationnow.formatImgUrl(gThumbnail, theme='genre');

                    gPath = utils.parseValue(item, ['pointer', 'path']);
                    gParams = utils.parseValue(item, ['pointer', 'params']);
                    gTarget = utils.parseValue(item, ['pointer', 'target']);

                    gListitem = xbmcgui.ListItem(gTitle, gTitle, gThumbnail, gThumbnail);

                    gListitem.setProperty('title', gTitle);
                    gListitem.setProperty('path', gPath);
                    gListitem.setProperty('params', gParams);
                    gListitem.setProperty('target', gTarget);

                    gControl.addItem(gListitem);


                except Exception as inst:
                    self.logger.error(inst);


    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);


    def getResultCode(self):
        return self.result_code;


    def menuNavigation(self, controlID):

        from resources.lib.modules import menunav;

        RESULT_CODE = menunav.chooser(self.landing_page, self, CURRENT_WINDOW, controlID);

        if RESULT_CODE == LOGOUT_CODE:
            
            self.landing_page.result_code = LOGOUT_CODE;
            self.close();

        if RESULT_CODE == HOME_SCREEN_CODE:
            
            self.landing_page.result_code = HOME_SCREEN_CODE;
            self.close();   


    def runDirectoryChecks(self):

        #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', utils.getAddonInfo('id')));
        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.select_main = os.path.join(dsPath, 'media/select/main');
        self.select_list = os.path.join(dsPath, 'media/select/list');
        self.shows_list_title = os.path.join(dsPath, 'media/shows/list/title');
        self.shows_list_subtitle = os.path.join(dsPath, 'media/shows/list/subtitle');
        self.shows_list_added = os.path.join(dsPath, 'media/shows/list/added');
        self.details_home_title = os.path.join(dsPath, 'media/details/home/title');

        utils.checkDirectory(self.select_main);
        utils.checkDirectory(self.select_list);
        utils.checkDirectory(self.shows_list_title);
        utils.checkDirectory(self.shows_list_subtitle);
        utils.checkDirectory(self.shows_list_added);
        utils.checkDirectory(self.details_home_title);



def genreshows(landing_page, navSet=None):

    
    genreshowsui = GenreShowsUI("funimation-genre-shows.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    genreshowsui.setInitialItem(landing_page, navSet);
    genreshowsui.doModal();

    del genreshowsui;

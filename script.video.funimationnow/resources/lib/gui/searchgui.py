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

CURRENT_WINDOW = SEARCH_WINDOW;

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

PANEL_LIST = 80001;

SEARCH_BTN = 1000;
SEARCH_INPUT = 1001;
CLEAR_BTN = 1002;
BACK_BTN = 110100;


class SearchUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();

        self.navigation = None;
        self.landing_page = None;
        self.queueLookup = None;
        self.myQueue = None;

        self.currentposition = 0;


    def onInit(self):

        self.setVisible(LOADING_SCREEN, True);

        if self.landing_page and self.landing_page.result_code in (HOME_SCREEN_CODE, EXIT_CODE, LOGOUT_CODE):
            self.close();

        else:

            self.runDirectoryChecks();
            self.initateSearch();

            try:
                xbmc.executebuiltin('Control.SetFocus(%s, %s)' % (PANEL_LIST, self.currentposition));

            except:
                pass;

            utils.unlock();

            self.setVisible(LOADING_SCREEN, False);


    def setInitialItem(self, landing_page):
        self.landing_page = landing_page;


    def checkQueue(self):

        if self.queueLookup is None:
            self.queueLookup = funimationnow.getMyQueueConfig();

            if self.queueLookup:
                self.myQueue = funimationnow.getMyQueue(self.queueLookup);

        else:
            self.myQueue = funimationnow.getMyQueue(self.queueLookup);

        self.logger.debug(json.dumps(self.myQueue));


    def onClick(self, controlID):

        #need to add a loading check and return None if loading

        if controlID == BACK_BTN:
            self.close();

        elif controlID == SEARCH_BTN:
            self.initateSearch();

        elif controlID == CLEAR_BTN:
            self.clearInput();

        elif controlID == PANEL_LIST:

            listitem = self.getControl(PANEL_LIST).getSelectedItem();
            self.currentposition = self.getControl(PANEL_LIST).getSelectedPosition();

            try:

                from resources.lib.gui.showgui import show;

                xrfPath = listitem.getProperty('path');
                xrfParam = listitem.getProperty('params');

                show(self.landing_page, xrfPath, xrfParam);

            except Exception as inst:
                self.logger.error(inst);


    def clearInput(self):
        self.getControl(SEARCH_INPUT).setText('');


    def initateSearch(self):

        self.setVisible(LOADING_SCREEN, True);
        
        inputText = self.getControl(SEARCH_INPUT).getText();

        if inputText and len(inputText) > 0:

            self.checkQueue();

            try:

                longList = funimationnow.getLongList('longlist/search/', ('q=%s' % inputText));

                self.logger.debug(json.dumps(longList));

                if longList:

                    pagination = utils.parseValue(longList, ['items', 'pagination'], False);

                    self.logger.debug(json.dumps(pagination));

                    pPath = utils.parseValue(pagination, ['path']);
                    pParams = utils.parseValue(pagination, ['params']);
                    startPosition = utils.parseValue(pagination, ['startPosition', 'param']);
                    maxCount = utils.parseValue(pagination, ['maxCount', 'param']);

                    pages = funimationnow.getPage(pPath, '%s&%s=0&%s=9999' % (pParams, startPosition, maxCount));

                    if pages:

                        self.logger.debug(json.dumps(pages));

                        self.setSearchDisplay(pages);
                
            except Exception as inst:
                self.logger.error(inst);


        self.setVisible(LOADING_SCREEN, False);


    def setSearchDisplay(self, pages):

        shControl = self.getControl(PANEL_LIST);

        shControl.reset();

        items = utils.parseValue(pages, ['items', 'item'], False);

        if items:
            if not isinstance(items, list):
                items = list([items]);


            for item in items:

                try:

                    button = None;
                    plPath = None;
                    plParams = None;

                    if self.myQueue is None:
                        self.myQueue = dict();

                    shTitle = utils.parseValue(item, ['title']);
                    shPath = utils.parseValue(item, ['pointer', 'path']);
                    shParams = utils.parseValue(item, ['pointer', 'params']);
                    shThumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                    shThumbnail = shThumbnail if shThumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                    shThumbnail = funimationnow.formatImgUrl(shThumbnail, theme='show');
                    shStarRating = utils.parseValue(item, ['starRating', 'rating']);
                    shTitleimg = os.path.join(self.shows_search_title, ('s_%s.png' % shParams));
                    shRecentContentItem = utils.parseValue(item, ['content', 'metadata', 'recentContentItem']);
                    shRecentlyAdded = utils.parseValue(item, ['content', 'metadata', 'recentlyAdded']);
                    buttons = utils.parseValue(item, ['legend', 'button'], False);

                    if buttons:

                        if not isinstance(buttons, list):
                            buttons = list([buttons]);

                        for btn in buttons:

                            bTarget = utils.parseValue(btn, ['pointer'], False);

                            if utils.parseValue(bTarget, ['target']) == 'togglewatchlist':

                                button = btn;

                            elif utils.parseValue(bTarget, ['target']) == 'player':

                                plPath = utils.parseValue(bTarget, ['path']);
                                plParams = utils.parseValue(bTarget, ['params']);


                    shToggleParams = utils.parseValue(button, ['pointer', 'toggle', 'data', 'params']);
                    shMyQueuePath = utils.parseValue(self.myQueue, [shToggleParams, 'myQueuePath']);
                    shTogglePath = utils.parseValue(btn, ['pointer', 'toggle', 'data', 'path']);
                    shToggleParams = shToggleParams;
                    shMyQueuePath = shMyQueuePath;
                    shMyQueueParams = utils.parseValue(self.myQueue, [shToggleParams, 'myQueueParams']);
                    shInQueue = str((0 if shMyQueuePath is not None else 1));


                    shListitem = xbmcgui.ListItem(shTitle, '', shThumbnail, shThumbnail);

                    titles = [shTitle];

                    shTitleimg = utils.text2Title(list(titles), self.details_search_title, shTitleimg);

                    if shTitleimg:
                        shListitem.setProperty('ctitle', shTitleimg);

                    if shInQueue is not None:
                        shListitem.setProperty('qtexture', str(shInQueue));

                    if shRecentContentItem:

                        if shRecentContentItem == 'Episode':
                            shRecentContentItem = 'Movie';

                        tempImg = os.path.join(self.shows_search_subtitle, ('%s.png' % re.sub(r'[^\w\d]+', '_', shRecentContentItem, re.I)));

                        if not os.path.isfile(tempImg):
                            utils.text2Display(shRecentContentItem, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                        shListitem.setProperty('subtitle', tempImg);


                    if shRecentlyAdded:

                        tfname = re.sub(r'[^\d]+', '', shRecentlyAdded, re.I);
                        ttname = 'added 0d ago';

                        try:

                            import time;
                            import dateutil.parser;

                            from time import mktime;
                            from datetime import datetime;

                            ttdate = datetime.fromtimestamp(mktime(time.gmtime(float(tfname))));
                            ttday = (datetime.utcnow() - ttdate).days;

                            if ttday >= 365:
                                ttname = 'added %sy ago' % int(round(float(ttday) / 365));

                            elif ttday >= 1:
                                ttname = 'added %sd ago' % ttday;

                            else:

                                ttday = (datetime.utcnow() - ttdate).total_seconds();

                                if(ttday / 60) <= 59:
                                    ttname = 'added %sm ago' % int(round(float(ttday) / 60));

                                else:
                                    ttname = 'added %sh ago' % int(round((float(ttday) / 60) / 60));

                        except Exception as inst:
                            self.logger.error(inst);
                            ttname = 'added 0d ago';


                        tempImg = os.path.join(self.shows_search_added, ('%s.png' % tfname));

                        #if not os.path.isfile(tempImg):
                        utils.text2Display(ttname, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Italic', tempImg, multiplier=1, sharpen=False, bgimage=None);

                        shListitem.setProperty('addedon', tempImg);


                    if shStarRating:

                        shStarRating = str(utils.roundQuarter(str(shStarRating)));
                        shListitem.setProperty('starrating', shStarRating);

                    else:
                        shListitem.setProperty('starrating', '0.0');


                    shListitem.setProperty('title', shTitle);
                    shListitem.setProperty('thumbnail', shThumbnail);
                    shListitem.setProperty('path', shPath);
                    shListitem.setProperty('params', shParams);
                    shListitem.setProperty('titleimg', shTitleimg);
                    shListitem.setProperty('recentContentItem', shRecentContentItem);
                    #shListitem.setProperty('recentlyAdded', shRecentlyAdded);
                    shListitem.setProperty('togglePath', shTogglePath);
                    shListitem.setProperty('toggleParams', shToggleParams);
                    shListitem.setProperty('myQueuePath', shMyQueuePath);
                    shListitem.setProperty('myQueueParams', shMyQueueParams);
                    shListitem.setProperty('inQueue', shInQueue);
                    #shListitem.setProperty('starRating', shStarRating);

                    shControl.addItem(shListitem);


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

        self.shows_search_title = os.path.join(dsPath, 'media/shows/search/title');
        self.shows_search_subtitle = os.path.join(dsPath, 'media/shows/search/subtitle');
        self.shows_search_added = os.path.join(dsPath, 'media/shows/search/added');
        self.details_search_title = os.path.join(dsPath, 'media/details/search/title');

        utils.checkDirectory(self.shows_search_title);
        utils.checkDirectory(self.shows_search_subtitle);
        utils.checkDirectory(self.shows_search_added);
        utils.checkDirectory(self.details_search_title);



def search(landing_page):

    
    searchui = SearchUI("funimation-search.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    searchui.setInitialItem(landing_page);
    searchui.doModal();

    del searchui;

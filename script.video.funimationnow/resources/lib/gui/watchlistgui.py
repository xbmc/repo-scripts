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
LOGOUT_CODE = 7;

CURRENT_WINDOW = 110102;

HOME_WINDOW = 110101;
QUEUE_WINDOW = 110102;
ALL_WINDOW = 110103;
SIMALCASTS_WINDOW = 110104;
DUBS_WINDOW = 110105;
GENRES_WINDOW = 110106;
SETTINGS_WINDOW = 110107;

SIDE_MENU = (
    HOME_WINDOW,
    QUEUE_WINDOW,
    ALL_WINDOW,
    SIMALCASTS_WINDOW,
    DUBS_WINDOW,
    GENRES_WINDOW,
    SETTINGS_WINDOW
);

LOADING_SCREEN = 90000;
MENU_BTN = 110100;

QUEUE_BTN = 1000;
HISTORY_BTN = 1001;

QUEUE_PANEL_LIST = 2000;
HISTORY_PANEL_LIST = 2001;

NAV_BUTTONS = (
    QUEUE_BTN,
    HISTORY_BTN
);

PANEL_LISTS = (
    QUEUE_PANEL_LIST,
    HISTORY_PANEL_LIST
);


class WatchListUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();

        self.landing_page = None;
        self.navigation = None;
        self.queueLookup = None;
        self.myQueue = None;
        self.currentSet = None;
        self.currentValue = None;
        self.currentParam = None;
        self.currentPanel = None;
        self.currentIndex = None;

        self.currentChoice = 0;
        self.contentMaps = dict();

        #self.result_code = BACK_CODE;

        self.isEmpty = True;


    def onInit(self):
        
        if self.landing_page.result_code == HOME_SCREEN_CODE:
            self.close();

        else:

            self.setVisible(LOADING_SCREEN, True);

            self.runDirectoryChecks();
            self.setButtonStates();
            self.setSelectedContent();

            if self.currentPanel is not None and self.currentIndex is not None:

                try:
                    xbmc.executebuiltin('Control.SetFocus(%s, %s)' % (self.currentPanel, self.currentIndex));

                except:
                    pass;

            utils.unlock();

            self.setVisible(LOADING_SCREEN, False);


    def setSelectedContent(self):

        self.setVisible(LOADING_SCREEN, True);

        try:

            for panel in PANEL_LISTS:
                self.getControl(panel).reset();


            sBtns = utils.parseValue(self.currentSet, ['longList', 'palette', 'filter', 'choices', 'button'], False);
            sParams = sBtns[self.currentChoice].get('value', None);
            
            if sParams:

                import urlparse;
                import urllib;

                self.currentSet = None;

                tmpParams = dict(urlparse.parse_qsl(self.navigation.get('params')));

                tmpParams.update({'id': sParams});

                tmpParams = urllib.urlencode(tmpParams);

                self.navigation.update({'params': tmpParams});

                self.getCurrentSet();

                self.logger.debug(json.dumps(self.currentSet))

                watchlist = funimationnow.watchlist(self.currentValue);

                if watchlist and self.currentSet:

                    self.logger.debug(json.dumps(watchlist));

                    emptytext = None;
                    emptythumb = None;

                    items = utils.parseValue(self.currentSet, ['longList', 'watchlist', 'item'], False);

                    if not isinstance(items, list):
                        items = list([items]);

                    for item in items:

                        if 'title' in item and 'thumbnail' in item:

                            emptytext = utils.parseValue(item, ['title']);
                            emptythumb = utils.parseValue(item, ['thumbnail']);

                    self.contentMaps.update({
                        watchlist[0]: dict({
                            'items': watchlist[1],
                            'current': watchlist[2],
                            'config': watchlist[4],
                            'emptytext': emptytext,
                            'emptythumb': emptythumb
                        })
                    });

                    self.setListContent(watchlist[0]);

                    #self.logger.debug(json.dumps(self.contentMaps));

                else:

                    for panel in PANEL_LISTS:
                        self.setVisible(panel, False);

            else:

                for panel in PANEL_LISTS:
                    self.setVisible(panel, False);


        except Exception as inst:
            self.logger.error(inst);


        self.setVisible(LOADING_SCREEN, False);


    def setListContent(self, viewType):

        try:

            cData = self.contentMaps.get(viewType, None);

            if cData:

                for idx, panel in enumerate(PANEL_LISTS, 0):

                    if self.currentChoice == idx:
                        self.setVisible(panel, True);

                    else:
                        self.setVisible(panel, False);


                lcontrol = self.getControl(PANEL_LISTS[self.currentChoice]);

                lItems = cData.get('items', None);

                if(lItems is None or len(lItems) < 1):

                    self.isEmpty = True;

                    lItems = self.contentMaps[viewType];

                    titles = [lItems['emptytext']];
                    listitem = None;
                    listitem = xbmcgui.ListItem(titles[0], titles[0], lItems['emptythumb'], lItems['emptythumb']);

                    titleimg = utils.text2Title(list(titles), self.details_home_title, 'emptytext_%s.png' % viewType);

                    if titleimg:
                        listitem.setProperty('ctitle', titleimg);


                    lcontrol.addItem(listitem); 

                else:

                    self.isEmpty = False;

                    for sIdx, item in enumerate(cData.get('items'), 0):

                        titles = [];
                        listitem = None;
                        listitem = xbmcgui.ListItem(item.get('title', ''), item.get('subtitle', ''), item.get('thumbnail', ''), item.get('thumbnail', ''));

                        if self.currentChoice == 0:
                            titles = [item.get('title', '')];

                        else:
                            titles = [item.get('title', ''), item.get('subtitle', '')];


                        titleimg = utils.text2Title(list(titles), self.details_home_title, item.get('titleimg', ''));

                        self.logger.debug(json.dumps(item));

                        try:

                            listitem.setProperty('viewtype', str(viewType));

                            for attr, val in item.items():

                                listitem.setProperty(attr, str(val));

                        except Exception as inst:
                            self.logger.error(inst);


                        if 'progress' in item:

                            cprogress = item.get('progress', 0);

                            listitem.setProperty('cprogress', str(cprogress));


                        if 'inQueue' in item:

                            inQueue = item.get('inQueue', None);

                            if inQueue is not None:

                                listitem.setProperty('qtexture', str(inQueue));


                        if 'quality' in item:

                            quality = item.get('quality', None);

                            if quality is not None:

                                tempImg = os.path.join(self.shows_list_quality, ('%s.png' % re.sub(r'[^\w\d]+', '_', quality, re.I)));

                                if not os.path.isfile(tempImg):
                                    utils.text2Display(quality, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                                listitem.setProperty('quality', tempImg);


                        if 'releaseYear' in item:

                            releaseYear = item.get('releaseYear', None);

                            if releaseYear is not None:

                                tempImg = os.path.join(self.shows_list_year, ('%s.png' % re.sub(r'[^\w\d]+', '_', releaseYear, re.I)));

                                if not os.path.isfile(tempImg):
                                    utils.text2Display(releaseYear, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                                listitem.setProperty('releaseYear', tempImg);


                        if 'starRating' in item:

                            starRating = item.get('starRating', 0);
                            starRating = str(utils.roundQuarter(str(starRating)));
                            listitem.setProperty('starrating', starRating);



                        if titleimg:
                            listitem.setProperty('ctitle', titleimg);


                        lcontrol.addItem(listitem); 


            else:

                for panel in PANEL_LISTS:
                    self.setVisible(panel, False);


        except Exception as inst:
            self.logger.error(inst);


    def setInitialItem(self, landing_page, navSet):
        self.navigation = navSet;
        self.landing_page = landing_page;


    def getCurrentSet(self):

        if self.currentSet is None:

            try:

                self.currentSet = funimationnow.getWatchListSet(self.navigation.get('path'), self.navigation.get('params'));

                if self.currentSet:
                    self.createButtons();

                    self.logger.debug(json.dumps(self.currentSet));


            except Exception as inst:
                self.logger.error(inst);
                

    def createButtons(self):

        filters = utils.parseValue(self.currentSet, ['longList', 'palette', 'filter'], False);
        buttons = utils.parseValue(filters, ['choices', 'button'], False);

        self.currentValue = utils.parseValue(filters, ['currentValue']);
        self.currentParam = utils.parseValue(filters, ['param']);

        if buttons:

            if not isinstance(buttons, list):
                buttons = list([buttons]);

            for idx, button in enumerate(buttons, 0):

                tmpText = button.get('title');
                fileText = button.get('value');

                if self.currentValue == fileText:
                    self.currentChoice = idx;

                tmpImgFocus = os.path.join(self.buttons, ('%s_on_focus.png' % fileText));
                tmpImgNoFocus = os.path.join(self.buttons, ('%s_on_nofocus.png' % fileText));

                #myqueue_on_focus
                #myqueue_on_nofocus
                #myqueue_off_focus
                #myqueue_off_nofocus

                utils.text2Display(tmpText, 'RGB', None, (164, 68, 182), 36, 'Bold', tmpImgFocus, multiplier=1, sharpen=False, bgimage='watchlist_on_focus.png');
                utils.text2Display(tmpText, 'RGB', None, (150, 39, 171), 36, 'Bold', tmpImgNoFocus, multiplier=1, sharpen=False, bgimage='watchlist_on_nofocus.png');

                tmpImgFocus = os.path.join(self.buttons, ('%s_off_focus.png' % fileText));
                tmpImgNoFocus = os.path.join(self.buttons, ('%s_off_nofocus.png' % fileText));

                #myqueue_on_focus
                #myqueue_on_nofocus
                #myqueue_off_focus
                #myqueue_off_nofocus

                utils.text2Display(tmpText, 'RGB', None, (255, 255, 255), 36, 'Bold', tmpImgFocus, multiplier=1, sharpen=False, bgimage='watchlist_off_focus.png');
                utils.text2Display(tmpText, 'RGB', None, (255, 255, 255), 36, 'Bold', tmpImgNoFocus, multiplier=1, sharpen=False, bgimage='watchlist_off_nofocus.png');


    def checkQueue(self):

        if self.queueLookup is None:
            self.queueLookup = funimationnow.getMyQueueConfig();

            if self.queueLookup:
                self.myQueue = funimationnow.getMyQueue(self.queueLookup);

        else:
            self.myQueue = funimationnow.getMyQueue(self.queueLookup);

        self.logger.debug(json.dumps(self.myQueue));


    def onClick(self, controlID):

        if controlID == MENU_BTN:
            self.close();

        elif controlID in NAV_BUTTONS:

            self.currentChoice = NAV_BUTTONS.index(controlID);
            self.setButtonStates();
            self.setSelectedContent();

        elif controlID in PANEL_LISTS:

            listitem = self.getControl(controlID).getSelectedItem();

            self.currentPanel = controlID;
            self.currentIndex = self.getControl(controlID).getSelectedPosition();

            if self.isEmpty is False:

                if controlID == QUEUE_PANEL_LIST:

                    try:

                        from resources.lib.gui.showgui import show;

                        xrfPath = listitem.getProperty('detailPath');
                        xrfParam = listitem.getProperty('detailParams');

                        show(self.landing_page, xrfPath, xrfParam);

                    except Exception as inst:
                        self.logger.error(inst);
                        

                elif controlID == HISTORY_PANEL_LIST:

                    utils.lock();

                    path = listitem.getProperty('path');
                    params = listitem.getProperty('params');

                    sDetails = funimationnow.selection(path, params, 'episodeDesc', self.currentValue, 0, False);

                    if sDetails:
                    
                        videourl = sDetails.get('videourl', None);
                        closedCaptionUrl = sDetails.get('closedCaptionUrl', None);

                        if videourl:

                            from resources.lib.modules.player import player;

                            try:

                                contMap = self.contentMaps.get(self.currentValue).get('config');

                                if contMap:

                                    pStart = contMap.get('startPosition', None);
                                    pDuration = contMap.get('duration', None);
                                    pAdd = contMap.get('add', None);

                                    if pStart and pDuration and pAdd:
                                        
                                        listitem.setProperty('pStart', str(pStart));
                                        listitem.setProperty('pDuration', str(pDuration));
                                        listitem.setProperty('pAdd', str(pAdd));

                                        if closedCaptionUrl:
                                            listitem.setSubtitles([closedCaptionUrl]);

                            except:
                                pass;

                            utils.unlock();

                            player().run(videourl, listitem);

                    utils.unlock();


        elif controlID in SIDE_MENU:
            self.menuNavigation(controlID);


    def setButtonStates(self):

        try:

            for idx, btn in enumerate(NAV_BUTTONS, 0):

                cBtn = self.getControl(btn);

                if idx == self.currentChoice:
                    cBtn.setSelected(True);

                else:
                    cBtn.setSelected(False);

        except Exception as inst:
            self.logger.error(inst);


    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);


    def getResultCode(self):
        #return self.result_code;

        pass;


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

        self.shows_list_title = os.path.join(dsPath, 'media/shows/list/title');
        self.shows_list_subtitle = os.path.join(dsPath, 'media/shows/list/subtitle');
        self.shows_list_quality = os.path.join(dsPath, 'media/shows/list/quality');
        self.shows_list_year = os.path.join(dsPath, 'media/shows/list/year');
        self.buttons = os.path.join(dsPath, 'media/buttons');
        self.details_home_title = os.path.join(dsPath, 'media/details/home/title');

        utils.checkDirectory(self.shows_list_title);
        utils.checkDirectory(self.shows_list_subtitle);
        utils.checkDirectory(self.shows_list_quality);
        utils.checkDirectory(self.shows_list_year);
        utils.checkDirectory(self.buttons);
        utils.checkDirectory(self.details_home_title);



def watchlist(landing_page, navSet=None):

    
    watchlistgui = WatchListUI("funimation-watchlist-select.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    watchlistgui.runDirectoryChecks();
    watchlistgui.setInitialItem(landing_page, navSet);
    watchlistgui.getCurrentSet();

    watchlistgui.doModal();

    del watchlistgui;
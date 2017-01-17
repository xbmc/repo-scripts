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

CURRENT_WINDOW = ALL_WINDOW;

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
RANGE_SELECT_IMG = 1004;
RANGE_SELECT_LIST = 1005;
SORT_DIRECTION_BTN = 1006;  #Sort Direction does not work for anything but recent so removing it.

NAV_SELECT_LISTS = (
    GENRE_SELECT_LIST,
    SORT_SELECT_LIST,
    RANGE_SELECT_LIST
);

NAV_SELECT_IMGS = (
    GENRE_SELECT_IMG,
    SORT_SELECT_IMG,
    RANGE_SELECT_IMG
);


class GenreSelectUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();

        self.landing_page = None;
        self.navigation = None;
        self.genredata = None;
        self.genreList = None;
        self.navmenu = None;
        self.navmenuparams = None;
        self.navtitle = None;
        self.navpath = None;
        self.navparams = None;
        self.navitemcurrent = None;
        self.queueLookup = None;
        self.myQueue = None;

        self.initialLoad = True;
        self.currentposition = 0;

        self.sortdirection = dict({
            0: 'ASC',
            1: 'DESC'
        });


    def onInit(self):

        if self.landing_page and self.landing_page.result_code in (HOME_SCREEN_CODE, EXIT_CODE, LOGOUT_CODE):
            self.close();

        else:

            self.runDirectoryChecks();
            self.checkQueue();
            self.getGenres(intial=True);

            try:
                xbmc.executebuiltin('Control.SetFocus(%s, %s)' % (PANEL_LIST, self.currentposition));

            except:
                pass;

            utils.unlock();

            #self.getControl(RANGE_SELECT_LIST).setEnabled(False)


        pass;


    def setInitialItem(self, landing_page, navSet):

        # The new API seems to have been screwed up agian so we are removing this additional text they added
        # We have a need to remove this in the future
        #navSet['params'] = re.sub(r'-shows-web', '', navSet['params']);
        # We moved this to a check self.insetupGenreSelect so hopefully it will not need to be edited in the future

        self.logger.debug(json.dumps(navSet));

        self.navigation = navSet;
        self.landing_page = landing_page;


        pass;


    def checkQueue(self):

        if self.queueLookup is None:
            self.queueLookup = funimationnow.getMyQueueConfig();

            if self.queueLookup:
                self.myQueue = funimationnow.getMyQueue(self.queueLookup);

        else:
            self.myQueue = funimationnow.getMyQueue(self.queueLookup);

            pass;

        self.logger.debug(json.dumps(self.myQueue));


    def onClick(self, controlID):

        #need to add a loading check and return None if loading

        if controlID == MENU_BTN:
            self.close();

        elif controlID in NAV_SELECT_LISTS:
            self.getSelectList(controlID);

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
                
                pass;

        elif controlID in SIDE_MENU:
            self.menuNavigation(controlID);

        pass;


    def getGenres(self, subFilter=None, intial=False):

        try:

            import urlparse;
            import urllib;

            self.setVisible(LOADING_SCREEN, True);

            shControl = self.getControl(PANEL_LIST);
            shControl.reset();

            self.navmenuparams = self.navigation.get('params', '');
            self.navmenuparams = dict(urlparse.parse_qsl(self.navmenuparams));
            self.navitemcurrent = self.navmenuparams.get('id', None);

            if self.navitemcurrent == 'recent-shows':

                if intial:
                    subFilter = 'start_date';

                self.navitemcurrent = 'recent';

            elif intial:
                    subFilter = 'slug_exact';


            if subFilter:
                self.navmenuparams.update({'sort': subFilter});

            self.navmenuparams.update({
                'showGenres': 'true',
                #'sort_direction': self.sortdirection[self.getControl(SORT_DIRECTION_BTN).isSelected()]
            });

            nmParams = urllib.urlencode(self.navmenuparams);

            genres = funimationnow.getGenres(self.navigation.get('path', ''), nmParams);

            if genres:

                self.logger.debug(json.dumps(genres));

                self.setupGenreSelect(genres);


                pass;
            
        except Exception as inst:
            self.logger.error(inst);

            pass;


        self.setVisible(LOADING_SCREEN, False);


        pass;


    def setupGenreSelect(self, genres):

        self.genredata = genres;
        
        longList = utils.parseValue(genres, ['longList'], False);
        filters = utils.parseValue(longList, ['palette', 'filter'], False);
        items = utils.parseValue(longList, ['items'], False);

        self.navtitle = utils.parseValue(longList, ['title']);
        self.navpath = utils.parseValue(longList, ['items', 'pagination', 'path']);
        self.navparams = utils.parseValue(longList, ['items', 'pagination', 'params']);

        if filters:
            if not isinstance(filters, list):
                filters = list([filters]);

            try:

                self.logger.debug(json.dumps(filters))

                self.navmenu = dict();

                for oIdx, ftlr in enumerate(filters, 0):

                    fplatform = utils.parseValue(ftlr, ['@platforms']);

                    if fplatform != 'appletv':

                        fname = utils.parseValue(ftlr, ['name']);
                        fparam = utils.parseValue(ftlr, ['param']);
                        fvalue = utils.parseValue(ftlr, ['currentValue']);
                        fidx = 0;
                        fchoices = dict();

                        self.navmenu.update({
                            fname: dict()
                        });

                        buttons = utils.parseValue(ftlr, ['choices', 'button'], False);

                        if not isinstance(buttons, list):
                            buttons = list([buttons]);

                        #if oIdx == 0:
                        if fname == 'GENRE':

                            buttons.append(dict({
                                'title': 'RECENTLY ADDED',
                                'value': 'recent'
                            }));

                            if self.navitemcurrent == 'recent':
                                fvalue = 'recent';

                            buttons = sorted(buttons, key=lambda k: k['title']);

                        for idx, button in enumerate(buttons, 0):

                            btitle = utils.parseValue(button, ['title']);
                            bvalue = utils.parseValue(button, ['value']);

                            if self.navitemcurrent == '%s-shows-web' % bvalue:
                                
                                fvalue = bvalue;
                                self.navitemcurrent = bvalue;


                            fchoices.update({
                                idx: dict({
                                    'title': btitle,
                                    'value': bvalue
                                })
                            });

                            if bvalue == fvalue:
                                fidx = idx;

                        self.navmenu[fname].update({
                            'fname': fname,
                            'fparam': fparam,
                            'fvalue': fvalue,
                            'fidx': fidx,
                            'fchoices': fchoices
                        });


            except Exception as inst:
                self.logger.error(inst);

                pass;


            if self.navmenu and len(self.navmenu) >= 1:
                self.setNavigationIndex();
                pass;

            else:
                #throw an error
                pass;

        try:

            self.setVisible(LOADING_SCREEN, True);

            addOffset = False;

            if 'subfilter' in self.navmenuparams:

                import urlparse;
                import urllib;


                self.navparams = dict(urlparse.parse_qsl(self.navparams));

                for idx, menu in enumerate(self.navmenu, 0):

                    plItem = self.navmenu[menu];
                    plIdx = plItem.get('fidx', 0);
                    plParam = plItem.get('fparam', None);
                    plValue = plItem['fchoices'][plIdx].get('value', '');

                    if plValue == 'recent':
                        addOffset = True;

                    if plParam:
                        self.navparams.update({plParam: plValue});

                if self.navparams.get('id', None) == 'recent' and 'subfilter' in self.navparams:
                    self.navparams.pop('subfilter');

                if 'title' in self.navparams:
                    self.navparams.update({'title': re.sub(r'(Genre(%3A|:)(%20|[+ ]+))+', 'Genre: ', self.navparams.get('title', ''), re.I)});

                #self.navparams.update({'sort_direction': self.sortdirection[self.getControl(SORT_DIRECTION_BTN).isSelected()]});

                self.navparams = urllib.urlencode(self.navparams);

            else:
                addOffset = True;


            ceParams = self.navparams;

            if addOffset:
                ceParams = '%s&offset=0&limit=144' % ceParams;

            longList = funimationnow.getPage(self.navpath, ceParams);

            if longList:
                
                self.setShows(longList);

                pass;

        except Exception as inst:
            self.logger.error(inst);

            pass;


        pass;


    def setShows(self, longList):

        try:

            shControl = self.getControl(PANEL_LIST);
            shControl.reset();
            items = utils.parseValue(longList, ['items', 'item'], False);

            if items:

                if not isinstance(items, list):
                    items = list([items]);

                for idxxx, item in enumerate(items):

                    try:

                        button = None;
                        plPath = None;
                        plParams = None;

                        if self.myQueue is None:
                            self.myQueue = dict();

                        shTitle = utils.parseValue(item, ['title']);
                        shPath = utils.parseValue(item, ['pointer', 'path']);
                        shParams = utils.parseValue(item, ['pointer', 'params']);
                        #shThumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'xbox360']);
                        shThumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                        shThumbnail = shThumbnail if shThumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                        #shThumbnail = utils.parseValue(item, ['thumbnail', '#text']);
                        shThumbnail = funimationnow.formatImgUrl(shThumbnail, theme='show');
                        shStarRating = utils.parseValue(item, ['starRating', 'rating']);
                        shTitleimg = os.path.join(self.shows_list_title, ('s_%s.png' % shParams));
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

                        shTitleimg = utils.text2Title(list(titles), self.details_home_title, shTitleimg);

                        if shTitleimg:
                            shListitem.setProperty('ctitle', shTitleimg);

                        if shInQueue is not None:
                            shListitem.setProperty('qtexture', str(shInQueue));

                        if shRecentContentItem:

                            if shRecentContentItem == 'Episode':
                                shRecentContentItem = 'Movie';

                            tempImg = os.path.join(self.shows_list_subtitle, ('%s.png' % re.sub(r'[^\w\d]+', '_', shRecentContentItem, re.I)));

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

                                pass;


                            tempImg = os.path.join(self.shows_list_added, ('%s.png' % tfname));

                            #if not os.path.isfile(tempImg):
                            utils.text2Display(ttname, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Italic', tempImg, multiplier=1, sharpen=False, bgimage=None);

                            shListitem.setProperty('addedon', tempImg);


                        if shStarRating:

                            shStarRating = str(utils.roundQuarter(str(shStarRating)));
                            shListitem.setProperty('starrating', shStarRating);

                        else:
                            shListitem.setProperty('starrating', '0.0');

                            pass;


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


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;
        

    def setNavigationIndex(self):

        disableSelect = False;

        try:

            for idx, menu in enumerate(self.navmenu, 0):

                try:

                    sControl = self.getControl(NAV_SELECT_IMGS[idx]);
                    sItem = self.navmenu[menu];
                    sIdx = sItem.get('fidx', 0);
                    sTitle = sItem['fchoices'][sIdx].get('title', '');
                    sValue = sItem['fchoices'][sIdx].get('value', '');
                    sfName = re.sub(r'[/]+', '_', sTitle, re.I);
                    sImg = os.path.join(self.select_main, ('%s.png' % sfName));

                    if not os.path.isfile(sImg):
                        utils.text2Select(sTitle, 'RGB', None, (225, 225, 225), 30, 'Bold', sImg, multiplier=1, sharpen=True, bgimage='select_control_bg.png');

                    sControl.setImage(sImg, False);

                    if sValue in ('recent', 'recent-shows', 'star_rating'):
                        disableSelect = True;

                except:
                    pass;


        except Exception as inst:
            self.logger.error(inst);

            pass;

        if disableSelect:
            
            self.getControl(RANGE_SELECT_LIST).setEnabled(False);
            self.getControl(RANGE_SELECT_IMG).setImage('select_control_disabled_bg.png');

        else:
            self.getControl(RANGE_SELECT_LIST).setEnabled(True);

        self.setVisible(LOADING_SCREEN, False);


        pass;


    def getSelectList(self, controlID):

        from resources.lib.gui.navlistgui import select;

        try:

            cSelection = None;
            cMenu = None;

            pControl = self.getControl(FILTER_GROUP);
            sControl = self.getControl(controlID);

            (pX, pY) = pControl.getPosition();
            sX = (sControl.getPosition()[0] + pX);
            sY = sControl.getPosition()[1] + (sControl.getHeight() - 2);

            tIndex = NAV_SELECT_LISTS.index(controlID);

            if controlID == GENRE_SELECT_LIST:

                cSelection = select(self.navmenu.values()[tIndex], (sX + 1), sY);
                
                if cSelection is not None:
                    self.navmenu.values()[tIndex]['fidx'] = cSelection;

            elif controlID == SORT_SELECT_LIST:

                cSelection = select(self.navmenu.values()[tIndex], (sX + 1), sY);
                
                if cSelection is not None:
                    self.navmenu.values()[tIndex]['fidx'] = cSelection;

                pass;

            elif controlID == RANGE_SELECT_LIST:

                cSelection = select(self.navmenu.values()[tIndex], (sX + 1), sY);
                
                if cSelection is not None:
                    self.navmenu.values()[tIndex]['fidx'] = cSelection;

                pass;

            if cSelection is not None:

                import urlparse;
                import urllib;


                alts = ('shows', 'slug_exact', 'A-C');
                sParams = dict(urlparse.parse_qsl(self.navparams));

                #sParams.update({'title': ('Genre: %s' % self.navtitle)});

                for dIdx, nmenu in enumerate(self.navmenu.values(), 0):

                    sDict = self.navmenu.values()[dIdx];
                    sParam = (sDict['fparam'], sDict['fchoices'][sDict['fidx']].get('value', alts[dIdx]));

                    if dIdx == 0 and sParam[1] == 'recent':
                        sParam[1] == 'recent-shows';

                    sParams.update({
                        sParam[0]: sParam[1],
                    });


                sParams = urllib.urlencode(sParams);

                self.navigation.update({
                    'params': sParams,
                    #'sort_direction': self.sortdirection[self.getControl(SORT_DIRECTION_BTN).isSelected()]
                });

                self.getGenres();


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);

        pass;


    def getResultCode(self):
        return self.result_code;

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

        pass;


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



def genreselect(landing_page, navSet=None):

    
    genreselectui = GenreSelectUI("funimation-genre-select.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    genreselectui.setInitialItem(landing_page, navSet);
    genreselectui.doModal();

    del genreselectui;
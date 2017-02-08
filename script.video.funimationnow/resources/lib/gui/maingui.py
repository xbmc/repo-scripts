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
import sys;
import re;
import logging;
import time;
import gc;
import json;


from resources.lib.modules import utils;
from resources.lib.modules import funimationnow;
from resources.lib.modules import workers;
from resources.lib.modules import syncdata;



EXIT_CODE = 2;
SUCCESS_CODE = 3;
EXPIRE_CODE = 4;
HOME_SCREEN_CODE = 5;
BACK_CODE = 6;
LOGOUT_CODE = 7;
REST_CODE = 8;

RESULT_CODE = EXIT_CODE;

PREVIOUS_WINDOW = (
    xbmcgui.ACTION_PREVIOUS_MENU, 
    xbmcgui.ACTION_NAV_BACK
);

EXIT_CLICK = (
    xbmcgui.ACTION_MOUSE_DOUBLE_CLICK, 
    xbmcgui.ACTION_MOUSE_LONG_CLICK, 
    xbmcgui.ACTION_TOUCH_LONGPRESS
);


SEARCH_WINDOW = 100100;
HOME_WINDOW = 110101;
QUEUE_WINDOW = 110102;
ALL_WINDOW = 110103;
SIMALCAST_WINDOW = 110104;
GENRE_WINDOW = 110105;
SETTINGS_WINDOW = 110106;
HELP_WINDOW = 110107;
LOGOUT_WINDOW = 110108;

CURRENT_WINDOW = HOME_WINDOW;

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

SCREEN_NAV_BTNS = (
    20000,
    20001,
    20002,
    20003,
    20004,
    20005,
    20006,
    20007,
    20008,
);

SHOW_VIEWS = ('shows', 'features', 'myqueue');
EPISODE_VIEWS = ('episodes', 'history');

LOADING_SET = [['900'], ['200', '220', '205']];

MENU_IDS = (1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008);
SHOW_IDS = (20500, 20502, 20504, 20505, 20506, 20507, 20508);
NAV_LISTS = (20500, 20501, 20502, 20503, 20504, 20505, 20506, 20507, 20508);

QUE_BTNS = dict({
    20600: 20500,
    20602: 20502,
    20604: 20504,
    20605: 20505,
    20606: 20506,
    20607: 20507,
    20608: 20508,
});

LST_Q_REF = dict({
    20500: 20600,
    20502: 20602,
    20504: 20604,
    20505: 20605,
    20506: 20606,
    20507: 20607,
    20508: 20608,
});


MPAA = 'flagging/mpaa/tv-ma_c_us.png';
QUALITY = 'flagging/resolution/SD (480p)_c.png';
RATING = 'flagging/rating/0.0_c.png';
LOADING = 'list_loading_db.gif';

SHOWCASE_DISPLAY = 21002;
SHOWCASE_ART_CONTROL = 21000;
SHOWCASE_QUALITY_CONTROL = 2100200;
SHOWCASE_MPAA_CONTROL = 2100201;
SHOWCASE_SHOW_TITLE_CONTROL = 2100204;
SHOWCASE_SHOW_STATS_CONTROL = 2100205;
SHOWCASE_GENRE_CONTROL = 2100206;
SHOWCASE_DESCRIPTION_CONTROL = 2100207;
SHOWCASE_STAR_RATING_CONTROL = 2100210;

current_date = utils.setDate(True);
expire_date = utils.setDate(False);



class FunimationNowUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();
                   
        self.initialized = False;
        self.dblstatus = False;
        self.aList = None;
        self.aPos = None;
        self.starter = None;

        self.menus = dict();
        self.mkeys = dict();
        self.updates = dict();
        self.showDetails = dict();
        self.episodeDetails = dict();
        self.episodeDetailExtras = dict();
        self.navigation = dict();

        self.result_code = REST_CODE;

        self.landing_page = None;


    def onInit(self):

        if self.previousWindow:
            self.previousWindow.close();

        if self.result_code == HOME_SCREEN_CODE:
            self.result_code = REST_CODE;

        elif self.result_code in (LOGOUT_CODE, EXIT_CODE):

            self.landing_page = None;
            self.close();


        self.runDirectoryChecks();


        self.password_string = '';
        self.password_length = 0;

        self.buildDetails();

        utils.unlock();


    def setPrevWindow(self, prev):
        self.previousWindow = prev;


    def setLandingPage(self):
        self.landing_page = self;


    def onAction(self, action):

        if action.getId() in PREVIOUS_WINDOW:

            self.landing_page = None;
            self.result_code = EXIT_CODE;

            self.close();
            
            #xbmcgui.WindowXML.onAction(self, action);
            return;
            

        if xbmc.getCondVisibility("Control.HasFocus(%s)" % 5003):
            self.updateMaskedPassword();

        controlID = self.adjustPosition(action);

        if controlID < 20500 or controlID > 20509:

            self.getControl(SHOWCASE_ART_CONTROL).setImage('');
            self.getControl(21001).setImage('');

        elif action.getId() in (1, 2):

            if 20500 <= controlID <= 20509:

                try:

                    self.startDetailsProcess(controlID, True);


                except Exception as inst:
                    self.logger.error(inst);


            elif controlID in QUE_BTNS:
                #self.updateQueue(controlID, update=False); #listitem remove not working with threads
                workers.DetailsThread(target=self.updateQueue, args=(controlID, False,)).start();


            else:
                self.setVisible(SHOWCASE_DISPLAY, False);

        else:
            xbmcgui.WindowXML.onAction(self, action);


    def onClick(self, controlID):

        if controlID in range(20500, 20510):

            listitem = self.getControl(controlID).getSelectedItem();

            videourl = None;
            viewtype = None;

            videourl = listitem.getProperty('videourl');
            viewtype = listitem.getProperty('viewtype');
            closedCaptionUrl = listitem.getProperty('closedCaptionUrl');

            if videourl:

                from resources.lib.modules.player import player;

                try:

                    contMap = self.updates.get(20001, None);

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

                            self.logger.debug(pAdd);

                except:
                    pass;


                player().run(videourl, listitem);

            elif viewtype in SHOW_VIEWS:

                self.logger.debug("This is a show so we are launching the SHOW GUI")

                from resources.lib.gui.showgui import show;
                #window = xbmcgui.Window(xbmcgui.getCurrentWindowId());
                xrfPath = listitem.getProperty('detailPath');
                xrfParam = listitem.getProperty('detailParams');

                self.logger.debug(xrfPath)
                self.logger.debug(xrfParam)

                if viewtype and viewtype == 'myqueue':
                    xrfPath = listitem.getProperty('detailPath');
                    xrfParam = listitem.getProperty('detailParams');

                else:
                    xrfPath = listitem.getProperty('path');
                    xrfParam = listitem.getProperty('params');

                show(self.landing_page, xrfPath, xrfParam);
                

            else:
                self.logger.error(viewtype);
                self.logger.error('No Url Found');


        elif controlID == 5004:
            self.login();

        elif controlID == 4002:
            import webbrowser;

            webbrowser.open('http://www.funimation.com/android-mobile/register?territory=%s' % funimationnow.getTerritory(), new=0, autoraise=True)

        elif controlID == 4004:

            self.createLoginSplash();
            
            self.getControl(500).setVisible(True);
            self.getControl(400).setVisible(False);

        elif controlID == 5000:

            self.getControl(400).setVisible(True);
            self.getControl(500).setVisible(False);

        elif controlID == 5004:

            self.getControl(400).setVisible(False);
            self.getControl(500).setVisible(False);
            self.getControl(401).setVisible(True);


        elif controlID in MENU_IDS:
            
            funimationnow.execute(self.menus[controlID]);


        elif controlID in QUE_BTNS:
            #self.updateQueue(controlID, True);
            workers.DetailsThread(target=self.updateQueue, args=(controlID, True,)).start();


        elif controlID in SCREEN_NAV_BTNS:
            self.prepNavigation(controlID);


        elif controlID in SIDE_MENU:
            self.menuNavigation(controlID);


    def onFocus(self, controlID):

        if 20500 <= controlID <= 20509:

            try:
                self.startDetailsProcess(controlID, True);

            except Exception as inst:
                self.logger.error(inst);


            #self.populateDetails(controlID);

        elif controlID in QUE_BTNS:
            #self.updateQueue(controlID, update=False);
            workers.DetailsThread(target=self.updateQueue, args=(controlID, False,)).start();


        else:
            self.setVisible(SHOWCASE_DISPLAY, False);


    def adjustPosition(self, action):

        #self.logger.error(action.getId())

        controlID = 0;

        for idx in NAV_LISTS:

            if xbmc.getCondVisibility("Control.HasFocus(%s)" % idx):

                controlID = idx;

                break;


        return controlID;


    def getAdjustedImage(self, controlID):

        img = str(self.getControl(controlID).getSelectedItem().getProperty('showcaseimg'));

        return img;


    def updateMaskedPassword(self):

        bullet_string = '';

        self.password_field = self.getControl(50033);
        self.hidden_password_field = self.getControl(5003);

        #self.password_string = self.password_string[0:len(self.password_field.getText())];


        for idx in range(0, len(self.hidden_password_field.getText())):
            bullet_string += '*';


        self.password_field.setText(bullet_string);

        #http://zurb.com/article/279/how-to-mask-passwords-like-the-iphone

    
    def buildDetails(self):

        self.setLoadingStates(LOADING_SET, True);

        menuitems = funimationnow.menu();
        homescreenitems = None;

        if menuitems:
            self.setMenuItems(menuitems);

            #self.logger.error(self.menus)

            if 1001 in self.menus:

                homescreenitems = funimationnow.homescreenmenu(self.menus[1001]);

                if homescreenitems:

                    self.logger.debug(json.dumps(homescreenitems));
                    self.setHomeScreenItems(homescreenitems);

                else:
                    self.logger.error('NO HOMESCREEN ITEMS FOUND')

            else:
                self.logger.debug('WE NEED AN ERROR Notification')


    def setLoadingStates(self, vset, iterate=False):

        if iterate:

            for idx in range(0, 10):

                for ix, view in enumerate(vset, 0):

                    vstate = True if ix < 1 else False;

                    for cview in view:
                    
                        try:

                            cview = int('%s%02d' % (cview, idx));

                            self.setVisible(cview, vstate);

                        except Exception as inst:
                            #self.logger.error(inst);
                            pass;

        else:

            for ix, view in enumerate(vset, 0):

                vstate = True if ix < 1 else False;

                for cview in view:
                    
                    try:

                        self.setVisible(cview, vstate);

                    except Exception as inst:
                        #self.logger.error(inst);
                        pass;


    def setVisible(self, view, state):

        try:
            self.getControl(view).setVisible(state);

        except Exception as inst:
            self.logger.warn(inst);


    def setMenuItems(self, menuitems):

        #1001 - 1009

        utils.lock();

        idxoffset = 0;

        for idx, menu in enumerate(menuitems, 1):

            try:

                if 'ratethisapp' != menu['target']:

                    title = None;
                    target = None;
                    path = None;
                    params = None;
                    size = None;
                    fsize = None;

                    if 'register' == menu['target']:
                        
                        smenu = menu['registration']['registered'];

                        title = smenu['title'];
                        target = smenu['pointer']['target'];
                        path = smenu['pointer']['path'];
                        params = None;

                    else:

                        title = menu['title'];
                        target = menu['target'];
                        path = menu['path'];
                        params = menu['params'];


                    self.menus.update({
                        int('100%s' % (idx + idxoffset)): dict({
                            'title': title,
                            'target': target,
                            'path': path,
                            'params': params 
                        })
                    });

                    size = (600, 60) if 'themes' in menu else (600, 90);
                    fsize = 36 if 'themes' in menu else 58; 

                    utils.text2Button(title, 'RGB', [(61, 3, 136), (68, 3, 151)], [(255, 255, 255), (255, 255, 255)], fsize, 'ExtraBold', size, (20, 4), ['menu-focus-button%s' % (idx + idxoffset), 'menu-no-focus-button%s' % (idx + idxoffset)], True);

                else:
                    idxoffset += -1;


            except Exception as inst:
                self.logger.error(inst);

        utils.unlock();


    def setHomeScreenItems(self, pointers):

        #20000 - 20009
        #20500 - 20509

        utils.lock();
        #UI Locking is bad we want some kind of non locking notification for the main gui

        self.resetListContents();

        self.logger.debug('SETTING HOMESCREEN ITEMS');

        #sysaddon = sys.argv[0];
        #syshandle = int(sys.argv[1]);

        threads = [];
        idx = 0;

        for tidx, pointer in enumerate(pointers, 0):

            try:

                itemset = None;
                longList = None;
                navmenu = None;

                #processes = [];

                mid = int('200%02d' % idx);
                lid = int('205%02d' % idx);
                qid = int('206%02d' % idx);

                if 'themes' in pointer:

                    if 'funType' in pointer: #API Keeps changing, it appears they are adding device specific content in a poor fashion
                        
                        funType = utils.parseValue(pointer, ['funType']);

                        #if funType == 'carousel_hero mobile-spotlight':
                        if funType == 'carousel_hero mobile-spotlight-android':
                            itemset = funimationnow.contentCarousel(pointer, idx);

                        else:
                            continue;

                elif 'longList' in pointer:

                    longList = pointer['longList'];

                    if 'watchlist' in longList:
                        itemset = funimationnow.watchlist(pointer=pointer, idx=idx);

                        if itemset and len(itemset) >= 4:

                            if itemset[2]:

                                mid = int('200%02d' % idx);
                                
                                self.menus.update({
                                    mid: itemset[2]
                                });

                                self.mkeys.update({
                                    itemset[0]: mid
                                });

                                self.updates.update({
                                    mid: itemset[4]
                                });

                            self.navigation.update({
                                mid: dict({
                                    'navset': itemset[3],
                                    'navtype': 'watchlist'
                                })
                            });

                    else:

                        if 'themes' in longList:

                            dset = self.menus.get(self.mkeys.get('history', None), None);
                            itemset = funimationnow.episode(pointer, idx, dset);

                        else:

                            dset = self.menus.get(self.mkeys.get('myqueue', None), None);
                            itemset = funimationnow.show(pointer, idx, dset);


                        if itemset:

                            if bool(re.compile(r'.*showGenres=true.*', re.I).match(itemset[2].get('params', ''))):
                                navType = 'genres';

                            else: 
                                navType = 'dateadded';

                            self.navigation.update({
                                mid: dict({
                                    'navset': itemset[2],
                                    'navtype': navType
                                })
                            });

                            #success = ['shows', shows, navigation];


                if itemset:
                    self.formatItemSet(threads, itemset, mid, lid, qid);

                try:

                    vset = [[int('200%02d' % idx), int('220%02d' % idx), int('205%02d' % idx)], [int('900%02d' % idx)]];

                    self.setLoadingStates(vset, False);

                except Exception as inst:
                    self.logger.error(inst);


            except Exception as inst:
                self.logger.error(inst);

            idx += 1;

        #See Line 696 & 812.  This is assigned to something, and should not be marked as an error
        [i.start() for i in threads];
        #[i.join() for i in threads];

        utils.unlock();

        self.logger.debug(self.navigation);


    def formatItemSet(self, threads, itemset, mid, lid, qid):

        mcontrol = self.getControl(mid);
        lcontrol = self.getControl(lid);
        qcontrol = None;

        try:

            qcontrol = self.getControl(qid);
            #qcontrol.setSelected(False);

        except Exception as inst:
            self.logger.warn(inst);


        #for item in itemset[1]:
        for sIdx, item in enumerate(itemset[1], 0):

            titles = [];
            listitem = None;
            thumbnail = item.get('thumbnail', '');

            if lid in SHOW_IDS:
                thumbnail = funimationnow.formatImgUrl(thumbnail, theme='show');

            else:
                thumbnail = funimationnow.formatImgUrl(thumbnail, theme='episode');


            listitem = xbmcgui.ListItem(item.get('title', ''), item.get('subtitle', ''), thumbnail, thumbnail);

            if itemset[0] == 'episodes' or itemset[0] == 'history':

                titles = [item.get('title', ''), item.get('subtitle', '')];

            else:
                titles = [item.get('title', '')];


            titleimg = utils.text2Title(list(titles), self.details_home_title, item.get('titleimg', ''));
                
            listitem.setProperty('showcaseimg', funimationnow.formatImgUrl(thumbnail));

            try:

                listitem.setProperty('viewtype', str(itemset[0]));

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

                elif qcontrol:
                    qcontrol.setVisible(False);
            

            if titleimg:
                listitem.setProperty('ctitle', titleimg);

            lcontrol.addItem(listitem);                      

            prefetch = utils.setting('fn.background_sync');

            if prefetch is None or prefetch in ('true', 'True', True):

                #http://stackoverflow.com/questions/1787397/how-do-i-limit-the-number-of-active-threads-in-python
                threads.append(workers.DetailsThread(target=self.populateDetails, args=(lcontrol, listitem, sIdx, itemset[0], lid, False,)));


        if len(itemset) < 4:
            navmenu = itemset[2];

        else: 
            navmenu = itemset[3];


        if navmenu:
            #self.logger.error(navmenu.get('width', '0'))
            mcontrol.setWidth(int(navmenu.get('width', '0')));


    def startDetailsProcess(self, controlID, loadDisplay=False):

        cItem = self.getControl(controlID);
        sItem = cItem.getSelectedItem();

        try:

            noitem = sItem.getProperty('noitem');

            if noitem:

                if controlID == 20502:
                    self.setVisible(20602, False);

                    return;

                elif controlID == 20501:
                    return;


            elif controlID == 20502 and cItem.size() < 1:
                self.setVisible(20602, False);


            elif controlID == 20502:
                self.setVisible(20602, True);

        except:
            pass;


        self.setVisible(SHOWCASE_DISPLAY, True);

        self.resetImage(SHOWCASE_ART_CONTROL);
        self.resetImage(SHOWCASE_DESCRIPTION_CONTROL);

        self.getControl(SHOWCASE_SHOW_TITLE_CONTROL).setImage(LOADING);
        self.getControl(SHOWCASE_SHOW_STATS_CONTROL).setImage(LOADING);
        self.getControl(SHOWCASE_GENRE_CONTROL).setImage(LOADING);
        self.getControl(SHOWCASE_MPAA_CONTROL).setImage(MPAA);
        self.getControl(SHOWCASE_QUALITY_CONTROL).setImage(QUALITY);
        self.getControl(SHOWCASE_STAR_RATING_CONTROL).setImage(RATING);

        sIdx = cItem.getSelectedPosition();
        viewtype = sItem.getProperty('viewtype');

        self.aList = controlID;
        self.aPos = sIdx;

        workers.DisplayThread(target=self.populateDetails, args=(cItem, sItem, sIdx, viewtype, controlID, loadDisplay,)).start();


    def populateDetails(self, cItem, sItem, sIdx, viewtype, controlID, loadDisplay):

        try:

            #if loadDisplay is False:
                #time.sleep(sIdx*2)

            detailspath = os.path.join(utils.getAddonInfo('path'), 'resources/skins/default/media/');

            titleImg = None;
            statsImg = None;
            genreImg = None;
            descImg = None;
            starImg = None;
            qualityImg = None;
            ratingImg = None;


            if viewtype in SHOW_VIEWS:
                
                (starRating, quality, ratings, params) = self.setShowDetails(cItem, sItem, sIdx, viewtype, loadDisplay);

                titleImg = os.path.join(self.details_title, ('%s.png' % params));
                statsImg = os.path.join(self.details_stats, ('%s.png' % params));
                genreImg = os.path.join(self.details_genre, ('%s.png' % params));
                descImg = os.path.join(self.details_desc, ('%s.png' % params));
                
            else:

                (starRating, quality, ratings, params) = self.setEpisodeDetails(cItem, sItem, sIdx, viewtype, loadDisplay);

                titleImg = os.path.join(self.details_title, ('%s.png' % params));
                statsImg = os.path.join(self.details_stats, ('%s.png' % params));
                genreImg = os.path.join(self.details_genre, ('%s.png' % params));
                descImg = os.path.join(self.details_desc, ('%s.png' % params));


            if ratings is None:

                tmpTerritory = funimationnow.getTerritory();

                if tmpTerritory:

                    if tmpTerritory == 'CA':
                        ratings = '18';

                    elif tmpTerritory == 'GB':
                        ratings = 'r18';

                    elif tmpTerritory == 'IE':
                        ratings = 'ma';

                    else:
                        ratings = 'tv-ma';


            starImg = '%sflagging/rating/%s_c.png' % (detailspath, starRating);
            qualityImg = '%sflagging/resolution/%s_c.png' % (detailspath, quality);
            ratingImg = ('%sflagging/mpaa/%s_c_%s.png' % (detailspath, ratings.lower(), funimationnow.getTerritory().lower()));


            if loadDisplay:

                ncItem = self.getControl(controlID);
                nsIdx = ncItem.getSelectedPosition();

                if self.aList == controlID and self.aPos == nsIdx:

                    self.getControl(SHOWCASE_ART_CONTROL).setImage(self.getAdjustedImage(controlID));
                    self.setDownloadedDetails(titleImg, statsImg, genreImg, descImg, params, starImg, qualityImg, ratingImg);           

                
        except Exception as inst:
            self.logger.error(inst);


    def setShowDetails(self, cItem, sItem, sIdx, viewtype, loadDisplay):

        if viewtype and viewtype == 'myqueue':
            path = sItem.getProperty('detailPath');
            params = sItem.getProperty('detailParams');

        else:
            path = sItem.getProperty('path');
            params = sItem.getProperty('params');

        titleimg = sItem.getProperty('titleimg');
        title = sItem.getProperty('title');

        counters = None;
        genres = None;
        description = None;

        starRating = '0.0';
        quality = 'HD (1080p)';
        ratings = 'tv-ma';


        if loadDisplay:

            self.getControl(SHOWCASE_SHOW_TITLE_CONTROL).setImage(LOADING);
            self.getControl(SHOWCASE_SHOW_STATS_CONTROL).setImage(LOADING);
            self.getControl(SHOWCASE_GENRE_CONTROL).setImage(LOADING);


        if params not in self.showDetails:

            detailData = syncdata.getDetailsData(params);
            dateExpired = True;

            if detailData:
                dateExpired = utils.dateExpired(detailData[2]);

            if dateExpired:

                sDetails = funimationnow.selection(path, params, 'showDesc', viewtype, sIdx, loadDisplay);

                if sDetails:

                    syncdata.setDetailsData(params, sDetails, expire_date);

                    self.showDetails.update({params: sDetails});

                    try:
                        counters = 'Seasons: %02d  |  Episodes: %02d  |  Year: %s' % (sDetails.get('seasons', 0), sDetails.get('episodes', 0), sDetails.get('releaseYear', 2016));

                    except Exception as inst:

                        if loadDisplay:
                            self.resetImage(SHOWCASE_SHOW_STATS_CONTROL);

                        self.logger.error(inst);

                    try:
                        #New API Removed Genres added lame show status.  We will keep genres incase they decide ot add it back
                        #genres = 'Genres: %s' % sDetails.get('genres', 'NA');

                        genres = 'Info: %s' % sDetails.get('sinfo', 'NA');

                    except Exception as inst:

                        if loadDisplay:
                            self.resetImage(SHOWCASE_GENRE_CONTROL);

                        self.logger.error(inst);

                    try:
                        description = sDetails.get('description', None);

                    except Exception as inst:

                        if loadDisplay:
                            self.resetImage(SHOWCASE_DESCRIPTION_CONTROL);

                        self.logger.error(inst);


                dtlList = list([
                    [title, 56, os.path.join(self.details_title, ('%s.png' % params))], 
                    [counters, 36, os.path.join(self.details_stats, ('%s.png' % params))], 
                    [genres, 36, os.path.join(self.details_genre, ('%s.png' % params))]
                ]);

                self.makeDetails(dtlList);

                os.path.join(self.details_title, ('%s.png' % params))
                os.path.join(self.details_stats, ('%s.png' % params))
                os.path.join(self.details_genre, ('%s.png' % params))
                os.path.join(self.details_desc, ('%s.png' % params))


                if description:
                    utils.text2DisplayWrap(description, 'RGB', (164, 164, 164), (255, 255, 255), 36, (976, 400), 52, 'SemiBold', os.path.join(self.details_desc, ('%s.png' % params)), multiplier=1, sharpen=False, bgimage=None);


            else:

                sDetails = json.loads(detailData[1]);

                self.showDetails.update({params: sDetails});


        else:
            sDetails = self.showDetails.get(params, None);


        if sDetails:

            starRating = utils.roundQuarter(str(sDetails.get('starRating', '0.0')));
            quality = sDetails.get('quality', 'HD (1080p)');

            ratings = sDetails.get('ratings', 'tv-ma');


        return list([starRating, quality, ratings, params]);


    def setEpisodeDetails(self, cItem, sItem, sIdx, viewtype, loadDisplay):

        self.logger.debug('Setting Episode Details');

        path = sItem.getProperty('path');
        params = sItem.getProperty('params');
        historyParams = sItem.getProperty('historyParams');
        titleimg = sItem.getProperty('titleimg');
        title = sItem.getProperty('title');
        progress = sItem.getProperty('progress');
        duration = sItem.getProperty('duration');
        quality = sItem.getProperty('quality');

        subtitle = None;
        genres = None;
        description = None;
        seasoninfo = None;
        description = None;

        season = 0;
        episode = 0;
        
        starRating = '0.0';
        ratings = 'tv-ma';

        efname = re.search(r'video_id=(\w+)', historyParams);

        try:
            efname = str(efname.group(1));

        except:
            efname = 'ed_filler';


        if loadDisplay:

            self.getControl(SHOWCASE_SHOW_TITLE_CONTROL).setImage(LOADING);
            self.getControl(SHOWCASE_SHOW_STATS_CONTROL).setImage(LOADING);
            self.getControl(SHOWCASE_GENRE_CONTROL).setImage(LOADING);


        if params not in self.episodeDetails:

            detailData = syncdata.getDetailsData(params);
            dateExpired = True;

            if detailData:
                dateExpired = utils.dateExpired(detailData[2]);

            if dateExpired:

                sDetails = funimationnow.selection(path, params, 'episodeDesc', viewtype, sIdx, loadDisplay);

                if sDetails == False:
                    
                    tparams = re.sub(r'audio=ja', 'audio=1', params);
                    tparams = re.sub(r'audio=en', 'audio=2', tparams);

                    sDetails = funimationnow.selection(path, tparams, 'episodeDesc', viewtype, sIdx, loadDisplay);


                if sDetails:

                    epsPath = sDetails.get('path', None);
                    epsParam = sDetails.get('params', None);

                    if epsPath and epsParam:
                        
                        extras = funimationnow.getEpisodeDetailExtras(epsPath, epsParam, loadDisplay);

                        #We need to make sure the extras get incorporated

                        if extras:

                            sDetails.update({'starRating': extras.get('starRating', '0.0')});


                    syncdata.setDetailsData(params, sDetails, expire_date);

                    self.episodeDetails.update({params: sDetails});


                    try:

                        seasoninfo = self.formatSeasonInfo(sDetails, progress);

                    except Exception as inst:

                        if loadDisplay:
                            self.resetImage(SHOWCASE_SHOW_STATS_CONTROL);

                        self.logger.error(inst);

                    try:
                        subtitle = 'Title: %s' % sDetails.get('subtitle', 'NA');

                        #self.logger.error(subtitle)

                    except Exception as inst:

                        if loadDisplay:
                            self.resetImage(SHOWCASE_GENRE_CONTROL);

                        self.logger.error(inst);

                    try:
                        description = sDetails.get('description', None);


                    except Exception as inst:

                        if loadDisplay:
                            self.resetImage(SHOWCASE_DESCRIPTION_CONTROL);

                        self.logger.error(inst);

                dtlList = list([
                    [title, 56, os.path.join(self.details_title, ('%s.png' % efname))], 
                    [seasoninfo, 36, os.path.join(self.details_stats, ('%s.png' % efname))], 
                    [subtitle, 36, os.path.join(self.details_genre, ('%s.png' % efname))]
                ]);

                self.makeDetails(dtlList);


                if description:
                    utils.text2DisplayWrap(description, 'RGB', (164, 164, 164), (255, 255, 255), 36, (976, 400), 52, 'SemiBold', os.path.join(self.details_desc, ('%s.png' % efname)), multiplier=1, sharpen=False, bgimage=None);

            else:

                sDetails = json.loads(detailData[1]);

                self.episodeDetails.update({params: sDetails});


        else:

            sDetails = self.episodeDetails.get(params, None);

            try:

                seasoninfo = self.formatSeasonInfo(sDetails, progress);

                dtlList = list([
                    [seasoninfo, 36, os.path.join(self.details_stats, ('%s.png' % efname))], 
                ]);

                self.makeDetails(dtlList);


            except Exception as inst:

                if loadDisplay:
                    self.resetImage(SHOWCASE_SHOW_STATS_CONTROL);

                self.logger.error(inst);


        if sDetails:

            videourl = sDetails.get('videourl', None);
            starRating = sDetails.get('starRating', '0.0');

            if videourl:
                sItem.setProperty('videourl', videourl);


            starRating = utils.roundQuarter(str(starRating));
            quality = quality if quality is not None else 'HD (1080p)';
            ratings = sDetails.get('ratings', 'tv-ma');


        return list([starRating, quality, ratings, efname]);


    def resetImage(self, control):
        self.getControl(control).setImage('');


    def makeDetails(self, details):

        for detail in details:

            if detail[0]:
                 utils.text2Display(detail[0], 'RGB', (164, 164, 164), (255, 255, 255), detail[1], 'ExtraBold', detail[2], multiplier=1, sharpen=False, bgimage=None);


    def formatSeasonInfo(self, sDetails, progress):

        import datetime;

        season = sDetails.get('season', 'Season 0');
        episode = sDetails.get('episode', 'Episode 0');
        #We wanted a special parser but since the new API sucks it is more trouble to determine the video type

        duration = sDetails.get('duration', 0);

        duration = int((0 if (duration is None or len(duration) < 1) else int(duration)) * 0.001);
        progress = str(0 if (progress is None or len(str(progress)) < 1) else progress);

        #Doesnt appear to work in all versions of Kodi
        #duration = '{}'.format(datetime.timedelta(seconds=int(duration)));
        #progress = '{}%'.format(progress);

        duration = str(datetime.timedelta(seconds=int(duration)));
        progress += '%';

        # we might need to change this later so that we cna update the progress realtime

        seasoninfo = '%s  |  %s  |  Duration: %s  |  Progress: %s' % (season, episode, duration, progress);

        
        return seasoninfo;


    def resetListContents(self):

        for idx in range(0, 10):

            try:

                idx = int('205%02d' % idx);

                tlControl = self.getControl(idx);

                if tlControl:
                    tlControl.reset();

            except:
                pass;

    
    def setDownloadedDetails(self, titleImg, statsImg, genreImg, descImg, params, starImg, qualityImg, ratingImg):

        gc.collect();
        
        self.getControl(SHOWCASE_SHOW_TITLE_CONTROL).setImage(titleImg, False);
        self.getControl(SHOWCASE_SHOW_STATS_CONTROL).setImage(statsImg, False);
        self.getControl(SHOWCASE_GENRE_CONTROL).setImage(genreImg, False);
        self.getControl(SHOWCASE_DESCRIPTION_CONTROL).setImage(descImg, False);
        self.getControl(SHOWCASE_STAR_RATING_CONTROL).setImage(starImg, False);
        self.getControl(SHOWCASE_QUALITY_CONTROL).setImage(qualityImg, False);
        self.getControl(SHOWCASE_MPAA_CONTROL).setImage(ratingImg, False);
        self.setVisible(SHOWCASE_ART_CONTROL, True);


    def updateQueue(self, controlID, update=False):

        try:

            qBtn = self.getControl(controlID);
            qCtrl = self.getControl(QUE_BTNS[controlID]);
            qPos = qCtrl.getSelectedPosition();
            qItem = qCtrl.getSelectedItem();
            qState = int(qItem.getProperty('qtexture'));

            updateQ = False;

            if update:

                viewtype = qItem.getProperty('viewtype');

                if viewtype == 'myqueue':

                    updateQ = True;

                    qPath = qItem.getProperty('myQueuePath');
                    qParams = qItem.getProperty('myQueueParams');

                else:

                    qPath = qItem.getProperty('togglePath');
                    qParams = qItem.getProperty('toggleParams');


                if qPath and qParams:

                    updated = funimationnow.updateQueue(qPath, qParams, qState);

                    if updated:

                        if qState > 0:

                            qItem.setProperty('qtexture', '0');
                            qBtn.setSelected(0);

                            self.adjustNavShowQueueState(qParams, 0);

                            if not updateQ:

                                itemset = funimationnow.watchlist('myqueue', qParams, pointer=None, idx=None);

                                if itemset:

                                    ttItem = self.getControl(20502);
                                    tsItem = ttItem.selectItem(0);
                                    tsItem = ttItem.getSelectedItem();

                                    try:

                                        noitem = tsItem.getProperty('noitem');

                                        if noitem:
                                            ttItem.removeItem(0);

                                    except Exception as inst:
                                        self.logger.error(inst);

                                    threads = [];

                                    self.formatItemSet(threads, itemset, 20002, 20502, 20602);

                                    [i.start() for i in threads];

                        else:
                            
                            qItem.setProperty('qtexture', '1');
                            qBtn.setSelected(1);

                            self.adjustNavShowQueueState(qParams, '1');

                            if updateQ:
                                qCtrl.removeItem(qPos);

                                if qCtrl.size() < 1:
                                    self.setVisible(20602, False);

                            else:

                                try:
                                    
                                    tCtrl = self.getControl(20502);
                                    tSize = tCtrl.size();

                                    for tix in range(0, tSize):

                                        try:

                                            tItem = tCtrl.getListItem(tix);

                                            if tItem:

                                                tParam = tItem.getProperty('myQueueParams');

                                                if tParam == qParams:
                                                    tCtrl.removeItem(tix);

                                                    break;

                                        except Exception as inst:
                                            #self.logger.error(inst);
                                            
                                            pass;


                                except Exception as inst:
                                    self.logger.error(inst);


                                #needs to add que lookup for epty list
                    

            else:
                qBtn.setSelected(qState);


        except Exception as inst:
            self.logger.error(inst);


    def adjustNavShowQueueState(self, qParams, qState):

        for idx in SHOW_IDS:

            try:

                sList = self.getControl(idx);
                sSize = sList.size();

                for sIdx in range(0, sSize):

                    lItem = sList.getListItem(sIdx);

                    if lItem:

                        lParam = lItem.getProperty('toggleParams');

                        if lParam == qParams:
                            lItem.setProperty('qtexture', str(qState));

                            break;


            except Exception as inst:
                self.logger.error(inst);


    def prepNavigation(self, controlID):

        navSet = self.navigation.get(controlID, None);

        if navSet:

            navtype = navSet.get('navtype', None);
            navset = navSet.get('navset', None);

            #self.logger.debug(json.dumps(self.navigation))

            if navset:

                if navtype == 'genres':
                    from resources.lib.gui.genreselectgui import genreselect;

                    genreselect(self.landing_page, navset);

                
                elif navtype == 'dateadded':
                    from resources.lib.gui.audioselectgui import audioselect;

                    audioselect(self.landing_page, navset);

                elif navtype == 'watchlist':
                    from resources.lib.gui.watchlistgui import watchlist;

                    watchlist(self.landing_page, navset);

            else:
                self.logger.error('Navigation error we need to send an alert');

        else:
            self.logger.error('NO NAV SET FOUND')
            self.logger.error('-------------------')


    def menuNavigation(self, controlID):

        from resources.lib.modules import menunav;

        try:

            RESULT_CODE = menunav.chooser(self.landing_page, self, CURRENT_WINDOW, controlID);

            if RESULT_CODE == LOGOUT_CODE:
                
                self.result_code = LOGOUT_CODE;
                self.close();

            elif RESULT_CODE == HOME_SCREEN_CODE:
                self.result_code = REST_CODE;

        except Exception as inst:
            self.logger.error(inst);


    def setMenuButtonPlaceHolders(self):

        for idx in range(1, 9):

            try:
            
                btxt = utils.lang(int('3052%d' % idx));
                size = (600, 60) if idx >= 6 else (600, 90);
                fsize = 36 if idx >= 6 else 58; 

                utils.text2Button(btxt, 'RGB', [(61, 3, 136), (68, 3, 151)], [(255, 255, 255), (255, 255, 255)], fsize, 'ExtraBold', size, (20, 4), ['menu-focus-button%s' % idx, 'menu-no-focus-button%s' % idx], True, filecheck=True);

            except Exception as inst:
                self.logger.error(inst);


        for idx in range(0, 9):

            try:
            
                btxt = utils.lang(int('3050%d' % idx));

                utils.text2HomeMenu(idx, btxt, filecheck=True);

            except Exception as inst:
                self.logger.error(inst);


    def getResultCode(self):
        return self.result_code;


    def runDirectoryChecks(self):

        #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', utils.getAddonInfo('id')));
        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.details_title = os.path.join(dsPath, 'media/details/title');
        self.details_stats = os.path.join(dsPath, 'media/details/stats');
        self.details_genre = os.path.join(dsPath, 'media/details/genre');
        self.details_desc = os.path.join(dsPath, 'media/details/desc');
        self.details_home_title = os.path.join(dsPath, 'media/details/home/title');

        utils.checkDirectory(self.details_title);
        utils.checkDirectory(self.details_stats);
        utils.checkDirectory(self.details_genre);
        utils.checkDirectory(self.details_desc);
        utils.checkDirectory(self.details_home_title);


    


def main(prev=None):
    
    fnui = FunimationNowUI("funimation-main.xml", utils.getAddonInfo('path'), 'default', "720p");

    fnui.setMenuButtonPlaceHolders();
    fnui.setPrevWindow(prev);
    fnui.setLandingPage();
    
    fnui.doModal();

    resultCode = fnui.getResultCode();
    
    del fnui;

    return resultCode;
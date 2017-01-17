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
import datetime;

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

EPISODE_PREVIEW_GROUP = 900;
EPISODE_PREVIEW_EP_NUMBER = 9000;
EPISODE_PREVIEW_TITLE = 9001;
EPISODE_PREVIEW_SUBTITLE = 9002;
EPISODE_PREVIEW_LANGUAGE = 9003;
EPISODE_PREVIEW_DURATION = 9004;
EPISODE_PREVIEW_QUALITY = 9005;
EPISODE_PREVIEW_DESCRIPTION = 9006;
EPISODE_PREVIEW_THUMBNAIL = 9007;
EPISODE_PREVIEW_PROGRESS = 9008;
EPISODE_PREVIEW_USER_RATING = 9010;
EPISODE_PREVIEW_STAR_RATING = 9012;

EPISODE_LIST = 4010;
RELATED_SHOWS_LIST = 80001;

RELATED_SHOWS_TITLE = 8000;

SPOTLIGHT_GROUP = 400;
SPOTLIGHT_NAME = 4000;
SPOTLIGHT_TITLE = 4001;
SPOTLIGHT_DURATION = 4002;
SPOTLIGHT_PREVIEW = 4003;
SPOTLIGHT_PROGRESS = 4004;

VERSIONS_SELECT_LIST = 4007;
VERSIONS_SELECT_IMG = 4006;
SEASONS_SELECT_LIST = 4009;
SEASONS_SELECT_IMG = 4008;
LANGUAGE_SELECT_LIST = 9014;
LANGUAGE_SELECT_IMG = 9013;

DISPLAY_BACKDROP_IMG = 200;
DISPLAY_TITLE_IMG = 3000;
DISPLAY_RATING_IMG = 3001;
DISPLAY_QUALITY_IMG = 3004;
DISPLAY_DESCRIPTION_IMG = 3005;

SHOW_RATING_BTN = 3002;
EPISODE_RATING_BTN = 9011;

RATING_BTNS = (
    SHOW_RATING_BTN,
    EPISODE_RATING_BTN
);

SPOTLIGHT_PLAY_BTN = 4005;
LIST_PLAY_BTN = 9009;
BACK_BTN = 1001;
SHOW_QUEUE_BTN = 3006;
LIST_QUEUE_BTN = 80002;

WINDOW_LOADING = 500;
EPISODE_LOADING = 4200;


LOADING_SCREENS = (
    WINDOW_LOADING, 
    EPISODE_LOADING
);

QUEUE_BTNS = (
    SHOW_QUEUE_BTN, 
    LIST_QUEUE_BTN
);

LIST_PLAYBACK = (
    EPISODE_LIST, 
    LIST_PLAY_BTN
);

PLAYBACK_BTNS = (
    SPOTLIGHT_PLAY_BTN, 
    LIST_PLAY_BTN, 
    EPISODE_LIST
);

PREVIOUS_WINDOW = (
    xbmcgui.ACTION_PREVIOUS_MENU, 
    xbmcgui.ACTION_NAV_BACK
);

EXIT_CLICK = (
    xbmcgui.ACTION_MOUSE_DOUBLE_CLICK, 
    xbmcgui.ACTION_MOUSE_LONG_CLICK, 
    xbmcgui.ACTION_TOUCH_LONGPRESS
);


class ShowViewUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.landing_page = None;
        self.spotlight = None;
        self.episodes = None;
        self.navmenu = None;
        self.myQueue = None;
        self.myHistory = None;
        self.myRatings = None;
        self.queueLookup = None;
        self.histLookup = None;
        self.rateLookup = None;
        self.starRatingPath = None;
        self.starRatingParams = None;
        self.starRating = None;
        self.starKey = None;
        self.showCaseQueue = None;
        self.userRating = 0;
        self.currentIndex = 0;

        self.depth = dict();
        self.languages = dict();

        self.logger = utils.getLogger();
                   

    def onInit(self):

        if self.landing_page and self.landing_page.result_code in (HOME_SCREEN_CODE, EXIT_CODE, LOGOUT_CODE):
            self.close();

        else:

            #self.logger.debug(xbmc.getUserAgent());

            self.setVisible(WINDOW_LOADING, True);
            self.setVisible(EPISODE_LOADING, True);

            self.checkHistory();
            self.checkQueue();
            self.checkRatings();

            self.runDirectoryChecks();

            if len(self.depth) > 0:

                self.createShowDisplay();
                self.updateSeasonList();

            utils.unlock();

        pass;


    def onAction(self, action):

        actionID = action.getId();
        controlID = self.getConrolID(action);

        if actionID in EXIT_CLICK and controlID == BACK_BTN:
            self.close();

            pass;

        elif actionID in PREVIOUS_WINDOW:
            self.updateDepth();

            pass;

        
        if controlID in (LIST_QUEUE_BTN, RELATED_SHOWS_LIST):
            self.updateQueue(LIST_QUEUE_BTN, False);

        
        if controlID == EPISODE_LIST:
            self.setListDisplay();

        
        pass;


    def onClick(self, controlID):

        #self.logger.debug(controlID)

        if controlID == BACK_BTN:
            #self.close();
            self.updateDepth();
            pass;

        elif controlID in (VERSIONS_SELECT_LIST, SEASONS_SELECT_LIST):
            self.currentIndex = 0;
            self.getSelectList(controlID);

        elif controlID == LANGUAGE_SELECT_LIST:
            self.getLangSelectList();

        elif controlID == RELATED_SHOWS_LIST:
            self.currentIndex = 0;
            self.updateDepth(True);

            pass;

        elif controlID in RATING_BTNS:
            self.setUserRating(controlID);

            pass;

        elif controlID in PLAYBACK_BTNS:
            self.prepPlayBack(controlID);
            
            pass;

        elif controlID in QUEUE_BTNS:
            from resources.lib.modules import workers;

            workers.DetailsThread(target=self.updateQueue, args=(controlID, True)).start();

            pass;


        pass;


    def onFocus(self, controlID):

        if controlID == EPISODE_LIST:
            self.setListDisplay();

        elif controlID in (LIST_QUEUE_BTN, RELATED_SHOWS_LIST):
            self.updateQueue(LIST_QUEUE_BTN, False);

        pass;


    def setInitialItem(self, landing_page, xrfPath, xrfParam):

        try:

            #Test Values
            #xrfPath = 'detail/';
            #xrfParam = 'pk=24351';
            #landing_page = self;

            self.depth.update({
                0: dict({
                    'path': xrfPath,
                    'params': xrfParam
                })
            });

            self.landing_page = landing_page;


        except Exception as inst:
            self.logger.error(inst);

            pass;


        pass;


    def checkHistory(self):

        if self.histLookup is None:
            self.histLookup = funimationnow.getHistoryConfig();

            if self.histLookup:
                self.myHistory = funimationnow.getHistory(self.histLookup);

        else:
            self.myHistory = funimationnow.getHistory(self.histLookup);

            pass;

        self.logger.debug(json.dumps(self.myHistory));


    def checkQueue(self):

        if self.queueLookup is None:
            self.queueLookup = funimationnow.getMyQueueConfig();

            if self.queueLookup:
                self.myQueue = funimationnow.getMyQueue(self.queueLookup);

        else:
            self.myQueue = funimationnow.getMyQueue(self.queueLookup);

            pass;

        self.logger.debug(json.dumps(self.myQueue));


    def checkRatings(self):

        if self.rateLookup is None:
            self.rateLookup = funimationnow.getRatingsConfig();

            if self.rateLookup:
                self.myRatings = funimationnow.getMyRatings(self.rateLookup);

        else:
            self.myRatings = funimationnow.getMyRatings(self.rateLookup);

            pass;

        self.logger.debug(json.dumps(self.myRatings));


    def updateDepth(self, state=None):

        from threading import Timer;

        try:

            dSize = (len(self.depth) - 1);

            if state:
                
                slControl = self.getControl(RELATED_SHOWS_LIST);
                slListItem = slControl.getSelectedItem();

                shPath = slListItem.getProperty('path');
                shParams = slListItem.getProperty('params');

                self.depth.update({
                    (dSize + 1): dict({
                        'path': shPath,
                        'params': shParams
                    })
                });

            else:

                if dSize == 0:
                    self.close();

                elif dSize in self.depth:

                    try:
                        self.depth.pop(dSize);

                    except Exception as inst:
                        self.logger.error(inst);
                        
                        pass;

            t = Timer(0.15, self.createShowDisplay);
            t.start();


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;


    def setUserRating(self, controlID):

        from resources.lib.gui.ratingsgui import rating;

        '''
            Appears to be some API issue with individual episode ratings
            <authentication>
                <error>Unexpected response from legacy api when posting user rating</error>
                <anonymous>false</anonymous>
            </authentication>

            #Update, New API Appears to work
        '''

        try:

            if controlID == SHOW_RATING_BTN:


                userRating = rating(self.userRating);

                if userRating:
            
                    success = funimationnow.updateRating(userRating, self.rateLookup, self.starRatingPath, self.starRatingParams);

                    if success:

                        self.userRating = userRating;

                        self.logger.debug(self.userRating);
                        self.logger.debug('flagging/rating/%s_overlay.png' % self.userRating);

                        self.getControl(DISPLAY_RATING_IMG).setImage('flagging/rating/%s_overlay.png' % self.userRating);
                        self.checkRatings();

                    pass;


            elif controlID == EPISODE_RATING_BTN:

                    tmpItem = self.getControl(EPISODE_LIST).getSelectedItem();

                    tmpsPath = tmpItem.getProperty('starPath');
                    tmpsParams = tmpItem.getProperty('starParams');
                    tmpsKey = tmpItem.getProperty('starKey');
                    tmpsRating = self.myRatings.get(tmpsKey, None);

                    if tmpsRating is None:
                        tmpsRating = 0;

                    else:
                        tmpsRating = tmpsRating.get('myStarRating', 0);


                    userRating = rating(tmpsRating);

                    if userRating:

                        success = funimationnow.updateRating(userRating, self.rateLookup, tmpsPath, tmpsParams);

                        if success:

                            self.userRating = userRating;

                            self.getControl(EPISODE_PREVIEW_USER_RATING).setImage('flagging/rating/%s_overlay.png' % self.userRating);
                            self.checkRatings();

                        pass;


        except Exception as inst:
            self.logger.error(inst);

            pass;


        self.checkRatings();


        pass;


    def updateQueue(self, controlID, update=False):

        try :

            if controlID == SHOW_QUEUE_BTN:

                qcBtn = self.getControl(SHOW_QUEUE_BTN);

                qState = int(not qcBtn.isSelected());
                qPath = self.showCaseQueue.get('qPath');
                qParams = self.showCaseQueue.get('qParams');

                updated = funimationnow.updateQueue(qPath, qParams, qState);

                if updated:
                    self.checkQueue();

                else:
                    qcBtn.setSelected(qState);


            elif controlID == LIST_QUEUE_BTN:

                qcBtn = self.getControl(LIST_QUEUE_BTN);
                qItem = self.getControl(RELATED_SHOWS_LIST).getSelectedItem();

                #qState = int(not qcBtn.isSelected());
                qState = int(qItem.getProperty('qtexture'));

                if update:

                    qPath = qItem.getProperty('togglePath');
                    qParams = qItem.getProperty('toggleParams');

                    updated = funimationnow.updateQueue(qPath, qParams, qState);

                    if updated:

                        qcBtn.setSelected((not qState));
                        qItem.setProperty('qtexture', str(int(not qState)));

                        self.checkQueue();

                    else:
                        qcBtn.setSelected(qState);

                else:
                    #qcBtn.setVisible(False)
                    qcBtn.setSelected(qState);
                    #qcBtn.setVisible(True)


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;


    def updateSeasonList(self):

        try:

            dSize = (len(self.depth) - 1);

            seasonList = self.depth.get(dSize, None);

            if seasonList:

                ssnPath = seasonList.get('sPath', None);
                ssnParams = seasonList.get('sParams', None);

                if ssnPath and ssnParams:

                    sepisodeset = funimationnow.getLongList(ssnPath, ssnParams);

                    if sepisodeset:
                        self.setSeasonEpisodes(sepisodeset);

                        sfilters = utils.parseValue(sepisodeset, ['palette', 'filter'], False);

                        if sfilters:
                            self.setSeasonInfo(sfilters);


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def createShowDisplay(self):

        self.setVisible(WINDOW_LOADING, True);
        self.setVisible(EPISODE_LOADING, True);

        self.starRatingPath = None;
        self.starRatingParams = None;
        self.starRating = None;
        self.starKey = None;
        self.showCaseQueue = None;
        self.userRating = 0;
        
        self.languages = dict();

        self.clearCurrentLists([EPISODE_LIST, RELATED_SHOWS_LIST]);

        cIndex = (len(self.depth) - 1);
        cDepth = self.depth[cIndex];

        self.initPath = cDepth['path'];
        self.initParams = cDepth['params'];

        showset = funimationnow.getSeries(self.initPath, self.initParams);

        if showset:

            try:

                self.setShowCaseInfo(showset);
                self.setEpisodesPointer(showset);
                self.setSeasonInfoFilter(showset);
                self.setSimilarShowsPointer(showset);

                self.setVisible(WINDOW_LOADING, False);
                self.setVisible(EPISODE_LOADING, False);

                #self.logger.debug(showset);

            except Exception as inst:
                self.logger.error(inst);
                #some kind of failure message is needed

                pass;

        else:
            #we need a notification of failure
            pass;


    def setShowCaseInfo(self, showset):

        try:

            self.logger.debug(json.dumps(showset));


            list2d = utils.parseValue(showset, ['list2d'], False);
            item = utils.parseValue(list2d, ['hero', 'item'], False);
            pointers = utils.parseValue(list2d, ['pointer'], False);
            thumbs = utils.parseValue(item, ['thumbnail', 'alternate'], False);
            buttons = utils.parseValue(item, ['legend', 'button'], False);

            self.title = utils.parseValue(item, ['title']);
            #self.thumbnail = utils.parseValue(item, ['thumbnail', '#text']);
            self.ratings = utils.parseValue(item, ['ratings', 'tv'], True, ['parseRegion', '@region', funimationnow.getTerritory()]);
            self.description = utils.parseValue(item, ['content', 'description']);
            self.quality = utils.parseValue(item, ['content', 'metadata', 'format']);

            self.starRatingPath = utils.parseValue(item, ['starRating', 'data', 'path']);
            self.starRatingParams = utils.parseValue(item, ['starRating', 'data', 'params']);
            self.starRating = utils.parseValue(item, ['starRating', 'rating']);


            if self.starRatingParams:

                try:
                    self.starKey = self.starRatingParams[0:12];
                    self.userRating = self.myRatings.get(self.starKey).get('myStarRating', 0);

                except:

                    self.starKey = None;
                    self.userRating = 0;

                    pass;

            else:
                self.starKey = None;
                self.userRating = 0;


            if thumbs:
                if not isinstance(thumbs, list):
                    thumbs = list([thumbs]);

                for thumb in thumbs:

                    thumbx = utils.parseValue(thumb, ['@platforms']);

                    if thumbx:
                        if 'windows' in thumbx.split(','):

                            self.thumbnail = utils.parseValue(thumb, ['#text']);

                        break;


            if self.thumbnail:
                #self.thumbnail = funimationnow.formatShowImgUrl(self.thumbnail);
                self.thumbnail = funimationnow.formatImgUrl(self.thumbnail);


            if pointers:
                if not isinstance(pointers, list):
                    pointers = list([pointers]);

            for pointer in pointers:
                if 'path' in pointer:

                    items = utils.parseValue(pointer, ['longList', 'items'], False);

                    if items:
                        if not isinstance(items, list):
                            items = list([items]);

                        for itm in items:
                            

                            if 'pointer' in itm:

                                sdPath = utils.parseValue(itm, ['pointer', 'path']);
                                sdParams = utils.parseValue(itm, ['pointer', 'params']);

                                sdDetails = funimationnow.getSeriesDetails(sdPath, sdParams);

                                if sdDetails:
                                    self.processSpotliteData(sdDetails);

                                break;

                    break;


            if buttons:

                if not isinstance(buttons, list):
                    buttons = list([buttons]);

                for button in buttons:

                    if 'pointer' in button:
                        bpointer = utils.parseValue(button, ['pointer'], False);

                        if 'target' in bpointer and utils.parseValue(bpointer, ['target']) == 'togglewatchlist':

                            qToggle = utils.parseValue(bpointer, ['toggle'], False);
                            qName = utils.parseValue(qToggle, ['name']);
                            qAdd = utils.parseValue(qToggle, ['add', 'analytics', 'click', 'action']);
                            qRemove = utils.parseValue(qToggle, ['remove', 'analytics', 'click', 'action']);
                            qPath = utils.parseValue(qToggle, ['data', 'path']);
                            qParams = utils.parseValue(qToggle, ['data', 'params']);

                            self.showCaseQueue = dict({
                                'qToggle': qToggle,
                                'qName': qName,
                                'qAdd': qAdd,
                                'qRemove': qRemove,
                                'qPath': qPath,
                                'qParams': qParams
                            });

                            sQC = self.getControl(SHOW_QUEUE_BTN);

                            if self.myQueue:

                                if qParams in self.myQueue:
                                    sQC.setSelected(False);

                                else:
                                    sQC.setSelected(True);


                            break;


            self.setShowCaseDisplay();


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def processSpotliteData(self, sdDetails):

        self.logger.debug(json.dumps(sdDetails));


        self.spotlight = None;

        items = utils.parseValue(sdDetails, ['items', 'item'], False);

        if items:
            if not isinstance(items, list):
                items = list([items]);

            for item in items:

                self.logger.debug(json.dumps(item))

                try:

                    if 'subtitle' in item:

                        spotTitle = utils.parseValue(item, ['title']);
                        spotSubTitle = utils.parseValue(item, ['subtitle']);
                        spotThumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                        spotThumbnail = spotThumbnail if spotThumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                        spotId = utils.parseValue(item, ['id']);
                        pointers = utils.parseValue(item, ['pointer'], False);
                        spotDuration = utils.parseValue(item, ['content', 'metadata', 'duration']);
                        duration = utils.parseValue(item, ['content', 'metadata', 'duration']);
                        historyPath = utils.parseValue(item, ['history', 'data', 'path']);
                        historyParams = utils.parseValue(item, ['history', 'data', 'params']);
                        startPosition = utils.parseValue(self.myHistory, [historyParams, 'startPosition']);
                        historyDuration = utils.parseValue(self.myHistory, [historyParams, 'historyDuration']);
                        starRatingPath = utils.parseValue(item, ['starRating', 'data', 'path']);
                        starRatingParams = utils.parseValue(item, ['starRating', 'data', 'params']);
                        starRating = utils.parseValue(item, ['starRating', 'rating']);

                        self.logger.error(spotThumbnail)

                        if pointers:
                            if not isinstance(pointers, list):
                                pointers = list([pointers]);

                            for pointer in pointers:
                                if 'target' in pointer and utils.parseValue(pointer, ['target']) == 'player':

                                    spotPath = utils.parseValue(pointer, ['path']);
                                    spotParams = utils.parseValue(pointer, ['params']);

                                    break;

                            if spotThumbnail:
                                spotThumbnail = funimationnow.formatImgUrl(spotThumbnail, theme='preview');

                            if spotDuration:

                                spotDuration = int((0 if (spotDuration is None or len(spotDuration) < 1) else int(spotDuration)) * self.formatDuration(spotDuration));
                                spotDuration = str(datetime.timedelta(seconds=int(spotDuration)));
                                spotDuration = re.sub(r'(^0:|[^1-9]0:)', '', spotDuration);

                            if duration:
                                duration = int((0 if (duration is None or len(duration) < 1) else int(duration)) * self.formatDuration(duration));


                            self.spotlight = dict({
                                'spotTitle': spotTitle,
                                'spotSubTitle': spotSubTitle,
                                'spotThumbnail': spotThumbnail,
                                'spotId': spotId,
                                'spotDuration': spotDuration,
                                'spotPath': spotPath,
                                'spotParams': spotParams,
                                'duration': duration,
                                'progress': utils.parseProgress(startPosition, historyDuration),
                                'historyPath': historyPath,
                                'historyParams': historyParams,
                                'startPosition': startPosition,
                                'historyDuration': historyDuration,
                                'starRatingPath': starRatingPath,
                                'starRatingParams': starRatingParams,
                                'starRating': starRating,
                            });

                            break;


                except Exception as inst:
                    self.logger.error(inst);

                    pass;


    def setShowCaseDisplay(self):

        if self.thumbnail:

            self.getControl(DISPLAY_BACKDROP_IMG).setImage(self.thumbnail, False);

        if self.title:

            titleImg = os.path.join(self.shows_title, ('%s.png' % self.initParams));

            utils.text2Display(self.title, 'RGBA', (255, 0, 0, 0), (255, 255, 255), 56, 'ExtraBold', titleImg, multiplier=1, sharpen=False, bgimage=None);
            self.getControl(DISPLAY_TITLE_IMG).setImage(titleImg, False);


        if self.starRating:

            self.starRating = utils.roundQuarter(str(self.starRating));
            self.getControl(3003).setImage('flagging/rating/r%s.png' % self.starRating, False);

        if self.userRating:
            self.getControl(DISPLAY_RATING_IMG).setImage('flagging/rating/%s_overlay.png' % self.userRating);

        else:
            self.getControl(DISPLAY_RATING_IMG).setImage('flagging/rating/0_overlay.png');


        self.quality = self.quality if self.quality is not None else '';
        self.ratings = self.ratings if self.ratings is not None else '';
        

        statdesc = '%s  |  %s' % (self.quality, self.ratings);
        statImg = os.path.join(self.shows_stats, ('%s.png' % self.initParams));

        try:

            utils.text2Display(statdesc, 'RGBA', (255, 0, 0, 0), (255, 255, 255), 56, 'Regular', statImg, multiplier=1, sharpen=False, bgimage=None);
            self.getControl(DISPLAY_QUALITY_IMG).setImage(statImg, False);

        except Exception as inst:
            self.logger.error(inst);

            pass;


        if self.description:

            descImg = os.path.join(self.shows_desc, ('%s.png' % self.initParams));

            utils.text2DisplayWrap(self.description, 'RGBA', (255, 0, 0, 0), (255, 255, 255), 36, (1500, 310), 80, 'SemiBold', descImg, multiplier=1, sharpen=False, bgimage=None);
            self.getControl(DISPLAY_DESCRIPTION_IMG).setImage(descImg, False);


        if self.spotlight:

            spotTitle = self.spotlight.get('spotTitle', None);
            spotSubTitle = self.spotlight.get('spotSubTitle', None);
            spotThumbnail = self.spotlight.get('spotThumbnail', None);
            spotId = self.spotlight.get('spotId', None);
            spotDuration = self.spotlight.get('spotDuration', None);
            progress = self.spotlight.get('progress', 0);


            if spotThumbnail:

                self.getControl(SPOTLIGHT_PREVIEW).setImage(spotThumbnail, False);

            if spotTitle:

                spotTitleImg = os.path.join(self.spotlight_title, ('sl_%s.png' % spotId));

                utils.text2Display(spotTitle, 'RGB', (255, 255, 255), (0, 0, 0), 36, 'ExtraBold', spotTitleImg, multiplier=1, sharpen=False, bgimage=None);
                self.getControl(SPOTLIGHT_NAME).setImage(spotTitleImg, False);

            if spotSubTitle:

                spotSubTitleImg = os.path.join(self.spotlight_subtitle, ('sl_%s.png' % spotId));

                utils.text2Display(spotSubTitle, 'RGB', (255, 255, 255), (0, 0, 0), 22, 'Regular', spotSubTitleImg, multiplier=1, sharpen=False, bgimage=None);
                self.getControl(SPOTLIGHT_TITLE).setImage(spotSubTitleImg, False);

            if spotDuration:

                spotDurationImg = os.path.join(self.spotlight_duration, ('sl_%s.png' % spotId));

                utils.text2Display(spotDuration, 'RGB', (255, 255, 255), (0, 0, 0), 22, 'Regular', spotDurationImg, multiplier=1, sharpen=False, bgimage=None);
                self.getControl(SPOTLIGHT_DURATION).setImage(spotDurationImg, False);

            if progress is not None:
                self.logger.error('flagging/progress/%s.png' % progress)
                self.getControl(SPOTLIGHT_PROGRESS).setImage('flagging/progress/%s.png' % progress, False);

        pass;


    def setSeasonInfoFilter(self, showset):

        try:

            pointers = utils.parseValue(showset, ['list2d', 'pointer'], False);

            if pointers:
                if not isinstance(pointers, list):
                    pointers = list([pointers]);

                for pointer in pointers:

                    if 'themes' in pointer and utils.parseValue(pointer, ['themes']) == 'vertical':

                        filters = utils.parseValue(pointer, ['longList', 'palette', 'filter'], False);
                        showid = utils.parseValue(pointer, ['params']);

                        cIndex = (len(self.depth) - 1);
                        cDepth = self.depth[cIndex];

                        cDepth.update({
                            'showid': showid
                        });

                        if filters:
                            self.setSeasonInfo(filters);

                        break;

        except Exception as inst:
            self.logger.error(inst);

            pass;


        if self.navmenu and len(self.navmenu) >= 2:
            self.setNavigationIndex();


        else:
            #throw an error
            pass;


        pass;


    def setSeasonInfo(self, filters):

        try:

            self.navmenu = dict();

            seasons = dict();
            versions = dict();

            if not isinstance(filters, list):
                filters = list([filters]);

            for ftlr in filters:

                fname = utils.parseValue(ftlr, ['name']);
                fpath = utils.parseValue(ftlr, ['path']);
                fparam = utils.parseValue(ftlr, ['param']);
                fvalue = utils.parseValue(ftlr, ['currentValue']);
                fidx = 0;
                fchoices = dict();

                if fname == 'VERSIONS':
                    
                    self.navmenu.update({
                        'VERSIONS': versions
                    });

                elif fname == 'SEASONS':
                    
                    self.navmenu.update({
                        'SEASONS': seasons
                    });

                buttons = utils.parseValue(ftlr, ['choices', 'button'], False);

                if not isinstance(buttons, list):
                    buttons = list([buttons]);

                for idx, button in enumerate(buttons, 0):

                    btitle = utils.parseValue(button, ['title']);
                    bvalue = utils.parseValue(button, ['value']);

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
                    'fpath': fpath,
                    'fparam': fparam,
                    'fvalue': fvalue,
                    'fidx': fidx,
                    'fchoices': fchoices
                });


        except Exception as inst:
            self.logger.error(inst);

            pass;


        if self.navmenu and len(self.navmenu) >= 2:
            self.setNavigationIndex();


        else:
            #throw an error
            pass;


        pass;


    def setEpisodesPointer(self, showset):

        try:

            list2d = utils.parseValue(showset, ['list2d'], False);
            pointers = utils.parseValue(list2d, ['pointer'], False);

            if pointers:
                if not isinstance(pointers, list):
                    pointers = list([pointers]);

            for pointer in pointers:
                if 'themes' in pointer and utils.parseValue(pointer, ['themes']) == 'vertical':

                    longList = utils.parseValue(pointer, ['longList'], False);

                    self.setSeasonEpisodes(longList);

                    break;


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;


    def setSeasonEpisodes(self, longList):

        try:

            self.episodes = None;

            items = utils.parseValue(longList, ['items'], False);

            if items:
                if not isinstance(items, list):
                    items = list([items]);

                for item in items:

                    if 'item' in item:

                        itm = utils.parseValue(item, ['item'], False);

                        if not isinstance(itm, list):
                            itm = list([itm]);

                        if len(itm) > 0:
                            self.episodes = dict();

                        for idx, episode in enumerate(itm, 0):

                            #self.logger.error(json.dumps(episode))

                            try:

                                languages = utils.parseValue(episode, ['content', 'metadata', 'languages']);
                                languages = languages if languages is not None else 'Japanese, English';
                                languages = eplanguage.split(', ');
                                languages.sort(reverse=True);
                                languages = ', '.join(eplanguage);

                            except:
                                languages = 'Japanese, English';

                                pass;

                            historyParams = utils.parseValue(episode, ['history', 'data', 'params']);
                            startPosition = utils.parseValue(self.myHistory, [historyParams, 'startPosition']);
                            historyDuration = utils.parseValue(self.myHistory, [historyParams, 'historyDuration']);
                            starParams = utils.parseValue(episode, ['starRating', 'data', 'params']);
                            epThumbnail = utils.parseValue(episode, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                            epThumbnail = epThumbnail if epThumbnail is not None else utils.parseValue(episode, ['thumbnail', '#text']);

                            if epThumbnail:
                                epThumbnail = funimationnow.formatImgUrl(epThumbnail, theme='preview');

                            try:
                                starKey = starParams[:12] + starParams[15:];

                            except:
                                starKey = None;

                            self.episodes.update({
                                idx: dict({
                                    'title': utils.parseValue(episode, ['title']),
                                    'subtitle': utils.parseValue(episode, ['subtitle']),
                                    'thumbnail': epThumbnail,
                                    'id': utils.parseValue(episode, ['id']),
                                    'langs': self.getLanguages(episode),
                                    'path': utils.parseValue(episode, ['pointer', 'path']),
                                    'params': utils.parseValue(episode, ['pointer', 'params']),
                                    'starPath': utils.parseValue(episode, ['starRating', 'data', 'path']),
                                    'starParams': starParams,
                                    'starKey': starKey,
                                    'starRating': utils.parseValue(episode, ['starRating', 'rating']),
                                    'ratings': utils.parseValue(episode, ['ratings', 'tv'], True, ['parseRegion', '@region', funimationnow.getTerritory()]),
                                    'description': utils.parseValue(episode, ['content', 'description']),
                                    'quality': utils.parseValue(episode, ['content', 'metadata', 'format']),
                                    'languages': languages,
                                    'duration': utils.parseValue(episode, ['content', 'metadata', 'duration']),
                                    'episodeNumber': utils.parseValue(episode, ['content', 'metadata', 'episodeNumber']),
                                    'contentType': utils.parseValue(episode, ['content', 'metadata', 'contentType']),
                                    'progress': utils.parseProgress(startPosition, historyDuration),
                                    'historyPath': utils.parseValue(episode, ['history', 'data', 'path']),
                                    'historyParams': historyParams,
                                    'startPosition': startPosition,
                                    'historyDuration': historyDuration
                                })
                            });


                        break;


            if self.episodes:
                self.populateEpisodeList();


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;


    def populateEpisodeList(self):

        epControl = self.getControl(EPISODE_LIST);
        epControl.reset();

        for idx, episode in self.episodes.iteritems():

            listitem = xbmcgui.ListItem(episode.get('title', ''), episode.get('subtitle', ''), episode.get('thumbnail', ''), episode.get('thumbnail', ''));

            for k in episode:

                if k != 'langs':

                    try:
                        
                        if k == 'progress':
                            listitem.setProperty(str(k), str(episode.get(k, 0)));

                        else:
                            listitem.setProperty(str(k), str(episode.get(k, '')));


                        if k == 'title':

                            tempImg = os.path.join(self.episodes_title, ('evl_%s.png' % episode.get('id', '')));
                            eptitle = str(episode.get(k, ''));

                            if len(eptitle) >= 70:
                                eptitle = '%s...' % eptitle[0:70]

                            if not os.path.isfile(tempImg):
                                utils.text2Display(eptitle, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);
                            #utils.text2DisplayWrap(str(episode.get(k, '')).encode('utf-8'), 'RGB', (255, 255, 255), (0, 0, 0), 36, (600, 120), 32, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);
                            listitem.setProperty('eptitle', tempImg);

                        elif k == 'subtitle':

                            tempImg = os.path.join(self.episodes_subtitle, ('evl_%s.png' % episode.get('id', '')));
                            epsubtitle = str(episode.get(k, ''));

                            if len(epsubtitle) >= 70:
                                epsubtitle = '%s...' % epsubtitle[0:70]

                            if not os.path.isfile(tempImg):
                                utils.text2Display(epsubtitle, 'RGB', (255, 255, 255), (178, 178, 178), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                            listitem.setProperty('epsubtitle', tempImg);

                        elif k == 'episodeNumber':

                            epnumber = episode.get(k, '0');
                            epnumber = str(epnumber) if epnumber is not None and epnumber.isdigit() else '0';

                            tempImg = os.path.join(self.episodes_number, ('%s.png' % epnumber));

                            if not os.path.isfile(tempImg):
                                utils.text2Display(epnumber, 'RGB', (255, 255, 255), (0, 0, 0), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                            listitem.setProperty('epnumber', tempImg);

                        elif k == 'languages':

                            eplanguage = str(episode.get(k, 'Japanese, English'));

                            tempImg = os.path.join(self.episodes_languages, ('%s.png' % eplanguage));

                            if not os.path.isfile(tempImg):
                                utils.text2Display(eplanguage, 'RGB', (255, 255, 255), (178, 178, 178), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                            listitem.setProperty('eplanguage', tempImg);

                        elif k == 'duration':

                            epduration = str(episode.get(k, '1'));
                            epduration = int((1 if (epduration is None or len(epduration) < 1) else int(epduration)) * self.formatDuration(epduration));

                            if(epduration / 60) <= 99:

                                epduration = '%s min' % (epduration / 60);

                            else:

                                epduration = '%s hour' % int(round((float(epduration) / 60) / 60));

                            tempImg = os.path.join(self.episodes_durations, ('%s.png' % epduration));

                            if not os.path.isfile(tempImg):
                                utils.text2Display(epduration, 'RGB', (255, 255, 255), (178, 178, 178), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                            listitem.setProperty('epduration', tempImg);


                    except Exception as inst:
                        self.logger.error(inst);

                        pass;

            epControl.addItem(listitem); 


        #epControl.selectItem(self.currentIndex);
        #Added so if a user plays a video the list will return to the last location the user was at instead of resetting.
        xbmc.executebuiltin('Control.SetFocus(%d, %d)' % (EPISODE_LIST, self.currentIndex));


    def setSimilarShowsPointer(self, showset):

        try:

            list2d = utils.parseValue(showset, ['list2d'], False);
            pointers = utils.parseValue(list2d, ['pointer'], False);

            if pointers:
                if not isinstance(pointers, list):
                    pointers = list([pointers]);

            for pointer in pointers:
                if 'title' in pointer and 'themes' in pointer and utils.parseValue(pointer, ['themes']) == 'detail':

                    longList = utils.parseValue(pointer, ['longList'], False);
                    rTitle = utils.parseValue(pointer, ['title']);

                    self.setRelatedTitle(rTitle);
                    self.setSimilarShows(longList);

                    break;


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;


    def setRelatedTitle(self, rTitle):

        try:

            if rTitle is not None:
                
                tControl = self.getControl(RELATED_SHOWS_TITLE);

                tempImg = os.path.join(self.shows_similar, ('evl_%s.png' % rTitle));

                if not os.path.isfile(tempImg):

                    utils.text2Display(rTitle, 'RGB', (255, 255, 255), (0, 0, 0), 36, 'Bold', tempImg, multiplier=1, sharpen=False, bgimage=None);
                
                tControl.setImage(tempImg, False);


        except Exception as inst:
            self.logger.error(inst);

            pass;


        pass;


    def setSimilarShows(self, longList):

        try:

            shControl = self.getControl(RELATED_SHOWS_LIST);
            items = utils.parseValue(longList, ['items', 'item'], False);

            if items:

                if not isinstance(items, list):
                    items = list([items]);

                for item in items:

                    self.logger.debug(json.dumps(item))

                    try:

                        shParams = utils.parseValue(item, ['pointer', 'params']);
                        shToggleParams = utils.parseValue(item, ['legend', 'button', 'pointer', 'toggle', 'data', 'params']);
                        shMyQueuePath = utils.parseValue(self.myQueue, [shToggleParams, 'myQueuePath']);
                        shThumbnail = utils.parseValue(item, ['thumbnail', 'alternate'], True, ['parseAlternateImg', '@platforms', 'firetv']);
                        shThumbnail = shThumbnail if shThumbnail is not None else utils.parseValue(item, ['thumbnail', '#text']);
                        shThumbnail = funimationnow.formatImgUrl(shThumbnail, theme='show');
                        shTitle = utils.parseValue(item, ['title']);
                        shPath = utils.parseValue(item, ['pointer', 'path']);
                        #shTitleimg = os.path.join(self.shows_list_title, ('s_%s.png' % shParams));
                        shTitleimg = ('s_%s.png' % shParams);
                        shTogglePath = utils.parseValue(item, ['legend', 'button', 'pointer', 'toggle', 'data', 'path']);
                        shToggleParams = shToggleParams;
                        shMyQueuePath = shMyQueuePath;
                        shMyQueueParams = utils.parseValue(self.myQueue, [shToggleParams, 'myQueueParams']);
                        shInQueue = str((0 if shMyQueuePath is not None else 1));

                        shListitem = xbmcgui.ListItem(shTitle, '', shThumbnail, shThumbnail);

                        titles = [shTitle];

                        shTitleimg = utils.text2Title(list(titles), self.shows_list_title, shTitleimg);

                        if shTitleimg:
                            shListitem.setProperty('ctitle', shTitleimg);

                        if shInQueue is not None:
                            shListitem.setProperty('qtexture', str(shInQueue));

                        shListitem.setProperty('title', shTitle);
                        shListitem.setProperty('thumbnail', shThumbnail);
                        shListitem.setProperty('path', shPath);
                        shListitem.setProperty('params', shParams);
                        shListitem.setProperty('titleimg', shTitleimg);
                        shListitem.setProperty('togglePath', shTogglePath);
                        shListitem.setProperty('toggleParams', shToggleParams);
                        shListitem.setProperty('myQueuePath', shMyQueuePath);
                        shListitem.setProperty('myQueueParams', shMyQueueParams);
                        shListitem.setProperty('inQueue', shInQueue);

                        shControl.addItem(shListitem);                      


                    except Exception as inst:
                        self.logger.error(inst);


        except Exception as inst:
            self.logger.error(inst);

            pass;

        pass;


    def getLanguages(self, episode):

        langs = None;
        filters = utils.parseValue(episode, ['legend', 'filter'], False);

        if filters:
            if not isinstance(filters, list):
                filters = list([filters]);

            for ftr in filters:

                if 'name' in ftr and utils.parseValue(ftr, ['name']) == 'AUDIO':

                    choices = utils.parseValue(ftr, ['choices', 'button'], False);

                    if choices:
                        if not isinstance(choices, list):
                            choices = list([choices]);

                        langs = dict();

                        for choice in choices:

                            langs.update({
                                utils.parseValue(choice, ['title']): utils.parseValue(choice, ['value'])
                            });

                    break;


        return langs;


    def setNavigationIndex(self):

        try:

            sControl = self.getControl(VERSIONS_SELECT_IMG);
            sItem = self.navmenu['VERSIONS'];
            sIdx = sItem.get('fidx', 0);
            sTitle = sItem['fchoices'][sIdx].get('title', '');
            sImg = os.path.join(self.select_main, ('%s.png' % sTitle));

            if not os.path.isfile(sImg):
                utils.text2Select(sTitle, 'RGB', None, (225, 225, 225), 30, 'Bold', sImg, multiplier=1, sharpen=True, bgimage='select_control_bg.png');

            sControl.setImage(sImg, False);

            sControl = self.getControl(SEASONS_SELECT_IMG);
            sItem = self.navmenu['SEASONS'];
            sIdx = sItem.get('fidx', 0);
            sTitle = sItem['fchoices'][sIdx].get('title', '');
            sImg = os.path.join(self.select_main, ('%s.png' % sTitle));

            if not os.path.isfile(sImg):
                utils.text2Select(sTitle, 'RGB', None, (225, 225, 225), 30, 'Bold', sImg, multiplier=1, sharpen=True, bgimage='select_control_bg.png');
            
            sControl.setImage(sImg, False);


        except Exception as inst:
            self.logger.error(inst);

            pass;


        pass;


    def getSelectList(self, controlID):

        from resources.lib.gui.navlistgui import select;

        try:

            cSelection = None;
            cMenu = None;

            pControl = self.getControl(SPOTLIGHT_GROUP);
            sControl = self.getControl(controlID);

            pX = pControl.getPosition()[0];
            sX = (sControl.getPosition()[0] + pX);
            sY = sControl.getPosition()[1];

            if controlID == VERSIONS_SELECT_LIST:

                cSelection = select(self.navmenu['VERSIONS'], sX, sY);

                if cSelection is not None:
                    self.navmenu['VERSIONS']['fidx'] = cSelection;

            elif controlID == SEASONS_SELECT_LIST:

                cSelection = select(self.navmenu['SEASONS'], sX, sY);
                
                if cSelection is not None:
                    self.navmenu['SEASONS']['fidx'] = cSelection;

                pass;

            if cSelection is not None:

                self.setVisible(EPISODE_LOADING, True);

                cIndex = (len(self.depth) - 1);
                cDepth = self.depth[cIndex];

                sDict = self.navmenu['SEASONS'];
                vDict = self.navmenu['VERSIONS'];

                showId = cDepth['showid'];
                sParam = '%s=%s' % (sDict['fparam'], sDict['fchoices'][sDict['fidx']].get('value', 'Season 1'));
                vParam = '%s=%s' % (vDict['fparam'], vDict['fchoices'][vDict['fidx']].get('value', 'Uncut'));

                sPath = self.navmenu['VERSIONS']['fpath'];
                sParams = '%s&%s&%s' % (showId, sParam, vParam);

                dSize = (len(self.depth) - 1);
                
                if sDict['fidx'] > 0 or vDict['fidx'] > 0:

                    self.depth.get(dSize).update({
                        'sPath': sPath,
                        'sParams': sParams,
                     });

                else:

                    if 'sPath' in self.depth.get(dSize):
                        self.depth.get(dSize).pop('sPath');

                    if 'sParams' in self.depth.get(dSize):
                        self.depth.get(dSize).pop('sParams');


                episodeset = funimationnow.getLongList(sPath, sParams);

                if episodeset:
                    self.setSeasonEpisodes(episodeset);

                    filters = utils.parseValue(episodeset, ['palette', 'filter'], False);

                    if filters:
                        self.setSeasonInfo(filters);


        except Exception as inst:
            self.logger.error(inst);

            pass;


        self.setVisible(EPISODE_LOADING, False);


    def formatDuration(self, duration):

        try:
            multiplier = 0.001 if len(str(duration)) == 7 else 0.01;

        except:
            multiplier = 0.001;


        return multiplier;


    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);

        pass;


    def getConrolID(self, action):

        if xbmc.getCondVisibility("Control.HasFocus(4010)"):
            return EPISODE_LIST;

        else:
            return None;


    def setListDisplay(self):

        try:

            lItem = self.getControl(EPISODE_LIST).getSelectedItem();
            dNumber = self.getControl(EPISODE_PREVIEW_EP_NUMBER);
            dTitle = self.getControl(EPISODE_PREVIEW_TITLE);
            dSubTitle = self.getControl(EPISODE_PREVIEW_SUBTITLE);
            dLanguage = self.getControl(EPISODE_PREVIEW_LANGUAGE);
            dDuration = self.getControl(EPISODE_PREVIEW_DURATION);
            dQuality = self.getControl(EPISODE_PREVIEW_QUALITY);
            dDescription = self.getControl(EPISODE_PREVIEW_DESCRIPTION);
            dImage = self.getControl(EPISODE_PREVIEW_THUMBNAIL);
            dProgess = self.getControl(EPISODE_PREVIEW_PROGRESS);
            dStarUserRating = self.getControl(EPISODE_PREVIEW_USER_RATING);
            dStarRating = self.getControl(EPISODE_PREVIEW_STAR_RATING);

            lId = lItem.getProperty('id');
            lQuality = lItem.getProperty('quality');
            lRating = lItem.getProperty('ratings');
            lDescription = lItem.getProperty('description');
            lLang = str(lItem.getProperty('languages'));
            lStarRating = lItem.getProperty('starRating');
            lDuration = str(lItem.getProperty('duration'));
            lProgress = str(lItem.getProperty('progress'));
            lImage = lItem.getProperty('thumbnail');

            try:

                tmpstarKey = lItem.getProperty('starKey');
                uRating = self.myRatings.get(tmpstarKey).get('myStarRating', 0);

            except:
                uRating = 0;

            lDuration = int((1 if (lDuration is None or len(lDuration) < 1) else int(lDuration)) * self.formatDuration(lDuration));

            if(lDuration / 60) <= 99:
                lDuration = '%s min' % (lDuration / 60);

            else:
                lDuration = '%s hour' % int(round((float(lDuration) / 60) / 60));

            if uRating is not None:
                dStarUserRating.setImage('flagging/rating/%s_overlay.png' % uRating);

            else:
                dStarUserRating.setImage('flagging/rating/0_overlay.png');

            if lStarRating is not None:

                lStarRating = utils.roundQuarter(str(lStarRating));
                dStarRating.setImage('flagging/rating/r%s.png' % lStarRating, False);


            if lQuality is not None or lRating is not None:

                cq = [];
                epquality = None;

                if lQuality is not None:
                    cq.append(lQuality);

                if lRating is not None:
                    cq.append(lRating);
               
                epquality = '  |  '.join(cq);

                if epquality:

                    tempImg = os.path.join(self.episodes_quality, ('evl_%s.png' % re.sub('[^\w\d]+', '_', epquality)));

                    if not os.path.isfile(tempImg):
                        utils.text2Display(epquality, 'RGB', (255, 255, 255), (128, 128, 128), 26, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                    dQuality.setImage(tempImg, False);


            if lDescription is not None:

                tempImg = os.path.join(self.episodes_desc, ('evl_%s.png' % lId));

                if not os.path.isfile(tempImg):
                    utils.text2DisplayWrap(lDescription, 'RGB', (255, 255, 255), (0, 0, 0), 26, (825, 135), 64, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                dDescription.setImage(tempImg, False);


            dTitle.setImage(os.path.join(self.episodes_title, ('evl_%s.png' % lId)));
            dSubTitle.setImage(os.path.join(self.episodes_subtitle, ('evl_%s.png' % lId)));
            dLanguage.setImage(os.path.join(self.episodes_languages, ('%s.png' % lLang)));
            dDuration.setImage(os.path.join(self.episodes_durations, ('%s.png' % lDuration)));
            dImage.setImage(lImage);

            dProgess.setImage('flagging/progress/%s.png' % lProgress, False);

            if lLang is not None:

                langs = lLang.split(', ');

                if lId not in self.languages:

                    fchoices = dict();

                    for idx, lang in enumerate(langs, 0):

                        fchoices.update({
                            idx: dict({
                                'title': lang,
                                'value': str(lang[0:2]).lower()
                            })
                        });

                    self.languages[lId] = dict({
                        'fidx': 0,
                        'fchoices': fchoices
                    });

                self.setLangNavigationIndex(lId);


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def getLangSelectList(self):

        from resources.lib.gui.navlistgui import select;

        try:

            cSelection = None;

            lItem = self.getControl(EPISODE_LIST).getSelectedItem();
            pControl = self.getControl(EPISODE_PREVIEW_GROUP);
            sControl = self.getControl(LANGUAGE_SELECT_LIST);

            lId = lItem.getProperty('id');

            pX = pControl.getPosition()[0];
            sX = (sControl.getPosition()[0] + pX);
            sY = (sControl.getPosition()[1] + 220);

            cSelection = select(self.languages[lId], sX, sY);
            
            if cSelection is not None:
                self.languages[lId]['fidx'] = cSelection;

            pass;

            if cSelection is not None:
                self.setLangNavigationIndex(lId);


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def setLangNavigationIndex(self, lId):

        sControl = self.getControl(LANGUAGE_SELECT_IMG);
        sItem = self.languages[lId];

        sIdx = sItem.get('fidx', 0);
        sTitle = sItem['fchoices'][sIdx].get('title', '');
        sImg = os.path.join(self.select_main, ('%s.png' % sTitle));

        if not os.path.isfile(sImg):
            utils.text2Select(sTitle, 'RGB', None, (225, 225, 225), 30, 'Bold', sImg, multiplier=1, sharpen=True, bgimage='select_control_bg.png');
        
        sControl.setImage(sImg, False);


    def prepPlayBack(self, controlID):

        from resources.lib.modules.player import player;

        utils.lock();

        try:

            videourl = None;
            pbListItem = None;

            if controlID == SPOTLIGHT_PLAY_BTN:

                epContent = funimationnow.player(
                    self.spotlight.get('spotPath'), 
                    self.spotlight.get('spotParams'), 
                    'episodeDesc', 
                    'episode', 
                    None, 
                    loadDisplay=False
                );

                if epContent:

                    videourl = epContent.get('videourl', None);

                    if videourl:

                        try:

                            contMap = self.histLookup;

                            pbListItem = xbmcgui.ListItem(
                                epContent.get('title', ''), 
                                epContent.get('subtitle', ''), 
                                epContent.get('spotThumbnail', ''), 
                                epContent.get('spotThumbnail', '')
                            );

                            if contMap:

                                pStart = contMap.get('startPosition', None);
                                pDuration = contMap.get('duration', None);
                                pAdd = contMap.get('add', None);
                                pStartPosition = self.spotlight.get('startPosition', 0);
                                pHistoryParams = self.spotlight.get('historyParams', '');


                                if pStart and pDuration and pAdd:
                                    
                                    pbListItem.setProperty('startPosition', str(pStartPosition));
                                    pbListItem.setProperty('pStart', str(pStart));
                                    pbListItem.setProperty('pDuration', str(pDuration));
                                    pbListItem.setProperty('historyParams', pHistoryParams);
                                    pbListItem.setProperty('pAdd', str(pAdd));

                        except:
                            pass;


            elif controlID in LIST_PLAYBACK:

                pbListItem = self.getControl(EPISODE_LIST).getSelectedItem();
                pbidx = self.getControl(EPISODE_LIST).getSelectedPosition();

                self.currentIndex = pbidx

                pbLidx = pbListItem.getProperty('id');
                pbParams = pbListItem.getProperty('params');

                if controlID == LIST_PLAY_BTN:
                    
                    pbLanguages = self.languages.get(pbLidx);
                    pbFidx = pbLanguages.get('fidx', 0);
                    pbLanguage = pbLanguages['fchoices'][pbFidx]['value'];

                    pbParams = re.sub(r'audio=[\w\d]+', ('audio=%s' % pbLanguage), pbParams, re.I);


                epContent = funimationnow.player(
                    pbListItem.getProperty('path'),
                    pbParams,
                    'episodeDesc', 
                    'episode', 
                    None, 
                    loadDisplay=False
                );


                if epContent:

                    videourl = epContent.get('videourl', None);

                    if videourl:

                        try:

                            contMap = self.histLookup;

                            if contMap:

                                pStart = contMap.get('startPosition', None);
                                pDuration = contMap.get('duration', None);
                                pAdd = contMap.get('add', None);

                                if pStart and pDuration and pAdd:

                                    pbListItem.setProperty('pStart', str(pStart));
                                    pbListItem.setProperty('pDuration', str(pDuration));
                                    pbListItem.setProperty('pAdd', str(pAdd));


                        except:
                            pass;


        except Exception as inst:
            self.logger.error(inst);

            pass;


        utils.unlock();

        if videourl is not None and pbListItem is not None:

            player().run(videourl, pbListItem);

            pass;


        pass;


    def clearCurrentLists(self, cLists):

        for cList in cLists:

            try:
                self.getControl(cList).reset();

            except Exception as inst:
                self.logger.error(inst);

                pass;

        pass;


    def getResultCode(self):
        return self.result_code;

        pass;

    
    def runDirectoryChecks(self):

        #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', utils.getAddonInfo('id')));
        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.shows_title = os.path.join(dsPath, 'media/shows/title');
        self.shows_stats = os.path.join(dsPath, 'media/shows/stats');
        self.shows_desc = os.path.join(dsPath, 'media/shows/desc');
        self.shows_similar = os.path.join(dsPath, 'media/shows/similar');
        self.episodes_title = os.path.join(dsPath, 'media/episodes/title');
        self.episodes_subtitle = os.path.join(dsPath, 'media/episodes/subtitle');
        self.episodes_number = os.path.join(dsPath, 'media/episodes/number');
        self.episodes_languages = os.path.join(dsPath, 'media/episodes/language');
        self.episodes_durations = os.path.join(dsPath, 'media/episodes/duration');
        self.episodes_quality = os.path.join(dsPath, 'media/episodes/quality');
        self.episodes_desc = os.path.join(dsPath, 'media/episodes/desc');
        self.spotlight_title = os.path.join(dsPath, 'media/spotlight/title');
        self.spotlight_subtitle = os.path.join(dsPath, 'media/spotlight/subtitle');
        self.spotlight_duration = os.path.join(dsPath, 'media/spotlight/duration');
        self.select_main = os.path.join(dsPath, 'media/select/main');
        self.select_list = os.path.join(dsPath, 'media/select/list');
        self.shows_list_title = os.path.join(dsPath, 'media/shows/list/title');

        utils.checkDirectory(self.shows_title);
        utils.checkDirectory(self.shows_stats);
        utils.checkDirectory(self.shows_desc);
        utils.checkDirectory(self.shows_similar);
        utils.checkDirectory(self.episodes_title);
        utils.checkDirectory(self.episodes_subtitle);
        utils.checkDirectory(self.episodes_number);
        utils.checkDirectory(self.episodes_languages);
        utils.checkDirectory(self.episodes_durations);
        utils.checkDirectory(self.episodes_quality);
        utils.checkDirectory(self.episodes_desc);
        utils.checkDirectory(self.spotlight_title);
        utils.checkDirectory(self.spotlight_subtitle);
        utils.checkDirectory(self.spotlight_duration);
        utils.checkDirectory(self.select_main);
        utils.checkDirectory(self.select_list);
        utils.checkDirectory(self.shows_list_title);


def show(landing_page=None, xrfPath=None, xrfParam=None):

    
    showui = ShowViewUI("funimation-show.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    showui.setInitialItem(landing_page, xrfPath, xrfParam);
    showui.doModal();

    del showui;

    


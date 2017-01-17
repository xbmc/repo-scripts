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
import os;

from resources.lib.modules import utils;
from resources.lib.modules import funimationnow;


EXIT_BTN = 1000;
DESC_TEXT = 1001;
EXP_TEXT = 1002;
EXP2_TEXT = 1003;
TRIAL_BTN = 1004;
LOGIN_TXT = 1005;
LOGIN_BTN = 10000;
LOGOUT_BTN = 10001;

EXIT_CODE = 2;
SUCCESS_CODE = 3;
EXPIRE_CODE = 4;
HOME_SCREEN_CODE = 5;
BACK_CODE = 6;
LOGOUT_CODE = 7;
REST_CODE = 8;

PREVIOUS_WINDOW = (
    xbmcgui.ACTION_PREVIOUS_MENU, 
    xbmcgui.ACTION_NAV_BACK
);

EXIT_CLICK = (
    xbmcgui.ACTION_MOUSE_DOUBLE_CLICK, 
    xbmcgui.ACTION_MOUSE_LONG_CLICK, 
    xbmcgui.ACTION_TOUCH_LONGPRESS
);




class TrialScreenUI(xbmcgui.WindowXML):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();

        self.control30600size = [0, 0];
        self.control30601size = [0, 0];
        self.control30602size = [0, 0];
        self.control30603size = [0, 0];
        self.control30604size = [0, 0];
        self.control30605size = [0, 0];
        self.control30606size = [0, 0];

        self.resultcode = False;
        self.viewState = EXIT_CODE;


    def onInit(self):

        self.validateState();
        self.setTrialObjectSizes();

        utils.unlock();


    def setViewState(self, viewstate):
        self.viewState = viewstate;


    def onAction(self, action):

        actionID = action.getId();

        if actionID in PREVIOUS_WINDOW:
            self.resultcode = EXIT_CODE;
            self.close();



    def onClick(self, controlID):

        if controlID == EXIT_BTN:
            self.resultcode = EXIT_CODE;
            self.close();

        elif controlID == TRIAL_BTN:
            utils.openBrowser('http://www.funimation.com/android-mobile/register?territory=%s' % funimationnow.getTerritory());

        elif controlID == LOGIN_BTN:
            from resources.lib.gui.logingui import loginscreen;

            self.viewState = loginscreen();
            self.validateState();

        elif controlID == LOGOUT_BTN:
            self.logoutProcess();

        else:
            self.resultcode = EXIT_CODE;
            self.close()


    def logoutProcess(self):

        self.resultcode = LOGOUT_CODE;

        from resources.lib.modules import cleardata;

        try:
            cleardata.cleanup();

        except:
            pass;

        self.close();


    def validateState(self):

        if self.viewState == EXIT_CODE:

            self.setVisible(EXP_TEXT, False);
            self.setVisible(EXP2_TEXT, False);
            self.setVisible(LOGOUT_BTN, False);

            self.setVisible(DESC_TEXT, True);
            self.setVisible(LOGIN_TXT, True);
            self.setVisible(LOGIN_BTN, True);

        elif self.viewState == EXPIRE_CODE:

            self.setVisible(EXP_TEXT, True);
            self.setVisible(EXP2_TEXT, True);
            self.setVisible(LOGOUT_BTN, True);

            self.setVisible(DESC_TEXT, False);
            self.setVisible(LOGIN_TXT, False);
            self.setVisible(LOGIN_BTN, False);

        elif self.viewState == SUCCESS_CODE:

            self.resultcode = self.viewState;
            self.close();


    def createTrialSplash(self):

        self.runDirectoryChecks();

        lang = xbmcaddon.Addon().getLocalizedString;

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30600'));
        self.control30600size = utils.text2Image(lang(30600).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (255, 255, 255), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30601a'));
        self.control30601size = utils.text2Image(lang(30601).encode('utf-8'), 'RGB', None, (255, 255, 255), 66, 'Bold', tempImg, 1, True, 'trial-btn-no-focus-bg.png');

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30601b'));
        self.control30601size = utils.text2Image(lang(30601).encode('utf-8'), 'RGB', None, (255, 255, 255), 66, 'Bold', tempImg, 1, True, 'trial-btn-focus-bg.png');

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30602'));
        self.control30602size = utils.text2Image(lang(30602).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (255, 255, 255), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30603a'));
        self.control30603size = utils.text2Image(lang(30603).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (255, 255, 255), 66, 'Bold', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30603b'));
        self.control30603size = utils.text2Image(lang(30603).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (150, 39, 171), 66, 'Bold', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30604'));
        self.control30604size = utils.text2Image(lang(30604).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (255, 255, 255), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30605'));
        self.control30605size = utils.text2Image(lang(30605).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (255, 255, 255), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30606a'));
        self.control30606size = utils.text2Image(lang(30606).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (255, 255, 255), 66, 'Bold', tempImg, 1, True);

        tempImg = os.path.join(self.media_trial, ('%s.png' % '30606b'));
        self.control30606size = utils.text2Image(lang(30606).encode('utf-8'), 'RGBA', (255, 0, 0, 0), (150, 39, 171), 66, 'Bold', tempImg, 1, True);


    def setTrialObjectSizes(self):

        try:


            control30600 = self.getControl(DESC_TEXT);
            control30601 = self.getControl(TRIAL_BTN);
            control30602 = self.getControl(LOGIN_TXT);
            control30603 = self.getControl(LOGIN_BTN);
            control30604 = self.getControl(EXP_TEXT);
            control30605 = self.getControl(EXP2_TEXT);
            control30606 = self.getControl(LOGOUT_BTN);

            control30600size = int(self.control30600size[0] / 4);
            control30601size = int(self.control30601size[0] / 4);
            control30602size = int(self.control30602size[0] / 4);
            control30603size = int(self.control30603size[0] / 4);
            control30604size = int(self.control30604size[0] / 4);
            control30605size = int(self.control30605size[0] / 4);
            control30606size = int(self.control30606size[0] / 4);

            control30600.setWidth(control30600size);
            control30601.setWidth(control30601size);
            control30602.setWidth(control30602size);
            control30603.setWidth(control30603size);
            control30604.setWidth(control30604size);
            control30605.setWidth(control30605size);
            control30606.setWidth(control30606size);

            #self.setFocus(control32131);


        except Exception as inst:
            self.logger.error(inst);


    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);


    def runDirectoryChecks(self):

        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.media_trial = os.path.join(dsPath, 'media/trial');

        utils.checkDirectory(self.media_trial);


    def getResult(self):
        return self.resultcode;


def trialscreen(viewstate=EXIT_CODE):
    
    trialgui = TrialScreenUI("funimation-trial.xml", utils.getAddonInfo('path'), 'default', "720p");

    trialgui.setViewState(viewstate);

    trialgui.createTrialSplash();
    trialgui.doModal();

    result = trialgui.getResult();

    del trialgui;

    return result
    


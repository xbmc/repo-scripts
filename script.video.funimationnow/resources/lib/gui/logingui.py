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
import json;
import re;

from resources.lib.modules import utils;
from resources.lib.modules import funimationnow;


EXIT_BTN = 1000;
DESC_TXT = 1001;
EMAIL_TEXT = 1002;
PASS_TEXT = 1003;
MASK_TEXT = 1004;
LOGIN_BTN = 1005;
LOGIN_MASK_BTN = 10055;
LOGIN_STAT = 1006;
FORGOT_BTN = 1007;


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

        self.control30620size = [0, 0];
        self.control30621size = [0, 0];
        self.control30622size = [0, 0];

        self.resultcode = False;


    def onInit(self):

        self.setLoginObjectSizes();
        self.setVisible(LOGIN_MASK_BTN, True);


        #https://github.com/MediaBrowser/plugin.video.emby/blob/develop/resources/lib/dialogs/loginconnect.py

        utils.unlock();


    def onClick(self, controlID):

        if controlID == EXIT_BTN:

            self.resultcode = EXIT_CODE;
            self.close();

        elif controlID == LOGIN_BTN:
            
            (success, access) = self.login();

            if success and access:
                self.resultcode = SUCCESS_CODE;
                self.close();

            elif success and not access:
                self.resultcode = EXPIRE_CODE;
                self.close();

            else:
                self.setVisible(LOGIN_STAT, True);

        elif controlID == FORGOT_BTN:
            utils.openBrowser('http://www.funimation.com/android-mobile/forgot-password?territory=%s' % funimationnow.getTerritory());


    def onAction(self, action):

        #if xbmc.getCondVisibility("Control.HasFocus(%s)" % MASK_TEXT):
        if self.getFocusId() == MASK_TEXT:
            self.updateMaskedPassword();
            #self.getFocusId()

        uidText = self.getControl(EMAIL_TEXT).getText();
        pwdText = self.getControl(PASS_TEXT).getText();

        if len(uidText) > 0 and len(pwdText) > 0:

            if bool(re.compile(r'.*@.*\..+').match(uidText)):
                self.setVisible(LOGIN_MASK_BTN, False);

            else:
                self.setVisible(LOGIN_MASK_BTN, True);

        else:
            self.setVisible(LOGIN_MASK_BTN, True);


        actionID = action.getId();

        if actionID in PREVIOUS_WINDOW:
            self.resultcode = EXIT_CODE;
            self.close();


    def createLoginSplash(self):

        self.runDirectoryChecks();

        lang = xbmcaddon.Addon().getLocalizedString;

        tempImg = os.path.join(self.media_login, ('%s.png' % '30620'));
        self.control30620size = utils.text2Image(lang(30620).encode('utf-8'), 'RGB', (68, 3, 151), (255, 255, 255), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_login, ('%s.png' % '30621a'));
        self.control30621size = utils.text2Image(lang(30621).encode('utf-8'), 'RGB', None, (255, 255, 255), 66, 'Bold', tempImg, 1, True, 'login-btn-no-focus-bg.png');

        tempImg = os.path.join(self.media_login, ('%s.png' % '30621b'));
        self.control30621size = utils.text2Image(lang(30621).encode('utf-8'), 'RGB', None, (255, 255, 255), 66, 'Bold', tempImg, 1, True, 'login-btn-focus-bg.png');

        tempImg = os.path.join(self.media_login, ('%s.png' % '30621c'));
        self.control30621size = utils.text2Image(lang(30621).encode('utf-8'), 'RGB', None, (255, 255, 255), 66, 'Bold', tempImg, 1, True, 'login-btn-disabled-focus-bg.png');

        tempImg = os.path.join(self.media_login, ('%s.png' % '30622a'));
        self.control30622size = utils.text2Image(lang(30622).encode('utf-8'), 'RGB', (68, 3, 151), (255, 255, 255), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_login, ('%s.png' % '30622b'));
        self.control30622size = utils.text2Image(lang(30622).encode('utf-8'), 'RGB', (68, 3, 151), (150, 39, 171), 66, 'Regular', tempImg, 1, True);

        tempImg = os.path.join(self.media_login, ('%s.png' % '30623'));
        self.control1006size = utils.text2Image(lang(30623).encode('utf-8'), 'RGB', (68, 3, 151), (255, 0, 0), 66, 'Regular', tempImg, 1, True);


    def setLoginObjectSizes(self):

        try:

            self.setVisible(LOGIN_STAT, False);

            control30620 = self.getControl(DESC_TXT);
            control1002 = self.getControl(EMAIL_TEXT);
            control1004 = self.getControl(MASK_TEXT);
            control30621 = self.getControl(LOGIN_BTN);
            control30622 = self.getControl(FORGOT_BTN);
            control1006 = self.getControl(LOGIN_STAT);

            control30620size = int(self.control30620size[0] / 4);
            control1002size = int(control30620size * 0.95);
            control1004size = control1002size;
            control30621size = int(self.control30621size[0] / 4);
            control30622size = int(self.control30622size[0] / 4);
            control1006size = int(self.control1006size[0] / 4);

            control30620.setWidth(control30620size);
            control1002.setWidth(control1002size);
            control1004.setWidth(control1004size);
            control30621.setWidth(control30621size);
            control30622.setWidth(control30622size);
            control1006.setWidth(control1006size);


        except Exception as inst:
            self.logger.error(inst);


    def updateMaskedPassword(self):

        bullet_string = '';

        self.password_field = self.getControl(PASS_TEXT);
        self.hidden_password_field = self.getControl(MASK_TEXT);

        for idx in range(0, len(self.hidden_password_field.getText())):
            bullet_string += '*';

        self.password_field.setText(bullet_string);


    def login(self):

        uid = self.getControl(EMAIL_TEXT).getText();
        pwd = self.getControl(MASK_TEXT).getText();

        return funimationnow.login(uid, pwd);


    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);


    def setEnabled(self, view, state):
        self.getControl(view).setEnabled(state);


    def runDirectoryChecks(self):

        #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', utils.getAddonInfo('id')));
        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.media_login = os.path.join(dsPath, 'media/login');

        utils.checkDirectory(self.media_login);


    def getResult(self):
        return self.resultcode;


def loginscreen():
    
    logingui = TrialScreenUI("funimation-login.xml", utils.getAddonInfo('path'), 'default', "720p");

    logingui.createLoginSplash();
    logingui.doModal();

    result = logingui.getResult();

    del logingui;

    return result
    


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


BACK_BTN = 1101001;

ABOUT_BTN = 110201;
FAQ_BTN = 110202;
CONTACT_BTN = 110203;
POLICY_BTN = 110204;
TERMS_BTN = 110205;

ABOUT_LIST = 1000;
FAQ_LIST = 1001;
CONTACT_LIST = 1002;
POLICY_LIST = 1003;
TERMS_LIST = 1004;

SIDE_MENU = (
    ABOUT_BTN,
    FAQ_BTN,
    CONTACT_BTN,
    POLICY_BTN,
    TERMS_BTN,
);

MENU_LISTS = (
    ABOUT_LIST,
    FAQ_LIST,
    CONTACT_LIST,
    POLICY_LIST,
    TERMS_LIST,
);

LIST_DICT = dict({
    ABOUT_BTN: ABOUT_LIST,
    FAQ_BTN: FAQ_LIST,
    CONTACT_BTN: CONTACT_LIST,
    POLICY_BTN: POLICY_LIST,
    TERMS_BTN: TERMS_LIST,
});

LOADING_SCREEN = 90000;


class HelpMenuUI(xbmcgui.WindowXMLDialog):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();
        self.menu = dict();


    def onInit(self):

        self.runDirectoryChecks();
        self.clearLists(0);

        self.getMenuitem(ABOUT_BTN)

        utils.unlock();

        self.setVisible(LOADING_SCREEN, False);

        pass;


    def createHelpMenuButtons(self):

        try:

            pointers = funimationnow.helpMenu();

            self.logger.debug(json.dumps(pointers));

            if pointers:
                self.createButtons(pointers);

        except Exception as inst:
            self.logger.error(inst);

            pass;


        pass;


    def createButtons(self, pointers):

        if not isinstance(pointers, list):
            pointers = list([pointers]);


        if len(pointers) >= 1:

            for idx, pointer in enumerate(pointers, 1):

                try:

                    tempTitle = utils.parseValue(pointer, ['title']);

                    self.menu.update({int('1102%02d' % idx): pointer});

                    utils.text2Button(tempTitle, 'RGB', [(61, 3, 136), (68, 3, 151)], [(255, 255, 255), (255, 255, 255)], 58, 'ExtraBold', (600, 90), (20, 4), ['menu-focus-button-1102%02d' % idx, 'menu-no-focus-button-1102%02d' % idx], True);

                except Exception as inst:
                    self.logger.error(inst);

                    pass;
                    
                pass;

        else:

            for idx in range(1, 6):

                try:

                    tempTitle = utils.lang(int('3053%d' % idx));

                    utils.text2Button(tempTitle, 'RGB', [(61, 3, 136), (68, 3, 151)], [(255, 255, 255), (255, 255, 255)], 58, 'ExtraBold', (600, 90), (20, 4), ['menu-focus-button-1102%02d' % idx, 'menu-no-focus-button-1102%02d' % idx], True);

                except Exception as inst:
                    self.logger.error(inst);

                    pass;
                    
                pass;


        pass;


    def onClick(self, controlID):

        if controlID in SIDE_MENU:
            self.getMenuitem(controlID);

            pass;

        elif controlID == BACK_BTN:
            self.close();

        pass;


    def getMenuitem(self, controlID):

        self.setVisible(LOADING_SCREEN, True);

        try:

            navSet = self.menu.get(controlID, None);

            if 'path' in navSet:

                results = funimationnow.actionBar(navSet['path'], navSet['params']);

                self.clearLists(controlID);

                getattr(self, re.sub(r'[^A-Za-z]+', '', navSet['title']).lower())(controlID, results);

            else:
                getattr(self, re.sub(r'[^A-Za-z]+', '', navSet['title']).lower())(navSet['webBrowserUrl']);


        except Exception as inst:
            self.logger.error(inst);

            pass;

        self.setVisible(LOADING_SCREEN, False);


    def clearLists(self, controlID):

        for lst in MENU_LISTS:

            try:
                self.getControl(lst).reset();

                try:

                    if LIST_DICT[controlID] == lst:
                        self.setVisible(lst, True);

                    else:
                        self.setVisible(lst, False);

                except:
                    self.setVisible(lst, False);

            except:
                pass;


    def about(self, controlID, results):

        try:

            title = utils.parseValue(results, ['title']);
            subtitle = utils.parseValue(results, ['subtitle']);

            tempImg = os.path.join(self.help_about, ('%s-%s.png' % (controlID, 0)));
            utils.text2Display(subtitle, 'RGB', (255, 255, 255), (0, 0, 0), 46, 'ExtraBold', tempImg, 1, True);

            helpList = self.getControl(LIST_DICT[controlID]);
            listitem = xbmcgui.ListItem(title, subtitle, tempImg, tempImg);

            helpList.addItem(listitem);

        except Exception as inst:
            self.logger.error(inst);

            pass;


    def faq(self, controlID, results):

        try:

            properties = utils.parseValue(results, ['item', 'content', 'properties', 'property'], False);

            if not isinstance(properties, list):
                properties = list([properties]);


            cidx = 0;
            cih = 0;
            
            bContent = list();
            nContent = list();


            for prop in properties:               

                bcontent = list();

                bcontent.append('_+_+_+_');
                bcontent.append(prop.get('name', '_+_+_+_'));
                bcontent.append('_+_+_+_');

                bContent.append(bcontent);

                ncontent = list();

                ncontent.append('_+_+_+_');

                tmbValue = prop.get('value', '_+_+_+_');
                tmbValue = tmbValue.replace(u"\u2022", u"~~~~~~\u2022")
                tmbValues = tmbValue.split('~~~~~~');

                for tvalue in tmbValues:
                    ncontent.append(tvalue);

                ncontent.append('_+_+_+_');
                ncontent.append('_+_+_+_');

                nContent.append(ncontent);

                cih = utils.text2HelpMultiSize(list([bContent, nContent]), 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1200), 140, list(['Bold', 'Regular']), None, multiplier=1, sharpen=False, bgimage='faq_list_border.png');

                if cih >= 975:
                    
                    tempImg = os.path.join(self.help_faq, ('%s-%s.png' % (controlID, cidx)));

                    utils.text2HelpMultiWrap(list([bContent, nContent]), 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1200), 140, list(['Bold', 'Regular']), tempImg, multiplier=1, sharpen=False, bgimage='faq_list_border.png');

                    helpList = self.getControl(LIST_DICT[controlID]);
                    listitem = xbmcgui.ListItem('NA', 'NA', tempImg, tempImg);

                    helpList.addItem(listitem);

                    cidx += 1;
                    cih = 0;

                    bContent = list();
                    nContent = list();


            if cih < 975 and cih > 0:

                tempImg = os.path.join(self.help_faq, ('%s-%s.png' % (controlID, cidx)));

                utils.text2HelpMultiWrap(list([bContent, nContent]), 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1200), 140, list(['Bold', 'Regular']), tempImg, multiplier=1, sharpen=False, bgimage='faq_list_border.png');

                helpList = self.getControl(LIST_DICT[controlID]);
                listitem = xbmcgui.ListItem('NA', 'NA', tempImg, tempImg);

                helpList.addItem(listitem);


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def privacypolicy(self, controlID, results):

        try:

            properties = utils.parseValue(results, ['statictext', 'contents', 'p'], False);

            if not isinstance(properties, list):
                properties = list([properties]);


            cidx = 0;
            cih = 0;
            
            bContent = list();
            nContent = list();

            tList = list();
            tdict = dict();

            for tidx, prop in enumerate(properties, 0):

                try:

                    if isinstance(prop, unicode):

                        if tidx < 1:
                            tdict.update({'name': ''});
                        
                        tdict.update({'value': tdict.get('value', '') + '~~~~~~' + prop});

                    elif prop is None:
                        pass;

                    else:


                        if len(tdict) > 0:
                            tList.append(tdict);
                            tdict = dict();

                        tdict.update({'name': prop.get('strong', '')});

                except Exception as inst:
                    self.logger.error(inst);
                    pass;

            if len(tdict) > 0:
                tList.append(tdict);

            #self.logger.error(tList)

            for prop in tList:

                bcontent = list();

                try:

                    bcontent.append('_+_+_+_');
                    bcontent.append(prop.get('name', '_+_+_+_'));
                    bcontent.append('_+_+_+_');

                    bContent.append(bcontent);

                except:
                    pass;

                try:

                    ncontent = list();

                    ncontent.append('_+_+_+_');

                    tmbValue = prop.get('value', '_+_+_+_');
                    tmbValue = tmbValue.replace(u"\u2022", u"~~~~~~\u2022")
                    tmbValues = tmbValue.split('~~~~~~');

                    for tvalue in tmbValues:
                        ncontent.append(tvalue);
                        ncontent.append('_+_+_+_');

                    ncontent.append('_+_+_+_');
                    ncontent.append('_+_+_+_');

                    nContent.append(ncontent);

                except:
                    pass;

                #self.logger.error(list([bContent, nContent]))

                cih = utils.text2HelpMultiSize(list([bContent, nContent]), 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1200), 140, list(['Bold', 'Regular']), None, multiplier=1, sharpen=False, bgimage='faq_list_border.png');

                if cih >= 975:
                    
                    tempImg = os.path.join(self.help_privacy, ('%s-%s.png' % (controlID, cidx)));

                    utils.text2HelpMultiWrap(list([bContent, nContent]), 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1200), 140, list(['Bold', 'Regular']), tempImg, multiplier=1, sharpen=False, bgimage='faq_list_border.png');

                    helpList = self.getControl(LIST_DICT[controlID]);
                    listitem = xbmcgui.ListItem('NA', 'NA', tempImg, tempImg);

                    helpList.addItem(listitem);

                    cidx += 1;
                    cih = 0;

                    bContent = list();
                    nContent = list();


            if cih < 975 and cih > 0:

                tempImg = os.path.join(self.help_faq, ('%s-%s.png' % (controlID, cidx)));

                utils.text2HelpMultiWrap(list([bContent, nContent]), 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1200), 140, list(['Bold', 'Regular']), tempImg, multiplier=1, sharpen=False, bgimage='faq_list_border.png');

                helpList = self.getControl(LIST_DICT[controlID]);
                listitem = xbmcgui.ListItem('NA', 'NA', tempImg, tempImg);

                helpList.addItem(listitem);


        except Exception as inst:
            self.logger.error(inst);

            pass;


    '''def privacypolicy(self, controlID, results):

        try:

            #contents = utils.parseValue(results, ['statictext', 'contents', 'content'], False);
            contents = utils.parseValue(results, ['statictext', 'contents', 'p'], False);

            if not isinstance(contents, list):
                contents = list([contents]);


            cidx = 0;
            cih = 0;
            ccontent = '';

            self.logger.error(json.dumps(contents))


            for idx, content in enumerate(contents, 0):

                try:

                    if content is None:
                        content = ' ~~~_+_+_+_~~~';

                    try:
                        ccontent += content.replace(u"\u2028", '~~~');
                    except:
                        ccontent += content.get('strong', '').replace(u"\u2028", '~~~');
                        ccontent += ' ~~~_+_+_+_~~~'

                    cih = utils.text2HelpSize(ccontent, 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1340), 140, 'Regular', None, multiplier=1, sharpen=False, bgimage=None);

                    if cih >= 1240:

                        tempImg = os.path.join(self.help_privacy, ('%s-%s.png' % (controlID, cidx)));

                        utils.text2HelpWrap(ccontent, 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1340), 140, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                        content = content.encode('utf-8');

                        helpList = self.getControl(LIST_DICT[controlID]);
                        listitem = xbmcgui.ListItem(content, content, tempImg, tempImg);

                        helpList.addItem(listitem);

                        cidx += 1;
                        cih = 0;
                        ccontent = '';

                except Exception as inst:
                    self.logger.error(inst);

                    pass;


            if cih < 1240 and cih > 0:

                tempImg = os.path.join(self.help_privacy, ('%s-%s.png' % (controlID, cidx)));

                utils.text2HelpWrap(ccontent, 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1340), 140, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                content = content.encode('utf-8');

                helpList = self.getControl(LIST_DICT[controlID]);
                listitem = xbmcgui.ListItem(content, content, tempImg, tempImg);

                helpList.addItem(listitem);


        except Exception as inst:
            self.logger.error(inst);

            pass;'''


    def terms(self, controlID, results):

        try:

            contents = utils.parseValue(results, ['statictext', 'contents', 'content'], False);

            if not isinstance(contents, list):
                contents = list([contents]);


            cidx = 0;
            cih = 0;
            ccontent = '';

            self.logger.debug(json.dumps(results));


            for idx, content in enumerate(contents, 0):

                if content is None:
                    content = ' ~~~_+_+_+_~~~';

                ccontent += content.replace(u"\u25cf", u"\u2022");
                ccontent += ' ~~~_+_+_+_~~~'

                cih = utils.text2HelpSize(ccontent, 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1340), 140, 'Regular', None, multiplier=1, sharpen=False, bgimage=None);

                if cih >= 1240:

                    tempImg = os.path.join(self.help_terms, ('%s-%s.png' % (controlID, cidx)));

                    utils.text2HelpWrap(ccontent, 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1340), 140, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                    content = content.encode('utf-8');

                    helpList = self.getControl(LIST_DICT[controlID]);
                    listitem = xbmcgui.ListItem(content, content, tempImg, tempImg);

                    helpList.addItem(listitem);

                    cidx += 1;
                    cih = 0;
                    ccontent = '';

            if cih < 1240 and cih > 0:

                tempImg = os.path.join(self.help_terms, ('%s-%s.png' % (controlID, cidx)));

                utils.text2HelpWrap(ccontent, 'RGB', (255, 255, 255), (0, 0, 0), 36, (2560, 1340), 140, 'Regular', tempImg, multiplier=1, sharpen=False, bgimage=None);

                content = content.encode('utf-8');

                helpList = self.getControl(LIST_DICT[controlID]);
                listitem = xbmcgui.ListItem(content, content, tempImg, tempImg);

                helpList.addItem(listitem);


        except Exception as inst:
            self.logger.error(inst);

            pass;


    def contactsupport(self, mailto):

        import platform;
        import webbrowser;

        try:

            mailtoURL = mailto.format(
                appid='FunimationNOW',
                version=utils.getAddonInfo('version'),
                device=('%s.%s' % (platform.system(), platform.machine())),
                os=('%s - Kodi.%s' % (platform.version(), xbmc.getInfoLabel('System.BuildVersion'))),
                connection='WiFi',
                carrier='N/A'
            );

            githubUrl = 'https://github.com/Protocol-X/%s/issues/new' % utils.getAddonInfo('id');

            osWin = xbmc.getCondVisibility('system.platform.windows');
            osOsx = xbmc.getCondVisibility('system.platform.osx');
            osLinux = xbmc.getCondVisibility('system.platform.linux');
            osAndroid = xbmc.getCondVisibility('System.Platform.Android');

            if osOsx:    
                
                try:
                    utils.openBrowser(mailtoURL);
                    utils.openBrowser(githubUrl);
                    
                except:
                    xbmc.executebuiltin("System.Exec(open '%s')" % mailtoURL);
                    xbmc.executebuiltin("System.Exec(open '%s')" % githubUrl);

            elif osWin:
                
                try:
                    utils.openBrowser(mailtoURL);
                    utils.openBrowser(githubUrl);
                    
                except:
                    xbmc.executebuiltin("System.Exec(cmd.exe /c start '%s')" % mailtoURL);
                    xbmc.executebuiltin("System.Exec(cmd.exe /c start '%s')" % githubUrl);

            elif osLinux and not osAndroid:
                
                try:
                    utils.openBrowser(mailtoURL);
                    utils.openBrowser(githubUrl);
                    
                except:
                    xbmc.executebuiltin("System.Exec(xdg-open '%s')" % mailtoURL);
                    xbmc.executebuiltin("System.Exec(xdg-open '%s')" % githubUrl);
                
            elif osAndroid:
                
                xbmc.executebuiltin("StartAndroidActivity(com.google.android.gmcom.google.android.gm.ComposeActivityGmail,android.content.Intent.ACTION_SENDTO,plain/text,%s)" % mailtoURL);

                #Until we can figure out the email issues.
                utils.openBrowser('https://github.com/Protocol-X/%s/issues/new' % utils.getAddonInfo('id'));
                #http://stackoverflow.com/questions/8284706/send-email-via-gmail
                #http://stackoverflow.com/questions/3470042/intent-uri-to-launch-gmail-app
                #http://forum.kodi.tv/showthread.php?tid=232485


        except:
            pass;
 

    def setVisible(self, view, state):
        self.getControl(view).setVisible(state);

        pass;


    def getResultCode(self):
        return self.result_code;

        pass;



    def runDirectoryChecks(self):

        #dsPath = xbmc.translatePath(os.path.join('special://userdata/addon_data', utils.getAddonInfo('id')));
        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.help_about = os.path.join(dsPath, 'media/help/about');
        self.help_faq = os.path.join(dsPath, 'media/help/faq');
        self.help_support = os.path.join(dsPath, 'media/help/support');
        self.help_privacy = os.path.join(dsPath, 'media/help/privacy');
        self.help_terms = os.path.join(dsPath, 'media/help/terms');

        utils.checkDirectory(self.help_about);
        utils.checkDirectory(self.help_faq);
        utils.checkDirectory(self.help_support);
        utils.checkDirectory(self.help_privacy);
        utils.checkDirectory(self.help_terms);



def helpmenu():
    
    helpmenugui = HelpMenuUI("funimation-help-menu.xml", utils.getAddonInfo('path'), 'default', "720p");

    helpmenugui.createHelpMenuButtons();
    helpmenugui.doModal();

    del helpmenugui;
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

from resources.lib.modules import utils;

CWD = os.getcwd()



class NAvListUi(xbmcgui.WindowXMLDialog):

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):

        self.logger = utils.getLogger();

        self.listset = None;
        self.sX = 0;
        self.sY = 51;
        self.sip = None;


    def setInitialItem(self, listset, x, y):

        self.listset = listset;
        self.sX = x;
        self.sY += y;


    def onInit(self):

        self.runDirectoryChecks();


        if self.listset:
            self.createOptionList();

        else:
            self.close();


    def onClick(self, controlID):

        if controlID == 20:

            selectList = self.getControl(controlID);
            self.sip = selectList.getSelectedPosition();

            self.close();


        elif controlID == 1000:
            self.close();


    def createOptionList(self):

        selectList = self.getControl(20);
        items = self.listset['fchoices'].items();
        fidx = self.listset['fidx'];

        selectList.setPosition(self.sX, self.sY);


        for idx, listData in items:

            listTitle = listData.get('title', '');
            listFile = re.sub(r'[/]+', '_', listTitle, re.I);

            listImg = os.path.join(self.select_list, ('%s.png' % listFile));

            if not os.path.isfile(listImg):
                utils.text2Display(listTitle, 'RGB', (242, 242, 242), (0, 0, 0), 28, 'Bold', listImg, multiplier=1, sharpen=True, bgimage=None);

            listitem = xbmcgui.ListItem('', '', listImg, listImg);

            selectList.addItem(listitem);

        try:
            xbmc.executebuiltin('Control.SetFocus(20, %s)' % fidx);

        except:
            pass;
            

    def runDirectoryChecks(self):

        dsPath = xbmc.translatePath(utils.addonInfo('profile'));

        self.select_main = os.path.join(dsPath, 'media/select/main');
        self.select_list = os.path.join(dsPath, 'media/select/list');

        utils.checkDirectory(self.select_main);
        utils.checkDirectory(self.select_list);



    def getSelectedItemPosition(self):
        return self.sip;



def select(listset, sX, sY):

    
    selectui = NAvListUi("funimation-select.xml", utils.getAddonInfo('path'), 'default', "720p");   
    
    selectui.setInitialItem(listset, sX, sY);
    selectui.doModal();


    selectedItemPosition = selectui.getSelectedItemPosition();

    del selectui;

    return selectedItemPosition

    



# declare file encoding
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html

import xbmcgui, xbmcaddon, xbmc
from resources.lazy_lib import *

#import sys
#sys.stdout = open('C:\\Temp\\test.txt', 'w')

global ignore_by
ignore_by = sys.argv[1][1:-1]
_addon_ = xbmcaddon.Addon("script.lazytv")
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString
scriptPath = _addon_.getAddonInfo('path')

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
SAVE = 5
HEADING = 1
ACTION_SELECT_ITEM = 7


class xGUI(xbmcgui.WindowXMLDialog):

    def onInit(self):

        self.ok = self.getControl(SAVE)
        self.ok.setLabel(lang(32105))

        self.hdg = self.getControl(HEADING)
        self.hdg.setLabel('LazyTV')
        self.hdg.setVisible(True)

        self.x = self.getControl(3)
        self.x.setVisible(False)

        self.name_list = self.getControl(6)
        self.uo = user_options
        self.new_ignore_list = []

        self.ea = xbmcgui.ListItem(lang(32107))
        self.ia = xbmcgui.ListItem(lang(32108))
        self.name_list.addItem(self.ea)
        self.name_list.addItem(self.ia)
        self.name_list.getListItem(0).select(True)

        self.ok.controlRight(self.name_list)

        self.item_count = 2

        for i in self.uo:
            
            if ignore_by == 'name':
                self.tmp = xbmcgui.ListItem(i[0],thumbnailImage=i[2])
                self.name_list.addItem(self.tmp)
                if i[1] in users_ignore_list:
                    self.name_list.getListItem(self.item_count).select(True)
            
            elif ignore_by == 'length':
                self.tmp = xbmcgui.ListItem(i[1])
                self.name_list.addItem(self.tmp)
                if i[0] in users_ignore_list:
                    self.name_list.getListItem(self.item_count).select(True)
            else:
                self.tmp = xbmcgui.ListItem(i)
                self.name_list.addItem(self.tmp)
                if i in users_ignore_list:
                    self.name_list.getListItem(self.item_count).select(True)
            
            self.item_count += 1

        self.setFocus(self.name_list)

    def onAction(self, action):
        actionID = action.getId()
        if (actionID in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK)):
            self.close()

    def onClick(self, controlID):

        if controlID == SAVE:
            for itm in range(self.item_count):
                if itm != 0 and itm != 1 and self.name_list.getListItem(itm).isSelected():
                    self.new_ignore_list.append(itm)
            self.close()

        else:
            selItem = self.name_list.getSelectedPosition()
            if selItem == 0:
                self.process_itemlist(True)
            elif selItem == 1:
                self.process_itemlist(False)
            else:
                if self.name_list.getSelectedItem().isSelected():
                    self.name_list.getSelectedItem().select(False)
                else:
                    self.name_list.getSelectedItem().select(True)

    def process_itemlist(self, set_to):
        for itm in range(self.item_count):
            if itm != 0 and itm != 1:
                if set_to == True:
                    self.name_list.getListItem(itm).select(True)
                else:
                    self.name_list.getListItem(itm).select(False)


def ignore_dialog_script(ignore_by):
 
    grab_all_shows = {"jsonrpc": "2.0", 
    "method": "VideoLibrary.GetTVShows","params": {"properties": ["genre", "title", "mpaa", "thumbnail"]}, "id": "allTVShows"}

    grab_all_episodes = {"jsonrpc": "2.0", 
    "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["runtime"]}, "id": "allTVEpisodes"}

    global primary_list
    global users_ignore_list
    global user_options
    all_variables = []
    users_ignore_list = []
    users_ignore_list_int = []
    add_setting = []
    carry_on = []
    primary_list = []
    user_options = []

    if ignore_by == 'name':
        all_shows = json_query(grab_all_shows, True)
        if 'tvshows' in all_shows:
            all_s = all_shows['tvshows']
            all_variables = [(x['title'],str(x['tvshowid']),x['thumbnail']) for x in all_s]
        else:
            all_variables = []
        all_variables.sort()

    elif ignore_by == 'genre':
        all_genres = json_query({"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"type": "tvshow"},"id": "1"}, True)
        if 'genres' in all_genres:
            all_g = all_genres['genres']
            all_variables = [x['label'] for x in all_g]
        else:
            all_variables = []
        all_variables.sort()

    elif ignore_by == 'rating':
        all_shows = json_query(grab_all_shows, True)
        if 'tvshows' in all_shows:
            all_s = all_shows['tvshows']   
            all_variables = [x['mpaa'] for x in all_s if x['mpaa'] != '']
            all_variables = list(set(all_variables))
        else:
            all_variables = []
        all_variables.sort()
        all_variables.append(lang(32111))

    elif ignore_by == 'length':
        all_shows = json_query(grab_all_episodes, True)  
        if 'episodes' in all_shows:
            all_s = all_shows['episodes']    
            all_variables = [x['runtime'] for x in all_s]
            all_variables = list(set(all_variables))
        else:
            all_variables = []
        all_variables.sort()
        
    else:
        pass

    IG_setting_string = _setting_('IGNORE')  

    if len(IG_setting_string) > 1:
        IG_setting_list = IG_setting_string.split('|')
        for item in IG_setting_list:
            if ignore_by + ':-:' in item:
                users_ignore_list_int.append(item)
                new_str = item.replace(ignore_by+":-:","")
                users_ignore_list.append(new_str)

        carry_on = [x for x in IG_setting_list if x not in users_ignore_list_int]
    else:
        carry_on = IG_setting_string.split('|')

    #users_ignore_list is the list of items that are currently ignored

    for var in all_variables:
        if ignore_by == 'name':
            line = var
            primary_list.append(var[1])
        elif ignore_by == 'length':
            line = (str(var), str(int(var)//60) + " minutes")
            primary_list.append(str(var))
        else:
            line = var
            primary_list.append(var)
        user_options.append(line)

    #primary_list is the list of items as they will be saved to the settings
    #user_options is the list of items as they will be seen on the screen
    #primary_list and user_options are in the same order

    creation = xGUI("DialogSelect.xml", scriptPath, 'Default')
    creation.doModal()
    new_ignore_list = creation.new_ignore_list
    del creation

    for x in new_ignore_list:
        add = ignore_by + ":-:" + primary_list[x-2] #if ignore_by != 'length' else str(item))
        add_setting.append(add)
        _addon_.setSetting(id="IGNORE",value="|".join(carry_on + add_setting))

ignore_dialog_script(ignore_by)
_addon_.openSettings()
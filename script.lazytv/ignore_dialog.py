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

import xbmc, xbmcgui, xbmcaddon
from resources.lazy_lib import *
import json

#import sys
#sys.stdout = open('C:\\Temp\\test.txt', 'w')

ignore_by = sys.argv[1][1:-1]
_addon_ = xbmcaddon.Addon("script.lazytv")
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString

def ignore_dialog_script(ignore_by):
 
    grab_all_shows = {"jsonrpc": "2.0", 
    "method": "VideoLibrary.GetTVShows","params": {"properties": ["genre", "title", "mpaa"]}, "id": "allTVShows"}

    grab_all_episodes = {"jsonrpc": "2.0", 
    "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["runtime"]}, "id": "allTVEpisodes"}

    idx = ['name','genre','length','rating'].index(ignore_by)
    element = [lang(30101),lang(30102),lang(30103), lang(30104)][idx]  
    all_variables = []
    users_ignore_list = []
    users_ignore_list_int = []
    add_setting = []
    carry_on = []

    if ignore_by == 'name':
        all_shows = json_query(grab_all_shows)['result']['tvshows']    
        all_variables = [x['title'] for x in all_shows]
        all_variables.sort()
    elif ignore_by == 'genre':
        all_genres = json_query({"jsonrpc": "2.0", "method": "VideoLibrary.GetGenres", "params": {"type": "tvshow"},"id": "1"})['result']['genres'] 
        all_variables = [x['label'] for x in all_genres]
        all_variables.sort()
    elif ignore_by == 'rating':
        all_shows = json_query(grab_all_shows)['result']['tvshows']    
        all_variables = [x['mpaa'] for x in all_shows if x['mpaa'] != '']
        all_variables = list(set(all_variables))
        all_variables.sort()
        all_variables.append(lang(30111))
    elif ignore_by == 'length':
        all_shows = json_query(grab_all_episodes)['result']['episodes']    
        all_variables = [x['runtime'] for x in all_shows ]
        all_variables = list(set(all_variables))
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

    while True:
        
        primary_list = ['SC','C','IA','IN']
        user_options = ["--"+lang(30105)+"--","--"+lang(30106)+"--","--"+lang(30107)+"--","--"+lang(30108)+"--"]  ###STRINGS###

        # creates user_options list, which is the list of all TV shows with [Excluded] appended to the ones that are in the ignore list
        for var in all_variables:
            try:
                primary_list.append(var)
                line = var if ignore_by != 'length' else str(int(var)//60) + " minutes"
                if var in users_ignore_list:
                    user_options.append("["+lang(30109)+"] " + line ) ###STRINGS###
                else:
                    user_options.append(line)
            except:
                break
          
        # creates the dialog with the user_options list
        inputchoice = xbmcgui.Dialog().select(lang(30110) % (element), user_options) ###STRINGS###

        #if the choice is a TV show, then see if it is in the ignored list, if it is then remove, if not then add it,  
        if inputchoice >3:
            if primary_list[inputchoice] in users_ignore_list:
                users_ignore_list.remove(primary_list[inputchoice])
            else:  
                users_ignore_list.append(primary_list[inputchoice])
        elif user_options[inputchoice] == "--"+lang(30105)+"--":            #save the ignored list as the new long term save ###STRINGS###
            for item in users_ignore_list:
                add = ignore_by + ":-:" + item #if ignore_by != 'length' else str(item))
                add_setting.append(add)
            _addon_.setSetting(id="IGNORE",value="|".join(carry_on + add_setting))
            break
        elif user_options[inputchoice] == "--"+lang(30106)+"--":            #closes the dialog without saving ###STRINGS###
            break
        elif user_options[inputchoice] == "--"+lang(30107)+"--":            #loops through all entries and set them to IGNORE ###STRINGS###
            users_ignore_list = []
            for itemY in all_variables:
                users_ignore_list.append(itemY)
        elif user_options[inputchoice] == "--"+lang(30108)+"--":        # clear the current user ignore list ###STRINGS###
            users_ignore_list = []
        else:
            break#"""

ignore_dialog_script(ignore_by)
_addon_.openSettings()
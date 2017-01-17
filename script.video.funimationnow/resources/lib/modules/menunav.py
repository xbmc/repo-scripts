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



import logging;
import re;
import xbmc;
import os;
import xbmcgui;

from resources.lib.modules import utils;


logger = logging.getLogger('funimationnow');



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


func = dict({
    SEARCH_WINDOW: 'search',
    HOME_WINDOW: 'home',
    QUEUE_WINDOW: 'queue',
    ALL_WINDOW: 'all',
    SIMALCAST_WINDOW: 'simalcast',
    GENRE_WINDOW: 'genres',
    SETTINGS_WINDOW: 'settings',
    HELP_WINDOW: 'help',
    LOGOUT_WINDOW: 'logout',
});


def chooser(landing_page, parent, child, controlID):

    result = EXIT_CODE;

    logger.debug(controlID);
    logger.debug(child);
    logger.debug(func.get(controlID));

    try:

        result = globals()[func.get(controlID)](landing_page, parent, child, controlID);

    except Exception as inst:
        logger.error(inst);

        pass;


    landing_page.result_code = result;


    return result;
    

def home(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;


    if child == HOME_WINDOW:
        RESULT_CODE = REST_CODE;

    else:
        RESULT_CODE = HOME_SCREEN_CODE;


    return RESULT_CODE;


def search(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    if child == SEARCH_WINDOW:
        pass;

    else:

        try:

            from resources.lib.gui.searchgui import search;

            search(landing_page);

            pass;

        except Exception as inst:
            logger.error(inst);

            pass;

    
    return RESULT_CODE;


def queue(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    if child == QUEUE_WINDOW:
        pass;

    else:

        try:

            from resources.lib.gui.watchlistgui import watchlist;
            
            mnavset = dict({
                'width': 95,
                'title': 'MY QUEUE',
                'params': 'id=myqueue&title=My Queue',
                'target': 'longlist',
                'path': 'longlist/myqueue/'
            });

            watchlist(landing_page, mnavset);

            pass;

        except Exception as inst:
            logger.error(inst);

            pass;

    
    return RESULT_CODE;


def all(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    if child == ALL_WINDOW:
        pass;

    else:

        try:

            from resources.lib.gui.genreselectgui import genreselect;
            
            mnavset = dict({
                'width': 140,
                'title': 'RECENTLY ADDED',
                'params': 'id=shows&title=All Shows&showGenres=true',
                'target': 'longlist',
                'path': 'longlist/content/',
                'offset': 0,
                'limit': 144
            });

            genreselect(landing_page, mnavset);

            pass;

        except Exception as inst:
            logger.error(inst);

            pass;

    
    return RESULT_CODE;


def simalcast(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    if child == SIMALCAST_WINDOW:
        pass;

    else:

        try:

            from resources.lib.gui.audioselectgui import audioselect;
            
            mnavset = dict({
                'width': 108,
                'title': 'SIMULDUBS',
                'params': 'id=simulcasts&title=Simulcasts',
                'target': 'longlist',
                'path': 'longlist/content/'
            });

            audioselect(landing_page, mnavset);

            pass;

        except Exception as inst:
            logger.error(inst);

            pass;

    
    return RESULT_CODE;


def genres(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    if child == GENRE_WINDOW:
        pass;

    else:

        try:

            from resources.lib.gui.genreshowsgui import genreshows;
            
            mnavset = dict({
                'width': 140,
                'title': 'RECENTLY ADDED',
                'params': 'id=genres&title=Genres&role=b',
                'target': 'longlist',
                'path': 'longlist/genres/',
                'offset': 0,
                'limit': 144
            });

            genreshows(landing_page, mnavset);

            pass;

        except Exception as inst:
            logger.error(inst);

            pass;


    return RESULT_CODE;


def settings(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    try:

        #xbmc.executebuiltin('Addon.OpenSettings(%s)' % utils.getAddonInfo('id'));
        utils.addon.openSettings();

        utils.lock();
        utils.sleep(2000);
        utils.unlock();

        addon_data = xbmc.translatePath(utils.getAddonInfo('profile')).decode('utf-8');
        tokens = xbmc.translatePath(os.path.join(addon_data, 'tokens.db'));

        if not os.path.exists(tokens):
            RESULT_CODE = LOGOUT_CODE;

    except Exception as inst:
        logger.error(inst);

        pass;


    return RESULT_CODE;


def help(landing_page, parent, child, controlID):

    RESULT_CODE = REST_CODE;

    try:

        from resources.lib.gui.helpmenugui import helpmenu;

        helpmenu();

    except Exception as inst:
        logger.error(inst);

        pass;



    return RESULT_CODE;


def logout(landing_page, parent, child, controlID):

    RESULT_CODE = LOGOUT_CODE;

    from resources.lib.modules import cleardata;

    logger.debug('Running Cleanup Script');

    try:
        cleardata.cleanup();

    except:
        pass;

    
    return RESULT_CODE;
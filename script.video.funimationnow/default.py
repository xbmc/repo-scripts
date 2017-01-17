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

    http://nullege.com/codes/show/src%40m%40y%40mythbox-HEAD%40resources%40src%40mythbox%40ui%40toolkit.py/270/xbmcgui.WindowXML/python
'''


import logging;
import sys;
import xbmc;

from resources.lib.modules import utils;
from resources.lib.gui.splashgui import splashscreen;
from resources.lib.gui.trialgui import trialscreen;
from resources.lib.gui.maingui import main;




logger = utils.getLogger();
logger.debug('ARGV: %s', sys.argv);



EXIT_CODE = 2;
SUCCESS_CODE = 3;
EXPIRE_CODE = 4;
HOME_SCREEN_CODE = 5;
BACK_CODE = 6;
LOGOUT_CODE = 7;



def loginWindow():

    result = trialscreen();

    while result is not True:

        logger.debug('CODE = %s' % result)
        
        if result == SUCCESS_CODE:
            mainGui();
            #exit();

            break;

        elif result == EXIT_CODE:
            exit();

            break;

        elif result == LOGOUT_CODE:
            loginWindow();

            break;


def mainGui():
    
    result = main();
    
    if result == EXIT_CODE:
        exit();

    elif result == LOGOUT_CODE:
        loginWindow();


def confirmLogin():

    token = utils.getToken('funimationnow');
    userType = utils.setting('fn.userType');

    if userType and token:

        if userType.lower() == 'funimationsubscriptionuser':
            return True;

        else:
            return False;

    else:
        return False;



if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':

    from resources.lib.modules import cleardata;

    logger.debug('Running Cleanup Script');

    try:
        cleardata.cleanup();

    except:
        pass;



elif (__name__ == '__main__'):

    splash_screen = utils.setting('fn.splash_screen');

    if splash_screen is None or splash_screen in ('true', 'True', True):
        splashscreen();


    if confirmLogin():
        mainGui();

    else:
        loginWindow();

    

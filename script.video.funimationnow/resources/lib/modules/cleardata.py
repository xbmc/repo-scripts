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
import logging;
import shutil;
import os;

from resources.lib.modules import utils;


logger = logging.getLogger('funimationnow');

#addon = xbmcaddon.Addon('script.video.funimationnow');


def cleanup(skip_settings=False):

    try:

        addon_data = xbmc.translatePath(utils.getAddonInfo('profile')).decode('utf-8');

        try:

            utils.resetSettings();

        except:
            pass;

        try:

            tokens = xbmc.translatePath(os.path.join(addon_data, 'tokens.db'));
            os.remove(tokens);

        except:
            pass;

        try:

            mediaPath = xbmc.translatePath(os.path.join(addon_data, 'media'));
            shutil.rmtree(mediaPath);

        except:
            pass;

        try:

            synch = xbmc.translatePath(os.path.join(addon_data, 'synch.db'));
            os.remove(synch);

        except:
            pass;


    except Exception as inst:
        logger.error(inst);

        pass;


    pass;
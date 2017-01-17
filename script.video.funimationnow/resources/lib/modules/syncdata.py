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


import time;
import hashlib;
import logging;
import json;

# convert to string


from resources.lib.modules import utils;

try: 
    from sqlite3 import dbapi2 as database;

except: 
    from pysqlite2 import dbapi2 as database;


logger = logging.getLogger('funimationnow');


def setDetailsData(pkey, details, refreshafter):
    
    logger.debug('Attempting to set Details Data in detailsdata DB.');
    
    try:

        logger.debug('Validating DB file exists.');

        utils.makeFile(utils.dataPath);

        dbcon = database.connect(utils.synchFile);
        dbcur = dbcon.cursor();

        logger.debug('Creating detailsdata table if it does not exist.');

        dbcur.execute("CREATE TABLE IF NOT EXISTS detailsdata (""pkey TEXT, ""details TEXT, ""refreshafter TEXT"", ""UNIQUE(pkey)"");");

        try: 

            logger.debug('Attempting to delete detailsdata entry.');

            dbcur.execute("DELETE FROM detailsdata WHERE pkey IN ('%s')" % pkey);

        except Exception as inst:

            logger.error(inst);

            pass;

        
        try: 

            logger.debug('Attempting to insert detailsdata entry.');

            details = json.dumps(details);

            dbcur.execute("INSERT INTO detailsdata Values (?, ?, ?)", (pkey, details, refreshafter));

        except Exception as inst:

            logger.error(inst);

            pass;


        logger.debug('Commiting DB change.');
        
        dbcon.commit();


        return True;


    except Exception as inst:

        logger.error(inst);

        return False;


def getToken(system):

    try:

        dbcon = database.connect(utils.tokensFile);
        dbcur = dbcon.cursor();

    except:

        return None;

    try:

        dbcur.execute("SELECT * FROM tokens WHERE system IN ('%s')" % system);

        match = dbcur.fetchone();

        if match is not None:

            return match;

        else:
            return None;

    except Exception as inst:
        logger.error(inst);

        return None;


def getDetailsData(pkey):
    
    logger.debug('Attempting to get Details Data in detailsdata DB.');
    
    try:

        dbcon = database.connect(utils.synchFile);
        dbcur = dbcon.cursor();

    except:
        return None;


    try:

        dbcur.execute("SELECT * FROM detailsdata WHERE pkey IN ('%s')" % pkey);

        match = dbcur.fetchone();

        if match is not None and len(match) == 3:
            return match;

        else:
            return None;

    except Exception as inst:
        logger.error(inst);

        return None;



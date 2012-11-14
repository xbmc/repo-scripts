#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

from datetime import datetime
import time

import mysql.connector

"""

Example using MySQL Connector/Python showing:
* How to get datetime, date and time types
* Shows also invalid dates returned and handled

"""

def main(config):
    db = mysql.connector.Connect(**config)
    cursor = db.cursor()
    
    tbl = 'myconnpy_dates'
    
    # Drop table if exists, and create it new
    stmt_drop = "DROP TABLE IF EXISTS %s" % (tbl)
    cursor.execute(stmt_drop)
    
    stmt_create = """
    CREATE TABLE %s (
      `id` tinyint(4) NOT NULL AUTO_INCREMENT,
      `c1` date DEFAULT NULL,
      `c2` datetime DEFAULT NULL,
      `c3` time DEFAULT NULL,
      `c4` timestamp DEFAULT 0,
      `changed` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`)
    )""" % (tbl)
    cursor.execute(stmt_create)

    # Note that by default MySQL takes invalid timestamps. This is for
    # backward compatibility. As of 5.0, use sql modes NO_ZERO_IN_DATE,NO_ZERO_DATE
    # to prevent this.
    data = [
        (datetime.now().date(),datetime.now(),time.localtime(),int(time.mktime(datetime.now().timetuple()))),
        ('0000-00-00','0000-00-00 00:00:00','00:00:00',0),
        ('1000-00-00','9999-00-00 00:00:00','00:00:00',0),
        ]
    
    # not using executemany to handle errors better
    for d in data:
        stmt_insert = "INSERT INTO %s (c1,c2,c3,c4) VALUES (%%s,%%s,%%s,FROM_UNIXTIME(%%s))" % (tbl)
        try:
            cursor.execute(stmt_insert, d)
        except (mysql.connector.errors.InterfaceError, TypeError), e:
            print "Failed inserting %s\nError: %s\n" % (d,e)
            raise
            
        warnings = cursor.fetchwarnings()
        if warnings:
            print warnings

    # Read the names again and print them
    stmt_select = "SELECT * FROM %s ORDER BY id" % (tbl)
    cursor.execute(stmt_select)

    for row in cursor.fetchall():
    	print "%3s | %10s | %19s | %8s | %19s |" % (
    	    row[0],
    	    row[1],
    	    row[2],
    	    row[3],
    	    row[4],
    	)
    	
    # Cleaning up, dropping the table again
    cursor.execute(stmt_drop)

    cursor.close()
    db.close()

if __name__ == '__main__':
    #
    # Configure MySQL login and database to use in config.py
    #
    from config import Config
    config = Config.dbinfo().copy()
    main(config)

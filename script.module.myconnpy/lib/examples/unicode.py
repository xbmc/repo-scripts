#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

import mysql.connector

"""

Example using MySQL Connector/Python showing:
* the usefulness of unicode, if it works correctly..
* dropping and creating a table
* inserting and selecting a row
"""

info = """
For this to work you need to make sure your terminal can output
unicode character correctly. Check if the encoding of your terminal
is set to UTF-8.
"""

def main(config):
    db = mysql.connector.Connect(**config)
    cursor = db.cursor()
    
    # Show the unicode string we're going to use
    unistr = u"\u00bfHabla espa\u00f1ol?"
    print "Unicode string: %s" % unistr.encode('utf8')
    
    # Drop table if exists, and create it new
    stmt_drop = "DROP TABLE IF EXISTS unicode"
    cursor.execute(stmt_drop)
    
    stmt_create = """
    CREATE TABLE unicode (
        id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
        str VARCHAR(50) DEFAULT '' NOT NULL,
        PRIMARY KEY (id)
    ) CHARACTER SET 'utf8'"""
    cursor.execute(stmt_create)
    
    # Insert a row
    stmt_insert = "INSERT INTO unicode (str) VALUES (%s)"
    cursor.execute(stmt_insert, (unistr,))
    
    # Select it again and show it
    stmt_select = "SELECT str FROM unicode WHERE id = %s"
    cursor.execute(stmt_select, (1,))
    row = cursor.fetchone()
    
    print "Unicode string coming from db: %s" % row[0].encode('utf8')
    
    # Cleaning up, dropping the table again
    cursor.execute(stmt_drop)
    db.close()

if __name__ == '__main__':
    #
    # Configure MySQL login and database to use in config.py
    #
    from config import Config
    config = Config.dbinfo().copy()
    print info
    main(config)

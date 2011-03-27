#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

import mysql.connector

"""

Example using MySQL Connector/Python showing:
* dropping and creating a table
* inserting 3 rows using executemany()
* selecting data and showing it

"""

def main(config):
    db = mysql.connector.Connect(**config)
    cursor = db.cursor()
    
    # Drop table if exists, and create it new
    stmt_drop = "DROP TABLE IF EXISTS names"
    cursor.execute(stmt_drop)
    
    stmt_create = """
    CREATE TABLE names (
        id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
        name VARCHAR(30) DEFAULT '' NOT NULL,
        info TEXT DEFAULT '',
        age TINYINT UNSIGNED DEFAULT '30',
        PRIMARY KEY (id)
    )"""
    cursor.execute(stmt_create)

    info = "abc"*10000

    # Insert 3 records
    names = ( ('Geert',info), ('Jan',info), ('Michel',info) )
    stmt_insert = "INSERT INTO names (name,info) VALUES (%s,%s)"
    cursor.executemany(stmt_insert, names)
    
    warnings = cursor.fetchwarnings()
    if warnings:
        print warnings
    db.commit()
    
    # Read the names again and print them
    stmt_select = "SELECT id, name, info, age FROM names ORDER BY id"
    cursor.execute(stmt_select)

    for row in cursor.fetchall():
        print "%d | %s | %d\nInfo: %s..\n" % (row[0], row[1], row[3], row[2][20])
    	
    # Cleaning up, dropping the table again
    cursor.execute(stmt_drop)

    db.close()

if __name__ == '__main__':
    #
    # Configure MySQL login and database to use in config.py
    #
    from config import Config
    config = Config.dbinfo().copy()
    main(config)
    
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

import mysql.connector

"""

Example using MySQL Connector/Python showing:
* sending multiple statements and retriving their results

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
    
    stmts = [
        "INSERT INTO names (name) VALUES ('Geert')",
        "SELECT COUNT(*) AS cnt FROM names",
        "INSERT INTO names (name) VALUES ('Jan'),('Michel')",
        "SELECT name FROM names",
        ]
    
    cursor.execute(' ; '.join(stmts))
    # 1st INSERT-statement
    print "Inserted %d row" % (cursor.rowcount)
    
    # 1st SELECT
    if cursor.next_resultset():
        print "Number of rows: %d" % cursor.fetchone()[0]
    
    # 2nd INSERT
    if cursor.next_resultset():
        print "Inserted %d rows" % (cursor.rowcount)
    
    # 2nd SELECT
    if cursor.next_resultset():
        print "Names in table:", ' '.join([ n[0] for n in cursor.fetchall()])
    
    cursor.execute(stmt_drop)

    db.close()

if __name__ == '__main__':
    #
    # Configure MySQL login and database to use in config.py
    #
    from config import Config
    config = Config.dbinfo().copy()
    main(config)

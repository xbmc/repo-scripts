#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

import mysql.connector

"""

Example using MySQL Connector/Python showing:
* that show engines works..

"""

def main(config):
    db = mysql.connector.Connect(**config)
    cursor = db.cursor()
    
    # Select it again and show it
    stmt_select = "SHOW ENGINES"
    cursor.execute(stmt_select)
    rows = cursor.fetchall()

    for row in rows:
        print row

    db.close()

if __name__ == '__main__':
    #
    # Configure MySQL login and database to use in config.py
    #
    from config import Config
    config = Config.dbinfo().copy()
    main(config)

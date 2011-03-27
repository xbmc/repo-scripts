#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

import mysql.connector

"""

Example using MySQL Connector/Python showing:
* using warnings

"""

def main(config):
    config['get_warnings'] = True
    db = mysql.connector.Connect(**config)
    cursor = db.cursor()
    
    stmt_select = "SELECT 'abc'+1"
    
    print "Remove all sql modes.."
    cursor.execute("SET sql_mode = ''") # Make sure we don't have strict on
    
    print "Execute '%s'" % stmt_select
    cursor.execute(stmt_select)
    cursor.fetchall()
    
    warnings = cursor.fetchwarnings()
    if warnings:
        print warnings
    else:
        print "We should have got warnings."
        raise StandardError("Got no warnings")

    db.close()

if __name__ == '__main__':
    #
    # Configure MySQL login and database to use in config.py
    #
    from config import Config
    config = Config.dbinfo().copy()
    main(config)

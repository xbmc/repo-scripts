"""
Database class to store offline information.
This databse will store information about
what the user has watch while he was offline.
"""

import sqlite3 as lite
import json
import helper

class Database(object):
    """ A helper class for the database """

    def __init__(self, db_file):
        self.__db_file = db_file

        con = lite.connect(self.__db_file)
        cur = con.cursor()

        try:
            cur.execute("SELECT id, p FROM parameter LIMIT 1")
        except lite.OperationalError:
            helper.debug("Create the table")

            try:
                cur.execute("CREATE TABLE IF NOT EXISTS 'parameter' (id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, p TEXT)")
            except Exception:
                helper.debug("Unable to create table")
        finally:
            cur.close()
            con.close()

    def get_all(self):
        """ Get all rows from the offline database """
        con = lite.connect(self.__db_file)
        cur = con.cursor()

        try:
            cur.execute("SELECT id, p FROM parameter")
            rows = cur.fetchall()
            return rows
        except lite.OperationalError:
            helper.debug("Unable to get parameter")
        finally:
            cur.close()
            con.close()

        return None

    def write(self, parameter):
        """ Insert new offline method """
        con = None

        try:
            data = json.dumps(parameter)
        except Exception:
            helper.debug("db write: unable to convert json object to string")
            return None

        con = lite.connect(self.__db_file)

        try:
            sql = "INSERT INTO parameter ( p ) VALUES ( ? )"
            con.execute(sql, (data, ))
            con.commit()
        except Exception:
            helper.debug("Unable to write to database: " + str(data))
        finally:
            con.close()
        return None

    def remove_rows(self, rows):
        """ Remove multiply rows. Rows = [row-id-numbers] """

        if type(rows) is not list:
            return None

        con = lite.connect(self.__db_file)

        for row_id in rows:
            try:
                sql = "DELETE FROM parameter WHERE id = " + str(row_id)
                con.execute(sql)
                con.commit()
            except lite.OperationalError:
                continue

        con.close()
        return None

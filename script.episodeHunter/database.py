#http://wiki.xbmc.org/index.php?title=Eden_API_changes
try:
    import sqlite3 as lite
except:
    import pysqlite2 as lite

from helper import *
import traceback

try:
    import simplejson as json
except ImportError:
    import json


class Database(object):

    def __init__(self, db_file):
        con = None
        cur = None
        self.db_file = db_file

        try:
            con = lite.connect(self.db_file)
            cur = con.cursor()
        except Exception:
            Debug("getAll: SQL error: " + e.args[0])

        if con is not None:
            try:
                cur.execute("SELECT id, p FROM parameter LIMIT 1")
            except Exception:
                Debug("Unable to get table parameter, create the table")
                print(traceback.format_exc())

                try:
                    cur.execute("CREATE TABLE IF NOT EXISTS 'parameter' (id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, p TEXT)")
                except Exception:
                    Debug("Unable to create table")
                    print(traceback.format_exc())
            finally:
                try:
                    cur.close()
                    con.close()
                except Exception:
                    pass
        return None

    # Get all rows from the offline database
    def getAll(self):
        con = None
        cur = None
        try:
            con = lite.connect(self.db_file)
            cur = con.cursor()
        except Exception:
            Debug("getAll: SQL error: " + e.args[0])

        if con is not None:
            try:
                cur.execute("SELECT id, p FROM parameter")
                rows = cur.fetchall()
                return rows
            except Exception:
                Debug("Unable to get parameter")
                print(traceback.format_exc())
            finally:
                try:
                    cur.close()
                    con.close()
                except Exception:
                    pass
        return None

    # Insert new offline method
    def write(self, parameter):
        # {"parameter": {"episode": 8, "title": "True Blood", "season": 5, "tvdb_id": "82283", "percent": 99, "year": null, "duration": 55.2}, "method": "scrobbleEpisode"}
        con = None

        try:
            data = json.dumps(parameter)
        except Exception:
            Debug("db write: unable to convert json object to string")
            return None

        try:
            con = lite.connect(self.db_file)
        except Exception:
            Debug("write: SQL error: " + e.args[0])

        if con is not None:
            try:
                sql = "INSERT INTO parameter ( p ) VALUES ( ? )"
                con.execute(sql, (data, ))
                con.commit()
            except Exception:
                Debug("Unable to write to database: " + str(data))
                print(traceback.format_exc())
            finally:
                try:
                    con.close()
                except Exception:
                    pass
        return None

    # Remove multiply rows. Rows = [row-id-numbers]
    def removeRows(self, rows):
        con = None

        try:
            con = lite.connect(self.db_file)
        except Exception:
            Debug("removeRows: SQL error: " + e.args[0])

        if con is not None:
            for row_id in rows:
                try:
                    sql = "DELETE FROM parameter WHERE id = " + str(row_id)
                    con.execute(sql)
                    con.commit()
                except Exception:
                    Debug("Unable to delete row: " + str(row_id))
                    print(traceback.format_exc())
                    continue

            try:
                con.close()
            except Exception:
                pass
        return None

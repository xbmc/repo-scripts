"""
    Cache service for Kodi
    Version 0.8

    Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen
    Copyright (C) 2019 anxdpanic

    This file is part of script.common.plugin.cache

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only.txt for more information.
"""

from contextlib import closing
import hashlib
import inspect
import os
import socket
import string
import sys
import time

import xbmc

sqlite3 = None
sqlite = None

try:
    import sqlite3
except ImportError:
    sqlite3 = None
    try:
        import sqlite
    except ImportError:
        sqlite = None


class StorageServer:
    def __init__(self, table=None, timeout=24, instance=False):
        if hasattr(sys.modules["__main__"], "xbmc"):
            self.xbmc = sys.modules["__main__"].xbmc
        else:
            import xbmc
            self.xbmc = xbmc

        if hasattr(sys.modules["__main__"], "xbmcvfs"):
            self.xbmcvfs = sys.modules["__main__"].xbmcvfs
        else:
            import xbmcvfs
            self.xbmcvfs = xbmcvfs

        if hasattr(sys.modules["__main__"], "xbmcaddon"):
            self.xbmcaddon = sys.modules["__main__"].xbmcaddon
        else:
            import xbmcaddon
            self.xbmcaddon = xbmcaddon

        if hasattr(sys.modules["__main__"], "xbmcgui"):
            self.xbmcgui = sys.modules["__main__"].xbmcgui
        else:
            import xbmcgui
            self.xbmcgui = xbmcgui

        if hasattr(self.xbmcvfs, "translatePath"):
            self.translate_path = self.xbmcvfs.translatePath
        else:
            self.translate_path = self.xbmc.translatePath

        self.instance = instance
        self._sock = None
        self.die = False
        self.force_abort = False

        self.settings = self.xbmcaddon.Addon(id='script.common.plugin.cache')
        self.language = self.settings.getLocalizedString

        self.dbg = self.settings.getSetting("debug") == "true"

        self.version = to_unicode(self.settings.getAddonInfo('version'))
        self.plugin = u"StorageClient-" + self.version

        self.path = to_unicode(self.translate_path('special://temp/'))
        if not self.xbmcvfs.exists(self.path):
            self._log(u"Making path structure: " + self.path)
            self.xbmcvfs.mkdir(self.path)
        self.path = os.path.join(self.path, 'commoncache.db')

        self.socket = ""
        self.clientsocket = False
        self.sql2 = True if sqlite else False
        self.sql3 = True if sqlite3 else False

        self.daemon_start_time = time.time()
        if self.instance:
            self.idle = int(self.settings.getSetting("timeout"))
        else:
            self.idle = 3

        self.platform = sys.platform
        self.network_buffer_size = 4096

        if isinstance(table, str) and len(table) > 0:
            self.table = ''.join(c for c in table if c in "%s%s" %
                                 (string.ascii_letters, string.digits))
            self._log("Setting table to : %s" % self.table)
        elif table is False:
            self._log("No table defined")

        self.timeout = float(timeout) * 3600

    def _startDB(self):
        try:
            if self.sql3:
                self._log("sql3 - " + self.path)
                self.conn = sqlite3.connect(self.path, check_same_thread=False)
            elif self.sql2:
                self._log("sql2 - " + self.path)
                self.conn = sqlite.connect(self.path)
            else:
                self._log("Error, no sql found")
                return False

            self.curs = self.conn.cursor()
            return True
        except Exception as e:
            self._log("Exception: " + repr(e))
            self.xbmcvfs.delete(self.path)
            return False

    def _aborting(self):
        if self.force_abort:
            if self._sock:
                self._sock.close()
            return True

        if self.instance:
            if self.die:
                return True
        else:
            return self.xbmc.Monitor().abortRequested()
        return False

    def _usePosixSockets(self):
        if (self.platform in ["win32", 'win10'] or
                xbmc.getCondVisibility('system.platform.android') or
                xbmc.getCondVisibility('system.platform.ios') or
                xbmc.getCondVisibility('system.platform.tvos')):
            return False
        else:
            return True

    def _sock_init(self, check_stale=False):
        if not self.socket or check_stale:
            self._log("Checking")

            if self._usePosixSockets():
                self._log("POSIX")
                self.socket = os.path.join(to_unicode(self.translate_path('special://temp/')),
                                           'commoncache.socket')
                if self.xbmcvfs.exists(self.socket) and check_stale:
                    self._log("Deleting stale socket file : " + self.socket)
                    self.xbmcvfs.delete(self.socket)
            else:
                self._log("Non-POSIX")
                port = self.settings.getSetting("port")
                self.socket = ("127.0.0.1", int(port))

        self._log("Done: " + repr(self.socket))

    def _recieveData(self):
        data = self._recv(self.clientsocket)
        self._log("received data: " + data)

        try:
            data = eval(data)
        except:
            self._log("Couldn't evaluate message : " + repr(data))
            data = {"action": "stop"}

        self._log("Done, got data: " + str(len(data)) + " - " + str(repr(data))[0:50])
        return data

    def _runCommand(self, data):
        res = ""
        if data["action"] == "get":
            res = self._sqlGet(data["table"], data["name"])
        elif data["action"] == "get_multi":
            res = self._sqlGetMulti(data["table"], data["name"], data["items"])
        elif data["action"] == "set_multi":
            res = self._sqlSetMulti(data["table"], data["name"], data["data"])
        elif data["action"] == "set":
            res = self._sqlSet(data["table"], data["name"], data["data"])
        elif data["action"] == "del":
            res = self._sqlDel(data["table"], data["name"])
        elif data["action"] == "lock":
            res = self._lock(data["table"], data["name"])
        elif data["action"] == "unlock":
            res = self._unlock(data["table"], data["name"])

        if len(res) > 0:
            self._log("Got response: " + str(len(res)) + " - " + str(repr(res))[0:50])
            self._send(self.clientsocket, repr(res))

        self._log("Done")

    def _showMessage(self, heading, message):
        self._log(repr(type(heading)) + " - " + repr(type(message)))
        icon = self.settings.getAddonInfo('icon')
        self.xbmcgui.Dialog().notification(heading, message, icon, 10000, sound=False)

    def run(self):
        self.plugin = "StorageServer-" + self.version
        self._sock_init(True)

        if not self._startDB():
            self._startDB()

        if self._usePosixSockets():
            self._sock = socket.socket(socket.AF_UNIX)
        else:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        with closing(self._sock) as open_socket:
            try:
                open_socket.bind(self.socket)
            except Exception as e:
                self._log("Exception: " + repr(e))
                self._showMessage(self.language(32100), self.language(32200))

                return False

            open_socket.listen(1)
            open_socket.setblocking(0)

            idle_since = time.time()
            waiting = 0
            while not self._aborting():
                if waiting == 0:
                    self._log("accepting")
                    waiting = 1
                try:
                    (self.clientsocket, address) = open_socket.accept()
                    if waiting == 2:
                        self._log("Waking up, slept for %s seconds." % int(time.time() - idle_since))
                    waiting = 0
                except socket.error as e:
                    if e.errno == 11 or e.errno == 10035 or e.errno == 35:
                        # There has to be a better way to accomplish this.
                        if idle_since + self.idle < time.time():
                            if self.instance:
                                self.die = True
                            if waiting == 1:
                                self._log("Idle for %s seconds. Going to sleep. zzzzzzzz " % self.idle)
                            time.sleep(0.5)
                            waiting = 2
                        continue
                    self._log("EXCEPTION : " + repr(e))
                except:
                    pass

                if waiting:
                    self._log("Continue : " + repr(waiting))
                    continue

                data = self._recieveData()
                self._runCommand(data)
                idle_since = time.time()

                self._log("Done")

            self._log("Closing down")
            # self.conn.close()

        if self._usePosixSockets():
            if self.xbmcvfs.exists(self.socket):
                self._log("Deleting socket file")
                self.xbmcvfs.delete(self.socket)
        self.xbmc.log(self.plugin + " Closed down")

    def _recv(self, sock):
        data = "   "
        idle = True

        i = 0
        start = time.time()
        recv_buffer = ""
        while data[len(data) - 2:] != "\r\n" or not idle:
            try:
                if idle:
                    recv_buffer = sock.recv(self.network_buffer_size)
                    idle = False
                    i += 1
                    recv_buffer = recv_buffer.decode('utf-8', 'ignore')
                    self._log(u"got data  : " + str(i) + u" - " + repr(idle) + u" - " +
                              str(len(data)) + u" + " + str(len(recv_buffer)) + u" | " +
                              repr(recv_buffer)[len(recv_buffer) - 5:])
                    data += recv_buffer
                    start = time.time()
                elif not idle:
                    if data[len(data) - 2:] == "\r\n":
                        content = "COMPLETE\r\n" + (" " * (15 - len("COMPLETE\r\n")))
                        content = content.encode('utf-8', 'ignore')
                        sock.send(content)
                        idle = True
                        self._log(u"sent COMPLETE " + str(i))
                    elif len(recv_buffer) > 0:
                        content = "ACK\r\n" + (" " * (15 - len("ACK\r\n")))
                        content = content.encode('utf-8', 'ignore')
                        sock.send(content)
                        idle = True
                        self._log(u"sent ACK " + str(i))
                    self._log(u"status " + repr(not idle) + u" - " +
                              repr(data[len(data) - 2:] != u"\r\n"))

            except socket.error as e:
                if e.errno not in [10035, 35]:
                    self._log(u"Except error " + repr(e))

                if e.errno in [22]:  # We can't fix this.
                    return ""

                if start + 10 < time.time():
                    self._log(u"over time")
                    break

        self._log(u"done")
        return data.strip()

    def _send(self, sock, data):
        idle = True
        status = ""
        result = ""
        self._log(str(len(data)) + u" - " + repr(data)[0:20])
        i = 0
        start = time.time()
        while len(data) > 0 or not idle:
            send_buffer = " "
            try:
                if idle:
                    if len(data) > self.network_buffer_size:
                        send_buffer = data[:self.network_buffer_size]
                    else:
                        send_buffer = data + "\r\n"
                    send_buffer = send_buffer.encode('utf-8', 'ignore')
                    result = sock.send(send_buffer)
                    i += 1
                    idle = False
                    start = time.time()
                elif not idle:
                    status = ""
                    while status.find("COMPLETE\r\n") == -1 and status.find("ACK\r\n") == -1:
                        status = sock.recv(15)
                        status = status.decode('utf-8', 'ignore')
                        i -= 1

                    idle = True
                    if len(data) > self.network_buffer_size:
                        data = data[self.network_buffer_size:]
                    else:
                        data = ""

                    self._log(u"Got response " + str(i) + u" - " + str(result) + u" == " +
                              str(len(send_buffer)) + u" | " + str(len(data)) + u" - " +
                              repr(send_buffer)[len(send_buffer) - 5:])

            except socket.error as e:
                self._log(u"Except error " + repr(e))
                if e.errno != 10035 and e.errno != 35 and e.errno != 107 and e.errno != 32:
                    self._log(u"Except error " + repr(e))
                    if start + 10 < time.time():
                        self._log(u"Over time")
                        break
        self._log(u"Done")
        return status.find(u"COMPLETE\r\n") > -1

    def _lock(self, table, name):  # This is NOT atomic
        self._log(name)
        locked = True
        curlock = self._sqlGet(table, name)
        if curlock.strip():
            if float(curlock) < self.daemon_start_time:
                self._log(u"removing stale lock.")
                self._sqlExecute("DELETE FROM " + table + " WHERE name = %s", (name,))
                self.conn.commit()
                locked = False
        else:
            locked = False

        if not locked:
            self._sqlExecute("INSERT INTO " + table + " VALUES ( %s , %s )", (name, time.time()))
            self.conn.commit()
            self._log(u"locked: " + to_unicode(name))

            return "true"

        self._log(u"failed for : " + to_unicode(name))
        return "false"

    def _unlock(self, table, name):
        self._log(name)

        self._checkTable(table)
        self._sqlExecute("DELETE FROM " + table + " WHERE name = %s", (name,))

        self.conn.commit()
        self._log(u"done")
        return "true"

    def _sqlSetMulti(self, table, pre, inp_data):
        self._log(pre)
        self._checkTable(table)
        for name in inp_data:
            if self._sqlGet(table, pre + name).strip():
                self._log(u"Update : " + pre + to_unicode(name))
                self._sqlExecute("UPDATE " + table + " SET data = %s WHERE name = %s",
                                 (inp_data[name], pre + name))
            else:
                self._log(u"Insert : " + pre + to_unicode(name))
                self._sqlExecute("INSERT INTO " + table + " VALUES ( %s , %s )",
                                 (pre + name, inp_data[name]))

        self.conn.commit()
        self._log(u"Done")
        return ""

    def _sqlGetMulti(self, table, pre, items):
        self._log(pre)

        self._checkTable(table)
        ret_val = []
        for name in items:
            self._log(pre + name)
            self._sqlExecute("SELECT data FROM " + table + " WHERE name = %s", (pre + name))

            result = ""
            for row in self.curs:
                self._log(u"Adding : " + str(repr(row[0]))[0:20])
                result = row[0]
            ret_val += [result]

        self._log(u"Returning : " + repr(ret_val))
        return ret_val

    def _sqlSet(self, table, name, data):
        self._log(name + str(repr(data))[0:20])

        self._checkTable(table)
        if self._sqlGet(table, name).strip():
            self._log(u"Update : " + to_unicode(data))
            self._sqlExecute("UPDATE " + table + " SET data = %s WHERE name = %s", (data, name))
        else:
            self._log(u"Insert : " + to_unicode(data))
            self._sqlExecute("INSERT INTO " + table + " VALUES ( %s , %s )", (name, data))

        self.conn.commit()
        self._log(u"Done")
        return ""

    def _sqlDel(self, table, name):
        self._log(name + u" - " + table)

        self._checkTable(table)

        self._sqlExecute("DELETE FROM " + table + " WHERE name LIKE %s", name)
        self.conn.commit()
        self._log(u"done")
        return "true"

    def _sqlGet(self, table, name):
        self._log(name + u" - " + table)

        self._checkTable(table)
        self._sqlExecute("SELECT data FROM " + table + " WHERE name = %s", name)

        for row in self.curs:
            self._log(u"Returning : " + str(repr(row[0]))[0:20])
            return row[0]

        self._log(u"Returning empty")
        return " "

    def _sqlExecute(self, sql, data):
        try:
            self._log(repr(sql) + u" - " + repr(data))
            if self.sql2:
                self.curs.execute(sql, data)
            elif self.sql3:
                sql = sql.replace("%s", "?")
                if isinstance(data, tuple):
                    self.curs.execute(sql, data)
                else:
                    self.curs.execute(sql, (data,))
        except sqlite3.DatabaseError as e:
            if (self.xbmcvfs.exists(self.path) and
                    (str(e).find("file is encrypted") > -1 or str(e).find("not a database") > -1)):
                self._log(u"Deleting broken database file")
                self.xbmcvfs.delete(self.path)
                self._startDB()
            else:
                self._log(u"Database error, but database NOT deleted: " + repr(e))
        except:
            self._log(u"Uncaught exception")

    def _checkTable(self, table):
        try:
            self.curs.execute("create table " + table + " (name text unique, data text)")
            self.conn.commit()
            self._log(u"Created new table")
        except:
            self._log(u"Passed")
            pass

    def _evaluate(self, data):
        try:
            data = eval(data)  # Test json.loads vs eval
            return data
        except:
            self._log(u"Couldn't evaluate message : " + repr(data))
            return ""

    def _generateKey(self, funct, *args):
        name = repr(funct)
        if name.find(" of ") > -1:
            name = name[name.find("method") + 7:name.find(" of ")]
        elif name.find(" at ") > -1:
            name = name[name.find("function") + 9:name.find(" at ")]

        keyhash = hashlib.md5()
        for params in args:
            if isinstance(params, dict):
                for key in sorted(params.keys()):
                    if key not in ["new_results_function"]:
                        val = params[key]
                        if not isinstance(val, str):
                            val = str(val)
                        if isinstance(key, str):
                            key = key.encode('utf-8')
                        if isinstance(val, str):
                            val = val.encode('utf-8')
                        key_val_pair = b"'%s'='%s'" % (key, val)
                        keyhash.update(key_val_pair)
            elif isinstance(params, list):
                hash_list = []
                for el in params:
                    if not isinstance(el, str):
                        el = str(el)
                    if isinstance(el, str):
                        el = el.encode('utf-8')
                    hash_list.append(el)
                keyhash.update(b",".join([b"%s" % el for el in hash_list]))
            else:
                if not isinstance(params, str):
                    params = str(params)
                if isinstance(params, str):
                    params = params.encode('utf-8')
                keyhash.update(params)

        name += "|" + keyhash.hexdigest() + "|"

        self._log(u"Done: " + repr(name))
        return name

    def _getCache(self, name, cache):
        if name in cache:
            if "timeout" not in cache[name]:
                cache[name]["timeout"] = 3600

            if cache[name]["timestamp"] > time.time() - (cache[name]["timeout"]):
                self._log(u"Done, found cache : " + to_unicode(name))
                return cache[name]["res"]
            else:
                self._log(u"Deleting old cache : " + to_unicode(name))
                del (cache[name])

        self._log(u"Done")
        return False

    def _setCache(self, cache, name, ret_val):
        if len(ret_val) > 0:
            if not isinstance(cache, dict):
                cache = {}
            cache[name] = {"timestamp": time.time(),
                           "timeout": self.timeout,
                           "res": ret_val}
            self._log(u"Saving cache: " + name + str(repr(cache[name]["res"]))[0:50])
            self.set("cache" + name, repr(cache))
        self._log(u"Done")
        return ret_val

    # EXTERNAL FUNCTIONS
    soccon = False
    table = False

    def cacheFunction(self, funct=False, *args):
        self._log(u"function : " + repr(funct) + u" - table_name: " + repr(self.table))
        if funct and self.table:
            name = self._generateKey(funct, *args)
            cache = self.get("cache" + name)

            if cache.strip() == "":
                cache = {}
            else:
                cache = self._evaluate(cache)

            ret_val = self._getCache(name, cache)

            if not ret_val:
                self._log(u"Running: " + to_unicode(name))
                ret_val = funct(*args)
                self._setCache(cache, name, ret_val)

            if ret_val:
                self._log(u"Returning result: " + str(len(ret_val)))
                self._log(ret_val)
                return ret_val
            else:
                self._log(u"Returning []. Got result: " + repr(ret_val))
                return []

        self._log(u"Error")
        return []

    def cacheDelete(self, name):
        self._log(name)
        if self._connect() and self.table:
            temp = repr({"action": "del", "table": self.table, "name": "cache" + name})
            self._send(self.soccon, temp)
            res = self._recv(self.soccon)
            self._log(u"GOT " + repr(res))

    def cacheClean(self, empty=False):
        if self.table:
            cache = self.get("cache" + self.table)

            try:
                cache = self._evaluate(cache)
            except:
                self._log(u"Couldn't evaluate message : " + repr(cache))

            self._log(u"Cache : " + repr(cache))
            if cache:
                new_cache = {}
                for item in cache:
                    if (cache[item]["timestamp"] > (time.time() - 3600)) and not empty:
                        new_cache[item] = cache[item]
                    else:
                        self._log(u"Deleting: " + to_unicode(item))

                self.set("cache", repr(new_cache))
                return True

        return False

    def lock(self, name):
        self._log(name)
        self._log(self.table)

        if self._connect() and self.table:
            data = repr({"action": "lock", "table": self.table, "name": name})
            self._send(self.soccon, data)
            res = self._recv(self.soccon)
            if res:
                res = self._evaluate(res)

                if res == "true":
                    self._log(u"Done : " + res.strip())
                    return True

        self._log(u"Failed")
        return False

    def unlock(self, name):
        self._log(name)

        if self._connect() and self.table:
            data = repr({"action": "unlock", "table": self.table, "name": name})
            self._send(self.soccon, data)
            res = self._recv(self.soccon)
            if res:
                res = self._evaluate(res)

                if res == "true":
                    self._log(u"Done: " + res.strip())
                    return True

        self._log(u"Failed")
        return False

    def _connect(self):
        self._sock_init()

        if self._usePosixSockets():
            self.soccon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            self.soccon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        connected = False
        try:
            self.soccon.connect(self.socket)
            connected = True
        except socket.error as e:
            if e.errno in [111]:
                self._log(u"StorageServer isn't running")
            else:
                self._log(u"Exception: " + repr(e))
                self._log(u"Exception: " + repr(self.socket))

        return connected

    def setMulti(self, name, data):
        self._log(name)
        if self._connect() and self.table:
            temp = repr({"action": "set_multi", "table": self.table, "name": name, "data": data})
            res = self._send(self.soccon, temp)
            self._log(u"GOT " + repr(res))

    def getMulti(self, name, items):
        self._log(name)
        if self._connect() and self.table:
            self._send(self.soccon, repr(
                {
                    "action": "get_multi",
                    "table": self.table,
                    "name": name,
                    "items": items
                }
            ))
            self._log(u"Receive")
            res = self._recv(self.soccon)

            self._log(u"res : " + str(len(res)))
            if res:
                res = self._evaluate(res)

                if res == " ":  # We return " " as nothing.
                    return ""
                else:
                    return res

        return ""

    def delete(self, name):
        self._log(name)
        if self._connect() and self.table:
            temp = repr({"action": "del", "table": self.table, "name": name})
            self._send(self.soccon, temp)
            res = self._recv(self.soccon)
            self._log(u"GOT " + repr(res))

    def set(self, name, data):
        self._log(name)
        if self._connect() and self.table:
            temp = repr({"action": "set", "table": self.table, "name": name, "data": data})
            res = self._send(self.soccon, temp)
            self._log(u"GOT " + repr(res))

    def get(self, name):
        self._log(name)
        if self._connect() and self.table:
            self._send(self.soccon, repr({"action": "get", "table": self.table, "name": name}))
            self._log(u"Receive")
            res = self._recv(self.soccon)

            self._log(u"res : " + str(len(res)))
            if res:
                res = self._evaluate(res)
                return res.strip()  # We return " " as nothing. Strip it out.

        return ""

    def setCacheTimeout(self, timeout):
        self.timeout = float(timeout) * 3600

    def _log(self, description):
        if self.dbg:
            try:
                self.xbmc.log(u"[%s] %s : '%s'" %
                              (self.plugin, repr(inspect.stack()[1][3]), description),
                              self.xbmc.LOGDEBUG)
            except:
                self.xbmc.log(u"[%s] %s : '%s'" %
                              (self.plugin, repr(inspect.stack()[1][3]),
                               repr(description)), self.xbmc.LOGDEBUG)


def to_unicode(text):
    if isinstance(text, bytes):
        return text.decode('utf-8')
    return text


# Check if this module should be run in instance mode or not.
__workersByName = {}


def run_async(func, *args, **kwargs):
    from threading import Thread
    worker = Thread(target=func, args=args, kwargs=kwargs)
    __workersByName[worker.getName()] = worker
    worker.start()
    return worker


def checkInstanceMode():
    if hasattr(sys.modules["__main__"], "xbmcaddon"):
        xbmcaddon = sys.modules["__main__"].xbmcaddon
    else:
        import xbmcaddon

    settings = xbmcaddon.Addon(id='script.common.plugin.cache')
    if settings.getSetting("autostart") == "false":
        s = StorageServer(table=False, instance=True)
        xbmc.log("[%s] Module loaded (instance only), starting server ..." % s.plugin,
                 xbmc.LOGDEBUG)
        run_async(s.run)
        return True
    else:
        return False


_ = checkInstanceMode()

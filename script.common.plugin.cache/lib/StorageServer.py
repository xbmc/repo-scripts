'''
    Cache service for XBMC
    Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

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
    Version 0.8
'''

import os, sys, socket, time, hashlib, inspect, platform

try: import sqlite
except: pass
try: import sqlite3
except: pass

class StorageServer():
	def __init__(self):
		self.plugin = "StorageClient-0.8"
		self.instance = False
		self.die = False

                try:
                        self.dbglevel = sys.modules[ "__main__" ].dbglevel
                except:
			self.dbglevel = 3

		try:
			self.dbg = sys.modules[ "__main__" ].dbg
		except:
	                self.dbg = True
	
		self.xbmc = sys.modules["__main__"].xbmc
		self.xbmcvfs = sys.modules["__main__"].xbmcvfs
		self.path = os.path.join( self.xbmc.translatePath( "special://database" ), 'commoncache.db')
		self.socket = ""
		self.clientscoket = False
		self.sql2 = False
		self.sql3 = False
		self.abortRequested = False
		self.daemon_start_time = time.time()
		self.idle = 3
		self.platform = sys.platform
		self.modules = sys.modules

	def startDB(self):
		try:
			if "sqlite3" in self.modules:
				self.sql3 = True
				self.log("sql3", 2)
				self.conn = sqlite3.connect(self.path, check_same_thread=False)
			elif "sqlite" in self.modules:
				self.sql2 = True
				self.log("sql2", 2)
				self.conn = sqlite.connect(self.path)
			else:
				self.log("Error, no sql found", 2)
				return False

			self.curs = self.conn.cursor()
			return True
		except sqlite.Error, e:
			self.log("Exception: " + repr(e))
			self.xbmcvfs.delete(self.path)
			return False	

	def aborting(self):
		if self.instance and self.die:
			return True
		return self.xbmc.abortRequested

	def sock_init(self, check_stale = False):
		if not self.socket:
			if self.platform == "win32":
				port = 59994
				self.socket = (socket.gethostname(), port)
			else:
				self.socket = os.path.join( self.xbmc.translatePath( "special://temp" ), 'commoncache.socket')
				if self.xbmcvfs.exists(self.socket) and check_stale:
					self.log("Deleting stale socket file")
					self.xbmcvfs.delete(self.socket)

	def run(self):
		self.plugin = "StorageServer"
		self.log("Storage Server starting " + self.path)
		self.sock_init(True)

		if not self.startDB():
			self.startDB()

		if self.platform == "win32":
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		else:
			sock = socket.socket(socket.AF_UNIX)

		sock.bind(self.socket)
		sock.listen(1)
		sock.setblocking(0)
		
		idle_since = time.time()
		waiting = 0
		while not self.aborting():
			if waiting == 0 :
				self.log("accepting", 2)
				waiting = 1
			try:
				(self.clientsocket, address) = sock.accept()
				if waiting == 2:
					self.log("Waking up, slept for %s seconds." % int(time.time() - idle_since) )
				waiting = 0
			except socket.error, e:
				if e.errno == 11 or e.errno == 10035 or e.errno == 35:
					# There has to be a better way to accomplish this.
					if idle_since + self.idle < time.time():
						if self.instance:
							self.die = True
						if waiting == 1:
							self.log("Idle for %s seconds. Going to sleep. zzzzzzzz " % self.idle)
						time.sleep(0.5)
						waiting = 2
					continue
				self.log("EXCEPTION : " + repr(e))
			except:				
				print "PASS"
				pass

			if waiting: 
				self.log("Continue : " + repr(waiting), 2)
				continue

			self.log("accepted", 2)
			data = self.recv(self.clientsocket)
			self.log("recieved data: " + data, 4)
			try:
				data = eval(data)
			except:
				self.log("Couldn't evaluate message : " + repr(data))
				data = {"action": "stop"}

			self.log("Got data: " + str(len(data)) + " - " + str(repr(data))[0:50], 1)
			
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
				self.log("Got response: " + str(len(res))  + " - " + str(repr(res))[0:50], 1)
				self.send(self.clientsocket, repr(res))

			idle_since = time.time()
			self.log("Done", 1)

		self.log("Closing down")
		#self.conn.close()
		if not self.platform == "win32":
			if self.xbmcvfs.exists(self.socket):
				self.log("Deleting socket file")
				self.xbmcvfs.delete(self.socket)	
		self.log("Closed down")

	def recv(self, sock):
		data = "   "
		idle = True
		temp = ""
		self.log("", 2)
		i = 0
		start = time.time()
		while data[len(data)-2:] != "\r\n" or not idle:
			try:
				if idle:
					recv_buffer = sock.recv(4096)
					idle = False
					i += 1
					self.log("got data  : " + str(i) + " - " + repr(idle) + " - " + str(len(data)) + " + " + str(len(recv_buffer)) + " | " + repr(recv_buffer)[len(recv_buffer) -5:], 3)
					data += recv_buffer
					start = time.time()
				elif not idle:
					if data[len(data)-2:] == "\r\n":
						sock.send("COMPLETE\r\n" + ( " " * ( 15 - len("COMPLETE\r\n") ) ) )
						idle = True
						self.log("sent COMPLETE " + str(i), 2)
					elif len(recv_buffer) > 0:
						sock.send("ACK\r\n" + ( " " * ( 15 - len("ACK\r\n") )) )
						idle = True
						self.log("sent ACK " + str(i), 2)
					recv_buffer = ""
					self.log("status " + repr( not idle) + " - " + repr(data[len(data)-2:] != "\r\n"), 3)
					
			except socket.error, e:
				if not e.errno in [ 10035, 35 ]:
					self.log("Except error " + repr(e))

				if e.errno in [ 22 ]: # We can't fix this.
					return ""

				if start + 10 < time.time():
					self.log("over time", 2)
					break
		self.log("done", 2)
		return data.strip()

	def send(self, sock, data):
		idle = True
		status = ""
		self.log(str(len(data)) + " - " + repr(data)[0:20], 2)
		i = 0
		start = time.time()
		while len(data) > 0 or not idle:
			send_buffer = " "
			try:
				if idle:
					if len(data) > 4096:
						send_buffer = data[:4096]
					else:
						send_buffer = data + "\r\n"

					result = sock.send(send_buffer)
					i += 1
					idle = False
					start = time.time()
				elif not idle:
					status = ""
					while status.find("COMPLETE\r\n") == -1 and status.find("ACK\r\n") == -1:
						status = sock.recv(15)
						i -= 1

					idle = True
					if len(data) > 4096:
						data = data[4096:]
					else:
						data = ""

					self.log("Got response " + str(i) + " - " + str(result) + " == " + str(len(send_buffer)) + " | " + str(len(data)) + " - " + repr(send_buffer)[len(send_buffer)-5:], 3)

			except socket.error, e:
				self.log("Except error " + repr(e))
				if e.errno != 10035 and e.errno != 35 and e.errno != 107 and e.errno != 32:
					self.log("Except error " + repr(e))
				if start + 10 < time.time():
					self.log("Over time", 2)
					break;
		self.log("Done", 2) 
		return status.find("COMPLETE\r\n") > -1

	def _lock(self, table, name): # This is NOT atomic
		self.log(name, 1)
		locked = True
		curlock = self._sqlGet(table, name)
		if curlock.strip():
			if float(curlock) < self.daemon_start_time:
				self.log("removing stale lock.")
				self._sqlExecute("DELETE FROM " + table + " WHERE name = %s", ( name, ) )
				self.conn.commit()
				locked = False
		else:
			locked = False

		if not locked:
			self._sqlExecute("INSERT INTO " + table + " VALUES ( %s , %s )", ( name, time.time()) )
			self.conn.commit()
			self.log("locked: " + name, 1)

			return "true"

		self.log("failed for : " + name, 1)
		return "false"

	def _unlock(self, table, name):
		self.log(name, 1)

		self.checkTable(table)
		self._sqlExecute("DELETE FROM " + table + " WHERE name = %s", ( name, ) )
		self.conn.commit()
		self.log("done", 1)
		return "true"


	def _sqlSetMulti(self, table, pre, inp_data):
		self.checkTable(table)
		for name in inp_data:
			if self._sqlGet(table, pre + name).strip():
				self.log("Update : " + pre + name, 2)
				self._sqlExecute("UPDATE " + table + " SET data = %s WHERE name = %s", ( inp_data[name], pre + name ))
			else:
				self.log("Insert  " + pre + name, 2)
				self._sqlExecute("INSERT INTO " + table + " VALUES ( %s , %s )", ( pre + name, inp_data[name]) )

		self.conn.commit()
		self.log("Done", 1)
		return ""

	def _sqlGetMulti(self, table, pre, items):
		self.log(pre, 1)

		self.checkTable(table)
		ret_val = []
		for name in items:
			self.log(pre + name, 2)
			self._sqlExecute("SELECT data FROM " + table + " WHERE name = %s", ( pre + name))

			result = ""
			for row in self.curs:
				self.log("Adding : " + str(repr(row[0]))[0:20], 3)
				result = row[0]
			ret_val += [result]

		self.log("Returning : " + repr(ret_val), 2)
		return ret_val

	def _sqlSet(self, table, name, data):
		self.log(name + str(repr(data))[0:20], 2)

		self.checkTable(table)
		if self._sqlGet(table, name).strip():
			self.log("Update : " + data, 3)
			self._sqlExecute("UPDATE " + table + " SET data = %s WHERE name = %s", ( data, name ) )
		else:
			self.log("Insert : " + data , 3)
			self._sqlExecute("INSERT INTO " + table + " VALUES ( %s , %s )", ( name, data) )
		self.conn.commit()

		self.log("Done", 2)
		return ""

	def _sqlDel(self, table, name):
		self.log(name + " - " + table, 1)

		self.checkTable(table)

		self._sqlExecute("DELETE FROM " + table + " WHERE name = %s", name)
		self.conn.commit()
		self.log("done", 1)
		return "true"

	def _sqlGet(self, table, name):
		self.log(name + " - " + table, 2)

		self.checkTable(table)

		self._sqlExecute("SELECT data FROM " + table + " WHERE name = %s", name )

		for row in self.curs:
			self.log("Returning : " + str(repr(row[0]))[0:20], 2)
			return row[0]

		self.log("Returning empty", 2)
		return " "

	def _sqlExecute(self, sql, data):
		try:
			if self.sql2:
				self.curs.execute(sql, data)
			elif self.sql3:
				sql = sql.replace("%s", "?")
				if isinstance(data, tuple):
					self.curs.execute(sql, data)
				else:
					self.curs.execute(sql, (data, ))
		except sqlite3.DatabaseError, e:
			if self.xbmcvfs.exists(self.path) and ( str(e).find("file is encrypted") > -1 or str(e).find("not a database") > -1) :
				self.log("Deleting broken database file")
				self.xbmcvfs.delete(self.path)
				self.startDB()
			else:
				self.log(repr(e))
		except:
			self.log("Uncaught exception")

	def checkTable(self, table):
		try:
			self.curs.execute("create table " + table + " (name text unique, data text)")
			self.conn.commit()
			self.log("Created new table")
		except:
			self.log("Passed", 2)

	def _evaluate(self, data):
		try:
			data = eval(data)
			return data
		except:
			self.log("Couldn't evaluate message : " + repr(data))
			return ""

### EXTERNAL FUNCTIONS ###
	soccon = False
	table_name = False

	def cacheFunction(self, funct = False, *args):
		self.log("function : " + repr(funct) + " - table_name: " + repr(self.table_name))
		if funct and self.table_name:
			name = repr(funct)
			if name.find(" of ") > -1:
				name = name[name.find("method") + 7 :name.find(" of ")]
			elif name.find(" at ") > -1:
				name = name[name.find("function") + 9 :name.find(" at ")]

			self.log(name  + " - " + str(repr(args))[0:50], 1)

			ret_val = False

			# Build unique name
			keyhash = hashlib.md5()
			for params in args:
				if isinstance(params, dict):
					for key in sorted(params.iterkeys()):
						if key not in [ "new_results_function" ]:
							keyhash.update("'%s'='%s'" % (key, params[key]))
				elif isinstance(params, list):
					keyhash.update(",".join(["%s" % el for el in params]))
				else:
					keyhash.update(params)

			name += "|" + keyhash.hexdigest() + "|"

			cache = self.get("cache" + name)

			if cache.strip() == "":
				cache = {}
			else:
				cache = self._evaluate(cache)

			if name in cache:
				self.log("Found cache : " + name)
				if cache[name]["timestamp"] > time.time() - (3600 * 24):
					ret_val = cache[name]["res"]
				else:
					self.log("Deleting old cache", 1)
					del(cache[name])

			if not ret_val: 
				self.log("Running function " + str(len(args)) + " - " + str(repr(args))[0:50])
				ret_val = funct(*args)
				if ret_val[1] == 200:
					cache[name] = { "timestamp": time.time(),
							"res": ret_val}
					self.log("Saving cache: " + name  + str(repr(cache[name]["res"]))[0:50], 1)
					self.set("cache" + name, repr(cache))

			if ret_val:
				self.log("Returning " + name)
				self.log(ret_val, 4)
				return ret_val

		self.log("Error")
		return ( "", 500 )

	def deleteCache(self, name):
		self.log(name, 1)
		if self.connect() and self.table_name:
			temp = repr({ "action": "del", "table": self.table_name, "name": "cache" + name})
			self.send(self.soccon, temp)
			res = self.recv(self.soccon)
			self.log("GOT " + repr(res), 2)

	def cleanCache(self, empty = False):
		self.log("")
		if self.table_name:
			cache = self.get("cache" + self.table_name)

			try:
				cache = eval(cache)
			except:
				self.log("Couldn't evaluate message : " + repr(cache))

			self.log("Cache : " + repr(cache), 5)
			if cache:
				new_cache = {}
				for item in cache:
					if ( cache[item]["timestamp"] > time.time() - (3600 * 24) ) and not empty:
						new_cache[item] = cache[item]
					else:
						self.log("Deleting: " + item)
				self.set("cache", repr(new_cache))
				return True
		return False

	def lock(self, name):
		self.log(name, 1)

		if self.connect() and self.table_name:
			data = repr({ "action": "lock", "table": self.table_name, "name": name})
			self.send(self.soccon, data)
			res = self.recv(self.soccon)
			if res:
				res = self._evaluate(res)

				if res == "true":
					self.log("Done : " + res.strip(), 1)
					return True

		self.log("Failed", 1)
		return False

	def unlock(self, name):
		self.log(name, 1)

		if self.connect() and self.table_name:
			data = repr({ "action": "unlock", "table": self.table_name, "name": name})
			self.send(self.soccon, data)
			res = self.recv(self.soccon)
			if res:
				res = self._evaluate(res)

				if res == "true":
					self.log("Done: " + res.strip(), 1)
					return True

		self.log("Failed", 1)
		return False

	def connect(self):
		self.log("", 1)
		self.sock_init()
		if self.platform == "win32":
			self.soccon = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		else:
			self.soccon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

		start = time.time()
		connected = False
		try:
			self.soccon.connect(self.socket)
			connected = True
		except socket.error, e:
			if e.errno in [ 111 ]:
				self.log("StorageServer isn't running")
			else:
				self.log("Exception: " + repr(e))
				self.log("Exception: " + repr(self.socket))

		return connected

	def setMulti(self, name, data):
		self.log(name, 1)
		if self.connect() and self.table_name:
			temp = repr({ "action": "set_multi", "table": self.table_name, "name": name, "data": data})
			res = self.send(self.soccon, temp)
			self.log("GOT " + repr(res), 2)

	def getMulti(self, name, items):
		self.log(name, 1)
		if self.connect() and self.table_name:
			self.send(self.soccon, repr({ "action": "get_multi", "table": self.table_name, "name": name, "items": items}))
			self.log("Recieve", 2)
			res = self.recv(self.soccon)

			self.log("res : " + str(len(res)), 2)
			if res:
				res = self._evaluate(res)

				if res == " ":# We return " " as nothing.
					return ""
				else:
					return res

		return ""

	def set(self, name, data):
		self.log(name, 1)
		if self.connect() and self.table_name:
			temp = repr({ "action": "set", "table": self.table_name, "name": name, "data": data})
			res = self.send(self.soccon, temp)
			self.log("GOT " + repr(res), 2)

	def get(self, name):
		self.log(name, 1)
		if self.connect() and self.table_name:
			self.send(self.soccon, repr({ "action": "get", "table": self.table_name, "name": name}))
			self.log("Recieve", 2)
			res = self.recv(self.soccon)

			self.log("res : " + str(len(res)), 2)
			if res:
				res = self._evaluate(res)

				return res.strip() # We return " " as nothing. Strip it out.

		return ""

	def log(self, description, level = 0):
		if self.dbg and self.dbglevel > level:
			self.xbmc.log("[%s] %s : '%s'" % (self.plugin, inspect.stack()[1][3], description), self.xbmc.LOGNOTICE)


# Check if this module should be run in instance mode or not.
def checkInstanceMode():
        if sys.modules["__main__"].xbmc.getCondVisibility('system.platform.ios'):
		__workersByName = {}
		def run_async(func, *args, **kwargs):
			from threading import Thread
			worker = Thread(target = func, args = args, kwargs = kwargs)
			__workersByName[worker.getName()] = worker
			worker.start()
			return worker

		s = StorageServer()
		s.instance = True
		print " StorageServer Module loaded RUN(instance only)"

		print s.plugin + " Starting server"
		
		run_async(s.run)
		return True
	else:
		return False

checkInstanceMode()

import rmpd,select,threading,traceback,xbmpc,time,Queue

# polling MPD Client
class PMPDClient(object):
	def __init__(self,poll_time=False):
		print self.__class__.__name__
		self.client = rmpd.RMPDClient()
		self.poller = rmpd.RMPDClient()
		self.time_poller = rmpd.RMPDClient()
		self.callback = None
		self.time_callback = None
		self.thread = threading.Thread(target=self._poll)
		self.thread.setDaemon(True)
		self._permitted_commands = []
		self.time_thread = None
		self.time_event = None
		if poll_time:
			self.time_thread = threading.Thread(target=self._poll_time)
			self.time_thread.setDaemon(True)
			self.time_event = threading.Event()
		
	def register_callback(self,callback):
		self.callback = callback
	def register_time_callback(self,callback):
		self.time_callback=callback;
	# need to call try_command before passing any commands to list!	
	def command_list_ok_begin(self):
		self.client.command_list_ok_begin()
	
	def command_list_end(self):
		return self.client.command_list_end()

	def try_command(self,command):
		if not command in self._permitted_commands:
			raise xbmpc.CommandError('No Permission for :'+command)
	def __getattr__(self,attr):
		if not attr in self._permitted_commands:
			raise xbmpc.CommandError('No Permission for :'+attr)
		return self.client.__getattr__(attr)
		
	def connect(self,host,port,password=None):
		self.client.connect(host,port)		
		self.poller.connect(host,port)
		if not password==None:
			self.poller.password(password)
			self.client.password(password)
		self._permitted_commands = self.client.commands()
		self.thread.start()
		if not self.time_thread == None:
			self.time_poller.connect(host,port)
			self.time_thread.start()
		
	def disconnect(self):
		print 'disconnecting'
		self.callback = None
		try:
			self.client.close()
		except:
			pass
		try:
			self.client.disconnect()
		except:
			pass
		try:
			self.poller.noidle()
		except:
			pass
		try:
			self.poller.close()
		except:
			pass
		try:
			self.poller.disconnect()
		except:
			pass

		print 'waiting for poller thread'
		if self.thread.isAlive():
			self.thread.join()
		print 'done'
		if not self.time_thread == None:
			print 'disconnecting time poller'
			try:
				self.time_poller.noidle()
			except:
				pass
			try:
				self.time_poller.close()
			except:
				pass
			try:
				self.time_poller.disconnect()
			except:
				pass
			try:
				print 'waiting for time poller thread'
				self.time_event.set()
				if self.time_thread.isAlive():
					self.time_thread.join(3)
					self.time_event=None
				print 'done'
			except:
				traceback.print_exc()
		print 'client disconnected'
		
	def _poll_time(self):
		print 'Starting time poller thread'
		while 1:
			try:
				status = self.time_poller.status()
				while not status['state'] == 'play':
					self.time_poller.send_idle()
					select.select([self.time_poller],[],[],1)
					changes = self.time_poller.fetch_idle()
					if changes:
						if 'player' in changes:
							status = self.time_poller.status()
				self.time_callback(self.time_poller,status)
				self.time_event.wait(0.9)
				if self.time_event.isSet():
#					print 'poller exited on event'
					break;
			except:
#				print "time poller error"
#				traceback.print_exc()
				self.time_event.set()
				return

	def _poll(self):
		while 1:			
			try:
#				print 'polling IDLE'
				self.poller.send_idle()
				select.select([self.poller],[],[],1)
				changes = self.poller.fetch_idle()
			except:
#				print "poller error"
#				traceback.print_exc()
				return
			try:
				if not self.callback == None and not changes == None:
					self.callback(self.poller,changes)
			except:
#				print "callback error"
#				traceback.print_exc()
				return

# polling MPD Client - combatible with mopidy
class MopidyMPDClient(object):
	def __init__(self,poll_time=False):
		print self.__class__.__name__
		self.client = rmpd.RMPDClient()
		self.poller = rmpd.RMPDClient()
		self.time_poller = rmpd.RMPDClient()
		self.callback = None
		self.thread = threading.Thread(target=self._poll)
		self.thread.setDaemon(True)
		self.event = threading.Event()
		self.idle_queue= Queue.Queue()
		self.recording = False
		self.recored = []
		self.time_callback = None
		self._permitted_commands = []
		self.time_thread = None
		self.time_event = None
		if poll_time:
			self.time_thread = threading.Thread(target=self._poll_time)
			self.time_thread.setDaemon(True)
			self.time_event = threading.Event()
		feeder = threading.Thread(target=self._feed_idle)
		feeder.setDaemon(True)
		feeder.start()

	def register_callback(self,callback):
		self.callback = callback
	def register_time_callback(self,callback):
		self.time_callback=callback;
	# need to call try_command before passing any commands to list!
	def command_list_ok_begin(self):
		self.recording = True
		self.recorded_command_list = []
		self.client.command_list_ok_begin()

	def command_list_end(self):
		self.recording = False
		records = list(set(self.recorded_command_list))
		for record in records:
			self._add_for_callback(record)
		return self.client.command_list_end()

	def try_command(self,command):
		if not command in self._permitted_commands:
			raise xbmpc.CommandError('No Permission for :'+command)
	def __getattr__(self,attr):
		if not attr in self._permitted_commands:
			raise xbmpc.CommandError('No Permission for :'+attr)
		if self.recording:
			self.recorded_command_list.append(attr)
		else:
			self._add_for_callback(attr)
		return self.client.__getattr__(attr)

	def _add_for_callback(self,command):
		if command in ['play','stop','seekid','next','previous','pause']:
			self.idle_queue.put('player')
		elif command in ['consume','repeat','random']:
			self.idle_queue.put('options')
		elif command in ['setvol']:
			self.idle_queue.put('mixer')
		elif command in ['clear','add','load','deleteid']:
			self.idle_queue.put('playlist')
		elif command in ['rm','save']:
			self.idle_queue.put('stored_playlist')

	def connect(self,host,port,password=None):
		self.client.connect(host,port)
		self.poller.connect(host,port)
		if not password==None:
			self.client.password(password)
			self.poller.password(password)
		self._permitted_commands = self.client.commands()
		self.thread.start()
		if not self.time_thread == None:
			self.time_poller.connect(host,port)
			self.time_thread.start()

	def disconnect(self):
		print 'disconnecting'
		self.callback = None
		try:
			self.client.close()
		except:
			pass
		try:
			self.client.disconnect()
		except:
			pass
		try:
			self.poller.close()
		except:
			pass
		try:
			self.poller.disconnect()
		except:
			pass
		try:
			print 'waiting for poller thread'
			if self.thread.isAlive():
				self.event.set()
				self.idle_queue.put('exit')
				self.thread.join(3)
			print 'done'
		except:
			traceback.print_exc()

		if not self.time_thread == None:
			print 'disconnecting time poller'
			try:
				self.time_poller.close()
			except:
				pass
			try:
				self.time_poller.disconnect()
			except:
				pass
			try:
				print 'waiting for time poller thread'
				if self.time_thread.isAlive():
					self.time_event.set()
					self.time_thread.join(3)
					self.time_event=None
				print 'done'
			except:
				traceback.print_exc()
		print 'client disconnected'

	def _poll_time(self):
		print 'Starting time poller thread'
		while 1:
			try:
				status = self.time_poller.status()
				if not status['state'] == 'play':
					self.time_event.wait(5)
				else:
					self.time_callback(self.time_poller,status)
					self.time_event.wait(0.9)
				if self.time_event.isSet():
#					print 'poller exited on event'
					break;
			except:
#				print "time poller error"
#				traceback.print_exc()
				self.time_event.set()
				return
	def _feed_idle(self):
		self.event.wait(5)
		if self.event.isSet():
			return
		state = ''
		songid = ''
		while 1:
			status = self.poller.status()
			if not 'state' in status:
				status['state']=''
			if not 'songid' in status:
				status['songid'] = ''
			if not state == status['state']:
				self._add_for_callback('play')
				state = status['state']
				continue
			if not songid == status['songid']:
				self._add_for_callback('play')
				songid = status['songid']
				continue
			self.event.wait(5)
			if self.event.isSet():
				break
	def _poll(self):
		print 'Starting poller thread'
		while 1:
			try:
				item = 	self.idle_queue.get()
				self.event.wait(0.2)
				self.callback(self.poller,[item])
				if self.event.isSet():
#					print 'poller exited on event'
					break;
			except:
#				print "Poller error"
#				traceback.print_exc()
				return
				

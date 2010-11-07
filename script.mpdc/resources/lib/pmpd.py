import rmpd,select,threading,traceback,mpd,time

# polling MPD Client
class PMPDClient(object):
	def __init__(self,poll_time=False):
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
			raise mpd.CommandError('No Permission for :'+command)
	def __getattr__(self,attr):
		if not attr in self._permitted_commands:
			raise mpd.CommandError('No Permission for :'+attr)
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
			print 'waiting for time poller thread'
			if not self.time_event and self.time_thread.isAlive():
				return
			self.time_event.set()
			self.time_thread.join()
			self.time_event=None
			print 'done'
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
				self.time_event = None
				return

	def _poll(self):
		while 1:			
			try:
				self.poller.send_idle()
				select.select([self.poller],[],[],1)
				changes = self.poller.fetch_idle()
			except:
#				print "poller error"
#				traceback.print_exc()
				return
			try:
				if not self.callback == None:
					self.callback(self.poller,changes)
			except:
#				print "callback error"
#				traceback.print_exc()
				return
				

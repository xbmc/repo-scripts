import rmpd,select,threading,traceback,mpd

# polling MPD Client
class PMPDClient(object):
	def __init__(self):
		self.client = rmpd.RMPDClient()
		self.poller = rmpd.RMPDClient()
		self.callback = None
		self.thread = threading.Thread(target=self._poll)
		self.thread.setDaemon(True)
		self._permitted_commands = []
		
	def register_callback(self,callback):
		self.callback = callback
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
		print 'client disconnected'
		
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
				

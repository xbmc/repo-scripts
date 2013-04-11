import xbmc, radiovis.stomp, re, radiovis.httpcomm, pyradiodns.rdns


#get actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/Key.h




class ServiceRecord():
	_port = "61613"
	_url = "127.0.0.1"
	
	def __init__(self, url, port):
		self._port = port
		self._url = url
	

class StompListener(radiovis.stomp.ConnectionListener):

	_connection = None
	_curImg = None
	_topic = ""
	_text_regex = re.compile(r"""
								  ^TEXT   # "TEXT" at start of line
								  \s+     # some whitespace
								  (.*)    # the text message
								  """,
								  re.VERBOSE | re.IGNORECASE)

	_show_regex = re.compile(r"""
								  ^SHOW   # "SHOW" at start of line
								  \s+     # some whitespace
								  (.*)    # the URL of the image to show
								  """,
								  re.VERBOSE | re.IGNORECASE)
	
	def __init__(self, connection, topic):
		radiovis.stomp.ConnectionListener.__init__(self)
		self._connection = connection
		self._topic = topic

	def on_connecting(self, host_and_port):
		self._connection.connect(wait = True)
		

	def on_connected(self, headers, body):
		self._connection.subscribe(destination = "/topic/"+self._topic+"/image", ack = 'auto')
		self._connection.subscribe(destination = "/topic/"+self._topic+"/text", ack = 'auto')
		

	def on_disconnected(self):
		#self._textLabel.setLabel("Lost Connection")
		pass
		
	def on_message(self, headers, body):
		lines = body.split('\n')

		for line in lines:
			# Remove leading and trailing whitespace. 
			line = line.strip()
			
			# Check for TEXT message.
			match = self._text_regex.match(line)
			
			if match:
				# TODO: text should be no more than 128 characters.
				text = match.group(1)
				if(self._curImg is not None):
					xbmc.executebuiltin('XBMC.Notification("'+text+'","", 999999, "'+self._curImg+'")')

				else:
					xbmc.executebuiltin('XBMC.Notification("'+text+'","", 999999)')

			else:
				# Check for SHOW message.
				match = self._show_regex.match(line)
				
				if match:
					url = match.group(1)
                    
					if 'link' in headers:
						link = headers['link']
					else:
						link = None
                    
					if 'trigger-time' in headers:
						# TODO: Parse date_time and construct a datetime object.
						date_time = headers['trigger-time']
					else:
						date_time = None
					
					self._curImg = url

				else:
					pass
		
	def on_error(self, headers, body):
		self._textLabel.setLabel("Error: " + body)
		
class RadioVISPlayer(xbmc.Player):

	_stompConnection = None
	_httpComm = radiovis.httpcomm.HTTPComm()

	_services = []
	_active = False
	
	def __init__(self, *args):

		pass
				
	def onPlayBackStarted( self ):
		self.stopRadioVis()
		self.initRadioVis(str(xbmc.Player().getPlayingFile()))

	def onPlayBackEnded( self ):
		self.stopRadioVis()

	def onPlayBackStopped( self ):
		self.stopRadioVis()

	def initRadioVis(self, url):
		if(self._active == False):
			self._active = True
			headers = self._httpComm.getHeaders(url)
			if(headers is not False):
				icy_url = headers.get( "icy-url" )	

				if(icy_url is not None):
					
					serviceLookUp = pyradiodns.rdns.RadioDNS()
					self._services = serviceLookUp.lookup_ip(icy_url, '')
					topic = 'id/'+icy_url.replace("http://", "")
					xbmc.executebuiltin('XBMC.Notification("TOPIC","'+topic+'")')


				try:
					self._services = self._services['applications']['radiovis']['servers']
					if(self._services is not None and self._services is not False and len(self._services) > 0):
						self._stompConnection = radiovis.stomp.Connection([(self._services[0]["target"], self._services[0]["port"])])				
						self._stompConnection.add_listener(StompListener(self._stompConnection, topic))
						self._stompConnection.start()

				except Exception, e:
					pass
					#xbmc.executebuiltin('XBMC.Notification("Station has no RadioVIS support","")')
		
		
	def stopRadioVis(self):
		self._active = False
		if(self._stompConnection is not None):
			self._stompConnection.stop()
			

player = RadioVISPlayer()


while (not xbmc.abortRequested):
	xbmc.sleep(100)	
	

del mydisplay
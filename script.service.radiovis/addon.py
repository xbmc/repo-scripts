import os, time, xbmc, xbmcaddon, radiovis.stomp, re, radiovis.httpcomm, pyradiodns.rdns


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
		xbmc.log('Stomp initialized on topic ' + topic)

	def on_connecting(self, host_and_port):
		xbmc.log('Stomp connecting to '+str(host_and_port)+' ...')
		self._connection.connect(wait = True)
		

	def on_connected(self, headers, body):
		xbmc.log('Stomp connected!  ('+body+')')
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
		xbmc.log('Stomp Error: '+body)
		
class RadioVISPlayer(xbmc.Player):
	#addonId = 'script.service.radiovis'
	_addon = xbmcaddon.Addon()
	_addonProfilePath = xbmc.translatePath( _addon.getAddonInfo('profile') ).decode('utf-8') # Dir where plugin settings and cache will be stored

	_checkinFile	= _addonProfilePath + "cache_lastcheckin.dat"

	_stompConnection = None
	_httpComm = radiovis.httpcomm.HTTPComm()

	_services = []
	_active = False
	
	def __init__(self, *args):
		if self.checkFileTime(self._checkinFile, self._addonProfilePath, 86400) == True :
			open(self._checkinFile, "w")
			self._httpComm.get('http://stats.backend-systems.net/xbmc/?plugin='+ self._addon.getAddonInfo('id') + '&version=' + self._addon.getAddonInfo('version'))
		pass
			

	def checkFileTime( self, tmpfile, cachedir, timesince ) :
		#xbmc.executebuiltin('XBMC.Notification("Checking filetime","")')
		if not os.path.exists( cachedir ) :
			os.makedirs( cachedir )
			return False
		# If file exists, check timestamp
		if os.path.exists( tmpfile ) :
			if os.path.getmtime( tmpfile ) > ( time.time() - timesince ) :
				xbmc.log( 'It has not been ' + str( timesince/60 ) + ' minutes since ' + tmpfile + ' was last updated', xbmc.LOGNOTICE )
				return False
			else :
				xbmc.log( 'The cachefile ' + tmpfile + ' + has expired', xbmc.LOGNOTICE )
				return True
		# If file does not exist, return true so the file will be created by scraping the page
		else :
			xbmc.log( 'The cachefile ' + tmpfile + ' does not exist', xbmc.LOGNOTICE )
			return True			
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
					fqdn = icy_url.replace("http://", "");
					fqdn = fqdn.replace("www.", "");
					fqdn = fqdn.split("/")[0];
					xbmc.log('ICY-URL: '+icy_url)
					xbmc.log('FQDN: '+fqdn)
					self._services = serviceLookUp.lookup_ip(fqdn, '')
					topic = 'id/'+icy_url.replace("http://", "")
					
					

				try:
					xbmc.log('Found service records')
					self._services = self._services['applications']['radiovis']['servers']
					if(self._services is not None and self._services is not False and len(self._services) > 0):
						xbmc.executebuiltin('XBMC.Notification("Connecting to RadioVIS:","Topic: '+topic+'")')
						self._stompConnection = radiovis.stomp.Connection([(self._services[0]["target"], self._services[0]["port"])])				
						self._stompConnection.add_listener(StompListener(self._stompConnection, topic))
						self._stompConnection.start()

				except Exception, e:
					xbmc.log('Error connecting to stations stomp server (no support?)');
					pass
					#xbmc.executebuiltin('XBMC.Notification("Station has no RadioVIS support","")')
		
		
	def stopRadioVis(self):
		self._active = False
		if(self._stompConnection is not None):
			try:
				self._stompConnection.stop()
			except Exception, e:
				xbmc.log('Could not stop stomp connection!')
				pass
			

player = RadioVISPlayer()


while (not xbmc.abortRequested):
	xbmc.sleep(100)	
	


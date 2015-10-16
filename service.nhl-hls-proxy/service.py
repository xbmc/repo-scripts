import cherrypy
import m3u8
import requests
import urllib
import urlparse
import xbmc
import xbmcaddon
import StringIO
from cherrypy.lib import file_generator
from datetime import datetime, timedelta
from dateutil import parser, tz

__addon__       = xbmcaddon.Addon()
__language__    = __addon__.getLocalizedString
__socket_host__ = __addon__.getSetting('hls_listen_host')
__socket_port__ = int(__addon__.getSetting('hls_listen_port'))

def rewind_playlist(m3u8_obj, start_at, segment_base_uri, key_headers={}):
	if m3u8_obj.is_variant:
		return None
	if m3u8_obj.media_sequence is None and m3u8_obj.is_endlist:
		# FIXME: This will attempt to play the file via the proxy, which will
		# fail due to the relative URLs.
		return m3u8_obj

	# Parse out the important pieces of the segment URI.
	base_segment = m3u8_obj.segments[0].uri
	segment_name_prefix = base_segment[:base_segment.rfind('_') + 1]
	segment_name_suffix = base_segment[base_segment.rfind('.'):]
	segment_time = base_segment[len(segment_name_prefix):len(base_segment) - len(segment_name_suffix)]
	segment_time = parser.parse(segment_time).replace(tzinfo=tz.tzutc())
	# Rewinding is easy. Going forward in time is, sadly, not possible.
	if start_at >= segment_time:
		return m3u8_obj
	start_at -= timedelta(seconds=start_at.second % m3u8_obj.target_duration)

	# Rewind the playlist to the specified time.
	segment_duration = timedelta(seconds=m3u8_obj.target_duration)
	playlist_beginning = segment_time - (segment_duration * m3u8_obj.media_sequence)
	if start_at < playlist_beginning:
		start_at = playlist_beginning
	time_difference = segment_time - start_at
	time_difference = time_difference.seconds + time_difference.days * 24 * 3600
	segment_time = start_at

	# Start building our new playlist.
	extra_headers = ''
	if len(key_headers) > 0:
		extra_headers = '&headers=' + urllib.quote(urllib.urlencode(key_headers))
	playlist = m3u8.M3U8()
	playlist.target_duration = m3u8_obj.target_duration
	playlist.media_sequence = int(m3u8_obj.media_sequence - (time_difference / m3u8_obj.target_duration))
	playlist.is_endlist = True

	# Stream encryption key parameters.
	key = None
	if m3u8_obj.key is not None:
		key_base_uri = 'http://%s:%d/key?url=' % (__socket_host__, __socket_port__)
		key_uri_fmt = '%s%%s%s' % (
			m3u8_obj.key.uri[:m3u8_obj.key.uri.rfind('/') + 1],
			m3u8_obj.key.uri[m3u8_obj.key.uri.rfind('/') + 15:],
		)
		key_time_fmt = '%Y%m%d%H0000'
		key = {
			'method': m3u8_obj.key.method,
			'uri': key_base_uri + \
				urllib.quote_plus(key_uri_fmt % segment_time.strftime(key_time_fmt)) + \
				extra_headers,
		}
		key_hour = segment_time.hour
		playlist.key = m3u8_obj.key
		playlist.key.uri = key['uri']

	# Add the video segments.
	segment_uri_fmt = '%s%s%%s%s' % (segment_base_uri, segment_name_prefix, segment_name_suffix)
	segment_time_fmt = '%Y%m%d%H%M%S'
	# Give the playlist a six hour duration.
	# The longest game that I've seen so far is just over 5 hours.  Hopefully
	# 6 hours will be long enough.
	for i in xrange(0, int(21600 / m3u8_obj.target_duration)):
		if key is not None and segment_time.hour != key_hour:
			key_hour = segment_time.hour
			key['uri'] = key_base_uri + \
				urllib.quote_plus(key_uri_fmt % segment_time.strftime(key_time_fmt)) + \
				extra_headers
		segment_uri = segment_uri_fmt % segment_time.strftime(segment_time_fmt)
		segment = m3u8.Segment(segment_uri, '', duration=m3u8_obj.target_duration, key=key)
		playlist.add_segment(segment)
		segment_time += segment_duration
	return playlist

class HLSProxy(object):
	def make_request(self, url, should_stream, headers=None):
		ignore_headers = ['connection', 'content-encoding', 'content-length', 'host', 'range', 'remote-addr']
		req_headers = {}
		for name, value in cherrypy.request.headers.items():
			if name.lower() not in ignore_headers:
				req_headers[name] = value
		if headers is not None:
			headers = urlparse.parse_qs(headers)
			for name, value in headers.items():
				if name.lower() not in ignore_headers:
					req_headers[name] = value[0]

		try:
			r = requests.get(url, headers=req_headers, stream=should_stream)
		except requests.exceptions.ConnectionError:
			raise cherrypy.HTTPError(500)
		if r.status_code != 200:
			raise cherrypy.HTTPError(r.status_code)
		for name, value in r.headers.items():
			if name.lower() not in ignore_headers:
				cherrypy.response.headers[name] = value

		return (req_headers, r)

	@cherrypy.expose
	def playlist(self, url, start_at, headers=None):
		req_headers, r = self.make_request(url, False, headers)
		start_at = parser.parse(start_at).replace(tzinfo=tz.tzutc())
		base_uri = url[:url.rfind('/') + 1]
		playlist = rewind_playlist(m3u8.loads(r.text), start_at, base_uri, req_headers)
		if playlist is None:
			raise cherrypy.HTTPError(500)
		return playlist.dumps() + '\n'

	@cherrypy.expose
	def key(self, url, headers=None):
		r = self.make_request(url, True, headers)[1]
		buffer = StringIO.StringIO()
		for chunk in r.iter_content(16):
			buffer.write(chunk)
		buffer.seek(0)
		return file_generator(buffer)

if __name__ == '__main__':
	from cherrypy._cpnative_server import CPHTTPServer

	if __socket_port__ < 1024 or __socket_port__ > 65535:
		raise ValueError(__language__(30004))
	cherrypy.config.update({
		'engine.autoreload.on': False,
		'engine.timeout_monitor.on': False,
		'server.socket_host': __socket_host__,
		'server.socket_port': __socket_port__,
		'tools.encode.on': False,
	})
	cherrypy.server.httpserver = CPHTTPServer(cherrypy.server)

	cherrypy.tree.mount(HLSProxy(), '/')
	cherrypy.engine.start()
	while (not xbmc.abortRequested):
		xbmc.sleep(500)
	cherrypy.engine.stop()

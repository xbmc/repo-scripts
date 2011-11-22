# coding: utf-8

"""
    Brightcove RTMP Builder
"""
import urllib2
import httplib, socket
import re
import pyamf
from pyamf import remoting

class ContentOverride( object ):
	def __init__( self, contentId, contentType=1, target='videoList' ):
		self.contentType = contentType
		self.contentId = contentId
		self.target = target
		self.contentIds = None
		self.contentRefId = None
		self.contentRefIds = None
		self.contentType = 1
		self.featureId = float(0)
		self.featuredRefId = None

def get_rtmp( playerId, contentId, key, const ):
	conn = httplib.HTTPConnection("c.brightcove.com")
	envelope = build_amf_request( playerId, contentId, key, const )
	conn.request("POST", "/services/messagebroker/amf?playerKey="+key, str(remoting.encode(envelope).read()),{'content-type': 'application/x-amf'})
	response = conn.getresponse().read()
	response = remoting.decode(response).bodies[0][1].body
	return response["videoList"]["mediaCollectionDTO"]["videoDTOs"][0]

def build_amf_request ( playerId, contentId, playerKey, const ):
	pyamf.register_class(ContentOverride, 'com.brightcove.experience.ContentOverride')
	content_override = ContentOverride(int(contentId))
	env = remoting.Envelope(amfVersion=3)
	env.bodies.append(
		  (
			"/1",
			remoting.Request(
				target="com.brightcove.experience.ExperienceRuntimeFacade.getProgrammingWithOverrides",
				body=[const, playerId, [content_override]],
				envelope=env
			)
		  )
	)
	# print env
	return env





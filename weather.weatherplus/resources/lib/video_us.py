# coding: utf-8

#***********************************************************************
#*                                                                     *
#*                                                                     *
#*              def _create_video( video_title )                       *
#*                                                                     *
#*            - creating video list of US Forecast Videos              *
#*                                                                     *
#*                                                                     *
#***********************************************************************

from utilities import printlog, _fetch_data
import video_amf as AMF
import re, time
import xbmcaddon

Addon = xbmcaddon.Addon( id="weather.weatherplus" )

def _create_video( video_title ):
	urls = []
	count = 1
	for title in video_title:
		#***************************
		# criticalmedia
		#***************************
		if ( title == "ABC 15 (AZ)" ):
			htmlSource = _fetch_data( "http://www.abc15.com/dpp/weather/forecast/todays_forecast/arizona-forecast", 15 )
			pattern_video = "http://media2.abc15.com//photo/(.+?)/Arizona_Weather_Foreca(.+?)0000"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://media2.abc15.com/video/criticalmedia/"+video[0][0]+"/Arizona_Weather_Foreca"+video[0][1]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 5 (Cleveland, OH)" ):
			htmlSource = _fetch_data( "http://www.newsnet5.com/subindex/weather", 15 )
			pattern_video = "http://media2.newsnet5.com//photo/(.+?)/(.+?)_weat(.+?)0000"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://media2.newsnet5.com/video/criticalmedia/"+video[0][0]+"/"+video[0][1]+"_weat"+video[0][2]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "WANE-TV (Fort Wayne, IN)" ):
			htmlSource = _fetch_data( "http://www.wane.com/dpp/weather/video_forecast/Daily_Video_Forecast", 15 )
			pattern_video = "http://media2.wane.com//photo/(.+?)/(.+?)_forecast(.+?)0000_"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://media2.wane.com/video/criticalmedia/"+video[0][0]+"/"+video[0][1]+"_forecast"+video[0][2]+".mp4")]
			else:
				urls += [("")]

		#***************************
		# outboundFeed?
		#***************************

		elif ( title == "Wood TV8 (Grand Rapids, MI)" ):
			htmlSource = _fetch_data( "http://www.woodtv.com/dpp/weather/storm_team_8_forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.woodtv.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "ABC 9 (Cincinnati, OH)" ):
			htmlSource = _fetch_data( "http://www.wcpo.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.wcpo.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "WIVB 4 (Buffalo, NY)" ):
			htmlSource = _fetch_data( "http://www.wivb.com/dpp/weather/video_forecast/news-4-weather-watch-forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.wivb.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 10 (Phoenix, AZ)" ):
			htmlSource = _fetch_data( "http://www.myfoxphoenix.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxphoenix.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 11 (Los Angeles, CA)" ):
			htmlSource = _fetch_data( "http://www.myfoxla.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxla.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 5 (Washington D.C)" ):
			htmlSource = _fetch_data( "http://www.myfoxdc.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxdc.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 35 (Orlando, FL)" ):
			htmlSource = _fetch_data( "http://www.myfoxorlando.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxorlando.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 13 (Tampa, FL)" ):
			htmlSource = _fetch_data( "http://www.myfoxtampabay.com/dpp/weather/video_forecast/weather_webcast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxtampabay.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 5 (Atlanta, GA)" ):
			htmlSource = _fetch_data( "http://www.myfoxatlanta.com/dpp/weather/video_forecast/Atlanta-Metro-Weather-Forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxatlanta.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 32 (Chicago, IL)" ):
			htmlSource = _fetch_data( "http://www.myfoxchicago.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxchicago.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 25 (Boston, MA)" ):
			htmlSource = _fetch_data( "http://www.myfoxboston.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxboston.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 2 (Detroit, MI)" ):
			htmlSource = _fetch_data( "http://www.myfoxdetroit.com/subindex/weather/forecasts", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxdetroit.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 5 (New York, NY)" ):
			htmlSource = _fetch_data( "http://www.myfoxny.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxny.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 13 (Memphis, TN)" ):
			htmlSource = _fetch_data( "http://www.myfoxmemphis.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxmemphis.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 7 (Austin, TX)" ):
			htmlSource = _fetch_data( "http://www.myfoxaustin.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxaustin.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 4 (Dallas-Fort Worth, TX)" ):
			htmlSource = _fetch_data( "http://www.myfoxdfw.com/dpp/weather/Dallas_Fort_Worth_Forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxdfw.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 26 (Houston, TX)" ):
			htmlSource = _fetch_data( "http://www.myfoxhouston.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxhouston.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 9 (Minneapolis, MN)" ):
			htmlSource = _fetch_data( "http://www.myfoxtwincities.com/subindex/weather", 15 )
			pattern_video = "componentId[%]3D(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.myfoxtwincities.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "ABC 8 (CT)" ):
			htmlSource = _fetch_data( "http://www.wtnh.com/dpp/weather/storm_team_8_forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED&componentId=([0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://www.wtnh.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video[0] )
				# print htmlSource
				pattern_video = "src=\"([^\"]+)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [( video[0] )]
				else:
					urls += [("")]
			else:
				urls += [("")]

		#***************************
		# Xw6mu (NBC Style)
		#***************************

		elif ( title == "NBC 4 (Los Angeles, CA)" ):
			htmlSource = _fetch_data( "http://www.nbclosangeles.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 7 (San Diego, CA)" ):
			htmlSource = _fetch_data( "http://www.nbcsandiego.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 12 (San Jose, CA)" ):
			htmlSource = _fetch_data( "http://www.nbcbayarea.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 30 (Hartford, CT)" ):
			htmlSource = _fetch_data( "http://www.nbcconnecticut.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 4 (Washington D.C)" ):
			htmlSource = _fetch_data( "http://www.nbcwashington.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 6 (Miami, FL)" ):
			htmlSource = _fetch_data( "http://www.nbcmiami.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 5 (Chicago, IL)" ):
			htmlSource = _fetch_data( "http://www.nbcchicago.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 4 (New York, NY)" ):
			htmlSource = _fetch_data( "http://www.nbcnewyork.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 10 (Philadelphia, PA)" ):
			htmlSource = _fetch_data( "http://www.nbcphiladelphia.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 5 (Dallas-Forth Worth, PA)" ):
			htmlSource = _fetch_data( "http://www.nbcdfw.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = _fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]

		#***************************
		# cdn.bimfs.com
		#***************************
		
		elif ( title == "KHOU 11 (Houston, TX)" ):
			htmlSource = _fetch_data( "http://www.khou.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KHOU/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KHOU/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 13 (Norfolk, VA)" ):
			htmlSource = _fetch_data( "http://www.wvec.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/WVEC/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WVEC/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC (Columbia, SC)" ):
			htmlSource = _fetch_data( "http://www.abccolumbia.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/WCCB/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WCCB/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 3 (Wilmington, NC)" ):
			htmlSource = _fetch_data( "http://www.wwaytv3.com/daily-weather-update", 15 )
			pattern_video = "url: \"http://www.wwaytv3.com/video/news/video/weather/(.+?).flv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://www.wwaytv3.com/video/news/video/weather/"+video[0]+".flv")]
			else:
				urls += [("")]
		elif ( title == "ABC 7 (Buffalo, NY)" ):
			htmlSource = _fetch_data( "http://www.wkbw.com/video?sec=673914", 15 )
			pattern_video = "http://cdn.bimfs.com/WKBW/(.+?).jpg"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WKBW/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 11 (Louisville, KY)" ):
			htmlSource = _fetch_data( "http://www.whas11.com/weather", 15 )
			pattern_video = "http://cdn.bimfs.com/WHAS/(.+?).jpg"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WHAS/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "CBS 58 (Milwaukee, WI)" ):
			htmlSource = _fetch_data( "http://www.cbs58.com/weather", 15 )
			pattern_video = "http://cdn.bimfs.com/WDJT/(.+?).jpg"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WDJT/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "CBS 11 (Anchorage, Alaska)" ):
			htmlSource = _fetch_data( "http://www.ktva.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KTVA/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KTVA/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "CBS 5 (Grand Junction, CO)" ):
			htmlSource = _fetch_data( "http://www.krextv.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KREX/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KREX/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "WINK-TV (Ft. Myers, FL)" ):
			htmlSource = _fetch_data( "http://www.winknews.com/Watch-Forecast", 15 )
			pattern_video = "\"url\": \"http://http://cdn.winknews.com/videos/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.winknews.com/videos/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "WWL-TV 4 (New Orleans, LA)" ):
			htmlSource = _fetch_data( "http://www.wwltv.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/WWLTV/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WWLTV/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "KOMV 4 (St. Louis, MO)" ):
			htmlSource = _fetch_data( "http://www.kmov.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KMOV/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KOMV/"+video[0]+".mp4")]
			else:
				urls += [("")]

		#***************************
		# rtmp (Brightcove)
		#***************************

		elif ( title == "ABC 9 (Orlando, FL)" ):
			htmlSource = _fetch_data( "http://www.wftv.com/s/weather/",  15 )
			# pattern_contentID = "<object id=\"myExperience([0-9]+)\" class=\"BrightcoveExperience\">"
			pattern_playerId = "<param name=\"playerID\" value=\"([0-9]+)\" />"
			pattern_playerKey = "<param name=\"playerKey\" value=\"([^\"]+)\"/>"
			pattern_contentId = "<param name=\"@videoList\" value=\"([0-9]+)\" />"	
			playerId = re.findall( pattern_playerId, htmlSource )
			playerKey = re.findall( pattern_playerKey, htmlSource )
			# playerKey = "AQ~~,AAAAPmbRNRk~,eMJgSV_RKKdQQ0LxUSni2YJuJke-LF5t"
			contentId = re.findall( pattern_contentId, htmlSource )
			print playerId, playerKey, contentId
			try:
				Response = AMF.get_rtmp( playerId[0], contentId[0], playerKey[0], "7a0deda8d3000831d003e195cc4f6135920cc954" )
				if ( Response ):
					url = "rtmp://cp131655.edgefcs.net:1935/ondemand?videoId=%d&lineUpId=%s&pubId=%d&playerId=%s&affiliateId=/%s" % ( int(Response["id"]), contentId[0], int(Response["publisherId"]), playerId[0], Response["FLVFullLengthURL"].split("&")[1] )
					app = "app=ondemand?videoId=%d&lineUpId=%s&pubId=%d&playerId=%s" % ( int(Response["id"]), contentId[0], int(Response["publisherId"]), playerId[0]  )
					pageUrl = "pageUrl=http://www.wftv.com/s/weather/"
					swfUrl = "swfUrl=http://admin.brightcove.com/viewer/us20110929.2031/federatedVideoUI/BrightcovePlayer.swf"
					tcUrl = "tcUrl=rtmp://cp131655.edgefcs.net:1935/ondemand?videoId=%d&lineUpId=%s&pubId=%d&playerId=%s" % ( int(Response["id"]), contentId[0], int(Response["publisherId"]), playerId[0] )
					playpath = "playpath=%s" % Response["FLVFullLengthURL"].split("&")[1]
					urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
				else:
					urls += [("")]
			except:
				urls += [("")]

		#***************************
		# rtmp (flv/xxxx/xxxx/xxxx)
		#***************************

		elif ( title == "ABC 13 (Colorado Springs, CO)" ):
			htmlSource = _fetch_data( "http://www.krdo.com/weather/index.html", 15 )
			pattern_video = "flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				url = "rtmp://96.7.215.29/ondemand?_fcs_vhost=cp92584.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				app = "app=ondemand?_fcs_vhost=cp92584.edgefcs.net"
				pageUrl = "pageUrl=http://www.krdo.com/weather/index.html"
				swfUrl = "swfUrl=http://www.krdo.com/_public/lib/swf/flowplayer/flowplayer.swf?0.6832529801616092"
				tcUrl = "tcUrl=rtmp://96.7.215.29/ondemand?_fcs_vhost=cp92584.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 7 (Denver, CO)" ):
			htmlSource = _fetch_data( "http://www.thedenverchannel.com/weather/index.html", 15 )
			pattern_video = "flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				url = "rtmp://96.7.215.29/ondemand?_fcs_vhost=cp12930.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				app = "app=ondemand?_fcs_vhost=cp12930.edgefcs.net"
				pageUrl = "pageUrl=http://www.thedenverchannel.com/weather/index.html"
				swfUrl = "swfUrl=http://www.thedenverchannel.com/_public/lib/swf/flowplayer/flowplayer.swf?0.47480804055357473"
				tcUrl = "tcUrl=rtmp://96.7.215.29/ondemand?_fcs_vhost=cp12930.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 8 (Grand Junction, CO)" ):
			htmlSource = _fetch_data( "http://www.kjct8.com/weather/index.html", 15 )
			pattern_video = "flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				url = "rtmp://96.7.215.36/ondemand?_fcs_vhost=cp92587.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				app = "app=ondemand?_fcs_vhost=cp92587.edgefcs.net"
				pageUrl = "pageUrl=http://www.kjct8.com/weather/index.html"
				swfUrl = "swfUrl=http://www.kjct8.com/_public/lib/swf/flowplayer/flowplayer.swf?0.4733280426739924"
				tcUrl = "tcUrl=rtmp://96.7.215.36/ondemand?_fcs_vhost=cp92587.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
				
			else:
				urls += [("")]
		elif ( title == "KIRO 7 (Seattle, WA)" ):
			htmlSource = _fetch_data( "http://www.kirotv.com/videoforecast/index.html", 15 )
			pattern_video = "/flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][2]
				url = "rtmp://96.7.215.31/ondemand?_fcs_vhost=cp12926.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".768k"
				app = "app=ondemand?_fcs_vhost=cp12926.edgefcs.net"
				pageUrl = "pageUrl=http://www.kirotv.com/videoforecast/index.html"
				swfUrl = "swfUrl=http://www.kirotv.com/_public/lib/swf/flowplayer/flowplayer.rtmp.swf"
				tcUrl = "tcUrl=rtmp://96.7.215.31/ondemand?_fcs_vhost=cp12926.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]

		#***************************
		# dig.abclocal.go.com
		#***************************

		elif ( title == "ABC 6 (Philadephia, PA)" ):
			htmlSource = _fetch_data( "http://cdn.abclocal.go.com/wpvi/xml?id=6340396", 15 )
			pattern_video = "AccuWeather</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/wpvi/video/(.+?).mp4\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/wpvi/video/%s.mp4") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (Los Angeles, CA)" ):
			htmlSource = _fetch_data( "http://cdn.abclocal.go.com/kabc/xml?id=6340292", 15 )
			pattern_video = "http://dig.abclocal.go.com/kabc/video/(.+?)_weather.flv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/kabc/video/%s_weather.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 12 (Flint, MI)" ):
			htmlSource = _fetch_data( "http://www.abc12.com/category/214773/weather-webcast?clienttype=rssmedia", 15 )
			pattern_video = "http://wjrt.videodownload.worldnow.com/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://wjrt.videodownload.worldnow.com/%s.mp4") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 11 (Raleigh-Durham, NC)" ):
			htmlSource = _fetch_data( "http://abclocal.go.com/wtvd/xml?id=7095536&param1=mrss", 15 )
			pattern_video = "forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/ktrk/video/(.+?).flv\" />"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/ktrk/video/%s.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 13 (Houston, TX)" ):
			htmlSource = _fetch_data( "http://abclocal.go.com/ktrk/xml?id=7076499&param1=mrss", 15 )
			pattern_video = "forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/ktrk/video/(.+?).flv\" />"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/ktrk/video/%s.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (San Francisco, CA)" ):
			htmlSource = _fetch_data( "http://abclocal.go.com/kgo/xml?id=7095531&param1=mrss", 15 )
			pattern_video = "forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/kgo/video/(.+?).flv\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/kgo/video/%s.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (Chicago, IL)" ):
			htmlSource = _fetch_data( "http://abclocal.go.com/wls/xml?id=7095534&param1=mrss", 15 )
			pattern_video = "Forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/wls/video/(.+?).mp4\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/wls/video/%s.mp4") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (New York, NY)" ):
			htmlSource = _fetch_data( "http://cdn.abclocal.go.com/wabc/xml?id=6340375", 15 )
			pattern_video = "AccuWeather</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/wabc/video/(.+?).mp4\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/wabc/video/%s.mp4") % video[0] ]
			else:
				urls += [("")]		
	
		#***************************
		# static rtmp address
		#***************************

		elif ( title == "KELO (Sioux Falls, SD)" ):
			url = "rtmp://flash.keloland.com:80/vod/mp4:/kelo/mp4:/kelo/WeatherUpdate.mp4"
			app = "app=vod/mp4:/kelo"
			pageUrl = "pageUrl=http://www2.keloland.com/_video/_videoplayer_embed.cfm?type=weather&ap=0"
			swfUrl = "swfUrl=http://www2.keloland.com/_video/2010/flowplayer.commercial-3.2.5.swf"
			tcUrl = "tcUrl=rtmp://flash.keloland.com:80/vod/mp4:/kelo"
			playpath = "playpath=mp4:/kelo/WeatherUpdate.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "ABC 13 (Asheville, NC)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:wlos/wlos_weather.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.wlos.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.wlos.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:wlos/wlos_weather.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "ABC 8 (Charleston, WV)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:wchs/webwx.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.wchstv.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.wchstv.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:wchs/webwx.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "CBS 2 (Cedar Rapids, IA)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:kgan/kgan_weather.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.kgan.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.kgan.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:kgan/kgan_weather.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "WGME 13 (Portland, ME)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:wgme/wgme_weather.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.wgme.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.wgme.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:wgme/wgme_weather.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]

		#***************************
		# video-cast, webcast
		#***************************

		# To be looked
		elif ( title == "ABC 9 (NH)" ):
			htmlSource = _fetch_data( "http://www.wmur.com/weather/15644234/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".600k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.wmur.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.wmur.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".600k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 7 (Omaha, NE)" ):
			htmlSource = _fetch_data( "http://www.ketv.com/weather/16777750/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.ketv.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.ketv.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 4 (Hawaii)" ):
			htmlSource = _fetch_data( "http://www.kitv.com/weather/17136897/media.html?qs=;longname=Video-Cast;shortname=VideoCast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg[^>]+><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.kitv.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.kitv.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 9 (Kansas City, MO)" ):
			htmlSource = _fetch_data( "http://www.kmbc.com/weather/15022109/media.html?qs=;longname=Forecast Video;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.kmbc.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.kmbc.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 5 (Oklahoma City, OK)" ):
			htmlSource = _fetch_data( "http://www.koco.com/weather/16746239/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.koco.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.koco.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 2 (Baton Rouge, LA)" ):
			htmlSource = _fetch_data("http://www.wbrz.com/videoplayer/playlist_rss.cfm?categories=66&items=1&cbplayer=0.18014425406210655", 15)
			pattern_video = "rtmp://hosting3.synapseip.tv/wbrz/(.+?)\""
			video = re.findall( pattern_video, htmlSource )
			if (video):
				url = "rtmp://hosting3.synapseip.tv/wbrz/%s" % video[0]
				app = "app=wbrz"
				pageUrl = "pageUrl=http://www.wbrz.com/videoplayer/?categories=66&player_width=300&player_height=220&has_playlist=false&total_playlist_items=1&items_per_page=1&will_stretch_videos=false&has_autoplay=false&auto_hide=never&show_info=false&show_companions=false&live=false&iframe=true"
				swfUrl = "swfUrl=http://www.wbrz.com/videoplayer/swf/flowplayer.commercial-3.2.5.swf?0.9569410777399932"
				tcUrl = "tcUrl=rtmp://hosting3.synapseip.tv/wbrz"
				playpath = "playpath=%s" % video[0]
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "KCCI 8 (Des Moines, IA)" ):
			htmlSource = _fetch_data( "http://www.kcci.com/weather/15912207/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.kcci.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.kcci.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "WLKY (Louisville, KY)" ):
			htmlSource = _fetch_data( "http://www.wlky.com/weather/16509268/media.html?qs=;longname=Webcast;shortname=Webcast;days=&ib_wxwidget=true", 15 )
			pattern_code = "<div class=\"id\" title=\"([0-9]+)\">"
			code = re.findall( pattern_code, htmlSource )	
			# print code
			if ( code ): 
				htmlSource = _fetch_data( "http://www.wlky.com/video-cast/%s/detail.html" % code[0] )
				pattern_video = "location:\'([^']+)\'"
				video = re.findall( pattern_video, htmlSource )
				# print video, htmlSource
				if ( video ):
					url = "rtmp://cp12892.edgefcs.net/ondemand%s.600k" % video[0]
					app = "app=ondemand%s" % video[0]
					pageUrl = "pageUrl=http://www.wlky.com/video-cast/%s/detail.html" % code[0]
					swfUrl = "swfUrl=http://www.wlky.com/_public/lib/swf/flowplayer/flowplayer.swf?0.10982807221342195"
					tcUrl = "tcUrl=rtmp://cp12892.edgefcs.net/ondemand/flv/%s/%s" % ( video[0].split("/")[2], video[0].split("/")[3] )
					playpath = "playpath="+ code[0] +".600k"
					urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
				else:
					urls += [("")]
			else:
				urls += [("")]

		#***************************
		# static address
		#***************************

		elif ( title == "ABC 20 (Gainesville, FL)" ):
			url = "http://wcjb.s3.amazonaws.com/one-minute/weather.flv"
			urls += [ (url) ]
		elif ( title == "CBS 8 (Montgomery, AL)" ):
			urls += [("http://www.waka.com/media/8/forecast.wmv")]
		elif ( title == "KLAS 8 (Las Vegas, NV)" ):
			urls += [("http://ftpcontent.worldnow.com/klas/weather/weather-webcast.mov")]	

		#***************************
		# xml list
		#***************************

		elif ( title == "CBS 11 (Dallas, TX)" ):
			htmlSource = _fetch_data( "http://video.dallas.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=195124&affiliateno=971&clientgroupid=1&rnd=19294", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (Los Angeles, CA)" ):
			htmlSource = _fetch_data( "http://video.losangeles.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=193005&affiliateno=961&clientgroupid=1&rnd=775526", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 4 (Denver, CO)" ):
			htmlSource = _fetch_data( "http://video.denver.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=202261&affiliateno=983&clientgroupid=1&rnd=390532", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 4 (Miami, FL)" ):
			htmlSource = _fetch_data( "http://video.miami.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=197329&affiliateno=988&clientgroupid=1&rnd=440486", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (Chicago, IL)" ):
			htmlSource = _fetch_data( "http://video.chicago.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=194890&affiliateno=967&clientgroupid=1&rnd=724298", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]mms://(.+?).wmv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("mms://%s.wmv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 13 (Baltimore, MD)" ):
			htmlSource = _fetch_data( "http://video.chicago.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=194890&affiliateno=967&clientgroupid=1&rnd=724298", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS (Boston, MA)" ):
			htmlSource = _fetch_data( "http://video.boston.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=195109&affiliateno=970&clientgroupid=1&rnd=692292", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS (Detroit, MI)" ):
			htmlSource = _fetch_data( "http://video.detroit.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=205457&affiliateno=984&clientgroupid=1&rnd=360968", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 4 (Minneapolis, MN)" ):
			htmlSource = _fetch_data( "http://video.minneapolis.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=195093&affiliateno=969&clientgroupid=1&rnd=929708", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (New York, NY)" ):
			htmlSource = _fetch_data( "http://video.newyork.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=191871&affiliateno=958&clientgroupid=1&rnd=22963", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 3 (Philadelphia, PA)" ):
			htmlSource = _fetch_data( "http://video.philadelphia.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=194876&affiliateno=966&clientgroupid=1&rnd=414300", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (Pittsburgh, PA)" ):
			htmlSource = _fetch_data( "http://video.pittsburgh.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=196782&affiliateno=977&clientgroupid=1&rnd=360214", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 13 (Sacramento, CA)" ):
			htmlSource = _fetch_data( "http://video.sacramento.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=196795&affiliateno=978&clientgroupid=1&rnd=92965", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KWCH 12 (Wichita, KS)" ):
			htmlSource = _fetch_data( "http://kwch.vidcms.trb.com/alfresco/service/edge/content/ad5cec9a-524e-4b82-8c01-e0562c31b09c", 15 )
			pattern_video = "/kwch/video/(.+?).flv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://kwch.vid.trb.com/kwch/video/%s.flv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WJTV (Jackson, MS)" ):
			htmlSource = _fetch_data( "http://www2.wjtv.com/weather_video_forecast/", 15 )
			pattern_video = "http://fcvfile.mgnetwork.com/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://fcvfile.mgnetwork.com/%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KCTV 5 (Kansas City, MO)" ):
			htmlSource = _fetch_data( "http://www.kctv5.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=213731&affiliateno=1041&clientgroupid=1&rnd=418997", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KRQE 13 (Albuquerque, NM)" ):
			htmlSource = _fetch_data( "http://www.krqe.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=23080464&FLVPlaybackVersion=1.0.2", 15 )
			pattern_video = "http://media2.krqe.com/video/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://media2.krqe.com/video/%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WBTV 3 (Charlotte, NC)" ):
			htmlSource = _fetch_data( "http://www.wbtv.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=135991&affiliateno=92&clientgroupid=1&rnd=757820", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KXJB (Fargo, ND)" ):
			htmlSource = _fetch_data( "http://www.valleynewslive.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=201384&affiliateno=962&clientgroupid=1&rnd=206292", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WBNS 10 (Columbus, OH)" ):
			htmlSource = _fetch_data( "http://www.10tv.com/content/digital/feeds/video/weather.xml", 15 )
			pattern_video = "http://static.dispatch.com/videos/10tv/(.+?).flv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://static.dispatch.com/videos/10tv/%s.flv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KOIN 6 (Portland, OR)" ):
			htmlSource = _fetch_data( "http://eplayer.clipsyndicate.com/pl_xml/playlist?id=21746&token=X5YExbjs9TmgPuJPTkMbOsG9Do9JAz97coMBuX2LZCE=", 15 )
			pattern_video = "<location>http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WPRI 12 (Providence, RI)" ):
			htmlSource = _fetch_data( "http://modules.lininteractive.com/wex_video/ajax.php?pid=0&ad=1&ver=lo&siteId=20004&categoryId=20780&zone=", 15 )
			pattern_video = "http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WTVF 5 (Nashville, TN)" ):
			htmlSource = _fetch_data( "http://www.newschannel5.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=85811&affiliateno=374&clientgroupid=1&rnd=779991", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]mms://(.+?).wmv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("mms://%s.wmv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WHDH 7 (Boston, MA)" ):
			htmlSource = _fetch_data( "http://wn.whdh.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=72108&affiliateno=428&clientgroupid=1&rnd=433299", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		else:
			urls += [ (Addon.getSetting("video%d_url" % count)) ]
		count = count + 1

	return urls
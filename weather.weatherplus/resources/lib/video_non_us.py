# coding: utf-8

#***********************************************************************
#*                                                                     *
#*                                                                     *
#*              def _create_video( country, continent )                *
#*                                                                     *
#*            - creating video list of non US Forecast Videos          *
#*                                                                     *
#*                                                                     *
#***********************************************************************

from utilities import printlog, _fetch_data
import re, hashlib, time, urllib2

def _create_video( country="", continent="" ):
	# Korea
	if (country == "KS"  or country == "kr" or country == "South Korea"):
		urls=[]
		titles=[]
	   	htmlSource = _fetch_data( "http://news.kbs.co.kr/forecast/", 15 )
		pattern_video = "F[|]10[|]/(.+?).mp4"
		pattern_video2 = "<a href=\"/forecast/(.+?).html\">"
		video = re.findall( pattern_video, htmlSource )	
		video2 = re.findall( pattern_video2, htmlSource )	
		if ( video ): 
			url = "rtmp://newsvod.kbs.co.kr/news/mp4:/%s.mp4" % video[0]
			app = "app=news"
			pageUrl = "pageUrl=http://news.kbs.co.kr/forecast/%s.html" % video2[0]
			swfUrl = "swfUrl=http://news.kbs.co.kr/app/flash_test/m_player.swf"
			tcUrl = "tcUrl=rtmp://newsvod.kbs.co.kr/news"
			playpath = "rtmp://newsvod.kbs.co.kr/news"
			urls += ["%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath)]
			titles += ["KBS"]
		else:
			urls += [""]
			titles += [""]
		'''
		htmlSource = _fetch_data( "http://www.ytnweather.co.kr/issue/weather_center.php", 15 )
		pattern_video = "img src=\"http://image.ytn.co.kr/general/jpg/(.+?)_b.jpg\""
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			urls += ["rtsp://nvod1.ytn.co.kr/general/mov/%s_s.wmv" % video[0]]
			titles += ["YTN"]
		else:
			urls += [""]
			titles += [""]
		'''
	   	htmlSource = _fetch_data( "http://www.obsnews.co.kr/Autobox/250_vod_news.html", 15 )
		pattern_video = "http://www.obsnews.co.kr/news/articleView.html[?]idxno=(.[0-9]+)"
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			htmlSource = _fetch_data( "http://www.obsnews.co.kr/news/articleView.html?idxno=%s" % video[0] )
			pattern_video = "http://vod.obs.co.kr/obsnews/(.+?).wmv"
			video = re.findall( pattern_video, htmlSource )
			if ( video ):
				urls += ["http://vod.obs.co.kr/obsnews/%s.wmv" % video[0]]
				titles += ["OBS"]
			else:
				urls += [""]
				titles += [""]
		else:
			urls += [""]
			titles += [""]

	   	htmlSource = _fetch_data( "http://www.kweather.co.kr/onkweather/onkweather_02.html?type=lifestyle", 15 )
		pattern_video = "http://www.kweather.co.kr/digital/LifeMove/(.+?).flv"
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			urls += ["http://www.kweather.co.kr/digital/LifeMove/%s.flv" % video[0]]
			titles += ["Kweather"]
		else:
			urls += [""]
			titles += [""]
		'''
		htmlSource = _fetch_data( "http://www.weather.kr/", 15 )
		pattern_video = "fct_mov_day_(.+?)_img_(.+?)_00.jpg"
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			url = "rtmp://kmafms.weather.kr/KMA/mp4:%s/fct_mov_day_%s_vod_%s.mp4" % ( "오늘의날씨", video[0][0], video[0][1] )
			app = "app=KMA"
			pageUrl = "pageUrl=http://www.weather.kr/weatherinfo/today.jsp"
			swfUrl = "swfUrl=http://www.weather.kr/player/flashPlayer/vod/KITTPlayer.swf?mode=service&accessJS=true&cid=23764&isCopy=true&startTime=0&endTime=0&autoPlay=false&volume=40&width=560&height=442"
			tcUrl = "tcUrl=rtmp://kmafms.weather.kr/KMA"
			playpath = "playpath=mp4:오늘의날씨/fct_mov_day_%s_vod_%s.mp4" % ( video[0][0], video[0][1] )
			urls += ["%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath)]
			titles += ["KMA (기상청)"]
		else:
			urls += [""]
			titles += [""]
		'''

		urls += [""]
		titles += [""]
		return urls, titles
	
	# Japan
	if (country == "JA" or country == "jp" or country == "Japan"):
		urls=[]
		titles=[]
		url = "rtmp://flv.nhk.or.jp/ondemand/flv/news/weather/weather001"
		app = "app=ondemand/flv"
		pageUrl = "pageUrl=http://www3.nhk.or.jp/weather/"
		swfUrl = "swfUrl=http://www3.nhk.or.jp/weather/news_player2.swf?automode=true&playmode=one&movie=weather001&fms=rtmp://flv.nhk.or.jp/ondemand/flv/news/weather/&debug=false"
		tcUrl = "tcUrl=rtmp://flv.nhk.or.jp/ondemand/flv"
		playpath = "playpath=news/weather/weather001"
		# extra = "extra=AAAAAAEAAAAAAAAAAAAAAAAA"
		urls += ["%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath)]
		titles += ["NHK"]
		
		urls += ["",""]
		titles += ["",""]
		return urls, titles

	# China
	if (country == "CH" or country == "cn" or country == "China"):
		urls=[]
		titles=[]
		urls += ["http://v.weather.com.cn/v/c/xwlb/xwlb.flv"]
		titles += ["CCTV"]
		
		urls += ["",""]
		titles += ["",""]
		return urls, titles

	# UK
        if (country == "UK" or country == "gb" or country == "United Kingdom"):
	    urls = []
	    titles = []
	    print "[Weather Plus] Video Location : UK"
	    # BBC
	    url = "http://news.bbc.co.uk/weather/forecast/10209"
	    pattern_url = "<param name=\"playlist\" value=\"(.+?)\""
	    htmlSource = _fetch_data( url, 15 )
	    url = re.findall( pattern_url, htmlSource )
	    if ( url ):
		htmlSource = _fetch_data( url[0], 15 )
		pattern_id = "<mediator identifier=\"(.+?)\" name=\"pips\""
		id = re.findall( pattern_id, htmlSource )
		if ( id ):
			url = "http://open.live.bbc.co.uk/mediaselector/4/mtis/stream/%s" % id [0]
			htmlSource = _fetch_data( url, 15 )
			pattern_app = "application=\"(.+?)\""
			pattern_auth = "authString=\"(.+?)\""
			pattern_playpath = "identifier=\"(.+?)\""
			app = re.findall( pattern_app, htmlSource )
			auth = re.findall( pattern_auth, htmlSource )
			playpath = re.findall( pattern_playpath, htmlSource )
			if ( app and auth and playpath ):
				swfUrl = "http://emp.bbci.co.uk/emp/worldwide/revisions/555290_554055/555290_554055_emp.swf"
				tcUrl = "rtmp://cp45414.edgefcs.net:80/ondemand"
				url = tcUrl + "?" + auth[0]
				pageUrl = "http://news.bbc.co.uk/weather/forecast/10209"
				urls += ["%s app=%s swfUrl=%s tcUrl=%s pageUrl=%s playpath=%s" % (url, app[0], swfUrl, tcUrl, pageUrl, playpath[0]) ]
				titles += ["BBC"]

	    urls += [ "http://static1.sky.com/feeds/skynews/latest/daily/ukweather.flv", "http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", "" ]
	    titles += ["SKY News (UK)", "SKY News (Europe)", ""]
            # return [url,"http://static1.sky.com/feeds/skynews/latest/weather/long.flv","http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv"], ["UK Forecast", "Long Range", "Europe Forecast"]
	    return urls, titles

        # Canada
        if (country == "CA" or country == "ca" or continent == "canada"):
            print "[Weather Plus] Video Location : Canada"
            accu_canada = "http://www.accuweather.com/video/1681759716/canadian-national-weather-fore.asp?channel=world"
            htmlSource = _fetch_data( accu_canada, 15 )
            pattern_video = "http://brightcove.vo.llnwd.net/d([0-9]+)/unsecured/media/1612802193/1612802193_([0-9]+)_(.+?)-thumb.jpg"
            pattern_playerID = "name=\"playerID\" value=\"(.+?)\""
            pattern_publisherID = "name=\"publisherID\" value=\"(.+?)\""
            pattern_videoID = "name=\"\@videoPlayer\" value=\"(.+?)\""
            video_ = re.findall( pattern_video, htmlSource )
            playerID = re.findall( pattern_playerID, htmlSource )
            publisherID = re.findall( pattern_publisherID, htmlSource )
            videoID = re.findall( pattern_videoID, htmlSource )
	    try:
		if (int(video_[0][1][8:])-1000 < 10000) :
			video= video_[0][1][:8] + "0" + str(int(video_[0][1][8:])-1000)
		else :
			video= video_[0][1][:8] + str(int(video_[0][1][8:])-1000)  
		if (video is not None and video_[0][2][15:] == "cnnational") :
			url = "http://brightcove.vo.llnwd.net/d" + video_[0][0] + "/unsecured/media/1612802193/1612802193_" + video + "_" + video_[0][2] + ".mp4" + "?videoId="+videoID[0]+"&pubId="+publisherID[0]+"&playerId="+playerID[0]
		else : 
			url = ""
	    except:
		url = ""
            print url
            return [url,"http://media.twnmm.com/storage/4902859/22","http://media.twnmm.com/storage/4902671/22"], ["Accuweather.com (Canada) ", "Weather News", "Long Range"]

	# Mexico
	'''
	if (self.code.startswith("MX") or country == "mx" or country == "Mexico"):
	    print "[Weather Plus] Video Location : Mexico"
	'''

	# Brazil
	'''
	if (self.code.startswith("BR") or country == "br" or country == "Brazil"):
	    printlog( "Video Location : Brazil" )
	    url = "http://embed.terratv.terra.com.br/bonsai/Info.aspx"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_url = "file=\"(.+?)\""
	    try:
		url = re.findall( pattern_url, htmlSource )[0].replace("&amp;","&")
		urls = [ url, "", "" ]
		titles = [ "Climatempo", "", "" ]
	    except:
		return ["", "", ""], ["", "", ""]
	    return urls, titles
	'''

	# France
	if (country == "FR" or country == "fr" or country == "France"):
	    urls = []
	    titles = []
	    print "[Weather Plus] Video Location : France"
	    # TF1
	    resp = urllib2.urlopen("http://www.wat.tv/swfap/196832Ac6Pjyk2651740/2427284")
	    ID = re.findall( "videoId=(.[0-9]+)", resp.geturl() )
	    if (ID):
		    ID = ID [0]
		    key = "9b673b13fa4682ed14c3cfa5af5310274b514c4133e9b3a81e6e3aba00912564"
		    hextime = "%x" % time.time()
		    hextime += "0" * ( len( hextime ) - 8 )
		    token = hashlib.md5( key + "/webhd/" + ID + hextime ).hexdigest() + "/" + hextime
		    url = "http://www.wat.tv/get/webhd/" + ID + "?token=" + token + "&context=swf2&getURL=1&version=WIN%2010,3,183,5&lieu=tf1" 
		    # print url
		    url = _fetch_data( url, )
		    urls += [url + "|User-Agent=Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)"]
		    titles += ["TF1"]
		
	    # France 2
	    url = "http://meteo.france2.fr/bulletin.php"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_id = "http://info.francetelevisions.fr/[?]id-video=(.+?)\""
	    id = re.findall ( pattern_id, htmlSource )
	    if ( id ):
		url = "http://meteo.france2.fr/appftv/webservices/video/getInfosCatalogueVideo.php?id-video=%s" % id [0]
		pattern_url = "<url-video>(.[^<]+)</url-video>"
		htmlSource = _fetch_data( url, 15 )
		url = re.findall ( pattern_url, htmlSource )
		print url, htmlSource
		if ( url ):
			url = "http://a988.v101995.c10199.e.vm.akamaistream.net/7/988/10199/3f97c7e6/ftvigrp.download.akamai.com/10199/cappuccino/production/publication/%s" % url [0]
			urls += [url]
			titles += ["France 2"]
		else:
			urls += [""]
			titles += [""]
	    else:
		urls += [""]
		titles += [""]

	    urls += ["http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", ""]
	    titles += ["SKY News (Europe)", ""]
	    print urls, titles
	    return urls, titles
	    
	# Italy
	if (country == "IT" or country == "it" or country == "Italy"):
	    print "[Weather Plus] Video Location : Italy"
            return ["http://media.ilmeteo.it/video/oggi-tg.mp4","http://media.ilmeteo.it/video/domani-tg.mp4", "http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv"], ["iL Meteo (Today)", "iL Meteo (Tomorrow)", "SKY News (Europe)"]

	urls = []
	titles = []
	Europe = 0

	# Bulgaria
	if (country == "BU" or country == "bg" or country == "Bulgaria"):
	    printlog( "Video Location : Bulgaria" )
	    urls = [ "http://meteotv.bg/str/HI01.flv" ]
	    titles = [ "Meteotv.bg"]
	    Europe = 1
	
	# Poland
	if (country == "PO" or country == "pl" or country == "Poland"):
	    printlog( "Video Location : Poland" )
	    url = "http://www.tvnmeteo.pl/wideo/prognoza,45,1.html"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_url = "http://redir.atmcdn.pl/scale/o2/tvn/web-content/m/v/([^/]+)/([^/]+)/S/"
	    try:
		url = re.findall( pattern_url, htmlSource )
		url = "http://dcs-212-91-8-229.atmcdn.pl/dcs/o2/tvn/web-content/m/v/%s/%s-480p.flv" % ( url[0][0], url[0][1] )
		urls = [ url ]
		titles = [ "TVN" ]
	    except:
		pass
	    Europe = 1
	

	# Ireland
	if (country == "EI" or country == "ie" or country == "Ireland"):
	    printlog( "Video Location : Ireland" )
	    url = "http://www.tv3.ie/weather.php"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_url = "url: \"http://cdn.tv3.ie/([^\"]+)\""
	    try:
		url = re.findall( pattern_url, htmlSource )[0]
		url = "http://cdn.tv3.ie/%s" % url
		htmlSource = _fetch_data( url, 15 )
		pattern_url = "<video src=\"(.+?)\""
		pattern_base = "<meta base=\"(.+?)\""
		try:
			code = re.findall( pattern_url, htmlSource )[0].replace("&amp;","&")
			base = re.findall( pattern_base, htmlSource )[0]
			pattern_app = "rtmp://[^/]+/([^/]+)/_(.+?)_"
			app = re.findall (pattern_app, htmlSource )[0]
			url = "%s/%s" % (base, code)
			app = "%s/_%s_" % (app[0], app[1])
			pageUrl = "http://www.tv3.ie/weather.php"
			swfUrl = "http://www.tv3.ie/includes/flash/flowplayer.commercial-3.2.6-dev2.swf?0.6006767218014416"
			tcUrl = "%s" % base
			playpath = code
			urls = [ "%s app=%s swfUrl=%s tcUrl=%s pageUrl=%s playpath=%s" % (url, app, swfUrl, tcUrl, pageUrl, playpath) ]
			titles = [ "TV3" ]
		except:
			pass
	    except:
		pass
	    Europe = 1

	# Germany
	if (country == "GM" or country == "de" or country == "Germany"):
	    printlog( "Video Location : Germany" )
	    url = "http://wetter.zdf.de/ZDFwetter/inhalt/0/0,5998,1040000,00.html?preview,0"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_code = "'eplayer_1','http://www.zdf.de/ZDFmediathek/content/([0-9]+)'" 
	    try:
		code = re.findall( pattern_code, htmlSource )[0]
		url = "http://www.zdf.de/ZDFmediathek/embedded/%s" % code
		htmlSource = _fetch_data( url, 15 )
		pattern_url = "<dsl2000>(.+?)</dsl2000>"
		try:
			url = re.findall( pattern_url, htmlSource )[0]
			htmlSource = _fetch_data( url, 15 )
			pattern_url = "<default-stream-url>(.+?)</default-stream-url>"
			try:
				url = re.findall( pattern_url, htmlSource )[0]
				app = "ondemand"
				pageUrl = "http://www.zdf.de/ZDFmediathek/beitrag/video/%s" % code
				swfUrl = "http://www.zdf.de/ZDFmediathek/flash/data/swf/AkamaiBasicStreamingPlugin.swf"
				tcUrl = "rtmp://cp125301.edgefcs.net:1935/ondemand"
				playpath = "mp4:%s" % url.split("mp4:")[1]
				urls = [ "%s app=%s swfUrl=%s tcUrl=%s pageUrl=%s playpath=%s" % (url, app, swfUrl, tcUrl, pageUrl, playpath) ]
				titles = [ "ZDF.de" ]
			except:
				pass
		except:
			pass
	    except:
		pass		
	    Europe = 1

	# Spain
	if (country == "SP" or country == "es" or country == "Spain"):
	    printlog( "Video Location : Spain" )
	    url = "http://flash.1.multimedia.cdn.rtve.es/resources/TE_NGVA/mp4/8/9/1322549664098.mp4?type=.smil"
	    auth_url = "http://flash.1.multimedia.cdn.rtve.es/auth/resources/TE_NGVA/mp4/8/9/1322549664098.mp4?v=2.1.20&fp=WIN%2011,1,102,55&r=EGOER&g=KRJRXYTCXDBM"
	    htmlSource = _fetch_data( url, 15 )
	    authSource = _fetch_data( auth_url, 15 )
	    pattern_base = "<meta name=\"httpBase\" content=\"([^\"]+)\"/>"
	    try:
	        base = re.findall( pattern_base, htmlSource )[0][:-1]
		url = "%s%s%s" % (base, authSource, "|User-Agent=Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)")
		urls = [ url ]
		titles = [ "tve" ]
	    except:
		pass
	    Europe = 1
	
	# Belgium
	if (country == "BE" or country == "be" or country == "Belgium"):
	    printlog( "Video Location : Belgium" )
	    url = "http://www.rtl.be/meteo/bulletin/"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_code = "src=\"../inc/embhtml5.php[?]id=([0-9]+)\">"
	    try:
		code = re.findall( pattern_code, htmlSource )[0]
		url = "http://videos.rtl.be/GetFlashParams.aspx?id=%s&bEmbed=1&sDummyPath=" % code
		htmlSource = _fetch_data( url, 15 )
		pattern_url = "<URL>(.+?)</URL>"
		try:
			url = re.findall( pattern_url, htmlSource )[0]
			urls = [ url ]
			titles = [ "RTL.be" ]
		except:
			pass
	    except:
		pass
	    
	    url = "http://www.deredactie.be/cm/vrtnieuws/mediatheek/weer?view=shortcutDepartment&shortcutView=defaultList"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_url = "div class=\"mediaItem\" id=\"([^\"]+)\""
	    try:
		url = re.findall( pattern_url, htmlSource )[0]
		htmlSource = _fetch_data( url, 15 )
		pattern_url = "= \'(.+?).flv\'"
		try:
			code = re.findall( pattern_url, htmlSource )[0]
			url = "rtmp://vrt.flash.streampower.be/vrtnieuws/%s" % code
			app = "vrtnieuws"
			pageUrl = "http://www.deredactie.be/cm/vrtnieuws/mediatheek/weer/"
			swfUrl = "http://www.deredactie.be/html/flash/common/player.swf"
			tcUrl = "rtmp://vrt.flash.streampower.be/vrtnieuws"
			playpath = code
			urls += [ "%s app=%s swfUrl=%s tcUrl=%s pageUrl=%s playpath=%s" % (url, app, swfUrl, tcUrl, pageUrl, playpath) ]
			titles += [ "Deredactie.be" ]
		except:
			pass
	    except:
		pass

	    Europe = 1

	# Netherlands
	if (country == "NL" or country == "nl" or country == "Netherlands"):
	    printlog( "Video Location : Netherlands" )
	    url = "http://www.weer.nl/weerpresentatie.html"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_url = "http://www.weer.nl/fileadmin/filemounts/nederlands/ftp_upload/video/(.+?).flv"
	    try:
		url = re.findall( pattern_url, htmlSource )[0]
		urls += [ "http://www.weer.nl/fileadmin/filemounts/nederlands/ftp_upload/video/%s.flv" % url ]
		titles += [ "Weer.nl" ]
	    except:
		pass

	    Europe = 1

	# Romania
	if (country == "RO" or country == "ro" or country == "Romania"):
	    printlog( "Video Location : Romania" )
	    url = "http://www.a1.ro/meteo/index.html"
	    htmlSource = _fetch_data( url, 15 )
	    pattern_url = "http://ivm.inin.ro/js/embed.js[?]autoplay=0&width=310&height=244&wide=1&id=(.+?)\""
	    try:
		url = re.findall( pattern_url, htmlSource )[0]
		url = "http://ivm.inin.ro/js/embed.js?autoplay=0&width=310&height=244&wide=1&id=%s" % url
		htmlSource = _fetch_data( url, 15 )
		pattern_url = "real_file: \'(.+?).mp4\'"
		try:
			url = re.findall( pattern_url, htmlSource )[0]
			url = "%s.mp4" % url
			urls += [ url ]
			titles += [ "Antenna 1" ]
		except:
			pass
	    except:
		pass

	    Europe = 1
	
	# Hungary
	if (country == "HU" or country == "hu" or country == "Hungary"):
	    printlog( "Video Location : Hungary" )
	    url = "http://94.199.183.188/rtlhirek/idojaras/meteor.flv"
	    urls += [ url ]
	    titles += [ "RTL Klub" ]
	    Europe = 1

        # Europe
        if (Europe or country == "GR" or country == "RS" or country == "PL" or continent.startswith("iseur") or continent == "europe"):    
            printlog( "Video Location : Europe" )
            accu_europe = "http://www.accuweather.com/video/1681759717/europe-weather-forecast.asp?channel=world"
            htmlSource = _fetch_data( accu_europe, 15 )
            pattern_video = "http://brightcove.vo.llnwd.net/d([0-9]+)/unsecured/media/1612802193/1612802193_([0-9]+)_(.+?)-thumb.jpg"
            pattern_playerID = "name=\"playerID\" value=\"(.+?)\""
            pattern_publisherID = "name=\"publisherID\" value=\"(.+?)\""
            pattern_videoID = "name=\"\@videoPlayer\" value=\"(.+?)\""
            video_ = re.findall( pattern_video, htmlSource )
            playerID = re.findall( pattern_playerID, htmlSource )
            publisherID = re.findall( pattern_publisherID, htmlSource )
            videoID = re.findall( pattern_videoID, htmlSource )
	    # print video_
	    try:
		if (int(video_[0][1][8:])-1000 < 10000) :
			video= video_[0][1][:8] + "0" + str(int(video_[0][1][8:])-1000)
		else :
			video= video_[0][1][:8] + str(int(video_[0][1][8:])-1000)
	        if (video_[0][2][15:] == "europe") :
                        urls += ["http://brightcove.vo.llnwd.net/d" + video_[0][0] + "/unsecured/media/1612802193/1612802193_" + video + "_" + video_[0][2] + ".mp4" + "?videoId="+videoID[0]+"&pubId="+publisherID[0]+"&playerId="+playerID[0], "http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", ""]
			titles += ["Accuweather.com (Europe)", "SKY News (Europe)", ""]
	        else : 
	                urls += ["http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", "", ""]
			titles += ["SKY News (Europe)", "", ""]
            except:
		urls += ["http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", "", ""]
		titles += ["SKY News (Europe)", "", ""]            
	    # print urls
            # return [url,"http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv",""], ["Accuweather.com (Europe)", "SKY News (Europe)", "No Video"]
            return urls, titles

	# Austrailia
	if (country == "AS" or country == "au" or continent == "oceania"):
		print "[Weather Plus] Video Location : Austrailia"
		abc = "http://www.abc.net.au/news/abcnews24/weather-in-90-seconds/"
		htmlSource = _fetch_data( abc, 15 )
		pattern_video = "http://mpegmedia.abc.net.au/news/weather/video/(.+?)video3.flv"
		video = re.findall( pattern_video, htmlSource )
		try:
			url = "http://mpegmedia.abc.net.au/news/weather/video/" + video[0] + "video3.flv"
		except:
			url = ""
		return [url, "", ""], ["ABC (Weather in 90 Seconds)", "No Video", "No video"]
        # No available video
        return ["","",""], ["","",""]

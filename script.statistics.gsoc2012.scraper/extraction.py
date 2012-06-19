from url import removeFromStackAndRecurse
import json

from xbmcjsonrpc import *

movie_properties = [
	"title",
	"runtime",
	"imdbnumber",
	"year",
	"file"
]

episode_properties = [
	"title",
	"season",
	"episode",
	"tvshowid",
	"file"
]

show_properties = [
	"title",
	"imdbnumber"
]

music_videos_properties = [
	"title",
	"runtime",
	"artist",
	"album",
	"file"
]

# Taken from XBMC
m_pictureExtensions = ".png|.jpg|.jpeg|.bmp|.gif|.ico|.tif|.tiff|.tga|.pcx|.cbz|.zip|.cbr|.rar|.m3u|.dng|.nef|.cr2|.crw|.orf|.arw|.erf|.3fr|.dcr|.x3f|.mef|.raf|.mrw|.pef|.sr2|.rss"
m_pictureExtensions = m_pictureExtensions.split("|")

# Taken from XBMC
m_musicExtensions = ".nsv|.m4a|.flac|.aac|.strm|.pls|.rm|.rma|.mpa|.wav|.wma|.ogg|.mp3|.mp2|.m3u|.mod|.amf|.669|.dmf|.dsm|.far|.gdm|.imf|.it|.m15|.med|.okt|.s3m|.stm|.sfx|.ult|.uni|.xm|.sid|.ac3|.dts|.cue|.aif|.aiff|.wpl|.ape|.mac|.mpc|.mp+|.mpp|.shn|.zip|.rar|.wv|.nsf|.spc|.gym|.adx|.dsp|.adp|.ymf|.ast|.afc|.hps|.xsp|.xwav|.waa|.wvs|.wam|.gcm|.idsp|.mpdsp|.mss|.spt|.rsd|.mid|.kar|.sap|.cmc|.cmr|.dmc|.mpt|.mpd|.rmt|.tmc|.tm8|.tm2|.oga|.url|.pxml|.tta|.rss|.cm3|.cms|.dlt|.brstm|.wtv|.mka"
m_musicExtensions = m_musicExtensions.split("|")

# Taken from XBMC
m_videoExtensions = ".m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.m3u|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.pva|.wmv|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.rar|.001|.wpl|.zip|.vdr|.dvr-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.webm|.bdmv|.wtv"
m_videoExtensions = m_videoExtensions.split("|")

def extractEpisodes(files, onProgress, isInterrupted):
# This method will fetch FILE TVSHOW_TITLE EPISODE_TITLE SEASON EPISODE from episodes in the video library
	tvshows = dict()

	result = getTVShows(show_properties)

	for show in result:
		if "title" in show:
			tvshows[show["tvshowid"]] = show["title"]

	result = getEpisodes(episode_properties)

	episodes = list()
	nbrEpisodes = len(result)

	for i in range(nbrEpisodes):
		e = result[i]

		if onProgress:
			onProgress(i * 100 / nbrEpisodes)

		path = removeFromStackAndRecurse(e["file"])
		files.add(path)

		if all([f in e for f in episode_properties]) and e["tvshowid"] in tvshows:
			episode = {
				"file": path,
				"tvshow_title": tvshows[e["tvshowid"]],
				"episode_title": e["title"],
				"season": e["season"],
				"episode": e["episode"]
			}

			episodes.append(episode)

		if isInterrupted():
			break

	return episodes

def extractMovies(files, onProgress, isInterrupted):
# This method will fetch FILE TITLE YEAR IMDB RUNTIME from movies in the video library
	result = getMovies(movie_properties)

	movies = list()
	nbrMovies = len(result)

	for i in range(nbrMovies):
		m = result[i]

		if onProgress:
			onProgress(i * 100 / nbrMovies)

		path = removeFromStackAndRecurse(m["file"])
		files.add(path)

		if all([f in m for f in movie_properties]):
			movie = {
				"file": path,
				"title": m["title"],
				"year": m["year"],
				"imdb": m["imdbnumber"],
				"runtime": m["runtime"]
			}

			movies.append(movie)

		if isInterrupted():
			break

	return movies

def extractMusicVideos(files, onProgress, isInterrupted):
# This method will fetch FILE FILE ARTIST TITLE RUNTIME from music videos in the video library
	result = getMusicVideos(music_videos_properties)

	musicVideos = list()
	nbrMusicVideos = len(result)

	for i in range(nbrMusicVideos):
		m = result[i]

		if onProgress:
			onProgress(i * 100 / nbrMusicVideos)

		path = removeFromStackAndRecurse(m["file"])
		files.add(path)

		if all([f in m for f in music_videos_properties]):
			musicVideo = {
				"file": path,
				"title": m["title"],
				"artist": m["artist"],
				"album": m["album"],
				"runtime": m["runtime"]
			}

			musicVideos.append(musicVideo)

		if isInterrupted():
			break

	return musicVideos

def getExtension(path):
	try:
		return path[path.rindex("."):].lower()
	except ValueError:
		return None

def extractVideoFilesFromDirectory(files, videoFiles, directory, isInterrupted, onProgress = None):
	result = getDirectory(directory)

	thisDirectory = result
	nbrFiles = len(thisDirectory)
	for i in range(nbrFiles):
		f = thisDirectory[i]

		if onProgress:
			onProgress(i * 100 / nbrFiles)

		if f["filetype"] == "directory":
			extractVideoFilesFromDirectory(files, videoFiles, f["file"], isInterrupted)
		elif f["filetype"] == "file":
			path = removeFromStackAndRecurse(f["file"])
			if path not in files and getExtension(path) in m_videoExtensions:

				# Here we could extract subtitles etc.

				videoFile = {
					"file": path
				}
				videoFiles.append(videoFile)

		if isInterrupted():
			break

def extractVideoFiles(files, onProgress, isInterrupted):
	sources = getSources()

	videoFiles = list()
	nbrSources = len(sources)

	for i in range(nbrSources):
		source = sources[i]

		if onProgress:
			onProgress(source["label"], i * 100 / len(sources))

			def midProgress(percentage):
				onProgress(source["label"], (i * 100 + (percentage / nbrSources) + 1) / nbrSources)
			extractVideoFilesFromDirectory(files, videoFiles, source["file"], isInterrupted, midProgress)
		else:
			extractVideoFilesFromDirectory(files, videoFiles, source["file"], isInterrupted, None)

		if isInterrupted():
			break

	return videoFiles

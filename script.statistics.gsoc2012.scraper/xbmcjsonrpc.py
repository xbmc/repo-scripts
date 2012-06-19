def safeGet(d, k, v):
	if d == None:
		return v

	vv = d.get(k, v)
	if vv == None:
		return v
	else:
		return vv

try:
	import xbmc
	import json
	import uuid

	def doXBMCRequest(method, *args, **kwargs):
		params = None

		if len(args):
			params = args
		else:
			params = kwargs

		request = { "jsonrpc": "2.0", "method": method, "params": params, "id": str(uuid.uuid1()) }
		response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
		return response.get("result", None)

	def getSources():
		result = doXBMCRequest("Files.GetSources", media="video")
		return safeGet(result, "sources", [])

	def getDirectory(directory):
		result = doXBMCRequest("Files.GetDirectory", directory)
		return safeGet(result, "files", [])

	def getMovies(properties):
		result = doXBMCRequest("VideoLibrary.GetMovies", properties=properties)
		return safeGet(result, "movies", [])

	def getEpisodes(properties):
		result = doXBMCRequest("VideoLibrary.GetEpisodes", properties=properties)
		return safeGet(result, "episodes", [])

	def getTVShows(properties):
		result = doXBMCRequest("VideoLibrary.GetTVShows", properties=properties)
		return safeGet(result, "tvshows", [])

	def getMusicVideos(properties):
		result = doXBMCRequest("VideoLibrary.GetMusicVideos", properties=properties)
		return safeGet(result, "musicvideos", [])
except:
	import jsonrpclib

	server = jsonrpclib.Server('http://localhost:8080/jsonrpc')

	def getSources():
		result = server.Files.GetSources(media="video")
		return safeGet(result, "sources", [])

	def getDirectory(directory):
		result = server.Files.GetDirectory(directory)
		return safeGet(result, "files", [])

	def getMovies(properties):
		result = server.VideoLibrary.GetMovies(properties=properties)
		return safeGet(result, "movies", [])

	def getEpisodes(properties):
		result = server.VideoLibrary.GetEpisodes(properties=properties)
		return safeGet(result, "episodes", [])

	def getTVShows(properties):
		result = server.VideoLibrary.GetTVShows(properties=properties)
		return safeGet(result, "tvshows", [])

	def getMusicVideos(properties):
		result = server.VideoLibrary.GetMusicVideos(properties=properties)
		return safeGet(result, "musicvideos", [])

import xbmc, xbmcgui, xbmcaddon
from xbmcjsonrpc import getSources
import extraction
import server
import string


__settings__ = xbmcaddon.Addon(id='script.statistics.gsoc2012.scraper')


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

class SubmitState(object):
	def __init__(self, episodes, movies, musicVideos, videoFiles):
		self.episodes = episodes
		self.movies = movies
		self.musicVideos = musicVideos
		self.videoFiles = videoFiles

	def doModal(self):
		dialog = xbmcgui.Dialog()
		ret = dialog.yesno(__settings__.getLocalizedString(32001), __settings__.getLocalizedString(32002).format(len(self.episodes), len(self.movies)), __settings__.getLocalizedString(32003).format(len(self.musicVideos), len(self.videoFiles)))

		if ret:
			chunksize = 20
			percentage = 0
			total = len(self.episodes) + len(self.movies) + len(self.musicVideos) + len(self.videoFiles)

			progress = xbmcgui.DialogProgress()
			ret = progress.create(__settings__.getLocalizedString(32004), __settings__.getLocalizedString(32005), "")

			for m in chunks(self.episodes, chunksize):
				server.uploadMedia("episodes", m)
				progress.update((percentage * 100) / total, __settings__.getLocalizedString(32006))
				percentage += chunksize
				if progress.iscanceled():
					return

			for m in chunks(self.movies, chunksize):
				server.uploadMedia("movies", m)
				progress.update((percentage * 100) / total, __settings__.getLocalizedString(32007))
				percentage += chunksize
				if progress.iscanceled():
					return

			for m in chunks(self.musicVideos, chunksize):
				server.uploadMedia("musicvideos", m)
				progress.update((percentage * 100) / total, __settings__.getLocalizedString(32008))
				percentage += chunksize
				if progress.iscanceled():
					return

			for m in chunks(self.videoFiles, chunksize):
				server.uploadMedia("videofiles", m)
				progress.update((percentage * 100) / total, __settings__.getLocalizedString(32009))
				percentage += chunksize
				if progress.iscanceled():
					return

			progress.update(100)
			progress.close()

	def close(self):
		pass

class GatherState(object):
	def __init__(self, extractionSteps):
		self.gatherDialog = xbmcgui.DialogProgress()
		self.extractionSteps = extractionSteps

	def doModal(self):
		ret = self.gatherDialog.create(__settings__.getLocalizedString(32004), __settings__.getLocalizedString(32010), "")

		episodes = list()
		movies = list()
		musicVideos = list()
		videoFiles = list()

		try:
			self.steps = len(self.extractionSteps)
			files = set()
			if "episodes" in self.extractionSteps:
				def episodeProgress(percentage):
					self.gatherDialog.update(percentage / self.steps, __settings__.getLocalizedString(32011), "", "")
				episodes = extraction.extractEpisodes(files, episodeProgress, self.gatherDialog.iscanceled)

			if "movies" in self.extractionSteps:
				def movieProgress(percentage):
					self.gatherDialog.update((100 + percentage) / self.steps, __settings__.getLocalizedString(32012), "", "")
				movies = extraction.extractMovies(files, movieProgress, self.gatherDialog.iscanceled)

			if "musicvideos" in self.extractionSteps:
				def musicVideosProgress(percentage):
					self.gatherDialog.update((100 + percentage) / self.steps, __settings__.getLocalizedString(32013), "", "")
				musicVideos = extraction.extractMusicVideos(files, musicVideosProgress, self.gatherDialog.iscanceled)

			sources = [s for s in getSources() if s["file"] in self.extractionSteps]
			nbrSources = len(sources)

			for i in range(nbrSources):
				source = sources[i]
				source["tick"] = 0
				source["percentage"] = 0

				def unscrapedIsCanceled():
					source["tick"] = source["tick"] + 1 if source["tick"] < 5 else 0
					s = string.join(['.' for s in range(source["tick"])])
					offset = 200 + i * nbrSources

					self.gatherDialog.update((offset + source["percentage"]) / self.steps, __settings__.getLocalizedString(32014) + s, source["label"], "")

					return self.gatherDialog.iscanceled()

				def midProgress(i):
					source["percentage"] = i / nbrSources
					unscrapedIsCanceled()

				extraction.extractVideoFilesFromDirectory(files, videoFiles, source["file"], unscrapedIsCanceled, midProgress)

		except:
			raise
		finally:
			self.gatherDialog.close()

		self.sm.switchTo(SubmitState(episodes, movies, musicVideos, videoFiles))

	def close(self):
		pass

class InitialWindow(xbmcgui.Window):
	def __init__(self):
		self.strActionInfo = xbmcgui.ControlLabel(0, 0, 300, 200, __settings__.getLocalizedString(32015), 'font13', '0xFFFFFFFF')
		self.addControl(self.strActionInfo)

		self.choiceButton = list()
		self.choiceID = list()

		self.gather = xbmcgui.ControlButton(800, 50, 200, 100, __settings__.getLocalizedString(32016))
		self.addControl(self.gather)

		self.addChoice(__settings__.getLocalizedString(32017), "movies")
		self.addChoice(__settings__.getLocalizedString(32018), "episodes")
		self.addChoice(__settings__.getLocalizedString(32019), "musicvideos")

		for source in getSources():
			self.addChoice(__settings__.getLocalizedString(32020) + '"' + source["label"] + u'"', source["file"])

		self.setFocus(self.choiceButton[0])
		self.gather.controlLeft(self.choiceButton[0])

	def addChoice(self, label, ID):
		button = xbmcgui.ControlRadioButton(50, 50 + 50 * len(self.choiceButton), 600, 40, label)
		self.addControl(button)
		button.setSelected(True)

		if len(self.choiceButton) > 0:
			last = self.choiceButton[-1]
			last.controlDown(button)
			button.controlUp(last)

		button.controlRight(self.gather)

		self.choiceID.append(ID)
		self.choiceButton.append(button)
 
	def onControl(self, control):
		if control is self.gather:
			steps = [self.choiceID[self.choiceButton.index(b)] for b in self.choiceButton if b.isSelected()]
			self.sm.switchTo(GatherState(steps))

class CheckServerState(object):
	def doModal(self):
		if server.serverActive():
			self.sm.switchTo(InitialWindow())
		else:
			dialog = xbmcgui.Dialog()
			dialog.ok(__settings__.getLocalizedString(32021), __settings__.getLocalizedString(32022))

	def close(self):
		pass

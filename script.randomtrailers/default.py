# Random trailer player
#
# Author - kzeleny
# Version - 1.0.2
# Compatibility - Frodo
#

import xbmc
import xbmcgui
from urllib import quote_plus, unquote_plus
import re
import sys
import os
import random
import simplejson as json
import time
import xbmcaddon
addon = xbmcaddon.Addon()
number_trailers =  addon.getSetting('number_trailers')
do_curtains = addon.getSetting('do_animation')
do_genre = addon.getSetting('do_genre')
hide_info = addon.getSetting('hide_info')
xbmc.log('do curtains = ' + do_curtains)

addon_path = addon.getAddonInfo('path')
resources_path = xbmc.translatePath( os.path.join( addon_path, 'resources' ) ).decode('utf-8')
media_path = xbmc.translatePath( os.path.join( resources_path, 'media' ) ).decode('utf-8')
open_curtain_path = xbmc.translatePath( os.path.join( media_path, 'OpenSequence.mp4' ) ).decode('utf-8')
close_curtain_path = xbmc.translatePath( os.path.join( media_path, 'ClosingSequence.mp4' ) ).decode('utf-8')
selectedGenre =''
exit_requested = False
movie_file = ''

def askGenres():
  # default is to select from all movies
  selectGenre = False
  # ask user whether they want to select a genre
  a = xbmcgui.Dialog().yesno("Select genre", "Do you want to select a genre to watch?")
  # deal with the output
  if a == 1: 
    # set filter
    selectGenre = True
  return selectGenre  
  
def selectGenre():
  success = False
  selectedGenre = ""
  myGenres = []
  trailerstring = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "properties": ["genre", "playcount", "file", "trailer"]}, "id": 1}')
  trailerstring = unicode(trailerstring, 'utf-8', errors='ignore')
  trailers = json.loads(trailerstring)
  for movie in trailers["result"]["movies"]:
    # Let's get the movie genres
    genres = movie["genre"]
    for genre in genres:
        # check if the genre is a duplicate
        if not genre in myGenres:
          # if not, add it to our list
          myGenres.append(genre)
  # sort the list alphabeticallt        
  mySortedGenres = sorted(myGenres)
  # prompt user to select genre
  selectGenre = xbmcgui.Dialog().select("Select genre:", mySortedGenres)
  # check whether user cancelled selection
  if not selectGenre == -1:
    # get the user's chosen genre
    selectedGenre = mySortedGenres[selectGenre]
    success = True
  else:
    success = False
  # return the genre and whether the choice was successfult
  return success, selectedGenre
  
def getTrailers(genre):
	# get the raw JSON output
	xbmc.log('selected genre = ' + genre)
	trailerstring = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "file", "year", "genre", "trailer"], "filter": {"field": "genre", "operator": "contains", "value": "%s"}}, "id": 1}' % genre)
	trailerstring = unicode(trailerstring, 'utf-8', errors='ignore')
	trailers = json.loads(trailerstring)
	random.shuffle(trailers["result"]["movies"])	
	return trailers

class movieWindow(xbmcgui.WindowXMLDialog):
    
	def onInit(self):
		global SelectedGenre
		player = XBMCPlayer()
		self.play_control = self.getControl(30003)
		self.name_control = self.getControl(30002)
		self.name_control.setVisible(False)
		self.play_control.setVisible(False)
		DO_MUTE = addon.getSetting('do_mute')
		DO_EXIT = addon.getSetting('do_exit')
		trailers = getTrailers(selectedGenre)
		movieTrailer =''
		sanity =0
		while movieTrailer == '':
			sanity = sanity + 1
			trailer=random.choice(trailers["result"]["movies"])
			if not trailer["trailer"] == '':
				movieYear = trailer["year"]
				self.movieFile = trailer["file"]
				movieTrailer = trailer["trailer"]
				movieTitle = trailer["title"]
				self.name_control.setLabel(movieTitle + ' - ' + str(movieYear))
			if sanity == 100:
				break
			if not movieTrailer == '':
				player.play(movieTrailer)
				while player.isPlaying():
					if hide_info == 'false':
						nameVisible = xbmc.getCondVisibility("Control.IsVisible(30002)")
						if nameVisible:
							self.name_control.setVisible(False)
							self.play_control.setVisible(True)
						else:
							self.play_control.setVisible(False)
							self.name_control.setVisible(True)						
					xbmc.sleep(3000)
		self.close()
		
	def onAction(self, action):
		ACTION_PREVIOUS_MENU = 10
		ACTION_ENTER = 7

		global exit_requested
		global movie_file
		if action == ACTION_PREVIOUS_MENU:
			xbmc.Player().stop()
			exit_requested = True
			self.close()

		if action == ACTION_ENTER:
			self.play_control = self.getControl(30003)
			self.name_control = self.getControl(30002)
			self.removeControl(self.play_control)
			self.removeControl(self.name_control)
			exit_requested = True
			xbmc.Player().stop()
			movie_file = self.movieFile
			self.close()
			
class blankscreen(xbmcgui.Window):
	def __init__(self,):
		pass
		
class XBMCPlayer(xbmc.Player):
	def __init__( self, *args, **kwargs ):
		pass
	def onPlayBackStarted(self):
		xbmc.log( 'Playbackstarted' )
	
	def onPlayBackStopped(self):
		global exit_requested
		
def playTrailers():
	bs=blankscreen()
	bs.show()
	global exit_requested
	global movie_file
	movie_file = ''
	exit_requested = False
	player = XBMCPlayer()
	xbmc.log('Getting Trailers')
	DO_CURTIANS = addon.getSetting('do_animation')
	DO_EXIT = addon.getSetting('do_exit')
	NUMBER_TRAILERS =  int(addon.getSetting('number_trailers'))
	if DO_CURTIANS == 'true':
		player.play(open_curtain_path)
		while player.isPlaying():
			xbmc.sleep(250)
	trailercount = 0
	while not exit_requested:
		for x in xrange(0, NUMBER_TRAILERS):
			myMovieWindow = movieWindow('script-trailerwindow.xml', addon_path,'default',)
			myMovieWindow.doModal()
			del myMovieWindow
			if exit_requested:
				break
		if not exit_requested:
			if DO_CURTIANS == 'true':
				player.play(close_curtain_path)
				while player.isPlaying():
					xbmc.sleep(250)
		exit_requested=True
	if not movie_file == '':
		xbmc.Player(0).play(movie_file)
	movie_file = ''
	del bs
		
filtergenre = False
if do_genre == 'true':
	filtergenre = askGenres()
	
success = False
if filtergenre:
	success, selectedGenre = selectGenre()

if success:
	trailers = getTrailers(selectedGenre)
else:
	trailers = getTrailers("")

playTrailers()

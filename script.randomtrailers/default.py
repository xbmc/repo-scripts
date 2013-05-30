# Random trailer player
#
# Author - kzeleny
# Version - 1.0.1
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

xbmc.log('do curtains = ' + do_curtains)

path = addon.getAddonInfo('path')
resources_path = xbmc.translatePath( os.path.join( path, 'resources' ) ).decode('utf-8')
media_path = xbmc.translatePath( os.path.join( resources_path, 'media' ) ).decode('utf-8')
open_curtain_path = xbmc.translatePath( os.path.join( media_path, 'CurtainOpeningSequence.flv' ) ).decode('utf-8')
close_curtain_path = xbmc.translatePath( os.path.join( media_path, 'CurtainClosingSequence.flv' ) ).decode('utf-8')



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
  
  for movie in trailers["result"]["movies"]:
    # Let's get the movie genres
    # If we're only looking at unwatched movies then restrict list to those movies
    genres = movie["genre"]
    #  genres = movie["genre"].split(" / ")
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
  
def getTrailers():
	# get the raw JSON output
	trailerstring = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "properties": ["genre", "playcount", "file", "trailer"]}, "id": 1}')
	trailerstring = unicode(trailerstring, 'utf-8', errors='ignore')
	trailers = json.loads(trailerstring)
	return trailers

def getTrailerList(filterGenre,genre):
	moviegenre = []
	trailerList =[]
	for trailer in trailers["result"]["movies"]:
		trailergenre = trailer["genre"]
		if not trailer["trailer"] == '':
			if ( filterGenre and genre in trailergenre ) or not filterGenre:
				trailerList.append(trailer["trailer"])
	return trailerList

trailers = getTrailers()

filtergenre = askGenres()	
success = False
if filtergenre:
	success, selectedGenre = selectGenre()

if success:
	trailerList = getTrailerList(True, selectedGenre)
else:
	trailerList = getTrailerList(False,"")

random.shuffle(trailerList)
playlist = xbmc.PlayList(0)
playlist.clear()
trailercount = 0
if do_curtains == 'true':
	playlist.add(open_curtain_path)
for trailer in trailerList:

	trailercount = trailercount +1
	playlist.add(trailer)
	if trailercount == int(number_trailers):
		break
if do_curtains == 'true':
	playlist.add(close_curtain_path)
xbmc.Player().play(playlist)

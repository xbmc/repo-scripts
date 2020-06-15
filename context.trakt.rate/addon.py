# -*- coding: utf-8 -*-

import xbmc

def __getMediaType():
	if xbmc.getCondVisibility('Container.Content(tvshows)'):
		return "show"
	elif xbmc.getCondVisibility('Container.Content(seasons)'):
		return "season"
	elif xbmc.getCondVisibility('Container.Content(episodes)'):
		return "episode"
	elif xbmc.getCondVisibility('Container.Content(movies)'):
		return "movie"
	else:
		return None

if __name__ == '__main__':
	xbmc.executebuiltin("RunScript(script.trakt,action=rate,media_type=%s,dbid=%s)" % (__getMediaType(), xbmc.getInfoLabel("ListItem.DBID")))


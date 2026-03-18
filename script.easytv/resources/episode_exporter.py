#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
A script to copy all the latest episodes included in the EasyTV listview to a folder selected by the user.

Logging:
    Module: export
    Events:
        - export.start (INFO): Export operation started
        - export.complete (INFO): Export completed successfully
        - export.cancel (INFO): Export cancelled by user
        - export.file_fail (WARNING): Individual file export failed
"""

import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import sys
import shutil
import ast
import json
from typing import cast

# Import shared utilities
from resources.lib.utils import lang, json_query, get_logger, get_bool_setting
from resources.lib.ui.dialogs import show_confirm, show_select
from resources.lib.constants import (
    KODI_HOME_WINDOW_ID,
    EXPORT_COMPLETE_DELAY_MS,
    PROP_SHOWS_WITH_NEXT_EPISODES,
)


__addon__        = xbmcaddon.Addon('script.easytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
addon_path       = xbmcvfs.translatePath('special://home/addons')
log              = get_logger('export')
filter_enabled         = get_bool_setting('filter_enabled')
populate_by    = __setting__('populate_by')
playlist_source        = __setting__('playlist_source')
default_playlist = __setting__('playlist_file')

WINDOW           = xbmcgui.Window(KODI_HOME_WINDOW_ID)

try:
	spec_shows = ast.literal_eval(__setting__('selection'))
except (ValueError, SyntaxError):
	spec_shows = []


# JSON-RPC query for playlist files
plf = {"jsonrpc": "2.0", "id": 1, "method": "Files.GetDirectory",
       "params": {"directory": "special://profile/playlists/video/", "media": "video"}}


def playlist_selection_window():
	'''Launch Select Window populated with smart playlists'''
	result = json_query(plf, True)
	playlist_files = result.get('files') if result else None
	
	if playlist_files is not None:
		plist_files = dict((x['label'], x['file']) for x in playlist_files)
		playlist_list = sorted(plist_files.keys())
		inputchoice = show_select(lang(32104), playlist_list)
		if inputchoice >= 0:
			return plist_files[playlist_list[inputchoice]]
	return 'empty'


def get_files():
	''' entry point for the file retrieval process_stored
		follows the same logic as creating a listview.
		'''
	try:
		provided_shows = sys.argv[1].split(':-exporter-:')
		return provided_shows
	
	except (IndexError, AttributeError):

		if filter_enabled:

			if populate_by == '1':

				if playlist_source == '0':
					selected_pl = playlist_selection_window()
					population = {'playlist': selected_pl}

				else:
					#get setting for default_playlist
					if not default_playlist:
						population = {'none':''}
					else:
						population = {'playlist': default_playlist}
			else:
				population = {'usersel':spec_shows}
		else:
			population = {'none':''}

		stored_file_data_filtered = process_stored(population)

		return stored_file_data_filtered


def process_stored(population):
	''' this function allows for the optional conversion of playlists to showlists
		'''

	stored_file_data = get_TVshows()

	if 'playlist' in population:
		extracted_showlist = convert_pl_to_showlist(population['playlist'])
	elif 'usersel' in population:
		extracted_showlist = population['usersel']
	else:
		extracted_showlist = False

	if extracted_showlist:
		stored_file_data_filtered  = [x[0] for x in stored_file_data if x[1] in extracted_showlist]
	else:
		stored_file_data_filtered = [x[0] for x in stored_file_data]

	log.debug("Process stored completed", file_count=len(stored_file_data_filtered))

	return stored_file_data_filtered


def convert_pl_to_showlist(pop):
	''' converts the playlist to a showlist
		'''

	# derive filtered_showids from smart playlist
	filename = os.path.split(pop)[1]
	clean_path = 'special://profile/playlists/video/' + filename

	#retrieve the shows in the supplied playlist, save their ids to a list
	plf  = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", 		"params": {"directory": "special://profile/playlists/video/", "media": "video"}}
	plf['params']['directory'] = clean_path

	playlist_contents = json_query(plf, True)

	if 'files' not in playlist_contents:
		log.warning("No files found in playlist", event="export.empty_playlist")
		sys.exit()
	else:
		if not playlist_contents['files']:
			log.warning("Playlist contains no files", event="export.empty_playlist")
			sys.exit()
		else:
			for x in playlist_contents['files']:
				filtered_showids = [x['id'] for x in playlist_contents['files'] if x['type'] == 'tvshow']
				log.debug("Shows extracted from playlist", show_ids=filtered_showids)
				if not filtered_showids:
					log.warning("No TV shows found in playlist", event="export.no_shows")
					sys.exit()

	#returns the list of all and filtered shows and episodes
	return filtered_showids


def get_TVshows():
	''' gets all the TV shows that have unwatched episodes, and gets the union of that list with the list that is stored
		'''

	#get the most recent info on inProgress TV shows, cross-check it with what is currently stored
	query          = '{"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"filter": {"field": "playcount", "operator": "is", "value": "0" },"properties": ["lastplayed"], "sort": {"order": "descending", "method": "lastplayed"} },"id": "1" }'

	shows_retrieved = xbmc.executeJSONRPC(query)
	shows_retrieved = json.loads(shows_retrieved)

	log.debug("TV shows query completed")

	if 'result' in shows_retrieved and 'tvshows' in shows_retrieved["result"] and shows_retrieved['result']['tvshows']:
		shows_retrieved = shows_retrieved['result']['tvshows']
	else:
		shows_retrieved = {}


	shows_from_service = WINDOW.getProperty(PROP_SHOWS_WITH_NEXT_EPISODES)

	if shows_from_service:
		show_id_list = ast.literal_eval(shows_from_service)
		shows_stored = [int(x) for x in show_id_list]
	else:
		log.warning("Service not running during export", event="export.service_missing")
		dialog.ok('EasyTV', lang(32115) + '\n' + lang(32116))
		sys.exit()

	active_shows = [x['tvshowid'] for x in shows_retrieved if x['tvshowid'] in shows_stored]

	stored_file_data = [[WINDOW.getProperty("EasyTV.%s.File"  % x),x] for x in active_shows]

	log.debug("TV shows retrieved", show_count=len(stored_file_data))

	return stored_file_data


def Main():
	try:
		# open location selection window
		location = cast(str, dialog.browse(3,lang(32180),'files'))

		log.info("Export started", event="export.start", location=location)

		# get file of selected shows
		file_list = get_files()


		# load list as normal, but on click, each show is copied over (and remains highlighted)
		# the top option is to export all

		progress_dialog = xbmcgui.DialogProgress()
		progress_dialog.create('EasyTV', lang(32183))

		sizes = []
		running_size = 0
		log.debug("Files to export", file_count=len(file_list), files=file_list)
		for f in file_list:
			try:
				sizes.append(os.path.getsize(f))
			except OSError:
				sizes.append(0)

		failures = []

		for i, video_file in enumerate(file_list):

			if (progress_dialog.iscanceled()):
				log.info("Export cancelled by user", event="export.cancel")
				sys.exit()

			prog = running_size / float(sum(sizes) or 1)

			fn = os.path.basename(video_file)

			progress_dialog.update(int(prog * 100.0), '{} {}'.format(lang(32184), fn))

			try:
				if not os.path.isfile(os.path.join(location, fn)):
					shutil.copyfile(video_file, os.path.join(location, fn))
					log.debug("File exported", filename=fn)
				else:
					log.debug("File already exists at destination", filename=fn)
			except (OSError, IOError, shutil.Error):
				failures.append(fn)
				log.warning("File export failed", event="export.file_fail", filename=fn)

			running_size += sizes[i]

		progress_dialog.close()

		if failures:
			# 32181: "Some files failed to transfer", 32182: "Would you like to see them?"
			ans = show_confirm('EasyTV', lang(32181) + '\n' + lang(32182))

			if ans:
				# populate list view with file names in alphabetical order
				log.debug("Displaying failed files to user", failure_count=len(failures))

				failures.sort()

				show_select('EasyTV', failures)
		else:
			xbmc.sleep(EXPORT_COMPLETE_DELAY_MS)
			dialog.ok('EasyTV',lang(32185))

			log.info("Export completed successfully", event="export.complete")
	except SystemExit:
		raise  # Let sys.exit() propagate
	except Exception:
		log.exception("Unhandled error in episode exporter", event="export.crash")



if __name__ == "__main__":

	Main()


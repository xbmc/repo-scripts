#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import xbmcaddon


ADDON = xbmcaddon.Addon()

# Question strings - movie
Q_WHAT_MOVIE_IS_THIS = 32400
Q_WHAT_MOVIE_IS_ACTOR_NOT_IN = 32401
Q_WHAT_YEAR_WAS_MOVIE_RELEASED = 32402
Q_WHAT_TAGLINE_BELONGS_TO_MOVIE = 32403
Q_WHO_DIRECTED_THIS_MOVIE = 32404
Q_WHAT_STUDIO_RELEASED_MOVIE = 32405
Q_WHAT_ACTOR_IS_THIS = 32406
Q_WHO_PLAYS_ROLE_IN_MOVIE = 32407
Q_WHO_VOICES_ROLE_IN_MOVIE = 32408
Q_WHAT_MOVIE_IS_THIS_QUOTE_FROM = 32409
Q_WHAT_MOVIE_IS_THE_NEWEST = 32410
Q_WHAT_MOVIE_IS_NOT_DIRECTED_BY = 32411
Q_WHAT_ACTOR_IS_IN_THESE_MOVIES = 32412
Q_WHAT_MOVIE_HAS_THE_LONGEST_RUNTIME = 32414

# Question strings - TV show
Q_WHAT_TVSHOW_IS_THIS = 32450
Q_WHAT_SEASON_IS_THIS = 32451
Q_WHAT_EPISODE_IS_THIS = 32452
Q_WHEN_WAS_TVSHOW_FIRST_AIRED = 32454
Q_WHO_PLAYS_ROLE_IN_TVSHOW = 32455
Q_WHO_VOICES_ROLE_IN_TVSHOW = 32456
Q_WHAT_TVSHOW_IS_THIS_QUOTE_FROM = 32457

# Question strings - Music
Q_WHAT_SONG_IS_THIS = 32475
Q_WHO_MADE_THE_SONG = 32476
Q_WHO_MADE_THE_ALBUM = 32477

# Menu strings
M_PLAY_MOVIE_QUIZ = 32100
M_PLAY_TVSHOW_QUIZ = 32101
M_PLAY_MUSIC_QUIZ = 32102
M_SETTINGS = 32103
M_ABOUT = 32104
M_EXIT = 32105
M_DOWNLOAD_IMDB = 32106
M_DOWNLOADING_IMDB_DATA = 32107
M_RETRIEVED_X_OF_Y_MB = 32108
M_DOWNLOAD_IMDB_INFO = 32109
M_FILE_X_OF_Y = 32110
M_DOWNLOAD_COMPLETE = 32111
M_ABOUT_TEXT_BODY = 32112

# Error strings
E_WARNING = 32013
E_ALL_MOVIE_QUESTIONS_DISABLED = 32014
E_ALL_TVSHOW_QUESTIONS_DISABLED = 32015
E_QUIZ_TYPE_NOT_AVAILABLE = 32016
E_REQUIREMENTS_MISSING = 32017
E_HAS_NO_CONTENT = 32018
E_ONLY_WATCHED = 32019
E_MOVIE_RATING_LIMIT = 32020
E_TVSHOW_RATING_LIMIT = 32021


def strings(*args):
    return ' '.join([ADDON.getLocalizedString(arg) for arg in args])

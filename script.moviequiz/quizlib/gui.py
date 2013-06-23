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
import random

import threading
import os
import re
import time
import datetime

import xbmc
import xbmcgui

import game
import question
import player
import highscore
import library

import buggalo

from strings import *

# Constants from [xbmc]/xbmc/guilib/Key.h
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10

ACTION_REMOTE0 = 58
ACTION_REMOTE1 = 59
ACTION_REMOTE2 = 60
ACTION_REMOTE3 = 61
ACTION_REMOTE4 = 62
ACTION_REMOTE5 = 63
ACTION_REMOTE6 = 64
ACTION_REMOTE7 = 65
ACTION_REMOTE8 = 66
ACTION_REMOTE9 = 67

ACTION_NAV_BACK = 92

ACTION_JUMP_SMS2 = 142
ACTION_JUMP_SMS3 = 143
ACTION_JUMP_SMS4 = 144
ACTION_JUMP_SMS5 = 145
ACTION_JUMP_SMS6 = 146
ACTION_JUMP_SMS7 = 147
ACTION_JUMP_SMS8 = 148
ACTION_JUMP_SMS9 = 149

RESOURCES_PATH = os.path.join(ADDON.getAddonInfo('path'), 'resources', )
AUDIO_CORRECT = os.path.join(RESOURCES_PATH, 'audio', 'correct.wav')
AUDIO_WRONG = os.path.join(RESOURCES_PATH, 'audio', 'wrong.wav')
BACKGROUND_MOVIE = os.path.join(RESOURCES_PATH, 'skins', 'Default', 'media', 'quiz-background-movie.jpg')
BACKGROUND_TV = os.path.join(RESOURCES_PATH, 'skins', 'Default', 'media', 'quiz-background-tvshows.jpg')
NO_PHOTO_IMAGE = os.path.join(RESOURCES_PATH, 'skins', 'Default', 'media', 'quiz-no-photo.png')

MPAA_RATINGS = ['R', 'Rated R', 'PG-13', 'Rated PG-13', 'PG', 'Rated PG', 'G', 'Rated G']
CONTENT_RATINGS = ['TV-MA', 'TV-14', 'TV-PG', 'TV-G', 'TV-Y7-FV', 'TV-Y7', 'TV-Y']


class MenuGui(xbmcgui.WindowXMLDialog):
    C_MENU_VISIBILITY = 4000
    C_MENU_LIST = 4001
    C_MENU_SELECTION_VISIBILITY = 4002
    C_MENU_SELECTION_START = 4003
    C_MENU_SELECTION_OPTION = 4004
    C_MENU_SELECTION_BACK = 4005

    C_MENU_HIGHSCORE_VISIBILITY = 4010
    C_MENU_HIGHSCORE_LOCAL_GLOBAL = 4011
    C_MENU_HIGHSCORE_GAME_TYPE = 4012
    C_MENU_HIGHSCORE_GAME_LIMIT = 4013
    C_MENU_HIGHSCORE_BACK = 4014

    C_MENU_CURRENT_PLAYER = 5000
    C_MENU_GAMES_PLAYED_LOCAL = 5001
    C_MENU_GAMES_PLAYED_COUNTRY = 5002
    C_MENU_GAMES_PLAYED_GLOBAL = 5003
    C_MENU_GAMES_PLAYED_COUNTRY_ICON = 5004

    C_MENU_ABOUT_VISIBILITY = 6000
    C_MENU_ABOUT_TEXT = 6001

    C_MENU_HIGHSCORE_TABLE_VISIBILITY = 7000
    C_MENU_HIGHSCORE_TABLE = 7001

    STATE_MAIN = 1
    STATE_MOVIE_QUIZ = 2
    STATE_TV_QUIZ = 3
    STATE_PLAYER = 4
    STATE_ABOUT = 5
    STATE_MOVIE_TIME = 6
    STATE_MOVIE_QUESTION = 7
    STATE_TVSHOW_TIME = 8
    STATE_TVSHOW_QUESTION = 9
    STATE_HIGHSCORE = 10
    STATE_EXIT = 99

    QUESTION_SUB_TYPES = [
        {'limit': '5', 'text': strings(M_X_QUESTIONS, '5')},
        {'limit': '10', 'text': strings(M_X_QUESTIONS, '10')},
        {'limit': '15', 'text': strings(M_X_QUESTIONS, '15')},
        {'limit': '25', 'text': strings(M_X_QUESTIONS, '25')},
        {'limit': '50', 'text': strings(M_X_QUESTIONS, '50')},
        {'limit': '100', 'text': strings(M_X_QUESTIONS, '100')}
    ]
    TIME_SUB_TYPES = [
        {'limit': '1', 'text': strings(M_ONE_MINUTE)},
        {'limit': '2', 'text': strings(M_X_MINUTES, '2')},
        {'limit': '3', 'text': strings(M_X_MINUTES, '3')},
        {'limit': '5', 'text': strings(M_X_MINUTES, '5')},
        {'limit': '10', 'text': strings(M_X_MINUTES, '10')},
        {'limit': '15', 'text': strings(M_X_MINUTES, '15')},
        {'limit': '30', 'text': strings(M_X_MINUTES, '30')}
    ]

    GAME_TYPES = [
        game.UnlimitedGame(game.GAMETYPE_MOVIE, -1, True),

        game.QuestionLimitedGame(game.GAMETYPE_MOVIE, -1, True, 5),
        game.QuestionLimitedGame(game.GAMETYPE_MOVIE, -1, True, 10),
        game.QuestionLimitedGame(game.GAMETYPE_MOVIE, -1, True, 15),
        game.QuestionLimitedGame(game.GAMETYPE_MOVIE, -1, True, 25),
        game.QuestionLimitedGame(game.GAMETYPE_MOVIE, -1, True, 50),
        game.QuestionLimitedGame(game.GAMETYPE_MOVIE, -1, True, 100),

        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 1),
        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 2),
        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 3),
        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 5),
        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 10),
        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 15),
        game.TimeLimitedGame(game.GAMETYPE_MOVIE, -1, True, 30),
    ]

    def __new__(cls, quizGui):
        return super(MenuGui, cls).__new__(cls, 'script-moviequiz-menu.xml', ADDON.getAddonInfo('path'))

    def __init__(self, quizGui):
        super(MenuGui, self).__init__()
        self.quizGui = quizGui
        self.trivia = None
        self.state = MenuGui.STATE_MAIN

        self.moviesEnabled = True
        self.tvShowsEnabled = True

        self.userId = -1
        self.statisticsLabel = None
        self.localHighscore = highscore.LocalHighscoreDatabase(xbmc.translatePath(ADDON.getAddonInfo('profile')))
        self.globalHighscore = highscore.GlobalHighscoreDatabase(ADDON.getAddonInfo('version'))
        self.globalHighscorePage = 0

        self.highscoreGlobal = None
        self.highscoreType = None
        self.highscoreGameType = None

    @buggalo.buggalo_try_except()
    def onInit(self):
        self.trivia = []

        movies = library.getMovies(['art']).limitTo(44).asList()
        posters = [movie['art']['poster'] for movie in movies if 'art' in movie and 'poster' in movie['art']]
        if posters:
            for idx in range(0, 44):
                self.getControl(1000 + idx).setImage(posters[idx % len(posters)])

        users = self.localHighscore.getUsers()
        if not users:
            self.userId = self.onAddNewUser(createDefault=True)
            users = self.localHighscore.getUsers()

        self.userId = users[0]['id']
        gamesPlayed = self.localHighscore.getGamesPlayed(self.userId)

        self.getControl(MenuGui.C_MENU_CURRENT_PLAYER).setLabel(users[0]['nickname'])
        self.getControl(MenuGui.C_MENU_GAMES_PLAYED_LOCAL).setLabel(str(gamesPlayed))

        # highscore menu
        listControl = self.getControl(MenuGui.C_MENU_HIGHSCORE_LOCAL_GLOBAL)
        item = xbmcgui.ListItem(strings(30703))
        item.setProperty('type', 'local')
        listControl.addItem(item)
        item = xbmcgui.ListItem(strings(30702))
        item.setProperty('type', 'global')
        listControl.addItem(item)

        listControl = self.getControl(MenuGui.C_MENU_HIGHSCORE_GAME_TYPE)
        item = xbmcgui.ListItem(strings(30810))
        item.setProperty('type', 'movie')
        listControl.addItem(item)
        item = xbmcgui.ListItem(strings(30811))
        item.setProperty('type', 'tvshow')
        listControl.addItem(item)

        listControl = self.getControl(MenuGui.C_MENU_HIGHSCORE_GAME_LIMIT)
        for gameType in self.GAME_TYPES:
            if isinstance(gameType, game.UnlimitedGame):
                listControl.addItem(xbmcgui.ListItem(strings(M_UNLIMITED)))
            elif isinstance(gameType, game.QuestionLimitedGame):
                listControl.addItem(xbmcgui.ListItem(strings(M_X_QUESTIONS, gameType.getGameSubType())))
            elif isinstance(gameType, game.TimeLimitedGame):
                listControl.addItem(xbmcgui.ListItem(strings(M_X_MINUTES, gameType.getGameSubType())))
            else:
                listControl.addItem(xbmcgui.ListItem(repr(gameType)))

        # Check preconditions
        hasMovies = library.hasMovies()
        hasTVShows = library.hasTVShows()

        if not hasMovies and not hasTVShows:
            self.close()
            self.quizGui.close()
            # Must have at least one movie or tvshow
            xbmcgui.Dialog().ok(strings(E_REQUIREMENTS_MISSING), strings(E_REQUIREMENTS_MISSING_LINE1),
                                strings(E_REQUIREMENTS_MISSING_LINE2), strings(E_REQUIREMENTS_MISSING_LINE3))
            return

        if not library.isAnyVideosWatched() and ADDON.getSetting(SETT_ONLY_WATCHED_MOVIES) == 'true':
            # Only watched movies requires at least one watched video files
            xbmcgui.Dialog().ok(strings(E_REQUIREMENTS_MISSING), strings(E_ONLY_WATCHED_LINE1),
                                strings(E_ONLY_WATCHED_LINE2), strings(E_ONLY_WATCHED_LINE3))
            ADDON.setSetting(SETT_ONLY_WATCHED_MOVIES, 'false')

        if not library.isAnyMPAARatingsAvailable() and ADDON.getSetting(SETT_MOVIE_RATING_LIMIT_ENABLED) == 'true':
            # MPAA rating requires ratings to be available in database
            xbmcgui.Dialog().ok(strings(E_REQUIREMENTS_MISSING), strings(E_MOVIE_RATING_LIMIT_LINE1),
                                strings(E_MOVIE_RATING_LIMIT_LINE2), strings(E_MOVIE_RATING_LIMIT_LINE3))
            ADDON.setSetting(SETT_MOVIE_RATING_LIMIT_ENABLED, 'false')

        if not library.isAnyContentRatingsAvailable() and ADDON.getSetting(SETT_TVSHOW_RATING_LIMIT_ENABLED) == 'true':
            # Content rating requires ratings to be available in database
            xbmcgui.Dialog().ok(strings(E_REQUIREMENTS_MISSING), strings(E_TVSHOW_RATING_LIMIT_LINE1),
                                strings(E_TVSHOW_RATING_LIMIT_LINE2), strings(E_TVSHOW_RATING_LIMIT_LINE3))
            ADDON.setSetting(SETT_TVSHOW_RATING_LIMIT_ENABLED, 'false')

        self.moviesEnabled = bool(hasMovies and question.isAnyMovieQuestionsEnabled())
        self.tvShowsEnabled = bool(hasTVShows and question.isAnyTVShowQuestionsEnabled())

        if not question.isAnyMovieQuestionsEnabled():
            xbmcgui.Dialog().ok(strings(E_WARNING), strings(E_ALL_MOVIE_QUESTIONS_DISABLED),
                                strings(E_QUIZ_TYPE_NOT_AVAILABLE))

        if not question.isAnyTVShowQuestionsEnabled():
            xbmcgui.Dialog().ok(strings(E_WARNING), strings(E_ALL_TVSHOW_QUESTIONS_DISABLED),
                                strings(E_QUIZ_TYPE_NOT_AVAILABLE))


        self.updateMenu()
        self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(False)

        threading.Timer(0.1, self.loadStatistics).start()

    def loadStatistics(self):
        globalHighscore = highscore.GlobalHighscoreDatabase(ADDON.getAddonInfo('version'))
        statistics = globalHighscore.getStatistics()

        self.statisticsLabel = strings(M_STATISTICS, (
            statistics['users']['unique_ips'],
            statistics['users']['unique_countries'],
            statistics['quiz']['total_games'],
            statistics['quiz']['total_questions'],
            statistics['quiz']['total_correct_answers'],
            statistics['quiz']['correct_percentage']
        ))

        self.getControl(MenuGui.C_MENU_GAMES_PLAYED_COUNTRY).setLabel(str(statistics['quiz']['total_games_in_country']))
        self.getControl(MenuGui.C_MENU_GAMES_PLAYED_COUNTRY_ICON).setImage(str(statistics['quiz']['countryIconUrl']))
        self.getControl(MenuGui.C_MENU_GAMES_PLAYED_GLOBAL).setLabel(str(statistics['quiz']['total_games']))

    def reloadHighscores(self):
        idx = self.getControl(MenuGui.C_MENU_HIGHSCORE_GAME_LIMIT).getSelectedPosition()
        highscoreGameType = MenuGui.GAME_TYPES[idx]

        if self.getControl(MenuGui.C_MENU_HIGHSCORE_GAME_TYPE).getSelectedItem().getProperty('type') == 'movie':
            highscoreType = game.GAMETYPE_MOVIE
        else:
            highscoreType = game.GAMETYPE_TVSHOW

        if self.getControl(MenuGui.C_MENU_HIGHSCORE_LOCAL_GLOBAL).getSelectedItem().getProperty('type') == 'global':
            highscoreGlobal = True
        else:
            highscoreGlobal = False

        if self.highscoreGameType == highscoreGameType and self.highscoreGlobal == highscoreGlobal and self.highscoreType == highscoreType:
            return

        print 'reloading highscores...'

        self.highscoreGlobal = highscoreGlobal
        self.highscoreType = highscoreType
        self.highscoreGameType = highscoreGameType

        self.getControl(MenuGui.C_MENU_HIGHSCORE_TABLE_VISIBILITY).setVisible(True)
        listControl = self.getControl(self.C_MENU_HIGHSCORE_TABLE)
        listControl.reset()

        if self.highscoreGlobal:
            entries = self.globalHighscore.getHighscores(self.highscoreGameType, self.globalHighscorePage)
        else:
            entries = self.localHighscore.getHighscores(self.highscoreGameType)

        items = list()
        for idx, entry in enumerate(entries):
            item = xbmcgui.ListItem(entry['nickname'])
            item.setProperty('position', str(entry['position']))
            item.setProperty('score', str(entry['score']))
            if self.highscoreGlobal:
                item.setProperty('countryIconUrl', entry['countryIconUrl'])
                item.setProperty('timestamp', entry['timeAgo'])
            else:
                item.setProperty('timestamp', entry['timestamp'][0:10])
            items.append(item)

            #if self.isClosing:
            #    return

        if not items:
            items.append(xbmcgui.ListItem('No entries'))

        listControl.addItems(items)
        self.getControl(MenuGui.C_MENU_HIGHSCORE_TABLE_VISIBILITY).setVisible(False)

    def close(self):
        # hide menus
        self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(True)
        self.getControl(MenuGui.C_MENU_SELECTION_VISIBILITY).setVisible(True)
        self.getControl(MenuGui.C_MENU_HIGHSCORE_VISIBILITY).setVisible(True)
        self.getControl(MenuGui.C_MENU_HIGHSCORE_TABLE_VISIBILITY).setVisible(True)
        self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(True)

        if self.localHighscore:
            self.localHighscore.close()

        super(MenuGui, self).close()

    @buggalo.buggalo_try_except()
    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_SELECTION_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_HIGHSCORE_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_HIGHSCORE_TABLE_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(True)
            xbmc.sleep(350)

            if MenuGui.STATE_MAIN == self.state:
                self.quizGui.close()
                self.close()
                return

            elif self.state in [MenuGui.STATE_MOVIE_QUIZ, MenuGui.STATE_TV_QUIZ, MenuGui.STATE_HIGHSCORE, MenuGui.STATE_ABOUT, MenuGui.STATE_PLAYER]:
                self.state = MenuGui.STATE_MAIN
                self.updateMenu()

            elif self.state in [MenuGui.STATE_MOVIE_TIME, MenuGui.STATE_MOVIE_QUESTION]:
                self.state = MenuGui.STATE_MOVIE_QUIZ
                self.updateMenu()

            elif self.state in [MenuGui.STATE_TVSHOW_TIME, MenuGui.STATE_TVSHOW_QUESTION]:
                self.state = MenuGui.STATE_TV_QUIZ
                self.updateMenu()

            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(False)

        elif MenuGui.STATE_HIGHSCORE == self.state:
            self.reloadHighscores()

        #elif action.getId() ==

    def updateMenu(self):
        listControl = self.getControl(MenuGui.C_MENU_LIST)
        listControl.reset()
        items = []
        if self.state == MenuGui.STATE_MAIN:
            if self.moviesEnabled:
                item = xbmcgui.ListItem(strings(30100))
                item.setProperty('state', str(MenuGui.STATE_MOVIE_QUIZ))
                items.append(item)
            if self.tvShowsEnabled:
                item = xbmcgui.ListItem(strings(30101))
                item.setProperty('state', str(MenuGui.STATE_TV_QUIZ))
                items.append(item)

            item = xbmcgui.ListItem(strings(30104))
            item.setProperty('state', str(MenuGui.STATE_PLAYER))
            items.append(item)
            item = xbmcgui.ListItem(strings(30102))
            item.setProperty('state', str(MenuGui.STATE_HIGHSCORE))
            items.append(item)
            item = xbmcgui.ListItem(strings(30801))
            item.setProperty('state', str(MenuGui.STATE_ABOUT))
            items.append(item)
            item = xbmcgui.ListItem(strings(30103))
            item.setProperty('state', str(MenuGui.STATE_EXIT))
            items.append(item)

        elif self.state in [MenuGui.STATE_MOVIE_QUIZ, MenuGui.STATE_TV_QUIZ]:
            items.append(xbmcgui.ListItem(strings(30602)))
            items.append(xbmcgui.ListItem(strings(30603)))
            items.append(xbmcgui.ListItem(strings(30604)))
            items.append(xbmcgui.ListItem(strings(M_GO_BACK)))

        elif self.state == MenuGui.STATE_ABOUT:
            items.append(xbmcgui.ListItem(strings(30801)))
            items.append(xbmcgui.ListItem(strings(30802)))
            items.append(xbmcgui.ListItem(strings(30803)))
            items.append(xbmcgui.ListItem(strings(M_GO_BACK)))

        elif self.state == MenuGui.STATE_PLAYER:
            item = xbmcgui.ListItem(strings(G_ADD_USER))
            item.setProperty('id', '-1')
            items.append(item)

            localHighscore = highscore.LocalHighscoreDatabase(xbmc.translatePath(ADDON.getAddonInfo('profile')))
            for user in localHighscore.getUsers():
                item = xbmcgui.ListItem(user['nickname'])
                item.setProperty('id', str(user['id']))
                items.append(item)
            localHighscore.close()

        listControl.addItems(items)
        self.setFocus(listControl)

    @buggalo.buggalo_try_except()
    def onClick(self, controlId):
        """
        @param controlId: id of the control that was clicked
        @type controlId: int
        """
        print 'onClick'

        if controlId == MenuGui.C_MENU_LIST:
            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_SELECTION_VISIBILITY).setVisible(True)
            xbmc.sleep(350)

            idx = self.getControl(MenuGui.C_MENU_LIST).getSelectedPosition()
            visibilityControlId = MenuGui.C_MENU_VISIBILITY

            if self.state == MenuGui.STATE_MAIN:
                item = self.getControl(MenuGui.C_MENU_LIST).getSelectedItem()
                self.state = int(item.getProperty('state'))

                if self.state == MenuGui.STATE_HIGHSCORE:
                    self.highscoreGlobal = None
                    self.highscoreType = None
                    self.highscoreGameType = None

                    self.getControl(MenuGui.C_MENU_HIGHSCORE_VISIBILITY).setVisible(False)
                    self.setFocusId(MenuGui.C_MENU_HIGHSCORE_LOCAL_GLOBAL)
                    self.reloadHighscores()
                    return

                elif self.state == MenuGui.STATE_ABOUT:
                    f = open(os.path.join(ADDON.getAddonInfo('path'), 'about.txt'))
                    self.getControl(MenuGui.C_MENU_ABOUT_TEXT).setText(f.read())
                    f.close()
                    self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(False)

                elif self.state == MenuGui.STATE_EXIT:
                    self.quizGui.close()
                    self.close()
                    return
                self.updateMenu()

            elif self.state == MenuGui.STATE_MOVIE_QUIZ:
                if idx == 0:  # unlimited
                    gameInstance = game.UnlimitedGame(game.GAMETYPE_MOVIE, self.userId, interactive=True)
                    self.close()
                    self.quizGui.newGame(gameInstance)
                    return

                elif idx == 1:  # time limited
                    self.state = MenuGui.STATE_MOVIE_TIME
                    visibilityControlId = MenuGui.C_MENU_SELECTION_VISIBILITY
                    self.setFocusId(MenuGui.C_MENU_SELECTION_START)

                    listControl = self.getControl(MenuGui.C_MENU_SELECTION_OPTION)
                    listControl.reset()
                    for subTypes in self.TIME_SUB_TYPES:
                        item = xbmcgui.ListItem(subTypes['text'])
                        item.setProperty("limit", subTypes['limit'])
                        listControl.addItem(item)

                elif idx == 2:  # question limited
                    self.state = MenuGui.STATE_MOVIE_QUESTION
                    visibilityControlId = MenuGui.C_MENU_SELECTION_VISIBILITY
                    self.setFocusId(MenuGui.C_MENU_SELECTION_START)

                    listControl = self.getControl(MenuGui.C_MENU_SELECTION_OPTION)
                    listControl.reset()
                    for subTypes in self.QUESTION_SUB_TYPES:
                        item = xbmcgui.ListItem(subTypes['text'])
                        item.setProperty("limit", subTypes['limit'])
                        listControl.addItem(item)

                elif idx == 3:  # main menu
                    self.state = MenuGui.STATE_MAIN
                    self.updateMenu()

            elif self.state == MenuGui.STATE_TV_QUIZ:
                if idx == 0:  # unlimited
                    gameInstance = game.UnlimitedGame(game.GAMETYPE_TVSHOW, self.userId, interactive=True)
                    self.close()
                    self.quizGui.newGame(gameInstance)
                    return

                elif idx == 1:  # time limited
                    self.state = MenuGui.STATE_TVSHOW_TIME
                    visibilityControlId = MenuGui.C_MENU_SELECTION_VISIBILITY
                    self.setFocusId(MenuGui.C_MENU_SELECTION_START)

                    listControl = self.getControl(MenuGui.C_MENU_SELECTION_OPTION)
                    listControl.reset()
                    for subTypes in self.TIME_SUB_TYPES:
                        item = xbmcgui.ListItem(subTypes['text'])
                        item.setProperty("limit", subTypes['limit'])
                        listControl.addItem(item)

                elif idx == 2:  # question limited
                    self.state = MenuGui.STATE_TVSHOW_QUESTION
                    visibilityControlId = MenuGui.C_MENU_SELECTION_VISIBILITY
                    self.setFocusId(MenuGui.C_MENU_SELECTION_START)

                    listControl = self.getControl(MenuGui.C_MENU_SELECTION_OPTION)
                    listControl.reset()
                    for subTypes in self.QUESTION_SUB_TYPES:
                        item = xbmcgui.ListItem(subTypes['text'])
                        item.setProperty("limit", subTypes['limit'])
                        listControl.addItem(item)

                elif idx == 3:  # main menu
                    self.state = MenuGui.STATE_MAIN
                    self.updateMenu()

            elif self.state == MenuGui.STATE_PLAYER:
                item = self.getControl(MenuGui.C_MENU_LIST).getSelectedItem()
                if item.getProperty('id') == '-1':
                    self.userId = self.onAddNewUser()

                elif item.getProperty('id') is not None:
                    self.userId = item.getProperty('id')

                localHighscore = highscore.LocalHighscoreDatabase(xbmc.translatePath(ADDON.getAddonInfo('profile')))
                nickname = localHighscore.getNickname(self.userId)
                gamesPlayed = localHighscore.getGamesPlayed(self.userId)
                self.getControl(MenuGui.C_MENU_GAMES_PLAYED_LOCAL).setLabel(str(gamesPlayed))

                localHighscore.close()

                self.getControl(MenuGui.C_MENU_CURRENT_PLAYER).setLabel(nickname)
                self.userId = item.getProperty('id')

                self.state = MenuGui.STATE_MAIN
                self.updateMenu()

            elif self.state == MenuGui.STATE_ABOUT:
                self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(True)
                xbmc.sleep(250)

                if idx == 0:
                    f = open(os.path.join(ADDON.getAddonInfo('path'), 'about.txt'))
                    self.getControl(MenuGui.C_MENU_ABOUT_TEXT).setText(f.read())
                    f.close()
                    self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(False)

                elif idx == 1:
                    f = open(os.path.join(ADDON.getAddonInfo('changelog')))
                    self.getControl(MenuGui.C_MENU_ABOUT_TEXT).setText(f.read())
                    f.close()
                    self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(False)
                elif idx == 2:
                    self.getControl(MenuGui.C_MENU_ABOUT_TEXT).setText(self.statisticsLabel)
                    self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(False)

                elif idx == 3:
                    self.getControl(MenuGui.C_MENU_ABOUT_VISIBILITY).setVisible(True)
                    self.state = MenuGui.STATE_MAIN
                    self.updateMenu()

            self.getControl(visibilityControlId).setVisible(False)

        elif MenuGui.C_MENU_SELECTION_START == controlId:
            listControl = self.getControl(MenuGui.C_MENU_SELECTION_OPTION)
            item = listControl.getSelectedItem()
            limit = int(item.getProperty('limit'))

            gameInstance = None
            if MenuGui.STATE_MOVIE_TIME == self.state:
                gameInstance = game.TimeLimitedGame(game.GAMETYPE_MOVIE, self.userId, interactive=True, timeLimitMinutes=limit)
            elif MenuGui.STATE_MOVIE_QUESTION == self.state:
                gameInstance = game.QuestionLimitedGame(game.GAMETYPE_MOVIE, self.userId, interactive=True, questionLimit=limit)
            elif MenuGui.STATE_TVSHOW_TIME == self.state:
                gameInstance = game.TimeLimitedGame(game.GAMETYPE_TVSHOW, self.userId, interactive=True, timeLimitMinutes=limit)
            elif MenuGui.STATE_TVSHOW_QUESTION == self.state:
                gameInstance = game.QuestionLimitedGame(game.GAMETYPE_TVSHOW, self.userId, interactive=True, questionLimit=limit)
            if gameInstance:
                self.close()
                self.quizGui.newGame(gameInstance)
                return

        elif MenuGui.C_MENU_SELECTION_OPTION == controlId:
            listControl = self.getControl(MenuGui.C_MENU_SELECTION_OPTION)
            idx = listControl.getSelectedPosition()
            if idx + 1 < listControl.size():
                listControl.selectItem(idx + 1)
            else:
                listControl.selectItem(0)

        elif MenuGui.C_MENU_SELECTION_BACK == controlId:
            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_SELECTION_VISIBILITY).setVisible(True)
            xbmc.sleep(350)

            if self.state in [MenuGui.STATE_MOVIE_QUESTION, MenuGui.STATE_MOVIE_TIME]:
                self.state = MenuGui.STATE_MOVIE_QUIZ
            elif self.state in [MenuGui.STATE_TVSHOW_QUESTION, MenuGui.STATE_TVSHOW_TIME]:
                self.state = MenuGui.STATE_TV_QUIZ
            else:
                self.state = MenuGui.STATE_MAIN
            self.updateMenu()
            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(False)

        elif MenuGui.C_MENU_HIGHSCORE_BACK == controlId:
            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_HIGHSCORE_VISIBILITY).setVisible(True)
            self.getControl(MenuGui.C_MENU_HIGHSCORE_TABLE_VISIBILITY).setVisible(True)
            xbmc.sleep(350)
            self.state = MenuGui.STATE_MAIN
            self.updateMenu()
            self.getControl(MenuGui.C_MENU_VISIBILITY).setVisible(False)

    @buggalo.buggalo_try_except()
    def onFocus(self, controlId):
        pass

    def onAddNewUser(self, createDefault=False):
        keyboard = xbmc.Keyboard('', strings(G_WELCOME_ENTER_NICKNAME))
        keyboard.doModal()
        name = None
        if keyboard.isConfirmed() and len(keyboard.getText().strip()) > 0:
            name = keyboard.getText().strip()
        elif createDefault:
            name = 'Unknown player'

        if name is not None:
            localHighscore = highscore.LocalHighscoreDatabase(xbmc.translatePath(ADDON.getAddonInfo('profile')))
            userId = localHighscore.createUser(name)
            localHighscore.close()

            return userId

        return None


class QuizGui(xbmcgui.WindowXML):
    C_MAIN_FIRST_ANSWER = 4000
    C_MAIN_LAST_ANSWER = 4003
    C_MAIN_REPLAY = 4010
    C_MAIN_EXIT = 4011
    C_MAIN_LOADING = 4020
    C_MAIN_CORRECT_SCORE = 4101
    C_MAIN_INCORRECT_SCORE = 4103
    C_MAIN_QUESTION_COUNT = 4104
    C_MAIN_COVER_IMAGE = 4200
    C_MAIN_QUESTION_LABEL = 4300
    C_MAIN_PHOTO = 4400
    C_MAIN_MOVIE_BACKGROUND = 4500
    C_MAIN_TVSHOW_BACKGROUND = 4501
    C_MAIN_QUOTE_LABEL = 4600
    C_MAIN_PHOTO_1 = 4701
    C_MAIN_PHOTO_2 = 4702
    C_MAIN_PHOTO_3 = 4703
    C_MAIN_PHOTO_LABEL_1 = 4711
    C_MAIN_PHOTO_LABEL_2 = 4712
    C_MAIN_PHOTO_LABEL_3 = 4713
    C_MAIN_VIDEO_FILE_NOT_FOUND = 4800
    C_MAIN_VIDEO_VISIBILITY = 5000
    C_MAIN_PHOTO_VISIBILITY = 5001
    C_MAIN_QUOTE_VISIBILITY = 5004
    C_MAIN_THREE_PHOTOS_VISIBILITY = 5006
    C_MAIN_THEME_VISIBILITY = 5008
    C_MAIN_CORRECT_VISIBILITY = 5002
    C_MAIN_INCORRECT_VISIBILITY = 5003
    C_MAIN_LOADING_VISIBILITY = 5005
    C_MAIN_COVER_IMAGE_VISIBILITY = 5007

    STATE_SPLASH = 1
    STATE_LOADING = 2
    STATE_PLAYING = 3
    STATE_GAME_OVER = 4

    def __new__(cls, gameInstance = None):
        return super(QuizGui, cls).__new__(cls, 'script-moviequiz-main.xml', ADDON.getAddonInfo('path'))

    def __init__(self, gameInstance = None):
        super(QuizGui, self).__init__()

        self.gameInstance = gameInstance

        self.player = player.TenSecondPlayer()
        self.questionCandidates = []
        self.defaultLibraryFilters = []

        self.questionPointsThread = None
        self.questionPoints = 0
        self.question = None
        self.previousQuestions = []
        self.lastClickTime = -1
        self.delayedNewQuestionTimer = None

        self.uiState = self.STATE_SPLASH

    @buggalo.buggalo_try_except()
    def onInit(self):
        self.getControl(2).setVisible(False)

        startTime = datetime.datetime.now()
        question.IMDB.loadData()
        delta = datetime.datetime.now() - startTime
        if delta.seconds < 2:
            xbmc.sleep(1000 * (2 - delta.seconds))

        if self.gameInstance:
            self.newGame(self.gameInstance)
        else:
            self.showMenuDialog()

    def showMenuDialog(self):
        menuGui = MenuGui(self)
        menuGui.doModal()
        del menuGui

    def newGame(self, gameInstance):
        self.getControl(1).setVisible(False)
        self.getControl(2).setVisible(True)

        self.gameInstance = gameInstance
        self.gameInstance.reset()

        xbmc.log("Starting game: %s" % str(self.gameInstance))

        if self.gameInstance.getType() == game.GAMETYPE_TVSHOW:
            self.defaultBackground = BACKGROUND_TV
        else:
            self.defaultBackground = BACKGROUND_MOVIE

        if self.gameInstance.getType() == game.GAMETYPE_TVSHOW:
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.defaultBackground)

        self.defaultLibraryFilters = list()
        if gameInstance.getType() == game.GAMETYPE_MOVIE and ADDON.getSetting('movie.rating.limit.enabled') == 'true':
            idx = MPAA_RATINGS.index(ADDON.getSetting('movie.rating.limit'))
            self.defaultLibraryFilters.extend(iter(library.buildRatingsFilters('mpaarating', MPAA_RATINGS[:idx])))

        elif gameInstance.getType() == game.GAMETYPE_TVSHOW and ADDON.getSetting(
                'tvshow.rating.limit.enabled') == 'true':
            idx = CONTENT_RATINGS.index(ADDON.getSetting('tvshow.rating.limit'))
            self.defaultLibraryFilters.extend(iter(library.buildRatingsFilters('rating', CONTENT_RATINGS[:idx])))

        if ADDON.getSetting(SETT_ONLY_WATCHED_MOVIES) == 'true':
            self.defaultLibraryFilters.extend(library.buildOnlyWathcedFilter())

        self.questionCandidates = question.getEnabledQuestionCandidates(self.gameInstance)

        self.questionPointsThread = None
        self.questionPoints = 0
        self.question = None
        self.previousQuestions = []
        self.uiState = self.STATE_LOADING

        self.onNewQuestion()

    def close(self):
        if self.player:
            if self.player.isPlaying():
                self.player.stopPlayback(True)
        super(QuizGui, self).close()

    @buggalo.buggalo_try_except()
    def onAction(self, action):
        if self.uiState == self.STATE_SPLASH and (action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU):
            self.close()
            return

        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self.onGameOver()

        if self.uiState == self.STATE_LOADING:
            return
        elif action.getId() in [ACTION_REMOTE1]:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER)
            self.onQuestionAnswered(self.question.getAnswer(0))
        elif action.getId() in [ACTION_REMOTE2, ACTION_JUMP_SMS2]:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER + 1)
            self.onQuestionAnswered(self.question.getAnswer(1))
        elif action.getId() in [ACTION_REMOTE3, ACTION_JUMP_SMS3]:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER + 2)
            self.onQuestionAnswered(self.question.getAnswer(2))
        elif action.getId() in [ACTION_REMOTE4, ACTION_JUMP_SMS4]:
            self.setFocusId(self.C_MAIN_FIRST_ANSWER + 3)
            self.onQuestionAnswered(self.question.getAnswer(3))

    @buggalo.buggalo_try_except()
    def onClick(self, controlId):
        difference = time.time() - self.lastClickTime
        self.lastClickTime = time.time()
        if difference < 0.7:
            xbmc.log("Ignoring key-repeat onClick")
            return

        if not self.gameInstance.isInteractive():
            return  # ignore
        elif controlId == self.C_MAIN_EXIT:
            self.onGameOver()
        elif self.uiState == self.STATE_LOADING:
            return  # ignore the rest while we are loading
        elif self.question and (self.C_MAIN_FIRST_ANSWER <= controlId <= self.C_MAIN_LAST_ANSWER):
            answer = self.question.getAnswer(controlId - self.C_MAIN_FIRST_ANSWER)
            self.onQuestionAnswered(answer)
        elif controlId == self.C_MAIN_REPLAY:
            self.player.replay()

    @buggalo.buggalo_try_except()
    def onFocus(self, controlId):
        self.onThumbChanged(controlId)

    def onGameOver(self):
        if self.uiState == self.STATE_GAME_OVER:
            return # ignore multiple invocations
        self.uiState = self.STATE_GAME_OVER

        if self.delayedNewQuestionTimer is not None:
            self.delayedNewQuestionTimer.cancel()

        if self.player.isPlaying():
            self.player.stopPlayback(True)

        if self.questionPointsThread is not None:
            self.questionPointsThread.cancel()

        if self.gameInstance.isInteractive():
            w = GameOverDialog(self, self.gameInstance)
            w.doModal()
            del w

    @buggalo.buggalo_try_except()
    def onNewQuestion(self):
        if self.gameInstance.isGameOver():
            self.onGameOver()
            return

        self.delayedNewQuestionTimer = None
        self.onStatsChanged()
        self.uiState = self.STATE_LOADING
        self.getControl(self.C_MAIN_LOADING_VISIBILITY).setVisible(True)
        self.question = self._getNewQuestion()
        if not self.question:
            self.onGameOver()
            return
        self.getControl(self.C_MAIN_QUESTION_LABEL).setLabel(self.question.getText())

        answers = self.question.getAnswers()
        for idx in range(0, 4):
            button = self.getControl(self.C_MAIN_FIRST_ANSWER + idx)
            if idx >= len(answers):
                button.setLabel('')
                button.setVisible(False)
            else:
                button.setLabel(answers[idx].text, textColor='0xFFFFFFFF')
                button.setVisible(True)

            if not self.gameInstance.isInteractive() and answers[idx].correct:
                # highlight correct answer
                self.setFocusId(self.C_MAIN_FIRST_ANSWER + idx)

        self.onThumbChanged()

        if self.question.getFanartFile() is not None:
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.question.getFanartFile())
        else:
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.defaultBackground)

        displayType = self.question.getDisplayType()
        if isinstance(displayType, question.VideoDisplayType):
            self.getControl(self.C_MAIN_VIDEO_FILE_NOT_FOUND).setVisible(False)
            xbmc.sleep(1500)  # give skin animation time to execute
            if not self.player.playWindowed(displayType.getVideoFile(), displayType.getResumePoint()):
                self.getControl(self.C_MAIN_VIDEO_FILE_NOT_FOUND).setVisible(True)

        elif isinstance(displayType, question.PhotoDisplayType):
            self.getControl(self.C_MAIN_PHOTO).setImage(displayType.getPhotoFile())

        elif isinstance(displayType, question.ThreePhotoDisplayType):
            self.getControl(self.C_MAIN_PHOTO_1).setImage(displayType.getPhotoFile(0)[0])
            self.getControl(self.C_MAIN_PHOTO_LABEL_1).setLabel(displayType.getPhotoFile(0)[1])
            self.getControl(self.C_MAIN_PHOTO_2).setImage(displayType.getPhotoFile(1)[0])
            self.getControl(self.C_MAIN_PHOTO_LABEL_2).setLabel(displayType.getPhotoFile(1)[1])
            self.getControl(self.C_MAIN_PHOTO_3).setImage(displayType.getPhotoFile(2)[0])
            self.getControl(self.C_MAIN_PHOTO_LABEL_3).setLabel(displayType.getPhotoFile(2)[1])

        elif isinstance(displayType, question.QuoteDisplayType):
            quoteText = displayType.getQuoteText()
            quoteText = self._obfuscateQuote(quoteText)
            self.getControl(self.C_MAIN_QUOTE_LABEL).setText(quoteText)

        elif isinstance(displayType, question.AudioDisplayType):
            self.player.playAudio(displayType.getAudioFile())

        self.onVisibilityChanged(displayType)

        if not self.gameInstance.isInteractive():
            # answers correctly in ten seconds
            threading.Timer(10.0, self._answer_correctly).start()

        self.uiState = self.STATE_PLAYING
        self.getControl(self.C_MAIN_LOADING_VISIBILITY).setVisible(False)

        self.questionPoints = None
        self.onQuestionPointTimer()

    def _getNewQuestion(self):
        retries = 0
        q = None
        while retries < 100 and self.uiState == self.STATE_LOADING:
            xbmc.sleep(10)  # give XBMC time to process other events
            retries += 1

            self.getControl(self.C_MAIN_LOADING).setPercent(retries)

            random.shuffle(self.questionCandidates)
            for candidate in self.questionCandidates:
                try:
                    q = candidate(self.defaultLibraryFilters)
                    break
                except question.QuestionException, ex:
                    print "QuestionException: %s" % str(ex)
                except Exception, ex:
                    xbmc.log("%s in %s" % (ex.__class__.__name__, candidate.__name__))
                    import traceback
                    import sys

                    traceback.print_exc(file=sys.stdout)

            if q is None or len(q.getAnswers()) < 3:
                continue

            print type(q)
            if not q.getUniqueIdentifier() in self.previousQuestions:
                self.previousQuestions.append(q.getUniqueIdentifier())
                break

        return q

    @buggalo.buggalo_try_except()
    def onQuestionPointTimer(self):
        """
        onQuestionPointTimer handles the decreasing amount of points awarded to the user when a question is
        answered correctly.

        The points start a 100 and is decreasing exponentially slower to make it more difficult to get a higher score.
        When the points reach 10 the decreasing ends, making 10 the lowest score you can get.

        Before the timer starts the user gets a three second head start - this is to actually make it possible to get a
        perfect 100 score.
        """
        if self.questionPointsThread is not None:
            self.questionPointsThread.cancel()

        if self.questionPoints is None:
            self.questionPoints = 100
        else:
            self.questionPoints -= 1

        self.getControl(4103).setLabel(str(self.questionPoints / 10.0))
        if self.questionPoints == 100:
            # three second head start
            self.questionPointsThread = threading.Timer(3, self.onQuestionPointTimer)
            self.questionPointsThread.start()
        elif self.questionPoints > 10:
            seconds = (100 - self.questionPoints) / 100.0
            self.questionPointsThread = threading.Timer(seconds, self.onQuestionPointTimer)
            self.questionPointsThread.start()

    def _answer_correctly(self):
        answer = self.question.getCorrectAnswer()
        self.onQuestionAnswered(answer)

    def onQuestionAnswered(self, answer):
        """
        @param answer: the chosen answer by the user
        @type answer: Answer
        """
        xbmc.log("onQuestionAnswered(..)")
        if self.questionPointsThread is not None:
            self.questionPointsThread.cancel()

        if answer is not None and answer.correct:
            xbmc.playSFX(AUDIO_CORRECT)
            self.gameInstance.correctAnswer(self.questionPoints / 10.0)
            self.getControl(self.C_MAIN_CORRECT_VISIBILITY).setVisible(False)
        else:
            xbmc.playSFX(AUDIO_WRONG)
            self.gameInstance.wrongAnswer()
            self.getControl(self.C_MAIN_INCORRECT_VISIBILITY).setVisible(False)

        if self.player.isPlaying():
            self.player.stopPlayback()

        threading.Timer(0.5, self.onQuestionAnswerFeedbackTimer).start()
        if ADDON.getSetting('show.correct.answer') == 'true' and not answer.correct:
            for idx, answer in enumerate(self.question.getAnswers()):
                if answer.correct:
                    self.getControl(self.C_MAIN_FIRST_ANSWER + idx).setLabel('[B]%s[/B]' % answer.text)
                    self.setFocusId(self.C_MAIN_FIRST_ANSWER + idx)
                    self.onThumbChanged(self.C_MAIN_FIRST_ANSWER + idx)
                else:
                    self.getControl(self.C_MAIN_FIRST_ANSWER + idx).setLabel(textColor='0x88888888')

            if isinstance(self.question.getDisplayType(), question.QuoteDisplayType):
                # Display non-obfuscated quote text
                self.getControl(self.C_MAIN_QUOTE_LABEL).setText(self.question.getDisplayType().getQuoteText())

            if self.uiState != self.STATE_GAME_OVER:
                self.delayedNewQuestionTimer = threading.Timer(3.0, self.onNewQuestion)
                self.delayedNewQuestionTimer.start()

        else:
            self.onNewQuestion()

    def onStatsChanged(self):
        self.getControl(self.C_MAIN_CORRECT_SCORE).setLabel(str(self.gameInstance.getPoints()))

        label = self.getControl(self.C_MAIN_QUESTION_COUNT)
        label.setLabel(self.gameInstance.getStatsString())

    def onThumbChanged(self, controlId=None):
        if self.question is None:
            return  # not initialized yet

        if controlId is None:
            controlId = self.getFocusId()

        if self.C_MAIN_FIRST_ANSWER <= controlId <= self.C_MAIN_LAST_ANSWER:
            answer = self.question.getAnswer(controlId - self.C_MAIN_FIRST_ANSWER)
            coverImage = self.getControl(self.C_MAIN_COVER_IMAGE)
            if answer is not None and answer.coverFile is not None:
                self.getControl(self.C_MAIN_COVER_IMAGE_VISIBILITY).setVisible(False)
                coverImage.setImage(answer.coverFile)
            elif answer is not None and answer.coverFile is not None:
                self.getControl(self.C_MAIN_COVER_IMAGE_VISIBILITY).setVisible(False)
                coverImage.setImage(NO_PHOTO_IMAGE)
            else:
                self.getControl(self.C_MAIN_COVER_IMAGE_VISIBILITY).setVisible(True)

    @buggalo.buggalo_try_except()
    def onQuestionAnswerFeedbackTimer(self):
        """
        onQuestionAnswerFeedbackTimer is invoked by a timer when the red or green background behind the answers box
        must be faded out and hidden.

        Note: Visibility is inverted in skin
        """
        self.getControl(self.C_MAIN_CORRECT_VISIBILITY).setVisible(True)
        self.getControl(self.C_MAIN_INCORRECT_VISIBILITY).setVisible(True)

    def onVisibilityChanged(self, displayType=None):
        """
        @type displayType: quizlib.question.DisplayType
        @param displayType: the type of display required by the current question
        """
        self.getControl(self.C_MAIN_VIDEO_VISIBILITY).setVisible(not isinstance(displayType, question.VideoDisplayType))
        self.getControl(self.C_MAIN_PHOTO_VISIBILITY).setVisible(not isinstance(displayType, question.PhotoDisplayType))
        self.getControl(self.C_MAIN_QUOTE_VISIBILITY).setVisible(not isinstance(displayType, question.QuoteDisplayType))
        self.getControl(self.C_MAIN_THREE_PHOTOS_VISIBILITY).setVisible(
            not isinstance(displayType, question.ThreePhotoDisplayType))
        self.getControl(self.C_MAIN_THEME_VISIBILITY).setVisible(not isinstance(displayType, question.AudioDisplayType))

    def _obfuscateQuote(self, quote):
        names = list()

        for m in re.finditer('(\[.*?\])', quote, re.DOTALL):
            quote = quote.replace(m.group(1), '')

        for m in re.finditer('(.*?:)', quote):
            name = m.group(1)
            if not name in names:
                names.append(name)

        for idx, name in enumerate(names):
            repl = '#%d:' % (idx + 1)
            quote = quote.replace(name, repl)

        return quote


class GameOverDialog(xbmcgui.WindowXMLDialog):
    C_GAMEOVER_RETRY = 2000
    C_GAMEOVER_MAINMENU = 2001

    C_GAMEOVER_HIGHSCORE_LIST_VISIBILITY = 8000
    C_GAMEOVER_HIGHSCORE_LIST = 8001
    C_GAMEOVER_HIGHSCORE_TITLE = 8002

    def __new__(cls, parentWindow, gameType):
        return super(GameOverDialog, cls).__new__(cls, 'script-moviequiz-gameover.xml', ADDON.getAddonInfo('path'))

    def __init__(self, parentWindow, game):
        super(GameOverDialog, self).__init__()

        self.parentWindow = parentWindow
        self.game = game
        self.localHighscoresShown = True
        self.highscoreTimer = None

    @buggalo.buggalo_try_except()
    def onInit(self):
        self.getControl(GameOverDialog.C_GAMEOVER_HIGHSCORE_LIST_VISIBILITY).setVisible(True)

        movies = library.getMovies(['art']).limitTo(44).asList()
        posters = [movie['art']['poster'] for movie in movies if 'art' in movie and 'poster' in movie['art']]
        if posters:
            for idx in range(0, 44):
                self.getControl(1000 + idx).setImage(posters[idx % len(posters)])

        self.getControl(4100).setLabel(
            strings(G_YOU_SCORED) % (self.game.getCorrectAnswers(), self.game.getTotalAnswers()))
        self.getControl(4101).setLabel(str(self.game.getPoints()))

        if self.game.isInteractive():
            self.loadHighscores()

            if self.globalHighscoreEntries is not None:
                self.highscoreTimer = threading.Timer(5, self.swapHighscoreDisplay)
                self.highscoreTimer.start()

    def close(self):
        if self.highscoreTimer:
            self.highscoreTimer.cancel()

        self.getControl(GameOverDialog.C_GAMEOVER_HIGHSCORE_LIST_VISIBILITY).setVisible(True)
        super(GameOverDialog, self).close()

    def swapHighscoreDisplay(self):
        if self.localHighscoresShown:
            self.showHighscores(M_GLOBAL_HIGHSCORE, self.globalHighscoreEntries, self.globalHighscoreNewId)
            self.localHighscoresShown = False
        else:
            self.showHighscores(M_LOCAL_HIGHSCORE, self.localHighscoreEntries, self.localHighscoreNewId)
            self.localHighscoresShown = True

        if self.globalHighscoreEntries:
            self.highscoreTimer = threading.Timer(5, self.swapHighscoreDisplay)
            self.highscoreTimer.start()

    @buggalo.buggalo_try_except()
    def onAction(self, action):
        if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU]:
            self.close()
            xbmc.sleep(500)

            w = MenuGui(self.parentWindow)
            w.doModal()
            del w

    @buggalo.buggalo_try_except()
    def onClick(self, controlId):
        if controlId == self.C_GAMEOVER_RETRY:
            self.close()
            self.parentWindow.newGame(self.parentWindow.gameInstance)

        elif controlId == self.C_GAMEOVER_MAINMENU:
            self.close()
            xbmc.sleep(500)

            w = MenuGui(self.parentWindow)
            w.doModal()
            del w

    @buggalo.buggalo_try_except()
    def onFocus(self, controlId):
        pass

    def loadHighscores(self):
        # Local highscore
        localHighscore = highscore.LocalHighscoreDatabase(xbmc.translatePath(ADDON.getAddonInfo('profile')))
        self.localHighscoreNewId = localHighscore.addHighscore(self.game)
        name = localHighscore.getNickname(self.game.getUserId())

        self.localHighscoreEntries = localHighscore.getHighscoresNear(self.game, self.localHighscoreNewId)
        localHighscore.close()
        self.showHighscores(M_LOCAL_HIGHSCORE, self.localHighscoreEntries, self.localHighscoreNewId)

        # Global highscore
        globalHighscore = highscore.GlobalHighscoreDatabase(ADDON.getAddonInfo('version'))
        if ADDON.getSetting('submit.highscores') == 'true':
            self.globalHighscoreNewId = globalHighscore.addHighscore(name, self.game)
        else:
            self.globalHighscoreNewId = -1

        self.globalHighscoreEntries = globalHighscore.getHighscoresNear(self.game, self.globalHighscoreNewId)

    def showHighscores(self, titleId, entries, newHighscoreId):
        self.getControl(GameOverDialog.C_GAMEOVER_HIGHSCORE_LIST_VISIBILITY).setVisible(True)
        xbmc.sleep(350)

        self.getControl(GameOverDialog.C_GAMEOVER_HIGHSCORE_TITLE).setLabel(strings(titleId))

        items = list()
        selectedIndex = -1
        for entry in entries:
            item = xbmcgui.ListItem(entry['nickname'])
            item.setProperty('position', str(entry['position']))
            item.setProperty('score', str(entry['score']))
            if 'timeAgo' in entry:
                item.setProperty('timestamp', entry['timeAgo'])
                item.setProperty('countryIconUrl', entry['countryIconUrl'])
            else:
                item.setProperty('timestamp', entry['timestamp'][0:10])

            if int(entry['id']) == int(newHighscoreId):
                item.setProperty('highlight', 'true')
                selectedIndex = len(items)
            items.append(item)
        listControl = self.getControl(self.C_GAMEOVER_HIGHSCORE_LIST)
        listControl.addItems(items)
        if selectedIndex != -1:
            if selectedIndex + 5 < len(items):
                listControl.selectItem(selectedIndex + 5)
            else:
                listControl.selectItem(len(items)-1)
            listControl.selectItem(selectedIndex)

        self.getControl(GameOverDialog.C_GAMEOVER_HIGHSCORE_LIST_VISIBILITY).setVisible(False)


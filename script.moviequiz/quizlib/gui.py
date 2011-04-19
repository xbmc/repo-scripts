import threading
import os
import re

import xbmc
import xbmcgui

import question
import player
import db
from strings import *

__author__ = 'twinther'

# Constants from [xbmc]/xbmc/guilib/Key.h
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10

class MenuGui(xbmcgui.WindowXML):
    C_MENU_MOVIE_QUIZ = 4001
    C_MENU_TVSHOW_QUIZ = 4002
    C_MENU_SETTINGS = 4000
    C_MENU_EXIT = 4003
    C_MENU_COLLECTION_TRIVIA = 6000

    def __init__(self, xmlFilename, scriptPath, addon):
        xbmcgui.WindowXML.__init__(self, xmlFilename, scriptPath)
        self.addon = addon

    def onInit(self):
        print "MenuGui.onInit"

        trivia = [strings(M_TRANSLATED_BY)]

        database = db.connect()

        if not database.hasMovies():
            self.getControl(self.C_MENU_MOVIE_QUIZ).setEnabled(False)
        else:
            movies = database.fetchone('SELECT COUNT(*) AS count, (SUM(c11) / 60) AS total_hours FROM movie')
            actors = database.fetchone('SELECT COUNT(DISTINCT idActor) AS count FROM actorlinkmovie')
            directors = database.fetchone('SELECT COUNT(DISTINCT idDirector) AS count FROM directorlinkmovie')
            studios = database.fetchone('SELECT COUNT(idStudio) AS count FROM studio')

            trivia += [
                    strings(M_MOVIE_COLLECTION_TRIVIA),
                    strings(M_MOVIE_COUNT) % movies['count'],
                    strings(M_ACTOR_COUNT) % actors['count'],
                    strings(M_DIRECTOR_COUNT) % directors['count'],
                    strings(M_STUDIO_COUNT) % studios['count'],
                    strings(M_HOURS_OF_ENTERTAINMENT) % int(movies['total_hours'])
            ]


        if not database.hasTVShows():
            self.getControl(self.C_MENU_TVSHOW_QUIZ).setEnabled(False)
        else:
            shows = database.fetchone('SELECT COUNT(*) AS count FROM tvshow')
            seasons = database.fetchone('SELECT SUM(season_count) AS count FROM (SELECT idShow, COUNT(DISTINCT c12) AS season_count from episodeview GROUP BY idShow) AS tbl')
            episodes = database.fetchone('SELECT COUNT(*) AS count FROM episode')

            trivia += [
                strings(M_TVSHOW_COLLECTION_TRIVIA),
                strings(M_TVSHOW_COUNT) % shows['count'],
                strings(M_SEASON_COUNT) % seasons['count'],
                strings(M_EPISODE_COUNT) % episodes['count']
            ]

        if not database.hasMovies() and not database.hasTVShows():
            line1 = 'Missing requirements!'
            line2 = 'To play the Movie Quiz you must[CR]have some movies or TV shows'
            line3 = 'in your Video library. See the[CR]XBMC wiki for information.'
            path = self.addon.getAddonInfo('path')
            w = ClapperDialog('script-moviequiz-clapper.xml', path, line1=line1, line2=line2, line3=line3, autoClose = False)
            w.doModal()
            del w

            self.close()


        database.close()

        label = '  *  '.join(trivia)
        self.getControl(self.C_MENU_COLLECTION_TRIVIA).setLabel(label)

    def onAction(self, action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlId):
        maxQuestions = -1
        if self.addon.getSetting('question.limit.enabled') == 'true':
            maxQuestions = int(self.addon.getSetting('question.limit'))

        maxRating = None

        if controlId == self.C_MENU_MOVIE_QUIZ:
            if self.addon.getSetting('movie.rating.limit.enabled') == 'true':
                maxRating = self.addon.getSetting('movie.rating.limit')

            path = self.addon.getAddonInfo('path')
            w = QuizGui('script-moviequiz-main.xml', path, addon=self.addon, type=question.TYPE_MOVIE, questionLimit=maxQuestions, maxRating=maxRating)
            w.doModal()
            del w

        elif controlId == self.C_MENU_TVSHOW_QUIZ:
            if self.addon.getSetting('tvshow.rating.limit.enabled') == 'true':
                maxRating = self.addon.getSetting('tvshow.rating.limit')
            path = self.addon.getAddonInfo('path')
            w = QuizGui('script-moviequiz-main.xml', path, addon=self.addon, type=question.TYPE_TV, questionLimit=maxQuestions, maxRating=maxRating)
            w.doModal()
            del w

        elif controlId == self.C_MENU_SETTINGS:
            self.addon.openSettings()

        elif controlId == self.C_MENU_EXIT:
            self.close()

    #noinspection PyUnusedLocal
    def onFocus(self, controlId):
        pass


class QuizGui(xbmcgui.WindowXML):
    C_MAIN_FIRST_ANSWER = 4000
    C_MAIN_LAST_ANSWER = 4003
    C_MAIN_REPLAY = 4010
    C_MAIN_EXIT = 4011
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
    C_MAIN_VIDEO_VISIBILITY = 5000
    C_MAIN_PHOTO_VISIBILITY = 5001
    C_MAIN_QUOTE_VISIBILITY = 5004
    C_MAIN_THREE_PHOTOS_VISIBILITY = 5006
    C_MAIN_CORRECT_VISIBILITY = 5002
    C_MAIN_INCORRECT_VISIBILITY = 5003
    C_MAIN_LOADING_VISIBILITY = 5005
    C_MAIN_REPLAY_BUTTON_VISIBILITY = 5007


    def __init__(self, xmlFilename, scriptPath, addon, type, questionLimit = -1, maxRating = None, interactive = True):
        xbmcgui.WindowXML.__init__(self, xmlFilename, scriptPath)
        self.addon = addon
        self.type = type
        self.questionLimit = questionLimit
        self.questionCount = 0
        self.maxRating = maxRating
        self.interactive = interactive

        path = self.addon.getAddonInfo('path')
        if self.type == question.TYPE_TV:
            self.defaultBackground = os.path.join(path, 'resources', 'skins', 'Default', 'media', 'quiz-background-tvshows.png')
        else:
            self.defaultBackground = os.path.join(path, 'resources', 'skins', 'Default', 'media', 'quiz-background.png')

        self.database = db.connect()
        self.player = player.TenSecondPlayer(database=self.database)
        self.question = question.Question(self.database, None, None, None)
        self.previousQuestions = []
        self.score = {'correct': 0, 'wrong': 0}

        self.maxRating = None
        if maxRating is not None:
            self.maxRating = maxRating
        elif self.type == question.TYPE_MOVIE and self.addon.getSetting('movie.rating.limit.enabled') == 'true':
            self.maxRating = self.addon.getSetting('movie.rating.limit')
        elif self.type == question.TYPE_TV and self.addon.getSetting('tvshow.rating.limit.enabled') == 'true':
            self.maxRating = self.addon.getSetting('tvshow.rating.limit')
        self.onlyWatchedMovies = self.addon.getSetting('only.watched.movies') == 'true'

    def onInit(self):
        try :
            xbmcgui.lock()
            if self.type == question.TYPE_TV:
                self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.defaultBackground)
        finally:
            xbmcgui.unlock()

        self._setup_question()

    def close(self):
        if self.player and self.player.isPlaying():
            self.player.stop()
        # TODO self.database.close()
        xbmcgui.WindowXML.close(self)
        
    def onAction(self, action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self._game_over()
            self.close()


    def onClick(self, controlId):
        if not self.interactive:
            return # ignore

        if self.question and (controlId >= self.C_MAIN_FIRST_ANSWER and controlId <= self.C_MAIN_LAST_ANSWER):
            answer = self.question.getAnswer(controlId - self.C_MAIN_FIRST_ANSWER)
            self._handle_answer(answer)
            self._setup_question()
        elif controlId == self.C_MAIN_EXIT:
            self._game_over()
        elif controlId == self.C_MAIN_REPLAY:
            self.player.replay()

    #noinspection PyUnusedLocal
    def onFocus(self, controlId):
        self._update_thumb(controlId)

    def _game_over(self):
        if self.interactive:
            total = self.score['correct'] + self.score['wrong']
            line1 = strings(G_GAME_OVER)
            line2 = strings(G_YOU_SCORED) % (self.score['correct'], total)

            path = self.addon.getAddonInfo('path')
            w = ClapperDialog('script-moviequiz-clapper.xml', path, line1=line1, line2=line2)
            w.doModal()
            del w

        self.close()

    def _setup_question(self):
        self.getControl(self.C_MAIN_LOADING_VISIBILITY).setVisible(True)

        self.questionCount += 1
        if self.questionLimit > 0 and self.questionCount > self.questionLimit:
            self._game_over()
            return

        self.question = self._getNewQuestion()
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

            if not self.interactive and answers[idx].correct:
                # highlight correct answer
                self.setFocusId(self.C_MAIN_FIRST_ANSWER + idx)

        self._update_thumb()
        self._update_stats()

        print self.question.getFanartFile()
        if self.question.getFanartFile() is not None and os.path.exists(self.question.getFanartFile()):
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.question.getFanartFile())
        else:
            self.getControl(self.C_MAIN_MOVIE_BACKGROUND).setImage(self.defaultBackground)

        correctAnswer = self.question.getCorrectAnswer()
        if self.question.getDisplay() == question.DISPLAY_VIDEO:
            self._changeVisibility(video = True)
            xbmc.sleep(1500) # give skin animation time to execute
            self.player.playWindowed(self.question.getVideoFile(), correctAnswer.idFile)

        elif self.question.getDisplay() == question.DISPLAY_PHOTO:
            self.getControl(self.C_MAIN_PHOTO).setImage(self.question.getPhotoFile())
            self._changeVisibility(photo = True)

        elif self.question.getDisplay() == question.DISPLAY_QUOTE:
            quoteText = self.question.getQuoteText()
            quoteText = self._obfuscateQuote(quoteText)
            self.getControl(self.C_MAIN_QUOTE_LABEL).setText(quoteText)
            self._changeVisibility(quote = True)

        elif self.question.getDisplay() == question.DISPLAY_NONE:
            self._changeVisibility()

        elif self.question.getDisplay() == question.DISPLAY_THREE_PHOTOS:
            self.getControl(self.C_MAIN_PHOTO_1).setImage(self.question.getPhotoFile(0))
            self.getControl(self.C_MAIN_PHOTO_2).setImage(self.question.getPhotoFile(1))
            self.getControl(self.C_MAIN_PHOTO_3).setImage(self.question.getPhotoFile(2))
            self._changeVisibility(threePhotos = True)

        if not self.interactive:
            # answers correctly in ten seconds
            threading.Timer(10.0, self._answer_correctly).start()

        self.getControl(self.C_MAIN_LOADING_VISIBILITY).setVisible(False)

    def _getNewQuestion(self):
        retries = 0
        q = None
        while retries < 100:
            q = question.getRandomQuestion(self.type, self.database, self.maxRating, self.onlyWatchedMovies)
            if q is None:
                continue
                
            try:
                self.previousQuestions.index(q.getUniqueIdentifier())
                print "Already had question %s" % q.getUniqueIdentifier()
                retries += 1
            except Exception:
                print "New question %s" % q.getUniqueIdentifier()
                self.previousQuestions.append(q.getUniqueIdentifier())
                break

        return q

    def _answer_correctly(self):
        answer = self.question.getCorrectAnswer()
        self._handle_answer(answer)
        self._setup_question()

    def _handle_answer(self, answer):
        if answer is not None and answer.correct:
            self.score['correct'] += 1
            self.getControl(self.C_MAIN_CORRECT_VISIBILITY).setVisible(False)
        else:
            self.score['wrong'] += 1
            self.getControl(self.C_MAIN_INCORRECT_VISIBILITY).setVisible(False)

        if self.player.isPlaying():
            self.player.stop()

        threading.Timer(3.0, self._hide_icons).start()
        if self.addon.getSetting('show.correct.answer') == 'true' and not answer.correct:
            for idx, answer in enumerate(self.question.getAnswers()):
                if answer.correct:
                    self.getControl(self.C_MAIN_FIRST_ANSWER + idx).setLabel('[B]%s[/B]' % answer.text)
                    self.setFocusId(self.C_MAIN_FIRST_ANSWER + idx)
                else:
                    self.getControl(self.C_MAIN_FIRST_ANSWER + idx).setLabel(textColor='0x88888888')

            if self.question.getDisplay() == question.DISPLAY_QUOTE:
                # Display non-obfuscated quote text
                self.getControl(self.C_MAIN_QUOTE_LABEL).setText(self.question.getQuoteText())

            xbmc.sleep(3000)

    def _update_stats(self):
        self.getControl(self.C_MAIN_CORRECT_SCORE).setLabel(str(self.score['correct']))
        self.getControl(self.C_MAIN_INCORRECT_SCORE).setLabel(str(self.score['wrong']))

        label = self.getControl(self.C_MAIN_QUESTION_COUNT)
        if self.questionLimit > 0:
            label.setLabel(strings(G_QUESTION_X_OF_Y, (self.questionCount, self.questionLimit)))
        else:
            label.setLabel('')


    def _update_thumb(self, controlId = None):
        if self.question is None:
            return # not initialized yet

        if controlId is None:
            controlId = self.getFocusId()
        if controlId >= self.C_MAIN_FIRST_ANSWER or controlId <= self.C_MAIN_LAST_ANSWER:
            answer = self.question.getAnswer(controlId - self.C_MAIN_FIRST_ANSWER)
            coverImage = self.getControl(self.C_MAIN_COVER_IMAGE)
            if answer is not None and answer.coverFile is not None and os.path.exists(answer.coverFile):
                coverImage.setVisible(True)
                coverImage.setImage(answer.coverFile)
            elif answer is not None and answer.coverFile is not None :
                path = self.addon.getAddonInfo('path')
                coverImage.setVisible(True)
                coverImage.setImage(os.path.join(path, 'resources', 'skins', 'Default', 'media', 'quiz-no-photo.png'))
            else:
                coverImage.setVisible(False)

    def _hide_icons(self):
        """Visibility is inverted in skin
        """
        self.getControl(self.C_MAIN_CORRECT_VISIBILITY).setVisible(True)
        self.getControl(self.C_MAIN_INCORRECT_VISIBILITY).setVisible(True)

    def _changeVisibility(self, video = False, photo = False, quote = False, threePhotos = False):
        """Visibility is inverted in skin
        """
        self.getControl(self.C_MAIN_VIDEO_VISIBILITY).setVisible(not video)
        self.getControl(self.C_MAIN_PHOTO_VISIBILITY).setVisible(not photo)
        self.getControl(self.C_MAIN_QUOTE_VISIBILITY).setVisible(not quote)
        self.getControl(self.C_MAIN_THREE_PHOTOS_VISIBILITY).setVisible(not threePhotos)
        
        self.getControl(self.C_MAIN_REPLAY_BUTTON_VISIBILITY).setVisible(video)

    def _obfuscateQuote(self, quote):
        names = list()
        for m in re.finditer('(.*?\:)', quote):
            name = m.group(1)
            if not name in names:
                names.append(name)

        for idx, name in enumerate(names):
            repl = '#%d:' % (idx + 1)
            quote = quote.replace(name, repl)

        return quote



class ClapperDialog(xbmcgui.WindowXMLDialog):
    C_CLAPPER_LINE1 = 4000
    C_CLAPPER_LINE2 = 4001
    C_CLAPPER_LINE3 = 4002

    def __init__(self, xmlFilename, scriptPath, line1=None, line2=None, line3=None, autoClose = True):
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self.autoClose = autoClose
        self.timer = threading.Timer(5, self.delayedClose)

        xbmcgui.WindowXMLDialog.__init__(self, xmlFilename, scriptPath)


    def onInit(self):
        print "ClapperDialog.onInit"

        if self.line1 is None:
            self.line1 = ''
        if self.line2 is None:
            self.line2 = ''
        if self.line3 is None:
            self.line3 = ''

        self.getControl(self.C_CLAPPER_LINE1).setLabel(self.line1)
        self.getControl(self.C_CLAPPER_LINE2).setLabel(self.line2)
        self.getControl(self.C_CLAPPER_LINE3).setLabel(self.line3)

        if self.autoClose:
            self.timer.start()

    def delayedClose(self):
        print "ClapperDialog.delayedClose"
        self.close()

    def onAction(self, action):
        print "ClapperDialog.onAction " + str(action)
        self.timer.cancel()
        self.close()

    def onClick(self, controlId):
        print "ClapperDialog.onClick " + str(controlId)

    def onFocus(self, controlId):
        print "ClapperDialog.onFocus " + str(controlId)


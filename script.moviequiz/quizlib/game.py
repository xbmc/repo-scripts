import datetime
import xbmcaddon

from strings import *

GAMETYPE_MOVIE = "movie"
GAMETYPE_TVSHOW = "tvshow"

ADDON = xbmcaddon.Addon(id = 'script.moviequiz')

class Game(object):
    def __init__(self, type, userId, interactive):
        self.type = type
        self.userId = userId
        self.interactive = interactive
        self.points = 0
        self.correctAnswers = 0
        self.wrongAnswers = 0

    def correctAnswer(self, points):
        self.correctAnswers += 1
        self.points += points

    def wrongAnswer(self):
        self.wrongAnswers += 1
        
    def isGameOver(self):
        raise

    def getStatsString(self):
        return ''

    def getType(self):
        return self.type

    def getPoints(self):
        return self.points

    def getTotalAnswers(self):
        return self.correctAnswers + self.wrongAnswers

    def getCorrectAnswers(self):
        return self.correctAnswers

    def getWrongAnswers(self):
        return self.wrongAnswers

    def getGameType(self):
        raise

    def getGameSubType(self):
        return -1

    def getUserId(self):
        return self.userId

    def onlyUseWatchedMovies(self):
        return ADDON.getSetting('only.watched.movies') == 'true'

    def getMaxRating(self):
        if self.type == GAMETYPE_MOVIE and ADDON.getSetting('movie.rating.limit.enabled') == 'true':
            return ADDON.getSetting('movie.rating.limit')
        elif self.type == GAMETYPE_TVSHOW and ADDON.getSetting('tvshow.rating.limit.enabled') == 'true':
            return ADDON.getSetting('tvshow.rating.limit')

    def isInteractive(self):
        return self.interactive

    def reset(self):
        self.points = 0
        self.correctAnswers = 0
        self.wrongAnswers = 0

class UnlimitedGame(Game):
    def __init__(self, type, userId, interactive):
        super(UnlimitedGame, self).__init__(type, userId, interactive)

    def isGameOver(self):
        return False

    def getGameType(self):
        return 'unlimited'


class QuestionLimitedGame(Game):
    def __init__(self, type, userId, interactive, questionLimit):
        super(QuestionLimitedGame, self).__init__(type, userId, interactive)
        self.questionLimit = questionLimit
        self.questionCount = 0

    def isGameOver(self):
        self.questionCount += 1
        return self.correctAnswers + self.wrongAnswers >= self.questionLimit

    def getStatsString(self):
        questionsLeft = self.questionLimit - self.questionCount
        if not questionsLeft:
            return "Last question"
        else:
            return str(questionsLeft) + " questions left"

    def getGameType(self):
        return 'question-limited'

    def getGameSubType(self):
        return str(self.questionLimit)

    def reset(self):
        self.questionCount = 0

class TimeLimitedGame(Game):
    def __init__(self, type, userId, interactive, timeLimitMinutes):
        super(TimeLimitedGame, self).__init__(type, userId, interactive)
        self.startTime = datetime.datetime.now()
        self.timeLimitMinutes = timeLimitMinutes

    def isGameOver(self):
        return self._minutesLeft() >= self.timeLimitMinutes

    def getStatsString(self):
        return str(self.timeLimitMinutes - self._minutesLeft()) + " mins. left"

    def _minutesLeft(self):
        delta = datetime.datetime.now() - self.startTime
        print delta
        return delta.seconds / 60

    def getGameType(self):
        return 'time-limited'

    def getGameSubType(self):
        return str(self.timeLimitMinutes)

    def reset(self):
        self.startTime = datetime.datetime.now()


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

import datetime

from strings import *

GAMETYPE_MOVIE = "movie"
GAMETYPE_TVSHOW = "tvshow"


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

    def setType(self, type):
        self.type = type

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

    def __repr__(self):
        return "<UnlimitedGame>"

    def __eq__(self, other):
        return type(other) == UnlimitedGame and self.type == other.type


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
            return strings(G_LAST_QUESTION)
        else:
            return strings(G_X_QUESTIONS_LEFT, questionsLeft)

    def getGameType(self):
        return 'question-limited'

    def getGameSubType(self):
        return str(self.questionLimit)

    def reset(self):
        super(QuestionLimitedGame, self).reset()
        self.questionCount = 0

    def __repr__(self):
        return "<QuestionLimitedGame %s>" % str(self.questionLimit)

    def __eq__(self, other):
        return type(other) == QuestionLimitedGame and self.type == other.type and self.questionLimit == other.questionLimit


class TimeLimitedGame(Game):
    def __init__(self, type, userId, interactive, timeLimitMinutes):
        super(TimeLimitedGame, self).__init__(type, userId, interactive)
        self.startTime = datetime.datetime.now()
        self.timeLimitMinutes = timeLimitMinutes

    def isGameOver(self):
        return self._minutesLeft() >= self.timeLimitMinutes

    def getStatsString(self):
        minutesLeft = self.timeLimitMinutes - self._minutesLeft()
        return strings(G_X_MINUTES_LEFT, minutesLeft)

    def _minutesLeft(self):
        delta = datetime.datetime.now() - self.startTime
        return delta.seconds / 60

    def getGameType(self):
        return 'time-limited'

    def getGameSubType(self):
        return str(self.timeLimitMinutes)

    def reset(self):
        super(TimeLimitedGame, self).reset()
        self.startTime = datetime.datetime.now()

    def __repr__(self):
        return "<TimeLimitedGame %s>" % str(self.timeLimitMinutes)

    def __eq__(self, other):
        return type(other) == TimeLimitedGame and self.type == other.type and self.timeLimitMinutes == other.timeLimitMinutes


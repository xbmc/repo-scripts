import xbmc

from quizlib.game import QuestionLimitedGame
from quizlib.gui import QuizGui

def runCinemaExperience(type, automatic, maxRating, genre, questionLimit):
    """
    Used by Cinema Experience integration. This method will block until the Movie Quiz is exited.

    Keyword arguments:
    type -- the type of quiz to run, either Movie or TV Quiz. Either use constants in question.py or 1 for Movie and 2 for TV Quiz.
    automatic -- pass True if the quiz should run non-interactively, ie. progressing automatically.
    maxRating -- the maximum allow MPAA rating to use.
    genre -- Unused at the moment.
    questionLimit -- the number of questions to go through before the quiz ends.
    """
    xbmc.log("Starting Movie Quiz in Cinema Experience mode with params: type=%s, automatic=%s, maxRating=%s, genre=%s, questionLimit=%d"
        % (type, automatic, maxRating, genre, questionLimit))
    game = QuestionLimitedGame(type, -1, not automatic, questionLimit)
    w = QuizGui(game)
    w.doModal()
    del w
    
    return True

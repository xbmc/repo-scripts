# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon

# Import the common settings
from settings import log
from settings import Settings
from core import FilmWiseCore
from database import FilmWiseDB

ADDON = xbmcaddon.Addon(id='script.game.filmwise')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


#################################
# Window to display the quiz in
#################################
class FilmWiseViewer(xbmcgui.WindowXMLDialog):
    TITLE_LABEL_ID = 201
    SCORE_LABEL_ID = 204
    CHECK_BUTTON = 301
    CLOSE_BUTTON = 302
    SOLUTION_BUTTON = 303
    IMAGE_IDS = [501, 502, 503, 504, 505, 506, 507, 508]
    EDIT_BOX_IDS = [601, 602, 603, 604, 605, 606, 607, 608]
    MARK_IDS = [701, 702, 703, 704, 705, 706, 707, 708]

    def __init__(self, *args, **kwargs):
        self.questions = []
        self.database = FilmWiseDB()
        self.form = None
        self.redirect = None
        self.correctUserAnswers = {}

        # The quiz number is the trigger to read and store answers in the database
        self.quizNum = -1
        if Settings.isSaveUserAnswers():
            self.quizNum = kwargs.get('quizNum', -1)

        self.title = kwargs.get('title', '')
        details = kwargs.get('details', None)
        if details is not None:
            self.questions = details['questions']
            self.form = details['form']
            self.redirect = details['redirect']
        self.solution = kwargs.get('solution', '')
        xbmcgui.WindowXMLDialog.__init__(self)

    @staticmethod
    def createFilmWiseViewer(quizNum, title, details, solution):
        return FilmWiseViewer("script-filmwise-dialog.xml", CWD, quizNum=quizNum, title=title, details=details, solution=solution)

    # Called when setting up the window
    def onInit(self):
        # Update the dialog to show the correct data
        labelControl = self.getControl(FilmWiseViewer.TITLE_LABEL_ID)
        labelControl.setLabel(self.title)

        # Check if we should show the solution button
        if self.solution in [None, ""]:
            solutionControl = self.getControl(FilmWiseViewer.SOLUTION_BUTTON)
            solutionControl.setVisible(False)

        # Make sure all the flags for correct and incorrect answers are cleared
        for i in range(0, 8):
            markControl = self.getControl(FilmWiseViewer.MARK_IDS[i])
            markControl.setVisible(False)

        # Make sure we do not display more image than we have slots available
        numQuestions = len(self.questions)
        if numQuestions > 8:
            numQuestions = 8

        # Check if there are already answers saved
        userAnswers = {}
        if self.quizNum > 0:
            userAnswers = self.database.getAnswers(self.quizNum)

        numCorrectAnswers = 0
        # Set all the images for the quiz
        for i in range(0, numQuestions):
            imageControl = self.getControl(FilmWiseViewer.IMAGE_IDS[i])
            imageControl.setImage(self.questions[i]['image'])
            # Also populate any previous answers
            userAnswer = userAnswers.get(self.questions[i]['name'], None)
            if userAnswer is not None:
                answerText = userAnswer.get('user_answer', '')
                if answerText not in [None, ""]:
                    editControl = self.getControl(FilmWiseViewer.EDIT_BOX_IDS[i])
                    editControl.setText(answerText)
                    isCorrect = userAnswer.get('isCorrect', None)
                    self._setCorrectFlag(i, isCorrect)

                    if isCorrect:
                        numCorrectAnswers = numCorrectAnswers + 1
                        self.correctUserAnswers[self.questions[i]['name']] = answerText

        self._setScore(numCorrectAnswers, numQuestions)

        xbmcgui.WindowXMLDialog.onInit(self)

    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == FilmWiseViewer.CLOSE_BUTTON:
            log("FilmWiseViewer: Close click action received: %d" % controlID)
            self.close()
        elif controlID == FilmWiseViewer.SOLUTION_BUTTON:
            log("FilmWiseViewer: Solution click action received: %d" % controlID)
            self.showSolution()
        elif controlID == FilmWiseViewer.CHECK_BUTTON:
            log("FilmWiseViewer: Check click action received: %d" % controlID)
            self.isCheckFlag = True
            self.checkAnswers()
        elif controlID in FilmWiseViewer.EDIT_BOX_IDS:
            log("FilmWiseViewer: Edit Control %d Changed" % controlID)
            idx = FilmWiseViewer.EDIT_BOX_IDS.index(controlID)
            log("FilmWiseViewer: Tick Control %d" % idx)
            # Clear any mark against this item as the text is about to change
            markControl = self.getControl(FilmWiseViewer.MARK_IDS[idx])
            markControl.setVisible(False)

    def close(self):
        log("FilmWiseViewer: Closing window")
        self.isCloseFlag = True
        xbmcgui.WindowXMLDialog.close(self)

    def showSolution(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        # Make sure there is a solution
        if self.solution in [None, ""]:
            return

        # Make the request to get the full solution
        filmWise = FilmWiseCore()
        solutionDetails = filmWise.getSolution(self.solution)
        del filmWise

        if len(solutionDetails) > 0:
            # Set all the images for the quiz
            for i in range(0, 8):
                img = self.questions[i].get('image', None)
                if img is None:
                    continue
                else:
                    solutionImg = img.replace('.jpg', 'a.jpg')
                    log("showSolution: Solution Img = %s" % solutionImg)
                editControl = self.getControl(FilmWiseViewer.EDIT_BOX_IDS[i])
                answer = solutionDetails.get(solutionImg, '')
                log("showSolution: Answer Is %s" % answer)
                editControl.setText(answer)

                # Also need to replace the images
                if answer not in [None, ""]:
                    imageControl = self.getControl(FilmWiseViewer.IMAGE_IDS[i])
                    imageControl.setImage(solutionImg)

        # Disable the buttons, the only option when you have seen the solution is close
        checkControl = self.getControl(FilmWiseViewer.CHECK_BUTTON)
        checkControl.setVisible(False)
        solutionControl = self.getControl(FilmWiseViewer.SOLUTION_BUTTON)
        solutionControl.setVisible(False)

        # We actually leave the tick flag as it was so the user can see if they
        # had it correct
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    def checkAnswers(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        numQuestions = len(self.questions)
        if numQuestions > 8:
            numQuestions = 8

        numCorrectAnswers = 0
        # Read the answers that are populated
        for i in range(0, numQuestions):
            editControl = self.getControl(FilmWiseViewer.EDIT_BOX_IDS[i])
            enteredAnswer = editControl.getText()
            tag = self.questions[i]['name']
            if (enteredAnswer is not None) and len(enteredAnswer) > 0:
                answers = {tag: enteredAnswer}

                correctAnswers = 0
                # Check if this answer is already in the correct answers list
                if self.correctUserAnswers.get(tag, '') == enteredAnswer:
                    correctAnswers = 1
                else:
                    # Now make the request to check the answers
                    filmWise = FilmWiseCore()
                    correctAnswers = filmWise.checkAnswer(self.form, self.redirect, answers)
                    del filmWise

                isCorrect = False
                if correctAnswers > 0:
                    isCorrect = True
                    numCorrectAnswers = numCorrectAnswers + 1
                    self.correctUserAnswers[tag] = enteredAnswer

                self._setCorrectFlag(i, isCorrect)
                # Save the answer to the database
                if self.quizNum > 0:
                    self.database.addAnswer(self.quizNum, tag, enteredAnswer, isCorrect)
            else:
                self._setCorrectFlag(i)
                # No answer entered for this one, so clear any DB entry
                if self.quizNum > 0:
                    self.database.deleteAnswer(self.quizNum, tag)

        # Now set the score total
        self._setScore(numCorrectAnswers, numQuestions)

        xbmc.executebuiltin("Dialog.Close(busydialog)")

    # Method to toggle the correct and incorrect flags
    def _setCorrectFlag(self, idx, isCorrect=None):
        markControl = self.getControl(FilmWiseViewer.MARK_IDS[idx])
        if isCorrect is None:
            markControl.setVisible(False)
        else:
            if isCorrect:
                markControl.setImage('correct.png')
            else:
                markControl.setImage('incorrect.png')
            markControl.setVisible(True)

    # Sets the text display of the score
    def _setScore(self, numCorrectAnswers, numQuestions):
        scoreText = "[B]%s: %d/%d[/B]" % (ADDON.getLocalizedString(32007), numCorrectAnswers, numQuestions)
        log("checkAnswers: Setting score label to %s" % scoreText)
        labelControl = self.getControl(FilmWiseViewer.SCORE_LABEL_ID)
        labelControl.setLabel(scoreText)

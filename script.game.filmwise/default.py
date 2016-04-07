# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

from resources.lib.core import FilmWiseCore
from resources.lib.viewer import FilmWiseViewer

ADDON = xbmcaddon.Addon(id='script.game.filmwise')


#########################
# Main
#########################
if __name__ == '__main__':
    log("FilmWise: Started")
    xbmc.executebuiltin("ActivateWindow(busydialog)")

    filmWise = FilmWiseCore()
    # get the list of available quizzes
    quizList = filmWise.getQuizList()

    # Now the system has been loaded, we should update the last viewed setting
    if len(quizList) > 0:
        Settings.setLastViewed(quizList[0]['link'])

    displayList = []

    for quiz in quizList:
        displayName = "%s %s" % (quiz['date'], quiz['name'])
        displayList.append(displayName)

    xbmc.executebuiltin("Dialog.Close(busydialog)")

    # Show the list to the user
    select = xbmcgui.Dialog().select(ADDON.getLocalizedString(32001), displayList)
    if select < 0:
        log("FilmWise: Cancelled by user")
    else:
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        quiz = quizList[select]
        log("FilmWise: Selected quiz: %s (%s)" % (displayList[select], quiz['link']))

        # Now get the details of the selected quiz
        quizDetails = filmWise.getQuizData(quiz['link'])

        viewer = FilmWiseViewer.createFilmWiseViewer(quiz['number'], quiz['name'], quizDetails, quiz['solution'])
        xbmc.executebuiltin("Dialog.Close(busydialog)")

        viewer.doModal()

    del filmWise
    log("FilmWise: Ended")

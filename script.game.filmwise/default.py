# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcgui
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.game.filmwise')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings

from core import FilmWiseCore
from viewer import FilmWiseViewer

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
    select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32001), displayList)
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

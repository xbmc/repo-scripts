# -*- coding: utf-8 -*-
import xbmcaddon
import xbmcgui

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings

from resources.lib.core import FilmWiseCore
from resources.lib.viewer import FilmWiseViewer

ADDON = xbmcaddon.Addon(id='script.game.filmwise')
ICON = ADDON.getAddonInfo('icon')


##################################
# Main of the FilmWise Service
##################################
if __name__ == '__main__':
    log("FilmWise: Service Started")

    # Check if the settings mean we want to notify the user
    notifyRequired = Settings.isNotifyNewQuiz()

    if notifyRequired:
        log("FilmWise: Notify enabled")
        lastViewed = Settings.getLastViewed()
        if lastViewed not in [None, ""]:
            # Find out the current list
            filmWise = FilmWiseCore()
            quizList = filmWise.getQuizList()

            # Now the system has been loaded, we should update the last viewed setting
            if len(quizList) > 0:
                if lastViewed != quizList[0]['link']:
                    # Either display the notification or open the viewer automatically
                    if Settings.isAutoOpenNewQuiz():
                        log("FilmWise: Service auto starting quiz: %s" % quizList[0]['link'])

                        # Now get the details of the selected quiz
                        quizDetails = filmWise.getQuizData(quizList[0]['link'])

                        viewer = FilmWiseViewer.createFilmWiseViewer(quizList[0]['number'], quizList[0]['name'], quizDetails, quizList[0]['solution'])
                        viewer.doModal()

                        # Record that we actually viewed the latest quiz
                        Settings.setLastViewed(quizList[0]['link'])
                    else:
                        quizNum = ''
                        if quizList[0]['number'] > 0:
                            quizNum = " (#%d)" % quizList[0]['number']
                        msg = "%s%s" % (ADDON.getLocalizedString(32013).encode('utf-8'), quizNum)
                        xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001).encode('utf-8'), msg, ICON, 5000, False)
                else:
                    log("FilmWise: Latest quiz already viewed")
            else:
                log("FilmWise: No quiz found")

            del filmWise
    else:
        log("FilmWise: Notify disabled")

    log("FilmWise: Service Ended")

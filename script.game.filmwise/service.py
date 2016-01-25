# -*- coding: utf-8 -*-
import sys
import os
import xbmc
import xbmcaddon
import xbmcgui


__addon__ = xbmcaddon.Addon(id='script.game.filmwise')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings

from core import FilmWiseCore
from viewer import FilmWiseViewer


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
                        msg = "%s%s" % (__addon__.getLocalizedString(32013).encode('utf-8'), quizNum)
                        xbmcgui.Dialog().notification(__addon__.getLocalizedString(32001).encode('utf-8'), msg, __icon__, 5000, False)
                else:
                    log("FilmWise: Latest quiz already viewed")
            else:
                log("FilmWise: No quiz found")

            del filmWise
    else:
        log("FilmWise: Notify disabled")

    log("FilmWise: Service Ended")

# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.game.filmwise')
__icon__ = __addon__.getAddonInfo('icon')
__fanart__ = __addon__.getAddonInfo('fanart')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log

from core import FilmWiseCore
from viewer import FilmWiseViewer


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    def rootMenu(self):

        filmWise = FilmWiseCore()
        # get the list of available quizzes
        quizList = filmWise.getQuizList()

        log("FilmWisePlugin: Available Number of Quizzes is %d" % len(quizList))

        # Now the system has been loaded, we should update the last viewed setting
        if len(quizList) > 0:
            Settings.setLastViewed(quizList[0]['link'])

        for quiz in quizList:
            displaytitle = "%s %s" % (quiz['date'], quiz['name'])

            li = xbmcgui.ListItem(displaytitle, iconImage=__icon__)
            li.setProperty("Fanart_Image", __fanart__)
            url = self._build_url({'mode': 'quiz', 'number': quiz['number'], 'name': quiz['name'], 'link': quiz['link'], 'solution': quiz['solution']})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        del filmWise

        xbmcplugin.endOfDirectory(self.addon_handle)

    def viewQuiz(self, quizNum, name, link, solution=None):
        log("FilmWisePlugin: %d. %s (%s)" % (quizNum, name, link))
        xbmc.executebuiltin("ActivateWindow(busydialog)")

        filmWise = FilmWiseCore()
        quizDetails = filmWise.getQuizData(link)

        viewer = FilmWiseViewer.createFilmWiseViewer(quizNum, name, quizDetails, solution)
        xbmc.executebuiltin("Dialog.Close(busydialog)")

        viewer.doModal()

        del filmWise


################################
# Main of the FilmWise Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("FilmWisePlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("FilmWisePlugin: Mode is NONE - showing quiz list")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.rootMenu()
        del menuNav
    elif mode[0] == 'quiz':
        log("FilmWisePlugin: Mode is Quiz")

        quizNum = 0
        name = ''
        link = None
        solution = None

        quizNumItem = args.get('number', None)
        if (quizNumItem is not None) and (len(quizNumItem) > 0):
            quizNum = int(quizNumItem[0])

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        solutionItem = args.get('solution', None)
        if (solutionItem is not None) and (len(solutionItem) > 0):
            solution = solutionItem[0]

        linkItem = args.get('link', None)
        if (linkItem is not None) and (len(linkItem) > 0):
            link = linkItem[0]
            # Must have a link to display a quiz
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.viewQuiz(quizNum, name, link, solution)
            del menuNav

# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcaddon
import xbmcgui

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Import the common settings
from settings import log
from settings import Settings
from recap import Recap
from viewer import Viewer

ADDON = xbmcaddon.Addon(id='script.recap')


# Makes a request to have a given show added
def makeAdditionRequest(showName):
    log("Recap: Making request for %s" % showName)
    # Only allow submissions for things that are actually also in the Kodi Library
    # this will prevent lots of junk being sent

    # Start by getting the Id of the TvShow - this will be the ID of the Show, Season or Episode
    dbid = xbmc.getInfoLabel("ListItem.DBID")

    if dbid in [None, ""]:
        log("Recap: No DBID set for request")
        return False

    # Work out which interface the dbid is for
    cmd = None
    target = None
    titletag = 'title'
    if xbmc.getInfoLabel("ListItem.dbtype") == 'tvshow':
        cmd = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid":%s, "properties": ["title"]}, "id": 1}'
        target = 'tvshowdetails'
    elif xbmc.getInfoLabel("ListItem.dbtype") == 'episode':
        cmd = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid":%s, "properties": ["showtitle"]}, "id": 1}'
        target = 'episodedetails'
        titletag = 'showtitle'
    else:
        # There is no interface for the season, so we do not allow requests based on seasons
        log("Recap: Not a TV Show or Episode set for request")
        return False

    officialTitle = ""

    # Make the call to check the dbid
    json_query = xbmc.executeJSONRPC(cmd % str(dbid))
    json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_response = simplejson.loads(json_query)
    log(json_response)
    if ("result" in json_response) and (target in json_response['result']):
        officialTitle = json_response['result'][target][titletag]
        log("Recap: Request for title %s" % str(officialTitle))

    if officialTitle in [None, ""]:
        return False

    if officialTitle != showName:
        log("Recap: Show titles do not match - not allowing request")
        return False

    msg = '%s "%s"' % (ADDON.getLocalizedString(32005), showName)
    makeRequest = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32001), msg, ADDON.getLocalizedString(32023))

    # Check if we want to make a request to add the show
    if makeRequest:
        recap = Recap()
        additionResponse = recap.requestAddition(showName)

        # Check if the submission was OK
        if additionResponse:
            msg = '%s "%s"' % (ADDON.getLocalizedString(32029), showName)
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), msg)
        else:
            msg = '%s "%s"' % (ADDON.getLocalizedString(32028), showName)
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), msg, ADDON.getLocalizedString(32020))

    return True


#########################
# Main
#########################
def runRecap(previous=False):
    log("runRecap: Started")

    # First check to see if we have a TV Show already selected
    showName = None
    if xbmc.getInfoLabel("ListItem.dbtype") in ['tvshow', 'season', 'episode']:
        showName = xbmc.getInfoLabel("ListItem.TVShowTitle")

    autoDetectedShowName = False
    # If there is no video name available prompt for it
    if showName in [None, ""]:
        log("Recap: No TV Show detected, prompting user")

        # Prompt the user for the new name
        keyboard = xbmc.Keyboard('', ADDON.getLocalizedString(32014), False)
        keyboard.doModal()

        if keyboard.isConfirmed():
            try:
                showName = keyboard.getText().decode("utf-8")
            except:
                showName = keyboard.getText()
    else:
        autoDetectedShowName = True

    recap = Recap()
    selectedItem = None

    # If we have a TV Show, then we can start the search
    if showName not in [None, ""]:
        log("Recap: Searching for show %s" % showName)

        # Perform a search on the recap site
        searchMatches = recap.getSelection(showName)

        if (len(searchMatches) == 1) and Settings.autoSelectSingle():
            # If there is only one match automatically select it
            selectedItem = searchMatches[0]
        elif len(searchMatches) > 0:
            # More than one possible match - prompt the user
            displayList = []
            for aMatch in searchMatches:
                displayList.append(aMatch["name"])

            select = xbmcgui.Dialog().select(ADDON.getLocalizedString(32004), displayList)
            if select == -1:
                log("Recap: Show select cancelled by user")
            else:
                log("Recap: Selected show item %d" % select)
                selectedItem = searchMatches[select]

        # If we haven't found anything, then see if we should add it
        if (selectedItem in [None, ""]) and autoDetectedShowName:
            requestMade = makeAdditionRequest(showName)
            if not requestMade:
                msg = '%s "%s"' % (ADDON.getLocalizedString(32005), showName)
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), msg)

    selectedSeason = -1

    # Check if a selection has been made so that we know what show
    # we are looking for
    if selectedItem not in [None, ""]:
        # Load the show that we are interested in from the recap site
        seasons = recap.loadShowFromPage(selectedItem["link"])

        # Check which season will be displayed
        if len(seasons) == 0:
            log("Recap: No seasons found for %s" % searchMatches[selectedItem]["link"])
        elif len(seasons) == 1:
            log("Recap: Only one season exists")
            selectedSeason = seasons.keys()[0]
        else:
            # Check if we already have a season selected
            seasonNumber = None
            if xbmc.getInfoLabel("ListItem.dbtype") in ['season', 'episode']:
                seasonNumber = xbmc.getInfoLabel("ListItem.Season")

            if seasonNumber not in [None, ""]:
                if int(seasonNumber) in seasons.keys():
                    selectedSeason = int(seasonNumber)
                    log("Recap: Auto detected season %d" % selectedSeason)
                else:
                    log("Recap: Season not available %s" % str(seasonNumber))

            if selectedSeason < 1:
                log("Recap: Prompting user for season number")
                # Prompt the user to see which season they want
                displayList = []
                for seasonNumber in sorted(seasons.keys()):
                    displayList.append("%s %d" % (ADDON.getLocalizedString(32008), seasonNumber))

                selectTitle = "%s - %s" % (selectedItem["name"], ADDON.getLocalizedString(32007))
                select = xbmcgui.Dialog().select(selectTitle, displayList)
                if select == -1:
                    log("Recap: Season select cancelled by user")
                else:
                    log("Recap: Selected season item %d" % select)
                    seasonNumber = sorted(seasons.keys())[select]
                    selectedSeason = seasons[seasonNumber]["season"]

    selectedEpisode = -1
    # If we know what season we are looking for, then we can check the episode
    if selectedSeason > 0:
        # Load an additional given season
        episodes = recap.getEpisodeList(selectedSeason)

        # Check which episode will be displayed
        if len(seasons) == 0:
            log("Recap: No episodes found for %s season %d" % (searchMatches[selectedItem]["link"], selectedSeason))
        elif len(seasons) == 1:
            log("Recap: Only one episode exists")
            selectedEpisode = episodes.keys()[0]
        else:
            # Check if we can auto detect the episode number
            episodeNumber = None
            if xbmc.getInfoLabel("ListItem.dbtype") in ['episode']:
                episodeNumber = xbmc.getInfoLabel("ListItem.Episode")

            if episodeNumber not in [None, ""]:
                if int(episodeNumber) in episodes.keys():
                    selectedEpisode = int(episodeNumber)
                    log("Recap: Auto detected episode %d" % selectedEpisode)
                else:
                    log("Recap: Episode not available %s" % str(episodeNumber))

            if selectedEpisode < 1:
                log("Recap: Prompting user for episode number")
                # Prompt the user to see which season they want
                displayList = []
                for episodeNumber in sorted(episodes.keys()):
                    displayList.append("%s %d" % (ADDON.getLocalizedString(32009), episodeNumber))

                selectTitle = "%s - %s" % (selectedItem["name"], ADDON.getLocalizedString(32010))
                select = xbmcgui.Dialog().select(selectTitle, displayList)
                if select == -1:
                    log("Recap: Episode select cancelled by user")
                else:
                    log("Recap: Selected episode item %d" % select)
                    episodeNumber = sorted(episodes.keys())[select]
                    selectedEpisode = episodes[episodeNumber]["number"]

    # Check if an episode was selected
    if selectedEpisode > 0:
        # Check if we actually want th eprevious episode
        if previous:
            log("Recap: Checking for previous episode")
            if selectedEpisode > 1:
                selectedEpisode = selectedEpisode - 1
            elif selectedSeason > 1:
                selectedSeason = selectedSeason - 1
                # Get the last episode of this season
                episodes = recap.getEpisodeList(selectedSeason)
                selectedEpisode = sorted(episodes.keys())[-1]

        log("Recap: Selected Season %d, Episode %d" % (selectedSeason, selectedEpisode))

        # Get the slideshow for the selected season and episode
        slideshow = recap.getEpisodeSlideshow(selectedSeason, selectedEpisode)

        # The display title is the Program name, series, episode and episode name
        displayTitle = "%s - %s" % (selectedItem["name"], episodes[selectedEpisode]["title"])

        showWindow(displayTitle, episodes[selectedEpisode]["summary"], slideshow)

    del recap
    log("runRecap: Ended")


def showWindow(displayTitle, summary, slideshow):
    log("Recap: Showing window for %s" % displayTitle)

    # Allow TvTunes to continue playing
    xbmcgui.Window(12000).setProperty("TvTunesContinuePlaying", "True")

    viewer = Viewer.createViewer(displayTitle, summary, slideshow)

    autoInterval = Settings.getAutoSlideshowInterval()

    if autoInterval > 100:
        viewer.show()
        # Before starting the slideshow,see if there should be a delay
        delayStart = Settings.getAutoSlideshowDelay()
        if delayStart > 0:
            monitor = xbmc.Monitor()
            monitor.waitForAbort(delayStart)
            del monitor

        timeToNextSlide = autoInterval
        while (not viewer.isClosed()) and (not xbmc.abortRequested):
            xbmc.sleep(100)
            timeToNextSlide = timeToNextSlide - 100

            # Skip to the next image if it is time to
            if timeToNextSlide <= 0:
                timeToNextSlide = autoInterval
                viewer.showNextSlideshowImage()

    else:
        viewer.doModal()

    del viewer

    # No need to force TvTunes now we have closed the dialog
    xbmcgui.Window(12000).clearProperty("TvTunesContinuePlaying")

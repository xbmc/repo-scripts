# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcgui

# Import the common settings
from settings import log
from settings import Settings
from scraper import KidsInMindScraper
from scraper import CommonSenseMediaScraper
from scraper import DoveFoundationScraper
from scraper import MovieGuideOrgScraper
from viewer import DetailViewer
from viewer import SummaryViewer

ADDON = xbmcaddon.Addon(id='script.suitability')


#########################
# Main
#########################
class SuitabilityCore():
    @staticmethod
    def runForVideo(videoName, isTvShow=False):
        log("SuitabilityCore: Video Name = %s" % videoName)
        # Get the initial Source to use
        searchSource = Settings.getDefaultSource()

        selectedViewer = Settings.getDefaultViewer()

        while searchSource is not None:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            dataScraper = None
            if searchSource == Settings.KIDS_IN_MIND:
                dataScraper = KidsInMindScraper(videoName, isTvShow)
            elif searchSource == Settings.DOVE_FOUNDATION:
                dataScraper = DoveFoundationScraper(videoName, isTvShow)
            elif searchSource == Settings.MOVIE_GUIDE_ORG:
                dataScraper = MovieGuideOrgScraper(videoName, isTvShow)
            else:
                dataScraper = CommonSenseMediaScraper(videoName, isTvShow)

            searchMatches = dataScraper.getSelection()
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            selectedItem = None

            # Work out what provider we would switch to if the user wants to switch
            switchSource = Settings.getNextSource(searchSource)

            if len(searchMatches) < 1:
                # Offer searching by the other provider if there is one
                if switchSource is not None:
                    msg1 = "%s %s" % (ADDON.getLocalizedString(32005), videoName)
                    msg2 = "%s %s" % (ADDON.getLocalizedString(32010), ADDON.getLocalizedString(switchSource))
                    switchSearch = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32001), msg1, msg2)
                    # If the user wants to switch the search then tidy up then loop again
                    if switchSearch:
                        searchSource = switchSource
                    else:
                        searchSource = None
                else:
                    searchSource = None
            elif len(searchMatches) == 1:
                selectedItem = searchMatches[0]
            elif len(searchMatches) > 1:
                displayList = []
                for aMatch in searchMatches:
                    displayList.append(aMatch["name"])
                select = xbmcgui.Dialog().select(ADDON.getLocalizedString(32004), displayList)
                if select == -1:
                    log("Suitability: Cancelled by user")
                    selectedItem = None
                    msg = "%s %s" % (ADDON.getLocalizedString(32010), ADDON.getLocalizedString(switchSource))
                    switchSearch = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32001), msg)
                    # If the user wants to switch the search then tidy up then loop again
                    if switchSearch:
                        searchSource = switchSource
                    else:
                        searchSource = None
                else:
                    log("Suitability: Selected item %d" % select)
                    selectedItem = searchMatches[select]

            displayTitle = None
            displayContent = ""
            details = None

            if selectedItem is None:
                log("Suitability: No matching movie found")
            else:
                xbmc.executebuiltin("ActivateWindow(busydialog)")
                # Now get the details of the single film
                displayTitle = "%s: %s" % (ADDON.getLocalizedString(searchSource), selectedItem["name"])
                log("Suitability: Found film with name: %s" % selectedItem["name"])

                details = dataScraper.getSuitabilityData(selectedItem["link"])

                displayContent = dataScraper.getTextView(details)
                xbmc.executebuiltin("Dialog.Close(busydialog)")

                # Clear the search source as that will be used to decide if we close the window or
                # loop again
                searchSource = None

            del dataScraper

            if displayContent not in [None, ""]:
                # Allow TvTunes to continue playing
                xbmcgui.Window(12000).setProperty("TvTunesContinuePlaying", "True")

                changingViewer = True
                while changingViewer:
                    viewer = None
                    # Create the type of viewer we need
                    if selectedViewer == Settings.VIEWER_DETAILED:
                        viewer = DetailViewer.createDetailViewer(switchSource, displayTitle, displayContent)
                    else:
                        viewer = SummaryViewer.createSummaryViewer(switchSource, displayTitle, details["details"])

                    # Display the viewer
                    viewer.doModal()

                    # Dialog has been exited, check if we need to reload with a different view
                    changingViewer = viewer.isChangeViewer()
                    if changingViewer:
                        if selectedViewer == Settings.VIEWER_DETAILED:
                            selectedViewer = Settings.VIEWER_SUMMARY
                        else:
                            selectedViewer = Settings.VIEWER_DETAILED
                    else:
                        # Check if the user wants to just switch providers
                        if viewer.isSwitch():
                            searchSource = switchSource
                        else:
                            searchSource = None
                    del viewer

                # No need to force TvTunes now we have closed the dialog
                xbmcgui.Window(12000).clearProperty("TvTunesContinuePlaying")

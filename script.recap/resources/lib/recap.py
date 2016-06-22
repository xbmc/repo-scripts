# -*- coding: utf-8 -*-
import re
import urllib
import urllib2
import requests
import traceback
from BeautifulSoup import BeautifulSoup

import xbmc
import xbmcaddon

# Import the common settings
from settings import log
from settings import Settings

ADDON = xbmcaddon.Addon(id='script.recap')


# Class to load data from the recapguide.com website
class Recap():
    def __init__(self):
        self.host = "recapguide.com"
        self.baseUrl = "http://%s" % self.host
        self.seasons = {}

    def _getHtmlSource(self, url):
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'RecapKodi/1.0.x')

        doc = None
        try:
            response = urllib2.urlopen(req)
            # Holds the webpage that was read via the response.read() command
            doc = response.read()

            # Closes the connection after we have read the webpage.
            try:
                response.close()
            except:
                pass
                log("Recap: Failed to close connection for %s" % url)
        except:
            log("Recap: ERROR opening page %s" % url, xbmc.LOGERROR)
            log("Recap: %s" % traceback.format_exc(), xbmc.LOGERROR)
            return None
        return doc

    # Make a request to add a given show
    def requestAddition(self, showname):
        log("Recap: Requesting Addition for: %s" % showname)
        # Generate the URL used for the post request
        url = "%s/search/%s" % (self.baseUrl, showname)

        postData = {'csrfmiddlewaretoken': None, 'username': 'human', 'type': 'submit_tv', 'comment': None, 'email': ""}
        postData['comment'] = urllib.quote_plus(showname)
        postData['email'] = Settings.getEmailAddress()

        response = None
        try:
            client = requests.session()

            # Load the cookie first
            client.get(url)
            postData['csrfmiddlewaretoken'] = client.cookies['csrftoken']

            response = client.post(url, data=postData, headers=dict(Referer=url))
        except:
            log("Recap: Failed to send request for %s" % showname)
            log("Recap: %s" % traceback.format_exc(), xbmc.LOGERROR)

        submittedOk = False
        # Check if the submission was successful
        if response not in [None, ""]:
            log("Recap: Addition request response: %d" % response.status_code)
            if response.status_code == 200:
                submittedOk = True
                log("Recap: Addition request response: %s" % response.text)
            else:
                log("Recap: Addition request response: %s" % response.text, xbmc.LOGERROR)
        else:
            log("Recap: No response returned from addition request")

        return submittedOk

    # Gets a list of the possible TV Shows that match
    def getSelection(self, showname):
        log("Recap: Getting selection for name: %s" % showname)
        # Generate the URL and get the page
        url = "%s/search/%s" % (self.baseUrl, showname)
        html = self._getHtmlSource(url)

        soup = BeautifulSoup(''.join(html))

        searchMatches = []

        # Check each of the entries found
        for entries in soup.findAll('ul', {"class": "gallery row"}):
            for listItem in entries.findAll('li'):
                showLink = {"name": "", "link": None}
                # Get the link
                link = listItem.find('a')
                showLink["name"] = re.sub(r'<[^>]+>', '', str(link)).strip()
                showLink["link"] = "%s%s" % (self.baseUrl, link['href'])
                searchMatches.append(showLink)
                log("Recap: Search Match: %s {%s}" % (showLink["name"], showLink["link"]))

        return searchMatches

    # Loads the required details from the web
    def loadShowFromPage(self, showUrl):
        log("Recap: Loading Show information for %s" % showUrl)
        html = self._getHtmlSource(showUrl)
        soup = BeautifulSoup(''.join(html))

        indexSection = soup.find('div', {"class": "tv-sticky-nav"})

        if indexSection in [None, ""]:
            return None

        # Check to see if we have already loaded the core details
        if len(self.seasons) < 1:
            seasonSection = indexSection.find('ul', {"class": "tv-numbers"})
            if seasonSection in [None, ""]:
                return None

            # Check each of the entries found
            for listItem in seasonSection.findAll('li'):
                seasonDetails = {"season": None, "link": None, "episodes": None}
                # Get the link
                link = listItem.find('a')
                seasonDetails["season"] = int(listItem.text.strip())
                seasonDetails["link"] = "http://recapguide.com%s" % link['href']
                self.seasons[seasonDetails["season"]] = seasonDetails
                log("Recap: Season List: %d {%s}" % (seasonDetails["season"], seasonDetails["link"]))

        # When the page loads it will actually display a single section
        # this is normally the most recent season
        activeSeason = indexSection.find('a', {"class": "active"})

        activeSeasonNumber = -1
        # If there is no active season, then there is nothing to do
        if activeSeason not in [None, ""]:
            activeSeasonNumber = int(activeSeason.text)
            log("Recap: Found active season %d" % activeSeasonNumber)
            # Get the link
            if activeSeasonNumber not in self.seasons:
                log("Recap: Active season %d not in season list" % activeSeasonNumber)
                return self.seasons
        else:
            return self.seasons

        # Get all the episodes in the active season
        episodeIndex = soup.find('div', {"class": "season-index"})

        if episodeIndex not in [None, ""]:
            episodes = {}
            for episodeRow in episodeIndex.findAll('div', {"class": "row ep-row"}, False):
                titleSection = episodeRow.find('h3', {"class": "ep-title"})
                if titleSection not in [None, ""]:
                    episodeDetails = {"number": -1, "title": None, "link": None, "summary": None, "slideshow": None}

                    # Get the link to the episode
                    link = titleSection.find('a')
                    episodeDetails["link"] = "%s%s" % (self.baseUrl, link['href'])

                    episodeNum = episodeDetails["link"].split('-')[-1]
                    episodeDetails["number"] = int(episodeNum.replace('/', ''))

                    # Get the title
                    try:
                        episodeDetails["title"] = link.text.encode('utf-8', 'ignore')
                    except:
                        episodeDetails["title"] = link.text

                    log("Recap: Episode %d: {%s}" % (episodeDetails["number"], episodeDetails["link"]))

                    # Now we have the title, also get the description
                    description = episodeRow.find('span')
                    if description not in [None, ""]:
                        try:
                            episodeDetails["summary"] = description.text.encode('utf-8', 'ignore')
                        except:
                            episodeDetails["summary"] = description.text
                    # Add this episode to the list
                    episodes[episodeDetails["number"]] = episodeDetails

            # Store the episode details for this season
            self.seasons[activeSeasonNumber]["episodes"] = episodes

        return self.seasons

    def getEpisodeList(self, seasonNumber):
        log("Recap: Getting episode list for season %d" % seasonNumber)
        # Check to see if we already have details for this show
        if len(self.seasons) < 0:
            return None

        if seasonNumber not in self.seasons:
            print "Season does not exist: %d" % seasonNumber
            return None

        # Check if episode details are already loaded for this season
        if self.seasons[seasonNumber]["episodes"] not in [None, ""]:
            log("Recap: Episodes already loaded for season %d" % seasonNumber)
            return self.seasons[seasonNumber]["episodes"]

        # Get the link for the season
        self.loadShowFromPage(self.seasons[seasonNumber]["link"])
        return self.seasons[seasonNumber]["episodes"]

    # Loads the data required for the recap
    def getEpisodeSlideshow(self, seasonNumber, episodeNumber):
        log("Recap: Getting episode slideshow for season %d, episode %d" % (seasonNumber, episodeNumber))
        if len(self.seasons) < 0:
            return None

        if seasonNumber not in self.seasons:
            log("Recap: Season does not exist: %d" % seasonNumber)
            return None

        # Make sure the episode list has already been loaded
        # and get the list of episodes
        episodeList = self.getEpisodeList(seasonNumber)

        # Make sure the required episode number esits
        if episodeNumber not in episodeList:
            log("Recap: Episode %d does not exist for season %d" % (episodeNumber, seasonNumber))
            return None

        # Get the details of the episode that we need
        episodeDetails = episodeList[episodeNumber]

        # Check if we have loaded the details for the image slideshow
        if episodeDetails["slideshow"] in [None, ""]:
            (summary, slideshow) = self._loadSlideshow(episodeDetails["link"])
            episodeDetails["slideshow"] = slideshow

            # Check if we need the description
            if (summary not in [None, ""]) and (episodeDetails["summary"] in [None, ""]):
                episodeDetails["summary"] = summary

        return episodeDetails["slideshow"]

    # Loads and slideshow images for a given episode
    def _loadSlideshow(self, episodeUrl):
        log("Recap: Getting slideshow for %s" % episodeUrl)
        html = self._getHtmlSource(episodeUrl)
        soup = BeautifulSoup(''.join(html))

        summary = None
        description = soup.find('p', {"class": "description"})
        if description not in [None, ""]:
            try:
                summary = description.text.encode('utf-8', 'ignore')
            except:
                summary = description.text

        slideshowSection = soup.find('div', {"class": "slideshow"})

        if slideshowSection in [None, ""]:
            return (summary, [])

        # Get anything that is a thumbnail within this slideshow
        slideshow = []
        for thumbnail in slideshowSection.findAll('a', {"class": re.compile("thumb.*")}):
            # Start by getting the image for this slide
            imgTag = thumbnail.find('img')
            if imgTag not in [None, ""]:
                slideEntry = {"image": None, "caption": ""}
                # Most entries are stored in the data-src field, but the first entry is
                # stored in the src field
                if imgTag.get('data-src', None) not in [None, ""]:
                    slideEntry["image"] = imgTag["data-src"]
                else:
                    slideEntry["image"] = imgTag["src"]

                # Get the caption for this image
                subtitle = thumbnail.find('div', {"class": "subtitle"})
                if subtitle not in [None, ""]:
                    slideEntry["caption"] = subtitle.getText().strip()

                log("Recap: Slide: %s %s" % (slideEntry["image"], slideEntry["caption"]))

                slideshow.append(slideEntry)

        return (summary, slideshow)

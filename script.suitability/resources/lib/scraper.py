# -*- coding: utf-8 -*-
import re
import traceback
import xbmc
import xml.etree.ElementTree as ET
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup

# Import the common settings
from settings import log


#################################
# Core Scraper class
#################################
class Scrapper():
    def __init__(self, videoName, isTvShow=False):
        self.videoTitle = videoName
        self.isTvShow = isTvShow

    def getSelection(self):
        return []

    def getSuitabilityData(self):
        return []

    def _findBetween(self, s, first, last):
        textBlock = s
        try:
            textBlock = s.decode("utf-8")
        except:
            textBlock = s
        try:
            start = textBlock.index(first) + len(first)
            end = textBlock.index(last, start)
            return textBlock[start:end]
        except ValueError:
            return ""

    def _getHtmlSource(self, url):
        req = urllib2.Request(url)
        req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')

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
                log("Scrapper: Failed to close connection for %s" % url)
        except:
            log("Scrapper: ERROR opening page %s" % url, xbmc.LOGERROR)
            log("Scrapper: %s" % traceback.format_exc(), xbmc.LOGERROR)
            return None
        return doc

    def _narrowDownSearch(self, searchMatches):
        betterMatches = []
        for searchMatch in searchMatches:
            # Check if the whole name as an exact match is in the list
            if self.videoTitle.lower() in searchMatch["name"].lower():
                betterMatches.append(searchMatch)
                log("Scrapper: Best Match: %s {%s}" % (searchMatch["name"], searchMatch["link"]))

        if len(betterMatches) > 0:
            searchMatches = []
            # If there are multiple exact matches, then we want the smallest one as
            # that will be a better match, as sequels will often just append a number
            currentMaxSize = None
            for aMatch in betterMatches:
                if len(searchMatches) < 1:
                    searchMatches = [aMatch]
                    currentMaxSize = len(aMatch["name"])
                elif len(aMatch["name"]) < currentMaxSize:
                    searchMatches = [aMatch]
                # If the size is the same, then we need to display this as well
                elif len(aMatch["name"]) == currentMaxSize:
                    searchMatches.append(aMatch)

        return searchMatches

    # Get the text for a given chapter
    def _convertHtmlIntoKodiText(self, htmlText):
        plainText = htmlText.replace('<', ' <')
        plainText = plainText.replace('>', '> ')
        # Replace the bold tags
        plainText = plainText.replace('<b>', '[B]')
        plainText = plainText.replace('</b>', '[/B]')
        plainText = plainText.replace('<B>', '[B]')
        plainText = plainText.replace('</B>', '[/B]')
        # Replace italic tags
        plainText = plainText.replace('<i>', '[I]')
        plainText = plainText.replace('</i>', '[/I]')
        plainText = plainText.replace('<I>', '[I]')
        plainText = plainText.replace('</I>', '[/I]')
        # Add an extra line for paragraphs
        plainText = plainText.replace('</p>', '</p>\n')
        # The html &nbsp; is not handle s well by ElementTree, so replace
        # it with a space before we start
        plainText = plainText.replace('&nbsp;', ' ')

        try:
            plainText = ''.join(ET.fromstring(plainText).itertext())
        except:
            log("Scrapper: Failed to strip html text with ElementTree, error: %s" % traceback.format_exc())
            log("Scrapper: Using regex for content handling")
            plainText = re.sub(r'<[^>]+>', '', plainText)

        # Replace any quotes or other escape characters
        plainText = plainText.replace('&quote;', '"')
        plainText = plainText.replace('&nbsp;', ' ')
        plainText = plainText.replace('&#039;', "'")
        plainText = plainText.replace('&amp;', '&')

        # Need to remove double tags as they are not handled very well when
        # displayed, they do not get nested, so the first end will close all
        # instances of this tag
        plainText = plainText.replace('[B][B]', '[B]')
        plainText = plainText.replace('[/B][/B]', '[/B]')
        plainText = plainText.replace('[I][I]', '[I]')
        plainText = plainText.replace('[/I][/I]', '[/I]')

        # Remove empty space between tags, where there is no content
        plainText = re.sub("\[B]\s*\[/B]", "", plainText)
        plainText = re.sub("\[I\]\s*\[/I\]", "", plainText)

        # Remove blank lines at the start of the text
        plainText = plainText.lstrip('\n')
        plainText = plainText.lstrip(' ')

        # Remove extra white space
        plainText = re.sub('\s\s+', ' ', plainText)

        return plainText

    # Get the details in a format to be displayed in kodi
    def getTextView(self, fullDetails):
        displayContent = ""

        parentsAge = fullDetails.get("parentsAge", None)
        if parentsAge not in [None, ""]:
            displayContent += "[B]Parents Say:[/B] %s\n" % parentsAge
            log("Suitability: parentsAge: %s" % parentsAge)

        childsAge = fullDetails.get("childsAge", None)
        if childsAge not in [None, ""]:
            displayContent += "[B]Children Say:[/B] %s\n" % childsAge
            log("Suitability: childsAge: %s" % childsAge)

        summary = fullDetails.get("summary", None)
        if summary not in [None, ""]:
            displayContent += "[B]Summary:[/B] %s\n" % summary
            log("Suitability: Summary: %s" % summary)

        overview = fullDetails.get("overview", None)
        if overview not in [None, ""]:
            overview = self._convertHtmlIntoKodiText(overview)
            if len(displayContent) > 0:
                displayContent += "\n"
            displayContent += "[B]Overview[/B]\n%s\n" % overview
            log("Suitability: Overview: %s" % overview)

        if len(displayContent) > 0:
            displayContent += "\n"

        log("Suitability: ******************************")
        for detail in fullDetails["details"]:
            displayContent += "[B]%s - %d/10[/B]\n" % (detail["name"], detail["score"])
            log("Suitability: %s - %d/10" % (detail["name"], detail["score"]))
            if detail["description"] not in [None, ""]:
                displayContent += "%s\n\n" % detail["description"]
                log("Suitability: %s" % detail["description"])
            log("Suitability: ******************************")

        return displayContent


#################################
# Kids In Mind Scraper class
#################################
class KidsInMindScraper(Scrapper):
    def getSelection(self, narrowSearch=True):
        # Generate the URL and get the page
        search_url = "http://www.kids-in-mind.com/cgi-bin/search/search.pl?q=%s"
        url = search_url % urllib.quote_plus(self.videoTitle)
        html = self._getHtmlSource(url)

        soup = BeautifulSoup(''.join(html))

        # findAll('p', {"style": "font-family: Verdana; font-size: 11px; line-height:19px"})
        searchResults = soup.findAll('p', {"start": "1"})

        searchMatches = []
        # Check each of the entries found
        for entries in searchResults:
            for link in entries.findAll('a'):
                # Get the link
                videoName = self._convertHtmlIntoKodiText(link.string)
                videoUrl = link['href']
                searchMatches.append({"name": videoName, "link": videoUrl})
                log("KidsInMindScraper: Initial Search Match: %s {%s}" % (videoName, videoUrl))

        # The kids in mind search can often return lots of entries that do not
        # contain the words in the requested video, so we can try and narrow it down
        if narrowSearch:
            searchMatches = self._narrowDownSearch(searchMatches)

        return searchMatches

    def getSuitabilityData(self, videoUrl):
        html = self._getHtmlSource(videoUrl)
        soup = BeautifulSoup(''.join(html))

        ratings = soup.findAll('span', {"style": "border-bottom:1px dotted #3C3C3C; color:#3C3C3C; text-decoration:none; font-weight: bold"})

        details = []

        for rating in ratings:
            # Split the rating name from its value
            ratingPart = rating.getText().split(' ')

            if len(ratingPart) < 2:
                continue

            # Items without rating values can be skipped
            if not ratingPart[1].isdigit():
                continue

            # Replace bullet points
            paraText = str(rating.parent).replace('<br />\n<span style="font-family: Arial; font-size: 12px; font-weight:bold">&#9658;</span>', '***')
            # Replace HTML spaces
            paraText = paraText.replace('&nbsp;', ' ')
            # Get the text description for this value, for this we go to the parent and then
            # trim to just our section
            description = self._findBetween(paraText, rating.getText() + "</span> - ", "<br")
            # Remove extra white space
            description = re.sub('\s\s+', ' ', description)
            description = description.replace('***', '\n*')
            # Links are added in square brackets, so remove anything in square brackets
            description = re.sub('\[.*?\]', '', description)
            # Add these details to the list
            details.append({"name": ratingPart[0], "score": int(ratingPart[1]), "description": description})

        fullDetails = {}
        fullDetails["title"] = self.videoTitle
        fullDetails["details"] = details

        return fullDetails


#################################
# Common Sense Media class
#################################
class CommonSenseMediaScraper(Scrapper):
    def getSelection(self, narrowSearch=True):
        typeFilter = 'movie'
        if self.isTvShow:
            typeFilter = 'tv'
        # Generate the URL and get the page
        search_url = "https://www.commonsensemedia.org/search/%s?f[0]=field_reference_review_ent_prod%%253Atype%%3Acsm_" + typeFilter
        url = search_url % urllib.quote_plus(self.videoTitle)
        html = self._getHtmlSource(url)

        soup = BeautifulSoup(''.join(html))

        searchResults = soup.findAll('div', {"class": "views-field views-field-field-reference-review-ent-prod-title result-title"})

        searchMatches = []

        # Check each of the entries found
        for entries in searchResults:
            for link in entries.findAll('a'):
                # Get the link
                videoName = self._convertHtmlIntoKodiText(link.string)
                videoUrl = "https://www.commonsensemedia.org%s" % link['href']
                searchMatches.append({"name": videoName, "link": videoUrl})
                log("CommonSenseMediaScraper: Initial Search Match: %s {%s}" % (videoName, videoUrl))

        # The Common Sense Media search can often return lots of entries that do not
        # contain the words in the requested video, so we can try and narrow it down
        if narrowSearch:
            searchMatches = self._narrowDownSearch(searchMatches)

        return searchMatches

    def getSuitabilityData(self, videoUrl):
        html = self._getHtmlSource(videoUrl)
        soup = BeautifulSoup(''.join(html))

        sections = ["message", "role_model", "violence", "sex", "language", "consumerism", "drugs"]

        details = []
        for section in sections:
            detail = self._getRatingData(soup, section)
            if detail is not None:
                details.append(detail)

        fullDetails = {}
        fullDetails["title"] = self.videoTitle
        fullDetails["details"] = details

        # Get the summary for the video
        summary = soup.find('meta', {"property": "description"})
        if summary is not None:
            fullDetails["summary"] = summary.get('content', "")

        # Get the overview for the video
        overview = soup.find('div', {"class": "field field-name-field-parents-need-to-know field-type-text-long field-label-hidden"})
        if overview not in [None, ""]:
            fullDetails["overview"] = str(overview)

        # Get the proposed ages
        fullDetails["parentsAge"] = self._getAge(soup, "adult")
        fullDetails["childsAge"] = self._getAge(soup, "child")

        return fullDetails

    # Gets the rating information for a given section
    def _getRatingData(self, soup, pageSection):
        classValue = "field field-name-field-content-grid-type field-type-list-text field-label-hidden field-content-grid-type %s" % pageSection

        sectionName = soup.find('div', {"class": classValue})
        if sectionName is None:
            return None

        description = sectionName.parent.find('div', {"class": "field field-name-field-content-grid-rating-text field-type-text-long field-label-hidden"})

        scoreSection = sectionName.parent.find('div', {"class": "field field-name-field-content-grid-rating field-type-list-integer field-label-hidden"})

        # Our scores should all be 10 based, not 5 based like the web site
        score = 0
        if "content-grid-1" in str(scoreSection):
            score = 2
        if "content-grid-2" in str(scoreSection):
            score = 4
        if "content-grid-3" in str(scoreSection):
            score = 6
        if "content-grid-4" in str(scoreSection):
            score = 8
        if "content-grid-5" in str(scoreSection):
            score = 10

        return {"name": sectionName.getText().replace("&amp;", "&"), "score": score, "description": description.getText()}

    # Gets the target age data from the HTML
    def _getAge(self, soup, ageView):
        classValue = "user-review-statistics %s" % ageView

        # Get the proposed age
        age = ""
        ageSection = soup.find('div', {"class": classValue})
        if ageSection is not None:
            ageSection = ageSection.find('div', {"class": "csm-green-age"})
            if ageSection is not None:
                age = ageSection.getText()

        return age


#################################
# Dove Foundation Scraper class
#################################
class DoveFoundationScraper(Scrapper):
    def getSelection(self, narrowSearch=True):
        # Generate the URL and get the page
        search_url = "https://www.dove.org/?s=%s"
        url = search_url % urllib.quote_plus(self.videoTitle)
        html = self._getHtmlSource(url)

        soup = BeautifulSoup(''.join(html))

        searchResults = soup.findAll('h1', {"class": "entry-title"})

        searchMatches = []

        # Check each of the entries found
        for entries in searchResults:
            for link in entries.findAll('a'):
                # Get the link
                videoName = self._convertHtmlIntoKodiText(link.string)
                videoUrl = link['href']
                searchMatches.append({"name": videoName, "link": videoUrl})
                log("DoveFoundationScraper: Initial Search Match: %s {%s}" % (videoName, videoUrl))

        # The kids in mind search can often return lots of entries that do not
        # contain the words in the requested video, so we can try and narrow it down
        if narrowSearch:
            searchMatches = self._narrowDownSearch(searchMatches)

        return searchMatches

    def getSuitabilityData(self, videoUrl):
        html = self._getHtmlSource(videoUrl)
        soup = BeautifulSoup(''.join(html))

        ratingChart = soup.find('div', {"class": "rating-chart"})

        details = []

        if ratingChart is not None:
            # Get all the rating entries
            imgEntries = ratingChart.findAll('img')

            for img in imgEntries:
                # Get the rating based off of the image used
                srcImg = img.get('src', None)
                # Skip anything that doesn't have an image
                if srcImg in [None, ""]:
                    continue
                # Calculate the score using the name of the image
                score = -1
                if srcImg.endswith("/g0.jpg"):
                    score = 0
                elif srcImg.endswith("/g1.jpg"):
                    score = 2
                elif srcImg.endswith("/g2.jpg"):
                    score = 4
                elif srcImg.endswith("/g3.jpg"):
                    score = 6
                elif srcImg.endswith("/g4.jpg"):
                    score = 8
                elif srcImg.endswith("/g5.jpg"):
                    score = 10
                else:
                    continue

                # Get the name of the rating type
                name = img.get('alt', None)
                if name in [None, ""]:
                    continue

                # Get the text description of each rating
                description = img.get('title', None)
                if description not in [None, ""]:
                    removeSection = "<b>%s: </b>" % name
                    if removeSection in description:
                        description = description.replace(removeSection, "")
                    else:
                        # If it is a 2 word name the key is just the first word
                        if " " in name:
                            removeSection = "<b>%s: </b>" % name.split(" ")[0]
                            description = description.replace(removeSection, "")

                details.append({"name": name, "score": score, "description": description})

        fullDetails = {}
        fullDetails["details"] = details

        # Get the summary
        approvalText = soup.find('div', {"class": "approved-text"})
        if approvalText not in [None, ""]:
            fullDetails["summary"] = approvalText.getText()
            print fullDetails["summary"]

        return fullDetails


#################################
# Movie Guide Org Scraper class
#################################
class MovieGuideOrgScraper(Scrapper):
    def getSelection(self, narrowSearch=True):
        # Generate the URL and get the page
        search_url = "https://www.movieguide.org/?s=%s"
        url = search_url % urllib.quote_plus(self.videoTitle)
        html = self._getHtmlSource(url)

        soup = BeautifulSoup(''.join(html))

        searchResults = soup.findAll('h2')

        searchMatches = []

        # Check each of the entries found
        for entries in searchResults:
            for link in entries.findAll('a'):
                # Get the link
                videoName = self._convertHtmlIntoKodiText(link.string)
                try:
                    videoName = videoName.encode('ascii', 'ignore')
                except:
                    pass
                videoUrl = link['href']
                searchMatches.append({"name": videoName, "link": videoUrl})
                log("MovieGuideOrgScraper: Initial Search Match: %s {%s}" % (videoName, videoUrl))

        # The kids in mind search can often return lots of entries that do not
        # contain the words in the requested video, so we can try and narrow it down
        if narrowSearch:
            searchMatches = self._narrowDownSearch(searchMatches)

        return searchMatches

    def getSuitabilityData(self, videoUrl):
        html = self._getHtmlSource(videoUrl)
        soup = BeautifulSoup(''.join(html))

        ratingTable = soup.find('table', {"class": "content-qual-tbl"})

        details = []

        if ratingTable is not None:
            # Get all the rows in the table
            tableRows = ratingTable.findAll('tr')

            for row in tableRows:
                # Get the title of the row
                ratingTitle = row.find('td', {"class": "param-cell"})
                if ratingTitle not in [None, ""]:
                    # Now we have the section title work out what the rating is
                    dtEntries = row.findAll('td')
                    rating = 0
                    ratingCount = 0
                    for entry in dtEntries:
                        if entry != ratingTitle:
                            # Check for the case where there is none
                            if "circle-green" in str(entry):
                                rating = ratingCount
                                break
                            ratingCount = ratingCount + 1
                            # Bad entries are marked with red
                            if "circle-red" in str(entry):
                                rating = ratingCount
                                break
                    # convert the ratings into an out-of-10 score
                    if rating == 2:
                        rating = 3
                    elif rating == 3:
                        rating = 6
                    elif rating == 4:
                        rating = 10
                    details.append({"name": ratingTitle.string, "score": rating, "description": ""})

        fullDetails = {}
        fullDetails["title"] = self.videoTitle
        fullDetails["details"] = details

        # Now get the details about the video
        contentHeader = soup.find('div', {"class": "content-qual-header"})

        if contentHeader is not None:
            summarySection = contentHeader.find('div', {"class": "content"})
            if summarySection is not None:
                category = summarySection.find('strong', {"style": "color:#545454;"})
                if category is not None:
                    fullDetails["summary"] = category.getText().strip()
                    if summarySection.get('title', None) not in [None, ""]:
                        fullDetails["summary"] = "%s - %s " % (fullDetails["summary"], summarySection['title'])
                        log("MovieGuideOrgScraper: Summary details = %s" % fullDetails["summary"])

        # Now get the text description
        contentBreakdown = soup.find('div', {"class": "content_content"})

        if contentBreakdown is not None:
            content = contentBreakdown.string
            if content in [None, ""]:
                content = str(contentBreakdown)
            if content not in [None, ""]:
                if content.startswith("CONTENT:"):
                    content = content[8:]
                try:
                    content = content.encode('utf-8', 'ignore')
                except:
                    pass
                try:
                    content = content.decode('utf-8', 'ignore')
                except:
                    pass
                fullDetails["overview"] = content.strip()

        return fullDetails

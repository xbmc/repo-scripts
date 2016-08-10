# -*- coding: utf-8 -*-
import sys
import urllib2
import traceback

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

from settings import log


class MpaaLookup():
    def __init__(self):
        self.imdb_url_prefix = 'http://www.omdbapi.com/'

    # Perform a lookup for the MPAA rating, this will only return the US version
    # of the rating
    def getMpaaRatings(self, name, year=''):
        mpaa = None
        if year not in [None, "", "0"]:
            # First try it as a TV Show and year
            mpaa = self.getIMDB_mpaa_by_name(name, str(year), True)

        # Check to see if a match was found, if not try without the year
        if mpaa in [None, ""]:
            mpaa = self.getIMDB_mpaa_by_name(name, '', True)

        # If no match was found as a TV Show, look for movies with this year
        if (mpaa in [None, ""]) and (year not in [None, "", "0"]):
            mpaa = self.getIMDB_mpaa_by_name(name, str(year), False)

        if mpaa in [None, ""]:
            mpaa = self.getIMDB_mpaa_by_name(name, '', False)

        return mpaa

    # Get the MPAA from imdb
    def getIMDB_mpaa_by_name(self, name, year='', isTvShow=True):
        log("IdLookup: Getting IMDB Mpaa by name %s, year=%s, tv=%s" % (name, year, str(isTvShow)))
        clean_name = urllib2.quote(name)
        query = '?t=%s' % clean_name

        if year not in [None, '', '0']:
            query = '%s&y=%s' % (query, str(year))

        if isTvShow:
            query = '%s&type=series' % query
        else:
            query = '%s&type=movie' % query

        url = "%s%s" % (self.imdb_url_prefix, query)

        log("MpaaLookup: Using call: %s" % url)
        json_details = self._makeCall(url)

        mpaa = None
        if json_details not in [None, ""]:
            json_response = json.loads(json_details)

            if json_response.get('Response', 'False') == 'True':
                if 'Rated' in json_response:
                    mpaa = json_response.get('Rated', None)
                    if mpaa not in [None, ""]:
                        mpaa = str(mpaa)
                        log("MovieLookup: Found mpaa %s" % str(mpaa))
                        if mpaa in ["N/A"]:
                            mpaa = None
            else:
                log("MpaaLookup: No results returned for imdb mpaa search")

        return mpaa

    # Perform the API call
    def _makeCall(self, url):
        log("MpaaLookup: Making query using %s" % url)
        resp_details = None
        try:
            req = urllib2.Request(url)
            req.add_header('Accept', 'application/json')
            response = urllib2.urlopen(req)
            resp_details = response.read()
            try:
                response.close()
                log("MpaaLookup: Request returned %s" % resp_details)
            except:
                pass
        except:
            log("MpaaLookup: Failed to retrieve details from %s: %s" % (url, traceback.format_exc()))

        return resp_details

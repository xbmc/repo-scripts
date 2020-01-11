import requests
import threading
from ... import util

API_KEY = '99ccac3e0d7fd2c7a076beea141c1057'
BASE_URL = 'https://api.themoviedb.org/3/movie/{endpoint}?language=en-US&api_key=' + API_KEY
UPCOMING_URL = {'endpoint': 'upcoming', 'params': '&page={page}'}
DETAILS_URL = {'params': '&append_to_response=videos,release_dates'}

class Scraper(object):
    def __init__(self):
        pass

    def apiGet(self, url):
        response = requests.get(url)
        return response.json()

    def getUpcoming(self, pages=1):
        upcoming = []

        for page in range(1, pages + 1):
            data = self.apiGet(BASE_URL.format(endpoint=UPCOMING_URL['endpoint']) + UPCOMING_URL['params'].format(page=page))
            upcoming += data['results']

        return upcoming

    def getDetails(self, ID):
        details = self.apiGet(BASE_URL.format(endpoint=ID) + DETAILS_URL['params'])
        if 'status_message' in details:
            util.DEBUG_LOG('Failed to get TMDB details: {0}'.format(details['status_message']))
            return None

        if not details.get('videos'):
            util.DEBUG_LOG('TMDB details had no videos: {0}'.format(details['id']))
            return None

        return details

    def getDetailsThreaded(self, ID, results):
        try:
            details = self.getDetails(ID)
            if details is None:
                return
            results.append(details)
        except:
            import traceback
            traceback.print_exc()

    def getTrailers(self):
        movies = self.getUpcoming(2)

        threads = []
        trailers = []

        # We can only do 40 requests every 10 seconds, and we already used 2 to get the list
        for movie in movies[:38]:
            thread = threading.Thread(target=self.getDetailsThreaded, args=(movie['id'], trailers))
            threads.append(thread)
            thread.start()

        for t in threads:
            t.join()

        return trailers

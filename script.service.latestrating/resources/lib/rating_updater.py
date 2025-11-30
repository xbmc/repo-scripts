# --------------------------------------------------------------------------------
# Latest Rating Service for Kodi
# Copyright (C) 2024
# --------------------------------------------------------------------------------
# This program is derived in part from the Kodi TV Show Scraper
# (https://github.com/xbmc/metadata.tvshows.themoviedb.org.python)
# which is licensed under GPL-3.0.
# --------------------------------------------------------------------------------
import xbmc
import xbmcaddon
import json
import requests
import re
from datetime import datetime, timedelta
from resources.lib.logger import Logger
from resources.lib.rate_limiter import RateLimiter

# Rating fetch functionality derived from Kodi's official TV Show scraper:
# https://github.com/xbmc/metadata.tvshows.themoviedb.org.python
# Specifically:
# - IMDb rating logic from libs/imdbratings.py
# - Trakt rating logic from libs/traktratings.py

IMDB_RATINGS_URL = 'https://www.imdb.com/title/{}/'
IMDB_JSON_REGEX = re.compile(r'<script type="application/ld\+json">(.*?)</script>')
IMDB_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'Accept': 'application/json'
}

# Rate limits (calls per second)
IMDB_RATE_LIMIT = 2   # 2 request per second
TRAKT_RATE_LIMIT = 2  # 2 request per second

TRAKT_HEADERS = {
    # Not sure if I can keep this info intact
    'User-Agent': 'Kodi TV Show scraper by Team Kodi; contact pkscout@kodi.tv',
    'Accept': 'application/json',
    # The Trakt API key here came from offical scraper's code mentioned above too
    'trakt-api-key': '90901c6be3b2de5a4fa0edf9ab5c75e9a5a0fef2b4ee7373d8b63dcf61f95697',
    'trakt-api-version': '2',
    'Content-Type': 'application/json'
}

TRAKT_SHOW_URL = 'https://api.trakt.tv/shows/{}'
TRAKT_MOVIE_URL = 'https://api.trakt.tv/movies/{}'
TRAKT_EP_URL = TRAKT_SHOW_URL + '/seasons/{}/episodes/{}/ratings'

class RatingUpdater:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.logger = Logger()
        self.rating_sources = self._get_enabled_sources()
        self.rate_limiters = {
            'imdb': RateLimiter(IMDB_RATE_LIMIT),
            'trakt': RateLimiter(TRAKT_RATE_LIMIT)
        }
        
    def _get_enabled_sources(self):
        sources = []
        if self.addon.getSettingBool('use_imdb'):
            sources.append('imdb')
        if self.addon.getSettingBool('use_trakt'):
            sources.append('trakt')
        
        if not sources:
            # Ensure at least one source is enabled
            self.addon.setSettingBool('use_imdb', True)
            sources.append('imdb')
            self.logger.warning("No rating source selected, defaulting to IMDb")
        
        return sources

    def update_library_ratings(self):
        if self.addon.getSettingBool('update_movies'):
            self.update_movies()
        
        #TV Shows
        if self.addon.getSettingBool('update_tvshows'):
            self.update_tvshow_episodes()

    def update_movies(self):
        self.logger.info("Starting movie ratings update")
        movies = self._get_movies()
        for movie in movies:
            try:
                old_rating = round(float(movie.get('rating', 0)), 1)
                new_rating = self._fetch_rating(movie['imdbnumber'], is_movie=True)
                if new_rating and new_rating != old_rating:
                    self._update_movie_rating(movie['movieid'], new_rating)
                    self.logger.update_result(f"Movie: {movie['title']} - Rating: {old_rating} → {new_rating}")
            except Exception as e:
                self.logger.error(f"Error updating {movie['title']}: {str(e)}")

    def update_tvshow_episodes(self):
        """Update ratings for TV show episodes"""
        self.logger.info("Starting TV show episode ratings update")
        episodes = self._get_tvshow_episodes()
        for episode in episodes:
            try:
                old_rating = round(float(episode.get('rating', 0)), 1)
                show_title = episode.get('showtitle', 'Unknown Show')
                season = episode.get('season')
                episode_num = episode.get('episode')
                
                self.logger.info(f"Processing {show_title} S{season:02d}E{episode_num:02d}")
                
                new_rating = self._fetch_rating(
                    episode,  # Pass entire episode object
                    is_movie=False,
                    season=season,
                    episode=episode_num
                )

                if new_rating and new_rating != old_rating:
                    self._update_episode_rating(episode['episodeid'], new_rating)
                    self.logger.update_result(f"TV: {show_title} S{season:02d}E{episode_num:02d} - Rating: {old_rating} → {new_rating}")
            except Exception as e:
                self.logger.error(f"Error updating {show_title} S{season:02d}E{episode_num:02d}: {str(e)}")

    def _get_movies(self):
        try:
            years_back = self.addon.getSettingInt('movie_years_back')
            current_year = datetime.now().year
            cutoff_year = current_year - years_back
            command = {
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.GetMovies',
                'params': {
                    'properties': [
                        'uniqueid',
                        'rating',
                        'year',
                        'title'
                    ]
                },
                'id': 1
            }
            
            command_str = json.dumps(command)
            self.logger.debug(f"Sending detailed GetMovies command: {command_str}")
            result = xbmc.executeJSONRPC(command_str)
            self.logger.debug(f"Detailed GetMovies raw response: {result}")
            
            if not result:
                self.logger.error("Empty response from JSON-RPC GetMovies call")
                return []
            
            response = json.loads(result)
            movies = response.get('result', {}).get('movies', [])
            self.logger.debug(f"Found {len(movies)} movies, cutoff year: {cutoff_year}")
            
            # Filter movies by year and extract IMDb ID
            recent_movies = []
            for movie in movies:
                if movie.get('year', 0) >= cutoff_year:
                    # uniqueid contains IMDb ID in format {'imdb': 'tt1234567', ...}
                    unique_ids = movie.get('uniqueid')
                    if not isinstance(unique_ids, dict):
                        continue
                        
                    imdb_id = unique_ids.get('imdb', '')
                    if not imdb_id:
                        continue
                        
                    movie['imdbnumber'] = imdb_id
                    recent_movies.append(movie)
            
            self.logger.debug(f"After year filter: {len(recent_movies)} movies")
            return recent_movies
        except Exception as e:
            self.logger.error(f"Error in _get_movies: {str(e)}")
            return []

    def _get_tvshow_episodes(self):
        """Get TV show episodes that need rating updates"""
        months_back = self.addon.getSettingInt('tvshow_months_back')
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)
        
        # First get all TV shows to get their IMDb IDs
        shows_command = {
            'jsonrpc': '2.0',
            'method': 'VideoLibrary.GetTVShows',
            'params': {
                'properties': [
                    'uniqueid'
                ]
            },
            'id': 1
        }
        
        try:
            command_str = json.dumps(shows_command)
            self.logger.debug(f"Sending GetTVShows command: {command_str}")
            result = xbmc.executeJSONRPC(command_str)
            
            if not result:
                self.logger.error("Empty response from JSON-RPC GetTVShows call")
                return []
            
            response = json.loads(result)
            shows = response.get('result', {}).get('tvshows', [])
            
            # Create a mapping of tvshowid to show IMDb ID
            show_imdb_map = {}
            for show in shows:
                unique_ids = show.get('uniqueid')
                if isinstance(unique_ids, dict):
                    imdb_id = unique_ids.get('imdb', '')
                    if imdb_id:
                        show_imdb_map[show['tvshowid']] = imdb_id
            
            # Now get all episodes
            episodes_command = {
                'jsonrpc': '2.0',
                'method': 'VideoLibrary.GetEpisodes',
                'params': {
                    'properties': [
                        'season',
                        'episode',
                        'firstaired',
                        'rating',
                        'showtitle',
                        'tvshowid',
                        'uniqueid'
                    ]
                },
                'id': 1
            }
            
            command_str = json.dumps(episodes_command)
            self.logger.debug(f"Sending GetEpisodes command: {command_str}")
            result = xbmc.executeJSONRPC(command_str)
            
            if not result:
                self.logger.error("Empty response from JSON-RPC GetEpisodes call")
                return []
            
            response = json.loads(result)
            episodes = response.get('result', {}).get('episodes', [])
            self.logger.debug(f"Found {len(episodes)} total episodes")
            
            # Filter episodes by air date and add both IMDb IDs
            recent_episodes = []
            for episode in episodes:
                if self._is_recent_episode(episode, cutoff_date):
                    # Get show's IMDb ID from our mapping
                    show_imdb = show_imdb_map.get(episode['tvshowid'])
                    if not show_imdb:
                        continue
                        
                    # Get episode's IMDb ID
                    unique_ids = episode.get('uniqueid')
                    if not isinstance(unique_ids, dict):
                        continue
                        
                    episode_imdb = unique_ids.get('imdb', '')
                    if not episode_imdb:
                        continue
                    
                    # Store both IDs
                    episode['imdbnumber'] = episode_imdb  # For IMDb API
                    episode['show_imdbnumber'] = show_imdb  # For Trakt API
                    recent_episodes.append(episode)
            
            self.logger.debug(f"Found {len(recent_episodes)} recent episodes with IMDb IDs")
            return recent_episodes
            
        except Exception as e:
            self.logger.error(f"Error in _get_tvshow_episodes: {str(e)}")
            return []

    def _is_recent_episode(self, episode, cutoff_date):
        """Check if episode aired after the cutoff date"""
        date_str = episode.get('firstaired', '')
        if not date_str:
            return False
        
        try:
            # Air date format: YYYY-MM-DD
            air_date = datetime.strptime(date_str, '%Y-%m-%d')
            return air_date >= cutoff_date
        except ValueError:
            self.logger.error(f"Invalid air date format: {date_str}")
            return False
        
    def _fetch_rating(self, imdb_id, is_movie=True, season=None, episode=None):
        """
        Fetch rating from external API
        Args:
            imdb_id: The IMDB ID of the movie or show
            is_movie: True if fetching movie rating, False for TV show
            season: Season number for TV shows (optional)
            episode: Episode number for TV shows (optional)
        Returns:
            float: Weighted average rating or None if no ratings found
        """
        total_rating_sum = 0
        total_vote_count = 0
        
        for source in self.rating_sources:
            try:
                rating = self._fetch_rating_from_source(
                    source, imdb_id, is_movie, season, episode
                )
                if rating is not None and isinstance(rating, tuple):
                    self.logger.info(f"New rating from {source}: {rating}")
                    rating_value, vote_count = rating
                    if rating_value > 0 and vote_count > 0:  # Only include valid ratings
                        total_rating_sum += rating_value * vote_count
                        total_vote_count += vote_count
            except Exception as e:
                self.logger.error(f"Error fetching {source} rating: {str(e)}")
        
        if total_vote_count == 0:
            return None
        
        # Calculate weighted average and round to 1 decimal place
        weighted_average = round(total_rating_sum / total_vote_count, 1)
        self.logger.info(f"New weighted average rating: {weighted_average}")
        return weighted_average

    def _fetch_rating_from_source(self, source, imdb_id, is_movie, season=None, episode=None):
        """
        Fetch rating from a specific source
        Args:
            source: 'imdb' or 'trakt'
            imdb_id: For movies: IMDb ID
                    For TV: Dictionary containing both episode and show IMDb IDs
            is_movie: True if fetching movie rating, False for TV show
            season: Season number for TV shows (optional)
            episode: Episode number for TV shows (optional)
        Returns: tuple(rating, vote_count) or None
                rating: average rating from the source
                vote_count: number of votes for this rating
        """
        if source == 'imdb':
            # For IMDb, use episode ID for TV shows
            episode_id = imdb_id if is_movie else imdb_id['imdbnumber']
            return self._fetch_imdb_rating(episode_id, is_movie, season, episode)
        elif source == 'trakt':
            # For Trakt, use show ID for TV shows
            show_id = imdb_id if is_movie else imdb_id['show_imdbnumber']
            return self._fetch_trakt_rating(show_id, is_movie, season, episode)
        
        return -1, -1

    def _fetch_imdb_rating(self, imdb_id, is_movie, season=None, episode=None):
        """Get IMDb rating and vote count"""
        try:
            # Wait for rate limit
            self.rate_limiters['imdb'].wait_for_token('imdb')
            
            # Make request to IMDb
            response = requests.get(IMDB_RATINGS_URL.format(imdb_id), headers=IMDB_HEADERS)
            response.raise_for_status()
            
            # Find and parse JSON data
            match = re.search(IMDB_JSON_REGEX, response.text)
            if not match:
                self.logger.error(f"No IMDb rating data found for {imdb_id}")
                return -1, -1
            
            imdb_json = json.loads(match.group(1))
            imdb_ratings = imdb_json.get("aggregateRating", {})
            
            rating = imdb_ratings.get("ratingValue")
            votes = imdb_ratings.get("ratingCount")
            
            if rating is not None and votes is not None:
                self.rate_limiters['imdb'].add_call('imdb')
                return float(rating), int(votes)
            
            return -1, -1
            
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Error fetching IMDb rating for {imdb_id}: {str(e)}")
            return -1, -1

    def _fetch_trakt_rating(self, imdb_id, is_movie, season=None, episode=None):
        # Hardcode a default client ID or return None if Trakt is disabled
        try:
            # Wait for rate limit
            self.rate_limiters['trakt'].wait_for_token('trakt')
            
            # Determine URL based on content type and parameters
            if is_movie:
                url = TRAKT_MOVIE_URL.format(imdb_id)
                params = {'extended': 'full'}
            elif season and episode:
                url = TRAKT_EP_URL.format(imdb_id, season, episode)
                params = None
            else:
                url = TRAKT_SHOW_URL.format(imdb_id)
                params = {'extended': 'full'}
            
            # Make request to Trakt
            response = requests.get(url, headers=TRAKT_HEADERS, params=params)
            response.raise_for_status()
            
            data = response.json()
            rating = data.get('rating')
            votes = data.get('votes')
            
            if rating is not None and votes is not None:
                self.rate_limiters['trakt'].add_call('trakt')
                return float(rating), int(votes)
            
            return -1, -1
            
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Error fetching Trakt rating for {imdb_id}: {str(e)}")
            return -1, -1

    def _update_movie_rating(self, movie_id, rating):
        command = {
            'jsonrpc': '2.0',
            'method': 'VideoLibrary.SetMovieDetails',
            'params': {'movieid': movie_id, 'rating': rating},
            'id': 1
        }
        try:
            command_str = json.dumps(command)
            self.logger.debug(f"Sending SetMovieDetails command: {command_str}")
            result = xbmc.executeJSONRPC(command_str)
            self.logger.debug(f"SetMovieDetails raw response: {result}")
            
            if not result:
                self.logger.error("Empty response from JSON-RPC SetMovieDetails call")
            else:
                response = json.loads(result)
                self.logger.debug(f"SetMovieDetails parsed response: {response}")
        except Exception as e:
            self.logger.error(f"Error in _update_movie_rating: {str(e)}")

    def _update_episode_rating(self, episode_id, rating):
        command = {
            'jsonrpc': '2.0',
            'method': 'VideoLibrary.SetEpisodeDetails',
            'params': {'episodeid': episode_id, 'rating': rating},
            'id': 1
        }
        try:
            command_str = json.dumps(command)
            self.logger.debug(f"Sending SetEpisodeDetails command: {command_str}")
            result = xbmc.executeJSONRPC(command_str)
            self.logger.debug(f"SetEpisodeDetails raw response: {result}")
            
            if not result:
                self.logger.error("Empty response from JSON-RPC SetEpisodeDetails call")
            else:
                response = json.loads(result)
                self.logger.debug(f"SetEpisodeDetails parsed response: {response}")
        except Exception as e:
            self.logger.error(f"Error in _update_episode_rating: {str(e)}")


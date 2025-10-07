from urllib.parse import unquote
from difflib import SequenceMatcher
import json
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon

from resources.lib.utilities import log, normalize_string

# Simple cache for library queries to avoid repeated calls
_library_cache = {}
_cache_max_age = 300  # 5 minutes

def _get_cache_key(method, params):
    """Generate a cache key for library queries"""
    import hashlib
    cache_str = f"{method}:{json.dumps(params, sort_keys=True) if params else 'None'}"
    return hashlib.md5(cache_str.encode()).hexdigest()

def _is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    import time
    return time.time() - cache_entry.get('timestamp', 0) < _cache_max_age

def _get_from_cache(method, params):
    """Get result from cache if available and valid"""
    cache_key = _get_cache_key(method, params)
    if cache_key in _library_cache:
        cache_entry = _library_cache[cache_key]
        if _is_cache_valid(cache_entry):
            log(__name__, f"📋 Cache hit for {method}")
            return cache_entry['result']
        else:
            # Remove expired entry
            del _library_cache[cache_key]
    return None

def _store_in_cache(method, params, result):
    """Store result in cache"""
    import time
    cache_key = _get_cache_key(method, params)
    _library_cache[cache_key] = {
        'result': result,
        'timestamp': time.time()
    }
    log(__name__, f"📋 Cached result for {method}")

__addon__ = xbmcaddon.Addon()


def get_file_path():
    return xbmc.Player().getPlayingFile()


# ---------- Small helpers ----------

def _strip_imdb_tt(value):
    if not value:
        return None
    s = str(value).strip()
    if s.startswith("tt"):
        s = s[2:]
    return s if s.isdigit() else None


def _extract_basic_tv_info(filename):
    """Extract basic TV show info from filename using simple regex"""
    import re
    
    # Remove file extension
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Pattern to match TV show episodes: S##E## or Season##Episode##
    season_episode_patterns = [
        r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S01E01, s01e01
        r'(\d{1,2})x(\d{1,2})',  # 1x01
    ]
    
    for pattern in season_episode_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            season_num = match.group(1)
            episode_num = match.group(2)
            # Extract show title (everything before the season/episode pattern)
            show_title = name[:match.start()].strip()
            # Clean up the show title
            show_title = re.sub(r'[._-]', ' ', show_title).strip()
            show_title = re.sub(r'\s+', ' ', show_title)  # Multiple spaces to single
            return show_title, season_num, episode_num
    
    return None, None, None



def _query_kodi_library_for_movie(movie_title, year=None, dbid=None):
    """Query Kodi library for movie IDs"""
    if not movie_title and not dbid:
        return None, None, None

    try:
        # If we have a specific database ID, query that movie directly
        if dbid and str(dbid).isdigit():
            query_params = {
                "movieid": int(dbid),
                "properties": ["imdbnumber", "uniqueid", "title", "year"]
            }
            result = _jsonrpc("VideoLibrary.GetMovieDetails", query_params, use_cache=False)
            if result and "moviedetails" in result:
                movie = result["moviedetails"]
                return _extract_movie_ids(movie)

        # Search by title if no dbid or dbid query failed
        if movie_title:
            query_params = {
                "properties": ["imdbnumber", "uniqueid", "title", "year"],
                "limits": {"end": 100}
            }
            result = _jsonrpc("VideoLibrary.GetMovies", query_params, use_cache=False)

            if result and "movies" in result and result["movies"]:
                matching_movies = []
                for movie in result["movies"]:
                    movie_title_lib = movie.get('title', '').lower()
                    search_title_lower = movie_title.lower()

                    if (search_title_lower in movie_title_lib or
                        movie_title_lib in search_title_lower):
                        matching_movies.append(movie)

                if matching_movies:
                    best_movie = _select_best_movie_match(matching_movies, movie_title, year)
                    if best_movie:
                        return _extract_movie_ids(best_movie)

    except Exception as e:
        log(__name__, f"Failed to query library for movie: {e}")

    return None, None, None

def _select_best_movie_match(movies, search_title, search_year=None):
    """Select the best matching movie from library results"""
    if not movies:
        return None

    if len(movies) == 1:
        return movies[0]

    best_score = 0
    best_movie = None

    for movie in movies:
        score = 0
        movie_title = movie.get('title', '')
        movie_year = movie.get('year')

        # Title matching score
        if search_title:
            title_similarity = SequenceMatcher(None, search_title.lower(), movie_title.lower()).ratio() * 100
            score += title_similarity

            # Exact title match bonus
            if search_title.lower() == movie_title.lower():
                score += 50

        # Year matching bonus
        if search_year and movie_year:
            year_diff = abs(int(search_year) - movie_year)
            if year_diff == 0:
                score += 25
            elif year_diff <= 1:
                score += 15

        if score > best_score:
            best_score = score
            best_movie = movie

    return best_movie


def _extract_movie_ids(movie):
    """Extract IMDb and TMDb IDs from movie data, return (imdb_id, tmdb_id, file_path)"""
    movie_imdb = None
    movie_tmdb = None
    file_path = movie.get('file', '')

    # IMDb ID extraction
    imdb_raw = movie.get("imdbnumber", "")
    imdb_digits = _strip_imdb_tt(imdb_raw)
    if imdb_digits and 6 <= len(imdb_digits) <= 8:
        movie_imdb = int(imdb_digits)
        log(__name__, f"Found Movie IMDb: {movie_imdb}")

    # TMDb ID from uniqueid
    uniqueids = movie.get("uniqueid", {})
    if isinstance(uniqueids, dict):
        tmdb_raw = uniqueids.get("tmdb", "")
        if tmdb_raw and str(tmdb_raw).isdigit():
            movie_tmdb = int(tmdb_raw)
            log(__name__, f"Found Movie TMDb: {movie_tmdb}")

    return movie_imdb, movie_tmdb, file_path

def _query_kodi_library_for_show(show_title, year=None):
    """Query Kodi library for TV show IDs"""
    if not show_title:
        return None, None, None

    try:
        query_params = {
            "properties": ["imdbnumber", "uniqueid", "title", "episodeguide"],
            "limits": {"end": 50}
        }
        result = _jsonrpc("VideoLibrary.GetTVShows", query_params, use_cache=False)

        if result and "tvshows" in result and result["tvshows"]:
            matching_shows = []
            for show in result["tvshows"]:
                show_title_lib = show.get('title', '').lower()
                search_title_lower = show_title.lower()
                if (search_title_lower in show_title_lib or
                    show_title_lib in search_title_lower):
                    matching_shows.append(show)

            if matching_shows:
                best_show = _select_best_show_match(matching_shows, show_title, year)
                if best_show:
                    return _extract_show_ids(best_show)

    except Exception as e:
        log(__name__, f"Failed to query library for show: {e}")

    return None, None, None

def _select_best_show_match(tvshows, search_title, search_year=None):
    """Select the best matching TV show from library results"""
    if not tvshows:
        return None

    if len(tvshows) == 1:
        return tvshows[0]

    best_score = 0
    best_show = None

    for show in tvshows:
        score = 0
        show_title = show.get('title', '')
        show_orig_title = show.get('originaltitle', '')
        show_year = show.get('year')

        # Title matching (0-100)
        if search_title:
            title_similarity = SequenceMatcher(None, search_title.lower(), show_title.lower()).ratio() * 100
            if show_orig_title:
                orig_title_similarity = SequenceMatcher(None, search_title.lower(), show_orig_title.lower()).ratio() * 100
                score += max(title_similarity, orig_title_similarity)
            else:
                score += title_similarity

            # Exact match bonus
            if search_title.lower() == show_title.lower() or search_title.lower() == show_orig_title.lower():
                score += 50

        # Year bonus (0-25)
        if search_year and show_year:
            year_diff = abs(int(search_year) - show_year)
            if year_diff == 0:
                score += 25
            elif year_diff <= 2:
                score += 10

        if score > best_score:
            best_score = score
            best_show = show

    return best_show

def _extract_show_ids(tvshow):
    """Extract IMDb and TMDb IDs from TV show data, return (imdb_id, tmdb_id, tvshow_id)"""
    parent_imdb = None
    parent_tmdb = None
    tvshow_id = tvshow.get('tvshowid')

    # IMDb ID
    imdb_raw = tvshow.get("imdbnumber", "")
    imdb_digits = _strip_imdb_tt(imdb_raw)
    if imdb_digits and 6 <= len(imdb_digits) <= 8:
        parent_imdb = int(imdb_digits)
        log(__name__, f"Found Parent IMDb: {parent_imdb}")

    # TMDb ID from uniqueid
    uniqueids = tvshow.get("uniqueid", {})
    if isinstance(uniqueids, dict):
        tmdb_raw = uniqueids.get("tmdb", "")
        if tmdb_raw and str(tmdb_raw).isdigit():
            parent_tmdb = int(tmdb_raw)
            log(__name__, f"Found Parent TMDb: {parent_tmdb}")

    # Alternative TMDb extraction from episodeguide
    if not parent_tmdb:
        episodeguide = tvshow.get("episodeguide", "")
        if episodeguide:
            try:
                import re
                tmdb_match = re.search(r'tmdb["\']?[:\s]*([0-9]+)', episodeguide, re.IGNORECASE)
                if tmdb_match:
                    parent_tmdb = int(tmdb_match.group(1))
                    log(__name__, f"Found Parent TMDb from episodeguide: {parent_tmdb}")
            except Exception:
                pass

    return parent_imdb, parent_tmdb, tvshow_id

def _call_guessit_api(filename):
    """Call OpenSubtitles guessit API to parse filename"""
    try:
        import urllib.request
        import urllib.parse
        import json
        
        # Get API key from addon settings
        api_key = __addon__.getSetting("APIKey")
        if not api_key:
            log(__name__, "No API key found for guessit call")
            return None
        
        # Prepare the request
        base_url = "https://api.opensubtitles.com/api/v1/utilities/guessit"
        params = {"filename": filename}
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        # Create request with headers
        req = urllib.request.Request(url)
        req.add_header("Api-Key", api_key)
        req.add_header("User-Agent", f"Kodi OpenSubtitles.com v{__addon__.getAddonInfo('version')}")
        req.add_header("Accept", "application/json")
        
        log(__name__, f"🔍 Calling guessit API for: {filename}")
        
        # Make the request
        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                log(__name__, f"✅ Guessit API response: {data}")
                return data
            else:
                log(__name__, f"❌ Guessit API error: HTTP {response.getcode()}")
                return None
                
    except Exception as e:
        log(__name__, f"❌ Failed to call guessit API: {e}")
        return None

def _jsonrpc(method, params=None, use_cache=True):
    """JSON-RPC call with caching and error handling"""
    # Check cache first for library queries
    if use_cache and method.startswith('VideoLibrary.'):
        cached_result = _get_from_cache(method, params)
        if cached_result is not None:
            return cached_result

    try:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params:
            payload["params"] = params

        resp = xbmc.executeJSONRPC(json.dumps(payload))
        data = json.loads(resp)

        # Check for JSON-RPC errors
        if "error" in data:
            error_info = data["error"]
            log(__name__, f"JSON-RPC error in {method}: {error_info.get('message', 'Unknown error')}")
            return None

        result = data.get("result")

        # Cache library query results
        if use_cache and method.startswith('VideoLibrary.') and result:
            _store_in_cache(method, params, result)

        return result

    except json.JSONDecodeError as e:
        log(__name__, f"JSON decode error in {method}: {e}")
        return None
    except Exception as e:
        log(__name__, f"JSON-RPC error in {method}: {e}")
        return None


def get_media_data():

    item = {"query": None,
            "year": xbmc.getInfoLabel("VideoPlayer.Year"),
            "season_number": str(xbmc.getInfoLabel("VideoPlayer.Season")),
            "episode_number": str(xbmc.getInfoLabel("VideoPlayer.Episode")),
            "tv_show_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")),
            "original_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            "parent_tmdb_id": None,
            "parent_imdb_id": None,
            "imdb_id": None,
            "tmdb_id": None}
    log(__name__, f"Initial media data from InfoLabels: {item}")
    
    # Check if we're dealing with a non-library file (all InfoLabels empty)
    if not any([item["tv_show_title"], item["original_title"], item["year"], 
                item["season_number"], item["episode_number"]]):
        log(__name__, "⚠️  All InfoLabels are empty - likely non-library file playback")
        
        try:
            playing_file = get_file_path()
            if playing_file:
                log(__name__, f"📁 Playing file path: {playing_file}")
                import os
                filename = os.path.basename(playing_file)
                log(__name__, f"📝 Filename to parse: {filename}")
                
                # STEP 1: Try basic filename parsing for TV shows
                show_title, season_num, episode_num = _extract_basic_tv_info(filename)
                if show_title and season_num and episode_num:
                    log(__name__, f"🎬 Basic parsing found TV show: '{show_title}' S{season_num}E{episode_num}")
                    
                    # STEP 2: Try to find this show in Kodi library
                    parent_imdb, parent_tmdb, tvshow_id = _query_kodi_library_for_show(show_title)
                    if parent_imdb or parent_tmdb:
                        # Success! We have parent IDs from library
                        item["tv_show_title"] = show_title
                        item["season_number"] = season_num
                        item["episode_number"] = episode_num
                        if parent_imdb:
                            item["parent_imdb_id"] = parent_imdb
                        if parent_tmdb:
                            item["parent_tmdb_id"] = parent_tmdb
                        if tvshow_id:
                            item["tvshowid"] = str(tvshow_id)
                        log(__name__, f"✅ Found in library with parent IDs - IMDb: {parent_imdb}, TMDb: {parent_tmdb}, DBID: {tvshow_id}")
                    else:
                        # Library search failed, set basic TV info for title search
                        item["tv_show_title"] = show_title
                        item["season_number"] = season_num
                        item["episode_number"] = episode_num
                        log(__name__, f"📚 Not in library, will search by title: '{show_title}' S{season_num}E{episode_num}")
                else:
                    # STEP 3: Fallback to guessit API for complex parsing
                    log(__name__, "🔍 Basic parsing failed, trying guessit API...")
                    guessed_data = _call_guessit_api(filename)
                    if guessed_data:
                        if guessed_data.get("type") == "episode":
                            # TV show episode
                            item["tv_show_title"] = guessed_data.get("title", "")
                            item["season_number"] = str(guessed_data.get("season", ""))
                            item["episode_number"] = str(guessed_data.get("episode", ""))
                            item["year"] = guessed_data.get("year")
                            log(__name__, f"🎬 Guessit parsed TV episode: {item['tv_show_title']} S{item['season_number']}E{item['episode_number']}")
                        elif guessed_data.get("type") == "movie":
                            # Movie
                            movie_title = guessed_data.get("title", "")
                            movie_year = guessed_data.get("year")
                            item["original_title"] = movie_title
                            item["query"] = movie_title  # Set query to clean title
                            item["year"] = str(movie_year) if movie_year else ""
                            log(__name__, f"🎬 Guessit parsed movie: {movie_title} ({movie_year})")
                            log(__name__, f"🔍 Set query to: '{item['query']}'")
                            
                            # Try to find this movie in Kodi library
                            movie_imdb, movie_tmdb, file_path = _query_kodi_library_for_movie(movie_title, movie_year)
                            if movie_imdb or movie_tmdb:
                                if movie_imdb:
                                    item["imdb_id"] = movie_imdb
                                if movie_tmdb:
                                    item["tmdb_id"] = movie_tmdb
                                if file_path:
                                    item["file_path"] = file_path
                                log(__name__, f"✅ Found movie in library with IDs - IMDb: {movie_imdb}, TMDb: {movie_tmdb}")
                            else:
                                log(__name__, f"📚 Movie not in library, will search by title: '{movie_title}' ({movie_year})")
                        else:
                            log(__name__, f"🎬 Guessit detected type: {guessed_data.get('type')}")
                    else:
                        log(__name__, "❌ All parsing methods failed, will use filename as query")
        except Exception as e:
            log(__name__, f"Failed to parse filename: {e}")
    
    # ---------------- TV SHOW (Episode) ----------------
    if item["tv_show_title"]:
        item["tvshowid"] = xbmc.getInfoLabel("VideoPlayer.TvShowDBID")
        item["query"] = item["tv_show_title"]
        item["year"] = None  # Safer for OS search

        # 1) Try to get TRUE parent show IDs first (these are more reliable)
        try:
            # True parent show IMDb ID from TvShow properties
            parent_imdb_raw = (xbmc.getInfoLabel("ListItem.Property(TvShow.IMDBNumber)")
                               or xbmc.getInfoLabel("VideoPlayer.TvShow.IMDBNumber"))
            imdb_digits = _strip_imdb_tt(parent_imdb_raw)
            if imdb_digits and 6 <= len(imdb_digits) <= 8:
                item["parent_imdb_id"] = int(imdb_digits)
                log(__name__, f"TRUE Parent Show IMDb ID: {item['parent_imdb_id']}")

            # True parent show TMDb ID (less common but check if available)
            parent_tmdb_raw = xbmc.getInfoLabel("VideoPlayer.TvShow.UniqueID(tmdb)")
            if parent_tmdb_raw and parent_tmdb_raw.isdigit():
                item["parent_tmdb_id"] = int(parent_tmdb_raw)
                log(__name__, f"TRUE Parent Show TMDb ID: {item['parent_tmdb_id']}")
        except Exception as e:
            log(__name__, f"Failed to read true parent IDs from InfoLabels: {e}")

        # 2) If no true parent IDs found, check if we have episode-specific IDs
        if not item.get("parent_imdb_id") and not item.get("parent_tmdb_id"):
            try:
                # These might be episode IDs, not parent IDs
                possible_episode_imdb = (xbmc.getInfoLabel("VideoPlayer.UniqueID(imdb)")
                                         or xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
                                         or xbmc.getInfoLabel("ListItem.IMDBNumber"))
                imdb_digits = _strip_imdb_tt(possible_episode_imdb)
                if imdb_digits and 6 <= len(imdb_digits) <= 8:
                    item["imdb_id"] = int(imdb_digits)
                    log(__name__, f"Episode-specific IMDb ID (not parent): {item['imdb_id']}")

                possible_episode_tmdb = xbmc.getInfoLabel("VideoPlayer.UniqueID(tmdb)")
                if possible_episode_tmdb and possible_episode_tmdb.isdigit():
                    item["tmdb_id"] = int(possible_episode_tmdb)
                    log(__name__, f"Episode-specific TMDb ID (not parent): {item['tmdb_id']}")
            except Exception as e:
                log(__name__, f"Failed to read episode IDs from InfoLabels: {e}")

        # 3) If still missing, fall back to library JSON-RPC (when the show is in the library)
        if len(item["tvshowid"]) != 0 and (not item["parent_tmdb_id"] or not item["parent_imdb_id"]):
            try:
                TVShowDetails = xbmc.executeJSONRPC(
                    '{ "jsonrpc": "2.0", "id":"1", "method": "VideoLibrary.GetTVShowDetails", '
                    '"params":{"tvshowid":' + item["tvshowid"] + ', "properties": ["episodeguide", "imdbnumber", "uniqueid"]} }'
                )
                TVShowDetails_dict = json.loads(TVShowDetails)
                if "result" in TVShowDetails_dict and "tvshowdetails" in TVShowDetails_dict["result"]:
                    tvshow_details = TVShowDetails_dict["result"]["tvshowdetails"]

                    # parent IMDb
                    if not item["parent_imdb_id"]:
                        imdb_raw = str(tvshow_details.get("imdbnumber") or "")
                        imdb_digits = _strip_imdb_tt(imdb_raw)
                        if imdb_digits and 6 <= len(imdb_digits) <= 8:
                            item["parent_imdb_id"] = int(imdb_digits)
                            log(__name__, f"Parent IMDb via JSON-RPC: {item['parent_imdb_id']}")

                    # parent TMDb (first try uniqueid, then episodeguide fallback)
                    if not item["parent_tmdb_id"]:
                        # Method 1: Try uniqueid field first (more reliable)
                        uniqueids = tvshow_details.get("uniqueid", {})
                        if isinstance(uniqueids, dict):
                            tmdb_raw = uniqueids.get("tmdb", "")
                            if tmdb_raw and str(tmdb_raw).isdigit():
                                item["parent_tmdb_id"] = int(tmdb_raw)
                                log(__name__, f"Parent TMDb via JSON-RPC (uniqueid): {item['parent_tmdb_id']}")

                        # Method 2: Fallback to episodeguide if uniqueid didn't work
                        if not item["parent_tmdb_id"]:
                            episodeguideXML = tvshow_details.get("episodeguide")
                            if episodeguideXML:
                                try:
                                    episodeguide = ET.fromstring(episodeguideXML)
                                    if episodeguide.text:
                                        guide_json = json.loads(episodeguide.text)
                                        tmdb = guide_json.get("tmdb")
                                        if tmdb and str(tmdb).isdigit():
                                            item["parent_tmdb_id"] = int(tmdb)
                                            log(__name__, f"Parent TMDb via JSON-RPC (episodeguide): {item['parent_tmdb_id']}")
                                except (ET.ParseError, json.JSONDecodeError, ValueError):
                                    pass  # Silent fail for malformed XML/JSON
            except (json.JSONDecodeError, ET.ParseError, ValueError, KeyError) as e:
                log(__name__, f"Failed to extract TV show IDs via JSON-RPC: {e}")

        # 4) Try to get specific episode IDs from dedicated episode fields (if available)
        try:
            ep_tmdb = xbmc.getInfoLabel("VideoPlayer.UniqueID(tmdbepisode)")
            if ep_tmdb and ep_tmdb.isdigit():
                item["tmdb_id"] = int(ep_tmdb)
                log(__name__, f"Dedicated Episode TMDb ID: {item['tmdb_id']}")
            ep_imdb = xbmc.getInfoLabel("VideoPlayer.UniqueID(imdbepisode)")
            ep_imdb_digits = _strip_imdb_tt(ep_imdb)
            if ep_imdb_digits and ep_imdb_digits.isdigit():
                item["imdb_id"] = int(ep_imdb_digits)
                log(__name__, f"Dedicated Episode IMDb ID: {item['imdb_id']}")
        except Exception as e:
            log(__name__, f"Failed to read dedicated episode IDs from InfoLabels: {e}")

    # ---------------- MOVIE ----------------
    elif item["original_title"]:
        item["query"] = item["original_title"]
        movie_dbid = xbmc.getInfoLabel("VideoPlayer.DBID")
        
        # First try to get IDs from InfoLabels (most reliable for library content)
        try:
            imdb_raw = (xbmc.getInfoLabel("VideoPlayer.UniqueID(imdb)")
                        or xbmc.getInfoLabel("VideoPlayer.IMDBNumber"))
            imdb_digits = _strip_imdb_tt(imdb_raw)
            if imdb_digits and 6 <= len(imdb_digits) <= 8:
                item["imdb_id"] = int(imdb_digits)
                log(__name__, f"Found IMDB ID for movie from InfoLabel: {item['imdb_id']}")

            tmdb_raw = xbmc.getInfoLabel("VideoPlayer.UniqueID(tmdb)")
            if tmdb_raw and str(tmdb_raw).isdigit():
                tmdb_id = int(tmdb_raw)
                if tmdb_id > 0:
                    item["tmdb_id"] = tmdb_id
                    log(__name__, f"Found TMDB ID for movie from InfoLabel: {item['tmdb_id']}")
        except (ValueError, KeyError) as e:
            log(__name__, f"Failed to extract movie IDs from InfoLabels: {e}")
        
        # If no IDs found and we have a database ID, query the library directly
        if not item.get("imdb_id") and not item.get("tmdb_id") and movie_dbid and movie_dbid.isdigit():
            log(__name__, f"🔍 No IDs from InfoLabels, trying library query with DBID: {movie_dbid}")
            movie_imdb, movie_tmdb, file_path = _query_kodi_library_for_movie(None, None, movie_dbid)
            if movie_imdb:
                item["imdb_id"] = movie_imdb
                log(__name__, f"Found IMDB ID from library query: {movie_imdb}")
            if movie_tmdb:
                item["tmdb_id"] = movie_tmdb
                log(__name__, f"Found TMDB ID from library query: {movie_tmdb}")
        
        # Last resort: search library by title and year
        if not item.get("imdb_id") and not item.get("tmdb_id"):
            log(__name__, f"🔍 No IDs found, searching library by title: '{item['original_title']}' ({item.get('year')})")
            movie_imdb, movie_tmdb, file_path = _query_kodi_library_for_movie(item["original_title"], item.get("year"))
            if movie_imdb:
                item["imdb_id"] = movie_imdb
                log(__name__, f"Found IMDB ID from title search: {movie_imdb}")
            if movie_tmdb:
                item["tmdb_id"] = movie_tmdb
                log(__name__, f"Found TMDB ID from title search: {movie_tmdb}")

    # ---------- Cleanup & precedence ----------
    for k in ("parent_tmdb_id", "parent_imdb_id", "tmdb_id", "imdb_id"):
        v = item.get(k)
        if v in (0, "0", "", None):
            item[k] = None

    # Prefer parent IMDb over parent TMDb for TV
    if item.get("parent_tmdb_id") and item.get("parent_imdb_id"):
        log(__name__, f"Both parent TMDB and IMDB IDs found, preferring IMDB ID: {item['parent_imdb_id']}")
        item["parent_tmdb_id"] = None

    # Prefer IMDb over TMDb for item-level IDs
    if item.get("tmdb_id") and item.get("imdb_id"):
        log(__name__, f"Both TMDB and IMDB IDs found for item, preferring IMDB ID: {item['imdb_id']}")
        item["tmdb_id"] = None

    # ---------- Final ID Strategy Selection (TV Episodes Only) ----------
    # Ensure we only use ONE strategy: parent IDs + season/episode OR episode-specific IDs
    if item.get("tv_show_title"):
        if item.get("parent_imdb_id"):
            # Strategy: Use parent IMDb ID with season/episode
            item["parent_tmdb_id"] = None  # Clear conflicting parent ID
            item["imdb_id"] = None         # Clear episode-specific IDs
            item["tmdb_id"] = None
            log(__name__, f"✅ Final Strategy: parent_imdb_id={item['parent_imdb_id']} + season/episode")
        elif item.get("parent_tmdb_id"):
            # Strategy: Use parent TMDb ID with season/episode
            item["parent_imdb_id"] = None  # Clear conflicting parent ID
            item["imdb_id"] = None         # Clear episode-specific IDs
            item["tmdb_id"] = None
            log(__name__, f"✅ Final Strategy: parent_tmdb_id={item['parent_tmdb_id']} + season/episode")
        elif item.get("imdb_id"):
            # Strategy: Use episode-specific IMDb ID only
            item["parent_imdb_id"] = None  # Clear parent IDs
            item["parent_tmdb_id"] = None
            item["tmdb_id"] = None         # Clear conflicting episode ID
            log(__name__, f"✅ Final Strategy: episode imdb_id={item['imdb_id']} (no season/episode)")
        elif item.get("tmdb_id"):
            # Strategy: Use episode-specific TMDb ID only
            item["parent_imdb_id"] = None  # Clear parent IDs
            item["parent_tmdb_id"] = None
            item["imdb_id"] = None         # Clear conflicting episode ID
            log(__name__, f"✅ Final Strategy: episode tmdb_id={item['tmdb_id']} (no season/episode)")

    # ---------- API Query Strategy Logging ----------
    # For TV episodes: Prioritize parent show IDs + season/episode, fallback to specific episode IDs
    if item.get("tv_show_title"):
        if item.get("parent_imdb_id"):
            log(__name__, f"🎯 API Strategy: parent_imdb_id={item['parent_imdb_id']}, season={item['season_number']}, episode={item['episode_number']}")
        elif item.get("parent_tmdb_id"):
            log(__name__, f"🎯 API Strategy: parent_tmdb_id={item['parent_tmdb_id']}, season={item['season_number']}, episode={item['episode_number']}")
        elif item.get("imdb_id"):
            log(__name__, f"🎯 API Strategy: imdb_id={item['imdb_id']} (episode-specific, no season/episode needed)")
        elif item.get("tmdb_id"):
            log(__name__, f"🎯 API Strategy: tmdb_id={item['tmdb_id']} (episode-specific, no season/episode needed)")
        else:
            log(__name__, f"🎯 API Strategy: title search only '{item['query']}' (no IDs available)")
    else:
        # For movies: Use specific movie IDs
        if item.get("imdb_id"):
            log(__name__, f"🎯 API Strategy: imdb_id={item['imdb_id']} (movie)")
        elif item.get("tmdb_id"):
            log(__name__, f"🎯 API Strategy: tmdb_id={item['tmdb_id']} (movie)")
        else:
            log(__name__, f"🎯 API Strategy: title search only '{item['query']}' (movie, no IDs available)")

    if not item.get("query"):
        fallback_title = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))
        if fallback_title:
            item["query"] = fallback_title
        else:
            # Last resort: use filename
            try:
                playing_file = get_file_path()
                if playing_file:
                    import os
                    filename = os.path.basename(playing_file)
                    item["query"] = filename
            except:
                item["query"] = "Unknown"

    # Specials handling
    if isinstance(item.get("episode_number"), str) and item["episode_number"] and item["episode_number"].lower().find("s") > -1:
        item["season_number"] = "0"
        item["episode_number"] = item["episode_number"][-1:]

    # Remove internal-only key
    if "tvshowid" in item:
        del item["tvshowid"]

    log(__name__, f"Media data result: {item.get('query')} - IMDb:{item.get('imdb_id') or item.get('parent_imdb_id')} TMDb:{item.get('tmdb_id') or item.get('parent_tmdb_id')}")

    return item


def get_language_data(params):
    search_languages = unquote(params.get("languages")).split(",")
    search_languages_str = ""
    preferred_language = params.get("preferredlanguage")

    if preferred_language and preferred_language not in search_languages and preferred_language != "Unknown" and preferred_language != "Undetermined":
        search_languages.append(preferred_language)
        search_languages_str = search_languages_str + "," + preferred_language

    for language in search_languages:
        lang = convert_language(language)
        if lang:
            log(__name__, f"Language  found: '{lang}' search_languages_str:'{search_languages_str}")
            if search_languages_str == "":
                search_languages_str = lang
            else:
                search_languages_str = search_languages_str + "," + lang
        else:
            log(__name__, f"Language code not found: '{language}'")

    item = {
        "hearing_impaired": __addon__.getSetting("hearing_impaired"),
        "foreign_parts_only": __addon__.getSetting("foreign_parts_only"),
        "machine_translated": __addon__.getSetting("machine_translated"),
        "ai_translated": __addon__.getSetting("ai_translated"),
        "languages": search_languages_str
    }

    return item


def convert_language(language, reverse=False):
    language_list = {
        "English": "en",
        "Portuguese (Brazil)": "pt-br",
        "Portuguese": "pt-pt",
        "Chinese": "zh-cn",
        "Chinese (simplified)": "zh-cn",
        "Chinese (traditional)": "zh-tw"}

    reverse_language_list = {v: k for k, v in list(language_list.items())}

    if reverse:
        iterated_list = reverse_language_list
        xbmc_param = xbmc.ENGLISH_NAME
    else:
        iterated_list = language_list
        xbmc_param = xbmc.ISO_639_1

    if language in iterated_list:
        return iterated_list[language]
    else:
        return xbmc.convertLanguage(language, xbmc_param)


def get_flag(language_code):
    language_list = {
        "pt-pt": "pt",
        "pt-br": "pb",
        "zh-cn": "zh",
        "zh-tw": "-"
    }
    return language_list.get(language_code.lower(), language_code)


def clean_feature_release_name(title, release, movie_name=""):
    if not title:
        if not movie_name:
            if not release:
                raise ValueError("None of title, release, movie_name contains a string")
            return release
        else:
            if not movie_name[0:4].isnumeric():
                name = movie_name
            else:
                name = movie_name[7:]
    else:
        name = title

    match_ratio = SequenceMatcher(None, name, release).ratio()
    log(__name__, f"name: {name}, release: {release}, match_ratio: {match_ratio}")
    if name in release:
        return release
    elif match_ratio > 0.3:
        return release
    else:
        return f"{name} {release}"

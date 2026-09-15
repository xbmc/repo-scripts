from urllib.parse import unquote, urlsplit
from difflib import SequenceMatcher
import json
import re
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon

from resources.lib.utilities import log, normalize_string, get_user_agent, redact_path, safe_media_filename, loggable_media

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

__addon__ = xbmcaddon.Addon("service.subtitles.opensubtitles-com")
__scriptid__ = __addon__.getAddonInfo("id")


def get_file_path():
    return xbmc.Player().getPlayingFile()


def _apply_player_tvshowid(item):
    """VideoPlayer.TvShowDBID, but only when it carries a value.

    The label is empty for non-library playback and must not clobber a
    tvshowid the filename->library lookup already found - losing it skips
    the original-title / parent-id JSON-RPC refinement. The key always ends
    up present: downstream does len(item["tvshowid"]).
    """
    player_tvshowid = xbmc.getInfoLabel("VideoPlayer.TvShowDBID")
    if player_tvshowid:
        item["tvshowid"] = player_tvshowid
    else:
        item.setdefault("tvshowid", "")


# ---------- Small helpers ----------

def _valid_coordinate(value, minimum=0):
    """Season/episode number as a digit string, or "" when implausible.

    Parsed metadata (guessit, filenames) is untrusted: a non-positive or
    non-numeric coordinate sent to the API fails the request and stops the
    fallback chain, so drop it here instead."""
    s = str(value).strip() if value is not None else ""
    return s if s.isdigit() and int(s) >= minimum else ""


def _valid_year(value):
    """Feature year as a string, or "" when outside the plausible range."""
    import datetime
    s = str(value).strip() if value is not None else ""
    return s if s.isdigit() and 1927 <= int(s) <= datetime.date.today().year + 1 else ""


def _strip_imdb_tt(value, require_tt=False):
    """Return the digits of an IMDb id, or None.

    Set require_tt when the value comes from Kodi's `imdbnumber` field. That field holds
    whatever the scraper treats as the item's primary id, which for a TVDB- or TMDb-scraped
    show is *not* an IMDb id - and once you look only at the digits, a foreign id is
    indistinguishable from a real one. Sending one as imdb_id/parent_imdb_id matches nothing:
    a user log had Succession's library id 338186 go out as parent_imdb_id (0 results) while
    the correct episode id was discarded. So only accept an explicit "tt" prefix there.
    """
    if not value:
        return None
    s = str(value).strip()
    if s.startswith("tt"):
        s = s[2:]
    elif require_tt:
        return None
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
                    movie_title_lib = str(movie.get('title') or '').lower()
                    search_title_lower = movie_title.lower()

                    if (search_title_lower in movie_title_lib or
                        movie_title_lib in search_title_lower):
                        matching_movies.append(movie)

                if matching_movies:
                    best_movie = _select_best_movie_match(matching_movies, movie_title, year)
                    if best_movie:
                        return _extract_movie_ids(best_movie)

    except Exception as e:
        log(__name__, f"Failed to query library for movie: {type(e).__name__}")

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

    # IMDb ID extraction: prefer the explicitly typed uniqueid; "imdbnumber" is only the
    # scraper's primary id and may hold a TVDB/TMDb one (see _strip_imdb_tt)
    uniqueids = movie.get("uniqueid") or {}
    imdb_digits = _strip_imdb_tt(uniqueids.get("imdb") if isinstance(uniqueids, dict) else None)
    if not imdb_digits:
        imdb_digits = _strip_imdb_tt(movie.get("imdbnumber"), require_tt=True)
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
                show_title_lib = str(show.get('title') or '').lower()
                search_title_lower = show_title.lower()
                if (search_title_lower in show_title_lib or
                    show_title_lib in search_title_lower):
                    matching_shows.append(show)

            if matching_shows:
                best_show = _select_best_show_match(matching_shows, show_title, year)
                if best_show:
                    return _extract_show_ids(best_show)

    except Exception as e:
        log(__name__, f"Failed to query library for show: {type(e).__name__}")

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

    # IMDb ID: prefer the explicitly typed uniqueid; "imdbnumber" is only the scraper's
    # primary id and may hold a TVDB/TMDb one (see _strip_imdb_tt)
    uniqueids = tvshow.get("uniqueid") or {}
    imdb_digits = _strip_imdb_tt(uniqueids.get("imdb") if isinstance(uniqueids, dict) else None)
    if not imdb_digits:
        imdb_digits = _strip_imdb_tt(tvshow.get("imdbnumber"), require_tt=True)
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
    """Call OpenSubtitles guessit API to parse filename with caching"""
    if not filename:
        return None

    try:
        import hashlib
        import json
        import urllib.parse
        import urllib.request
        from resources.lib.cache import Cache

        clean_filename = filename.strip()
        cache_key = f"guessit_{hashlib.sha256(clean_filename.encode('utf-8')).hexdigest()}"
        cache = Cache(key_prefix="os_com")

        cached = cache.get(cache_key)
        if cached is not None:
            # key prefix only: the filename is playback-derived and belongs
            # in no log line, even after safe_media_filename stripped it
            log(__name__, f"📋 Cache hit for guessit: {cache_key[:16]}")
            return cached or None

        # Get API key from addon settings
        api_key = __addon__.getSetting("APIKey")
        if not api_key:
            log(__name__, "No API key found for guessit call")
            return None

        # Prepare the request
        base_url = "https://api.opensubtitles.com/api/v1/utilities/guessit"
        params = {"filename": clean_filename}
        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        # Create request with headers
        req = urllib.request.Request(url)
        req.add_header("Api-Key", api_key)
        req.add_header("User-Agent", get_user_agent())
        req.add_header("Accept", "application/json")

        log(__name__, f"🔍 Calling guessit API ({cache_key[:16]})")

        # Make the request with a safe timeout
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode("utf-8"))
                # cache only object shapes: a cached list/scalar would come
                # back on every later call and crash .get() consumers
                if not isinstance(data, dict):
                    data = None
                cache.set(cache_key, data or {}, expires=60 * 60 * 24 * 30)
                if isinstance(data, dict):
                    # structural only - the parsed title is viewing history
                    log(__name__, "✅ Guessit parsed (cached): "
                                  f"title={'set' if data.get('title') else 'empty'} "
                                  f"year={data.get('year')} type={data.get('type')}")
                else:
                    log(__name__, "✅ Guessit response cached (non-object payload)")
                return data
            else:
                log(__name__, f"❌ Guessit API error: HTTP {response.getcode()}")
                return None

    except Exception as e:
        # class name only: urllib errors repeat the full request URL, and the
        # URL embeds the (playback-derived) filename
        log(__name__, f"❌ Failed to call guessit API: {type(e).__name__}")
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
        log(__name__, f"JSON decode error in {method}: {type(e).__name__}")
        return None
    except Exception as e:
        log(__name__, f"JSON-RPC error in {method}: {type(e).__name__}")
        return None


def get_media_data():

    # InfoLabels are external input: coordinates and year validated at intake,
    # so a malformed value can never fail the request and stop the fallbacks.
    # A bare "sN" episode label legitimately means special N of season 0 and
    # must convert BEFORE validation would drop it as non-numeric.
    raw_episode = str(xbmc.getInfoLabel("VideoPlayer.Episode") or "").strip()
    special = re.fullmatch(r"[sS](\d+)", raw_episode)
    season_label = "0" if special else xbmc.getInfoLabel("VideoPlayer.Season")
    episode_label = special.group(1) if special else raw_episode
    item = {"query": None,
            "year": _valid_year(xbmc.getInfoLabel("VideoPlayer.Year")),
            "season_number": _valid_coordinate(season_label, minimum=0),
            "episode_number": _valid_coordinate(episode_label, minimum=1),
            "tv_show_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")),
            "original_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            "parent_tmdb_id": None,
            "parent_imdb_id": None,
            "imdb_id": None,
            "tmdb_id": None}
    log(__name__, "Initial media data from InfoLabels: %s" % loggable_media(item))
    
    # Check if we're dealing with a non-library file (all InfoLabels empty)
    if not any([item["tv_show_title"], item["original_title"], item["year"], 
                item["season_number"], item["episode_number"]]):
        log(__name__, "⚠️  All InfoLabels are empty - likely non-library file playback")
        
        try:
            playing_file = get_file_path()
            if playing_file:
                # the path and filename are the user's viewing history -
                # neither belongs in a log users share publicly
                log(__name__, "📁 Playing file detected, deriving search data")
                filename = safe_media_filename(playing_file)
                
                # STEP 1: Try basic filename parsing for TV shows
                show_title, season_num, episode_num = _extract_basic_tv_info(filename)
                if show_title and season_num and episode_num:
                    log(__name__, f"🎬 Basic parsing found a TV show (S{season_num}E{episode_num})")
                    
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
                        log(__name__, f"📚 Not in library, will search by title (S{season_num}E{episode_num})")
                else:
                    # STEP 3: Fallback to guessit API for complex parsing
                    log(__name__, "🔍 Basic parsing failed, trying guessit API...")
                    guessed_data = _call_guessit_api(filename)
                    if guessed_data:
                        # guessit output is parsed from an arbitrary filename -
                        # validate coordinates here so an out-of-range year or
                        # nonsense episode can never turn into a failing API
                        # request that stops the whole fallback chain
                        if guessed_data.get("type") == "episode":
                            item["tv_show_title"] = guessed_data.get("title", "")
                            item["season_number"] = _valid_coordinate(guessed_data.get("season"), minimum=0)
                            item["episode_number"] = _valid_coordinate(guessed_data.get("episode"), minimum=1)
                            item["year"] = _valid_year(guessed_data.get("year"))
                            log(__name__, f"🎬 Guessit parsed TV episode (S{item['season_number']}E{item['episode_number']})")
                        elif guessed_data.get("type") == "movie":
                            # Movie
                            movie_title = guessed_data.get("title", "")
                            movie_year = _valid_year(guessed_data.get("year"))
                            item["original_title"] = movie_title
                            item["query"] = movie_title  # Set query to clean title
                            item["year"] = movie_year
                            log(__name__, f"🎬 Guessit parsed a movie ({movie_year})")
                            log(__name__, "🔍 Query set from parsed title")
                            
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
                                log(__name__, f"📚 Movie not in library, will search by title ({movie_year})")
                        else:
                            log(__name__, f"🎬 Guessit detected type: {guessed_data.get('type')}")
                    else:
                        log(__name__, "❌ All parsing methods failed, will use filename as query")
        except Exception as e:
            log(__name__, f"Failed to parse filename: {type(e).__name__}")
    
    # ---------------- TV SHOW (Episode) ----------------
    if item["tv_show_title"]:
        _apply_player_tvshowid(item)
        item["query"] = item["tv_show_title"]
        item["year"] = None  # Safer for OS search

        # 1) Try to get TRUE parent show IDs first (these are more reliable)
        try:
            # True parent show IMDb ID from TvShow properties. Neither of these is a core
            # Kodi InfoLabel, so both are usually empty and step 3 below (JSON-RPC on
            # VideoPlayer.TvShowDBID) is what actually resolves the parent ID; they are kept
            # because a skin or video add-on may set the ListItem property itself.
            # Do NOT "fix" this to VideoPlayer.IMDBNumber (suggested in issue #40): during
            # episode playback that label returns the *episode's* id, so it would be filed
            # as a parent id and then searched together with season/episode - which matches
            # nothing. It is already read as an episode id in step 2 below.
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
            log(__name__, f"Failed to read true parent IDs from InfoLabels: {type(e).__name__}")

        # 2) No true parent IDs, so fall back to whatever id the player exposes.
        #    These labels describe "the thing being played", and video add-ons disagree about
        #    what they put there: Seren reports the *episode's* IMDb id, Umbrella and POV
        #    report the *show's* (peno64's logs, issue #40). Nothing local tells them apart,
        #    so record the id but flag its role as unknown - the search plan at the end of
        #    this function tries both readings instead of guessing.
        if not item.get("parent_imdb_id") and not item.get("parent_tmdb_id"):
            try:
                possible_episode_imdb = (xbmc.getInfoLabel("VideoPlayer.UniqueID(imdb)")
                                         or xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
                                         or xbmc.getInfoLabel("ListItem.IMDBNumber"))
                imdb_digits = _strip_imdb_tt(possible_episode_imdb)
                if imdb_digits and 6 <= len(imdb_digits) <= 8:
                    item["imdb_id"] = int(imdb_digits)
                    item["_player_id_role_unknown"] = True
                    log(__name__, f"Player IMDb ID (show or episode, role unknown): {item['imdb_id']}")

                possible_episode_tmdb = xbmc.getInfoLabel("VideoPlayer.UniqueID(tmdb)")
                if possible_episode_tmdb and possible_episode_tmdb.isdigit():
                    item["tmdb_id"] = int(possible_episode_tmdb)
                    item["_player_id_role_unknown"] = True
                    log(__name__, f"Player TMDb ID (show or episode, role unknown): {item['tmdb_id']}")
            except Exception as e:
                log(__name__, f"Failed to read episode IDs from InfoLabels: {type(e).__name__}")

        # 3) Query the library (when the show is in it) for the true parent IDs and the
        #    show's ORIGINAL title. Runs whenever we have a tvshowid: even when parent IDs
        #    are already known we still want originaltitle so localized libraries
        #    (e.g. Polish "Żywe trupy" -> "The Walking Dead") match on OS.com.
        #    NB: this is the *show's* originaltitle from the library, unlike
        #    VideoPlayer.OriginalTitle, which during episode playback returns the
        #    *episode's* original title (usually empty). Thanks to @notoco (PR #38)
        #    for reporting the localized-title search failure.
        if len(item["tvshowid"]) != 0:
            try:
                TVShowDetails = xbmc.executeJSONRPC(
                    '{ "jsonrpc": "2.0", "id":"1", "method": "VideoLibrary.GetTVShowDetails", '
                    '"params":{"tvshowid":' + item["tvshowid"] + ', "properties": ["originaltitle", "episodeguide", "imdbnumber", "uniqueid"]} }'
                )
                TVShowDetails_dict = json.loads(TVShowDetails)
                if "result" in TVShowDetails_dict and "tvshowdetails" in TVShowDetails_dict["result"]:
                    tvshow_details = TVShowDetails_dict["result"]["tvshowdetails"]

                    # Prefer the show's original title for the search query (localized-library fix)
                    original_show_title = normalize_string(tvshow_details.get("originaltitle") or "")
                    if original_show_title:
                        item["query"] = original_show_title
                        log(__name__, "Using show original title for query")

                    uniqueids = tvshow_details.get("uniqueid", {})
                    if not isinstance(uniqueids, dict):
                        uniqueids = {}

                    # parent IMDb: uniqueid["imdb"] is explicitly typed, so trust it first.
                    # "imdbnumber" is only the scraper's primary id and may be a TVDB/TMDb
                    # one, hence require_tt (see _strip_imdb_tt).
                    if not item["parent_imdb_id"]:
                        imdb_digits = _strip_imdb_tt(uniqueids.get("imdb"))
                        source = "uniqueid"
                        if not imdb_digits:
                            imdb_digits = _strip_imdb_tt(tvshow_details.get("imdbnumber"), require_tt=True)
                            source = "imdbnumber"
                        if imdb_digits and 6 <= len(imdb_digits) <= 8:
                            item["parent_imdb_id"] = int(imdb_digits)
                            log(__name__, f"Parent IMDb via JSON-RPC ({source}): {item['parent_imdb_id']}")
                        elif tvshow_details.get("imdbnumber"):
                            log(__name__, "Library imdbnumber is not an IMDb id (no 'tt' prefix), ignoring it")

                    # parent TMDb (first try uniqueid, then episodeguide fallback)
                    if not item["parent_tmdb_id"]:
                        # Method 1: Try uniqueid field first (more reliable)
                        tmdb_raw = uniqueids.get("tmdb", "")
                        if tmdb_raw and str(tmdb_raw).isdigit():
                            item["parent_tmdb_id"] = int(tmdb_raw)
                            log(__name__, f"Parent TMDb via JSON-RPC (uniqueid): {item['parent_tmdb_id']}")

                        # Method 2: Fallback to episodeguide if uniqueid didn't work
                        if not item["parent_tmdb_id"]:
                            episodeguideXML = tvshow_details.get("episodeguide")
                            # scraper-written field: bound the size and reject
                            # entity declarations before parsing, same as the
                            # remote-manifest parser (ET expands entities)
                            if episodeguideXML and (
                                    len(str(episodeguideXML)) > 64 * 1024
                                    or re.search(r"<!\s*(DOCTYPE|ENTITY)",
                                                 str(episodeguideXML), re.IGNORECASE)):
                                log(__name__, "Ignoring oversized or entity-bearing episodeguide")
                                episodeguideXML = None
                            if episodeguideXML:
                                try:
                                    episodeguide = ET.fromstring(episodeguideXML)
                                    if episodeguide.text:
                                        guide_json = json.loads(episodeguide.text)
                                        # valid JSON is not necessarily an object -
                                        # a bare string/number must not abort the search
                                        tmdb = guide_json.get("tmdb") if isinstance(guide_json, dict) else None
                                        if tmdb and str(tmdb).isdigit():
                                            item["parent_tmdb_id"] = int(tmdb)
                                            log(__name__, f"Parent TMDb via JSON-RPC (episodeguide): {item['parent_tmdb_id']}")
                                except (ET.ParseError, json.JSONDecodeError, ValueError, TypeError, AttributeError):
                                    pass  # Silent fail for malformed XML/JSON of any shape
            except (json.JSONDecodeError, ET.ParseError, ValueError, KeyError, TypeError, AttributeError) as e:
                log(__name__, f"Failed to extract TV show IDs via JSON-RPC: {type(e).__name__}")

        # 4) Try to get specific episode IDs from dedicated episode fields (if available).
        #    Unlike step 2 these name the episode explicitly, so the id's role is not in doubt.
        try:
            ep_tmdb = xbmc.getInfoLabel("VideoPlayer.UniqueID(tmdbepisode)")
            if ep_tmdb and ep_tmdb.isdigit():
                item["tmdb_id"] = int(ep_tmdb)
                item["_player_id_role_unknown"] = False
                log(__name__, f"Dedicated Episode TMDb ID: {item['tmdb_id']}")
            ep_imdb = xbmc.getInfoLabel("VideoPlayer.UniqueID(imdbepisode)")
            ep_imdb_digits = _strip_imdb_tt(ep_imdb)
            if ep_imdb_digits and ep_imdb_digits.isdigit():
                item["imdb_id"] = int(ep_imdb_digits)
                item["_player_id_role_unknown"] = False
                log(__name__, f"Dedicated Episode IMDb ID: {item['imdb_id']}")
        except Exception as e:
            log(__name__, f"Failed to read dedicated episode IDs from InfoLabels: {type(e).__name__}")

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
            log(__name__, f"Failed to extract movie IDs from InfoLabels: {type(e).__name__}")
        
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
            log(__name__, f"🔍 No IDs found, searching library by title ({item.get('year')})")
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
        # Keep whatever the player gave us before the parent strategies clear it: a parent id
        # can be wrong (a mis-scraped library, or a foreign id), and then the episode id is
        # the only thing left that identifies the episode. Used as a last attempt below.
        item["_player_episode_ids"] = {"imdb_id": item.get("imdb_id"),
                                       "tmdb_id": item.get("tmdb_id")}

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
            log(__name__, "🎯 API Strategy: title search only (no IDs available)")
    else:
        # For movies: Use specific movie IDs
        if item.get("imdb_id") or item.get("tmdb_id"):
            id_name = f"imdb_id={item.get('imdb_id')}" if item.get("imdb_id") else f"tmdb_id={item.get('tmdb_id')}"
            log(__name__, f"🎯 API Strategy: {id_name} (movie)")
        else:
            log(__name__, "🎯 API Strategy: title search only (movie, no IDs available)")

    fallback_title = item.get("query") or item.get("original_title") or normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))
    if not fallback_title:
        # Last resort: use filename - path component only, a stream URL's
        # '?token=...' must reach neither the search query nor the logs
        try:
            fallback_title = safe_media_filename(get_file_path()) or "Unknown"
        except Exception:
            fallback_title = "Unknown"

    item["query"] = fallback_title

    # Specials handling: only a bare "sN" label means special episode N.
    # A substring test matched any label containing 's' - including compound
    # ones like "S01E05" - zeroing the season and keeping just the last digit.
    if isinstance(item.get("episode_number"), str):
        special = re.fullmatch(r"[sS](\d+)", item["episode_number"].strip())
        if special:
            item["season_number"] = "0"
            item["episode_number"] = special.group(1)

    # ---------- Search plan for TV episodes & Movies ----------
    # When unique IDs (IMDb/TMDb) are available, sending 'query' or 'year' introduces
    # over-constrained text matching (e.g. original titles in other languages or release year discrepancies).
    # We clear 'query' and 'year' for the primary ID search, keeping title_attempt as a fallback.
    if item.get("tv_show_title"):
        title_attempt = {"query": fallback_title,
                         "season_number": item.get("season_number"),
                         "episode_number": item.get("episode_number"),
                         "imdb_id": None, "tmdb_id": None,
                         "parent_imdb_id": None, "parent_tmdb_id": None}
        role_unknown = item.pop("_player_id_role_unknown", False)
        episode_ids = item.pop("_player_episode_ids", None) or {}

        if role_unknown and (item.get("imdb_id") or item.get("tmdb_id")):
            if item.get("imdb_id"):
                id_key, parent_key, value = "imdb_id", "parent_imdb_id", item["imdb_id"]
            else:
                id_key, parent_key, value = "tmdb_id", "parent_tmdb_id", item["tmdb_id"]
            item[parent_key] = value
            item[id_key] = None
            item["query"] = ""
            item["year"] = None
            item["ambiguous_player_id"] = {id_key: value}
            item["search_fallbacks"] = [
                # then as the episode's id, which has to be sent on its own (Seren)
                {parent_key: None, id_key: value,
                 "query": "", "season_number": None, "episode_number": None},
                # and only if neither id matches anything, fall back to a title search
                title_attempt,
            ]
            log(__name__, f"Ambiguous player ID {value}: trying {parent_key} + season/episode, "
                          f"then {id_key} alone, then title search")
        elif item.get("imdb_id") or item.get("tmdb_id"):
            # Known to be the episode's own id, so it must travel alone.
            item["query"] = ""
            item["year"] = None
            item["season_number"] = None
            item["episode_number"] = None
            item["search_fallbacks"] = [title_attempt]
            log(__name__, "Episode-level ID search: dropped query/year/season/episode (kept for retry)")
        elif item.get("parent_imdb_id") or item.get("parent_tmdb_id"):
            # Show ID + season/episode: drop redundant query and year.
            # A parent id from the library is usually right, but a mis-scraped show yields
            # one OS.com has never seen and the search returns nothing - so keep the episode
            # id the player gave us as a second attempt rather than discarding it. Seen in a
            # user log: a library "imdbnumber" that was not an IMDb id at all went out as
            # parent_imdb_id (0 results) while the episode's own id matched 10 subtitles.
            item["query"] = ""
            item["year"] = None
            fallbacks = []
            if episode_ids.get("imdb_id") or episode_ids.get("tmdb_id"):
                fallbacks.append({"parent_imdb_id": None, "parent_tmdb_id": None,
                                  "imdb_id": episode_ids.get("imdb_id"),
                                  "tmdb_id": episode_ids.get("tmdb_id"),
                                  "query": "", "season_number": None, "episode_number": None})
                log(__name__, f"Show-level ID search, keeping episode ID "
                              f"{episode_ids.get('imdb_id') or episode_ids.get('tmdb_id')} as a fallback")
            fallbacks.append(title_attempt)
            item["search_fallbacks"] = fallbacks
            log(__name__, "Show-level ID search: dropped redundant query and year (kept for retry)")
    else:
        # Movie search: If unique IMDb/TMDb ID is present, drop query and year from primary request
        if item.get("imdb_id") or item.get("tmdb_id"):
            # the raw InfoLabel year can be implausible - validated or dropped,
            # never allowed to fail the retry request and stop the chain
            title_attempt = {"query": fallback_title, "year": _valid_year(item.get("year")),
                             "imdb_id": None, "tmdb_id": None}
            item["query"] = ""
            item["year"] = None
            item["search_fallbacks"] = [title_attempt]
            log(__name__, "Movie ID search: dropped redundant query and year (kept for retry)")

        # NB: no parent_* branch here. Movies never carry a parent id (those are set only in
        # the TV block above), and the episode-id fallback that used to live here referenced
        # `episode_ids`, which is not bound on this path - it was unreachable dead code that
        # would have raised NameError if it ever ran. The real logic is in the TV branch.

    # ---------- Tier 3.5: the same title, without the year ----------
    # `year` is ANDed like every other parameter, and a release year is not the feature
    # year: festival-to-release gaps and BluRay re-labelling shift it by one routinely.
    # "Freaky Tales" is a 2024 film shipped in a file named (2025) - sending 2025 did not
    # merely fail to narrow the search, it excluded the only correct feature, and because
    # `query` is a fuzzy token match the API then returned 30 subtitles for everything else
    # sharing a word: "7 immoral Tales", "A Tooth Fairy Tale", "Dracula: A Love Tale".
    # Dropping the year puts the right film first. One extra request, and only when the
    # year-constrained attempt found nothing usable.
    try:
        if item.get("query") and item.get("year"):
            source = item
        else:
            # An id-first plan keeps its title search in the fallbacks; relax that one.
            source = next((f for f in (item.get("search_fallbacks") or [])
                           if f.get("query") and f.get("year")), None)
        if source is not None:
            item.setdefault("search_fallbacks", []).append(
                {"query": source.get("query"), "year": None,
                 "season_number": source.get("season_number"),
                 "episode_number": source.get("episode_number"),
                 "imdb_id": None, "tmdb_id": None,
                 "parent_imdb_id": None, "parent_tmdb_id": None})
            log(__name__, "Added no-year retry "
                          f"(release year {source.get('year')} may not be the feature year)")
    except Exception as e:
        log(__name__, f"Could not build the no-year fallback: {type(e).__name__}")

    # ---------- Tier 4: the raw release filename, as a last resort ----------
    # Everything above searches by id or by a cleaned-up title. When all of those miss - a
    # mis-scraped library, an unusual release, a feature OS.com files under something else -
    # the release filename itself sometimes matches, because uploaders name subtitles after
    # it. Only reached when every earlier attempt returned nothing, so it costs a request
    # exactly when we would otherwise show the user nothing at all.
    # Skipped for streams: there the "filename" is a CDN path with no release info in it,
    # which is what the extension check below screens out.
    try:
        # both are only imported inside other branches of this module, so bind them here
        import os

        playing_file = get_file_path()
        basename = safe_media_filename(playing_file) if playing_file else ""
        stem = re.sub(r"\.(mkv|mp4|avi|m4v|ts|mov|wmv|iso|m2ts|flv|webm)$", "", basename,
                      flags=re.IGNORECASE)
        # stem != basename means a real video extension was stripped, i.e. this looks like a
        # release filename rather than a CDN URL or an opaque id
        if stem and stem != basename and stem.lower() != (fallback_title or "").lower():
            item.setdefault("search_fallbacks", []).append(
                {"query": stem, "year": None, "season_number": None, "episode_number": None,
                 "imdb_id": None, "tmdb_id": None,
                 "parent_imdb_id": None, "parent_tmdb_id": None})
            log(__name__, "Added filename fallback attempt")
    except Exception as e:
        log(__name__, f"Could not build the filename fallback: {type(e).__name__}")

    # Remove internal-only key
    if "tvshowid" in item:
        del item["tvshowid"]

    log(__name__, f"Media data result: query={'set' if item.get('query') else 'empty'} - IMDb:{item.get('imdb_id') or item.get('parent_imdb_id')} TMDb:{item.get('tmdb_id') or item.get('parent_tmdb_id')}")

    return item


def is_kodi_hearing_impaired_preferred():
    """Checks if Kodi has 'prefer subtitles for hearing impaired' enabled in system settings."""
    try:
        query = json.dumps({
            "jsonrpc": "2.0",
            "method": "Settings.GetSettingValue",
            "params": {"setting": "subtitles.hearingimpaired"},
            "id": 1
        })
        response = json.loads(xbmc.executeJSONRPC(query))
        return bool(response.get("result", {}).get("value", False))
    except Exception:
        return False


def get_language_data(params):
    # Kodi may invoke a search with no languages parameter at all -
    # unquote(None) would raise TypeError and abort the whole search.
    search_languages = unquote(params.get("languages") or "").split(",")
    search_languages_str = ""
    preferred_language = params.get("preferredlanguage")

    if preferred_language and preferred_language not in search_languages and preferred_language != "Unknown" and preferred_language != "Undetermined":
        # Only queue the name for conversion below - seeding the string with the
        # raw English name put ",Slovak,sl,sk" on the wire (leading comma + a
        # value the API cannot parse as a language code). Backport of the 2.0.0 fix.
        search_languages.append(preferred_language)

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

    hi_setting = __addon__.getSetting("hearing_impaired")
    # If add-on setting is default "exclude", but Kodi system has prefer hearing impaired ON, reflect Kodi
    if (not hi_setting or hi_setting == "exclude") and is_kodi_hearing_impaired_preferred():
        hi_setting = "include"

    def _include_exclude(setting_id):
        # The API accepts only include/exclude for the translation filters.
        # Old settings files may still carry "only" from when the UI offered
        # it - map it to "include" instead of letting request construction
        # fail and kill every fallback.
        value = __addon__.getSetting(setting_id)
        return "include" if value == "only" else value

    item = {
        "hearing_impaired": hi_setting or "exclude",
        "foreign_parts_only": __addon__.getSetting("foreign_parts_only"),
        "machine_translated": _include_exclude("machine_translated"),
        "ai_translated": _include_exclude("ai_translated"),
        "languages": search_languages_str
    }

    return item


def convert_language(language, reverse=False):
    language_list = {
        "English": "en",
        "Czech": "cs",
        "Slovak": "sk",
        "Spanish": "es",
        "Portuguese (Brazil)": "pt-br",
        "Portuguese (Portugal)": "pt-pt",
        "Portuguese": "pt-pt",
        "French": "fr",
        "German": "de",
        "Italian": "it",
        "Dutch": "nl",
        "Polish": "pl",
        "Russian": "ru",
        "Ukrainian": "uk",
        "Turkish": "tr",
        "Arabic": "ar",
        "Hebrew": "he",
        "Greek": "el",
        "Romanian": "ro",
        "Hungarian": "hu",
        "Bulgarian": "bg",
        "Serbian": "sr",
        "Croatian": "hr",
        "Slovenian": "sl",
        "Swedish": "sv",
        "Danish": "da",
        "Norwegian": "no",
        "Finnish": "fi",
        "Chinese": "zh-cn",
        "Chinese (simplified)": "zh-cn",
        "Chinese (traditional)": "zh-tw",
        "Japanese": "ja",
        "Korean": "ko",
        "Vietnamese": "vi",
        "Thai": "th",
        "Indonesian": "id",
        "Malay": "ms",
        "Hindi": "hi",
        "Persian": "fa"
    }

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
    # language codes come from API payloads - never crash a list row over one
    code = str(language_code or "").lower()
    return language_list.get(code, code)


def clean_feature_release_name(title, release, movie_name=""):
    # API fields can be null - a None here must degrade to the other fields,
    # not TypeError out of the row (the caller skips the whole entry)
    title = title or ""
    release = release or ""
    movie_name = movie_name or ""
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
    log(__name__, f"clean_feature_release_name match_ratio: {match_ratio}")
    if name in release:
        return release
    elif match_ratio > 0.3:
        return release
    else:
        return f"{name} {release}"

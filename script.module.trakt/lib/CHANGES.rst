2.5.2 (2016-02-19)
------------------
**Added**
 - :code:`in_watchlist` property to :code:`Movie`, :code:`Show`, :code:`Season` and :code:`Episode` objects (#45)
 - :code:`Trakt.site_url` setter to override automatic detection
 - :code:`HttpClient` now supports direct calls (#43)

**Changed**
 - Tests are now included in builds, but are excluded from installations

2.5.1 (2015-09-25)
------------------
**Fixed**
 - Issue installing trakt.py when "six" hasn't been installed yet

2.5.0 (2015-09-24)
------------------
**Added**
 - :code:`Trakt['users'].likes()` method
 - :code:`CustomList.items()` method
 - :code:`Comment` object
 - :code:`Media.index` attribute (list item position/rank)
 - Basic documentation generation (#29)
 - :code:`NullHandler` to the logger to avoid "No handler found" warnings (#33)

**Changed**
 - 'movies' and 'shows' interface methods to support the :code:`exceptions=True` parameter (#32)
 - :code:`Interface.get_data()` to only parse the response body if the request is successful (#32)

**Fixed**
 - :code:`TypeError` was raised in :code:`SummaryMapper` if the request failed (#30, #31)
 - Constructing "Special" episodes could raise an :code:`AttributeError` (#38, #39)
 - :code:`Media._update()` "images" attribute
 - Issue serializing :code:`List` objects

2.4.1 (2015-09-12)
------------------
**Fixed**
 - Issue where the "_client" attribute on objects was being serialized
 - Issue installing trakt.py when "arrow" isn't available yet

2.4.0 (2015-07-09)
------------------
**Added**
 - :code:`trending()` method to :code:`Trakt['shows']` and :code:`Trakt['movies']` interfaces (#23)
 - :code:`seasons()` and :code:`episodes()` methods to the :code:`Trakt['sync/watchlist']` interface (#26)
 - Custom lists support (:code:`Trakt['users/*/lists']`, :code:`Trakt['users/*/lists/*']`) (#26)
 - :code:`__eq__()` method on the :code:`Rating` class
 - :code:`proxies` attribute on :code:`Trakt.http`

**Changed**
 - :code:`datetime` objects are now returned offset-aware **(make sure you use offset-aware `datetime` objects when comparing timestamps now)**
 - Force requests to use :code:`ssl.PROTOCOL_TLSv1` connections for https:// (#25)
 - Return site url from :code:`Trakt['oauth'].authorize_url()`
 - Use season number from parent when one isn't defined in the episode


2.3.0 (2015-04-11)
------------------
**Changes**
 - Added support for PIN authentication
 - Added automatic OAuth token refreshing *(see "examples/pin.py" for an example)*
 - Added :code:`Trakt.configuration.oauth.from_response()` configuration method
 - Added tests for the :code:`Trakt['oauth']` interface
 - Added tests to ensure authentication headers are being sent
 - :code:`Trakt['oauth']` methods now raise an exception if you are missing required configuration parameters
 - :code:`Trakt['oauth'].token()` method has been renamed to :code:`Trakt['oauth'].token_exchange()` *(old method is still present for compatibility)*

**Fixed**
 - :code:`Trakt['oauth']` "_url" methods could raise an exception in some cases

2.2.0 (2015-04-02)
------------------
**Changes**
 - Added unit tests (with travis-ci.org and coveralls.io integrations)
 - Added :code:`/movies`, :code:`/shows`, :code:`/search` and :code:`/users/settings` interfaces
 - Added parent properties ("show", "season")
 - Added "images", "overview" and "score" properties to the :code:`Media` class
 - Added "last_watched_at" property to movies and episodes
 - Updated :code:`/sync/playback` interface (to include type filtering)
 - "progress" and "paused_at" properties are now included in :code:`to_dict()`

**Fixed**
 - "year" property could be returned as a string in some cases
 - Catch an exception in :code:`trakt.media_mapper`
 - Catch a case where :code:`Interface.get_data()` can raise a :code:`KeyError: 'content-type'` exception

2.1.1 (2015-02-06)
------------------
**Changes**
 - Updated to use the new v2 API endpoint (api-v2launch.trakt.tv)
 - Episode and Movie :code:`to_dict()` method now always returns "plays" as an integer
 - Added "http.retry_sleep" and "http.timeout" configuration parameters
 - Setup travis/coveralls services

**Fixed**
 - Python 3.x compatibility issues

2.1.0 (2015-02-05)
------------------
**Changes**
 - Added "exceptions" and "parse" parameter to `Interface.get_data()`
 - Added additional error messages (502, 504, 520)
 - Renamed media object `to_info()` method to `to_identifier()`
 - Added new `to_dict()` method which returns a dictionary representation of the media object
 - Request retrying (on 5xx errors) can now be enabled with `Trakt.configuration.http(retry=True)`
 - requests/urllib3 now retries requests on connection errors (default: 3 retries)

**Fixed**
 - Thread synchronization issue with `trakt.core.configuration`
 - [/sync] last_activities() used an incorrect path

2.0.8 (2015-01-06)
------------------
 - Catch all response errors to avoid issues parsing the returned body

2.0.7 (2015-01-04)
------------------
 - Handle a case where [media_mapper] processes an item with an empty "ids" dict

2.0.6 (2015-01-02)
------------------
 - Switched to manual interface importing to avoid security restrictions

2.0.5 (2015-01-02)
------------------
 - Convert all datetime properties to UTC

2.0.4 (2015-01-02)
------------------
 - Allow for charset definitions in "Content-Type" response header

2.0.3 (2015-01-02)
------------------
 - Display request failed messages in log (with error name/desc)

2.0.2 (2015-01-02)
------------------
 - Fixed broken logging message

2.0.1 (2015-01-02)
------------------
 - Properly handle responses where trakt.tv returns errors without a json body

2.0.0 (2014-12-31)
------------------
 - Re-designed to support trakt 2.0 (note: this isn't a drop-in update - interfaces, objects and methods have changed to match the new API)
 - Support for OAuth and xAuth authentication methods
 - Simple configuration system

0.7.0 (2014-10-24)
------------------
 - "title" and "year" parameters are now optional on scrobble() and watching() methods
 - [movie] Added unseen() method
 - [show/episode] Added unseen() method

0.6.1 (2014-07-10)
------------------
- Return None if an action fails validation (instead of raising an exception)

0.6.0 (2014-06-23)
------------------
- Added Trakt.configure() method
- Rebuild session on socket.gaierror (workaround for urllib error)

0.5.3 (2014-05-10)
------------------
- Fixed bugs sending media actions
- Renamed cancel_watching() to cancelwatching()
- "title" and "year" parameters are now optional on media actions

0.5.2 (2014-04-20)
------------------
- [movie] Added seen(), library() and unlibrary() methods
- [movie] Implemented media mapping
- [rate] Added shows(), episodes() and movies() methods
- [show] Added unlibrary() method
- [show/episode] Added library() and seen() methods

0.5.1 (2014-04-19)
------------------
- Added @authenticated to MediaInterface.send()
- Fixed missing imports

0.5.0 (2014-04-18)
------------------
- Initial release
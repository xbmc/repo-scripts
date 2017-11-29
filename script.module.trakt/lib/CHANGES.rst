2.14.1 (2017-03-07)
-------------------
**Added**

- :code:`__future__` imports to :code:`trakt/hooks.py`

2.14.0 (2017-03-07)
-------------------
**Added**

- Support for Python 3.6
- Package version is now automatically written into the :code:`trakt.version` module on :code:`python setup.py egg_info`
- :code:`__future__` imports for more consistent Python 3 compatibility
- :code:`SummaryMapper.episode` method now accepts the "parse_show" parameter
- Interfaces:

  - :code:`Trakt['calendars']` (#56)

**Changed**

- Dropped support for Python 3.2
- Cleaned up documentation
- Switched to pbr setup configuration
- Ordering of import statements has been updated to be more consistent

**Tests**

- Replaced usage of :code:`responses` in tests with :code:`httmock`
- Updated :code:`tox.ini` with additional test environments and flake8 plugins
- Improved the :code:`fixtures` directory structure

**Travis CI**

- Switched to using "tox-travis", instead of running pytest directly
- Releases are now automatically uploaded to PyPI and GitHub Releases

2.13.0 (2017-02-16)
-------------------
**Added**

- :code:`Trakt['sync/playback'].delete(<id>)` method (#54)

2.12.0 (2017-01-11)
-------------------
**Added**

- Improved token refreshing *(and added the "oauth.refresh" and "oauth.refresh.rejected" events)*
- `RequestFailedError` exception will now be raised if no response was returned (if `exceptions=True`)
- :code:`Trakt.http.keep_alive` property *(defaults to :code:`True`)*
- :code:`Trakt.http.ssl_version` property *(defaults to :code:`None` / :code:`PROTOCOL_TLS` / :code:`PROTOCOL_SSLv23`)*

**Changed**

- Switched default API endpoint to https://api.trakt.tv
- SSL protocol version is now automatically negotiated with the server *(instead of defaulting to TLS v1.0)*
- Warning will now be displayed if a deadlock is detected inside token refresh events
- Fixed some inconsistencies in the handling of error responses
- Updated bundled emitter module (fuzeman/PyEmitter@3c558c7c2bc3ae07cb1e8e18b2c1c16be042c748)
- Interfaces:

  - :code:`Trakt['search']`

    - Updated to use the new search endpoints

- Methods:

  - :code:`Trakt['search'].lookup`

    - Now supports the :code:`extended` parameter

  - :code:`Trakt['search'].query`

    - Now supports the :code:`fields` and :code:`extended` parameters

**Fixed**

- :code:`@authenticated` decorator wasn't applied to some methods, resulting in tokens not being refreshed
- Exception raised when :code:`Trakt['scrobble']` methods are provided "app_version" or "app_date" parameters
- Error responses weren't being returned correctly with :code:`parse=False`
- Issue handling :code:`None` responses in the automatic token refresher
- Inconsistent handling of error responses in some methods

2.11.0 (2016-12-20)
-------------------
**Added**

- Properties

  - :code:`Movie`

    - :code:`tagline`
    - :code:`released`
    - :code:`runtime`
    - :code:`certification`
    - :code:`updated_at`
    - :code:`homepage`
    - :code:`trailer`
    - :code:`language`
    - :code:`available_translations`
    - :code:`genres`

  - :code:`Show`

    - :code:`first_aired`
    - :code:`airs`
    - :code:`runtime`
    - :code:`certification`
    - :code:`network`
    - :code:`country`
    - :code:`updated_at`
    - :code:`status`
    - :code:`homepage`
    - :code:`language`
    - :code:`available_translations`
    - :code:`genres`
    - :code:`aired_episodes`

  - :code:`Season`

    - :code:`first_aired`
    - :code:`episode_count`
    - :code:`aired_episodes`

  - :code:`Episode`

    - :code:`first_aired`
    - :code:`updated_at`
    - :code:`available_translations`

**Changed**

- Methods on the :code:`Trakt['movies']` and :code:`Trakt['shows']` interfaces now support the :code:`extended` parameter (#51)
- Minor improvements to property descriptions on the :code:`Show` and :code:`Episode` objects

2.10.1 (2016-12-15)
-------------------
**Changed**

- Removed some stray files from the source distribution

2.10.0 (2016-12-15)
-------------------
**Added**

- Methods:

  - :code:`Trakt['shows'].next_episode` (#50)
  - :code:`Trakt['shows'].last_episode` (#50)

2.9.0 (2016-10-16)
------------------
**Added**

- Properties:

  - :code:`Person.listed_at`
  - :code:`Video.action`

- Methods:

  - :code:`Trakt['sync/history'].get`
  - :code:`Trakt['sync/history'].shows`
  - :code:`Trakt['sync/history'].movies`

**Changed**

- Updated :code:`SyncMapper` to support flat iterators
- Methods:

  - :code:`Trakt['sync/ratings'].get`

    - Flat iterator will now be returned if no :code:`media` parameter is provided

  - :code:`Trakt['sync/watchlist'].get`

    - Pagination is now supported, can be enabled with :code:`pagination=True`
    - :code:`media` parameter can now be specified as :code:`None` to return all items (with no type filter)

**Fixed**

- Pagination wouldn't work correctly if a starting page was specified

2.8.0 (2016-09-17)
------------------
**Added**

- Lists containing people are now supported (instead of raising an exception)
- :code:`SyncMapper` can now be used without the :code:`store` parameter
- Objects:

  - :code:`Person`

- Properties:

  - :code:`Video.id` (history id)
  - :code:`Video.watched_at` (history timestamp)

- Methods:

  - :code:`Media.get_key(<service>)`

2.7.1 (2016-08-30)
------------------
**Fixed**

- Invalid classifier was defined in [setup.py]

2.7.0 (2016-08-30)
------------------
**Added**

- Support for multiple :code:`media` options on the :code:`Trakt['search'].query()` method
- Implemented the :code:`media` parameter on the :code:`Trakt['search'].lookup()` method

**Changed**

- "Request failed" warnings now display the request method and path to help with debugging
- Improved handling of requirements in [setup.py]

2.6.1 (2016-05-19)
------------------
**Changed**

- Updated request error messages

**Fixed**

- Authorization tokens generated with device authentication wouldn't refresh correctly

2.6.0 (2016-04-15)
------------------
**Added**

- :code:`Trakt['oauth/device']` (see :code:`examples/authentication/device.py` for usage details)
- :code:`Trakt['shows'].seasons()` now supports the :code:`extended="episodes"` parameter
- Pagination can now be enabled with :code:`pagination=True`, `warnings <https://docs.python.org/2/library/warnings.html>`_ will be displayed if you ignore pagination responses

**Changed**

- Moved the :code:`Trakt['oauth'].pin_url()` method to :code:`Trakt['oauth/pin'].url()`, the old method still works but will display a deprecation `warning <https://docs.python.org/2/library/warnings.html>`_

**Fixed**

- Issue retrieving lists by users with the :code:`.` character in their usernames

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

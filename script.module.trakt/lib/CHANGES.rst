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
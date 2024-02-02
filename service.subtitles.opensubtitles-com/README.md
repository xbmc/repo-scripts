# (Unofficial) Python2 backport of OpenSubtitles.com KODI add-on

**IMPORTANT NOTE**: This is an unofficial backport of [OpenSubtitles.com](https://github.com/opensubtitlesdev/service.subtitles.opensubtitles-com). The official add-on requires python3 ([so it does not work on Kodi v<19](https://github.com/opensubtitlesdev/service.subtitles.opensubtitles-com/issues/2) ). This backport to python 2 *works for me* on a Kodi Leia (v18).


Search and download subtitles for movies and TV-Series from OpenSubtitles.com. Search in 75 languages, 4.000.000+ subtitles, daily updates.

REST API implementation based on tomburke25 [python-opensubtitles-rest-api](https://github.com/tomburke25/python-opensubtitles-rest-api)                            


v1.0.4+leia.1 (2024-01-30)
- Backport v1.0.4 to Kodi Leia (forked by cpascual)

v1.0.4 (2024-01-15)
- Sanitize language query
- Improved sorting
- Improved error messages 
- Improved usage of moviehash 

v1.0.3 (2023-12-18)
- Fixed issue with file path

v1.0.2 (2023-08-28)
- Update user agent header

v1.0.1 (2023-07-28)
- Remove limit of 10 subtitles for the returned values
- Fix Portuguese and Brazilian flags

1.0.0
 Initial version, forked from https://github.com/juokelis/service.subtitles.opensubtitles
 Search fixed and improved

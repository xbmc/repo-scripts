# Latest Rating Service for Kodi

A Kodi service add-on that automatically updates movie and TV show ratings in your library.

## Features
- Automatically updates ratings on a configurable schedule
- Supports IMDb and Trakt as rating sources
- Weighted average calculation when multiple sources are enabled
- Configurable date range filters to limit which movies and TV shows get updated
- Built-in log viewer through "Run" function of the add-on (for now you can only see logs in current session)

## Installation
1. Download the zip file
2. In Kodi, go to Settings > Add-ons > Install from zip file
3. Select the downloaded zip file

## Configuration
1. Enable desired rating sources (IMDb and/or Trakt)
2. Set update interval and content filters
3. The service will start automatically

## Credits
Rating fetch functionality and Trakt API key from [Kodi's official TV Show scraper](https://github.com/xbmc/metadata.tvshows.themoviedb.org.python).

## License
GPL-3.0 
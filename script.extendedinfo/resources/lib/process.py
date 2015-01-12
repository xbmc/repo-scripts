from LastFM import *
from MiscScraper import *
from TheAudioDB import *
from TheMovieDB import *
from Utils import *
from RottenTomatoes import *
from YouTube import *
from Trakt import *
homewindow = xbmcgui.Window(10000)
Addon_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % addon_id).decode("utf-8"))
Skin_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % xbmc.getSkinDir()).decode("utf-8"))


def StartInfoActions(infos, params):
    if "artistname" in params:
        params["artistname"] = params.get("artistname", "").split(" feat. ")[0].strip()
        params["artist_mbid"] = GetMusicBrainzIdFromNet(params["artistname"])
    prettyprint(params)
    prettyprint(infos)
    if "prefix" in params and (not params["prefix"].endswith('.')) and (params["prefix"] is not ""):
        params["prefix"] = params["prefix"] + '.'
    for info in infos:
        data = None
        ########### Images #####################
        if info == 'xkcd':
            data = GetXKCDInfo(), "XKCD"
        elif info == 'flickr':
            data = GetFlickrImages(), "Flickr"
        elif info == 'cyanide':
            data = GetCandHInfo(), "CyanideHappiness"
        elif info == 'dailybabes':
            data = GetDailyBabes(), "DailyBabes"
        elif info == 'dailybabe':
            data = GetDailyBabes(single=True), "DailyBabe"
        ########### Audio #####################
        elif info == 'discography':
            Discography = GetDiscography(params["artistname"])
            if len(Discography) == 0:
                Discography = GetArtistTopAlbums(params.get("artist_mbid"))
            data = Discography, "Discography"
        elif info == 'mostlovedtracks':
            data = GetMostLovedTracks(params["artistname"]), "MostLovedTracks"
        elif info == 'artistdetails':
            ArtistDetails = GetArtistDetails(params["artistname"])
            passDictToSkin(ArtistDetails, params.get("prefix", ""))
            if "audiodbid" in ArtistDetails:
                data = GetMusicVideos(ArtistDetails["audiodbid"]), "MusicVideos"
        elif info == 'musicvideos':
            pass
            # if "audiodbid" in ArtistDetails:
            #     data = GetMusicVideos(ArtistDetails["audiodbid"]), "MusicVideos"
        elif info == 'albuminfo':
            if params.get("id", ""):
                AlbumDetails = GetAlbumDetails(params.get("id", ""))
                passDictToSkin(AlbumDetails, params.get("prefix", ""))
        elif info == 'trackdetails':
            if params.get("id", ""):
                data = GetTrackDetails(params.get("id", "")), "Trackinfo"
        elif info == 'albumshouts':
            if params["artistname"] and params["albumname"]:
                data = GetAlbumShouts(params["artistname"], params["albumname"]), "Shout"
        elif info == 'artistshouts':
            if params["artistname"]:
                data = GetArtistShouts(params["artistname"]), "Shout"
        elif info == 'topartists':
            data = GetTopArtists(), "TopArtists"
        elif info == 'hypedartists':
            data = GetHypedArtists(), "HypedArtists"
        ### RottenTomatoesMovies #################################################################################
        elif info == 'intheaters':
            data = GetRottenTomatoesMovies("movies/in_theaters"), "InTheatersMovies"
        elif info == 'boxoffice':
            data = GetRottenTomatoesMovies("movies/box_office"), "BoxOffice"
        elif info == 'opening':
            data = GetRottenTomatoesMovies("movies/opening"), "Opening"
        elif info == 'comingsoon':
            data = GetRottenTomatoesMovies("movies/upcoming"), "ComingSoonMovies"
        elif info == 'toprentals':
            data = GetRottenTomatoesMovies("dvds/top_rentals"), "TopRentals"
        elif info == 'currentdvdreleases':
            data = GetRottenTomatoesMovies("dvds/current_releases"), "CurrentDVDs"
        elif info == 'newdvdreleases':
            data = GetRottenTomatoesMovies("dvds/new_releases"), "NewDVDs"
        elif info == 'upcomingdvds':
            data = GetRottenTomatoesMovies("dvds/upcoming"), "UpcomingDVDs"
        ### The MovieDB ##########################################################################################
        elif info == 'incinemas':
            data = GetMovieDBMovies("now_playing"), "InCinemasMovies"
        elif info == 'upcoming':
            data = GetMovieDBMovies("upcoming"), "UpcomingMovies"
        elif info == 'topratedmovies':
            data = GetMovieDBMovies("top_rated"), "TopRatedMovies"
        elif info == 'popularmovies':
            data = GetMovieDBMovies("popular"), "PopularMovies"
        elif info == 'airingtodaytvshows':
            data = GetMovieDBTVShows("airing_today"), "AiringTodayTVShows"
        elif info == 'onairtvshows':
            data = GetMovieDBTVShows("on_the_air"), "OnAirTVShows"
        elif info == 'topratedtvshows':
            data = GetMovieDBTVShows("top_rated"), "TopRatedTVShows"
        elif info == 'populartvshows':
            data = GetMovieDBTVShows("popular"), "PopularTVShows"
        elif info == 'similarmovies':
            if params.get("id", False):
                MovieId = params["id"]
            elif int(params.get("dbid", -1)) > -1:
                MovieId = GetImdbIDFromDatabase("movie", params["dbid"])
                log("IMDBId from local DB:" + str(MovieId))
            else:
                MovieId = ""
            if MovieId:
                data = GetSimilarMovies(MovieId), "SimilarMovies"
        elif info == 'studio':
            if params["studio"]:
                CompanyId = SearchforCompany(params["studio"])[0]["id"]
                data = GetCompanyInfo(CompanyId), "StudioInfo"
        elif info == 'set':
            if params.get("dbid", False) and not "show" in str(params["type"]):
                name = GetMovieSetName(params["dbid"])
                if name:
                    params["setid"] = SearchForSet(name)
            if params["setid"]:
                SetData, info = GetSetMovies(params["setid"])
                if SetData:
                    data = SetData, "MovieSetItems"
        elif info == 'movielists':
            if params.get("dbid", False):
                movieid = GetImdbIDFromDatabase("movie", params["dbid"])
                log("MovieDB Id:" + str(movieid))
                if movieid:
                    data = GetMovieLists(movieid), "MovieLists"
        elif info == 'keywords':
            if params.get("dbid", False):
                movieid = GetImdbIDFromDatabase("movie", params["dbid"])
                log("MovieDB Id:" + str(movieid))
                if movieid:
                    data = GetMovieKeywords(movieid), "Keywords"
        elif info == 'popularpeople':
            data = GetPopularActorList(), "PopularPeople"
        elif info == 'extendedinfo':
            from DialogVideoInfo import DialogVideoInfo
            if params.get("handle", ""):
                xbmcplugin.endOfDirectory(params.get("handle", ""))
            dialog = DialogVideoInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=params.get("id", ""), dbid=params.get("dbid", None), imdbid=params.get("imdbid", ""), name=params.get("name", ""))
            dialog.doModal()
        elif info == 'extendedactorinfo':
            from DialogActorInfo import DialogActorInfo
            dialog = DialogActorInfo(u'script-%s-DialogInfo.xml' % addon_name, addon_path, id=params.get("id", ""), name=params.get("name", ""))
            dialog.doModal()

        elif info == 'extendedtvinfo':
            from DialogTVShowInfo import DialogTVShowInfo
            if params.get("handle", ""):
                xbmcplugin.endOfDirectory(params.get("handle", ""))
            dialog = DialogTVShowInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, id=params.get("id", ""), dbid=params.get("dbid", None), imdbid=params.get("imdbid", ""), name=params.get("name", ""))
            dialog.doModal()
        elif info == 'seasoninfo':
            if params.get("tvshow", False) and params.get("season", False):
                from DialogSeasonInfo import DialogSeasonInfo
                dialog = DialogSeasonInfo(u'script-%s-DialogVideoInfo.xml' % addon_name, addon_path, tvshow=params["tvshow"], season=params["season"])
                dialog.doModal()
            else:
                Notify("Error", "Required data missing in script call")
        elif info == 'directormovies':
            if params.get("director", False):
                directorid = GetPersonID(params["director"])["id"]
                if directorid:
                    data = GetDirectorMovies(directorid), "DirectorMovies"
        elif info == 'writermovies':
            if params.get("writer", False) and not params["writer"].split(" / ")[0] == params.get("director", "").split(" / ")[0]:
                writerid = GetPersonID(params["writer"])["id"]
                if writerid:
                    data = GetDirectorMovies(writerid), "WriterMovies"
        elif info == 'similarmoviestrakt':
            if params.get("id", False) or params.get("dbid", False):
                if params.get("dbid", False):
                    movieid = GetImdbIDFromDatabase("movie", params["dbid"])
                else:
                    movieid = params.get("id", "")
                data = GetSimilarTrakt("movie", movieid), "SimilarMovies"
        elif info == 'similartvshowstrakt':
            if (params.get("id", "") or params["dbid"]):
                if params.get("dbid", False):
                    if params["type"] == "episode":
                        tvshowid = GetImdbIDFromDatabasefromEpisode(params["dbid"])
                    else:
                        tvshowid = GetImdbIDFromDatabase("tvshow", params["dbid"])
                else:
                    tvshowid = params.get("id", "")
                data = GetSimilarTrakt("show", tvshowid), "SimilarTVShows"
        elif info == 'airingshows':
            data = GetTraktCalendarShows("shows"), "AiringShows"
        elif info == 'premiereshows':
            data = GetTraktCalendarShows("premieres"), "PremiereShows"
        elif info == 'trendingshows':
            data = GetTrendingShows(), "TrendingShows"
        elif info == 'trendingmovies':
            data = GetTrendingMovies(), "TrendingMovies"
        elif info == 'similarartistsinlibrary':
            if params.get("artist_mbid"):
                data = GetSimilarArtistsInLibrary(params.get("artist_mbid")), "SimilarArtists"
        elif info == 'artistevents':
            if params.get("artist_mbid"):
                data = GetEvents(params.get("artist_mbid")), "ArtistEvents"
        elif info == 'youtubesearch':
            homewindow.setProperty('%sSearchValue' % params.get("prefix", ""), params.get("id", ""))  # set properties
            if params.get("id", False):
                data = GetYoutubeSearchVideosV3(params.get("id", ""), params.get("hd", ""), params.get("orderby", "relevance")), "YoutubeSearch"
        elif info == 'youtubeplaylist':
            if params.get("id", False):
                data = GetYoutubePlaylistVideos(params.get("id", "")), "YoutubePlaylist"
        elif info == 'youtubeusersearch':
            if params.get("id", ""):
                data = GetYoutubeUserVideos(params.get("id", "")), "YoutubeUserSearch"
        elif info == 'nearevents':
            data = GetNearEvents(params.get("tag", ""), params.get("festivalsonly", ""), params.get("lat", ""), params.get("lon", ""), params.get("location", ""), params.get("distance", "")), "NearEvents"
        elif info == 'trackinfo':
            homewindow.setProperty('%sSummary' % params.get("prefix", ""), "")  # set properties
            if params["artistname"] and params["trackname"]:
                TrackInfo = GetTrackInfo(params["artistname"], params["trackname"])
                homewindow.setProperty('%sSummary' % params.get("prefix", ""), TrackInfo["summary"])  # set properties
        elif info == 'venueevents':
            if params["location"]:
                params["id"] = GetVenueID(params["location"])
            if params.get("id", ""):
                data = GetVenueEvents(params.get("id", "")), "VenueEvents"
            else:
                Notify("Error", "Could not find venue")
        elif info == 'topartistsnearevents':
            artists = GetXBMCArtists()
            data = GetArtistNearEvents(artists["result"]["artists"][0:49]), "TopArtistsNearEvents"
        elif info == 'channels':
            channels = create_channel_list()
      #      prettyprint(channels)
        elif info == 'favourites':
            if params.get("id", ""):
                favourites = GetFavouriteswithType(params.get("id", ""))
            else:
                favourites = GetFavourites()
                homewindow.setProperty('favourite.count', str(len(favourites)))
                if len(favourites) > 0:
                    homewindow.setProperty('favourite.1.name', favourites[-1]["Label"])
            data = favourites, "Favourites"
        elif info == 'json':
            data = GetYoutubeVideos(params["feed"]), "RSS"
        elif info == 'similarlocal' and "dbid" in params:
            data = GetSimilarFromOwnLibrary(params["dbid"]), "SimilarLocalMovies"
        elif info == 'iconpanel':
            data = GetIconPanel(int(self.id)), "IconPanel" + str(self.id)
        elif info == 'weather':
            data = GetWeatherImages(), "WeatherImages"
        elif info == 'updatexbmcdatabasewithartistmbidbg':
            SetMusicBrainzIDsForAllArtists(False, False)
        elif info == 'setfocus':
            params["control"] = ""  # workaround to avoid breaking PlayMedia
            xbmc.executebuiltin("SetFocus(22222)")
        elif info == 'playliststats':
            GetPlaylistStats(params.get("id", ""))
        elif info == "sortletters":
            data = GetSortLetters(params["path"], params.get("id", "")), "SortLetters"
        elif info == 'slideshow':
            windowid = xbmcgui.getCurrentWindowId()
            Window = xbmcgui.Window(windowid)
            # focusid = Window.getFocusId()
            itemlist = Window.getFocus()
            numitems = itemlist.getSelectedPosition()
            log("items:" + str(numitems))
            for i in range(0, numitems):
                Notify(item.getProperty("Image"))
        elif info == 'action':
            xbmc.executebuiltin(params.get("id", ""))
        elif info == 'bounce':
            homewindow.setProperty(params.get("name", ""), "True")
            xbmc.sleep(200)
            homewindow.clearProperty(params.get("name", ""))
        elif info == "youtubevideo":
            if params.get("id", ""):
                params["control"] = ""  # workaround to avoid breaking PlayMedia
                xbmc.executebuiltin("Dialog.Close(all,true)")
                PlayTrailer(params.get("id", ""))
        elif info == 'playtrailer':
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            xbmc.sleep(500)
            if params.get("id", ""):
                MovieId = params.get("id", "")
            elif int(params.get("dbid", -1)) > -1:
                MovieId = GetImdbIDFromDatabase("movie", params["dbid"])
                log("MovieDBID from local DB:" + str(MovieId))
            elif params.get("imdbid", ""):
                MovieId = GetMovieDBID(params.get("imdbid", ""))
            else:
                MovieId = ""
            if MovieId:
                trailer = GetTrailer(MovieId)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                if trailer:
                    PlayTrailer(trailer)
                    params["control"] = ""  # workaround to avoid breaking PlayMedia
                else:
                    Notify("Error", "No Trailer available")
        elif info == 'updatexbmcdatabasewithartistmbid':
            SetMusicBrainzIDsForAllArtists(True, False)
        if data:
            data, prefix = data
            passListToSkin(prefix, data, params.get("prefix", ""), params.get("window", ""), params.get("handle", ""), params.get("limit", 20))
        elif info == 'deletecache':
            for the_file in os.listdir(Addon_Data_Path):
                file_path = os.path.join(Addon_Data_Path, the_file)
                try:
                    if os.path.isfile(file_path) and not the_file == "settings.xml":
                        os.unlink(file_path)
                except Exception, e:
                    log(e)
            Notify("Cache deleted")
        elif info == 'syncwatchlist':
            pass
    return params["control"]

# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from LastFM import *
from TheAudioDB import *
from TheMovieDB import *
from Utils import *
from local_db import *
from YouTube import *
from Trakt import *
from WindowManager import wm
import VideoPlayer
PLAYER = VideoPlayer.VideoPlayer()


def start_info_actions(infos, params):
    if "artistname" in params:
        params["artistname"] = params.get("artistname", "").split(" feat. ")[0].strip()
        params["artist_mbid"] = fetch_musicbrainz_id(params["artistname"])
    prettyprint(params)
    prettyprint(infos)
    if "prefix" in params and (not params["prefix"].endswith('.')) and (params["prefix"] is not ""):
        params["prefix"] = params["prefix"] + '.'
    # NOTICE: compatibility
    if "imdbid" in params and "imdb_id" not in params:
        params["imdb_id"] = params["imdbid"]
    for info in infos:
        data = [], ""
        #  Images
        if info == 'xkcd':
            from MiscScraper import get_xkcd_images
            data = get_xkcd_images(), "XKCD"
        elif info == 'cyanide':
            from MiscScraper import get_cyanide_images
            data = get_cyanide_images(), "CyanideHappiness"
        elif info == 'dailybabes':
            from MiscScraper import get_babe_images
            data = get_babe_images(), "DailyBabes"
        elif info == 'dailybabe':
            from MiscScraper import get_babe_images
            data = get_babe_images(single=True), "DailyBabe"
        # Audio
        elif info == 'discography':
            discography = get_artist_discography(params["artistname"])
            if not discography:
                discography = get_artist_albums(params.get("artist_mbid"))
            data = discography, "discography"
        elif info == 'mostlovedtracks':
            data = get_most_loved_tracks(params["artistname"]), "MostLovedTracks"
        elif info == 'musicvideos':
            pass
            # if "audiodbid" in artist_details:
            #     data = get_musicvideos(artist_details["audiodbid"]), "MusicVideos"
        elif info == 'trackdetails':
            if params.get("id", ""):
                data = get_track_details(params.get("id", "")), "Trackinfo"
        elif info == 'albumshouts':
            if params["artistname"] and params["albumname"]:
                data = get_album_shouts(params["artistname"], params["albumname"]), "Shout"
        elif info == 'artistshouts':
            if params["artistname"]:
                data = get_artist_shouts(params["artistname"]), "Shout"
        elif info == 'topartists':
            data = get_top_artists(), "TopArtists"
        elif info == 'hypedartists':
            data = get_hyped_artists(), "HypedArtists"
        elif info == 'latestdbmovies':
            data = get_db_movies('"sort": {"order": "descending", "method": "dateadded"}', params.get("limit", 10)), "LatestMovies"
        elif info == 'randomdbmovies':
            data = get_db_movies('"sort": {"method": "random"}', params.get("limit", 10)), "RandomMovies"
        elif info == 'inprogressdbmovies':
            method = '"sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}'
            data = get_db_movies(method, params.get("limit", 10)), "RecommendedMovies"
    #  RottenTomatoesMovies
        elif info == 'intheaters':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("movies/in_theaters"), "InTheatersMovies"
        elif info == 'boxoffice':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("movies/box_office"), "BoxOffice"
        elif info == 'opening':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("movies/opening"), "Opening"
        elif info == 'comingsoon':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("movies/upcoming"), "ComingSoonMovies"
        elif info == 'toprentals':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("dvds/top_rentals"), "TopRentals"
        elif info == 'currentdvdreleases':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("dvds/current_releases"), "CurrentDVDs"
        elif info == 'newdvdreleases':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("dvds/new_releases"), "NewDVDs"
        elif info == 'upcomingdvds':
            from RottenTomatoes import get_rottentomatoes_movies
            data = get_rottentomatoes_movies("dvds/upcoming"), "UpcomingDVDs"
        #  The MovieDB
        elif info == 'incinemas':
            data = get_tmdb_movies("now_playing"), "InCinemasMovies"
        elif info == 'upcoming':
            data = get_tmdb_movies("upcoming"), "UpcomingMovies"
        elif info == 'topratedmovies':
            data = get_tmdb_movies("top_rated"), "TopRatedMovies"
        elif info == 'popularmovies':
            data = get_tmdb_movies("popular"), "PopularMovies"
        elif info == 'ratedmovies':
            data = get_rated_media_items("movies"), "RatedMovies"
        elif info == 'starredmovies':
            data = get_fav_items("movies"), "StarredMovies"
        elif info == 'accountlists':
            account_lists = handle_tmdb_misc(get_account_lists())
            for item in account_lists:
                item["directory"] = True
            data = account_lists, "AccountLists"
        elif info == 'listmovies':
            movies = get_movies_from_list(params["id"])
            data = movies, "AccountLists"
        elif info == 'airingtodaytvshows':
            data = get_tmdb_shows("airing_today"), "AiringTodayTVShows"
        elif info == 'onairtvshows':
            data = get_tmdb_shows("on_the_air"), "OnAirTVShows"
        elif info == 'topratedtvshows':
            data = get_tmdb_shows("top_rated"), "TopRatedTVShows"
        elif info == 'populartvshows':
            data = get_tmdb_shows("popular"), "PopularTVShows"
        elif info == 'ratedtvshows':
            data = get_rated_media_items("tv"), "RatedTVShows"
        elif info == 'starredtvshows':
            data = get_fav_items("tv"), "StarredTVShows"
        elif info == 'similarmovies':
            movie_id = params.get("id", False)
            if not movie_id:
                movie_id = get_movie_tmdb_id(imdb_id=params.get("imdb_id", False),
                                             dbid=params.get("dbid", False))
            if movie_id:
                data = get_similar_movies(movie_id), "SimilarMovies"
        elif info == 'similartvshows':
            tvshow_id = None
            dbid = params.get("dbid", False)
            name = params.get("name", False)
            tmdb_id = params.get("tmdb_id", False)
            tvdb_id = params.get("tvdb_id", False)
            imdb_id = params.get("imdb_id", False)
            if tmdb_id:
                tvshow_id = tmdb_id
            elif dbid and int(dbid) > 0:
                tvdb_id = get_imdb_id_from_db("tvshow", dbid)
                if tvdb_id:
                    tvshow_id = get_show_tmdb_id(tvdb_id)
            elif tvdb_id:
                tvshow_id = get_show_tmdb_id(tvdb_id)
            elif imdb_id:
                tvshow_id = get_show_tmdb_id(imdb_id, "imdb_id")
            elif name:
                tvshow_id = search_media(name, "", "tv")
            if tvshow_id:
                data = get_similar_tvshows(tvshow_id), "SimilarTVShows"
        elif info == 'studio':
            if "id" in params and params["id"]:
                data = get_company_data(params["id"]), "StudioInfo"
            elif "studio" in params and params["studio"]:
                company_data = search_company(params["studio"])
                if company_data:
                    data = get_company_data(company_data[0]["id"]), "StudioInfo"
        elif info == 'set':
            if params.get("dbid") and "show" not in str(params.get("type", "")):
                name = get_set_name_from_db(params["dbid"])
                if name:
                    params["setid"] = get_set_id(name)
            if params.get("setid"):
                set_data, _ = get_set_movies(params["setid"])
                if set_data:
                    data = set_data, "MovieSetItems"
        elif info == 'movielists':
            movie_id = params.get("id", False)
            if not movie_id:
                movie_id = get_movie_tmdb_id(imdb_id=params.get("imdb_id", False),
                                             dbid=params.get("dbid", False))
            if movie_id:
                data = get_movie_lists(movie_id), "MovieLists"
        elif info == 'keywords':
            movie_id = params.get("id", False)
            if not movie_id:
                movie_id = get_movie_tmdb_id(imdb_id=params.get("imdb_id", False),
                                             dbid=params.get("dbid", False))
            if movie_id:
                data = get_keywords(movie_id), "Keywords"
        elif info == 'popularpeople':
            data = get_popular_actors(), "PopularPeople"
        elif info == 'directormovies':
            if params.get("director"):
                director_info = get_person_info(person_label=params["director"],
                                                skip_dialog=True)
                if director_info and director_info.get("id"):
                    movies = get_person_movies(director_info["id"])
                    for item in movies:
                        del item["credit_id"]
                    data = merge_dict_lists(movies, key="department"), "DirectorMovies"
        elif info == 'writermovies':
            if params.get("writer") and not params["writer"].split(" / ")[0] == params.get("director", "").split(" / ")[0]:
                writer_info = get_person_info(person_label=params["writer"],
                                              skip_dialog=True)
                if writer_info and writer_info.get("id"):
                    movies = get_person_movies(writer_info["id"])
                    for item in movies:
                        del item["credit_id"]
                    data = merge_dict_lists(movies, key="department"), "WriterMovies"
        elif info == 'similarmoviestrakt':
            if params.get("id", False) or params.get("dbid"):
                if params.get("dbid"):
                    movie_id = get_imdb_id_from_db("movie", params["dbid"])
                else:
                    movie_id = params.get("id", "")
                data = get_trakt_similar("movie", movie_id), "SimilarMovies"
        elif info == 'similartvshowstrakt':
            if (params.get("id", "") or params["dbid"]):
                if params.get("dbid"):
                    if params.get("type") == "episode":
                        tvshow_id = get_tvshow_id_from_db_by_episode(params["dbid"])
                    else:
                        tvshow_id = get_imdb_id_from_db(media_type="tvshow",
                                                        dbid=params["dbid"])
                else:
                    tvshow_id = params.get("id", "")
                data = get_trakt_similar("show", tvshow_id), "SimilarTVShows"
        elif info == 'airingshows':
            data = get_trakt_calendar_shows("shows"), "AiringShows"
        elif info == 'premiereshows':
            data = get_trakt_calendar_shows("premieres"), "PremiereShows"
        elif info == 'trendingshows':
            data = get_trending_shows(), "TrendingShows"
        elif info == 'trendingmovies':
            data = get_trending_movies(), "TrendingMovies"
        elif info == 'similarartistsinlibrary':
            if params.get("artist_mbid"):
                data = get_similar_artists_from_db(params.get("artist_mbid")), "SimilarArtists"
        elif info == 'artistevents':
            if params.get("artist_mbid"):
                data = get_events(params.get("artist_mbid")), "ArtistEvents"
        elif info == 'youtubesearch':
            HOME.setProperty('%sSearchValue' % params.get("prefix", ""), params.get("id", ""))  # set properties
            if params.get("id"):
                listitems = search_youtube(search_str=params.get("id", ""),
                                           hd=params.get("hd", ""),
                                           orderby=params.get("orderby", "relevance"))
                data = listitems.get("listitems", []), "YoutubeSearch"
        elif info == 'youtubeplaylist':
            if params.get("id"):
                data = get_youtube_playlist_videos(params.get("id", "")), "YoutubePlaylist"
        elif info == 'youtubeusersearch':
            user_name = params.get("id", "")
            if user_name:
                playlists = get_youtube_user_playlists(user_name)
                data = get_youtube_playlist_videos(playlists["uploads"]), "YoutubeUserSearch"
        elif info == 'nearevents':
            eventinfo = get_near_events(tag=params.get("tag", ""),
                                        festivals_only=params.get("festivalsonly", ""),
                                        lat=params.get("lat", ""),
                                        lon=params.get("lon", ""),
                                        location=params.get("location", ""),
                                        distance=params.get("distance", ""))
            data = eventinfo, "NearEvents"
        elif info == 'trackinfo':
            HOME.setProperty('%sSummary' % params.get("prefix", ""), "")  # set properties
            if params["artistname"] and params["trackname"]:
                track_info = get_track_info(artist=params["artistname"],
                                            track=params["trackname"])
                HOME.setProperty('%sSummary' % params.get("prefix", ""), track_info["summary"])  # set properties
        elif info == 'venueevents':
            if params["location"]:
                params["id"] = get_venue_id(params["location"])
            if params.get("id", ""):
                data = get_venue_events(params.get("id", "")), "VenueEvents"
            else:
                notify("Error", "Could not find venue")
        elif info == 'topartistsnearevents':
            artists = get_kodi_artists()
            from MiscScraper import get_artist_near_events
            data = get_artist_near_events(artists["result"]["artists"][0:49]), "TopArtistsNearEvents"
        elif info == 'favourites':
            if params.get("id", ""):
                favs = get_favs_by_type(params.get("id", ""))
            else:
                favs = get_favs()
                HOME.setProperty('favourite.count', str(len(favs)))
                if favs:
                    HOME.setProperty('favourite.1.name', favs[-1]["Label"])
            data = favs, "Favourites"
        elif info == 'similarlocal' and "dbid" in params:
            data = get_similar_movies_from_db(params["dbid"]), "SimilarLocalMovies"
        elif info == 'iconpanel':
            data = get_icon_panel(int(params["id"])), "IconPanel" + str(params["id"])
        elif info == 'autocomplete':
            data = get_autocomplete_items(params["id"]), "AutoComplete"
        elif info == 'weather':
            data = get_weather_images(), "WeatherImages"
        elif info == "sortletters":
            data = get_sort_letters(params["path"], params.get("id", "")), "SortLetters"

        # ACTIONS
        elif info == 't9input':
            resolve_url(params.get("handle"))
            from dialogs.T9Search import T9Search
            dialog = T9Search(u'script-%s-T9Search.xml' % ADDON_NAME, ADDON_PATH,
                              call=None,
                              start_value="")
            dialog.doModal()
            get_kodi_json(method="Input.SendText",
                          params='{"text":"%s", "done":true}' % dialog.search_str)

        elif info == 'playmovie':
            resolve_url(params.get("handle"))
            get_kodi_json(method="Player.Open",
                          params='{"item": {"movieid": %s}, "options":{"resume": %s}}' % (params.get("dbid"), params.get("resume", "true")))
        elif info == 'playepisode':
            resolve_url(params.get("handle"))
            get_kodi_json(method="Player.Open",
                          params='{"item": {"episodeid": %s}, "options":{"resume": %s}}' % (params.get("dbid"), params.get("resume", "true")))
        elif info == 'playmusicvideo':
            resolve_url(params.get("handle"))
            get_kodi_json(method="Player.Open",
                          params='{"item": {"musicvideoid": %s}}' % (params.get("dbid")))
        elif info == 'playalbum':
            resolve_url(params.get("handle"))
            get_kodi_json(method="Player.Open",
                          params='{"item": {"albumid": %s}}' % (params.get("dbid")))
        elif info == 'playsong':
            resolve_url(params.get("handle"))
            get_kodi_json(method="Player.Open",
                          params='{"item": {"songid": %s}}' % (params.get("dbid")))
        elif info == "openinfodialog":
            resolve_url(params.get("handle"))
            dbid = xbmc.getInfoLabel("ListItem.DBID")
            if not dbid:
                dbid = xbmc.getInfoLabel("ListItem.Property(dbid)")
            if xbmc.getCondVisibility("Container.Content(movies)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=extendedinfo,dbid=%s,id=%s)" % (dbid, xbmc.getInfoLabel("ListItem.Property(id)")))
            elif xbmc.getCondVisibility("Container.Content(tvshows)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=extendedtvinfo,dbid=%s,id=%s)" % (dbid, xbmc.getInfoLabel("ListItem.Property(id)")))
            elif xbmc.getCondVisibility("Container.Content(seasons)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=seasoninfo,tvshow=%s,season=%s)" % (xbmc.getInfoLabel("ListItem.TVShowTitle"), xbmc.getInfoLabel("ListItem.Season")))
            elif xbmc.getCondVisibility("Container.Content(actors) | Container.Content(directors)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=extendedactorinfo,name=%s)" % (xbmc.getInfoLabel("ListItem.Label")))
        elif info == "ratedialog":
            resolve_url(params.get("handle"))
            if xbmc.getCondVisibility("Container.Content(movies)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=ratemedia,type=movie,dbid=%s,id=%s)" % (xbmc.getInfoLabel("ListItem.DBID"), xbmc.getInfoLabel("ListItem.Property(id)")))
            elif xbmc.getCondVisibility("Container.Content(tvshows)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=ratemedia,type=tv,dbid=%s,id=%s)" % (xbmc.getInfoLabel("ListItem.DBID"), xbmc.getInfoLabel("ListItem.Property(id)")))
            elif xbmc.getCondVisibility("Container.Content(episodes)"):
                xbmc.executebuiltin("RunScript(script.extendedinfo,info=ratemedia,type=episode,tvshow=%s,season=%s)" % (xbmc.getInfoLabel("ListItem.TVShowTitle"), xbmc.getInfoLabel("ListItem.Season")))
        elif info == 'youtubebrowser':
            resolve_url(params.get("handle"))
            wm.open_youtube_list(search_str=params.get("id", ""))
        elif info == 'extendedinfo':
            resolve_url(params.get("handle"))
            HOME.setProperty('infodialogs.active', "true")
            wm.open_movie_info(movie_id=params.get("id", ""),
                               dbid=params.get("dbid", None),
                               imdb_id=params.get("imdb_id", ""),
                               name=params.get("name", ""))
            HOME.clearProperty('infodialogs.active')
        elif info == 'extendedactorinfo':
            resolve_url(params.get("handle"))
            HOME.setProperty('infodialogs.active', "true")
            wm.open_actor_info(actor_id=params.get("id", ""),
                               name=params.get("name", ""))
            HOME.clearProperty('infodialogs.active')
        elif info == 'extendedtvinfo':
            resolve_url(params.get("handle"))
            HOME.setProperty('infodialogs.active', "true")
            wm.open_tvshow_info(tvshow_id=params.get("id", ""),
                                tvdb_id=params.get("tvdb_id", ""),
                                dbid=params.get("dbid", None),
                                imdb_id=params.get("imdb_id", ""),
                                name=params.get("name", ""))
            HOME.clearProperty('infodialogs.active')
        elif info == 'seasoninfo':
            resolve_url(params.get("handle"))
            HOME.setProperty('infodialogs.active', "true")
            wm.open_season_info(tvshow=params.get("tvshow"),
                                dbid=params.get("dbid"),
                                season=params.get("season"))
            HOME.clearProperty('infodialogs.active')
        elif info == 'extendedepisodeinfo':
            resolve_url(params.get("handle"))
            HOME.setProperty('infodialogs.active', "true")
            wm.open_episode_info(tvshow=params.get("tvshow"),
                                 tvshow_id=params.get("tvshow_id"),
                                 dbid=params.get("dbid"),
                                 episode=params.get("episode"),
                                 season=params.get("season"))
            HOME.clearProperty('infodialogs.active')
        elif info == 'albuminfo':
            resolve_url(params.get("handle"))
            if params.get("id", ""):
                album_details = get_album_details(params.get("id", ""))
                pass_dict_to_skin(album_details, params.get("prefix", ""))
        elif info == 'artistdetails':
            resolve_url(params.get("handle"))
            artist_details = get_artist_details(params["artistname"])
            pass_dict_to_skin(artist_details, params.get("prefix", ""))
        elif info == 'ratemedia':
            resolve_url(params.get("handle"))
            media_type = params.get("type", False)
            if media_type:
                if params.get("id") and params["id"]:
                    tmdb_id = params["id"]
                elif media_type == "movie":
                    tmdb_id = get_movie_tmdb_id(imdb_id=params.get("imdb_id", ""),
                                                dbid=params.get("dbid", ""),
                                                name=params.get("name", ""))
                elif media_type == "tv" and params["dbid"]:
                    tvdb_id = get_imdb_id_from_db(media_type="tvshow",
                                                  dbid=params["dbid"])
                    tmdb_id = get_show_tmdb_id(tvdb_id=tvdb_id)
                else:
                    return False
                set_rating_prompt(media_type=media_type,
                                  media_id=tmdb_id)
        elif info == 'updatexbmcdatabasewithartistmbidbg':
            resolve_url(params.get("handle"))
            set_mbids_for_artists(False, False)
        elif info == 'setfocus':
            resolve_url(params.get("handle"))
            xbmc.executebuiltin("SetFocus(22222)")
        elif info == 'playliststats':
            resolve_url(params.get("handle"))
            get_playlist_stats(params.get("id", ""))
        elif info == 'slideshow':
            resolve_url(params.get("handle"))
            window_id = xbmcgui.getCurrentwindow_id()
            window = xbmcgui.Window(window_id)
            # focusid = Window.getFocusId()
            itemlist = window.getFocus()
            num_items = itemlist.getSelectedPosition()
            for i in range(0, num_items):
                notify(item.getProperty("Image"))
        elif info == 'action':
            resolve_url(params.get("handle"))
            for builtin in params.get("id", "").split("$$"):
                xbmc.executebuiltin(builtin)
            return None
        elif info == 'selectautocomplete':
            resolve_url(params.get("handle"))
            try:
                window_id = xbmcgui.getCurrentWindowDialogId()
                window = xbmcgui.Window(window_id)
            except:
                return None
            get_kodi_json(method="Input.SendText",
                          params='{"text":"%s", "done":false}' % params.get("id"))
            # xbmc.executebuiltin("SendClick(103,32)")
            window.setFocusId(300)
        elif info == 'bounce':
            resolve_url(params.get("handle"))
            HOME.setProperty(params.get("name", ""), "True")
            xbmc.sleep(200)
            HOME.clearProperty(params.get("name", ""))
        elif info == "youtubevideo":
            resolve_url(params.get("handle"))
            xbmc.executebuiltin("Dialog.Close(all,true)")
            PLAYER.play_youtube_video(params.get("id", ""))
        elif info == 'playtrailer':
            resolve_url(params.get("handle"))
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            if params.get("id", ""):
                movie_id = params.get("id", "")
            elif int(params.get("dbid", -1)) > 0:
                movie_id = get_imdb_id_from_db(media_type="movie",
                                               dbid=params["dbid"])
            elif params.get("imdb_id", ""):
                movie_id = get_movie_tmdb_id(params.get("imdb_id", ""))
            else:
                movie_id = ""
            if movie_id:
                trailer = get_trailer(movie_id)
                xbmc.executebuiltin("Dialog.Close(busydialog)")
                xbmc.sleep(100)
                if trailer:
                    PLAYER.play_youtube_video(trailer)
                elif params.get("title"):
                    wm.open_youtube_list(search_str=params.get("title", ""))
                else:
                    xbmc.executebuiltin("Dialog.Close(busydialog)")
        elif info == 'updatexbmcdatabasewithartistmbid':
            resolve_url(params.get("handle"))
            set_mbids_for_artists(True, False)
        elif info == 'deletecache':
            resolve_url(params.get("handle"))
            HOME.clearProperties()
            import shutil
            for rel_path in os.listdir(ADDON_DATA_PATH):
                path = os.path.join(ADDON_DATA_PATH, rel_path)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                except Exception as e:
                    log(e)
            notify("Cache deleted")
        elif info == 'syncwatchlist':
            pass
        elif info == "widgetdialog":
            resolve_url(params.get("handle"))
            widget_selectdialog()
        listitems, prefix = data
        if params.get("handle"):
            xbmcplugin.addSortMethod(params.get("handle"), xbmcplugin.SORT_METHOD_TITLE)
            xbmcplugin.addSortMethod(params.get("handle"), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(params.get("handle"), xbmcplugin.SORT_METHOD_DURATION)
            if info.endswith("shows"):
                xbmcplugin.setContent(params.get("handle"), 'tvshows')
            else:
                xbmcplugin.setContent(params.get("handle"), 'movies')
        pass_list_to_skin(name=prefix,
                          data=listitems,
                          prefix=params.get("prefix", ""),
                          handle=params.get("handle", ""),
                          limit=params.get("limit", 20))


def resolve_url(handle):
    if handle:
        xbmcplugin.setResolvedUrl(handle=int(handle),
                                  succeeded=False,
                                  listitem=xbmcgui.ListItem())



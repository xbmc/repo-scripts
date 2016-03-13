# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details
from __future__ import unicode_literals
import time
import LastFM
import TheAudioDB as AudioDB
import TheMovieDB as tmdb
from Utils import *
import LocalDB
import YouTube
import Trakt
import RottenTomatoes
import KodiJson
from WindowManager import wm
import VideoPlayer


def start_info_actions(info, params):
    if "artistname" in params:
        params["artistname"] = params.get("artistname", "").split(" feat. ")[0].strip()
        params["artist_mbid"] = fetch_musicbrainz_id(params["artistname"])
    log(info)
    prettyprint(params)
    if "prefix" in params and not params["prefix"].endswith('.'):
        params["prefix"] = params["prefix"] + '.'

    # Audio
    if info == 'discography':
        discography = AudioDB.get_artist_discography(params["artistname"])
        if not discography:
            discography = LastFM.get_artist_albums(params.get("artist_mbid"))
        return discography
    elif info == 'mostlovedtracks':
        return AudioDB.get_most_loved_tracks(params["artistname"])
    elif info == 'trackdetails':
        return AudioDB.get_track_details(params.get("id", ""))
    elif info == 'topartists':
        return LastFM.get_top_artists()
    elif info == 'latestdbmovies':
        return LocalDB.local_db.get_movies('"sort": {"order": "descending", "method": "dateadded"}',
                                           params.get("limit", 10))
    elif info == 'randomdbmovies':
        return LocalDB.local_db.get_movies('"sort": {"method": "random"}', params.get("limit", 10))
    elif info == 'inprogressdbmovies':
        method = '"sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}'
        return LocalDB.local_db.get_movies(method, params.get("limit", 10))
#  RottenTomatoesMovies
    elif info == 'intheatermovies':
        return RottenTomatoes.get_movies("movies/in_theaters")
    elif info == 'boxofficemovies':
        return RottenTomatoes.get_movies("movies/box_office")
    elif info == 'openingmovies':
        return RottenTomatoes.get_movies("movies/opening")
    elif info == 'comingsoonmovies':
        return RottenTomatoes.get_movies("movies/upcoming")
    elif info == 'toprentalmovies':
        return RottenTomatoes.get_movies("dvds/top_rentals")
    elif info == 'currentdvdmovies':
        return RottenTomatoes.get_movies("dvds/current_releases")
    elif info == 'newdvdmovies':
        return RottenTomatoes.get_movies("dvds/new_releases")
    elif info == 'upcomingdvdmovies':
        return RottenTomatoes.get_movies("dvds/upcoming")
    #  The MovieDB
    elif info == 'incinemamovies':
        return tmdb.get_tmdb_movies("now_playing")
    elif info == 'upcomingmovies':
        return tmdb.get_tmdb_movies("upcoming")
    elif info == 'topratedmovies':
        return tmdb.get_tmdb_movies("top_rated")
    elif info == 'popularmovies':
        return tmdb.get_tmdb_movies("popular")
    elif info == 'ratedmovies':
        return tmdb.get_rated_media_items("movies")
    elif info == 'starredmovies':
        return tmdb.get_fav_items("movies")
    elif info == 'accountlists':
        account_lists = tmdb.handle_misc(tmdb.get_account_lists())
        for item in account_lists:
            item["directory"] = True
        return account_lists
    elif info == 'listmovies':
        return tmdb.get_movies_from_list(params["id"])
    elif info == 'airingtodaytvshows':
        return tmdb.get_tmdb_shows("airing_today")
    elif info == 'onairtvshows':
        return tmdb.get_tmdb_shows("on_the_air")
    elif info == 'topratedtvshows':
        return tmdb.get_tmdb_shows("top_rated")
    elif info == 'populartvshows':
        return tmdb.get_tmdb_shows("popular")
    elif info == 'ratedtvshows':
        return tmdb.get_rated_media_items("tv")
    elif info == 'starredtvshows':
        return tmdb.get_fav_items("tv")
    elif info == 'similarmovies':
        movie_id = params.get("id")
        if not movie_id:
            movie_id = tmdb.get_movie_tmdb_id(imdb_id=params.get("imdb_id"),
                                              dbid=params.get("dbid"))
        if movie_id:
            return tmdb.get_similar_movies(movie_id)
    elif info == 'similartvshows':
        tvshow_id = None
        dbid = params.get("dbid")
        name = params.get("name")
        tmdb_id = params.get("tmdb_id")
        tvdb_id = params.get("tvdb_id")
        imdb_id = params.get("imdb_id")
        if tmdb_id:
            tvshow_id = tmdb_id
        elif dbid and int(dbid) > 0:
            tvdb_id = LocalDB.local_db.get_imdb_id("tvshow", dbid)
            if tvdb_id:
                tvshow_id = tmdb.get_show_tmdb_id(tvdb_id)
        elif tvdb_id:
            tvshow_id = tmdb.get_show_tmdb_id(tvdb_id)
        elif imdb_id:
            tvshow_id = tmdb.get_show_tmdb_id(imdb_id, "imdb_id")
        elif name:
            tvshow_id = tmdb.search_media(media_name=name,
                                          year="",
                                          media_type="tv")
        if tvshow_id:
            return tmdb.get_similar_tvshows(tvshow_id)
    elif info == 'studio':
        if params.get("id"):
            return tmdb.get_company_data(params["id"])
        elif params.get("studio"):
            company_data = tmdb.search_company(params["studio"])
            if company_data:
                return tmdb.get_company_data(company_data[0]["id"])
    elif info == 'set':
        if params.get("dbid") and "show" not in params.get("type", ""):
            name = LocalDB.local_db.get_set_name(params["dbid"])
            if name:
                params["setid"] = tmdb.get_set_id(name)
        if params.get("setid"):
            set_data, _ = tmdb.get_set_movies(params["setid"])
            return set_data
    elif info == 'movielists':
        movie_id = params.get("id")
        if not movie_id:
            movie_id = tmdb.get_movie_tmdb_id(imdb_id=params.get("imdb_id"),
                                              dbid=params.get("dbid"))
        if movie_id:
            return tmdb.get_movie_lists(movie_id)
    elif info == 'keywords':
        movie_id = params.get("id")
        if not movie_id:
            movie_id = tmdb.get_movie_tmdb_id(imdb_id=params.get("imdb_id"),
                                              dbid=params.get("dbid"))
        if movie_id:
            return tmdb.get_keywords(movie_id)
    elif info == 'popularpeople':
        return tmdb.get_popular_actors()
    elif info == 'directormovies':
        director_info = tmdb.get_person_info(person_label=params.get("director"),
                                             skip_dialog=True)
        if director_info and director_info.get("id"):
            movies = tmdb.get_person_movies(director_info["id"])
            for item in movies:
                del item["credit_id"]
            return merge_dict_lists(movies, key="department")
    elif info == 'writermovies':
        writer = params.get("writer")
        if writer and not writer.split(" / ")[0] == params.get("director", "").split(" / ")[0]:
            writer_info = tmdb.get_person_info(person_label=writer,
                                               skip_dialog=True)
            if writer_info and writer_info.get("id"):
                movies = tmdb.get_person_movies(writer_info["id"])
                for item in movies:
                    del item["credit_id"]
                return merge_dict_lists(movies, key="department")
    elif info == 'traktsimilarmovies':
        if params.get("id") or params.get("dbid"):
            if params.get("dbid"):
                movie_id = LocalDB.local_db.get_imdb_id("movie", params["dbid"])
            else:
                movie_id = params["id"]
            return Trakt.get_similar("movie", movie_id)
    elif info == 'traktsimilartvshows':
        if params.get("id") or params.get("dbid"):
            if params.get("dbid"):
                if params.get("type") == "episode":
                    tvshow_id = LocalDB.local_db.get_tvshow_id_by_episode(params["dbid"])
                else:
                    tvshow_id = LocalDB.local_db.get_imdb_id(media_type="tvshow",
                                                             dbid=params["dbid"])
            else:
                tvshow_id = params["id"]
            return Trakt.get_similar("show", tvshow_id)
    elif info == 'airingepisodes':
        return Trakt.get_calendar_shows("shows")
    elif info == 'premiereepisodes':
        return Trakt.get_calendar_shows("premieres")
    elif info == 'trendingshows':
        return Trakt.get_trending_shows()
    elif info == 'trendingmovies':
        return Trakt.get_trending_movies()
    elif info == 'similarartistsinlibrary':
        return LocalDB.local_db.get_similar_artists(params.get("artist_mbid"))
    elif info == 'trackinfo':
        HOME.clearProperty('%sSummary' % params.get("prefix", ""))
        if params["artistname"] and params["trackname"]:
            track_info = LastFM.get_track_info(artist_name=params["artistname"],
                                               track=params["trackname"])
            HOME.setProperty('%sSummary' % params.get("prefix", ""), track_info["summary"])
    elif info == 'topartistsnearevents':
        artists = LocalDB.local_db.get_artists()
        import BandsInTown
        return BandsInTown.get_near_events(artists[0:49])
    elif info == 'youtubesearch':
        HOME.setProperty('%sSearchValue' % params.get("prefix", ""), params.get("id", ""))
        if params.get("id"):
            listitems = YouTube.search(search_str=params.get("id", ""),
                                       hd=params.get("hd", ""),
                                       orderby=params.get("orderby", "relevance"))
            return listitems.get("listitems", [])
    elif info == 'youtubeplaylist':
        return YouTube.get_playlist_videos(params.get("id", ""))
    elif info == 'youtubeusersearch':
        user_name = params.get("id")
        if user_name:
            playlists = YouTube.get_user_playlists(user_name)
            return YouTube.get_playlist_videos(playlists["uploads"])
    elif info == 'favourites':
        if params.get("id"):
            favs = get_favs_by_type(params["id"])
        else:
            favs = get_favs()
            HOME.setProperty('favourite.count', str(len(favs)))
            if favs:
                HOME.setProperty('favourite.1.name', favs[-1]["Label"])
        return favs
    elif info == 'similarlocalmovies' and "dbid" in params:
        return LocalDB.local_db.get_similar_movies(params["dbid"])
    elif info == 'iconpanel':
        return get_icon_panel(int(params["id"])), "IconPanel" + str(params["id"])
    elif info == 'weather':
        return get_weather_images()
    elif info == "sortletters":
        return get_sort_letters(params["path"], params.get("id", ""))

    # ACTIONS
    resolve_url(params.get("handle"))
    if info == 't9input':
        import T9Search
        dialog = T9Search.T9Search(call=None,
                                   start_value="")
        KodiJson.send_text(text=dialog.search_str)
    elif info in ['playmovie', 'playepisode', 'playmusicvideo', 'playalbum', 'playsong']:
        KodiJson.play_media(media_type=info.replace("play", ""),
                            dbid=params.get("dbid"),
                            resume=params.get("resume", "true"))
    elif info == "openinfodialog":
        if xbmc.getCondVisibility("System.HasModalDialog"):
            container_id = ""
        else:
            container_id = "Container(%s)" % get_infolabel("System.CurrentControlId")
        dbid = get_infolabel("%sListItem.DBID" % container_id)
        db_type = get_infolabel("%sListItem.DBType" % container_id)
        if not dbid:
            dbid = get_infolabel("%sListItem.Property(dbid)" % container_id)
        if db_type == "movie":
            params = {"dbid": dbid,
                      "id": get_infolabel("%sListItem.Property(id)" % container_id),
                      "name": get_infolabel("%sListItem.Title" % container_id)}
            start_info_actions("extendedinfo", params)
        elif db_type == "tvshow":
            params = {"dbid": dbid,
                      "tvdb_id": get_infolabel("%sListItem.Property(tvdb_id)" % container_id),
                      "id": get_infolabel("%sListItem.Property(id)" % container_id),
                      "name": get_infolabel("%sListItem.Title" % container_id)}
            start_info_actions("extendedtvinfo", params)
        elif db_type == "season":
            params = {"tvshow": get_infolabel("%sListItem.TVShowTitle" % container_id),
                      "season": get_infolabel("%sListItem.Season" % container_id)}
            start_info_actions("seasoninfo", params)
        elif db_type == "episode":
            params = {"tvshow": get_infolabel("%sListItem.TVShowTitle" % container_id),
                      "season": get_infolabel("%sListItem.Season" % container_id),
                      "episode": get_infolabel("%sListItem.Episode" % container_id)}
            start_info_actions("extendedepisodeinfo", params)
        elif db_type in ["actor", "director"]:
            params = {"name": get_infolabel("%sListItem.Label" % container_id)}
            start_info_actions("extendedactorinfo", params)
        else:
            notify("Error", "Could not find valid content type")
    elif info == "ratedialog":
        if xbmc.getCondVisibility("System.HasModalDialog"):
            container_id = ""
        else:
            container_id = "Container(%s)" % get_infolabel("System.CurrentControlId")
        dbid = get_infolabel("%sListItem.DBID" % container_id)
        db_type = get_infolabel("%sListItem.DBType" % container_id)
        if not dbid:
            dbid = get_infolabel("%sListItem.Property(dbid)" % container_id)
        if db_type == "movie":
            params = {"dbid": dbid,
                      "id": get_infolabel("%sListItem.Property(id)" % container_id),
                      "type": "movie"}
            start_info_actions("ratemedia", params)
        elif db_type == "tvshow":
            params = {"dbid": dbid,
                      "id": get_infolabel("%sListItem.Property(id)" % container_id),
                      "type": "tv"}
            start_info_actions("ratemedia", params)
        if db_type == "episode":
            params = {"tvshow": get_infolabel("%sListItem.TVShowTitle" % container_id),
                      "season": get_infolabel("%sListItem.Season" % container_id),
                      "type": "episode"}
            start_info_actions("ratemedia", params)
    elif info == 'youtubebrowser':
        wm.open_youtube_list(search_str=params.get("id", ""))
    elif info == 'moviedbbrowser':
        search_str = params.get("id", "")
        if not search_str and params.get("search"):
            result = xbmcgui.Dialog().input(heading=LANG(16017),
                                            type=xbmcgui.INPUT_ALPHANUM)
            if result and result > -1:
                search_str = result
            else:
                return None
        wm.open_video_list(search_str=search_str,
                           mode="search")
    elif info == 'extendedinfo':
        HOME.setProperty('infodialogs.active', "true")
        wm.open_movie_info(movie_id=params.get("id"),
                           dbid=params.get("dbid"),
                           imdb_id=params.get("imdb_id"),
                           name=params.get("name"))
        HOME.clearProperty('infodialogs.active')
    elif info == 'extendedactorinfo':
        HOME.setProperty('infodialogs.active', "true")
        wm.open_actor_info(actor_id=params.get("id"),
                           name=params.get("name"))
        HOME.clearProperty('infodialogs.active')
    elif info == 'extendedtvinfo':
        HOME.setProperty('infodialogs.active', "true")
        wm.open_tvshow_info(tmdb_id=params.get("id"),
                            tvdb_id=params.get("tvdb_id"),
                            dbid=params.get("dbid"),
                            imdb_id=params.get("imdb_id"),
                            name=params.get("name"))
        HOME.clearProperty('infodialogs.active')
    elif info == 'seasoninfo':
        HOME.setProperty('infodialogs.active', "true")
        wm.open_season_info(tvshow=params.get("tvshow"),
                            dbid=params.get("dbid"),
                            season=params.get("season"))
        HOME.clearProperty('infodialogs.active')
    elif info == 'extendedepisodeinfo':
        HOME.setProperty('infodialogs.active', "true")
        wm.open_episode_info(tvshow=params.get("tvshow"),
                             tvshow_id=params.get("tvshow_id"),
                             dbid=params.get("dbid"),
                             episode=params.get("episode"),
                             season=params.get("season"))
        HOME.clearProperty('infodialogs.active')
    elif info == 'albuminfo':
        if params.get("id"):
            album_details = AudioDB.get_album_details(params.get("id"))
            pass_dict_to_skin(album_details, params.get("prefix", ""))
    elif info == 'artistdetails':
        artist_details = AudioDB.get_artist_details(params["artistname"])
        pass_dict_to_skin(artist_details, params.get("prefix", ""))
    elif info == 'ratemedia':
        media_type = params.get("type")
        if media_type:
            if params.get("id"):
                tmdb_id = params["id"]
            elif media_type == "movie":
                tmdb_id = tmdb.get_movie_tmdb_id(imdb_id=params.get("imdb_id"),
                                                 dbid=params.get("dbid"),
                                                 name=params.get("name"))
            elif media_type == "tv" and params.get("dbid"):
                tvdb_id = LocalDB.local_db.get_imdb_id(media_type="tvshow",
                                                       dbid=params["dbid"])
                tmdb_id = tmdb.get_show_tmdb_id(tvdb_id=tvdb_id)
            else:
                return False
            tmdb.set_rating_prompt(media_type=media_type,
                                   media_id=tmdb_id,
                                   dbid=params.get("dbid"))
    elif info == 'playliststats':
        get_playlist_stats(params.get("id", ""))
    elif info == 'slideshow':
        window_id = xbmcgui.getCurrentwindow_id()
        window = xbmcgui.Window(window_id)
        # focusid = Window.getFocusId()
        num_items = window.getFocus().getSelectedPosition()
        for i in range(0, num_items):
            notify(item.getProperty("Image"))
    elif info == 'action':
        for builtin in params.get("id", "").split("$$"):
            xbmc.executebuiltin(builtin)
    elif info == "youtubevideo":
        xbmc.executebuiltin("Dialog.Close(all,true)")
        VideoPlayer.PLAYER.play_youtube_video(params.get("id", ""))
    elif info == 'playtrailer':
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        if params.get("id"):
            movie_id = params["id"]
        elif int(params.get("dbid", -1)) > 0:
            movie_id = LocalDB.local_db.get_imdb_id(media_type="movie",
                                                    dbid=params["dbid"])
        elif params.get("imdb_id"):
            movie_id = tmdb.get_movie_tmdb_id(params["imdb_id"])
        else:
            movie_id = ""
        if movie_id:
            trailer = tmdb.get_trailer(movie_id)
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            time.sleep(0.1)
            if trailer:
                VideoPlayer.PLAYER.play_youtube_video(trailer)
            elif params.get("title"):
                wm.open_youtube_list(search_str=params["title"])
            else:
                xbmc.executebuiltin("Dialog.Close(busydialog)")
    elif info == 'deletecache':
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
        widget_selectdialog()


def resolve_url(handle):
    if handle:
        xbmcplugin.setResolvedUrl(handle=int(handle),
                                  succeeded=False,
                                  listitem=xbmcgui.ListItem())



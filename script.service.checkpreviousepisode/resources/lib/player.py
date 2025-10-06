import json
import xbmc
import xbmcgui

from bossanova808.constants import TRANSLATE, HOME_WINDOW
from bossanova808.utilities import send_kodi_json, is_playback_paused
from bossanova808.logger import Logger
# noinspection PyPackages
from .store import Store


class KodiPlayer(xbmc.Player):
    """
    This class represents/monitors the Kodi video player
    """

    def __init__(self):
        super().__init__()
        Logger.debug('KodiPlayer __init__')

    def onAVStarted(self):
        """
        This does all the actual work...check if the previous episode exists, and if it has been watched.

        :return:
        """
        Logger.debug('onAVStarted')

        # Get active players
        command = json.dumps({
                "jsonrpc":"2.0",
                "id":1,
                "method":"Player.GetActivePlayers",
        })
        json_object = send_kodi_json("Get active players", command)

        active_players = json_object.get('result') or []
        video_players = [p for p in active_players if p.get('type') == 'video']
        if video_players:
            playerid = video_players[0].get('playerid')
            Logger.debug(f"Video player running with ID: {playerid}")
        else:
            Logger.debug("Player is not a video player")
            return

        command = json.dumps({
                "jsonrpc":"2.0",
                "id":1,
                "method":"Player.GetItem",
                "params":{"playerid":playerid},
        })
        json_object = send_kodi_json("Get playing item", command)

        item = json_object.get('result', {}).get('item', {})
        # Only do something if this is an episode of a TV show
        if item.get('type') == 'episode':

            episode_id = item.get('id') or item.get('episodeid')
            if not episode_id:
                Logger.warning("An episode is playing but no episode id was found; cannot check previous episode in the library.")
                return

            Logger.info(f"A TV show episode is playing (id: {episode_id}).")

            command = json.dumps({
                    "jsonrpc":"2.0",
                    "id":1,
                    "method":"VideoLibrary.GetEpisodeDetails",
                    "params":{
                            "episodeid":episode_id,
                            "properties":["tvshowid", "showtitle", "season", "episode", "resume"]
                    }
            })
            json_object = send_kodi_json("Get episode details", command)

            # Only do something if we can get the episode details from Kodi
            episodedetails = json_object.get('result', {}).get('episodedetails')
            if episodedetails:
                playing_tvshowid = episodedetails.get('tvshowid')
                playing_tvshow_title = episodedetails.get('showtitle')
                playing_season = episodedetails.get('season')
                playing_episode = episodedetails.get('episode')
                resume = episodedetails.get('resume') or {}
                resume_point = resume.get('position') or 0.0

                Logger.info(f'Playing - title: {playing_tvshow_title} , id: {playing_tvshowid} , season: {playing_season}, episode: {playing_episode}, resume: {resume_point}')

                # Is show set to be ignored?
                if Store.ignored_shows and playing_tvshowid in Store.ignored_shows:
                    Logger.info(f'Show {playing_tvshow_title} set to ignore, so allowing.')
                    return

                # Is the resume point is non-zero - then we've previously made a decision about playing this episode, so don't make the user make it again
                if resume_point > 0.0:
                    Logger.info(f"Show {playing_tvshow_title} Season {playing_season} Episode {playing_episode} has a non-zero resume point, so decision has been previously made to play this episode, so allowing.")
                    return

                # We ignore first episodes...
                if playing_episode > 1:

                    command = json.dumps({
                            "jsonrpc":"2.0",
                            "id":1,
                            "method":"VideoLibrary.GetEpisodes",
                            "params":{
                                    "tvshowid":playing_tvshowid,
                                    "season":playing_season,
                                    "properties":["episode", "playcount"]
                            }
                    })
                    json_object = send_kodi_json("Get episodes for season", command)

                    episodes = json_object.get('result', {}).get('episodes', [])

                    # Defaults
                    found = False
                    playcount = 0

                    if episodes:
                        for episode in episodes:
                            if episode.get('episode') == (playing_episode - 1):
                                playcount = (episode.get('playcount', 0) or 0)
                                found = True
                                break

                        Logger.info(f'Found previous episode: {found}, playcount: {playcount}, ignore if absent: {Store.ignore_if_episode_absent_from_library}')
                    else:
                        # No episodes returned by Kodi for this season
                        if Store.ignore_if_episode_absent_from_library:
                            Logger.info("Previous episode not found in library listing and user has opted to ignore; allowing.")
                            return
                        # Treat as 'not found' and continue to prompt/pause path
                        found = False
                        playcount = 0

                    # If we couldn't find the previous episode in the library,
                    # OR we have found the previous episode AND it is unwatched...
                    if not found or playcount == 0:

                        # Only trigger the pause if the player is actually playing as other addons may also have paused the player
                        if not is_playback_paused():
                            Logger.info("Prior episode not watched! -> pausing playback")
                            self.pause()

                        # Set a window property per Hitcher's request - https://forum.kodi.tv/showthread.php?tid=355464&pid=3191615#pid3191615
                        HOME_WINDOW.setProperty("CheckPreviousEpisode", "MissingPreviousEpisode")
                        try:
                            result = xbmcgui.Dialog().select(
                                    TRANSLATE(32020),
                                    [TRANSLATE(32021), TRANSLATE(32022), TRANSLATE(32023)],
                                    preselect=0
                            )
                        finally:
                            HOME_WINDOW.setProperty("CheckPreviousEpisode", "")

                        if result == -1:
                            Logger.info("User cancelled; resuming playback.")
                            if is_playback_paused():
                                self.pause()
                            return

                        if result == 2:
                            Logger.info(f"User has requested we ignore ({playing_tvshowid}) {playing_tvshow_title} from now on.")
                            Store.write_ignored_shows_to_config(playing_tvshow_title, playing_tvshowid)
                            # fall through to unpause

                        if result == 1 or result == 2:
                            if is_playback_paused():
                                Logger.info(f"Unpausing playback due to user input ({result})")
                                self.pause()
                        else:
                            Logger.info(f"Stopping playback due to user input ({result})")
                            self.stop()

                            if Store.force_browse:
                                Logger.info("Force browsing to show/season, as per user configuration")
                                # Special case is the user wants to go to the All Seasons view
                                if Store.force_all_seasons:
                                    playing_season = -1

                                command = json.dumps({
                                        "jsonrpc":"2.0",
                                        "id":1,
                                        "method":"GUI.ActivateWindow",
                                        "params":{
                                                "window":"videos",
                                                "parameters":[f'videodb://tvshows/titles/{playing_tvshowid}/{playing_season}'],
                                        }
                                })
                                send_kodi_json(f'Browse to {playing_tvshow_title}', command)

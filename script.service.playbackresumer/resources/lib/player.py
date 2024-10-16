from random import randint

from bossanova808.logger import Logger
from bossanova808.notify import Notify
from bossanova808.utilities import *

# noinspection PyPackages
from .store import Store
import json
import time
import os
import xbmc


class KodiPlayer(xbmc.Player):
    """
    This class represents/monitors the Kodi video player
    """

    def __init__(self, *args):
        xbmc.Player.__init__(self)
        Logger.debug('KodiPlayer __init__')

    def onPlayBackPaused(self):
        Logger.info('onPlayBackPaused')
        Store.paused_time = time.time()
        Logger.info(f'Playback paused at: {Store.paused_time}')

    def onPlayBackEnded(self):  # video ended normally (user didn't stop it)
        Logger.info("onPlayBackEnded")
        self.update_resume_point(-1)
        self.autoplay_random_if_enabled()

    def onPlayBackStopped(self):
        Logger.info("onPlayBackStopped")
        self.update_resume_point(-2)

    def onPlayBackSeek(self, time, seekOffset):
        Logger.info(f'onPlayBackSeek time {time}, seekOffset {seekOffset}')
        try:
            self.update_resume_point(self.getTime())
        except RuntimeError:
            Logger.warning("Could not get playing time - seeked past end?  Clearing resume point.")
            self.update_resume_point(0)
            pass

    def onPlayBackSeekChapter(self, chapter):
        Logger.info(f'onPlayBackSeekChapter chapter: {chapter}')
        try:
            self.update_resume_point(self.getTime())
        except RuntimeError:
            Logger.warning("Could not get playing time - seeked past end?  Clearing resume point.")
            self.update_resume_point(0)
            pass

    def onAVStarted(self):
        Logger.info("onAVStarted")

        # Clean up - get rid of any data about any files previously played
        Store.clear_old_play_details()

        if not self.isPlayingVideo():
            Logger.info("Not playing a video - skipping: " + self.getPlayingFile())
            return

        xbmc.sleep(1500)  # give it a bit to start playing and let the stopped method finish

        Store.update_current_playing_file_path(self.getPlayingFile())
        Store.length_of_currently_playing_file = self.getTotalTime()

        while self.isPlaying() and not Store.kodi_event_monitor.abortRequested():

            try:
                self.update_resume_point(self.getTime())
            except RuntimeError:
                Logger.error('Could not get current playback time from player')

            for i in range(0, Store.save_interval_seconds):
                # Shutting down or not playing video anymore...stop handling playback
                if Store.kodi_event_monitor.abortRequested() or not self.isPlaying():
                    return
                # Otherwise sleep 1 second & loop
                xbmc.sleep(1000)

    def update_resume_point(self, seconds):
        """
        This is where the work is done - stores a new resume point in the Kodi library for the currently playing file

        :param: seconds: the time to update the resume point to.  @todo add notes on -1, -2 etc here!
        :param: Store.library_id: the Kodi library id of the currently playing file
        :return: None
        """

        # cast to int just to be sure
        seconds = int(seconds)

        # short circuit if we haven't got a record of the file that is currently playing
        if not Store.currently_playing_file_path:
            Logger.info("No valid currently_playing_file_path found - therefore not setting resume point")
            return

        # -1 indicates that the video has stopped playing
        if seconds < 0:

            # check if Kodi is actually shutting down
            # (abortRequested happens slightly after onPlayBackStopped, hence the sleep/wait/check)
            for i in range(0, 30):

                if Store.kodi_event_monitor.abortRequested():
                    Logger.info("Kodi is shutting down, so Kodi will save resume point")
                    # Kodi is shutting down while playing a video.
                    return

                if self.isPlaying():
                    # a new video has started playing. Kodi is not actually shutting down
                    break

                xbmc.sleep(100)

        # Short circuit if current time < Kodi's ignoresecondsatstart setting
        if 0 < seconds < Store.ignore_seconds_at_start:
            Logger.info(f'Not updating resume point as current time ({seconds}) is below Kodi\'s ignoresecondsatstart'
                        f' setting of {Store.ignore_seconds_at_start}')
            return

        # Short circuits

        # Weird library ID
        if Store.library_id and Store.library_id < 0:
            Logger.info(f"No/invalid library id ({Store.library_id}) for {Store.currently_playing_file_path}")
            return
        # Kodi doing its normal stopping thing
        if seconds == -2:
            Logger.info("Not updating Kodi native resume point because the file was stopped normally, so Kodi should do it itself")
            return
        # At this point if seconds is < 0, it is -1 meaning end of file/clear resume point
        if seconds < 0:
            # zero indicates to JSON-RPC to remove the resume point
            seconds = 0

        # if current time > Kodi's ignorepercentatend setting
        percent_played = int((seconds * 100) / Store.length_of_currently_playing_file)
        if percent_played > (100 - Store.ignore_percent_at_end):
            Logger.info(f'Not updating resume point as current percent played ({percent_played}) is above Kodi\'s ignorepercentatend'
                        f' setting of {Store.ignore_percent_at_end}')
            return

        # OK, BELOW HERE, we're probably going to set a resume point

        # First update the resume point in the tracker file for later retrieval if needed
        Logger.info(f'Setting custom resume seconds to {seconds}')
        with open(Store.file_to_store_resume_point, 'w') as f:
            f.write(str(seconds))

        # Log what we are doing
        if seconds == 0:
            Logger.info(f'Removing resume point for: {Store.currently_playing_file_path}, type: {Store.type_of_video}, library id: {Store.library_id}')
        else:
            Logger.info(f'Setting resume point for: {Store.currently_playing_file_path}, type: {Store.type_of_video}, library id: {Store.library_id}, to: {seconds} seconds')

        # Determine the JSON-RPC setFooDetails method to use and what the library id name is based of the type of video
        id_name = None
        if Store.type_of_video == 'episode':
            method = 'VideoLibrary.SetEpisodeDetails'
            get_method = 'VideoLibrary.GetEpisodeDetails'
            id_name = 'episodeid'
        elif Store.type_of_video == 'movie':
            method = 'VideoLibrary.SetMovieDetails'
            get_method = 'VideoLibrary.GetMovieDetails'
            id_name = 'movieid'
        elif Store.type_of_video == 'musicvideo':
            method = 'VideoLibrary.SetMusicVideoDetails'
            get_method = 'VideoLibrary.GetMusicVideoDetails'
            id_name = 'musicvideoid'
        else:
            Logger.info(f'Did not recognise type of video [{Store.type_of_video}] - assume non-library video')
            method = 'Files.SetFileDetails'
            get_method = 'Files.GetFileDetails'

        json_dict = {
            "jsonrpc": "2.0",
            "id": "setResumePoint",
            "method": method,
        }
        if id_name:
            params = {
                    id_name: Store.library_id,
                    "resume": {
                        "position": seconds,
                        "total": Store.length_of_currently_playing_file
                    }
            }
        else:
            params = {
                "file": Store.currently_playing_file_path,
                "media": "video",
                "resume": {
                    "position": seconds,
                    "total": Store.length_of_currently_playing_file
                }
            }

        json_dict['params'] = params
        query = json.dumps(json_dict)
        send_kodi_json(f'Set resume point for: {Store.currently_playing_file_path}, type: {Store.type_of_video}, id: {Store.library_id}, to: {seconds} seconds, total: {Store.length_of_currently_playing_file}', query)

        # For debugging - let's retrieve and log the current resume point to check it was actually set as intended...
        json_dict = {
            "jsonrpc": "2.0",
            "id": "getResumePoint",
            "method": get_method,
        }
        if id_name:
            params = {
                id_name: Store.library_id,
                "properties": ["resume"],
            }
        else:
            params = {
                "file": Store.currently_playing_file_path,
                "media": "video",
                "properties": ["resume"],
            }

        json_dict['params'] = params
        query = json.dumps(json_dict)
        send_kodi_json(f'Check new resume point & total for: {Store.currently_playing_file_path}, type: {Store.type_of_video}, id: {Store.library_id}', query)

    def resume_if_was_playing(self):
        """
        Automatically resume a video after a crash, if one was playing...

        :return:
        """

        if Store.resume_on_startup \
                and os.path.exists(Store.file_to_store_resume_point) \
                and os.path.exists(Store.file_to_store_last_played):

            with open(Store.file_to_store_resume_point, 'r') as f:
                try:
                    resume_point = float(f.read())
                except Exception:
                    Logger.error("Error reading resume point from file, therefore not resuming.")
                    return

            # neg 1 means the video wasn't playing when Kodi ended
            if resume_point < 0:
                Logger.info("Not resuming playback because nothing was playing when Kodi last closed")
                return False

            with open(Store.file_to_store_last_played, 'r') as f:
                full_path = f.read()

            str_timestamp = '%d:%02d' % (resume_point / 60, resume_point % 60)
            Logger.info(f'Will resume playback at {str_timestamp} of {full_path}')

            self.play(full_path)

            # wait up to 10 secs for the video to start playing before we try to seek
            for i in range(0, 1000):
                if not self.isPlayingVideo() and not Store.kodi_event_monitor.abortRequested():
                    xbmc.sleep(100)
                else:
                    Notify.info(f'Resuming playback at {str_timestamp}')
                    self.seekTime(resume_point)
                    return True

        return False

    def get_random_library_video(self):
        """
        Get a random video from the library for playback

        :return:
        """

        # Short circuit if library is empty
        if not Store.video_types_in_library['episodes'] \
                and not Store.video_types_in_library['movies'] \
                and not Store.video_types_in_library['musicvideos']:
            Logger.warning('No episodes, movies, or music videos exist in the Kodi library. Cannot autoplay a random video.')
            return

        random_int = randint(0, 2)
        if random_int == 0:
            result_type = 'episodes'
            method = "GetEpisodes"
        elif random_int == 1:
            result_type = 'movies'
            method = "GetMovies"
        elif random_int == 2:
            result_type = 'musicvideos'
            method = "GetMusicVideos"

        # if the randomly chosen type is not in the library, keep randomly trying until we get
        # a type that is in the library...
        if not Store.video_types_in_library[result_type]:
            return self.get_random_library_video()  # get a different one

        Logger.info(f'Getting a random video from: {result_type}')

        query = {
                "jsonrpc": "2.0",
                "id": "randomLibraryVideo",
                "method": "VideoLibrary." + method,
                "params": {
                    "limits": {
                        "end": 1
                    },
                    "sort": {
                        "method": "random"
                    },
                    "properties": [
                        "file"
                    ]
                }
        }

        Logger.info(f'Executing JSON-RPC: {json.dumps(query)}')
        json_response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
        Logger.info(f'JSON-RPC VideoLibrary.{method} response: {json.dumps(json_response)}')

        # found a video!
        if json_response['result']['limits']['total'] > 0:
            Store.video_types_in_library[result_type] = True
            return json_response['result'][result_type][0]['file']
        # no videos of this type
        else:
            Logger.info("There are no " + result_type + " in the library")
            Store.video_types_in_library[result_type] = False
            return self.get_random_library_video()

    def autoplay_random_if_enabled(self):
        """
        Play a random video, if the setting is enabled
        :return:
        """

        if Store.autoplay_random:

            Logger.info("Autoplay random is enabled in addon settings, so will play a new random video now.")

            video_playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

            # make sure the current playlist has finished completely
            if not self.isPlayingVideo() \
                    and (video_playlist.getposition() == -1 or video_playlist.getposition() == video_playlist.size()):
                full_path = self.get_random_library_video()
                Logger.info("Auto-playing next random video because nothing is playing and playlist is empty: " + full_path)
                self.play(full_path)
                Notify.info(f'Auto-playing random video: {full_path}')
            else:
                Logger.info(f'Not auto-playing random as playlist not empty or something is playing.')
                Logger.info(f'Current playlist position: {video_playlist.getposition()}, playlist size: {video_playlist.size()}')

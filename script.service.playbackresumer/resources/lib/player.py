from random import randint

from bossanova808.logger import Logger
from bossanova808.notify import Notify
from bossanova808.utilities import send_kodi_json

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

    # noinspection PyUnusedLocal
    def __init__(self, *_args):
        """
        Initialize the KodiPlayer instance and bind it to xbmc.Player.
        
        Parameters:
            *_args: Optional positional arguments accepted for compatibility; any values passed are ignored.
        """
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
        """
        Handle the playback-stopped event and mark the current resume point as managed by Kodi.
        
        When playback stops, record a sentinel resume value indicating that Kodi should retain or handle the resume point (internal sentinel -2).
        """
        Logger.info("onPlayBackStopped")
        self.update_resume_point(-2)

    def onPlayBackSeek(self, time_to_seek, seek_offset):
        """
        Handle a user-initiated seek during playback and update the stored resume point.
        
        When a seek occurs, attempt to record the current playback time as the resume point.
        If reading the current playback time raises a RuntimeError (e.g., seeked past the end),
        clear the stored resume point.
        
        Parameters:
            time_to_seek (float): The target time position of the seek (seconds).
            seek_offset (float): The relative offset of the seek from the previous position (seconds).
        """
        Logger.info(f'onPlayBackSeek time {time_to_seek}, seekOffset {seek_offset}')
        try:
            self.update_resume_point(self.getTime())
        except RuntimeError:
            Logger.warning("Could not get playing time - seeked past end?  Clearing resume point.")
            self.update_resume_point(0)

    def onPlayBackSeekChapter(self, chapter):
        Logger.info(f'onPlayBackSeekChapter chapter: {chapter}')
        try:
            self.update_resume_point(self.getTime())
        except RuntimeError:
            Logger.warning("Could not get playing time - seeked past end?  Clearing resume point.")
            self.update_resume_point(0)

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

            # Skip (don't block on) this iteration's save while a startup resume seek is still
            # being verified (see resume_if_was_playing()), so it can't overwrite the real resume
            # point with a near-zero value - the next iteration picks it up as normal.
            if not Store.currently_resuming:
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

        :param seconds: target resume time in seconds.
                         Special values:
                           -2 -> stopped normally, let Kodi persist native resume (no-op here)
                           -1 -> end-of-file, clear resume point (sends 0)
                            0 -> explicit clear resume point
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
        # if current time > Kodi's ignorepercentatend setting
        total = Store.length_of_currently_playing_file
        if total:
            percent_played = int((seconds * 100) / total)
            if percent_played > (100 - Store.ignore_percent_at_end):
                Logger.info(f"Not updating resume point as current percent played ({percent_played}) is above Kodi's ignorepercentatend setting of {Store.ignore_percent_at_end}")
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
        Attempt to resume playback after a previous shutdown if resuming is enabled and saved resume data exist.

        If configured and valid resume data are present, the player will start the saved file and seek to the
        stored resume time; on any failure or if no resume data are applicable, no playback is resumed. Verifies
        the seek actually landed, retrying a few times if not, since a seek requested too soon after playback
        starts can be silently ignored by Kodi. The whole attempt is wrapped so a player exception (e.g. playback
        stopping mid-seek) can never crash the service.

        Returns:
            True if a resume was attempted (playback was started), False otherwise.
        """

        Logger.info("resume_if_was_playing: checking whether to attempt a resume on startup")

        if not Store.resume_on_startup:
            Logger.info("resume_if_was_playing: 'resume on startup' setting is disabled - not attempting resume")
            return False

        if not os.path.exists(Store.file_to_store_resume_point):
            Logger.info(f"resume_if_was_playing: resume point file not found ({Store.file_to_store_resume_point}) - not attempting resume")
            return False

        if not os.path.exists(Store.file_to_store_last_played):
            Logger.info(f"resume_if_was_playing: last played file not found ({Store.file_to_store_last_played}) - not attempting resume")
            return False

        with open(Store.file_to_store_resume_point, 'r') as f:
            raw_resume_point = f.read()

        try:
            resume_point = float(raw_resume_point)
        except Exception:
            Logger.error(f"resume_if_was_playing: error parsing resume point [{raw_resume_point}] from file, therefore not resuming.")
            return False

        # neg 1 means the video wasn't playing when Kodi ended
        if resume_point < 0:
            Logger.info(f"resume_if_was_playing: stored resume point is {resume_point} - nothing was playing when Kodi last closed, not resuming")
            return False

        with open(Store.file_to_store_last_played, 'r') as f:
            full_path = f.read()

        if not full_path:
            Logger.info("resume_if_was_playing: no last-played file found; skipping resume.")
            return False

        mins, secs = divmod(int(resume_point), 60)
        str_timestamp = f'{mins}:{secs:02d}'

        Logger.info(f"resume_if_was_playing: will attempt to resume [{full_path}] at {str_timestamp} ({resume_point} seconds)")

        # Flag that a resume attempt is in progress. onAVStarted's periodic save loop checks this
        # and skips its save (non-blocking) so it doesn't overwrite the real resume data with a
        # near-zero value while we're still trying to establish/verify the seek below.
        Store.currently_resuming = True

        try:
            self.play(full_path)

            started = False
            for i in range(100):
                if Store.kodi_event_monitor.abortRequested():
                    Logger.info("resume_if_was_playing: abort requested while waiting for playback to start - giving up on resume")
                    return False
                if self.isPlayingVideo():
                    started = True
                    break
                xbmc.sleep(100)

            if not started:
                Logger.warning("resume_if_was_playing: timed out (10s) waiting for isPlayingVideo() to become True - giving up on resume seek")
                return False

            Notify.info(f'Resuming playback at {str_timestamp}')

            # Attempt the seek, then verify it actually landed - retrying a few times if not, since a
            # seek requested too soon after playback starts can be silently ignored by Kodi. Every
            # player call here is guarded: if playback has stopped/aborted underneath us (e.g. the
            # device is shutting down), we log and bail out cleanly rather than raising.
            seek_succeeded = False
            attempt = 0
            for attempt in range(1, 6):

                if Store.kodi_event_monitor.abortRequested() or not self.isPlaying():
                    Logger.info(f"resume_if_was_playing: playback stopped/abort requested before seek attempt {attempt} - stopping verification")
                    break

                try:
                    self.seekTime(resume_point)
                except RuntimeError as e:
                    Logger.warning(f"resume_if_was_playing: seekTime() raised RuntimeError on attempt {attempt} ({e}) - playback has likely stopped, giving up on resume seek")
                    break

                xbmc.sleep(500)

                if Store.kodi_event_monitor.abortRequested() or not self.isPlaying():
                    Logger.info("resume_if_was_playing: playback stopped/abort requested while verifying seek - stopping verification")
                    break

                try:
                    post_seek_time = self.getTime()
                except RuntimeError:
                    Logger.warning("resume_if_was_playing: could not read player time while verifying seek (RuntimeError) - playback has likely stopped")
                    break

                if post_seek_time is not None and abs(post_seek_time - resume_point) < 5:
                    seek_succeeded = True
                    break

                Logger.warning(f"resume_if_was_playing: seek attempt {attempt} does not appear to have landed (expected ~{resume_point}s, got {post_seek_time}s) - retrying")

            if not seek_succeeded:
                Logger.warning(f"resume_if_was_playing: could NOT confirm the seek to {resume_point}s landed after {attempt} attempt(s) - "
                                f"playback may have started from 0:00 despite the notification, or playback stopped before the seek could be verified.")
            else:
                Logger.info("resume_if_was_playing: resume seek confirmed successful")

            return True

        except Exception as e:
            # Belt and braces: nothing in the resume path should ever be allowed to raise up out
            # of this function and crash the service - that leaves the whole addon not running for
            # the rest of the session, which is far worse than a failed resume.
            Logger.error(f"resume_if_was_playing: unexpected exception during resume attempt - giving up on resume, but continuing normally: {e}")
            return False

        finally:
            Store.currently_resuming = False

    def get_random_library_video(self):
        """
        Selects a random video file path from the Kodi library.
        
        Chooses among episodes, movies, and music videos and returns the file path of a randomly selected item if one exists. Updates Store.video_types_in_library to reflect whether a given type is present. If the library contains no eligible videos, no selection is made.
        
        Returns:
            str: File path of the selected video.
            False: If no episodes, movies, or music videos exist in the library.
        """

        # Short circuit if library is empty
        if not Store.video_types_in_library['episodes'] \
                and not Store.video_types_in_library['movies'] \
                and not Store.video_types_in_library['musicvideos']:
            Logger.warning('No episodes, movies, or music videos exist in the Kodi library. Cannot autoplay a random video.')
            return False

        random_int = randint(0, 2)
        result_type = None
        method = None
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
                if not full_path:
                    Logger.info("No random video available to autoplay.")
                    return
                Logger.info(f"Auto-playing next random video because nothing is playing and playlist is empty: {full_path}")
                self.play(full_path)
                Notify.info(f'Auto-playing random video: {full_path}')
            else:
                Logger.info(f'Not auto-playing random as playlist not empty or something is playing.')
                Logger.info(f'Current playlist position: {video_playlist.getposition()}, playlist size: {video_playlist.size()}')

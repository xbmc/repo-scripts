from random import randint

from bossanova808.logger import Logger
from bossanova808.notify import Notify
from bossanova808.playback import Playback
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

        file = self.getPlayingFile()
        if Store.is_excluded(file):
            Logger.info("Skipping excluded filepath: " + file)
            return

        Store.current_playback = Playback()
        Store.current_playback.update_playback_details(file, self.getPlayingItem())
        Logger.info(f'Kodi type: {Store.current_playback.type}, dbid: {Store.current_playback.dbid}')

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

        :param seconds: target resume time in seconds.
                         Special values:
                           -2 -> stopped normally, let Kodi persist native resume (no-op here)
                           -1 -> end-of-file, clear resume point (sends 0)
                            0 -> explicit clear resume point
        :param: Store.current_playback.dbid: the Kodi library id of the currently playing file, if any
        :return: None
        """

        # cast to int just to be sure
        seconds = int(seconds)

        playback = Store.current_playback

        # short circuit if we haven't got a record of the file that is currently playing
        if not playback or not playback.file:
            Logger.info("No current playback recorded - therefore not setting resume point")
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

        # Short circuit if current time < Kodi's ignoresecondsatstart setting - doesn't apply to
        # live TV, which has no meaningful position to wait out; we want to remember the channel
        # that was on immediately, not after some seconds of viewing
        if playback.source != "pvr_live" and 0 < seconds < Store.ignore_seconds_at_start:
            Logger.info(f'Not updating resume point as current time ({seconds}) is below Kodi\'s ignoresecondsatstart'
                        f' setting of {Store.ignore_seconds_at_start}')
            return

        # Short circuits

        # Kodi doing its normal stopping thing
        if seconds == -2:
            Logger.info("Not updating Kodi native resume point because the file was stopped normally, so Kodi should do it itself")
            return
        # At this point if seconds is < 0, it is -1 meaning end of file/clear resume point
        if seconds < 0:
            # zero indicates to JSON-RPC to remove the resume point
            seconds = 0

        # if current time > Kodi's ignorepercentatend setting
        total = playback.totaltime
        if total:
            percent_played = int((seconds * 100) / total)
            if percent_played > (100 - Store.ignore_percent_at_end):
                Logger.info(f"Not updating resume point as current percent played ({percent_played}) is above Kodi's ignorepercentatend setting of {Store.ignore_percent_at_end}")
                return

        # OK, BELOW HERE, we're probably going to set a resume point

        # First update our own tracker file (used to resume on next startup) with the full
        # playback details, not just the resume point - so we can rebuild a proper ListItem
        # (title, art, episode/season etc) for Kodi to display when resuming after a restart.
        Logger.info(f'Setting custom resume seconds to {seconds}')
        playback.resumetime = seconds
        with open(Store.file_to_store_playback, 'w', encoding='utf-8') as f:
            f.write(playback.toJson())

        # Neither PVR source accepts a library/file resume point via JSON-RPC - Files.SetFileDetails
        # rejects pvr:// paths outright ("Invalid params"), and there's no VideoLibrary.SetXDetails
        # equivalent for PVR recordings. Our own tracker file above is what resume_if_was_playing()
        # actually uses, so this JSON-RPC step is only meaningful for library/file items.
        if playback.source in ("pvr_live", "pvr_recording"):
            return

        # Log what we are doing
        if seconds == 0:
            Logger.info(f'Removing resume point for: {playback.file}, type: {playback.type}, dbid: {playback.dbid}')
        else:
            Logger.info(f'Setting resume point for: {playback.file}, type: {playback.type}, dbid: {playback.dbid}, to: {seconds} seconds')

        # Determine the JSON-RPC setFooDetails method to use and what the library id name is based of the type of video
        id_name = None
        if playback.dbid and playback.type == 'episode':
            method = 'VideoLibrary.SetEpisodeDetails'
            get_method = 'VideoLibrary.GetEpisodeDetails'
            id_name = 'episodeid'
        elif playback.dbid and playback.type == 'movie':
            method = 'VideoLibrary.SetMovieDetails'
            get_method = 'VideoLibrary.GetMovieDetails'
            id_name = 'movieid'
        elif playback.dbid and playback.type == 'musicvideo':
            method = 'VideoLibrary.SetMusicVideoDetails'
            get_method = 'VideoLibrary.GetMusicVideoDetails'
            id_name = 'musicvideoid'
        else:
            Logger.info(f'Not a recognised library item (type [{playback.type}], dbid [{playback.dbid}]) - treating as a non-library video')
            method = 'Files.SetFileDetails'
            get_method = 'Files.GetFileDetails'

        json_dict = {
            "jsonrpc": "2.0",
            "id": "setResumePoint",
            "method": method,
        }
        if id_name:
            params = {
                    id_name: playback.dbid,
                    "resume": {
                        "position": seconds,
                        "total": total
                    }
            }
        else:
            params = {
                "file": playback.file,
                "media": "video",
                "resume": {
                    "position": seconds,
                    "total": total
                }
            }

        json_dict['params'] = params
        query = json.dumps(json_dict)
        send_kodi_json(f'Set resume point for: {playback.file}, type: {playback.type}, dbid: {playback.dbid}, to: {seconds} seconds, total: {total}', query)

        # For debugging - let's retrieve and log the current resume point to check it was actually set as intended...
        json_dict = {
            "jsonrpc": "2.0",
            "id": "getResumePoint",
            "method": get_method,
        }
        if id_name:
            params = {
                id_name: playback.dbid,
                "properties": ["resume"],
            }
        else:
            params = {
                "file": playback.file,
                "media": "video",
                "properties": ["resume"],
            }

        json_dict['params'] = params
        query = json.dumps(json_dict)
        send_kodi_json(f'Check new resume point & total for: {playback.file}, type: {playback.type}, dbid: {playback.dbid}', query)

    def resume_if_was_playing(self):
        """
        Attempt to resume playback after a previous shutdown if resuming is enabled and saved resume data exist.

        If configured and valid resume data are present, rebuilds a proper ListItem (title, artwork,
        episode/season etc) from the persisted playback details and starts it with a StartOffset
        property set to the saved resume point - Kodi applies this directly when opening the file, so
        there's no separate seek call needed (and so nothing to race against onAVStarted's own periodic
        save loop). PVR is a special case throughout - both live TV and recordings are started via the
        PlayMedia(...) builtin rather than Player.play(), since a directly-resolved ListItem never
        routes through Kodi's PVR-aware CPVRGUIActionsPlayback playback path, so Kodi never activates
        a real PVR session (no channel-up/down, no OSD, etc) even though basic playback "works" -
        confirmed still required on current Kodi, not just an old-Kodi workaround (see
        https://forum.kodi.tv/showthread.php?tid=381623, posts #17-18). Specifically:
        - Live TV has no seek position at all - "resuming" just means retuning the channel, via
          PlayMedia(path) with no resume keyword.
        - PVR recordings do have a real position, but a manually-set StartOffset causes a black screen
          rather than actually resuming them. Kodi's own PVR manager already tracks each recording's
          resume position itself - the PVR client addon persists it to the backend automatically as
          part of ordinary playback, regardless of what started that playback - which is why the
          native "Resume from..." prompt just works. The reliable way to use that tracked position from
          an addon is PlayMedia(path, resume) - the same builtin Kodi's own resume prompt uses under
          the hood - rather than setting a position of our own.
        The whole attempt is wrapped so a player exception can never crash the service.

        Returns:
            True if a resume was attempted (playback was started), False otherwise.
        """

        Logger.info("resume_if_was_playing: checking whether to attempt a resume on startup")

        if not Store.resume_on_startup:
            Logger.info("resume_if_was_playing: 'resume on startup' setting is disabled - not attempting resume")
            return False

        if not os.path.exists(Store.file_to_store_playback):
            Logger.info(f"resume_if_was_playing: no stored playback found ({Store.file_to_store_playback}) - not attempting resume")
            return False

        try:
            with open(Store.file_to_store_playback, 'r', encoding='utf-8') as f:
                playback = Playback.from_dict(json.load(f))
        except (OSError, ValueError, TypeError) as e:
            Logger.error(f"resume_if_was_playing: error reading/parsing stored playback, therefore not resuming: {e}")
            return False

        if not playback.file:
            Logger.info("resume_if_was_playing: stored playback has no file path - not attempting resume")
            return False

        # Live TV has no seek position to resume to at all - "resuming" just means retuning the
        # channel, so it's not gated on resumetime the way a video's position is. PVR recordings do
        # have a real resume position and are still gated on resumetime (to decide whether this is
        # worth resuming at all), but the actual position used comes from Kodi/NextPVR's own tracking
        # (via PlayMedia resume, see docstring) rather than our own - our locally-observed resumetime
        # is only used here as a "was this being watched" signal.
        is_live = playback.source == "pvr_live"
        is_recording = playback.source == "pvr_recording"
        is_pvr = is_live or is_recording
        str_timestamp = None
        if is_live:
            Logger.info(f"resume_if_was_playing: will attempt to resume live channel [{playback.pluginlabel}]")
        else:
            if not playback.resumetime or playback.resumetime < Store.ignore_seconds_at_start:
                Logger.info(f"resume_if_was_playing: stored resume point is {playback.resumetime} - nothing meaningful to resume, not resuming")
                return False
            str_timestamp = playback.resume_timestamp
            if is_recording:
                Logger.info(f"resume_if_was_playing: will attempt to resume [{playback.pluginlabel}] (last seen around {str_timestamp}) "
                            f"via Kodi's own PVR resume tracking")
            else:
                Logger.info(f"resume_if_was_playing: will attempt to resume [{playback.pluginlabel}] at {str_timestamp} ({playback.resumetime} seconds)")

        try:
            # PVR items (live or recorded) are started via PlayMedia, not Player.play() - see
            # docstring above - so no ListItem is built/used for them at all; Kodi resolves its own
            # item (with its own metadata) for both. A manually-set StartOffset works fine for
            # ordinary library/file playback, so that's still built and used as before.
            list_item = None if is_pvr else playback.create_list_item_from_playback()
            if list_item is not None:
                list_item.setProperty('StartOffset', str(playback.resumetime))

            # PVR items (live or recorded) can fail to resolve for several seconds after Kodi
            # startup, while the PVR manager is still connecting to the backend and loading
            # channels/recordings - retry a few times (polling more briefly each time) rather than
            # giving up on the first attempt. Library/file playback doesn't have this startup race,
            # so one 10s-wait attempt, as before, is enough for those.
            max_attempts = 15 if is_pvr else 1
            wait_iterations = 30 if is_pvr else 100  # 3s per attempt (PVR) vs one 10s wait (VOD)
            started = False
            for attempt in range(1, max_attempts + 1):
                if is_recording:
                    xbmc.executebuiltin(f'PlayMedia("{playback.file}", resume)')
                elif is_live:
                    xbmc.executebuiltin(f'PlayMedia("{playback.file}")')
                else:
                    self.play(playback.file, list_item)

                for i in range(wait_iterations):
                    if Store.kodi_event_monitor.abortRequested():
                        Logger.info("resume_if_was_playing: abort requested while waiting for playback to start - giving up on resume")
                        return False
                    if self.isPlayingVideo():
                        started = True
                        break
                    xbmc.sleep(100)

                if started:
                    break

                if attempt < max_attempts:
                    Logger.info(f"resume_if_was_playing: playback did not start on attempt {attempt}/{max_attempts} "
                                f"(PVR backend may still be starting up) - retrying shortly")
                    xbmc.sleep(2000)

            if not started:
                Logger.warning(f"resume_if_was_playing: giving up after {max_attempts} attempt(s) - playback never started")
                return False

            image = playback.poster or playback.icon
            if is_live:
                # Retuning live TV involves Kodi spinning up a full PVR session (buffering etc),
                # which can take several seconds - call this out so it doesn't read as broken
                Notify.kodi_notification(f'Re-tuning live TV: {playback.pluginlabel_short} (this may take a moment)', 5000, image)
            elif is_recording:
                Notify.kodi_notification(f'Resuming PVR Recording: {playback.pluginlabel_short} at {str_timestamp}', 5000, image)
            else:
                Notify.kodi_notification(f'Resuming: {playback.pluginlabel_short} at {str_timestamp}', 5000, image)
            return True

        except Exception as e:
            # Belt and braces: nothing in the resume path should ever be allowed to raise up out
            # of this function and crash the service - that leaves the whole addon not running for
            # the rest of the session, which is far worse than a failed resume.
            Logger.error(f"resume_if_was_playing: unexpected exception during resume attempt - giving up on resume, but continuing normally: {e}")
            return False

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

        json_response = send_kodi_json(f'Get a random video from: {result_type}', query)
        result = json_response.get('result') if json_response else None

        # found a video!
        if result and result.get('limits', {}).get('total', 0) > 0:
            Store.video_types_in_library[result_type] = True
            return result[result_type][0]['file']
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

"""Seek backs module submits player seek commands based on playback events."""

import xbmc
import json
import time
from resources.lib.settings_manager import SettingsManager


class SeekBacks:
    # Event type mapping for settings
    SETTING_TYPE_MAP = {
        'resume': 'resume',
        'adjust': 'adjust',
        'unpause': 'unpause',
        'change': 'change'  # Keep 'change' separate from 'adjust'
    }

    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.settings_manager = SettingsManager()
        self.playback_state = {
            'paused': False,
            'last_seek_time': 0  # Track the last time we performed a seek
        }

    def start(self):
        """Start the seek backs module by subscribing to relevant events."""
        events = {
            'AV_STARTED': self.on_av_started,
            'ON_AV_CHANGE': self.on_av_change,
            'PLAYBACK_RESUMED': self.on_av_unpause,
            'PLAYBACK_PAUSED': self.on_playback_paused,
            'USER_ADJUSTMENT': self.on_user_adjustment,
            'PLAYBACK_STOPPED': self.on_playback_stopped,
            'PLAYBACK_ENDED': self.on_playback_stopped  # Use same handler for both stop and end
        }
        for event, callback in events.items():
            self.event_manager.subscribe(event, callback)

    def stop(self):
        """Stop the seek backs module and clean up subscriptions."""
        events = {
            'AV_STARTED': self.on_av_started,
            'ON_AV_CHANGE': self.on_av_change,
            'PLAYBACK_RESUMED': self.on_av_unpause,
            'PLAYBACK_PAUSED': self.on_playback_paused,
            'USER_ADJUSTMENT': self.on_user_adjustment,
            'PLAYBACK_STOPPED': self.on_playback_stopped,
            'PLAYBACK_ENDED': self.on_playback_stopped
        }
        for event, callback in events.items():
            self.event_manager.unsubscribe(event, callback)

    def on_av_started(self):
        """Handle AV started event."""
        # Reset playback state when new playback starts
        self.playback_state['paused'] = False
        self.perform_seek_back('resume')

    def on_av_change(self):
        """Handle AV change event."""
        self.perform_seek_back('adjust')

    def on_av_unpause(self):
        """Handle playback resume event."""
        xbmc.sleep(500)  # Small delay to avoid race condition on flag
        self.playback_state['paused'] = False
        self.perform_seek_back('unpause')

    def on_playback_paused(self):
        """Handle playback paused event."""
        self.playback_state['paused'] = True

    def on_playback_stopped(self):
        """Handle playback stopped/ended event."""
        xbmc.log("AOM_SeekBacks: Playback stopped/ended, resetting playback state", xbmc.LOGDEBUG)
        self.playback_state['paused'] = False
        self.playback_state['last_seek_time'] = 0

    def on_user_adjustment(self):
        """Handle user adjustment event."""
        xbmc.log("AOM_SeekBacks: Processing user adjustment event", xbmc.LOGDEBUG)
        # Check if seek back is enabled for changes (user adjustments)
        if self.settings_manager.get_setting_boolean('enable_seek_back_change'):
            self.perform_seek_back('change')
        else:
            xbmc.log("AOM_SeekBacks: Seek back for user adjustments is disabled", xbmc.LOGDEBUG)

    def _get_setting_type(self, event_type):
        """Get the correct setting type based on event type.
        
        Args:
            event_type: The type of event triggering the seek back
            
        Returns:
            str: The corresponding setting type
        """
        return self.SETTING_TYPE_MAP.get(event_type, event_type)

    def _should_perform_seek_back(self, event_type):
        """Check if seek back should be performed based on current conditions.
        
        Args:
            event_type: The type of event triggering the seek back
            
        Returns:
            tuple: (should_seek, seek_seconds) or (False, None) if seek is not needed
        """
        # Check if we've performed a seek back recently (within 2 seconds)
        current_time = time.time()
        if current_time - self.playback_state['last_seek_time'] < 2:
            xbmc.log(f"AOM_SeekBacks: Skipping seek back on {event_type} - too soon after last seek",
                     xbmc.LOGDEBUG)
            return False, None

        if self.playback_state['paused']:
            xbmc.log(f"AOM_SeekBacks: Playback is paused, skipping seek back "
                     f"on {event_type}", xbmc.LOGDEBUG)
            return False, None

        setting_type = self._get_setting_type(event_type)
        setting_base = f'seek_back_{setting_type}'
        
        # Check if seek back is enabled for this type
        enable_setting = f'enable_{setting_base}'
        if not self.settings_manager.get_setting_boolean(enable_setting):
            xbmc.log(f"AOM_SeekBacks: Seek back on {event_type} (setting: {enable_setting}) "
                     f"is not enabled", xbmc.LOGDEBUG)
            return False, None

        # Get seek back seconds
        seconds_setting = f'{setting_base}_seconds'
        seek_seconds = self.settings_manager.get_setting_integer(seconds_setting)
        if seek_seconds <= 0:
            xbmc.log(f"AOM_SeekBacks: Invalid seek back seconds ({seek_seconds}) "
                     f"for {event_type}", xbmc.LOGWARNING)
            return False, None

        xbmc.log(f"AOM_SeekBacks: Will seek back {seek_seconds} seconds on {event_type} "
                 f"(setting: {setting_type})", xbmc.LOGDEBUG)
        return True, seek_seconds

    def _execute_seek_command(self, seconds, event_type):
        """Execute the JSON-RPC seek command.
        
        Args:
            seconds: Number of seconds to seek back
            event_type: The type of event that triggered the seek
            
        Returns:
            bool: True if seek was successful, False otherwise
        """
        request = {
            "jsonrpc": "2.0",
            "method": "Player.Seek",
            "params": {
                "playerid": 1,
                "value": {"seconds": -seconds}
            },
            "id": 1
        }

        try:
            xbmc.log(f"AOM_SeekBacks: Attempting to seek back {seconds} seconds "
                     f"on {event_type}", xbmc.LOGDEBUG)
            response = xbmc.executeJSONRPC(json.dumps(request))
            response_json = json.loads(response)
            
            if "error" in response_json:
                xbmc.log(f"AOM_SeekBacks: Failed to perform seek back: "
                         f"{response_json['error']}", xbmc.LOGWARNING)
                return False
                
            # Update last seek time only on successful seek
            self.playback_state['last_seek_time'] = time.time()
            xbmc.log(f"AOM_SeekBacks: Successfully seeked back by {seconds} seconds "
                     f"on {event_type}", xbmc.LOGDEBUG)
            return True
            
        except Exception as e:
            xbmc.log(f"AOM_SeekBacks: Error executing seek command: {str(e)}",
                     xbmc.LOGERROR)
            return False

    def perform_seek_back(self, event_type):
        """Perform seek back operation based on event type and current conditions.
        
        Args:
            event_type: The type of event triggering the seek back
        """
        try:
            should_seek, seek_seconds = self._should_perform_seek_back(event_type)
            
            if not should_seek:
                return
                
            # Required delay for stream settling
            xbmc.sleep(2000)
            
            if not self._execute_seek_command(seek_seconds, event_type):
                xbmc.log(f"AOM_SeekBacks: Seek back operation failed for {event_type}",
                         xbmc.LOGWARNING)
                
        except Exception as e:
            xbmc.log(f"AOM_SeekBacks: Error in perform_seek_back: {str(e)}",
                     xbmc.LOGERROR)

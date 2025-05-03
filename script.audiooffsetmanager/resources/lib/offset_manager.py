"""Offset manager module to receive playback events and assign audio offsets as needed.
This module also controls the deployment of the Active Monitor when it's enabled.
"""

import xbmc
import json
from resources.lib.settings_manager import SettingsManager
from resources.lib.stream_info import StreamInfo
from resources.lib.active_monitor import ActiveMonitor
from resources.lib.notification_handler import NotificationHandler


class OffsetManager:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.stream_info = StreamInfo()
        self.settings_manager = SettingsManager()
        self.notification_handler = NotificationHandler(self.settings_manager)
        self.active_monitor = None

    def start(self):
        """Start the offset manager by subscribing to relevant events."""
        events = {
            'AV_STARTED': self.on_av_started,
            'ON_AV_CHANGE': self.on_av_change,
            'PLAYBACK_STOPPED': self.on_playback_stopped,
            'PLAYBACK_ENDED': self.on_playback_stopped,
            'USER_ADJUSTMENT': self.on_user_adjustment
        }
        for event, callback in events.items():
            self.event_manager.subscribe(event, callback)

    def stop(self):
        """Stop the offset manager and clean up subscriptions."""
        events = {
            'AV_STARTED': self.on_av_started,
            'ON_AV_CHANGE': self.on_av_change,
            'PLAYBACK_STOPPED': self.on_playback_stopped,
            'PLAYBACK_ENDED': self.on_playback_stopped,
            'USER_ADJUSTMENT': self.on_user_adjustment
        }
        for event, callback in events.items():
            self.event_manager.unsubscribe(event, callback)
        self.stop_active_monitor()

    def on_av_started(self):
        """Handle AV started event."""
        self._handle_av_event()

    def on_av_change(self):
        """Handle AV change event."""
        self._handle_av_event()

    def on_playback_stopped(self):
        """Handle playback stopped event."""
        self.stream_info.clear_stream_info()
        self.stop_active_monitor()
        
    def on_user_adjustment(self):
        """Handle user adjustment event (manual offset change)."""
        # Only send notification if active monitor is enabled
        if self.active_monitor is not None:
            # Get the current audio delay from settings
            stream_info = self.stream_info.info
            setting_id = self._get_setting_id(stream_info)
            delay_ms = self.settings_manager.get_setting_integer(setting_id)
            
            # Send notification about the manual offset change
            self.notification_handler.notify_manual_offset_saved(delay_ms, self.stream_info)
            xbmc.log(f"AOM_OffsetManager: Notified user about manual offset change to {delay_ms}ms",
                     xbmc.LOGDEBUG)

    def _handle_av_event(self):
        """Common handler for AV-related events."""
        self.stream_info.update_stream_info()
        self.apply_audio_offset()
        self.manage_active_monitor()

    def _should_apply_offset(self):
        """Check if audio offset should be applied based on current conditions."""
        if self.settings_manager.get_setting_boolean('new_install'):
            xbmc.log("AOM_OffsetManager: New install detected. Skipping "
                     "audio offset application.", xbmc.LOGDEBUG)
            return False

        stream_info = self.stream_info.info
        # Check for unknown formats
        if any(stream_info[key] == 'unknown' for key in 
               ['hdr_type', 'audio_format', 'video_fps_type']):
            xbmc.log(f"AOM_OffsetManager: Skipping audio offset - Unknown format detected "
                     f"(HDR: {stream_info['hdr_type']}, Audio: {stream_info['audio_format']}, "
                     f"FPS: {stream_info['video_fps_type']})", xbmc.LOGDEBUG)
            return False

        # Check if HDR type is enabled
        if not self.settings_manager.get_setting_boolean(f"enable_{stream_info['hdr_type']}"):
            xbmc.log(f"AOM_OffsetManager: HDR type {stream_info['hdr_type']} is not "
                     f"enabled in settings", xbmc.LOGDEBUG)
            return False

        return True

    def _get_setting_id(self, stream_info):
        """Generate the setting ID for the current stream configuration."""
        return f"{stream_info['hdr_type']}_{stream_info['video_fps_type']}_{stream_info['audio_format']}"

    def apply_audio_offset(self):
        """Apply audio offset based on current stream information and settings."""
        try:
            if not self._should_apply_offset():
                return

            stream_info = self.stream_info.info
            setting_id = self._get_setting_id(stream_info)
            delay_ms = self.settings_manager.get_setting_integer(setting_id)

            if delay_ms is None:
                xbmc.log(f"AOM_OffsetManager: No audio delay found for setting ID: {setting_id}",
                         xbmc.LOGDEBUG)
                return

            if stream_info['player_id'] != -1:
                self.set_audio_delay(stream_info['player_id'], delay_ms / 1000.0)
            else:
                xbmc.log("AOM_OffsetManager: No valid player ID found to set "
                         "audio delay", xbmc.LOGDEBUG)

        except Exception as e:
            xbmc.log(f"AOM_OffsetManager: Error applying audio offset: {str(e)}",
                     xbmc.LOGERROR)

    def set_audio_delay(self, player_id, delay_seconds):
        """Set the audio delay using JSON-RPC."""
        try:
            request = {
                "jsonrpc": "2.0",
                "method": "Player.SetAudioDelay",
                "params": {
                    "playerid": player_id,
                    "offset": delay_seconds
                },
                "id": 1
            }
            response = xbmc.executeJSONRPC(json.dumps(request))
            response_json = json.loads(response)
            
            if "error" in response_json:
                xbmc.log(f"AOM_OffsetManager: Failed to set audio offset: "
                         f"{response_json['error']}", xbmc.LOGWARNING)
            else:
                xbmc.log(f"AOM_OffsetManager: Audio offset set to "
                         f"{delay_seconds} seconds", xbmc.LOGDEBUG)
                
                # Convert seconds to milliseconds for notification
                delay_ms = int(delay_seconds * 1000)
                
                # Send notification for automatic offset application
                # This is only called for automatic offset application (not manual adjustments)
                self.notification_handler.notify_audio_offset_applied(delay_ms, self.stream_info)
        except Exception as e:
            xbmc.log(f"AOM_OffsetManager: Error setting audio delay: {str(e)}",
                     xbmc.LOGERROR)

    def _should_start_active_monitor(self):
        """Determine if active monitor should be started based on current conditions."""
        stream_info = self.stream_info.info
        active_monitoring_enabled = self.settings_manager.get_setting_boolean('enable_active_monitoring')
        hdr_type = stream_info['hdr_type']
        fps_type = stream_info['video_fps_type']
        hdr_type_enabled = self.settings_manager.get_setting_boolean(f'enable_{hdr_type}')

        return (active_monitoring_enabled and 
                hdr_type_enabled and 
                hdr_type != 'unknown' and 
                fps_type != 'unknown')

    def manage_active_monitor(self):
        """Manage the active monitor state based on current conditions."""
        xbmc.log(f"AOM_OffsetManager: Checking active monitor status - "
                 f"HDR: {self.stream_info.info['hdr_type']}, "
                 f"FPS: {self.stream_info.info['video_fps_type']}", 
                 xbmc.LOGDEBUG)

        if self._should_start_active_monitor():
            self.start_active_monitor()
        else:
            self.stop_active_monitor()

    def start_active_monitor(self):
        """Start the active monitor if it's not already running."""
        if self.active_monitor is None:
            self.active_monitor = ActiveMonitor(self.event_manager, self.stream_info, self)
            self.active_monitor.start()
            xbmc.log("AOM_OffsetManager: Active monitor started", xbmc.LOGDEBUG)

    def stop_active_monitor(self):
        """Stop the active monitor if it's running."""
        if self.active_monitor is not None:
            self.active_monitor.stop()
            self.active_monitor = None
            xbmc.log("AOM_OffsetManager: Active monitor stopped", xbmc.LOGDEBUG)

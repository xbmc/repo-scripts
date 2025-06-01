"""Active monitor module to detect user changes in audio offset values during playback."""

import xbmc
import xbmcgui
import threading
from resources.lib.settings_manager import SettingsManager


class ActiveMonitor:
    # Dialog IDs as constants for better maintainability
    AUDIO_SETTINGS_DIALOG = 10124
    AUDIO_SLIDER_DIALOG = 10145
    
    def __init__(self, event_manager, stream_info, offset_manager):
        self.event_manager = event_manager
        self.stream_info = stream_info
        self.offset_manager = offset_manager
        self.settings_manager = SettingsManager()
        self.monitor_thread = None
        
        # Consolidated state management
        self.state = {
            'monitor_active': False,
            'playback_active': False,
            'audio_settings_open': False,
            'slider_was_open': False,  # Track previous slider state
            'last_audio_delay': None,
            'last_stored_delay': None,
            'last_processed_delay': None
        }

    def start(self):
        """Start the active monitor if it's not already running."""
        if not self.state['monitor_active']:
            self._initialize_monitoring()
            self._start_monitor_thread()
            xbmc.log("AOM_ActiveMonitor: Active monitoring started", xbmc.LOGDEBUG)

    def stop(self):
        """Stop the active monitor if it's running."""
        if self.state['monitor_active']:
            self._cleanup_monitoring()
            xbmc.log("AOM_ActiveMonitor: Active monitoring stopped", xbmc.LOGDEBUG)

    def _initialize_monitoring(self):
        """Initialize monitoring state and update necessary information."""
        self.state.update({
            'monitor_active': True,
            'playback_active': True,
            'audio_settings_open': False,
            'slider_was_open': False
        })
        self.update_stream_info()
        self.update_last_stored_audio_delay()

    def _cleanup_monitoring(self):
        """Clean up monitoring state and stop the monitor thread."""
        self.state['monitor_active'] = False
        self.state['playback_active'] = False
        if self.monitor_thread is not None:
            self.monitor_thread.join()
            self.monitor_thread = None

    def _start_monitor_thread(self):
        """Start the monitor thread if it's not already running."""
        if self.monitor_thread is None:
            self.monitor_thread = threading.Thread(target=self.monitor_audio_offset)
            self.monitor_thread.start()

    def update_stream_info(self):
        """Update and validate stream information."""
        self.stream_info.update_stream_info()
        xbmc.log(f"AOM_ActiveMonitor: Updated stream info: {self.stream_info.info}", 
                 xbmc.LOGDEBUG)

    def _validate_stream_info(self):
        """Validate current stream information.
        
        Returns:
            tuple: (is_valid, stream_info_dict) or (False, None) if invalid
        """
        stream_info = self.stream_info.info
        required_keys = ['hdr_type', 'video_fps_type', 'audio_format']
        
        if any(stream_info.get(key, 'unknown') == 'unknown' for key in required_keys):
            xbmc.log(f"AOM_ActiveMonitor: Invalid stream info: {stream_info}", 
                     xbmc.LOGDEBUG)
            return False, None
            
        return True, stream_info

    def update_last_stored_audio_delay(self):
        """Update the last stored audio delay from settings."""
        try:
            is_valid, stream_info = self._validate_stream_info()
            if not is_valid:
                return

            setting_id = self._get_setting_id(stream_info)
            self.state['last_stored_delay'] = self.settings_manager.get_setting_integer(setting_id)
            self.state['last_processed_delay'] = self.state['last_stored_delay']
            
            xbmc.log(f"AOM_ActiveMonitor: Updated last stored audio delay to "
                     f"{self.state['last_stored_delay']} for setting {setting_id}", 
                     xbmc.LOGDEBUG)
                     
        except Exception as e:
            xbmc.log(f"AOM_ActiveMonitor: Error updating last stored audio delay: {str(e)}",
                     xbmc.LOGERROR)

    def _get_setting_id(self, stream_info):
        """Generate setting ID from stream information."""
        return f"{stream_info['hdr_type']}_{stream_info['video_fps_type']}_{stream_info['audio_format']}"

    def convert_delay_to_ms(self, delay_str):
        """Convert delay string to milliseconds integer.
        
        Args:
            delay_str: Delay string in format '-0.075 s'
            
        Returns:
            int: Delay in milliseconds or None if conversion fails
        """
        try:
            delay_seconds = float(delay_str.replace(' s', ''))
            return int(delay_seconds * 1000)
        except (ValueError, AttributeError):
            return None

    def _handle_dialog_state(self, current_dialog_id, monitor):
        """Handle dialog state changes and audio delay processing.
        
        Returns:
            float: Wait time for next iteration
        """
        # Track if slider is currently open
        slider_is_open = current_dialog_id == self.AUDIO_SLIDER_DIALOG

        # Handle audio settings dialog state
        if current_dialog_id == self.AUDIO_SETTINGS_DIALOG:
            if not self.state['audio_settings_open']:
                self.state['audio_settings_open'] = True
                self.state['last_processed_delay'] = None
                xbmc.log("AOM_ActiveMonitor: Audio settings opened", xbmc.LOGDEBUG)
        elif self.state['audio_settings_open'] and current_dialog_id != self.AUDIO_SETTINGS_DIALOG:
            self.state['audio_settings_open'] = False
            xbmc.log("AOM_ActiveMonitor: Audio settings closed", xbmc.LOGDEBUG)

        # Handle slider state and updates
        if slider_is_open:
            self.state['slider_was_open'] = True
            self._update_current_delay()
            xbmc.log("AOM_ActiveMonitor: Slider is open, monitoring changes", xbmc.LOGDEBUG)
        elif self.state['slider_was_open']:  # Slider just closed
            self.state['slider_was_open'] = False
            xbmc.log("AOM_ActiveMonitor: Slider closed, processing changes", xbmc.LOGDEBUG)
            self._process_final_delay()

        # Determine polling rate based on dialog states
        return 0.25 if (self.state['audio_settings_open'] or slider_is_open) else 1.0

    def _check_for_slider_dialog(self, monitor):
        """Check if the audio slider dialog appears within 1 second."""
        start_time = xbmc.getGlobalIdleTime()
        while (xbmc.getGlobalIdleTime() - start_time) < 1:
            if xbmcgui.getCurrentWindowDialogId() == self.AUDIO_SLIDER_DIALOG:
                return True
            if monitor.waitForAbort(0.1):
                return False
        return False

    def _update_current_delay(self):
        """Update the current audio delay value."""
        current_delay = xbmc.getInfoLabel('Player.AudioDelay')
        if current_delay != self.state['last_audio_delay']:
            self.state['last_audio_delay'] = current_delay
            xbmc.log(f"AOM_ActiveMonitor: Current delay updated to {current_delay}",
                     xbmc.LOGDEBUG)

    def _process_final_delay(self):
        """Process the final audio delay value when slider closes."""
        current_delay_ms = self.convert_delay_to_ms(self.state['last_audio_delay'])
        if (current_delay_ms is not None and 
            current_delay_ms != self.state['last_processed_delay']):
            xbmc.log("AOM_ActiveMonitor: Processing delay change after slider close",
                     xbmc.LOGDEBUG)
            self.process_audio_delay_change(self.state['last_audio_delay'])
            self.state['last_processed_delay'] = current_delay_ms

    def monitor_audio_offset(self):
        """Main monitoring loop for audio offset changes."""
        monitor = xbmc.Monitor()
        
        while (self.state['monitor_active'] and 
               self.state['playback_active'] and 
               not monitor.abortRequested()):
               
            current_dialog_id = xbmcgui.getCurrentWindowDialogId()
            wait_time = self._handle_dialog_state(current_dialog_id, monitor)
            
            if monitor.waitForAbort(wait_time):
                break

    def process_audio_delay_change(self, audio_delay):
        """Process and store audio delay changes.
        
        Args:
            audio_delay: The new audio delay value to process
        """
        try:
            xbmc.log(f"AOM_ActiveMonitor: Processing final audio delay: {audio_delay}",
                     xbmc.LOGDEBUG)
                     
            delay_ms = self.convert_delay_to_ms(audio_delay)
            if delay_ms is None:
                return

            is_valid, stream_info = self._validate_stream_info()
            if not is_valid:
                return

            setting_id = self._get_setting_id(stream_info)
            current_delay_ms = self.settings_manager.get_setting_integer(setting_id)
            
            if delay_ms != current_delay_ms:
                self.settings_manager.store_setting_integer(setting_id, delay_ms)
                xbmc.log(f"AOM_ActiveMonitor: Stored audio offset {delay_ms}ms "
                         f"for setting {setting_id}", xbmc.LOGDEBUG)
                self.event_manager.publish('USER_ADJUSTMENT')
                self.state['last_stored_delay'] = delay_ms
                
        except Exception as e:
            xbmc.log(f"AOM_ActiveMonitor: Error processing audio delay change: {str(e)}",
                     xbmc.LOGERROR)

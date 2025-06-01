"""
This module handles notifications for audio offset activies.
"""

import xbmc
import xbmcaddon
import xbmcgui


class NotificationHandler:
    """
    Class for handling Kodi GUI notifications.
    """
    # Dictionary mapping internal audio codec names to their external names
    AUDIO_FORMAT_NAMES = {
        'truehd': 'TrueHD',
        'eac3': 'DD+',
        'ac3': 'DD',
        'dtshd_ma': 'DTS-HD MA',
        'dtshd_hra': 'DTS-HD HRA',
        'dca': 'DTS',
        'pcm': 'PCM',
        'unknown': 'Unknown Format'
    }

    # Dictionary mapping internal HDR format names to their external names
    HDR_TYPE_NAMES = {
        'dolbyvision': 'DV',
        'hdr10': 'HDR10',
        'hdr10plus': 'HDR10+',
        'hlg': 'HLG',
        'sdr': 'SDR'
    }

    # Dictionary mapping internal FPS type names to their real FPS values
    FPS_TYPE_NAMES = {
        '23': '23.98',
        '24': '24.00',
        '25': '25.00',
        '29': '29.97',
        '30': '30.00',
        '50': '50.00',
        '59': '59.94',
        '60': '60.00'
    }
    
    def __init__(self, settings_manager):
        """
        Initialize the notification handler.
        
        Args:
            settings_manager: The settings manager instance to check notification settings
        """
        self.settings_manager = settings_manager
        self.addon = xbmcaddon.Addon('script.audiooffsetmanager')
        self.addon_name = self.addon.getAddonInfo('name')
        self.addon_icon = self.addon.getAddonInfo('icon')
    
    def _send_notification(self, delay_ms, stream_info, prefix):
        """
        Private helper method to send a notification with audio offset information.
        
        Args:
            delay_ms: The audio delay in milliseconds
            stream_info: The stream information object containing details about the current stream
            prefix: The prefix text for the notification message (e.g., "Offset applied:" or "Offset saved:")
        """
        # Check if notifications are enabled in settings
        if not self.settings_manager.get_setting_boolean('enable_notifications'):
            return
            
        # Format the delay value for display
        # Convert to appropriate format (positive = advance, negative = delay)
        sign = "+" if delay_ms > 0 else ""
        delay_text = f"{sign}{delay_ms} ms"
            
        # Get stream format information
        hdr_type = stream_info.info['hdr_type']
        fps_type = stream_info.info['video_fps_type']
        audio_format = stream_info.info['audio_format']
        
        # Log the raw values for debugging
        xbmc.log(f"AOM_NotificationHandler: Raw fps_type={fps_type}, type={type(fps_type)}", xbmc.LOGDEBUG)
        
        # Ensure fps_type is a string for dictionary lookup
        fps_type_str = str(fps_type)
        
        # Get the external names for formats
        audio_format_name = self.AUDIO_FORMAT_NAMES.get(audio_format, audio_format)
        hdr_type_name = self.HDR_TYPE_NAMES.get(hdr_type, hdr_type)
        fps_type_name = self.FPS_TYPE_NAMES.get(fps_type_str, f"{fps_type}")
        
        # Log the lookup result
        xbmc.log(f"AOM_NotificationHandler: fps_type_str={fps_type_str}, fps_type_name={fps_type_name}", xbmc.LOGDEBUG)
        
        # Create notification message
        # If fps_type is 'all', don't include it in the notification
        if fps_type_str.lower() == 'all':
            message = f"{prefix} {delay_text}\n{hdr_type_name} | {audio_format_name}"
        else:
            message = f"{prefix} {delay_text}\n{hdr_type_name} | {fps_type_name} FPS | {audio_format_name}"
        
        # Send notification
        # Get notification duration from settings (in seconds) and convert to milliseconds
        notification_duration_ms = self.settings_manager.get_setting_integer('notification_seconds') * 1000
        xbmcgui.Dialog().notification(
            self.addon_name,
            message,
            self.addon_icon,
            notification_duration_ms
        )
        xbmc.log(f"AOM_NotificationHandler: {message}", xbmc.LOGDEBUG)
    
    def notify_audio_offset_applied(self, delay_ms, stream_info):
        """
        Send a notification when an audio offset is applied for the currently played video.
        This is used when playback starts or when the audio channel changes during playback.
        
        Args:
            delay_ms: The audio delay in milliseconds
            stream_info: The stream information object containing details about the current stream
        """
        self._send_notification(delay_ms, stream_info, "Offset applied:")
        
    def notify_manual_offset_saved(self, delay_ms, stream_info):
        """
        Send a notification when a manual audio offset change is saved.
        This is used when the user manually adjusts the audio offset during playback
        and the active monitor is enabled.
        
        Args:
            delay_ms: The audio delay in milliseconds
            stream_info: The stream information object containing details about the current stream
        """
        self._send_notification(delay_ms, stream_info, "Offset saved:")
"""Module for handling test video playback functionality."""

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from resources.lib.settings_manager import SettingsManager


class TestVideoManager:
    """Manages test video playback functionality."""
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.test_video_path = xbmcvfs.translatePath(self.addon_path + '/resources/media/test-video.mp4')
        self.addon_icon = self.addon.getAddonInfo('icon')

    def play_test_video(self):
        """Play the test video for 5 seconds and return to addon settings."""
        if not xbmcvfs.exists(self.test_video_path):
            xbmcgui.Dialog().notification('Error', 'Test video not found',
                                        xbmcgui.NOTIFICATION_ERROR, 5000)
            return

        # Play the video
        xbmc.Player().play(self.test_video_path)

        # Show notification while video is playing
        xbmcgui.Dialog().notification('Audio Offset Manager',
                                    'Please wait...',
                                    self.addon_icon, 10000)

        # Wait for 5 seconds
        xbmc.sleep(5000)

        # Stop the video
        xbmc.Player().stop()

        # Show success notification
        xbmcgui.Dialog().notification('Audio Offset Manager',
                                    'Success! Test video completed',
                                    self.addon_icon, 10000)

        # Open addon settings
        xbmc.executebuiltin('Addon.OpenSettings(script.audiooffsetmanager)')
        
    def bypass_test_video(self):
        """Bypass the test video by setting new_install to false and refreshing settings."""
        try:
            # Get the settings
            settings = self.addon.getSettings()
            
            # Use direct setting function to avoid cache issues
            settings.setBool('new_install', False)
            
            # Force reload of the settings manager singleton to ensure synchronization
            settings_manager = SettingsManager()
            settings_manager.reload_if_needed()
            
            xbmc.log("AOM_TestVideoManager: Successfully bypassed test video requirement", xbmc.LOGINFO)
            # Show success notification
            xbmcgui.Dialog().notification('Audio Offset Manager',
                                        'Test video requirement bypassed',
                                        self.addon_icon, 3000)
            
            # Add a small delay to ensure settings are saved before reopening
            xbmc.sleep(500)
            
            # Re-open addon settings to refresh them
            xbmc.executebuiltin('Addon.OpenSettings(script.audiooffsetmanager)')
        except Exception as e:
            xbmc.log(f"AOM_TestVideoManager: Failed to bypass test video requirement: {str(e)}", xbmc.LOGWARNING)
            # Show error notification
            xbmcgui.Dialog().notification('Error',
                                        'Failed to bypass test video',
                                        xbmcgui.NOTIFICATION_ERROR, 3000)

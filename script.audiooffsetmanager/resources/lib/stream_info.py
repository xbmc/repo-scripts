"""Stream Info module used to gather stream HDR and audio format information."""

import xbmc
import xbmcgui
import time
import json
from resources.lib.settings_manager import SettingsManager


class StreamInfo:
    def __init__(self):
        self.info = {}
        self.settings_manager = SettingsManager()
        self.new_install = self.settings_manager.get_setting_boolean('new_install')
        self.valid_audio_formats = ['truehd', 'eac3', 'ac3', 'dtshd_ma', 'dtshd_hra', 'dca', 'pcm']
        self.valid_hdr_types = ['dolbyvision', 'hdr10', 'hdr10plus', 'hlg', 'sdr']
        self.valid_fps_types = [23, 24, 25, 29, 30, 50, 59, 60]

    def update_stream_info(self):
        # Gather updated playback details
        self.info = self.gather_stream_info()
        xbmc.log(f"AOM_StreamInfo: Updated stream info: {self.info}", xbmc.LOGDEBUG)

    def clear_stream_info(self):
        # Clear the stream information
        self.info = {}
        xbmc.log("AOM_StreamInfo: Cleared stream info", xbmc.LOGDEBUG)

    def is_valid_infolabel(self, label, value):
        return value and value.strip() and value.lower() != label.lower()

    def gather_stream_info(self):
        # Get player ID
        player_id = self.get_player_id()
        
        # Get audio information
        audio_format, audio_channels = self.get_audio_info(player_id)
        if audio_format not in self.valid_audio_formats:
            xbmc.log(f"AOM_StreamInfo: Invalid audio format detected: {audio_format}", xbmc.LOGDEBUG)
            audio_format = 'unknown'
        
        # Get FPS information
        fps_label = 'Player.Process(videofps)'
        fps_info = xbmc.getInfoLabel(fps_label)
        
        try:
            fps_value = int(float(fps_info))
            fps_type = fps_value if fps_value in self.valid_fps_types else 'unknown'
            if fps_type != 'unknown':
                xbmc.log(f"AOM_StreamInfo: Valid FPS type detected: {fps_type}", xbmc.LOGDEBUG)
            else:
                xbmc.log(f"AOM_StreamInfo: Non-standard FPS value: {fps_value}", xbmc.LOGDEBUG)
        except (ValueError, TypeError):
            fps_value = None
            fps_type = 'unknown'
            xbmc.log(f"AOM_StreamInfo: Unable to parse FPS value: {fps_info}", xbmc.LOGDEBUG)
        
        # Get HDR information
        hdr_label = 'Player.Process(video.source.hdr.type)'
        hdr_type = xbmc.getInfoLabel(hdr_label)
        xbmc.log(f"AOM_StreamInfo: Raw HDR type: '{hdr_type}'", xbmc.LOGDEBUG)
        
        # Check platform HDR support
        if self.is_valid_infolabel(hdr_label, hdr_type):
            platform_hdr_full = True
            xbmc.log("AOM_StreamInfo: Platform HDR full support detected", xbmc.LOGDEBUG)
        else:
            platform_hdr_full = False
            hdr_type = xbmc.getInfoLabel('VideoPlayer.HdrType')
            xbmc.log("AOM_StreamInfo: Using fallback HDR detection", xbmc.LOGDEBUG)
        
        # Process HDR type
        hdr_type = hdr_type.replace('+', 'plus').replace(' ', '').lower()
        if not hdr_type or hdr_type == hdr_label.lower():
            hdr_type = 'sdr'
        elif hdr_type == 'hlghdr':
            hdr_type = 'hlg'
        
        if hdr_type not in self.valid_hdr_types:
            xbmc.log(f"AOM_StreamInfo: Invalid HDR type detected: {hdr_type}", xbmc.LOGDEBUG)
            hdr_type = 'unknown'
        
        # Get gamut information
        gamut_label = 'Player.Process(amlogic.eoft_gamut)'
        gamut_info = xbmc.getInfoLabel(gamut_label)
        gamut_info_valid = self.is_valid_infolabel(gamut_label, gamut_info)
        
        if not gamut_info_valid:
            gamut_info = 'not available'
        
        # Check for HLG detection based on gamut_info
        if hdr_type == 'sdr' and gamut_info_valid and 'hlg' in gamut_info.lower():
            hdr_type = 'hlg'
            xbmc.log("AOM_StreamInfo: HLG detected via gamut info", xbmc.LOGDEBUG)
        
        # Store platform capabilities on every playback
        self.settings_manager.store_setting_boolean('platform_hdr_full', platform_hdr_full)
        advanced_hlg = gamut_info_valid
        self.settings_manager.store_setting_boolean('advanced_hlg', advanced_hlg)
        xbmc.log("AOM_StreamInfo: Updated platform capabilities", xbmc.LOGDEBUG)
        
        # Handle new install flag if needed
        if self.new_install:
            self.new_install = False
            self.settings_manager.store_setting_boolean('new_install', self.new_install)
            xbmc.log("AOM_StreamInfo: Updated new install flag", xbmc.LOGDEBUG)

        # Check if FPS type should be overridden based on HDR setting
        if hdr_type != 'unknown':
            setting_name = f'enable_fps_{hdr_type}'
            setting_value = self.settings_manager.get_setting_boolean(setting_name)
            xbmc.log(f"AOM_StreamInfo: Checking setting '{setting_name}' = {setting_value}", xbmc.LOGDEBUG)
            
            if not setting_value:
                fps_type = 'all'
                xbmc.log(f"AOM_StreamInfo: FPS type overridden to 'all' due to {setting_name} being disabled", xbmc.LOGDEBUG)
            else:
                xbmc.log(f"AOM_StreamInfo: Keeping original FPS type '{fps_type}' as {setting_name} is enabled", xbmc.LOGDEBUG)

        # Construct comprehensive stream information dictionary
        stream_info = {
            'player_id': player_id,
            'audio_format': audio_format,
            'audio_channels': audio_channels,
            'video_fps': fps_value,
            'video_fps_type': fps_type,
            'hdr_type': hdr_type,
            'gamut_info': gamut_info,
            'gamut_info_valid': gamut_info_valid,
            'platform_hdr_full': platform_hdr_full
        }

        xbmc.log(f"AOM_StreamInfo: Gathered complete stream info: {stream_info}", xbmc.LOGDEBUG)
        return stream_info

    def get_player_id(self):
        # Use JSON-RPC to retrieve the player ID, retrying up to 10 times if necessary
        for attempt in range(10):
            try:
                request = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "Player.GetActivePlayers",
                    "id": 1
                })
                response = xbmc.executeJSONRPC(request)
                response_json = json.loads(response)

                if "result" in response_json and len(response_json["result"]) > 0:
                    player_id = response_json["result"][0].get("playerid", -1)
                    if player_id != -1:
                        return player_id

                xbmc.log(f"AOM_StreamInfo: Invalid player ID, retrying... ({attempt + 1}/10)",
                         xbmc.LOGDEBUG)
                time.sleep(0.5)
            except Exception as e:
                xbmc.log(f"AOM_StreamInfo: Error getting player ID: {str(e)}",
                         xbmc.LOGERROR)
                time.sleep(0.5)

        xbmc.log("AOM_StreamInfo: Failed to retrieve valid player ID after 10 attempts",
                 xbmc.LOGWARNING)
        return -1

    def get_audio_info(self, player_id):
        # Use JSON-RPC to retrieve audio codec and channel count, retrying if 'none' is detected
        for attempt in range(10):
            try:
                request = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "Player.GetProperties",
                    "params": {
                        "playerid": player_id,
                        "properties": ["currentaudiostream"]
                    },
                    "id": 1
                })
                response = xbmc.executeJSONRPC(request)
                response_json = json.loads(response)

                if "result" in response_json and "currentaudiostream" in response_json["result"]:
                    audio_stream = response_json["result"]["currentaudiostream"]
                    audio_format = audio_stream.get("codec", "unknown").replace('pt-', '')
                    audio_channels = audio_stream.get("channels", "unknown")

                    if audio_format != 'none':
                        # Check if the reported format contains any of our valid formats
                        reported_format = audio_format.lower()
                        for valid_format in self.valid_audio_formats:
                            if valid_format in reported_format:
                                audio_format = valid_format
                                break
                        else:
                            # If no valid format is found, assume PCM
                            if audio_format != 'unknown':
                                audio_format = 'pcm'

                        return audio_format, audio_channels

                xbmc.log(f"AOM_StreamInfo: Invalid audio format 'none', retrying... ({attempt + 1}/10)",
                         xbmc.LOGDEBUG)
                time.sleep(0.5)
            except Exception as e:
                xbmc.log(f"AOM_StreamInfo: Error getting audio info: {str(e)}",
                         xbmc.LOGERROR)
                time.sleep(0.5)

        xbmc.log("AOM_StreamInfo: Failed to retrieve valid audio information after 10 attempts",
                 xbmc.LOGWARNING)
        return "unknown", "unknown"

"""Settings manager module to provide methods for other modules to interface with 
the addon settings.
"""

import xbmc
import xbmcaddon


class SettingsManager:
    _instance = None
    _settings = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        """Initialize the settings manager with addon settings."""
        self.addon = xbmcaddon.Addon('script.audiooffsetmanager')
        self._settings = self.addon.getSettings()

    def reload_if_needed(self):
        """Public method to reload settings when explicitly needed."""
        self._settings = self.addon.getSettings()

    def _safe_setting_operation(self, operation, setting_id, default_value, value_type):
        """Safely execute a settings operation with proper error handling.
        
        Args:
            operation: The settings method to call (getBool, getInt, etc)
            setting_id: The ID of the setting to access
            default_value: Value to return if operation fails
            value_type: String description of the value type for logging
        """
        try:
            return operation(setting_id)
        except:
            xbmc.log(f"AOM_SettingsManager: Error getting {value_type} setting "
                     f"'{setting_id}'. Using default: {default_value}", 
                     xbmc.LOGWARNING)
            return default_value

    def get_setting_boolean(self, setting_id):
        """Retrieve the boolean setting using Settings.getBool()."""
        return self._safe_setting_operation(
            self._settings.getBool, 
            setting_id, 
            False, 
            "boolean"
        )

    def get_setting_integer(self, setting_id):
        """Retrieve the integer setting using Settings.getInt()."""
        return self._safe_setting_operation(
            self._settings.getInt, 
            setting_id, 
            0, 
            "integer"
        )

    def get_setting_string(self, setting_id):
        """Retrieve the string setting using Settings.getString()."""
        return self._safe_setting_operation(
            self._settings.getString, 
            setting_id, 
            "", 
            "string"
        )

    def _safe_setting_store(self, operation, setting_id, value, value_type):
        """Safely store a setting value with proper error handling.
        
        Args:
            operation: The settings method to call (setBool, setInt, etc)
            setting_id: The ID of the setting to store
            value: The value to store
            value_type: String description of the value type for logging
        """
        try:
            xbmc.log(f"AOM_SettingsManager: Storing {value_type} setting {setting_id}: "
                     f"{value}", xbmc.LOGDEBUG)
            operation(setting_id, value)
            return True
        except:
            xbmc.log(f"AOM_SettingsManager: Error storing {value_type} setting "
                     f"'{setting_id}'.", xbmc.LOGWARNING)
            return False

    def store_setting_boolean(self, setting_id, value):
        """Store a boolean setting."""
        return self._safe_setting_store(
            self._settings.setBool,
            setting_id,
            value,
            "boolean"
        )

    def store_setting_integer(self, setting_id, value):
        """Store an integer setting."""
        return self._safe_setting_store(
            self._settings.setInt,
            setting_id,
            value,
            "integer"
        )

    def store_setting_string(self, setting_id, value):
        """Store a string setting."""
        return self._safe_setting_store(
            self._settings.setString,
            setting_id,
            value,
            "string"
        )

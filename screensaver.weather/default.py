# -*- coding: utf-8 -*-
import xbmcgui

#########################
# Main
#########################
if __name__ == '__main__':

    msg = 'The WeatherScreensaver Addon has been removed from the Official Repo'
    msg2 = 'WeatherScreensaver is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('WeatherScreensaver Has Moved', msg, msg2, msg3)

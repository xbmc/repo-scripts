# -*- coding: utf-8 -*-
import xbmcgui


###################################
# Main of the VideoScreensaver Service
###################################
if __name__ == '__main__':

    msg = 'The VideoScreensaver Addon has been removed from the Official Repo'
    msg2 = 'VideoScreensaver is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('VideoScreensaver Has Moved', msg, msg2, msg3)

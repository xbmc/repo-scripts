# -*- coding: utf-8 -*-
import xbmcgui


###################################
# Main of the VideoExtras Service
###################################
if __name__ == '__main__':

    msg = 'The VideoExtras Addon has been removed from the Official Repo'
    msg2 = 'VideoExtras is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('VideoExtras Has Moved', msg, msg2, msg3)

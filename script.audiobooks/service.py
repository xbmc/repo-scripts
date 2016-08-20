# -*- coding: utf-8 -*-
import xbmcgui


###################################
# Main of the AudioBooks Service
###################################
if __name__ == '__main__':

    msg = 'The AudioBooks Addon has been removed from the Official Repo'
    msg2 = 'AudioBooks is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('AudioBooks Has Moved', msg, msg2, msg3)

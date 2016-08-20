# -*- coding: utf-8 -*-
import xbmcgui


###################################
# Main of the Suitability Service
###################################
if __name__ == '__main__':

    msg = 'The Suitability Addon has been removed from the Official Repo'
    msg2 = 'Suitability is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('Suitability Has Moved', msg, msg2, msg3)

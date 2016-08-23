# -*- coding: utf-8 -*-
import xbmcgui


###################################
# Main of the PinSentry Service
###################################
if __name__ == '__main__':

    msg = 'The eBooks Addon has been removed from the Official Repo'
    msg2 = 'eBooks is now located in the robwebset repository.'
    msg3 = 'See the forum for more information'
    makeRequest = xbmcgui.Dialog().ok('eBooks Has Moved', msg, msg2, msg3)

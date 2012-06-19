import xbmc, xbmcgui
import xbmcjsonrpc
import state
import states

#get actioncodes from keymap.xml
ACTION_PREVIOUS_MENU = 10

sm = state.StateManager()

sm.switchTo(states.CheckServerState())
sm.doModal()

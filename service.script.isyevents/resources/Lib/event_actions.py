'''
    ISY Event Engine for XBMC (event_actions)
    Copyright (C) 2012 Ryan M. Kraus

    LICENSE:
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    DESCRIPTION:
    This Python Module translates the action names into functions for the
    ISY Events addon for XBMC.
    
    WRITTEN:    11/2012
'''

# dictionary to translate actions
__act_names__ = {
    'On': 'NodeOn',
    'Off': 'NodeOff',
    'Toggle': 'NodeToggle',
    'Fast On': 'NodeFastOn',
    'Fast Off': 'NodeFastOff',
    'Bright': 'NodeBright',
    'Dim': 'NodeDim',
    'On To 25%': 'NodeOn25',
    'On To 50%': 'NodeOn50',
    'On To 75%': 'NodeOn75',
    'On To 100%': 'NodeOn100',
    'Run': 'ProgramRun',
    'Run Then': 'ProgramRunThen',
    'Run Else': 'ProgramRunElse'
    }
    
def ParseActionSettings(isy, addr, action):
    if addr == '':
        return None
    elif action == 'None':
        return None
    else:
        fun = getattr(isy, __act_names__[action])
        return lambda: fun(addr)
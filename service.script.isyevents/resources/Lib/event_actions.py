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
    'Run': 'ProgramRun',
    'Run Then': 'ProgramRunThen',
    'Run Else': 'ProgramRunElse'
    }
    
def ParseDeviceSetting(isy, isy_events, name):
    enable = isy_events.getSetting(name + '_bool')
    addr = isy_events.getSetting(name)
    perc = int(float(isy_events.getSetting(name + '_perc')))
    
    if enable == 'true':
        if perc > 0:
            return lambda: isy.NodeOn(addr, val=perc*255/100)
        else:
            return lambda: isy.NodeOff(addr)
    else:
        return None
        
def ParseProgramSetting(isy, isy_events, name):
    enable = isy_events.getSetting(name + '_bool')
    addr = isy_events.getSetting(name)
    act = isy_events.getSetting(name + '_act')
    action = __act_names__[act]
    
    if enable == 'true':
        fun = getattr(isy, action)
        return lambda: fun(addr)
    else:
        return None
'''
    myCollections
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
    This Python Module contains different data types that perform basic
    functions to assist outside programs.
    
    WRITTEN:    11/2012
'''

class histlist(object):
    '''
    histlist
    
    The history list (histlist) is a list that tracks the history of a 
    value. The history list can also notify when the value is changed,
    This is referred to as a step. There are two kinds of steps that can
    be tracked. A regular step (value is changed) and a delayed step. A 
    delayed step requires that the value be changed a specified amount of
    consecutive times.
    
    On initialization, the hist list class requires either a set of initial
    conditions of a single value that will be set for all the initial 
    conditions. If a single value is given, 4 steps of history will be
    tracked.  If initial conditions are given, one step will be tracked for
    each entry in the array of initial conditions.
    '''

    __min_size__ = 4

    def __init__(self, IC):
        # create initial states
        if type(IC) == int or type(IC) == float or type(IC) == bool:
            # single value input, spread across all IC's
            self.state = list()
            self.state = [IC for ind in range(self.__min_size__)]
        
        elif type(IC) == list or type(IC) == tuple:
            # IC set was input
            IC = list(IC)
            if len(IC) < self.__min_size__:
                raise ValueError('Input must be of at least length ' + str(self.__min_size__))
            else:
                self.state = IC
                
        else:
            raise ValueError('Input must be of type bool, int, float, list, or tuple')
        
        self.__len__ = len(self.state)
        
    def set(self, val):
        self.state = [val] + [self.state[ind] for ind in xrange(0, self.__len__-1, 1)]
        
    def get(self, step=0):
        return self.state[step]
        
    def __str__(self):
        return "histlist(" + str(self.state) + ")"
        
    def __iter__(self):
        return self.state.__iter__()
        
    def step(self):
        return self.get(0) != self.get(1)
        
    def delayed_step(self, inc=2):
        step = True
        ind = 1
        while step and ind <= inc:
            step = step and (self.get(ind-1) != self.get(ind))
            ind += 1
        return step
        
    def step_on(self):
        return self.step() and (self.get(0) > 0)
        
    def delayed_step_on(self, inc=2):
        return self.delayed_step(inc) and (self.get(0) > 0)
        
    def step_off(self):
        return self.step() and (self.get(0) == 0)
        
    def delayed_step_off(self, inc=2):
        return self.delayed_step(inc) and (self.get(0) == 0)
'''
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0
    based on plugnplay by https://github.com/daltonmatos

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

'''
  The main plugin Manager class.
  Stores all implementors of all public interfaces
'''
class Manager(object):

    def __init__(self):
        self.iface_implementors = {}

    def add_implementor(self, interface, implementor_instance):
        self.iface_implementors.setdefault(interface, [])
        for index, item in enumerate(self.iface_implementors[interface]):
            if implementor_instance.priority <= item.priority:
                self.iface_implementors[interface].insert(index,
                                                      implementor_instance)
                return
        self.iface_implementors[interface].append(implementor_instance)

    def is_empty(self):
        return {} == self.iface_implementors

    def implementors(self, interface):
        self.iface_implementors.setdefault(interface, [])
        return self.iface_implementors.get(interface, [])

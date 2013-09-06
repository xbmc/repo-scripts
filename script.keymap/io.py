'''
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
import os
import xml.etree.cElementTree as etree
from elementtree.SimpleXMLWriter import XMLWriter

def read_keymap(filename):
  ret = []
  with open(filename, 'r') as xml:
    tree = etree.iterparse(xml)
    for _, keymap in tree:
      for context in keymap:
        for device in context:
          for mapping in device:
            key = mapping.get('id') or mapping.tag
            action = mapping.text
            if action:
              ret.append((context.tag.lower(), action.lower(), key.lower()))
  return ret

def write_keymap(keymap, filename):
  contexts = list(set([ c for c,a,k in keymap ]))
  actions  = list(set([ a for c,a,k in keymap ]))
  
  w = XMLWriter(filename, "utf-8")
  doc = w.start("keymap")
  
  for context in contexts:
    w.start(context)
    w.start("keyboard")
    for c,a,k in keymap:
      if c==context:
        w.element("key", a, id=k)
    w.end()
    w.end()
  w.end()
  w.close(doc)

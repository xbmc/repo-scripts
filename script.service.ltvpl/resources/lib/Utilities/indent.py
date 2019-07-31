#
#       Copyright (C) 2018
#       John Moore (jmooremcc@hotmail.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
from xml.etree import ElementTree

__Version__ = "1.0.0"

def indent(elem, level=0):
    TabSpace = "  "
    i = "\n" + level*TabSpace
    #j = "\n" + (level-1)*TabSpace
    #print("eTag:{} len(elem):{} i=*{}* j=*{}*".format(elem.tag,len(elem),i,j))
    if len(elem):
        #print("tag:{} text:{}".format(elem.tag,elem.text))
        if not elem.text or not elem.text.strip():
            elem.text = i + TabSpace
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        numChildren=len(elem) - 1 #JM Fix1
        for x,subelem in enumerate(elem):
            indent(subelem, level+1)
            #JM Fix1 to indent all children of an element 7/10/2017
            if x < numChildren:
                subelem.tail += (level - 1)*TabSpace
            else: # last child gets regular tail spacing
                subelem.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else: # Element has no children
        #print("level:{} tag:{} elem.tail:{}".format(level,elem.tag,elem.tail))
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

    return elem  


def indent2(elem, level=0):
    TabSpace = "  "
    i = "\n" + level*TabSpace
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + TabSpace
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent2(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


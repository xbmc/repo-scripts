# -*- coding: utf-8 -*-
'''
    script.matchcenter - Football information for Kodi
    A program addon that can be mapped to a key on your remote to display football information.
    Livescores, Event details, Line-ups, League tables, next and previous matches by team. Follow what
    others are saying about the match in twitter.
    Copyright (C) 2016 enen92

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
import xbmcgui

def getShirtHeight(pitchHeigh,positionPercent):
	shirtHeightPercent = 0.0752*positionPercent + 0.1204
	return int(shirtHeightPercent*pitchHeigh)

def getLabel(imagecontrol,label):
	#image control
	image_position = imagecontrol.getPosition()
	image_height = imagecontrol.getHeight()
	image_width = imagecontrol.getWidth()
	#label control
	label_x = int(image_position[0]-0.5*image_width)
	label_y = int(image_position[1]+image_height-0.04*image_height)
	label_height = int(0.2*image_height)
	label_width = int(2*image_width)
	return xbmcgui.ControlLabel(label_x, label_y, label_width, label_height, label, alignment = 0x00000002, font="font10", textColor="0xFFEB9E17")

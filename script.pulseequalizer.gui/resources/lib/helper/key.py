#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2022 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#
#

Modifier = [("CTRL",0x0001),
			("SHIFT",0x0002),
			("ALT ",0x0004),
			("RALT",0x0008),
			("SUPER",0x0010),
			("META",0X0020),
			("LONG",0X0100),
			("NUMLOCK",0X0200),
			("CAPSLOCK",0X0400),
			("SCROLLLOCK",0X0800)]

ModList = ["ctrl","shift","alt","","super","meta","longpress"]

RemoteIndex= {213: 'display', 226: 'reverse', 234: 'play', 227: 'forward', 221: 'skipminus', 224: 'stop', 230: 'pause', 223: 'skipplus', 229: 'title', 195: 'info', 166: 'up', 167: 'down', 169: 'left', 168: 'right', 11: 'select', 22: 'enter', 44: 'subtitle', 45: 'language', 247: 'menu', 216: 'back', 206: 'one', 205: 'two', 204: 'three', 203: 'four', 202: 'five', 201: 'six', 200: 'seven', 199: 'eight', 198: 'nine', 207: 'zero', 196: 'power', 49: 'mytv', 9: 'mymusic', 6: 'mypictures', 7: 'myvideo', 232: 'record', 37: 'start', 208: 'volumeplus', 209: 'volumeminus', 210: 'pageplus', 211: 'pageminus', 192: 'mute', 101: 'recordedtv', 24: 'livetv', 40: 'star', 41: 'hash', 249: 'clear', 250: 'teletext', 251: 'red', 252: 'green', 253: 'yellow', 254: 'blue', 255: 'playlist', 50: 'guide', 248: 'liveradio', 246: 'epgsearch', 235: 'eject', 236: 'contentsmenu', 237: 'rootmenu', 238: 'topmenu', 239: 'dvdmenu', 240: 'print'}
KeyIndex= {8: 'backspace', 9: 'tab', 13: 'return', 27: 'escape', 32: 'space', 33: 'exclaim', 34: 'doublequote', 35: 'hash', 36: 'dollar', 37: 'percent', 38: 'ampersand', 39: 'quote', 40: 'leftbracket', 41: 'rightbracket', 42: 'asterisk', 43: 'plus', 44: 'comma', 45: 'minus', 46: 'period', 47: 'forwardslash', 48: 'zero', 49: 'one', 50: 'two', 51: 'three', 52: 'four', 53: 'five', 54: 'six', 55: 'seven', 56: 'eight', 57: 'nine', 58: 'colon', 59: 'semicolon', 60: 'lessthan', 61: 'equals', 62: 'greaterthan', 63: 'questionmark', 64: 'at', 65: 'a', 66: 'b', 67: 'c', 68: 'd', 69: 'e', 70: 'f', 71: 'g', 72: 'h', 73: 'i', 74: 'j', 75: 'k', 76: 'l', 77: 'm', 78: 'n', 79: 'o', 80: 'p', 81: 'q', 82: 'r', 83: 's', 84: 't', 85: 'u', 86: 'v', 87: 'w', 88: 'x', 89: 'y', 90: 'z', 91: 'opensquarebracket', 92: 'backslash', 93: 'closesquarebracket', 94: 'caret', 95: 'underline', 96: 'leftquote', 97: 'numpaddivide', 98: 'numpadtimes', 99: 'numpadminus', 100: 'numpadplus', 101: 'enter', 102: 'numpadperiod', 112: 'numpadzero', 113: 'numpadone', 114: 'numpadtwo', 115: 'numpadthree', 116: 'numpadfour', 117: 'numpadfive', 118: 'numpadsix', 119: 'numpadseven', 120: 'numpadeight', 121: 'numpadnine', 123: 'openbrace', 124: 'pipe', 125: 'closebrace', 126: 'tilde', 128: 'up', 129: 'down', 130: 'left', 131: 'right', 132: 'pageup', 133: 'pagedown', 134: 'insert', 135: 'delete', 136: 'home', 137: 'end', 144: 'f1', 145: 'f2', 146: 'f3', 147: 'f4', 148: 'f5', 149: 'f6', 150: 'f7', 151: 'f8', 152: 'f9', 153: 'f10', 154: 'f11', 155: 'f12', 156: 'f13', 157: 'f14', 158: 'f15', 176: 'browser_back', 177: 'browser_forward', 178: 'browser_refresh', 179: 'browser_stop', 180: 'browser_search', 181: 'browser_favorites', 182: 'browser_home', 183: 'volume_mute', 184: 'volume_down', 185: 'volume_up', 186: 'next_track', 187: 'prev_track', 188: 'stop', 189: 'play_pause', 190: 'launch_mail', 191: 'launch_media_select', 192: 'launch_app1_pc_icon', 193: 'launch_app2_pc_icon', 194: 'launch_file_browser', 195: 'launch_media_center', 196: 'rewind', 197: 'fastforward', 198: 'record', 208: 'leftctrl', 209: 'rightctrl', 210: 'leftshift', 211: 'rightshift', 212: 'leftalt', 214: 'leftwindows', 215: 'rightwindows', 216: 'menu', 217: 'capslock', 218: 'numlock', 219: 'printscreen', 220: 'scrolllock', 221: 'pause', 222: 'power', 223: 'sleep', 224: 'guide', 225: 'settings', 226: 'info', 227: 'red', 228: 'green', 229: 'yellow', 230: 'blue', 231: 'zoom', 232: 'text', 233: 'favorites', 234: 'homepage', 235: 'config', 236: 'epg'}

def tr_keyboard(keycode):
	result = {"type":"keyboard"}

	mods = []
	keymod = keycode >> 16

	for mod in ModList:
		if keymod & 1 == 1:
			mods.append(mod)
		keymod >>= 1

	result["mods"] = mods

	try:
		result["keyname"] = KeyIndex[keycode & 0xFF]
	except KeyError:
		result["keyname"] = ""

	return result

def tr_remote(keycode):
	result = {"type":"remote","mods":[]}

	try:
		result["keyname"] = RemoteIndex[keycode]
	except KeyError:
		result["keyname"] = ""
	return result

def translate_keycode(keycode):
	if keycode & 0xF300 == 0xF000:
		return tr_keyboard(keycode)
	elif keycode < 256:
		return tr_remote(keycode)
	else:
		return None

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

RemoteIndex= {213: {'name': 'display', 'tr': 32815}, 226: {'name': 'reverse', 'tr': 32872}, 234: {'name': 'play', 'tr': 32861}, 227: {'name': 'forward', 'tr': 32826}, 221: {'name': 'skipminus', 'tr': 32882}, 224: {'name': 'stop', 'tr': 32887}, 230: {'name': 'pause', 'tr': 32860}, 223: {'name': 'skipplus', 'tr': 32883}, 229: {'name': 'title', 'tr': 32892}, 195: {'name': 'info', 'tr': 32831}, 166: {'name': 'up', 'tr': 32894}, 167: {'name': 'down', 'tr': 32816}, 169: {'name': 'left', 'tr': 32840}, 168: {'name': 'right', 'tr': 32874}, 11: {'name': 'select', 'tr': 32880}, 22: {'name': 'enter', 'tr': 32820}, 44: {'name': 'subtitle', 'tr': 32888}, 45: {'name': 'language', 'tr': 32833}, 247: {'name': 'menu', 'tr': 32847}, 216: {'name': 'back', 'tr': 32800}, 206: {'name': 'one', 'char': '1'}, 205: {'name': 'two', 'char': '2'}, 204: {'name': 'three', 'char': '3'}, 203: {'name': 'four', 'char': '4'}, 202: {'name': 'five', 'char': '5'}, 201: {'name': 'six', 'char': '6'}, 200: {'name': 'seven', 'char': '7'}, 199: {'name': 'eight', 'char': '8'}, 198: {'name': 'nine', 'char': '9'}, 207: {'name': 'zero', 'char': '0'}, 196: {'name': 'power', 'tr': 32864}, 49: {'name': 'mytv', 'tr': 32851}, 9: {'name': 'mymusic', 'tr': 32849}, 6: {'name': 'mypictures', 'tr': 32850}, 7: {'name': 'myvideo', 'tr': 32852}, 232: {'name': 'record', 'tr': 32868}, 37: {'name': 'start', 'tr': 32886}, 208: {'name': 'volumeplus', 'tr': 32899}, 209: {'name': 'volumeminus', 'tr': 32898}, 210: {'name': 'pageplus', 'tr': 32858}, 211: {'name': 'pageminus', 'tr': 32857}, 192: {'name': 'mute', 'tr': 32848}, 101: {'name': 'recordedtv', 'tr': 32869}, 24: {'name': 'livetv', 'tr': 32846}, 40: {'name': 'star', 'char': '*'}, 41: {'name': 'hash', 'char': '#'}, 249: {'name': 'clear', 'tr': 32811}, 250: {'name': 'teletext', 'tr': 32890}, 251: {'name': 'red', 'tr': 32870}, 252: {'name': 'green', 'tr': 32827}, 253: {'name': 'yellow', 'tr': 32900}, 254: {'name': 'blue', 'tr': 32802}, 255: {'name': 'playlist', 'tr': 32863}, 50: {'name': 'guide', 'tr': 32828}, 248: {'name': 'liveradio', 'tr': 32845}, 246: {'name': 'epgsearch', 'tr': 32822}, 235: {'name': 'eject', 'tr': 32818}, 236: {'name': 'contentsmenu', 'tr': 32813}, 237: {'name': 'rootmenu', 'tr': 32878}, 238: {'name': 'topmenu', 'tr': 32893}, 239: {'name': 'dvdmenu', 'tr': 32817}, 240: {'name': 'print', 'tr': 32866}}
KeyIndex= {8: {'name': 'backspace', 'tr': 32801}, 9: {'name': 'tab', 'tr': 32889}, 13: {'name': 'return', 'tr': 32871}, 27: {'name': 'escape', 'tr': 32823}, 32: {'name': 'space', 'tr': 32885}, 33: {'name': 'exclaim', 'char': '!'}, 34: {'name': 'doublequote', 'char': '"'}, 35: {'name': 'hash', 'char': '#'}, 36: {'name': 'dollar', 'char': '$'}, 37: {'name': 'percent', 'char': '%'}, 38: {'name': 'ampersand', 'char': '&'}, 39: {'name': 'quote', 'char': "'"}, 40: {'name': 'leftbracket', 'char': '('}, 41: {'name': 'rightbracket', 'char': ')'}, 42: {'name': 'asterisk', 'char': '*'}, 43: {'name': 'plus', 'char': '+'}, 44: {'name': 'comma', 'char': ','}, 45: {'name': 'minus', 'char': '-'}, 46: {'name': 'period', 'char': '.'}, 47: {'name': 'forwardslash', 'char': '/'}, 48: {'name': 'zero', 'char': '0'}, 49: {'name': 'one', 'char': '1'}, 50: {'name': 'two', 'char': '2'}, 51: {'name': 'three', 'char': '3'}, 52: {'name': 'four', 'char': '4'}, 53: {'name': 'five', 'char': '5'}, 54: {'name': 'six', 'char': '6'}, 55: {'name': 'seven', 'char': '7'}, 56: {'name': 'eight', 'char': '8'}, 57: {'name': 'nine', 'char': '9'}, 58: {'name': 'colon', 'char': ':'}, 59: {'name': 'semicolon', 'char': ';'}, 60: {'name': 'lessthan', 'char': '<'}, 61: {'name': 'equals', 'char': '='}, 62: {'name': 'greaterthan', 'char': '>'}, 63: {'name': 'questionmark', 'char': '?'}, 64: {'name': 'at', 'char': '@'}, 65: {'name': 'a', 'char': 'A'}, 66: {'name': 'b', 'char': 'B'}, 67: {'name': 'c', 'char': 'C'}, 68: {'name': 'd', 'char': 'D'}, 69: {'name': 'e', 'char': 'E'}, 70: {'name': 'f', 'char': 'F'}, 71: {'name': 'g', 'char': 'G'}, 72: {'name': 'h', 'char': 'H'}, 73: {'name': 'i', 'char': 'I'}, 74: {'name': 'j', 'char': 'J'}, 75: {'name': 'k', 'char': 'K'}, 76: {'name': 'l', 'char': 'L'}, 77: {'name': 'm', 'char': 'M'}, 78: {'name': 'n', 'char': 'N'}, 79: {'name': 'o', 'char': 'O'}, 80: {'name': 'p', 'char': 'P'}, 81: {'name': 'q', 'char': 'Q'}, 82: {'name': 'r', 'char': 'R'}, 83: {'name': 's', 'char': 'S'}, 84: {'name': 't', 'char': 'T'}, 85: {'name': 'u', 'char': 'U'}, 86: {'name': 'v', 'char': 'V'}, 87: {'name': 'w', 'char': 'W'}, 88: {'name': 'x', 'char': 'X'}, 89: {'name': 'y', 'char': 'Y'}, 90: {'name': 'z', 'char': 'Z'}, 91: {'name': 'opensquarebracket', 'char': '['}, 92: {'name': 'backslash', 'char': '\\'}, 93: {'name': 'closesquarebracket', 'char': ']'}, 94: {'name': 'caret', 'char': '^'}, 95: {'name': 'underline', 'char': '_'}, 96: {'name': 'leftquote', 'char': '`'}, 97: {'name': 'numpaddivide', 'char': 'NP /'}, 98: {'name': 'numpadtimes', 'char': 'NP *'}, 99: {'name': 'numpadminus', 'char': 'NP -'}, 100: {'name': 'numpadplus', 'char': 'NP +'}, 101: {'name': 'enter', 'tr': 32820}, 102: {'name': 'numpadperiod', 'tr': 32855}, 112: {'name': 'numpadzero', 'char': 'NP 0'}, 113: {'name': 'numpadone', 'char': 'NP 1'}, 114: {'name': 'numpadtwo', 'char': 'NP 2'}, 115: {'name': 'numpadthree', 'char': 'NP 3'}, 116: {'name': 'numpadfour', 'char': 'NP 4'}, 117: {'name': 'numpadfive', 'char': 'NP 5'}, 118: {'name': 'numpadsix', 'char': 'NP 6'}, 119: {'name': 'numpadseven', 'char': 'NP 7'}, 120: {'name': 'numpadeight', 'char': 'NP 8'}, 121: {'name': 'numpadnine', 'char': 'NP 9'}, 123: {'name': 'openbrace', 'char': '{'}, 124: {'name': 'pipe', 'char': '|'}, 125: {'name': 'closebrace', 'char': '}'}, 126: {'name': 'tilde', 'char': '~'}, 128: {'name': 'up', 'tr': 32894}, 129: {'name': 'down', 'tr': 32816}, 130: {'name': 'left', 'tr': 32840}, 131: {'name': 'right', 'tr': 32874}, 132: {'name': 'pageup', 'tr': 32859}, 133: {'name': 'pagedown', 'tr': 32856}, 134: {'name': 'insert', 'tr': 32832}, 135: {'name': 'delete', 'tr': 32814}, 136: {'name': 'home', 'tr': 32829}, 137: {'name': 'end', 'tr': 32819}, 144: {'name': 'f1', 'char': 'f1'}, 145: {'name': 'f2', 'char': 'f2'}, 146: {'name': 'f3', 'char': 'f3'}, 147: {'name': 'f4', 'char': 'f4'}, 148: {'name': 'f5', 'char': 'f5'}, 149: {'name': 'f6', 'char': 'f6'}, 150: {'name': 'f7', 'char': 'f7'}, 151: {'name': 'f8', 'char': 'f8'}, 152: {'name': 'f9', 'char': 'f9'}, 153: {'name': 'f10', 'char': 'f10'}, 154: {'name': 'f11', 'char': 'f11'}, 155: {'name': 'f12', 'char': 'f12'}, 156: {'name': 'f13', 'char': 'f13'}, 157: {'name': 'f14', 'char': 'f14'}, 158: {'name': 'f15', 'char': 'f15'}, 176: {'name': 'browser_back', 'tr': 32803}, 177: {'name': 'browser_forward', 'tr': 32805}, 178: {'name': 'browser_refresh', 'tr': 32807}, 179: {'name': 'browser_stop', 'tr': 32809}, 180: {'name': 'browser_search', 'tr': 32808}, 181: {'name': 'browser_favorites', 'tr': 32804}, 182: {'name': 'browser_home', 'tr': 32806}, 183: {'name': 'volume_mute', 'tr': 32896}, 184: {'name': 'volume_down', 'tr': 32895}, 185: {'name': 'volume_up', 'tr': 32897}, 186: {'name': 'next_track', 'tr': 32853}, 187: {'name': 'prev_track', 'tr': 32865}, 188: {'name': 'stop', 'tr': 32887}, 189: {'name': 'play_pause', 'tr': 32862}, 190: {'name': 'launch_mail', 'tr': 32837}, 191: {'name': 'launch_media_select', 'tr': 32839}, 192: {'name': 'launch_app1_pc_icon', 'tr': 32834}, 193: {'name': 'launch_app2_pc_icon', 'tr': 32835}, 194: {'name': 'launch_file_browser', 'tr': 32836}, 195: {'name': 'launch_media_center', 'tr': 32838}, 196: {'name': 'rewind', 'tr': 32873}, 197: {'name': 'fastforward', 'tr': 32824}, 198: {'name': 'record', 'tr': 32868}, 208: {'name': 'leftctrl', 'tr': 32842}, 209: {'name': 'rightctrl', 'tr': 32875}, 210: {'name': 'leftshift', 'tr': 32843}, 211: {'name': 'rightshift', 'tr': 32876}, 212: {'name': 'leftalt', 'tr': 32841}, 214: {'name': 'leftwindows', 'tr': 32844}, 215: {'name': 'rightwindows', 'tr': 32877}, 216: {'name': 'menu', 'tr': 32847}, 217: {'name': 'capslock', 'tr': 32810}, 218: {'name': 'numlock', 'tr': 32854}, 219: {'name': 'printscreen', 'tr': 32867}, 220: {'name': 'scrolllock', 'tr': 32879}, 221: {'name': 'pause', 'tr': 32860}, 222: {'name': 'power', 'tr': 32864}, 223: {'name': 'sleep', 'tr': 32884}, 224: {'name': 'guide', 'tr': 32828}, 225: {'name': 'settings', 'tr': 32881}, 226: {'name': 'info', 'tr': 32831}, 227: {'name': 'red', 'tr': 32870}, 228: {'name': 'green', 'tr': 32827}, 229: {'name': 'yellow', 'tr': 32900}, 230: {'name': 'blue', 'tr': 32802}, 231: {'name': 'zoom', 'tr': 32901}, 232: {'name': 'text', 'tr': 32891}, 233: {'name': 'favorites', 'tr': 32825}, 234: {'name': 'homepage', 'tr': 32830}, 235: {'name': 'config', 'tr': 32812}, 236: {'name': 'epg', 'tr': 32821}}

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

#!/usr/bin/python3

#	This file is part of PulseEqualizerGui for Kodi.
#
#	Copyright (C) 2021 wastis    https://github.com/wastis/PulseEqualizerGui
#
#	PulseEqualizerGui is free software; you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published
#	by the Free Software Foundation; either version 3 of the License,
#	or (at your option) any later version.
#

def check_control_list(cid, clist):
	for ctl in clist:
		if "attr" not in ctl: continue
		if "id" not in ctl["attr"]: continue
		print(ctl["attr"]["id"], cid)
		if ctl["attr"]["id"] == cid:
			return ctl

	if "control" in ctl:
		return check_control_list(cid,ctl["control"])

	return None

def find_control(cid, dic):
	try:
		return  check_control_list(cid, dic["window"][0]["controls"][0]["control"])
	except KeyError: return None

import time

def secondsToDuration(input):
	"""Formats the seconds to a duration string as used by XBMC.

	Keyword arguments:
	input -- the duration in seconds

	"""
	hours = input / 3600
	minutes = (input % 3600) / 60
	seconds = (input % 3600) % 60 

	return "%02d:%02d:%02d" % (hours, minutes, seconds)

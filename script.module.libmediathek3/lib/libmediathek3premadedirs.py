import urllib
import urllib2
import socket
import xbmc
import xbmcaddon
import xbmcvfs
import re
from datetime import date, timedelta

from libmediathek3utils import getTranslation as getTranslation


weekdayDict = { '0': getTranslation(31013),#Sonntag
				'1': getTranslation(31014),#Montag
				'2': getTranslation(31015),#Dienstag
				'3': getTranslation(31016),#Mittwoch
				'4': getTranslation(31017),#Donnerstag
				'5': getTranslation(31018),#Freitag
				'6': getTranslation(31019),#Samstag
			  }
	
def populateDirAZ(mode,ignore=[]):
	l = []
	if not '#' in ignore:
		d = {}
		d['mode'] = mode
		d['name'] = "#"
		d['type'] = 'dir'
		l.append(d)
	letters = [chr(i) for i in xrange(ord('a'), ord('z')+1)]
	for letter in letters:
		if not letter in ignore:
			d = {}
			d['mode'] = mode
			letter = letter.upper()
			d['name'] = letter
			l.append(d)
	return l
	
def populateDirDate(mode,channel=False,dateChooser=False):
	l = []
	d = {}
	d['mode'] = mode
	d['type'] = 'dir'
	if channel: d['channel'] = channel
	d['name'] = getTranslation(31020)
	d['datum'] = '0'
	d['yyyymmdd'] = _calcyyyymmdd(0)
	
	
	l.append(d)
	
	d = {}
	d['mode'] = mode
	d['type'] = 'dir'
	if channel: d['channel'] = channel
	d['name'] = getTranslation(31021)
	d['datum']  = '1'
	d['yyyymmdd'] = _calcyyyymmdd(1)
	l.append(d)
	
	i = 2
	while i <= 6:
		d = {}
		day = date.today() - timedelta(i)
		d['name'] = weekdayDict[day.strftime("%w")]
		d['datum']  = str(i)
		d['mode'] = mode
		d['type'] = 'dir'
		if channel: d['channel'] = channel
		d['yyyymmdd'] = _calcyyyymmdd(i)
		l.append(d)
		i += 1
	if dateChooser:
		d = {}
		d['mode'] = mode
		d['type'] = 'dir'
		if channel: d['channel'] = channel
		d['name'] = getTranslation(31022)
		l.append(d)
	return l
	
def _calcyyyymmdd(d):
	day = date.today() - timedelta(d)
	return day.strftime('%Y-%m-%d')


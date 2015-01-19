#!/usr/bin/python
# -*- coding: utf-8 -*-
#/*
# *      Copyright (C) 2005-2013 Team XBMC
# *      http://xbmc.org
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, see
# *  <http://www.gnu.org/licenses/>.
# *
# */

import os, re, sys, time
from threading import Thread

class WorkerThread(Thread):
	def __init__ (self, execPath):
		Thread.__init__(self)
		self.execPath = execPath
		self.stdout_value = ""
		self.stderr_value = ""
		self.retCode = 0

	def readFile(self, the_file):
		f = file(the_file, 'r')
		content = f.read()
		f.close()
		return content

	def run(self):
		"""
		# Not currently supported
		process = subprocess.Popen(self.execPath, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
		self.stdout_value, self.stderr_value = process.communicate()
		self.retCode = process.returncode
		"""

		"""
		# Not currently supported
		theFile = tempfile.NamedTemporaryFile(delete=False)
		stdoutTempFileName = theFile.name
		theFile.close()
		theFile = tempfile.NamedTemporaryFile(delete=False)
		stderrTempFileName = theFile.name
		theFile.close()
		"""

		# os.system always returns -1, hence the hack
		retCodeTempFileName = "/tmp/tmpRetcode"
		stdoutTempFileName = "/tmp/tmpStdout"
		stderrTempFileName = "/tmp/tmpStderr"

		os.system('bash -c "' + self.execPath + ' > ' + stdoutTempFileName + ' 2> ' + stderrTempFileName + '"; echo $? > ' + retCodeTempFileName)
		retCode = self.readFile(retCodeTempFileName)[:-1]

		self.retCode = int(retCode)
		self.stdout_value = self.readFile(stdoutTempFileName)[:-1]
		self.stderr_value = self.readFile(stderrTempFileName)[:-1]

		os.unlink(retCodeTempFileName)
		os.unlink(stdoutTempFileName)
		os.unlink(stderrTempFileName)

	def isRunning(self):
	      return self.running

	def getResults(self):
	      return self.retCode, self.stdout_value, self.stderr_value 

class alsaMixerCore:
	gDebugMode = 0
	controls = {}

	def __init__( self, debugLevel):
		self.gDebugMode = debugLevel
		self.__printDebugLine("alsaMixerCore start")

	def checkPlatform(self):
		if not sys.platform.startswith('linux'):
			 self.__printDebugLine("Invalid platform: " + sys.platform)
			 return 0

		# Check for external helpers
		stdErr, stdOut, retValue = self.__runSilent("which amixer")
		if len(stdOut)==0:
			self.__printDebugLine("Missing packages: amixer")
			return 0

		return 1

	def hasVolume(self, aControl):
		return self.controls[aControl][1]

	def hasSwitch(self, aControl):
		return self.controls[aControl][2]

	def getVolume(self, aControl):
		aVolume = self.controls[aControl][0]
		if aVolume < 0 :
			aCmd = "amixer get " + aControl
			stdErr, controlStatus, retValue = self.__runSilent(aCmd)
			outputLines = controlStatus.splitlines()
			lastLine = outputLines[len(outputLines)-1]

			values = re.findall("\[(.*?)\]" , lastLine)
			aVolume = values[len(values)-1]
			if self.hasVolume(aControl) and aVolume != "off":
				aVolume = values[0].replace('%','')

			self.controls[aControl][0] = aVolume
		return aVolume

	def setVolume(self, aControl, aVolume):
		retValue = 1
		if aVolume == "on" or aVolume == "off":
			aCmd = "amixer set %s %s" % (aControl,aVolume)
			stdErr, stdOut, retValue = self.__runSilent(aCmd)
			return retValue

		if self.hasVolume(aControl):
			aCmd = "amixer set " + aControl + " " + aVolume + "%"
			stdErr, stdOut, retValue = self.__runSilent(aCmd)

		self.controls[aControl][0] = aVolume
		return retValue

	def getPlaybackControls(self):
		stdErr, stdOut, retValue = self.__runSilent("amixer scontrols")
		if len(stdOut)==0:
			return ""

		#
		# TODO use a regexp to get all controls in one shot
		#
		outputLines = stdOut.splitlines()

		channels = ""
		for aMixer in outputLines:
			nameStart = aMixer.find("'")
			mixername= aMixer[nameStart:]

			volLevel = -1
			hasVol = False
			hasSw = False
			if nameStart>0:
				stdErr, stdOut, retValue = self.__runSilent("amixer sget " + mixername)
				if stdOut.find("pvolume") > 0:
					hasVol=True
				if stdOut.find("pswitch") > 0:
					hasSw = True
				if hasVol or hasSw:
					channels = channels + mixername + "|"
					self.controls[mixername] = [volLevel, hasVol, hasSw]

		return channels[:(len(channels) - 1)].split("|")

	def __printDebugLine(self, aLine):
		if self.gDebugMode>0:
			print aLine

	def __runSilent(self, aCmdline):
		self.__printDebugLine("Running: " + aCmdline)
		
		execution = WorkerThread(aCmdline)
		execution.start()

		while execution.isAlive():
			time.sleep(0.001)

		retCode, stdout_value, stderr_value = execution.getResults()

		self.__printDebugLine(" -D- Return code= " + str(retCode))
		self.__printDebugLine(" -D- Results: StdOut=" + repr(stdout_value))
		self.__printDebugLine(" -D- Results: StdErr=" + repr(stderr_value))
		return stderr_value, stdout_value, retCode

if __name__ == '__main__':
	from optparse import OptionParser

	usage = """usage: %prog [options] arg
	Examples:
		To get the list of alsa controls:
			%prog

		To set the volume level (on|off|percentage):
			%prog -c 'Master',0 -s off|on|90
		
		To query the volume level (returns: percentage|on|off):
			%prog -c 'Master',0

		To query the control type, ie if the control has volume level (returns: yes|no):
			%prog -c 'Master',0 -t

	"""
	parser = OptionParser(usage)
	parser.add_option("-c", "--control", dest="mixerControl")
	parser.add_option("-s", "--set", action="store_true", dest="setVolume")
	parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
	parser.add_option("-t", "--type", action="store_true", dest="queryType")

	(options, args) = parser.parse_args()

	if options.verbose:
		alsaCore = alsaMixerCore(1)
	else:
		alsaCore = alsaMixerCore(0)

	try:
		if alsaCore.checkPlatform() == 0:
			print "Unsupported platform!"
		else:
			if options.mixerControl:
				if options.setVolume:
					if len(args) != 1:
						parser.error("Please specify a volume level.")
					else:
						if alsaCore.setVolume(options.mixerControl, args[0]):
							print "Error setting volume, check values"
						else:
							print "Control:" + options.mixerControl + " - Volume set at " + args[0]
				elif options.queryType:
					if alsaCore.hasVolume(options.mixerControl):
						print "Control has volume capabilities."
					else:
						print "Control does not have volume capabilities."
				else:
					print "Volume = " + alsaCore.getVolume(options.mixerControl)
			else:
				controls = alsaCore.getPlaybackControls()
				for aControl in controls:
					print "Control=<" + aControl + ">"
					print "HasVolume=<" + str(alsaCore.hasVolume(aControl)) + ">"
					if alsaCore.hasVolume(aControl):
						print "Volume = " + alsaCore.getVolume(aControl) + " %"
					if alsaCore.hasSwitch(aControl):
						print "Switchable = YES"
					else:
						print "Switchable = NO"

	except Exception, error:
		print "ErrorCode:" + str(error)
		eCode = int(str(error))


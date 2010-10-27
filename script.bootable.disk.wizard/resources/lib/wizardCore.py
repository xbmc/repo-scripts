#!/usr/bin/env python
# -*- coding: utf-8 -*-
# *
# *      Copyright (C) 2005-2010 Team XBMC
# *      http://www.xbmc.org
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
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */


import tempfile
import os, re, sys, time
import subprocess
import random
import shutil
import statvfs
import optparse
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

class WizardCore:
	const_minSizeMB = 800
	const_permStorageFilename = "live-rw"
	const_rootFS = "live/filesystem.squashfs"
	const_skipLargeFiles = False

	bootDisk = None
	gDebugMode = 0
	udev_helper = None

	def __init__( self, debugLevel):
		print "Wizard start"
		self.gDebugMode = debugLevel
		self.gDebugMode = 1 # TODO Remove when xbmc.LOGDEBUG can be set from GUI
		self.statusUpdater = self.__updateProgress

	def checkPlatform(self):
		if not sys.platform.startswith('linux'):
			 self.__printDebugLine("Invalid platform: " + sys.platform)
			 return 0

		# Check for external helpers
		stdErr, stdOut, retValue = self.__runSilent("which devkit-disks")
		if len(stdOut)==0:
			stdErr, stdOut, retValue = self.__runSilent("which udisks")
			if len(stdOut)==0:
				self.__printDebugLine("Missing packages: devkit-disks/udisks")
				return 0
			else:
				self.__printDebugLine("Using package: udisks")
				self.udev_helper = "udisks"
		else:
			self.__printDebugLine("Using package: devkit-disks")
			self.udev_helper = "devkit-disks"

		stdErr, stdOut, retValue = self.__runSilent("which grub-install")
		if len(stdOut)==0:
			 self.__printDebugLine("Missing package: grub-install")
			 return 0
		stdErr, stdOut, retValue = self.__runSilent("which parted")
		if len(stdOut)==0:
			 self.__printDebugLine("Missing package: parted")
			 return 0
		stdErr, stdOut, retValue = self.__runSilent("which mkfs.vfat")
		if len(stdOut)==0:
			 self.__printDebugLine("Missing package: mkfs.vfat")
			 return 0
		stdErr, stdOut, retValue = self.__runSilent("which mkfs.ext3")
		if len(stdOut)==0:
			 self.__printDebugLine("Missing package: mkfs.ext3")
			 return 0

		# Check for os.path.islink
		print "Checking /vmlinuz (is symlink) ..."
		if not os.path.islink("/vmlinuz"):
			self.__printDebugLine("os.path.islink does not return a correct value!")



		# TODO Check for grub version

		return 1

	def getMinDiskSize(self):
		return self.const_minSizeMB

	def findLiveDirectory(self, customLiveDirectory=""):
		mountPath = customLiveDirectory
		if customLiveDirectory is "":
			mountPath = "/live/image/"

		if not os.path.exists(mountPath + self.const_rootFS):
			self.__printDebugLine("File does not exist: " + mountPath + self.const_rootFS)
			return None

		# Avoid comparing with the trailing slash
		stdErr, bootVolume, retValue = self.__runSilent("mount | grep " + mountPath[:-1] + " | cut -d' ' -f 1")
		self.bootDisk = bootVolume
		if bootVolume.find("/dev/sd")>=0:
			self.bootDisk = bootVolume[:-1]
		return mountPath

	def findRemovableDisks(self):
		suitableDevices = []
		stdErr, tuples, retValue = self.__runSilent(self.udev_helper + " --enumerate-device-files | grep -v /by-")

		devices = tuples.splitlines()
		for device in devices:
			print "Dev=" + str(device) + " - Boot=" + str(self.bootDisk)
			if not device == self.bootDisk:
				stdErr, tuples, retValue = self.__runSilent(self.udev_helper + " --show-info " + device)
				outList = tuples.splitlines()
				isRemovable = self.__findProperty(outList, "removable")
				if isRemovable == "1":
					fstype = self.__findProperty(outList, "type")
					if not fstype == "iso9660":
						vendor = self.__findProperty(outList, "vendor")
						model = self.__findProperty(outList, "model")
						size = self.__findProperty(outList, "size")
						sizeMB = int(size)/(1024*1024)
						if sizeMB >= self.const_minSizeMB:
							aString = device + " - " + vendor + " " + model + " - " + str(sizeMB) + " MB"
							suitableDevices.append(aString)
		return suitableDevices

	def getMaxPermStorageSize(self, aDevice):
		stdErr, tuples, retValue = self.__runSilent(self.udev_helper + " --show-info " + aDevice)
		outList = tuples.splitlines()
		diskSize = self.__findProperty(outList, "size")
		if diskSize == None:
			  return 0

		diskSizeMB = int(int(diskSize)/(1024*1024.0))
		# TODO get size of system disk files and check dynamically instead of statically set it to 500
		maxSize = diskSizeMB - 500
		if maxSize<=0:
			return 0

		# Leave space for a (large?) profile directory
		maxSize = maxSize - 200
		if maxSize<=0:
			return 0

		if maxSize > 4000:
			maxSize = 4000
		return maxSize

	def createBootableDisk(self, liveDirectory, targetDevice, storageSizeMB, aPassword, updateStatusHook=None):
		if not updateStatusHook == None:
			self.statusUpdater = updateStatusHook

		# remove a trailing slash if it exists
		if liveDirectory[-1:] == "/":
			liveDirectory = liveDirectory[0:-1]

		self.statusUpdater(1, 0)

		aCmd = "mount"
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		outputLines = stdOut.splitlines()
		for mountedDevice in outputLines:
			if mountedDevice.find(targetDevice)>=0:
				aDevice = (mountedDevice.split(' '))[0]
				aCmd = 'echo "' + aPassword + '" | sudo -S umount ' + aDevice
				stdErr, stdOut, retValue = self.__runSilent(aCmd)
				if retValue >0:
					raise RuntimeError("-99")

		self.statusUpdater(1, 1)

		retValue = self.__partitionFormatDisk(targetDevice, aPassword)
		if not retValue:
			raise RuntimeError("1")

		self.__runSilent("sync")

		# XBMC in standalone mode may mount the newly created partition
		# I wish there could be a way to temporaily inhibit automounting
		aCmd = self.udev_helper + " --mount " + targetDevice + "1"
		stdErr, stdOut, retValue = self.__runSilent(aCmd)

		aCmd = "mount | grep " + targetDevice + "1"
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue==0:
			# TODO make it locale-indipendent
			mountPoint = stdOut[stdOut.find("on") + 3:stdOut.find("type") - 1]
		else:
			raise RuntimeError("99")

		self.statusUpdater(2, 10)
		retValue = self.__copyFiles(liveDirectory, mountPoint, 10, 70)
		if not retValue:
			raise RuntimeError("2")

		self.__runSilent("sync")

		self.statusUpdater(3, 70)
		retValue = self.__installGRUB(targetDevice, mountPoint, aPassword)
		if not retValue:
			raise RuntimeError("3")

		self.__runSilent("sync")

		self.statusUpdater(4, 85)

		if storageSizeMB>0:
			retValue = self.__createPermStorage(storageSizeMB, mountPoint)
			if not retValue:
				raise RuntimeError("4")

			self.__runSilent("sync")

		aCmd = self.udev_helper + " --unmount " + targetDevice + "1"
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			raise RuntimeError("5")

		self.statusUpdater(4, 100)

	def __findProperty(self, aList, aToken):
		aProperty = None
		expr = re.compile(aToken)
		for text in aList:
			match = expr.search(text)
			if match != None:
				aProperty = match.string
				aProperty = (aProperty[aProperty.find(":")+1:]).strip()
				break
		return aProperty

	def __installGRUB(self, aTargetDevice, aMountPoint, aPassword):
		aCmd = 'echo "' + aPassword + '" | sudo -S grub-install --force --recheck --root-directory=' + aMountPoint + " " + aTargetDevice
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue>0:
			self.__printDebugLine("Error installing GRUB: " + stdOut)
			return False

		return True

	def __createPermStorage(self, storageSizeMB, mountPoint):
		aFilename = mountPoint + "/" + self.const_permStorageFilename
		aCmd = "dd if=/dev/zero of=" + aFilename + " bs=4M count=" + str(int(storageSizeMB)/4)
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			return False

		aCmd = "mkfs.ext3 -F " + aFilename
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			return False

		self.__runSilent("sync")
		return True

	def __partitionFormatDisk(self, aDevice, aPassword):
		aCmd = 'echo "' + aPassword + '" | sudo -S parted -s ' + aDevice + ' mklabel msdos'
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			self.__printDebugLine("Error partitioning (1): " + stdOut)
			return False

		aCmd = 'echo "' + aPassword + '" | sudo -S parted -s ' + aDevice + ' mkpart primary fat32 0.0 100%'
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			self.__printDebugLine("Error partitioning (2): " + stdOut)
			return False

		aCmd = 'echo "' + aPassword + '" | sudo -S parted -s ' + aDevice + ' set 1 boot on'
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			self.__printDebugLine("Error partitioning (3): " + stdOut)
			return False

		aCmd = 'echo "' + aPassword + '" | sudo -S parted -s ' + aDevice + ' set 1 lba off'
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			self.__printDebugLine("Error partitioning (4): " + stdOut)
			return False

		aLabel = "XBMCLive_" + str(random.randint(0, 99))
		aCmd = "echo " + aPassword + " | sudo -S mkfs.vfat -I -F 32 -n " + aLabel + " " + aDevice + "1"
		stdErr, stdOut, retValue = self.__runSilent(aCmd)
		if retValue >0:
			self.__printDebugLine("Error formatting: " + stdOut)
			return False

		return True

	def __copyFiles(self, srcDirectory, dstDirectory, percStart, percEnd):
		result = True
		# Get src disk size
		srcSize = 0
		for root, dirs, files in os.walk(srcDirectory):
			### Following code is provisional, keep until os.path.islink is fixed
			for aDir in dirs:
				if aDir == "debian":
					 dirs.remove(aDir)
			###

			for file in files:
				if file == self.const_permStorageFilename:
					continue

				# Speeds up debugging  - TODO Remove
				if self.const_skipLargeFiles == True:
					if file.find("ext3") > 0:
						self.__printDebugLine("TEST MODE: file skipped.")
						continue
					if file.find("squashfs") > 0:
						self.__printDebugLine("TEST MODE: file skipped.")
						continue

				filename = os.path.join(root, file)
				srcSize += os.path.getsize(filename)

		srcSizeMB = int(srcSize/(1024*1024.0))
		self.__printDebugLine("Total size of files to copy: " + str(srcSizeMB) + " MB")

		destSize = 0
		for root, dirs, files in os.walk(srcDirectory):
			### Following code is provisional, keep until os.path.islink is fixed
			for aDir in dirs:
				if aDir == "debian":
					 dirs.remove(aDir)
			###

			for file in files:
				percentage = percStart + int((destSize/(srcSize*1.0))*(percEnd*1.0 - percStart))

				from_ = os.path.join(root, file)
				to_ = from_.replace(srcDirectory, dstDirectory, 1)
				to_directory = os.path.split(to_)[0]

				# Do not copy storage file
				if file == self.const_permStorageFilename:
					continue

				# Speeds up debugging  - TODO Remove
				if self.const_skipLargeFiles == True:
					if file.find("ext3") > 0:
						self.__printDebugLine("TEST MODE: file skipped.")
						continue
					if file.find("squashfs") > 0:
						self.__printDebugLine("TEST MODE: file skipped.")
						continue

				if not os.path.exists(to_directory):
					os.makedirs(to_directory)

				fileSize = os.path.getsize(from_)
				destSize += fileSize
				self.statusUpdater(2, percentage, file + " (" + str(int(fileSize/(1024*1024.0))) + " MB)")

				try:
					shutil.copyfile(from_, to_)
				except:
					self.__printDebugLine("Error copying file: " + file + " - check your media")
					result = False
					continue

		if not os.path.exists(dstDirectory + "/" + "Hooks"):
			os.mkdir(dstDirectory + "/" + "Hooks")

		return result

	def __updateProgress(self, step, percentage = None, strItem = None):
		stepDescription = {
		  1: "Formatting disk...",
		  2: "Copying files...",
		  3: "Installing bootloader...",
		  4: "Creating permanent storage..."
		}[step]

		statusString = "Step #" + str(step) + " - " + stepDescription
		if not strItem == None:
			  statusString = statusString + " - " + strItem
		if not percentage == None:
			  statusString = statusString + " - " + str(percentage) + "%"

		self.__printDebugLine(statusString)

	def __printDebugLine(self, aLine):
		if self.gDebugMode > 0:
			print aLine

	def __runSilent(self, aCmdline):
		self.__printDebugLine("Running: " + aCmdline)

		execution = WorkerThread(aCmdline)
		execution.start()

		while execution.isAlive():
			time.sleep(0.001)

		retCode, stdout_value, stderr_value = execution.getResults()

		self.__printDebugLine("Return code= " + str(retCode))
		self.__printDebugLine("Results: StdOut=" + repr(stdout_value))
		self.__printDebugLine("Results: StdErr=" + repr(stderr_value))
		return stderr_value, stdout_value, retCode

if __name__ == '__main__':
	import getpass

	wCore = WizardCore(1)

	targetDevice = sys.argv[1]
	liveDirectory = sys.argv[2]
	storageSizeMB = sys.argv[3]
	print "Installing to: " + targetDevice
	print "Original files from: " + liveDirectory
	print "Permanent storage size: " + storageSizeMB
	aPassword = getpass.getpass("Pls type your password: ")

	try:
		if wCore.checkPlatform() == 0:
			print "Unsupported platform!"
		else:
			if wCore.findLiveDirectory(liveDirectory) == None:
				print "Invalid live directory!"
			else:
				wCore.createBootableDisk(liveDirectory, targetDevice, storageSizeMB, aPassword)
	except Exception, error:
		print "ErrorCode:" + str(error)
		eCode = int(str(error))
		print "An error has occurred: " + str(eCode)

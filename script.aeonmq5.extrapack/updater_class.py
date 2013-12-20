import dialogprogress
import os
import re
import shutil
import signal
import sys
from threading import Thread, activeCount
import time
import unicodedata
import urllib
import urllib2
import xbmc
import xbmcaddon
import xbmcgui

__addon__     = xbmcaddon.Addon()
__scriptname__ = __addon__.getAddonInfo('name')

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

class SVNDir(Thread):
	def __init__ ( self, obj, path ):
		Thread.__init__( self )
		self.path = path
		self.obj = obj
		self.status = -1
	def run(self):
		fnc = self.obj.SVNLookup(self.path)
		self.status = fnc
	
class UpdaterThread(Thread):
	def __init__ ( self, obj ):
		Thread.__init__( self )
		self.obj = obj
		self.status = -1
	def run(self):
		fnc = self.obj.Update()
		self.status = fnc		
		time.sleep(1)

class SVNDownload(Thread):
	def __init__ (self, obj, file):
		Thread.__init__(self)
		self.file = file
		self.obj = obj
		self.status = -1
		
	def run(self):
		#try:
		fnc = self.obj.DownloadUpdate(self.file)
		self.status = fnc
		#except:
			#self.log('Error in SVNDownload')
			#self.exit()
		

class Updater:
	
	def log(self, msg):
		msg = normalizeString(msg)
		xbmc.log(u"### [%s] - %s" % (__scriptname__,msg),level=xbmc.LOGDEBUG )

	def Language(self, language):
		self.Language = language
			
	def SVNLookup(self, path):
		self.log('SVNLookup')
		if (path == ''):
			path = self.SVNPathAddress
		self.log('path = ' +path)
		
		SVNhtml = self.DownloadSVNHTML(path)
		files = re.findall("<a href=\"([_A-Za-z0-9\(\)-.\s%]*?)\">",SVNhtml)
		for file in files:
			if(not path.endswith('/')):
				path = path + '/'
			newPath = path +file
			self.SVNFileList.append(newPath)
		
		count = 0
		for sub_path in re.findall("<a href=\"([^.]*?)/\">",SVNhtml):
			count = count + 1
			if(not path.endswith('/')):
				path = path + '/'
			
			current = SVNDir(self, path +sub_path)
			self.SVNThreads.append(current)
			current.start()
		return 1

		
	def DownloadSVNHTML(self, path):
		self.log('DownloadSVNHTML')
		try:
			html = urllib2.urlopen(path).read()
			return html
		except:
			time.sleep(2)
			try:
				html = urllib2.urlopen(self.SVNPathAddress+urllib.quote(path)+"?limit_changes=0").read()
				return html
			except:
				self.log("Failed to download changes.")
				sys.exit(0)


	def CleanDirectory(self, directory):
		try:
			for root, dirs, files in os.walk(directory, topdown=False):
				for items in dirs:
					shutil.rmtree(os.path.join(root, items), ignore_errors=True, onerror=None)
				for name in files:
					os.remove(os.path.join(root, name))
		except Exception, (exc):
			self.log("Error while cleaning directory: " +str(exc))
			try:
				for root, dirs, files in os.walk(directory, topdown=False):
					for items in dirs:
						try:
							shutil.rmtree(os.path.join(root, items).decode("utf-8"), ignore_errors=True, onerror=None)
						except Exception, (exc):
							self.log("Error while cleaning directory: " +str(exc))
					for name in files:
						try:
							os.remove(os.path.join(root, name).decode("utf-8"))
						except Exception, (exc):
							self.log("Error while cleaning directory: " +str(exc))
			except Exception, (exc):
				self.log("Error while cleaning directory: " +str(exc))
				pass

				
	def MakeDirectories(self):
		self.log('MakeDirectories')		
		self.BackupDir = os.path.join(self.BackupBasePath, "r"+str(self.CurrentRevision)+"-r"+str(self.HeadRevision))		
		self.log('BackupDir: ' +self.BackupDir)
		self.log('UpdateTempDir: ' +self.UpdateTempDir)
		self.log('UpdateTargetPath: ' +self.UpdateTargetPath)
		if not os.path.isdir(self.BackupDir): os.makedirs(self.BackupDir)
		if not os.path.isdir(self.UpdateTempDir): os.makedirs(self.UpdateTempDir)
		else: self.CleanDirectory(self.UpdateTempDir)
		if not os.path.isdir(self.UpdateTargetPath): os.makedirs(self.UpdateTargetPath)		

		
	def MakeBackup(self, file):
		if self.createBackups:
			self.log('MakeBackup')
			file = file.replace(self.SVNPathAddress,"")
			OriginalFilePath = os.path.join(self.UpdateTargetPath,file)
			BackupFilePath = os.path.join(self.BackupDir,file)
			if os.path.isfile(OriginalFilePath.decode('utf-8')):
				BackupFileDir = os.path.split(BackupFilePath)[0]
				if not os.path.isdir(BackupFileDir):
					os.makedirs(BackupFileDir)
				shutil.copy(OriginalFilePath.decode("utf-8"), BackupFileDir.decode("utf-8"))
		return 1

		
	def DownloadUpdate(self, file):
		self.log('Downloading: %s' % file)
		dirfile = os.path.join(self.UpdateTempDir,file)
		dirname, filename = os.path.split(dirfile)
		if not os.path.isdir(dirname):
			try:
				os.makedirs(dirname)
			except:
				self.log('Error creating directory: '  +dirname)
		url = self.SVNPathAddress+urllib.quote(file)
		try:
			if re.findall(".xbt",url):
				self.totalsize = int(re.findall("File length: ([0-9]*)",urllib2.urlopen(url+"?view=log").read())[0])
				urllib.urlretrieve( url.decode("utf-8"), dirfile.decode("utf-8"))
			else: urllib.urlretrieve( url.decode("utf-8"), dirfile.decode("utf-8") )
			self.DownloadedFiles.append(urllib.unquote(url))
			return 1
		except:
			try:
				time.sleep(2)
				if re.findall(".xbt",url):
					self.totalsize = int(re.findall("File length: ([0-9]*)",urllib2.urlopen(url+"?view=log").read())[0])
					urllib.urlretrieve(url.decode("utf-8"), dirfile.decode("utf-8"))
				else: urllib.urlretrieve(url.decode("utf-8"), dirfile.decode("utf-8") )
				urllib.urlretrieve(url.decode("utf-8"), dirfile.decode("utf-8"))
				self.DownloadedFiles.append(urllib.unquote(url))
				return 1
			except:
				self.log("Download failed: %s" % url)
				self.DownloadFailedFiles.append(urllib.unquote(url))
				return 0

				
	def MoveUpdate(self, file):
		self.log('MoveUpdate')
		try:
			file = file.replace(self.SVNPathAddress,"")
			updated_file_path = os.path.join(self.UpdateTempDir,file)
			OriginalFilePath = os.path.join(self.UpdateTargetPath,file)
			if os.path.isfile(updated_file_path.decode('utf-8')):
				if not os.path.isdir(os.path.split(OriginalFilePath)[0]):
					os.makedirs(os.path.split(OriginalFilePath)[0])
				shutil.move(updated_file_path.decode("utf-8"),OriginalFilePath.decode("utf-8"))
				return 1
			else: 
				self.log('Could not find file: ' +updated_file_path)
				return 0
		except Exception, (exc):
			self.log('Error while moving file: ' +str(exc))
			return 0
			
	def Update(self):
		self.log('Update')
		
		self.SVNFileList = []
		
		current = SVNDir(self, "") #SVNLookup
		self.SVNThreads.append(current)
		current.start()

		for t in self.SVNThreads:
			t.join()
		self.log( "Total Files: "+str(len(self.SVNFileList)))
		
		self.UpdatableFiles = []
		self.UpdateFailed = []
		XbtFiles = []
		
		#TODO File revision
		self.log("check which files already exist")
		for File in self.SVNFileList:
			if not re.findall(".xbt", File):
				#check if file already exists
				testFile = File.replace(self.SVNPathAddress,"")
				testFile = os.path.join(self.UpdateTargetPath,testFile)
				if os.path.isfile(testFile.decode('utf-8')):					
					self.log("file exists: " +testFile)
				else:
					self.UpdatableFiles.append(urllib.unquote(File))
			else:
				XbtFiles.append(urllib.unquote(File))

		LenFiles = len(self.UpdatableFiles)
		
		self.DownloadedFiles = []
		self.DownloadFailedFiles = []
		self.BackedUpFiles = []

		progressDialog = dialogprogress.ProgressDialogGUI()
		progressDialog.itemCount = len(self.UpdatableFiles)
		progressDialog.writeMsg(self.Language(31970).decode('utf-8'), "", "", 0)
		
		continueDownload = True
		
		for count, file in enumerate(self.UpdatableFiles):
			self.BackedUpFiles.append(self.MakeBackup(file))
			Flag = 1
			while Flag:
				if activeCount() < 20:
					file = file.replace(self.SVNPathAddress,"")
					continueDownload = progressDialog.writeMsg(self.Language(31970).decode('utf-8'), self.Language(31974).decode('utf-8') +file.decode('utf-8'), "", count)
					if not continueDownload:
						self.log("Download cancelled by user")
						break
					
					current = SVNDownload(self, file)
					self.SVNThreads.append(current)
					current.start()
					Flag = 0
			
			if not continueDownload:
				break
		
		for t in self.SVNThreads:
			t.join()
			self.log('join Threads')

			
		self.log('Threads joined')
			
		Errors = 0
		
		for f in self.UpdatableFiles:
			if not f in self.DownloadedFiles:
				Errors = 1
		
		if not Errors:
			LenFiles = len(self.DownloadedFiles)
			for count, file in enumerate(self.DownloadedFiles):
				MVStatus = self.MoveUpdate(file)
				if not MVStatus:
					Errors = 1

		print 'Errors (after MoveUpdate): ' +str(Errors)
					
		if not Errors:
			return 1
		else:
			return 0
		
		
	def HasUpdate(self):
		self.log('HasUpdate')
		
		try:
			self.HeadRevision = int(re.findall("mod-skin - Revision ([0-9]+):",urllib2.urlopen(self.SVNPathAddress).read())[0])
			self.log("Remote Rev: "+str(self.HeadRevision))
		except:
			self.log("Failed to determine HEAD revision.")
			return 0

		if self.CurrentRevision == self.HeadRevision or self.CurrentRevision > self.HeadRevision:
			self.log("Skin Aeon MQ 5 updated")
			return 0
		
		self.MakeDirectories()
		return 1


		
	def __init__(self):
		self.WINDOW = xbmcgui.Window( 10000 )
		self.SVNThreads = []
		self.createBackups = False

		
	def __del__(self):
		for a in range(10):
			print "teste"
		time.sleep(2)
		
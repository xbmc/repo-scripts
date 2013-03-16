import urllib2, os, re, sys, shutil, urllib, time, xbmc, xbmcgui, xbmcaddon, signal
import urllib2, os, re, sys, shutil, urllib, time, xbmc, xbmcgui, xbmcaddon, signal
from threading import Thread, activeCount
import dialogprogress

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
			#xbmc.log('Error in SVNDownload')
			#self.exit()
		

class Updater(xbmcgui.Window):

	def Language(self, language):
		self.Language = language
			
	def SVNLookup(self, path):
		xbmc.log('SVNLookup')
		if (path == ''):
			path = self.SVNPathAddress
		xbmc.log('path = ' +path)
		
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
		xbmc.log('DownloadSVNHTML')
		try:
			html = urllib2.urlopen(path).read()
			return html
		except:
			time.sleep(2)
			try:
				html = urllib2.urlopen(self.SVNPathAddress+urllib.quote(path)+"?limit_changes=0").read()
				return html
			except:
				xbmc.log("Failed to download changes.")
				sys.exit(0)


	def CleanDirectory(self, directory):
		try:
			for root, dirs, files in os.walk(directory, topdown=False):
				for items in dirs:
					shutil.rmtree(os.path.join(root, items), ignore_errors=True, onerror=None)
				for name in files:
					os.remove(os.path.join(root, name))
		except Exception, (exc):
			xbmc.log("Error while cleaning directory: " +str(exc))
			try:
				for root, dirs, files in os.walk(directory, topdown=False):
					for items in dirs:
						try:
							shutil.rmtree(os.path.join(root, items).decode("utf-8"), ignore_errors=True, onerror=None)
						except Exception, (exc):
							xbmc.log("Error while cleaning directory: " +str(exc))
					for name in files:
						try:
							os.remove(os.path.join(root, name).decode("utf-8"))
						except Exception, (exc):
							xbmc.log("Error while cleaning directory: " +str(exc))
			except Exception, (exc):
				xbmc.log("Error while cleaning directory: " +str(exc))
				pass

				
	def MakeDirectories(self):
		xbmc.log('MakeDirectories')		
		self.BackupDir = os.path.join(self.BackupBasePath, "r"+str(self.CurrentRevision)+"-r"+str(self.HeadRevision))		
		xbmc.log('BackupDir: ' +self.BackupDir)
		xbmc.log('UpdateTempDir: ' +self.UpdateTempDir)
		xbmc.log('UpdateTargetPath: ' +self.UpdateTargetPath)
		if not os.path.isdir(self.BackupDir): os.makedirs(self.BackupDir)
		if not os.path.isdir(self.UpdateTempDir): os.makedirs(self.UpdateTempDir)
		else: self.CleanDirectory(self.UpdateTempDir)
		if not os.path.isdir(self.UpdateTargetPath): os.makedirs(self.UpdateTargetPath)		

		
	def MakeBackup(self, file):
		xbmc.log('MakeBackup')
		file = file.replace(self.SVNPathAddress,"")
		OriginalFilePath = os.path.join(self.UpdateTargetPath,file)
		BackupFilePath = os.path.join(self.BackupDir,file)
		if os.path.isfile(OriginalFilePath.decode('utf-8')):
			BackupFileDir = os.path.split(BackupFilePath)[0]
			if not os.path.isdir(BackupFileDir):
				os.makedirs(BackupFileDir)
			shutil.copy(OriginalFilePath.decode("utf-8"), BackupFileDir.decode("utf-8"))
			return 1
		else: return 1

		
	def DownloadUpdate(self, file):
		xbmc.log('DownloadUpdate')
		xbmc.log('file: ' +file)
		dirfile = os.path.join(self.UpdateTempDir,file)
		dirname, filename = os.path.split(dirfile)
		if not os.path.isdir(dirname):
			try:
				os.makedirs(dirname)
			except:
				xbmc.log('Error creating directory: '  +dirname)
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
				xbmc.log("File "+url+"donwload failed.")
				self.DownloadFailedFiles.append(urllib.unquote(url))
				return 0

				
	def MoveUpdate(self, file):
		xbmc.log('MoveUpdate')
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
				xbmc.log('Could not find file: ' +updated_file_path)
				return 0
		except Exception, (exc):
			xbmc.log('Error while moving file: ' +str(exc))
			return 0
			
	def Update(self):
		xbmc.log('Update')
		
		self.SVNFileList = []
		
		current = SVNDir(self, "") #SVNLookup
		self.SVNThreads.append(current)
		current.start()

		for t in self.SVNThreads:
			t.join()
		xbmc.log( "Total Files: "+str(len(self.SVNFileList)))
		
		self.UpdatableFiles = []
		self.UpdateFailed = []
		XbtFiles = []
		
		#TODO File revision
		xbmc.log("check which files already exist")
		for File in self.SVNFileList:
			if not re.findall(".xbt", File):
				#check if file already exists
				testFile = File.replace(self.SVNPathAddress,"")
				testFile = os.path.join(self.UpdateTargetPath,testFile)
				if os.path.isfile(testFile.decode('utf-8')):					
					xbmc.log("file exists: " +testFile)
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
				if activeCount() < 10:
					file = file.replace(self.SVNPathAddress,"")
					continueDownload = progressDialog.writeMsg(self.Language(31970).decode('utf-8'), self.Language(31974).decode('utf-8') +file.decode('utf-8'), "", count)
					if not continueDownload:
						xbmc.log("Download cancelled by user")
						break
					
					current = SVNDownload(self, file)
					self.SVNThreads.append(current)
					current.start()
					Flag = 0
			
			if not continueDownload:
				break
		
		for t in self.SVNThreads:
			t.join()
			xbmc.log('join Threads')

			
		xbmc.log('Threads joined')
			
		Errors = 0
		
		"""
		print 'UpdatableFiles: ' +str(self.UpdatableFiles)
		print 'DownloadedFiles: ' +str(self.DownloadedFiles)
		for f in self.UpdatableFiles:
			if not f in self.DownloadedFiles:
				xbmc.log("Error. Did not find file: " +f)
				Errors = 1
		
		print 'Errors: ' +str(Errors)
		"""
		
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
		xbmc.log('HasUpdate')
		
		try:
			self.HeadRevision = int(re.findall("mod-skin - Revision ([0-9]+):",urllib2.urlopen(self.SVNPathAddress).read())[0])
			xbmc.log("Remote Rev: "+str(self.HeadRevision))
		except:
			xbmc.log("Failed to determine HEAD revision.")
			return 0

		if self.CurrentRevision == self.HeadRevision or self.CurrentRevision > self.HeadRevision:
			xbmc.log("Skin Ace updated")
			return 0
		
		self.MakeDirectories()
			
		return 1


		
	def __init__(self):
		self.SVNThreads = []

		
	def __del__(self):
		for a in range(10):
			print "teste"
		time.sleep(2)
		
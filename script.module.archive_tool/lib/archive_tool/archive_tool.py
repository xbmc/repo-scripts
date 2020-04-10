'''
Archive tool for kodi

Simplest usage example:
import archive_tool

my_archive = archive_tool.archive_tool(archive_file = 'myfile.zip',directory_out = '/my/output_directory/') #Current archive object using vfs.libarchive

file_listing = my_archive.list_all() #Lists all files in the archive

file_listing = my_archive.stat_all() #Dict of all files in the archive containing fullpath, filename, file size (extracted)

files_extracted, success_of_extraction = my_archive.extract()  #Extracts all files to directory_out, returns list of files extracted and True/False for extraction success.  Defaults to extract all files in the archive.

or

files_extracted, success_of_extraction = my_archive.extract(files_to_extract=file_listing[0])  #Extracts only the listed file(s) in the archive to directory_out, returns list of files extracted and True/False for extraction success

Additional functions:

my_archive.archive_file('myfile2.zip') #Updates the currently set archive

my_archive.directory_out('/my/output_directory2/') #Updates the currently set output directory

my_archive.files_to_extract([file_listing[0],file_listing[3]]) #Updates the currently set file(s) to extract from the archive

Use of vfs.rar:

Almost all archives can be handled by vfs.libarchive.  The only exception found at this point are solid RAR archives:
https://www.winrar-france.fr/winrar_instructions_for_use/source/html/HELPArcSolid.htm

You can set archive_tool to use vfs.rar in these cases with
my_archive = archive_tool.archive_tool(archive_file = 'myfile.rar',directory_out = '/my/output_directory/', use_vfs_rar=True) #Current archive object using vfs.rar instead of vfs.libarchive

'''

from kodi_six import xbmc, xbmcvfs
try:
	from urllib import quote_plus as url_quote #Python 2
except:
	from urllib.parse import quote_plus as url_quote #Python 3
import os, json

class archive_tool(object):

	def __init__(self, archive_file=None, files_to_extract=None, directory_out=None,use_vfs_rar=False):
		if archive_file is not None:
			if type(archive_file) is str or type(archive_file) is unicode:
				if len([x for x in json.loads(xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.GetAddons","params":{"type":"kodi.vfs", "enabled": true}, "id": "1"}')).get('result').get('addons') if x is not None and (x.get('addonid')=='vfs.libarchive' or x.get('addonid')=='vfs.rar')])>0:
					if xbmcvfs.exists(archive_file):
						if any([archive_file.lower().endswith(x) for x in '.7z|.tar.gz|.tar.bz2|.tar.xz|.zip|.iso|.tar|.rar|.tgz|.tbz2|.gz|.bz2|.xz|.cbr|.001'.split('|')]):
							self.archive_file = archive_file
						else:
							xbmc.log(msg='archive_tool error:  file type %(current_file_type)s is not a supported archive type' % {'current_file_type': os.path.splitext(archive_file)[-1]}, level=xbmc.LOGERROR)
							self.archive_file = None
					else:
						xbmc.log(msg='archive_tool error:  archive_file could not be found', level=xbmc.LOGERROR)
						self.archive_file = None
				else:
					xbmc.log(msg='archive_tool error:  vfs.libarchive and vfs.rar are not installed or enabled', level=xbmc.LOGERROR)
					self.archive_file = None
			else:
				xbmc.log(msg='archive_tool error:  archive_file must be string or unicode', level=xbmc.LOGERROR)
				self.archive_file = None
		else:
			self.archive_file = None
		if directory_out is not None:
			if type(directory_out) is str or type(directory_out) is unicode:
				self.directory_out = directory_out
			else:
				xbmc.log(msg='archive_tool error:  directory_out must be string or unicode', level=xbmc.LOGERROR)
				self.directory_out = None
		else:
			self.directory_out = None
		if files_to_extract is not None:
			if type(files_to_extract) is list:
				self.files_to_extract = files_to_extract
			elif type(files_to_extract) is str or type(files_to_extract) is unicode:
				self.files_to_extract = [files_to_extract]
			else:
				xbmc.log(msg='archive_tool error:  files_to_extract must be list,string or unicode', level=xbmc.LOGERROR)
				self.files_to_extract = None
		else:
			self.files_to_extract = None
		if use_vfs_rar:
			if len([x for x in json.loads(xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.GetAddons","params":{"type":"kodi.vfs", "enabled": true}, "id": "1"}')).get('result').get('addons') if x is not None and x.get('addonid')=='vfs.rar'])>0:
				if any([archive_file.lower().endswith(x) for x in '.rar|.cbr|.001'.split('|')]):
					xbmc.log(msg='archive_tool: set to use vfs.rar', level=xbmc.LOGDEBUG)
					self.use_vfs_rar = True
				else:
					xbmc.log(msg='archive_tool error:  Cannot use vfs.rar for file type %(current_file_type)s, defaulting to vfs.libarchive' % {'current_file_type': os.path.splitext(archive_file)[-1]}, level=xbmc.LOGERROR)
					self.use_vfs_rar = False
			else:
				xbmc.log(msg='archive_tool error:  vfs.rar was not found to be installed or is not enabled, defaulting to vfs.libarchive', level=xbmc.LOGERROR)
				self.use_vfs_rar = False
		else:
			xbmc.log(msg='archive_tool: set to use vfs.libarchive', level=xbmc.LOGDEBUG)
			self.use_vfs_rar = False

	def archive_file(self, archive_file=None):
		if archive_file is not None:
			if type(archive_file) is str or type(archive_file) is unicode:
				if xbmcvfs.exists(archive_file):
					if any([archive_file.lower().endswith(x) for x in '.7z|.tar.gz|.tar.bz2|.tar.xz|.zip|.rar|.tgz|.tbz2|.gz|.bz2|.xz|.cbr'.split('|')]):
						self.archive_file = archive_file
						xbmc.log(msg='archive_tool: Set archive file to %(archive_file)s' % {'archive_file': archive_file}, level=xbmc.LOGDEBUG)
					else:
						xbmc.log(msg='archive_tool error:  file type %(current_file_type)s is not a supported archive type' % {'current_file_type': os.path.splitext(archive_file)[-1]}, level=xbmc.LOGERROR)
						self.archive_file = None
				else:
					xbmc.log(msg='archive_tool error:  archive_file could not be found', level=xbmc.LOGERROR)
					self.archive_file = None
			else:
				xbmc.log(msg='archive_tool error:  archive_file must be string or unicode', level=xbmc.LOGERROR)
				self.archive_file = None
		else:
			self.archive_file = None

	def directory_out(self, directory_out=None):
		if directory_out is not None:
			if type(directory_out) is str or type(directory_out) is unicode:
				self.directory_out = directory_out
				xbmc.log(msg='archive_tool: Set output directory to %(directory_out)s' % {'directory_out': directory_out}, level=xbmc.LOGDEBUG)
			else:
				xbmc.log(msg='archive_tool error:  directory_out must be string or unicode', level=xbmc.LOGERROR)
				self.directory_out = None
		else:
			self.directory_out = None

	def files_to_extract(self, files_to_extract=None):
		if files_to_extract is not None:
			if type(files_to_extract) is list:
				self.files_to_extract = files_to_extract
				xbmc.log(msg='archive_tool: Set files to extract to %(files_to_extract)s' % {'files_to_extract': self.files_to_extract}, level=xbmc.LOGDEBUG)
			elif type(files_to_extract) is str or type(files_to_extract) is unicode:
				self.files_to_extract = [files_to_extract]
				xbmc.log(msg='archive_tool: Set files to extract to %(files_to_extract)s' % {'files_to_extract': self.files_to_extract}, level=xbmc.LOGDEBUG)
			else:
				xbmc.log(msg='archive_tool error:  files_to_extract must be list,string or unicode', level=xbmc.LOGERROR)
				self.files_to_extract = None
		else:
			self.files_to_extract = None

	def extract(self,current_archive_file=None,current_directory_out=None,files_to_extract=None,extract_all=True):
		files_out = list()
		overall_success = True

		if current_archive_file is None:
			current_archive_file = self.archive_file
		if current_directory_out is None:
			current_directory_out = self.directory_out
		if files_to_extract is None:
			if not extract_all and (self.files_to_extract is None or len(self.files_to_extract) == 0):
				xbmc.log(msg='archive_tool error:  extract_all set to False and no files were identified for extraction', level=xbmc.LOGERROR)
				overall_success = False
				return files_out, overall_success
			else:
				files_to_extract = self.files_to_extract
		else:
			if type(files_to_extract) is list and len(files_to_extract) > 0:
				extract_all = False #Override default extract_all if files_to_extract is populated

		if current_archive_file is not None:
			if current_directory_out is None:
				#Default to the same directory as the current_archive_file
				directory_to = os.path.join(os.path.split(xbmc.translatePath(current_archive_file))[0],'')
			else:
				directory_to = os.path.join(xbmc.translatePath(current_directory_out),'')
			
			if 'archive://' in current_archive_file or 'rar://' in current_archive_file:
				archive_path = current_archive_file
			else:
				if self.use_vfs_rar:
					archive_path = 'rar://%(archive_file)s' % {'archive_file': url_quote(xbmc.translatePath(current_archive_file))}
				else:
					archive_path = 'archive://%(archive_file)s' % {'archive_file': url_quote(xbmc.translatePath(current_archive_file))}
			
			dirs_in_archive, files_in_archive = xbmcvfs.listdir(archive_path)

			for ff in files_in_archive:
				file_from = os.path.join(archive_path,ff).replace('\\','/') #Windows unexpectedly requires a forward slash in the path
				if extract_all or file_from in files_to_extract:
					success = xbmcvfs.copy(file_from,os.path.join(xbmc.translatePath(directory_to),ff)) #Extract the file to the correct directory
					if not success:
						xbmc.log(msg='archive_tool error:  Error extracting file %(ff)s from archive %(archive_file)s' % {'ff': ff,'archive_file':current_archive_file}, level=xbmc.LOGERROR)
						overall_success = False
					else:
						xbmc.log(msg='archive_tool: Extracted file %(ff)s from archive %(archive_file)s' % {'ff': ff,'archive_file':current_archive_file}, level=xbmc.LOGDEBUG)
						files_out.append(os.path.join(xbmc.translatePath(directory_to),ff)) #Append the file to the list of extracted files
				else:
					xbmc.log(msg='archive_tool: The file %(ff)s from archive %(archive_file)s was not listed for extraction, so it will be skipped' % {'ff': file_from,'archive_file':current_archive_file}, level=xbmc.LOGDEBUG)
			for dd in dirs_in_archive:
				if xbmcvfs.mkdir(os.path.join(xbmc.translatePath(directory_to),dd)): #Make the archive directory in the directory_to
					xbmc.log(msg='archive_tool: Created folder %(dd)s for archive %(archive_file)s' % {'dd': os.path.join(xbmc.translatePath(directory_to),dd,''),'archive_file':current_archive_file}, level=xbmc.LOGDEBUG)
					files_out2, success2 = self.extract(current_archive_file=os.path.join(archive_path,dd,'').replace('\\','/'),current_directory_out=os.path.join(directory_to,dd))
					if success2:
						files_out = files_out + files_out2 #Append the files in the subdir to the list of extracted files
					else:
						xbmc.log(msg='archive_tool error:  Error extracting files from the subdirectory %(dd)s in the archive %(archive_file)s' % {'dd': dd,'archive_file':current_archive_file}, level=xbmc.LOGERROR)
						overall_success = False
				else:
					overall_success = False
					xbmc.log(msg='archive_tool error:  Unable to create the archive subdirectory %(dir_from)s in the archive %(archive_file)s' % {'dir_from': os.path.join(xbmc.translatePath(directory_to),dd),'archive_file':current_archive_file}, level=xbmc.LOGERROR)
		else:
			xbmc.log(msg='archive_tool error:  The current archive file is not valid', level=xbmc.LOGERROR)
			overall_success = False

		return files_out, overall_success

	def list_all(self,current_archive_file=None,current_directory_out=None):
		files_out = list()
		if current_archive_file is None:
			current_archive_file = self.archive_file
		if current_directory_out is None:
			current_directory_out = self.directory_out

		if current_archive_file is not None:
			if current_directory_out is None:
				#Default to the same directory as the current_archive_file
				directory_to = os.path.join(os.path.split(xbmc.translatePath(current_archive_file))[0],'')
			else:
				directory_to = os.path.join(xbmc.translatePath(current_directory_out),'')
			
			if 'archive://' in current_archive_file or 'rar://' in current_archive_file:
				archive_path = current_archive_file
			else:
				if self.use_vfs_rar:
					archive_path = 'rar://%(archive_file)s' % {'archive_file': url_quote(xbmc.translatePath(current_archive_file))}
				else:
					archive_path = 'archive://%(archive_file)s' % {'archive_file': url_quote(xbmc.translatePath(current_archive_file))}
			
			dirs_in_archive, files_in_archive = xbmcvfs.listdir(archive_path)
			for ff in files_in_archive:
				file_from = os.path.join(archive_path,ff).replace('\\','/') #Windows unexpectedly requires a forward slash in the path
				files_out.append(file_from) #Append the file to the list of extracted files
			for dd in dirs_in_archive:
				files_out2 = self.list_all(current_archive_file=os.path.join(archive_path,dd,'').replace('\\','/'),current_directory_out=os.path.join(directory_to,dd))		
				files_out = files_out + files_out2 #Append the files in the subdir to the list of extracted files
		return files_out

	def stat_all(self,current_archive_file=None):
		files_out = list()
		if current_archive_file is None:
			current_archive_file = self.archive_file
		
		if current_archive_file is not None:
			if 'archive://' in current_archive_file or 'rar://' in current_archive_file:
				archive_path = current_archive_file
			else:
				if self.use_vfs_rar:
					archive_path = 'rar://%(archive_file)s' % {'archive_file': url_quote(xbmc.translatePath(current_archive_file))}
				else:
					archive_path = 'archive://%(archive_file)s' % {'archive_file': url_quote(xbmc.translatePath(current_archive_file))}

			files_in_archive = self.list_all()
			for ff in files_in_archive:
				files_out.append({'fullpath':ff,'filename':os.path.split(ff)[-1],'size':int(xbmcvfs.File(ff).size())})

		return files_out
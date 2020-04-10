from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from kodi_six.utils import py2_encode, py2_decode
import os
import archive_tool


WIN = xbmcgui.Window(10000)
if not WIN.getProperty('archive_tool.script_started'):
	current_dialog = xbmcgui.Dialog()
	WIN.setProperty('archive_tool.script_started','True')
	xbmc.log(msg='archive_tool:  Test started.', level=xbmc.LOGDEBUG)

	addon_name = 'script.module.archive_tool'
	addon_handle = xbmcaddon.Addon(id='%(addon_name)s' % {'addon_name':addon_name})
	current_file = os.path.join(xbmc.translatePath(addon_handle.getSetting(id='archive_tool_file')))
	current_folder = os.path.join(xbmc.translatePath(addon_handle.getSetting(id='archive_tool_folder')))
	current_vfs = addon_handle.getSetting(id='archive_tool_vfs_type')
	xbmc.log(msg='archive_tool:  VFS Selected: %(current_vfs)s' % {'current_vfs':current_vfs}, level=xbmc.LOGDEBUG)
	if xbmcvfs.exists(current_file):
		if xbmcvfs.exists(os.path.join(current_folder,'')):
			xbmc.log(msg='archive_tool:  Current file selected %(current_file)s' % {'current_file':current_file}, level=xbmc.LOGDEBUG)
			xbmc.log(msg='archive_tool:  Current folder selected %(current_folder)s' % {'current_folder':current_folder}, level=xbmc.LOGDEBUG)

			if current_vfs == 'rar':
				xbmc.sleep(1000)
				xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled","params":{"addonid": "vfs.libarchive", "enabled": false} }') #Temporarily disable vfs.libarchive
				xbmc.sleep(1000)
				try:
					my_archive = archive_tool.archive_tool(archive_file = current_file,directory_out = current_folder, use_vfs_rar=True) #Current archive object using vfs.rar
					file_listing = my_archive.list_all() #Lists all files in the archive
					xbmc.log(msg='archive_tool:  File listing:\n%(file_listing)s' % {'file_listing':'\n'.join(file_listing)}, level=xbmc.LOGDEBUG)
					stat_listing = my_archive.stat_all() #Dict of all files in the archive containing fullpath, filename, file size (extracted)
					xbmc.log(msg='archive_tool:  File Stats:\n%(stat_listing)s' % {'stat_listing':'\n'.join(['Fullpath: %(file_fp)s, Filename: %(file_fn)s, Size: %(file_s)s,'%{'file_fp':x['fullpath'],'file_fn':x['filename'],'file_s':x['size']} for x in stat_listing])}, level=xbmc.LOGDEBUG)
					xbmc.log(msg='archive_tool:  File Extraction Starting', level=xbmc.LOGDEBUG)
					files_extracted, success_of_extraction = my_archive.extract()  #Extracts all files to directory_out, returns list of files extracted and True/False for extraction success.  Defaults to extract all files in the archive.
				except Exception as exc:
					files_extracted = []
					success_of_extraction = False
					xbmc.log(msg='archive_tool:  Unknown Error.  Exception %(exc)s' % {'exc': exc}, level=xbmc.LOGERROR)
				xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled","params":{"addonid": "vfs.libarchive", "enabled": true} }') #re-enable vfs.libarchive
				xbmc.sleep(1000)
			else:
				try:
					my_archive = archive_tool.archive_tool(archive_file = current_file,directory_out = current_folder)
					file_listing = my_archive.list_all() #Lists all files in the archive
					xbmc.log(msg='archive_tool:  File listing:\n%(file_listing)s' % {'file_listing':'\n'.join(file_listing)}, level=xbmc.LOGDEBUG)
					stat_listing = my_archive.stat_all() #Dict of all files in the archive containing fullpath, filename, file size (extracted)
					xbmc.log(msg='archive_tool:  File Stats:\n%(stat_listing)s' % {'stat_listing':'\n'.join(['Fullpath: %(file_fp)s, Filename: %(file_fn)s, Size: %(file_s)s,'%{'file_fp':x['fullpath'],'file_fn':x['filename'],'file_s':x['size']} for x in stat_listing])}, level=xbmc.LOGDEBUG)
					xbmc.log(msg='archive_tool:  File Extraction Starting', level=xbmc.LOGDEBUG)
					files_extracted, success_of_extraction = my_archive.extract()  #Extracts all files to directory_out, returns list of files extracted and True/False for extraction success.  Defaults to extract all files in the archive.
				except Exception as exc:
					files_extracted = []
					success_of_extraction = False
					xbmc.log(msg='archive_tool:  Unknown Error.  Exception %(exc)s' % {'exc': exc}, level=xbmc.LOGERROR)

			xbmc.log(msg='archive_tool:  Extraction success returned %(ex_success)s.  Files:\n%(file_listing)s' % {'ex_success':success_of_extraction,'file_listing':'\n'.join(files_extracted)}, level=xbmc.LOGDEBUG)
			if success_of_extraction:
				ok_ret = current_dialog.ok('Extraction Success','%(total_files)s total files were extracted' % {'total_files':len(file_listing)})
			else:
				ok_ret = current_dialog.ok('Extraction Failed','Check your debug log for results.')
		else:
			xbmc.log(msg='archive_tool:  ERROR, the selected folder %(current_folder)s was not found' % {'current_folder': current_folder}, level=xbmc.LOGERROR)
	else:
		xbmc.log(msg='archive_tool:  ERROR, the selected file %(current_file)s was not found' % {'current_file': current_file}, level=xbmc.LOGERROR)

	WIN.clearProperty('archive_tool.script_started')
	xbmc.log(msg='archive_tool:  Test completed', level=xbmc.LOGDEBUG)
else:
	xbmc.log(msg='archive_tool:  Test already running', level=xbmc.LOGDEBUG)
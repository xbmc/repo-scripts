import xbmc, os, subprocess, sys
import xbmcgui, xbmcaddon

from variables import *
from modules import *
from debug2 import *
from debug3 import *

printpoint = ""

class SendDebug:
	'''Current_Name'''
	returned = dialogkeyboard(Debug_Email, 'Email (related to facebook)', 0, '1', '', '')
	if returned == 'skip': notification_common("3")
	else:
		emailprovider = regex_from_to(returned, '@', returned[-4:], excluding=False)
		if emailprovider == "":
			notification('Email is not valid!',"","",2000)
		elif not emailprovider in Debug_EmailL:
			notification_common('27')
		else:
			Debug_Email = to_utf8(returned.lower())
			setsetting('Debug_Email',Debug_Email)
			returned = dialogkeyboard(Debug_Password, 'Email Password', 5, '1', '', '')
			if returned == 'skip': notification_common("3")
			else:
				Debug_Password = str(returned)
				'''Debug_Title'''
				returned = dialogkeyboard(Debug_Title,'Title',0,'1','Debug_Title', 'script.featherence.service')
				if returned == 'skip': notification_common("3")
				else:
					Debug_Title = to_utf8(returned)
					'''Debug_Message'''
					returned = dialogkeyboard(Debug_Message,'Message',0,'1','Debug_Message', 'script.featherence.service')
					if returned == 'skip': notification_common("3")
					else:
						Debug_Message = to_utf8(returned)
						'''Add File'''
						if 1 + 1 == 3:
							returned = dialogyesno('Would you like to add a screenshot?','')
							if returned == 'skip': Debug_File = ""
							else:
								Debug_File = setPath(type=1,mask="pic", folderpath="")
							
						'''include kodi.log'''
						list = ["None"]
						for x in [file1, file2]:
							filesize = 0
							x_ = str(os.path.basename(x))
							if os.path.exists(x):
								filesize = getFileAttribute(2, x, option=1)
								
								if filesize <= 5:
									x_ = '' + str(x_) + space + '(' + str(filesize) + 'MB' + ')' + ''
								else:
									x_ = '[COLOR=red]' + x_ + '[/COLOR]'
							else:
								x_ = '[COLOR=red]' + x_ + space + 'Not Found!' + '[/COLOR]'
								
							list.append(x_)
							
						returned, value = dialogselect(addonString_servicefeatherence(31).encode('utf-8'),list,0)	
						if returned == -1: printpoint = printpoint + "9"
						elif returned == 0: file = ""
						else:
							if returned == 1: file = file1
							elif returned == 2: file = file2
							
							if file != "":
								file = upload_file(file, value)
								file = to_utf8(file)
								
						#Debug_Message = Debug_Title + newline + newline + Debug_Message + newline + newline + file
						Debug_Message = newline + Debug_Message + newline + newline + file

						'''send debug prompt'''
						returned = dialogyesno(addonString(32098), addonString(32097))
						if returned == 'skip': notification('$LOCALIZE[257]',addonString(10).encode('utf-8'),"",2000)
						elif returned == 'ok':
							SendDebug(Debug_Email, Debug_Password, Debug_Title, Debug_Message, Debug_File)
					

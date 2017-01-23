import xbmc, os, subprocess, sys
import xbmcgui, xbmcaddon

from variables import *
from modules import *
from debug2 import *
from debug3 import *

printpoint = ""

class SendDebug:
	'''Current_Name'''
	returned = dialogkeyboard(Debug_Email, addonString(32115).encode('utf-8'), 0, '1', '', '')
	if returned == 'skip': notification_common("3")
	else:
		emailprovider = regex_from_to(returned, '@', returned[-4:], excluding=False)
		emailprovider = emailprovider.lower()
		if emailprovider == "":
			notification(addonString(32113).encode('utf-8'),"","",2000)
		elif not emailprovider in Debug_EmailL:
			notification_common('27')
		else:
			Debug_Email = to_utf8(returned.lower())
			setsetting('Debug_Email',Debug_Email)
			returned = dialogkeyboard(Debug_Password, addonString(32114).encode('utf-8'), 5, '1', '', '')
			if returned == 'skip': notification_common("3")
			else:
				Debug_Password = str(returned)
				'''Debug_Title'''
				returned = dialogkeyboard(Debug_Title,localize(528),0,'1','Debug_Title', 'script.featherence.service')
				if returned == 'skip': notification_common("3")
				else:
					Debug_Title = to_utf8(returned)
					'''Debug_Message'''
					returned = dialogkeyboard(Debug_Message,localize(15007),0,'1','Debug_Message', 'script.featherence.service')
					if returned == 'skip': notification_common("3")
					else:
						Debug_Message = to_utf8(returned)
						'''Add File'''
						if 1 + 1 == 3:
							returned = dialogyesno(localize(20008) + '?','')
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
								x_ = '[COLOR=red]' + x_ + space + localize(33077) + '[/COLOR]'
								
							list.append(x_)
							
						returned, value = dialogselect(addonString_servicefeatherence(32423).encode('utf-8'),list,0)	
						if returned == -1: printpoint = printpoint + "9"
						elif returned == 0: file = ""
						else:
							if returned == 1: file = file1
							elif returned == 2: file = file2
							
							if file != "":
								file = upload_file(file, value)
								file = to_utf8(file)
								
						#Debug_Message = Debug_Title + newline + newline + Debug_Message + newline + newline + file
						Debug_Message = newline + str(Debug_Message) + newline + newline + str(file)

						'''send debug prompt'''
						returned = dialogyesno(addonString(32098).encode('utf-8'), addonString(32097).encode('utf-8'))
						if returned == 'skip': notification(localize(2102, s=[localize(504)]),"","",2000)
						elif returned == 'ok':
							SendDebug(Debug_Email, Debug_Password, Debug_Title, Debug_Message, Debug_File)
					

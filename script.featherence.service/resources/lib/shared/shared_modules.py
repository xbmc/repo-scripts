import xbmc, xbmcgui, xbmcaddon
import os, sys

try: from variables import *
except:
	try: from shared_variables import *
	except: pass

def CreateZip(src, dst, filteron=[], filteroff=[], level=10000, append=False, ZipFullPath=False, temp=False):

	name = 'CreateZip'
	TypeError = "" ; extra = "" ; arcname = "" ; absname = "" ; dirname = "" ; files = "" ; printpoint = "" ; file = "" ; subdirs = "" ; subdir = "" ; temp__ = ".zip" ; returned = ""
	if append == False: append_ = "w"
	else: append_ = "a"
	
	if temp == False: temp_ = temp__
	else: temp_ = "_temp.zip"
	
	import zipfile
	zf = zipfile.ZipFile("%s%s" % (dst, temp_), append_, zipfile.ZIP_DEFLATED)
	abs_src = os.path.abspath(src)
	
	for dirname, subdirs, files in os.walk(src):

		printpoint = "" ; extra2 = ""
		
		subdir = dirname.replace(src, "")
		
		
		if systemplatformwindows:
			try: subdir2 = find_string(subdir, subdir[:1], "\\") ; subdir2 = subdir2.replace("\\","")
			except: subdir2 = "?"
			subdir_level = subdir.count("\\")
		else:
			try: subdir2 = find_string(subdir, subdir[:1], "/") ; subdir2 = subdir2.replace("/","")
			except: subdir2 = "?"
			subdir_level = subdir.count("/")
		
		if not os.path.exists(dst+temp_):
			zf.close()
			dialogok(localize(2102, s=['1015']),"","","")
			sys.exit()
		
		if subdir_level <= level:
			printpoint = printpoint + "1"
			if filteron == [] or subdir in filteron or subdir == ""  or subdirs == [] or subdir2 in filteron:
				printpoint = printpoint + "2"
				if filteroff == [] or (not subdir in filteroff and not subdir2 in filteroff):
					printpoint = printpoint + "3"
					for filename in files:
						printpoint = printpoint + "4" ; extra2 = extra2 + space + "filename" + space2 + filename
						if filteron == [] or filename in filteron or subdir in filteron or subdir2 in filteron:
							printpoint = printpoint + "5"
							if filteroff == [] or not filename in filteroff:
								printpoint = printpoint + "6"
								absname = os.path.abspath(os.path.join(dirname, filename))
								arcname = absname[len(abs_src) + 1:]
								arcname1dir = find_string(arcname, arcname[:2], "/")

								text = 'zipping %s as %s' % (os.path.join(to_utf8(dirname), to_utf8(filename)),to_utf8(arcname))
								printlog(title=name, printpoint=printpoint, text=text, level=2, option="")
								#if filteron == [] or arcname in filteron:
								#if filteroff == [] or not arcname in filteroff:
								try:
									if ZipFullPath == False: zf.write(absname, arcname)
									else:
										if systemplatformwindows:
											absname2 = absname
											if "\\Kodi\\" in absname2:
												split = absname2.split("Kodi")
												absname2 = absname2.replace(split[0]+'Kodi\\',"")
											elif "\\XBMC\\" in absname2:
												split = absname2.split("XBMC")
												absname2 = absname2.replace(split[0]+'XBMC\\',"")
											
											
											#if len(split[0]) == 2: absname2 = split[0] + "\\" + absname
											text = "split[0]" + space2 + str(split[0]) + space + "split[1]" + space2 + str(split[1])
											printlog(title=name + 'absname2_test', printpoint=printpoint, text=text, level=0, option="")
											
											#if "C:\\" in absname2: absname2 = absname2.replace("C:\\","C:\\\\")
											zf.write(absname, absname2)
										else:
											absname2 = absname.replace('/storage/','/')
											zf.write(absname, absname2)
											'''---------------------------'''

									printpoint = printpoint + "7"
									'''---------------------------'''
								except Exception, TypeError:
									printpoint = printpoint + "8"
									TypeError = str(TypeError) + space + "absname" + space2 + str(absname) + space + "arcname" + space2 + str(arcname)
									'''---------------------------'''
									
		else: printpoint = printpoint + "9"

		text = "dirname" + space2 + str(to_utf8(dirname)) + newline + \
		"subdir" + space2 + to_unicode(subdir) + space + "subdir_level" + space2 + str(subdir_level) + space + "subdir2" + space2 + str(to_utf8(subdir2)) + space + "files" + space2 + str(to_utf8(files)) + newline + \
		"file" + space2 + str(to_utf8(file)) + space + "level" + space2 + str(level) + newline + \
		'to_utf8(extra2)'
		printlog(title=name + '_LV', printpoint=printpoint, text=text, level=0, option="")
	
	#except Exception, TypeError:
	#TypeError = str(TypeError) + space + "os.walk(src)" + space2 + str(os.walk(src)) + space + "src" + space2 + str(src) + space + "dirname" + space2 + dirname + space + "files" + space2 + str(files)
	#notification("Error 1050","","",1000)
	#continue

	zf.close()
	
	if append == "End" and temp == True:
		xbmc.sleep(500)
		removefiles(dst + temp__)
		try:
			os.rename(dst + temp_, dst + temp__)
			notification("Zip File Ready!", dst + temp__, "", 2000)
		except Exception, TypeError:
			notification("Zip File Error!", dst + temp__, "", 2000)
		
		
		'''---------------------------'''
		returned = 'ok'
	elif temp != True and append == False: returned = 'ok'
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	if TypeError != "": extra = newline + "TypeError:" + space2 + str(TypeError)
	text = ""
	try: text = text + "src" + space2 + str(src) + space + "dst" + space2 + str(dst) + space + "filteron" + space2 + str(filteron) + space + "filteroff" + space2 + str(filteroff) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + "level" + space2 + str(level) + space + "arcname" + space2 + str(arcname) + space + "abs_src" + space2 + str(abs_src) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + "absname" + space2 + str(absname) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + "dirname" + space2 + str(dirname) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + "files" + space2 + str(files) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + "subdirs" + space2 + str(subdirs) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + "subdir" + space2 + to_unicode(subdir) + newline
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	try: text = text + extra
	except Exception, TypeError: extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")
	'''---------------------------'''
	return returned	

def TranslatePath(x, filename=True, urlcheck_=False, force=False):
	name = 'TranslatePath' ; printpoint = "" ; returned = "" ; returned2 = "" ; TypeError = "" ; extra = ""
	if x == None: x = ""
	
	x = to_utf8(x)
	returned = x
	
	if systemplatformwindows: slash = '\\'
	else: slash = '/'
	
	if 'image://' in x:
		printpoint = printpoint + '1'
		returned = x.replace('image://',"",1)
		returned = returned.replace('%5c',slash)
		returned = returned.replace('%3a',':')
		if returned[-1:] == '/': returned = returned.replace(returned[-1:],"",1)
		
		
	elif 'https://' in x or 'http://' in x or 'http:%2f' in x:
		printpoint = printpoint + '2'
		if urlcheck_ == True:
			from shared_modules3 import urlcheck
			valid = urlcheck(x, ping=False, timeout=1)
			if 'ok' in valid:
				printpoint = printpoint + "4"
				returned = x
			else:
				printpoint = printpoint + '9'
				if force == True: returned = ""
		else: returned = x
	elif 'special://' in x:
		try:
			printpoint = printpoint + '5'
			returned = os.path.join(xbmc.translatePath(x).decode("utf-8"))
		except Exception, TypeError:
			printpoint = printpoint + '9'
			extra = extra + newline + 'TypeError: ' + str(TypeError)
			
		returned2 = x
	
	if not '2' in printpoint:
		if os.path.exists(returned):
			printpoint = printpoint + '5'
			
			list = [temp_path, addons_path, xbmc_path, userdata_path, thumbnails_path, database_path]
			list2 = ['special://temp/', 'special://home/addons/', 'special://xbmc/',  'special://userdata/',  'special://thumbnails/',  'special://database/']
			i = 0
			for y in list:
				y = to_utf8(y)
				if y in returned:
					returned2 = returned.replace(y, list2[i])
					returned2 = returned2.replace('\\','/')
					break
				i += 1

		else:
			printpoint = printpoint + '9'
			if force == True: returned = ""
	
	if filename == False:
		filename_ = os.path.basename(returned)
		returned = returned.replace(filename_,"",1)
		
		filename_ = os.path.basename(returned2)
		returned2 = returned2.replace(filename_,"",1)
		
	text = newline + \
	'x' + space2 + str(x) + newline + \
	'returned' + space2 + to_utf8(returned) + newline + \
	'returned2' + space2 + to_utf8(returned2) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")
	
	return to_unicode(returned), to_unicode(returned2)

def GeneratePath(custom, formula, custommediaL, x2, x2_, ignoreL=[]):
	name = 'GeneratePath' ; printpoint = "" ; formula_ = "" ; subdir = "" ; filename = "" ; subdir_filename = "" ; TypeError = "" ; extra = "" ; level = 1
	if x2 == None: x2 = ""
	
	if systemplatformwindows: slash = '\\'
	else: slash = '/'
		
	if x2 == "" and custom == "":
		printpoint = printpoint + '9'
	elif x2 == "":
		printpoint = printpoint + '1'
		formula = formula + newline + custom + str(x2)
	elif 'https://' in x2 or 'http://' in x2 or 'http:%2f' in x2:
		printpoint = printpoint + '2'
		formula = formula + newline + custom + str(x2)
	else:
		if ignoreL != []:
			printpoint = printpoint + '3'
			for x in ignoreL:
				if x in x2_:
					printpoint = printpoint + '4'
					formula = formula + newline + custom + str(x2_)
					break
					
		if not '4' in printpoint:
			printpoint = printpoint + '7'
			filename = os.path.basename(x2)
			subdir = x2.split(slash)
			try: subdir = subdir[-2]
			except:
				subdir = ""
				level = 7
				extra = extra + newline + 'subdir list error' + space2 + 'x2' + space2 + str(x2) + newline + str(subdir) + filename
				
			subdir_filename = to_unicode(subdir) + '_' + to_unicode(filename)
			target = os.path.join(featherenceserviceaddondata_media_path, subdir_filename)
			
			copyfiles(x2, target)
			custommediaL.append(subdir_filename)
			
			formula = formula + newline + custom + 'special://userdata/addon_data/script.featherence.service/media/' + to_utf8(subdir_filename)
	
	text = 'custom' + space2 + str(custom) + newline + \
	'ignoreL' + space2 + str(ignoreL) + newline + \
	'x2' + space2 + to_utf8(x2) + newline + \
	'x2_' + space2 + to_utf8(x2_) + newline + \
	'subdir_filename' + space2 + to_utf8(subdir_filename) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=level, option="")
	
	return formula, custommediaL
	
def ExtractAll(source, output):
	name = 'ExtractAll' ; printpoint = "" ; TypeError = "" ; extra = "" ; level = 1
	if ".zip" in source:
		import zipfile
		try:
			zin = zipfile.ZipFile(source, 'r')
			zin.extractall(output)
			zin.close()
			printpoint = printpoint + "7"
		
		except Exception, TypeError:
			printpoint = printpoint + "9"
			
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	if TypeError != "":
		extra = newline + "TypeError:" + space2 + str(TypeError)
		level = 7
	text = "source" + space2 + source + space + "output" + space2 + output + space + extra
	printlog(title=name, printpoint=printpoint, text=text, level=1, option="")
	'''---------------------------'''
	if "7" in printpoint: return True
	else: return False

def getFileAttribute(custom, file, option=""):
	name = 'getFileAttribute' ; printpoint = "" ; extra = "" ; returned = ""
	
	if not os.path.exists(file): printpoint = printpoint + "8"
	elif custom == 1: #last modified
		import time
		if option == '1':
			timenow = dt.datetime.now()
			returned = timenow.strftime("%d/%m/%y %H:%M") #date and time representation
			
		else:
			returned = time.ctime(os.path.getmtime(file))
		
	elif custom == 2: #size
		returned = os.path.getsize(file)
		if option == 1:
			#returned = (returned // 100000)%10
			returned = (returned // 100000)*0.10
			
	text = "custom" + space2 + str(custom) + space + "file" + space2 + str(file) + newline + \
	"returned" + space2 + str(returned) + newline + \
	'option' + space2 + str(option) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return returned

def localize(value, s=[], addon=None):
	name = 'localize' ; printpoint = "" ; i = 0 ; s1 = "" ; s2 = "" ; s3 = "" ; s4 = "" ; TypeError = "" ; extra = "" ; returned = "" ; value = str(value)
	try:
		if addon == None: returned = xbmc.getInfoLabel('$LOCALIZE['+value+']')
		else: returned = xbmc.getInfoLabel('$ADDON['+addon+' '+value+']')
	except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError)
	
	try: returned = returned.decode('utf-8')
	except: pass
	
	try: value = value.encode('utf-8')
	except: pass
	
	if s != []:
		i = 1
		for x in s:
			if i == 1: s1 = str(x)
			elif i == 2: s2 = str(x)
			elif i == 3: s3 = str(x)
			elif i == 4: s4 = str(x)
			i += 1
		
		if addon == None:
			if i == 2: returned = xbmc.getInfoLabel('$LOCALIZE['+value+']') % (s1)
			elif i == 3: returned = xbmc.getInfoLabel('$LOCALIZE['+value+']') % (s1, s2)
			elif i == 4: returned = xbmc.getInfoLabel('$LOCALIZE['+value+']') % (s1, s2, s3)
			elif i == 5: returned = xbmc.getInfoLabel('$LOCALIZE['+value+']') % (s1, s2, s3, s4)
		else:
			if i == 2: returned = xbmc.getInfoLabel('$ADDON['+addon+' '+value+']') % (s1)
			elif i == 3: returned = xbmc.getInfoLabel('$ADDON['+addon+' '+value+']') % (s1, s2)
			elif i == 4: returned = xbmc.getInfoLabel('$ADDON['+addon+' '+value+']') % (s1, s2, s3)
			elif i == 5: returned = xbmc.getInfoLabel('$ADDON['+addon+' '+value+']') % (s1, s2, s3, s4)
	
	try: returned = returned.encode('utf-8')
	except: pass
	
	text = "value" + space2 + str(value) + space + 's' + space2 + str(s) + space + 'addon' + space2 + str(addon) + space + "returned" + space2 + str(returned) + space + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return returned

def find_string(findin, findwhat, findwhat2):
	'''Return a string in a variable from x to y'''
	name = 'find_string' ; printpoint = ""
	
	findin = to_utf8(findin)
	findinL = len(findin)
	findinLS = str(findinL)
	findinLN = int(findinLS)
	findwhat = to_utf8(findwhat)
	findwhatL = len(findwhat)
	findwhatLS = str(findwhatL)
	findwhatLN = int(findwhatLS)
	findwhat2 = to_utf8(findwhat2)
	findwhat2L = len(findwhat2)
	findwhat2LS = str(findwhat2L)
	findwhat2LN = int(findwhat2LS)
	'''---------------------------'''
	
	findin_start = findin.find(findwhat, 0, findinL)
	findin_startS = str(findin_start)
	findin_startN = int(findin_startS) + findwhatLN
	findin_startS = str(findin_start)
	'''---------------------------'''
	if findwhat2 == "": findin_end = findin.find(findwhat2, findin_startN, findinL)
	else:
		findin_end = findin.find(findwhat2, findin_startN, findin_startN + findwhatLN)
		if findin_end == -1: findin_end = findin.find(findwhat2, findin_startN, findinL)
	findin_endS = str(findin_end)
	findin_endN = int(findin_endS) + findwhat2LN
	'''---------------------------'''
	findin_startN = int(findin_startS) #SOME KIND OF BUG? BUT WORKING THIS WAY!
	if findwhat == "": findin_startN = 0
	if findwhat2 == "": findin_endN = findinLN
	found = findin[findin_startN:findin_endN]
	foundS = str(found)
	'''---------------------------'''
	try:
		foundF = float(foundS)
		found2 = round(foundF)
		found2S = str(found2)
		if ".0" in found2S: found2S = found2S.replace(".0","",1)
	except: pass
	
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "find_string" + space + "findin" + space2 + findin + newline + \
	"(" + findinLS + ")" + space + "findwhat" + space2 + findwhat + newline + \
	"(" + findwhatLS + ")" + space +  "findin_startS" + space2 + findin_startS + space + "findin_endS" + space2 + findin_endS + newline + \
	"findin_start" + space2 + str(findin_start) + space + "findin_startN" + space2 + str(findin_startN) + newline + \
	"foundS" + space2 + foundS
	'''---------------------------'''
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return foundS
	
def CleanString(output, filter=[]):
	'''used on read_from_file module if needed'''
	name = 'CleanString' ; output0 = str(output) ; output1 = "" ; output2 = "" ; output3 = "" ; printpoint = ""
	
	if filter != []:
		
		for x in filter:
			output0 = output0.replace(x, "")
			output0 = output0.replace(x.upper(), "")
			
		
	output1 = output0.split('\n')
		
	
	for x in output1:
		x2 = x.replace('   ','#')
		x2 = x2.replace('  \n','#')
		x2 = x2.replace(' \n','#')
		x2 = x2.replace('\n','#')
		x2 = x2.replace('  \r','#')
		x2 = x2.replace(' \r','#')
		x2 = x2.replace('\r','#')
		x2 = x2.replace("'",'')
		x2 = x2.replace("[",'')
		x2 = x2.replace("]",'')
		#x2 = x2.replace(' \xd7','#')
		#x2 = x2.replace('\xd7','#')
		#x2 = x2.replace('\xa1','#')
		#x2 = x2.replace('\x94"','#')
		#x2 = x2.replace('\x94','#')
		#x2 = x2.replace('\x9b','#')
		'''---------------------------'''
		output2 = output2 + x2
		'''---------------------------'''
		
	output3 = output2.split('#') ; x2 = ""
	
	for x in output3:
		
		if x != "" and x != " " and not "    " in x:
			x2 = x2 + x
			'''---------------------------'''
			
	output4 = x2
	output1 = str(output1) ; output2 = str(output2) ; output3 = str(output3) ; output4 = str(output4)
	
	text = "output" + space2 + str(output) + newline + "output0" + space2 + str(output0) + newline + "output1" + space2 + str(output1) + newline + "output2" + space2 + str(output2) + newline + "output3" + space2 + str(output3) + newline + "output4" + space2 + str(output4)		
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return output4

def CleanString2(x, comma=False):
	'''clean characters for Random-Play'''
	name = 'CleanString2' ; printpoint = ""
	x2 = str(x)
	x2 = x2.replace(' ','')
	x2 = x2.replace(' ','')
	x2 = x2.replace("'",'')
	x2 = x2.replace("[",'')
	x2 = x2.replace("]",'')
	if comma == False: x2 = x2.replace(",",'|')
		
	text = "x" + space2 + str(x) + newline + "x2" + space2 + str(x2)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return x2
		
def setPath(type=0,mask="", folderpath="", original=True):
	returned = "" ; count = 0
	folderpath = to_utf8(folderpath)
	if mask == 'pic': mask = '.jpg|.jpeg|.JPEG|.bmp|.gif|.GIF|.png|.PNG'
	elif mask == 'music': mask = '.mp3|.flac|.wav|.m3u'
	if type == 0: xbmc.executebuiltin('Skin.SetPath(TEMP)')
	elif type == 1: xbmc.executebuiltin('Skin.SetFile(TEMP,'+mask+','+folderpath+')')
	elif type == 2: xbmc.executebuiltin('Skin.SetImage(TEMP,'+mask+','+folderpath+')')
	xbmc.sleep(500); dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
	
	while count < 10 and not dialogfilebrowserW and not xbmc.abortRequested:
		count += 1
		xbmc.sleep(1000)
		dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
	
	while dialogfilebrowserW and not xbmc.abortRequested:
		xbmc.sleep(1000)
		dialogfilebrowserW = xbmc.getCondVisibility('Window.IsVisible(FileBrowser.xml)')
		
	xbmc.sleep(500)
	TEMP = xbmc.getInfoLabel('Skin.String(TEMP)')
	x2, x2_ = TranslatePath(TEMP, filename=True)

	if x2 == "": notification_common("6")
	elif original == True or x2_ == "": returned = x2
	elif original == False: returned = x2_
	
	return returned
	
def dialogkeyboard(input, heading, option, custom, set1, addon, force=False):
	'''option:
    - xbmcgui.INPUT_ALPHANUM (standard keyboard)
    - xbmcgui.INPUT_NUMERIC (format: #)
    - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
    - xbmcgui.INPUT_TIME (format: HH:MM)
    - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
    - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
	'''
	if set1 == None: set1 = ""
	if addon == None: addon = ""
	
	name = 'dialogkeyboard' ; printpoint = "" ; returned = 'skip' ; set1v = ""
	if '$LOCALIZE' in heading: heading = xbmc.getInfoLabel(heading)
	heading = to_utf8(heading)
	dialog = xbmcgui.Dialog()
	xbmc.sleep(40) #Delay time to make sure operation executed!
	keyboard = xbmc.Keyboard(input,heading,option)
	keyboard.doModal()
	
	'''---------------------------'''
	if (keyboard.isConfirmed()):
		printpoint = printpoint + "0"
		set1v = keyboard.getText()
		if custom == '1':
			'''not empty'''
			printpoint = printpoint + "1"
			if set1v != "": returned = 'ok'
			else: notification_common("3")
		elif custom == '2' and set1v == input:
			printpoint = printpoint + "2"
			returned = 'ok'
		elif custom == '3':
			printpoint = printpoint + "3"
			if set1v != input and set1v != "" and option == 0: xbmc.executebuiltin('Notification('+ heading +': '+ set1v +',,4000)')
			if set1v != "": returned = 'ok'
			'''---------------------------'''
		elif custom == '5':
			'''Custom Playlist'''
			printpoint = printpoint + "5"
			if set1v == "" or set1v[-1:] == "=":
				check = dialogyesno(addonString_servicefeatherence(32446).encode('utf-8'), localize(19194)) #Your input is empty!, Continue?
				if check == "ok":
					returned = "ok"
					set1v = "None"
			elif ("list=" in set1v or "watch?v=" in set1v or "/user/" in set1v or "/channel/" in set1v or "results?search_query=" in set1v or "&youtube_" in set1v):
				from shared_modules3 import urlcheck, clean_commonsearch
				set1v = clean_commonsearch(set1v)
				set1v_ = set1v ; set1v__ = ""
				if "results?search_query=" in set1v or "&youtube_se=" in set1v:
					set1v_ = set1v_.replace('&youtube_se=',"")
					set1v_ = 'https://www.youtube.com/results?search_query='+set1v_
				elif '&youtube_ch=' in set1v:
					set1v_ = set1v_.replace('&youtube_ch=',"")
					set1v_ = 'https://www.youtube.com/user/'+set1v_
					set1v__ = 'https://www.youtube.com/channel/'+set1v_
				elif '&youtube_pl=' in set1v:
					set1v_ = set1v_.replace('&youtube_pl=',"")
					set1v_ = 'https://www.youtube.com/playlist?list='+set1v_
				elif '&youtube_id=' in set1v:
					set1v_ = set1v_.replace('&youtube_id=',"")
					set1v_ = 'https://www.youtube.com/watch?v='+set1v_
					
				
				
				check = urlcheck(set1v_, ping=False, timeout=1)
				if check != 'ok' and set1v__ != "": check = urlcheck(set1v__, ping=False, timeout=1)
					
				if check == "ok":
					xbmc.executebuiltin('Notification('+ heading +': '+ set1v +',,4000)')
					returned = 'ok'
					'''---------------------------'''
				else: notification("URL is not valid!", "Try again..", "", 2000)
			else: notification("URL is not valid!", "Try again..", "", 2000)
			
		elif custom == "":
			printpoint = printpoint + "_"
			returned = 'ok'
		
	if returned == 'ok':
		returned = set1v
		if set1 != "" and addon != "":
			if addon == "0": setsetting(set1, to_utf8(set1v))
			elif addon != "": setsetting_custom1(addon,set1,to_utf8(set1v))
			'''---------------------------'''
		elif set1 != "" and addon == "": setSkinSetting("0",set1,set1v, force=force)
	
	if option != 0:
		set1v = "******"
		returnedv = "******"
	else: returnedv = returned
	
	text = "option" + space2 + str(option) + space + "returned" + space2 + str(returnedv) + space + "heading" + space2 + str(heading) + space + "set1v" + space2 + str(set1v)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return returned

def dialognumeric(type,heading,input,custom,set1,addon):
	'''type: 0 = #, 1 = DD/MM/YYYY, 2 = HH:MM, 3 = #.#.#.#, message2 = heading, message1 = content'''
	name = 'dialognumeric' ; printpoint = "" ; returned = "skip" ; TypeError = ""
	if '$LOCALIZE' in heading: heading = xbmc.getInfoLabel(heading)
	try: heading = heading.encode('utf-8')
	except: pass
	
	if custom == 0:
		try:
			if int(input) > 001000000 and int(input) < 9999999999 and input != "": pass
			else: input = 0
			'''---------------------------'''
		except Exception, TypeError: input = 0 ; printpoint = printpoint + "8"

	set1v = xbmcgui.Dialog().numeric(type, heading, str(input))
	
	if set1v == "" and custom != '1':
		notification_common("3")
		sys.exit()
		'''---------------------------'''
	
	if custom == '0':
		try:
			if int(set1v) > 001000000 and int(set1v) < 9999999999: returned = 'ok'
			elif int(set1v) < 001000000 or int(set1v) > 9999999999: returned = 'skip0'
			'''---------------------------'''
		except Exception, TypeError:
			returned = 'skip'
			printpoint = printpoint + "6"
			'''---------------------------'''
			
	elif custom == '1':
		if set1v != "": returned = 'ok'
		'''---------------------------'''
	elif custom == '2':
		if set1v == "": set1v = 0
		elif set1v != 0: returned = 'ok'
		'''---------------------------'''
	elif custom == "3":
		returned = 'ok'
		
	if returned == 'ok':
		if set1 != "" and addon != "":
			if addonID == addon: setsetting(set1, set1v) ; printpoint = printpoint + "A"
			else: setsetting_custom1(addon,set1,set1v) ; printpoint = printpoint + "B"
			'''---------------------------'''
		elif set1 != "" and addon == "":
			setSkinSetting("0", set1, set1v)
			printpoint = printpoint + "C"
			'''---------------------------'''
		else: printpoint = printpoint + "9"
		
	text = 'heading: ' + str(heading) + newline + \
	'input: ' + str(input) + newline + \
	'set1v: ' + str(set1v) + newline + \
	'returned: ' + str(returned)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	'''---------------------------'''
	return returned, set1v

def dialogok(heading,line1,line2,line3, line1c="", line2c="", line3c="", line4c=""):
	'''------------------------------
	---DIALOG-OK---------------------
	------------------------------'''
	dialog = xbmcgui.Dialog()
	name = 'dialogok' ; printpoint = "" ; TypeError = "" ; extra = ""
	if '$LOCALIZE' in heading or '$ADDON' in heading: heading = xbmc.getInfoLabel(heading)
	if '$LOCALIZE' in line1 or '$ADDON' in line1: line1 = xbmc.getInfoLabel(line1)
	if '$LOCALIZE' in line2 or '$ADDON' in line2: line2 = xbmc.getInfoLabel(line2)
	if '$LOCALIZE' in line3 or '$ADDON' in line3: line3 = xbmc.getInfoLabel(line3)
	
	heading = to_utf8(heading)
	line1 = to_utf8(line1)
	line2 = to_utf8(line2)
	line3 = to_utf8(line3)
	
	if line1c != "": heading = '[COLOR='+ line1c + ']' + heading + '[/COLOR]'
	if line2c != "": line1 = '[COLOR='+ line2c + ']' + line1 + '[/COLOR]'
	if line3c != "": line2 = '[COLOR='+ line3c + ']' + line2 + '[/COLOR]'
	if line4c != "": line3 = '[COLOR='+ line4c + ']' + line3 + '[/COLOR]'
		
	dialog.ok(heading,line1,line2,line3)
	
	text = 'heading: ' + str(heading) + newline + \
	'line1: ' + str(line1) + newline + \
	'line2: ' + str(line2) + newline + \
	'line3: ' + str(line3) + newline + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def dialogselect(heading, list, autoclose=0):
	'''------------------------------
	---DIALOG-SELECT-----------------
	------------------------------'''
	'''autoclose = [opt] integer - milliseconds to autoclose dialog. (default=do not autoclose)'''
	name = 'dialogselect' ; printpoint = "" ; TypeError = "" ; extra = ""
	dialog = xbmcgui.Dialog()
	if '$LOCALIZE' in heading or '$ADDON' in heading:
		printpoint = printpoint + "1"
		heading = xbmc.getInfoLabel(heading)

	heading = to_utf8(heading)
	
	returned = dialog.select(str(heading),list,autoclose)
	returned = int(returned)

	if returned == -1:
		notification_common("9")
		value = ""
	else:
		value = list[returned]
		value = to_utf8(value)
		value = str(value)

	text = str(heading) + "( " + str(returned) + " )" + space + "value" + space2 + value + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	return returned, value
	'''---------------------------'''

def diaogtextviewer(header,message):
	if '$LOCALIZE' in header or '$ADDON' in header: header = xbmc.getInfoLabel(header)
	if '$LOCALIZE' in message or '$ADDON' in message: message = xbmc.getInfoLabel(message)
	
	try: header = str(header.encode('utf-8'))
	except: pass
	try: message = str(message.encode('utf-8'))
	except: pass
	
	w = TextViewer_Dialog('DialogTextViewer.xml', "", header=header, text=message)
	w.doModal()
	
def dialogyesno(heading,line1,yes=False, nolabel="", yeslabel="", autoclose=0):
	'''------------------------------
	---DIALOG-YESNO------------------
	------------------------------'''
	name = 'dialogyesno' ; printpoint = ""
	if '$LOCALIZE' in heading or '$ADDON' in heading: heading = xbmc.getInfoLabel(heading)
	if '$LOCALIZE' in line1 or '$ADDON' in line1: line1 = xbmc.getInfoLabel(line1)
	returned = 'skip'
	
	if yes != False: xbmc.executebuiltin('AlarmClock(yes,Action(Down),0,silent)')
	yeslabel = to_utf8(yeslabel)
	nolabel = to_utf8(nolabel)

	if dialog.yesno(heading,line1, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose): returned = 'ok'
	
	try: heading = str(heading.encode('utf-8'))
	except: pass
	try: line1 = str(line1.encode('utf-8'))
	except: pass

	text = 'heading: ' + str(heading) + space + 'line1: ' + str(line1) + space + 'returned: ' + str(returned)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return returned
	'''---------------------------'''

def findin_controlhasfocus(custom,what,sleep,action,action2):
	'''action = not found | action2 = when found'''
	'''---------------------------'''
	what = str(what)
	custom = str(custom)
	if custom == "0": controlhasfocus = xbmc.getCondVisibility('Control.HasFocus('+ what +')')
	else: controlhasfocus = xbmc.getCondVisibility('ControlGroup('+ custom +').HasFocus('+ what +')')
	
	if (what != "" and not controlhasfocus and action != ""): xbmc.executebuiltin(''+ action +'')
	'''---------------------------'''
	xbmc.sleep(sleep)
	if custom == "0": controlhasfocus = xbmc.getCondVisibility('Control.HasFocus('+ what +')')
	else: controlhasfocus = xbmc.getCondVisibility('ControlGroup('+ custom +').HasFocus('+ what +')')
	#systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
	xbmc.sleep(sleep)
	'''---------------------------'''
	if (what != "" and controlhasfocus and action2 != ""): xbmc.executebuiltin(''+ action2 +'')
	'''---------------------------'''
	return controlhasfocus
	
def findin_systemcurrentcontrol(custom,what,sleep,action,action2):
	'''action = not found | action2 = when found'''
	'''---------------------------'''
	name = 'findin_systemcurrentcontrol'
	if '$LOCALIZE' in what or '$ADDON' in what: what = xbmc.getInfoLabel(what)
	try: what = what.encode('utf-8')
	except: pass
	
	systemcurrentcontrol = xbmc.getInfoLabel('System.CurrentControl')
	if custom == "0" and (what != "" and systemcurrentcontrol != what and action != ""): xbmc.executebuiltin(''+ action +'')
	elif custom == "1" and (what != "" and not what in systemcurrentcontrol and action != ""): xbmc.executebuiltin(''+ action +'')
	elif custom == "2" and (what != "" and systemcurrentcontrol not in what and action != ""): xbmc.executebuiltin(''+ action +'')
	'''---------------------------'''
	xbmc.sleep(sleep)
	systemcurrentcontrol2 = xbmc.getInfoLabel('System.CurrentControl')
	xbmc.sleep(sleep)
	'''---------------------------'''
	if custom == "0" and (what != "" and systemcurrentcontrol2 == what and action2 != ""): xbmc.executebuiltin(''+ action2 +'')
	elif custom == "1" and (what != "" and what in systemcurrentcontrol2 and action2 != ""): xbmc.executebuiltin(''+ action2 +'')
	elif custom == "2" and (what != "" and systemcurrentcontrol2 in what and action2 != ""): xbmc.executebuiltin(''+ action2 +'')
	'''---------------------------'''
	
	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	text = "custom" + space2 + custom + space + "what" + space2 + str(what) + space + "systemcurrentcontrol/2" + space2 + str(systemcurrentcontrol) + space5 + str(systemcurrentcontrol2)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return systemcurrentcontrol2
	
def get_types(value):
	import types
	name = 'get_types' ; printpoint = ""
	returned = str(type(value))

	text = "value" + space2 + str(value) + space + "type" + space2 + returned
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	
	return returned
	'''---------------------------'''

	
def getRandom(custom, min=0, max=100, percent=50):
	'''------------------------------
	---RANDOM------------------------
	------------------------------'''
	import random
	name = 'getRandom' ; printpoint = "" ; TypeError = "" ; extra = "" ; value = "" ; returned = ""

	try:
		custom = int(custom)
		min = int(min)
		max = int(max)
		percent = int(percent)
	except Exception, TypeError:
		printpoint = printpoint + "9"
		extra = extra + newline + 'TypeError' + space2 + str(TypeError)
	
	if not "9" in printpoint:
		'''---------------------------'''
		if custom == 0: value = random.randrange(min,max)
		'''---------------------------'''
		if value <= percent: returned = "ok"
		else: returned = "skip"

	text = "min" + space2 + str(min) + space + "max" + space2 + str(max) + space + "percent" + space2 + str(percent) + newline + "returned" + space2 + str(returned) + space + "value" + space2 + str(value) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
	return returned, value

def installaddon(addonid2, update=True):
	printpoint = "" ; name = 'installaddon' ; addonid2_ = addonid2
	
	if not xbmc.getCondVisibility('System.HasAddon('+ addonid2 +')') and not os.path.exists(addons_path + addonid2):
		printpoint = printpoint + "1"
		if update == True: notification_common("24")
			
	else: printpoint = printpoint + '7'
	if '1' in printpoint:
		if os.path.exists(addons_path + addonid2):
			if update == True:
				printpoint = printpoint + '5'
				xbmc.executebuiltin("UpdateLocalAddons")
			if 'repo' in addonid2: xbmc.executebuiltin("UpdateAddonRepos")
			
		else:
			printpoint = printpoint + '6'
			if not 'resources.' in addonid2:
				notification('Addon Required:[CR]' + addonid2,'','',4000)				
				#xbmc.executebuiltin('ActivateWindow(10025,plugin://'+ addonid2 +',return)')
				xbmc.executebuiltin('RunPlugin('+ addonid2 +')')
	text = 'addonid2_' + space2 + str(addonid2_) + newline + \
	'addonid2' + space2 + str(addonid2)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	'''---------------------------'''
	return printpoint

def getVersion(addon, url):
	name = 'getVersion' ; printpoint = "" ; returned = ""
	from shared_modules3 import OPEN_URL
	read = OPEN_URL(url)
	x = '<addon id="'+addon+'"' ; y = '>'
	line = regex_from_to(read, x, y, excluding=False)
	if line != "" and line != None and line != str(x) + str(y):
		'''continue'''
		x = 'version="' ; y = '"'
		version = regex_from_to(line, x, y, excluding=True)
		if version != "" and version != None and not x in version and not y in version and '.' in version:
			returned = version

	text = 'read' + space2 + str(read) + newline + 'line' + space2 + str(line) + space + 'returned' + space2 + str(returned)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return returned
	
def notification(heading, message, icon, time):
	'''------------------------------
	---Show a Notification alert.----
	------------------------------'''
	name = 'notification' ; printpoint = ""
	'''heading : string - dialog heading | message : string - dialog message. | icon : [opt] string - icon to use. (default xbmcgui.NOTIFICATION_INFO/NOTIFICATION_WARNING/NOTIFICATION_ERROR) | time : [opt] integer - time in milliseconds (default 5000) | sound : [opt] bool - play notification sound (default True)'''
	
	if '$LOCALIZE' in heading or '$ADDON' in heading: heading = xbmc.getInfoLabel(heading)
	if '$LOCALIZE' in message or '$ADDON' in message: message = xbmc.getInfoLabel(message)
	
	icon = ""
	
	dialog.notification(heading, message, icon, time)
	
	#if "addonString" in heading and not "+" in heading: heading = str(heading.encode('utf-8'))
	if "addonString" in heading:
		try: heading = str(heading.encode('utf-8'))
		except: heading = str(heading)
	elif '$LOCALIZE' in heading or '$ADDON' in heading: heading = str(heading)
	if "addonString" in message:
		try: message = str(message.encode('utf-8'))
		except: message = str(message)
	elif '$LOCALIZE' in message or '$ADDON' in message: message = str(message)
	
	time = str(time)

	text = to_utf8(heading) + space3 + to_utf8(message) + space + to_utf8(time)
	try: printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	except Exception, TypeError: printlog(title=name, printpoint=printpoint, text=str(TypeError), level=0, option="")

def removefiles(path, filteroff=[], dialogprogress=""):
	name = 'removefiles' ; printpoint = "" ; path1 = path[-1:] ; TypeError = "" ; extra = ""
	if dialogprogress != "":
		try:
			dialogprogress_ = dialogprogress
			dialogprogress_ + 1 - 1
		except: dilogprogress = ""
	if 1 + 1 == 2:
		if "*" in path: path = path.replace("*","")
		if os.path.exists(path):
			import shutil
			if dialogprogress != "": printpoint = printpoint + "5"
			elif os.path.isdir(path) == True or "\*" in path:
				try:
					if filteroff != []: error
					shutil.rmtree(path)
					printpoint = printpoint + "7"
				except Exception, TypeError:
					if 'The process cannot access the file because it is being used by another process' in TypeError or "global name 'error' is not defined" in TypeError:
						printpoint = printpoint + "5"
			
			if '5' in printpoint:
				printpoint = printpoint + "A"
				if dialogprogress != "":
					printpoint = printpoint + "B"
					dp = xbmcgui.DialogProgress()
					dp.create(addonString_servicefeatherence(32141).encode('utf-8') + space2 + path, "", " ") #Removing
					sumfolders = 0
					for folder in os.listdir(path):
						sumfolders += 1
					progress_ = sumfolders * 100 / (100 - dialogprogress)
				for file in os.listdir(path):
					if dialogprogress != "":
						dp.update(dialogprogress + progress_,str(os.listdir(path))," ")
					x = os.path.join(path, file)
					#print x
					if file in filteroff:
						extra = extra + newline + name + space + 'filteroff (skip)' + space2 + str(x)
					else:
						try: removefiles(x)
						except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError)
				if dialogprogress != "": dp.close
			elif os.path.exists(path):
				try:
					os.remove(path)
					printpoint = printpoint + "7"
				except Exception, TypeError:
					#if 'The process cannot access the file because it is being used by another process' in TypeError or "global name 'error' is not defined" in TypeError:
					pass
			else:
				printpoint = printpoint + "A"
				
		elif os.path.isfile(path) == True:
			printpoint = printpoint + "4"
			os.remove(path)
		else: printpoint = printpoint + "8"
	
	text = "path" + space2 + to_utf8(path) + newline + \
	"filteroff" + space2 + str(filteroff) + space + "dialogprogress" + space2 + str(dialogprogress) + newline + \
	to_utf8(extra)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def copytree(source, target, symlinks=False, ignore=None):
	import shutil
	for item in os.listdir(source):
		s = os.path.join(source, item)
		t = os.path.join(target, item)
		
		if os.path.isdir(s):
			if os.path.exists(t):
				copytree(s, t, symlinks, ignore)
			else: shutil.copytree(s,t, symlinks, ignore)
		else:
			shutil.copy(s,t)
		
		#print "item" + space2 + str(item)
	
def movefiles(source, target):
	name = 'movefiles' ; printpoint = "" ; level=1
	import shutil
	if os.path.exists(target):
		printpoint = printpoint + '1'
		copyfiles(source, target)
		removefiles(source)
	elif os.path.exists(source):
		printpoint = printpoint + '2'
		shutil.move(source, target)
	else:
		printpoint = printpoint + '3'
		xbmc.sleep(1000)
		if os.path.exists(source):
			printpoint = printpoint + '4'
			shutil.move(source, target)
		else:
			printpoint = printpoint + '9'
			level=7
		
	text = "source" + space2 + to_utf8(source) + space + "target" + space2 + to_utf8(target)
	printlog(title=name, printpoint=printpoint, text=text, level=level, option="")
		
def copyfiles(source, target):
	'''Copy files/folders'''
	name = 'copyfiles' ; printpoint = "" ; source1 = source[-1:] ; targetdir = "" ; TypeError = "" ; extra = ""

	import shutil
	try:
		if os.path.isdir(source) == True:
			printpoint = printpoint + "1"
			copytree(source, target, symlinks=False, ignore=None)
		else:
			printpoint = printpoint + "2"
			targetdir = os.path.basename(target)
			targetdir = target.replace(targetdir, "", 1)
			
			if not os.path.exists(targetdir):
				printpoint = printpoint + "3"
				os.mkdir(targetdir)
			if os.path.isfile(source) == True:
				printpoint = printpoint + "4"
				shutil.copy(source, target)
				#shutil.copyfile(source, target)
			else:
				printpoint = printpoint + "5"
				shutil.copy(source, target)
				#terminal('cp -rf '+source+' '+target+'',name + space2 + source + space5 + target) ; printpoint = printpoint + "3"
			
	except Exception, TypeError:
		try: extra = extra + newline + "TypeError" + space2 + str(TypeError)
		except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + 'Unknown'

	text = "source" + space2 + to_utf8(source) + space + "target" + space2 + to_utf8(target) + space + "source1" + space2 + to_utf8(source1) + space + 'targetdir' + space2 + to_utf8(targetdir) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def notification_common(custom):
	if custom == "2": notification(addonString_servicefeatherence(32414).encode('utf-8'),localize(20186),"",4000) #processing, please wait
	elif custom == "3": notification(localize(2102, s=[localize(504)]),"","",2000) #Error, Not Empty!
	elif custom == "4": notification('$ADDON[script.featherence.service 32401]','',"",2000) #Check network connection!...
	elif custom == "5": notification('$ADDON[script.featherence.service 32400]','$LOCALIZE[21451]',"",2000) #Check internet connection!...
	elif custom == "6": notification('Invalid Path','...',"",2000)
	elif custom == "8": notification('$LOCALIZE[16200]',"","",2000) #HAPEULA BUTLA
	elif custom == "9": notification('$LOCALIZE[16200]',addonString_servicefeatherence(32415).encode('utf-8'),"",2000) #HAPEULA BUTLA, LO BUTZHU SINUHIM
	elif custom == "13": notification('$LOCALIZE[79072]',"...","",2000) #HAPEULA ISTAIMA BEHATZLAHA!
	elif custom == "15":
		playlistlength = xbmc.getInfoLabel('Playlist.Length(video)')
		playlistposition = xbmc.getInfoLabel('Playlist.Position(video)')
		notification('$LOCALIZE[74998]','[COLOR=yellow]' + playlistposition + space4 + playlistlength + '[/COLOR]',"",2000) #Playlist Done,
	
	elif custom == "16": notification("Downloading Files...","","",4000) #
	
	elif custom == "17": notification(localize(257),'$LOCALIZE[1446]',"",2000) #Error, Unknown
	elif custom == "22": notification(addonString_servicefeatherence(32407).encode('utf-8'),'',"",4000) #The system is processing for solution...
	elif custom == "23": notification(addonString_servicefeatherence(32406).encode('utf-8'), addonString_servicefeatherence(32405).encode('utf-8'),"",4000) #Active download in background
	elif custom == "24": notification(addonString_servicefeatherence(32402).encode('utf-8'), addonString_servicefeatherence(32403).encode('utf-8'),"",2000) #Addon is missing! Trying to download addon
	elif custom == "25": notification(addonString_servicefeatherence(32142).encode('utf-8'),'',2000)
	elif custom == "26": notification(localize(13328, s=[localize(20331)]), "","",2000)
	elif custom == "27": notification(addonString_servicefeatherence(32100).encode('utf-8'), addonString_servicefeatherence(32101).encode('utf-8'),"",2000) #Your email provider isn't supported.
	elif custom == "100": pass
	elif custom == "101": pass

def write_to_file(path, content, append=False, silent=True , utf8=False):
	'''``r/r+/w/w+/a/a+'''
	name = 'write_to_file' ; printpoint = "" ; extra = "" ; TypeError = ""
	if utf8 == True: import codecs
	try:
		if append == True:
			if utf8 == True: f = codecs.open(path, 'ab', encoding='utf-8')
			else: f = open(path, 'ab')
		else:
			if utf8 == True: f = codecs.open(path, 'wb', 'utf-8')
			else: f = open(path, 'wb')

		f.write(content)
		f.close()
		return True
	except Exception, TypeError:
		extra = extra + newline + 'TypeError' + space2 + str(TypeError)
		text = 'path' + space2 + str(path) + newline + \
		'content' + space2 + str(content) + newline + \
		'append' + space2 + str(append) + space + 'silent' + space2 + str(silent) + space + 'utf8' + space2 + str(utf8) + newline + \
		extra
		if silent != True: level = 0
		else: level = 7
		printlog(title=name, printpoint=printpoint, text=text, level=level, option="")
		return False
	
def read_from_file(infile, silent=True, lines=False, retry=True, createlist=True, printpoint="", addlines=""):
	name = 'read_from_file' ; returned = "" ; TypeError = "" ; extra = "" ; l = [] ; l2 = "" ; lcount = 0
	try:
		if os.path.exists(infile):
			printpoint = printpoint + "1"
			infile_ = open(infile, 'rb')
			if lines == True:
				printpoint = printpoint + "2"
				for line in infile_.readlines():
					#print line
					#[x.encode('utf-8') for x in l]
					#line.decode('utf-8').encode('utf-8')
					if addlines != "":
						line = CleanString(line, filter=[])
						if createlist == True: l.append(str(addlines) + line)
						else: l2 = l2 + ',' + str(addlines) + line
						#l[lcount].encode('utf-8')
						#lcount += 1
					elif createlist == True: l.append(line)
					else: l2 = l2 + ',' + line
					
				if createlist == True: returned = l
				else: returned = l2
			else:
				printpoint = printpoint + "3"
				r = infile_.read()
				returned = str(r)
			infile_.close()
		
		if (returned == "" or returned == None) and retry == True:
			printpoint = printpoint + "6"
			xbmc.sleep(2000)
			read_from_file(infile, silent=silent, lines=lines, retry=False, printpoint=printpoint)
			
	except Exception, TypeError: extra = extra + newline + "TypeError" + space2 + str(TypeError) ; printpoint = printpoint + "9"
	
	if returned != "" or (returned == None or returned == "") and retry == False or 1 + 1 == 2:
		try: returned10 = str(returned[10])
		except: returned10 = ""
		text = "infile" + space2 + str(infile) + space + "lines" + space2 + str(lines) + space + "createlist" + space2 + str(createlist) + newline + \
		"returned10" + space2 + returned10 + space + 'l' + space2 + str(l) + space + 'l2' + space2 + str(l2) + extra
		printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
		
		return returned

def regex_from_to(text, from_string, to_string, excluding=True):
	import re
	name = 'regex_from_to'
	printpoint = "" ; TypeError = "" ; extra = ""
	if excluding:
		try: r = re.search("(?i)" + from_string + "([\S\s]+?)" + to_string, text).group(1)
		except Exception, TypeError:
			extra = newline + "TypeError" + space2 + str(TypeError)
			try:
			 r = re.search("(?i)" + from_string + "([\S\s]+?)" + to_string, text)
			 if r == None: r = ""
			except Exception, TypeError:
				extra = newline + "TypeError" + space2 + str(TypeError)
				r = ""
	else:
		try: r = re.search("(?i)(" + from_string + "[\S\s]+?" + to_string + ")", text).group(1)
		except Exception, TypeError:
			try:
				extra = newline + "TypeError" + space2 + str(TypeError)
				r = re.search("(?i)(" + from_string + "[\S\s]+?" + to_string + ")", text)
				if r == None: r = from_string + to_string
			except Exception, TypeError:
				extra = newline + "TypeError" + space2 + str(TypeError)
				r = ""
	
	r = to_utf8(r)
	#text = text.encode('utf-8')
	if excluding == True or r == "": text2 = "from_string" + space2 + str(from_string) + space + "to_string" + space2 + str(to_string) + space + "r" + space2 + to_unicode(r) + space + extra
	else: text2 = "regex_from_to" + space2 + "from_string" + space2 + "r" + space2 + str(r) + space + extra
	printlog(title=name, printpoint=printpoint, text=text2, level=0, option="")
	return str(r)

def to_utf8(text):
	result = text
	if isinstance(text, unicode):
		result = text.encode('utf-8')
		pass
	return result
	
def to_unicode(text):
	result = text
	if isinstance(text, str):
		result = text.decode('utf-8')
		pass
	return result
	
def replace_word(infile,old_word,new_word, infile_="", LineR=False , LineClean=False):
	name = 'replace_word' ; printpoint = "" ; extra = "" ; TypeError = "" ; value = ""

	if not os.path.isfile(infile): printpoint = printpoint + "9a" #(infile_ == "" or LineR == True) and
	elif old_word == None or new_word == None: printpoint = printpoint + "9b"
	else:
		if LineR == False:
			'''replace all'''
			printpoint = printpoint + "2" #if infile_ == "" or infile_ == None: 
			infile_ = read_from_file(infile, lines=False)
			value=infile_.replace(to_utf8(old_word),to_utf8(new_word))
			'''---------------------------'''
		else:
			'''replace each line'''
			printpoint = printpoint + "3"
			import fileinput, re
			infile_ = read_from_file(infile, lines=True)
			#print infile_
			for line in infile_:
				extra = extra + newline + str(line)
				if LineClean == True and re.match(r'^\s*$', line): line = "" #line.replace('\n\n','\n') #re.match(r'^\s*$', line)
				elif old_word != "" and new_word != "":
					if old_word in line:
						value = value + newline + line.replace(old_word,new_word)
						#line = '\n' + line
						#sys.stdout.write(line)
						'''---------------------------'''
					else: value = value + newline + line
				else:
					value = value + line
				#if value != "": value = value + newline
				'''---------------------------'''
					#line = '\n' + line
					#sys.stdout.write(line)
				
				
				#if line != "": sys.stdout.write(line) #infile__.write(line)
				#infile__.write(value)
				#infile__.close()
		
		infile__=open(infile,'wb')
		infile__.write(value)
		infile__.close()
		'''---------------------------'''
		
	text = "infile" + space2 + str(infile) + space + newline + \
	"old_word" + space2 + str(old_word) + newline + \
	"new_word" + space2 + str(new_word) + newline + \
	extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def ReloadSkin(admin,force=True):
	name = 'ReloadSkin' ; printpoint = ""
	if property_reloadskin == "":
		printpoint = printpoint + '1'
		xbmc.executebuiltin('ActivateWindow(1000)')
		xbmc.executebuiltin('SetProperty(ReloadSkin,true,home)')
		if force == True:
			playerhasmedia = xbmc.getCondVisibility('Player.HasMedia')
			if playerhasmedia: xbmc.executebuiltin('Action(Stop)') ; notification('Video Stop',"","",1000) ; xbmc.sleep(1000)
			notification("..","","",1000)
		xbmc.sleep(200)
		xbmc.executebuiltin('ReloadSkin()')
		if force == True:
			xbmc.sleep(1500)
			xbmc.executebuiltin('AlarmClock(reloadskin,ClearProperty(ReloadSkin,home),00:05,silent)')
		else: xbmc.executebuiltin('AlarmClock(reloadskin,ClearProperty(ReloadSkin,home),0,silent)')
		xbmc.executebuiltin('Action(Back)')
		
		
		#xbmc.executebuiltin('ReplaceWindow(CustomHomeCustomizer.xml)')
	else:
		printpoint = printpoint + '9'
		#xbmc.executebuiltin('RunScript(script.htpt.service,,?mode=215&value=_)')
	
	text = "property_reloadskin" + space2 + str(property_reloadskin)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")

def setProperty(id, value, type="home"):

	name = 'setProperty' ; printpoint = ""
	if value != "": xbmc.executebuiltin('SetProperty('+str(id)+','+str(value)+','+str(type)+')')
	else: xbmc.executebuiltin('ClearProperty('+str(id)+','+str(type)+')')
	xbmc.sleep(10)
	returned = xbmc.getInfoLabel('Window('+str(type)+').Property('+str(id)+')')
	
	text = 'id' + space2 + str(id) + newline + \
	'value' + space2 + str(value) + newline + \
	'type' + space2 + str(type) + newline + \
	'returned' + space2 + str(returned)
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	
def setSkinSetting(custom,set1,set1v, force=False):
	if xbmc.getSkinDir() == 'skin.featherence' or force == True:
		'''------------------------------
		---SET-SKIN-SETTING-1------------
		------------------------------'''
		#set1 = to_utf8(set1)
		name = 'setSkinSetting' ; printpoint = "" ; admin = xbmc.getInfoLabel('Skin.HasSetting(Admin)') ; admin2 = xbmc.getInfoLabel('Skin.HasSetting(Admin2)') ; setting1 = ""
		
		if '$LOCALIZE' in set1v or '$ADDON' in set1v: 
			try:
				set1v = xbmc.getInfoLabel(set1v) ; printpoint = printpoint + "1"
			except Exception, TypeError: printpoint = printpoint + "9"
		''' custom: 0 = Skin.String, 1 = Skin.HasSetting'''
		'''---------------------------'''
		set1v = to_utf8(set1v)
		printpoint = printpoint + "2"
		if custom == "0":
			printpoint = printpoint + "3"
			setting1 = xbmc.getInfoLabel('Skin.String('+ set1 +')')
			setting1 = to_utf8(setting1)
			if setting1 != set1v: xbmc.executebuiltin('Skin.SetString('+ set1 +','+ set1v +')')
			'''---------------------------'''
			
		elif custom == "1":
			printpoint = printpoint + "4"
			setting1 = xbmc.getInfoLabel('Skin.HasSetting('+ set1 +')')
			#print setting1 + "zzz"
			'''---------------------------'''
			if (setting1 == localize(20122) and localize(20122) != "") or setting1 == "true" or setting1 == "True": setting1 = "true"
			else: setting1 = "false"
			'''---------------------------'''
			if (set1v == localize(20122) and localize(20122) != "") or set1v == "true" or set1v == "True": set1v = "true"
			else: set1v = "false"
			'''---------------------------'''
			if setting1 != set1v: xbmc.executebuiltin('Skin.ToggleSetting('+ set1 +')')
			
		'''------------------------------
		---PRINT-END---------------------
		------------------------------'''
		if setting1 != set1v or force == True:
			text = custom + space + set1 + space2 + setting1 + " - " + set1v #newline + "localize(20122)" + space2 + to_utf8(localize(20122))
			'''---------------------------'''
			try: printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
			except Exception, TypeError: printlog(title=name, printpoint=printpoint, text='TypeError: ' + str(TypeError), level=0, option="")

def setsetting_custom1(addon,set1,set1v):
	'''------------------------------
	---SET-ADDON-SETTING-1-----------
	------------------------------'''
	name = 'setsetting_custom1' ; printpoint = "" ; TypeError = "" ; extra = "" 
	try:
		getsetting_custom          = xbmcaddon.Addon(addon).getSetting
		setsetting_custom          = xbmcaddon.Addon(addon).setSetting
	except Exception, TypeError:
		extra = extra + newline + "TypeError" + space2 + str(TypeError)
	
	if TypeError == "":
		set = getsetting_custom(set1)
		set1v = str(set1v)
		'''---------------------------'''
		if set != set1v:
			printpoint = printpoint + '7'
			setsetting_custom(set1,set1v)
			'''---------------------------'''
	
	text = 'addon' + space2 + str(addon) + space + 'set1' + space2 + str(set1) + space + 'set1v' + space2 + str(set1v) + newline + extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")


def stringtodate(dt_str, dt_func):
	#from datetime import datetime
	name = 'stringtodate' ; printpoint = "" ; TypeError = "" ; extra = "" ; count = 0
	dt_str = str(dt_str)
	dt_str = dt_str.replace(" ","",1)
	dt_obj = ""
	#dt_str = '9/24/2010 5:03:29 PM'
	#dt_func = '%m/%d/%Y %I:%M:%S %p'
	if dt_str == "" or dt_func == "" or dt_str == None or dt_func == None:
		printpoint = printpoint + "9"
		#if admin: notification("stringtodate_ERROR!","isEMPTY","",1000)
	else:
		while count < 3 and not "7" in printpoint and not xbmc.abortRequested:
			try:
				if count == 0: from datetime import datetime
				dt_obj = datetime.strptime(dt_str, dt_func)
				printpoint = printpoint + "7"
			except Exception, TypeError:
				dt_obj = "error"

			count += 1
			xbmc.sleep(100)

	'''------------------------------
	---PRINT-END---------------------
	------------------------------'''
	dt_objS = str(dt_obj)
	if TypeError != "": extra = newline + "TypeError" + space2 + str(TypeError) + space + "count" + space2 + str(count)

	text = 'dt_str' + space2 + str(dt_str) + space + 'dt_objS' + space2 + str(dt_objS) + newline + \
	extra
	printlog(title=name, printpoint=printpoint, text=text, level=0, option="")
	return dt_obj
	
class TextViewer_Dialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.text = kwargs.get('text')
        self.header = kwargs.get('header')

    def onInit(self):
        self.getControl(1).setLabel(self.header)
        self.getControl(5).setText(self.text)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        pass

    def onFocus(self, controlID):
        pass


class Custom1000_Dialog(xbmcgui.Window):
  '''progress= | title= | '''
  ACTION_SELECT_ITEM = 7
  def __init__(self):
	extra = "" ; extra2 = "" ; TypeError = "" ; printpoint = "" ; count_set = 0 ; exit_requested = False ; progress = '0' ; title = '' ; addonisrunning = '?'
	progress = xbmc.getInfoLabel('Window(home).Property(TEMP)')
	title = xbmc.getInfoLabel('Window(home).Property(TEMP2)')
	addonisrunning = xbmc.getInfoLabel('Window(home).Property(script.htpt.service_RUNNING)')
	
	self.strActionInfo = xbmcgui.ControlLabel(0, 0, 1260, 680,'', 'Size42B', 'white2','',6)
	self.addControl(self.strActionInfo)
	self.strActionInfo.setLabel(localize(20186))
	
	if progress != "":
		'''Create Dialog Progress'''
		self.strActionInfo = xbmcgui.ControlLabel(0, 50, 1260, 680,'', 'size36B', 'yellow','',6)
		self.addControl(self.strActionInfo)
		self.strActionInfo.setLabel(progress)
	
	if title != "":
		'''Create Subject'''
		self.strActionInfo = xbmcgui.ControlLabel(0, 100, 1260, 680,'', 'size28', 'white','',6)
		self.addControl(self.strActionInfo)
		self.strActionInfo.setLabel(str(title))
		
  def _exit(self):
      global exit_requested
      exit_requested = True
      self.close()

      text = 'progress' + space2 + str(progress) + space + 'title' + space2 + str(title) + newline + \
      'addonisrunning' + space2 + str(addonisrunning)
      printlog(title='Custom1000_Dialog', printpoint=printpoint, text=text, level=0, option="")
      return dt_obj
	  
  def onAction(self, action):
	if action == ACTION_PREVIOUS_MENU:
	  self._exit()
	elif action == ACTION_SELECT_ITEM:
	  self._exit()



def printlog(title="", printpoint="", text="", level=0, option=""):
	exe = ""
	
	if xbmc.getCondVisibility('System.HasAddon(script.featherence.service)'):
		getsetting_servicefeatherence = xbmcaddon.Addon('script.featherence.service').getSetting
		admin = getsetting_servicefeatherence('admin')
	else: admin = 'false'
	if xbmc.getSkinDir() == 'skin.featherence':
		admin2 = xbmc.getInfoLabel('Skin.HasSetting(Admin)')
		if admin2: admin2 = 'true'
		else: admin2 = 'false'
	else: admin2 = 'false'
	
	macaddress = xbmc.getInfoLabel('Network.MacAddress')
	User_Name = xbmc.getInfoLabel('Skin.String(User_Name)')
	if macaddress == '0C:8B:FD:9D:2F:CE' or User_Name == 'finalmakerr': admin3 = 'true'
	elif macaddress != "": admin3 = 'false'
	else: admin3 = 'false'
	
	if level == 0:
		if admin == 'true' and admin2 == 'true' and admin3 == 'true': exe = 0
	elif level == 1:
		if admin == 'true' and admin2 == 'true': exe = 1
	elif level == 2:
		if admin == 'true': exe = 2
	elif level == 3:
		if admin == 'true': exe = 3
	else: exe = 'ALL'
	
	if exe != "":
		message = printfirst + to_utf8(title) + '_LV' + str(printpoint) + space + to_utf8(text)
		xbmc.log(msg=to_utf8(message), level=xbmc.LOGNOTICE)
	return exe

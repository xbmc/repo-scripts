import xbmc, xbmcgui, xbmcaddon

from variables import *
from shared_variables import *
from shared_modules import *
from debug2 import *

def getAttachment(attachmentFilePath):
	name = 'getAttachment' ; printpoint = ""
	from email.MIMEText import MIMEText
	from email.MIMEBase import MIMEBase
	from email.MIMEImage import MIMEImage
	from email import Encoders
	import mimetypes, base64
	contentType, encoding = mimetypes.guess_type(attachmentFilePath)

	if contentType is None or encoding is not None:
		contentType = 'application/octet-stream'
	mainType, subType = contentType.split('/', 1)
	file = open(attachmentFilePath, 'rb')

	if mainType == 'text':
		attachment = MIMEText(file.read())
	elif mainType == 'message':
		attachment = email.message_from_file(file)
	elif mainType == 'image':
		attachment = MIMEImage(file.read(),_subType=subType)
	elif mainType == 'audio':
		attachment = MIMEAudio(file.read(),_subType=subType)
	else:
		attachment = MIMEBase(mainType, subType)
		attachment.set_payload(file.read())
		encoders.encode_base64(attachment)
	file.close()
	attachment.add_header('Content-Disposition', 'attachment',   filename=os.path.basename(attachmentFilePath))
	
	text = "attachmentFilePath" + space2 + str(attachmentFilePath) + newline + \
	"contentType" + space2 + str(contentType) + newline + \
	"encoding" + space2 + str(encoding) + newline + \
	"mainType" + space2 + str(mainType) + newline + \
	"subType" + space2 + str(subType) + newline
	#"attachment" + space2 + str(attachment)
	printlog(title='getAttachment', printpoint=printpoint, text=text, level=0, option="")

	return attachment
	
def sendMail(Debug_Email, Debug_Password, subject, text, *attachmentFilePaths):
	import smtplib
	from email.mime.multipart import MIMEMultipart
	from email.MIMEText import MIMEText
	#from email.MIMEImage import MIMEImage
	#from email import Encoders
	TypeError = "" ; extra = "" ; gmailUser = "" ; count = 0
	SMTP_SSL = False
	#recipient = 'infohtpt@gmail.com'
	#if 1 + 1 == 2:
	try:
		dp = xbmcgui.DialogProgress()
		dp.create(addonString(32095), addonString(10),"")
		while count == 0 and not dp.iscanceled() and not xbmc.abortRequested:
			if '@gmail.com' in Debug_Email: mailServer = smtplib.SMTP('smtp.gmail.com', 587) #, timeout=20
			elif '@walla.com' in Debug_Email:
				mailServer = smtplib.SMTP_SSL('out.walla.co.il', 587)
				SMTP_SSL = True
			elif '@walla.co.il' in Debug_Email:
				mailServer = smtplib.SMTP_SSL('out.walla.co.il', 587)
				SMTP_SSL = True
			else:
				notification_common('27')
				count += 1 ; xbmc.sleep(500)
			
			msg = MIMEMultipart()
			msg['From'] = Debug_Email
			msg['To'] = recipient
			msg['Subject'] = subject
			msg.attach(MIMEText(text))
			
			dp.update(10,addonString(32094), addonString(32093) % ("1","4"))
			if str(attachmentFilePaths) != "('',)":
				for attachmentFilePath in attachmentFilePaths:
					msg.attach(getAttachment(attachmentFilePath))
			else:
				pass
				#msg.attach(getAttachment(addonIcon))
			
			dp.update(20,addonString(32094), addonString(32093) % ("1","4"))
			#mailServer.ehlo()
			if SMTP_SSL == False:
				mailServer.starttls()
			dp.update(30,addonString(32094), addonString(32093) % ("2","4"))
			mailServer.ehlo()
			dp.update(40,addonString(32094), addonString(32093) % ("3","4"))
			mailServer.login(Debug_Email, Debug_Password)	
			dp.update(50,addonString(32094), addonString(32093) % ("3","4"))
			
			mailServer.sendmail(Debug_Email, recipient, msg.as_string())
			mailServer.quit()
			count += 1
			dp.update(100,addonString(32094), addonString(32093) % ("4","4"))
			notification(addonString(74483), localize(20186), "", 2000)
			returned = 'ok'
			'''---------------------------'''
	#try: test = 'test'
	except Exception, TypeError:
		try: mailServer.quit()
		except: pass
		notification(addonString(32092).encode('utf-8'), str(TypeError), "", 2000)
		
		if "535, '5.7.8 Username and Password not accepted." in TypeError:
			'''gmail'''
			returned = 'skip'
		elif "552," in TypeError and "5.2.3 Your message exceeded Google" in TypeError:
			'''gmail'''
			returned = 'error'
		elif "534, '5.7.14" in TypeError:
			'''gmail'''
			returned = 'skip'
		elif 'Server not connected' in TypeError:
			'''outlook'''
			returned = 'skip'
		elif 'getaddrinfo failed' in TypeError:
			returned = 'skip2'
		elif 'Connection unexpectedly closed' in TypeError:
			'''outlook'''
			returned = 'skip'
		else:
			returned = 'skip'
			'''---------------------------'''
			
	dp.close
	text = "returned" + space2 + to_utf8(returned) + newline + \
	"Debug_Email" + space2 + to_utf8(Debug_Email) + newline + \
	"recipient" + space2 + to_utf8(recipient) + newline + \
	"attachmentFilePaths" + space2 + str(attachmentFilePaths) + newline + \
	"extra" + space2 + to_utf8(extra)
	printlog(title='sendMail', printpoint=printpoint, text=text, level=1, option="")

	return returned, str(TypeError)

def SendDebug(Debug_Email, Debug_Password, Debug_Title, Debug_Message, Debug_File):
	printpoint = "" ; TypeError = "" ; TypeError2 = "" ; extra = ""
	
	returned, TypeError = sendMail(Debug_Email, Debug_Password, Debug_Title, Debug_Message, Debug_File)
	
	if returned == None: printpoint = printpoint + "6"
	elif returned == "error":
		printpoint = printpoint + "9"
	elif 'ok' in returned:
		printpoint = printpoint + "7"
	else: printpoint = printpoint + "6"
	
	if "6" in printpoint:
		'''------------------------------
		---PRINT-MAIL-FAILED------------
		------------------------------'''
		if not "skip2" in returned: printpoint = printpoint + "C"
		
		if "error" in returned: pass
		elif "skip2" in returned: pass
		elif "E" in printpoint and 1 + 1 == 3:
			notification_common("2")
			SendDebug(Debug_Email, Debug_Password, Debug_Title, Debug_Message, Debug_File)
		else:
			returned = dialogyesno(addonString(32092).encode('utf-8'), addonString(21).encode('utf-8') + '[CR]' + str(TypeError))
			if returned == 'ok': SendDebug(Debug_Email, Debug_Password, Debug_Title, Debug_Message, Debug_File)
			else:
				notification(localize(16200), addonString(10), "", 2000)
				'''---------------------------'''
	
	elif "7" in printpoint or "9" in printpoint:
		'''------------------------------
		---PRINT-MAIL-SUCUESS------------
		------------------------------'''
		dialogok(addonString(32096).encode('utf-8'), 'www.facebook.com/groups/featherence/', "" ,Debug_Message,line2c="yellow")
		setsetting('Debug_Title',"")
		setsetting('Debug_Message',"")
		setsetting('Debug_Email',Debug_Email)
		if Debug_PasswordKeeper == 'true': setsetting('Debug_Password',Debug_Password)
		'''---------------------------'''
	
	if Debug_PasswordKeeper != 'true': setsetting('Debug_Password',"")
	
	text = "returned" + space2 + to_utf8(returned) + newline + \
	"Debug_Title" + space2 + to_utf8(Debug_Title) + newline + \
	"Debug_Message" + space2 + to_utf8(Debug_Message) + newline + \
	"Debug_File" + space2 + to_utf8(Debug_File) + extra
	printlog(title='SendDebug', printpoint=printpoint, text=text, level=0, option="")
	
def upload_file(file, filesize):
	name = 'upload_file' ; printpoint = "" ; TypeError = "" ; extra = ""
	returned = "" ; paste_id = "" ; count = 0
	import re, urllib2, json
	
	dp = xbmcgui.DialogProgress()
	dp.create(addonString(32090) % (str(os.path.basename(filesize))), addonString(10).encode('utf-8'),'')
	
	while count == 0 and not dp.iscanceled() and not xbmc.abortRequested:
		file_content = open(file, 'rb').read()
		dp.update(10,addonString(32094), addonString(32093) % ("1","4") + '[CR]' + str(filesize))
		for pattern, repl in REPLACES:
			file_content = re.sub(pattern, repl, file_content)
		post_dict = {
			'data': file_content,
			'project': 'www',
			'language': 'text',
			'expire': 1209600,
		}
		dp.update(20,addonString(32094), addonString(32093) % ("1","4") + '[CR]' + str(filesize))
		post_data = json.dumps(post_dict)
		headers = {
			'User-Agent': '%s-%s' % (addonName, addonVersion),
			'Content-Type': 'application/json',
		}
		dp.update(30,addonString(32094), addonString(32093) % ("2","4") + '[CR]' + str(filesize))
		req = urllib2.Request(UPLOAD_URL, post_data, headers)
		dp.update(40,addonString(32094), addonString(32093) % ("3","4") + '[CR]' + str(filesize))
		try:
			response = urllib2.urlopen(req, timeout=60)
			response = response.read()
		except Exception, TypeError:
			extra = extra + newline + 'TypeError' + space2 + str(TypeError)
			
		dp.update(50,addonString(32094), addonString(32093) % ("3","4") + '[CR]' + str(filesize))

		try:
			response_data = json.loads(response)
		except Exception, TypeError:
			response_data = None
			extra = extra + newline + 'TypeError' + space2 + str(TypeError)
		if response_data and response_data.get('result', {}).get('id'):
			paste_id = response_data['result']['id']
			if paste_id != "":
				dp.update(100,addonString(32094), addonString(32093) % ("4","4"))
				printpoint = printpoint + '7'
				returned = 'http://xbmclogs.com/' + paste_id
		else:
			printpoint = printpoint + '9'

		count += 1
		
	text = "file" + space2 + str(file) + newline + \
	"headers" + space2 + str(headers) + newline + \
	"req" + space2 + str(req) + newline + \
	"response_data" + space2 + str(response_data) + newline + \
	"returned" + space2 + str(returned) + extra
	printlog(title=name, printpoint=printpoint, text=text, level=7, option="")
	
	dp.close
	if 'timed out' in extra:
		dialogok('Your %s is too big!' % (str(filesize)),'You should restart your Kodi and try again!','','')
		
	return returned

	
	
	
def upload_file2(file):
	name = 'upload_file2' ; printpoint = "" ; TypeError = "" ; extra = ""
	returned = "" ; paste_id = "" ; count = 0
	import re, urllib, urllib2, json
	
	dp = xbmcgui.DialogProgress()
	dp.create(addonString(32090), addonString(10),"")
	
	while count == 0 and not dp.iscanceled() and not xbmc.abortRequested:
		#file_content = getAttachment(file)
		file_content = file
		dp.update(10,addonString(32094), addonString(32093) % ("1","4"))
		#'expire': 1209600,
		post_dict = {
			'key': api_imagebin_featherence,
			'file': file_content,
		}
		post_dict = urllib.urlencode(post_dict)

		dp.update(20,addonString(32094), addonString(32093) % ("1","4"))
		
		post_data = json.dumps(post_dict)
		headers = {
			'User-Agent': '%s-%s' % (addonName, addonVersion),
			'Content-Type': 'application/json',
		}
		dp.update(30,addonString(32094), addonString(32093) % ("2","4"))
		req = urllib2.Request(UPLOAD_URL2, post_data, headers)
		dp.update(40,addonString(32094), addonString(32093) % ("3","4"))
		print 'req' + space2 + str(req)
		response = urllib2.urlopen(req).read()
		dp.update(50,addonString(32094), addonString(32093) % ("3","4"))

		try:
			response_data = json.loads(response)
		except Exception, TypeError:
			response_data = None
		if response_data and response_data.get('result', {}).get('id'):
			paste_id = response_data['result']['id']
			if paste_id != "":
				dp.update(100,addonString(32094), addonString(32093) % ("4","4"))
				printpoint = printpoint + '7'
				returned = 'http://imagebin.ca' + paste_id
		else:
			printpoint = printpoint + '9'
		count += 1
		
	text = "file" + space2 + str(file) + newline + \
	"headers" + space2 + str(headers) + newline + \
	"post_data" + space2 + str(post_data) + newline + \
	"req" + space2 + str(req) + newline + \
	"response_data" + space2 + str(response_data) + newline + \
	"returned" + space2 + str(returned) + newline
	printlog(title=name, printpoint=printpoint, text=text, level=7, option="")
	
	dp.close
	return returned

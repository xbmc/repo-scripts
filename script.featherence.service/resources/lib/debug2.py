import xbmcaddon, sys, os

from variables import *
from shared_variables import *

Debug_Email = getsetting('Debug_Email')
Debug_Password = getsetting('Debug_Password')
Debug_Title = getsetting('Debug_Title')
Debug_Message = getsetting('Debug_Message')
Debug_PasswordKeeper = getsetting('Debug_PasswordKeeper')

recipient = 'featherence@groups.facebook.com'
Debug_EmailL = ['@gmail.com', '@walla.com', '@walla.co.il']
Debug_File = ""

if systemplatformwindows:
	file1 = os.path.join(home_path, 'kodi.log')
	file2 = os.path.join(home_path, 'kodi.old.log')
else:
	file1 = os.path.join(temp_path, 'kodi.log')
	file2 = os.path.join(temp_path, 'kodi.old.log')

BASE_URL = 'http://xbmclogs.com'
UPLOAD_URL = BASE_URL + '/api/json/create'

BASE_URL2 = 'http://imagebin.ca'
UPLOAD_URL2 = BASE_URL2 + '/api/json/create'

REPLACES = (
    ('//.+?:.+?@', '//USER:PASSWORD@'),
    ('<user>.+?</user>', '<user>USER</user>'),
    ('<pass>.+?</pass>', '<pass>PASSWORD</pass>'),
)
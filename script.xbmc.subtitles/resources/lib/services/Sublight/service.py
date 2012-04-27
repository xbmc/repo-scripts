# -*- coding: utf-8 -*- 

################################   Sublight.si #################################


import sys
import os
import xmlrpclib
from utilities import  languageTranslate, log
import time
import array
import httplib
import xbmc
import xml.dom.minidom
import xml.sax.saxutils as SaxUtils
import base64
import gui

try:
  #Python 2.6 +
  from hashlib import md5
except ImportError:
  #Python 2.5 and earlier
  from md5 import new as md5

_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, language1, language2, language3, stack ): #standard input

  subtitles_list = []    
  for x in range(3):
    exec("if language%i == 'Serbian'            : language%i = 'SerbianLatin' "     % (x+1,x+1,))
    exec("if language%i == 'Bosnian'            : language%i = 'BosnianLatin' "     % (x+1,x+1,))
  sublightWebService = SublightWebService()
  session_id = sublightWebService.LogInAnonymous()
  
  try:
    video_hash = calculateVideoHash(file_original_path)
  except:
    video_hash = "0000000000000000000000000000000000000000000000000000"
  
  subtitles_list = []
  
  if len(tvshow) < 1:        
    movie_title = title
    episode = ""
    season = ""
  else:
    movie_title = tvshow     
  year = str(year)
       
  log( __name__ ,"Sublight Hash [%s]"                                   % str(video_hash) )
  log( __name__ ,"Language 1: [%s], Language 2: [%s], Language 3: [%s]" % (language1 ,language2 , language3,) )
  log( __name__ ,"Search Title:[%s]"                                    % movie_title )
  log( __name__ ,"Season:[%s]"                                          % season )
  log( __name__ ,"Episode:[%s]"                                         % episode )
  log( __name__ ,"Year:[%s]"                                            % year )
  
  subtitles_list = sublightWebService.SearchSubtitles(session_id,
                                                      video_hash,
                                                      movie_title,
                                                      year,season,
                                                      episode,
                                                      language2,
                                                      language1,
                                                      language3
                                                      )
  
  return subtitles_list, session_id, ""  #standard output
  


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input

  subtitle_id              = subtitles_list[pos][ "ID" ]
  language                 = subtitles_list[pos][ "language_name" ]
  sublightWebService       = SublightWebService()
  ticket_id, download_wait = sublightWebService.GetDownloadTicket(session_id, subtitle_id)
  
  if ticket_id != "" :
    icon =  os.path.join(__cwd__,"icon.png")
    if download_wait > 0 :
      delay = int(download_wait)
      for i in range (int(download_wait)):
        line2 = "download will start in %i seconds" % (delay,)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,1000,%s)" % (__scriptname__,line2,icon))
        delay -= 1
        time.sleep(1)

    subtitle_b64_data = sublightWebService.DownloadByID(session_id, subtitle_id, ticket_id)
    base64_file_path = os.path.join(tmp_sub_dir, "tmp_su.b64")
    base64_file      = open(base64_file_path, "wb")
    base64_file.write( subtitle_b64_data )
    base64_file.close()
    base64_file      = open(base64_file_path, "r")
    zip_file         = open(zip_subs, "wb")          
    base64.decode(base64_file, zip_file)
    base64_file.close()
    zip_file.close()
  
  return True,language, "" #standard output
  
#
# Integer => Hexadecimal
#
def dec2hex(n, l=0):
  # return the hexadecimal string representation of integer n
  s = "%X" % n
  if (l > 0) :
    while len(s) < l:
      s = "0" + s 
  return s


def calculateVideoHash(filename, isPlaying = True):
  #
  # Check file...
  #
  if not os.path.isfile(filename) :
    return ""
  
  if os.path.getsize(filename) < 5 * 1024 * 1024 :
    return ""

  #
  # Init
  #
  sum = 0
  hash = ""
  
  #
  # Byte 1 = 00 (reserved)
  #
  number = 0
  sum = sum + number
  hash = hash + dec2hex(number, 2) 
  
  #
  # Bytes 2-3 (video duration in seconds)
  #   
  seconds = int( xbmc.Player().getTotalTime() )
  # 
  sum = sum + (seconds & 0xff) + ((seconds & 0xff00) >> 8)
  hash = hash + dec2hex(seconds, 4)
  
  #
  # Bytes 4-9 (video length in bytes)
  #
  filesize = os.path.getsize(filename)
  
  sum = sum + (filesize & 0xff) + ((filesize & 0xff00) >> 8) + ((filesize & 0xff0000) >> 16) + ((filesize & 0xff000000) >> 24)
  hash = hash + dec2hex(filesize, 12) 
  
  #
  # Bytes 10-25 (md5 hash of the first 5 MB video data)
  #
  f = open(filename, mode="rb")
  buffer = f.read( 5 * 1024 * 1024 )
  f.close()
  
  md5hash = md5()
  md5hash.update(buffer)
  
  array_md5 = array.array('B')
  array_md5.fromstring(md5hash.digest())
  for b in array_md5 :
    sum = sum + b

  hash = hash + md5hash.hexdigest()
  
  #
  # Byte 26 (control byte)
  # 
  hash = hash + dec2hex(sum % 256, 2)
  hash = hash.upper()
  
  return hash
    
#
# SublightWebService class
#
class SublightWebService :
  def __init__ (self):
    self.SOAP_HOST                  = "www.sublight.si"
    self.SOAP_SUBTITLES_API_URL     = "/API/WS/Sublight.asmx"
    self.SOAP_SUBLIGHT_UTILITY_URL  = "/SublightUtility.asmx"
    self.LOGIN_ANONYMOUSLY_ACTION   = "http://www.sublight.si/LogInAnonymous4"
    self.SEARCH_SUBTITLES_ACTION    = "http://www.sublight.si/SearchSubtitles3"
    self.GET_DOWNLOAD_TICKET_ACTION = "http://www.sublight.si/GetDownloadTicket2"
    self.DOWNLOAD_BY_ID_ACTION      = "http://www.sublight.si/DownloadByID4"
    self.LOGOUT_ACTION              = "http://www.sublight.si/LogOut"
    
  #
  # Perform SOAP request...
  #
  def SOAP_POST (self, SOAPUrl, SOAPAction, SOAPRequestXML):
    # Handles making the SOAP request
    h = httplib.HTTPConnection(self.SOAP_HOST)
    headers = {
              'Host'           : self.SOAP_HOST,
              'Content-Type'   :'text/xml; charset=utf-8',
              'Content-Length' : len(SOAPRequestXML),
              'SOAPAction'     : '"%s"' % SOAPAction,
              }
    h.request ("POST", SOAPUrl, body=SOAPRequestXML, headers=headers)
    r = h.getresponse()
    d = r.read()
    h.close()
  
    return d
  
  #
  # LoginAnonymous3
  #
  def LogInAnonymous(self):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <LogInAnonymous4 xmlns="http://www.sublight.si/">
                          <clientInfo>
                            <ClientId>OpenSubtitles_OSD</ClientId>
                            <ApiKey>b44bc9b9-91f4-45be-8a49-c9b18ca86566</ApiKey>
                          </clientInfo>
                        </LogInAnonymous4>
                      </soap:Body>
                    </soap:Envelope>"""
    
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.LOGIN_ANONYMOUSLY_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    sessionId = xmlUtils.getText( resultDoc, "LogInAnonymous4Result" )
    
    # Return value
    return sessionId


    #
    # LogOut
    #
  def LogOut(self, sessionId):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <LogOut xmlns="http://www.sublight.si/">
                          <session>%s</session>
                        </LogOut>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionId )
                      
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.LOGOUT_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    result    = xmlUtils.getText( resultDoc, "LogOutResult" )
    
    # Return value
    return result
    
  #
  # SearchSubtitles
  #
  def SearchSubtitles(self, sessionId, videoHash, title, year, season, episode,language1, language2, language3):
    title = SaxUtils.escape(title)    
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <SearchSubtitles3 xmlns="http://www.sublight.si/">
                          <session>%s</session>
                          <videoHash>%s</videoHash>
                          <title>%s</title>
                          %s
                          %s
                          %s
                          <languages>
                            %s
                            %s
                            %s
                          </languages>
                          <genres>
                            <Genre>Movie</Genre>
                            <Genre>Cartoon</Genre>
                            <Genre>Serial</Genre>
                            <Genre>Documentary</Genre>
                            <Genre>Other</Genre>
                            <Genre>Unknown</Genre>
                          </genres>
                          <rateGreaterThan xsi:nil="true" />
                        </SearchSubtitles3>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionId, 
                                            videoHash,
                                            title,
                                            ( "<year>%s</year>" % year, "<year xsi:nil=\"true\" />" ) [ year == "" ],
		( "<season>%s</season>" % season, "<season xsi:nil=\"true\" />" ) [ season == "" ],                                                  
		( "<episode>%s</episode>" % episode, "<episode xsi:nil=\"true\" />" ) [ episode == "" ],
		  "<SubtitleLanguage>%s</SubtitleLanguage>" % language1,
                                            ( "<SubtitleLanguage>%s</SubtitleLanguage>" % language2, "" ) [ language2 == "None" ],
                                            ( "<SubtitleLanguage>%s</SubtitleLanguage>" % language3, "" ) [ language3 == "None" ] )
    
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.SEARCH_SUBTITLES_ACTION, requestXML)
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils() 
    result    = xmlUtils.getText(resultDoc, "SearchSubtitles3Result")
    subtitles = []      
    if (result == "true") :
      # Releases...
      releases = dict()
      releaseNodes = resultDoc.getElementsByTagName("Release")
      if releaseNodes != None :
        for releaseNode in releaseNodes :
          subtitleID  = xmlUtils.getText( releaseNode, "SubtitleID" )
          releaseName = xmlUtils.getText( releaseNode, "Name" )
          if releaseName > "" :
            releases[ subtitleID ] = releaseName
      # Subtitles...
      subtitleNodes = resultDoc.getElementsByTagName("Subtitle")
      for subtitleNode in subtitleNodes:
        title         = xmlUtils.getText( subtitleNode, "Title" )
        year          = xmlUtils.getText( subtitleNode, "Year" )
        try:
          release     = releases.get( subtitleID, ("%s (%s)" % ( title, year  ) ) )
        except :
          release     = "%s (%s)" % ( title, year )
        language      = xmlUtils.getText( subtitleNode, "Language" )
        subtitleID    = xmlUtils.getText( subtitleNode, "SubtitleID" )
        mediaType     = xmlUtils.getText( subtitleNode, "MediaType" )
        numberOfDiscs = xmlUtils.getText( subtitleNode, "NumberOfDiscs" ) 
        downloads     = xmlUtils.getText( subtitleNode, "Downloads" )
        isLinked      = xmlUtils.getText( subtitleNode, "IsLinked" )
        rate          = float(xmlUtils.getText( subtitleNode, "Rate" ))
        
        if language == "SerbianLatin": language = "Serbian"
        
        if isLinked == "true":
          linked = True
        else:
          linked = False    
        
        if len(language) > 1:
          flag_image = "flags/%s.gif" % (languageTranslate(language,0,2))
        else:                                                           
          flag_image = "-.gif"              

        subtitles.append( { "title"         : title,
                            "year"          : year,
                            "filename"      : release,
                            "language_name" : language,
                            "ID"            : subtitleID,
                            "mediaType"     : mediaType,
                            "numberOfDiscs" : numberOfDiscs,
                            "downloads"     : downloads,
                            "sync"          : linked,
                            "rating"        : str(int(round(rate*2))),
                            "language_flag" :flag_image
                            } )            
    
    # Return value
    return subtitles       
  
  #
  # GetDownloadTicket
  #
  def GetDownloadTicket(self, sessionID, subtitleID):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <GetDownloadTicket2 xmlns="http://www.sublight.si/">
                          <session>%s</session>
                          <id>%s</id>
                        </GetDownloadTicket2>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionID, subtitleID )
                    
    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.GET_DOWNLOAD_TICKET_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    result    = xmlUtils.getText( resultDoc, "GetDownloadTicket2Result" )
    
    ticket = ""
    if result == "true" :
      ticket  = xmlUtils.getText( resultDoc, "ticket" )
      que     = xmlUtils.getText( resultDoc, "que" )
        
    # Return value
    return ticket, que
  
  #
  # DownloadByID4 
  #
  def DownloadByID(self, sessionID, subtitleID, ticketID):
    # Build request XML...
    requestXML = """<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                                   xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                      <soap:Body>
                        <DownloadByID4 xmlns="http://www.sublight.si/">
                          <sessionID>%s</sessionID>
                          <subtitleID>%s</subtitleID>
                          <codePage>1250</codePage>
                          <removeFormatting>false</removeFormatting>
                          <ticket>%s</ticket>
                        </DownloadByID4>
                      </soap:Body>
                    </soap:Envelope>""" % ( sessionID, subtitleID, ticketID )

    # Call SOAP service...
    resultXML = self.SOAP_POST (self.SOAP_SUBTITLES_API_URL, self.DOWNLOAD_BY_ID_ACTION, requestXML)
    
    # Parse result
    resultDoc = xml.dom.minidom.parseString(resultXML)
    xmlUtils  = XmlUtils()
    result    = xmlUtils.getText( resultDoc, "DownloadByID4Result" )
    
    base64_data = ""
    if result == "true" :
      base64_data = xmlUtils.getText( resultDoc, "data" )
    
    # Return value
    return base64_data
        
#
#
#
class XmlUtils :
  def getText (self, nodeParent, childName ):
    # Get child node...
    node = nodeParent.getElementsByTagName( childName )[0]
    
    if node == None :
      return None
    
    # Get child text...
    text = ""
    for child in node.childNodes:
      if child.nodeType == child.TEXT_NODE :
        text = text + child.data
    return text

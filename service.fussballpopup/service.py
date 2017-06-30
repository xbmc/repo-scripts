#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, sys, os, urlparse,json
import xbmc ,xbmcgui, xbmcaddon,xbmcvfs
import urllib2,urllib,json
import shutil
import re,md5
import socket, cookielib
import feedparser
import HTMLParser,xbmcplugin
import functions
import popupwindow

from dateutil import parser
from django.utils.encoding import smart_str
from resources.lib.funktionen import *

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('path') )

profile    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
temp       = xbmc.translatePath( os.path.join( profile, 'temp', '') ).decode("utf-8")

def translation(text):
  text=__addon__.getLocalizedString(text).encode("utf-8")
  return text


yellow = xbmc.translatePath( os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'grafix','yellow.png')).decode('utf-8')


   
debug("YELLOW :" + yellow)    

if not xbmcvfs.exists(temp):
   xbmcvfs.mkdirs(temp)
   
def ersetze(text):
# 
    text=text.replace("<br>","").replace("<b>","").replace("</b>","").replace("<br/>","")
    text=text.replace ("</p>","").replace("<p>","").replace("<div id='articleTranscript'>","").replace("<br />","").replace('<div id="image-caption">',"").replace("  ","").replace("<p","")
    text=text.replace ("<em>","").replace("</em>","")
    text=text.replace ("<h3>","").replace("</h3>","")
    text=text.replace ('<span class="rottext>',"")
    text=text.replace ('<span class="gruentext>',"")
    text=text.replace ("<hr>","")
    text = text.replace("&quot;", "\"")
    text = text.replace("&apos;", "'")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&laquo;", "<<")
    text = text.replace("&raquo;", ">>")
    text = text.replace("&#039;", "'")
    text = text.replace("&#8220;", "\"")
    text = text.replace("&#8221;", "\"")
    text = text.replace("&#8211;", "-")
    text = text.replace("&#8216;", "\'")
    text = text.replace("&#8217;", "\'")
    text = text.replace("&#9632;", "")
    text = text.replace("&#8226;", "-")
    text = text.replace('<span class="caps">', "")
    text = text.replace('</span>', "")        
    text = text.replace('\/', "/")    
    #text = text.replace('\n', "")    
    text = text.strip()
    return text
  
    
def delspiel(ids,liste):  
  fileinhalt=""
  filename       = xbmc.translatePath( os.path.join( temp, 'spiel.txt') ).decode("utf-8")     
  for zeile in liste:
    try:  
      arr=zeile.split("##")    
      spielnr=arr[4] 
    except:
      spielnr=""
    if not spielnr in ids and "##" in zeile:
         debug("Attache Line"+ zeile)
         fileinhalt=fileinhalt+"\n"+zeile          
    else:
         debug("Delete Line"+ zeile)
  with open(filename, 'w') as fp :
    fp.write(fileinhalt)

   
if __name__ == '__main__':
    cimg=""
    xbmc.log("FussballPupup:  Starte Plugin")

    schown=[]
    monitor = xbmc.Monitor()   
    oldi=0
    while not monitor.abortRequested():
      titlelist=[]
      cimglist1=[]
      cimglist2=[]
      greyoutlist=[]
      lesezeitlist=[]
      timelist=[] 
      ids=[]
      ins=[]
      auss=[]
      anzal_meldungen=[]        
      foto1=""      
      foto2=""      
      xbmc.log("Get Enviroment")
      bild=__addon__.getSetting("bild") 
      lesezeit=__addon__.getSetting("lesezeit")
      greyout=__addon__.getSetting("greyout")
      xmessage=__addon__.getSetting("x-message")  
      ymessage=__addon__.getSetting("y-message")  
      hoehemessage=__addon__.getSetting("hoehe-message")  
      breitemessage=__addon__.getSetting("breite-message")  
      hoehebild1=__addon__.getSetting("hoehe-bild1")  
      breitebild1=__addon__.getSetting("breite-bild1")  
      hoehebild2=__addon__.getSetting("hoehe-bild2")  
      breitebild2=__addon__.getSetting("breite-bild2")
      font=__addon__.getSetting("font")  
      fontcolor=__addon__.getSetting("fontcolor") 
      oldmessages=__addon__.getSetting("oldmessages") 
      spielzeit=__addon__.getSetting("spielzeit") 
      karten=__addon__.getSetting("karten") 
      tor=__addon__.getSetting("tor") 
      elfmeter=__addon__.getSetting("elfmeter") 
      spielerwechsel=__addon__.getSetting("spielerwechsel") 
      anzahlmeldungen=__addon__.getSetting("anzahlmeldungen")
      
      filename       = xbmc.translatePath( os.path.join( temp, 'spiel.txt') ).decode("utf-8")
      gesamtliste=[]
      if xbmcvfs.exists(filename) :
        with open(filename, 'r') as fp :        
          contentf=fp.read()        
        liste=contentf.split("\n")                
        
        
        spiellisteneu=[]        
        delliste=[]
        timelist=[]
        
        # Spiele Ermitteln
        # File WIrd in Arraysgeladen
        name=[]
        live_status=[]
        lieganr=[]
        dayid=[]
        spielnr=[]
        aus=[]
        inn=[]
        match_date=[]
        match_time=[]
        lsv=[]
        ganzeliega=[]        
        minute_now=[]
        liste=contentf.split("\n")
        for spiel in liste:  
          if  "##" in spiel:          
            arr=spiel.split("##")
            debug("spielnr : "+arr[4])
            if arr[4]=="-1":
              ganzeliega.append(arr[2])
              name.append(arr[0])
              lieganr.append(arr[2])
              dayid.append(arr[3])
            else:                        
              name.append(arr[0])
              live_status.append(arr[1])
              lieganr.append(arr[2])
              dayid.append(arr[3])
              spielnr.append(arr[4])
              minute_now.append("-")
              aus.append(arr[5])
              inn.append(arr[6])
              hdate=arr[7]
              htime=arr[8]
              match_date.append(hdate)
              match_time.append(htime)
              zeitpunkt=hdate+ " "+htime                             
              debug("   zeitpunkt "+zeitpunkt)         
              dt = parser.parse(zeitpunkt, fuzzy=True,dayfirst=True)  
              lss=dt.timetuple()
              lsv.append(time.mktime(lss))
              debug("-------ADDE FILE-----------")       
              debug(arr[0])
        
        liegadone=[]
        
        #SpielePrüfen  
        delliste=[]
        ## Jede Liega Wird einmalgeladen
        for i in range(len(lieganr)):               
          liga=lieganr[i]
          debug("-------LIGA LOOP-----------")
          debug("Liega :"+liga)
          if not liga in liegadone:            
            day=dayid[i]
            liegadone.append(liga)
            debug("Hole LiegA")            
            if oldi==1:
              day="1"
            nurl="https://api.sport1.de/api/sports/matches-by-season/co"+liga+"/se/md"+day
            debug("NURL :"+nurl)
            debug("_----------")
            debug ("ganzeliega")
            debug(ganzeliega)
            debug ("spielnr")
            debug(spielnr)               
            content=geturl(nurl)           
            struktur = json.loads(content)
            try:
              tage=struktur["round"] 
            except:
               debug("Fehler")
               continue
            # Jeden Tagin derLiega            
            for tag in tage:
              debug("Neuer Tag")            
              spiele=tag["match"]                     
              #Jedes Spiel in dem Tag
              for spiel in spiele:   
                 aminute_now=spiel["current_minute"]              
                 id=spiel["id"] 
                 debug("Spiel :"+id)
                 debug("liga :"+liga)
                 ende=spiel["finished"] 
                 #Wenn das Spiel Oder die Ganze Liega ausgewählt wurde
                 debug("Spielnr :" +str(spielnr))
                 if str(id) in spielnr or liga in ganzeliega: 
                    debug("Spiel Ausgewaelt")
                    #Spiel Zuende? und keine Liega
                    if not ende=="no" and liga not in ganzeliega and oldi==0:
                      debug("Spiel zuende")
                      #Spiel Zuende? und keine Liega
                      delliste.append(id)
                      debug("Delete :"+id)
                    else:
                       # Wenn Ganze Liega oder Spiel noch nicht zuende     
                       debug("Neues Spiel")
                       if ende=="no" or oldi==1:
                           debug("Spiel läuft ")
                           # Nur Wenn das Spiel begonnen hat
                           if str(id) in spielnr:
                             if spielnr.index(id) not in spiellisteneu:                                
                                spiellisteneu.append(spielnr.index(id))
                                minute_now[spielnr.index(id)]=aminute_now
                                debug("Adde :"+str(spielnr.index(id)))
                           else :                              
                              a_live_status=smart_str(spiel["live_status"])
                              a_aus=smart_str(spiel["away"]["name"])
                              a_ins=smart_str(spiel["home"]["name"])
                              a_ende=spiel["finished"]
                              a_match_date=smart_str(spiel["match_date"])
                              a_match_time=smart_str(spiel["match_time"])
                              if a_match_time=="unknown":
                                 a_match_time=""     
                              a_id=spiel["id"]      
                              a_name=a_match_date +" "+ a_match_time +" : "+a_ins +" - "+ a_aus 
                              a_zeitpunkt=a_match_date+ " "+a_match_time                                       
                              a_dt = parser.parse(a_zeitpunkt, fuzzy=True,dayfirst=True)  
                              a_lss=a_dt.timetuple()
                              lsv.append(time.mktime(a_lss))
                              name.append(a_name)
                              live_status.append(a_live_status)
                              lieganr.append(liga)
                              dayid.append(day)
                              spielnr.append(a_id)                              
                              aus.append(a_aus)
                              inn.append(a_ins)
                              match_date.append(a_match_date)
                              match_time.append(a_match_time)                                
                              spiellisteneu.append(spielnr.index(id))    
                              debug("Adde Neu:"+str(spielnr.index(id)))
                              minute_now.append(aminute_now)
        debug(" minute_now : ")
        debug("---------------")
        debug (minute_now)
        # Loeschliste loeschen
        if len(delliste) > 0:
              delspiel(delliste,liste)                                          
        #Spiele Abarbeiten
        debug("spiellisteneu")
        debug(spiellisteneu)
        for nr in spiellisteneu: 
          debug(" : SPIEL ::")
          debug(nr)         
          debug ("ArrayY")
          debug(inn)
          in_spieler=""
          in_id=""
          out_spieler=""
          out_id=""
          url="https://api.sport1.de/api/sports/match-event/ma"+spielnr[nr]
          content=geturl(url)
          struktur = json.loads(content)
          debug("struktur")
          debug (struktur)
          ccontent="0:0"
          anzal_meldung=0
          for element in struktur: 
            foto1=""
            foto2=""
            anzal_meldung=anzal_meldung+1
            minute=element["minute"]
            action=element["action"]
            kind=element["kind"]
            if not element["content"]=="":
              ccontent=smart_str(element["content"])
            created=element["created"]
            id=element["id"]                 
            Meldung=""
            if action=="match":
              if spielzeit=="false":
                continue
              if kind=="game-end":
                Meldung=translation(30049)+ inn[nr] +translation(30041)+aus[nr] +translation(30053)+ccontent
              if kind=="game-start":
                Meldung=translation(30049)+ inn[nr] +translation(30041)+aus[nr] +translation(30052)
              if kind=="first-half-end":
                Meldung=translation(30048)+ inn[nr] +translation(30041)+aus[nr] +translation(30050)+ccontent                  
              if kind=="second-half-start":
                Meldung=translation(30047)+ inn[nr] +translation(30041)+aus[nr] +translation(30051)+ccontent            
              if kind=="second-half-end":
                Meldung=translation(30047)+ inn[nr] +translation(30041)+aus[nr] +translation(30050)+ccontent                          
              if kind=="first-extra-start":
                Meldung=translation(30045)+ inn[nr] +translation(30041)+aus[nr] +translation(30051)+ccontent          
              if kind=="first-extra-end":
                Meldung=translation(30045)+ inn[nr] +translation(30041)+aus[nr] +translation(30050)+ccontent                           
              if kind=="second-extra-start":
                Meldung=translation(30043)+ inn[nr] +translation(30041)+aus[nr] +translation(30051)+ccontent                                                 
              if kind=="second-extra-end":
                Meldung=translation(30043)+ inn[nr] +translation(30041)+aus[nr] +translation(30050)+ccontent                                                 
              if kind=="penalty-start":
                Meldung=translation(30040)+ inn[nr] +translation(30041)+aus[nr] +translation(30042)+ccontent                                                 
            if action=="card":
              if karten=="false":
                continue
              team=element["team"]["name"]
              person=element["person"]["name"]
              personid=element["person"]["id"]
              if kind=="yellow":
                Meldung=minute +translation(30039)+ person +translation(30036)+ team 
                foto1=yellow
              if kind=="red":
                Meldung=minute +translation(30038)+ person +translation(30036)+ team 
            if action=="goal": 
              if tor=="false":
                continue
              team=element["team"]["name"]
              person=element["person"]["name"]
              personid=element["person"]["id"]
              foto1="http://images.sport1.de/imagix/filter2/jpeg/_set=profile_picture/http://sport1.weltsport.net/gfx/person/l/"+personid+".jpg"
              if kind=="penalty":    
                Meldung=translation(30032)+minute +translation(30035)+ person +translation(30036)+ team +translation(30037)+ccontent                    
              else:   
                Meldung=translation(30031)+ minute +translation(30032)+person +translation(30033)+team+translation(30034)+ ccontent                          
            if action=="pso": 
              if elfmeter=="false":
                continue                    
              team=element["team"]["name"]
              person=element["person"]["name"]
              personid=element["person"]["id"]  
              foto1="http://images.sport1.de/imagix/filter2/jpeg/_set=profile_picture/http://sport1.weltsport.net/gfx/person/l/"+personid+".jpg"
              if kind=="goal": 
                Meldung=translation(30030)+ person +translation(30029)+ team
              if kind=="goal": 
                Meldung=translation(30028)+ person +translation(30029)+ team
            if action=="playing":
              if spielerwechsel=="false":
                continue
              team=element["team"]["name"]
              person=element["person"]["name"]
              personid=element["person"]["id"] 
              if kind=="substitute-out":                        
                out_spieler=person
                out_id=personid
                Meldung=""
              if kind=="substitute-in":                                               
                in_spieler=person
                in_id=personid
                Meldung=""
              if not in_spieler=="" and not out_spieler=="":
                Meldung=minute +translation(30025)+team +translation(30026)+out_spieler +translation(30027)+in_spieler 
                foto1="http://images.sport1.de/imagix/filter2/jpeg/_set=profile_picture/http://sport1.weltsport.net/gfx/person/l/"+out_id+".jpg"
                foto2="http://images.sport1.de/imagix/filter2/jpeg/_set=profile_picture/http://sport1.weltsport.net/gfx/person/l/"+in_id+".jpg"
                in_spieler=""
                out_spieler=""
                out_id=""
                in_id=""
                debug("Spiel Zeit"+ str(minute_now[nr]))
                debug("Spiel minute"+ str(minute))
            if not Meldung=="" and ( int(minute)>int(minute_now[nr]) or oldmessages=="true" ):              
              titlelist.append(Meldung)
              cimglist1.append(foto1)              
              cimglist2.append(foto2)              
              greyoutlist.append(greyout)
              lesezeitlist.append(lesezeit) 
              ins.append(inn)
              auss.append(aus)    
              anzal_meldungen.append(anzal_meldung)                           
              timelist.append(lsv[nr]+int(minute)*60)                    
              ids.append(id)
        #Sind Meldungen da
        if len(timelist)>0 :
          # Sortieren Meldungen
          timelist,anzal_meldungen,titlelist,cimglist1,cimglist2,lesezeitlist,greyoutlist,ids,ins,auss = (list(x) for x in zip(*sorted(zip(timelist,anzal_meldungen,titlelist,cimglist1,cimglist2,lesezeitlist,greyoutlist,ids,ins,auss))))                      
          for i in range(len(titlelist)):  
            #Meldungen die schon Da waren nicht mehr zeigen          
            if not ids[i] in  schown:
                debug("Zeit ist : "+str(timelist[i]))                
                popupwindow.savemessage(__addon__,titlelist[i],cimglist1[i],greyoutlist[i],lesezeitlist[i],xmessage,ymessage,breitemessage,hoehemessage,breitebild1,hoehebild1,font,fontcolor,-1,-1,cimglist2[i],-1,-1,breitebild2,hoehebild2)             
                schown.append(ids[i])    
                if len(schown)>anzahlmeldungen:
                    schown.pop(0)                
      if monitor.waitForAbort(60):
        break            
      
           
      

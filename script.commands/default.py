#!/usr/bin/python
# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, locale, sys, urllib, urllib2, re, os

addonID = "script.commands"
addon_work_folder=xbmc.translatePath("special://profile/addon_data/"+addonID)
commandsFile=xbmc.translatePath('special://profile/addon_data/'+addonID+'/commands')
commandsList=xbmc.translatePath('special://home/addons/'+addonID+'/commands.list')
favsFile=xbmc.translatePath("special://profile/favourites.xml")
settings = xbmcaddon.Addon(id=addonID)
translation = settings.getLocalizedString

if not os.path.isdir(addon_work_folder):
  os.mkdir(addon_work_folder)

def importCommands():
        global myCommands
        myCommands=[]
        if os.path.exists(commandsFile):
          fh = open(commandsFile, 'r')
          for line in fh:
            myCommands.append(line.replace("\n",""))
          fh.close()
        myCommands.append("- "+translation(30001))
        myCommands.append("- "+translation(30005))

def commandsMain():
        importCommands()
        myCommandsTemp=[]
        for temp in myCommands:
          if temp.find("###")>=0:
            myCommandsTemp.append(temp[:temp.find("###")])
          else:
            myCommandsTemp.append(temp)
        dialog = xbmcgui.Dialog()
        nr=dialog.select("Commands", myCommandsTemp)
        if nr>=0:
          entry=myCommands[nr]
          if entry.find("###")>=0:
            title = entry[:entry.find("###")]
            command = entry[entry.find("###")+3:]
            xbmc.executebuiltin(command)
          if entry=="- "+translation(30001):
            addCommand()
          elif entry=="- "+translation(30005):
            manageCommands()

def addCommand():
        dialog = xbmcgui.Dialog()
        modes=[translation(30002),translation(30003),translation(30004)]
        nr=dialog.select(translation(30001), modes)
        if nr>=0:
          mode = modes[nr]
          if mode==translation(30002):
            addCommandList()
          elif mode==translation(30003):
            addCommandFavs()
          elif mode==translation(30004):
            addCommandEnter()
        else:
          commandsMain()

def addCommandList():
        if os.path.exists(commandsList):
          favs=[]
          fh = open(commandsList, 'r')
          for line in fh:
              favs.append(line.replace("\n",""))
          fh.close()
          myCommandsTemp=[]
          for temp in favs:
            myCommandsTemp.append(temp[:temp.find("###")])
          dialog = xbmcgui.Dialog()
          nr=dialog.select(translation(30002), myCommandsTemp)
          if nr>=0:
            entry=favs[nr]
            title = entry[:entry.find("###")]
            command = entry[entry.find("###")+3:]
            if title+"###"+command not in myCommands:
              fh = open(commandsFile, 'a')
              fh.write(title+"###"+command+"\n")
              fh.close()
            commandsMain()
          else:
            addCommand()

def addCommandFavs():
        if os.path.exists(favsFile):
          favs=[]
          fh = open(favsFile, 'r')
          for line in fh:
            if line.find("<favourite name=")>=0:
              match=re.compile('<favourite name="(.+?)"', re.DOTALL).findall(line)
              title=match[0]
              match=re.compile('>(.+?)<', re.DOTALL).findall(line)
              command=match[0].replace("&quot;","").replace("&amp;","&")
              favs.append(title+"###"+command)
          fh.close()
          myCommandsTemp=[]
          for temp in favs:
            myCommandsTemp.append(temp[:temp.find("###")])
          dialog = xbmcgui.Dialog()
          nr=dialog.select(translation(30003), myCommandsTemp)
          if nr>=0:
            entry=favs[nr]
            title = entry[:entry.find("###")]
            command = entry[entry.find("###")+3:]
            if title+"###"+command not in myCommands:
              fh = open(commandsFile, 'a')
              fh.write(title+"###"+command+"\n")
              fh.close()
            commandsMain()
          else:
            addCommand()

def addCommandEnter():
        kb = xbmc.Keyboard("", "Title")
        kb.doModal()
        if kb.isConfirmed():
          title=kb.getText()
          kb = xbmc.Keyboard("", translation(30009))
          kb.doModal()
          if kb.isConfirmed():
            command=kb.getText()
            if title+"###"+command not in myCommands:
              fh = open(commandsFile, 'a')
              fh.write(title+"###"+command+"\n")
              fh.close()
            commandsMain()
          else:
            addCommand()
        else:
          addCommand()

def manageCommands():
        dialog = xbmcgui.Dialog()
        modes=[translation(30006),translation(30007),translation(30008)]
        nr=dialog.select(translation(30005), modes)
        if nr>=0:
          mode = modes[nr]
          if mode==translation(30006):
            manageCommandsEdit()
          elif mode==translation(30007):
            manageCommandsRemove()
          elif mode==translation(30008):
            manageCommandsSort()
        else:
          commandsMain()

def manageCommandsEdit():
        myCommandsTemp=[]
        for temp in myCommands:
          if temp.find("###")>=0:
            myCommandsTemp.append(temp[:temp.find("###")])
        dialog = xbmcgui.Dialog()
        nr=dialog.select(translation(30006), myCommandsTemp)
        if nr>=0:
          entry=myCommands[nr]
          if entry.find("###")>=0:
            title = entry[:entry.find("###")]
            command = entry[entry.find("###")+3:]
            oldTitle=title
            oldCommand=command
            kb = xbmc.Keyboard(title, translation(30010))
            kb.doModal()
            if kb.isConfirmed():
              title=kb.getText()
              kb = xbmc.Keyboard(command, translation(30009))
              kb.doModal()
              if kb.isConfirmed():
                command=kb.getText()
                newContent=""
                fh = open(commandsFile, 'r')
                for line in fh:
                  if line.find(oldTitle+"###")==0:
                    newContent+=line.replace(oldTitle,title).replace(oldCommand,command)
                  else:
                    newContent+=line
                fh.close()
                fh=open(commandsFile, 'w')
                fh.write(newContent)
                fh.close()
                importCommands()
                manageCommandsEdit()
        else:
          manageCommands()

def manageCommandsRemove():
        myCommandsTemp=[]
        for temp in myCommands:
          if temp.find("###")>=0:
            myCommandsTemp.append(temp[:temp.find("###")])
        dialog = xbmcgui.Dialog()
        nr=dialog.select(translation(30007), myCommandsTemp)
        if nr>=0:
          entry=myCommands[nr]
          if entry.find("###")>=0:
            title = entry[:entry.find("###")]
            command = entry[entry.find("###")+3:]
            newContent=""
            fh = open(commandsFile, 'r')
            for line in fh:
              if line.find(title+"###")==0:
                pass
              else:
                newContent+=line
            fh.close()
            fh=open(commandsFile, 'w')
            fh.write(newContent)
            fh.close()
            importCommands()
            manageCommandsRemove()
        else:
          manageCommands()

def manageCommandsSort():
        myCommandsTemp=[]
        for temp in myCommands:
          if temp.find("###")>=0:
            myCommandsTemp.append(temp[:temp.find("###")])
        dialog = xbmcgui.Dialog()
        nr=dialog.select(translation(30008), myCommandsTemp)
        if nr>=0:
          entry=myCommands[nr]
          if entry.find("###")>=0:
            dialog = xbmcgui.Dialog()
            pos = dialog.numeric(0, translation(30011))
            try:
              pos=int(pos)
            except:
              pos=-1
            if int(pos)<len(myCommandsTemp) and int(pos)>0:
              newContent=""
              fh = open(commandsFile, 'r')
              for line in fh:
                if line.find(entry)==0:
                  pass
                else:
                  newContent+=line
              fh.close()
              fh=open(commandsFile, 'w')
              fh.write(newContent)
              fh.close()
              newContent=""
              fh = open(commandsFile, 'r')
              lineNr=1
              for line in fh:
                if int(pos)==lineNr:
                  newContent+=entry+"\n"
                  newContent+=line
                else:
                  newContent+=line
                lineNr+=1
              fh.close()
              fh=open(commandsFile, 'w')
              fh.write(newContent)
              fh.close()
              importCommands()
              manageCommandsSort()
            else:
              manageCommandsSort()
        else:
          manageCommands()

commandsMain()

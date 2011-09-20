for skinners: HOW TO INTEGRATE THIS SCRIPT IN YOUR SKIN

  # for automatically download the script from xbmc, include this in your addon.xml:
  # 
  #   <requires>
  # 	<import addon="script.logo-downloader" version="3.0.0"/>
  #   </requires>
  #   
  # for solo mode (usually used from videoinfodialog) , $INFO[ListItem.TVShowTitle] is required. you have to add a button whit the following action:
  # exemple to launch:
  # <onclick>XBMC.RunScript(script.logo-downloader,mode=solo,logo=True,clearart=True,characterart=True,showthumb=landscape.jpg,poster=poster.jpg,banner=banner.jpg,showname=$INFO[ListItem.TVShowTitle])</onclick>
  # 
  # for bulk mode, no particular info needed, just need a button to launch from where you want.
  # exemple to launch:
  # <onclick>XBMC.RunScript(script.logo-downloader,mode=bulk,clearart=True,characterart=True,logo=True,showthumb=landscape.jpg,poster=poster.jpg,banner=banner.jpg)</onclick>
  # 
  # When type is set to "True" (example: showthumb=True), here are default images name:
  # clearart: clearart.png
  # characterart: character.png
  # logo: logo.png
  # showthumb/poster/banner: folder.jpg
  # 
  # if a certain type isn't in parameter, it won't be available to download
  # 
  

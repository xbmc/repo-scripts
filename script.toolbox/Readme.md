Dialog call examples:

- DialogSelect

<onclick>SetProperty(Dialog.1.Label,SOME TEXT)</onclick>
<onclick>SetProperty(Dialog.1.BuiltIn,BUILTIN)</onclick>
<onclick>SetProperty(Dialog.2.Label,SOME TEXT)</onclick>
<onclick>SetProperty(Dialog.2.BuiltIn,BUILTIN)</onclick>
<onclick>SetProperty(Dialog.3.Label,SOME TEXT)</onclick>
<onclick>SetProperty(Dialog.3.BuiltIn,BUILTIN)</onclick>
<onclick>RunScript(script.toolbox,info=selectdialog,header=SOME_TEXT)</onclick>


- DialogYesNo

<onclick>RunScript(script.toolbox,info=yesnodialog,header=SOME_TEXT,text=SOME_TEXT,yesaction=BUILTIN,noaction=BUILTIN,yeslabel=SOME_TEXT,nolabel=SOME_TEXT)</onclick>


- DialogOK

<onclick>RunScript(script.toolbox,info=okdialog,header=SOME_TEXT,text=SOME_TEXT)</onclick>


- DialogTextViewer

<onclick>RunScript(script.toolbox,info=textviewer,header=SOME_TEXT,text=SOME_TEXT)</onclick>


- Notification with extended options

<onclick>RunScript(script.toolbox,info=notification,header=SOME_TEXT,text=SOME_TEXT,icon=PATH_TO_ICON,time=SECONDS_TO_DISPLAY,sound=TRUE/FALSE)</onclick>


Notes:
- use "||" as separator to append several builtins
- escape stuff in following form: '"$INFO[xxx]"'



other calls:

<onclick>RunScript(script.toolbox,info=exportskinsettings[,text=SOME_TEXT])</onclick> ([,text=SOME_TEXT] optional string filter)
<onclick>RunScript(script.toolbox,info=importskinsettings)</onclick>
<onclick>RunScript(script.toolbox,info=blur,id=PATH_TO_IMAGE)</onclick>


** This script is also required for some functions of SublimeKodi ( https://github.com/phil65/SublimeKodi ) **

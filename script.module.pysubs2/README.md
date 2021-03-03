pysubs2 library Kodi plugin
===========================

KODI plugin that implements pysubs2 library for subtitle conversion.

All pysubs2 code is written by Tomas Karabela.
https://github.com/tkarabela/pysubs2


Installation in KODI:
=====================
- download plugin
- open KODI -> System -> Settings -> Add-ons -> Install from zip file
- navigate to the file you downloaded


Usage:
======
reference this plugin in your addon by:
```
  <requires>
    <import addon="script.module.pysubs2" version="1.0.0"/>
  </requires>
```


Import pysubs2 function in your script:

```
import pysubs2
```

Call the plugin's load function:
```
subs = pysubs2.load(<input_file>, encoding=<encoding>, fps=<fps>)
```

For use details, please see pysubs2 project documentation:
https://github.com/tkarabela/pysubs2
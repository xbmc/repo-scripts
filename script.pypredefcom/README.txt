====================================================================
  PyDev Predefined Completions Creator
  Copyright (C) 2010 James F. Carroll

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
====================================================================

August 15, 2010
PyDev Predefined Completions Creator is based on Pydoc by nuka1195 which provided a great example and starting point.

0) License and Warranty

The License is GPL. You can read a copy of the License in the root directory of this distribution in the License.txt file. As the license states, as well as the preamble to this README above, there is ABSOLUTELY NO WARRANTY.

1) What does this script do?

In short, it will generate a set of PyDev Predefined Completions for the XBMC built Python modules to be used by XBMC addon developers. PyDev Predefined Completions are a way of adding type, interface, and documentation information to the Eclipse IDE (with the PyDev plugin) for Python modules that have no ".py" file. This is typically the case for C/C++ developed Python modules (built-ins?) that are not part of the base Python implementation.

For a more detailed explanation of Pydev Predefined Completions and how to use them once you've generated them, see:

http://pydev.org/manual_101_interpreter.html#id2

Currently, it will generate Predefined Completions for the following built-in XBMC modules:

xbmc
xbmcgui
xbmcplugin
xbmcaddon

As of the branched Dharma version of XBMC (as of the date given above), these are the only 4 native modules added to Python by XBMC.

2) Why do I care?

If you're a Python XBMC script developer, and you use PyDev in Eclipse to do your development, you will be able to get "auto-completion" of the XBMC modules. This might not seem like much if you're not used to it but it's a great tool for development.

Auto-completion in Eclipse also includes the display of the documentation for the method/function/module/class that's being auto-completed. This provides a real-time immediate access to the documentation as your writing code in your code editor for the specific method/function/module/class you're using. This makes coming up to speed on what's available much easier (given the documentation doesn't suck).

3) Sound's great! How do I use this script.

This script needs to be installed as an addon in XBMC and run from inside XBMC. Once installed it should appear listed as an Addon under the "Programs" menu. The first time it's run you will be asked to identify the directory to write the Predefined Completions into. After that it will put them in the same directory.

Once you've generated the Predefined Completions follow the PyDev instructions for adding Predefined Completions to your Python interpreter definition.

4) How does it work

Python supports "introspection" of modules/libraries. From within a running addon this python program interrogates (introspects) the XBMC native modules to find out the names, types, attributes and documentation included, and generates Predefined Completions (.pypredef files) that can be loaded into the PyDev plugin for the Eclipse IDE.

Then again, if you're not developing XBMC addons in Python or you're not using PyDev in Eclipse, this wont help you.

5) What are the limitations and issues of the current implementation

Here is a short list of the current known limitations/issues:
     1) It provides Predefined Completions for the XBMC native modules for the version of XBMC that the script is run from within only. This shouldn't be an issue for anyone really. Keep in mind that if you install a new version of XBMC from Python development you should rerun this script from within this newly installed version.
     2) Predefined Completions provides the ability to identify the return type from a function or method. I have not figured out how to find this information through introspection so none of the function/method templates identify a return type.
     3) I haven't figured out how to extract the parameter list from functions/methods on native modules and therefore all of the method signatures take a variable argument list. It would be much better to be able to retrieve the original parameter list as it helps with the auto-completion and documentation.
     4) This works on the current XBMC modules (see limitation (1) above) but it is not exhaustive in generating a Predefined Completions for every possible Python language idiosyncrasy. It is possible that future versions (or maybe even past versions) of the XBMC native modules will not generate correctly using this version of the script. When that time arrives, I'll consider fixing it then.



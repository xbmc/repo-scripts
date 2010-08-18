#====================================================================
#  PyDev Predefined Completions Creator
#  Copyright (C) 2010 James F. Carroll
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#====================================================================

'''
Created on Jul 31, 2010

The main purpose of this module is to create a PyDev Predefined Completion from
another module using introspection and write it out to a file.

@author: jim
'''

import inspect
import os
import re

oneindent = "    "

def visiblename(name, all=None):
    """Decide whether to show documentation on a variable."""
    # Certain special names are redundant.
    if name in ['__builtins__', '__doc__', '__file__', '__path__',
                '__module__', '__name__', 'Helper' ]: return 0
    # Private names are hidden, but special names are displayed.
    if name.startswith('__') and name.endswith('__'): return 1
    if all is not None:
        # only document that which the programmer exported in __all__
        return name in all
    else:
        return not name.startswith('_')
    
def ensuredir(dir):
    """ This method simply ensures that the directory path provided exists and creates it otherwise. """
    if not os.path.exists(dir):
        os.makedirs(dir)

docquote = '''"""'''
quote = '''"'''

def displayDocLine(f,object, indent = ""):
    try:
        docline = object.__doc__
    except AttributeError:
        return
    
    if docline is None or len(docline) == 0:
        return
    lines = docline.splitlines()

    prefix = indent + docquote    
    for line in lines:
        f.write(prefix + line + "\n")
        prefix = indent
    f.write( indent + docquote + '\n\n')
    
def myformatvalue(object):
    """Format an argument default value as text."""
    return '=' + repr(object)

    
def displayMethod(f, method, indent = ""):
    name = method.__name__
    f.write (indent + "def " + name)
    
    try:
        args, varargs, varkw, defaults = inspect.getargspec(method)
        argspec = inspect.formatargspec(
            args, varargs, varkw, defaults, formatvalue=myformatvalue)
        if name == '<lambda>':
            argspec = argspec[1:-1] # remove parentheses
    except TypeError:
# None of this works because the docs are too inconsistent.
#        # many of the xbmc document strings contain an signature for the
#        # function. It may be possible to pull the signature from the document
#        # line but it's not necessarily reliable as it's more than likely that
#        # someone can update the signature but not go back and update the documentation.
#        # Nevertheless it's probably better to use it if it can be parsed out of
#        # the string than to simply provide varargs.
#        
#        # OK - we might as well make the attempt
#        
#        # TODO: There MUST be a better way to do this. How can I get the argspec
#        # from a built in/native Python method?
#        try:
#            docline = method.__doc__
#            argspec = re.search(name + "\( *.*\)", docline)
#            if argspec is None:
#                argspec = '(*args)'
#            else:
#                argspec = argspec.group(0)
#                # now get rid of square brackets that denote optional attributes
#                argspec = re.sub("\[", "", argspec, 999)
#                argspec = re.sub("\]", "", argspec, 999)
#                
#        except AttributeError:
#            argspec = '(*args)'
            argspec = '(*args)'
        
    f.write (argspec + ":\n")

    displayDocLine(f,method,indent + oneindent)
    
def displayClass(f, clazz, indent = ""):
    name = clazz.__name__
    all = dir(clazz)
    f.write (indent + "class " + name + ":\n" )
    displayDocLine(f, clazz, indent + oneindent)
    
    parts = inspect.getmembers(clazz)
        
    for key, value in parts:
        if visiblename(key,all):
# Apparently all classes contain other standard classes (and themselves as members?). If I run across a case
#  where this is needed then I will need to add a filter here.
#            if inspect.isclass(value):
#                displayClass(f,value, indent + oneindent)
            if lookslikeamethod(value):
                displayMethod(f,value,indent + oneindent)
            else:
                otherpart(f,key,value,indent + oneindent)
    f.write("\n\n")

def otherpart(f, key, value, indent = ""):
    """ If I don't know how to handle a 'part' then I call this method which
    currently just logs the details of the part to stdout for later evaluation """
#    f.write( indent +  "other part:" + key + ", " + str(value) + " --- of type --->(" + str(type(value)) + ")\n")
    print( indent +  "other part:" + key + ", " + str(value) + " --- of type --->(" + str(type(value)) + ")\n")
    print( indent + oneindent + str(inspect.getmembers(value)))
    return

def lookslikeamethod(part):
    """ Does the passed part appear to be methodlike? """
    if inspect.isfunction(part) or inspect.ismethod(part) or inspect.isbuiltin(part) or inspect.ismethoddescriptor(part):
        return True
    return False

def lookslikeattribute(part):
    """ Does the passed part look like an attribute of a class or modules? """
    if type(part) is int or type(part) is str or type(part) is bool:
        return True
    
def displayAttribute(f, attributename, attributevalue, indent = ""):
    # TODO: This seems to be a bit of a hack. There ought to be a better way to handle
    #  retrieving a string that contains the type (and only the type) of the attribute.
    mytype = re.sub("^<type '", "", repr(type(attributevalue)), 1)
    mytype = re.sub("'>$", "", mytype, 1)
    
    f.write( indent + attributename + " = " +  mytype + "\n")
    return

def pypredefmodule(f, module):
    """Produce PyDev Predefined Completions for a module."""
    
    print ("writing to file " + str(f))
    
    name = module.__name__ # ignore the passed-in name
    try:
        all = object.__all__
    except AttributeError:
        all = None
    
    displayDocLine(f, module)

    parts = inspect.getmembers(module)
    
    for key, value in parts:
        if visiblename(key, all):
            if inspect.isclass(value):
                displayClass(f,value)
            elif lookslikeamethod(value):
                displayMethod(f,value)
            elif lookslikeattribute(value):
                displayAttribute(f,key,value)
            else:
                otherpart(f,key,value)
    
    
    
    

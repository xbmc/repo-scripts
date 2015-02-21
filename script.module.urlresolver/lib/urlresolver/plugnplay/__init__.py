"""
    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0
    based on plugnplay by https://github.com/daltonmatos

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from glob import glob
from os.path import join, basename
import sys, re
from urlresolver import common
from manager import *
from types import FunctionType, ClassType

__version__ = "0.1"

__all__ = ['Interface', 'Plugin']


man = Manager()

plugin_dirs = []

def _is_method(o):
    return type(o) is FunctionType


''' Template that defines the parent properties into AutoloadPlugin properties
'''
def attr_set_property(attr_name):
    def _get_x(impl):
        try:
            return getattr(impl._ref, attr_name)
        except:
            pass
    def _set_x(impl, value):
        try:
            setattr(impl._ref, attr_name, value)
        except:
            pass
    return property(_get_x, _set_x)


''' Template that wraps an existing function in the parent class into a
    function with the same name in the AutoloadPlugin.
'''
def method_name_and_load(method_name):
    def _auto_caller_template(impl, *args, **kwargs):
        method = getattr(impl._ref, method_name)
        try:
            return method(*args, **kwargs)
        except ImportError: # Module not in memory yet
            orig_method = method
            load_plugin(impl)
            method = getattr(impl._ref, method_name)
            if (method == orig_method):
                common.addon.log_error('Unusable module %s in %s.py' % (impl.name, impl.fname))
            return method(*args, **kwargs)

    return _auto_caller_template


def canonical_name(obj):
    return "{0}.{1}".format(obj.__module__, obj.__name__)


'''
Wrapper for public interfaces
'''
class AutoloadMeta(type):
    def __new__(metaclass, classname, bases, attrs):
        new_class = super(AutoloadMeta, metaclass).__new__(metaclass, classname, bases, attrs)
        for b in bases:
            # print classname, b, type(b)
            # Ignore non classes
            if type(b) != ClassType:
                continue
            # Check parent dictionary
            for k in b.__dict__:
                v = b.__dict__[k]
                # print (k, type(v))
                if k in new_class.__dict__:
                    continue
                # print (k, type(v))
                if type(v) == FunctionType:
                    # print k
                    setattr(new_class, k, method_name_and_load(k))
                else:
                    setattr(new_class, k, attr_set_property(k))
        return new_class

    def __eq__(self, other):
        return canonical_name(self) == canonical_name(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(canonical_name(self))

'''
  Marker for public interfaces
'''
class Interface():
    @classmethod
    def implementors(klass):
        return man.implementors(klass)


'''
  Plugin's metaclass
  Create a Plugin class, and add a implementor from the newly created class
'''
class PluginMeta(type):

    def __new__(metaclass, classname, bases, attrs):
        new_class = super(PluginMeta, metaclass).__new__(metaclass, classname,
                                                         bases, attrs)

        new_class_instance = new_class()
        if attrs.has_key('implements'):
            for interface in attrs['implements']:
                notfound = True
                for impl in man.implementors(interface):
                    if impl.name == new_class_instance.name:
                        if getattr(impl, '_ref'):
                            impl._ref = new_class_instance
                            return # Wrapper will take care of all instances
                        else:
                            # Normal implementor
                            impl = new_class_instance
                            notfound = False
                if notfound: man.add_implementor(interface, new_class_instance)

        return new_class

# class Plugin(object):
#     __metaclass__ = PluginMeta
Plugin = PluginMeta('Plugin', (object, ), {})

#class AutoloadPlugin(object):
#    __metaclass__ = AutoloadMeta
AutoloadPlugin = AutoloadMeta('AutoloadPlugin', (object, ), {})

# Interface = InterfaceMeta('Interface', (object, ), {'implementors': implementors})


''' More functions '''
def set_plugin_dirs(*dirs):
  for d in dirs:
    common.addon.log_debug('adding plugin dir: %s' % d)
    plugin_dirs.append(d)  

def load_plugin(mod):
    common.addon.log_debug('loading plugin: %s from %s' % (mod.name, mod.fname))
    try:
        imported_module = __import__(mod.fname, globals(), locals())
        sys.modules[mod.fname] = imported_module
    except:
        common.addon.log_error('Unable to load plugin %s from %s.py' % (mod.name, mod.fname))

def load_plugins():
    for d in plugin_dirs:
        sys.path.insert(0, d)
        py_files = glob(join(d, '*.py'))

        # Remove ".py" for proper importing
        modules = [basename(f[:-3]) for f in py_files]
        for mod_name in modules:
            try:
                imported_module = __import__(mod_name, globals(), locals())
                sys.modules[mod_name] = imported_module
            except:
                common.addon.log_error('Unable to load plugin %s' % (mod_name))

def scan_plugins(wrappercls):
    re_class = re.compile('class\s+(\w+).*Plugin')
    for d in plugin_dirs:
        sys.path.insert(0, d)
        py_files = glob(join(d, '*.py'))
        for f in py_files:
            found_plugin = None
            mod_name = basename(f[:-3])
            for line in open(f, 'r'):
                if None == found_plugin:
                    res = re_class.match(line)
                    if res:
                        found_plugin = wrappercls()
                        found_plugin.fname = mod_name
                        found_plugin.class_name = res.group(1)
                else:
                    found_plugin.proc_plugin_line(line)
                    if found_plugin.plugin_ready():
                        _enabled = common.addon.get_setting('%s_enabled' % found_plugin.class_name)
                        if _enabled == "false": break
                        _priority = common.addon.get_setting('%s_priority' % found_plugin.class_name)
                        try:
                            found_plugin.priority = int(_priority)
                        except ValueError:
                            found_plugin.priority = 100
                        for cls in found_plugin.implements:
                            common.addon.log_debug("module %s supports %s in class %s" % (mod_name, cls, found_plugin.class_name))
                            man.add_implementor(cls, found_plugin)
                        break # Next file

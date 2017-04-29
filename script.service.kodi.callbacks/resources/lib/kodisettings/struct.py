#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import abc
from resources.lib.utils.poutil import KodiPo
from resources.lib.kodilogging import KodiLogger
log = KodiLogger.log
kodipo = KodiPo()
kodipo.updateAlways = True
_ = kodipo.getLocalizedStringId

def getSettingMock(sid):
    assert isinstance(sid, str) or isinstance(sid, unicode)
    return 'none'

try:
    import xbmcaddon
    getSetting = xbmcaddon.Addon().getSetting
except ImportError:
    getSetting = getSettingMock

class Settings(object):
    """
    Class representing the top level portion of the settings.xml
    Contains categories
    """

    def __init__(self):
        self._categories = []
        self._controldict = {}
        self._controldictbyrefid = {}
        self.id_position = {}
        self.duplicateids = []
        self.values = {}

    def category(self, label):
        """
        Retrieves a category by label
        :param label: English non-localized unicode or string for label
        :type label: unicode or str
        :return:
        :rtype: Category
        """
        assert (isinstance(label, unicode) or isinstance(label, str))
        label = unicode(label)
        ret = None
        for c in self._categories:
            if c.label == label:
                ret = c
                break
        if ret is None:
            raise KeyError('Category not found for: %s' % label)
        else:
            return ret

    def addCategory(self, category):
        """
        Add a category. Categories are listed as tabbed pages in settings.
        :param category:
        :type category: Category or str or unicode
        :return:
        :rtype: Category
        """
        if isinstance(category, str) or isinstance(category, unicode):
            category = Category(unicode(category))
            self._categories.append(category)
        elif isinstance(category, Category):
            self._categories.append(category)
        else:
            raise TypeError('Add Category must be string or Category')
        return category

    def addControl(self, catgorylabel, control):
        """
        Add a control to a specific category.
        :param catgorylabel:
        :type catgorylabel: unicode or str
        :param control:
        :type control: Control
        """
        assert isinstance(catgorylabel, unicode) or isinstance(catgorylabel, str)
        assert isinstance(control, Control)
        try:
            c = self.category(catgorylabel)
        except KeyError:
            raise KeyError('No category created with that label: %s' % catgorylabel)
        else:
            c.addControl(control)
            if control.internal_ref != u'':
                if self._controldict.has_key(control.internal_ref):
                    log(msg='Warning - control with duplicate internal reference: %s' % control.internal_ref)
                else:
                    self._controldict[control.internal_ref] = control


    def control(self, internal_ref):
        """
        Returns the instance of Control associated with the internal reference id, if the control has a unique id.
        Unless a specific internal reference id was provided during instantiation, the sid is the internal
        reference id.
        :param internal_ref:
        :type internal_ref: unicode or str
        :return:
        :rtype: Control
        """
        assert isinstance(internal_ref, unicode) or isinstance(internal_ref, str)
        internal_ref = unicode(internal_ref)
        try:
            return self._controldict[internal_ref]
        except KeyError:
            raise KeyError("No control found for sid: %s" % internal_ref)

    @staticmethod
    def renderHead():
        line1 = u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        line2 = u'<settings>'
        return [line1, line2]

    @staticmethod
    def renderTail():
        return [u'</settings>']

    def render(self):
        """
        Renders the xml version of the contained Categories and their Controls.
        :return: Unicode string representing the xml
        :rtype: unicode
        """
        self.buildIndices()
        output = self.renderHead()
        for category in self._categories:
            output += category.render(self)
        output += self.renderTail()
        output = u'\n'.join(output)
        return output

    def buildIndices(self):
        """
        Builds the index of positions of the currently contained categories and controls to be used for referenced
        conditionals.
        """
        curindex = 3
        for category in self._categories:
            curindex += 1
            for control in category._controls:
                curindex += control.weight
                if control.internal_ref != u'':
                    if not self.id_position.has_key(control.internal_ref):
                        self.id_position[control.internal_ref] = curindex
                    else:
                        log(msg='Warning duplicate key found: %s [%s, %s]' % (control.internal_ref, control.label, self.control(control.internal_ref).label))
                        self.duplicateids.append(control.internal_ref)
                control._outputindex = curindex
            curindex += 1

    def read(self):
        for category in self._categories:
            self.values.update(category.read())


class Category(object):
    """
    Class representing a category.
    """
    def __init__(self, label):
        """
        :param label:
        :type label: unicode or str
        """
        assert (isinstance(label, unicode) or isinstance(label, str))
        self.label = unicode(label)
        self._controls = []
        self.indent = u'  '

    def addControl(self, control):
        """
        Adds a control to the category
        :param control:
        :type control: Control
        """
        assert isinstance(control,Control)
        self._controls.append(control)

    def control(self, sid):
        """
        Retrieves control by sid
        :param sid:
        :type sid: unicode
        :return:
        :rtype: Control
        """
        assert isinstance(sid, unicode)
        ret = None
        for c in self._controls:
            if c.id == sid:
                ret = c
                break
        if ret is None:
            raise KeyError("Control not found for id: %s" % sid)
        else:
            return ret

    def renderHead(self):
        return [u'%s<category label="%s">' % (self.indent, _(self.label))]

    def renderTail(self):
        return [u'%s</category>' % self.indent]

    def render(self, parent):
        """
        Renders the category and its controls to xml
        :param parent:
        :type parent: resources.lib.kodisettings.struct.Settings
        :return:
        :rtype: unicode
        """
        output = self.renderHead()
        for control in self._controls:
            assert isinstance(control, Control)
            tmp = control.render(parent)
            output += tmp
        output += self.renderTail()
        return output

    def read(self):
        ret = {}
        for control in self._controls:
            ret.update(control.read())

class Control(object):
    """
    Base class for controls
    """
    __metaclass__ = abc.ABCMeta
    def __init__(self, stype, sid=u'', label=u'', enable=None, visible=None, subsetting=False, weight=1, internal_ref=None):
        """

        :param stype: The internally used type of control.
        :type stype: str
        :param sid: The settings id for the control.
        :type sid: unicode or str
        :param label: The label to be displayed. If it is a five digit integer, it will look in the po file for a localized string.
        :type label: unicode or str
        :param enable: If evaluates to false, the control is shown as greyed out and disabled.
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible: If evaluates to false, the control is not visible (hidden).
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting: If true, a dash is shown before the label.
        :type subsetting: bool
        :param weight: Internally used; the number of lines the control consumes.
        :type weight: int
        :param internal_ref: If needed, a separate internal reference id for the control. Needed if more than one control shares the same sid (and values).
        :type internal_ref: unicode or string
        """
        if isinstance(sid, str):
            sid = unicode(sid)
        if isinstance(label, str):
            label = unicode(label)
        assert isinstance(sid, unicode)
        assert isinstance(label, unicode)
        if enable is not None:
            if isinstance(enable, bool):
                enable = Conditionals(Conditional(Conditional.OP_BOOLEAN, enable))
            elif isinstance(enable, Conditional):
                enable = Conditionals(enable)
            else:
                assert isinstance(enable, Conditionals)
        if visible is not None:
            if isinstance(visible, bool):
                visible = Conditionals(Conditional(Conditional.OP_BOOLEAN, visible))
            elif isinstance(visible, Conditional):
                visible = Conditionals(visible)
            else:
                assert isinstance(visible, Conditionals)
        if internal_ref is not None:
            assert isinstance(internal_ref, str) or isinstance(internal_ref, unicode)
            self.internal_ref = unicode(internal_ref)
        else:
            self.internal_ref = sid
        self.sid = sid
        self.stype = stype
        self.label = label
        self.enable = enable
        self.visible = visible
        self.subsetting = subsetting
        self._outputindex = 0
        self.indent = u'    '
        self.weight = weight

    @abc.abstractmethod
    def render(self, parent):
        pass

    def requiredrenderlist(self, parent):
        """

        :param parent: A reference to the calling instantiation of Setttings.
        :type parent: resources.lib.kodisettings.struct.Settings
        :return: A list of rendered unicode strings.
        :rtype:list
        """
        if self.sid != u'':
            elements = [u'id="%s"' % self.sid]
        else:
            elements = []
        elements += [u'label="%s"' % _(self.label)]
        elements += [u'type="%s"' % self.stype]
        if self.subsetting is True:
            elements += [u'subsetting="true"']
        if self.enable is not None:
            elements += [u'enable="%s"' % self.enable.render(self, parent)]
        if self.visible is not None:
            elements += [u'visible="%s"' % self.visible.render(self, parent)]
        return elements

    def read(self):
        if self.sid != u'':
            return {self.sid: getSetting(self.sid)}
        else:
            return None

class Sep(Control):
    """
    Adds a horizontal separating line between other elements.
    """
    def __init__(self):
        super(Sep, self).__init__('sep')

    def render(self, parent):
        assert isinstance(parent, Settings)
        return [u'%s<setting type="sep"/>' % self.indent]

class Lsep(Control):
    """
    Shows a horizontal line with a text.
    """
    def __init__(self, sid=u'', label=u'', visible=None):
        """

        :param sid: The settings id for the control.
        :type sid: unicode or str
        :param label: The label to be displayed. If it is a five digit integer, it will look in the po file for a localized string.
        :type label: unicode or str
        :param visible: If evaluates to false, the control is not visible (hidden).
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        """
        super(Lsep, self).__init__('lsep', sid, label, visible=visible)


    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        elements += [u'/>']
        return [u' '.join(elements)]


class Text(Control):
    """
    Text input elements allow a user to input text in various formats.
    """
    def __init__(self, sid=u'', label=u'', enable=None, visible=None, subsetting=False, option=None, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label:  unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param option: "hidden"|"urlencoded" (optional)
        :type option: unicode or str
        :param default:  (optional) - the default value.
        :type default:  unicode or str
        :return:
        :rtype:
        """
        super(Text, self).__init__('text', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        self.option = option
        if option is not None:
            if option == 'hidden':
                self.option = unicode(option)
            elif option == 'urlencoded':
                self.option = unicode(option)
            else:
                raise SyntaxError('Text "option" not defined: %s' % option)
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        if self.option is not None:
            elements += [u'option="%s"' % self.option]
        elements += [u'/>']
        return [u' '.join(elements)]

class Ipaddress(Control):
    """

    """
    def __init__(self, sid=u'', label=u'', enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid:  unicode or str
        :param label:
        :type label:  unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(Ipaddress, self).__init__('ipaddress', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        elements += [u'/>']
        return [u' '.join(elements)]

class Number(Control):
    """
    Allows the user to enter an integer using up/down buttons.
    """
    def __init__(self, sid=u'', label=u'', enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label:  unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: int
        :return:
        :rtype:
        """
        super(Number, self).__init__('number', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        if default is not None:
            if isinstance(default, int):
                self.default = unicode(str(default))
            else:
                self.default = unicode(default)

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        elements += [u'/>']
        return [u' '.join(elements)]

    def read(self):
        try:
            value = int(getSetting(self.sid))
        except ValueError:
            value = 0
        return {self.sid: value}


class Slider(Control):
    """
    Allows the user to enter a number using a horizontal sliding bar.
    """
    def __init__(self, sid=u'', label=u'', srangemin=0, srangemax=100, srangestep=None, option=u'int', enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param srangemin:
        :type srangemin: int or float or str or unicode
        :param srangemax:
        :type srangemax: int or float or str or unicode
        :param srangestep:
        :type srangestep:  int or float or str or unicode
        :param option:
        :type option: unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting:bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """

        super(Slider, self).__init__('slider', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        self.srangemin = unicode(srangemin)
        self.srangemax = unicode(srangemax)
        if srangestep is not None:
            self.srangestep = unicode(srangestep)
        else:
            self.srangestep = u''
        assert isinstance(option, unicode) or isinstance(option, str)
        option = unicode(option)
        if option == u'int' or option == u'float' or option == u'percent':
            self.option = option
        else:
            raise SyntaxError('Slider option must be "int|float|percent" got: %s' % option)
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        if self.srangestep is not None:
            elements += [u'range="%s,%s,%s"' % (self.srangemin, self.srangestep, self.srangemax)]
        else:
            elements += [u'range="%s,%s"' % (self.srangemin, self.srangemax)]
        elements += [u'option="%s"' % self.option]
        elements += [u'/>']
        return [u' '.join(elements)]

    def read(self):
        rawvalue = getSetting(self.sid)
        if self.option == u'int':
            try:
                value = int(rawvalue)
            except ValueError:
                value = 0
        else:
            try:
                value = float(rawvalue)
            except ValueError:
                value = 0.00
            else:
                if self.option == u'percent':
                    value *= 100.0
        return {self.sid:value}

class Date(Control):
    """
    Displays a date picker dialog box.
    """
    def __init__(self, sid=u'', label=u'', enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(Date, self).__init__('date', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        elements += [u'/>']
        return [u' '.join(elements)]

class Time(Control):
    """
    Displays a time picker dialog box.
    """
    def __init__(self, sid=u'', label=u'', enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(Time, self).__init__('time', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        elements += [u'/>']
        return [u' '.join(elements)]

class Bool(Control):
    """
    Boolean input elements allow a user to switch a setting on or off.
    """
    def __init__(self, sid, label, enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting:  bool
        :param default:
        :type default: unicode or str or bool
        :return:
        :rtype:
        """
        super(Bool, self).__init__('bool', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        if default is not None:
            if isinstance(default, unicode) or isinstance(default, str):
                if default.lower() == 'true':
                    self.default = u'true'
                else:
                    self.default = u'false'
            elif isinstance(default, bool):
                if default is True:
                    self.default = u'true'
                else:
                    self.default = u'false'
            elif isinstance(default, int):
                if default == 0:
                    self.default = u'false'
                else:
                    self.default = u'true'
            else:
                raise TypeError ('Undefined type for default in Bool control')
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        elements += [u'/>']
        return [u' '.join(elements)]

    def read(self):
        return {self.sid:getSetting(self.sid)=='true'}

class Select(Control):
    """
    Will open separate selection window
    """
    def __init__(self, sid=u'', label=u'', values=None, lvalues=None, enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param values:
        :type values: list
        :param lvalues:
        :type lvalues: list
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(Select, self).__init__('select', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        assert ((values is not None and lvalues is None) or (lvalues is not None and values is None))
        if lvalues is not None:
            self.usinglvalues = True
        else:
            self.usinglvalues = False
        if self.usinglvalues:
            assert isinstance(lvalues, list)
            self.values = lvalues
        else:
            assert isinstance(values, list)
            self.values = values
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        if self.usinglvalues:
            lvalues = []
            for lvalue in self.values:
                lvalues.append(_(lvalue))
            elements += [u'lvalues="%s"' % '|'.join(lvalues)]
        else:
            elements += [u'values="%s"' % '|'.join(self.values)]
        elements += [u'/>']
        return [u' '.join(elements)]

class Addon(Control):
    """
    Displays a selection window with a list of addons.
    """
    def __init__(self, sid=u'', label=u'', addontype=u'xbmc.metadata.scraper.movies', multiselect=None, enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param addontype:
        :type addontype: unicode or str
        :param multiselect:
        :type multiselect: bool
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(Addon, self).__init__('addon', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        assert (isinstance(addontype, unicode) or isinstance(addontype, str))
        self.addontype = unicode(addontype)
        if multiselect is not None:
            assert isinstance(multiselect, bool)
            if multiselect is True:
                self.multiselect = u'true'
            else:
                self.multiselect = u'false'
        else:
            self.multiselect = None
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        elements += [u'addontype="%s"' % self.addontype]
        if self.multiselect is not None:
            elements += [u'multiselect="%s"' % self.multiselect]
        elements += [u'/>']
        return [u' '.join(elements)]

class Enum(Control):
    """
    A rotary selector allows the user to selected from a list of predefined values using the index of the chosen value.
    """
    def __init__(self, sid=u'', label=u'', values=None, lvalues=None, enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param values:
        :type values: list
        :param lvalues:
        :type lvalues: list
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(Enum, self).__init__('enum', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        assert ((values is not None and lvalues is None) or (lvalues is not None and values is None))
        if lvalues is not None:
            self.usinglvalues = True
        else:
            self.usinglvalues = False
        if self.usinglvalues:
            assert isinstance(lvalues, list)
            self.values = lvalues
        else:
            assert (isinstance(values, list) or values == u'$HOURS')
            self.values = values
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        if self.usinglvalues:
            lvalues = []
            for lvalue in self.values:
                lvalues.append(_(lvalue))
            elements += [u'lvalues="%s"' % '|'.join(lvalues)]
        elif self.values == u'$HOURS':
            elements += [u'values="$HOURS"']
        else:
            elements += [u'values="%s"' % '|'.join(self.values)]
        elements += [u'/>']
        return [u' '.join(elements)]

    def read(self):
        index = int(getSetting(self.sid))
        if self.values == u'$HOURS':
            return {self.sid:index}
        else:
            return {self.sid:self.values[index]}

class LabelEnum(Control):
    """
    A rotary selector allows the user to selected from a list of predefined values using the actual value of the chosen value.
    """
    def __init__(self, sid=u'', label=u'', values=None, lvalues=None, sort=u'no', enable=None, visible=None, subsetting=False, default=None, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param values:
        :type values: list
        :param lvalues:
        :type lvalues: list
        :param sort:
        :type sort: unicode or str or bool
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting:
        :param default: bool
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(LabelEnum, self).__init__('labelenum', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        assert ((values is not None and lvalues is None) or (lvalues is not None and values is None))
        if lvalues is not None:
            self.usinglvalues = True
        else:
            self.usinglvalues = False
        if self.usinglvalues:
            assert isinstance(lvalues, list)
            self.values = lvalues
        else:
            assert isinstance(values, list)
            self.values = values
        assert (sort == u'yes' or sort == u'no' or isinstance(sort, bool))
        if isinstance(sort, bool):
            if sort is True:
                self.sort = u'yes'
            else:
                self.sort = u'no'
        else:
            self.sort = sort
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'default="%s"' % self.default]
        if self.usinglvalues:
            lvalues = []
            for lvalue in self.values:
                lvalues.append(_(lvalue))
            elements += [u'lvalues="%s"' % '|'.join(lvalues)]
        else:
            elements += [u'values="%s"' % '|'.join(self.values)]
        if self.sort != u'no':
            elements += [u'sort="yes"']
        elements += [u'/>']
        return [u' '.join(elements)]

class FileBrowser(Control):
    """

    """
    TYPE_FILE = 0
    TYPE_AUDIO = 1
    TYPE_VIDEO = 2
    TYPE_IMAGE = 3
    TYPE_EXECUTABLE = 4
    TYPE_FOLDER = 5
    TYPE_FILE_ENUM = 6
    TYPE_DICT = {TYPE_FILE:'file', TYPE_AUDIO:'audio', TYPE_VIDEO:'video', TYPE_IMAGE:'image', TYPE_EXECUTABLE:'executable', TYPE_FOLDER:'folder', TYPE_FILE_ENUM:'fileenum'}

    def __init__(self, sid=u'', label=u'', fbtype=TYPE_FILE, source=u'auto', option=u'', mask=u'', enable=None, visible=None, subsetting=False, default=u'', internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param fbtype:
        :type fbtype:
        :param source:
        :type source: unicode or str
        :param option:
        :type option: unicode or str
        :param mask:
        :type mask: unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :param default:
        :type default: unicode or str
        :return:
        :rtype:
        """
        super(FileBrowser, self).__init__(self.TYPE_DICT[fbtype], sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        assert (self.TYPE_FILE <= fbtype <= self.TYPE_FILE_ENUM)
        self.fbtype = fbtype
        if fbtype == self.TYPE_FOLDER:
            self.source = source
            assert (option == u'' or option == 'writeable')
            self.option = option
        else:
            assert (option == u'' or option == u'hideext')
            self.option = option
        assert isinstance(mask, unicode) or isinstance(mask, str)
        self.mask = mask
        if default is not None:
            assert (isinstance(default, unicode) or isinstance(default, str))
            self.default = unicode(default)
        else:
            self.default = None

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        if self.default is not None:
            elements+= [u'value="%s"' % self.default]
        if self.fbtype == self.TYPE_FOLDER:
            if self.source != u'auto':
                elements += [u'source="%s"' % self.source]
            if self.option != u'':
                elements += [u'option="writeable"']
        else:
            if self.option != u'':
                elements += [u'option="hideext"']
        if self.mask != u'':
            elements += [u'mask="%s"' % self.mask]
        elements += [u'/>']
        return [u' '.join(elements)]

class Action(Control):
    """

    """
    def __init__(self, sid=u'', label=u'', action=u'', enable=None, visible=None, subsetting=False, internal_ref=None):
        """

        :param sid:
        :type sid: unicode or str
        :param label:
        :type label: unicode or str
        :param action:
        :type action: unicode or str
        :param enable:
        :type enable: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param visible:
        :type visible: NoneType or resources.lib.kodisettings.struct.Conditionals or bool or resources.lib.kodisettings.struct.Conditional
        :param subsetting:
        :type subsetting: bool
        :return:
        :rtype:
        """
        super(Action, self).__init__('action', sid, label, enable, visible, subsetting, internal_ref=internal_ref)
        assert (isinstance(action, unicode) or isinstance(action, str))
        self.action = unicode(action)

    def render(self, parent):
        elements = [u'%s<setting' % self.indent]
        elements += self.requiredrenderlist(parent)
        elements += [u'action="%s"' % self.action]
        elements += [u'/>']
        return [u' '.join(elements)]


class Conditionals(object):
    """

    """
    COMBINE_AND = 0
    COMBINE_OR = 1
    def __init__(self, args, combine_type=COMBINE_AND):
        """

        :param args:
        :type args: resources.lib.kodisettings.struct.Conditional or list
        :param combine_type:
        :type combine_type: int
        :return:
        :rtype:
        """
        if isinstance(args, list):
            for item in args:
                assert isinstance(item, Conditional)
            self.conditionals = args
        else:
            assert isinstance(args, Conditional)
            self.conditionals = [args]
        assert (combine_type==self.COMBINE_AND or combine_type==self.COMBINE_OR)
        self.combine_type = combine_type

    def addConditional(self, conditional):
        assert isinstance(conditional, Conditional)
        self.conditionals.append(conditional)

    def render(self, control, parent):
        """

        :param control:
        :type control: resources.lib.kodisettings.struct.Number or resources.lib.kodisettings.struct.Text or resources.lib.kodisettings.struct.FileBrowser or resources.lib.kodisettings.struct.Bool or resources.lib.kodisettings.struct.Lsep or resources.lib.kodisettings.struct.LabelEnum or resources.lib.kodisettings.struct.Select or resources.lib.kodisettings.struct.Action
        :param parent:
        :type parent: resources.lib.kodisettings.struct.Settings
        :return:
        :rtype:
        """
        cond = []
        for conditional in self.conditionals:
            cond += conditional.render(control, parent)
        if self.combine_type == self.COMBINE_AND:
            cond = u' + '.join(cond)
        else:
            cond = u' | '.join(cond)
        return cond


class Conditional(object):
    """

    """
    OP_EQUAL = 1
    OP_NOT_EQUAL = 2
    OP_GREATER_THAN = 3
    OP_LESSER_THAN = 5
    OP_HAS_ADDON = 7
    OP_BOOLEAN = 8
    OP_DICT = {OP_EQUAL:u'eq', OP_NOT_EQUAL:u'!eq', OP_GREATER_THAN:u'gt', OP_LESSER_THAN:u'lt'}
    def __init__(self, operator, value, reference=None):
        """

        :param operator:
        :type operator: int
        :param value:
        :type value:  unicode or str or bool
        :param reference:
        :type reference:  unicode or str
        :return:
        :rtype:
        """
        self.operator = operator
        if operator == Conditional.OP_BOOLEAN:
            assert isinstance(value, bool)
            if value is True:
                self.value = u'true'
            else:
                self.value = u'false'
        elif operator != Conditional.OP_HAS_ADDON:
            assert isinstance(reference, unicode) or isinstance(reference, str)
            assert isinstance(value, unicode) or isinstance(value, str)
            assert reference != u''
            self.reference = unicode(reference)
            self.value = unicode(value)
        else:
            assert isinstance(value, unicode) or isinstance(value, str)
            self.addonid = unicode(value)

    def render(self, control, parent):
        """

        :param control:
        :type control: resources.lib.kodisettings.struct.Number or resources.lib.kodisettings.struct.Text or resources.lib.kodisettings.struct.FileBrowser or resources.lib.kodisettings.struct.Bool or resources.lib.kodisettings.struct.Lsep or resources.lib.kodisettings.struct.LabelEnum or resources.lib.kodisettings.struct.Select or resources.lib.kodisettings.struct.Action
        :param parent:
        :type parent: resources.lib.kodisettings.struct.Settings
        :return:
        :rtype:
        """
        if self.operator == self.OP_BOOLEAN:
            return [self.value]
        elif self.operator == self.OP_HAS_ADDON:
            return [u'System.HasAddon(%s)' % self.addonid]
        else:
            assert isinstance(parent, Settings)
            if self.reference in parent.duplicateids:
                raise KeyError('Cannot use control with duplicated id as reference: %s' % self.reference)
            relindex = parent.control(self.reference)._outputindex - control._outputindex
            refcontrol = parent.control(self.reference)
            assert isinstance(refcontrol, Control)
            if refcontrol.stype == u'enum' or refcontrol.stype == u'labelenum':
                assert (isinstance(refcontrol, Enum) or isinstance(refcontrol, LabelEnum))
                index = None
                for i, item in enumerate(refcontrol.values):
                    if item == self.value:
                        index = i
                        break
                if index is None:
                    raise KeyError('Conditional Error: match value (%s) not in list of values: %s' % (self.value, refcontrol.values))
                else:
                    return [u'%s(%s,%s)' % (self.OP_DICT[self.operator], relindex, index)]
            elif refcontrol.stype == u'labelenum':
                assert isinstance(refcontrol, LabelEnum)
                if self.value in refcontrol.values:
                    return [u'%s(%s,%s)' % (self.OP_DICT[self.operator], relindex, self.value)]
                else:
                    raise KeyError('Conditional Error: match value (%s) not in list of values: %s' % (self.value, refcontrol.values))
            else:
                return [u'%s(%s,%s)' % (self.OP_DICT[self.operator], relindex, self.value)]

getControlClass = {'sep': Sep, 'lsep':Lsep, 'text':Text, 'ipaddress':Ipaddress, 'number':Number, 'slider':Slider,
                   'date':Date, 'time':Time, 'bool':Bool, 'select':Select, 'addon':Addon, 'enum':Enum,
                   'labelenum':LabelEnum, 'browser':FileBrowser, 'action':Action}




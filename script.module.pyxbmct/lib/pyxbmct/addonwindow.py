# -*- coding: utf-8 -*-
# PyXBMCt framework module
#
# PyXBMCt is a mini-framework for creating Kodi (XBMC) Python addons
# with arbitrary UI made of Controls - decendants of xbmcgui.Control class.
# The framework uses image textures from Kodi Confluence skin.
#
# Licence: GPL v.3 <http://www.gnu.org/licenses/gpl.html>
"""
This module contains all classes and constants of PyXBMCt framework
"""

from __future__ import absolute_import, division, unicode_literals
import os
from six.moves import range
from kodi_six import xbmc, xbmcgui
from .addonskin import Skin

skin = Skin()

# Text alighnment constants. Mixed variants are obtained by bit OR (|)
ALIGN_LEFT = 0
"""Align left"""
ALIGN_RIGHT = 1
"""Align right"""
ALIGN_CENTER_X = 2
"""Align center horisontally"""
ALIGN_CENTER_Y = 4
"""Align center vertically"""
ALIGN_CENTER = 6
"""Align center by both axis"""
ALIGN_TRUNCATED = 8
"""Align truncated"""
ALIGN_JUSTIFY = 10
"""Align justify"""

# Kodi key action codes.
# More codes available in xbmcgui module
ACTION_PREVIOUS_MENU = 10
"""ESC action"""
ACTION_NAV_BACK = 92
"""Backspace action"""
ACTION_MOVE_LEFT = 1
"""Left arrow key"""
ACTION_MOVE_RIGHT = 2
"""Right arrow key"""
ACTION_MOVE_UP = 3
"""Up arrow key"""
ACTION_MOVE_DOWN = 4
"""Down arrow key"""
ACTION_MOUSE_WHEEL_UP = 104
"""Mouse wheel up"""
ACTION_MOUSE_WHEEL_DOWN = 105
"""Mouse wheel down"""
ACTION_MOUSE_DRAG = 106
"""Mouse drag"""
ACTION_MOUSE_MOVE = 107
"""Mouse move"""
ACTION_MOUSE_LEFT_CLICK = 100
"""Mouse click"""


def _set_textures(textures, kwargs):
    """Set texture arguments for controls."""
    for texture in textures:
        if kwargs.get(texture) is None:
            kwargs[texture] = textures[texture]


class AddonWindowError(Exception):
    """Custom exception"""
    pass


class Label(xbmcgui.ControlLabel):
    """
    Label(label, font=None, textColor=None, disabledColor=None, alignment=0,hasPath=False, angle=0)
    
    ControlLabel class.
    
    Implements a simple text label.

    :param label: text string
    :type label: str
    :param font: font used for label text. (e.g. ``'font13'``)
    :type font: str
    :param textColor: hex color code of enabled label's label. (e.g. ``'0xFFFFFFFF'``)
    :type textColor: str
    :param disabledColor: hex color code of disabled label's label. (e.g. ``'0xFFFF3300'``)
    :type disabledColor: str
    :param alignment: alignment of label. **Note**: see ``xbfont.h``
    :type alignment: int
    :param hasPath: ``True`` = stores a path / ``False`` = no path.
    :type hasPath: bool
    :param angle: angle of control. (``+`` rotates CCW, ``-`` rotates CW)
    :type angle: int

    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::

        self.label = Label('Status', angle=45)
    """
    def __new__(cls, *args, **kwargs):
        return super(Label, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class FadeLabel(xbmcgui.ControlFadeLabel):
    """
    FadeLabel(font=None, textColor=None, _alignment=0)
    
    Control that scrolls label text.
    
    Implements a text label that can auto-scroll very long text.
    
    :param font: font used for label text. (e.g. ``'font13'``)
    :type font: str
    :param textColor: hex color code of fadelabel's labels. (e.g. ``'0xFFFFFFFF'``)
    :type textColor: str
    :param _alignment: alignment of label. **Note**: see ``xbfont.h``
    :type _alignment: int
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::
    
        self.fadelabel = FadeLabel(textColor='0xFFFFFFFF')
    """
    def __new__(cls, *args, **kwargs):
        return super(FadeLabel, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class TextBox(xbmcgui.ControlTextBox):
    """
    TextBox(font=None, textColor=None)
    
    ControlTextBox class
    
    Implements a box for displaying multi-line text.
    Long text is truncated from below. Also supports auto-scrolling.
    
    :param font: font used for text. (e.g. ``'font13'``)
    :type font: str
    :param textColor: hex color code of textbox's text. (e.g. ``'0xFFFFFFFF'``)
    :type textColor: str
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::
    
        self.textbox = TextBox(textColor='0xFFFFFFFF')
    """
    def __new__(cls, *args, **kwargs):
        return super(TextBox, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class Image(xbmcgui.ControlImage):
    """
    Image(filename, aspectRatio=0, colorDiffuse=None)
    
    ControlImage class.
    
    Implements a box for displaying ``.jpg``, ``.png``, and ``.gif`` images.

    :param filename: path or URL to an image file.
    :type filename: str
    :param aspectRatio: (values: ``0`` = stretch (default), ``1`` = scale up (crops), ``2`` = scale down (black bars)
    :type aspectRatio: int
    :param colorDiffuse: for example, ``'0xC0FF0000'`` (red tint)
    :type colorDiffuse: str
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::
    
        self.image = Image('d:\images\picture.jpg', aspectRatio=2)
    """
    def __new__(cls, *args, **kwargs):
        return super(Image, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class CompareMixin(object):
    def __eq__(self, other):
        if hasattr(other, 'getId'):
            return self.getId() == other.getId()
        return False


class Button(CompareMixin, xbmcgui.ControlButton):
    """
    Button(label, focusTexture=None, noFocusTexture=None, textOffsetX=CONTROL_TEXT_OFFSET_X, textOffsetY=CONTROL_TEXT_OFFSET_Y, alignment=4, font=None, textColor=None, disabledColor=None, angle=0, shadowColor=None, focusedColor=None)
    
    ControlButton class.
    
    Implements a clickable button.

    :param label: button caption
    :type label: str
    :param focusTexture: filename for focus texture.
    :type focusTexture: str
    :param noFocusTexture: filename for no focus texture.
    :type noFocusTexture: str
    :param textOffsetX: x offset of label.
    :type textOffsetX: int
    :param textOffsetY: y offset of label.
    :type textOffsetY: int
    :param alignment: alignment of label. **Note**: see ``xbfont.h``
    :type alignment: int
    :param font: font used for label text. (e.g. ``'font13'``)
    :type font: str
    :param textColor: hex color code of enabled button's label. (e.g. ``'0xFFFFFFFF'``)
    :type textColor: str
    :param disabledColor: hex color code of disabled button's label. (e.g. ``'0xFFFF3300'``)
    :type disabledColor: str
    :param angle: angle of control. (``+`` rotates CCW, ``-`` rotates CW)
    :type angle: int
    :param shadowColor: hex color code of button's label's shadow. (e.g. ``'0xFF000000'``)
    :type shadowColor: str
    :param focusedColor: hex color code of focused button's label. (e.g. ``'0xFF00FFFF'``)
    :type focusedColor: str
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
        
    Example::
    
        self.button = Button('Status', font='font14')
    """
    def __new__(cls, *args, **kwargs):
        textures = {'focusTexture': os.path.join(skin.images, 'Button', 'KeyboardKey.png'),
                    'noFocusTexture': os.path.join(skin.images, 'Button', 'KeyboardKeyNF.png')}
        _set_textures(textures, kwargs)
        if kwargs.get('alignment') is None:
            kwargs['alignment'] = ALIGN_CENTER
        return super(Button, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class RadioButton(CompareMixin, xbmcgui.ControlRadioButton):
    """
    RadioButton(label, focusTexture=None, noFocusTexture=None, textOffsetX=None, textOffsetY=None, _alignment=None, font=None, textColor=None, disabledColor=None, angle=None, shadowColor=None, focusedColor=None, focusOnTexture=None, noFocusOnTexture=None, focusOffTexture=None, noFocusOffTexture=None)
    
    ControlRadioButton class.
    
    Implements a 2-state switch.
    
    :param label: label text.
    :type: str or unicode
    :param focusTexture: filename for focus texture.
    :type focusTexture: str
    :param noFocusTexture: filename for no focus texture.
    :type noFocusTexture: str
    :param textOffsetX: x offset of label.
    :type textOffsetX: int
    :param textOffsetY: y offset of label.
    :type textOffsetY: int
    :param _alignment: alignment of label - *Note, see xbfont.h
    :type _alignment: int
    :param font: font used for label text. (e.g. 'font13')
    :type font: str
    :param textColor: hexstring -- color of enabled radio button's label. (e.g. '0xFFFFFFFF')
    :type textColor: str
    :param disabledColor: hexstring -- color of disabled radio button's label. (e.g. '0xFFFF3300')
    :type disabledColor: str
    :param angle: angle of control. (+ rotates CCW, - rotates CW)
    :type angle: int
    :param shadowColor: hexstring -- color of radio button's label's shadow. (e.g. '0xFF000000')
    :type shadowColor: str
    :param focusedColor: hexstring -- color of focused radio button's label. (e.g. '0xFF00FFFF')
    :type focusedColor: str
    :param focusOnTexture: filename for radio focused/checked texture.
    :type focusOnTexture: str
    :param noFocusOnTexture: filename for radio not focused/checked texture.
    :type noFocusOnTexture: str
    :param focusOffTexture: filename for radio focused/unchecked texture.
    :type focusOffTexture: str
    :param noFocusOffTexture: filename for radio not focused/unchecked texture.
    :type noFocusOffTexture: str
    
    .. note:: To customize RadioButton all 4 abovementioned textures need to be provided.
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::
    
        self.radiobutton = RadioButton('Status', font='font14')
    """
    def __new__(cls, *args, **kwargs):
        if xbmc.getInfoLabel('System.BuildVersion')[:2] >= '13':
            textures = {'focusTexture': os.path.join(skin.images, 'RadioButton', 'MenuItemFO.png'),
                        'noFocusTexture': os.path.join(skin.images, 'RadioButton', 'MenuItemNF.png'),
                        'focusOnTexture': os.path.join(skin.images, 'RadioButton', 'radiobutton-focus.png'),
                        'noFocusOnTexture': os.path.join(skin.images, 'RadioButton', 'radiobutton-focus.png'),
                        'focusOffTexture': os.path.join(skin.images, 'RadioButton', 'radiobutton-nofocus.png'),
                        'noFocusOffTexture': os.path.join(skin.images, 'RadioButton', 'radiobutton-nofocus.png')}
        else: # This is for compatibility with Frodo and earlier versions.
            textures = {'focusTexture': os.path.join(skin.images, 'RadioButton', 'MenuItemFO.png'),
                        'noFocusTexture': os.path.join(skin.images, 'RadioButton', 'MenuItemNF.png'),
                        'TextureRadioFocus': os.path.join(skin.images, 'RadioButton', 'radiobutton-focus.png'),
                        'TextureRadioNoFocus': os.path.join(skin.images, 'RadioButton', 'radiobutton-nofocus.png')}
        _set_textures(textures, kwargs)
        return super(RadioButton, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class Edit(CompareMixin, xbmcgui.ControlEdit):
    """
    Edit(label, font=None, textColor=None, disabledColor=None, _alignment=0, focusTexture=None, noFocusTexture=None, isPassword=False)
    
    ControlEdit class.
    
    Implements a clickable text entry field with an on-screen keyboard.

    :param label: text string.
    :type label: str or unicode
    :param font: [opt] font used for label text. (e.g. 'font13')
    :type font: str
    :param textColor: [opt] hexstring -- color of enabled label's label. (e.g. '0xFFFFFFFF')
    :type textColor: str
    :param disabledColor: [opt] hexstring -- color of disabled label's label. (e.g. '0xFFFF3300')
    :type disabledColor: str
    :param _alignment: [opt] lignment of label - *Note, see xbfont.h
    :type _alignment: int
    :param focusTexture: [opt] filename for focus texture.
    :type focusTexture: str
    :param noFocusTexture: [opt] filename for no focus texture.
    :type noFocusTexture: str
    :param isPassword: [opt] if ``True``, mask text value.
    :type isPassword: bool
    
    .. note:: You can use the above as keywords for arguments and skip certain optional arguments.
        Once you use a keyword, all following arguments require the keyword.
        After you create the control, you need to add it to the window with ``placeControl()``.
    
    Example::
    
        self.edit = Edit('Status')
    """
    def __new__(cls, *args, **kwargs):
        textures = {'focusTexture': os.path.join(skin.images, 'Edit', 'button-focus.png'),
                    'noFocusTexture': os.path.join(skin.images, 'Edit', 'black-back2.png')}
        _set_textures(textures, kwargs)
        return super(Edit, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class List(CompareMixin, xbmcgui.ControlList):
    """
    List(font=None, textColor=None, buttonTexture=None, buttonFocusTexture=None, selectedColor=None, _imageWidth=10, _imageHeight=10, _itemTextXOffset=10, _itemTextYOffset=2, _itemHeight=27, _space=2, _alignmentY=4)
    
    ControlList class.
    
    Implements a scrollable list of items.
    
    :param font: string - font used for items label. (e.g. 'font13')
    :param textColor: hexstring - color of items label. (e.g. '0xFFFFFFFF')
    :param buttonTexture: string - filename for no focus texture.
    :param buttonFocusTexture: string - filename for focus texture.
    :param selectedColor: integer - x offset of label.
    :param _imageWidth: integer - width of items icon or thumbnail.
    :param _imageHeight: integer - height of items icon or thumbnail.
    :param _itemTextXOffset: integer - x offset of items label.
    :param _itemTextYOffset: integer - y offset of items label.
    :param _itemHeight: integer - height of items.
    :param _space: integer - space between items.
    :param _alignmentY: integer - Y-axis alignment of items label - *Note, see xbfont.h
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::
    
        self.cList = List('font14', space=5)
    """
    def __new__(cls, *args, **kwargs):
        textures = {'buttonTexture': os.path.join(skin.images, 'List', 'MenuItemNF.png'),
                    'buttonFocusTexture': os.path.join(skin.images, 'List', 'MenuItemFO.png')}
        _set_textures(textures, kwargs)
        return super(List, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class Slider(CompareMixin, xbmcgui.ControlSlider):
    """
    Slider(textureback=None, texture=None, texturefocus=None, orientation=xbmcgui.HORIZONTAL)
    
    ControlSlider class.
    
    Implements a movable slider for adjusting some value.
    
    :param textureback: string -- image filename.
    :param texture: string -- image filename.
    :param texturefocus: string -- image filename.
    :param orientation: int -- slider orientation
    
    .. note:: After you create the control, you need to add it to the window with placeControl().
    
    Example::
    
        self.slider = Slider()
    """
    def __new__(cls, *args, **kwargs):
        textures = {'textureback': os.path.join(skin.images, 'Slider', 'osd_slider_bg.png'),
                    'texture': os.path.join(skin.images, 'Slider', 'osd_slider_nibNF.png'),
                    'texturefocus': os.path.join(skin.images, 'Slider', 'osd_slider_nib.png')}
        _set_textures(textures, kwargs)
        if xbmc.getInfoLabel('System.BuildVersion')[:2] >= '17':
            kwargs['orientation'] = xbmcgui.HORIZONTAL
        return super(Slider, cls).__new__(cls, -10, -10, 1, 1, *args, **kwargs)


class AbstractWindow(object):

    """
    Top-level control window.
    
    The control windows serves as a parent widget for other XBMC UI controls
    much like Tkinter.Tk or PyQt QWidget class.
    
    This class is a basic "skeleton" for a control window.

    .. warning:: This is an abstract class and is not supposed to be instantiated directly!
    """

    def __init__(self):
        self.actions_connected = []
        self.controls_connected = []

    def setGeometry(self, width_, height_, rows_, columns_, pos_x=-1, pos_y=-1):
        """
        Set width, height, Grid layout, and coordinates (optional) for a new control window.
        
        :param width_: widgh of the created window.
        :param height_: height of the created window.
        :param rows_: # rows of the Grid layout to place controls on.
        :param columns_: # colums of the Grid layout to place controls on.
        :param pos_x: (opt) x coordinate of the top left corner of the window.
        :param pos_y: (opt) y coordinates of the top left corner of the window.
        
        If pos_x and pos_y are not privided, the window will be placed
        at the center of the screen.

        Example::
        
            self.setGeometry(400, 500, 5, 4)
        """
        self.width = width_
        self.height = height_
        self.rows = rows_
        self.columns = columns_
        if pos_x > 0 and pos_y > 0:
            self.x = pos_x
            self.y = pos_y
        else:
            self.x = 640 - self.width // 2
            self.y = 360 - self.height // 2
        self._setGrid()

    def _setGrid(self):
        """
        Set window grid layout of rows x columns.

        This is a helper method not to be called directly.
        """
        self.grid_x = self.x
        self.grid_y = self.y
        self.tile_width = self.width // self.columns
        self.tile_height = self.height // self.rows

    def placeControl(self, control, row, column, rowspan=1, columnspan=1, pad_x=5, pad_y=5):
        """
        Place a control within the window grid layout.

        :param control: control instance to be placed in the grid.
        :param row: row number where to place the control (starts from 0).
        :param column: column number where to place the control (starts from 0).
        :param rowspan: set when the control needs to occupy several rows.
        :param columnspan: set when the control needs to occupy several columns.
        :param pad_x: horisontal padding.
        :param pad_y: vertical padding.
        :raises: :class:`AddonWindowError` if a grid has not yet been set.

        Use ``pad_x`` and ``pad_y`` to adjust control's aspect.
        Negative padding values can be used to make a control overlap with grid cells next to it, if necessary.

        Example::

            self.placeControl(self.label, 0, 1)
        """
        try:
            control_x = (self.grid_x + self.tile_width * column) + pad_x
            control_y = (self.grid_y + self.tile_height * row) + pad_y
            control_width = self.tile_width * columnspan - 2 * pad_x
            control_height = self.tile_height * rowspan - 2 * pad_y
        except AttributeError:
            raise AddonWindowError('Window geometry is not defined! Call setGeometry first.')
        control.setPosition(control_x, control_y)
        control.setWidth(control_width)
        control.setHeight(control_height)
        self.addControl(control)
        self.setAnimation(control)

    def getX(self):
        """Get X coordinate of the top-left corner of the window."""
        try:
            return self.x
        except AttributeError:
            raise AddonWindowError('Window geometry is not defined! Call setGeometry first.')

    def getY(self):
        """Get Y coordinate of the top-left corner of the window."""
        try:
            return self.y
        except AttributeError:
            raise AddonWindowError('Window geometry is not defined! Call setGeometry first.')

    def getWindowWidth(self):
        """Get window width."""
        try:
            return self.width
        except AttributeError:
            raise AddonWindowError('Window geometry is not defined! Call setGeometry first.')

    def getWindowHeight(self):
        """Get window height."""
        try:
            return self.height
        except AttributeError:
            raise AddonWindowError('Window geometry is not defined! Call setGeometry first.')

    def getRows(self):
        """
        Get grid rows count.

        :raises: :class:`AddonWindowError` if a grid has not yet been set.
        """
        try:
            return self.rows
        except AttributeError:
            raise AddonWindowError('Grid layot is not set! Call setGeometry first.')

    def getColumns(self):
        """
        Get grid columns count.

        :raises: :class:`AddonWindowError` if a grid has not yet been set.
        """
        try:
            return self.columns
        except AttributeError:
            raise AddonWindowError('Grid layout is not set! Call setGeometry first.')

    def connect(self, event, callable):
        """
        Connect an event to a function.

        :param event: event to be connected.
        :param callable: callable object the event is connected to.

        An event can be an inctance of a Control object or an integer key action code.
        Several basic key action codes are provided by PyXBMCt. ``xbmcgui`` module
        provides more action codes.

        You can connect the following Controls: :class:`Button`, :class:`RadioButton`
        and :class:`List`. Other Controls do not generate any control events when activated
        so their connections won't work.

        To catch :class:`Slider` events you need to connect the following key actions:
        ``ACTION_MOVE_LEFT``, ``ACTION_MOVE_RIGHT`` and ``ACTION_MOUSE_DRAG``, and do a check
        whether the ``Slider`` instance is focused.

        ``callable`` parameter is a function or a method to be executed on when the event is fired.

        .. warning:: For connection you must provide a function object without brackets ``()``,
            not a function call!

        ``lambda`` can be used as to call another function or method with parameters known at runtime.

        Examples::

            self.connect(self.exit_button, self.close)

        or::

            self.connect(ACTION_NAV_BACK, self.close)
        """
        try:
            self.disconnect(event)
        except AddonWindowError:
            if isinstance(event, int):
                self.actions_connected.append([event, callable])
            else:
                self.controls_connected.append([event, callable])

    def connectEventList(self, events, function):
        """
        Connect a list of controls/action codes to a function.

        See :meth:`connect` docstring for more info.
        """
        [self.connect(event, function) for event in events]

    def disconnect(self, event):
        """
        Disconnect an event from a function.

        An event can be an inctance of a Control object or an integer key action code
        which has previously been connected to a function or a method.

        :param event: event to be disconnected.
        :raises: :class:`AddonWindowError` if an event is not connected to any function.

        Examples::

            self.disconnect(self.exit_button)

        or::

            self.disconnect(ACTION_NAV_BACK)
        """
        if isinstance(event, int):
             event_list = self.actions_connected
        else:
             event_list = self.controls_connected
        for index in range(len(event_list)):
            if event == event_list[index][0]:
                event_list.pop(index)
                break
        else:
            raise AddonWindowError('The action or control %s is not connected!' % event)

    def disconnectEventList(self, events):
        """
        Disconnect a list of controls/action codes from functions.

        See :func:`disconnect` docstring for more info.

        :param events: the list of events to be disconnected.
        :raises: :class:`AddonWindowError` if at least one event in the list
            is not connected to any function.
        """
        [self.disconnect(event) for event in events]

    def _executeConnected(self, event, connected_list):
        """
        Execute a connected event (an action or a control).

        This is a helper method not to be called directly.
        """
        for item in connected_list:
            if item[0] == event:
                item[1]()
                break

    def setAnimation(self, control):
        """
        Set animation for control

        :param control: control for which animation is set.

        This method is called automatically to set animation properties for all controls
        added to the current addon window instance -- both for built-in controls
        (window background, title bar etc.) and for controls added with :meth:`placeControl`.

        It receives a control instance as the 2nd positional argument (besides ``self``).
        By default the method does nothing, i.e. no animation is set for controls.
        To add animation you need to re-implement this method in your child class.

        E.g::

            def setAnimation(self, control):
                control.setAnimations([('WindowOpen', 'effect=fade start=0 end=100 time=1000',),
                                        ('WindowClose', 'effect=fade start=100 end=0 time=1000',)])
        """
        pass


class AddonWindow(AbstractWindow):

    """
    Top-level control window.

    The control windows serves as a parent widget for other XBMC UI controls
    much like ``Tkinter.Tk`` or PyQt ``QWidget`` class.
    This is an abstract class which is not supposed to be instantiated directly
    and will raise exeptions. It is designed to be implemented in a grand-child class
    with the second inheritance from ``xbmcgui.Window`` or ``xbmcgui.WindowDialog``
    in a direct child class.

    This class provides a control window with a background and a header
    similar to top-level widgets of desktop UI frameworks.

    .. warning:: This is an abstract class and is not supposed to be instantiated directly!
    """

    def __init__(self, title=''):
        """Constructor method."""
        super(AddonWindow, self).__init__()
        self._setFrame(title)

    def _setFrame(self, title):
        """
        Set window frame

        Define paths to images for window background and title background textures,
        and set control position adjustment constants used in setGrid.

        This is a helper method not to be called directly.
        """
        # Window background image
        self.background_img = skin.background_img
        # Background for a window header
        self.title_background_img = skin.title_background_img
        self.background = xbmcgui.ControlImage(-10, -10, 1, 1, self.background_img)
        self.addControl(self.background)
        self.setAnimation(self.background)
        self.title_background = xbmcgui.ControlImage(-10, -10, 1, 1, self.title_background_img)
        self.addControl(self.title_background)
        self.setAnimation(self.title_background)
        self.title_bar = xbmcgui.ControlLabel(-10, -10, 1, 1, title, alignment=skin.header_align,
                                              textColor=skin.header_text_color, font='font13_title')
        self.addControl(self.title_bar)
        self.setAnimation(self.title_bar)
        self.window_close_button = xbmcgui.ControlButton(-100, -100, skin.close_btn_width, skin.close_btn_height, '',
                        focusTexture=skin.close_button_focus,
                        noFocusTexture=skin.close_button_no_focus)
        self.addControl(self.window_close_button)
        self.setAnimation(self.window_close_button)

    def setGeometry(self, width_, height_, rows_, columns_, pos_x=-1, pos_y=-1, padding=5):
        """
        Set width, height, Grid layout, and coordinates (optional) for a new control window.

        :param width_: new window width in pixels.
        :param height_: new window height in pixels.
        :param rows_: # of rows in the Grid layout to place controls on.
        :param columns_: # of colums in the Grid layout to place controls on.
        :param pos_x: (optional) x coordinate of the top left corner of the window.
        :param pos_y: (optional) y coordinate of the top left corner of the window.
        :param padding: (optional) padding between outer edges of the window
        and controls placed on it.

        If ``pos_x`` and ``pos_y`` are not privided, the window will be placed
        at the center of the screen.

        Example::

            self.setGeometry(400, 500, 5, 4)
        """
        self.win_padding = padding
        super(AddonWindow, self).setGeometry(width_, height_, rows_, columns_, pos_x, pos_y)
        self.background.setPosition(self.x, self.y)
        self.background.setWidth(self.width)
        self.background.setHeight(self.height)
        self.title_background.setPosition(self.x + skin.x_margin, self.y + skin.y_margin + skin.title_back_y_shift)
        self.title_background.setWidth(self.width - 2 * skin.x_margin)
        self.title_background.setHeight(skin.header_height)
        self.title_bar.setPosition(self.x + skin.x_margin + skin.title_bar_x_shift,
                                   self.y + skin.y_margin + skin.title_bar_y_shift)
        self.title_bar.setWidth(self.width - 2 * skin.x_margin)
        self.title_bar.setHeight(skin.header_height)
        self.window_close_button.setPosition(self.x + self.width - skin.close_btn_x_offset,
                                             self.y + skin.y_margin + skin.close_btn_y_offset)

    def _setGrid(self):
        """
        Set window grid layout of rows * columns.

        This is a helper method not to be called directly.
        """
        self.grid_x = self.x + skin.x_margin + self.win_padding
        self.grid_y = self.y + skin.y_margin + skin.title_back_y_shift + skin.header_height + self.win_padding
        self.tile_width = (self.width - 2 * (skin.x_margin + self.win_padding)) // self.columns
        self.tile_height = ((self.height - skin.header_height - skin.title_back_y_shift -
                             2 * (skin.y_margin + self.win_padding)) // self.rows)

    def setWindowTitle(self, title=''):
        """
        Set window title.

        .. warning:: This method must be called **AFTER** (!!!) :meth:`setGeometry`,
            otherwise there is some werid bug with all skin text labels set to the ``title`` text.

        Example::

            self.setWindowTitle('My Cool Addon')
        """
        self.title_bar.setLabel(title)

    def getWindowTitle(self):
        """Get window title."""
        return self.title_bar.getLabel()


class FullWindowMixin(xbmcgui.Window):

    """An abstract class to define window event processing."""

    def onAction(self, action):
        """
        Catch button actions.

        ``action`` is an instance of :class:`xbmcgui.Action` class.
        """
        if action == ACTION_PREVIOUS_MENU:
            self.close()
        else:
            self._executeConnected(action, self.actions_connected)

    def onControl(self, control):
        """
        Catch activated controls.

        ``control`` is an instance of :class:`xbmcgui.Control` class.
        """
        if (hasattr(self, 'window_close_button') and
                control.getId() == self.window_close_button.getId()):
            self.close()
        else:
            self._executeConnected(control, self.controls_connected)


class DialogWindowMixin(xbmcgui.WindowDialog):

    """An abstract class to define window event processing."""

    def onAction(self, action):
        """
        Catch button actions.

        ``action`` is an instance of class:`xbmcgui.Action` class.
        """
        if action == ACTION_PREVIOUS_MENU:
            self.close()
        else:
            self._executeConnected(action, self.actions_connected)

    def onControl(self, control):
        """
        Catch activated controls.

        ``control`` is an instance of :class:`xbmcgui.Control` class.
        """
        if (hasattr(self, 'window_close_button') and
                control.getId() == self.window_close_button.getId()):
            self.close()
        else:
            self._executeConnected(control, self.controls_connected)


class BlankFullWindow(AbstractWindow, FullWindowMixin):
    """
    BlankFullWindow()

    Addon UI container with a solid background.

    This is a blank window with a black background and without any elements whatsoever.
    The decoration and layout are completely up to an addon developer.
    The window controls can hide under video or music visualization.
    """
    pass


class BlankDialogWindow(AbstractWindow, DialogWindowMixin):
    """
    BlankDialogWindow()

    Addon UI container with a transparent background.

    This is a blank window with a transparent background and without any elements whatsoever.
    The decoration and layout are completely up to an addon developer.
    The window controls are always displayed over video or music visualization.
    """
    pass


class AddonFullWindow(AddonWindow, FullWindowMixin):

    """
    AddonFullWindow(title='')

    Addon UI container with a solid background.

    ``AddonFullWindow`` instance is displayed on top of the main background image --
    ``self.main_bg`` -- and can hide behind a fullscreen video or music viaualisation.

    Minimal example::

        addon = AddonFullWindow('My Cool Addon')
        addon.setGeometry(400, 300, 4, 3)
        addon.doModal()
    """

    def __new__(cls, title='', *args, **kwargs):
        return super(AddonFullWindow, cls).__new__(cls, *args, **kwargs)

    def _setFrame(self, title):
        """
        Set the image for for the fullscreen background.
        """
        # Image for the fullscreen background.
        self.main_bg_img = skin.main_bg_img
        # Fullscreen background image control.
        self.main_bg = xbmcgui.ControlImage(1, 1, 1280, 720, self.main_bg_img)
        self.addControl(self.main_bg)
        super(AddonFullWindow, self)._setFrame(title)

    def setBackground(self, image=''):
        """
        Set the main bacground to an image file.

        :param image: path to an image file as str.

        Example::

            self.setBackground('/images/bacground.png')
        """
        self.main_bg.setImage(image)


class AddonDialogWindow(AddonWindow, DialogWindowMixin):
    """
    AddonDialogWindow(title='')

    Addon UI container with a transparent background.

    .. note:: ``AddonDialogWindow`` instance is displayed on top of XBMC UI,
        including fullscreen video and music visualization.

    Minimal example::

        addon = AddonDialogWindow('My Cool Addon')
        addon.setGeometry(400, 300, 4, 3)
        addon.doModal()
    """
    pass

"""Color picker action for skin utilities."""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
import xbmc
import xbmcgui
import xbmcvfs

from lib.kodi.client import log, ADDON
from lib.kodi.utilities import resolve_infolabel as _resolve_infolabel


def _show_error(message: str) -> None:
    """Show error notification."""
    xbmcgui.Dialog().notification(
        'Color Picker Error',
        message,
        xbmcgui.NOTIFICATION_ERROR,
        3000
    )


class _ColorPickerDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.current_color = kwargs.pop('current_color')
        self.default_color = kwargs.pop('default_color')
        self.palette_colors = kwargs.pop('palette_colors', [])
        self.onback = kwargs.pop('onback', '')
        self.result_color = None
        self._initialized = False
        super().__init__(*args, **kwargs)

    def onInit(self):
        if self._initialized:
            return
        self._initialized = True
        self._parse_and_set_sliders(self.current_color)
        self._update_preview()
        self._populate_palette()

        try:
            panel = self.getControl(300)
            if panel.size() > 0:  # type: ignore[attr-defined]
                self.setFocusId(300)
        except Exception:
            pass

    def onAction(self, action):
        if action.getId() in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            self._update_preview()
        elif action.getId() == xbmcgui.ACTION_SELECT_ITEM:
            focused_id = self.getFocusId()
            if focused_id == 300:
                self._select_palette_color()
        elif action.getId() in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            if self.onback:
                self._execute_onback()
                return
        super().onAction(action)

    def _execute_onback(self) -> None:
        """Execute onback behavior with conditional support."""
        for block in self.onback.split('||'):
            block = block.strip()
            if not block:
                continue

            if '::' in block:
                condition, actions = block.split('::', 1)
                condition = condition.strip()
                actions = actions.strip()
            else:
                condition = block.strip()
                actions = None

            condition_met = True
            if condition:
                condition_met = xbmc.getCondVisibility(condition)

            if condition_met:
                if actions:
                    for action in actions.split(';'):
                        xbmc.executebuiltin(action.strip(), True)
                else:
                    self.close()
                return

    def _select_palette_color(self) -> None:
        """Update preview and sliders when palette color is selected."""
        try:
            palette_list = self.getControl(300)
            selected_item = palette_list.getSelectedItem()  # type: ignore[attr-defined]
            if selected_item:
                color_value = selected_item.getProperty('color')
                if color_value and len(color_value) == 8:
                    self._parse_and_set_sliders(color_value)
                    self._update_preview()
        except Exception as e:
            log("General", f'Color Picker: Error selecting palette color: {e}', xbmc.LOGERROR)

    def _update_preview(self) -> None:
        """Update preview color property based on current slider values."""
        try:
            current_hex = self._merge_color()
            xbmc.executebuiltin(f'SetProperty(SkinInfo.ColorPicker.Preview,{current_hex},home)')
        except Exception:
            pass

    def _parse_color(self, hex_color: str) -> dict | None:
        """Parse AARRGGBB hex color into RGBA components."""
        try:
            alpha = int(hex_color[0:2], 16)
            red = int(hex_color[2:4], 16)
            green = int(hex_color[4:6], 16)
            blue = int(hex_color[6:8], 16)

            return {
                'alpha': {'hex': hex_color[0:2], 'int': alpha, 'pct': int((alpha / 255) * 100)},
                'red': {'hex': hex_color[2:4], 'int': red, 'pct': int((red / 255) * 100)},
                'green': {'hex': hex_color[4:6], 'int': green, 'pct': int((green / 255) * 100)},
                'blue': {'hex': hex_color[6:8], 'int': blue, 'pct': int((blue / 255) * 100)},
            }
        except (ValueError, IndexError):
            return None

    def _parse_and_set_sliders(self, hex_color: str) -> None:
        """Parse hex color and set slider positions."""
        components = self._parse_color(hex_color)
        if not components:
            log("General", f'Color Picker: Failed to parse color {hex_color}', xbmc.LOGERROR)
            return

        try:
            self.getControl(100).setPercent(components['red']['pct'])  # type: ignore[attr-defined]
            self.getControl(101).setPercent(components['green']['pct'])  # type: ignore[attr-defined]
            self.getControl(102).setPercent(components['blue']['pct'])  # type: ignore[attr-defined]
            self.getControl(103).setPercent(components['alpha']['pct'])  # type: ignore[attr-defined]
        except Exception as e:
            log("General", f'Color Picker: Failed to set sliders: {e}', xbmc.LOGERROR)

    def _merge_color(self) -> str:
        """Read slider values and merge into hex color."""
        try:
            red_pct = self.getControl(100).getPercent()  # type: ignore[attr-defined]
            green_pct = self.getControl(101).getPercent()  # type: ignore[attr-defined]
            blue_pct = self.getControl(102).getPercent()  # type: ignore[attr-defined]
            alpha_pct = self.getControl(103).getPercent()  # type: ignore[attr-defined]

            alpha = int((alpha_pct / 100) * 255)
            red = int((red_pct / 100) * 255)
            green = int((green_pct / 100) * 255)
            blue = int((blue_pct / 100) * 255)

            return f'{alpha:02X}{red:02X}{green:02X}{blue:02X}'
        except Exception:
            return self.current_color

    def _populate_palette(self) -> None:
        """Populate color palette panel with predefined colors."""
        try:
            palette_list = self.getControl(300)
            palette_list.reset()  # type: ignore[attr-defined]

            for color_info in self.palette_colors:
                item = xbmcgui.ListItem(color_info['name'])
                item.setProperty('color', color_info['value'])
                palette_list.addItem(item)  # type: ignore[attr-defined]
        except Exception as e:
            log("General", f'Color Picker: Failed to populate palette: {e}', xbmc.LOGERROR)

    def _enter_hex_code(self) -> None:
        """Prompt user to enter hex color code and update sliders/preview."""
        dialog = xbmcgui.Dialog()
        hex_input = dialog.input(
            'Enter Hex Color Code',
            type=xbmcgui.INPUT_ALPHANUM
        )

        if not hex_input:
            return

        hex_input = hex_input.strip().upper()

        if hex_input.startswith('#'):
            hex_input = hex_input[1:]

        if len(hex_input) == 6:
            hex_input = 'FF' + hex_input
        elif len(hex_input) != 8:
            dialog.notification(
                'Invalid Hex Code',
                'Please enter 6 (RRGGBB) or 8 (AARRGGBB) hex digits',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            return

        if not all(c in '0123456789ABCDEF' for c in hex_input):
            dialog.notification(
                'Invalid Hex Code',
                'Hex code must contain only 0-9 and A-F',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            return

        try:
            self._parse_and_set_sliders(hex_input)
            self._update_preview()
            log("General", f'Color Picker: Applied hex code {hex_input}', xbmc.LOGDEBUG)
        except Exception as e:
            log("General", f'Color Picker: Failed to apply hex code: {e}', xbmc.LOGERROR)
            dialog.notification(
                'Error',
                'Failed to apply hex code',
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )

    def onClick(self, controlId: int) -> None:
        if controlId == 200:
            self.result_color = self._merge_color()
            self.close()
        elif controlId == 201:
            self.result_color = None
            self.close()
        elif controlId == 202:
            self._parse_and_set_sliders(self.default_color)
            self._update_preview()
        elif controlId == 203:
            self._enter_hex_code()
        elif controlId == 300:
            self._select_palette_color()


def colorpicker(setting: str = '', default: str = '', colors: str = '',
                onback: str = '', **kwargs) -> None:
    """Open the RGBA color picker; onback runs condition::action blocks (separated by ||)
    when the user backs out."""
    setting = _resolve_infolabel(setting)
    default = _resolve_infolabel(default) or 'FFFFFFFF'
    colors = _resolve_infolabel(colors)
    onback = _resolve_infolabel(onback)

    if not setting:
        _show_error('colorpicker requires setting parameter')
        return

    current_color = xbmc.getInfoLabel(f"Skin.String({setting})") or default

    if len(current_color) != 8:
        _show_error(f'Invalid color format: {current_color} (expected AARRGGBB)')
        return

    if not colors:
        colors = xbmcvfs.translatePath('special://xbmc/system/colors.xml')

    palette_colors = []
    if os.path.exists(colors):
        try:
            tree = ET.parse(colors)
            root = tree.getroot()

            for color in root.findall('color'):
                name = color.get('name', '')
                value = color.text.strip() if color.text else ''
                if value and len(value) == 8:
                    palette_colors.append({'name': name, 'value': value})
        except Exception as e:
            log("General", f'Color Picker: Failed to parse colors.xml: {e}', xbmc.LOGERROR)
    else:
        log("General", f'Color Picker: colors.xml not found at {colors}', xbmc.LOGERROR)

    dialog = _ColorPickerDialog(
        'script.skin.info.service-ColorPicker.xml',
        ADDON.getAddonInfo('path'),
        'default',
        '1080i',
        current_color=current_color,
        default_color=default,
        palette_colors=palette_colors,
        onback=onback
    )
    dialog.doModal()

    if dialog.result_color:
        xbmc.executebuiltin(f'Skin.SetString({setting},{dialog.result_color})')

    monitor = xbmc.Monitor()
    while not monitor.abortRequested() and xbmc.getCondVisibility(
        'Window.IsVisible(script.skin.info.service-ColorPicker.xml)'
    ):
        monitor.waitForAbort(0.1)

    xbmc.executebuiltin('ClearProperty(SkinInfo.ColorPicker.CustomMode,home)')
    xbmc.executebuiltin('ClearProperty(SkinInfo.ColorPicker.Preview,home)')

    del dialog

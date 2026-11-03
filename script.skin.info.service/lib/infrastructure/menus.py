"""Select-dialog menus with nested navigation and a cancel row for the running task."""
from __future__ import annotations

from typing import Sequence, Tuple, Optional, Any, Callable
import time
import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import ADDON

RETURN_TO_MAIN_SENTINEL = object()


class MenuItem:
    """Menu row whose action is run, opened as a submenu or returned as the result."""

    def __init__(self, label: str, action, loop: bool = False):
        self.label = label
        self.action = action
        self.loop = loop


class Menu:
    """Select-dialog menu with nested submenus; Cancel in a submenu returns to the main menu."""

    def __init__(self, title: str, items: Sequence[MenuItem], is_main_menu: bool = False):
        self.title = title
        self.items = list(items)
        self.is_main_menu = is_main_menu
        self._last_selected_idx: Optional[int] = None

    def show(self, preselect: Optional[int] = None) -> Any:
        """Show the menu until an action returns a result; None on back or abort."""
        monitor = xbmc.Monitor()

        while not monitor.abortRequested():
            selected_idx = preselect if preselect is not None else self._last_selected_idx

            options: list[tuple[str, Optional[str]]] = [
                (item.label, str(idx)) for idx, item in enumerate(self.items)
            ]
            if not self.is_main_menu:
                options.append((xbmc.getLocalizedString(222), '__cancel__'))

            choice_str, cancelled = show_menu_with_cancel(self.title, options,
                                                          preselect=selected_idx)

            if cancelled:
                return None

            if choice_str == '__back__':
                return None

            if choice_str == '__cancel__':
                if self.is_main_menu:
                    return None
                else:
                    return RETURN_TO_MAIN_SENTINEL

            if choice_str is None:
                return None

            try:
                choice = int(choice_str)
            except (ValueError, TypeError):
                return None

            if choice < 0 or choice >= len(self.items):
                return None

            item = self.items[choice]

            self._last_selected_idx = choice

            if isinstance(item.action, Menu):
                result = item.action.show()
                if result is RETURN_TO_MAIN_SENTINEL:
                    if self.is_main_menu:
                        continue
                    else:
                        return RETURN_TO_MAIN_SENTINEL
                continue
            elif callable(item.action):
                result = item.action()
                if result is RETURN_TO_MAIN_SENTINEL:
                    if self.is_main_menu:
                        continue
                    else:
                        return RETURN_TO_MAIN_SENTINEL
                if item.loop:
                    continue
                return result
            else:
                return item.action

        return None


def run_with_mode_choice(operation_name: str, run: Callable[[bool], None]) -> Any:
    """Run after a foreground/background choice, claiming the task slot for the callback first."""
    def _start(use_background: bool) -> None:
        if task_manager.acquire_task_slot(operation_name, use_background):
            run(use_background)

    return Menu(ADDON.getLocalizedString(32410), [
        MenuItem(ADDON.getLocalizedString(32411), lambda: _start(False)),
        MenuItem(ADDON.getLocalizedString(32412), lambda: _start(True)),
    ]).show()


def show_menu_with_cancel(title: str, options: Sequence[Tuple[str, Optional[str]]],
                          preselect: Optional[int] = None) -> Tuple[Optional[str], bool]:
    """Show a select dialog topped by a cancel row for any running task; `'__back__'` on Back."""
    task_info = task_manager.get_task_info()

    display_options = []
    action_map = []

    if task_info:
        task_name = task_info['name']
        cancel_label = f"[B]{ADDON.getLocalizedString(32730).format(task_name)}[/B]"
        display_options.append(cancel_label)
        action_map.append('__cancel_task__')

    for label, action in options:
        display_options.append(label)
        action_map.append(action)

    adjusted_preselect = preselect
    if adjusted_preselect is not None and task_info:
        adjusted_preselect += 1

    choice = xbmcgui.Dialog().select(
        title, display_options,
        preselect=adjusted_preselect if adjusted_preselect is not None else -1)

    if choice == -1:
        return ('__back__', False)

    selected_action = action_map[choice]

    if selected_action == '__cancel_task__':
        task_manager.cancel_task()
        return (None, True)

    return (selected_action, False)


def _elapsed(seconds: float) -> str:
    """Format a span as `5m 3s`, or `3s` under a minute."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs}s" if minutes else f"{secs}s"


def confirm_cancel_running_task(new_task_name: str) -> bool:
    """Confirm cancelling the running task for a new one; True at once when none is running."""
    from lib.infrastructure.dialogs import show_yesno

    task_info = task_manager.get_task_info()
    if not task_info:
        return True

    now = time.time()
    current_task = task_info.get('name') or xbmc.getLocalizedString(13205)
    lines = [
        ADDON.getLocalizedString(32731).format(current_task),
        ADDON.getLocalizedString(32732).format(_elapsed(now - task_info.get('started_at', now))),
        ADDON.getLocalizedString(32733).format(
            _elapsed(now - task_info.get('last_progress', now))),
        "",
        ADDON.getLocalizedString(32734).format(new_task_name),
        "",
        ADDON.getLocalizedString(32735),
    ]

    message = "[CR]".join(lines)

    return show_yesno(
        ADDON.getLocalizedString(32571),
        message,
        nolabel=ADDON.getLocalizedString(32570),
        yeslabel=ADDON.getLocalizedString(32569)
    )

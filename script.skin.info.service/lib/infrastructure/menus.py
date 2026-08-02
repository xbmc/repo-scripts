"""Menu helper utilities with automatic navigation and task cancellation support."""
from __future__ import annotations

from typing import Sequence, Tuple, Optional, Any, Callable
import time
import xbmc
import xbmcgui

from lib.infrastructure import tasks as task_manager
from lib.kodi.client import ADDON

# Sentinel value to signal "return to main menu" vs "go back one level"
RETURN_TO_MAIN_SENTINEL = object()


class MenuItem:
    """Menu row with a label and an action.

    `action` can be a callable (executed), another `Menu` (shown as submenu),
    or a plain value (returned as-is). `loop=True` re-shows the parent menu
    after the action completes.
    """

    def __init__(self, label: str, action, loop: bool = False):
        self.label = label
        self.action = action
        self.loop = loop


class Menu:
    """Declarative menu with back/cancel/task-cancel handling and nested-submenu navigation.

    `is_main_menu=True` makes the top-level Cancel exit to Kodi instead of bubbling up.
    """

    def __init__(self, title: str, items: Sequence[MenuItem], is_main_menu: bool = False):
        self.title = title
        self.items = list(items)
        self.is_main_menu = is_main_menu
        self._last_selected_idx: Optional[int] = None

    def show(self, preselect: Optional[int] = None) -> Any:
        """Show menu and run navigation. Returns action result, or None on back/ESC/abort."""
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
    """Foreground/background picker, then claim the task slot and run in the chosen mode.

    `run` gets the chosen use_background bool and owns its own dialog and work; it must
    not claim the slot itself.
    """
    def _start(use_background: bool) -> None:
        if task_manager.acquire_task_slot(operation_name, use_background):
            run(use_background)

    return Menu(ADDON.getLocalizedString(32410), [
        MenuItem(ADDON.getLocalizedString(32411), lambda: _start(False)),
        MenuItem(ADDON.getLocalizedString(32412), lambda: _start(True)),
    ]).show()


def show_menu_with_cancel(title: str, options: Sequence[Tuple[str, Optional[str]]],
                          preselect: Optional[int] = None) -> Tuple[Optional[str], bool]:
    """Show a select dialog, injecting a "Cancel Current Task" row at the top if a task is running.

    Returns `(action, was_task_cancelled)`. `action` is `'__back__'` for ESC,
    the selected row's action string otherwise.
    """
    task_info = task_manager.get_task_info()

    display_options = []
    action_map = []

    if task_info:
        task_name = task_info['name']
        cancel_label = f"[B]Cancel Current Task: {task_name}[/B]"
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


def confirm_cancel_running_task(new_task_name: str) -> bool:
    """Prompt the user to cancel the running task in favour of `new_task_name`.

    Dialog shows the current task, its duration, last-activity age, and the intended new task.
    """
    from lib.infrastructure.dialogs import show_yesno

    task_info = task_manager.get_task_info()
    if not task_info:
        return True

    current_task = task_info.get('name', 'Unknown task')
    started_at = task_info.get('started_at', time.time())
    last_progress = task_info.get('last_progress', time.time())

    now = time.time()
    duration_seconds = int(now - started_at)
    progress_seconds = int(now - last_progress)

    duration_mins = duration_seconds // 60
    duration_secs = duration_seconds % 60

    progress_mins = progress_seconds // 60
    progress_secs = progress_seconds % 60

    if duration_mins > 0:
        duration_str = f"{duration_mins}m {duration_secs}s"
    else:
        duration_str = f"{duration_secs}s"

    if progress_mins > 0:
        progress_str = f"{progress_mins}m {progress_secs}s"
    else:
        progress_str = f"{progress_secs}s"

    lines = [
        f"[B]Currently Running:[/B] {current_task}",
        f"[B]Duration:[/B] {duration_str}",
        f"[B]Last Activity:[/B] {progress_str} ago",
        "",
        f"[B]New Task:[/B] {new_task_name}",
        "",
        "Cancelling will stop the current task safely.",
        "You can resume it later from the menu."
    ]

    message = "[CR]".join(lines)

    return show_yesno(
        ADDON.getLocalizedString(32571),
        message,
        nolabel=ADDON.getLocalizedString(32570),
        yeslabel=ADDON.getLocalizedString(32569)
    )

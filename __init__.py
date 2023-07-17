"""
Interaction with kb layout on windows
"""
import win32gui
import win32api
import win32process
import win32con

import contextlib
from itertools import cycle

from pynput import keyboard as kb
from pynput._util.win32 import KeyTranslator


CAPS_LOCK = kb.KeyCode(255)

WM_INPUTLANGCHANGEREQUEST = 0x0050  # win32api const


def get_foreground_window() -> int:
    return win32gui.GetForegroundWindow()


def get_foreground_window_thread_id() -> int:
    window_handle = get_foreground_window()
    return win32process.GetWindowThreadProcessId(window_handle)[0]


def get_foreground_window_kb_layout():
    """
    Returns foreground window kb layout as integer

    Examples:
    67699721 - 0x04090409 - english
    """
    thread_id = get_foreground_window_thread_id()
    layout_id = win32api.GetKeyboardLayout(thread_id)
    return layout_id


def change_foreground_window_kb_layout(layout_id: int = 0):
    """
    Change foreground window kb layout
    layout_id=0 : integer, containing a locale id, eg 68748313 - 0x04190419 - 0x419 - russian
    """
    window_handle = get_foreground_window()
    win32api.SendMessage(window_handle, WM_INPUTLANGCHANGEREQUEST, 0, layout_id)

layouts = cycle(tuple(l for l in win32api.GetKeyboardLayoutList()))

class CustomKeyTranslator(KeyTranslator):
    def __init__(self):
        super().__init__()

    @contextlib.contextmanager
    def _thread_input(self):
        yield get_foreground_window_thread_id()

kt = CustomKeyTranslator()

whdl = get_foreground_window()

buffer: list[kb.Key | kb.KeyCode | None] = []

controller = kb.Controller()

def on_activate(buffer):
    '''Defines what happens on press of the hotkey'''
    def wrapper():
        for _ in range(len(buffer)):
            controller.press(kb.Key.backspace)
        controller.type(''.join(reversed(buffer)))
        print('fdsf')
    return wrapper

hotkey = kb.HotKey(
    kb.HotKey.parse('<ctrl_l>+<shift>'), on_activate(buffer)
)

def on_press(key: kb.Key | kb.KeyCode | None):
    print(key)
    if key == kb.Key.esc:
        return False

    if key is None:
        return

    if buffer:
        current_whdl = get_foreground_window()
        if current_whdl != whdl:
            buffer.clear()
    print(buffer)
    hotkey = kb.HotKey(
        kb.HotKey.parse('<ctrl_l>+<shift>'), on_activate(buffer)
    )
    hotkey.press(key)

    if not isinstance(key, kb.KeyCode):
        return

    buffer.append(key)

    if key.vk == CAPS_LOCK.vk or key is kb.Key.caps_lock:
        next_layout = next(layouts)
        current_layour = get_foreground_window_kb_layout()
        if current_layour == next_layout:
            next_layout = next(layouts)
        change_foreground_window_kb_layout(next_layout)
        kt.update_layout()


with kb.Listener(on_press=hotkey.press) as listener:
    listener.join()

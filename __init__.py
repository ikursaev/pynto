"""
Interaction with kb layout on windows
"""
import win32gui
import win32api
import win32process

import time
import threading
import contextlib
from itertools import cycle

from pynput import keyboard as kb
from pynput._util.win32 import KeyTranslator


LOGI_CAPS_LOCK = kb.KeyCode(255)

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
    return win32api.GetKeyboardLayout(thread_id)


def change_foreground_window_kb_layout(layout_id: int = 0):
    """
    Change foreground window kb layout
    layout_id=0 : integer, containing a locale id, eg 68748313 - 0x04190419 - 0x419 - russian
    """
    window_handle = get_foreground_window()
    win32api.SendMessage(window_handle, WM_INPUTLANGCHANGEREQUEST, 0, layout_id)


layouts = cycle(l for l in win32api.GetKeyboardLayoutList())


class CustomKeyTranslator(KeyTranslator):
    def __init__(self):
        super().__init__()

    @contextlib.contextmanager
    def _thread_input(self):
        yield get_foreground_window_thread_id()


kt = CustomKeyTranslator()

whdl = get_foreground_window()

buffer: list[kb.KeyCode] = []
key_to_vk: dict = {}

controller = kb.Controller()

current_key = None


def change_layout():
    next_layout = next(layouts)
    current_layout = get_foreground_window_kb_layout()
    if current_layout == next_layout:
        next_layout = next(layouts)
    change_foreground_window_kb_layout(next_layout)
    kt.update_layout()


def on_ctrl_shift():
    '''Defines what happens on press of the hotkey'''
    global buffer
    change_layout()
    for key in buffer:
        controller.press(kb.Key.backspace)
        key_data = kt(key.vk, None)
        char = kt.char_from_scan(key_data["_scan"])
        controller.press(char)
        controller.release(char)


HOTKEY_CTRL_SHIFT = kb.HotKey(
    kb.HotKey.parse('<ctrl_l>+<shift>'), on_ctrl_shift,
)


def is_caps(key: kb.KeyCode):
    return key.vk == LOGI_CAPS_LOCK.vk or key is kb.Key.caps_lock


def on_press(key: kb.Key | kb.KeyCode | None):
    global current_key
    current_key = key

    if key is None:
        return

    HOTKEY_CTRL_SHIFT.press(key)

    if not isinstance(key, kb.KeyCode):
        return

    if is_caps(key):
        change_layout()
        return

    buffer.append(key)


def on_release(key: kb.Key | kb.KeyCode | None):
    if key is None:
        return

    HOTKEY_CTRL_SHIFT.release(key)


def is_esc(listener: kb.Listener):
    global current_key

    while True:
        if current_key and current_key is kb.Key.esc:
            listener.stop()
            break
        time.sleep(0.01)


with kb.Listener(on_press=on_press, on_release=on_release) as listener:

    th = threading.Thread(target=is_esc, args=(listener,))
    th.start()
    th.join()
    listener.join()


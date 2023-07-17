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

buffer: list[kb.KeyCode] = []

controller = kb.Controller()

def update_layout():
    next_layout = next(layouts)
    current_layout = get_foreground_window_kb_layout()
    if current_layout == next_layout:
        next_layout = next(layouts)
    change_foreground_window_kb_layout(next_layout)
    kt.update_layout()

def on_activate(buffer):
    '''Defines what happens on press of the hotkey'''
    def wrapper():
        for _ in buffer:
            controller.press(kb.Key.backspace)
        update_layout()
        controller.type(''.join(kt(key.vk, ...)['char'] for key in buffer))
    return wrapper

hotkey = kb.HotKey(
    kb.HotKey.parse('<ctrl_l>+<shift>'), on_activate(buffer)
)


current_key = None


def is_esc():
    global current_key
    if current_key and current_key == kb.Key.esc:
        return True
    return False


def check_window_is_switched():
    while True:
        if is_esc():
            return
        if buffer:
            current_whdl = get_foreground_window()
            if current_whdl != whdl:
                buffer.clear()
        time.sleep(0.1)


def on_press(key: kb.Key | kb.KeyCode | None):
    global current_key
    current_key = key
    if is_esc():
        return False

    if key is None:
        return

    if not isinstance(key, kb.KeyCode):
        return

    buffer.append(key)

    if key.vk == CAPS_LOCK.vk or key is kb.Key.caps_lock:
        update_layout()


    # print(kt(key.vk, ...)['char'])


def on_release(key: kb.Key):
    hotkey.press(key)


buffer_thread = threading.Thread(target=check_window_is_switched)
buffer_thread.start()
with kb.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
buffer_thread.join()


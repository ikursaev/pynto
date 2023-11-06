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

buffer: list[kb.KeyCode | kb.Key] = []

controller = kb.Controller()

current_key = None


def update_layout():
    next_layout = next(layouts)
    current_layout = get_foreground_window_kb_layout()
    if current_layout == next_layout:
        next_layout = next(layouts)
    change_foreground_window_kb_layout(next_layout)
    kt.update_layout()


def on_ctrl_shift(buffer):
    '''Defines what happens on press of the hotkey'''
    def wrapper():
        for _ in buffer:
            controller.press(kb.Key.backspace)
        update_layout()
        local_buffer = []
        for key in buffer:
            scan = getattr(key, '_scan', None)
            if scan is not None:
                char = kt.char_from_scan(scan)
                if char is not None:
                    k = kb.KeyCode.from_char(char=char, vk=key.vk)
                    controller.press(k)
                    local_buffer.append(k)
        buffer.clear()
        for k in local_buffer:
            buffer.append(k)
        print(buffer)
    return wrapper

HOTKEY_CTRL_SHIFT = kb.HotKey(
    kb.HotKey.parse('<ctrl_l>+<shift>'), on_ctrl_shift(buffer)
)


def check_window_has_switched():
    while True:
        if buffer:
            current_whdl = get_foreground_window()
            if current_whdl != whdl:
                buffer.clear()
        time.sleep(0.1)


def on_caps(key: kb.KeyCode):
    if key.vk == LOGI_CAPS_LOCK.vk or key is kb.Key.caps_lock:
        update_layout()


def on_press(key: kb.Key | kb.KeyCode | None):
    global current_key
    current_key = key

    if key is None:
        return

    HOTKEY_CTRL_SHIFT.press(key)

    if not isinstance(key, kb.KeyCode):
        return

    buffer.append(key)

    on_caps(key)


def on_release(key: kb.Key | kb.KeyCode | None):
    if key is None:
        return

    HOTKEY_CTRL_SHIFT.release(key)


# def win32_event_filter(msg, data):
#     print(msg, type(msg), type(data), type(data.vkCode), data.vkCode)
#     if msg == 256 and data.vkCode == 255:
#         print('caps')
#         # Suppress x
#         # listener.suppress_event()
#     if (msg == 256 and HOTKEY_CTRL_SHIFT._state == HOTKEY_CTRL_SHIFT._keys):
#         print('ctr')
#         # listener.suppress_event()


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


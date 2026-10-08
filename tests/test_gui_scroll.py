from types import SimpleNamespace
from unittest.mock import Mock
import sys

import pytest

from anytool.grounding.backends.gui.transport.actions import build_pyautogui_command


@pytest.mark.parametrize("dx,dy", [(4, 0), (-4, 0), (4, -2), (0, 2)])
def test_scroll_action_executes_both_requested_axes(dx, dy, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    gui = SimpleNamespace(scroll=Mock(), hscroll=Mock(), failSafeCheck=Mock())
    command = build_pyautogui_command("SCROLL", {"dx": dx, "dy": dy})
    exec(command, {"pyautogui": gui})
    if dx:
        gui.hscroll.assert_called_once_with(dx)
    else:
        gui.hscroll.assert_not_called()
    gui.scroll.assert_called_once_with(dy)


@pytest.mark.parametrize("dx,dy", [(4, 0), (-4, 0), (4, -2), (0, 2)])
def test_windows_scroll_uses_horizontal_wheel_event(dx, dy, monkeypatch):
    mouse_event = Mock()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "ctypes", SimpleNamespace(
        windll=SimpleNamespace(user32=SimpleNamespace(mouse_event=mouse_event)),
    ))
    gui = SimpleNamespace(scroll=Mock(), hscroll=Mock(), failSafeCheck=Mock())
    command = build_pyautogui_command("SCROLL", {"dx": dx, "dy": dy})
    exec(command, {"pyautogui": gui})
    gui.hscroll.assert_not_called()
    if dx:
        gui.failSafeCheck.assert_called_once_with()
        mouse_event.assert_called_once_with(0x1000, 0, 0, dx * 120, 0)
    else:
        mouse_event.assert_not_called()
    gui.scroll.assert_called_once_with(dy)

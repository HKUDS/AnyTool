from types import SimpleNamespace

import pytest

from anytool.grounding.backends.gui.transport.connector import GUIConnector
from anytool.grounding.backends.gui.transport.local_connector import LocalGUIConnector


@pytest.mark.parametrize("connector", [GUIConnector, LocalGUIConnector])
@pytest.mark.parametrize("text", ["a'<b", 'a"<b', "a\\<b", "a\n<b", "中文<文本", "<<", "plain"])
@pytest.mark.parametrize("interval", [False, True])
def test_less_than_workaround_preserves_literal_text_and_interval(connector, text, interval):
    typed = []
    intervals = []

    def typewrite(value, **kwargs):
        typed.append(value)
        intervals.append(kwargs.get("interval"))

    def hotkey(*keys):
        assert keys == ("shift", ",")
        typed.append("<")

    fake = SimpleNamespace(typewrite=typewrite, hotkey=hotkey)
    suffix = ", interval=0.01" if interval else ""
    command = f"pyautogui.typewrite({text!r}{suffix})"
    fixed = connector._fix_pyautogui_less_than_bug(command)
    exec(compile(fixed, "<test>", "exec"), {"pyautogui": fake})
    assert "".join(typed) == text
    assert intervals == [0.01 if interval else None] * len(intervals)
    assert all("<" not in part for part in typed if part != "<")
    if "<" in text:
        assert len(typed) > 1 or text == "<"


@pytest.mark.parametrize("connector", [GUIConnector, LocalGUIConnector])
def test_workaround_does_not_rewrite_command_text_inside_a_string(connector):
    command = '''print("pyautogui.typewrite('a<b')")'''
    assert connector._fix_pyautogui_less_than_bug(command) == command


@pytest.mark.parametrize("connector", [GUIConnector, LocalGUIConnector])
def test_escaped_less_than_press_is_transformed(connector):
    calls = []
    fake = SimpleNamespace(hotkey=lambda *keys: calls.append(keys))
    fixed = connector._fix_pyautogui_less_than_bug("pyautogui.press('\\u003c')")
    exec(fixed, {"pyautogui": fake})
    assert calls == [("shift", ",")]

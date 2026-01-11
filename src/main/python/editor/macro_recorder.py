# SPDX-License-Identifier: GPL-2.0-or-later
import sys

from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QWidget, QLabel, QVBoxLayout, QGroupBox, QTabWidget

from editor.basic_editor import BasicEditor
from macro.macro_action import ActionText, ActionTap, ActionDown, ActionUp
from macro.macro_action_ui import ui_action
from macro.macro_key import KeyString, KeyDown, KeyUp, KeyTap
from macro.macro_optimizer import macro_optimize
from macro.macro_tab import MacroTab
from unlocker import Unlocker
from util import tr
from vial_device import VialKeyboard
from tabbed_keycodes import TabbedKeycodes


class MacroRecorder(BasicEditor):

    def __init__(self):
        super().__init__()

        self.keyboard = None
        self.suppress_change = False

        self.keystrokes = []
        self.macro_tabs = []
        self.macro_tab_w = []

        self.recorder = None
        self.selected_key_widget = None  # Track currently selected key widget

        if sys.platform.startswith("linux"):
            from macro.macro_recorder_linux import LinuxRecorder

            self.recorder = LinuxRecorder()
        elif sys.platform.startswith("win"):
            from macro.macro_recorder_windows import WindowsRecorder

            self.recorder = WindowsRecorder()

        if self.recorder:
            self.recorder.keystroke.connect(self.on_keystroke)
            self.recorder.stopped.connect(self.on_stop)
        self.recording = False

        self.recording_tab = None
        self.recording_append = False

        # Header section with title and description
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)

        title_label = QLabel("<b>Macro Editor</b>")
        title_label.setStyleSheet("font-size: 14pt;")
        header_layout.addWidget(title_label)

        desc = QLabel("Configure macros to send sequences of keystrokes with a single keypress.\n"
                      "Click a key slot below, then select a keycode from the panel at the bottom.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; font-size: 9pt;")
        header_layout.addWidget(desc)

        self.addLayout(header_layout)

        # Macro tabs in a group box with instructions
        macro_group = QGroupBox("Macro Slots")
        macro_layout = QVBoxLayout()

        instruction_layout = QHBoxLayout()
        instruction_label = QLabel("← Click a key to select, then choose from keycodes below")
        instruction_label.setStyleSheet("color: gray; font-style: italic;")
        instruction_layout.addWidget(instruction_label)
        instruction_layout.addStretch()
        macro_layout.addLayout(instruction_layout)

        self.tabs = QTabWidget()
        macro_layout.addWidget(self.tabs)

        macro_group.setLayout(macro_layout)
        self.addWidget(macro_group)

        self.lbl_memory = QLabel()

        buttons = QHBoxLayout()
        buttons.addWidget(self.lbl_memory)
        buttons.addStretch()
        self.btn_save = QPushButton(tr("MacroRecorder", "Save"))
        self.btn_save.setMinimumHeight(30)
        self.btn_save.setMaximumHeight(30)
        self.btn_save.setMinimumWidth(80)
        self.btn_save.setStyleSheet("QPushButton { border-radius: 5px; }")
        self.btn_save.clicked.connect(self.on_save)
        btn_revert = QPushButton(tr("MacroRecorder", "Revert"))
        btn_revert.setMinimumHeight(30)
        btn_revert.setMaximumHeight(30)
        btn_revert.setMinimumWidth(80)
        btn_revert.setStyleSheet("QPushButton { border-radius: 5px; }")
        btn_revert.clicked.connect(self.on_revert)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(btn_revert)

        self.addLayout(buttons)

        # TabbedKeycodes always visible at the bottom
        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_selected)
        self.addWidget(self.tabbed_keycodes)

    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return
        self.keyboard = self.device.keyboard

        for x in range(self.keyboard.macro_count - len(self.macro_tab_w)):
            tab = MacroTab(self, self.recorder is not None)
            tab.changed.connect(self.on_change)
            tab.record.connect(self.on_record)
            tab.record_stop.connect(self.on_tab_stop)
            tab.key_selected.connect(self.on_key_widget_selected)
            self.macro_tabs.append(tab)
            w = QWidget()
            w.setLayout(tab)
            self.macro_tab_w.append(w)

        # only show the number of macro editors that keyboard supports
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        for x, w in enumerate(self.macro_tab_w[:self.keyboard.macro_count]):
            self.tabs.addTab(w, "")

        # deserialize macros that came from keyboard
        self.deserialize(self.keyboard.macro)

        self.on_change()

    def on_key_widget_selected(self, widget):
        """Handle when a key widget is selected in a macro tab"""
        # Deselect the previously selected widget
        if self.selected_key_widget is not None and self.selected_key_widget != widget:
            self.selected_key_widget.set_selected(False)

        # Select the new widget
        self.selected_key_widget = widget
        widget.set_selected(True)

    def on_keycode_selected(self, keycode):
        """Handle keycode selection from TabbedKeycodes"""
        if self.selected_key_widget is not None:
            self.selected_key_widget.set_keycode(keycode)
            # Keep the widget selected for easy consecutive key assignments
            # User can click another key to switch selection

    def update_tab_titles(self):
        macros = self.keyboard.macro.split(b"\x00")
        for x, w in enumerate(self.macro_tab_w[:self.keyboard.macro_count]):
            title = "M{}".format(x)
            if macros[x] != self.keyboard.macro_serialize(self.macro_tabs[x].actions()):
                title += "*"
            self.tabs.setTabText(x, title)

    def on_record(self, tab, append):
        self.recording_tab = tab
        self.recording_append = append

        self.recording_tab.pre_record()

        for x, w in enumerate(self.macro_tabs[:self.keyboard.macro_count]):
            if tab != w:
                self.tabs.tabBar().setTabEnabled(x, False)

        self.recording = True
        self.keystrokes = []
        self.recorder.start()

    def on_tab_stop(self):
        self.recorder.stop()

    def on_stop(self):
        for x in range(self.keyboard.macro_count):
            self.tabs.tabBar().setTabEnabled(x, True)

        if not self.recording_append:
            self.recording_tab.clear()

        self.recording_tab.post_record()

        self.keystrokes = macro_optimize(self.keystrokes)
        actions = []
        for k in self.keystrokes:
            if isinstance(k, KeyString):
                actions.append(ActionText(k.string))
            else:
                cls = {KeyDown: ActionDown, KeyUp: ActionUp, KeyTap: ActionTap}[type(k)]
                actions.append(cls([k.keycode.qmk_id]))

        # merge: i.e. replace multiple instances of KeyDown with a single multi-key ActionDown, etc
        actions = self.keyboard.macro_deserialize(self.keyboard.macro_serialize(actions))
        for act in actions:
            self.recording_tab.add_action(ui_action[type(act)](self.recording_tab.container, act))

    def on_keystroke(self, keystroke):
        self.keystrokes.append(keystroke)

    def on_change(self):
        if self.suppress_change:
            return

        data = self.serialize()
        memory = len(data)
        self.lbl_memory.setText("Memory used by macros: {}/{}".format(memory, self.keyboard.macro_memory))
        self.btn_save.setEnabled(data != self.keyboard.macro and memory <= self.keyboard.macro_memory)
        self.lbl_memory.setStyleSheet("QLabel { color: red; }" if memory > self.keyboard.macro_memory else "")
        self.update_tab_titles()

    def serialize(self):
        macros = []
        for x, t in enumerate(self.macro_tabs[:self.keyboard.macro_count]):
            macros.append(t.actions())
        return self.keyboard.macros_serialize(macros)

    def deserialize(self, data):
        self.suppress_change = True
        macros = self.keyboard.macros_deserialize(data)
        for macro, tab in zip(macros, self.macro_tabs[:self.keyboard.macro_count]):
            tab.clear()
            for act in macro:
                tab.add_action(ui_action[type(act)](tab.container, act))
        self.suppress_change = False

    def on_revert(self):
        self.keyboard.reload_macros()
        self.deserialize(self.keyboard.macro)
        self.on_change()

    def on_save(self):
        Unlocker.unlock(self.device.keyboard)
        self.keyboard.set_macro(self.serialize())
        self.on_change()

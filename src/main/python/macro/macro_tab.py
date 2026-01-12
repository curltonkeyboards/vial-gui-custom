# SPDX-License-Identifier: GPL-2.0-or-later
import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QGridLayout, QHBoxLayout, QToolButton, QVBoxLayout, \
    QWidget, QMenu, QScrollArea, QFrame, QLabel, QGroupBox

from keycodes.keycodes import Keycode
from macro.macro_action import ActionTap
from macro.macro_action_ui import ActionTextUI, ActionTapUI, ui_action, tag_to_action
from macro.macro_line import MacroLine
from protocol.constants import VIAL_PROTOCOL_EXT_MACROS
from tabbed_keycodes import keycode_filter_masked
from util import tr, make_scrollable
from textbox_window import TextboxWindow
from constants import KEY_SIZE_RATIO


class MacroTab(QVBoxLayout):

    changed = pyqtSignal()
    record = pyqtSignal(object, bool)
    record_stop = pyqtSignal()
    key_selected = pyqtSignal(object)  # Emits the selected key widget
    widget_deleted = pyqtSignal(object)  # Emits when a widget is about to be deleted

    def __init__(self, parent, enable_recorder, macro_index=0):
        super().__init__()

        self.parent = parent
        self.macro_index = macro_index
        self.lines = []

        self.setSpacing(12)
        self.setContentsMargins(16, 16, 16, 16)

        # Header with macro name
        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"<b>M{macro_index}</b>")
        self.title_label.setStyleSheet("font-size: 14pt;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.addLayout(header_layout)

        # Description
        desc = QLabel("Configure keystrokes to send when this macro is triggered.\n"
                      "Assign this macro to a key in your keymap using the Macro tab in keycodes.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; font-size: 9pt;")
        self.addWidget(desc)

        # Actions group
        actions_group = QGroupBox("Keystrokes")
        actions_layout = QVBoxLayout()

        # Container for macro lines
        self.container = QGridLayout()

        # Instruction label (to the right of keys)
        self.instruction_label = QLabel("← Click a key to select, then choose from keycodes below")
        self.instruction_label.setStyleSheet("color: gray; font-style: italic;")

        # Top button row with + button
        self.top_btn_layout = QHBoxLayout()
        self.btn_add_key = QToolButton()
        self.btn_add_key.setText("+")
        self.btn_add_key.setFixedWidth(int(self.btn_add_key.fontMetrics().height() * KEY_SIZE_RATIO))
        self.btn_add_key.setFixedHeight(int(self.btn_add_key.fontMetrics().height() * KEY_SIZE_RATIO))
        self.btn_add_key.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_add_key.clicked.connect(self.on_add_tap_key)
        self.top_btn_layout.addWidget(self.btn_add_key)
        self.top_btn_layout.addWidget(self.instruction_label)
        self.top_btn_layout.addStretch()

        actions_layout.addLayout(self.top_btn_layout)
        actions_layout.addLayout(self.container)
        actions_layout.addStretch()

        actions_group.setLayout(actions_layout)

        # Scroll area for actions
        scroll = QScrollArea()
        scroll.setWidget(actions_group)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.addWidget(scroll)

        # Bottom buttons
        menu_record = QMenu()
        menu_record.addAction(tr("MacroRecorder", "Append to current"))\
            .triggered.connect(lambda: self.record.emit(self, True))
        menu_record.addAction(tr("MacroRecorder", "Replace everything"))\
            .triggered.connect(lambda: self.record.emit(self, False))

        self.btn_record = QPushButton(tr("MacroRecorder", "Record macro"))
        self.btn_record.setMinimumHeight(30)
        self.btn_record.setMaximumHeight(30)
        self.btn_record.setStyleSheet("QPushButton { border-radius: 5px; }")
        self.btn_record.setMenu(menu_record)
        if not enable_recorder:
            self.btn_record.hide()

        self.btn_record_stop = QPushButton(tr("MacroRecorder", "Stop recording"))
        self.btn_record_stop.setMinimumHeight(30)
        self.btn_record_stop.setMaximumHeight(30)
        self.btn_record_stop.setStyleSheet("QPushButton { border-radius: 5px; }")
        self.btn_record_stop.clicked.connect(lambda: self.record_stop.emit())
        self.btn_record_stop.hide()

        self.btn_add = QToolButton()
        self.btn_add.setText(tr("MacroRecorder", "Add action"))
        self.btn_add.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_add.setMinimumHeight(30)
        self.btn_add.setMaximumHeight(30)
        self.btn_add.setStyleSheet("QToolButton { border-radius: 5px; }")
        self.btn_add.clicked.connect(self.on_add)

        self.btn_text_window = QToolButton()
        self.btn_text_window.setText(tr("MacroRecorder", "Open Text Editor..."))
        self.btn_text_window.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_text_window.setMinimumHeight(30)
        self.btn_text_window.setMaximumHeight(30)
        self.btn_text_window.setStyleSheet("QToolButton { border-radius: 5px; }")
        self.btn_text_window.clicked.connect(self.on_text_window)

        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(self.btn_text_window)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.btn_add)
        layout_buttons.addWidget(self.btn_record)
        layout_buttons.addWidget(self.btn_record_stop)

        self.addLayout(layout_buttons)

        self.dlg_textbox = None

    def set_macro_index(self, index):
        """Update the macro index shown in the header"""
        self.macro_index = index
        self.title_label.setText(f"<b>M{index}</b>")

    def add_action(self, act):
        if self.parent.keyboard.vial_protocol < VIAL_PROTOCOL_EXT_MACROS:
            act.set_keycode_filter(keycode_filter_masked)
        line = MacroLine(self, act)
        line.changed.connect(self.on_change)
        line.key_selected.connect(self.on_key_selected)
        self.lines.append(line)
        line.insert(len(self.lines) - 1)
        self.changed.emit()

    def on_key_selected(self, widget):
        """Bubble up key selection to parent MacroRecorder"""
        self.key_selected.emit(widget)

    def on_add(self):
        self.add_action(ActionTextUI(self.container))

    def on_add_tap_key(self):
        """Add a new tap action with KC_NO"""
        self.add_action(ActionTapUI(self.container, ActionTap(["KC_NO"])))

    def on_remove(self, obj):
        # Emit widget_deleted for all key widgets in this line before deletion
        if hasattr(obj.action, 'widgets'):
            for widget in obj.action.widgets:
                self.widget_deleted.emit(widget)

        for line in self.lines:
            if line == obj:
                line.remove()
                line.delete()
        self.lines.remove(obj)
        for line in self.lines:
            line.remove()
        for x, line in enumerate(self.lines):
            line.insert(x)
        self.changed.emit()

    def clear(self):
        for line in self.lines[:]:
            self.on_remove(line)

    def on_move(self, obj, offset):
        if offset == 0:
            return
        index = self.lines.index(obj)
        if index + offset < 0 or index + offset >= len(self.lines):
            return
        other = self.lines.index(self.lines[index + offset])
        self.lines[index].remove()
        self.lines[other].remove()
        self.lines[index], self.lines[other] = self.lines[other], self.lines[index]
        self.lines[index].insert(index)
        self.lines[other].insert(other)
        self.changed.emit()

    def on_text_window(self):
        # serialize all actions in this tab to a json
        macro_text = json.dumps([act.save() for act in self.actions()])

        self.dlg_textbox = TextboxWindow(macro_text, "vim", "Vial macro")
        self.dlg_textbox.setModal(True)
        self.dlg_textbox.finished.connect(self.on_dlg_finished)
        self.dlg_textbox.show()

    def on_dlg_finished(self, res):
        if res > 0:
            macro_text = self.dlg_textbox.getText()
            if len(macro_text) < 6:
                macro_text = "[]"
            macro_load = json.loads(macro_text)

            # ensure a list exists
            if not isinstance(macro_load, list):
                return

            # clear the actions from this tab
            self.clear()

            # add each action from the json to this tab
            for act in macro_load:
                if act[0] in tag_to_action:
                    obj = tag_to_action[act[0]]()
                    actionUI = ui_action[type(obj)]
                    obj.restore(act)
                    self.add_action(actionUI(self.container, obj))

    def on_change(self):
        self.changed.emit()

    def pre_record(self):
        self.btn_record.hide()
        self.btn_add.hide()
        self.btn_add_key.hide()
        self.btn_text_window.hide()
        self.btn_record_stop.show()

    def post_record(self):
        self.btn_record.show()
        self.btn_add.show()
        self.btn_add_key.show()
        self.btn_text_window.show()
        self.btn_record_stop.hide()

    def actions(self):
        return [line.action.act for line in self.lines]

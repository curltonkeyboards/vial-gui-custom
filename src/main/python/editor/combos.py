# SPDX-License-Identifier: GPL-2.0-or-later
import sip

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import QTabWidget, QWidget, QSizePolicy, QGridLayout, QVBoxLayout, QLabel, QScrollArea, \
    QHBoxLayout, QPushButton, QGroupBox

from protocol.constants import VIAL_PROTOCOL_DYNAMIC
from widgets.key_widget import KeyWidget
from tabbed_keycodes import TabbedKeycodes
from util import tr
from vial_device import VialKeyboard
from editor.basic_editor import BasicEditor


class ComboKeyWidget(KeyWidget):
    """Custom KeyWidget that doesn't open tray - parent will handle keycode selection"""

    selected = pyqtSignal(object)  # Emits self when clicked

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_selected = False

    def mousePressEvent(self, ev):
        # Set active_key to the actual widget so KeyboardWidget draws the highlight
        if len(self.widgets) > 0:
            self.active_key = self.widgets[0]
            self.active_mask = False

        # Emit that we're selected (don't call parent which opens tray)
        self.selected.emit(self)
        self.update()
        ev.accept()

    def mouseReleaseEvent(self, ev):
        ev.accept()

    def set_selected(self, selected):
        """Visual feedback for selection"""
        self.is_selected = selected
        if selected:
            if len(self.widgets) > 0:
                self.active_key = self.widgets[0]
                self.active_mask = False
        else:
            self.active_key = None
        self.update()


class ComboEntryUI(QObject):

    key_changed = pyqtSignal()
    key_selected = pyqtSignal(object)  # Emits when a key widget is selected

    def __init__(self, idx):
        super().__init__()

        self.idx = idx
        self.kc_inputs = []
        self.key_widgets = []

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header with combo name
        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"<b>Combo {idx + 1}</b>")
        self.title_label.setStyleSheet("font-size: 14pt;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Description
        desc = QLabel("Define a key combination that triggers an output key.\n"
                      "Press multiple keys simultaneously to activate the combo.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; font-size: 9pt;")
        main_layout.addWidget(desc)

        # Keys group
        keys_group = QGroupBox("Trigger Keys + Output")
        keys_layout = QVBoxLayout()

        # Instruction text
        instruction = QLabel("← Click a key to select, then choose from keycodes below")
        instruction.setStyleSheet("color: gray; font-style: italic;")
        keys_layout.addWidget(instruction)

        # Container for key widgets
        self.container = QGridLayout()
        self.populate_container()
        keys_layout.addLayout(self.container)

        keys_layout.addStretch()
        keys_group.setLayout(keys_layout)

        # Scroll area for keys group
        scroll = QScrollArea()
        scroll.setWidget(keys_group)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        main_layout.addWidget(scroll)

        # Create widget for the layout
        self.w2 = QWidget()
        self.w2.setLayout(main_layout)

    def populate_container(self):
        # Input keys (Key 1-4)
        for x in range(4):
            kc_widget = ComboKeyWidget()
            kc_widget.changed.connect(self.on_key_changed)
            kc_widget.selected.connect(self._on_key_selected)
            self.container.addWidget(QLabel("Key {}".format(x + 1)), x, 0)
            self.container.addWidget(kc_widget, x, 1)
            self.kc_inputs.append(kc_widget)
            self.key_widgets.append(kc_widget)

        # Output key
        self.kc_output = ComboKeyWidget()
        self.kc_output.changed.connect(self.on_key_changed)
        self.kc_output.selected.connect(self._on_key_selected)
        self.container.addWidget(QLabel("Output key"), 4, 0)
        self.container.addWidget(self.kc_output, 4, 1)
        self.key_widgets.append(self.kc_output)

    def _on_key_selected(self, widget):
        """Bubble up key selection"""
        self.key_selected.emit(widget)

    def widget(self):
        return self.w2

    def load(self, data):
        objs = self.kc_inputs + [self.kc_output]
        for o in objs:
            o.blockSignals(True)

        for x in range(4):
            self.kc_inputs[x].set_keycode(data[x])
        self.kc_output.set_keycode(data[4])

        for o in objs:
            o.blockSignals(False)

    def save(self):
        return (
            self.kc_inputs[0].keycode,
            self.kc_inputs[1].keycode,
            self.kc_inputs[2].keycode,
            self.kc_inputs[3].keycode,
            self.kc_output.keycode
        )

    def on_key_changed(self):
        self.key_changed.emit()


class Combos(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None
        self.selected_key_widget = None

        self.combo_entries = []
        self.combo_entries_available = []
        self.tabs = QTabWidget()
        for x in range(128):
            entry = ComboEntryUI(x)
            entry.key_changed.connect(self.on_key_changed)
            entry.key_selected.connect(self.on_key_widget_selected)
            self.combo_entries_available.append(entry)

        self.addWidget(self.tabs)

        # Save/Revert buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton(tr("Combos", "Save"))
        self.btn_save.setMinimumHeight(30)
        self.btn_save.setMaximumHeight(30)
        self.btn_save.setMinimumWidth(80)
        self.btn_save.setStyleSheet("QPushButton { border-radius: 5px; }")
        self.btn_save.clicked.connect(self.on_save)
        btn_revert = QPushButton(tr("Combos", "Revert"))
        btn_revert.setMinimumHeight(30)
        btn_revert.setMaximumHeight(30)
        btn_revert.setMinimumWidth(80)
        btn_revert.setStyleSheet("QPushButton { border-radius: 5px; }")
        btn_revert.clicked.connect(self.on_revert)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(btn_revert)
        self.addLayout(buttons)

        # TabbedKeycodes always visible at bottom
        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_selected)
        self.addWidget(self.tabbed_keycodes)

    def on_key_widget_selected(self, widget):
        """Handle when a key widget is selected"""
        if self.selected_key_widget is not None and self.selected_key_widget != widget:
            try:
                if not sip.isdeleted(self.selected_key_widget):
                    self.selected_key_widget.set_selected(False)
            except RuntimeError:
                pass
            self.selected_key_widget = None

        self.selected_key_widget = widget
        widget.set_selected(True)

    def on_keycode_selected(self, keycode):
        """Handle keycode selection from TabbedKeycodes"""
        if self.selected_key_widget is not None:
            try:
                if not sip.isdeleted(self.selected_key_widget):
                    self.selected_key_widget.set_keycode(keycode)
            except RuntimeError:
                self.selected_key_widget = None

    def rebuild_ui(self):
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        self.combo_entries = self.combo_entries_available[:self.keyboard.combo_count]
        for x, e in enumerate(self.combo_entries):
            self.tabs.addTab(e.widget(), str(x + 1))
        self.reload_ui()

    def reload_ui(self):
        for x, e in enumerate(self.combo_entries):
            e.load(self.keyboard.combo_get(x))
        self.update_modified_state()

    def on_save(self):
        for x, e in enumerate(self.combo_entries):
            self.keyboard.combo_set(x, self.combo_entries[x].save())
        self.update_modified_state()

    def on_revert(self):
        self.keyboard.reload_dynamic()
        self.reload_ui()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.rebuild_ui()

    def valid(self):
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_DYNAMIC
                and self.device.keyboard.combo_count > 0)

    def on_key_changed(self):
        self.on_save()

    def update_modified_state(self):
        """ Update indication of which tabs are modified, and keep Save button enabled only if it's needed """
        has_changes = False
        for x, e in enumerate(self.combo_entries):
            if self.combo_entries[x].save() != self.keyboard.combo_get(x):
                has_changes = True
                self.tabs.setTabText(x, "{}*".format(x + 1))
            else:
                self.tabs.setTabText(x, str(x + 1))
        self.btn_save.setEnabled(has_changes)

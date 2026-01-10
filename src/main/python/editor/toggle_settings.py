# SPDX-License-Identifier: GPL-2.0-or-later
"""
Toggle Keys Settings Editor

Allows configuration of toggle key slots (TGL_00 - TGL_99).
Users configure slots with target keycodes and then assign TGL_XX keycodes to keys via the keymap editor.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QGroupBox, QMessageBox, QFrame,
                              QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal

from editor.basic_editor import BasicEditor
from protocol.toggle_protocol import (ProtocolToggle, ToggleSlot,
                                       TOGGLE_NUM_SLOTS, TOGGLE_KEY_BASE,
                                       slot_to_toggle_keycode)
from keycodes.keycodes import Keycode
from widgets.key_widget import KeyWidget
from tabbed_keycodes import TabbedKeycodes, FilteredTabbedKeycodes, keycode_filter_any, keycode_filter_masked
from tabbed_keycodes import KeyboardTab, MusicTab, GamingTab, MacroTab, LightingTab, LightingTab2, MIDITab, SimpleTab
from keycodes.keycodes import (KEYCODES_MACRO_BASE, KEYCODES_MACRO, KEYCODES_TAP_DANCE, KEYCODES_BACKLIGHT,
                               KEYCODES_RGBSAVE, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR,
                               KEYCODES_RGB_KC_CUSTOM2, KEYCODES_CLEAR, KEYCODES_GAMING,
                               KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_OSL)
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard


class FilteredTabbedKeycodesNoLayers(QTabWidget):
    """Custom FilteredTabbedKeycodes without LayerTab to avoid overlay issues"""

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self, parent=None, keycode_filter=keycode_filter_any):
        super().__init__(parent)

        self.keycode_filter = keycode_filter

        # Create tabs WITHOUT LayerTab
        self.tabs = [
            KeyboardTab(self),
            MusicTab(self),
            GamingTab(self, "Gaming", KEYCODES_GAMING),
            MacroTab(self, "Macro", KEYCODES_MACRO_BASE, KEYCODES_MACRO, KEYCODES_TAP_DANCE),
            LightingTab2(self, "Layers", KEYCODES_LAYERS_DF, KEYCODES_LAYERS_MO, KEYCODES_LAYERS_OSL),
            LightingTab(self, "Lighting", KEYCODES_BACKLIGHT, KEYCODES_RGBSAVE, KEYCODES_RGB_KC_CUSTOM, KEYCODES_RGB_KC_COLOR, KEYCODES_RGB_KC_CUSTOM2),
            MIDITab(self),
            SimpleTab(self, " ", KEYCODES_CLEAR),
        ]

        for tab in self.tabs:
            tab.keycode_changed.connect(self.on_keycode_changed)

        self.recreate_keycode_buttons()
        KeycodeDisplay.notify_keymap_override(self)

    def on_keycode_changed(self, code):
        """Handle keycode changes from tabs"""
        if code == "Any":
            self.anykey.emit()
        else:
            self.keycode_changed.emit(Keycode.normalize(code))

    def recreate_keycode_buttons(self):
        """Recreate all keycode buttons based on filter"""
        prev_tab = self.tabText(self.currentIndex()) if self.currentIndex() >= 0 else ""
        while self.count() > 0:
            self.removeTab(0)

        for tab in self.tabs:
            tab.recreate_buttons(self.keycode_filter)
            if tab.has_buttons():
                self.addTab(tab, tr("TabbedKeycodes", tab.label))
                if tab.label == prev_tab:
                    self.setCurrentIndex(self.count() - 1)

    def on_keymap_override(self):
        """Update button labels when keymap overrides change"""
        for tab in self.tabs:
            tab.relabel_buttons()

    def set_keyboard(self, keyboard):
        """Set keyboard reference for tabs that need it"""
        for tab in self.tabs:
            if hasattr(tab, 'keyboard'):
                tab.keyboard = keyboard


class TabbedKeycodesNoLayers(QWidget):
    """Custom TabbedKeycodes without LayerTab for Toggle settings"""

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.target = None
        self.is_tray = False

        self.layout = QVBoxLayout()

        # Use our custom FilteredTabbedKeycodes without layers
        self.all_keycodes = FilteredTabbedKeycodesNoLayers()
        self.basic_keycodes = FilteredTabbedKeycodesNoLayers(keycode_filter=keycode_filter_masked)
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.keycode_changed.connect(self.keycode_changed)
            opt.anykey.connect(self.anykey)
            self.layout.addWidget(opt)

        self.setLayout(self.layout)
        self.set_keycode_filter(keycode_filter_any)

    def set_keycode_filter(self, keycode_filter):
        """Show/hide filtered keycode widgets"""
        if keycode_filter == keycode_filter_masked:
            self.all_keycodes.hide()
            self.basic_keycodes.show()
        else:
            self.all_keycodes.show()
            self.basic_keycodes.hide()

    def set_keyboard(self, keyboard):
        """Set keyboard reference for all tab widgets"""
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.set_keyboard(keyboard)


class ToggleKeyWidget(KeyWidget):
    """Custom KeyWidget that doesn't open tray - parent will handle keycode selection"""

    selected = pyqtSignal(object)  # Emits self when clicked

    def __init__(self):
        super().__init__()
        self.is_selected = False

    def mousePressEvent(self, ev):
        # Set active_key to the actual widget so KeyboardWidget draws the highlight
        if len(self.widgets) > 0:
            self.active_key = self.widgets[0]
            self.active_mask = False

        # Emit that we're selected (don't call parent which opens tray)
        self.selected.emit(self)
        self.update()  # Force repaint to show highlight
        ev.accept()

    def mouseReleaseEvent(self, ev):
        # Override to prevent any tray behavior
        ev.accept()

    def set_selected(self, selected):
        """Visual feedback for selection"""
        self.is_selected = selected
        if selected:
            # Set active_key to show native KeyboardWidget highlighting
            if len(self.widgets) > 0:
                self.active_key = self.widgets[0]
                self.active_mask = False
        else:
            # Clear active_key to remove highlighting
            self.active_key = None
        self.update()


class ToggleEntryUI(QWidget):
    """UI for a single toggle slot"""

    changed = pyqtSignal()

    def __init__(self, slot_num, toggle_protocol=None):
        super().__init__()
        self.slot_num = slot_num
        self.toggle_protocol = toggle_protocol
        self.slot = ToggleSlot()
        self.pending_changes = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Slot info header
        header_layout = QHBoxLayout()

        slot_label = QLabel(f"<b>TGL_{self.slot_num:02d}</b>")
        slot_label.setStyleSheet("font-size: 14pt;")
        header_layout.addWidget(slot_label)

        self.keycode_label = QLabel(f"Keycode: 0x{slot_to_toggle_keycode(self.slot_num):04X}")
        self.keycode_label.setStyleSheet("font-family: monospace; color: gray;")
        header_layout.addWidget(self.keycode_label)

        header_layout.addStretch()

        self.status_label = QLabel("(Not configured)")
        self.status_label.setStyleSheet("color: gray;")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Description
        desc = QLabel("Configure the target keycode that will be toggled when this key is pressed.\n"
                      "Assign this TGL keycode to a physical key in your keymap.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(desc)

        # Target keycode section
        target_group = QGroupBox("Target Keycode")
        target_layout = QHBoxLayout()

        target_layout.addWidget(QLabel("Target:"))

        self.target_key = ToggleKeyWidget()
        self.target_key.selected.connect(self._on_target_selected)
        target_layout.addWidget(self.target_key)

        target_layout.addWidget(QLabel("← Click to select, then choose from keycodes below"))
        target_layout.addStretch()

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear Slot")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)

        btn_layout.addStretch()

        self.save_btn = QPushButton("Save to Keyboard")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Load from Keyboard")
        self.load_btn.clicked.connect(self._on_load)
        btn_layout.addWidget(self.load_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        self.setLayout(layout)

    def set_protocol(self, protocol):
        """Set the toggle protocol for communication"""
        self.toggle_protocol = protocol

    def _on_target_selected(self, widget):
        """Handle target key widget selection"""
        # Mark this widget as selected for keycode assignment
        self.target_key.set_selected(True)

    def on_keycode_selected(self, keycode):
        """Called when a keycode is selected from TabbedKeycodes"""
        if self.target_key.is_selected:
            # Convert qmk_id string to integer keycode for firmware
            try:
                keycode_value = Keycode.deserialize(keycode)
            except Exception:
                keycode_value = 0

            self.slot.target_keycode = keycode_value
            self._update_display()
            self.pending_changes = True
            self.save_btn.setEnabled(True)
            self.changed.emit()
            self.target_key.set_selected(False)

    def _update_display(self):
        """Update the UI to reflect current slot state"""
        if self.slot.target_keycode != 0:
            # Convert integer keycode to qmk_id string for display
            qmk_id = Keycode.serialize(self.slot.target_keycode)
            self.target_key.set_keycode(qmk_id)
            self.status_label.setText("Configured")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.target_key.set_keycode("KC_NO")
            self.status_label.setText("(Not configured)")
            self.status_label.setStyleSheet("color: gray;")

    def _on_clear(self):
        """Clear this slot"""
        self.slot.target_keycode = 0
        self._update_display()
        self.pending_changes = True
        self.save_btn.setEnabled(True)
        self.changed.emit()

    def _on_save(self):
        """Save slot to keyboard"""
        if not self.toggle_protocol:
            QMessageBox.warning(self, "Error", "Not connected to keyboard")
            return

        if self.toggle_protocol.set_slot(self.slot_num, self.slot):
            if self.toggle_protocol.save_to_eeprom():
                QMessageBox.information(self, "Success", f"TGL_{self.slot_num:02d} saved to keyboard")
                self.pending_changes = False
                self.save_btn.setEnabled(False)
            else:
                QMessageBox.warning(self, "Error", "Failed to save to EEPROM")
        else:
            QMessageBox.warning(self, "Error", "Failed to send configuration to keyboard")

    def _on_load(self):
        """Load slot from keyboard"""
        if not self.toggle_protocol:
            QMessageBox.warning(self, "Error", "Not connected to keyboard")
            return

        slot = self.toggle_protocol.get_slot(self.slot_num)
        if slot:
            self.slot = slot
            self._update_display()
            self.pending_changes = False
            self.save_btn.setEnabled(False)
        else:
            QMessageBox.warning(self, "Error", "Failed to load configuration from keyboard")


class ToggleSettingsTab(BasicEditor):
    """Main Toggle settings editor tab"""

    def __init__(self, layout_editor=None):
        super().__init__()
        self.layout_editor = layout_editor
        self.toggle_protocol = None
        self.toggle_entries = []
        self.loaded_slots = set()  # Track which slots have been loaded

        # Create tab widget for toggle slots
        self.tabs = QTabWidget()

        # Create all toggle entries
        for i in range(TOGGLE_NUM_SLOTS):
            entry = ToggleEntryUI(i)
            entry.changed.connect(self.on_entry_changed)
            self.toggle_entries.append(entry)

        # Add tabs to widget (group by 10s for easier navigation)
        for i, entry in enumerate(self.toggle_entries):
            scroll = QScrollArea()
            scroll.setWidget(entry)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.tabs.addTab(scroll, f"TGL{i:02d}")

        self.addWidget(self.tabs)

        # Connect tab changes for lazy loading
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Bottom action buttons
        button_layout = QHBoxLayout()

        self.reset_all_btn = QPushButton("Reset All Slots")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        button_layout.addWidget(self.reset_all_btn)

        button_layout.addStretch()

        self.load_eeprom_btn = QPushButton("Load All from EEPROM")
        self.load_eeprom_btn.clicked.connect(self._on_load_eeprom)
        button_layout.addWidget(self.load_eeprom_btn)

        self.addLayout(button_layout)

        # Add TabbedKeycodes at the bottom
        self.tabbed_keycodes = TabbedKeycodesNoLayers()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_selected)
        self.addWidget(self.tabbed_keycodes)

    def on_entry_changed(self):
        """Handle entry change"""
        pass

    def on_keycode_selected(self, keycode):
        """Called when a keycode is selected from TabbedKeycodes"""
        current_idx = self.tabs.currentIndex()
        if current_idx >= 0 and current_idx < len(self.toggle_entries):
            self.toggle_entries[current_idx].on_keycode_selected(keycode)

    def _on_tab_changed(self, index):
        """Handle tab change - lazy load slot data"""
        if index >= 0 and index < len(self.toggle_entries):
            # Lazy load: Only load slot data when first viewing the tab
            if self.toggle_protocol and index not in self.loaded_slots:
                self.toggle_entries[index]._on_load()
                self.loaded_slots.add(index)

    def _on_reset_all(self):
        """Reset all slots to defaults"""
        if not self.toggle_protocol:
            return

        reply = QMessageBox.question(
            None, "Confirm Reset",
            "Reset ALL Toggle slots to default configuration? This cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.toggle_protocol.reset_all_slots():
                QMessageBox.information(None, "Success", "All slots reset to defaults")
                # Reload current tab
                current_idx = self.tabs.currentIndex()
                self.toggle_entries[current_idx]._on_load()
            else:
                QMessageBox.warning(None, "Error", "Failed to reset slots")

    def _on_load_eeprom(self):
        """Load all slots from EEPROM"""
        if not self.toggle_protocol:
            return

        if self.toggle_protocol.load_from_eeprom():
            QMessageBox.information(None, "Success", "Toggle configurations loaded from EEPROM")
            # Reload current tab
            current_idx = self.tabs.currentIndex()
            self.toggle_entries[current_idx]._on_load()
        else:
            QMessageBox.warning(None, "Error", "Failed to load from EEPROM")

    def rebuild(self, device):
        """Rebuild the tab when device changes"""
        super().rebuild(device)

        if self.valid():
            self.keyboard = device.keyboard
            self.toggle_protocol = ProtocolToggle(self.keyboard)

            # Set protocol on all entries
            for entry in self.toggle_entries:
                entry.set_protocol(self.toggle_protocol)

            # Set keyboard on tabbed keycodes
            self.tabbed_keycodes.set_keyboard(self.keyboard)

            # Clear loaded slots cache
            self.loaded_slots.clear()

            # Load current tab
            current_idx = self.tabs.currentIndex()
            if current_idx >= 0:
                self.toggle_entries[current_idx]._on_load()
                self.loaded_slots.add(current_idx)

    def valid(self):
        """Check if device is valid"""
        return isinstance(self.device, VialKeyboard)

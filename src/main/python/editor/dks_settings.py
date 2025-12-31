# SPDX-License-Identifier: GPL-2.0-or-later
"""
DKS (Dynamic Keystroke) Settings Editor

Allows configuration of multi-action analog keys with customizable actuation points.
Users configure DKS slots (DKS_00 - DKS_49) and then assign them to keys via the keymap editor.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QSlider, QGroupBox, QMessageBox, QFrame,
                              QSizePolicy, QCheckBox, QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from editor.basic_editor import BasicEditor
from protocol.dks_protocol import (ProtocolDKS, DKSSlot, DKS_BEHAVIOR_TAP,
                                   DKS_BEHAVIOR_PRESS, DKS_BEHAVIOR_RELEASE,
                                   DKS_NUM_SLOTS, DKS_ACTIONS_PER_STAGE)
from keycodes.keycodes import Keycode, KEYCODES
from util import tr


class TravelBarWidget(QWidget):
    """Visual representation of key travel with actuation points"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.press_actuations = []      # List of (actuation_point, enabled) tuples
        self.release_actuations = []    # List of (actuation_point, enabled) tuples

    def set_actuations(self, press_points, release_points):
        """Set actuation points to display

        Args:
            press_points: List of (actuation, enabled) tuples for press actions
            release_points: List of (actuation, enabled) tuples for release actions
        """
        self.press_actuations = press_points
        self.release_actuations = release_points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate drawing area
        width = self.width()
        height = self.height()
        margin = 20
        bar_height = 30
        bar_y = (height - bar_height) // 2

        # Draw travel bar background
        bar_rect = painter.drawRect(margin, bar_y, width - 2 * margin, bar_height)
        painter.setBrush(QColor(60, 60, 60))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(margin, bar_y, width - 2 * margin, bar_height)

        # Draw 0mm and 2.5mm labels
        painter.setPen(QColor(200, 200, 200))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(margin - 5, bar_y + bar_height + 15, "0.0mm")
        painter.drawText(width - margin - 30, bar_y + bar_height + 15, "2.5mm")

        # Draw press actuation points (orange, above bar)
        for actuation, enabled in self.press_actuations:
            if not enabled:
                continue

            x = margin + int((actuation / 100.0) * (width - 2 * margin))

            # Draw line
            painter.setPen(QPen(QColor(255, 140, 0), 3))  # Orange
            painter.drawLine(x, bar_y - 15, x, bar_y)

            # Draw circle at top
            painter.setBrush(QColor(255, 140, 0))
            painter.drawEllipse(x - 4, bar_y - 23, 8, 8)

            # Draw actuation value
            mm_value = (actuation / 100.0) * 2.5
            painter.setPen(QColor(255, 140, 0))
            painter.drawText(x - 15, bar_y - 28, f"{mm_value:.2f}")

        # Draw release actuation points (cyan, below bar)
        for actuation, enabled in self.release_actuations:
            if not enabled:
                continue

            x = margin + int((actuation / 100.0) * (width - 2 * margin))

            # Draw line
            painter.setPen(QPen(QColor(0, 255, 255), 3))  # Cyan
            painter.drawLine(x, bar_y + bar_height, x, bar_y + bar_height + 15)

            # Draw circle at bottom
            painter.setBrush(QColor(0, 255, 255))
            painter.drawEllipse(x - 4, bar_y + bar_height + 15, 8, 8)

            # Draw actuation value
            mm_value = (actuation / 100.0) * 2.5
            painter.setPen(QColor(0, 255, 255))
            painter.drawText(x - 15, bar_y + bar_height + 35, f"{mm_value:.2f}")


class ActionEditorWidget(QWidget):
    """Editor for a single DKS action (keycode, actuation, behavior)"""

    changed = pyqtSignal()

    def __init__(self, action_name, is_press=True):
        super().__init__()
        self.is_press = is_press
        self.action_name = action_name

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Enable checkbox
        self.enable_check = QCheckBox()
        self.enable_check.setChecked(False)
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_check)

        # Action label
        label = QLabel(action_name)
        label.setMinimumWidth(60)
        layout.addWidget(label)

        # Keycode selector
        layout.addWidget(QLabel("Key:"))
        self.keycode_combo = QComboBox()
        self.keycode_combo.setMinimumWidth(120)
        self.keycode_combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self.keycode_combo)

        # Actuation slider
        layout.addWidget(QLabel("Actuation:"))
        self.actuation_slider = QSlider(Qt.Horizontal)
        self.actuation_slider.setMinimum(0)
        self.actuation_slider.setMaximum(100)
        self.actuation_slider.setValue(60)
        self.actuation_slider.setMinimumWidth(150)
        self.actuation_slider.valueChanged.connect(self._update_actuation_label)
        self.actuation_slider.valueChanged.connect(self._on_changed)
        layout.addWidget(self.actuation_slider)

        # Actuation value label
        self.actuation_label = QLabel("1.50mm")
        self.actuation_label.setMinimumWidth(50)
        layout.addWidget(self.actuation_label)

        # Behavior selector
        layout.addWidget(QLabel("Behavior:"))
        self.behavior_combo = QComboBox()
        self.behavior_combo.addItems(["Tap", "Press", "Release"])
        self.behavior_combo.setCurrentIndex(DKS_BEHAVIOR_TAP)
        self.behavior_combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self.behavior_combo)

        layout.addStretch()

        self.setLayout(layout)
        self._update_actuation_label()
        self._update_enabled_state()

    def _on_enable_changed(self):
        self._update_enabled_state()
        self._on_changed()

    def _update_enabled_state(self):
        """Enable/disable controls based on checkbox"""
        enabled = self.enable_check.isChecked()
        self.keycode_combo.setEnabled(enabled)
        self.actuation_slider.setEnabled(enabled)
        self.behavior_combo.setEnabled(enabled)

    def _update_actuation_label(self):
        """Update actuation label with mm value"""
        value = self.actuation_slider.value()
        mm = (value / 100.0) * 2.5
        self.actuation_label.setText(f"{mm:.2f}mm")

    def _on_changed(self):
        """Emit changed signal"""
        self.changed.emit()

    def populate_keycodes(self, keycodes):
        """Populate keycode dropdown with available keycodes"""
        self.keycode_combo.clear()
        self.keycode_combo.addItem("None (KC_NO)", 0)

        for kc in keycodes:
            if kc.qmk_id and kc.label:
                self.keycode_combo.addItem(kc.label, kc.qmk_id)

    def set_action(self, keycode, actuation, behavior):
        """Set action values"""
        # Find keycode in combo box
        enabled = (keycode != 0)
        self.enable_check.setChecked(enabled)

        for i in range(self.keycode_combo.count()):
            if self.keycode_combo.itemData(i) == keycode:
                self.keycode_combo.setCurrentIndex(i)
                break

        self.actuation_slider.setValue(actuation)
        self.behavior_combo.setCurrentIndex(behavior)
        self._update_enabled_state()

    def get_action(self):
        """Get action values as (keycode, actuation, behavior) tuple"""
        if not self.enable_check.isChecked():
            return (0, self.actuation_slider.value(), self.behavior_combo.currentIndex())

        keycode = self.keycode_combo.currentData()
        actuation = self.actuation_slider.value()
        behavior = self.behavior_combo.currentIndex()
        return (keycode, actuation, behavior)


class DKSSettingsTab(BasicEditor):
    """Main DKS settings editor tab"""

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor
        self.dks_protocol = None
        self.current_slot = 0
        self.unsaved_changes = False

        # Set spacing for this layout
        self.setSpacing(10)

        # Top bar: Slot selector and buttons
        top_bar = self._create_top_bar()
        self.addLayout(top_bar)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.addWidget(separator)

        # Travel bar visualization
        travel_group = QGroupBox("Key Travel Visualization")
        travel_layout = QVBoxLayout()
        self.travel_bar = TravelBarWidget()
        travel_layout.addWidget(self.travel_bar)

        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("🟠 Press Actions (downstroke)"))
        legend_layout.addStretch()
        legend_layout.addWidget(QLabel("🔵 Release Actions (upstroke)"))
        travel_layout.addLayout(legend_layout)

        travel_group.setLayout(travel_layout)
        self.addWidget(travel_group)

        # Press actions group
        press_group = self._create_action_group("Press Actions (Downstroke)", True)
        self.addWidget(press_group)

        # Release actions group
        release_group = self._create_action_group("Release Actions (Upstroke)", False)
        self.addWidget(release_group)

        # Bottom buttons
        bottom_bar = self._create_bottom_bar()
        self.addLayout(bottom_bar)

        self.addStretch()

    def _create_top_bar(self):
        """Create top bar with slot selector and load/save buttons"""
        layout = QHBoxLayout()

        # Slot selector
        layout.addWidget(QLabel("DKS Slot:"))
        self.slot_combo = QComboBox()
        for i in range(DKS_NUM_SLOTS):
            self.slot_combo.addItem(f"DKS_{i:02d} (0x{0xED00 + i:04X})", i)
        self.slot_combo.setCurrentIndex(0)
        self.slot_combo.currentIndexChanged.connect(self._on_slot_changed)
        layout.addWidget(self.slot_combo)

        layout.addSpacing(20)

        # Load from keyboard button
        self.load_btn = QPushButton("Load from Keyboard")
        self.load_btn.clicked.connect(self._on_load_from_keyboard)
        layout.addWidget(self.load_btn)

        layout.addStretch()

        # Info label
        self.info_label = QLabel("Assign this DKS keycode to keys via the Keymap tab")
        self.info_label.setStyleSheet("color: #888;")
        layout.addWidget(self.info_label)

        return layout

    def _create_action_group(self, title, is_press):
        """Create a group of 4 action editors"""
        group = QGroupBox(title)
        layout = QVBoxLayout()

        # Create 4 action editors
        editors = []
        for i in range(DKS_ACTIONS_PER_STAGE):
            action_name = f"Action {i + 1}:"
            editor = ActionEditorWidget(action_name, is_press)
            editor.changed.connect(self._on_action_changed)
            layout.addWidget(editor)
            editors.append(editor)

        # Store editors
        if is_press:
            self.press_editors = editors
        else:
            self.release_editors = editors

        group.setLayout(layout)
        return group

    def _create_bottom_bar(self):
        """Create bottom bar with action buttons"""
        layout = QHBoxLayout()

        # Reset slot button
        self.reset_slot_btn = QPushButton("Reset This Slot")
        self.reset_slot_btn.clicked.connect(self._on_reset_slot)
        layout.addWidget(self.reset_slot_btn)

        # Reset all button
        self.reset_all_btn = QPushButton("Reset All Slots")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        layout.addWidget(self.reset_all_btn)

        layout.addStretch()

        # Save to EEPROM button
        self.save_btn = QPushButton("Save to EEPROM")
        self.save_btn.setStyleSheet("background-color: #4CAF50; font-weight: bold;")
        self.save_btn.clicked.connect(self._on_save_to_eeprom)
        layout.addWidget(self.save_btn)

        # Load from EEPROM button
        self.load_eeprom_btn = QPushButton("Load from EEPROM")
        self.load_eeprom_btn.clicked.connect(self._on_load_from_eeprom)
        layout.addWidget(self.load_eeprom_btn)

        return layout

    def _on_slot_changed(self, index):
        """Handle slot selection change"""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Load the selected slot anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.slot_combo.setCurrentIndex(self.current_slot)
                return

        self.current_slot = index
        self._load_slot_from_keyboard()

    def _on_load_from_keyboard(self):
        """Load current slot from keyboard"""
        self._load_slot_from_keyboard()

    def _load_slot_from_keyboard(self):
        """Load current slot configuration from keyboard"""
        if not self.dks_protocol:
            return

        slot = self.dks_protocol.get_slot(self.current_slot)
        if not slot:
            QMessageBox.warning(self, "Error", "Failed to load DKS slot from keyboard")
            return

        # Update UI
        self._populate_editors_from_slot(slot)
        self.unsaved_changes = False
        self._update_travel_bar()

    def _populate_editors_from_slot(self, slot):
        """Populate action editors from slot data"""
        # Press actions
        for i, editor in enumerate(self.press_editors):
            action = slot.press_actions[i]
            editor.set_action(action.keycode, action.actuation, action.behavior)

        # Release actions
        for i, editor in enumerate(self.release_editors):
            action = slot.release_actions[i]
            editor.set_action(action.keycode, action.actuation, action.behavior)

    def _on_action_changed(self):
        """Handle action editor change"""
        self.unsaved_changes = True
        self._update_travel_bar()

        # Send to keyboard immediately
        self._send_current_slot_to_keyboard()

    def _send_current_slot_to_keyboard(self):
        """Send current slot configuration to keyboard"""
        if not self.dks_protocol:
            return

        # Send press actions
        for i, editor in enumerate(self.press_editors):
            keycode, actuation, behavior = editor.get_action()
            self.dks_protocol.set_action(
                self.current_slot, True, i, keycode, actuation, behavior
            )

        # Send release actions
        for i, editor in enumerate(self.release_editors):
            keycode, actuation, behavior = editor.get_action()
            self.dks_protocol.set_action(
                self.current_slot, False, i, keycode, actuation, behavior
            )

    def _update_travel_bar(self):
        """Update travel bar visualization"""
        # Get press actuations
        press_points = []
        for editor in self.press_editors:
            keycode, actuation, behavior = editor.get_action()
            enabled = (keycode != 0)
            press_points.append((actuation, enabled))

        # Get release actuations
        release_points = []
        for editor in self.release_editors:
            keycode, actuation, behavior = editor.get_action()
            enabled = (keycode != 0)
            release_points.append((actuation, enabled))

        self.travel_bar.set_actuations(press_points, release_points)

    def _on_save_to_eeprom(self):
        """Save all DKS configurations to EEPROM"""
        if not self.dks_protocol:
            return

        if self.dks_protocol.save_to_eeprom():
            QMessageBox.information(self, "Success", "DKS configurations saved to EEPROM")
            self.unsaved_changes = False
        else:
            QMessageBox.warning(self, "Error", "Failed to save DKS configurations")

    def _on_load_from_eeprom(self):
        """Load all DKS configurations from EEPROM"""
        if not self.dks_protocol:
            return

        if self.dks_protocol.load_from_eeprom():
            QMessageBox.information(self, "Success", "DKS configurations loaded from EEPROM")
            self._load_slot_from_keyboard()
        else:
            QMessageBox.warning(self, "Error", "Failed to load DKS configurations")

    def _on_reset_slot(self):
        """Reset current slot to defaults"""
        if not self.dks_protocol:
            return

        reply = QMessageBox.question(
            self, "Confirm Reset",
            f"Reset DKS_{self.current_slot:02d} to default configuration?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.dks_protocol.reset_slot(self.current_slot):
                QMessageBox.information(self, "Success", "Slot reset to defaults")
                self._load_slot_from_keyboard()
            else:
                QMessageBox.warning(self, "Error", "Failed to reset slot")

    def _on_reset_all(self):
        """Reset all slots to defaults"""
        if not self.dks_protocol:
            return

        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Reset ALL DKS slots to default configuration? This cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.dks_protocol.reset_all_slots():
                QMessageBox.information(self, "Success", "All slots reset to defaults")
                self._load_slot_from_keyboard()
            else:
                QMessageBox.warning(self, "Error", "Failed to reset slots")

    def rebuild(self, device):
        """Rebuild the editor when device changes"""
        super().rebuild(device)

        if not self.valid():
            self.dks_protocol = None
            return

        # Create DKS protocol handler
        self.dks_protocol = ProtocolDKS(device)

        # Populate keycode dropdowns
        for editor in self.press_editors:
            editor.populate_keycodes(KEYCODES)
        for editor in self.release_editors:
            editor.populate_keycodes(KEYCODES)

        # Load current slot
        self._load_slot_from_keyboard()

    def valid(self):
        """Check if this tab is valid for the current device"""
        # DKS is always available (it's a firmware feature)
        from vial_device import VialKeyboard
        return isinstance(self.device, VialKeyboard)

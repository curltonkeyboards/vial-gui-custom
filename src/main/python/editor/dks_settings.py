# SPDX-License-Identifier: GPL-2.0-or-later
"""
DKS (Dynamic Keystroke) Settings Editor

Allows configuration of multi-action analog keys with customizable actuation points.
Users configure DKS slots (DKS_00 - DKS_49) and then assign them to keys via the keymap editor.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QComboBox, QSlider, QGroupBox, QMessageBox, QFrame,
                              QSizePolicy, QCheckBox, QSpinBox, QScrollArea, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPalette

from editor.basic_editor import BasicEditor
from protocol.dks_protocol import (ProtocolDKS, DKSSlot, DKS_BEHAVIOR_TAP,
                                   DKS_BEHAVIOR_PRESS, DKS_BEHAVIOR_RELEASE,
                                   DKS_NUM_SLOTS, DKS_ACTIONS_PER_STAGE)
from keycodes.keycodes import Keycode
from widgets.key_widget import KeyWidget
from widgets.tab_widget_keycodes import TabWidgetWithKeycodes
from tabbed_keycodes import TabbedKeycodes
from vial_device import VialKeyboard


class DKSKeyWidget(KeyWidget):
    """Custom KeyWidget that doesn't open tray - parent will handle keycode selection"""

    selected = pyqtSignal(object)  # Emits self when clicked

    def __init__(self):
        super().__init__()
        self.is_selected = False

    def mousePressEvent(self, ev):
        # Don't call parent's mousePressEvent which would open the tray
        # Instead, just emit that we're selected
        self.selected.emit(self)
        ev.accept()

    def set_selected(self, selected):
        """Visual feedback for selection"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                QWidget {
                    border: 2px solid palette(highlight);
                    background: palette(highlight);
                }
            """)
        else:
            self.setStyleSheet("")
        self.update()


class TravelBarWidget(QWidget):
    """Visual representation of key travel with actuation points"""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)
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

        # Get theme colors
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        is_dark = brightness < 127

        # Calculate drawing area
        width = self.width()
        height = self.height()
        margin = 40
        bar_height = 30
        bar_y = (height - bar_height) // 2

        # Draw travel bar background
        if is_dark:
            bar_bg = QColor(60, 60, 60)
            bar_border = QColor(100, 100, 100)
            text_color = QColor(200, 200, 200)
        else:
            bar_bg = QColor(220, 220, 220)
            bar_border = QColor(150, 150, 150)
            text_color = QColor(60, 60, 60)

        painter.setBrush(bar_bg)
        painter.setPen(QPen(bar_border, 2))
        painter.drawRect(margin, bar_y, width - 2 * margin, bar_height)

        # Draw 0mm and 2.5mm labels
        painter.setPen(text_color)
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(margin - 10, bar_y + bar_height + 20, "0.0mm")
        painter.drawText(width - margin - 35, bar_y + bar_height + 20, "2.5mm")

        # Draw press actuation points (orange, above bar)
        for actuation, enabled in self.press_actuations:
            if not enabled:
                continue

            x = margin + int((actuation / 100.0) * (width - 2 * margin))

            # Draw line
            painter.setPen(QPen(QColor(255, 140, 0), 3))  # Orange
            painter.drawLine(x, bar_y - 20, x, bar_y)

            # Draw circle at top
            painter.setBrush(QColor(255, 140, 0))
            painter.drawEllipse(x - 5, bar_y - 28, 10, 10)

            # Draw actuation value
            mm_value = (actuation / 100.0) * 2.5
            painter.setPen(QColor(255, 140, 0))
            font_small = QFont()
            font_small.setPointSize(8)
            painter.setFont(font_small)
            painter.drawText(x - 18, bar_y - 32, f"{mm_value:.2f}")
            painter.setFont(font)

        # Draw release actuation points (cyan, below bar)
        for actuation, enabled in self.release_actuations:
            if not enabled:
                continue

            x = margin + int((actuation / 100.0) * (width - 2 * margin))

            # Draw line
            painter.setPen(QPen(QColor(0, 200, 200), 3))  # Cyan
            painter.drawLine(x, bar_y + bar_height, x, bar_y + bar_height + 20)

            # Draw circle at bottom
            painter.setBrush(QColor(0, 200, 200))
            painter.drawEllipse(x - 5, bar_y + bar_height + 20, 10, 10)

            # Draw actuation value
            mm_value = (actuation / 100.0) * 2.5
            painter.setPen(QColor(0, 200, 200))
            font_small = QFont()
            font_small.setPointSize(8)
            painter.setFont(font_small)
            painter.drawText(x - 18, bar_y + bar_height + 42, f"{mm_value:.2f}")
            painter.setFont(font)


class DKSActionEditor(QWidget):
    """Editor for a single DKS action with DKSKeyWidget integration"""

    changed = pyqtSignal()
    key_selected = pyqtSignal(object)  # Emits the DKSKeyWidget when clicked

    def __init__(self, action_num, is_press=True):
        super().__init__()
        self.action_num = action_num
        self.is_press = is_press

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Action label
        action_type = "Press" if is_press else "Release"
        label_text = f"{action_type} {action_num + 1}"
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self.label)

        # Key widget - use custom DKSKeyWidget
        self.key_widget = DKSKeyWidget()
        self.key_widget.setFixedSize(60, 50)
        self.key_widget.changed.connect(self._on_changed)
        self.key_widget.selected.connect(self._on_key_selected)
        layout.addWidget(self.key_widget, alignment=Qt.AlignCenter)

        # Actuation slider with label
        actuation_layout = QVBoxLayout()
        actuation_layout.setSpacing(2)

        self.actuation_label = QLabel("1.50mm")
        self.actuation_label.setAlignment(Qt.AlignCenter)
        self.actuation_label.setStyleSheet("font-size: 10px;")
        actuation_layout.addWidget(self.actuation_label)

        self.actuation_slider = QSlider(Qt.Vertical)
        self.actuation_slider.setMinimum(0)
        self.actuation_slider.setMaximum(100)
        self.actuation_slider.setValue(60)
        self.actuation_slider.setFixedHeight(120)
        self.actuation_slider.valueChanged.connect(self._update_actuation_label)
        self.actuation_slider.valueChanged.connect(self._on_changed)
        actuation_layout.addWidget(self.actuation_slider, alignment=Qt.AlignCenter)

        layout.addLayout(actuation_layout)

        # Behavior selector
        behavior_label = QLabel("Behavior:")
        behavior_label.setAlignment(Qt.AlignCenter)
        behavior_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(behavior_label)

        self.behavior_combo = QComboBox()
        self.behavior_combo.addItems(["Tap", "Press", "Release"])
        self.behavior_combo.setCurrentIndex(DKS_BEHAVIOR_TAP)
        self.behavior_combo.currentIndexChanged.connect(self._on_changed)
        self.behavior_combo.setFixedWidth(80)
        layout.addWidget(self.behavior_combo, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.setLayout(layout)
        self._update_actuation_label()

        # Style the widget with theme colors
        self.setStyleSheet("""
            DKSActionEditor {
                border: 1px solid palette(mid);
                border-radius: 5px;
                background: palette(base);
            }
        """)

    def _update_actuation_label(self):
        """Update actuation label with mm value"""
        value = self.actuation_slider.value()
        mm = (value / 100.0) * 2.5
        self.actuation_label.setText(f"{mm:.2f}mm")

    def _on_changed(self):
        """Emit changed signal"""
        self.changed.emit()

    def _on_key_selected(self, widget):
        """Forward key selection signal to parent"""
        self.key_selected.emit(widget)

    def set_action(self, keycode, actuation, behavior):
        """Set action values"""
        # Convert keycode integer to string qmk_id
        if isinstance(keycode, int):
            if keycode == 0:
                keycode_str = "KC_NO"
            else:
                keycode_str = Keycode.serialize(keycode)
        else:
            keycode_str = keycode

        self.key_widget.set_keycode(keycode_str)
        self.actuation_slider.setValue(actuation)
        self.behavior_combo.setCurrentIndex(behavior)

    def get_action(self):
        """Get action values as (keycode, actuation, behavior) tuple"""
        keycode_str = self.key_widget.keycode

        # Convert keycode string to integer
        if keycode_str == "KC_NO" or keycode_str == "":
            keycode = 0
        else:
            keycode = Keycode.deserialize(keycode_str)

        actuation = self.actuation_slider.value()
        behavior = self.behavior_combo.currentIndex()
        return (keycode, actuation, behavior)


class DKSVisualWidget(QWidget):
    """Visual layout widget for DKS actions, similar to gaming settings"""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(900, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Will be set by parent
        self.press_editors = []
        self.release_editors = []

    def set_editors(self, press_editors, release_editors):
        """Position the action editors in the visual layout"""
        self.press_editors = press_editors
        self.release_editors = release_editors

        # Position press actions (top row, orange theme)
        press_x_start = 50
        press_spacing = 120
        press_y = 50

        for i, editor in enumerate(self.press_editors):
            editor.setParent(self)
            x = press_x_start + i * press_spacing
            editor.move(x, press_y)
            editor.show()
            editor.label.setStyleSheet("""
                font-weight: bold;
                font-size: 11px;
                color: rgb(255, 140, 0);
            """)

        # Position release actions (bottom row, cyan theme)
        release_x_start = 50
        release_spacing = 120
        release_y = 350

        for i, editor in enumerate(self.release_editors):
            editor.setParent(self)
            x = release_x_start + i * release_spacing
            editor.move(x, release_y)
            editor.show()
            editor.label.setStyleSheet("""
                font-weight: bold;
                font-size: 11px;
                color: rgb(0, 200, 200);
            """)

    def paintEvent(self, event):
        """Draw the background and connection lines"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Get theme colors
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        is_dark = brightness < 127

        # Draw background
        if is_dark:
            bg_color = QColor(40, 40, 40)
        else:
            bg_color = QColor(245, 245, 245)

        painter.fillRect(self.rect(), bg_color)

        # Draw section labels
        if is_dark:
            text_color = QColor(200, 200, 200)
        else:
            text_color = QColor(60, 60, 60)

        painter.setPen(text_color)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        # Key Press section label
        painter.setPen(QColor(255, 140, 0))
        painter.drawText(50, 30, "Key Press (Downstroke)")

        # Key Release section label
        painter.setPen(QColor(0, 200, 200))
        painter.drawText(50, 330, "Key Release (Upstroke)")

        # Draw travel direction indicator
        painter.setPen(QPen(text_color, 2))
        painter.drawLine(550, 100, 550, 450)

        # Draw arrow pointing down
        painter.setBrush(text_color)
        arrow_points = [
            (550, 450),
            (545, 440),
            (555, 440)
        ]
        from PyQt5.QtGui import QPolygon
        from PyQt5.QtCore import QPoint
        painter.drawPolygon(QPolygon([QPoint(*p) for p in arrow_points]))

        # Draw "Travel" label
        painter.save()
        painter.translate(570, 275)
        painter.rotate(-90)
        painter.drawText(0, 0, "Travel Direction →")
        painter.restore()


class DKSEntryUI(QWidget):
    """UI for a single DKS slot"""

    changed = pyqtSignal()

    def __init__(self, slot_idx):
        super().__init__()
        self.slot_idx = slot_idx
        self.dks_protocol = None
        self.selected_key_widget = None  # Track which key widget is selected

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Info section
        info_layout = QHBoxLayout()
        info_text = f"Configure actions for <b>DKS_{slot_idx:02d}</b> (keycode: <code>0x{0xED00 + slot_idx:04X}</code>)"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: palette(text); font-size: 11px;")
        info_layout.addWidget(info_label)
        info_layout.addStretch()

        # Load button
        self.load_btn = QPushButton("Load from Keyboard")
        self.load_btn.clicked.connect(self._on_load)
        info_layout.addWidget(self.load_btn)

        main_layout.addLayout(info_layout)

        # Travel bar visualization
        travel_group = QGroupBox("Key Travel Visualization")
        travel_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid palette(mid);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        travel_layout = QVBoxLayout()
        self.travel_bar = TravelBarWidget()
        travel_layout.addWidget(self.travel_bar)
        travel_group.setLayout(travel_layout)
        main_layout.addWidget(travel_group)

        # Visual action editor
        visual_group = QGroupBox("Action Configuration")
        visual_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid palette(mid);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        visual_layout = QVBoxLayout()

        self.visual_widget = DKSVisualWidget()

        # Create action editors
        self.press_editors = []
        self.release_editors = []

        for i in range(DKS_ACTIONS_PER_STAGE):
            press_editor = DKSActionEditor(i, is_press=True)
            press_editor.changed.connect(self._on_action_changed)
            press_editor.key_selected.connect(self._on_key_selected)
            self.press_editors.append(press_editor)

            release_editor = DKSActionEditor(i, is_press=False)
            release_editor.changed.connect(self._on_action_changed)
            release_editor.key_selected.connect(self._on_key_selected)
            self.release_editors.append(release_editor)

        # Set editors in visual widget
        self.visual_widget.set_editors(self.press_editors, self.release_editors)

        visual_layout.addWidget(self.visual_widget)
        visual_group.setLayout(visual_layout)
        main_layout.addWidget(visual_group)

        # Bottom buttons
        bottom_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Reset Slot")
        self.reset_btn.clicked.connect(self._on_reset)
        bottom_layout.addWidget(self.reset_btn)

        bottom_layout.addStretch()

        self.save_eeprom_btn = QPushButton("Save to EEPROM")
        self.save_eeprom_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 palette(light), stop: 1 palette(button));
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        self.save_eeprom_btn.clicked.connect(self._on_save_eeprom)
        bottom_layout.addWidget(self.save_eeprom_btn)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def set_dks_protocol(self, protocol):
        """Set the DKS protocol handler"""
        self.dks_protocol = protocol

    def _on_load(self):
        """Load slot from keyboard"""
        if not self.dks_protocol:
            return

        slot = self.dks_protocol.get_slot(self.slot_idx)
        if not slot:
            QMessageBox.warning(self, "Error", "Failed to load DKS slot from keyboard")
            return

        self.load_from_slot(slot)

    def load_from_slot(self, slot):
        """Load UI from slot data"""
        # Press actions
        for i, editor in enumerate(self.press_editors):
            action = slot.press_actions[i]
            editor.set_action(action.keycode, action.actuation, action.behavior)

        # Release actions
        for i, editor in enumerate(self.release_editors):
            action = slot.release_actions[i]
            editor.set_action(action.keycode, action.actuation, action.behavior)

        self._update_travel_bar()

    def save_to_slot(self):
        """Save UI to slot (returns tuple of press and release actions)"""
        press_actions = []
        for editor in self.press_editors:
            press_actions.append(editor.get_action())

        release_actions = []
        for editor in self.release_editors:
            release_actions.append(editor.get_action())

        return (press_actions, release_actions)

    def _on_action_changed(self):
        """Handle action change"""
        self._update_travel_bar()
        self._send_to_keyboard()
        self.changed.emit()

    def _on_key_selected(self, widget):
        """Handle key widget selection - update visual feedback"""
        # Clear previous selection
        if self.selected_key_widget:
            self.selected_key_widget.set_selected(False)

        # Set new selection
        self.selected_key_widget = widget
        widget.set_selected(True)

    def on_keycode_selected(self, keycode):
        """Handle keycode selection from TabbedKeycodes"""
        if self.selected_key_widget:
            self.selected_key_widget.on_keycode_changed(keycode)

    def _send_to_keyboard(self):
        """Send current configuration to keyboard"""
        if not self.dks_protocol:
            return

        # Send press actions
        for i, editor in enumerate(self.press_editors):
            keycode, actuation, behavior = editor.get_action()
            self.dks_protocol.set_action(
                self.slot_idx, True, i, keycode, actuation, behavior
            )

        # Send release actions
        for i, editor in enumerate(self.release_editors):
            keycode, actuation, behavior = editor.get_action()
            self.dks_protocol.set_action(
                self.slot_idx, False, i, keycode, actuation, behavior
            )

    def _update_travel_bar(self):
        """Update travel bar visualization"""
        press_points = []
        for editor in self.press_editors:
            keycode, actuation, behavior = editor.get_action()
            enabled = (keycode != 0)
            press_points.append((actuation, enabled))

        release_points = []
        for editor in self.release_editors:
            keycode, actuation, behavior = editor.get_action()
            enabled = (keycode != 0)
            release_points.append((actuation, enabled))

        self.travel_bar.set_actuations(press_points, release_points)

    def _on_reset(self):
        """Reset slot to defaults"""
        if not self.dks_protocol:
            return

        reply = QMessageBox.question(
            self, "Confirm Reset",
            f"Reset DKS_{self.slot_idx:02d} to default configuration?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.dks_protocol.reset_slot(self.slot_idx):
                QMessageBox.information(self, "Success", "Slot reset to defaults")
                self._on_load()
            else:
                QMessageBox.warning(self, "Error", "Failed to reset slot")

    def _on_save_eeprom(self):
        """Save to EEPROM"""
        if not self.dks_protocol:
            return

        if self.dks_protocol.save_to_eeprom():
            QMessageBox.information(self, "Success", "DKS configuration saved to EEPROM")
        else:
            QMessageBox.warning(self, "Error", "Failed to save to EEPROM")


class DKSSettingsTab(BasicEditor):
    """Main DKS settings editor tab with filtered slots"""

    def __init__(self, layout_editor):
        super().__init__()
        self.layout_editor = layout_editor
        self.dks_protocol = None
        self.dks_entries = []

        # Create tab widget for DKS slots
        self.tabs = TabWidgetWithKeycodes()

        # Create all DKS entries (pre-create like TapDance does)
        for i in range(DKS_NUM_SLOTS):
            entry = DKSEntryUI(i)
            entry.changed.connect(self.on_entry_changed)
            self.dks_entries.append(entry)

        # Add tabs to widget
        for i, entry in enumerate(self.dks_entries):
            scroll = QScrollArea()
            scroll.setWidget(entry)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.tabs.addTab(scroll, f"DKS{i}")

        self.addWidget(self.tabs)

        # Add TabbedKeycodes at the bottom for keycode selection
        self.tabbed_keycodes = TabbedKeycodes()
        self.addWidget(self.tabbed_keycodes)

        # Connect tab changes to update keycode connections
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Initialize connection to first tab
        self._on_tab_changed(0)

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

    def on_entry_changed(self):
        """Handle entry change (can be used for modified indicators)"""
        # Future: Add modified state tracking like TapDance
        pass

    def _on_tab_changed(self, index):
        """Handle tab change - connect TabbedKeycodes to new entry"""
        if index >= 0 and index < len(self.dks_entries):
            # Disconnect all previous connections (if any)
            try:
                self.tabbed_keycodes.keycode_changed.disconnect()
            except:
                pass  # No connections yet

            # Connect to current entry
            self.tabbed_keycodes.keycode_changed.connect(
                self.dks_entries[index].on_keycode_selected
            )

    def _on_reset_all(self):
        """Reset all slots to defaults"""
        if not self.dks_protocol:
            return

        reply = QMessageBox.question(
            None, "Confirm Reset",
            "Reset ALL DKS slots to default configuration? This cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.dks_protocol.reset_all_slots():
                QMessageBox.information(None, "Success", "All slots reset to defaults")
                # Reload current tab
                current_idx = self.tabs.currentIndex()
                self.dks_entries[current_idx]._on_load()
            else:
                QMessageBox.warning(None, "Error", "Failed to reset slots")

    def _on_load_eeprom(self):
        """Load all slots from EEPROM"""
        if not self.dks_protocol:
            return

        if self.dks_protocol.load_from_eeprom():
            QMessageBox.information(None, "Success", "DKS configurations loaded from EEPROM")
            # Reload current tab
            current_idx = self.tabs.currentIndex()
            self.dks_entries[current_idx]._on_load()
        else:
            QMessageBox.warning(None, "Error", "Failed to load from EEPROM")

    def rebuild(self, device):
        """Rebuild the editor when device changes"""
        super().rebuild(device)

        if not self.valid():
            self.dks_protocol = None
            return

        # Create DKS protocol handler
        self.dks_protocol = ProtocolDKS(device)

        # Set protocol for all entries
        for entry in self.dks_entries:
            entry.set_dks_protocol(self.dks_protocol)

        # Load first slot
        if len(self.dks_entries) > 0:
            self.dks_entries[0]._on_load()

    def valid(self):
        """Check if this tab is valid for the current device"""
        return isinstance(self.device, VialKeyboard)

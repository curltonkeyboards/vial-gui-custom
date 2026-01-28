# SPDX-License-Identifier: GPL-2.0-or-later
"""
Velocity Tab - Real-time MIDI velocity visualization and configuration

This tab provides:
1. Layer selection to view MIDI keys on specific layers
2. Keyboard visualization with velocity values (1-127) overlaid
3. Live velocity curve editor
4. Min/max travel time calibration for velocity scaling
"""

from PyQt5.QtWidgets import (QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel,
                           QSizePolicy, QGroupBox, QGridLayout, QComboBox, QCheckBox,
                           QFrame, QScrollArea, QSlider, QSpinBox, QButtonGroup,
                           QRadioButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont

from widgets.combo_box import ArrowComboBox
from widgets.curve_editor import CurveEditorWidget
from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidgetSimple
from themes import Theme
from util import tr
from vial_device import VialKeyboard


# MIDI note keycode range (from keycodes_v6.py)
MIDI_NOTE_MIN = 0x7103  # MI_C
MIDI_NOTE_MAX = 0x714A  # MI_B_5


def is_midi_note_keycode(keycode):
    """Check if a keycode is a MIDI note (not control codes like octave/transpose)"""
    if not keycode or keycode == "KC_NO" or keycode == "KC_TRNS":
        return False

    # Handle string keycodes (most common case from keyboard.layout)
    if isinstance(keycode, str):
        # Check for MI_SPLIT_ (keysplit) and MI_SPLIT2_ (triplesplit) first
        if keycode.startswith("MI_SPLIT2_") or keycode.startswith("MI_SPLIT_"):
            if keycode.startswith("MI_SPLIT2_"):
                remaining = keycode[10:]
            else:
                remaining = keycode[9:]
            if remaining and remaining[0] in 'CDEFGAB':
                return True
            return False

        # Check for MI_ prefix (base MIDI notes like MI_C, MI_C_1, MI_Cs, etc.)
        if keycode.startswith("MI_"):
            note_prefixes = ['MI_C', 'MI_D', 'MI_E', 'MI_F', 'MI_G', 'MI_A', 'MI_B']
            for prefix in note_prefixes:
                if keycode.startswith(prefix):
                    # Make sure it's not a control code like MI_CHANNEL
                    remaining = keycode[len(prefix):]
                    if not remaining or remaining[0] in 'sS_0123456789':
                        return True
            return False
        return False

    # Handle numeric keycodes
    return MIDI_NOTE_MIN <= keycode <= MIDI_NOTE_MAX


class VelocityKeyboardWidget(KeyboardWidgetSimple):
    """Extended keyboard widget that displays velocity values on keys"""

    def __init__(self, layout_editor):
        super().__init__(layout_editor)
        self.velocity_values = {}  # {(row, col): velocity}
        self.midi_keys = set()     # Set of (row, col) that have MIDI notes
        self.show_velocity = True

    def set_velocity(self, row, col, velocity):
        """Set velocity value for a specific key"""
        self.velocity_values[(row, col)] = velocity
        self.update()

    def set_midi_keys(self, midi_keys):
        """Set which keys are MIDI keys (to highlight them)"""
        self.midi_keys = set(midi_keys)
        self.update()

    def clear_velocities(self):
        """Clear all velocity values"""
        self.velocity_values = {}
        self.update()

    def paintEvent(self, event):
        # Call parent paint first
        super().paintEvent(event)

        if not self.show_velocity:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Check if light theme
        light_themes = ["Light", "Lavender Dream", "Mint Fresh", "Peachy Keen", "Sky Serenity", "Rose Garden"]
        is_light = Theme.get_theme() in light_themes

        font = QFont()
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)

        # Draw velocity values on keys
        for widget in self.widgets:
            if not hasattr(widget, 'desc'):
                continue

            row = widget.desc.row
            col = widget.desc.col

            # Get widget geometry
            rect = widget.geometry()
            center_x = rect.x() + rect.width() // 2
            center_y = rect.y() + rect.height() // 2

            # Check if this is a MIDI key
            is_midi = (row, col) in self.midi_keys

            if is_midi:
                # Draw velocity value for MIDI keys
                velocity = self.velocity_values.get((row, col), 0)

                # Color based on velocity (low = blue, high = red)
                if velocity > 0:
                    # Interpolate from blue (low) to red (high)
                    ratio = velocity / 127.0
                    r = int(50 + ratio * 205)
                    g = int(150 - ratio * 100)
                    b = int(255 - ratio * 205)
                    color = QColor(r, g, b)
                else:
                    color = QColor(100, 100, 100)  # Gray for 0

                # Draw background circle
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color))
                circle_size = min(rect.width(), rect.height()) * 0.6
                painter.drawEllipse(
                    int(center_x - circle_size/2),
                    int(center_y - circle_size/2),
                    int(circle_size),
                    int(circle_size)
                )

                # Draw velocity text
                painter.setPen(QPen(QColor(255, 255, 255) if velocity > 60 else QColor(0, 0, 0)))
                painter.drawText(
                    rect.x(), rect.y(), rect.width(), rect.height(),
                    Qt.AlignCenter,
                    str(velocity) if velocity > 0 else "-"
                )
            else:
                # Non-MIDI keys - show grayed out indicator
                painter.setPen(QPen(QColor(120, 120, 120, 100)))
                painter.setBrush(Qt.NoBrush)
                painter.drawText(
                    rect.x(), rect.y(), rect.width(), rect.height(),
                    Qt.AlignCenter,
                    "-"
                )

        painter.end()


class VelocityTab(BasicEditor):
    """Main velocity tab for real-time velocity visualization and configuration"""

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor
        self.keyboard = None
        self.current_layer = 0
        self.midi_keys = []  # List of (row, col) for MIDI keys on current layer

        # Velocity time settings
        self.min_time = 100  # ms for min velocity (slow press)
        self.max_time = 10   # ms for max velocity (fast press)

        # Polling timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_velocity)
        self.poll_interval = 50  # 50ms = 20Hz

        # Track if tab is active
        self.is_active = False

        self.setup_ui()

    def setup_ui(self):
        self.addStretch()

        # Create scroll area for the main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumSize(900, 700)

        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_widget.setLayout(main_layout)

        scroll.setWidget(main_widget)
        self.addWidget(scroll)
        self.setAlignment(scroll, QtCore.Qt.AlignHCenter)

        # Title
        title_label = QLabel(tr("VelocityTab", "Velocity Monitor"))
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(tr("VelocityTab",
            "Monitor real-time MIDI velocity values for keys on each layer.\n"
            "Select a layer to see which keys have MIDI notes and their current velocity."))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-size: 9pt;")
        desc_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(desc_label)

        # Layer selector
        layer_container = QWidget()
        layer_layout = QHBoxLayout()
        layer_layout.setContentsMargins(0, 0, 0, 0)
        layer_container.setLayout(layer_layout)

        layer_layout.addStretch()

        layer_label = QLabel(tr("VelocityTab", "Layer:"))
        layer_label.setStyleSheet("font-weight: bold;")
        layer_layout.addWidget(layer_label)

        self.layer_buttons = QButtonGroup()
        for i in range(12):
            btn = QRadioButton(str(i))
            btn.setMinimumWidth(35)
            if i == 0:
                btn.setChecked(True)
            self.layer_buttons.addButton(btn, i)
            layer_layout.addWidget(btn)

        self.layer_buttons.buttonClicked.connect(self.on_layer_changed)

        layer_layout.addStretch()
        main_layout.addWidget(layer_container)

        # MIDI keys info label
        self.midi_info_label = QLabel(tr("VelocityTab", "MIDI Keys: 0"))
        self.midi_info_label.setStyleSheet("color: #888; font-size: 10pt;")
        self.midi_info_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.midi_info_label)

        # Keyboard widget
        self.keyboard_widget = VelocityKeyboardWidget(self.layout_editor)
        self.keyboard_widget.setMinimumWidth(800)
        self.keyboard_widget.setMinimumHeight(250)
        main_layout.addWidget(self.keyboard_widget, alignment=Qt.AlignCenter)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Bottom section: Curve editor and time calibration side by side
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # Velocity Curve Editor Group
        curve_group = QGroupBox(tr("VelocityTab", "Velocity Curve"))
        curve_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        curve_layout = QVBoxLayout()
        curve_group.setLayout(curve_layout)

        # Curve editor widget
        self.curve_editor = CurveEditorWidget(show_save_button=False)
        self.curve_editor.setMinimumSize(300, 200)
        self.curve_editor.curve_changed.connect(self.on_curve_changed)
        curve_layout.addWidget(self.curve_editor)

        # Curve preset selector
        preset_layout = QHBoxLayout()
        preset_label = QLabel(tr("VelocityTab", "Preset:"))
        preset_layout.addWidget(preset_label)

        self.curve_preset_combo = ArrowComboBox()
        for i, name in enumerate(CurveEditorWidget.FACTORY_CURVES):
            self.curve_preset_combo.addItem(name, i)
        self.curve_preset_combo.setCurrentIndex(2)  # Linear default
        self.curve_preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.curve_preset_combo)
        preset_layout.addStretch()
        curve_layout.addLayout(preset_layout)

        bottom_layout.addWidget(curve_group)

        # Time Calibration Group
        time_group = QGroupBox(tr("VelocityTab", "Speed Calibration"))
        time_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        time_layout = QVBoxLayout()
        time_layout.setSpacing(15)
        time_group.setLayout(time_layout)

        # Description
        time_desc = QLabel(tr("VelocityTab",
            "Set the press speed range for velocity mapping.\n"
            "Fast press time = maximum velocity (127)\n"
            "Slow press time = minimum velocity (1)"))
        time_desc.setStyleSheet("color: gray; font-size: 9pt;")
        time_desc.setWordWrap(True)
        time_layout.addWidget(time_desc)

        # Fast press time (max velocity)
        fast_layout = QHBoxLayout()
        fast_label = QLabel(tr("VelocityTab", "Fast press (max vel):"))
        fast_label.setMinimumWidth(130)
        fast_layout.addWidget(fast_label)

        self.fast_time_spin = QSpinBox()
        self.fast_time_spin.setRange(5, 100)
        self.fast_time_spin.setValue(10)
        self.fast_time_spin.setSuffix(" ms")
        self.fast_time_spin.setMinimumWidth(80)
        self.fast_time_spin.valueChanged.connect(self.on_time_changed)
        fast_layout.addWidget(self.fast_time_spin)
        fast_layout.addStretch()
        time_layout.addLayout(fast_layout)

        # Slow press time (min velocity)
        slow_layout = QHBoxLayout()
        slow_label = QLabel(tr("VelocityTab", "Slow press (min vel):"))
        slow_label.setMinimumWidth(130)
        slow_layout.addWidget(slow_label)

        self.slow_time_spin = QSpinBox()
        self.slow_time_spin.setRange(10, 400)
        self.slow_time_spin.setValue(100)
        self.slow_time_spin.setSuffix(" ms")
        self.slow_time_spin.setMinimumWidth(80)
        self.slow_time_spin.valueChanged.connect(self.on_time_changed)
        slow_layout.addWidget(self.slow_time_spin)
        slow_layout.addStretch()
        time_layout.addLayout(slow_layout)

        time_layout.addStretch()

        # Save button
        save_time_btn = QPushButton(tr("VelocityTab", "Save to Keyboard"))
        save_time_btn.setMinimumHeight(35)
        save_time_btn.clicked.connect(self.on_save_time_settings)
        time_layout.addWidget(save_time_btn)

        bottom_layout.addWidget(time_group)

        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

        self.addStretch()

    def valid(self):
        # Only show if keyboard supports velocity features
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        self.keyboard = device.keyboard if device else None

        if self.keyboard:
            # Load velocity time settings from keyboard
            self.load_time_settings()
            # Rebuild keyboard widget
            self.keyboard_widget.set_keys(device.keyboard.keys, device.keyboard.encoders)
            # Scan for MIDI keys on current layer
            self.scan_midi_keys()

    def activate(self):
        """Called when tab becomes active"""
        self.is_active = True
        if self.keyboard:
            self.scan_midi_keys()
            self.poll_timer.start(self.poll_interval)

    def deactivate(self):
        """Called when tab becomes inactive"""
        self.is_active = False
        self.poll_timer.stop()
        self.keyboard_widget.clear_velocities()

    def on_layer_changed(self, button):
        """Handle layer selection change"""
        self.current_layer = self.layer_buttons.id(button)
        self.scan_midi_keys()

    def scan_midi_keys(self):
        """Scan current layer for MIDI note keycodes"""
        if not self.keyboard:
            return

        self.midi_keys = []

        # Iterate through all keys on the current layer
        for (layer, row, col), keycode in self.keyboard.layout.items():
            if layer != self.current_layer:
                continue

            # Check if this is a MIDI note keycode
            if is_midi_note_keycode(keycode):
                self.midi_keys.append((row, col))

        # Update keyboard widget
        self.keyboard_widget.set_midi_keys(self.midi_keys)

        # Update info label
        self.midi_info_label.setText(
            tr("VelocityTab", f"MIDI Keys on Layer {self.current_layer}: {len(self.midi_keys)}")
        )

    def poll_velocity(self):
        """Poll velocity values from keyboard"""
        if not self.keyboard or not self.is_active:
            return

        if not self.midi_keys:
            return

        # Poll in batches of 6 (firmware limit)
        for i in range(0, len(self.midi_keys), 6):
            batch = self.midi_keys[i:i+6]
            result = self.keyboard.velocity_matrix_poll(batch)

            if result:
                for (row, col), data in result.items():
                    velocity = data.get('velocity', 0)
                    self.keyboard_widget.set_velocity(row, col, velocity)

    def load_time_settings(self):
        """Load velocity time settings from keyboard"""
        if not self.keyboard:
            return

        result = self.keyboard.get_velocity_time_settings()
        if result:
            self.min_time = result.get('min_time', 100)
            self.max_time = result.get('max_time', 10)

            # Update spinboxes without triggering valueChanged
            self.slow_time_spin.blockSignals(True)
            self.fast_time_spin.blockSignals(True)
            self.slow_time_spin.setValue(self.min_time)
            self.fast_time_spin.setValue(self.max_time)
            self.slow_time_spin.blockSignals(False)
            self.fast_time_spin.blockSignals(False)

    def on_time_changed(self):
        """Handle time setting changes"""
        new_min = self.slow_time_spin.value()
        new_max = self.fast_time_spin.value()

        # Ensure max_time < min_time
        if new_max >= new_min:
            # Adjust to maintain valid relationship
            if self.sender() == self.fast_time_spin:
                # User changed fast time, adjust slow time
                self.slow_time_spin.blockSignals(True)
                self.slow_time_spin.setValue(new_max + 10)
                self.slow_time_spin.blockSignals(False)
                new_min = new_max + 10
            else:
                # User changed slow time, adjust fast time
                self.fast_time_spin.blockSignals(True)
                self.fast_time_spin.setValue(new_min - 10)
                self.fast_time_spin.blockSignals(False)
                new_max = new_min - 10

        # Send to keyboard immediately for real-time feedback
        if self.keyboard:
            self.keyboard.set_velocity_time_settings(new_min, new_max)

    def on_save_time_settings(self):
        """Save time settings to keyboard EEPROM"""
        if not self.keyboard:
            return

        success = self.keyboard.save_velocity_time_settings()
        if success:
            QMessageBox.information(
                None,
                tr("VelocityTab", "Settings Saved"),
                tr("VelocityTab", "Velocity time settings saved to keyboard.")
            )
        else:
            QMessageBox.warning(
                None,
                tr("VelocityTab", "Save Failed"),
                tr("VelocityTab", "Failed to save velocity time settings.")
            )

    def on_curve_changed(self):
        """Handle curve editor changes"""
        # The curve editor emits this when user drags control points
        # For now, just update the display - actual curve changes
        # would need to be sent to the keyboard
        pass

    def on_preset_changed(self, index):
        """Handle preset selection"""
        if index >= 0 and index < len(CurveEditorWidget.FACTORY_CURVES):
            # Load factory curve points into the curve editor
            points = CurveEditorWidget.FACTORY_CURVE_POINTS[index]
            self.curve_editor.set_points(points)

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
from protocol.keyboard_comm import (
    PARAM_PEAK_RETRIGGER_ENABLED, PARAM_PEAK_RETRIGGER_DISTANCE,
    PARAM_PEAK_SPEED_RATIO, PARAM_PEAK_ACTUATION_OVERRIDE_ENABLED,
    PARAM_PEAK_ACTUATION_OVERRIDE, PARAM_MIN_PRESS_TIME, PARAM_MAX_PRESS_TIME
)


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

            # KeyWidget2 uses rect property, not geometry() method
            # Also need to account for scale and shift transforms
            scale = self.scale * 1.3
            rect_x = int((widget.x + widget.shift_x) * scale)
            rect_y = int((widget.y + widget.shift_y) * scale)
            rect_w = int(widget.w * scale)
            rect_h = int(widget.h * scale)

            center_x = rect_x + rect_w // 2
            center_y = rect_y + rect_h // 2

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
                circle_size = min(rect_w, rect_h) * 0.6
                painter.drawEllipse(
                    int(center_x - circle_size/2),
                    int(center_y - circle_size/2),
                    int(circle_size),
                    int(circle_size)
                )

                # Draw velocity text
                painter.setPen(QPen(QColor(255, 255, 255) if velocity > 60 else QColor(0, 0, 0)))
                painter.drawText(
                    rect_x, rect_y, rect_w, rect_h,
                    Qt.AlignCenter,
                    str(velocity) if velocity > 0 else "-"
                )
            else:
                # Non-MIDI keys - show grayed out indicator
                painter.setPen(QPen(QColor(120, 120, 120, 100)))
                painter.setBrush(Qt.NoBrush)
                painter.drawText(
                    rect_x, rect_y, rect_w, rect_h,
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
        # Create scroll area for the main content - stretches to fill window
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Show horizontal scroll when needed
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_widget = QWidget()
        main_widget.setMinimumWidth(1000)  # Minimum 1000px width
        main_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_widget.setLayout(main_layout)

        scroll.setWidget(main_widget)
        self.addWidget(scroll, stretch=1)  # Allow scroll area to stretch

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

        # Save curve button
        save_curve_btn = QPushButton(tr("VelocityTab", "Save Curve to Keyboard"))
        save_curve_btn.setMinimumHeight(30)
        save_curve_btn.clicked.connect(self.on_save_curve)
        curve_layout.addWidget(save_curve_btn)

        bottom_layout.addWidget(curve_group)

        # Time Calibration Group
        time_group = QGroupBox(tr("VelocityTab", "Speed Calibration"))
        time_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        time_layout = QVBoxLayout()
        time_layout.setSpacing(15)
        time_group.setLayout(time_layout)

        # Velocity mode display
        self.velocity_mode_label = QLabel(tr("VelocityTab", "Velocity Mode: -"))
        self.velocity_mode_label.setStyleSheet("font-weight: bold; color: #4a90d9;")
        time_layout.addWidget(self.velocity_mode_label)

        # Description
        time_desc = QLabel(tr("VelocityTab",
            "Set the press speed range for velocity mapping.\n"
            "Fast press time = maximum velocity (127)\n"
            "Slow press time = minimum velocity (1)"))
        time_desc.setStyleSheet("color: gray; font-size: 9pt;")
        time_desc.setWordWrap(True)
        time_layout.addWidget(time_desc)

        # Warning label for modes that don't use time settings
        self.time_warning_label = QLabel(tr("VelocityTab",
            "⚠ Time settings only apply to Mode 2 (Speed) and Mode 3 (Combined)"))
        self.time_warning_label.setStyleSheet("color: #ff9800; font-size: 9pt;")
        self.time_warning_label.setWordWrap(True)
        self.time_warning_label.hide()  # Hidden by default
        time_layout.addWidget(self.time_warning_label)

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

        # Mode 3 (Speed+Peak) Settings Group
        mode3_group = QGroupBox(tr("VelocityTab", "Mode 3 (Speed+Peak) Settings"))
        mode3_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        mode3_layout = QVBoxLayout()
        mode3_layout.setSpacing(10)
        mode3_group.setLayout(mode3_layout)

        # Re-trigger enable checkbox
        self.retrigger_checkbox = QCheckBox(tr("VelocityTab", "Enable Partial Release Re-triggering"))
        self.retrigger_checkbox.setChecked(True)
        self.retrigger_checkbox.setToolTip(
            "When enabled, releasing a key partially and pressing again triggers a new note.\n"
            "The velocity is scaled by how much the key was released."
        )
        self.retrigger_checkbox.stateChanged.connect(self.on_mode3_setting_changed)
        mode3_layout.addWidget(self.retrigger_checkbox)

        # Re-trigger distance slider (0.2mm - 1.5mm)
        retrigger_dist_layout = QHBoxLayout()
        retrigger_dist_label = QLabel(tr("VelocityTab", "Re-trigger Distance:"))
        retrigger_dist_label.setMinimumWidth(130)
        retrigger_dist_layout.addWidget(retrigger_dist_label)

        self.retrigger_dist_slider = QSlider(Qt.Horizontal)
        self.retrigger_dist_slider.setRange(12, 90)  # 0.2mm to 1.5mm in units
        self.retrigger_dist_slider.setValue(12)
        self.retrigger_dist_slider.setTickPosition(QSlider.TicksBelow)
        self.retrigger_dist_slider.setTickInterval(13)
        self.retrigger_dist_slider.valueChanged.connect(self.on_retrigger_dist_changed)
        retrigger_dist_layout.addWidget(self.retrigger_dist_slider)

        self.retrigger_dist_value = QLabel("0.2 mm")
        self.retrigger_dist_value.setMinimumWidth(50)
        retrigger_dist_layout.addWidget(self.retrigger_dist_value)
        mode3_layout.addLayout(retrigger_dist_layout)

        # Speed:Peak ratio slider (0-100)
        ratio_layout = QHBoxLayout()
        ratio_label = QLabel(tr("VelocityTab", "Speed:Peak Ratio:"))
        ratio_label.setMinimumWidth(130)
        ratio_layout.addWidget(ratio_label)

        self.speed_ratio_slider = QSlider(Qt.Horizontal)
        self.speed_ratio_slider.setRange(0, 100)
        self.speed_ratio_slider.setValue(50)
        self.speed_ratio_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_ratio_slider.setTickInterval(25)
        self.speed_ratio_slider.valueChanged.connect(self.on_speed_ratio_changed)
        ratio_layout.addWidget(self.speed_ratio_slider)

        self.speed_ratio_value = QLabel("50:50")
        self.speed_ratio_value.setMinimumWidth(50)
        ratio_layout.addWidget(self.speed_ratio_value)
        mode3_layout.addLayout(ratio_layout)

        # Actuation override checkbox and slider
        self.actuation_override_checkbox = QCheckBox(tr("VelocityTab", "Override Per-Key Actuation"))
        self.actuation_override_checkbox.setChecked(False)
        self.actuation_override_checkbox.setToolTip(
            "Override the per-key actuation point for Mode 3.\n"
            "Useful to set a consistent trigger point across all keys."
        )
        self.actuation_override_checkbox.stateChanged.connect(self.on_mode3_setting_changed)
        mode3_layout.addWidget(self.actuation_override_checkbox)

        actuation_layout = QHBoxLayout()
        actuation_label = QLabel(tr("VelocityTab", "Actuation Point:"))
        actuation_label.setMinimumWidth(130)
        actuation_layout.addWidget(actuation_label)

        self.actuation_slider = QSlider(Qt.Horizontal)
        self.actuation_slider.setRange(0, 240)  # 0-4mm in units (60 units per mm)
        self.actuation_slider.setValue(120)  # 2mm default
        self.actuation_slider.setTickPosition(QSlider.TicksBelow)
        self.actuation_slider.setTickInterval(60)
        self.actuation_slider.valueChanged.connect(self.on_actuation_override_changed)
        self.actuation_slider.setEnabled(False)  # Disabled until checkbox is checked
        actuation_layout.addWidget(self.actuation_slider)

        self.actuation_value = QLabel("2.0 mm")
        self.actuation_value.setMinimumWidth(50)
        actuation_layout.addWidget(self.actuation_value)
        mode3_layout.addLayout(actuation_layout)

        mode3_layout.addStretch()

        # Save Mode 3 settings button
        save_mode3_btn = QPushButton(tr("VelocityTab", "Save Mode 3 Settings"))
        save_mode3_btn.setMinimumHeight(35)
        save_mode3_btn.clicked.connect(self.on_save_mode3_settings)
        mode3_layout.addWidget(save_mode3_btn)

        bottom_layout.addWidget(mode3_group)

        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

    def valid(self):
        """This tab is always valid for VialKeyboard devices"""
        return isinstance(self.device, VialKeyboard)

    def rebuild(self, device):
        super().rebuild(device)
        if not self.valid():
            return

        self.keyboard = device.keyboard

        try:
            # Rebuild keyboard widget
            self.keyboard_widget.set_keys(self.keyboard.keys, self.keyboard.encoders)
            # Load velocity time settings from keyboard
            self.load_time_settings()
            # Load velocity curve from keyboard
            self.load_velocity_curve()
            # Load velocity mode for current layer
            self.load_velocity_mode()
            # Load Mode 3 settings
            self.load_mode3_settings()
            # Scan for MIDI keys on current layer
            self.scan_midi_keys()
        except Exception as e:
            print(f"VelocityTab rebuild error: {e}")

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
        self.load_velocity_mode()

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
        """Load velocity time settings from keyboard via get_midi_config"""
        if not self.keyboard:
            return

        try:
            # Time settings are part of keyboard_settings, loaded via get_midi_config
            config = self.keyboard.get_midi_config()
            if config:
                # These might be in the config if firmware sends them
                # For now, use defaults if not available
                self.min_time = config.get('min_press_time', 200)
                self.max_time = config.get('max_press_time', 20)

                # Update spinboxes without triggering valueChanged
                self.slow_time_spin.blockSignals(True)
                self.fast_time_spin.blockSignals(True)
                self.slow_time_spin.setValue(self.min_time)
                self.fast_time_spin.setValue(self.max_time)
                self.slow_time_spin.blockSignals(False)
                self.fast_time_spin.blockSignals(False)
        except Exception as e:
            print(f"Error loading time settings: {e}")

    def on_time_changed(self):
        """Handle time setting changes - uses set_keyboard_param_single like keymap_editor"""
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

        # Send to keyboard immediately using set_keyboard_param_single (same as keymap_editor)
        if self.keyboard:
            # PARAM_MIN_PRESS_TIME and PARAM_MAX_PRESS_TIME are 16-bit values
            self.keyboard.set_keyboard_param_single(PARAM_MIN_PRESS_TIME, new_min)
            self.keyboard.set_keyboard_param_single(PARAM_MAX_PRESS_TIME, new_max)

    def on_save_time_settings(self):
        """Save time settings - settings are applied via set_keyboard_param_single"""
        if not self.keyboard:
            return

        # Settings are already applied via set_keyboard_param_single
        # They update both the RAM variable and keyboard_settings struct
        # To persist to EEPROM, user should save via MIDI Settings tab
        QMessageBox.information(
            None,
            tr("VelocityTab", "Settings Applied"),
            tr("VelocityTab", "Speed settings are active.\n\nTo save permanently, use 'MIDI Settings' tab → Save Settings → Save as Default.")
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

    def load_velocity_curve(self):
        """Load current velocity curve from keyboard"""
        if not self.keyboard:
            return

        try:
            # Get keyboard config which includes velocity curve
            config = self.keyboard.get_keyboard_config()
            if config:
                curve_index = config.get('he_velocity_curve', 2)  # Default to Linear (2)
                if 0 <= curve_index < len(CurveEditorWidget.FACTORY_CURVES):
                    self.curve_preset_combo.blockSignals(True)
                    self.curve_preset_combo.setCurrentIndex(curve_index)
                    self.curve_preset_combo.blockSignals(False)
                    # Update the curve editor display
                    points = CurveEditorWidget.FACTORY_CURVE_POINTS[curve_index]
                    self.curve_editor.set_points(points)
        except Exception as e:
            print(f"Error loading velocity curve: {e}")

    def load_velocity_mode(self):
        """Load and display velocity mode for current layer"""
        if not self.keyboard:
            return

        try:
            # Get layer actuation settings which include velocity mode
            result = self.keyboard.get_layer_actuation(self.current_layer)
            if result:
                velocity_mode = result.get('velocity', 0)
                mode_names = {
                    0: "Fixed",
                    1: "Peak Travel",
                    2: "Speed",
                    3: "Combined (Speed + Peak)"
                }
                mode_name = mode_names.get(velocity_mode, f"Unknown ({velocity_mode})")
                self.velocity_mode_label.setText(
                    tr("VelocityTab", f"Velocity Mode: {mode_name}")
                )

                # Show warning if mode doesn't use time settings
                if velocity_mode in (0, 1):
                    self.time_warning_label.show()
                else:
                    self.time_warning_label.hide()
        except Exception as e:
            print(f"Error loading velocity mode: {e}")

    def on_save_curve(self):
        """Save velocity curve selection to keyboard"""
        if not self.keyboard:
            return

        curve_index = self.curve_preset_combo.currentIndex()

        try:
            # Use set_keyboard_param_single to set the velocity curve
            # PARAM_HE_VELOCITY_CURVE = 4 (from keyboard_comm.py constants)
            success = self.keyboard.set_keyboard_param_single(4, curve_index)
            if success:
                QMessageBox.information(
                    None,
                    tr("VelocityTab", "Curve Saved"),
                    tr("VelocityTab", f"Velocity curve '{CurveEditorWidget.FACTORY_CURVES[curve_index]}' saved to keyboard.")
                )
            else:
                QMessageBox.warning(
                    None,
                    tr("VelocityTab", "Save Failed"),
                    tr("VelocityTab", "Failed to save velocity curve.")
                )
        except Exception as e:
            QMessageBox.warning(
                None,
                tr("VelocityTab", "Save Failed"),
                tr("VelocityTab", f"Error saving curve: {e}")
            )

    def on_retrigger_dist_changed(self, value):
        """Update re-trigger distance display and send to keyboard"""
        mm_value = value / 60.0  # Convert units to mm (60 units per mm)
        self.retrigger_dist_value.setText(f"{mm_value:.1f} mm")
        # Send to keyboard immediately for real-time feedback
        if self.keyboard:
            self.keyboard.set_keyboard_param_single(PARAM_PEAK_RETRIGGER_DISTANCE, value)

    def on_speed_ratio_changed(self, value):
        """Update speed:peak ratio display and send to keyboard"""
        peak_ratio = 100 - value
        self.speed_ratio_value.setText(f"{value}:{peak_ratio}")
        # Send to keyboard immediately for real-time feedback
        if self.keyboard:
            self.keyboard.set_keyboard_param_single(PARAM_PEAK_SPEED_RATIO, value)

    def on_actuation_override_changed(self, value):
        """Update actuation override display and send to keyboard"""
        mm_value = value / 60.0  # Convert units to mm (60 units per mm)
        self.actuation_value.setText(f"{mm_value:.1f} mm")
        # Send to keyboard immediately for real-time feedback
        if self.keyboard and self.actuation_override_checkbox.isChecked():
            self.keyboard.set_keyboard_param_single(PARAM_PEAK_ACTUATION_OVERRIDE, value)

    def on_mode3_setting_changed(self):
        """Handle Mode 3 checkbox changes"""
        if not self.keyboard:
            return

        # Handle re-trigger enable
        if self.sender() == self.retrigger_checkbox:
            enabled = self.retrigger_checkbox.isChecked()
            self.keyboard.set_keyboard_param_single(PARAM_PEAK_RETRIGGER_ENABLED, 1 if enabled else 0)
            # Enable/disable the distance slider
            self.retrigger_dist_slider.setEnabled(enabled)

        # Handle actuation override enable
        if self.sender() == self.actuation_override_checkbox:
            enabled = self.actuation_override_checkbox.isChecked()
            self.keyboard.set_keyboard_param_single(PARAM_PEAK_ACTUATION_OVERRIDE_ENABLED, 1 if enabled else 0)
            # Enable/disable the actuation slider
            self.actuation_slider.setEnabled(enabled)
            # Send the actuation value if enabling
            if enabled:
                self.keyboard.set_keyboard_param_single(
                    PARAM_PEAK_ACTUATION_OVERRIDE, self.actuation_slider.value()
                )

    def on_save_mode3_settings(self):
        """Save Mode 3 settings - settings are applied via set_keyboard_param_single"""
        if not self.keyboard:
            return

        # Settings are already applied via set_keyboard_param_single
        # They update both the RAM variable and keyboard_settings struct
        # To persist to EEPROM, user should save via MIDI Settings tab
        QMessageBox.information(
            None,
            tr("VelocityTab", "Settings Applied"),
            tr("VelocityTab", "Mode 3 settings are active.\n\nTo save permanently, use 'MIDI Settings' tab → Save Settings → Save as Default.")
        )

    def load_mode3_settings(self):
        """Load Mode 3 settings from keyboard"""
        if not self.keyboard:
            return

        try:
            config = self.keyboard.get_keyboard_config()
            if config:
                # Load re-trigger enabled
                retrigger_enabled = config.get('peak_retrigger_enabled', True)
                self.retrigger_checkbox.blockSignals(True)
                self.retrigger_checkbox.setChecked(retrigger_enabled)
                self.retrigger_checkbox.blockSignals(False)
                self.retrigger_dist_slider.setEnabled(retrigger_enabled)

                # Load re-trigger distance
                retrigger_dist = config.get('peak_retrigger_distance', 12)
                self.retrigger_dist_slider.blockSignals(True)
                self.retrigger_dist_slider.setValue(retrigger_dist)
                self.retrigger_dist_slider.blockSignals(False)
                self.retrigger_dist_value.setText(f"{retrigger_dist / 60.0:.1f} mm")

                # Load speed ratio
                speed_ratio = config.get('peak_speed_ratio', 50)
                self.speed_ratio_slider.blockSignals(True)
                self.speed_ratio_slider.setValue(speed_ratio)
                self.speed_ratio_slider.blockSignals(False)
                self.speed_ratio_value.setText(f"{speed_ratio}:{100 - speed_ratio}")

                # Load actuation override enabled
                actuation_enabled = config.get('peak_actuation_override_enabled', False)
                self.actuation_override_checkbox.blockSignals(True)
                self.actuation_override_checkbox.setChecked(actuation_enabled)
                self.actuation_override_checkbox.blockSignals(False)
                self.actuation_slider.setEnabled(actuation_enabled)

                # Load actuation override value
                actuation_value = config.get('peak_actuation_override', 120)
                self.actuation_slider.blockSignals(True)
                self.actuation_slider.setValue(actuation_value)
                self.actuation_slider.blockSignals(False)
                self.actuation_value.setText(f"{actuation_value / 60.0:.1f} mm")
        except Exception as e:
            print(f"Error loading Mode 3 settings: {e}")

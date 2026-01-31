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
from editor.arpeggiator import DebugConsole
from themes import Theme
from util import tr
from vial_device import VialKeyboard
from protocol.keyboard_comm import (
    PARAM_VELOCITY_MODE, PARAM_AFTERTOUCH_MODE, PARAM_AFTERTOUCH_CC,
    PARAM_VIBRATO_SENSITIVITY, PARAM_VIBRATO_DECAY_TIME,
    PARAM_MIN_PRESS_TIME, PARAM_MAX_PRESS_TIME,
    HID_CMD_SET_KEYBOARD_PARAM_SINGLE
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

        # Global MIDI settings for velocity/aftertouch
        self.global_midi_settings = {
            'velocity_mode': 2,         # 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
            'aftertouch_mode': 0,       # 0=Off, 1=Reverse, 2=Bottom-out, 3=Post-actuation, 4=Vibrato
            'aftertouch_cc': 255,       # 0-127=CC number, 255=off (poly AT only)
            'vibrato_sensitivity': 100, # 50-200 (percentage)
            'vibrato_decay_time': 200,  # 0-2000 (milliseconds)
            'min_press_time': 200,      # 50-500ms (slow press threshold)
            'max_press_time': 20        # 5-100ms (fast press threshold)
        }

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

        # Advanced Settings Group (velocity, aftertouch settings) - GLOBAL settings
        advanced_group = QGroupBox(tr("VelocityTab", "Advanced Settings"))
        advanced_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        advanced_layout = QVBoxLayout()
        advanced_layout.setSpacing(6)
        advanced_group.setLayout(advanced_layout)

        # Global settings header
        header_label = QLabel(tr("VelocityTab", "Global MIDI Settings"))
        header_label.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; color: #333; }")
        advanced_layout.addWidget(header_label, alignment=Qt.AlignCenter)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        advanced_layout.addWidget(line)

        # Velocity Mode combo
        velocity_layout = QHBoxLayout()
        velocity_layout.setContentsMargins(0, 0, 0, 0)
        velocity_layout.setSpacing(4)
        velocity_layout.addWidget(self.create_help_label(
            "How MIDI velocity is calculated:\n"
            "Fixed (64): Always sends velocity 64\n"
            "Peak at Apex: Velocity based on key apex position\n"
            "Speed-Based: Velocity based on key press speed\n"
            "Speed + Peak: Combines speed and apex methods"
        ))
        velocity_label = QLabel(tr("VelocityTab", "Velocity:"))
        velocity_label.setMinimumWidth(95)
        velocity_layout.addWidget(velocity_label)

        self.velocity_combo = ArrowComboBox()
        self.velocity_combo.setMaximumHeight(25)
        self.velocity_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 10px; text-align: center; }")
        self.velocity_combo.addItem("Fixed (64)", 0)
        self.velocity_combo.addItem("Peak at Apex", 1)
        self.velocity_combo.addItem("Speed-Based", 2)
        self.velocity_combo.addItem("Speed + Peak", 3)
        self.velocity_combo.setCurrentIndex(2)
        self.velocity_combo.setEditable(True)
        self.velocity_combo.lineEdit().setReadOnly(True)
        self.velocity_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.velocity_combo.currentIndexChanged.connect(self.on_velocity_mode_changed)
        velocity_layout.addWidget(self.velocity_combo, 1)
        advanced_layout.addLayout(velocity_layout)

        # Min Press Time slider (for slow press = min velocity)
        min_press_layout = QHBoxLayout()
        min_press_layout.setContentsMargins(0, 0, 0, 0)
        min_press_layout.setSpacing(4)
        min_press_layout.addWidget(self.create_help_label(
            "Slow press threshold (ms):\n"
            "Keys pressed slower than this time get minimum velocity.\n"
            "Lower = need slower press for soft notes."
        ))
        min_press_label = QLabel(tr("VelocityTab", "Slow Press:"))
        min_press_label.setMinimumWidth(95)
        min_press_layout.addWidget(min_press_label)

        self.min_press_slider = QSlider(Qt.Horizontal)
        self.min_press_slider.setMinimum(50)
        self.min_press_slider.setMaximum(500)
        self.min_press_slider.setValue(200)
        self.min_press_slider.valueChanged.connect(self.on_min_press_changed)
        min_press_layout.addWidget(self.min_press_slider, 1)

        self.min_press_value = QLabel("200ms")
        self.min_press_value.setMinimumWidth(50)
        self.min_press_value.setStyleSheet("QLabel { font-weight: bold; }")
        min_press_layout.addWidget(self.min_press_value)
        advanced_layout.addLayout(min_press_layout)

        # Max Press Time slider (for fast press = max velocity)
        max_press_layout = QHBoxLayout()
        max_press_layout.setContentsMargins(0, 0, 0, 0)
        max_press_layout.setSpacing(4)
        max_press_layout.addWidget(self.create_help_label(
            "Fast press threshold (ms):\n"
            "Keys pressed faster than this time get maximum velocity.\n"
            "Higher = need faster press for loud notes."
        ))
        max_press_label = QLabel(tr("VelocityTab", "Fast Press:"))
        max_press_label.setMinimumWidth(95)
        max_press_layout.addWidget(max_press_label)

        self.max_press_slider = QSlider(Qt.Horizontal)
        self.max_press_slider.setMinimum(5)
        self.max_press_slider.setMaximum(100)
        self.max_press_slider.setValue(20)
        self.max_press_slider.valueChanged.connect(self.on_max_press_changed)
        max_press_layout.addWidget(self.max_press_slider, 1)

        self.max_press_value = QLabel("20ms")
        self.max_press_value.setMinimumWidth(50)
        self.max_press_value.setStyleSheet("QLabel { font-weight: bold; }")
        max_press_layout.addWidget(self.max_press_value)
        advanced_layout.addLayout(max_press_layout)

        # Separator between velocity and aftertouch
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        advanced_layout.addWidget(line2)

        # Aftertouch Mode dropdown
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(4)
        mode_layout.addWidget(self.create_help_label(
            "Aftertouch pressure behavior:\n"
            "Off: No aftertouch\n"
            "Reverse: Pressure on key release\n"
            "Bottom-Out: Pressure when fully pressed\n"
            "Post-Actuation: Pressure after actuation point\n"
            "Vibrato: Wiggle key for more aftertouch value"
        ))
        mode_label = QLabel(tr("VelocityTab", "Aftertouch Mode:"))
        mode_label.setMinimumWidth(95)
        mode_layout.addWidget(mode_label)

        self.aftertouch_mode_combo = ArrowComboBox()
        self.aftertouch_mode_combo.setMaximumHeight(25)
        self.aftertouch_mode_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 10px; }")
        self.aftertouch_mode_combo.setEditable(True)
        self.aftertouch_mode_combo.lineEdit().setReadOnly(True)
        self.aftertouch_mode_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.aftertouch_mode_combo.addItem("Off", 0)
        self.aftertouch_mode_combo.addItem("Reverse", 1)
        self.aftertouch_mode_combo.addItem("Bottom-Out", 2)
        self.aftertouch_mode_combo.addItem("Post-Actuation", 3)
        self.aftertouch_mode_combo.addItem("Vibrato", 4)
        self.aftertouch_mode_combo.setCurrentIndex(0)
        self.aftertouch_mode_combo.currentIndexChanged.connect(self.on_aftertouch_mode_changed)
        mode_layout.addWidget(self.aftertouch_mode_combo, 1)
        advanced_layout.addLayout(mode_layout)

        # Aftertouch CC dropdown
        cc_layout = QHBoxLayout()
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(4)
        cc_layout.addWidget(self.create_help_label("MIDI CC number to send for aftertouch.\nOff: Send standard aftertouch messages\nCC#0-127: Send specified CC instead"))
        cc_label = QLabel(tr("VelocityTab", "Aftertouch CC:"))
        cc_label.setMinimumWidth(95)
        cc_layout.addWidget(cc_label)

        self.aftertouch_cc_combo = ArrowComboBox()
        self.aftertouch_cc_combo.setMaximumHeight(25)
        self.aftertouch_cc_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 10px; }")
        self.aftertouch_cc_combo.setEditable(True)
        self.aftertouch_cc_combo.lineEdit().setReadOnly(True)
        self.aftertouch_cc_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.aftertouch_cc_combo.addItem("Off", 255)
        for cc in range(128):
            self.aftertouch_cc_combo.addItem(f"CC#{cc}", cc)
        self.aftertouch_cc_combo.setCurrentIndex(0)
        self.aftertouch_cc_combo.currentIndexChanged.connect(self.on_aftertouch_cc_changed)
        cc_layout.addWidget(self.aftertouch_cc_combo, 1)
        advanced_layout.addLayout(cc_layout)

        # Vibrato Sensitivity slider (hidden by default)
        self.vibrato_sens_widget = QWidget()
        sens_layout = QHBoxLayout()
        sens_layout.setContentsMargins(0, 0, 0, 0)
        self.vibrato_sens_widget.setLayout(sens_layout)

        sens_layout.addWidget(self.create_help_label("Wiggle key more = more aftertouch value.\n50% = Less sensitive, 200% = Very sensitive"))
        sens_label = QLabel(tr("VelocityTab", "Vibrato Sensitivity:"))
        sens_label.setMinimumWidth(95)
        sens_layout.addWidget(sens_label)

        self.vibrato_sens_slider = QSlider(Qt.Horizontal)
        self.vibrato_sens_slider.setMinimum(50)
        self.vibrato_sens_slider.setMaximum(200)
        self.vibrato_sens_slider.setValue(100)
        self.vibrato_sens_slider.valueChanged.connect(self.on_vibrato_sensitivity_changed)
        sens_layout.addWidget(self.vibrato_sens_slider, 1)

        self.vibrato_sens_value = QLabel("100%")
        self.vibrato_sens_value.setMinimumWidth(45)
        self.vibrato_sens_value.setStyleSheet("QLabel { font-weight: bold; }")
        sens_layout.addWidget(self.vibrato_sens_value)

        advanced_layout.addWidget(self.vibrato_sens_widget)
        self.vibrato_sens_widget.setVisible(False)

        # Vibrato Decay Time slider (hidden by default)
        self.vibrato_decay_widget = QWidget()
        decay_layout = QHBoxLayout()
        decay_layout.setContentsMargins(0, 0, 0, 0)
        self.vibrato_decay_widget.setLayout(decay_layout)

        decay_layout.addWidget(self.create_help_label("How long aftertouch value lasts after key wiggle stops.\n0ms = Instant decay, 2000ms = Slow decay"))
        decay_label = QLabel(tr("VelocityTab", "Vibrato Decay:"))
        decay_label.setMinimumWidth(95)
        decay_layout.addWidget(decay_label)

        self.vibrato_decay_slider = QSlider(Qt.Horizontal)
        self.vibrato_decay_slider.setMinimum(0)
        self.vibrato_decay_slider.setMaximum(2000)
        self.vibrato_decay_slider.setValue(200)
        self.vibrato_decay_slider.valueChanged.connect(self.on_vibrato_decay_changed)
        decay_layout.addWidget(self.vibrato_decay_slider, 1)

        self.vibrato_decay_value = QLabel("200ms")
        self.vibrato_decay_value.setMinimumWidth(50)
        self.vibrato_decay_value.setStyleSheet("QLabel { font-weight: bold; }")
        decay_layout.addWidget(self.vibrato_decay_value)

        advanced_layout.addWidget(self.vibrato_decay_widget)
        self.vibrato_decay_widget.setVisible(False)

        advanced_layout.addStretch()

        # Save button
        self.advanced_save_btn = QPushButton(tr("VelocityTab", "Save Advanced Settings"))
        self.advanced_save_btn.setMinimumHeight(30)
        self.advanced_save_btn.clicked.connect(self.on_save_advanced)
        advanced_layout.addWidget(self.advanced_save_btn)

        # Debug console for HID communication debugging
        self.advanced_debug_console = DebugConsole("Advanced Settings Debug Console")
        advanced_layout.addWidget(self.advanced_debug_console)

        bottom_layout.addWidget(advanced_group)

        main_layout.addLayout(bottom_layout)
        main_layout.addStretch()

    def create_help_label(self, tooltip_text):
        """Create a small question mark button with tooltip for help"""
        help_btn = QPushButton("?")
        help_btn.setStyleSheet("""
            QPushButton {
                color: #888;
                font-weight: bold;
                font-size: 9pt;
                border: 1px solid #888;
                border-radius: 9px;
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
                padding: 0px;
                margin: 0px;
                background: transparent;
            }
            QPushButton:hover {
                color: #fff;
                background-color: #555;
                border-color: #fff;
            }
        """)
        help_btn.setToolTip(tooltip_text)
        help_btn.setFocusPolicy(Qt.NoFocus)
        return help_btn

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
            # Load advanced settings from keyboard
            self.load_advanced_settings()
            # Load velocity curve from keyboard
            self.load_velocity_curve()
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

    def load_advanced_settings(self):
        """Load advanced settings (velocity, aftertouch) from keyboard"""
        if not self.keyboard:
            return

        try:
            # Get layer actuation settings which include all the MIDI settings
            result = self.keyboard.get_layer_actuation(0)  # Use layer 0 for global settings
            if result:
                # Load velocity mode
                velocity_mode = result.get('velocity', 2)
                self.global_midi_settings['velocity_mode'] = velocity_mode
                self.velocity_combo.blockSignals(True)
                for i in range(self.velocity_combo.count()):
                    if self.velocity_combo.itemData(i) == velocity_mode:
                        self.velocity_combo.setCurrentIndex(i)
                        break
                self.velocity_combo.blockSignals(False)

                # Load aftertouch mode
                aftertouch_mode = result.get('aftertouch_mode', 0)
                self.global_midi_settings['aftertouch_mode'] = aftertouch_mode
                self.aftertouch_mode_combo.blockSignals(True)
                self.aftertouch_mode_combo.setCurrentIndex(aftertouch_mode)
                self.aftertouch_mode_combo.blockSignals(False)
                # Show/hide vibrato controls based on mode
                is_vibrato = (aftertouch_mode == 4)
                self.vibrato_sens_widget.setVisible(is_vibrato)
                self.vibrato_decay_widget.setVisible(is_vibrato)

                # Load aftertouch CC
                aftertouch_cc = result.get('aftertouch_cc', 255)
                self.global_midi_settings['aftertouch_cc'] = aftertouch_cc
                self.aftertouch_cc_combo.blockSignals(True)
                if aftertouch_cc == 255:
                    self.aftertouch_cc_combo.setCurrentIndex(0)  # Off
                else:
                    self.aftertouch_cc_combo.setCurrentIndex(aftertouch_cc + 1)  # CC#0-127
                self.aftertouch_cc_combo.blockSignals(False)

                # Load vibrato sensitivity
                vibrato_sens = result.get('vibrato_sensitivity', 100)
                self.global_midi_settings['vibrato_sensitivity'] = vibrato_sens
                self.vibrato_sens_slider.blockSignals(True)
                self.vibrato_sens_slider.setValue(vibrato_sens)
                self.vibrato_sens_slider.blockSignals(False)
                self.vibrato_sens_value.setText(f"{vibrato_sens}%")

                # Load vibrato decay time
                vibrato_decay = result.get('vibrato_decay_time', 200)
                self.global_midi_settings['vibrato_decay_time'] = vibrato_decay
                self.vibrato_decay_slider.blockSignals(True)
                self.vibrato_decay_slider.setValue(vibrato_decay)
                self.vibrato_decay_slider.blockSignals(False)
                self.vibrato_decay_value.setText(f"{vibrato_decay}ms")

            # Load press time settings from velocity time settings
            time_result = self.keyboard.get_velocity_time_settings()
            if time_result:
                min_time = time_result.get('min_time', 200)
                max_time = time_result.get('max_time', 20)
                self.global_midi_settings['min_press_time'] = min_time
                self.global_midi_settings['max_press_time'] = max_time

                self.min_press_slider.blockSignals(True)
                self.min_press_slider.setValue(min_time)
                self.min_press_slider.blockSignals(False)
                self.min_press_value.setText(f"{min_time}ms")

                self.max_press_slider.blockSignals(True)
                self.max_press_slider.setValue(max_time)
                self.max_press_slider.blockSignals(False)
                self.max_press_value.setText(f"{max_time}ms")

        except Exception as e:
            print(f"Error loading advanced settings: {e}")

    def on_velocity_mode_changed(self, index):
        """Handle velocity mode change (GLOBAL)"""
        mode = self.velocity_combo.currentData()
        self.global_midi_settings['velocity_mode'] = mode

    def on_min_press_changed(self, value):
        """Handle min press time slider change (GLOBAL)"""
        self.min_press_value.setText(f"{value}ms")
        self.global_midi_settings['min_press_time'] = value

    def on_max_press_changed(self, value):
        """Handle max press time slider change (GLOBAL)"""
        self.max_press_value.setText(f"{value}ms")
        self.global_midi_settings['max_press_time'] = value

    def on_aftertouch_mode_changed(self, index):
        """Handle aftertouch mode change - show/hide vibrato controls (GLOBAL)"""
        mode = self.aftertouch_mode_combo.currentData()
        is_vibrato = (mode == 4)
        self.vibrato_sens_widget.setVisible(is_vibrato)
        self.vibrato_decay_widget.setVisible(is_vibrato)
        self.global_midi_settings['aftertouch_mode'] = mode

    def on_aftertouch_cc_changed(self, index):
        """Handle aftertouch CC change (GLOBAL)"""
        cc = self.aftertouch_cc_combo.currentData()
        self.global_midi_settings['aftertouch_cc'] = cc

    def on_vibrato_sensitivity_changed(self, value):
        """Handle vibrato sensitivity slider change (GLOBAL)"""
        self.vibrato_sens_value.setText(f"{value}%")
        self.global_midi_settings['vibrato_sensitivity'] = value

    def on_vibrato_decay_changed(self, value):
        """Handle vibrato decay slider change (GLOBAL)"""
        self.vibrato_decay_value.setText(f"{value}ms")
        self.global_midi_settings['vibrato_decay_time'] = value

    def on_save_advanced(self):
        """Save advanced settings (velocity, aftertouch) to keyboard - GLOBAL settings"""
        # Start debug console operation
        self.advanced_debug_console.mark_operation_start()
        self.advanced_debug_console.log("=" * 50, "DEBUG")
        self.advanced_debug_console.log("SAVE ADVANCED SETTINGS - Starting", "INFO")
        self.advanced_debug_console.log("=" * 50, "DEBUG")

        try:
            if not self.keyboard:
                self.advanced_debug_console.log("ERROR: Device not connected", "ERROR")
                self.advanced_debug_console.mark_operation_end(success=False)
                raise RuntimeError("Device not connected")

            settings = self.global_midi_settings
            kb = self.keyboard

            # Log HID command info
            self.advanced_debug_console.log(f"HID Command: SET_KEYBOARD_PARAM_SINGLE (0x{HID_CMD_SET_KEYBOARD_PARAM_SINGLE:02X})", "DEBUG")
            self.advanced_debug_console.log("-" * 50, "DEBUG")

            # Define parameters to save with their names and value ranges
            params_to_save = [
                ("VELOCITY_MODE", PARAM_VELOCITY_MODE, settings.get('velocity_mode', 2), "0-3 (Fixed/Peak/Speed/Speed+Peak)"),
                ("AFTERTOUCH_MODE", PARAM_AFTERTOUCH_MODE, settings.get('aftertouch_mode', 0), "0-4 (Off/Reverse/Bottom/Post/Vibrato)"),
                ("AFTERTOUCH_CC", PARAM_AFTERTOUCH_CC, settings.get('aftertouch_cc', 255), "0-127 or 255=Off"),
                ("VIBRATO_SENSITIVITY", PARAM_VIBRATO_SENSITIVITY, settings.get('vibrato_sensitivity', 100), "50-200 (percentage)"),
                ("VIBRATO_DECAY_TIME", PARAM_VIBRATO_DECAY_TIME, settings.get('vibrato_decay_time', 200), "0-2000ms (16-bit)"),
                ("MIN_PRESS_TIME", PARAM_MIN_PRESS_TIME, settings.get('min_press_time', 200), "50-500ms (16-bit)"),
                ("MAX_PRESS_TIME", PARAM_MAX_PRESS_TIME, settings.get('max_press_time', 20), "5-100ms (16-bit)"),
            ]

            failed_params = []
            success_count = 0

            for param_name, param_id, value, value_range in params_to_save:
                self.advanced_debug_console.log(f"[{param_name}] Sending param_id={param_id}, value={value} ({value_range})", "DEBUG")

                # Call the detailed version that returns debug info
                success, debug_info = kb.set_keyboard_param_single_debug(param_id, value)

                # Log the detailed debug info
                if debug_info:
                    self.advanced_debug_console.log(f"  TX Packet: {debug_info.get('tx_packet', 'N/A')}", "DEBUG")
                    self.advanced_debug_console.log(f"  TX Data: {debug_info.get('tx_data', 'N/A')}", "DEBUG")
                    self.advanced_debug_console.log(f"  RX Response: {debug_info.get('rx_response', 'N/A')}", "DEBUG")
                    self.advanced_debug_console.log(f"  Status byte (response[5]): {debug_info.get('status_byte', 'N/A')}", "DEBUG")
                    self.advanced_debug_console.log(f"  Attempts: {debug_info.get('attempts', 'N/A')}", "DEBUG")

                if success:
                    self.advanced_debug_console.log(f"  -> SUCCESS", "INFO")
                    success_count += 1
                else:
                    error_msg = debug_info.get('error', 'Unknown error') if debug_info else 'Unknown error'
                    self.advanced_debug_console.log(f"  -> FAILED: {error_msg}", "ERROR")
                    failed_params.append(f"{param_name}({param_id})={value}")

                self.advanced_debug_console.log("-" * 30, "DEBUG")

            # Summary
            self.advanced_debug_console.log("=" * 50, "DEBUG")
            self.advanced_debug_console.log(f"SAVE COMPLETE: {success_count}/{len(params_to_save)} parameters saved", "INFO")

            if len(failed_params) == 0:
                self.advanced_debug_console.log("All settings saved successfully!", "INFO")
                self.advanced_debug_console.mark_operation_end(success=True)
                QMessageBox.information(None, "Success", "Global MIDI settings saved!")
            else:
                self.advanced_debug_console.log(f"FAILED parameters: {failed_params}", "ERROR")
                self.advanced_debug_console.log("", "DEBUG")
                self.advanced_debug_console.log("TROUBLESHOOTING:", "WARN")
                self.advanced_debug_console.log("  1. Check firmware supports HID_CMD_SET_KEYBOARD_PARAM_SINGLE (0xBD)", "WARN")
                self.advanced_debug_console.log("  2. Verify parameter IDs are correct in firmware", "WARN")
                self.advanced_debug_console.log("  3. Check for firmware version mismatch", "WARN")
                self.advanced_debug_console.log("  4. status_byte=1 means success, 0 or 0xFF means error", "WARN")
                self.advanced_debug_console.mark_operation_end(success=False)
                raise RuntimeError(f"Failed to save: {', '.join(failed_params)}")

        except Exception as e:
            self.advanced_debug_console.log(f"EXCEPTION: {str(e)}", "ERROR")
            self.advanced_debug_console.mark_operation_end(success=False)
            QMessageBox.critical(None, "Error",
                f"Failed to save advanced settings: {str(e)}")

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

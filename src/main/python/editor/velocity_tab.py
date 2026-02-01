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
                           QRadioButton, QMessageBox, QTabWidget)
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
    PARAM_AFTERTOUCH_MODE, PARAM_AFTERTOUCH_CC,
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

        # Global MIDI settings
        # Note: velocity_mode is fixed at 3 (Speed+Peak) in firmware, not configurable
        # Base zone settings are at the top level, keysplit/triplesplit zones are in sub-dicts
        self.global_midi_settings = {
            'velocity_min': 1,          # 1-127 (minimum MIDI velocity)
            'velocity_max': 127,        # 1-127 (maximum MIDI velocity)
            'aftertouch_mode': 0,       # 0=Off, 1=Reverse, 2=Bottom-out, 3=Post-actuation, 4=Vibrato
            'aftertouch_cc': 255,       # 0-127=CC number, 255=off (poly AT only)
            'vibrato_sensitivity': 100, # 50-200 (percentage)
            'vibrato_decay_time': 200,  # 0-2000 (milliseconds)
            'min_press_time': 200,      # 50-500ms (slow press threshold)
            'max_press_time': 20,       # 5-100ms (fast press threshold)
            'actuation_override': False, # Override per-key actuation for MIDI keys
            'actuation_point': 20,      # 0-40 = 0.0-4.0mm in 0.1mm steps
            'speed_peak_ratio': 50,     # 0-100 = ratio of speed to peak (0=all peak, 100=all speed)
            'retrigger_distance': 0,    # 0=off, 5-20 = 0.5-2.0mm retrigger distance
            # Zone enable flags
            'keysplit_enabled': False,
            'triplesplit_enabled': False,
            # Keysplit zone settings (used when keysplit_enabled is True)
            'keysplit_zone': {
                'velocity_min': 1, 'velocity_max': 127,
                'aftertouch_mode': 0, 'aftertouch_cc': 255,
                'vibrato_sensitivity': 100, 'vibrato_decay_time': 200,
                'min_press_time': 200, 'max_press_time': 20,
                'actuation_override': False, 'actuation_point': 20,
                'speed_peak_ratio': 50, 'retrigger_distance': 0,
                'points': [[0, 0], [85, 85], [170, 170], [255, 255]]
            },
            # Triplesplit zone settings (used when triplesplit_enabled is True)
            'triplesplit_zone': {
                'velocity_min': 1, 'velocity_max': 127,
                'aftertouch_mode': 0, 'aftertouch_cc': 255,
                'vibrato_sensitivity': 100, 'vibrato_decay_time': 200,
                'min_press_time': 200, 'max_press_time': 20,
                'actuation_override': False, 'actuation_point': 20,
                'speed_peak_ratio': 50, 'retrigger_distance': 0,
                'points': [[0, 0], [85, 85], [170, 170], [255, 255]]
            }
        }

        # Polling timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_velocity)
        self.poll_interval = 50  # 50ms = 20Hz

        # Track if tab is active
        self.is_active = False

        self.setup_ui()

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
            }
        """)
        help_btn.setToolTip(tooltip_text)
        help_btn.setCursor(Qt.WhatsThisCursor)
        return help_btn

    def create_zone_controls(self, zone_name):
        """Create a widget containing all velocity controls for a specific zone (base/keysplit/triplesplit).
        Returns (container_widget, controls_dict) where controls_dict has references to all control widgets."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(5, 5, 5, 5)
        container.setLayout(layout)

        controls = {}

        # Velocity Min row
        vel_min_layout = QHBoxLayout()
        vel_min_layout.setContentsMargins(0, 0, 0, 0)
        vel_min_layout.setSpacing(4)
        vel_min_label = QLabel(tr("VelocityTab", "Vel Min:"))
        vel_min_label.setMinimumWidth(65)
        vel_min_layout.addWidget(vel_min_label)

        controls['vel_min_slider'] = QSlider(Qt.Horizontal)
        controls['vel_min_slider'].setMinimum(1)
        controls['vel_min_slider'].setMaximum(127)
        controls['vel_min_slider'].setValue(1)
        controls['vel_min_slider'].setProperty('zone', zone_name)
        vel_min_layout.addWidget(controls['vel_min_slider'], 1)

        controls['vel_min_value'] = QLabel("1")
        controls['vel_min_value'].setMinimumWidth(30)
        controls['vel_min_value'].setStyleSheet("QLabel { font-weight: bold; }")
        vel_min_layout.addWidget(controls['vel_min_value'])
        layout.addLayout(vel_min_layout)

        # Velocity Max row
        vel_max_layout = QHBoxLayout()
        vel_max_layout.setContentsMargins(0, 0, 0, 0)
        vel_max_layout.setSpacing(4)
        vel_max_label = QLabel(tr("VelocityTab", "Vel Max:"))
        vel_max_label.setMinimumWidth(65)
        vel_max_layout.addWidget(vel_max_label)

        controls['vel_max_slider'] = QSlider(Qt.Horizontal)
        controls['vel_max_slider'].setMinimum(1)
        controls['vel_max_slider'].setMaximum(127)
        controls['vel_max_slider'].setValue(127)
        controls['vel_max_slider'].setProperty('zone', zone_name)
        vel_max_layout.addWidget(controls['vel_max_slider'], 1)

        controls['vel_max_value'] = QLabel("127")
        controls['vel_max_value'].setMinimumWidth(30)
        controls['vel_max_value'].setStyleSheet("QLabel { font-weight: bold; }")
        vel_max_layout.addWidget(controls['vel_max_value'])
        layout.addLayout(vel_max_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Press Time sliders
        # Slow Press Time
        min_press_layout = QHBoxLayout()
        min_press_layout.setContentsMargins(0, 0, 0, 0)
        min_press_layout.setSpacing(4)
        min_press_layout.addWidget(self.create_help_label(
            "Slow press threshold (ms):\n"
            "Keys pressed slower than this get minimum velocity."
        ))
        min_press_label = QLabel(tr("VelocityTab", "Slow Press:"))
        min_press_label.setMinimumWidth(85)
        min_press_layout.addWidget(min_press_label)

        controls['min_press_slider'] = QSlider(Qt.Horizontal)
        controls['min_press_slider'].setMinimum(50)
        controls['min_press_slider'].setMaximum(500)
        controls['min_press_slider'].setValue(200)
        controls['min_press_slider'].setProperty('zone', zone_name)
        min_press_layout.addWidget(controls['min_press_slider'], 1)

        controls['min_press_value'] = QLabel("200ms")
        controls['min_press_value'].setMinimumWidth(50)
        controls['min_press_value'].setStyleSheet("QLabel { font-weight: bold; }")
        min_press_layout.addWidget(controls['min_press_value'])
        layout.addLayout(min_press_layout)

        # Fast Press Time
        max_press_layout = QHBoxLayout()
        max_press_layout.setContentsMargins(0, 0, 0, 0)
        max_press_layout.setSpacing(4)
        max_press_layout.addWidget(self.create_help_label(
            "Fast press threshold (ms):\n"
            "Keys pressed faster than this get maximum velocity."
        ))
        max_press_label = QLabel(tr("VelocityTab", "Fast Press:"))
        max_press_label.setMinimumWidth(85)
        max_press_layout.addWidget(max_press_label)

        controls['max_press_slider'] = QSlider(Qt.Horizontal)
        controls['max_press_slider'].setMinimum(5)
        controls['max_press_slider'].setMaximum(100)
        controls['max_press_slider'].setValue(20)
        controls['max_press_slider'].setProperty('zone', zone_name)
        max_press_layout.addWidget(controls['max_press_slider'], 1)

        controls['max_press_value'] = QLabel("20ms")
        controls['max_press_value'].setMinimumWidth(50)
        controls['max_press_value'].setStyleSheet("QLabel { font-weight: bold; }")
        max_press_layout.addWidget(controls['max_press_value'])
        layout.addLayout(max_press_layout)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)

        # Aftertouch Mode
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(4)
        mode_layout.addWidget(self.create_help_label(
            "Aftertouch pressure behavior:\n"
            "Off: No aftertouch\n"
            "Reverse: Pressure on key release\n"
            "Bottom-Out: Pressure when fully pressed\n"
            "Post-Actuation: Pressure after actuation\n"
            "Vibrato: Wiggle key for aftertouch"
        ))
        mode_label = QLabel(tr("VelocityTab", "Aftertouch:"))
        mode_label.setMinimumWidth(85)
        mode_layout.addWidget(mode_label)

        controls['aftertouch_mode_combo'] = ArrowComboBox()
        controls['aftertouch_mode_combo'].setMaximumHeight(25)
        controls['aftertouch_mode_combo'].setStyleSheet("QComboBox { padding: 0px; font-size: 10px; }")
        controls['aftertouch_mode_combo'].setEditable(True)
        controls['aftertouch_mode_combo'].lineEdit().setReadOnly(True)
        controls['aftertouch_mode_combo'].lineEdit().setAlignment(Qt.AlignCenter)
        controls['aftertouch_mode_combo'].addItem("Off", 0)
        controls['aftertouch_mode_combo'].addItem("Reverse", 1)
        controls['aftertouch_mode_combo'].addItem("Bottom-Out", 2)
        controls['aftertouch_mode_combo'].addItem("Post-Actuation", 3)
        controls['aftertouch_mode_combo'].addItem("Vibrato", 4)
        controls['aftertouch_mode_combo'].setCurrentIndex(0)
        controls['aftertouch_mode_combo'].setProperty('zone', zone_name)
        mode_layout.addWidget(controls['aftertouch_mode_combo'], 1)
        layout.addLayout(mode_layout)

        # Aftertouch CC
        cc_layout = QHBoxLayout()
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(4)
        cc_layout.addWidget(self.create_help_label("MIDI CC for aftertouch.\nOff: Standard aftertouch\nCC#: Send as CC instead"))
        cc_label = QLabel(tr("VelocityTab", "AT CC:"))
        cc_label.setMinimumWidth(85)
        cc_layout.addWidget(cc_label)

        controls['aftertouch_cc_combo'] = ArrowComboBox()
        controls['aftertouch_cc_combo'].setMaximumHeight(25)
        controls['aftertouch_cc_combo'].setStyleSheet("QComboBox { padding: 0px; font-size: 10px; }")
        controls['aftertouch_cc_combo'].setEditable(True)
        controls['aftertouch_cc_combo'].lineEdit().setReadOnly(True)
        controls['aftertouch_cc_combo'].lineEdit().setAlignment(Qt.AlignCenter)
        controls['aftertouch_cc_combo'].addItem("Off", 255)
        for cc in range(128):
            controls['aftertouch_cc_combo'].addItem(f"CC#{cc}", cc)
        controls['aftertouch_cc_combo'].setCurrentIndex(0)
        controls['aftertouch_cc_combo'].setProperty('zone', zone_name)
        cc_layout.addWidget(controls['aftertouch_cc_combo'], 1)
        layout.addLayout(cc_layout)

        # Vibrato Sensitivity (hidden by default)
        controls['vibrato_sens_widget'] = QWidget()
        sens_layout = QHBoxLayout()
        sens_layout.setContentsMargins(0, 0, 0, 0)
        controls['vibrato_sens_widget'].setLayout(sens_layout)

        sens_layout.addWidget(self.create_help_label("Wiggle sensitivity.\n50%=Less, 200%=Very sensitive"))
        sens_label = QLabel(tr("VelocityTab", "Vib Sens:"))
        sens_label.setMinimumWidth(85)
        sens_layout.addWidget(sens_label)

        controls['vibrato_sens_slider'] = QSlider(Qt.Horizontal)
        controls['vibrato_sens_slider'].setMinimum(50)
        controls['vibrato_sens_slider'].setMaximum(200)
        controls['vibrato_sens_slider'].setValue(100)
        controls['vibrato_sens_slider'].setProperty('zone', zone_name)
        sens_layout.addWidget(controls['vibrato_sens_slider'], 1)

        controls['vibrato_sens_value'] = QLabel("100%")
        controls['vibrato_sens_value'].setMinimumWidth(45)
        controls['vibrato_sens_value'].setStyleSheet("QLabel { font-weight: bold; }")
        sens_layout.addWidget(controls['vibrato_sens_value'])

        layout.addWidget(controls['vibrato_sens_widget'])
        controls['vibrato_sens_widget'].setVisible(False)

        # Vibrato Decay (hidden by default)
        controls['vibrato_decay_widget'] = QWidget()
        decay_layout = QHBoxLayout()
        decay_layout.setContentsMargins(0, 0, 0, 0)
        controls['vibrato_decay_widget'].setLayout(decay_layout)

        decay_layout.addWidget(self.create_help_label("How long aftertouch lasts after wiggle stops."))
        decay_label = QLabel(tr("VelocityTab", "Vib Decay:"))
        decay_label.setMinimumWidth(85)
        decay_layout.addWidget(decay_label)

        controls['vibrato_decay_slider'] = QSlider(Qt.Horizontal)
        controls['vibrato_decay_slider'].setMinimum(0)
        controls['vibrato_decay_slider'].setMaximum(2000)
        controls['vibrato_decay_slider'].setValue(200)
        controls['vibrato_decay_slider'].setProperty('zone', zone_name)
        decay_layout.addWidget(controls['vibrato_decay_slider'], 1)

        controls['vibrato_decay_value'] = QLabel("200ms")
        controls['vibrato_decay_value'].setMinimumWidth(50)
        controls['vibrato_decay_value'].setStyleSheet("QLabel { font-weight: bold; }")
        decay_layout.addWidget(controls['vibrato_decay_value'])

        layout.addWidget(controls['vibrato_decay_widget'])
        controls['vibrato_decay_widget'].setVisible(False)

        # Separator before actuation override
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line3)

        # Actuation Override checkbox
        actuation_layout = QHBoxLayout()
        actuation_layout.setContentsMargins(0, 0, 0, 0)
        actuation_layout.setSpacing(4)
        actuation_layout.addWidget(self.create_help_label(
            "Override per-key actuation points for MIDI keys.\n"
            "When enabled, MIDI note-on triggers at this fixed distance\n"
            "instead of each key's individual actuation point."
        ))
        controls['actuation_override_checkbox'] = QCheckBox(tr("VelocityTab", "Override MIDI actuation"))
        controls['actuation_override_checkbox'].setChecked(False)
        controls['actuation_override_checkbox'].setProperty('zone', zone_name)
        actuation_layout.addWidget(controls['actuation_override_checkbox'])
        actuation_layout.addStretch()
        layout.addLayout(actuation_layout)

        # Actuation Point slider (hidden by default)
        controls['actuation_point_widget'] = QWidget()
        actuation_point_layout = QHBoxLayout()
        actuation_point_layout.setContentsMargins(0, 0, 0, 0)
        controls['actuation_point_widget'].setLayout(actuation_point_layout)

        actuation_point_layout.addWidget(self.create_help_label(
            "Actuation distance for MIDI note-on.\n"
            "0.0mm = very sensitive (top of travel)\n"
            "4.0mm = full press required"
        ))
        actuation_label = QLabel(tr("VelocityTab", "Actuation:"))
        actuation_label.setMinimumWidth(85)
        actuation_point_layout.addWidget(actuation_label)

        controls['actuation_point_slider'] = QSlider(Qt.Horizontal)
        controls['actuation_point_slider'].setMinimum(0)
        controls['actuation_point_slider'].setMaximum(40)  # 0-40 = 0.0-4.0mm in 0.1mm steps
        controls['actuation_point_slider'].setValue(20)  # Default 2.0mm
        controls['actuation_point_slider'].setProperty('zone', zone_name)
        actuation_point_layout.addWidget(controls['actuation_point_slider'], 1)

        controls['actuation_point_value'] = QLabel("2.0mm")
        controls['actuation_point_value'].setMinimumWidth(50)
        controls['actuation_point_value'].setStyleSheet("QLabel { font-weight: bold; }")
        actuation_point_layout.addWidget(controls['actuation_point_value'])

        layout.addWidget(controls['actuation_point_widget'])
        controls['actuation_point_widget'].setVisible(False)

        # Separator before speed/peak ratio
        line4 = QFrame()
        line4.setFrameShape(QFrame.HLine)
        line4.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line4)

        # Speed/Peak Ratio slider
        ratio_layout = QHBoxLayout()
        ratio_layout.setContentsMargins(0, 0, 0, 0)
        ratio_layout.setSpacing(4)
        ratio_layout.addWidget(self.create_help_label(
            "Velocity calculation blend:\n"
            "0% = All peak (position-based)\n"
            "50% = Equal blend (default)\n"
            "100% = All speed (timing-based)"
        ))
        ratio_label = QLabel(tr("VelocityTab", "Speed/Peak:"))
        ratio_label.setMinimumWidth(85)
        ratio_layout.addWidget(ratio_label)

        controls['speed_peak_slider'] = QSlider(Qt.Horizontal)
        controls['speed_peak_slider'].setMinimum(0)
        controls['speed_peak_slider'].setMaximum(100)
        controls['speed_peak_slider'].setValue(50)  # Default 50%
        controls['speed_peak_slider'].setProperty('zone', zone_name)
        ratio_layout.addWidget(controls['speed_peak_slider'], 1)

        controls['speed_peak_value'] = QLabel("50%")
        controls['speed_peak_value'].setMinimumWidth(45)
        controls['speed_peak_value'].setStyleSheet("QLabel { font-weight: bold; }")
        ratio_layout.addWidget(controls['speed_peak_value'])
        layout.addLayout(ratio_layout)

        # Retrigger checkbox
        retrigger_layout = QHBoxLayout()
        retrigger_layout.setContentsMargins(0, 0, 0, 0)
        retrigger_layout.setSpacing(4)
        retrigger_layout.addWidget(self.create_help_label(
            "Enable note retrigger without full release.\n"
            "Release to the retrigger point and press again\n"
            "to send a new note-on. Velocity is capped based\n"
            "on how far the key was released."
        ))
        controls['retrigger_checkbox'] = QCheckBox(tr("VelocityTab", "Enable Retrigger"))
        controls['retrigger_checkbox'].setChecked(False)
        controls['retrigger_checkbox'].setProperty('zone', zone_name)
        retrigger_layout.addWidget(controls['retrigger_checkbox'])
        retrigger_layout.addStretch()
        layout.addLayout(retrigger_layout)

        # Retrigger Distance slider (hidden by default)
        controls['retrigger_widget'] = QWidget()
        retrigger_dist_layout = QHBoxLayout()
        retrigger_dist_layout.setContentsMargins(0, 0, 0, 0)
        controls['retrigger_widget'].setLayout(retrigger_dist_layout)

        retrigger_dist_layout.addWidget(self.create_help_label(
            "Retrigger distance from actuation point.\n"
            "0.5mm = sensitive retrigger\n"
            "2.0mm = requires more release"
        ))
        retrigger_dist_label = QLabel(tr("VelocityTab", "Retrigger:"))
        retrigger_dist_label.setMinimumWidth(85)
        retrigger_dist_layout.addWidget(retrigger_dist_label)

        controls['retrigger_slider'] = QSlider(Qt.Horizontal)
        controls['retrigger_slider'].setMinimum(5)   # 0.5mm minimum
        controls['retrigger_slider'].setMaximum(20)  # 2.0mm maximum
        controls['retrigger_slider'].setValue(10)    # Default 1.0mm
        controls['retrigger_slider'].setProperty('zone', zone_name)
        retrigger_dist_layout.addWidget(controls['retrigger_slider'], 1)

        controls['retrigger_value'] = QLabel("1.0mm")
        controls['retrigger_value'].setMinimumWidth(50)
        controls['retrigger_value'].setStyleSheet("QLabel { font-weight: bold; }")
        retrigger_dist_layout.addWidget(controls['retrigger_value'])

        layout.addWidget(controls['retrigger_widget'])
        controls['retrigger_widget'].setVisible(False)

        # Add curve editor for zone tabs (keysplit/triplesplit only)
        if zone_name != 'base':
            line5 = QFrame()
            line5.setFrameShape(QFrame.HLine)
            line5.setFrameShadow(QFrame.Sunken)
            layout.addWidget(line5)

            curve_label = QLabel(tr("VelocityTab", "Zone Velocity Curve:"))
            curve_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(curve_label)

            controls['curve_editor'] = CurveEditorWidget(show_save_button=False)
            controls['curve_editor'].setMinimumSize(200, 150)
            controls['curve_editor'].setMaximumHeight(180)
            controls['curve_editor'].setProperty('zone', zone_name)
            layout.addWidget(controls['curve_editor'])

        layout.addStretch()
        return container, controls

    def connect_zone_controls(self, controls, zone_name):
        """Connect signals for zone controls. Zone name is 'base', 'keysplit', or 'triplesplit'."""
        # Get the settings dict for this zone
        def get_settings():
            if zone_name == 'base':
                return self.global_midi_settings
            else:
                return self.global_midi_settings.get(f'{zone_name}_zone', {})

        def set_setting(key, value):
            if zone_name == 'base':
                self.global_midi_settings[key] = value
            else:
                self.global_midi_settings[f'{zone_name}_zone'][key] = value

        # Velocity min/max
        def on_vel_min_changed(value):
            controls['vel_min_value'].setText(str(value))
            set_setting('velocity_min', value)
            if value > controls['vel_max_slider'].value():
                controls['vel_max_slider'].blockSignals(True)
                controls['vel_max_slider'].setValue(value)
                controls['vel_max_value'].setText(str(value))
                set_setting('velocity_max', value)
                controls['vel_max_slider'].blockSignals(False)

        def on_vel_max_changed(value):
            controls['vel_max_value'].setText(str(value))
            set_setting('velocity_max', value)
            if value < controls['vel_min_slider'].value():
                controls['vel_min_slider'].blockSignals(True)
                controls['vel_min_slider'].setValue(value)
                controls['vel_min_value'].setText(str(value))
                set_setting('velocity_min', value)
                controls['vel_min_slider'].blockSignals(False)

        controls['vel_min_slider'].valueChanged.connect(on_vel_min_changed)
        controls['vel_max_slider'].valueChanged.connect(on_vel_max_changed)

        # Press times
        def on_min_press_changed(value):
            controls['min_press_value'].setText(f"{value}ms")
            set_setting('min_press_time', value)

        def on_max_press_changed(value):
            controls['max_press_value'].setText(f"{value}ms")
            set_setting('max_press_time', value)

        controls['min_press_slider'].valueChanged.connect(on_min_press_changed)
        controls['max_press_slider'].valueChanged.connect(on_max_press_changed)

        # Aftertouch mode
        def on_aftertouch_mode_changed(index):
            mode = controls['aftertouch_mode_combo'].currentData()
            is_vibrato = (mode == 4)
            controls['vibrato_sens_widget'].setVisible(is_vibrato)
            controls['vibrato_decay_widget'].setVisible(is_vibrato)
            set_setting('aftertouch_mode', mode)

        controls['aftertouch_mode_combo'].currentIndexChanged.connect(on_aftertouch_mode_changed)

        # Aftertouch CC
        def on_aftertouch_cc_changed(index):
            cc = controls['aftertouch_cc_combo'].currentData()
            set_setting('aftertouch_cc', cc)

        controls['aftertouch_cc_combo'].currentIndexChanged.connect(on_aftertouch_cc_changed)

        # Vibrato settings
        def on_vibrato_sens_changed(value):
            controls['vibrato_sens_value'].setText(f"{value}%")
            set_setting('vibrato_sensitivity', value)

        def on_vibrato_decay_changed(value):
            controls['vibrato_decay_value'].setText(f"{value}ms")
            set_setting('vibrato_decay_time', value)

        controls['vibrato_sens_slider'].valueChanged.connect(on_vibrato_sens_changed)
        controls['vibrato_decay_slider'].valueChanged.connect(on_vibrato_decay_changed)

        # Actuation override
        def on_actuation_override_changed(state):
            enabled = (state == Qt.Checked)
            controls['actuation_point_widget'].setVisible(enabled)
            set_setting('actuation_override', enabled)

        controls['actuation_override_checkbox'].stateChanged.connect(on_actuation_override_changed)

        # Actuation point
        def on_actuation_point_changed(value):
            mm_value = value / 10.0
            controls['actuation_point_value'].setText(f"{mm_value:.1f}mm")
            set_setting('actuation_point', value)

        controls['actuation_point_slider'].valueChanged.connect(on_actuation_point_changed)

        # Speed/Peak ratio
        def on_speed_peak_changed(value):
            controls['speed_peak_value'].setText(f"{value}%")
            set_setting('speed_peak_ratio', value)

        controls['speed_peak_slider'].valueChanged.connect(on_speed_peak_changed)

        # Retrigger
        def on_retrigger_changed(state):
            enabled = (state == Qt.Checked)
            controls['retrigger_widget'].setVisible(enabled)
            if enabled:
                set_setting('retrigger_distance', controls['retrigger_slider'].value())
            else:
                set_setting('retrigger_distance', 0)

        controls['retrigger_checkbox'].stateChanged.connect(on_retrigger_changed)

        def on_retrigger_distance_changed(value):
            mm_value = value / 10.0
            controls['retrigger_value'].setText(f"{mm_value:.1f}mm")
            set_setting('retrigger_distance', value)

        controls['retrigger_slider'].valueChanged.connect(on_retrigger_distance_changed)

        # Curve editor for zone tabs
        if 'curve_editor' in controls:
            def on_curve_changed():
                points = controls['curve_editor'].get_points()
                set_setting('points', points)
            controls['curve_editor'].curve_changed.connect(on_curve_changed)

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

        # Bottom section: Combined Velocity Preset configuration
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # =====================================================================
        # LEFT SIDE: Velocity Preset Group (curve on left, settings on right)
        # =====================================================================
        preset_group = QGroupBox(tr("VelocityTab", "Velocity Preset"))
        preset_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        preset_main_layout = QHBoxLayout()
        preset_main_layout.setSpacing(15)
        preset_group.setLayout(preset_main_layout)

        # Curve editor widget (LEFT side) - for base zone
        self.curve_editor = CurveEditorWidget(show_save_button=True)
        self.curve_editor.setMinimumSize(280, 220)
        self.curve_editor.setMaximumWidth(320)
        self.curve_editor.curve_changed.connect(self.on_curve_changed)
        self.curve_editor.user_curve_selected.connect(self.on_user_curve_selected)
        self.curve_editor.save_to_user_requested.connect(self.on_save_to_user_curve)
        preset_main_layout.addWidget(self.curve_editor)

        # RIGHT side: Zone enable checkboxes + Tab widget for zone controls
        right_side_layout = QVBoxLayout()
        right_side_layout.setSpacing(8)
        preset_main_layout.addLayout(right_side_layout, 1)

        # Zone enable checkboxes
        zone_enable_layout = QHBoxLayout()
        zone_enable_layout.setContentsMargins(0, 0, 0, 0)
        zone_enable_layout.addWidget(self.create_help_label(
            "Enable independent velocity settings for split keyboard zones.\n"
            "Keysplit: Left/right split (2 zones)\n"
            "Triplesplit: Three zones (left/center/right)"
        ))
        self.keysplit_enable_checkbox = QCheckBox(tr("VelocityTab", "Enable Keysplit"))
        self.keysplit_enable_checkbox.stateChanged.connect(self.on_keysplit_enable_changed)
        zone_enable_layout.addWidget(self.keysplit_enable_checkbox)
        self.triplesplit_enable_checkbox = QCheckBox(tr("VelocityTab", "Enable Triplesplit"))
        self.triplesplit_enable_checkbox.stateChanged.connect(self.on_triplesplit_enable_changed)
        zone_enable_layout.addWidget(self.triplesplit_enable_checkbox)
        zone_enable_layout.addStretch()
        right_side_layout.addLayout(zone_enable_layout)

        # Tab widget for zone settings (tabs appear when zones are enabled)
        self.zone_tab_widget = QTabWidget()
        self.zone_tab_widget.setStyleSheet("QTabWidget::pane { border: 1px solid #444; }")
        right_side_layout.addWidget(self.zone_tab_widget)

        # Store zone controls for easy access
        self.zone_controls = {}

        # Create base zone controls (always visible)
        base_widget, base_controls = self.create_zone_controls('base')
        self.zone_controls['base'] = base_controls
        self.connect_zone_controls(base_controls, 'base')
        self.zone_tab_widget.addTab(base_widget, "Basic")

        # Create keysplit zone controls (hidden initially)
        keysplit_widget, keysplit_controls = self.create_zone_controls('keysplit')
        self.zone_controls['keysplit'] = keysplit_controls
        self.connect_zone_controls(keysplit_controls, 'keysplit')
        self.keysplit_tab_index = -1  # Will be set when tab is added

        # Create triplesplit zone controls (hidden initially)
        triplesplit_widget, triplesplit_controls = self.create_zone_controls('triplesplit')
        self.zone_controls['triplesplit'] = triplesplit_controls
        self.connect_zone_controls(triplesplit_controls, 'triplesplit')
        self.triplesplit_tab_index = -1  # Will be set when tab is added

        # Store widgets for later tab management
        self.keysplit_tab_widget = keysplit_widget
        self.triplesplit_tab_widget = triplesplit_widget

        # Create references to base zone controls for backward compatibility
        self.vel_min_slider = base_controls['vel_min_slider']
        self.vel_max_slider = base_controls['vel_max_slider']
        self.vel_min_value = base_controls['vel_min_value']
        self.vel_max_value = base_controls['vel_max_value']
        self.min_press_slider = base_controls['min_press_slider']
        self.max_press_slider = base_controls['max_press_slider']
        self.min_press_value = base_controls['min_press_value']
        self.max_press_value = base_controls['max_press_value']
        self.aftertouch_mode_combo = base_controls['aftertouch_mode_combo']
        self.aftertouch_cc_combo = base_controls['aftertouch_cc_combo']
        self.vibrato_sens_widget = base_controls['vibrato_sens_widget']
        self.vibrato_sens_slider = base_controls['vibrato_sens_slider']
        self.vibrato_sens_value = base_controls['vibrato_sens_value']
        self.vibrato_decay_widget = base_controls['vibrato_decay_widget']
        self.vibrato_decay_slider = base_controls['vibrato_decay_slider']
        self.vibrato_decay_value = base_controls['vibrato_decay_value']
        self.actuation_override_checkbox = base_controls['actuation_override_checkbox']
        self.actuation_point_widget = base_controls['actuation_point_widget']
        self.actuation_point_slider = base_controls['actuation_point_slider']
        self.actuation_point_value = base_controls['actuation_point_value']
        self.speed_peak_slider = base_controls['speed_peak_slider']
        self.speed_peak_value = base_controls['speed_peak_value']
        self.retrigger_checkbox = base_controls['retrigger_checkbox']
        self.retrigger_widget = base_controls['retrigger_widget']
        self.retrigger_slider = base_controls['retrigger_slider']
        self.retrigger_value = base_controls['retrigger_value']

        # Apply Preset button (below tabs)
        save_curve_btn = QPushButton(tr("VelocityTab", "Apply Preset to Keyboard"))
        save_curve_btn.setMinimumHeight(30)
        save_curve_btn.clicked.connect(self.on_save_curve)
        right_side_layout.addWidget(save_curve_btn)

        bottom_layout.addWidget(preset_group)

        # =====================================================================
        # RIGHT SIDE: Debug Console + Save Settings
        # =====================================================================
        right_group = QGroupBox(tr("VelocityTab", "Save & Debug"))
        right_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        right_layout = QVBoxLayout()
        right_group.setLayout(right_layout)

        # Save all settings button
        self.advanced_save_btn = QPushButton(tr("VelocityTab", "Save All Settings to Keyboard"))
        self.advanced_save_btn.setMinimumHeight(35)
        self.advanced_save_btn.clicked.connect(self.on_save_advanced)
        right_layout.addWidget(self.advanced_save_btn)

        # Toggle OLED debug display button
        self.oled_debug_btn = QPushButton(tr("VelocityTab", "Toggle OLED Preset Debug"))
        self.oled_debug_btn.setMinimumHeight(30)
        self.oled_debug_btn.setToolTip("Show velocity preset settings on keyboard OLED")
        self.oled_debug_btn.clicked.connect(self.on_toggle_oled_debug)
        right_layout.addWidget(self.oled_debug_btn)

        # Debug console for HID communication
        self.advanced_debug_console = DebugConsole("Velocity Settings Debug Console")
        right_layout.addWidget(self.advanced_debug_console)

        bottom_layout.addWidget(right_group)

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
            # Load velocity curve from keyboard
            self.load_velocity_curve()
            # Load advanced settings from keyboard
            self.load_advanced_settings()
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
        """Load advanced settings from keyboard (same approach as keymap_editor)"""
        if not self.keyboard:
            return

        try:
            # Get layer actuation settings (velocity_mode is fixed at 3 in firmware)
            result = self.keyboard.get_layer_actuation(0)  # Get from layer 0 for global settings
            if result:
                # Update global_midi_settings from device
                # Note: velocity_mode is fixed at Speed+Peak (3) and not configurable
                aftertouch_mode = result.get('aftertouch_mode', 0)
                self.global_midi_settings['aftertouch_mode'] = aftertouch_mode
                aftertouch_cc = result.get('aftertouch_cc', 255)
                self.global_midi_settings['aftertouch_cc'] = aftertouch_cc
                vibrato_sens = result.get('vibrato_sensitivity', 100)
                self.global_midi_settings['vibrato_sensitivity'] = vibrato_sens
                vibrato_decay = result.get('vibrato_decay_time', 200)
                self.global_midi_settings['vibrato_decay_time'] = vibrato_decay

                # Update UI from settings
                self.load_advanced_ui_from_settings()
        except Exception as e:
            print(f"Error loading advanced settings: {e}")

    def load_advanced_ui_from_settings(self):
        """Update UI controls from global_midi_settings"""
        settings = self.global_midi_settings

        # Block signals during UI update
        # Note: velocity_mode is fixed at Speed+Peak (3), no UI control needed
        self.aftertouch_mode_combo.blockSignals(True)
        self.aftertouch_cc_combo.blockSignals(True)
        self.vibrato_sens_slider.blockSignals(True)
        self.vibrato_decay_slider.blockSignals(True)
        self.min_press_slider.blockSignals(True)
        self.max_press_slider.blockSignals(True)

        # Set min/max press time
        min_press = settings.get('min_press_time', 200)
        self.min_press_slider.setValue(min_press)
        self.min_press_value.setText(f"{min_press}ms")

        max_press = settings.get('max_press_time', 20)
        self.max_press_slider.setValue(max_press)
        self.max_press_value.setText(f"{max_press}ms")

        # Set aftertouch mode
        mode = settings.get('aftertouch_mode', 0)
        for i in range(self.aftertouch_mode_combo.count()):
            if self.aftertouch_mode_combo.itemData(i) == mode:
                self.aftertouch_mode_combo.setCurrentIndex(i)
                break

        # Show/hide vibrato controls
        is_vibrato = (mode == 4)
        self.vibrato_sens_widget.setVisible(is_vibrato)
        self.vibrato_decay_widget.setVisible(is_vibrato)

        # Set aftertouch CC
        cc = settings.get('aftertouch_cc', 255)
        for i in range(self.aftertouch_cc_combo.count()):
            if self.aftertouch_cc_combo.itemData(i) == cc:
                self.aftertouch_cc_combo.setCurrentIndex(i)
                break

        # Set vibrato settings
        sens = settings.get('vibrato_sensitivity', 100)
        self.vibrato_sens_slider.setValue(sens)
        self.vibrato_sens_value.setText(f"{sens}%")

        decay = settings.get('vibrato_decay_time', 200)
        self.vibrato_decay_slider.setValue(decay)
        self.vibrato_decay_value.setText(f"{decay}ms")

        # Unblock signals
        self.aftertouch_mode_combo.blockSignals(False)
        self.aftertouch_cc_combo.blockSignals(False)
        self.vibrato_sens_slider.blockSignals(False)
        self.vibrato_decay_slider.blockSignals(False)
        self.min_press_slider.blockSignals(False)
        self.max_press_slider.blockSignals(False)

    def on_min_press_changed(self, value):
        """Handle min press time slider change"""
        self.min_press_value.setText(f"{value}ms")
        self.global_midi_settings['min_press_time'] = value

    def on_max_press_changed(self, value):
        """Handle max press time slider change"""
        self.max_press_value.setText(f"{value}ms")
        self.global_midi_settings['max_press_time'] = value

    def on_aftertouch_mode_changed(self, index):
        """Handle aftertouch mode change - show/hide vibrato controls"""
        mode = self.aftertouch_mode_combo.currentData()
        is_vibrato = (mode == 4)
        self.vibrato_sens_widget.setVisible(is_vibrato)
        self.vibrato_decay_widget.setVisible(is_vibrato)
        self.global_midi_settings['aftertouch_mode'] = mode

    def on_aftertouch_cc_changed(self, index):
        """Handle aftertouch CC change"""
        cc = self.aftertouch_cc_combo.currentData()
        self.global_midi_settings['aftertouch_cc'] = cc

    def on_vibrato_sensitivity_changed(self, value):
        """Handle vibrato sensitivity slider change"""
        self.vibrato_sens_value.setText(f"{value}%")
        self.global_midi_settings['vibrato_sensitivity'] = value

    def on_vibrato_decay_changed(self, value):
        """Handle vibrato decay slider change"""
        self.vibrato_decay_value.setText(f"{value}ms")
        self.global_midi_settings['vibrato_decay_time'] = value

    def on_actuation_override_changed(self, state):
        """Handle actuation override checkbox change"""
        enabled = (state == Qt.Checked)
        self.actuation_point_widget.setVisible(enabled)
        self.global_midi_settings['actuation_override'] = enabled

    def on_actuation_point_changed(self, value):
        """Handle actuation point slider change"""
        mm_value = value / 10.0  # Convert 0-40 to 0.0-4.0mm
        self.actuation_point_value.setText(f"{mm_value:.1f}mm")
        self.global_midi_settings['actuation_point'] = value

    def on_speed_peak_changed(self, value):
        """Handle speed/peak ratio slider change"""
        self.speed_peak_value.setText(f"{value}%")
        self.global_midi_settings['speed_peak_ratio'] = value

    def on_retrigger_changed(self, state):
        """Handle retrigger checkbox change"""
        enabled = (state == Qt.Checked)
        self.retrigger_widget.setVisible(enabled)
        if enabled:
            # When enabling, use the slider's current value
            self.global_midi_settings['retrigger_distance'] = self.retrigger_slider.value()
        else:
            # When disabling, set to 0
            self.global_midi_settings['retrigger_distance'] = 0

    def on_retrigger_distance_changed(self, value):
        """Handle retrigger distance slider change"""
        mm_value = value / 10.0  # Convert 5-20 to 0.5-2.0mm
        self.retrigger_value.setText(f"{mm_value:.1f}mm")
        self.global_midi_settings['retrigger_distance'] = value

    def on_keysplit_enable_changed(self, state):
        """Handle keysplit zone enable checkbox change"""
        enabled = (state == Qt.Checked)
        self.global_midi_settings['keysplit_enabled'] = enabled

        if enabled:
            # Add keysplit tab if not already present
            if self.keysplit_tab_index == -1:
                self.keysplit_tab_index = self.zone_tab_widget.addTab(
                    self.keysplit_tab_widget, "Keysplit"
                )
        else:
            # Remove keysplit tab
            if self.keysplit_tab_index != -1:
                # Find the tab index (it may have shifted due to other tabs)
                for i in range(self.zone_tab_widget.count()):
                    if self.zone_tab_widget.widget(i) == self.keysplit_tab_widget:
                        self.zone_tab_widget.removeTab(i)
                        break
                self.keysplit_tab_index = -1
                # Update triplesplit tab index if it was affected
                if self.triplesplit_tab_index > i:
                    self.triplesplit_tab_index -= 1

    def on_triplesplit_enable_changed(self, state):
        """Handle triplesplit zone enable checkbox change"""
        enabled = (state == Qt.Checked)
        self.global_midi_settings['triplesplit_enabled'] = enabled

        if enabled:
            # Add triplesplit tab if not already present
            if self.triplesplit_tab_index == -1:
                self.triplesplit_tab_index = self.zone_tab_widget.addTab(
                    self.triplesplit_tab_widget, "Triplesplit"
                )
        else:
            # Remove triplesplit tab
            if self.triplesplit_tab_index != -1:
                # Find the tab index (it may have shifted due to other tabs)
                for i in range(self.zone_tab_widget.count()):
                    if self.zone_tab_widget.widget(i) == self.triplesplit_tab_widget:
                        self.zone_tab_widget.removeTab(i)
                        break
                self.triplesplit_tab_index = -1

    def update_zone_controls_from_settings(self, zone_name, zone_data):
        """Update zone controls UI from zone settings data"""
        controls = self.zone_controls.get(zone_name)
        if not controls or not zone_data:
            return

        # Block signals during update
        for control in controls.values():
            if hasattr(control, 'blockSignals'):
                control.blockSignals(True)

        # Update velocity min/max
        vel_min = zone_data.get('velocity_min', 1)
        vel_max = zone_data.get('velocity_max', 127)
        controls['vel_min_slider'].setValue(vel_min)
        controls['vel_max_slider'].setValue(vel_max)
        controls['vel_min_value'].setText(str(vel_min))
        controls['vel_max_value'].setText(str(vel_max))

        # Update press times
        slow_press = zone_data.get('slow_press_time', zone_data.get('min_press_time', 200))
        fast_press = zone_data.get('fast_press_time', zone_data.get('max_press_time', 20))
        controls['min_press_slider'].setValue(slow_press)
        controls['max_press_slider'].setValue(fast_press)
        controls['min_press_value'].setText(f"{slow_press}ms")
        controls['max_press_value'].setText(f"{fast_press}ms")

        # Update aftertouch mode
        at_mode = zone_data.get('aftertouch_mode', 0)
        for i in range(controls['aftertouch_mode_combo'].count()):
            if controls['aftertouch_mode_combo'].itemData(i) == at_mode:
                controls['aftertouch_mode_combo'].setCurrentIndex(i)
                break

        # Show/hide vibrato controls based on mode
        is_vibrato = (at_mode == 4)
        controls['vibrato_sens_widget'].setVisible(is_vibrato)
        controls['vibrato_decay_widget'].setVisible(is_vibrato)

        # Update aftertouch CC
        at_cc = zone_data.get('aftertouch_cc', 255)
        for i in range(controls['aftertouch_cc_combo'].count()):
            if controls['aftertouch_cc_combo'].itemData(i) == at_cc:
                controls['aftertouch_cc_combo'].setCurrentIndex(i)
                break

        # Update vibrato settings
        vib_sens = zone_data.get('vibrato_sensitivity', 100)
        vib_decay = zone_data.get('vibrato_decay', zone_data.get('vibrato_decay_time', 200))
        controls['vibrato_sens_slider'].setValue(vib_sens)
        controls['vibrato_sens_value'].setText(f"{vib_sens}%")
        controls['vibrato_decay_slider'].setValue(vib_decay)
        controls['vibrato_decay_value'].setText(f"{vib_decay}ms")

        # Update actuation override
        actuation_override = zone_data.get('actuation_override', False)
        actuation_point = zone_data.get('actuation_point', 20)
        controls['actuation_override_checkbox'].setChecked(actuation_override)
        controls['actuation_point_slider'].setValue(actuation_point)
        mm_value = actuation_point / 10.0
        controls['actuation_point_value'].setText(f"{mm_value:.1f}mm")
        controls['actuation_point_widget'].setVisible(actuation_override)

        # Update speed/peak ratio
        speed_peak_ratio = zone_data.get('speed_peak_ratio', 50)
        controls['speed_peak_slider'].setValue(speed_peak_ratio)
        controls['speed_peak_value'].setText(f"{speed_peak_ratio}%")

        # Update retrigger settings
        retrigger_distance = zone_data.get('retrigger_distance', 0)
        retrigger_enabled = (retrigger_distance > 0)
        controls['retrigger_checkbox'].setChecked(retrigger_enabled)
        if retrigger_enabled:
            controls['retrigger_slider'].setValue(retrigger_distance)
            mm_value = retrigger_distance / 10.0
            controls['retrigger_value'].setText(f"{mm_value:.1f}mm")
        controls['retrigger_widget'].setVisible(retrigger_enabled)

        # Update curve editor if present (for keysplit/triplesplit zones)
        if 'curve_editor' in controls:
            points = zone_data.get('points', [[0, 0], [85, 85], [170, 170], [255, 255]])
            controls['curve_editor'].set_points(points)

        # Unblock signals
        for control in controls.values():
            if hasattr(control, 'blockSignals'):
                control.blockSignals(False)

    def on_save_advanced(self):
        """Save advanced settings (velocity, aftertouch) to keyboard - GLOBAL settings"""
        # Start debug console operation
        self.advanced_debug_console.mark_operation_start()
        self.advanced_debug_console.log("=" * 50, "DEBUG")
        self.advanced_debug_console.log("SAVE ADVANCED SETTINGS - Starting", "INFO")
        self.advanced_debug_console.log("=" * 50, "DEBUG")

        try:
            if not self.keyboard:
                self.advanced_debug_console.log("ERROR: Keyboard not connected", "ERROR")
                self.advanced_debug_console.mark_operation_end(success=False)
                raise RuntimeError("Keyboard not connected")

            settings = self.global_midi_settings
            kb = self.keyboard

            # Log HID command info
            self.advanced_debug_console.log(f"HID Command: SET_KEYBOARD_PARAM_SINGLE (0x{HID_CMD_SET_KEYBOARD_PARAM_SINGLE:02X})", "DEBUG")
            self.advanced_debug_console.log("-" * 50, "DEBUG")

            # Define parameters to save with their names and value ranges
            # Note: VELOCITY_MODE is fixed at 3 (Speed+Peak) in firmware, not configurable
            params_to_save = [
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
                self.advanced_debug_console.log("  1. Check firmware supports HID_CMD_SET_KEYBOARD_PARAM_SINGLE (0xE8)", "WARN")
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

    def load_velocity_curve(self):
        """Load current velocity curve and user curve names from keyboard"""
        if not self.keyboard:
            return

        try:
            # Load user curve names from keyboard
            user_curve_names = self.keyboard.get_all_user_curve_names()
            if user_curve_names:
                self.curve_editor.set_user_curve_names(user_curve_names)

            # Get keyboard config which includes velocity curve index
            config = self.keyboard.get_keyboard_config()
            if config:
                curve_index = config.get('he_velocity_curve', 2)  # Default to Linear (2)
                # Update the curve editor's preset combo
                self.curve_editor.preset_combo.blockSignals(True)
                if 0 <= curve_index < 7:
                    # Factory curve
                    self.curve_editor.preset_combo.setCurrentIndex(curve_index)
                    points = CurveEditorWidget.FACTORY_CURVE_POINTS[curve_index]
                    self.curve_editor.set_points(points)
                elif 7 <= curve_index <= 16:
                    # User curve - find it in the combo (after separator)
                    # Factory curves: 0-6, separator, User curves: 7-16
                    combo_index = curve_index + 1  # +1 for separator after factory curves
                    if combo_index < self.curve_editor.preset_combo.count():
                        self.curve_editor.preset_combo.setCurrentIndex(combo_index)
                        # Load user curve points from keyboard
                        self.on_user_curve_selected(curve_index - 7)
                self.curve_editor.preset_combo.blockSignals(False)
        except Exception as e:
            print(f"Error loading velocity curve: {e}")

    def on_vel_min_changed(self, value):
        """Handle velocity min slider change"""
        self.vel_min_value.setText(str(value))
        self.global_midi_settings['velocity_min'] = value
        # Ensure min <= max
        if value > self.vel_max_slider.value():
            self.vel_max_slider.blockSignals(True)
            self.vel_max_slider.setValue(value)
            self.vel_max_value.setText(str(value))
            self.global_midi_settings['velocity_max'] = value
            self.vel_max_slider.blockSignals(False)

    def on_vel_max_changed(self, value):
        """Handle velocity max slider change"""
        self.vel_max_value.setText(str(value))
        self.global_midi_settings['velocity_max'] = value
        # Ensure max >= min
        if value < self.vel_min_slider.value():
            self.vel_min_slider.blockSignals(True)
            self.vel_min_slider.setValue(value)
            self.vel_min_value.setText(str(value))
            self.global_midi_settings['velocity_min'] = value
            self.vel_min_slider.blockSignals(False)

    def on_user_curve_selected(self, slot_index):
        """Load user curve (velocity preset) from keyboard when selected in dropdown.
        This loads all preset settings including zone data for keysplit/triplesplit."""
        if not self.keyboard:
            return

        try:
            # get_velocity_preset returns full preset with zone data
            result = self.keyboard.get_velocity_preset(slot_index)
            if result:
                # Load and display preset name from device
                preset_name = result.get('name', f'User {slot_index + 1}')
                if preset_name:  # Only update if name is not empty
                    self.curve_editor.set_user_curve_name(slot_index, preset_name)

                # Load zone enable flags
                keysplit_enabled = result.get('keysplit_enabled', False)
                triplesplit_enabled = result.get('triplesplit_enabled', False)

                # Update checkboxes (this will trigger tab add/remove)
                self.keysplit_enable_checkbox.blockSignals(True)
                self.triplesplit_enable_checkbox.blockSignals(True)
                self.keysplit_enable_checkbox.setChecked(keysplit_enabled)
                self.triplesplit_enable_checkbox.setChecked(triplesplit_enabled)
                self.keysplit_enable_checkbox.blockSignals(False)
                self.triplesplit_enable_checkbox.blockSignals(False)

                # Update tabs manually since we blocked signals
                self.global_midi_settings['keysplit_enabled'] = keysplit_enabled
                self.global_midi_settings['triplesplit_enabled'] = triplesplit_enabled

                # Add/remove tabs based on enable state
                if keysplit_enabled and self.keysplit_tab_index == -1:
                    self.keysplit_tab_index = self.zone_tab_widget.addTab(
                        self.keysplit_tab_widget, "Keysplit")
                elif not keysplit_enabled and self.keysplit_tab_index != -1:
                    for i in range(self.zone_tab_widget.count()):
                        if self.zone_tab_widget.widget(i) == self.keysplit_tab_widget:
                            self.zone_tab_widget.removeTab(i)
                            break
                    self.keysplit_tab_index = -1

                if triplesplit_enabled and self.triplesplit_tab_index == -1:
                    self.triplesplit_tab_index = self.zone_tab_widget.addTab(
                        self.triplesplit_tab_widget, "Triplesplit")
                elif not triplesplit_enabled and self.triplesplit_tab_index != -1:
                    for i in range(self.zone_tab_widget.count()):
                        if self.zone_tab_widget.widget(i) == self.triplesplit_tab_widget:
                            self.zone_tab_widget.removeTab(i)
                            break
                    self.triplesplit_tab_index = -1

                # Load base zone data
                base_zone = result.get('base', result)  # Fallback to top-level for backward compat
                points = base_zone.get('points', [[0, 0], [85, 85], [170, 170], [255, 255]])
                self.curve_editor.load_user_curve_points(points, slot_index)

                # Update base zone controls and settings
                self.update_zone_controls_from_settings('base', base_zone)

                # Store base zone settings in global_midi_settings
                self.global_midi_settings['velocity_min'] = base_zone.get('velocity_min', 1)
                self.global_midi_settings['velocity_max'] = base_zone.get('velocity_max', 127)
                self.global_midi_settings['min_press_time'] = base_zone.get('slow_press_time', 200)
                self.global_midi_settings['max_press_time'] = base_zone.get('fast_press_time', 20)
                self.global_midi_settings['aftertouch_mode'] = base_zone.get('aftertouch_mode', 0)
                self.global_midi_settings['aftertouch_cc'] = base_zone.get('aftertouch_cc', 255)
                self.global_midi_settings['vibrato_sensitivity'] = base_zone.get('vibrato_sensitivity', 100)
                self.global_midi_settings['vibrato_decay_time'] = base_zone.get('vibrato_decay', 200)
                self.global_midi_settings['actuation_override'] = base_zone.get('actuation_override', False)
                self.global_midi_settings['actuation_point'] = base_zone.get('actuation_point', 20)
                self.global_midi_settings['speed_peak_ratio'] = base_zone.get('speed_peak_ratio', 50)
                self.global_midi_settings['retrigger_distance'] = base_zone.get('retrigger_distance', 0)

                # Load keysplit zone data if enabled
                if keysplit_enabled:
                    keysplit_zone = result.get('keysplit', {})
                    self.update_zone_controls_from_settings('keysplit', keysplit_zone)
                    self.global_midi_settings['keysplit_zone'] = keysplit_zone

                # Load triplesplit zone data if enabled
                if triplesplit_enabled:
                    triplesplit_zone = result.get('triplesplit', {})
                    self.update_zone_controls_from_settings('triplesplit', triplesplit_zone)
                    self.global_midi_settings['triplesplit_zone'] = triplesplit_zone

        except Exception as e:
            print(f"Error loading user curve {slot_index}: {e}")

    def get_zone_settings_from_controls(self, zone_name):
        """Get zone settings from the zone controls widgets"""
        controls = self.zone_controls.get(zone_name)
        if not controls:
            return None

        zone_data = {
            'velocity_min': controls['vel_min_slider'].value(),
            'velocity_max': controls['vel_max_slider'].value(),
            'slow_press_time': controls['min_press_slider'].value(),
            'fast_press_time': controls['max_press_slider'].value(),
            'aftertouch_mode': controls['aftertouch_mode_combo'].currentData(),
            'aftertouch_cc': controls['aftertouch_cc_combo'].currentData(),
            'vibrato_sensitivity': controls['vibrato_sens_slider'].value(),
            'vibrato_decay': controls['vibrato_decay_slider'].value(),
            'actuation_override': controls['actuation_override_checkbox'].isChecked(),
            'actuation_point': controls['actuation_point_slider'].value(),
            'speed_peak_ratio': controls['speed_peak_slider'].value(),
            'retrigger_distance': controls['retrigger_slider'].value() if controls['retrigger_checkbox'].isChecked() else 0
        }

        # Get curve points for zone tabs (keysplit/triplesplit)
        if 'curve_editor' in controls:
            zone_data['points'] = controls['curve_editor'].get_points()
        else:
            # For base zone, use the main curve editor
            zone_data['points'] = self.curve_editor.get_points()

        return zone_data

    def on_save_to_user_curve(self, slot_index, curve_name):
        """Save current velocity preset to a user slot on the keyboard.
        This saves all preset settings including zone data for keysplit/triplesplit."""
        if not self.keyboard:
            QMessageBox.warning(
                None,
                tr("VelocityTab", "Save Failed"),
                tr("VelocityTab", "Keyboard not connected.")
            )
            return

        try:
            points = self.curve_editor.get_points()
            settings = self.global_midi_settings

            # Get zone enable states
            keysplit_enabled = settings.get('keysplit_enabled', False)
            triplesplit_enabled = settings.get('triplesplit_enabled', False)

            # Build keysplit zone data from controls
            keysplit_zone = None
            if keysplit_enabled:
                keysplit_zone = self.get_zone_settings_from_controls('keysplit')

            # Build triplesplit zone data from controls
            triplesplit_zone = None
            if triplesplit_enabled:
                triplesplit_zone = self.get_zone_settings_from_controls('triplesplit')

            # Use the set_velocity_preset method with zone data
            success = self.keyboard.set_velocity_preset(
                slot=slot_index,
                points=points,
                name=curve_name,
                velocity_min=settings.get('velocity_min', 1),
                velocity_max=settings.get('velocity_max', 127),
                slow_press_time=settings.get('min_press_time', 200),
                fast_press_time=settings.get('max_press_time', 20),
                aftertouch_mode=settings.get('aftertouch_mode', 0),
                aftertouch_cc=settings.get('aftertouch_cc', 255),
                vibrato_sensitivity=settings.get('vibrato_sensitivity', 100),
                vibrato_decay=settings.get('vibrato_decay_time', 200),
                actuation_override=settings.get('actuation_override', False),
                actuation_point=settings.get('actuation_point', 20),
                speed_peak_ratio=settings.get('speed_peak_ratio', 50),
                retrigger_distance=settings.get('retrigger_distance', 0),
                keysplit_enabled=keysplit_enabled,
                triplesplit_enabled=triplesplit_enabled,
                keysplit_zone=keysplit_zone,
                triplesplit_zone=triplesplit_zone
            )

            if success:
                extra_info = ""
                if settings.get('actuation_override', False):
                    mm_value = settings.get('actuation_point', 20) / 10.0
                    extra_info += f", actuation override {mm_value:.1f}mm"
                extra_info += f", speed/peak {settings.get('speed_peak_ratio', 50)}%"
                retrig = settings.get('retrigger_distance', 0)
                if retrig > 0:
                    extra_info += f", retrigger {retrig/10.0:.1f}mm"
                if keysplit_enabled:
                    extra_info += ", keysplit zone"
                if triplesplit_enabled:
                    extra_info += ", triplesplit zone"
                QMessageBox.information(
                    None,
                    tr("VelocityTab", "Velocity Preset Saved"),
                    tr("VelocityTab", f"Preset saved to User slot {slot_index + 1} as '{curve_name}'.\n\n"
                       f"Includes: curve, velocity {settings.get('velocity_min', 1)}-{settings.get('velocity_max', 127)}, "
                       f"press times, aftertouch, vibrato{extra_info}.")
                )
                # Update the user curve name in the dropdown
                names = list(self.curve_editor.user_curve_names)
                names[slot_index] = curve_name
                self.curve_editor.set_user_curve_names(names)
            else:
                QMessageBox.warning(
                    None,
                    tr("VelocityTab", "Save Failed"),
                    tr("VelocityTab", "Failed to save velocity preset to keyboard.")
                )
        except Exception as e:
            QMessageBox.warning(
                None,
                tr("VelocityTab", "Save Failed"),
                tr("VelocityTab", f"Error saving velocity preset: {e}")
            )

    def on_toggle_oled_debug(self):
        """Toggle velocity preset debug display on keyboard OLED"""
        if not self.keyboard:
            self.advanced_debug_console.log("ERROR: Keyboard not connected", "ERROR")
            return

        try:
            result = self.keyboard.toggle_velocity_preset_debug()
            if result is not None:
                state = "ON" if result else "OFF"
                self.advanced_debug_console.log(f"OLED preset debug display: {state}", "INFO")
            else:
                self.advanced_debug_console.log("Failed to toggle OLED debug display", "ERROR")
        except Exception as e:
            self.advanced_debug_console.log(f"Error toggling OLED debug: {e}", "ERROR")

    def on_save_curve(self):
        """Save velocity curve selection to keyboard (sets the active curve index)"""
        if not self.keyboard:
            return

        # Get curve index from the CurveEditorWidget's preset combo
        curve_index = self.curve_editor.preset_combo.currentData()

        if curve_index == -1:
            # Custom curve - need to save to a user slot first
            QMessageBox.information(
                None,
                tr("VelocityTab", "Custom Curve"),
                tr("VelocityTab", "To use a custom curve, save it to a User slot first using 'Save to User...'")
            )
            return

        try:
            # Use set_keyboard_param_single to set the velocity curve
            # PARAM_HE_VELOCITY_CURVE = 4 (from keyboard_comm.py constants)
            success = self.keyboard.set_keyboard_param_single(4, curve_index)
            if success:
                # Get the curve name for display
                if curve_index < 7:
                    curve_name = CurveEditorWidget.FACTORY_CURVES[curve_index]
                else:
                    slot = curve_index - 7
                    curve_name = self.curve_editor.user_curve_names[slot] if slot < 10 else f"User {slot + 1}"
                QMessageBox.information(
                    None,
                    tr("VelocityTab", "Curve Applied"),
                    tr("VelocityTab", f"Velocity curve '{curve_name}' applied to keyboard.")
                )
            else:
                QMessageBox.warning(
                    None,
                    tr("VelocityTab", "Apply Failed"),
                    tr("VelocityTab", "Failed to apply velocity curve.")
                )
        except Exception as e:
            QMessageBox.warning(
                None,
                tr("VelocityTab", "Apply Failed"),
                tr("VelocityTab", f"Error applying curve: {e}")
            )

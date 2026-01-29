# SPDX-License-Identifier: GPL-2.0-or-later
import json
import struct

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QGroupBox, QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
                              QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from widgets.combo_box import ArrowComboBox
from any_keycode_dialog import AnyKeycodeDialog
from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget2, KeyboardWidgetSimple, EncoderWidget, EncoderWidget2
from keycodes.keycodes import Keycode
from widgets.square_button import SquareButton
from tabbed_keycodes import TabbedKeycodes, keycode_filter_masked
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard
from editor.arpeggiator import DebugConsole
from protocol.keyboard_comm import (
    PARAM_CHANNEL_NUMBER, PARAM_TRANSPOSE_NUMBER, PARAM_TRANSPOSE_NUMBER2, PARAM_TRANSPOSE_NUMBER3,
    PARAM_HE_VELOCITY_CURVE, PARAM_HE_VELOCITY_MIN, PARAM_HE_VELOCITY_MAX,
    PARAM_KEYSPLIT_HE_VELOCITY_CURVE, PARAM_KEYSPLIT_HE_VELOCITY_MIN, PARAM_KEYSPLIT_HE_VELOCITY_MAX,
    PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE, PARAM_TRIPLESPLIT_HE_VELOCITY_MIN, PARAM_TRIPLESPLIT_HE_VELOCITY_MAX,
    # PARAM_AFTERTOUCH_MODE and PARAM_AFTERTOUCH_CC removed - aftertouch is now per-layer
    PARAM_BASE_SUSTAIN, PARAM_KEYSPLIT_SUSTAIN, PARAM_TRIPLESPLIT_SUSTAIN,
    PARAM_KEYSPLITCHANNEL, PARAM_KEYSPLIT2CHANNEL, PARAM_KEYSPLITSTATUS, PARAM_KEYSPLITTRANSPOSESTATUS, PARAM_KEYSPLITVELOCITYSTATUS,
    PARAM_VELOCITY_SENSITIVITY, PARAM_CC_SENSITIVITY
)


class Debouncer:
    """Debounce utility for delaying function calls until user stops interacting

    Usage:
        debouncer = Debouncer(200, my_function, arg1, arg2)
        # Call trigger() each time the event happens
        debouncer.trigger()  # Function will only execute 200ms after last trigger
    """
    def __init__(self, delay_ms, callback, *args, **kwargs):
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: callback(*args, **kwargs))
        self.delay_ms = delay_ms

    def trigger(self):
        """Trigger the debouncer - restarts the timer"""
        self.timer.stop()
        self.timer.start(self.delay_ms)

    def cancel(self):
        """Cancel pending callback"""
        self.timer.stop()


class QuickActuationWidget(QWidget):
    """Full-featured per-layer actuation controls in keymap editor"""

    # Signal emitted when "Enable Per-Key" is checked
    enable_per_key_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.device = None
        self.syncing = False
        self.current_layer = 0
        self.per_layer_enabled = False
        self.trigger_settings_ref = None  # Reference to TriggerSettingsTab

        # Cache all layer data in memory to avoid device I/O lag
        self.layer_data = []
        for _ in range(12):
            self.layer_data.append({
                'normal': 80,
                'midi': 80,
                'velocity': 2,  # Velocity mode (0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak)
                'vel_speed': 10,  # Velocity speed scale
                'aftertouch_mode': 0,  # 0=Off, 1=Reverse, 2=Bottom-Out, 3=Post-Act, 4=Vibrato
                'aftertouch_cc': 255,  # 255=Off (no CC), 0-127=CC number
                'vibrato_sensitivity': 100,  # 50-200 (percentage)
                'vibrato_decay_time': 200  # 0-2000 (milliseconds)
            })

        # MIDI settings (global, per keyboard)
        self.midi_settings = {
            'channel': 0,
            'transpose': 0,
            'sustain': 0,  # Allow
            'velocity_preset': 2,  # Medium
            'velocity_curve': 2,
            'velocity_min': 1,
            'velocity_max': 127,
            'keysplit_enabled': False,
            'keysplit_channel': 0,
            'keysplit_transpose': 0,
            'keysplit_sustain': 0,  # Allow
            'keysplit_velocity_curve': 2,
            'keysplit_velocity_min': 1,
            'keysplit_velocity_max': 127,
            'triplesplit_enabled': False,
            'triplesplit_channel': 0,
            'triplesplit_transpose': 0,
            'triplesplit_sustain': 0,  # Allow
            'triplesplit_velocity_curve': 2,
            'triplesplit_velocity_min': 1,
            'triplesplit_velocity_max': 127
        }

        # Global MIDI settings for velocity/aftertouch (not per-layer)
        self.global_midi_settings = {
            'velocity_mode': 2,         # 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
            'aftertouch_mode': 0,       # 0=Off, 1=Reverse, 2=Bottom-out, 3=Post-actuation, 4=Vibrato
            'aftertouch_cc': 255,       # 0-127=CC number, 255=off (poly AT only)
            'vibrato_sensitivity': 100, # 50-200 (percentage)
            'vibrato_decay_time': 200,  # 0-2000 (milliseconds)
            'min_press_time': 200,      # 50-500ms (slow press threshold)
            'max_press_time': 20        # 5-100ms (fast press threshold)
        }

        self.setMinimumWidth(320)
        self.setMaximumWidth(320)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 0, 10)  # No right margin for flush layout
        self.setLayout(layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabWidget { font-size: 10px; }")
        layout.addWidget(self.tab_widget)

        # Create Actuation Settings tab
        self.actuation_tab = self.create_actuation_tab()
        self.tab_widget.addTab(self.actuation_tab, "Actuation Settings")

        # Create MIDI Settings tab
        self.midi_tab = self.create_midi_tab()
        self.tab_widget.addTab(self.midi_tab, "MIDI Settings")

        # Create Advanced tab (formerly Aftertouch) - rightmost position
        self.advanced_tab = self.create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "Advanced")

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

    def create_actuation_tab(self):
        """Create the Actuation Settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Top row with checkboxes
        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(10)

        self.enable_per_key_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable Per-Key"))
        self.enable_per_key_checkbox.setStyleSheet("QCheckBox { font-weight: bold; font-size: 10px; } QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.enable_per_key_checkbox.stateChanged.connect(self.on_enable_per_key_toggled)
        top_row_layout.addWidget(self.create_help_label("Enable individual actuation point per key.\nConfigure in Trigger Settings tab."))
        top_row_layout.addWidget(self.enable_per_key_checkbox)

        top_row_layout.addWidget(self.create_help_label("Enable different actuation points per layer.\nWhen off, same actuation applies to all layers."))
        self.per_layer_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable Per-Layer Actuation"))
        self.per_layer_checkbox.setStyleSheet("QCheckBox { font-weight: bold; font-size: 10px; } QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_toggled)
        top_row_layout.addWidget(self.per_layer_checkbox)

        top_row_layout.addStretch()
        layout.addLayout(top_row_layout)

        # Layer indicator (only visible in per-layer mode)
        self.layer_label = QLabel(tr("QuickActuationWidget", "Layer 0"))
        self.layer_label.setStyleSheet("QLabel { font-weight: bold; font-size: 10px; color: #666; }")
        self.layer_label.setVisible(False)
        layout.addWidget(self.layer_label, alignment=Qt.AlignCenter)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Per-key mode message (shown when per-key actuation is enabled)
        self.per_key_message = QLabel(tr("QuickActuationWidget", "Per-key actuation enabled.\nChange per key actuation in Trigger Settings tab."))
        self.per_key_message.setStyleSheet("QLabel { font-style: italic; font-size: 10px; color: #888; padding: 10px; }")
        self.per_key_message.setAlignment(Qt.AlignCenter)
        self.per_key_message.setVisible(False)
        layout.addWidget(self.per_key_message)

        # Container for sliders (hidden when per-key is enabled)
        self.sliders_container = QWidget()
        sliders_layout = QVBoxLayout()
        sliders_layout.setContentsMargins(0, 0, 0, 0)
        sliders_layout.setSpacing(6)
        self.sliders_container.setLayout(sliders_layout)

        # Normal Keys Actuation slider - ALWAYS VISIBLE
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(4)
        slider_layout.addWidget(self.create_help_label("Actuation point for non-MIDI keys.\nLower = more sensitive, higher = deeper press required."))
        label = QLabel(tr("QuickActuationWidget", "Normal Keys:"))
        label.setMinimumWidth(75)
        label.setMaximumWidth(75)
        slider_layout.addWidget(label)

        self.normal_slider = QSlider(Qt.Horizontal)
        self.normal_slider.setMinimum(0)
        self.normal_slider.setMaximum(100)
        self.normal_slider.setValue(80)
        slider_layout.addWidget(self.normal_slider, 1)

        self.normal_value_label = QLabel("2.00mm")
        self.normal_value_label.setMinimumWidth(50)
        self.normal_value_label.setMaximumWidth(50)
        self.normal_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        slider_layout.addWidget(self.normal_value_label)

        sliders_layout.addLayout(slider_layout)
        self.normal_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('normal', v, self.normal_value_label)
        )

        # MIDI Keys Actuation slider - now always visible
        midi_slider_layout = QHBoxLayout()
        midi_slider_layout.setContentsMargins(0, 0, 0, 0)
        midi_slider_layout.setSpacing(4)
        midi_slider_layout.addWidget(self.create_help_label("Actuation point for MIDI note keys.\nLower = more sensitive, higher = deeper press required."))
        midi_label = QLabel(tr("QuickActuationWidget", "MIDI Keys:"))
        midi_label.setMinimumWidth(75)
        midi_label.setMaximumWidth(75)
        midi_slider_layout.addWidget(midi_label)

        self.midi_slider = QSlider(Qt.Horizontal)
        self.midi_slider.setMinimum(0)
        self.midi_slider.setMaximum(100)
        self.midi_slider.setValue(80)
        midi_slider_layout.addWidget(self.midi_slider, 1)

        self.midi_value_label = QLabel("2.00mm")
        self.midi_value_label.setMinimumWidth(50)
        self.midi_value_label.setMaximumWidth(50)
        self.midi_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        midi_slider_layout.addWidget(self.midi_value_label)

        sliders_layout.addLayout(midi_slider_layout)

        self.midi_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('midi', v, self.midi_value_label)
        )

        layout.addWidget(self.sliders_container)

        layout.addStretch()

        # Save button at the bottom
        self.save_btn = QPushButton(tr("QuickActuationWidget", "Save to All Layers"))
        self.save_btn.setMaximumHeight(24)
        self.save_btn.setStyleSheet("padding: 2px 6px; font-size: 9pt;")
        self.save_btn.clicked.connect(self.on_save_actuation)
        layout.addWidget(self.save_btn)

        return tab

    def create_advanced_tab(self):
        """Create the Advanced tab (velocity, aftertouch settings) - GLOBAL settings"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Global settings header
        header_label = QLabel(tr("QuickActuationWidget", "Global MIDI Settings"))
        header_label.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; color: #333; }")
        layout.addWidget(header_label, alignment=Qt.AlignCenter)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

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
        velocity_label = QLabel(tr("QuickActuationWidget", "Velocity:"))
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
        self.velocity_combo.currentIndexChanged.connect(self.on_combo_changed)
        velocity_layout.addWidget(self.velocity_combo, 1)
        layout.addLayout(velocity_layout)

        # Min Press Time slider (for slow press = max velocity)
        min_press_layout = QHBoxLayout()
        min_press_layout.setContentsMargins(0, 0, 0, 0)
        min_press_layout.setSpacing(4)
        min_press_layout.addWidget(self.create_help_label(
            "Slow press threshold (ms):\n"
            "Keys pressed slower than this time get minimum velocity.\n"
            "Lower = need slower press for soft notes."
        ))
        min_press_label = QLabel(tr("QuickActuationWidget", "Slow Press:"))
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
        layout.addLayout(min_press_layout)

        # Max Press Time slider (for fast press = min velocity)
        max_press_layout = QHBoxLayout()
        max_press_layout.setContentsMargins(0, 0, 0, 0)
        max_press_layout.setSpacing(4)
        max_press_layout.addWidget(self.create_help_label(
            "Fast press threshold (ms):\n"
            "Keys pressed faster than this time get maximum velocity.\n"
            "Higher = need faster press for loud notes."
        ))
        max_press_label = QLabel(tr("QuickActuationWidget", "Fast Press:"))
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
        layout.addLayout(max_press_layout)

        # Separator between velocity and aftertouch
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)

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
        mode_label = QLabel(tr("QuickActuationWidget", "Aftertouch Mode:"))
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
        layout.addLayout(mode_layout)

        # Aftertouch CC dropdown
        cc_layout = QHBoxLayout()
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(4)
        cc_layout.addWidget(self.create_help_label("MIDI CC number to send for aftertouch.\nOff: Send standard aftertouch messages\nCC#0-127: Send specified CC instead"))
        cc_label = QLabel(tr("QuickActuationWidget", "Aftertouch CC:"))
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
        layout.addLayout(cc_layout)

        # Vibrato Sensitivity slider (hidden by default)
        self.vibrato_sens_widget = QWidget()
        sens_layout = QHBoxLayout()
        sens_layout.setContentsMargins(0, 0, 0, 0)
        self.vibrato_sens_widget.setLayout(sens_layout)

        sens_layout.addWidget(self.create_help_label("Wiggle key more = more aftertouch value.\n50% = Less sensitive, 200% = Very sensitive"))
        sens_label = QLabel(tr("QuickActuationWidget", "Vibrato Sensitivity:"))
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

        layout.addWidget(self.vibrato_sens_widget)
        self.vibrato_sens_widget.setVisible(False)

        # Vibrato Decay Time slider (hidden by default)
        self.vibrato_decay_widget = QWidget()
        decay_layout = QHBoxLayout()
        decay_layout.setContentsMargins(0, 0, 0, 0)
        self.vibrato_decay_widget.setLayout(decay_layout)

        decay_layout.addWidget(self.create_help_label("How long aftertouch value lasts after key wiggle stops.\n0ms = Instant decay, 2000ms = Slow decay"))
        decay_label = QLabel(tr("QuickActuationWidget", "Vibrato Decay:"))
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

        layout.addWidget(self.vibrato_decay_widget)
        self.vibrato_decay_widget.setVisible(False)

        layout.addStretch()

        # Save button
        self.advanced_save_btn = QPushButton(tr("QuickActuationWidget", "Save Advanced Settings"))
        self.advanced_save_btn.setMaximumHeight(24)
        self.advanced_save_btn.setStyleSheet("padding: 2px 6px; font-size: 9pt;")
        self.advanced_save_btn.clicked.connect(self.on_save_advanced)
        layout.addWidget(self.advanced_save_btn)

        # Debug console for HID communication debugging
        self.advanced_debug_console = DebugConsole("Advanced Settings Debug Console")
        layout.addWidget(self.advanced_debug_console)

        return tab

    def on_aftertouch_mode_changed(self, index):
        """Handle aftertouch mode change - show/hide vibrato controls (GLOBAL)"""
        mode = self.aftertouch_mode_combo.currentData()
        is_vibrato = (mode == 4)
        self.vibrato_sens_widget.setVisible(is_vibrato)
        self.vibrato_decay_widget.setVisible(is_vibrato)
        # Update global settings
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

    def on_min_press_changed(self, value):
        """Handle min press time slider change (GLOBAL)"""
        self.min_press_value.setText(f"{value}ms")
        self.global_midi_settings['min_press_time'] = value

    def on_max_press_changed(self, value):
        """Handle max press time slider change (GLOBAL)"""
        self.max_press_value.setText(f"{value}ms")
        self.global_midi_settings['max_press_time'] = value

    def on_save_advanced(self):
        """Save advanced settings (velocity, aftertouch) to keyboard - GLOBAL settings"""
        from protocol.keyboard_comm import (
            PARAM_VELOCITY_MODE, PARAM_AFTERTOUCH_MODE, PARAM_AFTERTOUCH_CC,
            PARAM_VIBRATO_SENSITIVITY, PARAM_VIBRATO_DECAY_TIME,
            PARAM_MIN_PRESS_TIME, PARAM_MAX_PRESS_TIME,
            HID_CMD_SET_KEYBOARD_PARAM_SINGLE
        )

        # Start debug console operation
        self.advanced_debug_console.mark_operation_start()
        self.advanced_debug_console.log("=" * 50, "DEBUG")
        self.advanced_debug_console.log("SAVE ADVANCED SETTINGS - Starting", "INFO")
        self.advanced_debug_console.log("=" * 50, "DEBUG")

        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                self.advanced_debug_console.log("ERROR: Device not connected", "ERROR")
                self.advanced_debug_console.mark_operation_end(success=False)
                raise RuntimeError("Device not connected")

            settings = self.global_midi_settings
            kb = self.device.keyboard

            # Log HID command info
            self.advanced_debug_console.log(f"HID Command: SET_KEYBOARD_PARAM_SINGLE (0x{HID_CMD_SET_KEYBOARD_PARAM_SINGLE:02X})", "DEBUG")
            self.advanced_debug_console.log(f"Device: {self.device.desc.get('name', 'Unknown')}", "DEBUG")
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

    def create_midi_tab(self):
        """Create the MIDI Settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)

        # Advanced checkbox and split enable checkboxes at the top
        advanced_row = QHBoxLayout()
        advanced_row.setContentsMargins(0, 0, 0, 0)
        advanced_row.setSpacing(15)

        self.midi_advanced_checkbox = QCheckBox(tr("QuickActuationWidget", "Show Advanced"))
        self.midi_advanced_checkbox.setStyleSheet("QCheckBox { font-size: 10px; } QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.midi_advanced_checkbox.stateChanged.connect(self.on_midi_advanced_toggled)
        advanced_row.addWidget(self.midi_advanced_checkbox)

        # Enable KeySplit - Checkbox on left, labels on right vertically centered
        keysplit_container = QHBoxLayout()
        keysplit_container.setSpacing(5)
        keysplit_container.setContentsMargins(0, 0, 0, 0)

        self.keysplit_enabled_checkbox = QCheckBox()
        self.keysplit_enabled_checkbox.setStyleSheet("QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.keysplit_enabled_checkbox.stateChanged.connect(self.on_keysplit_enabled_toggled)
        keysplit_container.addWidget(self.keysplit_enabled_checkbox, 0, Qt.AlignCenter)

        keysplit_labels = QVBoxLayout()
        keysplit_labels.setSpacing(0)
        keysplit_labels.setContentsMargins(0, 0, 0, 0)

        enable_label_ks = QLabel(tr("QuickActuationWidget", "Enable"))
        enable_label_ks.setStyleSheet("QLabel { font-size: 9px; }")
        enable_label_ks.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        keysplit_labels.addWidget(enable_label_ks)

        keysplit_label = QLabel(tr("QuickActuationWidget", "KeySplit"))
        keysplit_label.setStyleSheet("QLabel { font-size: 10px; }")
        keysplit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        keysplit_labels.addWidget(keysplit_label)

        keysplit_container.addLayout(keysplit_labels)

        keysplit_widget = QWidget()
        keysplit_widget.setLayout(keysplit_container)
        keysplit_widget.setVisible(False)
        advanced_row.addWidget(keysplit_widget)
        self.keysplit_enable_widget = keysplit_widget

        # Enable TripleSplit - Checkbox on left, labels on right vertically centered
        triplesplit_container = QHBoxLayout()
        triplesplit_container.setSpacing(5)
        triplesplit_container.setContentsMargins(0, 0, 0, 0)

        self.triplesplit_enabled_checkbox = QCheckBox()
        self.triplesplit_enabled_checkbox.setStyleSheet("QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.triplesplit_enabled_checkbox.stateChanged.connect(self.on_triplesplit_enabled_toggled)
        triplesplit_container.addWidget(self.triplesplit_enabled_checkbox, 0, Qt.AlignCenter)

        triplesplit_labels = QVBoxLayout()
        triplesplit_labels.setSpacing(0)
        triplesplit_labels.setContentsMargins(0, 0, 0, 0)

        enable_label_ts = QLabel(tr("QuickActuationWidget", "Enable"))
        enable_label_ts.setStyleSheet("QLabel { font-size: 9px; }")
        enable_label_ts.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        triplesplit_labels.addWidget(enable_label_ts)

        triplesplit_label = QLabel(tr("QuickActuationWidget", "TripleSplit"))
        triplesplit_label.setStyleSheet("QLabel { font-size: 10px; }")
        triplesplit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        triplesplit_labels.addWidget(triplesplit_label)

        triplesplit_container.addLayout(triplesplit_labels)

        triplesplit_widget = QWidget()
        triplesplit_widget.setLayout(triplesplit_container)
        triplesplit_widget.setVisible(False)
        advanced_row.addWidget(triplesplit_widget)
        self.triplesplit_enable_widget = triplesplit_widget

        advanced_row.addStretch()
        layout.addLayout(advanced_row)

        # Container that will hold tabbed view (always visible)
        self.midi_settings_container = QWidget()
        self.midi_settings_layout = QVBoxLayout()
        self.midi_settings_layout.setContentsMargins(0, 0, 0, 0)
        self.midi_settings_layout.setSpacing(6)
        self.midi_settings_container.setLayout(self.midi_settings_layout)
        layout.addWidget(self.midi_settings_container)

        # Create tabbed container (always shown, tabs dynamically added/removed)
        self.midi_tabs = QTabWidget()
        self.midi_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid palette(mid); }
            QTabBar::tab {
                font-size: 9px;
                padding: 4px 8px;
                min-width: 53px;
            }
            QTabBar {
                qproperty-expanding: true;
            }
        """)

        # Create simple controls for non-advanced mode
        self.simple_midi_widget = self.create_simple_midi_controls()
        self.midi_settings_layout.addWidget(self.simple_midi_widget)

        # Create tabs for advanced mode
        self.basic_tab_widget = self.create_basic_midi_controls()
        self.keysplit_tab_widget = self.create_keysplit_midi_controls()
        self.triplesplit_tab_widget = self.create_triplesplit_midi_controls()

        self.midi_tabs.addTab(self.basic_tab_widget, "Basic")

        self.midi_settings_layout.addWidget(self.midi_tabs)
        self.midi_tabs.setVisible(False)  # Hidden by default, shown when advanced mode is on

        layout.addStretch()

        # Save MIDI Settings button
        self.save_midi_btn = QPushButton(tr("QuickActuationWidget", "Save MIDI Settings"))
        self.save_midi_btn.setMaximumHeight(24)
        self.save_midi_btn.setStyleSheet("padding: 2px 6px; font-size: 9pt;")
        self.save_midi_btn.clicked.connect(self.on_save_midi)
        layout.addWidget(self.save_midi_btn)

        return tab

    def create_simple_midi_controls(self):
        """Create simple MIDI controls for non-advanced mode (channel, transpose, velocity preset only)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        # Channel slider
        ch_row = QHBoxLayout()
        ch_row.setContentsMargins(0, 0, 0, 0)
        ch_row.setSpacing(6)

        ch_label = QLabel(tr("QuickActuationWidget", "Channel:"))
        ch_label.setStyleSheet("QLabel { font-size: 14px; }")
        ch_label.setMinimumWidth(90)
        ch_label.setMaximumWidth(90)
        ch_row.addWidget(ch_label)

        self.simple_channel_slider = QSlider(Qt.Horizontal)
        self.simple_channel_slider.setMinimum(0)
        self.simple_channel_slider.setMaximum(15)
        self.simple_channel_slider.setValue(0)
        self.simple_channel_slider.valueChanged.connect(lambda v: self.on_simple_channel_changed(v))
        ch_row.addWidget(self.simple_channel_slider, 1)

        self.simple_channel_label = QLabel("1")
        self.simple_channel_label.setMinimumWidth(35)
        self.simple_channel_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.simple_channel_label.setAlignment(Qt.AlignCenter)
        ch_row.addWidget(self.simple_channel_label)

        layout.addLayout(ch_row)

        # Transposition slider
        trans_row = QHBoxLayout()
        trans_row.setContentsMargins(0, 0, 0, 0)
        trans_row.setSpacing(6)

        trans_label = QLabel(tr("QuickActuationWidget", "Transposition:"))
        trans_label.setStyleSheet("QLabel { font-size: 14px; }")
        trans_label.setMinimumWidth(90)
        trans_label.setMaximumWidth(90)
        trans_row.addWidget(trans_label)

        self.simple_transpose_slider = QSlider(Qt.Horizontal)
        self.simple_transpose_slider.setMinimum(-12)
        self.simple_transpose_slider.setMaximum(12)
        self.simple_transpose_slider.setValue(0)
        self.simple_transpose_slider.valueChanged.connect(lambda v: self.on_simple_transpose_changed(v))
        trans_row.addWidget(self.simple_transpose_slider, 1)

        self.simple_transpose_label = QLabel("0")
        self.simple_transpose_label.setMinimumWidth(35)
        self.simple_transpose_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.simple_transpose_label.setAlignment(Qt.AlignCenter)
        trans_row.addWidget(self.simple_transpose_label)

        layout.addLayout(trans_row)

        # Velocity preset (label next to dropdown)
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(6)

        preset_label = QLabel(tr("QuickActuationWidget", "Velocity:"))
        preset_label.setStyleSheet("QLabel { font-size: 14px; }")
        preset_label.setMinimumWidth(90)
        preset_label.setMaximumWidth(90)
        preset_row.addWidget(preset_label)

        self.simple_velocity_preset_combo = ArrowComboBox()
        self.simple_velocity_preset_combo.setFixedWidth(70)
        self.simple_velocity_preset_combo.setMaximumHeight(35)
        self.simple_velocity_preset_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.simple_velocity_preset_combo.setEditable(True)
        self.simple_velocity_preset_combo.lineEdit().setReadOnly(True)
        self.simple_velocity_preset_combo.lineEdit().setAlignment(Qt.AlignCenter)
        # Factory curves (0-6)
        self.simple_velocity_preset_combo.addItem("Linear", 0)
        self.simple_velocity_preset_combo.addItem("Aggro", 1)
        self.simple_velocity_preset_combo.addItem("Slow", 2)
        self.simple_velocity_preset_combo.addItem("Smooth", 3)
        self.simple_velocity_preset_combo.addItem("Steep", 4)
        self.simple_velocity_preset_combo.addItem("Instant", 5)
        self.simple_velocity_preset_combo.addItem("Turbo", 6)
        # User curves (7-16) - will be populated when keyboard connects
        for i in range(10):
            self.simple_velocity_preset_combo.addItem(f"User {i+1}", 7 + i)
        self.simple_velocity_preset_combo.setCurrentIndex(0)
        self.simple_velocity_preset_combo.currentIndexChanged.connect(self.on_velocity_preset_changed)
        preset_row.addWidget(self.simple_velocity_preset_combo)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        return widget

    def create_basic_midi_controls(self):
        """Create basic MIDI controls (channel, transpose, sustain, velocity)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(10, 10, 10, 10)
        widget.setLayout(layout)

        # Channel slider
        ch_row = QHBoxLayout()
        ch_row.setContentsMargins(0, 0, 0, 0)
        ch_row.setSpacing(6)

        ch_label = QLabel(tr("QuickActuationWidget", "Channel:"))
        ch_label.setStyleSheet("QLabel { font-size: 14px; }")
        ch_label.setMinimumWidth(90)
        ch_label.setMaximumWidth(90)
        ch_row.addWidget(ch_label)

        self.midi_channel_slider = QSlider(Qt.Horizontal)
        self.midi_channel_slider.setMinimum(0)
        self.midi_channel_slider.setMaximum(15)
        self.midi_channel_slider.setValue(0)
        self.midi_channel_slider.valueChanged.connect(lambda v: self.on_midi_channel_changed(v))
        ch_row.addWidget(self.midi_channel_slider, 1)

        self.midi_channel_label = QLabel("1")
        self.midi_channel_label.setMinimumWidth(35)
        self.midi_channel_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.midi_channel_label.setAlignment(Qt.AlignCenter)
        ch_row.addWidget(self.midi_channel_label)

        layout.addLayout(ch_row)

        # Transposition slider
        trans_row = QHBoxLayout()
        trans_row.setContentsMargins(0, 0, 0, 0)
        trans_row.setSpacing(6)

        trans_label = QLabel(tr("QuickActuationWidget", "Transposition:"))
        trans_label.setStyleSheet("QLabel { font-size: 14px; }")
        trans_label.setMinimumWidth(90)
        trans_label.setMaximumWidth(90)
        trans_row.addWidget(trans_label)

        self.midi_transpose_slider = QSlider(Qt.Horizontal)
        self.midi_transpose_slider.setMinimum(-12)
        self.midi_transpose_slider.setMaximum(12)
        self.midi_transpose_slider.setValue(0)
        self.midi_transpose_slider.valueChanged.connect(lambda v: self.on_midi_transpose_changed(v))
        trans_row.addWidget(self.midi_transpose_slider, 1)

        self.midi_transpose_label = QLabel("0")
        self.midi_transpose_label.setMinimumWidth(35)
        self.midi_transpose_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.midi_transpose_label.setAlignment(Qt.AlignCenter)
        trans_row.addWidget(self.midi_transpose_label)

        layout.addLayout(trans_row)

        # Velocity Min (slider with label)
        vel_min_layout = QHBoxLayout()
        vel_min_layout.setSpacing(2)
        vel_min_title = QLabel(tr("QuickActuationWidget", "Vel Min"))
        vel_min_title.setMinimumWidth(60)
        vel_min_title.setStyleSheet("QLabel { font-size: 14px; }")
        vel_min_layout.addWidget(vel_min_title)
        self.midi_velocity_min = QSlider(Qt.Horizontal)
        self.midi_velocity_min.setMinimum(1)
        self.midi_velocity_min.setMaximum(127)
        self.midi_velocity_min.setValue(1)
        self.midi_velocity_min.valueChanged.connect(lambda v: self.on_midi_velocity_slider_changed('min', v))
        vel_min_layout.addWidget(self.midi_velocity_min, 1)
        self.midi_velocity_min_label = QLabel("1")
        self.midi_velocity_min_label.setMinimumWidth(35)
        self.midi_velocity_min_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12px; }")
        self.midi_velocity_min_label.setAlignment(Qt.AlignCenter)
        vel_min_layout.addWidget(self.midi_velocity_min_label)
        layout.addLayout(vel_min_layout)

        # Velocity Max (slider with label)
        vel_max_layout = QHBoxLayout()
        vel_max_layout.setSpacing(2)
        vel_max_title = QLabel(tr("QuickActuationWidget", "Vel Max"))
        vel_max_title.setMinimumWidth(60)
        vel_max_title.setStyleSheet("QLabel { font-size: 14px; }")
        vel_max_layout.addWidget(vel_max_title)
        self.midi_velocity_max = QSlider(Qt.Horizontal)
        self.midi_velocity_max.setMinimum(1)
        self.midi_velocity_max.setMaximum(127)
        self.midi_velocity_max.setValue(127)
        self.midi_velocity_max.valueChanged.connect(lambda v: self.on_midi_velocity_slider_changed('max', v))
        vel_max_layout.addWidget(self.midi_velocity_max, 1)
        self.midi_velocity_max_label = QLabel("127")
        self.midi_velocity_max_label.setMinimumWidth(35)
        self.midi_velocity_max_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12px; }")
        self.midi_velocity_max_label.setAlignment(Qt.AlignCenter)
        vel_max_layout.addWidget(self.midi_velocity_max_label)
        layout.addLayout(vel_max_layout)

        # Velocity Curve (label next to dropdown)
        curve_row = QHBoxLayout()
        curve_row.setContentsMargins(0, 0, 0, 0)
        curve_row.setSpacing(6)

        curve_label = QLabel(tr("QuickActuationWidget", "Velocity Curve:"))
        curve_label.setStyleSheet("QLabel { font-size: 14px; }")
        curve_label.setMinimumWidth(100)
        curve_label.setMaximumWidth(100)
        curve_row.addWidget(curve_label)

        self.midi_velocity_curve = ArrowComboBox()
        self.midi_velocity_curve.setMaximumWidth(120)
        self.midi_velocity_curve.setMaximumHeight(30)
        self.midi_velocity_curve.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.midi_velocity_curve.setEditable(True)
        self.midi_velocity_curve.lineEdit().setReadOnly(True)
        self.midi_velocity_curve.lineEdit().setAlignment(Qt.AlignCenter)
        # Factory curves (0-6)
        self.midi_velocity_curve.addItem("Linear", 0)
        self.midi_velocity_curve.addItem("Aggro", 1)
        self.midi_velocity_curve.addItem("Slow", 2)
        self.midi_velocity_curve.addItem("Smooth", 3)
        self.midi_velocity_curve.addItem("Steep", 4)
        self.midi_velocity_curve.addItem("Instant", 5)
        self.midi_velocity_curve.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            self.midi_velocity_curve.addItem(f"User {i+1}", 7 + i)
        self.midi_velocity_curve.setCurrentIndex(0)
        self.midi_velocity_curve.currentIndexChanged.connect(self.on_midi_settings_changed)
        curve_row.addWidget(self.midi_velocity_curve)
        curve_row.addStretch()
        layout.addLayout(curve_row)

        # 5px spacing between velocity curve and sustain
        layout.addSpacing(5)

        # Sustain (label next to dropdown) - below velocity min/max - hidden unless splits enabled
        sustain_row = QHBoxLayout()
        sustain_row.setContentsMargins(0, 0, 0, 0)
        sustain_row.setSpacing(6)

        sustain_label = QLabel(tr("QuickActuationWidget", "Sustain:"))
        sustain_label.setStyleSheet("QLabel { font-size: 14px; }")
        sustain_label.setMinimumWidth(100)
        sustain_label.setMaximumWidth(100)
        sustain_row.addWidget(sustain_label)

        self.midi_sustain_combo = ArrowComboBox()
        self.midi_sustain_combo.setMaximumWidth(120)
        self.midi_sustain_combo.setMaximumHeight(30)
        self.midi_sustain_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.midi_sustain_combo.setEditable(True)
        self.midi_sustain_combo.lineEdit().setReadOnly(True)
        self.midi_sustain_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.midi_sustain_combo.addItem("Allow", 0)
        self.midi_sustain_combo.addItem("Ignore", 1)
        self.midi_sustain_combo.setCurrentIndex(0)
        self.midi_sustain_combo.currentIndexChanged.connect(self.on_midi_settings_changed)
        sustain_row.addWidget(self.midi_sustain_combo)
        sustain_row.addStretch()

        self.midi_sustain_widget = QWidget()
        self.midi_sustain_widget.setLayout(sustain_row)
        self.midi_sustain_widget.setVisible(False)  # Hidden by default
        layout.addWidget(self.midi_sustain_widget)

        return widget

    def create_keysplit_midi_controls(self):
        """Create KeySplit MIDI controls"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(10, 10, 10, 10)
        widget.setLayout(layout)

        # Channel slider
        ch_row = QHBoxLayout()
        ch_row.setContentsMargins(0, 0, 0, 0)
        ch_row.setSpacing(6)

        ch_label = QLabel(tr("QuickActuationWidget", "Channel:"))
        ch_label.setStyleSheet("QLabel { font-size: 14px; }")
        ch_label.setMinimumWidth(90)
        ch_label.setMaximumWidth(90)
        ch_row.addWidget(ch_label)

        self.keysplit_channel_slider = QSlider(Qt.Horizontal)
        self.keysplit_channel_slider.setMinimum(0)
        self.keysplit_channel_slider.setMaximum(15)
        self.keysplit_channel_slider.setValue(0)
        self.keysplit_channel_slider.valueChanged.connect(lambda v: self.on_keysplit_channel_changed(v))
        ch_row.addWidget(self.keysplit_channel_slider, 1)

        self.keysplit_channel_label = QLabel("1")
        self.keysplit_channel_label.setMinimumWidth(35)
        self.keysplit_channel_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.keysplit_channel_label.setAlignment(Qt.AlignCenter)
        ch_row.addWidget(self.keysplit_channel_label)

        layout.addLayout(ch_row)

        # Transposition slider
        trans_row = QHBoxLayout()
        trans_row.setContentsMargins(0, 0, 0, 0)
        trans_row.setSpacing(6)

        trans_label = QLabel(tr("QuickActuationWidget", "Transposition:"))
        trans_label.setStyleSheet("QLabel { font-size: 14px; }")
        trans_label.setMinimumWidth(90)
        trans_label.setMaximumWidth(90)
        trans_row.addWidget(trans_label)

        self.keysplit_transpose_slider = QSlider(Qt.Horizontal)
        self.keysplit_transpose_slider.setMinimum(-12)
        self.keysplit_transpose_slider.setMaximum(12)
        self.keysplit_transpose_slider.setValue(0)
        self.keysplit_transpose_slider.valueChanged.connect(lambda v: self.on_keysplit_transpose_changed(v))
        trans_row.addWidget(self.keysplit_transpose_slider, 1)

        self.keysplit_transpose_label = QLabel("0")
        self.keysplit_transpose_label.setMinimumWidth(35)
        self.keysplit_transpose_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.keysplit_transpose_label.setAlignment(Qt.AlignCenter)
        trans_row.addWidget(self.keysplit_transpose_label)

        layout.addLayout(trans_row)

        # Velocity Min (slider with label)
        ks_min_layout = QHBoxLayout()
        ks_min_layout.setSpacing(2)
        ks_min_title = QLabel(tr("QuickActuationWidget", "Vel Min"))
        ks_min_title.setMinimumWidth(60)
        ks_min_title.setStyleSheet("QLabel { font-size: 14px; }")
        ks_min_layout.addWidget(ks_min_title)
        self.keysplit_velocity_min = QSlider(Qt.Horizontal)
        self.keysplit_velocity_min.setMinimum(1)
        self.keysplit_velocity_min.setMaximum(127)
        self.keysplit_velocity_min.setValue(1)
        self.keysplit_velocity_min.valueChanged.connect(lambda v: self.on_keysplit_velocity_slider_changed('min', v))
        ks_min_layout.addWidget(self.keysplit_velocity_min, 1)
        self.keysplit_velocity_min_label = QLabel("1")
        self.keysplit_velocity_min_label.setMinimumWidth(35)
        self.keysplit_velocity_min_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12px; }")
        self.keysplit_velocity_min_label.setAlignment(Qt.AlignCenter)
        ks_min_layout.addWidget(self.keysplit_velocity_min_label)
        layout.addLayout(ks_min_layout)

        # Velocity Max (slider with label)
        ks_max_layout = QHBoxLayout()
        ks_max_layout.setSpacing(2)
        ks_max_title = QLabel(tr("QuickActuationWidget", "Vel Max"))
        ks_max_title.setMinimumWidth(60)
        ks_max_title.setStyleSheet("QLabel { font-size: 14px; }")
        ks_max_layout.addWidget(ks_max_title)
        self.keysplit_velocity_max = QSlider(Qt.Horizontal)
        self.keysplit_velocity_max.setMinimum(1)
        self.keysplit_velocity_max.setMaximum(127)
        self.keysplit_velocity_max.setValue(127)
        self.keysplit_velocity_max.valueChanged.connect(lambda v: self.on_keysplit_velocity_slider_changed('max', v))
        ks_max_layout.addWidget(self.keysplit_velocity_max, 1)
        self.keysplit_velocity_max_label = QLabel("127")
        self.keysplit_velocity_max_label.setMinimumWidth(35)
        self.keysplit_velocity_max_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12px; }")
        self.keysplit_velocity_max_label.setAlignment(Qt.AlignCenter)
        ks_max_layout.addWidget(self.keysplit_velocity_max_label)
        layout.addLayout(ks_max_layout)

        # Velocity Curve (label next to dropdown)
        curve_row = QHBoxLayout()
        curve_row.setContentsMargins(0, 0, 0, 0)
        curve_row.setSpacing(6)

        curve_label = QLabel(tr("QuickActuationWidget", "Velocity Curve:"))
        curve_label.setStyleSheet("QLabel { font-size: 14px; }")
        curve_label.setMinimumWidth(100)
        curve_label.setMaximumWidth(100)
        curve_row.addWidget(curve_label)

        self.keysplit_velocity_curve = ArrowComboBox()
        self.keysplit_velocity_curve.setMaximumWidth(120)
        self.keysplit_velocity_curve.setMaximumHeight(30)
        self.keysplit_velocity_curve.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.keysplit_velocity_curve.setEditable(True)
        self.keysplit_velocity_curve.lineEdit().setReadOnly(True)
        self.keysplit_velocity_curve.lineEdit().setAlignment(Qt.AlignCenter)
        # Factory curves (0-6)
        self.keysplit_velocity_curve.addItem("Linear", 0)
        self.keysplit_velocity_curve.addItem("Aggro", 1)
        self.keysplit_velocity_curve.addItem("Slow", 2)
        self.keysplit_velocity_curve.addItem("Smooth", 3)
        self.keysplit_velocity_curve.addItem("Steep", 4)
        self.keysplit_velocity_curve.addItem("Instant", 5)
        self.keysplit_velocity_curve.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            self.keysplit_velocity_curve.addItem(f"User {i+1}", 7 + i)
        self.keysplit_velocity_curve.setCurrentIndex(0)
        self.keysplit_velocity_curve.currentIndexChanged.connect(self.on_midi_settings_changed)
        curve_row.addWidget(self.keysplit_velocity_curve)
        curve_row.addStretch()
        layout.addLayout(curve_row)

        # 5px spacing between velocity curve and sustain
        layout.addSpacing(5)

        # Sustain (label next to dropdown) - below velocity min/max
        sustain_row = QHBoxLayout()
        sustain_row.setContentsMargins(0, 0, 0, 0)
        sustain_row.setSpacing(6)

        sustain_label = QLabel(tr("QuickActuationWidget", "Sustain:"))
        sustain_label.setStyleSheet("QLabel { font-size: 14px; }")
        sustain_label.setMinimumWidth(100)
        sustain_label.setMaximumWidth(100)
        sustain_row.addWidget(sustain_label)

        self.keysplit_sustain_combo = ArrowComboBox()
        self.keysplit_sustain_combo.setMaximumWidth(120)
        self.keysplit_sustain_combo.setMaximumHeight(30)
        self.keysplit_sustain_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.keysplit_sustain_combo.setEditable(True)
        self.keysplit_sustain_combo.lineEdit().setReadOnly(True)
        self.keysplit_sustain_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.keysplit_sustain_combo.addItem("Allow", 0)
        self.keysplit_sustain_combo.addItem("Ignore", 1)
        self.keysplit_sustain_combo.setCurrentIndex(0)
        self.keysplit_sustain_combo.currentIndexChanged.connect(self.on_midi_settings_changed)
        sustain_row.addWidget(self.keysplit_sustain_combo)
        sustain_row.addStretch()
        layout.addLayout(sustain_row)

        return widget

    def create_triplesplit_midi_controls(self):
        """Create TripleSplit MIDI controls"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(10, 10, 10, 10)
        widget.setLayout(layout)

        # Channel slider
        ch_row = QHBoxLayout()
        ch_row.setContentsMargins(0, 0, 0, 0)
        ch_row.setSpacing(6)

        ch_label = QLabel(tr("QuickActuationWidget", "Channel:"))
        ch_label.setStyleSheet("QLabel { font-size: 14px; }")
        ch_label.setMinimumWidth(90)
        ch_label.setMaximumWidth(90)
        ch_row.addWidget(ch_label)

        self.triplesplit_channel_slider = QSlider(Qt.Horizontal)
        self.triplesplit_channel_slider.setMinimum(0)
        self.triplesplit_channel_slider.setMaximum(15)
        self.triplesplit_channel_slider.setValue(0)
        self.triplesplit_channel_slider.valueChanged.connect(lambda v: self.on_triplesplit_channel_changed(v))
        ch_row.addWidget(self.triplesplit_channel_slider, 1)

        self.triplesplit_channel_label = QLabel("1")
        self.triplesplit_channel_label.setMinimumWidth(35)
        self.triplesplit_channel_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.triplesplit_channel_label.setAlignment(Qt.AlignCenter)
        ch_row.addWidget(self.triplesplit_channel_label)

        layout.addLayout(ch_row)

        # Transposition slider
        trans_row = QHBoxLayout()
        trans_row.setContentsMargins(0, 0, 0, 0)
        trans_row.setSpacing(6)

        trans_label = QLabel(tr("QuickActuationWidget", "Transposition:"))
        trans_label.setStyleSheet("QLabel { font-size: 14px; }")
        trans_label.setMinimumWidth(90)
        trans_label.setMaximumWidth(90)
        trans_row.addWidget(trans_label)

        self.triplesplit_transpose_slider = QSlider(Qt.Horizontal)
        self.triplesplit_transpose_slider.setMinimum(-12)
        self.triplesplit_transpose_slider.setMaximum(12)
        self.triplesplit_transpose_slider.setValue(0)
        self.triplesplit_transpose_slider.valueChanged.connect(lambda v: self.on_triplesplit_transpose_changed(v))
        trans_row.addWidget(self.triplesplit_transpose_slider, 1)

        self.triplesplit_transpose_label = QLabel("0")
        self.triplesplit_transpose_label.setMinimumWidth(35)
        self.triplesplit_transpose_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; }")
        self.triplesplit_transpose_label.setAlignment(Qt.AlignCenter)
        trans_row.addWidget(self.triplesplit_transpose_label)

        layout.addLayout(trans_row)

        # Velocity Min (slider with label)
        ts_min_layout = QHBoxLayout()
        ts_min_layout.setSpacing(2)
        ts_min_title = QLabel(tr("QuickActuationWidget", "Vel Min"))
        ts_min_title.setMinimumWidth(60)
        ts_min_title.setStyleSheet("QLabel { font-size: 14px; }")
        ts_min_layout.addWidget(ts_min_title)
        self.triplesplit_velocity_min = QSlider(Qt.Horizontal)
        self.triplesplit_velocity_min.setMinimum(1)
        self.triplesplit_velocity_min.setMaximum(127)
        self.triplesplit_velocity_min.setValue(1)
        self.triplesplit_velocity_min.valueChanged.connect(lambda v: self.on_triplesplit_velocity_slider_changed('min', v))
        ts_min_layout.addWidget(self.triplesplit_velocity_min, 1)
        self.triplesplit_velocity_min_label = QLabel("1")
        self.triplesplit_velocity_min_label.setMinimumWidth(35)
        self.triplesplit_velocity_min_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12px; }")
        self.triplesplit_velocity_min_label.setAlignment(Qt.AlignCenter)
        ts_min_layout.addWidget(self.triplesplit_velocity_min_label)
        layout.addLayout(ts_min_layout)

        # Velocity Max (slider with label)
        ts_max_layout = QHBoxLayout()
        ts_max_layout.setSpacing(2)
        ts_max_title = QLabel(tr("QuickActuationWidget", "Vel Max"))
        ts_max_title.setMinimumWidth(60)
        ts_max_title.setStyleSheet("QLabel { font-size: 14px; }")
        ts_max_layout.addWidget(ts_max_title)
        self.triplesplit_velocity_max = QSlider(Qt.Horizontal)
        self.triplesplit_velocity_max.setMinimum(1)
        self.triplesplit_velocity_max.setMaximum(127)
        self.triplesplit_velocity_max.setValue(127)
        self.triplesplit_velocity_max.valueChanged.connect(lambda v: self.on_triplesplit_velocity_slider_changed('max', v))
        ts_max_layout.addWidget(self.triplesplit_velocity_max, 1)
        self.triplesplit_velocity_max_label = QLabel("127")
        self.triplesplit_velocity_max_label.setMinimumWidth(35)
        self.triplesplit_velocity_max_label.setStyleSheet("QLabel { font-weight: bold; font-size: 12px; }")
        self.triplesplit_velocity_max_label.setAlignment(Qt.AlignCenter)
        ts_max_layout.addWidget(self.triplesplit_velocity_max_label)
        layout.addLayout(ts_max_layout)

        # Velocity Curve (label next to dropdown)
        curve_row = QHBoxLayout()
        curve_row.setContentsMargins(0, 0, 0, 0)
        curve_row.setSpacing(6)

        curve_label = QLabel(tr("QuickActuationWidget", "Velocity Curve:"))
        curve_label.setStyleSheet("QLabel { font-size: 14px; }")
        curve_label.setMinimumWidth(100)
        curve_label.setMaximumWidth(100)
        curve_row.addWidget(curve_label)

        self.triplesplit_velocity_curve = ArrowComboBox()
        self.triplesplit_velocity_curve.setMaximumWidth(120)
        self.triplesplit_velocity_curve.setMaximumHeight(30)
        self.triplesplit_velocity_curve.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.triplesplit_velocity_curve.setEditable(True)
        self.triplesplit_velocity_curve.lineEdit().setReadOnly(True)
        self.triplesplit_velocity_curve.lineEdit().setAlignment(Qt.AlignCenter)
        # Factory curves (0-6)
        self.triplesplit_velocity_curve.addItem("Linear", 0)
        self.triplesplit_velocity_curve.addItem("Aggro", 1)
        self.triplesplit_velocity_curve.addItem("Slow", 2)
        self.triplesplit_velocity_curve.addItem("Smooth", 3)
        self.triplesplit_velocity_curve.addItem("Steep", 4)
        self.triplesplit_velocity_curve.addItem("Instant", 5)
        self.triplesplit_velocity_curve.addItem("Turbo", 6)
        # User curves (7-16)
        for i in range(10):
            self.triplesplit_velocity_curve.addItem(f"User {i+1}", 7 + i)
        self.triplesplit_velocity_curve.setCurrentIndex(0)
        self.triplesplit_velocity_curve.currentIndexChanged.connect(self.on_midi_settings_changed)
        curve_row.addWidget(self.triplesplit_velocity_curve)
        curve_row.addStretch()
        layout.addLayout(curve_row)

        # 5px spacing between velocity curve and sustain
        layout.addSpacing(5)

        # Sustain (label next to dropdown) - below velocity min/max
        sustain_row = QHBoxLayout()
        sustain_row.setContentsMargins(0, 0, 0, 0)
        sustain_row.setSpacing(6)

        sustain_label = QLabel(tr("QuickActuationWidget", "Sustain:"))
        sustain_label.setStyleSheet("QLabel { font-size: 14px; }")
        sustain_label.setMinimumWidth(100)
        sustain_label.setMaximumWidth(100)
        sustain_row.addWidget(sustain_label)

        self.triplesplit_sustain_combo = ArrowComboBox()
        self.triplesplit_sustain_combo.setMaximumWidth(120)
        self.triplesplit_sustain_combo.setMaximumHeight(30)
        self.triplesplit_sustain_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 14px; text-align: center; }")
        self.triplesplit_sustain_combo.setEditable(True)
        self.triplesplit_sustain_combo.lineEdit().setReadOnly(True)
        self.triplesplit_sustain_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.triplesplit_sustain_combo.addItem("Allow", 0)
        self.triplesplit_sustain_combo.addItem("Ignore", 1)
        self.triplesplit_sustain_combo.setCurrentIndex(0)
        self.triplesplit_sustain_combo.currentIndexChanged.connect(self.on_midi_settings_changed)
        sustain_row.addWidget(self.triplesplit_sustain_combo)
        sustain_row.addStretch()
        layout.addLayout(sustain_row)

        return widget
        
    def update_per_key_ui_state(self, per_key_enabled):
        """Update UI state when per-key mode changes"""
        # Show/hide sliders and message based on per-key state
        self.sliders_container.setVisible(not per_key_enabled)
        self.per_key_message.setVisible(per_key_enabled)
        # Disable save button when per-key is enabled (managed in Trigger Settings)
        self.save_btn.setEnabled(not per_key_enabled)
    
    def on_per_layer_toggled(self):
        """Handle per-layer mode toggle"""
        self.per_layer_enabled = self.per_layer_checkbox.isChecked()

        # Show/hide layer label
        self.layer_label.setVisible(self.per_layer_enabled)

        # Update save button text
        if self.per_layer_enabled:
            self.save_btn.setText(tr("QuickActuationWidget", f"Save to Layer {self.current_layer}"))
            # Load current layer's settings from memory
            self.load_layer_from_memory()
        else:
            self.save_btn.setText(tr("QuickActuationWidget", "Save to All Layers"))

        # Synchronize with Trigger Settings tab
        if self.trigger_settings_ref:
            self.trigger_settings_ref.syncing = True
            self.trigger_settings_ref.per_layer_checkbox.setChecked(self.per_layer_enabled)
            self.trigger_settings_ref.syncing = False

    def on_enable_per_key_toggled(self):
        """Handle enable per-key checkbox toggle"""
        if self.syncing:
            return

        per_key_enabled = self.enable_per_key_checkbox.isChecked()

        # Update UI state based on per-key mode
        self.update_per_key_ui_state(per_key_enabled)

        # Sync with Trigger Settings tab
        if self.trigger_settings_ref:
            self.trigger_settings_ref.syncing = True
            self.trigger_settings_ref.enable_checkbox.setChecked(per_key_enabled)
            self.trigger_settings_ref.syncing = False
            # Trigger the enable_changed handler to update trigger settings UI
            self.trigger_settings_ref.on_enable_changed(Qt.Checked if per_key_enabled else Qt.Unchecked)

        if per_key_enabled:
            # Show notification and switch to trigger settings tab
            QMessageBox.information(
                self,
                tr("QuickActuationWidget", "Per-Key Actuation Enabled"),
                tr("QuickActuationWidget", "Per-key actuation is now enabled.\nUse Trigger Settings tab to configure individual keys.")
            )
            # Emit signal to request tab switch
            self.enable_per_key_requested.emit()

    def on_simple_channel_changed(self, value):
        """Handle simple channel slider changes"""
        self.simple_channel_label.setText(str(value + 1))
        if not self.syncing:
            self.midi_settings['channel'] = value
            # Sync to advanced control if it exists
            if hasattr(self, 'midi_channel_slider'):
                self.syncing = True
                self.midi_channel_slider.setValue(value)
                self.midi_channel_label.setText(str(value + 1))
                self.syncing = False

    def on_simple_transpose_changed(self, value):
        """Handle simple transpose slider changes"""
        self.simple_transpose_label.setText(f"{'+' if value >= 0 else ''}{value}")
        if not self.syncing:
            self.midi_settings['transpose'] = value
            # Sync to advanced control if it exists
            if hasattr(self, 'midi_transpose_slider'):
                self.syncing = True
                self.midi_transpose_slider.setValue(value)
                self.midi_transpose_label.setText(f"{'+' if value >= 0 else ''}{value}")
                self.syncing = False

    def on_midi_channel_changed(self, value):
        """Handle MIDI channel slider changes"""
        self.midi_channel_label.setText(str(value + 1))
        if not self.syncing:
            self.save_midi_ui_to_memory()
            # Sync to simple control if it exists
            if hasattr(self, 'simple_channel_slider'):
                self.syncing = True
                self.simple_channel_slider.setValue(value)
                self.simple_channel_label.setText(str(value + 1))
                self.syncing = False

    def on_midi_transpose_changed(self, value):
        """Handle MIDI transpose slider changes"""
        self.midi_transpose_label.setText(f"{'+' if value >= 0 else ''}{value}")
        if not self.syncing:
            self.save_midi_ui_to_memory()
            # Sync to simple control if it exists
            if hasattr(self, 'simple_transpose_slider'):
                self.syncing = True
                self.simple_transpose_slider.setValue(value)
                self.simple_transpose_label.setText(f"{'+' if value >= 0 else ''}{value}")
                self.syncing = False

    def on_keysplit_channel_changed(self, value):
        """Handle keysplit channel slider changes"""
        self.keysplit_channel_label.setText(str(value + 1))
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_keysplit_transpose_changed(self, value):
        """Handle keysplit transpose slider changes"""
        self.keysplit_transpose_label.setText(f"{'+' if value >= 0 else ''}{value}")
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_triplesplit_channel_changed(self, value):
        """Handle triplesplit channel slider changes"""
        self.triplesplit_channel_label.setText(str(value + 1))
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_triplesplit_transpose_changed(self, value):
        """Handle triplesplit transpose slider changes"""
        self.triplesplit_transpose_label.setText(f"{'+' if value >= 0 else ''}{value}")
        if not self.syncing:
            self.save_midi_ui_to_memory()
    
    def on_slider_changed(self, key, value, label):
        """Handle slider changes"""
        if self.syncing:
            return

        if key in ['normal', 'midi']:
            label.setText(f"{value * 0.025:.2f}mm")
        elif key == 'midi_rapid_vel':
            label.setText(f"±{value}")
        else:
            label.setText(str(value))

        # Update memory
        self.save_ui_to_memory()

        # Sync to TriggerSettingsTab if reference exists
        if self.trigger_settings_ref and key in ['normal', 'midi']:
            ts = self.trigger_settings_ref
            ts.syncing = True

            if key == 'normal':
                ts.global_normal_slider.set_actuation(value)
                ts.global_normal_value_label.setText(f"Act: {value * 0.025:.2f}mm")
            elif key == 'midi':
                ts.global_midi_slider.set_actuation(value)
                ts.global_midi_value_label.setText(f"Act: {value * 0.025:.2f}mm")

            # Initialize pending_layer_data if not already
            if ts.pending_layer_data is None:
                ts.pending_layer_data = []
                for layer_data in ts.layer_data:
                    ts.pending_layer_data.append(layer_data.copy())

            # Update pending_layer_data for current layer (or all layers if not per-layer)
            if self.per_layer_enabled:
                ts.pending_layer_data[self.current_layer][key] = value
            else:
                for i in range(12):
                    ts.pending_layer_data[i][key] = value

            # Also update layer_data to keep in sync
            if self.per_layer_enabled:
                ts.layer_data[self.current_layer][key] = value
            else:
                for i in range(12):
                    ts.layer_data[i][key] = value

            # Apply actuation to matching keys (normal or MIDI)
            ts.apply_actuation_to_keys(is_midi=(key == 'midi'), value=value)

            # Mark as having unsaved changes
            ts.has_unsaved_changes = True
            ts.save_btn.setEnabled(True)

            # Update display
            ts.refresh_layer_display()
            ts.update_actuation_visualizer()

            ts.syncing = False
    
    def on_combo_changed(self):
        """Handle combo box changes"""
        if not self.syncing:
            self.save_ui_to_memory()
    
    def save_ui_to_memory(self):
        """Save current UI state to memory (for current layer if per-layer, all if master)"""
        # Velocity mode is now GLOBAL
        self.global_midi_settings['velocity_mode'] = self.velocity_combo.currentData()

        if self.per_layer_enabled:
            # Update only the basic actuation keys
            self.layer_data[self.current_layer].update({
                'normal': self.normal_slider.value(),
                'midi': self.midi_slider.value()
            })
        else:
            # Save to all layers (master mode)
            data = {
                'normal': self.normal_slider.value(),
                'midi': self.midi_slider.value()
            }
            for i in range(12):
                self.layer_data[i].update(data)
    
    def load_layer_from_memory(self):
        """Load layer settings from memory cache"""
        self.syncing = True

        data = self.layer_data[self.current_layer]

        # Set sliders and immediately update labels
        self.normal_slider.setValue(data['normal'])
        self.normal_value_label.setText(f"{data['normal'] * 0.025:.2f}mm")

        self.midi_slider.setValue(data['midi'])
        self.midi_value_label.setText(f"{data['midi'] * 0.025:.2f}mm")

        # Velocity mode is now GLOBAL (loaded from global_midi_settings)
        velocity_mode = self.global_midi_settings.get('velocity_mode', 2)
        for i in range(self.velocity_combo.count()):
            if self.velocity_combo.itemData(i) == velocity_mode:
                self.velocity_combo.setCurrentIndex(i)
                break

        self.syncing = False
    
    def on_midi_settings_changed(self):
        """Handle MIDI settings changes"""
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_velocity_preset_changed(self):
        """Handle velocity preset changes - update curve index"""
        if self.syncing:
            return

        curve_index = self.simple_velocity_preset_combo.currentData()
        # New curve system: 0-6 = factory curves, 7-16 = user curves
        if curve_index is not None:
            self.midi_settings['velocity_curve'] = curve_index
            self.midi_settings['velocity_preset'] = curve_index

            # Update advanced controls (they're synced from preset)
            self.syncing = True
            for i in range(self.midi_velocity_curve.count()):
                if self.midi_velocity_curve.itemData(i) == config['curve']:
                    self.midi_velocity_curve.setCurrentIndex(i)
                    break
            self.midi_velocity_min.setValue(config['min'])
            self.midi_velocity_min_label.setText(str(config['min']))
            self.midi_velocity_max.setValue(config['max'])
            self.midi_velocity_max_label.setText(str(config['max']))
            self.syncing = False

    def on_midi_advanced_toggled(self):
        """Toggle advanced MIDI options visibility"""
        show_advanced = self.midi_advanced_checkbox.isChecked()

        # Show/hide keysplit/triplesplit enable widgets
        self.keysplit_enable_widget.setVisible(show_advanced)
        self.triplesplit_enable_widget.setVisible(show_advanced)

        # Toggle between simple controls and tabs
        if show_advanced:
            # Hide simple widget, show tabs
            self.simple_midi_widget.setVisible(False)
            self.midi_tabs.setVisible(True)
            # Sync values from simple to advanced controls
            self.sync_simple_to_advanced()
            # Update tab view based on split settings
            self.update_midi_container_view()
        else:
            # Show simple widget, hide tabs
            self.simple_midi_widget.setVisible(True)
            self.midi_tabs.setVisible(False)
            # Sync values from advanced to simple controls
            self.sync_advanced_to_simple()
            # Uncheck keysplit/triplesplit when leaving advanced mode
            self.keysplit_enabled_checkbox.setChecked(False)
            self.triplesplit_enabled_checkbox.setChecked(False)

    def sync_simple_to_advanced(self):
        """Sync values from simple controls to advanced tab controls"""
        # Sync channel
        channel_val = self.simple_channel_slider.value()
        self.midi_channel_slider.setValue(channel_val)
        self.midi_channel_label.setText(str(channel_val + 1))

        # Sync transpose
        transpose_val = self.simple_transpose_slider.value()
        self.midi_transpose_slider.setValue(transpose_val)
        self.midi_transpose_label.setText(f"{'+' if transpose_val >= 0 else ''}{transpose_val}")

    def sync_advanced_to_simple(self):
        """Sync values from advanced tab controls to simple controls"""
        # Sync channel
        channel_val = self.midi_channel_slider.value()
        self.simple_channel_slider.setValue(channel_val)
        self.simple_channel_label.setText(str(channel_val + 1))

        # Sync transpose
        transpose_val = self.midi_transpose_slider.value()
        self.simple_transpose_slider.setValue(transpose_val)
        self.simple_transpose_label.setText(f"{'+' if transpose_val >= 0 else ''}{transpose_val}")

    def on_midi_velocity_slider_changed(self, slider_type, value):
        """Handle velocity slider changes"""
        if slider_type == 'min':
            self.midi_velocity_min_label.setText(str(value))
        elif slider_type == 'max':
            self.midi_velocity_max_label.setText(str(value))

        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_keysplit_velocity_slider_changed(self, slider_type, value):
        """Handle keysplit velocity slider changes"""
        if slider_type == 'min':
            self.keysplit_velocity_min_label.setText(str(value))
        elif slider_type == 'max':
            self.keysplit_velocity_max_label.setText(str(value))

        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_triplesplit_velocity_slider_changed(self, slider_type, value):
        """Handle triplesplit velocity slider changes"""
        if slider_type == 'min':
            self.triplesplit_velocity_min_label.setText(str(value))
        elif slider_type == 'max':
            self.triplesplit_velocity_max_label.setText(str(value))

        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_keysplit_enabled_toggled(self):
        """Toggle KeySplit settings - switch to tabbed view when enabled"""
        # Adjust status values when disabling keysplit
        if not self.keysplit_enabled_checkbox.isChecked():
            self._adjust_status_values_on_keysplit_close()

        self.update_midi_container_view()
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_triplesplit_enabled_toggled(self):
        """Toggle TripleSplit settings - auto-enable keysplit and switch to tabbed view"""
        if self.triplesplit_enabled_checkbox.isChecked():
            # Auto-tick keysplit when triplesplit is enabled
            if not self.keysplit_enabled_checkbox.isChecked():
                self.keysplit_enabled_checkbox.setChecked(True)
        else:
            # Adjust status values when disabling triplesplit
            self._adjust_status_values_on_triplesplit_close()

        self.update_midi_container_view()
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def set_matrix_test_reference(self, matrix_test):
        """Set reference to MatrixTest widget for status value adjustments"""
        self.matrix_test = matrix_test

    def _adjust_status_values_on_keysplit_close(self):
        """Adjust status values when keysplit window is closed
        - Status 3 (Both Splits On) -> 2 (TripleSplit On)
        - Status 1 (KeySplit On) -> 0 (Disable Keysplit)
        """
        if not self.matrix_test:
            return

        try:
            # Adjust channel split status
            current_value = self.matrix_test.key_split_status.currentData()
            if current_value == 3:  # Both Splits On -> TripleSplit On
                self.matrix_test.key_split_status.setCurrentIndex(2)
            elif current_value == 1:  # KeySplit On -> Disable Keysplit
                self.matrix_test.key_split_status.setCurrentIndex(0)

            # Adjust transpose split status
            current_value = self.matrix_test.key_split_transpose_status.currentData()
            if current_value == 3:  # Both Splits On -> TripleSplit On
                self.matrix_test.key_split_transpose_status.setCurrentIndex(2)
            elif current_value == 1:  # KeySplit On -> Disable Keysplit
                self.matrix_test.key_split_transpose_status.setCurrentIndex(0)

            # Adjust velocity split status
            current_value = self.matrix_test.key_split_velocity_status.currentData()
            if current_value == 3:  # Both Splits On -> TripleSplit On
                self.matrix_test.key_split_velocity_status.setCurrentIndex(2)
            elif current_value == 1:  # KeySplit On -> Disable Keysplit
                self.matrix_test.key_split_velocity_status.setCurrentIndex(0)
        except Exception as e:
            pass

    def _adjust_status_values_on_triplesplit_close(self):
        """Adjust status values when triplesplit window is closed
        - Status 3 (Both Splits On) -> 1 (KeySplit On)
        - Status 2 (TripleSplit On) -> 0 (Disable Keysplit)
        """
        if not self.matrix_test:
            return

        try:
            # Adjust channel split status
            current_value = self.matrix_test.key_split_status.currentData()
            if current_value == 3:  # Both Splits On -> KeySplit On
                self.matrix_test.key_split_status.setCurrentIndex(1)
            elif current_value == 2:  # TripleSplit On -> Disable Keysplit
                self.matrix_test.key_split_status.setCurrentIndex(0)

            # Adjust transpose split status
            current_value = self.matrix_test.key_split_transpose_status.currentData()
            if current_value == 3:  # Both Splits On -> KeySplit On
                self.matrix_test.key_split_transpose_status.setCurrentIndex(1)
            elif current_value == 2:  # TripleSplit On -> Disable Keysplit
                self.matrix_test.key_split_transpose_status.setCurrentIndex(0)

            # Adjust velocity split status
            current_value = self.matrix_test.key_split_velocity_status.currentData()
            if current_value == 3:  # Both Splits On -> KeySplit On
                self.matrix_test.key_split_velocity_status.setCurrentIndex(1)
            elif current_value == 2:  # TripleSplit On -> Disable Keysplit
                self.matrix_test.key_split_velocity_status.setCurrentIndex(0)
        except Exception as e:
            pass

    def update_midi_container_view(self):
        """Update tabs based on split settings - always show tabs"""
        keysplit_enabled = self.keysplit_enabled_checkbox.isChecked()
        triplesplit_enabled = self.triplesplit_enabled_checkbox.isChecked()

        # Show/hide sustain widget in Basic tab based on split settings
        if hasattr(self, 'midi_sustain_widget'):
            self.midi_sustain_widget.setVisible(keysplit_enabled or triplesplit_enabled)

        # Tabs are always shown, just rebuild which tabs are visible
        self.midi_tabs.clear()
        self.midi_tabs.addTab(self.basic_tab_widget, "Basic")
        if keysplit_enabled:
            self.midi_tabs.addTab(self.keysplit_tab_widget, "KeySplit")
        if triplesplit_enabled:
            self.midi_tabs.addTab(self.triplesplit_tab_widget, "TripleSplit")

    def on_keysplit_tab_checkbox_changed(self):
        """Handle keysplit checkbox changes from tab widgets"""
        if self.syncing:
            return
        # Get the state from whichever checkbox was changed
        checked = False
        if hasattr(self, 'keysplit_enabled_checkbox_tab') and self.sender() == self.keysplit_enabled_checkbox_tab:
            checked = self.keysplit_enabled_checkbox_tab.isChecked()
        elif hasattr(self, 'keysplit_enabled_checkbox_tab_ts') and self.sender() == self.keysplit_enabled_checkbox_tab_ts:
            checked = self.keysplit_enabled_checkbox_tab_ts.isChecked()

        # Update main checkbox
        self.syncing = True
        self.keysplit_enabled_checkbox.setChecked(checked)
        self.syncing = False

        # Update view and save
        self.update_midi_container_view()
        self.save_midi_ui_to_memory()

    def on_triplesplit_tab_checkbox_changed(self):
        """Handle triplesplit checkbox changes from tab widgets"""
        if self.syncing:
            return
        # Get the state from whichever checkbox was changed
        checked = False
        if hasattr(self, 'triplesplit_enabled_checkbox_tab') and self.sender() == self.triplesplit_enabled_checkbox_tab:
            checked = self.triplesplit_enabled_checkbox_tab.isChecked()
        elif hasattr(self, 'triplesplit_enabled_checkbox_tab_ks') and self.sender() == self.triplesplit_enabled_checkbox_tab_ks:
            checked = self.triplesplit_enabled_checkbox_tab_ks.isChecked()

        # Update main checkbox (this will trigger auto-tick of keysplit if needed)
        self.syncing = True
        self.triplesplit_enabled_checkbox.setChecked(checked)
        self.syncing = False

        # If enabling triplesplit, also enable keysplit
        if checked and not self.keysplit_enabled_checkbox.isChecked():
            self.keysplit_enabled_checkbox.setChecked(True)

        # Update view and save
        self.update_midi_container_view()
        self.save_midi_ui_to_memory()

    def save_midi_ui_to_memory(self):
        """Save MIDI settings from UI to memory"""
        self.midi_settings['channel'] = self.midi_channel_slider.value()
        self.midi_settings['transpose'] = self.midi_transpose_slider.value()
        self.midi_settings['sustain'] = self.midi_sustain_combo.currentData()
        self.midi_settings['velocity_curve'] = self.midi_velocity_curve.currentData()
        self.midi_settings['velocity_min'] = self.midi_velocity_min.value()
        self.midi_settings['velocity_max'] = self.midi_velocity_max.value()

        self.midi_settings['keysplit_enabled'] = self.keysplit_enabled_checkbox.isChecked()
        self.midi_settings['keysplit_channel'] = self.keysplit_channel_slider.value()
        self.midi_settings['keysplit_transpose'] = self.keysplit_transpose_slider.value()
        self.midi_settings['keysplit_sustain'] = self.keysplit_sustain_combo.currentData()
        self.midi_settings['keysplit_velocity_curve'] = self.keysplit_velocity_curve.currentData()
        self.midi_settings['keysplit_velocity_min'] = self.keysplit_velocity_min.value()
        self.midi_settings['keysplit_velocity_max'] = self.keysplit_velocity_max.value()

        self.midi_settings['triplesplit_enabled'] = self.triplesplit_enabled_checkbox.isChecked()
        self.midi_settings['triplesplit_channel'] = self.triplesplit_channel_slider.value()
        self.midi_settings['triplesplit_transpose'] = self.triplesplit_transpose_slider.value()
        self.midi_settings['triplesplit_sustain'] = self.triplesplit_sustain_combo.currentData()
        self.midi_settings['triplesplit_velocity_curve'] = self.triplesplit_velocity_curve.currentData()
        self.midi_settings['triplesplit_velocity_min'] = self.triplesplit_velocity_min.value()
        self.midi_settings['triplesplit_velocity_max'] = self.triplesplit_velocity_max.value()

    def on_save_actuation(self):
        """Save actuation settings - to all layers or current layer depending on mode
        NOTE: velocity_mode, aftertouch settings are now GLOBAL and saved via Advanced tab.
        This function only saves actuation points (normal, midi) per-layer.
        """
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")

            # Get global settings for backward compatibility with firmware protocol
            global_settings = self.global_midi_settings

            if self.per_layer_enabled:
                # Save to current layer only
                data = self.layer_data[self.current_layer]
                flags = 0
                if data.get('rapidfire_enabled', False):
                    flags |= 0x01
                if data.get('midi_rapidfire_enabled', False):
                    flags |= 0x02

                vibrato_decay = global_settings.get('vibrato_decay_time', 200)
                # Protocol: 11 bytes (layer + 10 data bytes)
                # velocity/aftertouch fields use GLOBAL settings
                payload = bytearray([
                    self.current_layer,
                    data['normal'],
                    data['midi'],
                    global_settings.get('velocity_mode', 2),   # GLOBAL
                    10,  # vel_speed deprecated, use default
                    flags,
                    global_settings.get('aftertouch_mode', 0),      # GLOBAL
                    global_settings.get('aftertouch_cc', 255),      # GLOBAL
                    global_settings.get('vibrato_sensitivity', 100), # GLOBAL
                    vibrato_decay & 0xFF,
                    (vibrato_decay >> 8) & 0xFF
                ])

                if not self.device.keyboard.set_layer_actuation(payload):
                    raise RuntimeError(f"Failed to set actuation for layer {self.current_layer}")

                QMessageBox.information(None, "Success",
                    f"Layer {self.current_layer} actuation saved successfully!")
            else:
                # Save to all 12 layers
                vibrato_decay = global_settings.get('vibrato_decay_time', 200)
                for layer in range(12):
                    data = self.layer_data[layer]
                    flags = 0
                    if data.get('rapidfire_enabled', False):
                        flags |= 0x01
                    if data.get('midi_rapidfire_enabled', False):
                        flags |= 0x02

                    # Protocol: 11 bytes (layer + 10 data bytes)
                    # velocity/aftertouch fields use GLOBAL settings
                    payload = bytearray([
                        layer,
                        data['normal'],
                        data['midi'],
                        global_settings.get('velocity_mode', 2),   # GLOBAL
                        10,  # vel_speed deprecated, use default
                        flags,
                        global_settings.get('aftertouch_mode', 0),      # GLOBAL
                        global_settings.get('aftertouch_cc', 255),      # GLOBAL
                        global_settings.get('vibrato_sensitivity', 100), # GLOBAL
                        vibrato_decay & 0xFF,
                        (vibrato_decay >> 8) & 0xFF
                    ])

                    if not self.device.keyboard.set_layer_actuation(payload):
                        raise RuntimeError(f"Failed to set actuation for layer {layer}")

                QMessageBox.information(None, "Success",
                    "Actuation saved to all layers successfully!")

        except Exception as e:
            QMessageBox.critical(None, "Error",
                f"Failed to save actuation settings: {str(e)}")

    def on_save_midi(self):
        """Save MIDI settings to keyboard"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")

            # This is a simplified save for per-layer MIDI tab
            # The full global MIDI config is in the MIDI Settings tab (matrix_test.py)
            # Here we only save what's visible based on advanced mode state

            show_advanced = self.midi_advanced_checkbox.isChecked()
            keysplit_enabled = self.keysplit_enabled_checkbox.isChecked()
            triplesplit_enabled = self.triplesplit_enabled_checkbox.isChecked()

            # Pack the visible settings only
            # Note: This is a placeholder - actual implementation would need to integrate
            # with the global keyboard MIDI config system from matrix_test.py

            QMessageBox.information(None, "Info",
                "MIDI settings are saved globally in the 'MIDI Settings' tab. "
                "Use that tab for comprehensive MIDI configuration.")

        except Exception as e:
            QMessageBox.critical(None, "Error",
                f"Failed to save MIDI settings: {str(e)}")

    def set_device(self, device):
        """Set the device and load initial settings from device"""
        self.device = device
        is_vial = isinstance(device, VialKeyboard)
        self.setEnabled(is_vial)

        # Ensure checkboxes always stay enabled when widget is enabled
        if is_vial:
            self.per_layer_checkbox.setEnabled(True)
            self.enable_per_key_checkbox.setEnabled(True)

        if self.device and isinstance(self.device, VialKeyboard):
            # Load all layers from device into memory cache
            self.load_all_layers_from_device()
            # Load current layer to UI
            self.load_layer_from_memory()
    
    def load_all_layers_from_device(self):
        """Load all 12 layers from device into memory cache (only called once on connect)"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                return

            actuations = self.device.keyboard.get_all_layer_actuations()

            if not actuations or len(actuations) < 120:  # 12 layers * 10 bytes
                return

            # Load all layers into memory
            # New format: [normal, midi, velocity_mode, vel_speed, flags,
            #              aftertouch_mode, aftertouch_cc, vibrato_sensitivity,
            #              vibrato_decay_time_low, vibrato_decay_time_high]
            for layer in range(12):
                offset = layer * 10
                flags = actuations[offset + 4]
                vibrato_decay = actuations[offset + 8] | (actuations[offset + 9] << 8)

                self.layer_data[layer] = {
                    'normal': actuations[offset + 0],
                    'midi': actuations[offset + 1],
                    'velocity': actuations[offset + 2],  # Velocity mode
                    'vel_speed': actuations[offset + 3],
                    'rapidfire_enabled': (flags & 0x01) != 0,
                    'midi_rapidfire_enabled': (flags & 0x02) != 0,
                    'aftertouch_mode': actuations[offset + 5],
                    'aftertouch_cc': actuations[offset + 6],
                    'vibrato_sensitivity': actuations[offset + 7],
                    'vibrato_decay_time': vibrato_decay
                }

            # Load advanced settings UI from layer 0 (or current layer)
            if hasattr(self, 'aftertouch_mode_combo'):
                self.load_advanced_from_memory()

        except Exception:
            pass
    
    def set_layer(self, layer):
        """Set current layer and load its settings if in per-layer mode"""
        self.current_layer = layer
        self.layer_label.setText(tr("QuickActuationWidget", f"Layer {layer}"))

        # Update save button text if in per-layer mode
        if self.per_layer_enabled:
            self.save_btn.setText(tr("QuickActuationWidget", f"Save to Layer {layer}"))
            # Load from memory (fast, no device I/O)
            self.load_layer_from_memory()

        # Advanced tab settings are GLOBAL now, no layer-specific loading needed

    def load_advanced_from_memory(self):
        """Load advanced settings (velocity, aftertouch) from GLOBAL settings"""
        settings = self.global_midi_settings

        # Update UI without triggering callbacks
        self.velocity_combo.blockSignals(True)
        self.aftertouch_mode_combo.blockSignals(True)
        self.aftertouch_cc_combo.blockSignals(True)
        self.vibrato_sens_slider.blockSignals(True)
        self.vibrato_decay_slider.blockSignals(True)
        self.min_press_slider.blockSignals(True)
        self.max_press_slider.blockSignals(True)

        # Set velocity mode (GLOBAL)
        velocity = settings.get('velocity_mode', 2)
        for i in range(self.velocity_combo.count()):
            if self.velocity_combo.itemData(i) == velocity:
                self.velocity_combo.setCurrentIndex(i)
                break

        # Set min/max press time (GLOBAL)
        min_press = settings.get('min_press_time', 200)
        self.min_press_slider.setValue(min_press)
        self.min_press_value.setText(f"{min_press}ms")

        max_press = settings.get('max_press_time', 20)
        self.max_press_slider.setValue(max_press)
        self.max_press_value.setText(f"{max_press}ms")

        # Set aftertouch mode (GLOBAL)
        mode = settings.get('aftertouch_mode', 0)
        for i in range(self.aftertouch_mode_combo.count()):
            if self.aftertouch_mode_combo.itemData(i) == mode:
                self.aftertouch_mode_combo.setCurrentIndex(i)
                break

        # Show/hide vibrato controls
        is_vibrato = (mode == 4)
        self.vibrato_sens_widget.setVisible(is_vibrato)
        self.vibrato_decay_widget.setVisible(is_vibrato)

        # Set aftertouch CC (GLOBAL)
        cc = settings.get('aftertouch_cc', 255)
        for i in range(self.aftertouch_cc_combo.count()):
            if self.aftertouch_cc_combo.itemData(i) == cc:
                self.aftertouch_cc_combo.setCurrentIndex(i)
                break

        # Set vibrato settings (GLOBAL)
        sens = settings.get('vibrato_sensitivity', 100)
        self.vibrato_sens_slider.setValue(sens)
        self.vibrato_sens_value.setText(f"{sens}%")

        decay = settings.get('vibrato_decay_time', 200)
        self.vibrato_decay_slider.setValue(decay)
        self.vibrato_decay_value.setText(f"{decay}ms")

        self.velocity_combo.blockSignals(False)
        self.aftertouch_mode_combo.blockSignals(False)
        self.aftertouch_cc_combo.blockSignals(False)
        self.vibrato_sens_slider.blockSignals(False)
        self.vibrato_decay_slider.blockSignals(False)
        self.min_press_slider.blockSignals(False)
        self.max_press_slider.blockSignals(False)


class EncoderButton(QWidget):
    """Circular encoder button widget with arrow indicator"""

    clicked = pyqtSignal()

    def __init__(self, is_up=True):
        super().__init__()
        self.is_up = is_up
        self.is_selected = False
        self.text = "KC_NO"
        self.setFixedSize(55, 55)
        self.setMouseTracking(True)

    def setChecked(self, checked):
        self.is_selected = checked
        self.update()

    def setText(self, text):
        self.text = text
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPainterPath, QPen, QBrush, QFont
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPalette
        from PyQt5.QtCore import Qt

        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Draw circular background with 50% opacity fill
        if self.is_selected:
            pen = QPen(QApplication.palette().color(QPalette.Highlight))
            pen.setWidth(2)
            qp.setPen(pen)
        else:
            pen = QPen(QApplication.palette().color(QPalette.Window))
            pen.setWidth(2)
            qp.setPen(pen)

        # Create brush with 50% opacity
        button_color = QApplication.palette().color(QPalette.Button)
        button_color.setAlpha(128)  # 50% opacity
        brush = QBrush(button_color)
        qp.setBrush(brush)
        qp.drawEllipse(3, 3, 49, 49)

        # Draw keycode text (label is now outside button)
        qp.setPen(QApplication.palette().color(QPalette.ButtonText))
        font = QFont()
        font.setPointSize(8)  # Match keyboard widget font size
        qp.setFont(font)
        text_rect = self.rect().adjusted(3, 3, -3, -3)
        qp.drawText(text_rect, Qt.AlignCenter, self.text)

        qp.end()


class PushButton(QWidget):
    """Square push button widget"""

    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_selected = False
        self.text = "KC_NO"
        self.setFixedSize(55, 55)
        self.setMouseTracking(True)

    def setChecked(self, checked):
        self.is_selected = checked
        self.update()

    def setText(self, text):
        self.text = text
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QBrush, QFont
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPalette
        from PyQt5.QtCore import Qt

        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Draw square background with 50% opacity fill
        if self.is_selected:
            pen = QPen(QApplication.palette().color(QPalette.Highlight))
            pen.setWidth(2)
            qp.setPen(pen)
        else:
            pen = QPen(QApplication.palette().color(QPalette.Window))
            pen.setWidth(2)
            qp.setPen(pen)

        # Create brush with 50% opacity
        button_color = QApplication.palette().color(QPalette.Button)
        button_color.setAlpha(128)  # 50% opacity
        brush = QBrush(button_color)
        qp.setBrush(brush)
        qp.drawRoundedRect(3, 3, 49, 49, 4, 4)

        # Draw keycode text (label is now outside button)
        qp.setPen(QApplication.palette().color(QPalette.ButtonText))
        font = QFont()
        font.setPointSize(8)  # Match keyboard widget font size
        qp.setFont(font)
        text_rect = self.rect().adjusted(3, 3, -3, -3)
        qp.drawText(text_rect, Qt.AlignCenter, self.text)

        qp.end()


class SustainButton(QWidget):
    """Sustain pedal button widget"""

    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_selected = False
        self.text = "KC_NO"
        self.setFixedSize(50, 50)
        self.setMouseTracking(True)

    def setChecked(self, checked):
        self.is_selected = checked
        self.update()

    def setText(self, text):
        self.text = text
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QBrush, QFont
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPalette
        from PyQt5.QtCore import Qt

        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rectangle background with 50% opacity
        if self.is_selected:
            pen = QPen(QApplication.palette().color(QPalette.Highlight))
            pen.setWidth(2)
            qp.setPen(pen)
        else:
            pen = QPen(QApplication.palette().color(QPalette.Window))
            pen.setWidth(2)
            qp.setPen(pen)

        # Create brush with 50% opacity
        button_color = QApplication.palette().color(QPalette.Button)
        button_color.setAlpha(128)  # 50% opacity
        brush = QBrush(button_color)
        qp.setBrush(brush)
        qp.drawRoundedRect(3, 3, 44, 44, 4, 4)

        # Draw keycode text
        qp.setPen(QApplication.palette().color(QPalette.ButtonText))
        font = QFont()
        font.setPointSize(8)  # Match keyboard widget font size
        qp.setFont(font)
        text_rect = self.rect().adjusted(3, 3, -3, -3)
        qp.drawText(text_rect, Qt.AlignCenter, self.text)

        qp.end()


class EncoderAssignWidget(QWidget):
    """Widget for assigning keycodes to encoders and sustain pedal per layer"""

    clicked = pyqtSignal()  # Emitted when a button is clicked (for tabbed_keycodes integration)

    def __init__(self):
        super().__init__()

        self.current_layer = 0
        self.selected_button = None
        self.buttons = []
        self.labels = [
            "Encoder 1 Up",
            "Encoder 1 Down",
            "Encoder 1 Press",
            "Encoder 2 Up",
            "Encoder 2 Down",
            "Encoder 2 Press",
            "Sustain Pedal"
        ]

        self.setMinimumWidth(185)
        self.setMaximumWidth(185)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # Make background transparent so keyboard background shows through
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(5, 45, 5, 10)  # 45px top margin
        self.setLayout(layout)

        # Create buttons in logical order (indices 0-6) before adding to UI
        # Index 0: Encoder 1 Up
        enc1_up_btn = EncoderButton(is_up=True)
        enc1_up_btn.clicked.connect(lambda: self.on_button_clicked(0))
        self.buttons.append(enc1_up_btn)

        # Index 1: Encoder 1 Down
        enc1_down_btn = EncoderButton(is_up=False)
        enc1_down_btn.clicked.connect(lambda: self.on_button_clicked(1))
        self.buttons.append(enc1_down_btn)

        # Index 2: Encoder 1 Press
        enc1_push_btn = PushButton()
        enc1_push_btn.clicked.connect(lambda: self.on_button_clicked(2))
        self.buttons.append(enc1_push_btn)

        # Index 3: Encoder 2 Up
        enc2_up_btn = EncoderButton(is_up=True)
        enc2_up_btn.clicked.connect(lambda: self.on_button_clicked(3))
        self.buttons.append(enc2_up_btn)

        # Index 4: Encoder 2 Down
        enc2_down_btn = EncoderButton(is_up=False)
        enc2_down_btn.clicked.connect(lambda: self.on_button_clicked(4))
        self.buttons.append(enc2_down_btn)

        # Index 5: Encoder 2 Press
        enc2_push_btn = PushButton()
        enc2_push_btn.clicked.connect(lambda: self.on_button_clicked(5))
        self.buttons.append(enc2_push_btn)

        # Index 6: Sustain Pedal
        sustain_btn = SustainButton()
        sustain_btn.clicked.connect(lambda: self.on_button_clicked(6))
        self.buttons.append(sustain_btn)

        # Now add to UI layout in display order (sustain at top, then encoders)
        # Sustain pedal group - at top, center aligned with 20px left shift
        sustain_label = QLabel("Sustain Pedal")
        sustain_label.setStyleSheet("QLabel { font-size: 11px; font-weight: bold; background: transparent; }")
        sustain_label.setAlignment(Qt.AlignCenter)
        sustain_label_container = QHBoxLayout()
        sustain_label_container.addWidget(sustain_label)
        layout.addLayout(sustain_label_container)

        sustain_layout = QHBoxLayout()
        sustain_layout.setSpacing(5)
        sustain_layout.addSpacing(63)  # 20px left shift
        sustain_layout.addWidget(sustain_btn)
        sustain_layout.addStretch()
        layout.addLayout(sustain_layout)

        # Add 10px spacer below sustain button
        layout.addSpacing(23)

        # Encoder 1 group
        encoder1_label = QLabel("Encoder 1")
        encoder1_label.setStyleSheet("QLabel { font-size: 11px; font-weight: bold; background: transparent; }")
        encoder1_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(encoder1_label)

        # 7px spacing between Encoder 1 title and button labels
        layout.setSpacing(7)

        # Encoder 1 button labels (above buttons)
        encoder1_labels_layout = QHBoxLayout()
        encoder1_labels_layout.setSpacing(5)
        enc1_up_label = QLabel("UP")
        enc1_up_label.setStyleSheet("QLabel { font-size: 9px; background: transparent; }")
        enc1_up_label.setAlignment(Qt.AlignCenter)
        enc1_up_label.setFixedWidth(55)
        enc1_down_label = QLabel("DOWN")
        enc1_down_label.setStyleSheet("QLabel { font-size: 9px; background: transparent; }")
        enc1_down_label.setAlignment(Qt.AlignCenter)
        enc1_down_label.setFixedWidth(55)
        enc1_push_label = QLabel("PUSH")
        enc1_push_label.setStyleSheet("QLabel { font-size: 9px; background: transparent; }")
        enc1_push_label.setAlignment(Qt.AlignCenter)
        enc1_push_label.setFixedWidth(55)
        encoder1_labels_layout.addWidget(enc1_up_label)
        encoder1_labels_layout.addWidget(enc1_down_label)
        encoder1_labels_layout.addWidget(enc1_push_label)
        encoder1_labels_layout.addStretch()
        layout.addLayout(encoder1_labels_layout)

        # 3px spacing between labels and buttons
        layout.setSpacing(3)

        # Encoder 1 buttons (Up/Down circular, Press square)
        encoder1_layout = QHBoxLayout()
        encoder1_layout.setSpacing(5)
        encoder1_layout.addWidget(enc1_up_btn)
        encoder1_layout.addWidget(enc1_down_btn)
        encoder1_layout.addWidget(enc1_push_btn)
        encoder1_layout.addStretch()
        layout.addLayout(encoder1_layout)

        # 7px spacing between Encoder 1 buttons and Encoder 2 title
        layout.setSpacing(7)

        # Encoder 2 group
        encoder2_label = QLabel("Encoder 2")
        encoder2_label.setStyleSheet("QLabel { font-size: 11px; font-weight: bold; background: transparent; }")
        encoder2_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(encoder2_label)

        # 7px spacing between Encoder 2 title and button labels
        layout.setSpacing(7)

        # Encoder 2 button labels (above buttons)
        encoder2_labels_layout = QHBoxLayout()
        encoder2_labels_layout.setSpacing(5)
        enc2_up_label = QLabel("UP")
        enc2_up_label.setStyleSheet("QLabel { font-size: 9px; background: transparent; }")
        enc2_up_label.setAlignment(Qt.AlignCenter)
        enc2_up_label.setFixedWidth(55)
        enc2_down_label = QLabel("DOWN")
        enc2_down_label.setStyleSheet("QLabel { font-size: 9px; background: transparent; }")
        enc2_down_label.setAlignment(Qt.AlignCenter)
        enc2_down_label.setFixedWidth(55)
        enc2_push_label = QLabel("PUSH")
        enc2_push_label.setStyleSheet("QLabel { font-size: 9px; background: transparent; }")
        enc2_push_label.setAlignment(Qt.AlignCenter)
        enc2_push_label.setFixedWidth(55)
        encoder2_labels_layout.addWidget(enc2_up_label)
        encoder2_labels_layout.addWidget(enc2_down_label)
        encoder2_labels_layout.addWidget(enc2_push_label)
        encoder2_labels_layout.addStretch()
        layout.addLayout(encoder2_labels_layout)

        # 3px spacing between labels and buttons
        layout.setSpacing(3)

        # Encoder 2 buttons (Up/Down circular, Press square)
        encoder2_layout = QHBoxLayout()
        encoder2_layout.setSpacing(5)
        encoder2_layout.addWidget(enc2_up_btn)
        encoder2_layout.addWidget(enc2_down_btn)
        encoder2_layout.addWidget(enc2_push_btn)
        encoder2_layout.addStretch()
        layout.addLayout(encoder2_layout)

        layout.addStretch()

    def on_button_clicked(self, index):
        """Handle button click - mark as selected and notify parent"""
        # Deselect all other buttons
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)

        self.selected_button = index
        self.clicked.emit()

    def deselect(self):
        """Deselect all buttons"""
        for btn in self.buttons:
            btn.setChecked(False)
        self.selected_button = None

    def set_keycode(self, index, keycode):
        """Update button display with keycode"""
        if 0 <= index < len(self.buttons):
            self.buttons[index].setText(Keycode.label(keycode))

    def set_layer(self, layer, keyboard=None):
        """Update current layer and refresh button displays from keyboard"""
        self.current_layer = layer

        # Load keycodes from keyboard if provided
        if keyboard is not None:
            # Encoder rotation mapping (only CW and CCW, not press)
            encoder_mapping = {
                0: (0, 1),  # Encoder 1 Up (enc_idx=0, dir=1 CW)
                1: (0, 0),  # Encoder 1 Down (enc_idx=0, dir=0 CCW)
                3: (1, 1),  # Encoder 2 Up (enc_idx=1, dir=1 CW)
                4: (1, 0),  # Encoder 2 Down (enc_idx=1, dir=0 CCW)
            }

            # Matrix key mapping for encoder press and sustain pedal
            matrix_key_mapping = {
                2: (5, 1),  # Encoder 1 Press -> row 5, col 1
                5: (5, 0),  # Encoder 2 Press -> row 5, col 0
                6: (5, 2),  # Sustain Pedal -> row 5, col 2
            }

            # Update encoder rotation buttons (from encoder_layout)
            for idx in encoder_mapping:
                enc_idx, direction = encoder_mapping[idx]
                keycode = keyboard.encoder_layout.get((layer, enc_idx, direction), "KC_NO")
                self.buttons[idx].setText(Keycode.label(keycode))

            # Update encoder press and sustain pedal buttons (from regular matrix layout)
            for idx in matrix_key_mapping:
                row, col = matrix_key_mapping[idx]
                keycode = keyboard.layout.get((layer, row, col), "KC_NO")
                self.buttons[idx].setText(Keycode.label(keycode))

        # Deselect when changing layers
        self.deselect()


class ClickableWidget(QWidget):

    clicked = pyqtSignal()

    def mousePressEvent(self, evt):
        super().mousePressEvent(evt)
        self.clicked.emit()


class OverlayContainer(QWidget):
    """Container that overlays encoder widget on top of keyboard widget"""

    def __init__(self, keyboard_widget, encoder_widget):
        super().__init__()
        self.keyboard_widget = keyboard_widget
        self.encoder_widget = encoder_widget

        # Set up layout with no spacing
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(keyboard_widget)
        self.setLayout(layout)

        # Make encoder widget a child of this container for overlay
        encoder_widget.setParent(self)
        encoder_widget.raise_()  # Bring to front

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position encoder widget to overlay the left side of keyboard widget
        # Position it at the left edge of the keyboard widget, offset down by 30 pixels
        keyboard_pos = self.keyboard_widget.pos()
        self.encoder_widget.move(keyboard_pos.x(), keyboard_pos.y() + 30)


class KeymapEditor(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor
        self.matrix_test = None  # Reference to MatrixTest widget for status adjustments

        self.layout_layers = QHBoxLayout()
        self.layout_size = QVBoxLayout()
        layer_label = QLabel(tr("KeymapEditor", "Layer"))

        layout_labels_container = QHBoxLayout()
        layout_labels_container.addWidget(layer_label)
        layout_labels_container.addLayout(self.layout_layers)
        layout_labels_container.addStretch()
        layout_labels_container.addLayout(self.layout_size)

        # Create quick actuation widget
        self.quick_actuation = QuickActuationWidget()

        # Create encoder assignment widget
        self.encoder_assign = EncoderAssignWidget()

        # contains the actual keyboard
        self.container = KeyboardWidgetSimple(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)

        # Connect encoder widget signals
        self.encoder_assign.clicked.connect(self.on_encoder_clicked)

        # Create overlay container with encoder widget overlaying keyboard
        self.keyboard_overlay = OverlayContainer(self.container, self.encoder_assign)

        # Layout with actuation on left, then keyboard with encoder overlay
        keyboard_layout = QHBoxLayout()
        keyboard_layout.setSpacing(0)  # No spacing between widgets
        keyboard_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        keyboard_layout.addStretch(1)  # Add stretch before
        keyboard_layout.addWidget(self.quick_actuation, 0, Qt.AlignTop)
        keyboard_layout.addWidget(self.keyboard_overlay, 0, Qt.AlignTop)
        keyboard_layout.addStretch(1)  # Add stretch after

        layout = QVBoxLayout()
        layout.addLayout(layout_labels_container)
        layout.addLayout(keyboard_layout)

        w = ClickableWidget()
        w.setLayout(layout)
        w.clicked.connect(self.on_empty_space_clicked)

        # Wrap in scroll area for better resizing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidget(w)

        self.layer_buttons = []
        self.keyboard = None
        self.current_layer = 0

        layout_editor.changed.connect(self.on_layout_changed)

        self.container.anykey.connect(self.on_any_keycode)

        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_changed)
        self.tabbed_keycodes.anykey.connect(self.on_any_keycode)

        self.addWidget(scroll_area)
        self.addWidget(self.tabbed_keycodes)

        self.device = None
        KeycodeDisplay.notify_keymap_override(self)

    def set_matrix_test_reference(self, matrix_test):
        """Set reference to MatrixTest widget for status value adjustments"""
        self.matrix_test = matrix_test
        # Also set the reference in the quick_actuation widget
        self.quick_actuation.set_matrix_test_reference(matrix_test)

    def on_empty_space_clicked(self):
        self.container.deselect()
        self.encoder_assign.deselect()
        self.container.update()

    def on_keycode_changed(self, code):
        # Check if encoder button is selected
        if self.encoder_assign.selected_button is not None:
            self.set_encoder_keycode(self.encoder_assign.selected_button, code)
        else:
            # Otherwise, set keyboard key
            self.set_key(code)

    def rebuild_layers(self):
        # delete old layer labels
        for label in self.layer_buttons:
            label.hide()
            label.deleteLater()
        self.layer_buttons = []

        # create new layer labels
        for x in range(self.keyboard.layers):
            btn = SquareButton(str(x))
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setRelSize(1.667)
            btn.setCheckable(True)
            btn.clicked.connect(lambda state, idx=x: self.switch_layer(idx))
            self.layout_layers.addWidget(btn)
            self.layer_buttons.append(btn)
        for x in range(0,2):
            btn = SquareButton("-") if x else SquareButton("+")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setCheckable(False)
            btn.clicked.connect(lambda state, idx=x: self.adjust_size(idx))
            self.layout_size.addWidget(btn)
            self.layer_buttons.append(btn)

    def adjust_size(self, minus):
        if minus:
            self.container.set_scale(self.container.get_scale() - 0.1)
        else:
            self.container.set_scale(self.container.get_scale() + 0.1)
        self.refresh_layer_display()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            # get number of layers
            self.rebuild_layers()

            self.container.set_keys(self.keyboard.keys, self.keyboard.encoders)

            self.current_layer = 0
            self.on_layout_changed()

            self.tabbed_keycodes.recreate_keycode_buttons()
            TabbedKeycodes.tray.recreate_keycode_buttons()

            # Initialize encoder widget with keyboard data
            self.encoder_assign.set_layer(self.current_layer, self.keyboard)

            self.refresh_layer_display()

        # Set device for quick actuation widget (loads all layers once)
        self.quick_actuation.set_device(device)
        if self.valid():
            self.quick_actuation.set_layer(self.current_layer)
        self.container.setEnabled(self.valid())

    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def save_layout(self):
        return self.keyboard.save_layout()

    def restore_layout(self, data):
        if json.loads(data.decode("utf-8")).get("uid") != self.keyboard.keyboard_id:
            ret = QMessageBox.question(self.widget(), "",
                                       tr("KeymapEditor", "Saved keymap belongs to a different keyboard,"
                                                          " are you sure you want to continue?"),
                                       QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.keyboard.restore_layout(data)
        self.refresh_layer_display()

    def on_any_keycode(self):
        if self.container.active_key is None:
            return
        current_code = self.code_for_widget(self.container.active_key)
        if self.container.active_mask:
            kc = Keycode.find_inner_keycode(current_code)
            current_code = kc.qmk_id

        self.dlg = AnyKeycodeDialog(current_code)
        self.dlg.finished.connect(self.on_dlg_finished)
        self.dlg.setModal(True)
        self.dlg.show()

    def on_dlg_finished(self, res):
        if res > 0:
            self.on_keycode_changed(self.dlg.value)

    def code_for_widget(self, widget):
        if widget.desc.row is not None:
            return self.keyboard.layout[(self.current_layer, widget.desc.row, widget.desc.col)]
        else:
            return self.keyboard.encoder_layout[(self.current_layer, widget.desc.encoder_idx,
                                                 widget.desc.encoder_dir)]

    def refresh_layer_display(self):
        """ Refresh text on key widgets to display data corresponding to current layer """

        self.container.update_layout()

        for idx, btn in enumerate(self.layer_buttons):
            btn.setEnabled(idx != self.current_layer)
            btn.setChecked(idx == self.current_layer)

        for widget in self.container.widgets:
            code = self.code_for_widget(widget)
            KeycodeDisplay.display_keycode(widget, code)
        self.container.update()
        self.container.updateGeometry()

    def switch_layer(self, idx):
        self.container.deselect()
        self.current_layer = idx
        # Update quick actuation widget layer (loads from memory, no lag)
        self.quick_actuation.set_layer(idx)
        # Update encoder widget layer (load from keyboard)
        self.encoder_assign.set_layer(idx, self.keyboard)
        self.refresh_layer_display()

    def set_key(self, keycode):
        """ Change currently selected key to provided keycode """

        if self.container.active_key is None:
            return

        if isinstance(self.container.active_key, EncoderWidget2):
            self.set_key_encoder(keycode)
        else:
            self.set_key_matrix(keycode)

        self.container.select_next()

    def set_encoder_keycode(self, button_index, keycode):
        """Set keycode for encoder/sustain button and send to keyboard via USB"""
        l = self.current_layer

        # Map button index to encoder parameters or matrix key positions
        # Button 0: Encoder 1 Up (enc_idx=0, dir=1) - encoder rotation
        # Button 1: Encoder 1 Down (enc_idx=0, dir=0) - encoder rotation
        # Button 2: Encoder 1 Press - matrix key at row=5, col=1
        # Button 3: Encoder 2 Up (enc_idx=1, dir=1) - encoder rotation
        # Button 4: Encoder 2 Down (enc_idx=1, dir=0) - encoder rotation
        # Button 5: Encoder 2 Press - matrix key at row=5, col=0
        # Button 6: Sustain Pedal - matrix key at row=5, col=2

        # Matrix key mappings for encoder clicks and sustain pedal
        matrix_key_mapping = {
            2: (5, 1),  # Encoder 1 Press -> row 5, col 1
            5: (5, 0),  # Encoder 2 Press -> row 5, col 0
            6: (5, 2),  # Sustain Pedal -> row 5, col 2
        }

        if button_index in matrix_key_mapping:
            # These are regular matrix keys, not encoder actions
            row, col = matrix_key_mapping[button_index]
            self.keyboard.set_key(l, row, col, keycode)
        else:
            # Map button index to encoder index and direction (rotation only)
            encoder_mapping = {
                0: (0, 1),  # Encoder 1 Up (CW)
                1: (0, 0),  # Encoder 1 Down (CCW)
                3: (1, 1),  # Encoder 2 Up (CW)
                4: (1, 0),  # Encoder 2 Down (CCW)
            }

            if button_index in encoder_mapping:
                enc_idx, direction = encoder_mapping[button_index]
                self.keyboard.set_encoder(l, enc_idx, direction, keycode)

        # Update the button display
        self.encoder_assign.set_keycode(button_index, keycode)
        self.refresh_layer_display()

    def set_key_encoder(self, keycode):
        l, i, d = self.current_layer, self.container.active_key.desc.encoder_idx,\
                            self.container.active_key.desc.encoder_dir

        # if masked, ensure that this is a byte-sized keycode
        if self.container.active_mask:
            if not Keycode.is_basic(keycode):
                return
            kc = Keycode.find_outer_keycode(self.keyboard.encoder_layout[(l, i, d)])
            if kc is None:
                return
            keycode = kc.qmk_id.replace("(kc)", "({})".format(keycode))

        self.keyboard.set_encoder(l, i, d, keycode)
        self.refresh_layer_display()

    def set_key_matrix(self, keycode):
        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            # if masked, ensure that this is a byte-sized keycode
            if self.container.active_mask:
                if not Keycode.is_basic(keycode):
                    return
                kc = Keycode.find_outer_keycode(self.keyboard.layout[(l, r, c)])
                if kc is None:
                    return
                keycode = kc.qmk_id.replace("(kc)", "({})".format(keycode))

            self.keyboard.set_key(l, r, c, keycode)
            self.refresh_layer_display()

    def on_key_clicked(self):
        """ Called when a key on the keyboard widget is clicked """
        # Deselect encoder buttons when keyboard is clicked
        self.encoder_assign.deselect()

        self.refresh_layer_display()
        if self.container.active_mask:
            self.tabbed_keycodes.set_keycode_filter(keycode_filter_masked)
        else:
            self.tabbed_keycodes.set_keycode_filter(None)

    def on_key_deselected(self):
        self.tabbed_keycodes.set_keycode_filter(None)

    def on_encoder_clicked(self):
        """ Called when an encoder button is clicked """
        # Deselect keyboard keys when encoder button is clicked
        self.container.deselect()
        self.container.update()

        # No filter needed for encoder assignments
        self.tabbed_keycodes.set_keycode_filter(None)

    def on_layout_changed(self):
        if self.keyboard is None:
            return

        self.refresh_layer_display()
        self.keyboard.set_layout_options(self.layout_editor.pack())

    def on_keymap_override(self):
        self.refresh_layer_display()
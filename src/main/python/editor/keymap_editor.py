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
from protocol.keyboard_comm import (
    PARAM_CHANNEL_NUMBER, PARAM_TRANSPOSE_NUMBER, PARAM_TRANSPOSE_NUMBER2, PARAM_TRANSPOSE_NUMBER3,
    PARAM_HE_VELOCITY_CURVE, PARAM_HE_VELOCITY_MIN, PARAM_HE_VELOCITY_MAX,
    PARAM_KEYSPLIT_HE_VELOCITY_CURVE, PARAM_KEYSPLIT_HE_VELOCITY_MIN, PARAM_KEYSPLIT_HE_VELOCITY_MAX,
    PARAM_TRIPLESPLIT_HE_VELOCITY_CURVE, PARAM_TRIPLESPLIT_HE_VELOCITY_MIN, PARAM_TRIPLESPLIT_HE_VELOCITY_MAX,
    PARAM_AFTERTOUCH_MODE, PARAM_AFTERTOUCH_CC, PARAM_BASE_SUSTAIN, PARAM_KEYSPLIT_SUSTAIN, PARAM_TRIPLESPLIT_SUSTAIN,
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
                'vel_speed': 10  # Velocity speed scale
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
            'aftertouch': 0,
            'aftertouch_cc': 74,
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
        top_row_layout.addWidget(self.enable_per_key_checkbox)

        self.per_layer_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable Per-Layer Actuation"))
        self.per_layer_checkbox.setStyleSheet("QCheckBox { font-weight: bold; font-size: 10px; } QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_toggled)
        top_row_layout.addWidget(self.per_layer_checkbox)

        self.advanced_checkbox = QCheckBox(tr("QuickActuationWidget", "Show Advanced"))
        self.advanced_checkbox.setStyleSheet("QCheckBox { font-weight: normal; font-size: 10px; } QCheckBox::indicator { border: 1px solid palette(mid); background-color: palette(button); width: 13px; height: 13px; } QCheckBox::indicator:checked { border: 1px solid palette(highlight); background-color: palette(highlight); }")
        self.advanced_checkbox.stateChanged.connect(self.on_advanced_toggled)
        top_row_layout.addWidget(self.advanced_checkbox)

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
        
        # Normal Keys Actuation slider - ALWAYS VISIBLE
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(6)
        label = QLabel(tr("QuickActuationWidget", "Normal Keys:"))
        label.setMinimumWidth(90)
        label.setMaximumWidth(90)
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
        
        layout.addLayout(slider_layout)
        self.normal_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('normal', v, self.normal_value_label)
        )

        # MIDI Keys Actuation slider (visible in advanced mode)
        midi_slider_layout = QHBoxLayout()
        midi_slider_layout.setContentsMargins(0, 0, 0, 0)
        midi_slider_layout.setSpacing(6)
        midi_label = QLabel(tr("QuickActuationWidget", "MIDI Keys:"))
        midi_label.setMinimumWidth(90)
        midi_label.setMaximumWidth(90)
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

        self.midi_widget = QWidget()
        self.midi_widget.setLayout(midi_slider_layout)
        self.midi_widget.setVisible(False)
        layout.addWidget(self.midi_widget)

        self.midi_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('midi', v, self.midi_value_label)
        )

        # Note: Velocity Curve, Velocity Min/Max, Transpose, Channel, Aftertouch, and Aftertouch CC
        # have been moved to the MIDI Settings tab as global keyboard settings

        # === ADVANCED OPTIONS (hidden by default) ===
        self.advanced_widget = QWidget()
        advanced_layout = QVBoxLayout()
        advanced_layout.setSpacing(6)
        advanced_layout.setContentsMargins(0, 5, 0, 0)
        self.advanced_widget.setLayout(advanced_layout)
        self.advanced_widget.setVisible(False)
        
        # Separator
        adv_line = QFrame()
        adv_line.setFrameShape(QFrame.HLine)
        adv_line.setFrameShadow(QFrame.Sunken)
        advanced_layout.addWidget(adv_line)

        # Velocity Mode combo
        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(6)
        label = QLabel(tr("QuickActuationWidget", "Velocity:"))
        label.setMinimumWidth(90)
        label.setMaximumWidth(90)
        combo_layout.addWidget(label)

        self.velocity_combo = ArrowComboBox()
        self.velocity_combo.setMaximumHeight(30)
        self.velocity_combo.setMaximumWidth(180)
        self.velocity_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        self.velocity_combo.addItem("Fixed (64)", 0)
        self.velocity_combo.addItem("Peak at Apex", 1)
        self.velocity_combo.addItem("Speed-Based", 2)
        self.velocity_combo.addItem("Speed + Peak", 3)
        self.velocity_combo.setCurrentIndex(2)
        self.velocity_combo.setEditable(True)
        self.velocity_combo.lineEdit().setReadOnly(True)
        self.velocity_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(self.velocity_combo, 1)
        
        advanced_layout.addLayout(combo_layout)
        self.velocity_combo.currentIndexChanged.connect(self.on_combo_changed)
        
        # Velocity Speed Scale combo
        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(6)
        label = QLabel(tr("QuickActuationWidget", "Velocity Scale:"))
        label.setMinimumWidth(90)
        label.setMaximumWidth(90)
        combo_layout.addWidget(label)

        self.vel_speed_combo = ArrowComboBox()
        self.vel_speed_combo.setMaximumHeight(30)
        self.vel_speed_combo.setMaximumWidth(180)
        self.vel_speed_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for i in range(1, 21):
            self.vel_speed_combo.addItem(str(i), i)
        self.vel_speed_combo.setCurrentIndex(9)
        self.vel_speed_combo.setEditable(True)
        self.vel_speed_combo.lineEdit().setReadOnly(True)
        self.vel_speed_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(self.vel_speed_combo, 1)
        
        advanced_layout.addLayout(combo_layout)
        self.vel_speed_combo.currentIndexChanged.connect(self.on_combo_changed)

        layout.addWidget(self.advanced_widget)

        layout.addStretch()

        # Save button at the bottom
        self.save_btn = QPushButton(tr("QuickActuationWidget", "Save to All Layers"))
        self.save_btn.setMaximumHeight(24)
        self.save_btn.setStyleSheet("padding: 2px 6px; font-size: 9pt;")
        self.save_btn.clicked.connect(self.on_save_actuation)
        layout.addWidget(self.save_btn)

        return tab

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

        # Advanced MIDI Settings (aftertouch, shown when advanced is enabled)
        self.midi_advanced_widget = QWidget()
        adv_layout = QVBoxLayout()
        adv_layout.setSpacing(6)
        adv_layout.setContentsMargins(0, 5, 0, 0)
        self.midi_advanced_widget.setLayout(adv_layout)
        self.midi_advanced_widget.setVisible(False)
        layout.addWidget(self.midi_advanced_widget)

        # Aftertouch settings (no title to save space)
        aftertouch_group = QWidget()
        aftertouch_layout = QVBoxLayout()
        aftertouch_layout.setSpacing(4)
        aftertouch_layout.setContentsMargins(0, 0, 0, 0)
        aftertouch_group.setLayout(aftertouch_layout)
        adv_layout.addWidget(aftertouch_group)

        # Aftertouch and AT CC side by side
        at_row_layout = QHBoxLayout()
        at_row_layout.setContentsMargins(0, 0, 0, 0)
        at_row_layout.setSpacing(10)

        # Aftertouch (same width as CC)
        at_container = QVBoxLayout()
        at_container.setSpacing(2)
        at_label = QLabel(tr("QuickActuationWidget", "Aftertouch"))
        at_label.setAlignment(Qt.AlignCenter)
        at_label.setStyleSheet("QLabel { font-size: 12px; }")
        at_container.addWidget(at_label)
        self.midi_aftertouch = ArrowComboBox()
        self.midi_aftertouch.setMaximumHeight(30)
        self.midi_aftertouch.setStyleSheet("QComboBox { padding: 0px; font-size: 10px; text-align: center; }")
        self.midi_aftertouch.setEditable(True)
        self.midi_aftertouch.lineEdit().setReadOnly(True)
        self.midi_aftertouch.lineEdit().setAlignment(Qt.AlignCenter)
        self.midi_aftertouch.addItem("Off", 0)
        self.midi_aftertouch.addItem("Reverse", 1)
        self.midi_aftertouch.addItem("Bottom-Out", 2)
        self.midi_aftertouch.addItem("Post-Act", 3)
        self.midi_aftertouch.addItem("Vibrato", 4)
        self.midi_aftertouch.setCurrentIndex(0)
        self.midi_aftertouch.currentIndexChanged.connect(self.on_midi_settings_changed)
        at_container.addWidget(self.midi_aftertouch)
        at_row_layout.addLayout(at_container, 1)

        # Aftertouch CC (same width as Aftertouch)
        atcc_container = QVBoxLayout()
        atcc_container.setSpacing(2)
        atcc_label = QLabel(tr("QuickActuationWidget", "Aftertouch CC"))
        atcc_label.setAlignment(Qt.AlignCenter)
        atcc_label.setStyleSheet("QLabel { font-size: 12px; }")
        atcc_container.addWidget(atcc_label)
        self.midi_aftertouch_cc = ArrowComboBox()
        self.midi_aftertouch_cc.setMaximumHeight(30)
        self.midi_aftertouch_cc.setStyleSheet("QComboBox { padding: 0px; font-size: 10px; text-align: center; }")
        self.midi_aftertouch_cc.setEditable(True)
        self.midi_aftertouch_cc.lineEdit().setReadOnly(True)
        self.midi_aftertouch_cc.lineEdit().setAlignment(Qt.AlignCenter)
        for cc in range(128):
            self.midi_aftertouch_cc.addItem(f"CC#{cc}", cc)
        self.midi_aftertouch_cc.setCurrentIndex(74)
        self.midi_aftertouch_cc.currentIndexChanged.connect(self.on_midi_settings_changed)
        atcc_container.addWidget(self.midi_aftertouch_cc)
        at_row_layout.addLayout(atcc_container, 1)

        aftertouch_layout.addLayout(at_row_layout)

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
        
    def on_advanced_toggled(self):
        """Toggle advanced options visibility"""
        show_advanced = self.advanced_checkbox.isChecked()
        self.advanced_widget.setVisible(show_advanced)

        # Show/hide MIDI controls based on advanced state
        self.midi_widget.setVisible(show_advanced)
    
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
        if self.enable_per_key_checkbox.isChecked():
            # Show notification message
            QMessageBox.information(
                self,
                tr("QuickActuationWidget", "Switching to Advanced Trigger Settings"),
                tr("QuickActuationWidget", "Switching to advanced trigger settings tab")
            )

            # Emit signal to request tab switch
            self.enable_per_key_requested.emit()

            # Uncheck this checkbox (it will be managed in Trigger Settings tab)
            self.syncing = True
            self.enable_per_key_checkbox.setChecked(False)
            self.syncing = False

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
            # Sync MIDI to normal when advanced is off
            if key == 'normal' and not self.advanced_widget.isVisible():
                self.midi_slider.setValue(value)
                self.midi_value_label.setText(f"{value * 0.025:.2f}mm")
        elif key == 'midi_rapid_vel':
            label.setText(f"±{value}")
        else:
            label.setText(str(value))
        
        # Update memory
        self.save_ui_to_memory()
    
    def on_combo_changed(self):
        """Handle combo box changes"""
        if not self.syncing:
            self.save_ui_to_memory()
    
    def save_ui_to_memory(self):
        """Save current UI state to memory (for current layer if per-layer, all if master)"""
        if self.per_layer_enabled:
            # Save only to current layer
            self.layer_data[self.current_layer] = {
                'normal': self.normal_slider.value(),
                'midi': self.midi_slider.value(),
                'velocity': self.velocity_combo.currentData(),
                'vel_speed': self.vel_speed_combo.currentData()
            }
        else:
            # Save to all layers (master mode)
            data = {
                'normal': self.normal_slider.value(),
                'midi': self.midi_slider.value(),
                'velocity': self.velocity_combo.currentData(),
                'vel_speed': self.vel_speed_combo.currentData()
            }
            for i in range(12):
                self.layer_data[i] = data.copy()
    
    def load_layer_from_memory(self):
        """Load layer settings from memory cache"""
        self.syncing = True
        
        data = self.layer_data[self.current_layer]
        
        # Set sliders and immediately update labels
        self.normal_slider.setValue(data['normal'])
        self.normal_value_label.setText(f"{data['normal'] * 0.025:.2f}mm")

        self.midi_slider.setValue(data['midi'])
        self.midi_value_label.setText(f"{data['midi'] * 0.025:.2f}mm")

        # Set combos
        for i in range(self.velocity_combo.count()):
            if self.velocity_combo.itemData(i) == data['velocity']:
                self.velocity_combo.setCurrentIndex(i)
                break

        for i in range(self.vel_speed_combo.count()):
            if self.vel_speed_combo.itemData(i) == data['vel_speed']:
                self.vel_speed_combo.setCurrentIndex(i)
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
        self.midi_advanced_widget.setVisible(show_advanced)

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
        self.midi_settings['aftertouch'] = self.midi_aftertouch.currentData()
        self.midi_settings['aftertouch_cc'] = self.midi_aftertouch_cc.currentData()

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
        """Save actuation settings - to all layers or current layer depending on mode"""
        try:
            if not self.device or not isinstance(self.device, VialKeyboard):
                raise RuntimeError("Device not connected")
            
            if self.per_layer_enabled:
                # Save to current layer only
                data = self.layer_data[self.current_layer]
                flags = 0
                if data['rapidfire_enabled']:
                    flags |= 0x01
                if data['midi_rapidfire_enabled']:
                    flags |= 0x02

                # New structure: 9 bytes total (layer + 8 data bytes)
                # Global MIDI settings (velocity curves, aftertouch, transpose, channel) moved to keyboard settings
                payload = bytearray([
                    self.current_layer,
                    data['normal'],
                    data['midi'],
                    data['velocity'],  # Velocity mode
                    data['rapid'],
                    data['midi_rapid_sens'],
                    data['midi_rapid_vel'],
                    data['vel_speed'],
                    flags
                ])

                if not self.device.keyboard.set_layer_actuation(payload):
                    raise RuntimeError(f"Failed to set actuation for layer {self.current_layer}")

                QMessageBox.information(None, "Success",
                    f"Layer {self.current_layer} actuation saved successfully!")
            else:
                # Save to all 12 layers
                for layer in range(12):
                    data = self.layer_data[layer]
                    flags = 0
                    if data['rapidfire_enabled']:
                        flags |= 0x01
                    if data['midi_rapidfire_enabled']:
                        flags |= 0x02

                    # New structure: 9 bytes total (layer + 8 data bytes)
                    # Global MIDI settings (velocity curves, aftertouch, transpose, channel) moved to keyboard settings
                    payload = bytearray([
                        layer,
                        data['normal'],
                        data['midi'],
                        data['velocity'],  # Velocity mode
                        data['rapid'],
                        data['midi_rapid_sens'],
                        data['midi_rapid_vel'],
                        data['vel_speed'],
                        flags
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
            self.advanced_checkbox.setEnabled(True)

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

            if not actuations or len(actuations) != 96:  # 12 layers * 8 bytes
                return

            # Load all layers into memory
            # Note: Global MIDI settings (velocity curves, aftertouch, transpose, channel) moved to keyboard settings
            for layer in range(12):
                offset = layer * 8
                flags = actuations[offset + 7]

                self.layer_data[layer] = {
                    'normal': actuations[offset + 0],
                    'midi': actuations[offset + 1],
                    'velocity': actuations[offset + 2],  # Velocity mode
                    'rapid': actuations[offset + 3],
                    'midi_rapid_sens': actuations[offset + 4],
                    'midi_rapid_vel': actuations[offset + 5],
                    'vel_speed': actuations[offset + 6],
                    'rapidfire_enabled': (flags & 0x01) != 0,
                    'midi_rapidfire_enabled': (flags & 0x02) != 0
                }
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
            # Map button indices to encoder/key parameters
            # Buttons 0-5 are encoders, button 6 is sustain pedal
            encoder_mapping = {
                0: (0, 1),  # Encoder 1 Up (enc_idx=0, dir=1)
                1: (0, 0),  # Encoder 1 Down (enc_idx=0, dir=0)
                2: (0, 2),  # Encoder 1 Press (enc_idx=0, dir=2)
                3: (1, 1),  # Encoder 2 Up (enc_idx=1, dir=1)
                4: (1, 0),  # Encoder 2 Down (enc_idx=1, dir=0)
                5: (1, 2),  # Encoder 2 Press (enc_idx=1, dir=2)
            }

            # Update encoder buttons
            for idx in range(6):
                if idx in encoder_mapping:
                    enc_idx, direction = encoder_mapping[idx]
                    keycode = keyboard.encoder_layout.get((layer, enc_idx, direction), "KC_NO")
                    self.buttons[idx].setText(Keycode.label(keycode))

            # Update sustain pedal button (row=5, col=2)
            sustain_keycode = keyboard.layout.get((layer, 5, 2), "KC_NO")
            self.buttons[6].setText(Keycode.label(sustain_keycode))

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

        # Map button index to encoder parameters or sustain pedal key position
        # Button 0: Encoder 1 Up (enc_idx=0, dir=1)
        # Button 1: Encoder 1 Down (enc_idx=0, dir=0)
        # Button 2: Encoder 1 Press (enc_idx=0, dir=2)
        # Button 3: Encoder 2 Up (enc_idx=1, dir=1)
        # Button 4: Encoder 2 Down (enc_idx=1, dir=0)
        # Button 5: Encoder 2 Press (enc_idx=1, dir=2)
        # Button 6: Sustain Pedal (row=5, col=2)

        if button_index == 6:
            # Sustain pedal is a regular matrix key at row=5, col=2
            self.keyboard.set_key(l, 5, 2, keycode)
        else:
            # Map button index to encoder index and direction
            encoder_mapping = {
                0: (0, 1),  # Encoder 1 Up
                1: (0, 0),  # Encoder 1 Down
                2: (0, 2),  # Encoder 1 Press
                3: (1, 1),  # Encoder 2 Up
                4: (1, 0),  # Encoder 2 Down
                5: (1, 2),  # Encoder 2 Press
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
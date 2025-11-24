# SPDX-License-Identifier: GPL-2.0-or-later
import json
import struct

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QWidget,
                              QGroupBox, QSlider, QCheckBox, QPushButton, QComboBox, QFrame,
                              QSizePolicy, QScrollArea, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal

from widgets.combo_box import ArrowComboBox
from any_keycode_dialog import AnyKeycodeDialog
from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget2, EncoderWidget, EncoderWidget2
from keycodes.keycodes import Keycode
from widgets.square_button import SquareButton
from tabbed_keycodes import TabbedKeycodes, keycode_filter_masked
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard


class QuickActuationWidget(QWidget):
    """Full-featured per-layer actuation controls in keymap editor"""

    def __init__(self):
        super().__init__()

        self.device = None
        self.syncing = False
        self.current_layer = 0
        self.per_layer_enabled = False

        # Cache all layer data in memory to avoid device I/O lag
        self.layer_data = []
        for _ in range(12):
            self.layer_data.append({
                'normal': 80,
                'midi': 80,
                'velocity': 2,  # Velocity mode (0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak)
                'rapid': 4,
                'midi_rapid_sens': 10,
                'midi_rapid_vel': 10,
                'vel_speed': 10,  # Velocity speed scale
                'rapidfire_enabled': False,
                'midi_rapidfire_enabled': False
            })

        # MIDI settings (global, per keyboard)
        self.midi_settings = {
            'channel': 0,
            'transpose': 0,
            'velocity_preset': 2,  # Medium
            'velocity_curve': 2,
            'velocity_min': 1,
            'velocity_max': 127,
            'aftertouch': 0,
            'aftertouch_cc': 74,
            'keysplit_enabled': False,
            'keysplit_channel': 0,
            'keysplit_transpose': 0,
            'keysplit_velocity_curve': 2,
            'keysplit_velocity_min': 1,
            'keysplit_velocity_max': 127,
            'triplesplit_enabled': False,
            'triplesplit_channel': 0,
            'triplesplit_transpose': 0,
            'triplesplit_velocity_curve': 2,
            'triplesplit_velocity_min': 1,
            'triplesplit_velocity_max': 127
        }

        self.setMinimumWidth(200)
        self.setMaximumWidth(350)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
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

        # Top row with Enable Per-Layer and Show Advanced checkboxes
        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(10)

        self.per_layer_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable Per-Layer"))
        self.per_layer_checkbox.setStyleSheet("QCheckBox { font-weight: bold; font-size: 10px; }")
        self.per_layer_checkbox.stateChanged.connect(self.on_per_layer_toggled)
        top_row_layout.addWidget(self.per_layer_checkbox)

        self.advanced_checkbox = QCheckBox(tr("QuickActuationWidget", "Show Advanced"))
        self.advanced_checkbox.setStyleSheet("QCheckBox { font-weight: normal; font-size: 10px; }")
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
        
        # Enable Rapidfire checkbox - ALWAYS VISIBLE
        self.rapid_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable Rapidfire"))
        self.rapid_checkbox.setChecked(False)
        layout.addWidget(self.rapid_checkbox)
        self.rapid_checkbox.stateChanged.connect(self.on_rapidfire_toggled)
        
        # Rapidfire Sensitivity slider (hidden by default)
        rapid_slider_layout = QHBoxLayout()
        rapid_slider_layout.setContentsMargins(0, 0, 0, 0)
        rapid_slider_layout.setSpacing(6)
        rapid_label = QLabel(tr("QuickActuationWidget", "RF Sensitivity:"))
        rapid_label.setMinimumWidth(90)
        rapid_label.setMaximumWidth(90)
        rapid_slider_layout.addWidget(rapid_label)
        
        self.rapid_slider = QSlider(Qt.Horizontal)
        self.rapid_slider.setMinimum(1)
        self.rapid_slider.setMaximum(100)
        self.rapid_slider.setValue(4)
        rapid_slider_layout.addWidget(self.rapid_slider, 1)
        
        self.rapid_value_label = QLabel("4")
        self.rapid_value_label.setMinimumWidth(50)
        self.rapid_value_label.setMaximumWidth(50)
        self.rapid_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        rapid_slider_layout.addWidget(self.rapid_value_label)
        
        self.rapid_widget = QWidget()
        self.rapid_widget.setLayout(rapid_slider_layout)
        self.rapid_widget.setVisible(False)
        layout.addWidget(self.rapid_widget)
        
        self.rapid_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('rapid', v, self.rapid_value_label)
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

        # Enable MIDI Rapidfire checkbox (visible in advanced mode)
        self.midi_rapid_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable MIDI Rapidfire"))
        self.midi_rapid_checkbox.setChecked(False)
        self.midi_rapid_checkbox.setVisible(False)
        layout.addWidget(self.midi_rapid_checkbox)
        self.midi_rapid_checkbox.stateChanged.connect(self.on_midi_rapidfire_toggled)
        
        # MIDI Rapidfire Sensitivity slider
        midi_rapid_sens_layout = QHBoxLayout()
        midi_rapid_sens_layout.setContentsMargins(0, 0, 0, 0)
        midi_rapid_sens_layout.setSpacing(6)
        midi_rapid_sens_label = QLabel(tr("QuickActuationWidget", "MRF Sens:"))
        midi_rapid_sens_label.setMinimumWidth(90)
        midi_rapid_sens_label.setMaximumWidth(90)
        midi_rapid_sens_layout.addWidget(midi_rapid_sens_label)
        
        self.midi_rapid_sens_slider = QSlider(Qt.Horizontal)
        self.midi_rapid_sens_slider.setMinimum(1)
        self.midi_rapid_sens_slider.setMaximum(100)
        self.midi_rapid_sens_slider.setValue(10)
        midi_rapid_sens_layout.addWidget(self.midi_rapid_sens_slider, 1)
        
        self.midi_rapid_sens_value_label = QLabel("10")
        self.midi_rapid_sens_value_label.setMinimumWidth(50)
        self.midi_rapid_sens_value_label.setMaximumWidth(50)
        self.midi_rapid_sens_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        midi_rapid_sens_layout.addWidget(self.midi_rapid_sens_value_label)
        
        self.midi_rapid_sens_widget = QWidget()
        self.midi_rapid_sens_widget.setLayout(midi_rapid_sens_layout)
        self.midi_rapid_sens_widget.setVisible(False)
        layout.addWidget(self.midi_rapid_sens_widget)
        
        self.midi_rapid_sens_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('midi_rapid_sens', v, self.midi_rapid_sens_value_label)
        )
        
        # MIDI Rapidfire Velocity Range slider
        midi_rapid_vel_layout = QHBoxLayout()
        midi_rapid_vel_layout.setContentsMargins(0, 0, 0, 0)
        midi_rapid_vel_layout.setSpacing(6)
        midi_rapid_vel_label = QLabel(tr("QuickActuationWidget", "MRF Vel:"))
        midi_rapid_vel_label.setMinimumWidth(90)
        midi_rapid_vel_label.setMaximumWidth(90)
        midi_rapid_vel_layout.addWidget(midi_rapid_vel_label)
        
        self.midi_rapid_vel_slider = QSlider(Qt.Horizontal)
        self.midi_rapid_vel_slider.setMinimum(0)
        self.midi_rapid_vel_slider.setMaximum(20)
        self.midi_rapid_vel_slider.setValue(10)
        midi_rapid_vel_layout.addWidget(self.midi_rapid_vel_slider, 1)
        
        self.midi_rapid_vel_value_label = QLabel("±10")
        self.midi_rapid_vel_value_label.setMinimumWidth(50)
        self.midi_rapid_vel_value_label.setMaximumWidth(50)
        self.midi_rapid_vel_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        midi_rapid_vel_layout.addWidget(self.midi_rapid_vel_value_label)
        
        self.midi_rapid_vel_widget = QWidget()
        self.midi_rapid_vel_widget.setLayout(midi_rapid_vel_layout)
        self.midi_rapid_vel_widget.setVisible(False)
        layout.addWidget(self.midi_rapid_vel_widget)
        
        self.midi_rapid_vel_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('midi_rapid_vel', v, self.midi_rapid_vel_value_label)
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

        # Basic MIDI Settings
        basic_group = QGroupBox(tr("QuickActuationWidget", "Basic MIDI Settings"))
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(4)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Channel
        ch_layout = QHBoxLayout()
        ch_layout.setContentsMargins(0, 0, 0, 0)
        ch_layout.setSpacing(6)
        ch_label = QLabel(tr("QuickActuationWidget", "Channel:"))
        ch_label.setMinimumWidth(70)
        ch_label.setMaximumWidth(70)
        ch_layout.addWidget(ch_label)
        self.midi_channel = ArrowComboBox()
        self.midi_channel.setMaximumHeight(30)
        self.midi_channel.setMaximumWidth(180)
        self.midi_channel.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for i in range(16):
            self.midi_channel.addItem(f"Channel {i + 1}", i)
        self.midi_channel.setCurrentIndex(0)
        self.midi_channel.currentIndexChanged.connect(self.on_midi_settings_changed)
        ch_layout.addWidget(self.midi_channel)
        ch_layout.addStretch()
        basic_layout.addLayout(ch_layout)

        # Transpose
        trans_layout = QHBoxLayout()
        trans_layout.setContentsMargins(0, 0, 0, 0)
        trans_layout.setSpacing(6)
        trans_label = QLabel(tr("QuickActuationWidget", "Transpose:"))
        trans_label.setMinimumWidth(70)
        trans_label.setMaximumWidth(70)
        trans_layout.addWidget(trans_label)
        self.midi_transpose = ArrowComboBox()
        self.midi_transpose.setMaximumHeight(30)
        self.midi_transpose.setMaximumWidth(180)
        self.midi_transpose.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for i in range(-64, 65):
            self.midi_transpose.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.midi_transpose.setCurrentIndex(64)  # 0
        self.midi_transpose.currentIndexChanged.connect(self.on_midi_settings_changed)
        trans_layout.addWidget(self.midi_transpose)
        trans_layout.addStretch()
        basic_layout.addLayout(trans_layout)

        # Velocity Preset
        vel_preset_layout = QHBoxLayout()
        vel_preset_layout.setContentsMargins(0, 0, 0, 0)
        vel_preset_layout.setSpacing(6)
        self.midi_velocity_preset_label = QLabel(tr("QuickActuationWidget", "Velocity:"))
        self.midi_velocity_preset_label.setMinimumWidth(70)
        self.midi_velocity_preset_label.setMaximumWidth(70)
        vel_preset_layout.addWidget(self.midi_velocity_preset_label)
        self.midi_velocity_preset = ArrowComboBox()
        self.midi_velocity_preset.setMaximumHeight(30)
        self.midi_velocity_preset.setMaximumWidth(180)
        self.midi_velocity_preset.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        self.midi_velocity_preset.addItem("Softest", 0)
        self.midi_velocity_preset.addItem("Soft", 1)
        self.midi_velocity_preset.addItem("Medium", 2)
        self.midi_velocity_preset.addItem("Hard", 3)
        self.midi_velocity_preset.addItem("Hardest", 4)
        self.midi_velocity_preset.setCurrentIndex(2)
        self.midi_velocity_preset.currentIndexChanged.connect(self.on_velocity_preset_changed)
        vel_preset_layout.addWidget(self.midi_velocity_preset)
        vel_preset_layout.addStretch()
        basic_layout.addLayout(vel_preset_layout)

        # Advanced MIDI checkbox
        self.midi_advanced_checkbox = QCheckBox(tr("QuickActuationWidget", "Show Advanced MIDI Settings"))
        self.midi_advanced_checkbox.stateChanged.connect(self.on_midi_advanced_toggled)
        layout.addWidget(self.midi_advanced_checkbox)

        # Advanced MIDI Settings (hidden by default)
        self.midi_advanced_widget = QWidget()
        adv_layout = QVBoxLayout()
        adv_layout.setSpacing(6)
        adv_layout.setContentsMargins(0, 5, 0, 0)
        self.midi_advanced_widget.setLayout(adv_layout)
        self.midi_advanced_widget.setVisible(False)
        layout.addWidget(self.midi_advanced_widget)

        # Velocity Min/Max/Curve (replaces preset in advanced mode)
        adv_vel_group = QGroupBox(tr("QuickActuationWidget", "Velocity Settings"))
        adv_vel_layout = QVBoxLayout()
        adv_vel_layout.setSpacing(4)
        adv_vel_group.setLayout(adv_vel_layout)
        adv_layout.addWidget(adv_vel_group)

        # Velocity Curve
        curve_layout = QHBoxLayout()
        curve_layout.setContentsMargins(0, 0, 0, 0)
        curve_layout.setSpacing(6)
        curve_label = QLabel(tr("QuickActuationWidget", "Curve:"))
        curve_label.setMinimumWidth(70)
        curve_label.setMaximumWidth(70)
        curve_layout.addWidget(curve_label)
        self.midi_velocity_curve = ArrowComboBox()
        self.midi_velocity_curve.setMaximumHeight(30)
        self.midi_velocity_curve.setMaximumWidth(180)
        self.midi_velocity_curve.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        self.midi_velocity_curve.addItem("Softest", 0)
        self.midi_velocity_curve.addItem("Soft", 1)
        self.midi_velocity_curve.addItem("Medium", 2)
        self.midi_velocity_curve.addItem("Hard", 3)
        self.midi_velocity_curve.addItem("Hardest", 4)
        self.midi_velocity_curve.setCurrentIndex(2)
        self.midi_velocity_curve.currentIndexChanged.connect(self.on_midi_settings_changed)
        curve_layout.addWidget(self.midi_velocity_curve)
        curve_layout.addStretch()
        adv_vel_layout.addLayout(curve_layout)

        # Velocity Min (slider)
        min_layout = QHBoxLayout()
        min_layout.setContentsMargins(0, 0, 0, 0)
        min_layout.setSpacing(6)
        min_label = QLabel(tr("QuickActuationWidget", "Min:"))
        min_label.setMinimumWidth(70)
        min_label.setMaximumWidth(70)
        min_layout.addWidget(min_label)
        self.midi_velocity_min = QSlider(Qt.Horizontal)
        self.midi_velocity_min.setMinimum(1)
        self.midi_velocity_min.setMaximum(127)
        self.midi_velocity_min.setValue(1)
        self.midi_velocity_min.valueChanged.connect(lambda v: self.on_midi_velocity_slider_changed('min', v))
        min_layout.addWidget(self.midi_velocity_min, 1)
        self.midi_velocity_min_label = QLabel("1")
        self.midi_velocity_min_label.setMinimumWidth(40)
        self.midi_velocity_min_label.setMaximumWidth(40)
        self.midi_velocity_min_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        min_layout.addWidget(self.midi_velocity_min_label)
        adv_vel_layout.addLayout(min_layout)

        # Velocity Max (slider)
        max_layout = QHBoxLayout()
        max_layout.setContentsMargins(0, 0, 0, 0)
        max_layout.setSpacing(6)
        max_label = QLabel(tr("QuickActuationWidget", "Max:"))
        max_label.setMinimumWidth(70)
        max_label.setMaximumWidth(70)
        max_layout.addWidget(max_label)
        self.midi_velocity_max = QSlider(Qt.Horizontal)
        self.midi_velocity_max.setMinimum(1)
        self.midi_velocity_max.setMaximum(127)
        self.midi_velocity_max.setValue(127)
        self.midi_velocity_max.valueChanged.connect(lambda v: self.on_midi_velocity_slider_changed('max', v))
        max_layout.addWidget(self.midi_velocity_max, 1)
        self.midi_velocity_max_label = QLabel("127")
        self.midi_velocity_max_label.setMinimumWidth(40)
        self.midi_velocity_max_label.setMaximumWidth(40)
        self.midi_velocity_max_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        max_layout.addWidget(self.midi_velocity_max_label)
        adv_vel_layout.addLayout(max_layout)

        # Aftertouch settings
        aftertouch_group = QGroupBox(tr("QuickActuationWidget", "Aftertouch Settings"))
        aftertouch_layout = QVBoxLayout()
        aftertouch_layout.setSpacing(4)
        aftertouch_group.setLayout(aftertouch_layout)
        adv_layout.addWidget(aftertouch_group)

        # Aftertouch
        at_layout = QHBoxLayout()
        at_layout.setContentsMargins(0, 0, 0, 0)
        at_layout.setSpacing(6)
        at_label = QLabel(tr("QuickActuationWidget", "Aftertouch:"))
        at_label.setMinimumWidth(70)
        at_label.setMaximumWidth(70)
        at_layout.addWidget(at_label)
        self.midi_aftertouch = ArrowComboBox()
        self.midi_aftertouch.setMaximumHeight(30)
        self.midi_aftertouch.setMaximumWidth(180)
        self.midi_aftertouch.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        self.midi_aftertouch.addItem("Off", 0)
        self.midi_aftertouch.addItem("Reverse", 1)
        self.midi_aftertouch.addItem("Bottom-Out", 2)
        self.midi_aftertouch.addItem("Post-Actuation", 3)
        self.midi_aftertouch.addItem("Vibrato", 4)
        self.midi_aftertouch.setCurrentIndex(0)
        self.midi_aftertouch.currentIndexChanged.connect(self.on_midi_settings_changed)
        at_layout.addWidget(self.midi_aftertouch)
        at_layout.addStretch()
        aftertouch_layout.addLayout(at_layout)

        # Aftertouch CC
        atcc_layout = QHBoxLayout()
        atcc_layout.setContentsMargins(0, 0, 0, 0)
        atcc_layout.setSpacing(6)
        atcc_label = QLabel(tr("QuickActuationWidget", "AT CC:"))
        atcc_label.setMinimumWidth(70)
        atcc_label.setMaximumWidth(70)
        atcc_layout.addWidget(atcc_label)
        self.midi_aftertouch_cc = ArrowComboBox()
        self.midi_aftertouch_cc.setMaximumHeight(30)
        self.midi_aftertouch_cc.setMaximumWidth(180)
        self.midi_aftertouch_cc.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for cc in range(128):
            self.midi_aftertouch_cc.addItem(f"CC#{cc}", cc)
        self.midi_aftertouch_cc.setCurrentIndex(74)
        self.midi_aftertouch_cc.currentIndexChanged.connect(self.on_midi_settings_changed)
        atcc_layout.addWidget(self.midi_aftertouch_cc)
        atcc_layout.addStretch()
        aftertouch_layout.addLayout(atcc_layout)

        # KeySplit Enable
        self.keysplit_enabled_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable KeySplit"))
        self.keysplit_enabled_checkbox.stateChanged.connect(self.on_keysplit_enabled_toggled)
        adv_layout.addWidget(self.keysplit_enabled_checkbox)

        # KeySplit Settings (hidden by default)
        self.keysplit_widget = QWidget()
        keysplit_layout = QVBoxLayout()
        keysplit_layout.setSpacing(4)
        keysplit_layout.setContentsMargins(20, 5, 0, 0)
        self.keysplit_widget.setLayout(keysplit_layout)
        self.keysplit_widget.setVisible(False)
        adv_layout.addWidget(self.keysplit_widget)

        ks_label = QLabel(tr("QuickActuationWidget", "KeySplit Settings"))
        ks_label.setStyleSheet("QLabel { font-weight: bold; }")
        keysplit_layout.addWidget(ks_label)

        # KeySplit Channel
        ks_ch_layout = QHBoxLayout()
        ks_ch_layout.addWidget(QLabel(tr("QuickActuationWidget", "Channel:")))
        self.keysplit_channel = ArrowComboBox()
        self.keysplit_channel.setMinimumWidth(80)
        for i in range(16):
            self.keysplit_channel.addItem(f"{i + 1}", i)
        self.keysplit_channel.setCurrentIndex(0)
        self.keysplit_channel.currentIndexChanged.connect(self.on_midi_settings_changed)
        ks_ch_layout.addWidget(self.keysplit_channel)
        keysplit_layout.addLayout(ks_ch_layout)

        # KeySplit Transpose
        ks_trans_layout = QHBoxLayout()
        ks_trans_layout.addWidget(QLabel(tr("QuickActuationWidget", "Transpose:")))
        self.keysplit_transpose = ArrowComboBox()
        self.keysplit_transpose.setMinimumWidth(80)
        for i in range(-64, 65):
            self.keysplit_transpose.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.keysplit_transpose.setCurrentIndex(64)
        self.keysplit_transpose.currentIndexChanged.connect(self.on_midi_settings_changed)
        ks_trans_layout.addWidget(self.keysplit_transpose)
        keysplit_layout.addLayout(ks_trans_layout)

        # KeySplit Velocity Curve
        ks_curve_layout = QHBoxLayout()
        ks_curve_layout.addWidget(QLabel(tr("QuickActuationWidget", "Curve:")))
        self.keysplit_velocity_curve = ArrowComboBox()
        self.keysplit_velocity_curve.setMinimumWidth(80)
        self.keysplit_velocity_curve.addItem("Softest", 0)
        self.keysplit_velocity_curve.addItem("Soft", 1)
        self.keysplit_velocity_curve.addItem("Medium", 2)
        self.keysplit_velocity_curve.addItem("Hard", 3)
        self.keysplit_velocity_curve.addItem("Hardest", 4)
        self.keysplit_velocity_curve.setCurrentIndex(2)
        self.keysplit_velocity_curve.currentIndexChanged.connect(self.on_midi_settings_changed)
        ks_curve_layout.addWidget(self.keysplit_velocity_curve)
        keysplit_layout.addLayout(ks_curve_layout)

        # KeySplit Velocity Min
        ks_min_layout = QHBoxLayout()
        ks_min_layout.addWidget(QLabel(tr("QuickActuationWidget", "Min:")))
        self.keysplit_velocity_min = ArrowComboBox()
        self.keysplit_velocity_min.setMinimumWidth(80)
        for i in range(1, 128):
            self.keysplit_velocity_min.addItem(str(i), i)
        self.keysplit_velocity_min.setCurrentIndex(0)
        self.keysplit_velocity_min.currentIndexChanged.connect(self.on_midi_settings_changed)
        ks_min_layout.addWidget(self.keysplit_velocity_min)
        keysplit_layout.addLayout(ks_min_layout)

        # KeySplit Velocity Max
        ks_max_layout = QHBoxLayout()
        ks_max_layout.addWidget(QLabel(tr("QuickActuationWidget", "Max:")))
        self.keysplit_velocity_max = ArrowComboBox()
        self.keysplit_velocity_max.setMinimumWidth(80)
        for i in range(1, 128):
            self.keysplit_velocity_max.addItem(str(i), i)
        self.keysplit_velocity_max.setCurrentIndex(126)
        self.keysplit_velocity_max.currentIndexChanged.connect(self.on_midi_settings_changed)
        ks_max_layout.addWidget(self.keysplit_velocity_max)
        keysplit_layout.addLayout(ks_max_layout)

        # TripleSplit Enable
        self.triplesplit_enabled_checkbox = QCheckBox(tr("QuickActuationWidget", "Enable TripleSplit"))
        self.triplesplit_enabled_checkbox.stateChanged.connect(self.on_triplesplit_enabled_toggled)
        adv_layout.addWidget(self.triplesplit_enabled_checkbox)

        # TripleSplit Settings (hidden by default)
        self.triplesplit_widget = QWidget()
        triplesplit_layout = QVBoxLayout()
        triplesplit_layout.setSpacing(4)
        triplesplit_layout.setContentsMargins(20, 5, 0, 0)
        self.triplesplit_widget.setLayout(triplesplit_layout)
        self.triplesplit_widget.setVisible(False)
        adv_layout.addWidget(self.triplesplit_widget)

        ts_label = QLabel(tr("QuickActuationWidget", "TripleSplit Settings"))
        ts_label.setStyleSheet("QLabel { font-weight: bold; }")
        triplesplit_layout.addWidget(ts_label)

        # TripleSplit Channel
        ts_ch_layout = QHBoxLayout()
        ts_ch_layout.addWidget(QLabel(tr("QuickActuationWidget", "Channel:")))
        self.triplesplit_channel = ArrowComboBox()
        self.triplesplit_channel.setMinimumWidth(80)
        for i in range(16):
            self.triplesplit_channel.addItem(f"{i + 1}", i)
        self.triplesplit_channel.setCurrentIndex(0)
        self.triplesplit_channel.currentIndexChanged.connect(self.on_midi_settings_changed)
        ts_ch_layout.addWidget(self.triplesplit_channel)
        triplesplit_layout.addLayout(ts_ch_layout)

        # TripleSplit Transpose
        ts_trans_layout = QHBoxLayout()
        ts_trans_layout.addWidget(QLabel(tr("QuickActuationWidget", "Transpose:")))
        self.triplesplit_transpose = ArrowComboBox()
        self.triplesplit_transpose.setMinimumWidth(80)
        for i in range(-64, 65):
            self.triplesplit_transpose.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.triplesplit_transpose.setCurrentIndex(64)
        self.triplesplit_transpose.currentIndexChanged.connect(self.on_midi_settings_changed)
        ts_trans_layout.addWidget(self.triplesplit_transpose)
        triplesplit_layout.addLayout(ts_trans_layout)

        # TripleSplit Velocity Curve
        ts_curve_layout = QHBoxLayout()
        ts_curve_layout.addWidget(QLabel(tr("QuickActuationWidget", "Curve:")))
        self.triplesplit_velocity_curve = ArrowComboBox()
        self.triplesplit_velocity_curve.setMinimumWidth(80)
        self.triplesplit_velocity_curve.addItem("Softest", 0)
        self.triplesplit_velocity_curve.addItem("Soft", 1)
        self.triplesplit_velocity_curve.addItem("Medium", 2)
        self.triplesplit_velocity_curve.addItem("Hard", 3)
        self.triplesplit_velocity_curve.addItem("Hardest", 4)
        self.triplesplit_velocity_curve.setCurrentIndex(2)
        self.triplesplit_velocity_curve.currentIndexChanged.connect(self.on_midi_settings_changed)
        ts_curve_layout.addWidget(self.triplesplit_velocity_curve)
        triplesplit_layout.addLayout(ts_curve_layout)

        # TripleSplit Velocity Min
        ts_min_layout = QHBoxLayout()
        ts_min_layout.addWidget(QLabel(tr("QuickActuationWidget", "Min:")))
        self.triplesplit_velocity_min = ArrowComboBox()
        self.triplesplit_velocity_min.setMinimumWidth(80)
        for i in range(1, 128):
            self.triplesplit_velocity_min.addItem(str(i), i)
        self.triplesplit_velocity_min.setCurrentIndex(0)
        self.triplesplit_velocity_min.currentIndexChanged.connect(self.on_midi_settings_changed)
        ts_min_layout.addWidget(self.triplesplit_velocity_min)
        triplesplit_layout.addLayout(ts_min_layout)

        # TripleSplit Velocity Max
        ts_max_layout = QHBoxLayout()
        ts_max_layout.addWidget(QLabel(tr("QuickActuationWidget", "Max:")))
        self.triplesplit_velocity_max = ArrowComboBox()
        self.triplesplit_velocity_max.setMinimumWidth(80)
        for i in range(1, 128):
            self.triplesplit_velocity_max.addItem(str(i), i)
        self.triplesplit_velocity_max.setCurrentIndex(126)
        self.triplesplit_velocity_max.currentIndexChanged.connect(self.on_midi_settings_changed)
        ts_max_layout.addWidget(self.triplesplit_velocity_max)
        triplesplit_layout.addLayout(ts_max_layout)

        layout.addStretch()

        # Save MIDI Settings button
        self.save_midi_btn = QPushButton(tr("QuickActuationWidget", "Save MIDI Settings"))
        self.save_midi_btn.setMaximumHeight(24)
        self.save_midi_btn.setStyleSheet("padding: 2px 6px; font-size: 9pt;")
        self.save_midi_btn.clicked.connect(self.on_save_midi)
        layout.addWidget(self.save_midi_btn)

        return tab
    
    def on_advanced_toggled(self):
        """Toggle advanced options visibility"""
        show_advanced = self.advanced_checkbox.isChecked()
        self.advanced_widget.setVisible(show_advanced)

        # Show/hide MIDI controls based on advanced state
        self.midi_widget.setVisible(show_advanced)
        self.midi_rapid_checkbox.setVisible(show_advanced)

        # Update MIDI rapidfire widgets visibility based on checkbox state
        if show_advanced and self.midi_rapid_checkbox.isChecked():
            self.midi_rapid_sens_widget.setVisible(True)
            self.midi_rapid_vel_widget.setVisible(True)
        else:
            self.midi_rapid_sens_widget.setVisible(False)
            self.midi_rapid_vel_widget.setVisible(False)
    
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
    
    def on_rapidfire_toggled(self, state):
        """Show/hide rapidfire sensitivity slider"""
        self.rapid_widget.setVisible(state == Qt.Checked)
        if not self.syncing:
            self.save_ui_to_memory()
    
    def on_midi_rapidfire_toggled(self, state):
        """Show/hide MIDI rapidfire sliders"""
        enabled = (state == Qt.Checked)
        # Only show if advanced is visible
        if self.advanced_widget.isVisible():
            self.midi_rapid_sens_widget.setVisible(enabled)
            self.midi_rapid_vel_widget.setVisible(enabled)
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
                'rapid': self.rapid_slider.value(),
                'midi_rapid_sens': self.midi_rapid_sens_slider.value(),
                'midi_rapid_vel': self.midi_rapid_vel_slider.value(),
                'vel_speed': self.vel_speed_combo.currentData(),
                'rapidfire_enabled': self.rapid_checkbox.isChecked(),
                'midi_rapidfire_enabled': self.midi_rapid_checkbox.isChecked()
            }
        else:
            # Save to all layers (master mode)
            data = {
                'normal': self.normal_slider.value(),
                'midi': self.midi_slider.value(),
                'velocity': self.velocity_combo.currentData(),
                'rapid': self.rapid_slider.value(),
                'midi_rapid_sens': self.midi_rapid_sens_slider.value(),
                'midi_rapid_vel': self.midi_rapid_vel_slider.value(),
                'vel_speed': self.vel_speed_combo.currentData(),
                'rapidfire_enabled': self.rapid_checkbox.isChecked(),
                'midi_rapidfire_enabled': self.midi_rapid_checkbox.isChecked()
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
        
        self.rapid_slider.setValue(data['rapid'])
        self.rapid_value_label.setText(str(data['rapid']))
        
        self.midi_rapid_sens_slider.setValue(data['midi_rapid_sens'])
        self.midi_rapid_sens_value_label.setText(str(data['midi_rapid_sens']))
        
        self.midi_rapid_vel_slider.setValue(data['midi_rapid_vel'])
        self.midi_rapid_vel_value_label.setText(f"±{data['midi_rapid_vel']}")

        # Set combos
        for i in range(self.velocity_combo.count()):
            if self.velocity_combo.itemData(i) == data['velocity']:
                self.velocity_combo.setCurrentIndex(i)
                break

        for i in range(self.vel_speed_combo.count()):
            if self.vel_speed_combo.itemData(i) == data['vel_speed']:
                self.vel_speed_combo.setCurrentIndex(i)
                break

        # Set checkboxes
        self.rapid_checkbox.setChecked(data['rapidfire_enabled'])
        self.rapid_widget.setVisible(data['rapidfire_enabled'])
        self.midi_rapid_checkbox.setChecked(data['midi_rapidfire_enabled'])

        # Update MIDI rapidfire widgets visibility based on checkbox state and advanced mode
        if self.advanced_widget.isVisible() and data['midi_rapidfire_enabled']:
            self.midi_rapid_sens_widget.setVisible(True)
            self.midi_rapid_vel_widget.setVisible(True)
        else:
            self.midi_rapid_sens_widget.setVisible(False)
            self.midi_rapid_vel_widget.setVisible(False)

        self.syncing = False
    
    def on_midi_settings_changed(self):
        """Handle MIDI settings changes"""
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_velocity_preset_changed(self):
        """Handle velocity preset changes - update curve/min/max accordingly"""
        if self.syncing:
            return

        preset = self.midi_velocity_preset.currentData()
        # Preset mappings: Softest(0), Soft(1), Medium(2), Hard(3), Hardest(4)
        preset_map = {
            0: {'curve': 0, 'min': 1, 'max': 90},     # Softest
            1: {'curve': 1, 'min': 1, 'max': 110},    # Soft
            2: {'curve': 2, 'min': 1, 'max': 127},    # Medium
            3: {'curve': 3, 'min': 20, 'max': 127},   # Hard
            4: {'curve': 4, 'min': 40, 'max': 127}    # Hardest
        }

        if preset in preset_map:
            config = preset_map[preset]
            self.midi_settings['velocity_curve'] = config['curve']
            self.midi_settings['velocity_min'] = config['min']
            self.midi_settings['velocity_max'] = config['max']
            self.midi_settings['velocity_preset'] = preset

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

        # When entering advanced mode, hide preset selector
        # When leaving advanced mode, show preset selector
        if show_advanced:
            self.midi_velocity_preset.setVisible(False)
            self.midi_velocity_preset_label.setVisible(False)
            # Double the width when showing advanced settings
            self.setMinimumWidth(350)
            self.setMaximumWidth(700)
        else:
            self.midi_velocity_preset.setVisible(True)
            self.midi_velocity_preset_label.setVisible(True)
            # Set both min and max to standard width when not showing advanced
            self.setMinimumWidth(350)
            self.setMaximumWidth(350)

    def on_midi_velocity_slider_changed(self, slider_type, value):
        """Handle velocity slider changes"""
        if slider_type == 'min':
            self.midi_velocity_min_label.setText(str(value))
        elif slider_type == 'max':
            self.midi_velocity_max_label.setText(str(value))

        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_keysplit_enabled_toggled(self):
        """Toggle KeySplit settings visibility"""
        self.keysplit_widget.setVisible(self.keysplit_enabled_checkbox.isChecked())
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def on_triplesplit_enabled_toggled(self):
        """Toggle TripleSplit settings visibility"""
        self.triplesplit_widget.setVisible(self.triplesplit_enabled_checkbox.isChecked())
        if not self.syncing:
            self.save_midi_ui_to_memory()

    def save_midi_ui_to_memory(self):
        """Save MIDI settings from UI to memory"""
        self.midi_settings['channel'] = self.midi_channel.currentData()
        self.midi_settings['transpose'] = self.midi_transpose.currentData()
        self.midi_settings['velocity_preset'] = self.midi_velocity_preset.currentData()
        self.midi_settings['velocity_curve'] = self.midi_velocity_curve.currentData()
        self.midi_settings['velocity_min'] = self.midi_velocity_min.value()
        self.midi_settings['velocity_max'] = self.midi_velocity_max.value()
        self.midi_settings['aftertouch'] = self.midi_aftertouch.currentData()
        self.midi_settings['aftertouch_cc'] = self.midi_aftertouch_cc.currentData()

        self.midi_settings['keysplit_enabled'] = self.keysplit_enabled_checkbox.isChecked()
        self.midi_settings['keysplit_channel'] = self.keysplit_channel.currentData()
        self.midi_settings['keysplit_transpose'] = self.keysplit_transpose.currentData()
        self.midi_settings['keysplit_velocity_curve'] = self.keysplit_velocity_curve.currentData()
        self.midi_settings['keysplit_velocity_min'] = self.keysplit_velocity_min.currentData()
        self.midi_settings['keysplit_velocity_max'] = self.keysplit_velocity_max.currentData()

        self.midi_settings['triplesplit_enabled'] = self.triplesplit_enabled_checkbox.isChecked()
        self.midi_settings['triplesplit_channel'] = self.triplesplit_channel.currentData()
        self.midi_settings['triplesplit_transpose'] = self.triplesplit_transpose.currentData()
        self.midi_settings['triplesplit_velocity_curve'] = self.triplesplit_velocity_curve.currentData()
        self.midi_settings['triplesplit_velocity_min'] = self.triplesplit_velocity_min.currentData()
        self.midi_settings['triplesplit_velocity_max'] = self.triplesplit_velocity_max.currentData()

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


class ClickableWidget(QWidget):

    clicked = pyqtSignal()

    def mousePressEvent(self, evt):
        super().mousePressEvent(evt)
        self.clicked.emit()


class KeymapEditor(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

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

        # contains the actual keyboard
        self.container = KeyboardWidget2(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)

        # Layout with actuation on left, keyboard in center
        keyboard_layout = QHBoxLayout()
        keyboard_layout.setSpacing(10)  # Small spacing between widgets
        keyboard_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        keyboard_layout.addStretch(1)  # Add stretch before
        keyboard_layout.addWidget(self.quick_actuation, 0, Qt.AlignTop)
        keyboard_layout.addWidget(self.container, 0, Qt.AlignTop)
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

    def on_empty_space_clicked(self):
        self.container.deselect()
        self.container.update()

    def on_keycode_changed(self, code):
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
        self.refresh_layer_display()
        if self.container.active_mask:
            self.tabbed_keycodes.set_keycode_filter(keycode_filter_masked)
        else:
            self.tabbed_keycodes.set_keycode_filter(None)

    def on_key_deselected(self):
        self.tabbed_keycodes.set_keycode_filter(None)

    def on_layout_changed(self):
        if self.keyboard is None:
            return

        self.refresh_layer_display()
        self.keyboard.set_layout_options(self.layout_editor.pack())

    def on_keymap_override(self):
        self.refresh_layer_display()
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


class QuickActuationWidget(QGroupBox):
    """Full-featured per-layer actuation controls in keymap editor"""
    
    def __init__(self):
        super().__init__(tr("QuickActuationWidget", "Actuation Settings"))
        
        self.device = None
        self.syncing = False
        self.current_layer = 0
        self.per_layer_enabled = False
        
        # Cache all layer data in memory to avoid device I/O lag
        # Note: Global MIDI settings (velocity curves, aftertouch, transpose, channel) moved to keyboard settings
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
        
        self.setMinimumWidth(200)
        self.setMaximumWidth(350)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 15, 10, 10)
        self.setLayout(layout)
        
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

        # === VELOCITY CURVE CONTROLS ===
        # Velocity Curve combo (visible in advanced mode)
        curve_layout = QHBoxLayout()
        curve_layout.setContentsMargins(0, 0, 0, 0)
        curve_layout.setSpacing(6)
        curve_label = QLabel(tr("QuickActuationWidget", "Velocity Curve:"))
        curve_label.setMinimumWidth(90)
        curve_label.setMaximumWidth(90)
        curve_layout.addWidget(curve_label)

        self.he_curve_combo = ArrowComboBox()
        self.he_curve_combo.setMaximumHeight(30)
        self.he_curve_combo.setMaximumWidth(180)
        self.he_curve_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        self.he_curve_combo.setEditable(True)
        self.he_curve_combo.lineEdit().setReadOnly(True)
        self.he_curve_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.he_curve_combo.addItem("Softest", 0)
        self.he_curve_combo.addItem("Soft", 1)
        self.he_curve_combo.addItem("Medium", 2)
        self.he_curve_combo.addItem("Hard", 3)
        self.he_curve_combo.addItem("Hardest", 4)
        self.he_curve_combo.setCurrentIndex(2)  # Default: Medium
        curve_layout.addWidget(self.he_curve_combo, 1)

        self.velocity_curve_widget = QWidget()
        self.velocity_curve_widget.setLayout(curve_layout)
        self.velocity_curve_widget.setVisible(False)
        layout.addWidget(self.velocity_curve_widget)
        self.he_curve_combo.currentIndexChanged.connect(self.on_combo_changed)

        # Velocity Min slider
        vel_min_layout = QHBoxLayout()
        vel_min_layout.setContentsMargins(0, 0, 0, 0)
        vel_min_layout.setSpacing(6)
        vel_min_label = QLabel(tr("QuickActuationWidget", "Velocity Min:"))
        vel_min_label.setMinimumWidth(90)
        vel_min_label.setMaximumWidth(90)
        vel_min_layout.addWidget(vel_min_label)

        self.he_min_slider = QSlider(Qt.Horizontal)
        self.he_min_slider.setMinimum(1)
        self.he_min_slider.setMaximum(127)
        self.he_min_slider.setValue(1)
        vel_min_layout.addWidget(self.he_min_slider, 1)

        self.he_min_value_label = QLabel("1")
        self.he_min_value_label.setMinimumWidth(50)
        self.he_min_value_label.setMaximumWidth(50)
        self.he_min_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        vel_min_layout.addWidget(self.he_min_value_label)

        layout.addLayout(vel_min_layout)
        self.he_min_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('he_min', v, self.he_min_value_label)
        )

        # Velocity Max slider
        vel_max_layout = QHBoxLayout()
        vel_max_layout.setContentsMargins(0, 0, 0, 0)
        vel_max_layout.setSpacing(6)
        vel_max_label = QLabel(tr("QuickActuationWidget", "Velocity Max:"))
        vel_max_label.setMinimumWidth(90)
        vel_max_label.setMaximumWidth(90)
        vel_max_layout.addWidget(vel_max_label)

        self.he_max_slider = QSlider(Qt.Horizontal)
        self.he_max_slider.setMinimum(1)
        self.he_max_slider.setMaximum(127)
        self.he_max_slider.setValue(127)
        vel_max_layout.addWidget(self.he_max_slider, 1)

        self.he_max_value_label = QLabel("127")
        self.he_max_value_label.setMinimumWidth(50)
        self.he_max_value_label.setMaximumWidth(50)
        self.he_max_value_label.setStyleSheet("QLabel { font-weight: bold; font-size: 9px; }")
        vel_max_layout.addWidget(self.he_max_value_label)

        layout.addLayout(vel_max_layout)
        self.he_max_slider.valueChanged.connect(
            lambda v: self.on_slider_changed('he_max', v, self.he_max_value_label)
        )

        # === TRANSPOSE AND CHANNEL (always visible) ===
        # Transpose combo
        transpose_layout = QHBoxLayout()
        transpose_layout.setContentsMargins(0, 0, 0, 0)
        transpose_layout.setSpacing(6)
        transpose_label = QLabel(tr("QuickActuationWidget", "Transpose:"))
        transpose_label.setMinimumWidth(90)
        transpose_label.setMaximumWidth(90)
        transpose_layout.addWidget(transpose_label)

        self.transpose_combo = ArrowComboBox()
        self.transpose_combo.setMaximumHeight(30)
        self.transpose_combo.setMaximumWidth(180)
        self.transpose_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for i in range(-64, 65):
            self.transpose_combo.addItem(f"{'+' if i >= 0 else ''}{i}", i)
        self.transpose_combo.setCurrentIndex(64)  # Default: 0
        self.transpose_combo.setEditable(True)
        self.transpose_combo.lineEdit().setReadOnly(True)
        self.transpose_combo.lineEdit().setAlignment(Qt.AlignCenter)
        transpose_layout.addWidget(self.transpose_combo, 1)
        layout.addLayout(transpose_layout)
        self.transpose_combo.currentIndexChanged.connect(self.on_combo_changed)

        # Channel combo
        channel_layout = QHBoxLayout()
        channel_layout.setContentsMargins(0, 0, 0, 0)
        channel_layout.setSpacing(6)
        channel_label = QLabel(tr("QuickActuationWidget", "Channel:"))
        channel_label.setMinimumWidth(90)
        channel_label.setMaximumWidth(90)
        channel_layout.addWidget(channel_label)

        self.channel_combo = ArrowComboBox()
        self.channel_combo.setMaximumHeight(30)
        self.channel_combo.setMaximumWidth(180)
        self.channel_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for i in range(16):
            self.channel_combo.addItem(f"Channel {i + 1}", i)
        self.channel_combo.setCurrentIndex(0)  # Default: Channel 1 (0)
        self.channel_combo.setEditable(True)
        self.channel_combo.lineEdit().setReadOnly(True)
        self.channel_combo.lineEdit().setAlignment(Qt.AlignCenter)
        channel_layout.addWidget(self.channel_combo, 1)
        layout.addLayout(channel_layout)
        self.channel_combo.currentIndexChanged.connect(self.on_combo_changed)

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
        
        # Aftertouch Mode combo
        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(6)
        label = QLabel(tr("QuickActuationWidget", "Aftertouch:"))
        label.setMinimumWidth(90)
        label.setMaximumWidth(90)
        combo_layout.addWidget(label)

        self.aftertouch_combo = ArrowComboBox()
        self.aftertouch_combo.setMaximumHeight(30)
        self.aftertouch_combo.setMaximumWidth(180)
        self.aftertouch_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        self.aftertouch_combo.addItem("Off", 0)
        self.aftertouch_combo.addItem("Reverse", 1)
        self.aftertouch_combo.addItem("Bottom-Out", 2)
        self.aftertouch_combo.addItem("Post-Actuation", 3)
        self.aftertouch_combo.addItem("Vibrato", 4)
        self.aftertouch_combo.setCurrentIndex(0)
        self.aftertouch_combo.setEditable(True)
        self.aftertouch_combo.lineEdit().setReadOnly(True)
        self.aftertouch_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(self.aftertouch_combo, 1)
        
        advanced_layout.addLayout(combo_layout)
        self.aftertouch_combo.currentIndexChanged.connect(self.on_combo_changed)
        
        # Aftertouch CC combo
        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(6)
        label = QLabel(tr("QuickActuationWidget", "Aftertouch CC:"))
        label.setMinimumWidth(90)
        label.setMaximumWidth(90)
        combo_layout.addWidget(label)

        self.aftertouch_cc_combo = ArrowComboBox()
        self.aftertouch_cc_combo.setMaximumHeight(30)
        self.aftertouch_cc_combo.setMaximumWidth(180)
        self.aftertouch_cc_combo.setStyleSheet("QComboBox { padding: 0px; font-size: 12px; text-align: center; }")
        for cc in range(128):
            self.aftertouch_cc_combo.addItem(f"CC#{cc}", cc)
        self.aftertouch_cc_combo.setCurrentIndex(74)
        self.aftertouch_cc_combo.setEditable(True)
        self.aftertouch_cc_combo.lineEdit().setReadOnly(True)
        self.aftertouch_cc_combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo_layout.addWidget(self.aftertouch_cc_combo, 1)
        
        advanced_layout.addLayout(combo_layout)
        self.aftertouch_cc_combo.currentIndexChanged.connect(self.on_combo_changed)
        
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
        self.save_btn.clicked.connect(self.on_save)
        layout.addWidget(self.save_btn)
    
    def on_advanced_toggled(self):
        """Toggle advanced options visibility"""
        show_advanced = self.advanced_checkbox.isChecked()
        self.advanced_widget.setVisible(show_advanced)

        # Show/hide MIDI controls based on advanced state
        self.midi_widget.setVisible(show_advanced)
        self.midi_rapid_checkbox.setVisible(show_advanced)
        self.velocity_curve_widget.setVisible(show_advanced)

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
                'aftertouch': self.aftertouch_combo.currentData(),
                'velocity': self.velocity_combo.currentData(),
                'rapid': self.rapid_slider.value(),
                'midi_rapid_sens': self.midi_rapid_sens_slider.value(),
                'midi_rapid_vel': self.midi_rapid_vel_slider.value(),
                'vel_speed': self.vel_speed_combo.currentData(),
                'aftertouch_cc': self.aftertouch_cc_combo.currentData(),
                'rapidfire_enabled': self.rapid_checkbox.isChecked(),
                'midi_rapidfire_enabled': self.midi_rapid_checkbox.isChecked(),
                # HE Velocity fields
                'use_fixed_velocity': False,  # Fixed velocity feature removed
                'he_curve': self.he_curve_combo.currentData(),
                'he_min': self.he_min_slider.value(),
                'he_max': self.he_max_slider.value(),
                # Transpose and Channel
                'transpose': self.transpose_combo.currentData(),
                'channel': self.channel_combo.currentData()
            }
        else:
            # Save to all layers (master mode)
            data = {
                'normal': self.normal_slider.value(),
                'midi': self.midi_slider.value(),
                'aftertouch': self.aftertouch_combo.currentData(),
                'velocity': self.velocity_combo.currentData(),
                'rapid': self.rapid_slider.value(),
                'midi_rapid_sens': self.midi_rapid_sens_slider.value(),
                'midi_rapid_vel': self.midi_rapid_vel_slider.value(),
                'vel_speed': self.vel_speed_combo.currentData(),
                'aftertouch_cc': self.aftertouch_cc_combo.currentData(),
                'rapidfire_enabled': self.rapid_checkbox.isChecked(),
                'midi_rapidfire_enabled': self.midi_rapid_checkbox.isChecked(),
                # HE Velocity fields
                'use_fixed_velocity': False,  # Fixed velocity feature removed
                'he_curve': self.he_curve_combo.currentData(),
                'he_min': self.he_min_slider.value(),
                'he_max': self.he_max_slider.value(),
                # Transpose and Channel
                'transpose': self.transpose_combo.currentData(),
                'channel': self.channel_combo.currentData()
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
        for i in range(self.aftertouch_combo.count()):
            if self.aftertouch_combo.itemData(i) == data['aftertouch']:
                self.aftertouch_combo.setCurrentIndex(i)
                break
        
        for i in range(self.aftertouch_cc_combo.count()):
            if self.aftertouch_cc_combo.itemData(i) == data['aftertouch_cc']:
                self.aftertouch_cc_combo.setCurrentIndex(i)
                break
        
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

        # Velocity settings (renamed from HE Velocity)
        self.he_min_slider.setValue(data.get('he_min', 1))
        self.he_min_value_label.setText(str(data.get('he_min', 1)))
        self.he_max_slider.setValue(data.get('he_max', 127))
        self.he_max_value_label.setText(str(data.get('he_max', 127)))

        # Velocity Curve combo (renamed from HE Curve)
        for i in range(self.he_curve_combo.count()):
            if self.he_curve_combo.itemData(i) == data.get('he_curve', 2):
                self.he_curve_combo.setCurrentIndex(i)
                break

        # Transpose and Channel
        for i in range(self.transpose_combo.count()):
            if self.transpose_combo.itemData(i) == data.get('transpose', 0):
                self.transpose_combo.setCurrentIndex(i)
                break

        for i in range(self.channel_combo.count()):
            if self.channel_combo.itemData(i) == data.get('channel', 0):
                self.channel_combo.setCurrentIndex(i)
                break

        # Update MIDI rapidfire widgets visibility based on checkbox state and advanced mode
        if self.advanced_widget.isVisible() and data['midi_rapidfire_enabled']:
            self.midi_rapid_sens_widget.setVisible(True)
            self.midi_rapid_vel_widget.setVisible(True)
        else:
            self.midi_rapid_sens_widget.setVisible(False)
            self.midi_rapid_vel_widget.setVisible(False)

        self.syncing = False
    
    def on_save(self):
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